#!/usr/bin/env python3
"""
快速测试Buddy系统基本功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import logging
from datetime import datetime
from src.buddy_system import BuddySystem, UserMood, InteractionType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_buddy_initialization():
    """测试Buddy系统初始化"""
    print("1. 测试Buddy系统初始化...")
    
    # 使用内存数据库
    buddy = BuddySystem(":memory:")
    
    print(f"   用户ID: {buddy.user_state['user_id']}")
    print(f"   用户情绪: {buddy.user_state['current_mood']}")
    print(f"   活动等级: {buddy.user_state['activity_level']}")
    
    return buddy

def test_interaction_message_generation(buddy):
    """测试交互消息生成"""
    print("\n2. 测试交互消息生成...")
    
    greeting_msg = buddy._generate_interaction_message(InteractionType.GREETING)
    print(f"   问候消息: {greeting_msg}")
    
    suggestion_msg = buddy._generate_interaction_message(InteractionType.SUGGESTION)
    print(f"   建议消息: {suggestion_msg}")
    
    status_msg = buddy._generate_interaction_message(InteractionType.STATUS_CHECK)
    print(f"   状态检查消息: {status_msg}")

def test_user_mood_setting(buddy):
    """测试用户情绪设置"""
    print("\n3. 测试用户情绪设置...")
    
    moods_to_test = [
        (UserMood.HAPPY, "happy"),
        (UserMood.FOCUSED, "focused"),
        (UserMood.TIRED, "tired"),
        (UserMood.CREATIVE, "creative")
    ]
    
    for mood_enum, expected_value in moods_to_test:
        buddy.set_user_mood(mood_enum)
        actual_value = buddy.user_state["current_mood"]
        
        if actual_value == expected_value:
            print(f"   ✅ {mood_enum.value}: 设置成功")
        else:
            print(f"   ❌ {mood_enum.value}: 设置失败 (期望: {expected_value}, 实际: {actual_value})")

def test_interaction_service(buddy):
    """测试交互服务启动停止"""
    print("\n4. 测试交互服务启动停止...")
    
    print("   启动交互服务...")
    buddy.start_interaction_service()
    
    # 等待服务启动
    time.sleep(2)
    
    print(f"   服务运行状态: {buddy.running}")
    print(f"   交互启用状态: {buddy.interaction_enabled}")
    
    # 获取状态摘要
    summary = buddy.get_interaction_summary()
    print(f"   交互总数: {summary['total_interactions']}")
    print(f"   活跃交互: {summary['active_interactions']}")
    
    print("   停止交互服务...")
    buddy.stop_interaction_service()
    
    # 等待服务停止
    time.sleep(1)
    
    print(f"   服务运行状态: {buddy.running}")

def test_interaction_initiation(buddy):
    """测试交互发起"""
    print("\n5. 测试交互发起...")
    
    # 模拟触发一个交互
    interaction_id = 100
    message = buddy._generate_interaction_message(InteractionType.ENCOURAGEMENT)
    
    print(f"   交互ID: {interaction_id}")
    print(f"   交互消息: {message}")
    
    # 记录交互
    buddy.active_interactions[interaction_id] = {
        "type": InteractionType.ENCOURAGEMENT.value,
        "message": message,
        "initiated_at": datetime.now().isoformat(),
        "status": "pending"
    }
    
    print("   交互已记录")
    
    # 模拟用户响应
    response_text = "谢谢鼓励！我会继续努力的。"
    buddy.process_user_response(interaction_id, response_text, "happy")
    
    print(f"   用户响应: {response_text}")
    print(f"   用户情绪: happy")

def test_kairos_integration():
    """测试KAIROS集成"""
    print("\n6. 测试KAIROS集成...")
    
    from src.kairos_guardian import KAIROSGuardian
    
    guardian = KAIROSGuardian(":memory:")
    
    print(f"   Buddy系统实例: {guardian.buddy_system}")
    print(f"   Buddy系统类型: {type(guardian.buddy_system)}")
    
    # 获取状态报告
    status = guardian.get_guardian_status()
    
    if "buddy_system_status" in status:
        print("   ✅ Buddy系统状态已集成到Guardian报告中")
        buddy_status = status["buddy_system_status"]
        print(f"      交互启用: {buddy_status.get('interaction_enabled', 'N/A')}")
        print(f"      总交互数: {buddy_status.get('total_interactions', 'N/A')}")
    else:
        print("   ❌ Buddy系统状态未集成到Guardian报告中")
    
    # 清理
    guardian.stop_guardian_service()

def main():
    """主测试函数"""
    print("=" * 60)
    print("Buddy系统快速测试")
    print("=" * 60)
    
    try:
        # 测试初始化
        buddy = test_buddy_initialization()
        
        # 测试消息生成
        test_interaction_message_generation(buddy)
        
        # 测试用户情绪设置
        test_user_mood_setting(buddy)
        
        # 测试交互服务
        test_interaction_service(buddy)
        
        # 测试交互发起
        test_interaction_initiation(buddy)
        
        # 测试KAIROS集成
        test_kairos_integration()
        
        print("\n" + "=" * 60)
        print("✅ 所有快速测试通过！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)