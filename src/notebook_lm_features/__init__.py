"""
Notebook LM四大核心功能模块包

此包包含SellAI系统与Notebook LM集成的四大核心功能：
1. 多格式资料整合
2. 零幻觉精准问答
3. 智能知识提取
4. AI内容创作工坊
"""

from .multi_format_support import MultiFormatProcessor, process_document
from .factual_qa_engine import FactualQAEngine, create_factual_qa_engine
from .knowledge_extraction import KnowledgeExtractionEngine, create_extraction_engine
from .content_creation_workshop import ContentCreationWorkshop, create_content_workshop

__all__ = [
    # 多格式资料整合
    "MultiFormatProcessor",
    "process_document",
    
    # 零幻觉精准问答
    "FactualQAEngine",
    "create_factual_qa_engine",
    
    # 智能知识提取
    "KnowledgeExtractionEngine",
    "create_extraction_engine",
    
    # AI内容创作工坊
    "ContentCreationWorkshop",
    "create_content_workshop"
]

__version__ = "1.0.0"
__description__ = "SellAI系统Notebook LM四大核心功能集成包"