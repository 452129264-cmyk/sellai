#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory V2 成功后再索引模块
实现验证通过后才构建索引的机制，支持分层索引策略和异步构建。
"""

import json
import logging
import time
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set, Tuple
from enum import Enum
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IndexTier(Enum):
    """索引层级枚举"""
    HOT = "hot"      # 热数据：最近7天，高频访问
    WARM = "warm"    # 温数据：30天内，中等频率
    COLD = "cold"    # 冷数据：归档数据，低频访问


class IndexType(Enum):
    """索引类型枚举"""
    FULL_TEXT = "full_text"      # 全文索引
    KEYWORD = "keyword"          # 关键词索引
    METADATA = "metadata"        # 元数据索引
    SEMANTIC = "semantic"        # 语义索引
    RELATIONAL = "relational"    # 关系索引


@dataclass
class IndexConfig:
    """索引配置"""
    tier: IndexTier
    index_types: List[IndexType]
    rebuild_interval_hours: int
    compression_enabled: bool


class MemoryV2Indexer:
    """Memory V2 索引器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化索引器
        
        Args:
            db_path: 共享状态库路径
        """
        self.db_path = db_path
        self.index_queue = []
        self.indexing_lock = threading.Lock()
        self._init_database()
        self._start_background_indexer()
    
    def _init_database(self):
        """初始化索引相关的数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建索引元数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_indexes (
                index_id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                avatar_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                tier TEXT CHECK(tier IN ('hot', 'warm', 'cold')),
                index_types TEXT NOT NULL,  -- JSON数组
                build_status TEXT CHECK(build_status IN ('pending', 'building', 'built', 'failed')),
                build_start_time TIMESTAMP,
                build_end_time TIMESTAMP,
                index_size_bytes INTEGER DEFAULT 0,
                compression_ratio REAL DEFAULT 1.0,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (memory_id) REFERENCES memory_validation_status(memory_id)
            )
        ''')
        
        # 创建索引条目表（支持多种索引类型）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_index_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_id TEXT NOT NULL,
                entry_type TEXT CHECK(entry_type IN ('full_text', 'keyword', 'metadata', 'semantic', 'relational')),
                entry_key TEXT NOT NULL,
                entry_value TEXT,
                entry_weight REAL DEFAULT 1.0,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (index_id) REFERENCES memory_indexes(index_id)
            )
        ''')
        
        # 创建索引查询优化表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS index_query_stats (
                query_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_pattern TEXT NOT NULL,
                index_ids TEXT NOT NULL,  -- JSON数组
                response_time_ms INTEGER NOT NULL,
                result_count INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                query_timestamp TIMESTAMP NOT NULL
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_index_memory 
            ON memory_indexes(memory_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_index_avatar 
            ON memory_indexes(avatar_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_index_tier 
            ON memory_indexes(tier, build_status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_entries_key 
            ON memory_index_entries(entry_type, entry_key)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_query_stats 
            ON index_query_stats(query_pattern, success)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Memory V2 索引数据库初始化完成")
    
    def _start_background_indexer(self):
        """启动后台索引构建线程"""
        def indexer_worker():
            while True:
                try:
                    self._process_index_queue()
                    time.sleep(5)  # 每5秒检查一次队列
                except Exception as e:
                    logger.error(f"后台索引器异常: {e}")
                    time.sleep(30)
        
        thread = threading.Thread(target=indexer_worker, daemon=True)
        thread.start()
        logger.info("后台索引器已启动")
    
    def _process_index_queue(self):
        """处理索引队列"""
        with self.indexing_lock:
            if not self.index_queue:
                return
            
            # 获取需要构建索引的记忆ID
            memory_ids = self.index_queue[:100]  # 每次最多处理100个
            self.index_queue = self.index_queue[100:]
        
        for memory_id in memory_ids:
            try:
                self._build_index_for_memory(memory_id)
            except Exception as e:
                logger.error(f"构建索引失败 {memory_id}: {e}")
    
    def _build_index_for_memory(self, memory_id: str):
        """
        为单个记忆构建索引
        
        Args:
            memory_id: 记忆ID
        """
        # 1. 获取记忆数据和验证状态
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT vs.avatar_id, vs.memory_type, vs.data_hash, 
                   cs.original_data, vs.created_at
            FROM memory_validation_status vs
            LEFT JOIN memory_data_checksums cs ON vs.memory_id = cs.memory_id
            WHERE vs.memory_id = ? 
              AND vs.verification_status = 'verified'
        ''', (memory_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            logger.warning(f"找不到已验证的记忆: {memory_id}")
            return
        
        avatar_id, memory_type, data_hash, original_data_json, created_at = result
        
        try:
            original_data = json.loads(original_data_json)
        except json.JSONDecodeError:
            logger.error(f"记忆数据JSON解析失败: {memory_id}")
            conn.close()
            return
        
        # 2. 确定索引层级（基于创建时间）
        created_dt = datetime.fromisoformat(created_at)
        days_old = (datetime.now() - created_dt).days
        
        if days_old <= 7:
            tier = IndexTier.HOT
        elif days_old <= 30:
            tier = IndexTier.WARM
        else:
            tier = IndexTier.COLD
        
        # 3. 确定索引类型（基于记忆类型和数据内容）
        index_types = self._determine_index_types(memory_type, original_data)
        
        # 4. 生成索引ID
        index_id = f"idx_{memory_id}_{int(time.time())}"
        
        # 5. 记录索引元数据（状态为building）
        cursor.execute('''
            INSERT OR REPLACE INTO memory_indexes 
            (index_id, memory_id, avatar_id, memory_type, tier, 
             index_types, build_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            index_id,
            memory_id,
            avatar_id,
            memory_type,
            tier.value,
            json.dumps([t.value for t in index_types]),
            'building',
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        
        # 6. 构建具体索引条目
        index_entries = []
        
        for idx_type in index_types:
            entries = self._build_index_entries(idx_type, memory_id, index_id, 
                                              original_data, memory_type)
            index_entries.extend(entries)
        
        # 7. 批量插入索引条目
        if index_entries:
            cursor.executemany('''
                INSERT INTO memory_index_entries 
                (index_id, entry_type, entry_key, entry_value, entry_weight, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', index_entries)
        
        # 8. 更新索引元数据状态为built
        cursor.execute('''
            UPDATE memory_indexes 
            SET build_status = 'built',
                build_end_time = ?,
                index_size_bytes = ?,
                updated_at = ?
            WHERE index_id = ?
        ''', (
            datetime.now().isoformat(),
            len(json.dumps(index_entries)) if index_entries else 0,
            datetime.now().isoformat(),
            index_id
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"索引构建完成: {memory_id} -> {index_id} (tier: {tier.value})")
    
    def _determine_index_types(self, memory_type: str, 
                             data: Dict[str, Any]) -> List[IndexType]:
        """
        确定需要构建的索引类型
        
        Args:
            memory_type: 记忆类型
            data: 记忆数据
            
        Returns:
            索引类型列表
        """
        index_types = [IndexType.METADATA]
        
        # 根据记忆类型添加特定索引
        if memory_type == "intelligence_officer":
            index_types.extend([
                IndexType.KEYWORD,      # 数据源、筛选原因
                IndexType.RELATIONAL    # 商机关联
            ])
            
            # 如果有描述性文本，添加全文索引
            if "filter_reasons" in data and isinstance(data["filter_reasons"], list):
                if any(len(str(reason)) > 20 for reason in data["filter_reasons"]):
                    index_types.append(IndexType.FULL_TEXT)
        
        elif memory_type == "strategy_30margin":
            index_types.extend([
                IndexType.KEYWORD,      # 机会ID、类别
                IndexType.RELATIONAL    # 成本分析关联
            ])
        
        elif memory_type == "copy_channel_officer":
            index_types.extend([
                IndexType.KEYWORD,      # 平台、模板、关键词
                IndexType.FULL_TEXT     # 内容描述
            ])
        
        elif memory_type == "todo_executor":
            index_types.extend([
                IndexType.KEYWORD,      # 任务类型、状态
                IndexType.RELATIONAL    # 任务依赖关系
            ])
        
        elif memory_type == "avatar_processor":
            index_types.extend([
                IndexType.KEYWORD,      # 用户ID、消息类型
                IndexType.SEMANTIC      # 对话语义
            ])
        
        # 去重
        unique_types = []
        for idx_type in index_types:
            if idx_type not in unique_types:
                unique_types.append(idx_type)
        
        return unique_types
    
    def _build_index_entries(self, index_type: IndexType, memory_id: str, 
                           index_id: str, data: Dict[str, Any], 
                           memory_type: str) -> List[Tuple]:
        """
        构建特定类型的索引条目
        
        Args:
            index_type: 索引类型
            memory_id: 记忆ID
            index_id: 索引ID
            data: 记忆数据
            memory_type: 记忆类型
            
        Returns:
            索引条目列表
        """
        entries = []
        created_at = datetime.now().isoformat()
        
        if index_type == IndexType.METADATA:
            # 元数据索引：记忆类型、时间戳等
            entries.append((
                index_id,
                IndexType.METADATA.value,
                "memory_type",
                memory_type,
                1.0,
                created_at
            ))
            
            # 数据源索引（如果有）
            if "data_source" in data:
                entries.append((
                    index_id,
                    IndexType.METADATA.value,
                    "data_source",
                    str(data["data_source"]),
                    0.8,
                    created_at
                ))
        
        elif index_type == IndexType.KEYWORD:
            # 关键词索引：提取数据中的关键词
            keywords = self._extract_keywords(data, memory_type)
            
            for keyword, weight in keywords:
                entries.append((
                    index_id,
                    IndexType.KEYWORD.value,
                    "keyword",
                    keyword,
                    weight,
                    created_at
                ))
        
        elif index_type == IndexType.FULL_TEXT:
            # 全文索引：将文本内容分词索引
            text_content = self._extract_text_content(data, memory_type)
            
            if text_content:
                # 简单分词（实际应用中可以使用更复杂的分词算法）
                words = text_content.split()
                unique_words = set(words[:100])  # 限制索引大小
                
                for word in unique_words:
                    if len(word) > 2:  # 忽略过短的词
                        entries.append((
                            index_id,
                            IndexType.FULL_TEXT.value,
                            "word",
                            word.lower(),
                            0.5,
                            created_at
                        ))
        
        elif index_type == IndexType.RELATIONAL:
            # 关系索引：建立数据关联关系
            relations = self._extract_relations(data, memory_type)
            
            for relation_type, target_id, weight in relations:
                entries.append((
                    index_id,
                    IndexType.RELATIONAL.value,
                    relation_type,
                    target_id,
                    weight,
                    created_at
                ))
        
        elif index_type == IndexType.SEMANTIC:
            # 语义索引：提取语义特征（简化版）
            semantic_features = self._extract_semantic_features(data, memory_type)
            
            for feature_type, feature_value, weight in semantic_features:
                entries.append((
                    index_id,
                    IndexType.SEMANTIC.value,
                    feature_type,
                    feature_value,
                    weight,
                    created_at
                ))
        
        return entries
    
    def _extract_keywords(self, data: Dict[str, Any], 
                        memory_type: str) -> List[Tuple[str, float]]:
        """提取关键词"""
        keywords = []
        
        if memory_type == "intelligence_officer":
            # 数据源、筛选原因
            if "data_source" in data:
                keywords.append((str(data["data_source"]), 0.9))
            
            if "filter_reasons" in data and isinstance(data["filter_reasons"], list):
                for reason in data["filter_reasons"][:5]:
                    keywords.append((str(reason), 0.7))
        
        elif memory_type == "strategy_30margin":
            # 机会ID、类别
            if "opportunity_id" in data:
                keywords.append((str(data["opportunity_id"]), 0.9))
            
            if "category" in data:
                keywords.append((str(data["category"]), 0.8))
        
        elif memory_type == "copy_channel_officer":
            # 目标平台、内容模板
            if "target_platform" in data:
                keywords.append((str(data["target_platform"]), 0.9))
            
            if "content_template" in data:
                keywords.append((str(data["content_template"]), 0.8))
            
            if "keywords" in data and isinstance(data["keywords"], list):
                for keyword in data["keywords"][:10]:
                    keywords.append((str(keyword), 0.6))
        
        # 通用关键词
        keywords.append((memory_type, 0.5))
        
        return keywords
    
    def _extract_text_content(self, data: Dict[str, Any], 
                            memory_type: str) -> Optional[str]:
        """提取文本内容"""
        if memory_type == "intelligence_officer":
            parts = []
            if "filter_reasons" in data and isinstance(data["filter_reasons"], list):
                parts.extend([str(r) for r in data["filter_reasons"]])
            return " ".join(parts)
        
        elif memory_type == "copy_channel_officer":
            parts = []
            if "content_template" in data:
                parts.append(str(data["content_template"]))
            return " ".join(parts)
        
        return None
    
    def _extract_relations(self, data: Dict[str, Any], 
                         memory_type: str) -> List[Tuple[str, str, float]]:
        """提取关系"""
        relations = []
        
        if memory_type == "intelligence_officer":
            # 商机关联
            if "data_source" in data and "raw_items_count" in data:
                relation_key = f"source_{data['data_source']}"
                relations.append(("data_source", relation_key, 0.8))
        
        elif memory_type == "strategy_30margin":
            # 成本分析关联
            if "opportunity_id" in data:
                relations.append(("opportunity", data["opportunity_id"], 0.9))
        
        elif memory_type == "todo_executor":
            # 任务依赖关系
            if "task_id" in data:
                relations.append(("task", data["task_id"], 0.9))
        
        return relations
    
    def _extract_semantic_features(self, data: Dict[str, Any], 
                                 memory_type: str) -> List[Tuple[str, str, float]]:
        """提取语义特征（简化版）"""
        features = []
        
        if memory_type == "avatar_processor":
            # 对话语义特征
            if "response_strategy" in data:
                features.append(("strategy", str(data["response_strategy"]), 0.7))
            
            if "user_satisfaction_indicator" in data:
                satisfaction = str(data["user_satisfaction_indicator"])
                features.append(("satisfaction", satisfaction, 0.6))
        
        return features
    
    def queue_memory_for_indexing(self, memory_id: str):
        """
        将记忆加入索引队列
        
        Args:
            memory_id: 记忆ID
        """
        with self.indexing_lock:
            if memory_id not in self.index_queue:
                self.index_queue.append(memory_id)
                logger.debug(f"记忆加入索引队列: {memory_id}")
    
    def query_memories(self, query: Dict[str, Any], 
                      tier_filter: Optional[IndexTier] = None,
                      limit: int = 50) -> List[Dict[str, Any]]:
        """
        查询记忆
        
        Args:
            query: 查询条件
            tier_filter: 层级过滤
            limit: 结果限制
            
        Returns:
            记忆结果列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = ["mi.build_status = 'built'"]
            params = []
            
            # 层级过滤
            if tier_filter:
                conditions.append("mi.tier = ?")
                params.append(tier_filter.value)
            
            # 关键词查询
            if "keywords" in query and query["keywords"]:
                keyword_conditions = []
                for keyword in query["keywords"][:5]:
                    keyword_conditions.append("mie.entry_key LIKE ?")
                    params.append(f"%{keyword}%")
                
                if keyword_conditions:
                    keyword_sql = " OR ".join(keyword_conditions)
                    conditions.append(f"EXISTS (SELECT 1 FROM memory_index_entries mie WHERE mie.index_id = mi.index_id AND ({keyword_sql}))")
            
            # 记忆类型过滤
            if "memory_type" in query and query["memory_type"]:
                conditions.append("mi.memory_type = ?")
                params.append(query["memory_type"])
            
            # 分身ID过滤
            if "avatar_id" in query and query["avatar_id"]:
                conditions.append("mi.avatar_id = ?")
                params.append(query["avatar_id"])
            
            # 时间范围过滤
            if "start_date" in query and query["start_date"]:
                conditions.append("mi.created_at >= ?")
                params.append(query["start_date"])
            
            if "end_date" in query and query["end_date"]:
                conditions.append("mi.created_at <= ?")
                params.append(query["end_date"])
            
            # 构建SQL
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            sql = f'''
                SELECT DISTINCT 
                    mi.memory_id, mi.avatar_id, mi.memory_type, mi.tier,
                    mi.created_at, mi.updated_at, mi.access_count,
                    cs.original_data
                FROM memory_indexes mi
                LEFT JOIN memory_data_checksums cs ON mi.memory_id = cs.memory_id
                WHERE {where_clause}
                ORDER BY 
                    CASE mi.tier 
                        WHEN 'hot' THEN 1
                        WHEN 'warm' THEN 2
                        WHEN 'cold' THEN 3
                    END,
                    mi.access_count DESC,
                    mi.created_at DESC
                LIMIT ?
            '''
            
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # 更新访问统计
            for row in rows:
                memory_id = row["memory_id"]
                cursor.execute('''
                    UPDATE memory_indexes 
                    SET access_count = access_count + 1,
                        last_accessed = ?,
                        updated_at = ?
                    WHERE memory_id = ?
                ''', (
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    memory_id
                ))
            
            conn.commit()
            
            # 格式化结果
            results = []
            for row in rows:
                result = dict(row)
                
                # 解析原始数据
                if result.get("original_data"):
                    try:
                        result["data"] = json.loads(result["original_data"])
                    except json.JSONDecodeError:
                        result["data"] = {}
                
                # 移除原始JSON字符串
                if "original_data" in result:
                    del result["original_data"]
                
                results.append(result)
            
            conn.close()
            
            # 记录查询统计
            self._record_query_stat(query, len(results), True)
            
            logger.info(f"记忆查询完成: {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"记忆查询失败: {e}")
            self._record_query_stat(query, 0, False)
            return []
    
    def _record_query_stat(self, query: Dict[str, Any], result_count: int, 
                          success: bool):
        """记录查询统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query_pattern = json.dumps(query, sort_keys=True)[:500]
            
            cursor.execute('''
                INSERT INTO index_query_stats 
                (query_pattern, index_ids, response_time_ms, result_count, success, query_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                query_pattern,
                json.dumps([]),  # 简化的索引ID记录
                100,  # 简化响应时间
                result_count,
                success,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录查询统计失败: {e}")
    
    def rebuild_indexes(self, memory_ids: Optional[List[str]] = None,
                       force: bool = False) -> int:
        """
        重建索引
        
        Args:
            memory_ids: 要重建的记忆ID列表（None表示所有）
            force: 是否强制重建（即使状态正常）
            
        Returns:
            重建的索引数量
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确定需要重建的记忆
            if memory_ids:
                placeholders = ','.join(['?'] * len(memory_ids))
                memory_filter = f"AND memory_id IN ({placeholders})"
                params = memory_ids
            else:
                memory_filter = ""
                params = []
            
            # 获取需要重建的记忆ID
            if force:
                cursor.execute(f'''
                    SELECT memory_id FROM memory_validation_status
                    WHERE verification_status = 'verified'
                    {memory_filter}
                ''', params)
            else:
                # 只重建状态为failed或过期的索引
                cursor.execute(f'''
                    SELECT mi.memory_id FROM memory_indexes mi
                    WHERE mi.build_status = 'failed'
                      OR (mi.build_status = 'built' AND mi.updated_at < ?)
                    {memory_filter}
                ''', [datetime.now() - timedelta(hours=24)] + params)
            
            memory_ids_to_rebuild = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            # 加入队列
            for mid in memory_ids_to_rebuild:
                self.queue_memory_for_indexing(mid)
            
            logger.info(f"索引重建计划完成: {len(memory_ids_to_rebuild)} 个记忆")
            return len(memory_ids_to_rebuild)
            
        except Exception as e:
            logger.error(f"索引重建计划失败: {e}")
            return 0
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息
        
        Returns:
            索引统计字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 按层级统计
            cursor.execute('''
                SELECT tier, COUNT(*) as count,
                       SUM(index_size_bytes) as total_size,
                       AVG(access_count) as avg_access,
                       SUM(CASE WHEN build_status = 'built' THEN 1 ELSE 0 END) as built_count
                FROM memory_indexes
                GROUP BY tier
            ''')
            
            tier_stats = {}
            for row in cursor.fetchall():
                tier, count, total_size, avg_access, built_count = row
                tier_stats[tier] = {
                    "count": count,
                    "total_size_bytes": total_size or 0,
                    "avg_access_count": avg_access or 0,
                    "built_count": built_count
                }
            
            # 按类型统计
            cursor.execute('''
                SELECT memory_type, COUNT(*) as count
                FROM memory_indexes
                GROUP BY memory_type
            ''')
            
            type_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 查询性能统计
            cursor.execute('''
                SELECT 
                    AVG(response_time_ms) as avg_response_time,
                    AVG(result_count) as avg_result_count,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
                    COUNT(*) as total_queries
                FROM index_query_stats
                WHERE query_timestamp > ?
            ''', [(datetime.now() - timedelta(days=7)).isoformat()])
            
            query_row = cursor.fetchone()
            query_stats = {
                "avg_response_time_ms": query_row[0] or 0,
                "avg_result_count": query_row[1] or 0,
                "success_rate": (query_row[2] / query_row[3]) if query_row[3] > 0 else 0,
                "total_queries": query_row[3] or 0
            }
            
            conn.close()
            
            return {
                "tier_stats": tier_stats,
                "type_stats": type_stats,
                "query_stats": query_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取索引统计失败: {e}")
            return {}


# 简化索引接口
def index_verified_memory(memory_id: str):
    """
    为已验证记忆构建索引（简化接口）
    
    Args:
        memory_id: 记忆ID
    """
    indexer = MemoryV2Indexer()
    indexer.queue_memory_for_indexing(memory_id)
    logger.info(f"记忆索引已排队: {memory_id}")


def query_indexed_memories(query: Dict[str, Any], 
                          limit: int = 50) -> List[Dict[str, Any]]:
    """
    查询索引记忆（简化接口）
    
    Args:
        query: 查询条件
        limit: 结果限制
        
    Returns:
        记忆结果列表
    """
    indexer = MemoryV2Indexer()
    return indexer.query_memories(query, limit=limit)


if __name__ == "__main__":
    # 测试代码
    print("Memory V2 索引器测试")
    
    # 创建索引器
    indexer = MemoryV2Indexer()
    
    # 测试索引统计
    stats = indexer.get_index_stats()
    print(f"索引统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    # 测试查询（假设有数据）
    test_query = {
        "memory_type": "intelligence_officer",
        "keywords": ["TikTok", "数据源"]
    }
    
    results = indexer.query_memories(test_query, limit=10)
    print(f"查询结果数量: {len(results)}")
    
    # 测试索引重建
    rebuild_count = indexer.rebuild_indexes(force=True)
    print(f"索引重建计划: {rebuild_count} 个记忆")
    
    print("测试完成")