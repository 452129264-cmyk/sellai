#!/usr/bin/env python3
"""
Notebook LM 集成核心模块

此模块提供与Notebook LM企业版API的集成接口，支持知识库创建、文档管理、知识检索等功能。
作为SellAI系统的永久记忆与知识底座核心组件。
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContentType(Enum):
    """文档内容类型枚举"""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    CSV = "csv"
    PLAIN_TEXT = "plain_text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class SourceType(Enum):
    """数据源类型枚举"""
    TASK_RESULT = "task_result"
    MARKET_DATA = "market_data"
    USER_INTERACTION = "user_interaction"
    SYSTEM_LOG = "system_log"
    CONTENT_OUTPUT = "content_output"
    CONFIGURATION = "configuration"
    BEST_PRACTICE = "best_practice"


@dataclass
class KnowledgeDocument:
    """知识文档数据结构"""
    title: str
    content: str
    content_type: ContentType
    source_type: SourceType
    source_id: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['content_type'] = self.content_type.value
        data['source_type'] = self.source_type.value
        # 清理None值
        data = {k: v for k, v in data.items() if v is not None}
        return data


class NotebookLMIntegration:
    """
    Notebook LM集成核心类
    
    提供与Notebook LM企业版API的完整接口，包括：
    - 知识库管理（创建、删除、列表）
    - 文档管理（添加、查询、更新、删除）
    - 知识检索（智能问答、相关文档查询）
    - 内容生成（基于知识库的内容创作）
    """
    
    def __init__(self, api_key: Optional[str] = None, 
                 base_url: str = "https://api.notebooklm.com/v1",
                 cache_enabled: bool = True):
        """
        初始化Notebook LM集成
        
        Args:
            api_key: Notebook LM企业版API密钥，如果为None则从环境变量读取
            base_url: API基础URL
            cache_enabled: 是否启用本地缓存
        """
        self.api_key = api_key or os.getenv("NOTEBOOKLM_API_KEY")
        if not self.api_key:
            raise ValueError("未提供Notebook LM API密钥，请通过参数传入或设置环境变量NOTEBOOKLM_API_KEY")
        
        self.base_url = base_url
        self.cache_enabled = cache_enabled
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"SellAI-NotebookLM-Integration/1.0"
        })
        
        # 知识库ID缓存
        self.knowledge_base_cache = {}
        # 本地缓存（简化实现）
        self.local_cache = {}
        
        logger.info(f"Notebook LM集成初始化完成，基础URL: {base_url}")
    
    def _make_request(self, method: str, endpoint: str, 
                     data: Optional[Dict] = None, 
                     params: Optional[Dict] = None,
                     retries: int = 3) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            method: HTTP方法（GET, POST, PUT, DELETE）
            endpoint: API端点
            data: 请求数据
            params: 查询参数
            retries: 重试次数
            
        Returns:
            API响应数据
            
        Raises:
            requests.exceptions.RequestException: 网络请求异常
            ValueError: API返回错误
        """
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=30
                )
                
                # 检查HTTP状态
                response.raise_for_status()
                
                # 解析JSON响应
                result = response.json()
                
                # 检查API错误
                if "error" in result:
                    error_msg = result["error"].get("message", "Unknown API error")
                    logger.error(f"API返回错误: {error_msg}")
                    raise ValueError(f"Notebook LM API错误: {error_msg}")
                
                return result
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 ({attempt+1}/{retries})，端点: {endpoint}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    raise
            except requests.exceptions.ConnectionError:
                logger.warning(f"连接错误 ({attempt+1}/{retries})，端点: {endpoint}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {str(e)}")
                raise
    
    def create_knowledge_base(self, name: str, 
                             description: Optional[str] = None,
                             tags: Optional[List[str]] = None) -> str:
        """
        创建知识库
        
        Args:
            name: 知识库名称
            description: 知识库描述
            tags: 标签列表
            
        Returns:
            知识库ID
        """
        endpoint = "knowledge_bases"
        
        payload = {
            "name": name,
            "description": description or f"SellAI知识库 - {name}",
            "tags": tags or ["sellai", "ai_partner", "global_business"],
            "metadata": {
                "created_by": "SellAI系统",
                "created_at": datetime.now().isoformat(),
                "system_version": "v2.2"
            }
        }
        
        logger.info(f"创建知识库: {name}")
        result = self._make_request("POST", endpoint, data=payload)
        
        kb_id = result["id"]
        self.knowledge_base_cache[kb_id] = {
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"知识库创建成功，ID: {kb_id}")
        return kb_id
    
    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """
        列出所有知识库
        
        Returns:
            知识库列表
        """
        endpoint = "knowledge_bases"
        
        logger.info("获取知识库列表")
        result = self._make_request("GET", endpoint)
        
        knowledge_bases = result.get("knowledge_bases", [])
        logger.info(f"获取到 {len(knowledge_bases)} 个知识库")
        
        return knowledge_bases
    
    def add_document(self, knowledge_base_id: str, 
                    document: KnowledgeDocument,
                    validate: bool = True) -> str:
        """
        添加文档到知识库
        
        Args:
            knowledge_base_id: 知识库ID
            document: 知识文档对象
            validate: 是否验证文档格式
            
        Returns:
            文档ID
        """
        if validate:
            self._validate_document(document)
        
        endpoint = "documents"
        
        # 准备文档数据
        doc_data = document.to_dict()
        doc_data["knowledge_base_id"] = knowledge_base_id
        
        # 添加系统元数据
        if not doc_data.get("metadata"):
            doc_data["metadata"] = {}
        
        doc_data["metadata"].update({
            "imported_at": datetime.now().isoformat(),
            "document_hash": self._calculate_document_hash(doc_data)
        })
        
        logger.info(f"添加文档到知识库 {knowledge_base_id}: {document.title}")
        result = self._make_request("POST", endpoint, data=doc_data)
        
        doc_id = result["document_id"]
        logger.info(f"文档添加成功，ID: {doc_id}")
        
        return doc_id
    
    def batch_add_documents(self, knowledge_base_id: str,
                           documents: List[KnowledgeDocument],
                           batch_size: int = 100) -> List[Dict[str, Any]]:
        """
        批量添加文档
        
        Args:
            knowledge_base_id: 知识库ID
            documents: 文档列表
            batch_size: 每批处理数量
            
        Returns:
            处理结果列表
        """
        results = []
        total_docs = len(documents)
        
        logger.info(f"开始批量添加 {total_docs} 个文档到知识库 {knowledge_base_id}")
        
        for i in range(0, total_docs, batch_size):
            batch = documents[i:i+batch_size]
            batch_results = []
            
            for doc in batch:
                try:
                    doc_id = self.add_document(knowledge_base_id, doc, validate=False)
                    batch_results.append({
                        "document_title": doc.title,
                        "document_id": doc_id,
                        "status": "success"
                    })
                except Exception as e:
                    logger.error(f"文档添加失败: {doc.title}, 错误: {str(e)}")
                    batch_results.append({
                        "document_title": doc.title,
                        "document_id": None,
                        "status": "failed",
                        "error": str(e)
                    })
            
            results.extend(batch_results)
            
            # 进度报告
            processed = min(i + batch_size, total_docs)
            logger.info(f"批量添加进度: {processed}/{total_docs} ({processed/total_docs*100:.1f}%)")
            
            # 避免API限流
            if i + batch_size < total_docs:
                time.sleep(1)
        
        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(f"批量添加完成，成功: {success_count}/{total_docs}")
        
        return results
    
    def query_knowledge_base(self, knowledge_base_id: str,
                            question: str,
                            context: Optional[str] = None,
                            max_results: int = 5,
                            include_sources: bool = True) -> Dict[str, Any]:
        """
        查询知识库
        
        Args:
            knowledge_base_id: 知识库ID
            question: 查询问题
            context: 上下文信息
            max_results: 最大返回结果数
            include_sources: 是否包含来源信息
            
        Returns:
            查询结果
        """
        endpoint = "query"
        
        # 检查缓存
        cache_key = f"query_{knowledge_base_id}_{hashlib.md5(question.encode()).hexdigest()}"
        if self.cache_enabled and cache_key in self.local_cache:
            cache_data = self.local_cache[cache_key]
            if time.time() - cache_data["timestamp"] < 300:  # 5分钟缓存
                logger.debug(f"缓存命中: {question[:50]}...")
                return cache_data["result"]
        
        payload = {
            "knowledge_base_id": knowledge_base_id,
            "question": question,
            "max_results": max_results,
            "include_sources": include_sources
        }
        
        if context:
            payload["context"] = context
        
        logger.info(f"查询知识库 {knowledge_base_id}: {question[:100]}...")
        result = self._make_request("POST", endpoint, data=payload)
        
        # 更新缓存
        if self.cache_enabled:
            self.local_cache[cache_key] = {
                "result": result,
                "timestamp": time.time()
            }
        
        return result
    
    def generate_content(self, knowledge_base_id: str,
                        prompt: str,
                        style: str = "professional",
                        language: str = "zh-CN",
                        fact_check: bool = True,
                        brand_consistency: bool = True) -> str:
        """
        基于知识库生成内容
        
        Args:
            knowledge_base_id: 知识库ID
            prompt: 生成提示
            style: 内容风格
            language: 目标语言
            fact_check: 是否进行事实核查
            brand_consistency: 是否保持品牌一致性
            
        Returns:
            生成的内容
        """
        endpoint = "generate"
        
        payload = {
            "knowledge_base_id": knowledge_base_id,
            "prompt": prompt,
            "style": style,
            "language": language,
            "fact_check": fact_check,
            "brand_consistency": brand_consistency,
            "metadata": {
                "generated_by": "SellAI系统",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        logger.info(f"基于知识库 {knowledge_base_id} 生成内容，提示: {prompt[:100]}...")
        result = self._make_request("POST", endpoint, data=payload)
        
        content = result.get("content", "")
        logger.info(f"内容生成完成，长度: {len(content)} 字符")
        
        return content
    
    def extract_insights(self, knowledge_base_id: str,
                        document_ids: Optional[List[str]] = None,
                        topics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        从知识库提取洞察
        
        Args:
            knowledge_base_id: 知识库ID
            document_ids: 指定文档ID列表，None表示所有文档
            topics: 主题列表，None表示自动提取
            
        Returns:
            洞察结果
        """
        endpoint = "insights"
        
        payload = {
            "knowledge_base_id": knowledge_base_id,
            "depth": "comprehensive"
        }
        
        if document_ids:
            payload["document_ids"] = document_ids
        
        if topics:
            payload["topics"] = topics
        else:
            # 默认主题
            payload["topics"] = [
                "最佳实践",
                "失败教训",
                "行业趋势",
                "成本优化机会",
                "效率提升策略"
            ]
        
        logger.info(f"从知识库 {knowledge_base_id} 提取洞察")
        result = self._make_request("POST", endpoint, data=payload)
        
        return result
    
    def _validate_document(self, document: KnowledgeDocument) -> None:
        """
        验证文档格式
        
        Args:
            document: 待验证文档
            
        Raises:
            ValueError: 文档格式验证失败
        """
        # 检查必填字段
        if not document.title or not document.title.strip():
            raise ValueError("文档标题不能为空")
        
        if not document.content or not document.content.strip():
            raise ValueError("文档内容不能为空")
        
        # 检查内容长度
        if len(document.content) > 1000000:  # 1MB限制
            raise ValueError("文档内容过大，超过1MB限制")
        
        # 检查标题长度
        if len(document.title) > 200:
            raise ValueError("文档标题过长，超过200字符限制")
        
        logger.debug(f"文档验证通过: {document.title}")
    
    def _calculate_document_hash(self, document_data: Dict[str, Any]) -> str:
        """
        计算文档哈希值
        
        Args:
            document_data: 文档数据
            
        Returns:
            文档哈希值
        """
        content_str = document_data.get("content", "")
        title_str = document_data.get("title", "")
        
        hash_input = f"{title_str}:{content_str}".encode('utf-8')
        return hashlib.md5(hash_input).hexdigest()[:16]
    
    def get_knowledge_base_info(self, knowledge_base_id: str) -> Optional[Dict[str, Any]]:
        """
        获取知识库信息
        
        Args:
            knowledge_base_id: 知识库ID
            
        Returns:
            知识库信息，如果不存在则返回None
        """
        try:
            endpoint = f"knowledge_bases/{knowledge_base_id}"
            result = self._make_request("GET", endpoint)
            return result
        except ValueError as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    def delete_knowledge_base(self, knowledge_base_id: str) -> bool:
        """
        删除知识库
        
        Args:
            knowledge_base_id: 知识库ID
            
        Returns:
            是否删除成功
        """
        try:
            endpoint = f"knowledge_bases/{knowledge_base_id}"
            self._make_request("DELETE", endpoint)
            logger.info(f"知识库删除成功: {knowledge_base_id}")
            return True
        except Exception as e:
            logger.error(f"知识库删除失败: {knowledge_base_id}, 错误: {str(e)}")
            return False
    
    def search_documents(self, knowledge_base_id: str,
                        query: str,
                        filter_tags: Optional[List[str]] = None,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索文档
        
        Args:
            knowledge_base_id: 知识库ID
            query: 搜索查询
            filter_tags: 过滤标签
            limit: 返回结果限制
            
        Returns:
            文档列表
        """
        endpoint = "documents/search"
        
        payload = {
            "knowledge_base_id": knowledge_base_id,
            "query": query,
            "limit": limit
        }
        
        if filter_tags:
            payload["filter_tags"] = filter_tags
        
        result = self._make_request("POST", endpoint, data=payload)
        
        return result.get("documents", [])


# 工具函数
def create_document_from_task_result(task_id: str, 
                                    task_description: str,
                                    task_result: str,
                                    avatar_id: str,
                                    additional_tags: Optional[List[str]] = None) -> KnowledgeDocument:
    """
    从任务结果创建知识文档
    
    Args:
        task_id: 任务ID
        task_description: 任务描述
        task_result: 任务结果
        avatar_id: 执行分身ID
        additional_tags: 附加标签
        
    Returns:
        知识文档对象
    """
    content = f"""
# 任务执行记录

## 任务信息
- **任务ID**: {task_id}
- **执行分身**: {avatar_id}
- **执行时间**: {datetime.now().isoformat()}
- **任务描述**: {task_description}

## 执行结果
{task_result}

## 经验总结
- 成功因素分析
- 改进建议
- 相关知识链接
"""
    
    tags = ["task_record", "experience", "avatar_execution"]
    if additional_tags:
        tags.extend(additional_tags)
    
    return KnowledgeDocument(
        title=f"任务记录_{task_id}",
        content=content,
        content_type=ContentType.MARKDOWN,
        source_type=SourceType.TASK_RESULT,
        source_id=task_id,
        tags=tags,
        metadata={
            "task_type": "avatar_execution",
            "avatar_id": avatar_id,
            "recorded_at": datetime.now().isoformat()
        }
    )


def create_document_from_market_data(source: str,
                                    title: str,
                                    content: str,
                                    region: str,
                                    industry: str,
                                    data_source: str) -> KnowledgeDocument:
    """
    从市场数据创建知识文档
    
    Args:
        source: 数据来源
        title: 文档标题
        content: 数据内容
        region: 地区
        industry: 行业
        data_source: 数据源描述
        
    Returns:
        知识文档对象
    """
    return KnowledgeDocument(
        title=title,
        content=content,
        content_type=ContentType.MARKDOWN,
        source_type=SourceType.MARKET_DATA,
        source_id=f"market_{hashlib.md5(title.encode()).hexdigest()[:8]}",
        tags=["market_intelligence", region.lower(), industry.lower()],
        metadata={
            "source": source,
            "region": region,
            "industry": industry,
            "data_source": data_source,
            "collected_at": datetime.now().isoformat()
        }
    )


# 配置管理
class NotebookLMConfig:
    """Notebook LM配置管理"""
    
    def __init__(self, config_file: str = "configs/notebook_lm_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            # 默认配置
            default_config = {
                "api_key": "",
                "base_url": "https://api.notebooklm.com/v1",
                "knowledge_bases": {
                    "historical_tasks": {
                        "name": "历史任务库",
                        "description": "存储所有分身任务执行记录",
                        "tags": ["task_history", "avatar_execution"]
                    },
                    "global_intelligence": {
                        "name": "全球市场情报库",
                        "description": "跨国市场数据和行业趋势",
                        "tags": ["market_intelligence", "global_business"]
                    }
                },
                "cache_settings": {
                    "enabled": True,
                    "ttl_seconds": 300
                }
            }
            
            # 创建目录
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # 保存默认配置
            self.save_config(default_config)
            return default_config
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """保存配置"""
        if config is None:
            config = self.config
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"配置已保存到: {self.config_file}")
    
    def get_api_key(self) -> str:
        """获取API密钥"""
        api_key = self.config.get("api_key", "")
        if not api_key:
            api_key = os.getenv("NOTEBOOKLM_API_KEY", "")
        
        return api_key
    
    def set_api_key(self, api_key: str) -> None:
        """设置API密钥"""
        self.config["api_key"] = api_key
        self.save_config()
        
        logger.info("API密钥已更新")


# 便捷初始化函数
def initialize_notebook_lm_integration(config_file: Optional[str] = None) -> NotebookLMIntegration:
    """
    初始化Notebook LM集成
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        NotebookLMIntegration实例
    """
    # 加载配置
    config_path = config_file or "configs/notebook_lm_config.json"
    config_manager = NotebookLMConfig(config_path)
    
    # 获取API密钥
    api_key = config_manager.get_api_key()
    if not api_key:
        raise ValueError("未配置Notebook LM API密钥，请运行配置脚本或设置环境变量")
    
    # 创建集成实例
    integration = NotebookLMIntegration(
        api_key=api_key,
        base_url=config_manager.config.get("base_url", "https://api.notebooklm.com/v1")
    )
    
    logger.info("Notebook LM集成初始化完成")
    return integration


if __name__ == "__main__":
    # 模块测试
    print("Notebook LM集成模块测试")
    
    # 示例：创建知识文档
    sample_doc = create_document_from_task_result(
        task_id="test_001",
        task_description="测试任务执行",
        task_result="任务成功完成，所有指标达标",
        avatar_id="avatar_test",
        additional_tags=["test", "example"]
    )
    
    print(f"示例文档标题: {sample_doc.title}")
    print(f"示例文档内容类型: {sample_doc.content_type.value}")
    print(f"示例文档标签: {sample_doc.tags}")
    
    print("\n模块测试完成")
    print("注意：完整测试需要配置有效的Notebook LM API密钥")