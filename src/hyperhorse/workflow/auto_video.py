#!/usr/bin/env python3
"""
HyperHorse自动化视频生成工作流
实现参数解析→引擎调用→结果回传→素材库归档的全链路自动化
集成容错机制：自动重试、降级策略、超时处理
"""

import json
import logging
import time
import uuid
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from enum import Enum
import hashlib
import sqlite3
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.hyperhorse.api_adapter import (
    HyperHorseAPIAdapter,
    VideoGenerationRequest,
    VideoGenerationResponse
)

logger = logging.getLogger(__name__)

# ====================== 工作流状态与常量 ======================

class WorkflowStatus(Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    TIMEOUT = "timeout"

class VideoQualityLevel(str, Enum):
    """视频质量等级"""
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"
    ULTRA = "ultra"

# ====================== 工作流数据模型 ======================

@dataclass
class VideoGenerationTask:
    """视频生成任务"""
    task_id: str
    prompt: str
    category: str
    target_regions: List[str]
    duration_seconds: int
    quality_level: VideoQualityLevel
    target_platforms: List[str]
    target_language: str
    style_guidelines: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    status: WorkflowStatus
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    priority: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['status'] = self.status.value
        data['quality_level'] = self.quality_level.value
        return data

@dataclass
class WorkflowResult:
    """工作流执行结果"""
    task_id: str
    status: WorkflowStatus
    video_urls: List[str]
    error_messages: List[str]
    performance_metrics: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data

# ====================== 参数解析器 ======================

class ParameterParser:
    """
    参数解析器
    将各种输入格式解析为标准化任务参数
    """
    
    @staticmethod
    def parse_openai_format(request_data: Dict[str, Any]) -> VideoGenerationTask:
        """
        解析OpenAI Video兼容格式
        
        参数:
            request_data: OpenAI格式请求数据
        
        返回:
            视频生成任务
        """
        # 提取基础参数
        prompt = request_data.get('prompt', '')
        model = request_data.get('model', 'hyperhorse-video-v1')
        size = request_data.get('size', '1080x1920')
        duration = request_data.get('duration', 15)
        quality = request_data.get('quality', 'hd')
        n = request_data.get('n', 1)
        language = request_data.get('language', 'en')
        
        # 解析品类
        category = ParameterParser._parse_category_from_prompt(prompt)
        
        # 解析尺寸
        width, height = ParameterParser._parse_size(size)
        
        # 映射质量等级
        quality_level = ParameterParser._map_quality_level(quality)
        
        # 映射目标平台
        target_platforms = ParameterParser._map_size_to_platforms(size)
        
        # 创建任务
        task_id = f"vid_{uuid.uuid4().hex[:24]}"
        now = datetime.now()
        
        return VideoGenerationTask(
            task_id=task_id,
            prompt=prompt,
            category=category,
            target_regions=["global"],
            duration_seconds=duration,
            quality_level=quality_level,
            target_platforms=target_platforms,
            target_language=language,
            style_guidelines={
                "prompt": prompt,
                "model": model,
                "size": size,
                "duration": duration,
                "quality": quality,
                "n": n,
                "width": width,
                "height": height
            },
            metadata=request_data.get('metadata', {}),
            created_at=now,
            updated_at=now,
            status=WorkflowStatus.PENDING
        )
    
    @staticmethod
    def parse_hyperhorse_format(request: VideoGenerationRequest) -> VideoGenerationTask:
        """
        解析HyperHorse原生格式
        
        参数:
            request: HyperHorse生成请求
        
        返回:
            视频生成任务
        """
        task_id = request.request_id or f"vid_{uuid.uuid4().hex[:24]}"
        now = datetime.now()
        
        return VideoGenerationTask(
            task_id=task_id,
            prompt=request.style_guidelines.get('prompt', '') if request.style_guidelines else '',
            category=request.category,
            target_regions=request.target_regions,
            duration_seconds=request.duration_seconds,
            quality_level=VideoQualityLevel(request.quality_level),
            target_platforms=request.target_platforms or [],
            target_language=request.target_language,
            style_guidelines=request.style_guidelines or {},
            metadata=request.metadata or {},
            created_at=now,
            updated_at=now,
            status=WorkflowStatus.PENDING
        )
    
    @staticmethod
    def _parse_category_from_prompt(prompt: str) -> str:
        """从prompt解析品类"""
        prompt_lower = prompt.lower()
        
        category_map = {
            "服装": ["clothing", "fashion", "apparel", "dress", "shirt", "pants", "jeans", "jacket"],
            "电子产品": ["electronics", "phone", "laptop", "camera", "gadget", "smartphone", "tablet"],
            "家居": ["home", "furniture", "decor", "kitchen", "bedroom", "living room", "家具"],
            "美妆": ["beauty", "cosmetics", "makeup", "skincare", "perfume", "化妆品", "护肤品"],
            "食品": ["food", "snack", "drink", "beverage", "recipe", "零食", "饮料"],
            "运动": ["sports", "fitness", "exercise", "outdoor", "gym", "健身", "运动装备"]
        }
        
        for category, keywords in category_map.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    return category
        
        return "综合"
    
    @staticmethod
    def _parse_size(size_str: str) -> Tuple[int, int]:
        """解析尺寸字符串"""
        try:
            parts = size_str.lower().replace('x', '×').split('×')
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        except:
            pass
        return 1080, 1920  # 默认竖屏
    
    @staticmethod
    def _map_quality_level(quality: str) -> VideoQualityLevel:
        """映射质量等级"""
        mapping = {
            "standard": VideoQualityLevel.STANDARD,
            "hd": VideoQualityLevel.PREMIUM,
            "ultra_hd": VideoQualityLevel.ULTRA,
            "economy": VideoQualityLevel.ECONOMY
        }
        return mapping.get(quality.lower(), VideoQualityLevel.PREMIUM)
    
    @staticmethod
    def _map_size_to_platforms(size: str) -> List[str]:
        """根据尺寸映射推荐平台"""
        if '1080x1920' in size or '1920x1080' not in size and '1080' in size:
            return ["tiktok", "instagram", "youtube_shorts"]
        elif '1920x1080' in size:
            return ["youtube", "facebook", "bilibili"]
        else:
            return ["instagram", "pinterest", "tiktok"]

# ====================== 容错处理器 ======================

class FaultToleranceHandler:
    """
    容错处理器
    实现自动重试、降级策略、超时处理
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: int = 5,
        timeout_seconds: int = 300,
        enable_degradation: bool = True
    ):
        """
        初始化容错处理器
        
        参数:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout_seconds: 超时时间（秒）
            enable_degradation: 是否启用降级策略
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout_seconds = timeout_seconds
        self.enable_degradation = enable_degradation
    
    def execute_with_retry(
        self,
        task_func: Callable,
        task_args: Tuple = (),
        task_kwargs: Dict[str, Any] = None,
        retry_conditions: Optional[List[Callable[[Exception], bool]]] = None
    ) -> Any:
        """
        带自动重试的执行
        
        参数:
            task_func: 任务函数
            task_args: 位置参数
            task_kwargs: 关键字参数
            retry_conditions: 重试条件函数列表
        
        返回:
            任务结果
        
        异常:
            重试耗尽后抛出最后一个异常
        """
        if task_kwargs is None:
            task_kwargs = {}
        
        last_exception = None
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                logger.info(f"执行任务，重试次数: {retry_count}/{self.max_retries}")
                
                # 执行任务
                result = task_func(*task_args, **task_kwargs)
                
                logger.info(f"任务执行成功，重试次数: {retry_count}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"任务执行失败: {str(e)}，重试次数: {retry_count}/{self.max_retries}")
                
                # 检查是否需要重试
                should_retry = self._should_retry(e, retry_conditions)
                
                if should_retry and retry_count < self.max_retries:
                    retry_count += 1
                    
                    # 应用降级策略
                    if self.enable_degradation:
                        task_kwargs = self._apply_degradation_strategy(
                            task_kwargs, retry_count
                        )
                    
                    # 延迟重试
                    if retry_count > 0:
                        delay = self.retry_delay * retry_count
                        logger.info(f"等待{delay}秒后重试...")
                        time.sleep(delay)
                else:
                    break
        
        # 重试耗尽
        error_msg = f"任务重试{self.max_retries}次后仍然失败: {str(last_exception)}"
        logger.error(error_msg)
        raise last_exception
    
    def execute_with_timeout(
        self,
        task_func: Callable,
        task_args: Tuple = (),
        task_kwargs: Dict[str, Any] = None,
        timeout_seconds: Optional[int] = None
    ) -> Any:
        """
        带超时控制的执行
        
        参数:
            task_func: 任务函数
            task_args: 位置参数
            task_kwargs: 关键字参数
            timeout_seconds: 超时时间（秒），默认使用实例设置
        
        返回:
            任务结果
        
        异常:
            超时抛出TimeoutError
        """
        if task_kwargs is None:
            task_kwargs = {}
        
        actual_timeout = timeout_seconds or self.timeout_seconds
        
        # 使用线程池执行带超时的任务
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(task_func, *task_args, **task_kwargs)
            
            try:
                result = future.result(timeout=actual_timeout)
                logger.info(f"任务在超时时间内完成: {actual_timeout}秒")
                return result
                
            except TimeoutError:
                logger.error(f"任务执行超时: {actual_timeout}秒")
                future.cancel()
                raise TimeoutError(f"任务执行超过{actual_timeout}秒未完成")
    
    def _should_retry(
        self,
        exception: Exception,
        retry_conditions: Optional[List[Callable[[Exception], bool]]] = None
    ) -> bool:
        """
        判断是否需要重试
        
        参数:
            exception: 异常对象
            retry_conditions: 自定义重试条件
        
        返回:
            是否需要重试
        """
        # 默认重试条件：网络相关错误、服务不可用、临时故障
        default_conditions = [
            lambda e: isinstance(e, ConnectionError),
            lambda e: isinstance(e, TimeoutError),
            lambda e: "timeout" in str(e).lower(),
            lambda e: "connection" in str(e).lower(),
            lambda e: "retry" in str(e).lower(),
            lambda e: "temporary" in str(e).lower(),
            lambda e: "service unavailable" in str(e).lower(),
        ]
        
        # 合并条件
        conditions = default_conditions
        if retry_conditions:
            conditions.extend(retry_conditions)
        
        # 检查是否满足任一条件
        for condition in conditions:
            try:
                if condition(exception):
                    return True
            except:
                continue
        
        return False
    
    def _apply_degradation_strategy(
        self,
        task_kwargs: Dict[str, Any],
        retry_count: int
    ) -> Dict[str, Any]:
        """
        应用降级策略
        
        参数:
            task_kwargs: 任务参数
            retry_count: 当前重试次数
        
        返回:
            应用降级后的任务参数
        """
        # 根据重试次数应用不同级别的降级
        degradation_level = min(retry_count, 3)  # 0-3级
        
        if degradation_level == 1:
            # 轻度降级：降低质量，缩短时长
            if 'quality_level' in task_kwargs:
                task_kwargs['quality_level'] = VideoQualityLevel.STANDARD
            if 'duration_seconds' in task_kwargs and task_kwargs['duration_seconds'] > 10:
                task_kwargs['duration_seconds'] = 10
            
        elif degradation_level == 2:
            # 中度降级：进一步降低质量，限制平台
            task_kwargs['quality_level'] = VideoQualityLevel.ECONOMY
            task_kwargs['duration_seconds'] = 5
            if 'target_platforms' in task_kwargs:
                task_kwargs['target_platforms'] = task_kwargs['target_platforms'][:1] if task_kwargs['target_platforms'] else ["tiktok"]
            
        elif degradation_level >= 3:
            # 重度降级：最小化配置
            task_kwargs['quality_level'] = VideoQualityLevel.ECONOMY
            task_kwargs['duration_seconds'] = 3
            task_kwargs['target_platforms'] = ["tiktok"]
            if 'style_guidelines' in task_kwargs:
                task_kwargs['style_guidelines']['minimal'] = True
        
        logger.info(f"应用降级策略级别{degradation_level}，更新任务参数")
        return task_kwargs

# ====================== 结果处理器 ======================

class ResultProcessor:
    """
    结果处理器
    处理生成结果，归档到素材库，回传到调用方
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化结果处理器
        
        参数:
            db_path: 数据库路径
        """
        self.db_path = db_path
    
    def process_result(
        self,
        task: VideoGenerationTask,
        response: VideoGenerationResponse
    ) -> WorkflowResult:
        """
        处理生成结果
        
        参数:
            task: 原始任务
            response: 生成响应
        
        返回:
            工作流结果
        """
        logger.info(f"处理视频生成结果，任务ID: {task.task_id}")
        
        try:
            # 归档到素材库
            archive_result = self._archive_to_material_library(task, response)
            
            # 创建结果对象
            result = WorkflowResult(
                task_id=task.task_id,
                status=WorkflowStatus.COMPLETED,
                video_urls=response.video_urls or [],
                error_messages=response.error_messages or [],
                performance_metrics=response.performance_metrics or {},
                created_at=task.created_at,
                completed_at=datetime.now()
            )
            
            # 记录性能数据
            self._record_performance_metrics(task, response)
            
            logger.info(f"结果处理完成，生成视频数量: {len(response.video_urls)}")
            
            return result
            
        except Exception as e:
            logger.error(f"结果处理失败: {str(e)}", exc_info=True)
            
            # 返回失败结果
            return WorkflowResult(
                task_id=task.task_id,
                status=WorkflowStatus.FAILED,
                video_urls=[],
                error_messages=[f"结果处理失败: {str(e)}"],
                performance_metrics={},
                created_at=task.created_at,
                completed_at=datetime.now()
            )
    
    def _archive_to_material_library(
        self,
        task: VideoGenerationTask,
        response: VideoGenerationResponse
    ) -> Dict[str, Any]:
        """
        归档到素材库
        
        参数:
            task: 原始任务
            response: 生成响应
        
        返回:
            归档结果
        """
        try:
            # 连接到素材库数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确保表存在
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS video_materials (
                    material_id TEXT PRIMARY KEY,
                    task_id TEXT,
                    prompt TEXT,
                    category TEXT,
                    quality_level TEXT,
                    duration_seconds INTEGER,
                    target_platforms TEXT,
                    video_urls TEXT,
                    style_guidelines TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    archive_status TEXT
                )
            ''')
            
            # 生成素材ID
            material_id = f"mat_{uuid.uuid4().hex[:16]}"
            
            # 插入数据
            cursor.execute('''
                INSERT INTO video_materials (
                    material_id, task_id, prompt, category, quality_level,
                    duration_seconds, target_platforms, video_urls,
                    style_guidelines, metadata, created_at, updated_at,
                    archive_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                material_id,
                task.task_id,
                task.prompt,
                task.category,
                task.quality_level.value,
                task.duration_seconds,
                json.dumps(task.target_platforms),
                json.dumps(response.video_urls),
                json.dumps(task.style_guidelines),
                json.dumps(task.metadata),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                "archived"
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"视频素材归档成功，素材ID: {material_id}")
            
            return {
                "material_id": material_id,
                "archive_status": "success"
            }
            
        except Exception as e:
            logger.error(f"素材归档失败: {str(e)}")
            raise
    
    def _record_performance_metrics(
        self,
        task: VideoGenerationTask,
        response: VideoGenerationResponse
    ):
        """
        记录性能指标
        
        参数:
            task: 原始任务
            response: 生成响应
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确保性能指标表存在
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS video_performance_metrics (
                    metric_id TEXT PRIMARY KEY,
                    task_id TEXT,
                    category TEXT,
                    quality_level TEXT,
                    duration_seconds INTEGER,
                    generation_time_seconds REAL,
                    video_count INTEGER,
                    success_rate REAL,
                    created_at TIMESTAMP
                )
            ''')
            
            # 计算生成时间
            if task.created_at and response.timestamp:
                generation_time = (response.timestamp - task.created_at).total_seconds()
            else:
                generation_time = 0
            
            # 计算成功率
            success_rate = 1.0 if response.status == "completed" else 0.0
            
            # 插入性能数据
            metric_id = f"met_{uuid.uuid4().hex[:16]}"
            
            cursor.execute('''
                INSERT INTO video_performance_metrics (
                    metric_id, task_id, category, quality_level,
                    duration_seconds, generation_time_seconds,
                    video_count, success_rate, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric_id,
                task.task_id,
                task.category,
                task.quality_level.value,
                task.duration_seconds,
                generation_time,
                len(response.video_urls),
                success_rate,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"性能指标记录成功，指标ID: {metric_id}")
            
        except Exception as e:
            logger.error(f"性能指标记录失败: {str(e)}")
            # 不抛出异常，避免影响主流程

# ====================== 工作流管理器 ======================

class AutoVideoWorkflowManager:
    """
    自动化视频生成工作流管理器
    协调参数解析、引擎调用、结果处理全流程
    """
    
    def __init__(
        self,
        db_path: str = "data/shared_state/state.db",
        max_retries: int = 3,
        timeout_seconds: int = 300
    ):
        """
        初始化工作流管理器
        
        参数:
            db_path: 数据库路径
            max_retries: 最大重试次数
            timeout_seconds: 超时时间（秒）
        """
        self.db_path = db_path
        
        # 初始化组件
        self.parameter_parser = ParameterParser()
        self.fault_tolerance = FaultToleranceHandler(
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        self.result_processor = ResultProcessor(db_path)
        
        # 初始化HyperHorse适配器
        self.adapter = HyperHorseAPIAdapter(db_path)
        
        logger.info(f"初始化自动化视频生成工作流管理器，数据库: {db_path}")
    
    def execute_workflow(
        self,
        request_data: Union[Dict[str, Any], VideoGenerationRequest],
        request_format: str = "auto"
    ) -> WorkflowResult:
        """
        执行工作流
        
        参数:
            request_data: 请求数据，支持多种格式
            request_format: 请求格式，可选"auto"、"openai"、"hyperhorse"
        
        返回:
            工作流结果
        """
        logger.info(f"开始执行视频生成工作流，请求格式: {request_format}")
        
        start_time = datetime.now()
        
        try:
            # 第一步：参数解析
            task = self._parse_parameters(request_data, request_format)
            
            # 第二步：生成视频（带容错处理）
            response = self._generate_video_with_fault_tolerance(task)
            
            # 第三步：处理结果
            result = self.result_processor.process_result(task, response)
            
            # 计算总耗时
            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"工作流执行完成，总耗时: {total_time:.2f}秒，状态: {result.status.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}", exc_info=True)
            
            # 创建失败结果
            end_time = datetime.now()
            
            # 尝试提取任务ID
            task_id = "unknown"
            if isinstance(request_data, VideoGenerationRequest) and hasattr(request_data, 'request_id'):
                task_id = request_data.request_id
            elif isinstance(request_data, dict):
                task_id = request_data.get('request_id', f"vid_{uuid.uuid4().hex[:24]}")
            
            return WorkflowResult(
                task_id=task_id,
                status=WorkflowStatus.FAILED,
                video_urls=[],
                error_messages=[f"工作流执行失败: {str(e)}"],
                performance_metrics={
                    "total_time_seconds": (end_time - start_time).total_seconds(),
                    "error_type": type(e).__name__
                },
                created_at=start_time,
                completed_at=end_time
            )
    
    def _parse_parameters(
        self,
        request_data: Union[Dict[str, Any], VideoGenerationRequest],
        request_format: str
    ) -> VideoGenerationTask:
        """
        解析参数
        
        参数:
            request_data: 请求数据
            request_format: 请求格式
        
        返回:
            视频生成任务
        """
        # 自动检测格式
        if request_format == "auto":
            if isinstance(request_data, VideoGenerationRequest):
                request_format = "hyperhorse"
            elif isinstance(request_data, dict) and 'prompt' in request_data:
                request_format = "openai"
            else:
                request_format = "hyperhorse"
        
        # 根据格式解析
        if request_format == "openai":
            return self.parameter_parser.parse_openai_format(request_data)
        elif request_format == "hyperhorse":
            if isinstance(request_data, VideoGenerationRequest):
                return self.parameter_parser.parse_hyperhorse_format(request_data)
            else:
                # 转换为VideoGenerationRequest
                request = VideoGenerationRequest(**request_data)
                return self.parameter_parser.parse_hyperhorse_format(request)
        else:
            raise ValueError(f"不支持的请求格式: {request_format}")
    
    def _generate_video_with_fault_tolerance(
        self,
        task: VideoGenerationTask
    ) -> VideoGenerationResponse:
        """
        带容错处理的视频生成
        
        参数:
            task: 视频生成任务
        
        返回:
            视频生成响应
        """
        logger.info(f"开始带容错处理的视频生成，任务ID: {task.task_id}")
        
        # 创建HyperHorse请求
        request = VideoGenerationRequest(
            request_id=task.task_id,
            category=task.category,
            target_regions=task.target_regions,
            duration_seconds=task.duration_seconds,
            quality_level=task.quality_level.value,
            target_platforms=task.target_platforms,
            target_language=task.target_language,
            style_guidelines=task.style_guidelines,
            metadata=task.metadata
        )
        
        # 定义生成函数
        def generate_func():
            return self.adapter.generate_video(request)
        
        # 带超时和重试的执行
        try:
            # 带超时执行
            response = self.fault_tolerance.execute_with_timeout(
                generate_func,
                timeout_seconds=task.timeout_seconds
            )
            
            # 如果失败，尝试重试
            if response.status != "completed":
                logger.warning(f"视频生成未完成，状态: {response.status}，尝试重试")
                
                response = self.fault_tolerance.execute_with_retry(
                    generate_func,
                    retry_conditions=[
                        lambda e: response.status in ["failed", "timeout"]
                    ]
                )
            
            return response
            
        except TimeoutError:
            logger.error(f"视频生成超时，任务ID: {task.task_id}")
            raise
        except Exception as e:
            logger.error(f"视频生成失败: {str(e)}")
            raise

# ====================== 快速使用接口 ======================

def create_video_generation_workflow(
    prompt: str,
    category: Optional[str] = None,
    duration_seconds: int = 15,
    quality_level: str = "premium",
    target_regions: Optional[List[str]] = None,
    target_platforms: Optional[List[str]] = None,
    request_format: str = "openai",
    **kwargs
) -> WorkflowResult:
    """
    快速创建视频生成工作流（简化接口）
    
    参数:
        prompt: 视频内容描述
        category: 视频品类，如未提供则自动解析
        duration_seconds: 视频时长（秒）
        quality_level: 质量等级（economy/standard/premium/ultra）
        target_regions: 目标地区列表
        target_platforms: 目标平台列表
        request_format: 请求格式（openai/hyperhorse）
        **kwargs: 其他参数
    
    返回:
        工作流结果
    
    示例:
    ```python
    result = create_video_generation_workflow(
        prompt="时尚服装展示",
        duration_seconds=30,
        quality_level="ultra"
    )
    ```
    """
    # 初始化管理器
    manager = AutoVideoWorkflowManager()
    
    # 准备请求数据
    if request_format == "openai":
        request_data = {
            "prompt": prompt,
            "duration": duration_seconds,
            "quality": quality_level,
            "metadata": kwargs
        }
    else:
        # hyperhorse格式
        request_data = VideoGenerationRequest(
            category=category or "综合",
            target_regions=target_regions or ["global"],
            duration_seconds=duration_seconds,
            quality_level=quality_level,
            target_platforms=target_platforms or ["tiktok"],
            target_language="en",
            style_guidelines={"prompt": prompt},
            metadata=kwargs
        )
    
    # 执行工作流
    return manager.execute_workflow(request_data, request_format)

# ====================== 批量处理接口 ======================

def batch_video_generation_workflow(
    prompts: List[str],
    category: Optional[str] = None,
    max_workers: int = 3,
    **kwargs
) -> List[WorkflowResult]:
    """
    批量视频生成工作流
    
    参数:
        prompts: 视频内容描述列表
        category: 视频品类
        max_workers: 最大并行工作数
        **kwargs: 其他参数
    
    返回:
        工作流结果列表
    
    示例:
    ```python
    results = batch_video_generation_workflow(
        prompts=["时尚服装", "电子产品", "家居装饰"],
        category="服装",
        max_workers=2
    )
    ```
    """
    logger.info(f"开始批量视频生成，任务数量: {len(prompts)}，最大并行数: {max_workers}")
    
    results = []
    
    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 创建任务列表
        future_to_prompt = {
            executor.submit(
                create_video_generation_workflow,
                prompt=prompt,
                category=category,
                **kwargs
            ): prompt
            for prompt in prompts
        }
        
        # 收集结果
        for future in as_completed(future_to_prompt):
            prompt = future_to_prompt[future]
            
            try:
                result = future.result()
                results.append(result)
                logger.info(f"批量任务完成，prompt: {prompt[:50]}...，状态: {result.status.value}")
                
            except Exception as e:
                logger.error(f"批量任务失败，prompt: {prompt[:50]}...，错误: {str(e)}")
                
                # 创建失败结果
                failed_result = WorkflowResult(
                    task_id=f"batch_failed_{uuid.uuid4().hex[:12]}",
                    status=WorkflowStatus.FAILED,
                    video_urls=[],
                    error_messages=[f"批量任务失败: {str(e)}"],
                    performance_metrics={"error": type(e).__name__},
                    created_at=datetime.now(),
                    completed_at=datetime.now()
                )
                results.append(failed_result)
    
    logger.info(f"批量视频生成完成，成功: {sum(1 for r in results if r.status == WorkflowStatus.COMPLETED)}，失败: {sum(1 for r in results if r.status == WorkflowStatus.FAILED)}")
    
    return results

# ====================== 主函数（示例使用） ======================

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 示例1：使用OpenAI格式
    print("=== 示例1: OpenAI格式视频生成 ===")
    
    result = create_video_generation_workflow(
        prompt="时尚服装展示视频，模特在都市街拍，展示最新秋季服装系列",
        duration_seconds=30,
        quality_level="ultra",
        style="cinematic",
        language="en"
    )
    
    print(f"任务ID: {result.task_id}")
    print(f"状态: {result.status.value}")
    print(f"视频数量: {len(result.video_urls)}")
    if result.video_urls:
        print(f"视频URL示例: {result.video_urls[0]}")
    
    print("\n=== 示例2: 批量视频生成 ===")
    
    prompts = [
        "电子产品开箱视频，最新智能手机详细评测",
        "美食制作教程，简单易学的意大利面做法",
        "健身训练指导，家庭健身器材使用演示"
    ]
    
    results = batch_video_generation_workflow(
        prompts=prompts,
        max_workers=2
    )
    
    for i, r in enumerate(results):
        print(f"任务{i+1}: ID={r.task_id}, 状态={r.status.value}, 视频数量={len(r.video_urls)}")