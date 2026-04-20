"""
智能风控合规系统
版本：v1.0
基于SellAI封神版A架构的全球全行业合规筛查系统
"""

__version__ = "1.0.0"
__author__ = "SellAI Compliance Team"

from .database.models import *
from .engine.rule_engine import SmartRuleEngine
from .screening.content_screener import ContentScreener
from .screening.risk_assessor import RiskAssessor
from .screening.interceptor import ContentInterceptor
from .integrators.notebooklm_integrator import NotebookLMIntegrator
from .integrators.deepl_integrator import DeepLIntegrator
from .integrators.originality_integrator import OriginalityIntegrator
from .services.compliance_service import ComplianceCheckService
from .services.risk_service import RiskAssessmentService
from .services.report_service import ComplianceReportService

__all__ = [
    # 核心引擎
    "SmartRuleEngine",
    
    # 筛查模块
    "ContentScreener",
    "RiskAssessor",
    "ContentInterceptor",
    
    # 集成模块
    "NotebookLMIntegrator",
    "DeepLIntegrator",
    "OriginalityIntegrator",
    
    # 服务模块
    "ComplianceCheckService",
    "RiskAssessmentService",
    "ComplianceReportService",
]