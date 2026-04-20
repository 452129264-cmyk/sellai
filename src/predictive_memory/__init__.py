#!/usr/bin/env python3
"""
预测性主动记忆系统
Predictive Active Memory System (PAMS)

核心理念：记忆不是为了回忆过去，而是为了预测未来

模块组成：
- CausalPatternBank: 因果模式库
- DecisionPatternBank: 决策模式库
- EmotionalPatternBank: 情感模式库
- SocialPatternBank: 关系模式库
- PredictionEngine: 预测引擎
- MetaCognition: 元认知系统
- PredictiveMemorySystem: 主控制器
"""

from .causal_pattern_bank import CausalPatternBank
from .decision_pattern_bank import DecisionPatternBank
from .emotional_pattern_bank import EmotionalPatternBank
from .social_pattern_bank import SocialPatternBank
from .prediction_engine import PredictionEngine
from .meta_cognition import MetaCognition
from .predictive_memory_system import PredictiveMemorySystem

__version__ = "1.0.0"
__all__ = [
    'CausalPatternBank',
    'DecisionPatternBank',
    'EmotionalPatternBank',
    'SocialPatternBank',
    'PredictionEngine',
    'MetaCognition',
    'PredictiveMemorySystem'
]
