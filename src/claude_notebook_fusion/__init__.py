"""
Claude Code × Notebook LM 架构融合模块

实现Claude负责代码/多Agent协作，Notebook LM负责知识/记忆/内容生产的完整闭环。
提供双向数据通道，优化多Agent协作流程，确保执行效率提升≥20%。
"""

__version__ = "1.0.0"
__author__ = "SellAI Technical Team"

from .claude_notebook_fusion_controller import ClaudeNotebookFusionController
from .notebook_lm_service_client import NotebookLMServiceClient
from .performance_monitor import PerformanceMonitor
from .knowledge_query_agent import KnowledgeQueryAgent
from .task_optimizer import TaskOptimizer

__all__ = [
    "ClaudeNotebookFusionController",
    "NotebookLMServiceClient", 
    "PerformanceMonitor",
    "KnowledgeQueryAgent",
    "TaskOptimizer"
]