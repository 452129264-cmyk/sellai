#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')
from src.shared_state_manager import SharedStateManager
import json
import hashlib
from datetime import datetime, timedelta

def integration_test():
    """全流程集成测试"""
    print("开始全流程集成测试...")
    
    # 初始化管理器
    manager = SharedStateManager()
    
    # 1. 测试分身注册
    print("1. 测试分身注册...")
    avatar_id = "test_integration_avatar"
    avatar_profile = {
        "avatar_id": avatar_id,
        "avatar_name": "集成测试分身",
        "template_id": "vertical_jeans_expert",
        "capability_scores": {"content_creation": 85, "data_analysis": 90, "market_research": 88},
        "specialization_tags": ["jeans", "fashion", "ecommerce"],
        "success_rate": 0.92,
        "total_tasks_completed": 12,
        "avg_completion_time_seconds": 1800,
        "current_load": 0,
        "last_active": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat()
    }
    
    success = manager.register_avatar(avatar_profile)
    if not success:
        print("❌ 分身注册失败")
        return False
    print("✅ 分身注册成功")
    
    # 2. 测试商机去重
    print("2. 测试商机去重...")
    test_url = "https://example.com/test_integration_opportunity"
    opportunity_hash = hashlib.sha256(test_url.encode()).hexdigest()
    
    # 第一次插入
    opp1 = {
        "opportunity_hash": opportunity_hash,
        "source_platform": "test_platform",
        "original_id": "test_123",
        "title": "集成测试商机",
        "first_discovered": datetime.now().isoformat(),
        "last_checked": datetime.now().isoformat(),
        "processed_by_avatars": "",
        "status": "new"
    }
    
    inserted1 = manager.record_processed_opportunity(opp1)
    if not inserted1:
        print("❌ 第一次商机插入失败")
        return False
    print("✅ 第一次商机插入成功")
    
    # 第二次插入相同hash（应失败）
    inserted2 = manager.record_processed_opportunity(opp1)
    if inserted2:
        print("❌ 重复商机插入成功（去重失败）")
        return False
    print("✅ 重复商机去重成功")
    
    # 3. 测试任务分配
    print("3. 测试任务分配...")
    assignment = {
        "opportunity_hash": opportunity_hash,
        "assigned_avatar": avatar_id,
        "assignment_time": datetime.now().isoformat(),
        "deadline": (datetime.now() + timedelta(days=3)).isoformat(),
        "priority": "medium",
        "completion_status": "pending",
        "result_summary": ""
    }
    
    assignment_id = manager.assign_task(assignment)
    if not assignment_id:
        print("❌ 任务分配失败")
        return False
    print(f"✅ 任务分配成功，分配ID: {assignment_id}")
    
    # 4. 测试成本记录
    print("4. 测试成本记录...")
    cost_record = {
        "avatar_id": avatar_id,
        "cost_type": "api_calls",
        "amount": 1000,
        "unit_price": 0.01,
        "total_cost": 10.0,
        "currency": "USD",
        "country_code": "US",
        "logistics_cost": 5.0,
        "tax_rate": 10.0,
        "local_operations_cost": 500.0,
        "shipping_time_days": 7,
        "period_start": (datetime.now() - timedelta(days=30)).isoformat(),
        "period_end": datetime.now().isoformat(),
        "notes": "集成测试成本记录"
    }
    
    log_id = manager.record_cost_consumption(cost_record)
    if not log_id:
        print("❌ 成本记录失败")
        return False
    print(f"✅ 成本记录成功，日志ID: {log_id}")
    
    # 5. 验证数据查询
    print("5. 验证数据查询...")
    
    # 查询分身
    avatar = manager.get_avatar_profile(avatar_id)
    if not avatar:
        print("❌ 分身查询失败")
        return False
    print(f"✅ 分身查询成功: {avatar['avatar_name']}")
    
    # 查询商机
    opportunity = manager.get_opportunity_details(opportunity_hash)
    if not opportunity:
        print("❌ 商机查询失败")
        return False
    print(f"✅ 商机查询成功: {opportunity['title']}")
    
    # 查询任务
    tasks = manager.get_tasks_for_avatar(avatar_id)
    if len(tasks) == 0:
        print("❌ 任务查询失败")
        return False
    print(f"✅ 任务查询成功，找到{len(tasks)}个任务")
    
    # 查询成本
    costs = manager.get_costs_for_avatar(avatar_id)
    if len(costs) == 0:
        print("❌ 成本查询失败")
        return False
    print(f"✅ 成本查询成功，找到{len(costs)}条成本记录")
    
    print("\n🎉 全流程集成测试通过！")
    print("   测试步骤：")
    print("     1. 分身注册 ✓")
    print("     2. 商机去重 ✓")
    print("     3. 任务分配 ✓")
    print("     4. 成本记录 ✓")
    print("     5. 数据查询 ✓")
    
    return True

if __name__ == '__main__':
    success = integration_test()
    sys.exit(0 if success else 1)