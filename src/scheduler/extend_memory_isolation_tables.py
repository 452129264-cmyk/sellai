#!/usr/bin/env python3
"""
扩展记忆隔离系统数据库表
在现有共享状态库基础上添加记忆隔离相关表结构
"""

import sqlite3
import sys
import os
import json
from typing import Optional, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def extend_memory_isolation_tables(db_path: str = "data/shared_state/state.db"):
    """
    扩展记忆隔离系统数据库表
    
    参数：
        db_path: 数据库文件路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("开始扩展记忆隔离系统数据库表...")
        
        # 1. user_memory_isolation 表：用户级记忆隔离策略
        print("创建 user_memory_isolation 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memory_isolation (
                isolation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                avatar_id TEXT NOT NULL,
                memory_space_id TEXT NOT NULL,
                access_permission TEXT NOT NULL CHECK(access_permission IN (
                    'read_only', 'read_write', 'admin', 'none'
                )),
                encryption_key_hash TEXT,  -- 加密密钥的哈希值（用于验证）
                isolation_level TEXT NOT NULL DEFAULT 'strict' CHECK(isolation_level IN (
                    'strict', 'relaxed', 'shared'
                )),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                metadata TEXT,  -- JSON格式：{"auto_cleanup_days": 30, "backup_enabled": true, ...}
                UNIQUE(user_id, avatar_id, memory_space_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (avatar_id) REFERENCES avatar_capability_profiles(avatar_id)
            )
        """)
        
        # 2. memory_sharing_channel 表：安全记忆共享通道
        print("创建 memory_sharing_channel 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_sharing_channel (
                channel_id TEXT PRIMARY KEY,
                source_avatar_id TEXT NOT NULL,
                target_avatar_id TEXT NOT NULL,
                sharing_content_type TEXT NOT NULL CHECK(sharing_content_type IN (
                    'memory_fragment', 'knowledge_base', 'task_history', 'user_preference'
                )),
                permission_level TEXT NOT NULL CHECK(permission_level IN (
                    'read_only', 'read_write', 'forward_allowed', 'admin'
                )),
                encryption_key TEXT,  -- 加密共享内容的对称密钥（加密存储）
                is_encrypted BOOLEAN NOT NULL DEFAULT 1,
                shared_data_hash TEXT NOT NULL,  -- 共享内容的哈希值
                shared_metadata TEXT NOT NULL,  -- JSON格式：包含描述、标签等
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                valid_until TIMESTAMP,
                max_access_count INTEGER DEFAULT 0,  -- 0表示无限制
                current_access_count INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN (
                    'active', 'expired', 'revoked', 'suspended'
                )),
                revocation_reason TEXT,
                created_by TEXT NOT NULL,  -- 创建者用户ID
                audit_trail TEXT,  -- JSON数组：记录所有访问日志ID
                FOREIGN KEY (source_avatar_id) REFERENCES avatar_capability_profiles(avatar_id),
                FOREIGN KEY (target_avatar_id) REFERENCES avatar_capability_profiles(avatar_id),
                FOREIGN KEY (created_by) REFERENCES users(user_id)
            )
        """)
        
        # 3. memory_access_log 表：记忆访问操作日志
        print("创建 memory_access_log 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_access_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                avatar_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                operation_type TEXT NOT NULL CHECK(operation_type IN (
                    'read', 'write', 'update', 'delete', 'share', 'unshare', 
                    'encrypt', 'decrypt', 'validate', 'cleanup'
                )),
                target_memory_space TEXT NOT NULL,
                target_memory_id TEXT,  -- 具体记忆ID（可选）
                resource_type TEXT CHECK(resource_type IN (
                    'user_memory_isolation', 'memory_sharing_channel', 
                    'memory_data', 'validation_status', 'index_entry'
                )),
                result_status TEXT NOT NULL CHECK(result_status IN (
                    'success', 'failure', 'partial', 'unauthorized', 'timeout'
                )),
                error_message TEXT,
                ip_address TEXT,
                user_agent TEXT,
                request_id TEXT UNIQUE,  -- 唯一请求标识符
                processing_time_ms INTEGER,
                data_size_bytes INTEGER,
                encrypted_access BOOLEAN DEFAULT 0,
                audit_signature TEXT,  -- 审计签名（防止篡改）
                metadata TEXT,  -- JSON格式：包含详细操作上下文
                FOREIGN KEY (avatar_id) REFERENCES avatar_capability_profiles(avatar_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # 4. memory_space 表：记忆空间定义（可选，用于更细粒度控制）
        print("创建 memory_space 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_space (
                memory_space_id TEXT PRIMARY KEY,
                space_name TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                space_type TEXT NOT NULL CHECK(space_type IN (
                    'personal', 'project', 'team', 'organization', 'public'
                )),
                description TEXT,
                default_permission TEXT NOT NULL DEFAULT 'none' CHECK(default_permission IN (
                    'read_only', 'read_write', 'admin', 'none'
                )),
                encryption_enabled BOOLEAN NOT NULL DEFAULT 1,
                retention_days INTEGER DEFAULT 365,  -- 保留天数
                max_size_mb INTEGER DEFAULT 1024,  -- 最大大小（MB）
                current_size_mb REAL DEFAULT 0.0,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                metadata TEXT,  -- JSON格式
                FOREIGN KEY (owner_user_id) REFERENCES users(user_id)
            )
        """)
        
        # 创建索引
        print("创建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_isolation_user ON user_memory_isolation(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_isolation_avatar ON user_memory_isolation(avatar_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_isolation_space ON user_memory_isolation(memory_space_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_isolation_permission ON user_memory_isolation(access_permission)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sharing_channel_source ON memory_sharing_channel(source_avatar_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sharing_channel_target ON memory_sharing_channel(target_avatar_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sharing_channel_status ON memory_sharing_channel(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sharing_channel_validity ON memory_sharing_channel(valid_until)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_log_avatar ON memory_access_log(avatar_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_log_user ON memory_access_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_log_operation ON memory_access_log(operation_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_log_timestamp ON memory_access_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_log_status ON memory_access_log(result_status)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_space_owner ON memory_space(owner_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_space_type ON memory_space(space_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_space_active ON memory_space(is_active)")
        
        # 初始化默认记忆空间（每个用户一个个人空间）
        print("初始化默认记忆空间...")
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        
        for (user_id,) in users:
            personal_space_id = f"personal_{user_id}"
            cursor.execute("""
                INSERT OR IGNORE INTO memory_space 
                (memory_space_id, space_name, owner_user_id, space_type, description, default_permission)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                personal_space_id,
                "个人记忆空间",
                user_id,
                "personal",
                f"用户 {user_id} 的默认个人记忆空间",
                "read_write"
            ))
            
            # 为用户的默认分身添加访问权限
            cursor.execute("""
                SELECT avatar_id FROM avatar_capability_profiles 
                WHERE avatar_id LIKE ? || '_%' OR avatar_id LIKE 'default_%'
            """, (user_id,))
            avatars = cursor.fetchall()
            
            for (avatar_id,) in avatars:
                cursor.execute("""
                    INSERT OR IGNORE INTO user_memory_isolation 
                    (user_id, avatar_id, memory_space_id, access_permission, isolation_level)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    avatar_id,
                    personal_space_id,
                    "read_write",
                    "strict"
                ))
        
        conn.commit()
        print("记忆隔离系统数据库表扩展完成！")
        
        # 显示创建的表
        print("\n已创建的表：")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN (
                'user_memory_isolation', 'memory_sharing_channel', 
                'memory_access_log', 'memory_space'
            )
        """)
        for table in cursor.fetchall():
            print(f"  - {table[0]}")
            
        print("\n索引：")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_memory_%'
        """)
        for idx in cursor.fetchall():
            print(f"  - {idx[0]}")
        
    except Exception as e:
        print(f"扩展失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """主函数"""
    try:
        # 检查数据库文件是否存在
        if not os.path.exists("data/shared_state/state.db"):
            print("错误：共享状态库不存在，请先运行 init_scheduler_tables.py")
            sys.exit(1)
        
        extend_memory_isolation_tables()
        
        print("\n扩展成功！")
        print("数据库路径: data/shared_state/state.db")
        
    except Exception as e:
        print(f"扩展过程出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()