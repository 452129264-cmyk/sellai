"""
合规检查服务主模块
提供完整的合规检查工作流
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict

from ..database.models import (
    ComplianceRequest,
    ComplianceResult,
    ComplianceConfig,
    RiskLevel,
    ContentType
)
from ..screening.content_screener import ContentScreener
from ..screening.interceptor import ContentInterceptor
from ..screening.risk_assessor import RiskAssessor
from ..integrators.notebooklm_integrator import NotebookLMIntegrator
from ..integrators.deepl_integrator import DeepLIntegrator
from ..integrators.originality_integrator import OriginalityIntegrator

logger = logging.getLogger(__name__)

class ComplianceCheckService:
    """合规检查服务"""
    
    def __init__(self, config: Optional[ComplianceConfig] = None):
        self.config = config or ComplianceConfig()
        
        # 初始化核心组件
        self.content_screener = ContentScreener({
            "max_text_length": self.config.max_text_length,
            "enable_ai_assessment": self.config.enable_ai_assessment,
            "interception": {
                "high_risk_threshold": 0.85,
                "score_threshold": 0.95
            }
        })
        
        self.risk_assessor = RiskAssessor({
            "risk_thresholds": {
                "low": 0.3,
                "medium": 0.5,
                "high": 0.75,
                "critical": 0.9
            },
            "feature_weights": {
                "violation_count": 0.3,
                "risk_level_sum": 0.4,
            "confidence_avg": 0.2,
                "text_length_factor": 0.1
            }
        })
        
        self.interceptor = ContentInterceptor({
            "risk_thresholds": {
                "critical": {"score": 0.9, "action": "block"},
                "high": {"score": 0.75, "action": "flag"},
                "medium": {"score": 0.5, "action": "warn"},
                "low": {"score": 0.3, "action": "pass"}
            },
            "critical_clause_codes": [
                "FTC_CRITICAL_001",
                "GDPR_CRITICAL_001",
                "CN_AD_CRITICAL_001"
            ]
        })
        
        # 初始化集成器（需要外部配置）
        self.notebooklm_integrator = None
        self.deepl_integrator = None
        self.originality_integrator = None
        
        # 服务统计
        self.service_stats = {
            "total_requests": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "total_processing_time_ms": 0.0,
            "avg_check_time_ms": 0.0,
            "start_time": datetime.now().isoformat()
        }
        
        logger.info("ComplianceCheckService initialized")
    
    def initialize_integrations(self, 
                               notebooklm_config: Optional[Dict[str, Any]] = None,
                               deepl_config: Optional[Dict[str, Any]] = None,
                               originality_config: Optional[Dict[str, Any]] = None):
        """初始化集成服务"""
        if notebooklm_config:
            self.notebooklm_integrator = NotebookLMIntegrator(notebooklm_config)
        
        if deepl_config:
            self.deepl_integrator = DeepLIntegrator(deepl_config)
        
        if originality_config:
            self.originality_integrator = OriginalityIntegrator(originality_config)
        
        # 配置内容筛查器的集成器
        self.content_screener.initialize_integrators(
            notebooklm_config=notebooklm_config,
            deepl_config=deepl_config,
            originality_config=originality_config
        )
    
    async def check_content(self, request: ComplianceRequest) -> ComplianceResult:
        """
        执行完整的合规检查
        Args:
            request: 合规检查请求
        Returns:
            合规检查结果
        """
        start_time = time.time()
        
        try:
            # 验证请求
            self._validate_request(request)
            
            # 1. 内容筛查
            compliance_result = await self.content_screener.screen_content(request)
            
            # 2. 原创性检查（如果有集成）
            if self.originality_integrator:
                originality_request = self._build_originality_request(request)
                originality_result = await self.originality_integrator.check_originality(
                    originality_request
                )
                
                # 整合结果
                integrated_result = await self.originality_integrator.integrate_results(
                    compliance_result,
                    originality_result
                )
                
                # 更新结果中的建议
                if "suggestions" in integrated_result:
                    compliance_result.suggestions = integrated_result["suggestions"]
            
            # 3. 风险评估
            risk_assessment = self.risk_assessor.assess_risk(
                text=request.text,
                country_code=request.target_country,
                content_type=request.content_type.value,
                industry=request.industry,
                violations=[asdict(v) for v in compliance_result.violations]
            )
            
            # 更新风险分数
            compliance_result.risk_score = risk_assessment["risk_score"]
            
            # 4. 拦截判断与执行
            interception_result = self.interceptor.process_compliance_result(
                compliance_result
            )
            
            # 更新拦截状态
            compliance_result.intercepted = interception_result["intercepted"]
            compliance_result.interception_reason = interception_result.get("reason")
            
            # 更新处理时间
            processing_time = (time.time() - start_time) * 1000
            compliance_result.processing_time_ms = processing_time
            
            # 更新服务统计
            self._update_service_stats(success=True, processing_time=processing_time)
            
            logger.info(f"合规检查完成: content_id={request.content_id}, "
                       f"risk_level={compliance_result.risk_level.value}, "
                       f"risk_score={compliance_result.risk_score:.2f}, "
                       f"intercepted={compliance_result.intercepted}, "
                       f"time={processing_time:.2f}ms")
            
            return compliance_result
            
        except Exception as e:
            # 更新服务统计
            self._update_service_stats(success=False, processing_time=0)
            
            logger.error(f"合规检查失败: content_id={request.content_id}, error={str(e)}")
            
            # 返回错误结果
            return self._create_error_result(request, str(e))
    
    async def batch_check_content(self, requests: List[ComplianceRequest]) -> List[ComplianceResult]:
        """
        批量执行合规检查
        Args:
            requests: 合规检查请求列表
        Returns:
            合规检查结果列表
        """
        results = []
        
        # 分批处理以避免资源耗尽
        batch_size = min(10, len(requests))
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i+batch_size]
            
            # 并行处理批内请求
            batch_tasks = [self.check_content(req) for req in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"批量检查失败: {str(result)}")
                    # 创建错误结果
                    error_result = self._create_error_result(
                        ComplianceRequest(
                            content_id="unknown",
                            text="",
                            content_type=ContentType.ADVERTISEMENT,
                            target_country="US"
                        ),
                        str(result)
                    )
                    results.append(error_result)
                else:
                    results.append(result)
            
            # 短暂延迟，避免资源竞争
            if i + batch_size < len(requests):
                await asyncio.sleep(0.1)
        
        return results
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态
        Returns:
            服务状态信息
        """
        status = {
            "service": "ComplianceCheckService",
            "version": "1.0.0",
            "status": "running",
            "uptime_seconds": (datetime.now() - datetime.fromisoformat(
                self.service_stats["start_time"].replace('Z', '+00:00')
            )).total_seconds(),
            "stats": self.service_stats.copy(),
            "components": {
                "content_screener": self.content_screener.get_stats(),
                "risk_assessor": "initialized",
                "interceptor": self.interceptor.get_stats()
            },
            "integrations": {
                "notebooklm": "initialized" if self.notebooklm_integrator else "not_configured",
                "deepl": "initialized" if self.deepl_integrator else "not_configured",
                "originality": "initialized" if self.originality_integrator else "not_configured"
            },
            "config": asdict(self.config),
            "timestamp": datetime.now().isoformat()
        }
        
        return status
    
    async def check_health(self) -> Dict[str, Any]:
        """
        健康检查
        Returns:
            健康状态
        """
        health_status = {
            "service": "ComplianceCheckService",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": []
        }
        
        # 检查内容筛查器
        try:
            screener_stats = self.content_screener.get_stats()
            health_status["checks"].append({
                "component": "content_screener",
                "status": "healthy",
                "details": f"total_checks={screener_stats.get('total_checks', 0)}"
            })
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"].append({
                "component": "content_screener",
                "status": "unhealthy",
                "error": str(e)
            })
        
        # 检查拦截器
        try:
            interceptor_stats = self.interceptor.get_stats()
            health_status["checks"].append({
                "component": "interceptor",
                "status": "healthy",
                "details": f"total_processed={interceptor_stats.get('total_processed', 0)}"
            })
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"].append({
                "component": "interceptor",
                "status": "unhealthy",
                "error": str(e)
            })
        
        # 检查集成服务
        if self.notebooklm_integrator:
            try:
                health_status["checks"].append({
                    "component": "notebooklm_integrator",
                    "status": "healthy",
                    "details": "initialized"
                })
            except Exception as e:
                health_status["status"] = "unhealthy"
                health_status["checks"].append({
                    "component": "notebooklm_integrator",
                    "status": "unhealthy",
                    "error": str(e)
                })
        
        return health_status
    
    def _validate_request(self, request: ComplianceRequest):
        """验证请求"""
        if not request.content_id:
            raise ValueError("content_id is required")
        
        if not request.text or len(request.text.strip()) == 0:
            raise ValueError("text is required and cannot be empty")
        
        if not request.target_country:
            raise ValueError("target_country is required")
        
        if request.target_country not in self.config.supported_countries:
            logger.warning(f"Unsupported country: {request.target_country}")
        
        # 检查文本长度
        if len(request.text) > self.config.max_text_length:
            logger.warning(f"Text length {len(request.text)} exceeds maximum "
                          f"{self.config.max_text_length}, will be truncated")
    
    def _build_originality_request(self, compliance_request: ComplianceRequest) -> Any:
        """构建原创性检查请求"""
        from ..integrators.originality_integrator import OriginalityRequest
        
        return OriginalityRequest(
            content_id=compliance_request.content_id,
            text=compliance_request.text,
            content_type=compliance_request.content_type.value,
            target_countries=[compliance_request.target_country],
            language="auto"
        )
    
    def _create_error_result(self, request: ComplianceRequest, error_message: str) -> ComplianceResult:
        """创建错误结果"""
        return ComplianceResult(
            content_id=request.content_id,
            risk_level=RiskLevel.MEDIUM,
            risk_score=0.5,
            violations=[],
            suggestions=[
                "合规检查过程中发生错误",
                f"错误信息: {error_message}",
                "请人工审核内容或稍后重试"
            ],
            similar_cases=[],
            processing_time_ms=0.0,
            intercepted=False,
            interception_reason=f"检查失败: {error_message}"
        )
    
    def _update_service_stats(self, success: bool, processing_time: float):
        """更新服务统计"""
        self.service_stats["total_requests"] += 1
        
        if success:
            self.service_stats["successful_checks"] += 1
            self.service_stats["total_processing_time_ms"] += processing_time
            
            # 更新平均检查时间（移动平均）
            current_avg = self.service_stats["avg_check_time_ms"]
            n = self.service_stats["successful_checks"]
            self.service_stats["avg_check_time_ms"] = (
                current_avg * (n - 1) + processing_time
            ) / n
        
        else:
            self.service_stats["failed_checks"] += 1
    
    def reset_service_stats(self):
        """重置服务统计"""
        self.service_stats = {
            "total_requests": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "total_processing_time_ms": 0.0,
            "avg_check_time_ms": 0.0,
            "start_time": datetime.now().isoformat()
        }
        
        # 重置组件统计
        self.content_screener.reset_stats()
        self.interceptor.reset_stats()
        
        logger.info("服务统计已重置")
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        # 更新服务配置
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # 更新组件配置
        if "content_screener" in new_config:
            self.content_screener.config.update(new_config["content_screener"])
        
        if "risk_assessor" in new_config:
            self.risk_assessor.update_config(new_config["risk_assessor"])
        
        if "interceptor" in new_config:
            self.interceptor.config.update(new_config["interceptor"])
        
        logger.info("服务配置已更新")