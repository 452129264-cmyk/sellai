"""
全品类商业数据分析模型
提供行业趋势分析、利润测算、风口研判、项目筛选的完整决策支持系统
"""

__version__ = "1.0.0"
__author__ = "SellAI Team"

from .models.data_models import *
from .services.industry_service import IndustryAnalysisService
from .services.profit_service import ProfitCalculationService
from .services.trend_service import TrendAnalysisService
from .engine.industry_classifier import IndustryClassifier
from .engine.profit_calculator import ProfitCalculator
from .engine.trend_predictor import TrendPredictor

__all__ = [
    "IndustryAnalysisService",
    "ProfitCalculationService",
    "TrendAnalysisService",
    "IndustryClassifier",
    "ProfitCalculator",
    "TrendPredictor",
]