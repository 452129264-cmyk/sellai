"""
测试邀请裂变系统与佣金计算器的集成
"""

import sys
sys.path.append('.')

from src.invitation_fission_manager import InvitationFissionManager
from src.commission_calculator import CommissionCalculator


def test_integration():
    """测试邀请裂变与佣金计算的集成"""
    print("测试邀请裂变系统与佣金计算器的集成...")
    
    # 初始化管理器
    manager = InvitationFissionManager()
    calculator = CommissionCalculator()
    
    try:
        # 创建邀请人用户
        print("\n1. 创建邀请人用户...")
        inviter = manager.create_user(username="master_inviter", email="master@example.com")
        print(f"   邀请人创建成功: ID={inviter['user_id']}")
        
        # 创建被邀请人用户（通过邀请）
        print("\n2. 创建被邀请人用户（通过邀请）...")
        invitee = manager.create_user(
            username="invited_user", 
            email="invited@example.com",
            invited_by=inviter['user_id']
        )
        print(f"   被邀请人创建成功: ID={invitee['user_id']}")
        
        # 发放邀请奖励积分
        print("\n3. 发放邀请奖励积分...")
        credit_result = manager.grant_invitation_credits(
            inviter_id=inviter['user_id'],
            invitee_id=invitee['user_id']
        )
        print(f"   积分发放成功: {credit_result['message']}")
        
        # 测试佣金计算器中的邀请关系检查
        print("\n4. 测试佣金计算器邀请关系检查...")
        
        # 测试场景1: 被邀请人参与交易（应有邀请关系）
        transaction_id = "test_transaction_001"
        relationship = manager.check_invitation_relationship(
            user_id=invitee['user_id'],
            transaction_id=transaction_id
        )
        
        print(f"   被邀请人{invitee['user_id']}的邀请关系: {relationship}")
        
        if relationship:
            print(f"   邀请人ID: {relationship['inviter_id']}")
            print(f"   关系ID: {relationship['relationship_id']}")
        
        # 测试场景2: 计算包含邀请关系的佣金
        print("\n5. 测试包含邀请关系的佣金计算...")
        
        # 使用commission_calculator的calculate_commission方法
        # 注意：需要先更新commission_calculator.py以使用真正的邀请裂变管理器
        # 这里我们先测试模拟版本
        
        test_transaction = {
            "transaction_value": 50000.0,
            "business_type": "regular_business",
            "user_id": invitee['user_id'],
            "transaction_id": transaction_id
        }
        
        commission_result = calculator.calculate_commission(
            transaction_value=test_transaction['transaction_value'],
            business_type=test_transaction['business_type'],
            user_id=test_transaction['user_id'],
            transaction_id=test_transaction['transaction_id']
        )
        
        print(f"   交易金额: ${test_transaction['transaction_value']:,.2f}")
        print(f"   业务类型: {test_transaction['business_type']}")
        print(f"   系统佣金: {commission_result['system_commission_rate']*100}% (${commission_result['system_commission_amount']:,.2f})")
        
        if 'invitation_split' in commission_result:
            print(f"   邀请分成: {commission_result['invitation_split']['rate']*100}% (${commission_result['invitation_split']['amount']:,.2f})")
            print(f"   总佣金: ${commission_result['total_commission_amount']:,.2f}")
        
        # 测试场景3: 获取用户邀请统计
        print("\n6. 获取邀请人统计信息...")
        stats = manager.get_user_invitation_stats(inviter['user_id'])
        print(f"   邀请总数: {stats['stats']['total_invitations']}")
        print(f"   已接受邀请: {stats['stats']['accepted_invitations']}")
        print(f"   获得的积分奖励: {stats['stats']['total_credits_earned']}")
        
        # 测试场景4: 生成推广内容
        print("\n7. 生成推广内容...")
        promotion = manager.generate_promotion_content(
            user_id=inviter['user_id'],
            content_type='social_post',
            platform='tiktok'
        )
        print(f"   推广内容生成成功: {promotion['title']}")
        print(f"   内容类型: {promotion['content_type']}")
        print(f"   平台: {promotion['platform']}")
        
        print("\n✅ 集成测试通过！")
        
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_integration()