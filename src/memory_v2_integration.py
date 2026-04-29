#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory V2 系统集成模块
将验证器和索引器集成到现有SellAI系统中。
"""

import json
import logging
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Tuple
import threading

from memory_v2_validator import MemoryV2Validator, validate_memory_write, ValidationStatus
from memory_v2_indexer import MemoryV2Indexer, IndexTier

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MemoryV2IntegrationManager:
    """Memory V2 集成管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化集成管理器
        
        Args:
            db_path: 共享状态库路径
        """
        self.db_path = db_path
        self.validator = MemoryV2Validator(db_path)
        self.indexer = MemoryV2Indexer(db_path)
        self._running = False
        self._background_thread = None
        
        # 初始化集成表
        self._init_integration_tables()
    
    def _init_integration_tables(self):
        """初始化集成相关的数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建记忆同步状态表（记录Coze记忆与本地验证的同步状态）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_sync_status (
                coze_memory_id TEXT PRIMARY KEY,
                local_memory_id TEXT,
                sync_status TEXT CHECK(sync_status IN ('pending', 'synced', 'verified', 'failed')),
                sync_timestamp TIMESTAMP,
                last_check TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''')
        
        # 创建记忆查询缓存表（加速已验证记忆的查询）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_query_cache (
                query_hash TEXT PRIMARY KEY,
                memory_ids TEXT NOT NULL,  -- JSON数组
                result_count INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                last_accessed TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 0
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sync_status 
            ON memory_sync_status(sync_status, last_check)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_access 
            ON memory_query_cache(last_accessed)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Memory V2 集成数据库初始化完成")
    
    def start_background_services(self):
        """启动后台服务"""
        if self._running:
            logger.warning("后台服务已在运行中")
            return
        
        self._running = True
        self._background_thread = threading.Thread(target=self._background_worker, daemon=True)
        self._background_thread.start()
        logger.info("Memory V2 后台服务已启动")
    
    def stop_background_services(self):
        """停止后台服务"""
        self._running = False
        if self._background_thread:
            self._background_thread.join(timeout=10)
        logger.info("Memory V2 后台服务已停止")
    
    def _background_worker(self):
        """后台工作线程"""
        logger.info("Memory V2 后台工作线程启动")
        
        while self._running:
            try:
                # 1. 处理未验证的记忆
                self._process_pending_memories()
                
                # 2. 重建失败的索引
                self._rebuild_failed_indexes()
                
                # 3. 清理旧缓存
                self._cleanup_old_cache()
                
                # 4. 更新统计信息
                self._update_system_stats()
                
                # 休眠一段时间
                time.sleep(30)  # 每30秒执行一次
                
            except Exception as e:
                logger.error(f"后台工作线程异常: {e}")
                time.sleep(60)  # 异常后休眠更久
    
    def _process_pending_memories(self):
        """处理待验证的记忆"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取待验证的记忆（状态为written但未verified）
            cursor.execute('''
                SELECT memory_id, avatar_id, memory_type, data_hash
                FROM memory_validation_status
                WHERE write_status = 'written'
                  AND verification_status = 'pending'
                ORDER BY created_at ASC
                LIMIT 50
            ''')
            
            pending_memories = cursor.fetchall()
            
            for memory_id, avatar_id, memory_type, data_hash in pending_memories:
                try:
                    # 模拟读取函数（实际应用中需要实现真实的Coze记忆读取）
                    def mock_read_func(mid: str) -> Tuple[bool, Any]:
                        # 这里应该调用Coze API读取记忆数据
                        # 为简化，我们假设总是读取成功
                        conn_inner = sqlite3.connect(self.db_path)
                        cursor_inner = conn_inner.cursor()
                        
                        cursor_inner.execute('''
                            SELECT original_data FROM memory_data_checksums
                            WHERE memory_id = ?
                        ''', (mid,))
                        
                        result = cursor_inner.fetchone()
                        conn_inner.close()
                        
                        if result:
                            return True, json.loads(result[0])
                        else:
                            return False, "找不到记忆数据"
                    
                    # 执行验证
                    verify_success, verify_error = self.validator.post_write_verification(
                        memory_id, mock_read_func
                    )
                    
                    if verify_success:
                        # 验证成功，更新状态
                        self.validator.update_verification_status(
                            memory_id, ValidationStatus.VERIFIED
                        )
                        
                        # 加入索引队列
                        self.indexer.queue_memory_for_indexing(memory_id)
                        
                        logger.info(f"记忆验证成功: {memory_id}")
                    else:
                        # 验证失败，更新状态
                        self.validator.update_verification_status(
                            memory_id, ValidationStatus.FAILED, verify_error
                        )
                        
                        # 增加重试计数
                        cursor.execute('''
                            UPDATE memory_validation_status
                            SET retry_count = retry_count + 1,
                                updated_at = ?
                            WHERE memory_id = ?
                        ''', (datetime.now().isoformat(), memory_id))
                        
                        logger.warning(f"记忆验证失败: {memory_id} - {verify_error}")
                
                except Exception as e:
                    logger.error(f"处理记忆 {memory_id} 异常: {e}")
            
            conn.commit()
            conn.close()
            
            if pending_memories:
                logger.debug(f"处理了 {len(pending_memories)} 个待验证记忆")
                
        except Exception as e:
            logger.error(f"处理待验证记忆异常: {e}")
    
    def _rebuild_failed_indexes(self):
        """重建失败的索引"""
        try:
            # 重建所有失败的索引
            rebuild_count = self.indexer.rebuild_indexes(force=False)
            
            if rebuild_count > 0:
                logger.info(f"索引重建计划: {rebuild_count} 个索引")
                
        except Exception as e:
            logger.error(f"重建索引异常: {e}")
    
    def _cleanup_old_cache(self):
        """清理旧缓存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 删除7天前的缓存
            cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
            
            cursor.execute('''
                DELETE FROM memory_query_cache
                WHERE last_accessed < ?
            ''', (cutoff_date,))
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个旧缓存条目")
                
        except Exception as e:
            logger.error(f"清理缓存异常: {e}")
    
    def _update_system_stats(self):
        """更新系统统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取验证统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN verification_status = 'verified' THEN 1 ELSE 0 END) as verified,
                    SUM(CASE WHEN verification_status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN verification_status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM memory_validation_status
            ''')
            
            stats_row = cursor.fetchone()
            
            # 获取索引统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as indexed,
                    SUM(CASE WHEN build_status = 'built' THEN 1 ELSE 0 END) as built,
                    SUM(CASE WHEN build_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM memory_indexes
            ''')
            
            index_row = cursor.fetchone()
            
            # 计算验证成功率
            total = stats_row[0] or 0
            verified = stats_row[1] or 0
            success_rate = (verified / total * 100) if total > 0 else 0
            
            # 保存统计信息（可以用于仪表盘展示）
            stats_data = {
                "timestamp": datetime.now().isoformat(),
                "validation_stats": {
                    "total_memories": total,
                    "verified": verified,
                    "failed": stats_row[2] or 0,
                    "pending": stats_row[3] or 0,
                    "success_rate_percent": round(success_rate, 2)
                },
                "indexing_stats": {
                    "total_indexed": index_row[0] or 0,
                    "built": index_row[1] or 0,
                    "failed": index_row[2] or 0
                }
            }
            
            # 这里可以将统计信息保存到特定表或文件中
            # 例如：cursor.execute('INSERT INTO system_stats (stats_json) VALUES (?)', (json.dumps(stats_data),))
            
            conn.close()
            
            # 每10次记录一次日志
            if int(time.time()) % 600 < 30:  # 每10分钟记录一次
                logger.info(f"系统统计: {json.dumps(stats_data, ensure_ascii=False)}")
                
        except Exception as e:
            logger.error(f"更新系统统计异常: {e}")
    
    def integrate_with_avatar_processor(self, avatar_id: str, 
                                       memory_type: str, 
                                       memory_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        与分身处理器集成（模拟Coze记忆写入的拦截点）
        
        Args:
            avatar_id: 分身ID
            memory_type: 记忆类型
            memory_data: 记忆数据
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 构建完整的记忆数据
            full_memory_data = {
                "avatar_id": avatar_id,
                "memory_type": memory_type,
                "data": memory_data
            }
            
            # 模拟写入函数（实际应该调用Coze记忆API）
            def mock_write_func(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
                # 这里应该调用Coze API写入记忆
                # 为简化，我们假设总是写入成功
                logger.info(f"模拟Coze记忆写入: {data.get('avatar_id')} - {data.get('memory_type')}")
                return True, None
            
            # 模拟读取函数
            def mock_read_func(mid: str) -> Tuple[bool, Any]:
                # 这里应该调用Coze API读取记忆
                # 为简化，我们从校验和表读取
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT original_data FROM memory_data_checksums
                    WHERE memory_id = ?
                ''', (mid,))
                
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    return True, json.loads(result[0])
                else:
                    return False, "找不到记忆数据"
            
            # 执行验证流程
            success, memory_id, error = validate_memory_write(
                full_memory_data,
                mock_write_func,
                mock_read_func,
                storage_target="coze_memory"
            )
            
            if success:
                logger.info(f"记忆写入验证完成: {memory_id}")
                
                # 记录同步状态
                self._record_sync_status(memory_id, "coze_simulated_id", "synced")
                
                return True, memory_id
            else:
                logger.error(f"记忆写入验证失败: {error}")
                return False, error
                
        except Exception as e:
            logger.error(f"与分身处理器集成异常: {e}")
            return False, str(e)
    
    def _record_sync_status(self, local_memory_id: str, coze_memory_id: str, 
                           status: str):
        """记录同步状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO memory_sync_status 
                (coze_memory_id, local_memory_id, sync_status, 
                 sync_timestamp, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                coze_memory_id,
                local_memory_id,
                status,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录同步状态异常: {e}")
    
    def query_verified_memories(self, query: Dict[str, Any], 
                               limit: int = 50) -> List[Dict[str, Any]]:
        """
        查询已验证的记忆
        
        Args:
            query: 查询条件
            limit: 结果限制
            
        Returns:
            记忆结果列表
        """
        try:
            # 首先尝试缓存
            query_hash = self._calculate_query_hash(query)
            cached_result = self._get_cached_query(query_hash)
            
            if cached_result:
                logger.debug(f"查询缓存命中: {query_hash}")
                return cached_result
            
            # 查询索引
            results = self.indexer.query_memories(query, limit=limit)
            
            # 过滤只返回已验证的记忆
            verified_results = []
            for result in results:
                memory_id = result.get("memory_id")
                if memory_id:
                    status = self.validator.get_validation_status(memory_id)
                    if status and status.get("verification_status") == "verified":
                        verified_results.append(result)
            
            # 更新缓存
            self._update_query_cache(query_hash, verified_results)
            
            return verified_results
            
        except Exception as e:
            logger.error(f"查询已验证记忆异常: {e}")
            return []
    
    def _calculate_query_hash(self, query: Dict[str, Any]) -> str:
        """计算查询哈希值"""
        import hashlib
        query_str = json.dumps(query, sort_keys=True)
        return hashlib.sha256(query_str.encode()).hexdigest()[:32]
    
    def _get_cached_query(self, query_hash: str) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的查询结果"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT memory_ids FROM memory_query_cache
                WHERE query_hash = ?
                  AND last_accessed > ?
                LIMIT 1
            ''', (
                query_hash,
                (datetime.now() - timedelta(hours=1)).isoformat()
            ))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                memory_ids = json.loads(result[0])
                
                # 从索引获取完整数据
                if memory_ids:
                    query = {"memory_ids": memory_ids}
                    return self.indexer.query_memories(query, limit=len(memory_ids))
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存查询异常: {e}")
            return None
    
    def _update_query_cache(self, query_hash: str, results: List[Dict[str, Any]]):
        """更新查询缓存"""
        try:
            if not results:
                return
            
            memory_ids = [r.get("memory_id") for r in results if r.get("memory_id")]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO memory_query_cache
                (query_hash, memory_ids, result_count, created_at, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, COALESCE(
                    (SELECT access_count + 1 FROM memory_query_cache WHERE query_hash = ?),
                    1
                ))
            ''', (
                query_hash,
                json.dumps(memory_ids),
                len(results),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                query_hash
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"更新查询缓存异常: {e}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        获取系统健康状态
        
        Returns:
            健康状态字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取验证失败率
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN verification_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM memory_validation_status
                WHERE created_at > ?
            ''', [(datetime.now() - timedelta(hours=24)).isoformat()])
            
            row = cursor.fetchone()
            total = row[0] or 0
            failed = row[1] or 0
            failure_rate = (failed / total * 100) if total > 0 else 0
            
            # 获取索引构建失败率
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN build_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM memory_indexes
                WHERE created_at > ?
            ''', [(datetime.now() - timedelta(hours=24)).isoformat()])
            
            index_row = cursor.fetchone()
            index_total = index_row[0] or 0
            index_failed = index_row[1] or 0
            index_failure_rate = (index_failed / index_total * 100) if index_total > 0 else 0
            
            conn.close()
            
            # 评估健康状态
            health_status = "healthy"
            if failure_rate > 10:
                health_status = "warning"
            if failure_rate > 30:
                health_status = "critical"
            
            return {
                "health_status": health_status,
                "metrics": {
                    "validation_failure_rate_percent": round(failure_rate, 2),
                    "indexing_failure_rate_percent": round(index_failure_rate, 2),
                    "total_memories_24h": total,
                    "failed_memories_24h": failed
                },
                "timestamp": datetime.now().isoformat(),
                "recommendations": self._generate_health_recommendations(failure_rate, index_failure_rate)
            }
            
        except Exception as e:
            logger.error(f"获取系统健康状态异常: {e}")
            return {
                "health_status": "unknown",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_health_recommendations(self, failure_rate: float, 
                                        index_failure_rate: float) -> List[str]:
        """生成健康建议"""
        recommendations = []
        
        if failure_rate > 5:
            recommendations.append("验证失败率较高，建议检查数据源稳定性")
        
        if failure_rate > 20:
            recommendations.append("验证失败率过高，可能需要调整验证阈值")
        
        if index_failure_rate > 10:
            recommendations.append("索引构建失败率较高，建议检查存储空间")
        
        if not recommendations:
            recommendations.append("系统运行正常，建议定期监控")
        
        return recommendations


# 简化集成接口
def integrate_memory_v2():
    """
    集成Memory V2系统（简化接口）
    
    Returns:
        集成管理器实例
    """
    manager = MemoryV2IntegrationManager()
    manager.start_background_services()
    logger.info("Memory V2 系统集成完成")
    return manager


def write_memory_with_validation(avatar_id: str, memory_type: str, 
                                memory_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    带验证的记忆写入（简化接口）
    
    Args:
        avatar_id: 分身ID
        memory_type: 记忆类型
        memory_data: 记忆数据
        
    Returns:
        (是否成功, 错误信息)
    """
    manager = MemoryV2IntegrationManager()
    return manager.integrate_with_avatar_processor(avatar_id, memory_type, memory_data)


def query_memories_safely(query: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
    """
    安全查询记忆（只返回已验证数据）
    
    Args:
        query: 查询条件
        limit: 结果限制
        
    Returns:
        记忆结果列表
    """
    manager = MemoryV2IntegrationManager()
    return manager.query_verified_memories(query, limit=limit)


if __name__ == "__main__":
    # 测试代码
    print("Memory V2 集成模块测试")
    
    # 集成系统
    manager = integrate_memory_v2()
    
    # 测试记忆写入
    test_memory_data = {
        "data_source": "TikTok",
        "raw_items_count": 200,
        "high_margin_items_count": 60,
        "filter_reasons": ["成本过高", "市场饱和"],
        "success_rate": 0.88,
        "estimated_opportunity_value": 18000.0
    }
    
    success, result = write_memory_with_validation(
        "avatar_test_002",
        "intelligence_officer",
        test_memory_data
    )
    
    print(f"记忆写入结果: {success}, 结果: {result}")
    
    # 等待后台处理
    print("等待后台处理...")
    time.sleep(10)
    
    # 测试查询
    test_query = {
        "memory_type": "intelligence_officer",
        "keywords": ["TikTok"]
    }
    
    results = query_memories_safely(test_query, limit=10)
    print(f"查询结果数量: {len(results)}")
    
    # 获取系统健康状态
    health = manager.get_system_health()
    print(f"系统健康状态: {json.dumps(health, indent=2, ensure_ascii=False)}")
    
    # 停止服务
    manager.stop_background_services()
    
    print("测试完成")