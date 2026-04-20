#!/usr/bin/env python3
"""
SellAI v3.0.0 - 网络数据同步系统
Network Data Sync & Shared State Manager
跨节点数据同步、共享状态管理

功能：
- 网络数据同步
- 共享状态管理
- 数据一致性保证
"""

import os
import time
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    FAILED = "failed"


@dataclass
class SyncNode:
    node_id: str
    name: str
    endpoint: str
    status: str = "active"
    last_sync: Optional[str] = None
    priority: int = 1


@dataclass
class DataRecord:
    record_id: str
    key: str
    value: Any
    version: int = 1
    checksum: str = ""
    sync_status: SyncStatus = SyncStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    synced_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class NetworkDataSync:
    """网络数据同步"""
    
    def __init__(self, db_path: str = "data/shared_state/network_sync.db"):
        self.db_path = db_path
        self.nodes: Dict[str, SyncNode] = {}
        self.records: Dict[str, DataRecord] = {}
        self.sync_queue: List[str] = []
        self._ensure_data_dir()
        logger.info("网络数据同步系统初始化完成")
    
    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def register_node(self, name: str, endpoint: str, priority: int = 1) -> SyncNode:
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        node = SyncNode(node_id=node_id, name=name, endpoint=endpoint, priority=priority)
        self.nodes[node_id] = node
        logger.info(f"注册同步节点: {node_id}")
        return node
    
    def put(self, key: str, value: Any, metadata: Dict = None) -> DataRecord:
        record_id = f"rec_{uuid.uuid4().hex[:8]}"
        
        # 计算校验和
        value_str = str(value)
        checksum = hashlib.md5(value_str.encode()).hexdigest()
        
        record = DataRecord(
            record_id=record_id,
            key=key,
            value=value,
            checksum=checksum,
            sync_status=SyncStatus.PENDING,
            metadata=metadata or {}
        )
        
        self.records[record_id] = record
        self.sync_queue.append(record_id)
        
        logger.info(f"写入数据: {key} -> {record_id}")
        return record
    
    def get(self, key: str) -> Optional[Any]:
        for r in self.records.values():
            if r.key == key and r.sync_status == SyncStatus.SYNCED:
                return r.value
        return None
    
    def sync_to_node(self, node_id: str) -> Dict[str, Any]:
        node = self.nodes.get(node_id)
        if not node:
            return {"success": False, "error": "节点不存在"}
        
        synced = []
        for record_id in self.sync_queue:
            record = self.records.get(record_id)
            if record:
                record.sync_status = SyncStatus.SYNCED
                record.synced_at = datetime.now().isoformat()
                synced.append(record_id)
        
        for rid in synced:
            self.sync_queue.remove(rid)
        
        node.last_sync = datetime.now().isoformat()
        
        return {
            "success": True,
            "synced_count": len(synced),
            "node": node_id
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": "NetworkDataSync",
            "total_nodes": len(self.nodes),
            "total_records": len(self.records),
            "pending_sync": len(self.sync_queue)
        }


class SharedStateManager:
    """共享状态管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/shared_state.db"):
        self.db_path = db_path
        self.state: Dict[str, Any] = {}
        self.locks: Dict[str, str] = {}  # key -> locker_id
        self.watchers: Dict[str, List[callable]] = {}  # key -> callback functions
        self._ensure_data_dir()
        logger.info("共享状态管理器初始化完成")
    
    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def set(self, key: str, value: Any, locker_id: Optional[str] = None) -> bool:
        # 检查锁
        if key in self.locks and self.locks[key] != locker_id:
            return False
        
        old_value = self.state.get(key)
        self.state[key] = value
        
        # 触发watchers
        if key in self.watchers:
            for callback in self.watchers[key]:
                try:
                    callback(key, old_value, value)
                except Exception as e:
                    logger.error(f"Watcher callback error: {e}")
        
        logger.info(f"设置状态: {key}")
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)
    
    def delete(self, key: str, locker_id: Optional[str] = None) -> bool:
        if key in self.locks and self.locks[key] != locker_id:
            return False
        
        if key in self.state:
            del self.state[key]
            return True
        return False
    
    def lock(self, key: str, locker_id: str, timeout: int = 60) -> bool:
        if key in self.locks:
            return False
        self.locks[key] = locker_id
        logger.info(f"锁定状态: {key} by {locker_id}")
        return True
    
    def unlock(self, key: str, locker_id: str) -> bool:
        if self.locks.get(key) == locker_id:
            del self.locks[key]
            logger.info(f"解锁状态: {key}")
            return True
        return False
    
    def watch(self, key: str, callback: callable):
        if key not in self.watchers:
            self.watchers[key] = []
        self.watchers[key].append(callback)
    
    def get_all(self) -> Dict[str, Any]:
        return self.state.copy()
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": "SharedStateManager",
            "total_keys": len(self.state),
            "locked_keys": len(self.locks),
            "watched_keys": len(self.watchers)
        }


__all__ = [
    "NetworkDataSync",
    "SharedStateManager",
    "SyncNode",
    "DataRecord",
    "SyncStatus"
]
