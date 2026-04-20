"""
Multilingual原创合规校验系统主服务入口
提供完整的API接口和系统管理功能
"""

import logging
import sys
import time
from typing import Dict, Optional, Any
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .services.originality_service import OriginalityDetectionService, OriginalityServiceConfig
from .services.compliance_service import ComplianceValidationService, ComplianceServiceConfig
from .models.data_models import (
    OriginalityRequest, OriginalityResult, 
    ComplianceRequest, ComplianceResult,
    ContentType, CountryCode, RiskLevel
)
from .models.config_models import SystemSettings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/originality_compliance.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class OriginalityComplianceSystem:
    """原创合规校验系统主类"""
    
    def __init__(self, config: Optional[SystemSettings] = None):
        """
        初始化系统
        
        Args:
            config: 系统配置
        """
        self.config = config or SystemSettings.from_env()
        
        # 初始化子系统
        originality_config = OriginalityServiceConfig(
            notebooklm_config=self.config.api,
            deepl_config=self.config.api
        )
        
        compliance_config = ComplianceServiceConfig(
            rules_database_path=self.config.database.path
        )
        
        self.originality_service = OriginalityDetectionService(originality_config)
        self.compliance_service = ComplianceValidationService(compliance_config)
        
        # 系统状态
        self.system_status = {
            "initialized": True,
            "startup_time": datetime.now(),
            "total_requests": 0,
            "last_health_check": datetime.now(),
            "components": {
                "originality_service": True,
                "compliance_service": True
            }
        }
        
        logger.info("原创合规校验系统初始化完成")
    
    def check_originality(self, request: OriginalityRequest) -> OriginalityResult:
        """
        原创性检测接口
        
        Args:
            request: 检测请求
            
        Returns:
            检测结果
        """
        self.system_status["total_requests"] += 1
        
        try:
            result = self.originality_service.check_originality(request)
            
            # 记录日志
            logger.info(f"原创性检测完成: score={result.originality_score:.2f}, "
                       f"risk={result.plagiarism_risk.value}, "
                       f"time={result.processing_time_ms:.1f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"原创性检测失败: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def validate_compliance(self, request: ComplianceRequest) -> ComplianceResult:
        """
        合规性校验接口
        
        Args:
            request: 校验请求
            
        Returns:
            校验结果
        """
        self.system_status["total_requests"] += 1
        
        try:
            result = self.compliance_service.validate_compliance(request)
            
            # 记录日志
            logger.info(f"合规性校验完成: score={result.compliance_score:.2f}, "
                       f"risk={result.overall_risk.value}, "
                       f"passed={result.passed}")
            
            return result
            
        except Exception as e:
            logger.error(f"合规性校验失败: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def comprehensive_check(self, 
                           text: str, 
                           content_type: ContentType,
                           target_country: CountryCode,
                           language: str = "auto") -> Dict[str, Any]:
        """
        综合检测接口（原创性+合规性）
        
        Args:
            text: 待检测文本
            content_type: 内容类型
            target_country: 目标国家
            language: 文本语言
            
        Returns:
            综合检测结果
        """
        start_time = time.time()
        
        try:
            # 构建请求
            originality_request = OriginalityRequest(
                text=text,
                content_type=content_type,
                language=language,
                target_countries=[target_country]
            )
            
            compliance_request = ComplianceRequest(
                text=text,
                content_type=content_type,
                target_country=target_country,
                industry="general"
            )
            
            # 并行执行检测（简化实现：顺序执行）
            originality_result = self.originality_service.check_originality(originality_request)
            compliance_result = self.compliance_service.validate_compliance(compliance_request)
            
            # 计算综合分数
            overall_score = (
                originality_result.originality_score * 0.6 +
                compliance_result.compliance_score * 0.4
            )
            
            # 确定综合风险等级
            overall_risk = self._determine_overall_risk(
                originality_result.plagiarism_risk,
                compliance_result.overall_risk
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "data": {
                    "overall_score": overall_score,
                    "overall_risk": overall_risk.value,
                    "originality_result": {
                        "score": originality_result.originality_score,
                        "risk": originality_result.plagiarism_risk.value,
                        "similarity_items_count": len(originality_result.similarity_items)
                    },
                    "compliance_result": {
                        "score": compliance_result.compliance_score,
                        "risk": compliance_result.overall_risk.value,
                        "violations_count": len(compliance_result.violations),
                        "risk_items_count": len(compliance_result.risk_items)
                    },
                    "recommendations": originality_result.recommendations + 
                                       compliance_result.recommendations,
                    "processing_time_ms": processing_time
                },
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            logger.error(f"综合检测失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000
            }
    
    def _determine_overall_risk(self, 
                               originality_risk: RiskLevel,
                               compliance_risk: RiskLevel) -> RiskLevel:
        """确定综合风险等级"""
        # 取较高的风险等级
        risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        originality_index = risk_levels.index(originality_risk)
        compliance_index = risk_levels.index(compliance_risk)
        
        return risk_levels[max(originality_index, compliance_index)]
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        # 更新组件状态
        self.system_status["components"]["originality_service"] = (
            self.originality_service is not None
        )
        self.system_status["components"]["compliance_service"] = (
            self.compliance_service is not None
        )
        
        # 更新健康检查时间
        self.system_status["last_health_check"] = datetime.now()
        
        return self.system_status
    
    def health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        components_status = {
            "originality_service": self.originality_service is not None,
            "compliance_service": self.compliance_service is not None
        }
        
        # 检查子系统健康
        if self.originality_service:
            originality_health = self.originality_service.get_service_health()
            components_status["originality_details"] = originality_health
        
        if self.compliance_service:
            # 简化的健康检查
            components_status["compliance_details"] = {
                "rules_loaded": len(self.compliance_service.rules) > 0
            }
        
        # 总体状态
        all_healthy = all(components_status.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.system_status["startup_time"]).total_seconds(),
            "components": components_status,
            "total_requests": self.system_status["total_requests"]
        }


# FastAPI应用实例
app = FastAPI(
    title="Multilingual原创合规校验系统",
    description="提供全品类文案、宣传物料、商业内容的全球原创检测与合规校验",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局系统实例
_system_instance: Optional[OriginalityComplianceSystem] = None


def get_system() -> OriginalityComplianceSystem:
    """获取系统实例"""
    global _system_instance
    
    if _system_instance is None:
        _system_instance = OriginalityComplianceSystem()
    
    return _system_instance


# API路由
@app.get("/")
async def root():
    """根路径"""
    return {"service": "Multilingual原创合规校验系统", "version": "1.0.0"}


@app.get("/health")
async def health_check_endpoint(system: OriginalityComplianceSystem = Depends(get_system)):
    """健康检查接口"""
    return system.health_check()


@app.get("/status")
async def system_status_endpoint(system: OriginalityComplianceSystem = Depends(get_system)):
    """系统状态接口"""
    return system.get_system_status()


@app.post("/api/v1/originality/detect")
async def detect_originality_endpoint(
    request: OriginalityRequest,
    system: OriginalityComplianceSystem = Depends(get_system)
):
    """原创性检测接口"""
    try:
        result = system.check_originality(request)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "originality_score": result.originality_score,
                    "plagiarism_risk": result.plagiarism_risk.value,
                    "similarity_items": [
                        {
                            "source_id": item.source_id,
                            "similarity_score": item.similarity_score,
                            "risk_level": item.risk_level.value,
                            "matched_text": item.matched_text[:100] + "..." if len(item.matched_text) > 100 else item.matched_text
                        }
                        for item in result.similarity_items[:5]  # 只返回前5个
                    ],
                    "recommendations": result.recommendations,
                    "processing_time_ms": result.processing_time_ms,
                    "language_detected": result.language_detected
                },
                "processing_time_ms": result.processing_time_ms
            }
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"API调用失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"检测服务暂时不可用: {str(e)}",
                "suggestion": "请稍后重试或联系技术支持"
            }
        )


@app.post("/api/v1/compliance/validate")
async def validate_compliance_endpoint(
    request: ComplianceRequest,
    system: OriginalityComplianceSystem = Depends(get_system)
):
    """合规性校验接口"""
    try:
        result = system.validate_compliance(request)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "compliance_score": result.compliance_score,
                    "overall_risk": result.overall_risk.value,
                    "passed": result.passed,
                    "violations": [
                        {
                            "rule_code": violation.rule_code,
                            "rule_name": violation.rule_name,
                            "description": violation.description,
                            "risk_level": violation.risk_level.value,
                            "suggested_fix": violation.suggested_fix
                        }
                        for violation in result.violations
                    ],
                    "risk_items": [
                        {
                            "risk_type": risk.risk_type,
                            "risk_name": risk.risk_name,
                            "description": risk.description,
                            "risk_level": risk.risk_level.value,
                            "confidence": risk.confidence
                        }
                        for risk in result.risk_items
                    ],
                    "recommendations": result.recommendations,
                    "processing_time_ms": result.processing_time_ms
                },
                "processing_time_ms": result.processing_time_ms
            }
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"API调用失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"校验服务暂时不可用: {str(e)}",
                "suggestion": "请稍后重试或联系技术支持"
            }
        )


@app.post("/api/v1/comprehensive/check")
async def comprehensive_check_endpoint(
    text: str,
    content_type: ContentType = ContentType.MARKETING,
    target_country: CountryCode = CountryCode.US,
    language: str = "auto",
    system: OriginalityComplianceSystem = Depends(get_system)
):
    """综合检测接口"""
    result = system.comprehensive_check(
        text=text,
        content_type=content_type,
        target_country=target_country,
        language=language
    )
    
    if result["success"]:
        return JSONResponse(
            status_code=200,
            content=result
        )
    else:
        return JSONResponse(
            status_code=500,
            content=result
        )


# 启动函数
def run_server(host: str = "0.0.0.0", port: int = 8000):
    """启动Web服务器"""
    logger.info(f"启动原创合规校验系统服务器: {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()