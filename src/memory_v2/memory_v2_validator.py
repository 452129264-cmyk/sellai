#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory V2 写入验证模块
实现写入前校验、写入中监控、写入后验证三个环节，确保记忆数据100%准确可靠。
"""

import hashlib
import json
import logging
import time
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """记忆验证状态枚举"""
    PENDING = "pending"
    WRITING = "writing"
    WRITTEN = "written"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"


class WriteStatus(Enum):
    """写入状态枚举"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class MemoryV2Validator:
    """Memory V2 写入验证器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化验证器
        
        Args:
            db_path: 共享状态库路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化验证相关的数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建记忆验证状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_validation_status (
                memory_id TEXT PRIMARY KEY,
                avatar_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                storage_target TEXT NOT NULL,
                write_status TEXT CHECK(write_status IN ('pending', 'writing', 'written', 'verified', 'failed')),
                verification_status TEXT CHECK(verification_status IN ('pending', 'verifying', 'verified', 'failed')),
                write_timestamp TIMESTAMP,
                verification_timestamp TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''')
        
        # 创建记忆数据校验和表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_data_checksums (
                memory_id TEXT PRIMARY KEY,
                data_hash TEXT NOT NULL,
                original_data TEXT NOT NULL,
                compressed_data BLOB,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (memory_id) REFERENCES memory_validation_status(memory_id)
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memory_avatar 
            ON memory_validation_status(avatar_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memory_status 
            ON memory_validation_status(write_status, verification_status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memory_type 
            ON memory_validation_status(memory_type)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Memory V2 验证数据库初始化完成")
    
    def generate_memory_id(self, avatar_id: str, memory_type: str, timestamp: Optional[str] = None) -> str:
        """
        生成唯一记忆ID
        
        Args:
            avatar_id: 分身ID
            memory_type: 记忆类型
            timestamp: 时间戳（可选）
            
        Returns:
            唯一记忆ID
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        unique_str = f"{avatar_id}_{memory_type}_{timestamp}"
        return hashlib.sha256(unique_str.encode()).hexdigest()[:32]
    
    def calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """
        计算数据哈希值
        
        Args:
            data: 记忆数据
            
        Returns:
            数据哈希值
        """
        # 将数据排序确保一致性
        sorted_data = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def pre_write_validation(self, memory_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        写入前校验
        
        Args:
            memory_data: 记忆数据
            
        Returns:
            (是否通过, 错误信息)
        """
        try:
            # 1. 必填字段检查
            required_fields = ['avatar_id', 'memory_type', 'data']
            for field in required_fields:
                if field not in memory_data:
                    return False, f"缺少必填字段: {field}"
            
            # 2. 数据格式检查
            if not isinstance(memory_data['data'], dict):
                return False, "data字段必须是字典类型"
            
            # 3. 业务规则检查（根据记忆类型）
            memory_type = memory_data['memory_type']
            
            # 情报官记忆检查
            if memory_type == 'intelligence_officer':
                required_data_fields = ['data_source', 'raw_items_count', 'high_margin_items_count']
                for field in required_data_fields:
                    if field not in memory_data['data']:
                        return False, f"情报官记忆缺少字段: {field}"
            
            # 策略师记忆检查
            elif memory_type == 'strategy_30margin':
                required_data_fields = ['opportunity_id', 'initial_margin_estimate', 'validated_margin']
                for field in required_data_fields:
                    if field not in memory_data['data']:
                        return False, f"策略师记忆缺少字段: {field}"
            
            # 文案官记忆检查
            elif memory_type == 'copy_channel_officer':
                required_data_fields = ['target_platform', 'content_template', 'ctr_estimate']
                for field in required_data_fields:
                    if field not in memory_data['data']:
                        return False, f"文案官记忆缺少字段: {field}"
            
            # 执行官记忆检查
            elif memory_type == 'todo_executor':
                required_data_fields = ['task_id', 'task_type', 'priority_assignment']
                for field in required_data_fields:
                    if field not in memory_data['data']:
                        return False, f"执行官记忆缺少字段: {field}"
            
            # 分身处理器记忆检查
            elif memory_type == 'avatar_processor':
                required_data_fields = ['user_id', 'message_type', 'response_strategy']
                for field in required_data_fields:
                    if field not in memory_data['data']:
                        return False, f"分身处理器记忆缺少字段: {field}"
            
            # 4. 数据大小检查（防止过大数据）
            data_size = len(json.dumps(memory_data['data']))
            if data_size > 1024 * 1024:  # 1MB限制
                return False, f"数据过大: {data_size}字节，超过1MB限制"
            
            return True, None
            
        except Exception as e:
            logger.error(f"写入前校验异常: {e}")
            return False, f"校验异常: {str(e)}"
    
    def record_memory_attempt(self, memory_id: str, memory_data: Dict[str, Any], 
                            storage_target: str = "coze_memory") -> bool:
        """
        记录记忆写入尝试
        
        Args:
            memory_id: 记忆ID
            memory_data: 记忆数据
            storage_target: 存储目标
            
        Returns:
            是否成功
        """
        try:
            avatar_id = memory_data['avatar_id']
            memory_type = memory_data['memory_type']
            data_hash = self.calculate_data_hash(memory_data['data'])
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 保存原始数据到校验和表
            cursor.execute('''
                INSERT OR REPLACE INTO memory_data_checksums 
                (memory_id, data_hash, original_data, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                memory_id,
                data_hash,
                json.dumps(memory_data['data'], ensure_ascii=False),
                datetime.now().isoformat()
            ))
            
            # 插入验证状态记录
            cursor.execute('''
                INSERT OR REPLACE INTO memory_validation_status 
                (memory_id, avatar_id, memory_type, data_hash, storage_target,
                 write_status, verification_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory_id,
                avatar_id,
                memory_type,
                data_hash,
                storage_target,
                ValidationStatus.PENDING.value,
                ValidationStatus.PENDING.value,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"记忆尝试记录成功: {memory_id} (avatar: {avatar_id}, type: {memory_type})")
            return True
            
        except Exception as e:
            logger.error(f"记录记忆尝试失败: {e}")
            return False
    
    def update_write_status(self, memory_id: str, status: ValidationStatus, 
                          error_message: Optional[str] = None) -> bool:
        """
        更新写入状态
        
        Args:
            memory_id: 记忆ID
            status: 写入状态
            error_message: 错误信息
            
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            update_fields = ["write_status = ?", "updated_at = ?"]
            params = [status.value, datetime.now().isoformat()]
            
            if status == ValidationStatus.WRITING:
                update_fields.append("write_timestamp = ?")
                params.append(datetime.now().isoformat())
            
            if error_message:
                update_fields.append("error_message = ?")
                params.append(error_message[:500])  # 限制长度
            
            if status == ValidationStatus.FAILED:
                cursor.execute('''
                    UPDATE memory_validation_status 
                    SET retry_count = retry_count + 1 
                    WHERE memory_id = ?
                ''', (memory_id,))
            
            cursor.execute(f'''
                UPDATE memory_validation_status 
                SET {', '.join(update_fields)}
                WHERE memory_id = ?
            ''', params + [memory_id])
            
            conn.commit()
            conn.close()
            
            logger.debug(f"写入状态更新: {memory_id} -> {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新写入状态失败: {e}")
            return False
    
    def update_verification_status(self, memory_id: str, status: ValidationStatus,
                                 error_message: Optional[str] = None) -> bool:
        """
        更新验证状态
        
        Args:
            memory_id: 记忆ID
            status: 验证状态
            error_message: 错误信息
            
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            update_fields = ["verification_status = ?", "updated_at = ?"]
            params = [status.value, datetime.now().isoformat()]
            
            if status == ValidationStatus.VERIFIED:
                update_fields.append("verification_timestamp = ?")
                params.append(datetime.now().isoformat())
            
            if error_message:
                update_fields.append("error_message = ?")
                params.append(error_message[:500])
            
            cursor.execute(f'''
                UPDATE memory_validation_status 
                SET {', '.join(update_fields)}
                WHERE memory_id = ?
            ''', params + [memory_id])
            
            conn.commit()
            conn.close()
            
            logger.debug(f"验证状态更新: {memory_id} -> {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新验证状态失败: {e}")
            return False
    
    def post_write_verification(self, memory_id: str, 
                              read_data_func: callable) -> Tuple[bool, Optional[str]]:
        """
        写入后验证
        
        Args:
            memory_id: 记忆ID
            read_data_func: 读取数据的函数，返回(是否成功, 数据或错误信息)
            
        Returns:
            (是否验证通过, 错误信息)
        """
        try:
            # 1. 从数据库获取原始数据哈希
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT data_hash, original_data FROM memory_data_checksums
                WHERE memory_id = ?
            ''', (memory_id,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False, "找不到记忆数据"
            
            original_hash, original_data_json = result
            original_data = json.loads(original_data_json)
            conn.close()
            
            # 2. 读取刚写入的数据
            success, read_result = read_data_func(memory_id)
            if not success:
                return False, f"读取写入数据失败: {read_result}"
            
            read_data = read_result
            
            # 3. 计算读取数据的哈希值
            read_hash = self.calculate_data_hash(read_data)
            
            # 4. 比对哈希值
            if read_hash != original_hash:
                logger.warning(f"哈希值不匹配: 原始={original_hash[:16]}, 读取={read_hash[:16]}")
                
                # 尝试数据内容比对（更详细的诊断）
                mismatched_fields = []
                for key in set(original_data.keys()) | set(read_data.keys()):
                    if key not in original_data or key not in read_data:
                        mismatched_fields.append(f"{key}: 字段缺失")
                    elif original_data[key] != read_data[key]:
                        mismatched_fields.append(f"{key}: 值不同")
                
                error_msg = f"数据不一致 (哈希不匹配)。差异字段: {mismatched_fields[:5]}"
                return False, error_msg
            
            logger.info(f"写入后验证通过: {memory_id}")
            return True, None
            
        except Exception as e:
            logger.error(f"写入后验证异常: {e}")
            return False, f"验证异常: {str(e)}"
    
    def get_validation_status(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        获取记忆验证状态
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            验证状态信息，失败返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT memory_id, avatar_id, memory_type, storage_target,
                       write_status, verification_status, write_timestamp,
                       verification_timestamp, error_message, retry_count,
                       created_at, updated_at
                FROM memory_validation_status
                WHERE memory_id = ?
            ''', (memory_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
            
        except Exception as e:
            logger.error(f"获取验证状态失败: {e}")
            return None
    
    def get_failed_memories(self, max_retry: int = 3, 
                          hours_ago: int = 24) -> List[Dict[str, Any]]:
        """
        获取验证失败的记忆
        
        Args:
            max_retry: 最大重试次数
            hours_ago: 多少小时内的记录
            
        Returns:
            失败记忆列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            time_threshold = (datetime.now() - timedelta(hours=hours_ago)).isoformat()
            
            cursor.execute('''
                SELECT memory_id, avatar_id, memory_type, storage_target,
                       write_status, verification_status, error_message, retry_count,
                       created_at
                FROM memory_validation_status
                WHERE (write_status = 'failed' OR verification_status = 'failed')
                  AND retry_count < ?
                  AND created_at > ?
                ORDER BY created_at DESC
                LIMIT 100
            ''', (max_retry, time_threshold))
            
            rows = cursor.fetchall()
            conn.close()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"获取失败记忆失败: {e}")
            return []
    
    def cleanup_old_records(self, days_keep: int = 30) -> int:
        """
        清理旧的验证记录
        
        Args:
            days_keep: 保留天数
            
        Returns:
            清理的记录数
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days_keep)).isoformat()
            
            # 删除校验和表记录
            cursor.execute('''
                DELETE FROM memory_data_checksums
                WHERE created_at < ?
                  AND memory_id IN (
                    SELECT memory_id FROM memory_validation_status
                    WHERE verification_status = 'verified'
                      AND created_at < ?
                  )
            ''', (cutoff_date, cutoff_date))
            
            checksums_deleted = cursor.rowcount
            
            # 删除验证状态记录
            cursor.execute('''
                DELETE FROM memory_validation_status
                WHERE verification_status = 'verified'
                  AND created_at < ?
            ''', (cutoff_date,))
            
            status_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"清理旧记录: 校验和={checksums_deleted}, 状态={status_deleted}")
            return checksums_deleted + status_deleted
            
        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")
            return 0


# 简化的验证流程接口
def validate_memory_write(memory_data: Dict[str, Any], 
                         write_func: callable,
                         read_func: callable,
                         storage_target: str = "coze_memory") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    简化的记忆写入验证流程
    
    Args:
        memory_data: 记忆数据
        write_func: 实际写入函数，参数为记忆数据，返回(是否成功, 错误信息)
        read_func: 读取函数，参数为记忆ID，返回(是否成功, 数据或错误信息)
        storage_target: 存储目标
        
    Returns:
        (是否成功, 记忆ID, 错误信息)
    """
    validator = MemoryV2Validator()
    
    # 1. 写入前校验
    valid, error = validator.pre_write_validation(memory_data)
    if not valid:
        logger.error(f"写入前校验失败: {error}")
        return False, None, error
    
    # 2. 生成记忆ID
    memory_id = validator.generate_memory_id(
        memory_data['avatar_id'],
        memory_data['memory_type']
    )
    
    # 3. 记录写入尝试
    if not validator.record_memory_attempt(memory_id, memory_data, storage_target):
        return False, memory_id, "记录记忆尝试失败"
    
    # 4. 更新写入状态为writing
    validator.update_write_status(memory_id, ValidationStatus.WRITING)
    
    # 5. 执行实际写入
    write_success, write_error = write_func(memory_data)
    if not write_success:
        validator.update_write_status(memory_id, ValidationStatus.FAILED, write_error)
        return False, memory_id, f"写入失败: {write_error}"
    
    # 6. 更新写入状态为written
    validator.update_write_status(memory_id, ValidationStatus.WRITTEN)
    
    # 7. 更新验证状态为verifying
    validator.update_verification_status(memory_id, ValidationStatus.VERIFYING)
    
    # 8. 写入后验证
    def read_wrapper(mid: str) -> Tuple[bool, Any]:
        return read_func(mid)
    
    verify_success, verify_error = validator.post_write_verification(memory_id, read_wrapper)
    if not verify_success:
        validator.update_verification_status(memory_id, ValidationStatus.FAILED, verify_error)
        return False, memory_id, f"验证失败: {verify_error}"
    
    # 9. 更新验证状态为verified
    validator.update_verification_status(memory_id, ValidationStatus.VERIFIED)
    
    logger.info(f"记忆写入验证完成: {memory_id}")
    return True, memory_id, None


if __name__ == "__main__":
    # 测试代码
    print("Memory V2 验证模块测试")
    
    # 创建测试数据
    test_data = {
        "avatar_id": "avatar_test_001",
        "memory_type": "intelligence_officer",
        "data": {
            "data_source": "TikTok",
            "raw_items_count": 150,
            "high_margin_items_count": 45,
            "filter_reasons": ["成本过高", "竞争激烈"],
            "success_rate": 0.85,
            "estimated_opportunity_value": 12500.0
        }
    }
    
    # 测试写入前校验
    validator = MemoryV2Validator()
    valid, error = validator.pre_write_validation(test_data)
    print(f"写入前校验: {valid}, 错误: {error}")
    
    # 测试数据哈希计算
    data_hash = validator.calculate_data_hash(test_data['data'])
    print(f"数据哈希: {data_hash[:16]}...")
    
    # 测试记忆ID生成
    memory_id = validator.generate_memory_id(test_data['avatar_id'], test_data['memory_type'])
    print(f"生成的记忆ID: {memory_id}")
    
    print("测试完成")