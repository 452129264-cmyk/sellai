"""
快速测试邀请裂变系统与佣金计算器的集成
"""

import sys
sys.path.append('.')

from src.commission_calculator import CommissionCalculator


def test_commission_with_invitation():
    """测试包含邀请关系的佣金计算"""
    print("测试佣金计算器与邀请裂变系统的集成...")
    
    calculator = CommissionCalculator()
    
    # 测试场景1: 被邀请人（user_002）参与交易
    print("\n1. 测试被邀请人参与交易...")
    result1 = calculator.calculate_commission(
        transaction_value=50000.0,
        business_type="regular_business",
        user_id="user_002",  # 模拟的邀请关系中的被邀请人
        transaction_id="test_txn_001"
    )
    
    print(f"   交易金额: $50,000.00")
    print(f"   用户ID: user_002")
    print(f"   系统佣金: {result1['system_commission_rate']*100}% (${result1['system_commission_amount']:,.2f})")
    
    if 'invitation_split' in result1:
        print(f"   邀请分成: {result1['invitation_split']['rate']*100}% (${result1['invitation_split']['amount']:,.2f})")
        print(f"   总佣金: ${result1['total_commission_amount']:,.2f}")
        print(f"   邀请人ID: {result1['invitation_split'].get('inviter_id', 'unknown')}")
    else:
        print("   无邀请分成（可能邀请关系不存在）")
    
    # 测试场景2: 无邀请关系的用户参与交易
    print("\n2. 测试无邀请关系的用户参与交易...")
    result2 = calculator.calculate_commission(
        transaction_value=100000.0,
        business_type="large_supply_chain",
        user_id="user_005",  # 模拟中没有邀请关系
        transaction_id="test_txn_002"
    )
    
    print(f"   交易金额: $100,000.00")
    print(f"   用户ID: user_005")
    print(f"   系统佣金: {result2['system_commission_rate']*100}% (${result2['system_commission_amount']:,.2f})")
    
    if 'invitation_split' in result2:
        print(f"   邀请分成: {result2['invitation_split']['rate']*100}% (${result2['invitation_split']['amount']:,.2f})")
    else:
        print("   无邀请分成（正确）")
    
    # 测试场景3: 检查不同业务类型的佣金
    print("\n3. 测试不同业务类型的佣金...")
    
    test_cases = [
        (5000.0, "regular_business", "常规中小生意"),
        (2000000.0, "large_supply_chain", "大额供应链"),
        (15000.0, "premium_niche", "稀缺高利润项目")
    ]
    
    for value, biz_type, desc in test_cases:
        result = calculator.calculate_commission(
            transaction_value=value,
            business_type=biz_type,
            user_id="user_002",
            transaction_id=f"test_{biz_type}"
        )
        
        print(f"   {desc}: ${value:,.2f} → 佣金率: {result['system_commission_rate']*100}% (${result['system_commission_amount']:,.2f})")
    
    print("\n✅ 集成测试完成！")
    
    return True


if __name__ == "__main__":
    test_commission_with_invitation()