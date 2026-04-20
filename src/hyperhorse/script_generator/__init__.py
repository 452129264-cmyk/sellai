"""
HyperHorse智能脚本生成器模块
基于全品类商业数据分析模型，自动生成符合30%毛利门槛的高转化视频脚本
支持全行业覆盖、多语言生成与效果优化闭环
"""

from .script_generator import ScriptGenerator
from .template_manager import TemplateManager
from .language_adapter import LanguageAdapter
from .feedback_optimizer import FeedbackOptimizer

__all__ = [
    'ScriptGenerator',
    'TemplateManager', 
    'LanguageAdapter',
    'FeedbackOptimizer'
]