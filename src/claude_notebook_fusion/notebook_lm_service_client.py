#!/usr/bin/env python3
"""
Notebook LM 服务客户端

提供与Notebook LM服务的通信接口，支持知识查询、内容生成、记忆存储等功能。
实现双向数据通道的客户端部分。
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import requests
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServiceEndpoint(Enum):
    """服务端点枚举"""
    QUERY = "query"
    MEMORY_WRITE = "memory/write"
    CONTENT_GENERATE = "content/generate"
    BATCH_IMPORT = "batch/import"
    HEALTH_CHECK = "health"


class QueryMode(Enum):
    """查询模式枚举"""
    REAL_TIME = "real_time"
    BATCH = "batch"
    STREAMING = "streaming"


@dataclass
class QueryRequest:
    """查询请求数据结构"""
    query_id: str
    query_text: str
    query_type: str = "factual_qa"
    context: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 10
    mode: QueryMode = QueryMode.REAL_TIME
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query_id": self.query_id,
            "query_text": self.query_text,
            "query_type": self.query_type,
            "context": self.context,
            "filters": self.filters,
            "max_results": self.max_results,
            "mode": self.mode.value
        }


@dataclass
class MemoryWriteRequest:
    """记忆写入请求数据结构"""
    request_id: str
    avatar_id: str
    memory_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_required: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "avatar_id": self.avatar_id,
            "memory_type": self.memory_type,
            "data": self.data,
            "metadata": self.metadata,
            "validation_required": self.validation_required
        }


@dataclass
class ContentGenerateRequest:
    """内容生成请求数据结构"""
    request_id: str
    content_type: str
    topic: str
    requirements: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    style_preferences: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "content_type": self.content_type,
            "topic": self.topic,
            "requirements": self.requirements,
            "context": self.context,
            "style_preferences": self.style_preferences
        }


@dataclass
class QueryResponse:
    """查询响应数据结构"""
    query_id: str
    success: bool
    results: List[Dict[str, Any]]
    confidence: float
    processing_time: float
    source_count: int = 0
    error_message: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryResponse":
        """从字典创建"""
        return cls(
            query_id=data.get("query_id", ""),
            success=data.get("success", False),
            results=data.get("results", []),
            confidence=data.get("confidence", 0.0),
            processing_time=data.get("processing_time", 0.0),
            source_count=data.get("source_count", 0),
            error_message=data.get("error_message")
        )


@dataclass
class MemoryWriteResponse:
    """记忆写入响应数据结构"""
    request_id: str
    success: bool
    memory_id: Optional[str] = None
    validation_status: Optional[str] = None
    index_status: Optional[str] = None
    error_message: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryWriteResponse":
        """从字典创建"""
        return cls(
            request_id=data.get("request_id", ""),
            success=data.get("success", False),
            memory_id=data.get("memory_id"),
            validation_status=data.get("validation_status"),
            index_status=data.get("index_status"),
            error_message=data.get("error_message")
        )


@dataclass
class ContentGenerateResponse:
    """内容生成响应数据结构"""
    request_id: str
    success: bool
    content: Optional[str] = None
    quality_score: Optional[float] = None
    generation_time: Optional[float] = None
    error_message: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentGenerateResponse":
        """从字典创建"""
        return cls(
            request_id=data.get("request_id", ""),
            success=data.get("success", False),
            content=data.get("content"),
            quality_score=data.get("quality_score"),
            generation_time=data.get("generation_time"),
            error_message=data.get("error_message")
        )


def retry(max_attempts: int = 3, delay: float = 1.0):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间(秒)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        sleep_time = delay * (2 ** attempt)  # 指数退避
                        logger.warning(
                            f"函数 {func.__name__} 调用失败，"
                            f"第 {attempt+1}/{max_attempts} 次重试，"
                            f"等待 {sleep_time:.1f} 秒，错误: {str(e)}"
                        )
                        time.sleep(sleep_time)
                    else:
                        logger.error(
                            f"函数 {func.__name__} 重试 {max_attempts} 次后仍失败，"
                            f"最后错误: {str(e)}"
                        )
            raise last_exception
        return wrapper
    return decorator


class NotebookLMServiceClient:
    """
    Notebook LM 服务客户端
    
    提供与Notebook LM服务的完整通信接口。
    """
    
    def __init__(self, 
                 base_url: str = "http://notebook-lm-service:8080",
                 api_key: Optional[str] = None,
                 timeout: float = 30.0,
                 max_retries: int = 3):
        """
        初始化服务客户端
        
        Args:
            base_url: 服务基础URL
            api_key: API密钥(可选)
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 创建会话
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": f"SellAI-NotebookLM-Client/1.0"
        })
        
        if api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {api_key}"
            })
        
        # 缓存设置
        self.query_cache: Dict[str, Tuple[QueryResponse, float]] = {}
        self.cache_ttl = 300  # 缓存有效期(秒)
        
        # 性能统计
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_response_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        
        # 连接池监控
        self._last_health_check = None
        self._health_status = "unknown"
        
        logger.info(f"NotebookLMServiceClient初始化完成，服务地址: {base_url}")
    
    @retry(max_attempts=3, delay=1.0)
    def query_knowledge(self, request: QueryRequest) -> QueryResponse:
        """
        查询知识库
        
        Args:
            request: 查询请求
            
        Returns:
            查询响应
        """
        start_time = time.time()
        query_id = request.query_id
        
        # 生成缓存键
        cache_key = self._generate_query_cache_key(request)
        
        # 检查缓存
        cached_response = self._get_cached_query(cache_key)
        if cached_response:
            logger.debug(f"查询缓存命中: {query_id}")
            self.stats["cache_hits"] += 1
            return cached_response
        
        logger.info(f"执行知识查询: {query_id} - 类型: {request.query_type}")
        
        try:
            # 构建请求
            endpoint = f"{self.base_url}/api/v1/notebook/{ServiceEndpoint.QUERY.value}"
            payload = request.to_dict()
            
            # 发送请求
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 解析响应
            response_data = response.json()
            
            # 创建响应对象
            query_response = QueryResponse.from_dict(response_data)
            query_response.processing_time = time.time() - start_time
            
            # 更新统计
            self.stats["total_queries"] += 1
            self.stats["successful_queries"] += 1
            self._update_avg_response_time(query_response.processing_time)
            
            # 缓存结果
            self._cache_query(cache_key, query_response)
            self.stats["cache_misses"] += 1
            
            logger.debug(f"知识查询完成: {query_id}, 耗时: {query_response.processing_time:.2f}秒")
            
            return query_response
            
        except requests.exceptions.Timeout:
            error_msg = f"查询超时: {query_id}"
            logger.error(error_msg)
            self.stats["failed_queries"] += 1
            raise TimeoutError(error_msg)
            
        except requests.exceptions.ConnectionError:
            error_msg = f"连接错误: {query_id}"
            logger.error(error_msg)
            self.stats["failed_queries"] += 1
            raise ConnectionError(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求异常: {query_id}, 错误: {str(e)}"
            logger.error(error_msg)
            self.stats["failed_queries"] += 1
            raise RuntimeError(error_msg) from e
    
    @retry(max_attempts=3, delay=1.0)
    def write_memory(self, request: MemoryWriteRequest) -> MemoryWriteResponse:
        """
        写入记忆
        
        Args:
            request: 记忆写入请求
            
        Returns:
            记忆写入响应
        """
        start_time = time.time()
        request_id = request.request_id
        
        logger.info(f"写入记忆: {request_id} - 类型: {request.memory_type}")
        
        try:
            # 构建请求
            endpoint = f"{self.base_url}/api/v1/notebook/{ServiceEndpoint.MEMORY_WRITE.value}"
            payload = request.to_dict()
            
            # 发送请求
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 解析响应
            response_data = response.json()
            
            # 创建响应对象
            memory_response = MemoryWriteResponse.from_dict(response_data)
            
            logger.debug(f"记忆写入完成: {request_id}, 耗时: {time.time() - start_time:.2f}秒")
            
            return memory_response
            
        except requests.exceptions.Timeout:
            error_msg = f"记忆写入超时: {request_id}"
            logger.error(error_msg)
            raise TimeoutError(error_msg)
            
        except requests.exceptions.ConnectionError:
            error_msg = f"记忆写入连接错误: {request_id}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
            
        except Exception as e:
            error_msg = f"记忆写入失败: {request_id}, 错误: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    @retry(max_attempts=3, delay=1.0)
    def generate_content(self, request: ContentGenerateRequest) -> ContentGenerateResponse:
        """
        生成内容
        
        Args:
            request: 内容生成请求
            
        Returns:
            内容生成响应
        """
        start_time = time.time()
        request_id = request.request_id
        
        logger.info(f"生成内容: {request_id} - 类型: {request.content_type}")
        
        try:
            # 构建请求
            endpoint = f"{self.base_url}/api/v1/notebook/{ServiceEndpoint.CONTENT_GENERATE.value}"
            payload = request.to_dict()
            
            # 发送请求
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 解析响应
            response_data = response.json()
            
            # 创建响应对象
            content_response = ContentGenerateResponse.from_dict(response_data)
            
            # 添加生成时间
            content_response.generation_time = time.time() - start_time
            
            logger.debug(f"内容生成完成: {request_id}, 耗时: {content_response.generation_time:.2f}秒")
            
            return content_response
            
        except requests.exceptions.Timeout:
            error_msg = f"内容生成超时: {request_id}"
            logger.error(error_msg)
            raise TimeoutError(error_msg)
            
        except requests.exceptions.ConnectionError:
            error_msg = f"内容生成连接错误: {request_id}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
            
        except Exception as e:
            error_msg = f"内容生成失败: {request_id}, 错误: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def batch_import_memories(self, memories: List[MemoryWriteRequest], 
                             batch_size: int = 100) -> List[MemoryWriteResponse]:
        """
        批量导入记忆
        
        Args:
            memories: 记忆列表
            batch_size: 批次大小
            
        Returns:
            导入结果列表
        """
        results = []
        total_memories = len(memories)
        
        logger.info(f"开始批量导入记忆，总数: {total_memories}, 批次大小: {batch_size}")
        
        # 分批处理
        for i in range(0, total_memories, batch_size):
            batch = memories[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_memories + batch_size - 1) // batch_size
            
            logger.info(f"处理批次 {batch_num}/{total_batches}, 大小: {len(batch)}")
            
            # 并行处理批次内的记忆
            futures = []
            for memory_request in batch:
                future = self.thread_pool.submit(
                    self.write_memory,
                    memory_request
                )
                futures.append(future)
            
            # 收集结果
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"记忆导入失败: {str(e)}")
                    results.append(MemoryWriteResponse(
                        request_id=memory_request.request_id,
                        success=False,
                        error_message=str(e)
                    ))
            
            # 批次间延迟，避免过载
            if i + batch_size < total_memories:
                time.sleep(0.5)
        
        logger.info(f"批量导入完成，成功: {sum(1 for r in results if r.success)}, "
                   f"失败: {sum(1 for r in results if not r.success)}")
        
        return results
    
    def check_health(self) -> Dict[str, Any]:
        """
        检查服务健康状态
        
        Returns:
            健康状态信息
        """
        try:
            endpoint = f"{self.base_url}/api/v1/notebook/{ServiceEndpoint.HEALTH_CHECK.value}"
            
            response = self.session.get(
                endpoint,
                timeout=5.0
            )
            response.raise_for_status()
            
            health_data = response.json()
            self._health_status = health_data.get("status", "unknown")
            self._last_health_check = datetime.now()
            
            return health_data
            
        except Exception as e:
            logger.warning(f"健康检查失败: {str(e)}")
            self._health_status = "unhealthy"
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态
        
        Returns:
            服务状态信息
        """
        return {
            "health_status": self._health_status,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "base_url": self.base_url,
            "stats": self.stats.copy()
        }
    
    def _generate_query_cache_key(self, request: QueryRequest) -> str:
        """
        生成查询缓存键
        
        Args:
            request: 查询请求
            
        Returns:
            缓存键
        """
        # 使用查询文本、类型和过滤器生成缓存键
        key_data = {
            "query_text": request.query_text,
            "query_type": request.query_type,
            "filters": json.dumps(request.filters, sort_keys=True)
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached_query(self, cache_key: str) -> Optional[QueryResponse]:
        """
        获取缓存的查询结果
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存的查询响应或None
        """
        if cache_key in self.query_cache:
            cached_response, timestamp = self.query_cache[cache_key]
            # 检查是否过期
            if time.time() - timestamp < self.cache_ttl:
                return cached_response
            else:
                # 缓存过期，删除
                del self.query_cache[cache_key]
        
        return None
    
    def _cache_query(self, cache_key: str, response: QueryResponse):
        """
        缓存查询结果
        
        Args:
            cache_key: 缓存键
            response: 查询响应
        """
        # 限制缓存大小
        if len(self.query_cache) > 1000:
            # 删除最旧的20%条目
            items_to_remove = int(len(self.query_cache) * 0.2)
            sorted_items = sorted(self.query_cache.items(), key=lambda x: x[1][1])
            for i in range(min(items_to_remove, len(sorted_items))):
                del self.query_cache[sorted_items[i][0]]
        
        self.query_cache[cache_key] = (response, time.time())
    
    def _update_avg_response_time(self, response_time: float):
        """
        更新平均响应时间
        
        Args:
            response_time: 新的响应时间
        """
        total_queries = self.stats["total_queries"]
        current_avg = self.stats["avg_response_time"]
        
        if total_queries == 1:
            self.stats["avg_response_time"] = response_time
        else:
            self.stats["avg_response_time"] = (
                (current_avg * (total_queries - 1) + response_time) / total_queries
            )
    
    def clear_cache(self):
        """
        清空缓存
        """
        self.query_cache.clear()
        logger.info("查询缓存已清空")
    
    def shutdown(self):
        """
        关闭客户端
        """
        self.thread_pool.shutdown(wait=True)
        logger.info("NotebookLMServiceClient已关闭")