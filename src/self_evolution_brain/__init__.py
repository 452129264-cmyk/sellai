"""
自主迭代进化大脑核心模块
实现每日自动复盘、策略优化、经验永久沉淀功能
与Notebook LM知识底座深度集成，实现长期自主进化
"""

__version__ = "1.0.0"
__author__ = "SellAI Evolution Team"

from .daily_review_engine import DailyReviewEngine
from .strategy_optimizer import StrategyOptimizer
from .experience_persistence import ExperiencePersistence
from .main_controller import SelfEvolutionBrainController
from .config_manager import SelfEvolutionConfig

__all__ = [
    "DailyReviewEngine",
    "StrategyOptimizer", 
    "ExperiencePersistence",
    "SelfEvolutionBrainController",
    "SelfEvolutionConfig"
]