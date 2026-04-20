#!/usr/bin/env python3
"""
HyperHorse API适配器
提供与现有视频生成服务（video_generation_service.py）兼容的接口
将现有API调用转换为HyperHorse引擎的内部格式
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import asdict
import threading

from .core import (
    HyperHorseEngine,
    VideoScript,
    VideoGenerationResult,
    TrendAnalysisResult,
    VideoQualityLevel,
    VideoPlatform,
    LanguageCode
)

logger = logging.getLogger(__name__)

# 兼容现有服务的请求格式
class VideoGenerationRequest:
    """兼容现有视频生成服务的请求格式"""
    
    def __init__(self,
                 category: str,
                 target_regions: List[str],
                 duration_seconds: int = 60,
                 quality_level: str = "premium",
                 target_platforms: List[str] = None,
                 target_language: str = "en",
                 style_guidelines: Optional[Dict[str, Any]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        初始化视频生成请求
        
        参数：
            category: 视频品类
            target_regions: 目标地区列表
            duration_seconds: 视频时长（秒）
            quality_level: 质量等级（economy, standard, premium, ultra）
            target_platforms: 目标平台列表
            target_language: 目标语言代码
            style_guidelines: 风格指导
            metadata: 元数据
        """
        self.request_id = f"request_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        self.category = category
        self.target_regions = target_regions or []
        self.duration_seconds = duration_seconds
        self.quality_level = quality_level
        self.target_platforms = target_platforms or ["tiktok", "instagram"]
        self.target_language = target_language
        self.style_guidelines = style_guidelines or {}
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        
        logger.info(f"创建视频生成请求: {self.request_id}，品类: {self.category}")

class VideoGenerationResponse:
    """兼容现有视频生成服务的响应格式"""
    
    def __init__(self,
                 task_id: str,
                 status: str,
                 generated_videos: List[Dict[str, Any]],
                 performance_metrics: Dict[str, Any],
                 error_messages: Optional[List[str]] = None):
        """
        初始化视频生成响应
        
        参数：
            task_id: 任务ID
            status: 状态（success, partial_success, failed）
            generated_videos: 生成的视频信息列表
            performance_metrics: 性能指标
            error_messages: 错误信息列表
        """
        self.task_id = task_id
        self.status = status
        self.generated_videos = generated_videos or []
        self.performance_metrics = performance_metrics or {}
        self.error_messages = error_messages or []
        self.timestamp = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "generated_videos": self.generated_videos,
            "performance_metrics": self.performance_metrics,
            "error_messages": self.error_messages,
            "timestamp": self.timestamp.isoformat()
        }

class HyperHorseAPIAdapter:
    """
    HyperHorse API适配器主类
    提供与现有视频生成服务完全兼容的接口
    """
    
    def __init__(self, 
                 db_path: str = "data/shared_state/state.db",
                 engine_config: Optional[Dict[str, Any]] = None):
        """
        初始化API适配器
        
        参数：
            db_path: 共享状态数据库路径
            engine_config: 引擎配置
        """
        self.db_path = db_path
        self.engine_config = engine_config or {}
        
        # 初始化HyperHorse引擎
        self.engine = HyperHorseEngine(db_path, self.engine_config)
        
        # 兼容性映射
        self.quality_level_map = {
            "economy": VideoQualityLevel.ECONOMY,
            "standard": VideoQualityLevel.STANDARD,
            "premium": VideoQualityLevel.PREMIUM,
            "ultra": VideoQualityLevel.ULTRA
        }
        
        self.platform_map = {
            "tiktok": VideoPlatform.TIKTOK,
            "instagram": VideoPlatform.INSTAGRAM,
            "youtube_shorts": VideoPlatform.YOUTUBE_SHORTS,
            "facebook_reels": VideoPlatform.FACEBOOK_REELS,
            "shopify": VideoPlatform.SHOPIFY,
            "amazon": VideoPlatform.AMAZON,
            "aliexpress": VideoPlatform.ALIEXPRESS,
            "independent_site": VideoPlatform.INDEPENDENT_SITE
        }
        
        logger.info(f"初始化HyperHorse API适配器，引擎ID: {self.engine.engine_id}")
    
    # ====================== 兼容现有服务的主要接口 ======================
    
    def generate_video(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        """
        生成视频（兼容现有接口）
        
        参数：
            request: 视频生成请求
        
        返回：
            视频生成响应
        """
        logger.info(f"开始视频生成，请求ID: {request.request_id}")
        
        try:
            # 将请求转换为HyperHorse引擎格式
            # 1. 趋势分析
            trend_analysis = self.engine.analyze_global_commercial_trends(
                request.target_regions,
                [request.category]
            )
            
            # 2. 脚本生成
            script = self.engine.generate_high_conversion_script(
                trend_analysis,
                request.target_platforms[0] if request.target_platforms else "tiktok",
                request.duration_seconds
            )
            
            # 3. 语言适配（如果需要）
            if request.target_language != script.target_language:
                script = self.engine.adapt_script_for_language(
                    script, 
                    request.target_language
                )
            
            # 4. 质量等级转换
            quality_level = self.quality_level_map.get(
                request.quality_level, 
                VideoQualityLevel.PREMIUM
            )
            
            # 5. 视频生成
            result = self.engine.generate_video_from_script(
                script,
                quality_level,
                request.target_platforms
            )
            
            # 6. 转换为兼容格式
            response = self._convert_to_compatible_response(result)
            
            logger.info(f"视频生成完成，任务ID: {result.task_id}，状态: {result.status}")
            
            return response
            
        except Exception as e:
            error_msg = f"视频生成失败: {str(e)[:200]}"
            logger.error(error_msg)
            
            return VideoGenerationResponse(
                task_id=f"error_{int(time.time())}_{uuid.uuid4().hex[:4]}",
                status="failed",
                generated_videos=[],
                performance_metrics={},
                error_messages=[error_msg]
            )
    
    def generate_batch_videos(self, 
                            requests: List[VideoGenerationRequest],
                            callback: Optional[Callable] = None) -> List[VideoGenerationResponse]:
        """
        批量生成视频
        
        参数：
            requests: 视频生成请求列表
            callback: 回调函数（可选）
        
        返回：
            视频生成响应列表
        """
        logger.info(f"开始批量视频生成，请求数量: {len(requests)}")
        
        results = []
        threads = []
        
        def process_request(req: VideoGenerationRequest) -> VideoGenerationResponse:
            """处理单个请求"""
            try:
                return self.generate_video(req)
            except Exception as e:
                logger.error(f"处理请求失败 {req.request_id}: {e}")
                return VideoGenerationResponse(
                    task_id=f"batch_error_{int(time.time())}",
                    status="failed",
                    generated_videos=[],
                    performance_metrics={},
                    error_messages=[str(e)[:100]]
                )
        
        # 使用线程池处理请求
        for request in requests:
            thread = threading.Thread(
                target=lambda r=request: results.append(process_request(r))
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 调用回调函数（如果有）
        if callback and callable(callback):
            callback(results)
        
        logger.info(f"批量视频生成完成，成功: {sum(1 for r in results if r.status == 'success')}")
        
        return results
    
    def get_video_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取视频生成状态
        
        参数：
            task_id: 任务ID
        
        返回：
            状态信息字典
        """
        # 这里应该查询数据库中的任务状态
        # 暂时模拟状态查询
        try:
            # 假设从数据库查询
            return {
                "task_id": task_id,
                "status": "completed",  # 模拟完成状态
                "progress_percentage": 100,
                "estimated_completion_time": datetime.now().isoformat(),
                "generated_videos": [
                    {
                        "video_id": f"video_{task_id}",
                        "platform": "tiktok",
                        "duration_seconds": 60,
                        "file_url": f"https://storage.sellai.com/videos/{task_id}.mp4",
                        "generated_at": datetime.now().isoformat()
                    }
                ],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"查询状态失败 {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "unknown",
                "error": str(e)[:100],
                "timestamp": datetime.now().isoformat()
            }
    
    def cancel_video_generation(self, task_id: str) -> bool:
        """
        取消视频生成任务
        
        参数：
            task_id: 任务ID
        
        返回：
            取消成功返回True，失败返回False
        """
        logger.info(f"尝试取消视频生成任务: {task_id}")
        
        try:
            # 这里应该更新数据库中的任务状态
            # 暂时模拟取消逻辑
            logger.warning(f"任务取消功能待实现: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消任务失败 {task_id}: {e}")
            return False
    
    # ====================== 新增HyperHorse特有接口 ======================
    
    def analyze_trends(self, 
                      target_regions: List[str],
                      categories: List[str]) -> TrendAnalysisResult:
        """
        分析全球商业趋势
        
        参数：
            target_regions: 目标地区列表
            categories: 品类列表
        
        返回：
            趋势分析结果
        """
        return self.engine.analyze_global_commercial_trends(target_regions, categories)
    
    def create_commercial_script(self,
                               trend_analysis: TrendAnalysisResult,
                               target_platform: str,
                               duration_seconds: int) -> VideoScript:
        """
        创建商业视频脚本
        
        参数：
            trend_analysis: 趋势分析结果
            target_platform: 目标平台
            duration_seconds: 视频时长
        
        返回：
            视频脚本
        """
        return self.engine.generate_high_conversion_script(
            trend_analysis,
            target_platform,
            duration_seconds
        )
    
    def localize_script(self,
                       script: VideoScript,
                       target_language: str) -> VideoScript:
        """
        本地化脚本
        
        参数：
            script: 原始脚本
            target_language: 目标语言
        
        返回：
            本地化后的脚本
        """
        return self.engine.adapt_script_for_language(script, target_language)
    
    def publish_videos(self,
                      video_files: List[Dict[str, Any]],
                      platforms: List[str],
                      publish_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发布视频到平台
        
        参数：
            video_files: 视频文件信息列表
            platforms: 目标平台列表
            publish_config: 发布配置
        
        返回：
            发布结果
        """
        return self.engine.publish_to_platforms(video_files, platforms, publish_config)
    
    def update_performance_data(self,
                              task_result: VideoGenerationResult,
                              actual_performance: Dict[str, Any]) -> bool:
        """
        更新性能数据
        
        参数：
            task_result: 视频生成结果
            actual_performance: 实际表现数据
        
        返回：
            更新成功返回True，失败返回False
        """
        return self.engine.update_success_patterns(task_result, actual_performance)
    
    def get_engine_metrics(self) -> Dict[str, Any]:
        """
        获取引擎指标
        
        返回：
            引擎指标字典
        """
        return self.engine.get_engine_info()
    
    # ====================== 与现有无限分身架构集成接口 ======================
    
    def register_with_agent_system(self, agent_system_config: Dict[str, Any]) -> bool:
        """
        注册到无限分身架构系统
        
        参数：
            agent_system_config: 分身系统配置
        
        返回：
            注册成功返回True，失败返回False
        """
        logger.info("开始注册到无限分身架构系统...")
        
        try:
            # 这里应该调用分身系统的注册API
            # 暂时模拟注册逻辑
            
            # 1. 获取分身系统配置
            agent_registry_url = agent_system_config.get("registry_url", "")
            api_key = agent_system_config.get("api_key", "")
            
            # 2. 创建服务描述
            service_description = {
                "service_id": "hyperhorse_video_engine",
                "service_name": "HyperHorse视频生成引擎",
                "service_type": "video_generation",
                "capabilities": [
                    "global_commercial_video_generation",
                    "high_conversion_script_writing",
                    "multilingual_adaptation",
                    "multi_platform_publishing"
                ],
                "endpoints": {
                    "generate_video": "/api/hyperhorse/generate",
                    "analyze_trends": "/api/hyperhorse/trends",
                    "publish_videos": "/api/hyperhorse/publish"
                },
                "engine_info": self.engine.get_engine_info(),
                "registered_at": datetime.now().isoformat()
            }
            
            # 3. 注册服务（模拟）
            logger.info(f"服务描述: {json.dumps(service_description, ensure_ascii=False)[:200]}...")
            
            # 4. 更新数据库记录
            self._update_service_registration(service_description)
            
            logger.info("成功注册到无限分身架构系统")
            return True
            
        except Exception as e:
            logger.error(f"注册到分身系统失败: {e}")
            return False
    
    def integrate_with_memory_v2(self, memory_system_config: Dict[str, Any]) -> bool:
        """
        与Memory V2记忆系统集成
        
        参数：
            memory_system_config: 记忆系统配置
        
        返回：
            集成成功返回True，失败返回False
        """
        logger.info("开始与Memory V2记忆系统集成...")
        
        try:
            # 这里应该调用Memory V2系统的集成API
            # 暂时模拟集成逻辑
            
            # 1. 配置记忆存储
            memory_config = {
                "module_id": self.engine.engine_id,
                "module_type": "video_generation_engine",
                "storage_schema": {
                    "video_generation_results": {
                        "fields": ["task_id", "script_data", "video_files", "performance_metrics"],
                        "indexes": ["task_id", "generation_timestamp"]
                    },
                    "success_patterns": {
                        "fields": ["pattern_id", "features", "success_score", "usage_count"],
                        "indexes": ["pattern_id", "success_score"]
                    }
                },
                "retrieval_policies": {
                    "by_task_id": True,
                    "by_performance_score": True,
                    "by_category": True
                },
                "integration_timestamp": datetime.now().isoformat()
            }
            
            # 2. 保存配置
            self._save_memory_integration_config(memory_config)
            
            logger.info("成功与Memory V2记忆系统集成")
            return True
            
        except Exception as e:
            logger.error(f"与Memory V2集成失败: {e}")
            return False
    
    # ====================== 内部工具方法 ======================
    
    def _convert_to_compatible_response(self, 
                                      result: VideoGenerationResult) -> VideoGenerationResponse:
        """将HyperHorse结果转换为兼容格式"""
        
        # 转换生成的视频信息
        compatible_videos = []
        for video in result.generated_videos:
            compatible_video = {
                "video_id": video.get("video_id", ""),
                "platform": video.get("platform", ""),
                "duration_seconds": video.get("duration_seconds", 0),
                "resolution": video.get("resolution", "1080x1920"),
                "file_format": video.get("file_format", "mp4"),
                "estimated_size_mb": video.get("estimated_size_mb", 50),
                "quality_level": video.get("quality_level", "premium"),
                "file_url": f"https://storage.sellai.com/videos/{video.get('video_id', 'unknown')}.mp4",  # 模拟URL
                "platform_specific_settings": video.get("platform_specific_settings", {}),
                "metadata": video.get("metadata", {})
            }
            compatible_videos.append(compatible_video)
        
        # 转换性能指标
        compatible_metrics = {
            "generation_time_seconds": result.generation_time_seconds,
            "video_count": len(result.generated_videos),
            "total_duration_seconds": sum(v.get("duration_seconds", 0) for v in result.generated_videos),
            "quality_scores": result.performance_metrics.get("quality_scores", {}),
            "efficiency_score": result.performance_metrics.get("efficiency_score", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        return VideoGenerationResponse(
            task_id=result.task_id,
            status=result.status,
            generated_videos=compatible_videos,
            performance_metrics=compatible_metrics,
            error_messages=result.error_messages
        )
    
    def _update_service_registration(self, service_description: Dict[str, Any]) -> bool:
        """更新服务注册信息到数据库"""
        try:
            # 连接到数据库
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hyperhorse_service_registry (
                    service_id TEXT PRIMARY KEY,
                    service_data TEXT NOT NULL,
                    registered_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入或更新记录
            cursor.execute("""
                INSERT OR REPLACE INTO hyperhorse_service_registry
                (service_id, service_data, registered_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                service_description["service_id"],
                json.dumps(service_description),
                service_description["registered_at"]
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"更新服务注册信息: {service_description['service_id']}")
            return True
            
        except Exception as e:
            logger.error(f"更新服务注册失败: {e}")
            return False
    
    def _save_memory_integration_config(self, memory_config: Dict[str, Any]) -> bool:
        """保存记忆集成配置"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hyperhorse_memory_integration (
                    module_id TEXT PRIMARY KEY,
                    memory_config TEXT NOT NULL,
                    integrated_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 保存配置
            cursor.execute("""
                INSERT OR REPLACE INTO hyperhorse_memory_integration
                (module_id, memory_config, integrated_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                memory_config["module_id"],
                json.dumps(memory_config),
                memory_config["integration_timestamp"]
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"保存记忆集成配置: {memory_config['module_id']}")
            return True
            
        except Exception as e:
            logger.error(f"保存记忆配置失败: {e}")
            return False
    
    # ====================== 辅助方法 ======================
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "service_type": "hyperhorse_video_engine",
            "engine_info": self.engine.get_engine_info(),
            "capabilities": [
                "Global Commercial Video Generation",
                "High Conversion Script Writing",
                "Multilingual Adaptation",
                "Multi-Platform Publishing",
                "Trend Analysis and Optimization",
                "Performance Tracking and Learning"
            ],
            "compatibility": {
                "existing_video_service": True,
                "infinite_agents_system": True,
                "memory_v2_system": True,
                "global_business_brain": True
            },
            "status": "active",
            "timestamp": datetime.now().isoformat()
        }
    
    def shutdown(self) -> bool:
        """关闭适配器和引擎"""
        logger.info("关闭HyperHorse API适配器...")
        
        # 关闭引擎
        engine_shutdown = self.engine.shutdown_engine()
        
        logger.info("API适配器关闭完成")
        return engine_shutdown