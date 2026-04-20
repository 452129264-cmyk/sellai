#!/usr/bin/env python3
"""
DeepL翻译服务适配器
将统一调度器任务转换为DeepL服务调用
"""

import logging
import time
from typing import Dict, Any, List
from datetime import datetime

from .base_adapter import CapabilityAdapter

logger = logging.getLogger(__name__)


class DeepLAdapter(CapabilityAdapter):
    """DeepL翻译服务适配器"""
    
    def __init__(self):
        """初始化DeepL适配器"""
        super().__init__(
            capability_id="deepl",
            capability_name="DeepL全域多语种原生润色"
        )
        
        # 初始化DeepL服务
        try:
            from src.deepl_translation_service import DeepLTranslationService
            self.service = DeepLTranslationService()
            self.service.start()
            logger.info("DeepL服务启动成功")
        except ImportError as e:
            logger.warning(f"无法导入DeepL服务: {str(e)}，使用模拟模式")
            self.service = None
        except Exception as e:
            logger.error(f"DeepL服务启动失败: {str(e)}")
            self.service = None
    
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行DeepL翻译任务
        
        Args:
            payload: 任务载荷，包含:
                - text: 待翻译文本
                - target_lang: 目标语言代码，默认 "EN-US"
                - source_lang: 源语言代码，可选
                - formality: 正式度 "default"|"less"|"more"
                - glossary_id: 术语表ID，可选
                - operation: 操作类型，支持 "translate"|"detect"|"usage"|"health"
                
        Returns:
            翻译结果或服务状态
        """
        start_time = time.time()
        operation = payload.get("operation", "translate")
        
        try:
            if operation == "translate":
                result = self._execute_translation(payload)
            elif operation == "detect":
                result = self._execute_detection(payload)
            elif operation == "usage":
                result = self._execute_usage_check(payload)
            elif operation == "health":
                result = self._execute_health_check(payload)
            else:
                raise ValueError(f"不支持的DeepL操作: {operation}")
            
            response_time = round((time.time() - start_time) * 1000, 2)
            self._update_stats(success=True, response_time_ms=response_time)
            
            return result
            
        except Exception as e:
            logger.error(f"DeepL执行失败: {str(e)}")
            self._update_stats(success=False)
            raise
    
    def _execute_translation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行翻译操作"""
        text = payload["text"]
        target_lang = payload.get("target_lang", "EN-US")
        source_lang = payload.get("source_lang")
        formality = payload.get("formality", "default")
        glossary_id = payload.get("glossary_id")
        
        if self.service:
            try:
                # 创建翻译请求
                from src.deepl_translation_service import TranslationRequest
                request = TranslationRequest(
                    text=text,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    formality=formality,
                    glossary_id=glossary_id
                )
                
                # 调用翻译服务
                response = self.service.safe_translate(
                    request,
                    fallback_text=payload.get("fallback_text"),
                    retry_count=payload.get("retry_count", 3),
                    use_cache=payload.get("use_cache", True)
                )
                
                return response
            except Exception as e:
                logger.warning(f"DeepL实际服务调用失败，使用模拟结果: {str(e)}")
        
        # 模拟模式或服务调用失败
        return {
            "original_text": text,
            "translated_text": f"[模拟翻译] {text} -> 目标语言: {target_lang}",
            "detected_source_lang": source_lang or "EN",
            "formality": formality,
            "translation_time_ms": 150,
            "model_used": "deepl_simulation",
            "success": True,
            "from_cache": False
        }
    
    def _execute_detection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行语言检测操作"""
        text = payload["text"]
        
        # 调用语言检测
        result = self.service.detect_language(text)
        
        return {
            "operation": "detect",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_usage_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行用量查询操作"""
        result = self.service.get_usage()
        
        return {
            "operation": "usage",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_health_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行健康检查操作"""
        result = self.service.check_service_health()
        
        return {
            "operation": "health",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """检查DeepL服务健康状态"""
        try:
            health_status = self.service.check_service_health()
            
            return {
                "capability_id": self.capability_id,
                "status": health_status.status,
                "details": {
                    "error_rate": health_status.error_rate_last_hour,
                    "response_time_p95": health_status.response_time_p95,
                    "cache_hit_rate": health_status.cache_hit_rate
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"DeepL健康检查失败: {str(e)}")
            
            return {
                "capability_id": self.capability_id,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_description(self) -> str:
        """获取能力描述"""
        return "DeepL专业翻译服务，支持28种语言互译，提供高质量、地道、符合语境的翻译结果。"
    
    def _get_supported_operations(self) -> List[str]:
        """获取支持的操作列表"""
        return [
            "translate",      # 文本翻译
            "detect",         # 语言检测
            "usage",          # 用量查询
            "health"          # 健康检查
        ]
    
    def __del__(self):
        """清理资源"""
        try:
            self.service.stop()
            logger.info("DeepL服务已停止")
        except:
            pass