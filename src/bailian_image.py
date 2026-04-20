#!/usr/bin/env python3
"""
阿里云百炼（Bailian）图片生成适配器

SellAI视觉生成模块扩展，支持百炼平台的图片生成能力：
- 文生图（wanx-v1）
- 图生图
- 虚拟模特（virtualmodel-v2）
- AI试衣
- 创意海报生成
- 图像背景生成

Author: SellAI Team
Version: 1.0.0
Date: 2026-04-16
"""

import os
import json
import time
import asyncio
import logging
import uuid
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

import httpx

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BailianTaskStatus(Enum):
    """百炼任务状态枚举"""
    PENDING = "PENDING"           # 任务等待中
    RUNNING = "RUNNING"          # 任务执行中
    SUCCEEDED = "SUCCEEDED"      # 任务成功
    FAILED = "FAILED"            # 任务失败
    CANCELLED = "CANCELLED"      # 任务取消


class BailianImageStyle(str, Enum):
    """百炼图片风格枚举"""
    PHOTOGRAPHY = "photography"               # 摄影风格
    PORTRAIT = "portrait"                     # 人像风格
    CD3_CARTOON = "3d-cartoon"                # 3D卡通（CD3避免冲突）
    ANIME = "anime"                           # 动画风格
    OIL_PAINTING = "oil_painting"             # 油画风格
    WATERCOLOR = "watercolor"                 # 水彩风格
    SKETCH = "sketch"                         # 素描风格
    CHINESE_PAINTING = "chinese_painting"    # 中国画
    MINIMALIST = "minimalist"                 # 极简风格
    COMMERCIAL = "commercial"                 # 商业摄影
    
    @property
    def raw_value(self):
        return self.value
    
    @classmethod
    def from_value(cls, value):
        """从值获取枚举成员"""
        for member in cls:
            if member.value == value:
                return member
        return None


class BailianModel(Enum):
    """百炼模型枚举"""
    TEXT2IMAGE = "wanx-v1"               # 文生图
    IMAGE2IMAGE = "image-synthesis"      # 图生图
    VIRTUAL_MODEL = "virtualmodel-v2"   # 虚拟模特
    AI_TRYON = "ai-tryon"               # AI试衣
    POSTER = "wanx-poster"              # 创意海报
    BACKGROUND = "background-generation"  # 背景生成


@dataclass
class BailianImageRequest:
    """百炼图片生成请求"""
    request_id: str
    model: Union[str, BailianModel]
    prompt: str
    negative_prompt: Optional[str] = None
    style: Optional[Union[str, BailianImageStyle]] = None
    image_url: Optional[str] = None  # 图生图/虚拟模特需要
    input_image_type: Optional[str] = None  # input_image_type
    n: int = 1  # 生成数量
    size: str = "1024*1024"  # 图片尺寸
    seed: Optional[int] = None
    ref_image_url: Optional[str] = None
    mask_image_url: Optional[str] = None
    output_type: str = "url"  # url or base64
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = f"bailian_{uuid.uuid4().hex[:12]}"
        if isinstance(self.model, BailianModel):
            self.model = self.model.value
        if isinstance(self.style, BailianImageStyle):
            self.style = self.style.value


@dataclass
class BailianTask:
    """百炼异步任务"""
    task_id: str
    request: BailianImageRequest
    status: BailianTaskStatus
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'request_id': self.request.request_id,
            'status': self.status.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'result': self.result,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }


@dataclass
class BailianImageResult:
    """百炼图片生成结果"""
    request_id: str
    success: bool
    task_id: Optional[str] = None
    images: List[Dict[str, str]] = field(default_factory=list)  # [{url, base64}]
    status: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'request_id': self.request_id,
            'success': self.success,
            'metadata': self.metadata
        }
        
        if self.task_id:
            result['task_id'] = self.task_id
        if self.images:
            result['images'] = self.images
        if self.status:
            result['status'] = self.status
        if self.error_message:
            result['error_message'] = self.error_message
        if self.processing_time:
            result['processing_time'] = self.processing_time
            
        return result


class BailianConfig:
    """百炼配置管理"""
    
    DEFAULT_CONFIG = {
        "bailian": {
            "api_key": "",
            "base_url": "https://dashscope.aliyuncs.com",
            "models": {
                "text2image": "wanx-v1",
                "image2image": "image-synthesis",
                "virtual_model": "virtualmodel-v2",
                "ai_tryon": "ai-tryon",
                "poster": "wanx-poster",
                "background": "background-generation"
            },
            "timeouts": {
                "task_submit": 30,
                "task_query": 10,
                "task_poll": 60
            },
            "polling": {
                "max_attempts": 60,
                "interval": 2
            },
            "retry": {
                "max_attempts": 3,
                "backoff_factor": 1.5
            }
        }
    }
    
    def __init__(self, config_path: str = "ecommerce_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 确保bailian配置存在
                if 'bailian' not in config:
                    config['bailian'] = self.DEFAULT_CONFIG['bailian']
                    self._save_config(config)
                return config
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
                return self.DEFAULT_CONFIG
        else:
            # 创建默认配置
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(self.config_path) if os.path.dirname(self.config_path) else '.', exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置文件已保存: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get('bailian', {}).get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        if 'bailian' not in self.config:
            self.config['bailian'] = {}
        self.config['bailian'][key] = value
        return self._save_config(self.config)
    
    def get_api_key(self) -> str:
        """获取API密钥"""
        return self.get('api_key', '')
    
    def get_base_url(self) -> str:
        """获取基础URL"""
        return self.get('base_url', 'https://dashscope.aliyuncs.com')
    
    def get_model(self, model_key: str) -> str:
        """获取模型名称"""
        models = self.get('models', {})
        return models.get(model_key, model_key)


class BailianImageAdapter:
    """
    阿里云百炼图片生成适配器
    
    特性：
    - 异步任务提交与轮询
    - 多种图片生成模式（文生图、图生图、虚拟模特等）
    - 自动重试机制
    - 任务状态管理
    - 错误处理与日志
    """
    
    def __init__(self, config: Optional[BailianConfig] = None, 
                 config_path: str = "ecommerce_config.json"):
        """
        初始化百炼适配器
        
        Args:
            config: BailianConfig实例，如果为None则从配置文件加载
            config_path: 配置文件路径
        """
        self.config = config or BailianConfig(config_path)
        self._init_client()
        self._tasks: Dict[str, BailianTask] = {}
        
        logger.info("阿里云百炼图片生成适配器初始化完成")
    
    def _init_client(self):
        """初始化HTTP客户端"""
        timeout_config = self.config.get('timeouts', {})
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=30,
                read=timeout_config.get('task_query', 10),
                write=timeout_config.get('task_submit', 30),
                pool=60
            ),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        api_key = self.config.get_api_key()
        if not api_key:
            logger.warning("百炼API密钥未配置，请在配置文件或环境变量中设置")
        
        return {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'true'
        }
    
    def _get_service_url(self, model: str) -> str:
        """获取服务URL"""
        base_url = self.config.get_base_url()
        return f"{base_url}/api/v1/services/aigc/text2image/{model}"
    
    async def submit_task(self, request: BailianImageRequest) -> BailianTask:
        """
        提交图片生成任务
        
        Args:
            request: 图片生成请求
            
        Returns:
            BailianTask: 提交的任务对象
        """
        task_id = None
        error_msg = None
        
        try:
            # 构建请求体
            payload = self._build_payload(request)
            
            # 获取服务URL
            service_url = self._get_service_url(request.model)
            
            logger.info(f"提交百炼任务: {request.request_id}, 模型: {request.model}")
            logger.debug(f"请求URL: {service_url}")
            logger.debug(f"请求体: {json.dumps(payload, ensure_ascii=False)[:500]}")
            
            # 发送请求
            headers = self._get_headers()
            response = await self.client.post(
                service_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get('output', {}).get('task_id')
                
                if task_id:
                    logger.info(f"任务提交成功: {task_id}")
                else:
                    error_msg = f"响应中未包含task_id: {result}"
                    logger.error(error_msg)
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"任务提交失败: {error_msg}")
                
                # 尝试从响应中提取错误信息
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = error_data['error'].get('message', error_msg)
                except:
                    pass
                    
        except httpx.TimeoutException:
            error_msg = "请求超时"
            logger.error(f"任务提交超时: {request.request_id}")
        except httpx.ConnectError as e:
            error_msg = f"连接失败: {str(e)}"
            logger.error(f"连接失败: {error_msg}")
        except Exception as e:
            error_msg = f"提交任务异常: {str(e)}"
            logger.error(error_msg)
        
        # 创建任务对象
        now = datetime.now().isoformat()
        task = BailianTask(
            task_id=task_id or f"local_{uuid.uuid4().hex[:12]}",
            request=request,
            status=BailianTaskStatus.SUCCEEDED if task_id else FAILED,
            created_at=now,
            updated_at=now,
            error_message=error_msg
        )
        
        self._tasks[task.task_id] = task
        return task
    
    def _build_payload(self, request: BailianImageRequest) -> Dict[str, Any]:
        """构建请求体"""
        payload = {
            "model": request.model,
            "input": {
                "prompt": request.prompt
            },
            "parameters": {
                "n": request.n,
                "size": request.size,
                "output_type": request.output_type
            }
        }
        
        # 添加负面提示词
        if request.negative_prompt:
            payload["input"]["negative_prompt"] = request.negative_prompt
        
        # 添加风格
        if request.style:
            payload["parameters"]["style"] = request.style
        
        # 添加参考图（图生图/虚拟模特等）
        if request.ref_image_url:
            payload["input"]["ref_image_url"] = request.ref_image_url
        
        # 添加输入图片（图生图）
        if request.image_url:
            payload["input"]["image_url"] = request.image_url
        
        # 添加掩码图
        if request.mask_image_url:
            payload["input"]["mask_image_url"] = request.mask_image_url
        
        # 添加随机种子
        if request.seed is not None:
            payload["parameters"]["seed"] = request.seed
        
        return payload
    
    async def query_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        查询任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        try:
            base_url = self.config.get_base_url()
            query_url = f"{base_url}/api/v1/tasks/{task_id}"
            
            headers = self._get_headers()
            response = await self.client.get(query_url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"查询任务失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"查询任务异常: {e}")
            return None
    
    async def wait_for_completion(self, task_id: str, 
                                  max_attempts: Optional[int] = None,
                                  interval: Optional[float] = None) -> BailianTask:
        """
        等待任务完成（轮询）
        
        Args:
            task_id: 任务ID
            max_attempts: 最大轮询次数
            interval: 轮询间隔（秒）
            
        Returns:
            完成的任务对象
        """
        polling_config = self.config.get('polling', {})
        max_attempts = max_attempts or polling_config.get('max_attempts', 60)
        interval = interval or polling_config.get('interval', 2)
        
        task = self._tasks.get(task_id)
        if not task:
            task = BailianTask(
                task_id=task_id,
                request=BailianImageRequest(request_id=task_id, model="wanx-v1", prompt=""),
                status=BailianTaskStatus.PENDING,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            self._tasks[task_id] = task
        
        for attempt in range(max_attempts):
            try:
                result = await self.query_task(task_id)
                
                if result:
                    output = result.get('output', {})
                    task_status = output.get('task_status', '')
                    
                    # 映射状态
                    if task_status == 'SUCCEEDED':
                        task.status = BailianTaskStatus.SUCCEEDED
                        task.result = output
                        task.updated_at = datetime.now().isoformat()
                        logger.info(f"任务完成: {task_id}")
                        return task
                    elif task_status == 'FAILED':
                        task.status = BailianTaskStatus.FAILED
                        task.error_message = output.get('message', '任务失败')
                        task.updated_at = datetime.now().isoformat()
                        logger.error(f"任务失败: {task_id}, 原因: {task.error_message}")
                        return task
                    elif task_status == 'CANCELLED':
                        task.status = BailianTaskStatus.CANCELLED
                        task.updated_at = datetime.now().isoformat()
                        return task
                    else:
                        task.status = BailianTaskStatus.RUNNING
                        task.updated_at = datetime.now().isoformat()
                        
                if attempt < max_attempts - 1:
                    await asyncio.sleep(interval)
                    
            except Exception as e:
                logger.error(f"轮询任务异常: {e}")
                task.retry_count += 1
                
                if task.retry_count >= 3:
                    task.status = BailianTaskStatus.FAILED
                    task.error_message = f"轮询失败: {str(e)}"
                    return task
                    
                await asyncio.sleep(interval * 2)
        
        # 超时处理
        task.status = BailianTaskStatus.FAILED
        task.error_message = f"任务超时（轮询{max_attempts}次）"
        logger.warning(f"任务超时: {task_id}")
        return task
    
    async def generate_text2image(self, prompt: str,
                                  style: Optional[Union[str, BailianImageStyle]] = None,
                                  negative_prompt: Optional[str] = None,
                                  size: str = "1024*1024",
                                  n: int = 1,
                                  seed: Optional[int] = None,
                                  wait: bool = True,
                                  timeout: int = 120) -> BailianImageResult:
        """
        文生图 - 根据文字描述生成图片
        
        Args:
            prompt: 图片描述
            style: 风格（可选）
            negative_prompt: 负面提示词
            size: 图片尺寸
            n: 生成数量
            seed: 随机种子
            wait: 是否等待完成
            timeout: 超时时间（秒）
            
        Returns:
            BailianImageResult: 生成结果
        """
        request = BailianImageRequest(
            request_id=f"t2i_{uuid.uuid4().hex[:8]}",
            model=BailianModel.TEXT2IMAGE.value,
            prompt=prompt,
            style=style,
            negative_prompt=negative_prompt,
            size=size,
            n=n,
            seed=seed
        )
        
        return await self._execute_request(request, wait, timeout)
    
    async def generate_image2image(self, prompt: str,
                                    ref_image_url: str,
                                    style: Optional[Union[str, BailianImageStyle]] = None,
                                    strength: float = 0.7,
                                    size: str = "1024*1024",
                                    n: int = 1,
                                    wait: bool = True,
                                    timeout: int = 120) -> BailianImageResult:
        """
        图生图 - 参考图片生成新图
        
        Args:
            prompt: 图片描述
            ref_image_url: 参考图片URL
            style: 风格（可选）
            strength: 生成强度 (0-1)
            size: 图片尺寸
            n: 生成数量
            wait: 是否等待完成
            timeout: 超时时间（秒）
            
        Returns:
            BailianImageResult: 生成结果
        """
        request = BailianImageRequest(
            request_id=f"i2i_{uuid.uuid4().hex[:8]}",
            model=BailianModel.IMAGE2IMAGE.value,
            prompt=prompt,
            style=style,
            ref_image_url=ref_image_url,
            size=size,
            n=n
        )
        
        return await self._execute_request(request, wait, timeout)
    
    async def generate_virtual_model(self, product_image_url: str,
                                       model_type: str = "female_casual",
                                       size: str = "1024*1024",
                                       wait: bool = True,
                                       timeout: int = 180) -> BailianImageResult:
        """
        虚拟模特 - 人台图生成真人模特图
        
        Args:
            product_image_url: 产品/人台图URL
            model_type: 模特类型 (female_casual, male_suit, etc.)
            size: 图片尺寸
            wait: 是否等待完成
            timeout: 超时时间（秒）
            
        Returns:
            BailianImageResult: 生成结果
        """
        request = BailianImageRequest(
            request_id=f"vm_{uuid.uuid4().hex[:8]}",
            model=BailianModel.VIRTUAL_MODEL.value,
            prompt=f"虚拟模特图，类型: {model_type}",
            image_url=product_image_url,
            size=size,
            n=1
        )
        
        return await self._execute_request(request, wait, timeout)
    
    async def generate_ai_tryon(self, garment_image_url: str,
                                 model_image_url: str,
                                 size: str = "1024*1024",
                                 wait: bool = True,
                                 timeout: int = 180) -> BailianImageResult:
        """
        AI试衣 - 模特换装试穿
        
        Args:
            garment_image_url: 服装图片URL
            model_image_url: 模特图片URL
            size: 图片尺寸
            wait: 是否等待完成
            timeout: 超时时间（秒）
            
        Returns:
            BailianImageResult: 生成结果
        """
        request = BailianImageRequest(
            request_id=f"tryon_{uuid.uuid4().hex[:8]}",
            model=BailianModel.AI_TRYON.value,
            prompt="AI试衣效果图",
            image_url=model_image_url,
            ref_image_url=garment_image_url,
            size=size,
            n=1
        )
        
        return await self._execute_request(request, wait, timeout)
    
    async def generate_poster(self, prompt: str,
                               size: str = "1024*1782",
                               wait: bool = True,
                               timeout: int = 120) -> BailianImageResult:
        """
        创意海报生成
        
        Args:
            prompt: 海报描述
            size: 海报尺寸（竖版海报常用1782*1024）
            wait: 是否等待完成
            timeout: 超时时间（秒）
            
        Returns:
            BailianImageResult: 生成结果
        """
        request = BailianImageRequest(
            request_id=f"poster_{uuid.uuid4().hex[:8]}",
            model=BailianModel.POSTER.value,
            prompt=prompt,
            size=size,
            n=1
        )
        
        return await self._execute_request(request, wait, timeout)
    
    async def generate_background(self, product_image_url: str,
                                   background_prompt: str,
                                   size: str = "1024*1024",
                                   wait: bool = True,
                                   timeout: int = 120) -> BailianImageResult:
        """
        图像背景生成 - 产品图换背景
        
        Args:
            product_image_url: 产品图片URL
            background_prompt: 背景描述
            size: 图片尺寸
            wait: 是否等待完成
            timeout: 超时时间（秒）
            
        Returns:
            BailianImageResult: 生成结果
        """
        request = BailianImageRequest(
            request_id=f"bg_{uuid.uuid4().hex[:8]}",
            model=BailianModel.BACKGROUND.value,
            prompt=background_prompt,
            image_url=product_image_url,
            size=size,
            n=1
        )
        
        return await self._execute_request(request, wait, timeout)
    
    async def _execute_request(self, request: BailianImageRequest,
                               wait: bool, timeout: int) -> BailianImageResult:
        """执行请求并返回结果"""
        start_time = time.time()
        
        # 提交任务
        task = await self.submit_task(request)
        
        if not task.task_id or task.status == BailianTaskStatus.FAILED:
            return BailianImageResult(
                request_id=request.request_id,
                success=False,
                error_message=task.error_message or "任务提交失败",
                processing_time=time.time() - start_time
            )
        
        # 如果需要等待
        if wait:
            try:
                # 使用asyncio.wait_for设置超时
                task = await asyncio.wait_for(
                    self.wait_for_completion(task.task_id),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                return BailianImageResult(
                    request_id=request.request_id,
                    success=False,
                    task_id=task.task_id,
                    status="timeout",
                    error_message=f"任务超时（{timeout}秒）",
                    processing_time=time.time() - start_time
                )
        
        # 解析结果
        images = []
        if task.status == BailianTaskStatus.SUCCEEDED and task.result:
            output = task.result.get('results', [{}])[0] if task.result.get('results') else {}
            image_url = output.get('image_url')
            image_base64 = output.get('image_base64')
            
            if image_url:
                images.append({'url': image_url})
            if image_base64:
                images.append({'base64': image_base64})
        
        return BailianImageResult(
            request_id=request.request_id,
            success=task.status == BailianTaskStatus.SUCCEEDED,
            task_id=task.task_id,
            images=images,
            status=task.status.value,
            error_message=task.error_message,
            processing_time=time.time() - start_time
        )
    
    def get_task(self, task_id: str) -> Optional[BailianTask]:
        """获取任务对象"""
        return self._tasks.get(task_id)
    
    def list_tasks(self, status: Optional[BailianTaskStatus] = None) -> List[BailianTask]:
        """列出任务"""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
        logger.info("百炼适配器客户端已关闭")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# ============================================================
# 同步封装（兼容同步调用场景）
# ============================================================

class BailianImageAdapterSync:
    """百炼适配器同步封装"""
    
    def __init__(self, config: Optional[BailianConfig] = None,
                 config_path: str = "ecommerce_config.json"):
        self.config = config or BailianConfig(config_path)
        self._adapter = BailianImageAdapter(self.config, config_path)
    
    def generate_text2image(self, **kwargs) -> BailianImageResult:
        """文生图（同步）"""
        return asyncio.run(self._adapter.generate_text2image(**kwargs))
    
    def generate_image2image(self, **kwargs) -> BailianImageResult:
        """图生图（同步）"""
        return asyncio.run(self._adapter.generate_image2image(**kwargs))
    
    def generate_virtual_model(self, **kwargs) -> BailianImageResult:
        """虚拟模特（同步）"""
        return asyncio.run(self._adapter.generate_virtual_model(**kwargs))
    
    def generate_ai_tryon(self, **kwargs) -> BailianImageResult:
        """AI试衣（同步）"""
        return asyncio.run(self._adapter.generate_ai_tryon(**kwargs))
    
    def generate_poster(self, **kwargs) -> BailianImageResult:
        """创意海报（同步）"""
        return asyncio.run(self._adapter.generate_poster(**kwargs))
    
    def generate_background(self, **kwargs) -> BailianImageResult:
        """背景生成（同步）"""
        return asyncio.run(self._adapter.generate_background(**kwargs))
    
    def get_task(self, task_id: str) -> Optional[BailianTask]:
        return self._adapter.get_task(task_id)
    
    def close(self):
        asyncio.run(self._adapter.close())


# ============================================================
# SellAI集成
# ============================================================

class BailianVisualIntegration:
    """
    百炼视觉生成与SellAI集成类
    
    将百炼图片生成能力集成到SellAI的视觉生成服务体系
    """
    
    def __init__(self, config_path: str = "ecommerce_config.json"):
        self.adapter = BailianImageAdapter(config_path=config_path)
        self.config = self.adapter.config
    
    async def generate_product_image(self, product_name: str,
                                       product_description: str,
                                       category: str = "general",
                                       style: str = "photography",
                                       size: str = "1024*1024") -> Dict[str, Any]:
        """
        生成电商产品图片
        
        Args:
            product_name: 产品名称
            product_description: 产品描述
            category: 产品类别
            style: 视觉风格
            size: 图片尺寸
            
        Returns:
            标准化的生成结果
        """
        # 构建产品图提示词
        prompt = f"专业电商产品摄影，{product_name}，{product_description}，"
        prompt += f"白色背景，高清细节，光线均匀，商业摄影风格"
        
        result = await self.adapter.generate_text2image(
            prompt=prompt,
            style=style,
            size=size
        )
        
        return {
            'success': result.success,
            'request_id': result.request_id,
            'images': result.images,
            'metadata': {
                'product_name': product_name,
                'category': category,
                'style': style,
                **result.metadata
            },
            'error': result.error_message
        }
    
    async def generate_lifestyle_image(self, product_name: str,
                                         scene: str,
                                         target_market: str = "US") -> Dict[str, Any]:
        """
        生成场景图（生活方式图）
        
        Args:
            product_name: 产品名称
            scene: 使用场景描述
            target_market: 目标市场
            
        Returns:
            标准化的生成结果
        """
        market_styles = {
            'US': '现代美式生活方式，温馨家庭氛围',
            'EU': '欧式简约风格，优雅格调',
            'JP': '日式清新风格，精致生活',
            'CN': '中式现代风格，传统文化元素'
        }
        
        style_desc = market_styles.get(target_market, '现代简约风格')
        prompt = f"{product_name}，{scene}，{style_desc}，自然光线，"
        prompt += "高品质生活方式摄影，适合电商详情页"
        
        result = await self.adapter.generate_text2image(
            prompt=prompt,
            style=BailianImageStyle.LIFESTYLE.value,
            size="1024*1024"
        )
        
        return {
            'success': result.success,
            'request_id': result.request_id,
            'images': result.images,
            'metadata': {
                'product_name': product_name,
                'scene': scene,
                'target_market': target_market
            },
            'error': result.error_message
        }
    
    async def generate_banner_image(self, title: str,
                                      subtitle: str = "",
                                      brand_colors: List[str] = None,
                                      size: str = "1024*512") -> Dict[str, Any]:
        """
        生成营销横幅图
        
        Args:
            title: 标题
            subtitle: 副标题
            brand_colors: 品牌色列表
            size: 图片尺寸
            
        Returns:
            标准化的生成结果
        """
        colors_str = ""
        if brand_colors:
            colors_str = "，".join([f"{c}色调" for c in brand_colors[:3]])
        
        prompt = f"创意海报设计，标题: {title}，{subtitle}，{colors_str}，"
        prompt += "现代商业设计，文字清晰，视觉冲击力强"
        
        result = await self.adapter.generate_poster(prompt=prompt, size=size)
        
        return {
            'success': result.success,
            'request_id': result.request_id,
            'images': result.images,
            'metadata': {
                'title': title,
                'subtitle': subtitle,
                'brand_colors': brand_colors
            },
            'error': result.error_message
        }
    
    def close(self):
        """关闭连接"""
        asyncio.run(self.adapter.close())


# ============================================================
# CLI工具
# ============================================================

async def cli_demo():
    """CLI演示"""
    print("=" * 60)
    print("阿里云百炼图片生成适配器 - CLI演示")
    print("=" * 60)
    
    adapter = BailianImageAdapter()
    
    # 检查API配置
    api_key = adapter.config.get_api_key()
    if not api_key:
        print("⚠️  警告: 未配置API密钥，请在ecommerce_config.json中设置bailian.api_key")
        print("\n请访问 https://dashscope.console.aliyun.com/ 获取API密钥")
        return
    
    print(f"✓ API密钥已配置: {api_key[:8]}...{api_key[-4:]}")
    
    # 测试文生图
    print("\n📝 测试文生图...")
    result = await adapter.generate_text2image(
        prompt="专业电商产品摄影，无线蓝牙耳机，白色背景，高清细节，商业摄影风格",
        style=BailianImageStyle.PHOTOGRAPHY.value,
        size="1024*1024",
        wait=True,
        timeout=120
    )
    
    print(f"  请求ID: {result.request_id}")
    print(f"  成功: {result.success}")
    print(f"  状态: {result.status}")
    print(f"  图片数量: {len(result.images)}")
    if result.error_message:
        print(f"  错误: {result.error_message}")
    
    if result.images:
        print(f"  图片URL: {result.images[0].get('url', 'N/A')}")
    
    print(f"  处理时间: {result.processing_time:.2f}秒")
    
    await adapter.close()
    print("\n" + "=" * 60)


def main():
    """主入口"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        asyncio.run(cli_demo())
    else:
        print("阿里云百炼图片生成适配器")
        print("Usage: python bailian_image.py --demo")
        print("\n在ecommerce_config.json中配置API密钥后运行演示")


if __name__ == "__main__":
    main()
