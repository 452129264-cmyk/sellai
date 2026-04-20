"""
Multilingual原创合规校验系统核心模块

此模块提供全品类文案、宣传物料、商业内容的全球原创检测与合规校验能力。
集成到SellAI现有架构（无限AI分身、Claude Code架构、Notebook LM知识底座、DeepL集成能力）。

主要功能：
1. 原创性检测：支持中英文等多语种原创检测，准确率≥95%
2. 合规校验：支持至少5个国家商业法规检查（中美欧日韩）
3. 侵权风险识别：商标、版权、专利风险识别准确率≥90%
4. 高风险内容自动拦截：拦截率100%
5. 系统集成：与Notebook LM知识库、DeepL翻译服务深度集成

版本：v1.0
创建时间：2026-04-05
"""

from .services.originality_service import OriginalityDetectionService
from .services.compliance_service import ComplianceValidationService
from .services.risk_assessment_service import RiskAssessmentService
from .main import OriginalityComplianceSystem

__all__ = [
    'OriginalityDetectionService',
    'ComplianceValidationService', 
    'RiskAssessmentService',
    'OriginalityComplianceSystem'
]