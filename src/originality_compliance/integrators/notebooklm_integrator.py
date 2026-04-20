"""
Notebook LM知识库集成模块
提供与Notebook LM企业版API的集成接口，支持知识检索、相似内容查询等功能
"""

import logging
import json
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import requests
from datetime import datetime
import hashlib

from ..models.data_models import SimilarityItem, RiskLevel, ContentType
from ..utils.text_processor import TextProcessor

logger = logging.getLogger(__name__)


@dataclass
class NotebookLMConfig:
    """Notebook LM配置"""
    api_key: str = ""                    # API密钥
    api_endpoint: str = "https://api.notebooklm.com/v1"  # API端点
    timeout_seconds: int = 30           # 请求超时时间
    max_retries: int = 3                # 最大重试次数
    cache_enabled: bool = True          # 启用缓存
    cache_ttl_seconds: int = 3600       # 缓存生存时间
    min_similarity_threshold: float = 0.4  # 最小相似度阈值


class NotebookLMIntegrator:
    """Notebook LM集成器"""
    
    def __init__(self, config: Optional[NotebookLMConfig] = None):
        """
        初始化Notebook LM集成器
        
        Args:
            config: 配置对象
        """
        self.config = config or NotebookLMConfig()
        self.text_processor = TextProcessor()
        
        # API客户端配置
        self.headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        # 缓存（简化实现）
        self._cache: Dict[str, Dict[str, Any]] = {}
        
    def query_similar_content(self, 
                              text: str, 
                              content_type: Optional[ContentType] = None,
                              max_results: int = 10) -> List[Dict[str, Any]]:
        """
        查询相似知识内容
        
        Args:
            text: 查询文本
            content_type: 内容类型过滤（可选）
            max_results: 最大返回结果数
            
        Returns:
            相似知识项列表
        """
        # 生成缓存键
        cache_key = self._generate_cache_key("similar", text, content_type, max_results)
        
        # 检查缓存
        if self.config.cache_enabled and cache_key in self._cache:
            cached_item = self._cache[cache_key]
            if time.time() - cached_item["timestamp"] < self.config.cache_ttl_seconds:
                logger.debug(f"从缓存获取相似内容: {cache_key}")
                return cached_item["data"]
        
        try:
            # 构建查询请求
            query_data = {
                "query": text,
                "max_results": max_results,
                "threshold": self.config.min_similarity_threshold
            }
            
            if content_type:
                query_data["content_type"] = content_type.value
            
            # 调用Notebook LM相似性搜索API
            # 注：以下为示例实现，实际API端点可能不同
            response = self._make_api_request(
                "POST",
                f"{self.config.api_endpoint}/search/similar",
                data=query_data
            )
            
            if response and "results" in response:
                results = response["results"]
                
                # 转换结果为标准格式
                knowledge_items = []
                for result in results[:max_results]:
                    item = self._convert_to_knowledge_item(result)
                    knowledge_items.append(item)
                
                # 缓存结果
                if self.config.cache_enabled:
                    self._cache[cache_key] = {
                        "timestamp": time.time(),
                        "data": knowledge_items
                    }
                
                return knowledge_items
            
            else:
                logger.warning("Notebook LM查询返回空结果")
                return []
                
        except Exception as e:
            logger.error(f"查询Notebook LM相似内容失败: {str(e)}")
            return []
    
    def search_knowledge_base(self, 
                              keywords: List[str],
                              filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        Args:
            keywords: 关键词列表
            filters: 过滤条件（可选）
            
        Returns:
            知识项列表
        """
        try:
            # 构建搜索请求
            search_data = {
                "keywords": keywords,
                "match_type": "any"  # any/all/phrase
            }
            
            if filters:
                search_data["filters"] = filters
            
            # 调用Notebook LM搜索API
            response = self._make_api_request(
                "POST",
                f"{self.config.api_endpoint}/knowledge/search",
                data=search_data
            )
            
            if response and "items" in response:
                items = response["items"]
                
                # 转换结果为标准格式
                knowledge_items = []
                for item in items:
                    knowledge_item = self._convert_to_knowledge_item(item)
                    knowledge_items.append(knowledge_item)
                
                return knowledge_items
            
            else:
                logger.warning("Notebook LM搜索返回空结果")
                return []
                
        except Exception as e:
            logger.error(f"搜索Notebook LM知识库失败: {str(e)}")
            return []
    
    def retrieve_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        检索特定文档
        
        Args:
            document_id: 文档ID
            
        Returns:
            文档信息字典
        """
        # 生成缓存键
        cache_key = self._generate_cache_key("document", document_id)
        
        # 检查缓存
        if self.config.cache_enabled and cache_key in self._cache:
            cached_item = self._cache[cache_key]
            if time.time() - cached_item["timestamp"] < self.config.cache_ttl_seconds:
                logger.debug(f"从缓存获取文档: {document_id}")
                return cached_item["data"]
        
        try:
            # 调用Notebook LM文档检索API
            response = self._make_api_request(
                "GET",
                f"{self.config.api_endpoint}/documents/{document_id}"
            )
            
            if response:
                # 转换结果为标准格式
                document = self._convert_to_knowledge_item(response)
                
                # 缓存结果
                if self.config.cache_enabled:
                    self._cache[cache_key] = {
                        "timestamp": time.time(),
                        "data": document
                    }
                
                return document
            
            else:
                logger.warning(f"文档检索返回空结果: {document_id}")
                return None
                
        except Exception as e:
            logger.error(f"检索Notebook LM文档失败: {str(e)}")
            return None
    
    def add_to_knowledge_base(self, 
                              content: str,
                              metadata: Dict[str, Any]) -> Optional[str]:
        """
        添加内容到知识库
        
        Args:
            content: 文本内容
            metadata: 元数据
            
        Returns:
            创建的文档ID（如果成功）
        """
        try:
            # 构建添加请求
            add_data = {
                "content": content,
                "metadata": metadata,
                "content_type": metadata.get("content_type", "text")
            }
            
            # 调用Notebook LM添加文档API
            response = self._make_api_request(
                "POST",
                f"{self.config.api_endpoint}/documents",
                data=add_data
            )
            
            if response and "document_id" in response:
                document_id = response["document_id"]
                logger.info(f"成功添加文档到知识库: {document_id}")
                return document_id
            
            else:
                logger.warning("添加文档到知识库失败")
                return None
                
        except Exception as e:
            logger.error(f"添加内容到Notebook LM知识库失败: {str(e)}")
            return None
    
    def convert_to_similarity_items(self, 
                                   knowledge_items: List[Dict[str, Any]],
                                   query_text: str) -> List[SimilarityItem]:
        """
        将知识库查询结果转换为相似性检测项
        
        Args:
            knowledge_items: 知识项列表
            query_text: 查询文本（用于计算相似度）
            
        Returns:
            相似性检测项列表
        """
        similarity_items = []
        
        for item in knowledge_items:
            try:
                # 提取内容
                content = item.get("content", "")
                if not content:
                    continue
                
                # 计算文本相似度（简化实现）
                similarity_score = self._calculate_text_similarity(query_text, content)
                
                if similarity_score < self.config.min_similarity_threshold:
                    continue
                
                # 确定风险等级
                risk_level = self._determine_risk_level(similarity_score)
                
                # 提取匹配片段
                matched_text = self._extract_matched_fragment(query_text, content)
                
                # 生成建议
                recommendations = self._generate_recommendations(similarity_score, risk_level)
                
                # 创建相似性检测项
                similarity_item = SimilarityItem(
                    source_id=item.get("id", "unknown"),
                    source_type="notebooklm",
                    similarity_score=similarity_score,
                    matched_text=matched_text,
                    risk_level=risk_level,
                    recommendations=recommendations,
                    metadata={
                        "source_type": item.get("source_type", ""),
                        "created_at": item.get("created_at", ""),
                        "author": item.get("author", "")
                    }
                )
                
                similarity_items.append(similarity_item)
                
            except Exception as e:
                logger.error(f"转换知识项失败: {str(e)}")
                continue
        
        # 按相似度排序
        similarity_items.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return similarity_items
    
    def _make_api_request(self, 
                          method: str, 
                          url: str, 
                          data: Optional[Dict[str, Any]] = None,
                          retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """
        发送API请求
        
        Args:
            method: HTTP方法
            url: 请求URL
            data: 请求数据（可选）
            retry_count: 当前重试次数
            
        Returns:
            响应数据字典
        """
        try:
            request_kwargs = {
                "headers": self.headers,
                "timeout": self.config.timeout_seconds
            }
            
            if data:
                request_kwargs["json"] = data
            
            if method.upper() == "GET":
                response = requests.get(url, **request_kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, **request_kwargs)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if retry_count < self.config.max_retries:
                logger.warning(f"API请求失败，第{retry_count+1}次重试: {str(e)}")
                time.sleep(2 ** retry_count)  # 指数退避
                return self._make_api_request(method, url, data, retry_count + 1)
            else:
                logger.error(f"API请求失败，已达最大重试次数: {str(e)}")
                return None
    
    def _generate_cache_key(self, *args) -> str:
        """生成缓存键"""
        key_string = ":".join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _convert_to_knowledge_item(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """转换API结果为标准知识项格式"""
        return {
            "id": api_result.get("id", ""),
            "content": api_result.get("content", ""),
            "title": api_result.get("title", ""),
            "source_type": api_result.get("source_type", ""),
            "created_at": api_result.get("created_at", ""),
            "updated_at": api_result.get("updated_at", ""),
            "author": api_result.get("author", ""),
            "content_type": api_result.get("content_type", ""),
            "metadata": api_result.get("metadata", {}),
            "similarity_score": api_result.get("similarity", 0.0)
        }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化实现）"""
        # 归一化处理
        normalized1 = self.text_processor.normalize_text(text1)
        normalized2 = self.text_processor.normalize_text(text2)
        
        # 转换为词汇集合
        words1 = set(self.text_processor.tokenize_words(normalized1))
        words2 = set(self.text_processor.tokenize_words(normalized2))
        
        if not words1 or not words2:
            return 0.0
        
        # 计算Jaccard相似度
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _determine_risk_level(self, similarity_score: float) -> RiskLevel:
        """根据相似度分数确定风险等级"""
        if similarity_score >= 0.8:
            return RiskLevel.HIGH
        elif similarity_score >= 0.6:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _extract_matched_fragment(self, text1: str, text2: str) -> str:
        """提取匹配文本片段"""
        # 简单实现：找出最长的公共连续词汇
        words1 = text1.split()
        words2 = text2.split()
        
        max_length = 0
        best_fragment = ""
        
        for i in range(len(words1)):
            for j in range(len(words2)):
                length = 0
                while (i + length < len(words1) and 
                       j + length < len(words2) and
                       words1[i + length].lower() == words2[j + length].lower()):
                    length += 1
                
                if length > max_length and length >= 2:
                    max_length = length
                    best_fragment = ' '.join(words1[i:i+length])
        
        if best_fragment:
            return f"匹配内容: {best_fragment}"
        else:
            # 返回文本开头部分作为备选
            return text2[:100] + "..." if len(text2) > 100 else text2
    
    def _generate_recommendations(self, similarity_score: float, risk_level: RiskLevel) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "内容与知识库现有资料高度相似，建议大幅修改",
                "考虑添加更多原创分析和独特见解",
                "重新组织语言结构和表达方式"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend([
                "部分内容与知识库资料相似，建议优化表达",
                "增加个性化内容以降低相似度",
                "确保引用来源明确标注"
            ])
        else:
            recommendations.extend([
                "内容原创性良好，可以继续使用",
                "建议保持当前创作风格和质量"
            ])
        
        return recommendations