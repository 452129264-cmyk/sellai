#!/usr/bin/env python3
"""
测试数据库连接和基本功能
"""

import sys
sys.path.append('.')

import sqlite3
import os

def test_database_connection():
    """测试数据库连接"""
    db_path = "./data/shared_state/state.db"
    
    print(f"测试数据库连接: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_table = cursor.fetchone()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invitation_relationships'")
        invitation_table = cursor.fetchone()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='credit_records'")
        credit_table = cursor.fetchone()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='promotion_contents'")
        promotion_table = cursor.fetchone()
        
        print("数据库表检查:")
        print(f"  users表: {'存在' if users_table else '不存在'}")
        print(f"  invitation_relationships表: {'存在' if invitation_table else '不存在'}")
        print(f"  credit_records表: {'存在' if credit_table else '不存在'}")
        print(f"  promotion_contents表: {'存在' if promotion_table else '不存在'}")
        
        # 检查现有数据
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"  现有用户数: {user_count}")
        
        cursor.execute("SELECT COUNT(*) FROM invitation_relationships")
        invitation_count = cursor.fetchone()[0]
        print(f"  现有邀请关系数: {invitation_count}")
        
        cursor.execute("SELECT COUNT(*) FROM credit_records")
        credit_count = cursor.fetchone()[0]
        print(f"  现有积分记录数: {credit_count}")
        
        # 显示用户数据
        cursor.execute("SELECT user_id, username, credits_balance, invited_by FROM users")
        users = cursor.fetchall()
        
        print("\n现有用户:")
        for user in users:
            print(f"  ID: {user[0]}, 用户名: {user[1]}, 积分: {user[2]}, 邀请人: {user[3]}")
        
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
        return False
    except Exception as e:
        print(f"其他错误: {e}")
        return False


def test_invitation_manager():
    """测试邀请裂变管理器"""
    print("\n测试邀请裂变管理器...")
    
    try:
        from src.invitation_fission_manager import InvitationFissionManager
        
        manager = InvitationFissionManager()
        
        # 测试1: 检查现有邀请关系
        print("1. 检查现有邀请关系...")
        
        # 获取现有用户
        conn = sqlite3.connect("./data/shared_state/state.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users LIMIT 2")
        users = cursor.fetchall()
        conn.close()
        
        if len(users) >= 2:
            user1 = users[0][0]
            user2 = users[1][0]
            
            # 模拟检查邀请关系
            print(f"  用户1: {user1}")
            print(f"  用户2: {user2}")
            
            # 测试检查邀请关系方法
            relationship = manager.check_invitation_relationship(
                user_id=user2,
                transaction_id="test_txn_001"
            )
            
            print(f"  邀请关系检查结果: {relationship}")
        
        # 测试2: 创建新用户
        print("\n2. 创建新用户（测试）...")
        try:
            test_user = manager.create_user(
                username="test_user_" + str(hash(os.urandom(8)))[:8],
                email="test@example.com"
            )
            print(f"  测试用户创建成功: ID={test_user['user_id']}, 邀请码={test_user['invitation_code']}")
        except Exception as e:
            print(f"  测试用户创建失败（可能是重复用户名）: {e}")
        
        print("\n✅ 邀请裂变管理器测试完成")
        
        return True
        
    except ImportError as e:
        print(f"❌ 无法导入邀请裂变管理器: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_commission_integration():
    """测试佣金计算器集成"""
    print("\n测试佣金计算器集成...")
    
    try:
        from src.commission_calculator import CommissionCalculator
        
        calculator = CommissionCalculator()
        
        # 测试场景: 常规业务，无邀请关系
        print("1. 测试常规业务，无邀请关系...")
        result1 = calculator.calculate_commission(
            transaction_value=50000.0,
            business_type="regular_business",
            user_id=None,
            transaction_id=None
        )
        
        print(f"  交易金额: $50,000.00")
        print(f"  系统佣金率: {result1['system_commission']['rate']*100}%")
        print(f"  系统佣金金额: ${result1['system_commission']['amount']:,.2f}")
        
        # 测试场景: 包含邀请关系
        print("\n2. 测试包含邀请关系...")
        result2 = calculator.calculate_commission(
            transaction_value=50000.0,
            business_type="regular_business",
            user_id="user_002",  # 模拟的邀请关系中的用户
            transaction_id="test_txn_002"
        )
        
        print(f"  交易金额: $50,000.00")
        print(f"  系统佣金率: {result2['system_commission']['rate']*100}%")
        print(f"  系统佣金金额: ${result2['system_commission']['amount']:,.2f}")
        
        if result2['invitation_split']['has_invitation']:
            print(f"  邀请分成率: {result2['invitation_split']['rate']*100}%")
            print(f"  邀请分成金额: ${result2['invitation_split']['amount']:,.2f}")
            print(f"  总佣金金额: ${result2['total_commission']['amount']:,.2f}")
        
        print("\n✅ 佣金计算器集成测试完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 佣金计算器集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("邀请裂变系统集成测试")
    print("=" * 60)
    
    # 测试数据库连接
    db_success = test_database_connection()
    
    # 测试邀请裂变管理器
    manager_success = test_invitation_manager()
    
    # 测试佣金计算器集成
    commission_success = test_commission_integration()
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    print(f"  数据库连接测试: {'通过' if db_success else '失败'}")
    print(f"  邀请裂变管理器测试: {'通过' if manager_success else '失败'}")
    print(f"  佣金计算器集成测试: {'通过' if commission_success else '失败'}")
    
    all_success = db_success and manager_success and commission_success
    print(f"\n  总体测试: {'✅ 通过' if all_success else '❌ 失败'}")
    print("=" * 60)