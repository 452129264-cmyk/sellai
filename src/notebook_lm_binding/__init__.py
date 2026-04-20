"""
Notebook LM绑定模块

此模块提供无限分身系统与Notebook LM知识底座的深度绑定功能：
1. 优先检索机制配置
2. 知识库数据导入
3. 分身能力校准
4. 统一配置管理
"""

from src.notebook_lm_binding.knowledge_driven_template_enhancer import (
    KnowledgeDrivenTemplateEnhancer
)
from src.notebook_lm_binding.knowledge_base_importer import KnowledgeBaseImporter
from src.notebook_lm_binding.avatar_capability_calibrator import (
    AvatarCapabilityCalibrator,
    CapabilityScore
)

__all__ = [
    "KnowledgeDrivenTemplateEnhancer",
    "KnowledgeBaseImporter",
    "AvatarCapabilityCalibrator",
    "CapabilityScore"
]

__version__ = "1.0.0"