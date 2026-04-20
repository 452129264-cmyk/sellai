"""
八大能力适配器模块
为SellAI全局调度器提供统一的能力调用接口
"""

from .base_adapter import CapabilityAdapter
from .deepl_adapter import DeepLAdapter
from .firecrawl_adapter import FirecrawlAdapter
from .multilingual_adapter import MultilingualAdapter
from .risk_compliance_adapter import RiskComplianceAdapter
from .business_analysis_adapter import BusinessAnalysisAdapter
from .visual_generation_adapter import VisualGenerationAdapter
from .video_creation_adapter import VideoCreationAdapter
from .self_evolution_adapter import SelfEvolutionAdapter

# 能力适配器注册表
CAPABILITY_ADAPTERS = {
    "deepl": DeepLAdapter,
    "firecrawl": FirecrawlAdapter,
    "multilingual": MultilingualAdapter,
    "risk_compliance": RiskComplianceAdapter,
    "business_analysis": BusinessAnalysisAdapter,
    "visual_generation": VisualGenerationAdapter,
    "video_creation": VideoCreationAdapter,
    "self_evolution": SelfEvolutionAdapter
}

def get_adapter(capability_id: str) -> CapabilityAdapter:
    """
    获取能力适配器实例
    
    Args:
        capability_id: 能力标识符
        
    Returns:
        能力适配器实例
        
    Raises:
        ValueError: 能力标识符不存在
    """
    if capability_id not in CAPABILITY_ADAPTERS:
        raise ValueError(f"未知能力标识符: {capability_id}")
    
    adapter_class = CAPABILITY_ADAPTERS[capability_id]
    return adapter_class()

__all__ = [
    "CapabilityAdapter",
    "DeepLAdapter",
    "FirecrawlAdapter",
    "MultilingualAdapter",
    "RiskComplianceAdapter",
    "BusinessAnalysisAdapter",
    "VisualGenerationAdapter",
    "VideoCreationAdapter",
    "SelfEvolutionAdapter",
    "get_adapter",
    "CAPABILITY_ADAPTERS"
]