#!/usr/bin/env python3
"""
权限管控模块
负责用户权限管理、社交边界控制和隐私保护功能

主要功能：
1. 社交边界控制：用户自主关闭AI主动私聊、隐藏商机推送、设置接收消息时段
2. 隐私保护机制：消息阅后即焚、聊天记录自动清理、敏感信息过滤
3. 权限分级管理：支持不同用户角色（管理员、普通用户、访客）的差异化权限
4. 安全审计集成：权限操作记录集成到现有安全审计系统
"""

import sqlite3
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from enum import Enum

# 导入现有安全审计系统
try:
    from src.undercover_auditor import UndercoverAuditor, SecurityLevel
    HAS_UNDERCOVER = True
except ImportError:
    HAS_UNDERCOVER = False
    print("警告: 未找到undercover_auditor，安全审计功能将受限")

# 配置日志
logger = logging.getLogger(__name__)

class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"  # 管理员：拥有所有权限
    USER = "user"    # 普通用户：默认权限
    GUEST = "guest"  # 访客：受限权限

class PermissionType(Enum):
    """权限类型枚举"""
    # 社交边界控制
    AI_INITIATED_CHAT = "ai_initiated_chat"  # 允许AI主动发起聊天
    SHOW_OPPORTUNITY_PUSH = "show_opportunity_push"  # 显示商机推送
    AI_AI_COLLABORATION_VISIBILITY = "ai_ai_collaboration_visibility"  # 显示AI间协作
    
    # 隐私保护
    SELF_DESTRUCT_MESSAGES = "self_destruct_messages"  # 消息阅后即焚
    AUTO_CLEAN_CHAT_HISTORY = "auto_clean_chat_history"  # 自动清理聊天记录
    SENSITIVE_INFO_FILTERING = "sensitive_info_filtering"  # 敏感信息过滤
    
    # 系统管理
    MANAGE_USERS = "manage_users"  # 管理用户
    VIEW_AUDIT_LOGS = "view_audit_logs"  # 查看审计日志
    SYSTEM_CONFIG = "system_config"  # 系统配置
    CREATE_AI_AVATARS = "create_ai_avatars"  # 创建AI分身

class MessageTimeSlot:
    """消息接收时段管理"""
    
    def __init__(self, start_hour: int = 8, start_minute: int = 0,
                 end_hour: int = 22, end_minute: int = 0):
        self.start_time = (start_hour, start_minute)
        self.end_time = (end_hour, end_minute)
    
    def is_within_time_slot(self, timestamp: datetime = None) -> bool:
        """检查给定时间是否在允许的时段内"""
        if timestamp is None:
            timestamp = datetime.now()
        
        current_time = (timestamp.hour, timestamp.minute)
        
        # 处理跨天情况（如22:00-08:00）
        if self.start_time > self.end_time:
            # 跨天时段，如晚上22:00到次日08:00
            return current_time >= self.start_time or current_time <= self.end_time
        else:
            # 当天时段，如08:00-22:00
            return self.start_time <= current_time <= self.end_time
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "start_hour": self.start_time[0],
            "start_minute": self.start_time[1],
            "end_hour": self.end_time[0],
            "end_minute": self.end_time[1]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MessageTimeSlot':
        """从字典创建实例"""
        return cls(
            start_hour=data.get("start_hour", 8),
            start_minute=data.get("start_minute", 0),
            end_hour=data.get("end_hour", 22),
            end_minute=data.get("end_minute", 0)
        )

class PermissionManager:
    """权限管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化权限管理器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        
        # 初始化安全审计系统（如果可用）
        self.auditor = None
        if HAS_UNDERCOVER:
            try:
                self.auditor = UndercoverAuditor(db_path)
                logger.info("安全审计系统初始化成功")
            except Exception as e:
                logger.error(f"安全审计系统初始化失败: {e}")
        
        # 初始化数据库表
        self._init_permission_tables()
        
        # 加载角色权限配置
        self.role_permissions = self._load_role_permissions()
        
        logger.info("权限管理器初始化完成")
    
    def _init_permission_tables(self):
        """初始化权限相关数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 1. 创建或扩展users表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT,
                        email TEXT,
                        registration_time TIMESTAMP,
                        credits_balance INTEGER DEFAULT 0,
                        invitation_code TEXT,
                        invited_by TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 检查并添加role字段（如果不存在）
                cursor.execute("""
                    SELECT COUNT(*) FROM pragma_table_info('users') 
                    WHERE name='role'
                """)
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'
                    """)
                    logger.info("users表已添加role字段")
                
                # 2. 创建user_privacy_settings表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_privacy_settings (
                        user_id TEXT PRIMARY KEY,
                        allow_ai_initiated_chat BOOLEAN DEFAULT 1,
                        show_opportunity_push BOOLEAN DEFAULT 1,
                        allow_ai_ai_collaboration_visibility BOOLEAN DEFAULT 1,
                        auto_add_ai_friends BOOLEAN DEFAULT 1,
                        receive_message_start_hour INTEGER DEFAULT 8,
                        receive_message_start_minute INTEGER DEFAULT 0,
                        receive_message_end_hour INTEGER DEFAULT 22,
                        receive_message_end_minute INTEGER DEFAULT 0,
                        message_retention_days INTEGER DEFAULT 30,
                        self_destruct_enabled BOOLEAN DEFAULT 0,
                        self_destruct_seconds INTEGER DEFAULT 60,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 3. 创建角色权限表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS role_permissions (
                        role TEXT NOT NULL,
                        permission_type TEXT NOT NULL,
                        granted BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (role, permission_type)
                    )
                """)
                
                # 4. 创建消息自毁记录表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS self_destruct_messages (
                        message_id TEXT PRIMARY KEY,
                        room_id TEXT NOT NULL,
                        sender_id TEXT NOT NULL,
                        self_destruct_seconds INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        destruct_at TIMESTAMP,
                        is_destructed BOOLEAN DEFAULT 0
                    )
                """)
                
                conn.commit()
                logger.info("权限数据库表初始化完成")
                
        except Exception as e:
            logger.error(f"初始化权限数据库表失败: {e}")
            raise
    
    def _load_role_permissions(self) -> Dict[str, Dict[str, bool]]:
        """加载角色权限配置"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role, permission_type, granted FROM role_permissions")
                
                role_permissions = {}
                for row in cursor.fetchall():
                    role, permission_type, granted = row
                    if role not in role_permissions:
                        role_permissions[role] = {}
                    role_permissions[role][permission_type] = bool(granted)
                
                # 如果没有配置，则创建默认权限配置
                if not role_permissions:
                    role_permissions = self._create_default_role_permissions()
                
                return role_permissions
                
        except Exception as e:
            logger.error(f"加载角色权限配置失败: {e}")
            return self._create_default_role_permissions()
    
    def _create_default_role_permissions(self) -> Dict[str, Dict[str, bool]]:
        """创建默认角色权限配置"""
        default_permissions = {
            UserRole.ADMIN.value: {
                PermissionType.AI_INITIATED_CHAT.value: True,
                PermissionType.SHOW_OPPORTUNITY_PUSH.value: True,
                PermissionType.AI_AI_COLLABORATION_VISIBILITY.value: True,
                PermissionType.SELF_DESTRUCT_MESSAGES.value: True,
                PermissionType.AUTO_CLEAN_CHAT_HISTORY.value: True,
                PermissionType.SENSITIVE_INFO_FILTERING.value: True,
                PermissionType.MANAGE_USERS.value: True,
                PermissionType.VIEW_AUDIT_LOGS.value: True,
                PermissionType.SYSTEM_CONFIG.value: True,
                PermissionType.CREATE_AI_AVATARS.value: True,
            },
            UserRole.USER.value: {
                PermissionType.AI_INITIATED_CHAT.value: True,
                PermissionType.SHOW_OPPORTUNITY_PUSH.value: True,
                PermissionType.AI_AI_COLLABORATION_VISIBILITY.value: True,
                PermissionType.SELF_DESTRUCT_MESSAGES.value: True,
                PermissionType.AUTO_CLEAN_CHAT_HISTORY.value: True,
                PermissionType.SENSITIVE_INFO_FILTERING.value: True,
                PermissionType.MANAGE_USERS.value: False,
                PermissionType.VIEW_AUDIT_LOGS.value: False,
                PermissionType.SYSTEM_CONFIG.value: False,
                PermissionType.CREATE_AI_AVATARS.value: True,
            },
            UserRole.GUEST.value: {
                PermissionType.AI_INITIATED_CHAT.value: False,
                PermissionType.SHOW_OPPORTUNITY_PUSH.value: False,
                PermissionType.AI_AI_COLLABORATION_VISIBILITY.value: False,
                PermissionType.SELF_DESTRUCT_MESSAGES.value: False,
                PermissionType.AUTO_CLEAN_CHAT_HISTORY.value: False,
                PermissionType.SENSITIVE_INFO_FILTERING.value: True,
                PermissionType.MANAGE_USERS.value: False,
                PermissionType.VIEW_AUDIT_LOGS.value: False,
                PermissionType.SYSTEM_CONFIG.value: False,
                PermissionType.CREATE_AI_AVATARS.value: False,
            }
        }
        
        # 保存到数据库
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for role, permissions in default_permissions.items():
                    for permission_type, granted in permissions.items():
                        cursor.execute("""
                            INSERT OR REPLACE INTO role_permissions 
                            (role, permission_type, granted, updated_at)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        """, (role, permission_type, granted))
                
                conn.commit()
                logger.info("默认角色权限配置已创建并保存")
                
        except Exception as e:
            logger.error(f"保存默认角色权限配置失败: {e}")
        
        return default_permissions
    
    def get_user_role(self, user_id: str) -> str:
        """获取用户角色"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT role FROM users WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    role = result[0]
                    # 确保角色有效，否则返回默认角色
                    if role in [r.value for r in UserRole]:
                        return role
                
                # 默认返回普通用户角色
                return UserRole.USER.value
                
        except Exception as e:
            logger.error(f"获取用户角色失败: {e}")
            return UserRole.USER.value
    
    def set_user_role(self, user_id: str, role: str, admin_user_id: str = None):
        """
        设置用户角色
        
        Args:
            user_id: 要设置角色的用户ID
            role: 新角色（admin/user/guest）
            admin_user_id: 执行操作的管理员用户ID（用于审计）
        """
        # 验证角色有效性
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValueError(f"无效的角色: {role}，有效角色: {valid_roles}")
        
        # 记录审计日志
        if admin_user_id:
            self._log_permission_operation(
                admin_user_id,
                "set_user_role",
                f"将用户 {user_id} 的角色设置为 {role}",
                {"user_id": user_id, "new_role": role}
            )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (role, user_id)
                )
                
                if cursor.rowcount == 0:
                    # 用户不存在，插入新用户记录（简化处理）
                    cursor.execute(
                        "INSERT INTO users (user_id, role) VALUES (?, ?)",
                        (user_id, role)
                    )
                
                conn.commit()
                logger.info(f"用户 {user_id} 角色已设置为 {role}")
                
        except Exception as e:
            logger.error(f"设置用户角色失败: {e}")
            raise
    
    def check_permission(self, user_id: str, permission_type: str) -> bool:
        """
        检查用户是否拥有指定权限
        
        Args:
            user_id: 用户ID
            permission_type: 权限类型
        
        Returns:
            bool: 是否拥有权限
        """
        # 获取用户角色
        role = self.get_user_role(user_id)
        
        # 检查角色权限配置
        if role in self.role_permissions:
            role_perm = self.role_permissions[role]
            if permission_type in role_perm:
                return role_perm[permission_type]
        
        # 默认拒绝
        return False
    
    def get_user_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户隐私设置
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 隐私设置
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM user_privacy_settings WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    # 转换为字典
                    columns = [desc[0] for desc in cursor.description]
                    settings = dict(zip(columns, result))
                    
                    # 添加消息接收时段对象
                    time_slot = MessageTimeSlot(
                        start_hour=settings.get('receive_message_start_hour', 8),
                        start_minute=settings.get('receive_message_start_minute', 0),
                        end_hour=settings.get('receive_message_end_hour', 22),
                        end_minute=settings.get('receive_message_end_minute', 0)
                    )
                    settings['message_time_slot'] = time_slot.to_dict()
                    
                    return settings
                
                # 如果用户没有隐私设置记录，创建默认设置
                return self._create_default_privacy_settings(user_id)
                
        except Exception as e:
            logger.error(f"获取用户隐私设置失败: {e}")
            return self._create_default_privacy_settings(user_id)
    
    def _create_default_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        """创建默认隐私设置"""
        default_settings = {
            'user_id': user_id,
            'allow_ai_initiated_chat': True,
            'show_opportunity_push': True,
            'allow_ai_ai_collaboration_visibility': True,
            'auto_add_ai_friends': True,
            'receive_message_start_hour': 8,
            'receive_message_start_minute': 0,
            'receive_message_end_hour': 22,
            'receive_message_end_minute': 0,
            'message_retention_days': 30,
            'self_destruct_enabled': False,
            'self_destruct_seconds': 60,
            'updated_at': datetime.now().isoformat()
        }
        
        # 保存到数据库
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 构建插入语句
                columns = ', '.join(default_settings.keys())
                placeholders = ', '.join(['?' for _ in default_settings])
                values = list(default_settings.values())
                
                cursor.execute(
                    f"INSERT OR REPLACE INTO user_privacy_settings ({columns}) VALUES ({placeholders})",
                    values
                )
                
                conn.commit()
                logger.info(f"用户 {user_id} 的默认隐私设置已创建")
                
        except Exception as e:
            logger.error(f"保存默认隐私设置失败: {e}")
        
        return default_settings
    
    def update_privacy_settings(self, user_id: str, settings: Dict[str, Any]):
        """
        更新用户隐私设置
        
        Args:
            user_id: 用户ID
            settings: 新的隐私设置
        """
        # 记录审计日志
        self._log_permission_operation(
            user_id,
            "update_privacy_settings",
            f"更新隐私设置",
            settings
        )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取现有设置
                current_settings = self.get_user_privacy_settings(user_id)
                
                # 更新设置
                for key, value in settings.items():
                    if key in current_settings:
                        current_settings[key] = value
                
                # 添加更新时间
                current_settings['updated_at'] = datetime.now().isoformat()
                
                # 构建更新语句
                columns = ', '.join(current_settings.keys())
                placeholders = ', '.join(['?' for _ in current_settings])
                values = list(current_settings.values())
                
                cursor.execute(
                    f"INSERT OR REPLACE INTO user_privacy_settings ({columns}) VALUES ({placeholders})",
                    values
                )
                
                conn.commit()
                logger.info(f"用户 {user_id} 的隐私设置已更新")
                
        except Exception as e:
            logger.error(f"更新隐私设置失败: {e}")
            raise
    
    def can_receive_message(self, user_id: str, timestamp: datetime = None) -> bool:
        """
        检查用户在当前时间是否可以接收消息
        
        Args:
            user_id: 用户ID
            timestamp: 要检查的时间（默认当前时间）
        
        Returns:
            bool: 是否可以接收消息
        """
        settings = self.get_user_privacy_settings(user_id)
        
        # 创建消息接收时段对象
        time_slot = MessageTimeSlot(
            start_hour=settings.get('receive_message_start_hour', 8),
            start_minute=settings.get('receive_message_start_minute', 0),
            end_hour=settings.get('receive_message_end_hour', 22),
            end_minute=settings.get('receive_message_end_minute', 0)
        )
        
        return time_slot.is_within_time_slot(timestamp)
    
    def can_ai_initiate_chat(self, user_id: str) -> bool:
        """检查是否允许AI主动发起聊天"""
        settings = self.get_user_privacy_settings(user_id)
        return settings.get('allow_ai_initiated_chat', True)
    
    def should_show_opportunity_push(self, user_id: str) -> bool:
        """检查是否显示商机推送"""
        settings = self.get_user_privacy_settings(user_id)
        return settings.get('show_opportunity_push', True)
    
    def add_self_destruct_message(self, message_id: str, room_id: str, 
                                sender_id: str, self_destruct_seconds: int):
        """
        添加阅后即焚消息记录
        
        Args:
            message_id: 消息ID
            room_id: 房间ID
            sender_id: 发送者ID
            self_destruct_seconds: 自毁秒数
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 计算销毁时间
                created_at = datetime.now()
                destruct_at = created_at + timedelta(seconds=self_destruct_seconds)
                
                cursor.execute("""
                    INSERT INTO self_destruct_messages 
                    (message_id, room_id, sender_id, self_destruct_seconds, created_at, destruct_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    message_id,
                    room_id,
                    sender_id,
                    self_destruct_seconds,
                    created_at.isoformat(),
                    destruct_at.isoformat()
                ))
                
                conn.commit()
                logger.info(f"阅后即焚消息 {message_id} 已添加，将在 {self_destruct_seconds} 秒后销毁")
                
        except Exception as e:
            logger.error(f"添加阅后即焚消息失败: {e}")
    
    def check_and_destruct_messages(self):
        """检查并销毁到期的阅后即焚消息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查找需要销毁的消息
                cursor.execute("""
                    SELECT message_id, room_id, sender_id 
                    FROM self_destruct_messages 
                    WHERE is_destructed = 0 
                    AND datetime(destruct_at) <= datetime('now')
                """)
                
                messages_to_destruct = cursor.fetchall()
                
                if messages_to_destruct:
                    # 从chat_messages表中删除消息内容
                    for msg in messages_to_destruct:
                        message_id, room_id, sender_id = msg
                        
                        # 将消息内容替换为已销毁标记
                        cursor.execute("""
                            UPDATE chat_messages 
                            SET content = '[消息已销毁]',
                                is_deleted = 1,
                                deleted_at = CURRENT_TIMESTAMP
                            WHERE message_id = ?
                        """, (message_id,))
                        
                        # 标记为已销毁
                        cursor.execute("""
                            UPDATE self_destruct_messages 
                            SET is_destructed = 1 
                            WHERE message_id = ?
                        """, (message_id,))
                        
                        # 记录审计日志
                        self._log_permission_operation(
                            sender_id,
                            "self_destruct_message",
                            f"消息 {message_id} 已自动销毁",
                            {"message_id": message_id, "room_id": room_id}
                        )
                    
                    conn.commit()
                    logger.info(f"已销毁 {len(messages_to_destruct)} 条阅后即焚消息")
                    
        except Exception as e:
            logger.error(f"检查并销毁阅后即焚消息失败: {e}")
    
    def auto_clean_chat_history(self, user_id: str):
        """
        自动清理用户的聊天记录（根据保留期限）
        
        Args:
            user_id: 用户ID
        """
        settings = self.get_user_privacy_settings(user_id)
        retention_days = settings.get('message_retention_days', 30)
        
        if retention_days <= 0:
            # 保留期限为0或负数表示不清理
            return
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查找用户所在的房间
                cursor.execute("""
                    SELECT room_id FROM room_members WHERE user_id = ?
                """, (user_id,))
                
                rooms = [row[0] for row in cursor.fetchall()]
                
                if rooms:
                    # 删除过期的消息
                    cursor.execute(f"""
                        UPDATE chat_messages 
                        SET content = '[消息已自动清理]',
                            is_deleted = 1,
                            deleted_at = CURRENT_TIMESTAMP
                        WHERE room_id IN ({','.join(['?' for _ in rooms])})
                        AND datetime(timestamp) < ?
                        AND is_deleted = 0
                    """, rooms + [cutoff_date.isoformat()])
                    
                    conn.commit()
                    logger.info(f"用户 {user_id} 的聊天记录已自动清理（保留期限: {retention_days}天）")
                    
        except Exception as e:
            logger.error(f"自动清理聊天记录失败: {e}")
    
    def _log_permission_operation(self, user_id: str, operation_type: str, 
                                description: str, details: Dict[str, Any]):
        """
        记录权限操作审计日志
        
        Args:
            user_id: 操作用户ID
            operation_type: 操作类型
            description: 操作描述
            details: 操作详情
        """
        # 记录到现有安全审计系统（如果可用）
        if self.auditor:
            try:
                audit_data = {
                    "user_id": user_id,
                    "operation_type": operation_type,
                    "description": description,
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                }
                
                # 使用UndercoverAuditor记录审计事件
                self.auditor.log_audit_event(
                    event_type="permission_operation",
                    user_id=user_id,
                    component_id="permission_manager",
                    action=operation_type,
                    resource="user_permissions",
                    details=audit_data
                )
                
            except Exception as e:
                logger.error(f"记录权限操作审计日志失败: {e}")
        
        # 同时记录到本地日志
        logger.info(f"权限操作 - 用户: {user_id}, 操作: {operation_type}, 描述: {description}")


# 单例实例
_permission_manager_instance = None

def get_permission_manager(db_path: str = "data/shared_state/state.db") -> PermissionManager:
    """获取权限管理器单例实例"""
    global _permission_manager_instance
    if _permission_manager_instance is None:
        _permission_manager_instance = PermissionManager(db_path)
    return _permission_manager_instance