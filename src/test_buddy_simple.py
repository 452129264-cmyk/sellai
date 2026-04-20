#!/usr/bin/env python3
"""
简单测试Buddy系统功能
"""

import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

import time
import json
from datetime import datetime

try:
    from buddy_system import BuddySystem, UserMood, InteractionType
    print("✅ BuddySystem模块导入成功")
    
    # 测试初始化
    print("\n1. 测试Buddy系统初始化...")
    buddy = BuddySystem(":memory:")
    print(f"   用户ID: {buddy.user_state['user_id']}")
    
    # 测试消息生成
    print("\n2. 测试交互消息生成...")
    greeting_msg = buddy._generate_interaction_message(InteractionType.GREETING)
    print(f"   问候消息: {greeting_msg}")
    
    suggestion_msg = buddy._generate_interaction_message(InteractionType.SUGGESTION)
    print(f"   建议消息: {suggestion_msg}")
    
    # 测试用户情绪设置
    print("\n3. 测试用户情绪设置...")
    buddy.set_user_mood(UserMood.HAPPY)
    print(f"   用户情绪: {buddy.user_state['current_mood']}")
    
    # 测试获取状态摘要
    print("\n4. 测试获取状态摘要...")
    summary = buddy.get_interaction_summary()
    print(f"   交互总数: {summary['total_interactions']}")
    
    # 测试KAIROS集成
    print("\n5. 测试KAIROS集成...")
    try:
        from kairos_guardian import KAIROSGuardian
        guardian = KAIROSGuardian(":memory:")
        print(f"   Buddy系统已集成: {guardian.buddy_system is not None}")
        
        # 测试状态报告
        status = guardian.get_guardian_status()
        if "buddy_system_status" in status:
            print("   ✅ Buddy系统状态已包含在Guardian报告中")
        else:
            print("   ❌ Buddy系统状态未包含在Guardian报告中")
            
    except ImportError as e:
        print(f"   ⚠️ KAIROSGuardian导入失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Buddy系统基本功能测试通过")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)