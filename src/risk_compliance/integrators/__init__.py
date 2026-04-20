"""
智能风控合规系统集成模块
包含与外部系统的集成功能
"""

from .notebooklm_integrator import NotebookLMIntegrator
from .deepl_integrator import DeepLIntegrator, TranslationRequest, TranslationResponse
from .originality_integrator import OriginalityIntegrator, OriginalityRequest, OriginalityResult

__all__ = [
    "NotebookLMIntegrator",
    "DeepLIntegrator",
    "TranslationRequest",
    "TranslationResponse",
    "OriginalityIntegrator",
    "OriginalityRequest",
    "OriginalityResult"
]