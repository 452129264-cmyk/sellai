#!/usr/bin/env python3
"""
测试AI谈判引擎导入和基本功能
"""

import sys
sys.path.append('.')

print("测试AI谈判引擎...")

try:
    from src.ai_negotiation_engine import AINegotiationEngine
    print("✅ AINegotiationEngine 导入成功")
    
    # 测试创建实例
    engine = AINegotiationEngine("data/shared_state/state.db")
    print("✅ AINegotiationEngine 实例创建成功")
    
    # 测试生成初始提案
    context = {
        "scenario": "price_negotiation",
        "strategy": "balanced_win_win",
        "buyer_budget": 100000,
        "seller_ask": 120000,
        "industry": "manufacturing"
    }
    
    initial_proposal = engine.generate_initial_proposal(context=context)
    print("✅ generate_initial_proposal 调用成功")
    
    # 验证返回结构
    assert "proposal" in initial_proposal, "缺少 proposal 字段"
    assert "negotiation_stage" in initial_proposal, "缺少 negotiation_stage 字段"
    
    proposal = initial_proposal["proposal"]
    print(f"✅ 提案结构正确: {list(proposal.keys())}")
    
    # 验证价格在合理范围内
    if "unit_price" in proposal:
        price = proposal["unit_price"]
        print(f"✅ 单位价格: ${price:.2f}")
        # 价格应该在买家预算和卖家要价之间
        assert 100000 <= price <= 120000, f"价格不在合理范围: ${price:.2f}"
        print("✅ 价格在合理范围内")
    
    # 测试评估还价
    counter_offer = proposal.copy()
    if "unit_price" in counter_offer:
        counter_offer["unit_price"] = counter_offer["unit_price"] * 0.9  # 降价10%
    
    evaluation = engine.evaluate_counter_offer(
        original_proposal=proposal,
        counter_offer=counter_offer,
        context=context
    )
    
    print("✅ evaluate_counter_offer 调用成功")
    print(f"✅ 还价评估结构: {list(evaluation.keys())}")
    
    print("\n✅ AI谈判引擎测试全部通过！")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)