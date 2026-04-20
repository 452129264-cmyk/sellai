#!/usr/bin/env python3
"""
权限管理器测试脚本
测试权限管控模块的各项功能
"""

import sys
import os
import logging
import sqlite3
import json
from datetime import datetime, timedelta

# 添加src目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入权限管理器
from src.permission_manager import (
    PermissionManager, 
    UserRole, 
    PermissionType,
    MessageTimeSlot
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - TEST_PERMISSION - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_memory_database():
    """为测试设置内存数据库"""
    # 创建内存数据库连接
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # 创建users表（模拟现有表）
    cursor.execute("""
        CREATE TABLE users (
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
    
    # 创建user_privacy_settings表
    cursor.execute("""
        CREATE TABLE user_privacy_settings (
            user_id TEXT PRIMARY KEY,
            allow_ai_initiated_chat BOOLEAN DEFAULT 1,
            show_opportunity_push BOOLEAN DEFAULT 1,
            allow_ai_ai_collaboration_visibility BOOLEAN DEFAULT 1,
            auto_add_ai_friends BOOLEAN DEFAULT 1,
            updated_at TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def test_message_time_slot():
    """测试消息接收时段功能"""
    print("测试消息接收时段功能...")
    
    # 测试当天时段 (08:00-22:00)
    time_slot = MessageTimeSlot(8, 0, 22, 0)
    
    # 测试在时段内
    test_time = datetime(2026, 1, 1, 12, 0)  # 中午12点
    assert time_slot.is_within_time_slot(test_time), "12点应该在时段内"
    
    # 测试不在时段内
    test_time = datetime(2026, 1, 1, 23, 0)  # 晚上11点
    assert not time_slot.is_within_time_slot(test_time), "23点不应该在时段内"
    
    # 测试跨天时段 (22:00-08:00)
    time_slot = MessageTimeSlot(22, 0, 8, 0)
    
    # 测试在时段内（晚上）
    test_time = datetime(2026, 1, 1, 23, 0)  # 晚上11点
    assert time_slot.is_within_time_slot(test_time), "23点应该在跨天时段内"
    
    # 测试在时段内（早上）
    test_time = datetime(2026, 1, 1, 7, 0)  # 早上7点
    assert time_slot.is_within_time_slot(test_time), "7点应该在跨天时段内"
    
    # 测试不在时段内（下午）
    test_time = datetime(2026, 1, 1, 14, 0)  # 下午2点
    assert not time_slot.is_within_time_slot(test_time), "14点不应该在时段内"
    
    print("✓ 消息接收时段功能测试通过")

def test_permission_manager_basic():
    """测试权限管理器基本功能"""
    print("测试权限管理器基本功能...")
    
    # 先设置内存数据库
    setup_memory_database()
    
    # 创建权限管理器实例
    permission_manager = PermissionManager(":memory:")
    
    # 测试默认角色权限
    admin_permissions = permission_manager.role_permissions[UserRole.ADMIN.value]
    user_permissions = permission_manager.role_permissions[UserRole.USER.value]
    guest_permissions = permission_manager.role_permissions[UserRole.GUEST.value]
    
    # 管理员应该拥有所有权限
    for perm in PermissionType:
        assert admin_permissions.get(perm.value, False) == True, f"管理员应该拥有 {perm.value} 权限"
    
    # 访客不应该拥有大多数权限
    assert guest_permissions.get(PermissionType.AI_INITIATED_CHAT.value, True) == False, "访客不应该允许AI主动聊天"
    assert guest_permissions.get(PermissionType.SHOW_OPPORTUNITY_PUSH.value, True) == False, "访客不应该显示商机推送"
    assert guest_permissions.get(PermissionType.CREATE_AI_AVATARS.value, True) == False, "访客不应该允许创建AI分身"
    
    print("✓ 权限管理器基本功能测试通过")

def test_user_role_management():
    """测试用户角色管理"""
    print("测试用户角色管理...")
    
    # 先设置内存数据库
    setup_memory_database()
    
    permission_manager = PermissionManager(":memory:")
    
    # 测试设置用户角色
    permission_manager.set_user_role("test_user_1", UserRole.ADMIN.value, "system")
    
    # 验证角色设置
    role = permission_manager.get_user_role("test_user_1")
    assert role == UserRole.ADMIN.value, f"用户角色应该是admin，实际是 {role}"
    
    # 测试权限检查
    can_manage_users = permission_manager.check_permission("test_user_1", PermissionType.MANAGE_USERS.value)
    assert can_manage_users, "管理员应该可以管理用户"
    
    # 测试普通用户角色
    permission_manager.set_user_role("test_user_2", UserRole.USER.value, "system")
    can_view_audit_logs = permission_manager.check_permission("test_user_2", PermissionType.VIEW_AUDIT_LOGS.value)
    assert not can_view_audit_logs, "普通用户不应该查看审计日志"
    
    print("✓ 用户角色管理测试通过")

def test_privacy_settings():
    """测试隐私设置功能"""
    print("测试隐私设置功能...")
    
    # 先设置内存数据库
    setup_memory_database()
    
    permission_manager = PermissionManager(":memory:")
    
    # 获取默认隐私设置
    settings = permission_manager.get_user_privacy_settings("test_user_3")
    
    # 验证默认值
    assert settings['allow_ai_initiated_chat'] == True, "默认应该允许AI主动聊天"
    assert settings['show_opportunity_push'] == True, "默认应该显示商机推送"
    assert settings['message_retention_days'] == 30, "默认消息保留期限应该是30天"
    
    # 更新隐私设置
    new_settings = {
        'allow_ai_initiated_chat': False,
        'show_opportunity_push': False,
        'message_retention_days': 7,
        'self_destruct_enabled': True,
        'self_destruct_seconds': 30
    }
    
    permission_manager.update_privacy_settings("test_user_3", new_settings)
    
    # 验证更新后的设置
    updated_settings = permission_manager.get_user_privacy_settings("test_user_3")
    assert updated_settings['allow_ai_initiated_chat'] == False, "应该已禁用AI主动聊天"
    assert updated_settings['show_opportunity_push'] == False, "应该已隐藏商机推送"
    assert updated_settings['message_retention_days'] == 7, "消息保留期限应该是7天"
    assert updated_settings['self_destruct_enabled'] == True, "应该已启用阅后即焚"
    assert updated_settings['self_destruct_seconds'] == 30, "阅后即焚秒数应该是30秒"
    
    print("✓ 隐私设置功能测试通过")

def test_message_reception_control():
    """测试消息接收控制功能"""
    print("测试消息接收控制功能...")
    
    # 先设置内存数据库
    setup_memory_database()
    
    permission_manager = PermissionManager(":memory:")
    
    # 测试默认时段（08:00-22:00）内的消息接收
    test_time = datetime(2026, 1, 1, 14, 0)  # 下午2点
    can_receive = permission_manager.can_receive_message("test_user_4", test_time)
    assert can_receive, "下午2点应该可以接收消息"
    
    # 测试默认时段外的消息接收
    test_time = datetime(2026, 1, 1, 23, 0)  # 晚上11点
    can_receive = permission_manager.can_receive_message("test_user_4", test_time)
    assert not can_receive, "晚上11点不应该接收消息"
    
    # 更新为自定义时段（10:00-18:00）
    custom_settings = {
        'receive_message_start_hour': 10,
        'receive_message_start_minute': 0,
        'receive_message_end_hour': 18,
        'receive_message_end_minute': 0
    }
    
    permission_manager.update_privacy_settings("test_user_4", custom_settings)
    
    # 测试新时段内的消息接收
    test_time = datetime(2026, 1, 1, 12, 0)  # 中午12点
    can_receive = permission_manager.can_receive_message("test_user_4", test_time)
    assert can_receive, "中午12点应该可以接收消息（新时段）"
    
    # 测试新时段外的消息接收
    test_time = datetime(2026, 1, 1, 9, 0)  # 早上9点
    can_receive = permission_manager.check_permission("test_user_4", PermissionType.AI_INITIATED_CHAT.value)
    # 注意：这里测试AI主动聊天权限，不测试时间段
    
    print("✓ 消息接收控制功能测试通过")

def test_self_destruct_messages():
    """测试阅后即焚消息功能"""
    print("测试阅后即焚消息功能...")
    
    # 先设置内存数据库
    setup_memory_database()
    
    permission_manager = PermissionManager(":memory:")
    
    # 添加阅后即焚消息
    permission_manager.add_self_destruct_message(
        message_id="test_msg_1",
        room_id="test_room_1",
        sender_id="test_sender_1",
        self_destruct_seconds=5  # 5秒后销毁
    )
    
    print("✓ 阅后即焚消息添加功能测试通过")
    
    # 注意：实际销毁检查需要依赖定时任务或外部调用
    # 这里只测试添加功能

def test_ai_chat_permissions():
    """测试AI聊天权限功能"""
    print("测试AI聊天权限功能...")
    
    # 先设置内存数据库
    setup_memory_database()
    
    permission_manager = PermissionManager(":memory:")
    
    # 测试默认允许AI主动聊天
    can_ai_chat = permission_manager.can_ai_initiate_chat("test_user_5")
    assert can_ai_chat, "默认应该允许AI主动聊天"
    
    # 禁用AI主动聊天
    permission_manager.update_privacy_settings("test_user_5", {
        'allow_ai_initiated_chat': False
    })
    
    # 验证禁用
    can_ai_chat = permission_manager.can_ai_initiate_chat("test_user_5")
    assert not can_ai_chat, "应该已禁用AI主动聊天"
    
    print("✓ AI聊天权限功能测试通过")

def test_opportunity_push_permissions():
    """测试商机推送权限功能"""
    print("测试商机推送权限功能...")
    
    # 先设置内存数据库
    setup_memory_database()
    
    permission_manager = PermissionManager(":memory:")
    
    # 测试默认显示商机推送
    should_show = permission_manager.should_show_opportunity_push("test_user_6")
    assert should_show, "默认应该显示商机推送"
    
    # 隐藏商机推送
    permission_manager.update_privacy_settings("test_user_6", {
        'show_opportunity_push': False
    })
    
    # 验证隐藏
    should_show = permission_manager.should_show_opportunity_push("test_user_6")
    assert not should_show, "应该已隐藏商机推送"
    
    print("✓ 商机推送权限功能测试通过")

def run_all_tests():
    """运行所有测试"""
    print("开始权限管控模块测试...")
    print("=" * 60)
    
    test_message_time_slot()
    print()
    
    test_permission_manager_basic()
    print()
    
    test_user_role_management()
    print()
    
    test_privacy_settings()
    print()
    
    test_message_reception_control()
    print()
    
    test_self_destruct_messages()
    print()
    
    test_ai_chat_permissions()
    print()
    
    test_opportunity_push_permissions()
    print()
    
    print("=" * 60)
    print("所有测试通过！✓")
    print()
    
    return True

if __name__ == "__main__":
    try:
        run_all_tests()
        sys.exit(0)
    except AssertionError as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)