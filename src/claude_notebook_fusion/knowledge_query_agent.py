#!/usr/bin/env python3
"""
知识查询代理模块

作为Claude执行层与Notebook LM知识层之间的桥梁，
负责处理知识查询请求，管理查询缓存，优化查询效率。
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import threading
from collections import OrderedDict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QueryCache:
    """
    查询缓存管理器
    
    实现LRU缓存策略，支持TTL过期机制。
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存有效期(秒)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self._lock = threading.Lock()
        
        logger.info(f"查询缓存初始化完成，最大大小: {max_size}, TTL: {ttl}秒")
    
    def get(self, cache_key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存值或None
        """
        with self._lock:
            if cache_key in self.cache:
                value, timestamp = self.cache[cache_key]
                
                # 检查是否过期
                if time.time() - timestamp < self.ttl:
                    # 移动到最近使用位置
                    self.cache.move_to_end(cache_key)
                    return value
                else:
                    # 删除过期条目
                    del self.cache[cache_key]
        
        return None
    
    def put(self, cache_key: str, value: Any):
        """
        存储缓存值
        
        Args:
            cache_key: 缓存键
            value: 缓存值
        """
        with self._lock:
            # 如果键已存在，先删除
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            # 检查是否超出最大大小
            if len(self.cache) >= self.max_size:
                # 删除最久未使用的条目
                self.cache.popitem(last=False)
            
            # 存储新条目
            self.cache[cache_key] = (value, time.time())
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
        
        logger.info("查询缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计
        
        Returns:
            缓存统计信息
        """
        with self._lock:
            current_time = time.time()
            active_entries = 0
            expired_entries = 0
            
            for key, (value, timestamp) in self.cache.items():
                if current_time - timestamp < self.ttl:
                    active_entries += 1
                else:
                    expired_entries += 1
            
            return {
                "total_entries": len(self.cache),
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
                "cache_hit_rate": self._calculate_hit_rate()
            }
    
    def _calculate_hit_rate(self) -> float:
        """
        计算缓存命中率（简化实现）
        
        Returns:
            命中率(0-1)
        """
        # 在实际应用中，需要记录查询次数和命中次数
        # 这里返回一个估计值
        if len(self.cache) == 0:
            return 0.0
        
        return min(0.7, len(self.cache) / self.max_size)


class KnowledgeQueryAgent:
    """
    知识查询代理
    
    管理知识查询请求，提供缓存、重试、结果格式化功能。
    """
    
    def __init__(self, 
                 notebook_lm_client: Any,
                 cache_max_size: int = 1000,
                 cache_ttl: int = 300):
        """
        初始化知识查询代理
        
        Args:
            notebook_lm_client: Notebook LM服务客户端
            cache_max_size: 缓存最大大小
            cache_ttl: 缓存TTL(秒)
        """
        self.notebook_lm_client = notebook_lm_client
        self.query_cache = QueryCache(max_size=cache_max_size, ttl=cache_ttl)
        
        # 查询统计
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "direct_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_query_time": 0.0
        }
        
        # 重试配置
        self.retry_config = {
            "max_attempts": 3,
            "initial_delay": 1.0,
            "max_delay": 5.0,
            "backoff_factor": 2.0
        }
        
        # 性能监控
        self.query_times = []
        self.max_query_history = 100
        
        logger.info("知识查询代理初始化完成")
    
    def query(self, query_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行知识查询
        
        Args:
            query_request: 查询请求
            
        Returns:
            查询结果
        """
        start_time = time.time()
        query_id = query_request.get("query_id", f"query_{int(time.time())}")
        
        # 生成缓存键
        cache_key = self._generate_cache_key(query_request)
        
        # 检查缓存
        cached_result = self.query_cache.get(cache_key)
        if cached_result:
            logger.debug(f"缓存命中: {query_id}")
            self.stats["cache_hits"] += 1
            self.stats["total_queries"] += 1
            
            # 更新性能数据
            query_time = time.time() - start_time
            self._update_query_stats(query_time, True)
            
            return self._format_result(cached_result, query_id, query_time, True)
        
        logger.info(f"执行直接查询: {query_id}")
        self.stats["direct_queries"] += 1
        self.stats["total_queries"] += 1
        
        # 执行查询（支持重试）
        try:
            result = self._execute_with_retry(query_request)
            
            query_time = time.time() - start_time
            
            # 缓存结果
            self.query_cache.put(cache_key, result)
            
            # 更新统计
            self.stats["successful_queries"] += 1
            self._update_query_stats(query_time, True)
            
            return self._format_result(result, query_id, query_time, False)
            
        except Exception as e:
            query_time = time.time() - start_time
            
            # 更新失败统计
            self.stats["failed_queries"] += 1
            self._update_query_stats(query_time, False)
            
            logger.error(f"查询失败: {query_id}, 错误: {str(e)}")
            
            return self._format_error_result(query_id, query_time, str(e))
    
    def batch_query(self, query_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量执行查询
        
        Args:
            query_requests: 查询请求列表
            
        Returns:
            查询结果列表
        """
        results = []
        
        logger.info(f"执行批量查询，总数: {len(query_requests)}")
        
        for query_request in query_requests:
            try:
                result = self.query(query_request)
                results.append(result)
            except Exception as e:
                logger.error(f"批量查询中单个查询失败: {str(e)}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "query_id": query_request.get("query_id", "unknown")
                })
        
        return results
    
    def get_related_knowledge(self, topic: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        获取相关知识点
        
        Args:
            topic: 主题
            max_results: 最大结果数
            
        Returns:
            相关知识列表
        """
        query_request = {
            "query_id": f"related_{hashlib.md5(topic.encode()).hexdigest()[:8]}_{int(time.time())}",
            "query_text": f"与'{topic}'相关的知识",
            "query_type": "knowledge_extract",
            "max_results": max_results,
            "filters": {
                "relevance_threshold": 0.7
            }
        }
        
        result = self.query(query_request)
        
        if result.get("success", False):
            return result.get("results", [])
        else:
            logger.warning(f"获取相关知识失败: {topic}")
            return []
    
    def get_task_guidance(self, task_description: str, 
                         task_type: str = "general") -> Dict[str, Any]:
        """
        获取任务指导
        
        Args:
            task_description: 任务描述
            task_type: 任务类型
            
        Returns:
            任务指导信息
        """
        query_request = {
            "query_id": f"task_guidance_{hashlib.md5(task_description.encode()).hexdigest()[:8]}_{int(time.time())}",
            "query_text": f"针对{task_type}任务: {task_description}，提供执行指导和注意事项",
            "query_type": "factual_qa",
            "max_results": 5,
            "filters": {
                "source_type": ["task_result", "best_practice"],
                "time_range": {
                    "start": (datetime.now() - timedelta(days=90)).isoformat(),
                    "end": datetime.now().isoformat()
                }
            }
        }
        
        result = self.query(query_request)
        
        if result.get("success", False):
            return {
                "success": True,
                "guidance": result.get("results", []),
                "confidence": result.get("confidence", 0.0),
                "query_time": result.get("processing_time", 0.0)
            }
        else:
            return {
                "success": False,
                "error": result.get("error_message", "未知错误"),
                "guidance": []
            }
    
    def clear_cache(self):
        """清空查询缓存"""
        self.query_cache.clear()
        logger.info("查询缓存已清空")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计
        
        Returns:
            性能统计信息
        """
        cache_stats = self.query_cache.get_stats()
        
        stats = self.stats.copy()
        stats.update({
            "cache_stats": cache_stats,
            "cache_hit_rate": (self.stats["cache_hits"] / max(1, self.stats["total_queries"])),
            "success_rate": (self.stats["successful_queries"] / max(1, self.stats["total_queries"])),
            "timestamp": datetime.now().isoformat()
        })
        
        return stats
    
    def _execute_with_retry(self, query_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        带重试的查询执行
        
        Args:
            query_request: 查询请求
            
        Returns:
            查询结果
            
        Raises:
            Exception: 查询失败异常
        """
        max_attempts = self.retry_config["max_attempts"]
        current_delay = self.retry_config["initial_delay"]
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                # 调用Notebook LM客户端
                # 这里需要根据实际API调整
                result = self._call_notebook_lm_api(query_request)
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < max_attempts - 1:
                    # 计算下次重试延迟
                    sleep_time = min(
                        current_delay * (self.retry_config["backoff_factor"] ** attempt),
                        self.retry_config["max_delay"]
                    )
                    
                    logger.warning(f"查询重试 {attempt+1}/{max_attempts}, "
                                 f"等待 {sleep_time:.1f}秒, 错误: {str(e)}")
                    
                    time.sleep(sleep_time)
                else:
                    logger.error(f"查询重试 {max_attempts}次后仍失败，最后错误: {str(e)}")
        
        raise last_exception or Exception("查询执行失败")
    
    def _call_notebook_lm_api(self, query_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用Notebook LM API
        
        Args:
            query_request: 查询请求
            
        Returns:
            API响应
            
        Raises:
            Exception: API调用异常
        """
        # 这里应调用实际的Notebook LM客户端
        # 简化实现，返回模拟数据
        
        query_text = query_request.get("query_text", "")
        query_type = query_request.get("query_type", "factual_qa")
        
        # 模拟不同类型的查询结果
        if "成功率" in query_text or "success" in query_text.lower():
            return {
                "results": [
                    {
                        "title": "SellAI系统成功率",
                        "content": "根据历史任务执行数据统计，SellAI系统整体成功率为85%，核心功能成功率92%，数据管道成功率70%，商务匹配准确率90%。",
                        "confidence": 0.85,
                        "source": "task_result_analysis",
                        "timestamp": "2026-04-05T22:30:00",
                        "references": ["task_118", "task_119", "task_14"]
                    }
                ],
                "confidence": 0.85,
                "source_count": 1,
                "query_id": query_request.get("query_id")
            }
        
        elif "指导" in query_text or "guidance" in query_text.lower():
            return {
                "results": [
                    {
                        "title": "任务执行指导",
                        "content": "1. 首先查询相关知识库获取背景信息\n2. 分解任务为可执行的子任务\n3. 基于分身能力矩阵分配合适的任务\n4. 协调分身并行执行\n5. 聚合结果并存储到知识库",
                        "confidence": 0.9,
                        "source": "best_practice_guide",
                        "timestamp": "2026-04-05T10:15:00"
                    }
                ],
                "confidence": 0.9,
                "source_count": 1,
                "query_id": query_request.get("query_id")
            }
        
        else:
            # 通用知识查询
            return {
                "results": [
                    {
                        "title": f"关于'{query_text[:20]}...'的知识",
                        "content": f"这是关于{query_text}的详细知识说明。根据SellAI知识库记录，相关任务执行成功率85%，系统稳定性92%。建议在执行时参考历史最佳实践。",
                        "confidence": 0.8,
                        "source": "knowledge_base",
                        "timestamp": datetime.now().isoformat()
                    }
                ],
                "confidence": 0.8,
                "source_count": 1,
                "query_id": query_request.get("query_id")
            }
    
    def _generate_cache_key(self, query_request: Dict[str, Any]) -> str:
        """
        生成缓存键
        
        Args:
            query_request: 查询请求
            
        Returns:
            缓存键
        """
        # 提取关键字段
        key_data = {
            "query_text": query_request.get("query_text", ""),
            "query_type": query_request.get("query_type", ""),
            "filters": query_request.get("filters", {})
        }
        
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _format_result(self, api_result: Dict[str, Any], query_id: str,
                      query_time: float, cached: bool) -> Dict[str, Any]:
        """
        格式化查询结果
        
        Args:
            api_result: API原始结果
            query_id: 查询ID
            query_time: 查询时间
            cached: 是否缓存命中
            
        Returns:
            格式化结果
        """
        return {
            "success": True,
            "query_id": query_id,
            "results": api_result.get("results", []),
            "confidence": api_result.get("confidence", 0.0),
            "processing_time": query_time,
            "source_count": api_result.get("source_count", 0),
            "cached": cached,
            "timestamp": datetime.now().isoformat()
        }
    
    def _format_error_result(self, query_id: str, query_time: float,
                           error_message: str) -> Dict[str, Any]:
        """
        格式化错误结果
        
        Args:
            query_id: 查询ID
            query_time: 查询时间
            error_message: 错误消息
            
        Returns:
            错误结果
        """
        return {
            "success": False,
            "query_id": query_id,
            "error_message": error_message,
            "processing_time": query_time,
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_query_stats(self, query_time: float, success: bool):
        """
        更新查询统计
        
        Args:
            query_time: 查询时间
            success: 是否成功
        """
        # 记录查询时间
        self.query_times.append(query_time)
        if len(self.query_times) > self.max_query_history:
            self.query_times.pop(0)
        
        # 更新平均查询时间
        if success:
            total_queries = self.stats["successful_queries"]
            current_avg = self.stats["avg_query_time"]
            
            if total_queries == 1:
                self.stats["avg_query_time"] = query_time
            else:
                self.stats["avg_query_time"] = (
                    (current_avg * (total_queries - 1) + query_time) / total_queries
                )