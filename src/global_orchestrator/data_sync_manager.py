#!/usr/bin/env python3
"""
统一调度器数据流同步与冲突解决管理器
确保多分身并行工作的数据一致性

核心功能：
1. 分布式锁机制（基于共享状态库 `data/shared_state/state.db`）
2. 数据版本控制与冲突检测
3. 自动冲突解决策略（基于业务优先级）
4. 性能优化与监控
"""

import sqlite3
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum
import uuid
import hashlib

logger = logging.getLogger(__name__)


class SyncDomain(Enum):
    """同步领域枚举"""
    TASK_ASSIGNMENT = "task_assignment"
    OPPORTUNITY_PROCESSING = "opportunity_processing"
    AVATAR_STATE = "avatar_state"
    CAPABILITY_DATA = "capability_data"
    BUSINESS_ANALYSIS = "business_analysis"
    VISUAL_CONTENT = "visual_content"
    VIDEO_CONTENT = "video_content"
    MEMORY_SYNC = "memory_sync"
    COST_TRACKING = "cost_tracking"


class ConflictResolutionStrategy(Enum):
    """冲突解决策略枚举"""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    BUSINESS_PRIORITY = "business_priority"
    MERGE = "merge"
    MANUAL = "manual"
    AVOIDANCE = "avoidance"  # 通过锁避免冲突


class DataVersion:
    """数据版本控制类"""
    
    def __init__(self, version_id: str = None, timestamp: datetime = None):
        self.version_id = version_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now()
        self.hash = None
    
    def calculate_hash(self, data: Dict[str, Any]) -> str:
        """计算数据哈希值"""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        self.hash = hashlib.sha256(data_str.encode()).hexdigest()
        return self.hash
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version_id": self.version_id,
            "timestamp": self.timestamp.isoformat(),
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataVersion':
        """从字典创建"""
        version = cls(
            version_id=data.get("version_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        )
        version.hash = data.get("hash")
        return version


class DistributedLock:
    """基于数据库的分布式锁"""
    
    def __init__(self, db_path: str, lock_name: str, timeout_seconds: int = 30):
        """
        初始化分布式锁
        
        Args:
            db_path: 数据库路径
            lock_name: 锁名称
            timeout_seconds: 锁超时时间（秒）
        """
        self.db_path = db_path
        self.lock_name = lock_name
        self.timeout_seconds = timeout_seconds
        self.lock_id = str(uuid.uuid4())
        self._connection_cache = threading.local()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程安全的数据库连接"""
        if not hasattr(self._connection_cache, 'conn'):
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            self._connection_cache.conn = conn
        return self._connection_cache.conn
    
    def acquire(self, wait_timeout_seconds: int = 10) -> bool:
        """
        获取锁
        
        Args:
            wait_timeout_seconds: 等待超时时间（秒）
            
        Returns:
            是否成功获取锁
        """
        conn = self._get_connection()
        start_time = time.time()
        
        while time.time() - start_time < wait_timeout_seconds:
            try:
                # 清理过期锁
                conn.execute(
                    "DELETE FROM locks WHERE lock_name = ? AND acquired_at < ?",
                    (self.lock_name, datetime.now() - timedelta(seconds=self.timeout_seconds))
                )
                conn.commit()
                
                # 尝试获取锁
                cursor = conn.execute(
                    "INSERT INTO locks (lock_name, lock_id, acquired_at) VALUES (?, ?, ?)",
                    (self.lock_name, self.lock_id, datetime.now())
                )
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.debug(f"成功获取锁: {self.lock_name} (ID: {self.lock_id})")
                    return True
                    
            except sqlite3.IntegrityError:
                # 锁已被其他进程持有
                pass
            except Exception as e:
                logger.error(f"获取锁时发生错误: {e}")
            
            # 等待重试
            time.sleep(0.1)
        
        logger.warning(f"获取锁超时: {self.lock_name}")
        return False
    
    def release(self) -> bool:
        """
        释放锁
        
        Returns:
            是否成功释放锁
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM locks WHERE lock_name = ? AND lock_id = ?",
                (self.lock_name, self.lock_id)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.debug(f"成功释放锁: {self.lock_name} (ID: {self.lock_id})")
                return True
            else:
                logger.warning(f"锁不存在或已被释放: {self.lock_name}")
                return False
                
        except Exception as e:
            logger.error(f"释放锁时发生错误: {e}")
            return False
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class DataSyncManager:
    """数据同步管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化数据同步管理器
        
        Args:
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self._init_database()
        
        # 锁管理器
        self.lock_manager = self
        
        # 性能统计
        self.stats = {
            "total_sync_operations": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "avg_sync_time_ms": 0.0,
            "last_sync_time": None
        }
        
        # 领域特定的冲突解决策略
        self.domain_strategies = {
            SyncDomain.TASK_ASSIGNMENT: ConflictResolutionStrategy.BUSINESS_PRIORITY,
            SyncDomain.OPPORTUNITY_PROCESSING: ConflictResolutionStrategy.LAST_WRITE_WINS,
            SyncDomain.AVATAR_STATE: ConflictResolutionStrategy.LAST_WRITE_WINS,
            SyncDomain.CAPABILITY_DATA: ConflictResolutionStrategy.MERGE,
            SyncDomain.BUSINESS_ANALYSIS: ConflictResolutionStrategy.MERGE,
            SyncDomain.VISUAL_CONTENT: ConflictResolutionStrategy.MANUAL,
            SyncDomain.VIDEO_CONTENT: ConflictResolutionStrategy.MANUAL,
            SyncDomain.MEMORY_SYNC: ConflictResolutionStrategy.FIRST_WRITE_WINS,
            SyncDomain.COST_TRACKING: ConflictResolutionStrategy.BUSINESS_PRIORITY
        }
        
        logger.info(f"数据同步管理器初始化完成，数据库: {db_path}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # 创建锁表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS locks (
                lock_name TEXT NOT NULL,
                lock_id TEXT NOT NULL,
                acquired_at TIMESTAMP NOT NULL,
                PRIMARY KEY (lock_name)
            )
        """)
        
        # 创建数据版本表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS data_versions (
                domain TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                version_id TEXT NOT NULL,
                version_data TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (domain, resource_id)
            )
        """)
        
        # 创建同步状态表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                sync_id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                resource_id TEXT,
                status TEXT NOT NULL,
                operation TEXT NOT NULL,
                source_node TEXT NOT NULL,
                target_node TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                error_message TEXT
            )
        """)
        
        # sync_conflicts表已存在，确保有必要的索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_domain ON sync_conflicts(domain)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_resource ON sync_conflicts(resource_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_resolved ON sync_conflicts(resolved_at)
        """)
        
        conn.commit()
        conn.close()
    
    def get_lock(self, lock_name: str, timeout_seconds: int = 30) -> DistributedLock:
        """获取分布式锁实例"""
        return DistributedLock(self.db_path, lock_name, timeout_seconds)
    
    def sync_data(self, domain: SyncDomain, resource_id: str, 
                 data: Dict[str, Any], source_node: str = "local",
                 force: bool = False) -> Dict[str, Any]:
        """
        同步数据
        
        Args:
            domain: 同步领域
            resource_id: 资源ID
            data: 要同步的数据
            source_node: 源节点标识
            force: 是否强制同步（忽略冲突）
            
        Returns:
            同步结果
        """
        start_time = time.time()
        sync_id = f"sync_{int(start_time)}_{uuid.uuid4().hex[:8]}"
        
        try:
            # 记录同步开始
            self._record_sync_start(sync_id, domain, resource_id, "sync", source_node, "shared_state")
            
            # 获取领域锁
            lock_name = f"{domain.value}_{resource_id}"
            lock = self.get_lock(lock_name)
            
            if not lock.acquire(wait_timeout_seconds=5):
                self.stats["failed_syncs"] += 1
                error_msg = f"获取锁超时: {lock_name}"
                self._record_sync_error(sync_id, error_msg)
                return {
                    "status": "failed",
                    "sync_id": sync_id,
                    "error": error_msg,
                    "conflict": False
                }
            
            try:
                # 检查数据版本
                current_version = self._get_current_version(domain, resource_id)
                new_version = DataVersion()
                new_version_hash = new_version.calculate_hash(data)
                
                # 检测冲突
                conflict_detected = False
                conflict_info = None
                
                if current_version and not force:
                    conflict_detected, conflict_info = self._detect_conflict(
                        domain, resource_id, current_version, new_version_hash, data
                    )
                    
                    if conflict_detected:
                        self.stats["conflicts_detected"] += 1
                        
                        # 应用冲突解决策略
                        resolution = self._resolve_conflict(
                            domain, resource_id, current_version, new_version, 
                            data, conflict_info
                        )
                        
                        if resolution["status"] == "resolved":
                            data = resolution["resolved_data"]
                            new_version = resolution["new_version"]
                            self.stats["conflicts_resolved"] += 1
                        elif resolution["status"] == "rejected":
                            # 同步被拒绝
                            return {
                                "status": "conflict_rejected",
                                "sync_id": sync_id,
                                "conflict": True,
                                "conflict_info": conflict_info,
                                "resolution": resolution
                            }
                        else:
                            # 需要手动解决
                            self._record_conflict(
                                domain, resource_id, 
                                current_version.to_dict(),
                                new_version.to_dict(),
                                conflict_info
                            )
                            return {
                                "status": "conflict_requires_manual",
                                "sync_id": sync_id,
                                "conflict": True,
                                "conflict_info": conflict_info,
                                "recorded_conflict_id": self._get_last_conflict_id()
                            }
                
                # 保存新版本数据
                self._save_version(domain, resource_id, new_version, data)
                
                # 更新统计
                self.stats["total_sync_operations"] += 1
                self.stats["successful_syncs"] += 1
                
                # 记录同步完成
                sync_time_ms = (time.time() - start_time) * 1000
                self._update_avg_sync_time(sync_time_ms)
                self._record_sync_complete(sync_id)
                
                result = {
                    "status": "success",
                    "sync_id": sync_id,
                    "version": new_version.to_dict(),
                    "conflict": conflict_detected,
                    "sync_time_ms": sync_time_ms
                }
                
                if conflict_detected:
                    result["conflict_resolution"] = "auto_resolved"
                
                return result
                
            finally:
                lock.release()
                
        except Exception as e:
            self.stats["failed_syncs"] += 1
            error_msg = f"同步失败: {str(e)}"
            logger.error(error_msg)
            self._record_sync_error(sync_id, error_msg)
            
            return {
                "status": "failed",
                "sync_id": sync_id,
                "error": error_msg,
                "conflict": False
            }
    
    def _detect_conflict(self, domain: SyncDomain, resource_id: str,
                        current_version: DataVersion, new_version_hash: str,
                        new_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        检测数据冲突
        
        Returns:
            (是否冲突, 冲突信息)
        """
        # 如果哈希值相同，没有冲突
        if current_version.hash == new_version_hash:
            return False, {}
        
        # 检查数据是否正在被其他进程处理
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT 1 FROM locks WHERE lock_name LIKE ?",
            (f"%{domain.value}%",)
        )
        concurrent_locks = cursor.fetchall()
        conn.close()
        
        conflict_info = {
            "domain": domain.value,
            "resource_id": resource_id,
            "current_version": current_version.to_dict(),
            "new_version_hash": new_version_hash,
            "concurrent_operations": len(concurrent_locks) > 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 对于某些领域，如果存在并发操作则视为冲突
        if domain in [SyncDomain.TASK_ASSIGNMENT, SyncDomain.OPPORTUNITY_PROCESSING]:
            if len(concurrent_locks) > 0:
                return True, conflict_info
        
        # 对于其他领域，如果版本哈希不同且数据差异超过阈值，则视为冲突
        # 这里简化处理：只要哈希不同就视为冲突
        return True, conflict_info
    
    def _resolve_conflict(self, domain: SyncDomain, resource_id: str,
                         current_version: DataVersion, new_version: DataVersion,
                         new_data: Dict[str, Any], conflict_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        解决数据冲突
        
        Returns:
            解决结果
        """
        strategy = self.domain_strategies.get(domain, ConflictResolutionStrategy.LAST_WRITE_WINS)
        
        if strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            # 新版本覆盖旧版本
            return {
                "status": "resolved",
                "strategy": strategy.value,
                "new_version": new_version,
                "resolved_data": new_data,
                "message": "新版本覆盖旧版本（最后写入获胜）"
            }
            
        elif strategy == ConflictResolutionStrategy.FIRST_WRITE_WINS:
            # 保留旧版本
            return {
                "status": "rejected",
                "strategy": strategy.value,
                "message": "保留旧版本（首次写入获胜）"
            }
            
        elif strategy == ConflictResolutionStrategy.BUSINESS_PRIORITY:
            # 基于业务优先级决定
            # 这里简化：比较数据的优先级字段
            current_priority = new_data.get("priority", 0)
            # 假设可以通过查询获取当前数据的优先级
            # 这里简化：总是接受新数据
            return {
                "status": "resolved",
                "strategy": strategy.value,
                "new_version": new_version,
                "resolved_data": new_data,
                "message": "基于业务优先级接受新版本"
            }
            
        elif strategy == ConflictResolutionStrategy.MERGE:
            # 尝试合并数据
            try:
                merged_data = self._merge_data(domain, resource_id, new_data)
                merged_version = DataVersion()
                merged_version.calculate_hash(merged_data)
                
                return {
                    "status": "resolved",
                    "strategy": strategy.value,
                    "new_version": merged_version,
                    "resolved_data": merged_data,
                    "message": "数据合并成功"
                }
            except Exception as e:
                logger.warning(f"数据合并失败: {e}")
                # 合并失败，需要手动解决
                return {
                    "status": "requires_manual",
                    "strategy": strategy.value,
                    "message": f"数据合并失败，需要手动解决: {str(e)}"
                }
        
        else:
            # 其他策略默认为需要手动解决
            return {
                "status": "requires_manual",
                "strategy": strategy.value,
                "message": f"需要手动解决的冲突策略: {strategy.value}"
            }
    
    def _merge_data(self, domain: SyncDomain, resource_id: str, 
                   new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并数据
        
        Args:
            domain: 数据领域
            resource_id: 资源ID
            new_data: 新数据
            
        Returns:
            合并后的数据
        """
        # 获取当前数据
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT version_data FROM data_versions WHERE domain = ? AND resource_id = ?",
            (domain.value, resource_id)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return new_data
        
        current_data = json.loads(row["version_data"])
        
        # 根据领域应用不同的合并策略
        if domain == SyncDomain.AVATAR_STATE:
            # 对于分身状态，优先保留新版本的状态
            merged = current_data.copy()
            merged.update(new_data)
            return merged
            
        elif domain == SyncDomain.CAPABILITY_DATA:
            # 对于能力数据，合并列表和字典
            merged = current_data.copy()
            for key, value in new_data.items():
                if key in merged and isinstance(merged[key], list) and isinstance(value, list):
                    # 合并列表，去重
                    merged[key] = list(set(merged[key] + value))
                elif key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    # 合并字典
                    merged[key].update(value)
                else:
                    merged[key] = value
            return merged
            
        elif domain == SyncDomain.BUSINESS_ANALYSIS:
            # 对于商业分析数据，合并分析结果
            merged = current_data.copy()
            # 保留最新的时间戳数据
            if "updated_at" in new_data and "updated_at" in merged:
                if new_data["updated_at"] > merged["updated_at"]:
                    merged = new_data
                else:
                    # 合并关键指标
                    if "metrics" in new_data and "metrics" in merged:
                        for metric_name, metric_value in new_data["metrics"].items():
                            if metric_name not in merged["metrics"]:
                                merged["metrics"][metric_name] = metric_value
            return merged
            
        else:
            # 默认合并策略：新数据覆盖旧数据
            merged = current_data.copy()
            merged.update(new_data)
            return merged
    
    def _get_current_version(self, domain: SyncDomain, resource_id: str) -> Optional[DataVersion]:
        """获取当前版本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT version_id, version_data, created_at FROM data_versions WHERE domain = ? AND resource_id = ?",
            (domain.value, resource_id)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        version_data = json.loads(row["version_data"])
        version = DataVersion(row["version_id"], datetime.fromisoformat(row["created_at"]))
        version.hash = version_data.get("_version_hash")
        return version
    
    def _save_version(self, domain: SyncDomain, resource_id: str, 
                     version: DataVersion, data: Dict[str, Any]):
        """保存版本数据"""
        # 在数据中嵌入版本哈希
        data_with_hash = data.copy()
        data_with_hash["_version_hash"] = version.hash
        data_with_hash["_version_id"] = version.version_id
        data_with_hash["_updated_at"] = datetime.now().isoformat()
        
        version_data = {
            "version": version.to_dict(),
            "data": data_with_hash
        }
        
        conn = sqlite3.connect(self.db_path)
        now = datetime.now()
        
        # 检查是否已存在
        cursor = conn.execute(
            "SELECT 1 FROM data_versions WHERE domain = ? AND resource_id = ?",
            (domain.value, resource_id)
        )
        exists = cursor.fetchone()
        
        if exists:
            # 更新
            conn.execute(
                """UPDATE data_versions 
                   SET version_id = ?, version_data = ?, updated_at = ? 
                   WHERE domain = ? AND resource_id = ?""",
                (version.version_id, json.dumps(version_data), now, domain.value, resource_id)
            )
        else:
            # 插入
            conn.execute(
                """INSERT INTO data_versions (domain, resource_id, version_id, version_data, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (domain.value, resource_id, version.version_id, json.dumps(version_data), now, now)
            )
        
        conn.commit()
        conn.close()
    
    def _record_sync_start(self, sync_id: str, domain: SyncDomain, 
                          resource_id: str, operation: str, 
                          source_node: str, target_node: str):
        """记录同步开始"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO sync_status (sync_id, domain, resource_id, status, operation, 
                  source_node, target_node, started_at)
               VALUES (?, ?, ?, 'started', ?, ?, ?, ?)""",
            (sync_id, domain.value, resource_id, operation, source_node, target_node, datetime.now())
        )
        conn.commit()
        conn.close()
    
    def _record_sync_complete(self, sync_id: str):
        """记录同步完成"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE sync_status SET status = 'completed', completed_at = ? WHERE sync_id = ?",
            (datetime.now(), sync_id)
        )
        conn.commit()
        conn.close()
    
    def _record_sync_error(self, sync_id: str, error_message: str):
        """记录同步错误"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE sync_status SET status = 'failed', error_message = ? WHERE sync_id = ?",
            (error_message[:500], sync_id)  # 限制错误消息长度
        )
        conn.commit()
        conn.close()
    
    def _record_conflict(self, domain: SyncDomain, resource_id: str,
                        local_version: Dict[str, Any], remote_version: Dict[str, Any],
                        conflict_info: Dict[str, Any]):
        """记录冲突"""
        conflict_data = {
            "domain": domain.value,
            "resource_id": resource_id,
            "local_version": local_version,
            "remote_version": remote_version,
            "conflict_info": conflict_info,
            "timestamp": datetime.now().isoformat()
        }
        
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO sync_conflicts (domain, resource_id, local_version, remote_version, conflict_data)
               VALUES (?, ?, ?, ?, ?)""",
            (domain.value, resource_id, 
             json.dumps(local_version), 
             json.dumps(remote_version),
             json.dumps(conflict_data))
        )
        conn.commit()
        conn.close()
    
    def _get_last_conflict_id(self) -> Optional[int]:
        """获取最后记录的冲突ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT MAX(conflict_id) as last_id FROM sync_conflicts"
        )
        row = cursor.fetchone()
        conn.close()
        
        return row["last_id"] if row and row["last_id"] else None
    
    def _update_avg_sync_time(self, new_sync_time_ms: float):
        """更新平均同步时间"""
        total_syncs = self.stats["successful_syncs"] + self.stats["failed_syncs"]
        
        if total_syncs == 1:
            self.stats["avg_sync_time_ms"] = new_sync_time_ms
        else:
            self.stats["avg_sync_time_ms"] = (
                (self.stats["avg_sync_time_ms"] * (total_syncs - 1) + new_sync_time_ms) / total_syncs
            )
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        return {
            "stats": self.stats.copy(),
            "timestamp": datetime.now().isoformat(),
            "domain_strategies": {k.value: v.value for k, v in self.domain_strategies.items()}
        }
    
    def cleanup_expired_locks(self, timeout_seconds: int = 60) -> int:
        """清理过期的锁"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "DELETE FROM locks WHERE acquired_at < ?",
            (datetime.now() - timedelta(seconds=timeout_seconds),)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"清理了 {deleted_count} 个过期的锁")
        
        return deleted_count
    
    def get_pending_conflicts(self, domain: Optional[SyncDomain] = None) -> List[Dict[str, Any]]:
        """获取待解决的冲突"""
        conn = sqlite3.connect(self.db_path)
        
        if domain:
            cursor = conn.execute(
                """SELECT * FROM sync_conflicts 
                   WHERE domain = ? AND resolved_at IS NULL 
                   ORDER BY created_at DESC""",
                (domain.value,)
            )
        else:
            cursor = conn.execute(
                """SELECT * FROM sync_conflicts 
                   WHERE resolved_at IS NULL 
                   ORDER BY created_at DESC"""
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        conflicts = []
        for row in rows:
            conflict = dict(row)
            conflict["conflict_data"] = json.loads(conflict["conflict_data"])
            conflicts.append(conflict)
        
        return conflicts


# 全局数据同步管理器实例
_global_data_sync_manager = None

def get_global_data_sync_manager() -> DataSyncManager:
    """获取全局数据同步管理器实例"""
    global _global_data_sync_manager
    if _global_data_sync_manager is None:
        _global_data_sync_manager = DataSyncManager()
    return _global_data_sync_manager


if __name__ == "__main__":
    """简单的功能验证"""
    print("数据同步管理器简单验证开始...")
    
    # 初始化管理器
    manager = DataSyncManager()
    
    # 清理过期锁
    cleaned = manager.cleanup_expired_locks()
    print(f"清理了 {cleaned} 个过期锁")
    
    # 测试同步数据
    test_domain = SyncDomain.AVATAR_STATE
    test_resource_id = "avatar_001"
    test_data = {
        "avatar_id": "avatar_001",
        "name": "测试分身",
        "status": "busy",
        "load_factor": 0.5,
        "last_heartbeat": datetime.now().isoformat(),
        "priority": 2
    }
    
    # 第一次同步
    result1 = manager.sync_data(test_domain, test_resource_id, test_data)
    print(f"第一次同步结果: {result1['status']}, 版本: {result1['version']['version_id']}")
    
    # 修改数据，再次同步
    test_data["load_factor"] = 0.7
    test_data["status"] = "idle"
    
    result2 = manager.sync_data(test_domain, test_resource_id, test_data)
    print(f"第二次同步结果: {result2['status']}, 版本: {result2['version']['version_id']}")
    
    # 获取统计信息
    stats = manager.get_sync_stats()
    print(f"同步统计: 总操作数={stats['stats']['total_sync_operations']}, "
          f"成功数={stats['stats']['successful_syncs']}, "
          f"平均时间={stats['stats']['avg_sync_time_ms']:.2f}ms")
    
    print("数据同步管理器简单验证完成")