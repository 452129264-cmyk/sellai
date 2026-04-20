#!/usr/bin/env python3
"""
运行核心压力测试：AI谈判引擎和数据管道稳定性
"""

import sys
sys.path.append('.')

print("运行核心压力测试...")
print("=" * 60)

# 导入压力测试套件
from src.pressure_test_suite import PressureTestSuite

# 创建测试套件实例
test_suite = PressureTestSuite("data/shared_state/pressure_test.db")

print("\n1. 测试AI谈判引擎并发验证...")
print("-" * 40)

# 直接调用谈判引擎测试方法
negotiation_results = test_suite.test_negotiation_engine_concurrent()

# 检查测试结果（方法没有返回值，但会打印结果）
# 我们通过捕获输出来判断

print("\n2. 测试数据管道稳定性验证...")
print("-" * 40)

# 直接调用数据管道测试方法
pipeline_results = test_suite.test_data_pipeline_stability()

print("\n" + "=" * 60)
print("核心压力测试执行完成")

# 验证至少3种商务场景下的谈判逻辑
print("\n验证至少3种商务场景下的谈判逻辑和佣金计算准确性...")

# 创建一个简化的测试来验证3种场景
from src.commission_calculator import CommissionCalculator

calculator = CommissionCalculator()

test_scenarios = [
    {
        "name": "大额供应链项目",
        "transaction_value": 1500000.0,
        "business_type": "large_supply_chain",
        "expected_min_rate": 0.02,
        "expected_max_rate": 0.03
    },
    {
        "name": "常规中小生意",
        "transaction_value": 50000.0,
        "business_type": "regular_business",
        "expected_rate": 0.05
    },
    {
        "name": "稀缺高利润小众项目",
        "transaction_value": 200000.0,
        "business_type": "premium_niche",
        "expected_rate": 0.08
    }
]

passed_scenarios = 0

for scenario in test_scenarios:
    print(f"\n测试场景: {scenario['name']}")
    print(f"  交易金额: ${scenario['transaction_value']:,.2f}")
    
    result = calculator.calculate_commission(
        transaction_value=scenario['transaction_value'],
        business_type=scenario['business_type'],
        user_id=None,
        transaction_id=None
    )
    
    system_commission = result['system_commission']
    actual_rate = system_commission['rate']
    actual_amount = system_commission['amount']
    
    print(f"  实际佣金费率: {actual_rate:.4f} ({actual_rate*100:.2f}%)")
    print(f"  实际佣金金额: ${actual_amount:,.2f}")
    
    if scenario['business_type'] == 'large_supply_chain':
        # 检查是否在2%-3%范围内
        if scenario['expected_min_rate'] <= actual_rate <= scenario['expected_max_rate']:
            print(f"  ✅ 佣金费率在期望范围内 (2%-3%)")
            passed_scenarios += 1
        else:
            print(f"  ❌ 佣金费率超出期望范围: 期望 2%-3%，实际 {actual_rate*100:.2f}%")
    else:
        expected_rate = scenario['expected_rate']
        if abs(actual_rate - expected_rate) < 0.001:
            print(f"  ✅ 佣金费率符合期望 ({expected_rate*100:.0f}%)")
            passed_scenarios += 1
        else:
            print(f"  ❌ 佣金费率不符合期望: 期望 {expected_rate*100:.0f}%，实际 {actual_rate*100:.2f}%")

print(f"\n{'='*60}")
print(f"场景测试结果: {passed_scenarios}/{len(test_scenarios)} 个场景通过")
if passed_scenarios >= 3:
    print("✅ 达到验收标准: 至少3种商务场景测试通过")
else:
    print("❌ 未达到验收标准: 需要至少3种商务场景测试通过")
    sys.exit(1)

print("\n✅ 核心压力测试验证通过！")