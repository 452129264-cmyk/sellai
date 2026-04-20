"""
全局主脑统一调度系统 - 核心包

提供八大顶级AI能力的统一调度与深度打通：
1. Firecrawl全域爬虫
2. DeepL全域多语种原生润色
3. Multilingual原创合规校验
4. 智能风控合规系统接入
5. 全品类商业数据分析模型接入
6. 高端全场景视觉生成能力接入
7. 全域短视频创作引擎接入
8. 自主迭代进化大脑植入

与现有无限分身系统、Claude Code架构、Notebook LM知识底座、Memory V2记忆系统完全兼容。
"""

# 简化导入，只导入实际存在的模块
from .config import OrchestratorConfig
from .core_scheduler import CoreScheduler

__version__ = "1.0.0"
__all__ = [
    "CoreScheduler",
    "OrchestratorConfig"
]