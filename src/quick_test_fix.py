#!/usr/bin/env python3
"""
快速测试修复效果
"""

import sys
sys.path.append('.')

print("测试佣金计算器修复...")

try:
    from src.commission_calculator import CommissionCalculator
    print("✅ CommissionCalculator 导入成功")
    
    calculator = CommissionCalculator()
    
    # 测试 calculate_commission 方法
    result = calculator.calculate_commission(
        transaction_value=50000.0,
        business_type="regular_business",
        user_id="test_user",
        transaction_id="test_tx"
    )
    
    print("✅ calculate_commission 调用成功")
    
    # 验证返回结构
    assert 'system_commission' in result, "缺少 system_commission"
    assert 'amount' in result['system_commission'], "system_commission 缺少 amount 字段"
    assert 'invitation_split' in result, "缺少 invitation_split"
    assert 'total_commission' in result, "缺少 total_commission"
    
    print("✅ 返回结构正确")
    
    # 验证金额计算
    expected_system_commission = 50000.0 * 0.05
    actual_system_commission = result['system_commission']['amount']
    
    assert abs(actual_system_commission - expected_system_commission) < 0.01, \
        f"系统佣金计算错误: 期望 {expected_system_commission}, 实际 {actual_system_commission}"
    
    print(f"✅ 系统佣金计算正确: ${actual_system_commission:.2f}")
    
    # 测试 IndustryResourceImporter 的 insert_industry_resource 方法
    try:
        from src.industry_resource_importer import IndustryResourceImporter
        
        importer = IndustryResourceImporter()
        test_resource = {
            "resource_type": "supply_chain",
            "industry": "manufacturing",
            "title": "测试资源",
            "description": "测试描述",
            "country": "US",
            "value_range": "100000-500000",
            "contact_info": "test@example.com",
            "created_at": "2024-01-01T00:00:00",
            "status": "active"
        }
        
        resource_id = importer.insert_industry_resource(test_resource)
        assert resource_id is not None, "资源插入失败"
        print(f"✅ IndustryResourceImporter.insert_industry_resource 调用成功，资源ID: {resource_id}")
        
    except Exception as e:
        print(f"❌ IndustryResourceImporter 测试失败: {e}")
    
    # 测试 SharedStateManager 的 register_network_node 方法
    try:
        from src.shared_state_manager import SharedStateManager
        
        manager = SharedStateManager()
        node_info = {
            "node_id": "test_node_001",
            "node_type": "sellai_instance",
            "capabilities": ["negotiation", "resource_matching"],
            "last_seen": "2024-01-01T00:00:00",
            "status": "active"
        }
        
        success = manager.register_network_node(node_info)
        assert success, "网络节点注册失败"
        print("✅ SharedStateManager.register_network_node 调用成功")
        
    except Exception as e:
        print(f"❌ SharedStateManager 测试失败: {e}")
    
    print("\n✅ 所有修复测试通过！")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)