"""
HyperHorse自研视频引擎模块
SellAI核心一级模块，提供下一代全球商业视频生成能力
性能全面超越Happy Horse，实现全球商业视频全链路自动化
"""

from .module_registry import HyperHorseModule
from .core import HyperHorseEngine
from .api_adapter import HyperHorseAPIAdapter

__all__ = [
    'HyperHorseModule',
    'HyperHorseEngine',
    'HyperHorseAPIAdapter'
]