#!/usr/bin/env python3
"""
基础适配器接口定义
为八大能力模块提供统一调用接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class CapabilityAdapter(ABC):
    """能力适配器基类"""
    
    def __init__(self, capability_id: str, capability_name: str):
        """
        初始化适配器
        
        Args:
            capability_id: 能力标识符，如 "deepl", "firecrawl"
            capability_name: 能力名称，如 "DeepL翻译服务", "Firecrawl爬虫"
        """
        self.capability_id = capability_id
        self.capability_name = capability_name
        self.last_heartbeat = datetime.now()
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_response_time_ms": 0.0,
            "last_call_time": None,
            "created_at": datetime.now().isoformat()
        }
        logger.info(f"初始化能力适配器: {capability_name} ({capability_id})")
    
    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行能力调用
        
        Args:
            payload: 任务载荷，包含调用参数
            
        Returns:
            执行结果，包含成功状态和数据
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        检查能力服务健康状态
        
        Returns:
            健康状态信息
        """
        pass
    
    def safe_execute(self, payload: Dict[str, Any], 
                    fallback_result: Optional[Dict[str, Any]] = None,
                    retry_count: int = 3) -> Dict[str, Any]:
        """
        带重试和兜底的安全执行接口
        
        Args:
            payload: 任务载荷
            fallback_result: 兜底结果，当所有重试失败时返回
            retry_count: 重试次数
            
        Returns:
            执行结果，包含状态和来源信息
        """
        last_exception = None
        
        for attempt in range(retry_count):
            try:
                # 应用指数退避
                if attempt > 0:
                    wait_time = 2 ** (attempt - 1)
                    logger.debug(f"第 {attempt + 1} 次重试，等待 {wait_time} 秒")
                    time.sleep(wait_time)
                
                result = self.execute(payload)
                
                # 更新统计信息
                self._update_stats(success=True)
                
                return {
                    "status": "success",
                    "data": result,
                    "source": self.capability_id,
                    "retry_count": attempt,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                last_exception = e
                logger.warning(f"第 {attempt + 1} 次执行失败: {str(e)}")
                continue
        
        # 所有重试失败
        logger.error(f"所有 {retry_count} 次重试失败")
        
        if fallback_result:
            logger.info(f"使用兜底结果")
            return {
                "status": "fallback",
                "data": fallback_result,
                "source": "fallback",
                "error": str(last_exception) if last_exception else "unknown error",
                "retry_count": retry_count,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "failed",
                "data": None,
                "source": self.capability_id,
                "error": str(last_exception) if last_exception else "unknown error",
                "retry_count": retry_count,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_capability_info(self) -> Dict[str, Any]:
        """
        获取能力信息
        
        Returns:
            能力描述信息
        """
        return {
            "capability_id": self.capability_id,
            "capability_name": self.capability_name,
            "type": self.__class__.__name__,
            "description": self._get_description(),
            "supported_operations": self._get_supported_operations(),
            "stats": self.stats,
            "last_heartbeat": self.last_heartbeat.isoformat()
        }
    
    @abstractmethod
    def _get_description(self) -> str:
        """获取能力描述"""
        pass
    
    @abstractmethod
    def _get_supported_operations(self) -> List[str]:
        """获取支持的操作列表"""
        pass
    
    def _update_stats(self, success: bool, response_time_ms: float = 0.0):
        """更新统计信息"""
        self.stats["total_calls"] += 1
        
        if success:
            self.stats["successful_calls"] += 1
            self.stats["total_response_time_ms"] += response_time_ms
        else:
            self.stats["failed_calls"] += 1
        
        self.stats["last_call_time"] = datetime.now().isoformat()
        
        # 计算平均响应时间
        if self.stats["successful_calls"] > 0:
            self.stats["avg_response_time_ms"] = (
                self.stats["total_response_time_ms"] / self.stats["successful_calls"]
            )
    
    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_heartbeat = datetime.now()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标
        
        Returns:
            性能指标数据
        """
        total = self.stats["total_calls"]
        successful = self.stats["successful_calls"]
        
        if total == 0:
            success_rate = 1.0
        else:
            success_rate = successful / total
        
        return {
            "capability_id": self.capability_id,
            "total_calls": total,
            "successful_calls": successful,
            "failed_calls": self.stats["failed_calls"],
            "success_rate": success_rate,
            "avg_response_time_ms": self.stats.get("avg_response_time_ms", 0.0),
            "uptime_seconds": (datetime.now() - datetime.fromisoformat(self.stats["created_at"])).total_seconds(),
            "last_call_time": self.stats["last_call_time"],
            "timestamp": datetime.now().isoformat()
        }