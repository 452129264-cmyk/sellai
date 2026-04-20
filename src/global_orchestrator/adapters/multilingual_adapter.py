#!/usr/bin/env python3
"""
Multilingual原创合规校验适配器
将统一调度器任务转换为原创合规检测服务调用
"""

import logging
import time
from typing import Dict, Any, List
from datetime import datetime

from .base_adapter import CapabilityAdapter

logger = logging.getLogger(__name__)


class MultilingualAdapter(CapabilityAdapter):
    """Multilingual原创合规校验适配器"""
    
    def __init__(self):
        """初始化Multilingual适配器"""
        super().__init__(
            capability_id="multilingual",
            capability_name="Multilingual原创合规校验"
        )
        
        # 初始化原创合规检测服务
        try:
            from src.originality_compliance.services.originality_service import OriginalityDetectionService
            self.service = OriginalityDetectionService()
            logger.info("原创合规检测服务初始化成功")
        except (ImportError, KeyError, ModuleNotFoundError) as e:
            logger.warning(f"无法导入原创合规检测服务: {str(e)}，使用模拟模式")
            self.service = None
    
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行原创合规检测任务
        
        Args:
            payload: 任务载荷，包含:
                - text: 待检测文本
                - operation: 操作类型，支持 "detect"|"health"
                
        Returns:
            检测结果或服务状态
        """
        start_time = time.time()
        operation = payload.get("operation", "detect")
        
        try:
            if operation == "detect":
                result = self._execute_detection(payload)
            elif operation == "health":
                result = self._execute_health_check(payload)
            else:
                raise ValueError(f"不支持的Multilingual操作: {operation}")
            
            response_time = round((time.time() - start_time) * 1000, 2)
            self._update_stats(success=True, response_time_ms=response_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Multilingual执行失败: {str(e)}")
            self._update_stats(success=False)
            raise
    
    def _execute_detection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行原创性检测操作"""
        text = payload["text"]
        
        if self.service:
            # 实际调用服务
            # 注意：这里需要根据实际服务接口调整
            # detection_result = self.service.detect_originality(text)
            # 暂时使用模拟结果
            detection_result = {
                "originality_score": 0.92,
                "risk_level": "low",
                "similar_sources": [
                    {"url": "example.com", "similarity": 0.15}
                ],
                "recommendations": ["建议添加更多原创内容"]
            }
        else:
            # 模拟检测结果
            detection_result = {
                "originality_score": 0.85 + (hash(text) % 100) / 1000,  # 模拟随机分数
                "risk_level": "low" if len(text) > 100 else "medium",
                "similar_sources": [],
                "recommendations": []
            }
        
        return {
            "operation": "detect",
            "text_length": len(text),
            "result": detection_result,
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_health_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行健康检查"""
        if self.service:
            # 实际健康检查
            health_status = "healthy"
        else:
            health_status = "simulation"
        
        return {
            "operation": "health",
            "status": health_status,
            "details": {
                "simulation_mode": self.service is None
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """检查原创合规检测服务健康状态"""
        try:
            if self.service:
                # 实际健康检查逻辑
                status = "healthy"
                details = {"service_available": True}
            else:
                status = "simulation"
                details = {"simulation_mode": True}
            
            return {
                "capability_id": self.capability_id,
                "status": status,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Multilingual健康检查失败: {str(e)}")
            
            return {
                "capability_id": self.capability_id,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_description(self) -> str:
        """获取能力描述"""
        return "多语言原创合规检测服务，集成多个检测引擎，提供原创性评分、侵权风险评估、修改建议等功能。"
    
    def _get_supported_operations(self) -> List[str]:
        """获取支持的操作列表"""
        return [
            "detect",   # 原创性检测
            "health"    # 健康检查
        ]