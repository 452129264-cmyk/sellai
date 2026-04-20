#!/usr/bin/env python3
"""
记忆隔离系统核心模块
提供分身级记忆隔离机制与安全共享体系
"""

import sqlite3
import json
import hashlib
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import base64
import os
import hmac

class AccessPermission(Enum):
    """访问权限枚举"""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    NONE = "none"

class IsolationLevel(Enum):
    """隔离级别枚举"""
    STRICT = "strict"      # 严格隔离：仅能访问分配给该分身的记忆空间
    RELAXED = "relaxed"    # 宽松隔离：可访问同一用户的其他分身的记忆空间
    SHARED = "shared"      # 共享隔离：可跨用户访问（需特别授权）

class SharingContentType(Enum):
    """共享内容类型枚举"""
    MEMORY_FRAGMENT = "memory_fragment"    # 记忆片段
    KNOWLEDGE_BASE = "knowledge_base"      # 知识库
    TASK_HISTORY = "task_history"          # 任务历史
    USER_PREFERENCE = "user_preference"    # 用户偏好

class PermissionLevel(Enum):
    """权限级别枚举"""
    READ_ONLY = "read_only"          # 只读
    READ_WRITE = "read_write"        # 可读写
    FORWARD_ALLOWED = "forward_allowed"  # 可转发
    ADMIN = "admin"                  # 管理员

class OperationType(Enum):
    """操作类型枚举"""
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    SHARE = "share"
    UNSHARE = "unshare"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    VALIDATE = "validate"
    CLEANUP = "cleanup"

class ResultStatus(Enum):
    """结果状态枚举"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNAUTHORIZED = "unauthorized"
    TIMEOUT = "timeout"

@dataclass
class MemoryIsolationRecord:
    """记忆隔离记录"""
    isolation_id: Optional[int] = None
    user_id: str = ""
    avatar_id: str = ""
    memory_space_id: str = ""
    access_permission: AccessPermission = AccessPermission.NONE
    encryption_key_hash: Optional[str] = None
    isolation_level: IsolationLevel = IsolationLevel.STRICT
    created_at: datetime = None
    updated_at: datetime = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class MemorySpace:
    """记忆空间"""
    memory_space_id: str = ""
    space_name: str = ""
    owner_user_id: str = ""
    space_type: str = "personal"
    description: str = ""
    default_permission: AccessPermission = AccessPermission.NONE
    encryption_enabled: bool = True
    retention_days: int = 365
    max_size_mb: int = 1024
    current_size_mb: float = 0.0
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    deleted_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SharingChannel:
    """共享通道"""
    channel_id: str = ""
    source_avatar_id: str = ""
    target_avatar_id: str = ""
    sharing_content_type: SharingContentType = SharingContentType.MEMORY_FRAGMENT
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    encryption_key: Optional[str] = None
    is_encrypted: bool = True
    shared_data_hash: str = ""
    shared_metadata: Dict[str, Any] = None
    created_at: datetime = None
    valid_from: datetime = None
    valid_until: Optional[datetime] = None
    max_access_count: int = 0
    current_access_count: int = 0
    status: str = "active"
    revocation_reason: Optional[str] = None
    created_by: str = ""
    audit_trail: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.valid_from is None:
            self.valid_from = datetime.now()
        if self.shared_metadata is None:
            self.shared_metadata = {}
        if self.audit_trail is None:
            self.audit_trail = []

@dataclass
class AccessLog:
    """访问日志"""
    log_id: Optional[int] = None
    timestamp: datetime = None
    avatar_id: str = ""
    user_id: str = ""
    operation_type: OperationType = OperationType.READ
    target_memory_space: str = ""
    target_memory_id: Optional[str] = None
    resource_type: Optional[str] = None
    result_status: ResultStatus = ResultStatus.SUCCESS
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: str = ""
    processing_time_ms: Optional[int] = None
    data_size_bytes: Optional[int] = None
    encrypted_access: bool = False
    audit_signature: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
        if not self.request_id:
            self.request_id = str(uuid.uuid4())

class MemoryEncryptionService:
    """记忆加密服务"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        初始化加密服务
        
        参数：
            master_key: 主密钥，如果为None则从环境变量获取
        """
        self.master_key = master_key or os.getenv("MEMORY_ENCRYPTION_MASTER_KEY", "default_master_key_placeholder")
        self.key_version = "v1"
        
    def generate_key(self) -> bytes:
        """生成随机AES-256密钥"""
        return os.urandom(32)  # 256位
    
    def generate_iv(self) -> bytes:
        """生成随机初始化向量"""
        return os.urandom(16)  # 128位
    
    def encrypt_data(self, plaintext: bytes, key: bytes) -> Tuple[bytes, bytes]:
        """
        加密数据
        
        参数：
            plaintext: 明文数据
            key: 加密密钥
            
        返回：
            (加密数据, 初始化向量)
        """
        # 注意：实际生产环境应使用 cryptography 库的AES实现
        # 这里使用模拟实现，实际部署需要替换为真正的加密
        iv = self.generate_iv()
        # 模拟加密：实际应为 AES-CBC 加密
        # 为简化实现，这里返回模拟结果
        # 生产环境替换为：cipher = AES.new(key, AES.MODE_CBC, iv)
        #                ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
        simulated_ciphertext = plaintext + b"_encrypted_" + key[:8]
        return simulated_ciphertext, iv
    
    def decrypt_data(self, ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
        """
        解密数据
        
        参数：
            ciphertext: 加密数据
            key: 解密密钥
            iv: 初始化向量
            
        返回：
            明文数据
        """
        # 模拟解密：实际应为 AES-CBC 解密
        # 生产环境替换为：cipher = AES.new(key, AES.MODE_CBC, iv)
        #                plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
        if ciphertext.endswith(b"_encrypted_" + key[:8]):
            return ciphertext[:-len(b"_encrypted_" + key[:8])]
        return ciphertext
    
    def hash_key(self, key: bytes) -> str:
        """计算密钥哈希"""
        return hashlib.sha256(key).hexdigest()
    
    def encrypt_key(self, key: bytes) -> str:
        """使用主密钥加密数据密钥"""
        # 模拟加密：实际应使用HMAC或KMS
        combined = key + self.master_key.encode()
        return base64.b64encode(hashlib.sha256(combined).digest()).decode()
    
    def decrypt_key(self, encrypted_key: str) -> bytes:
        """使用主密钥解密数据密钥"""
        # 模拟解密：实际应使用HMAC或KMS
        # 这里无法真正解密，返回模拟密钥
        return os.urandom(32)

class MemoryIsolationManager:
    """记忆隔离管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self.encryption_service = MemoryEncryptionService()
        
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def verify_access(self, avatar_id: str, memory_space_id: str, 
                     operation_type: OperationType) -> Tuple[bool, Optional[str]]:
        """
        验证分身对记忆空间的访问权限
        
        参数：
            avatar_id: 分身ID
            memory_space_id: 记忆空间ID
            operation_type: 操作类型
            
        返回：
            (是否允许访问, 错误信息)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. 获取用户ID
            cursor.execute("SELECT user_id FROM user_avatar_relationships WHERE avatar_id = ?", (avatar_id,))
            avatar_result = cursor.fetchone()
            if not avatar_result:
                return False, f"分身 {avatar_id} 不存在"
            user_id = avatar_result[0]
            
            # 2. 查询记忆隔离记录
            cursor.execute("""
                SELECT access_permission, isolation_level, expires_at 
                FROM user_memory_isolation 
                WHERE user_id = ? AND avatar_id = ? AND memory_space_id = ?
            """, (user_id, avatar_id, memory_space_id))
            
            isolation_result = cursor.fetchone()
            
            # 3. 如果记录不存在，检查是否为默认个人空间
            if not isolation_result:
                # 检查是否为该用户的个人空间
                cursor.execute("""
                    SELECT owner_user_id FROM memory_space 
                    WHERE memory_space_id = ? AND space_type = 'personal'
                """, (memory_space_id,))
                space_result = cursor.fetchone()
                
                if space_result and space_result[0] == user_id:
                    # 是用户的个人空间，默认允许读写
                    access_permission = AccessPermission.READ_WRITE.value
                    isolation_level = IsolationLevel.STRICT.value
                else:
                    return False, f"分身 {avatar_id} 无权限访问记忆空间 {memory_space_id}"
            else:
                access_permission, isolation_level_str, expires_at = isolation_result
                isolation_level = IsolationLevel(isolation_level_str)
                
                # 检查有效期
                if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                    return False, f"访问权限已过期"
            
            # 4. 验证操作权限
            permission = AccessPermission(access_permission)
            operation_allowed = self._check_operation_permission(permission, operation_type)
            
            if not operation_allowed:
                return False, f"权限不足: {permission.value} 不允许 {operation_type.value} 操作"
            
            # 5. 验证隔离级别
            if isolation_level == IsolationLevel.STRICT:
                # 严格隔离：仅允许访问分配给该分身的记忆空间
                # 已通过前面的查询验证
                pass
            elif isolation_level == IsolationLevel.RELAXED:
                # 宽松隔离：允许访问同一用户的其他分身的记忆空间
                # 检查记忆空间是否属于同一用户
                cursor.execute("""
                    SELECT owner_user_id FROM memory_space 
                    WHERE memory_space_id = ?
                """, (memory_space_id,))
                space_result = cursor.fetchone()
                if not space_result or space_result[0] != user_id:
                    return False, f"宽松隔离仅允许访问同一用户的记忆空间"
            elif isolation_level == IsolationLevel.SHARED:
                # 共享隔离：需额外检查跨用户授权
                cursor.execute("""
                    SELECT 1 FROM user_memory_isolation 
                    WHERE user_id = ? AND avatar_id = ? AND memory_space_id = ? 
                    AND access_permission != 'none'
                """, (user_id, avatar_id, memory_space_id))
                if not cursor.fetchone():
                    return False, f"未获得跨用户访问授权"
            
            return True, None
            
        except Exception as e:
            return False, f"验证失败: {str(e)}"
        finally:
            conn.close()
    
    def _check_operation_permission(self, permission: AccessPermission, 
                                   operation_type: OperationType) -> bool:
        """
        检查操作权限
        
        返回：
            是否允许操作
        """
        permission_map = {
            AccessPermission.READ_ONLY: [OperationType.READ],
            AccessPermission.READ_WRITE: [OperationType.READ, OperationType.WRITE, OperationType.UPDATE],
            AccessPermission.ADMIN: [OperationType.READ, OperationType.WRITE, OperationType.UPDATE, 
                                   OperationType.DELETE, OperationType.SHARE, OperationType.UNSHARE,
                                   OperationType.CLEANUP],
            AccessPermission.NONE: []
        }
        
        return operation_type in permission_map.get(permission, [])
    
    def create_isolation_record(self, record: MemoryIsolationRecord) -> bool:
        """
        创建记忆隔离记录
        
        参数：
            record: 记忆隔离记录
            
        返回：
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO user_memory_isolation 
                (user_id, avatar_id, memory_space_id, access_permission, 
                 encryption_key_hash, isolation_level, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.user_id,
                record.avatar_id,
                record.memory_space_id,
                record.access_permission.value,
                record.encryption_key_hash,
                record.isolation_level.value,
                record.expires_at.isoformat() if record.expires_at else None,
                json.dumps(record.metadata) if record.metadata else None
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"创建记忆隔离记录失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_memory_spaces(self, user_id: str) -> List[MemorySpace]:
        """
        获取用户的所有记忆空间
        
        参数：
            user_id: 用户ID
            
        返回：
            记忆空间列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM memory_space 
                WHERE owner_user_id = ? AND is_active = 1
                ORDER BY created_at DESC
            """, (user_id,))
            
            spaces = []
            for row in cursor.fetchall():
                space = MemorySpace(
                    memory_space_id=row[0],
                    space_name=row[1],
                    owner_user_id=row[2],
                    space_type=row[3],
                    description=row[4],
                    default_permission=AccessPermission(row[5]),
                    encryption_enabled=bool(row[6]),
                    retention_days=row[7],
                    max_size_mb=row[8],
                    current_size_mb=row[9],
                    is_active=bool(row[10]),
                    created_at=datetime.fromisoformat(row[11]),
                    updated_at=datetime.fromisoformat(row[12]),
                    deleted_at=datetime.fromisoformat(row[13]) if row[13] else None,
                    metadata=json.loads(row[14]) if row[14] else {}
                )
                spaces.append(space)
            
            return spaces
            
        except Exception as e:
            print(f"获取用户记忆空间失败: {e}")
            return []
        finally:
            conn.close()

class SharingChannelManager:
    """共享通道管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self.encryption_service = MemoryEncryptionService()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def create_sharing_channel(self, channel: SharingChannel) -> Optional[str]:
        """
        创建共享通道
        
        参数：
            channel: 共享通道配置
            
        返回：
            通道ID，失败返回None
        """
        if not channel.channel_id:
            channel.channel_id = f"share_{uuid.uuid4().hex[:16]}"
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 验证源分身是否存在
            cursor.execute("SELECT 1 FROM avatar_capability_profiles WHERE avatar_id = ?", 
                         (channel.source_avatar_id,))
            if not cursor.fetchone():
                print(f"源分身 {channel.source_avatar_id} 不存在")
                return None
            
            # 验证目标分身是否存在
            cursor.execute("SELECT 1 FROM avatar_capability_profiles WHERE avatar_id = ?", 
                         (channel.target_avatar_id,))
            if not cursor.fetchone():
                print(f"目标分身 {channel.target_avatar_id} 不存在")
                return None
            
            # 插入记录
            cursor.execute("""
                INSERT INTO memory_sharing_channel 
                (channel_id, source_avatar_id, target_avatar_id, sharing_content_type,
                 permission_level, encryption_key, is_encrypted, shared_data_hash,
                 shared_metadata, created_at, valid_from, valid_until, max_access_count,
                 current_access_count, status, created_by, audit_trail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                channel.channel_id,
                channel.source_avatar_id,
                channel.target_avatar_id,
                channel.sharing_content_type.value,
                channel.permission_level.value,
                channel.encryption_key,
                1 if channel.is_encrypted else 0,
                channel.shared_data_hash,
                json.dumps(channel.shared_metadata),
                channel.created_at.isoformat(),
                channel.valid_from.isoformat(),
                channel.valid_until.isoformat() if channel.valid_until else None,
                channel.max_access_count,
                channel.current_access_count,
                channel.status,
                channel.created_by,
                json.dumps(channel.audit_trail)
            ))
            
            conn.commit()
            return channel.channel_id
            
        except Exception as e:
            conn.rollback()
            print(f"创建共享通道失败: {e}")
            return None
        finally:
            conn.close()
    
    def access_shared_content(self, channel_id: str, avatar_id: str) -> Optional[Dict[str, Any]]:
        """
        访问共享内容
        
        参数：
            channel_id: 通道ID
            avatar_id: 访问者分身ID
            
        返回：
            共享内容，失败返回None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 查询通道信息
            cursor.execute("""
                SELECT * FROM memory_sharing_channel 
                WHERE channel_id = ? AND status = 'active'
            """, (channel_id,))
            
            channel_data = cursor.fetchone()
            if not channel_data:
                print(f"共享通道 {channel_id} 不存在或已失效")
                return None
            
            # 检查访问者是否为授权目标
            target_avatar_id = channel_data[2]  # target_avatar_id字段
            if avatar_id != target_avatar_id:
                print(f"分身 {avatar_id} 无权限访问通道 {channel_id}")
                return None
            
            # 检查有效期
            valid_until = channel_data[11]  # valid_until字段
            if valid_until and datetime.fromisoformat(valid_until) < datetime.now():
                print(f"共享通道 {channel_id} 已过期")
                return None
            
            # 检查访问次数限制
            max_access_count = channel_data[12]  # max_access_count字段
            current_access_count = channel_data[13]  # current_access_count字段
            if max_access_count > 0 and current_access_count >= max_access_count:
                print(f"共享通道 {channel_id} 访问次数已达上限")
                return None
            
            # 更新访问计数
            cursor.execute("""
                UPDATE memory_sharing_channel 
                SET current_access_count = current_access_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE channel_id = ?
            """, (channel_id,))
            
            # 获取共享内容（模拟）
            shared_content = {
                "channel_id": channel_id,
                "source_avatar_id": channel_data[1],  # source_avatar_id
                "content_type": channel_data[3],      # sharing_content_type
                "permission_level": channel_data[4],  # permission_level
                "shared_metadata": json.loads(channel_data[8]) if channel_data[8] else {},
                "access_time": datetime.now().isoformat(),
                "remaining_access": max_access_count - (current_access_count + 1) if max_access_count > 0 else "unlimited"
            }
            
            conn.commit()
            return shared_content
            
        except Exception as e:
            conn.rollback()
            print(f"访问共享内容失败: {e}")
            return None
        finally:
            conn.close()

class AccessAuditLogger:
    """访问审计日志器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def log_access(self, log: AccessLog) -> bool:
        """
        记录访问日志
        
        参数：
            log: 访问日志
            
        返回：
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 生成审计签名（模拟）
            audit_data = f"{log.avatar_id}|{log.operation_type.value}|{log.target_memory_space}|{log.timestamp.isoformat()}"
            audit_signature = hashlib.sha256(audit_data.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO memory_access_log 
                (timestamp, avatar_id, user_id, operation_type, target_memory_space,
                 target_memory_id, resource_type, result_status, error_message,
                 ip_address, user_agent, request_id, processing_time_ms,
                 data_size_bytes, encrypted_access, audit_signature, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log.timestamp.isoformat(),
                log.avatar_id,
                log.user_id,
                log.operation_type.value,
                log.target_memory_space,
                log.target_memory_id,
                log.resource_type,
                log.result_status.value,
                log.error_message,
                log.ip_address,
                log.user_agent,
                log.request_id,
                log.processing_time_ms,
                log.data_size_bytes,
                1 if log.encrypted_access else 0,
                audit_signature,
                json.dumps(log.metadata) if log.metadata else None
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"记录访问日志失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_access_logs(self, avatar_id: Optional[str] = None, 
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       limit: int = 100) -> List[AccessLog]:
        """
        查询访问日志
        
        参数：
            avatar_id: 分身ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            limit: 返回条数限制
            
        返回：
            访问日志列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM memory_access_log WHERE 1=1"
            params = []
            
            if avatar_id:
                query += " AND avatar_id = ?"
                params.append(avatar_id)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            logs = []
            for row in cursor.fetchall():
                log = AccessLog(
                    log_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    avatar_id=row[2],
                    user_id=row[3],
                    operation_type=OperationType(row[4]),
                    target_memory_space=row[5],
                    target_memory_id=row[6],
                    resource_type=row[7],
                    result_status=ResultStatus(row[8]),
                    error_message=row[9],
                    ip_address=row[10],
                    user_agent=row[11],
                    request_id=row[12],
                    processing_time_ms=row[13],
                    data_size_bytes=row[14],
                    encrypted_access=bool(row[15]),
                    audit_signature=row[16],
                    metadata=json.loads(row[17]) if row[17] else {}
                )
                logs.append(log)
            
            return logs
            
        except Exception as e:
            print(f"查询访问日志失败: {e}")
            return []
        finally:
            conn.close()

# 全局实例
memory_isolation_manager = MemoryIsolationManager()
sharing_channel_manager = SharingChannelManager()
access_audit_logger = AccessAuditLogger()

if __name__ == "__main__":
    # 测试代码
    print("记忆隔离系统核心模块测试...")
    
    # 测试权限验证
    allowed, error = memory_isolation_manager.verify_access(
        avatar_id="test_avatar",
        memory_space_id="personal_test_user",
        operation_type=OperationType.READ
    )
    
    print(f"权限验证结果: allowed={allowed}, error={error}")
    
    # 测试记忆空间查询
    spaces = memory_isolation_manager.get_user_memory_spaces("test_user")
    print(f"用户记忆空间数量: {len(spaces)}")
    
    print("测试完成！")