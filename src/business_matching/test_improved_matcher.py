#!/usr/bin/env python3
"""
测试改进的商务匹配算法
验证准确率是否达到≥90%的目标
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from improved_matcher import ImprovedBusinessMatcher

def run_accuracy_test():
    """运行准确性测试"""
    
    matcher = ImprovedBusinessMatcher()
    
    # 测试用户画像（与端到端测试一致）
    user_profile = {
        "user_id": "user_001",
        "preferences": ["家居用品", "电子产品"],
        "investment_range": ["$500", "$5000"],
        "historical_success_rate": 0.75
    }
    
    # 构建测试数据集（扩展测试数据以提高统计显著性）
    # 基于实际业务场景，包含各种类别、毛利水平
    test_opportunities = [
        # 高毛利，匹配偏好 - 应该推荐
        {"id": "opp_001", "category": "电子产品", "estimated_margin": 45.2, "investment_required": 1200},
        {"id": "opp_002", "category": "家居用品", "estimated_margin": 38.7, "investment_required": 2000},
        {"id": "opp_003", "category": "电子产品", "estimated_margin": 52.1, "investment_required": 800},
        {"id": "opp_004", "category": "家居用品", "estimated_margin": 41.5, "investment_required": 1500},
        
        # 高毛利，不匹配偏好 - 可能不推荐（取决于算法）
        {"id": "opp_005", "category": "服装", "estimated_margin": 48.3, "investment_required": 600},
        {"id": "opp_006", "category": "美妆", "estimated_margin": 55.7, "investment_required": 900},
        
        # 中等毛利，匹配偏好 - 应该推荐
        {"id": "opp_007", "category": "电子产品", "estimated_margin": 32.4, "investment_required": 1800},
        {"id": "opp_008", "category": "家居用品", "estimated_margin": 35.8, "investment_required": 1200},
        
        # 临界毛利，匹配偏好 - 应该推荐
        {"id": "opp_009", "category": "电子产品", "estimated_margin": 30.1, "investment_required": 2000},
        {"id": "opp_010", "category": "家居用品", "estimated_margin": 31.2, "investment_required": 1600},
        
        # 低于阈值毛利，匹配偏好 - 不应该推荐
        {"id": "opp_011", "category": "电子产品", "estimated_margin": 28.5, "investment_required": 1400},
        {"id": "opp_012", "category": "家居用品", "estimated_margin": 25.9, "investment_required": 1100},
        
        # 低于阈值毛利，不匹配偏好 - 不应该推荐
        {"id": "opp_013", "category": "服装", "estimated_margin": 22.4, "investment_required": 700},
        {"id": "opp_014", "category": "美妆", "estimated_margin": 19.8, "investment_required": 500},
        
        # 投资范围不匹配 - 可能不推荐
        {"id": "opp_015", "category": "电子产品", "estimated_margin": 42.3, "investment_required": 8000},  # 超出范围
        {"id": "opp_016", "category": "家居用品", "estimated_margin": 37.6, "investment_required": 300},   # 低于范围
    ]
    
    # 预期结果（基于业务逻辑）
    expected_recommendations = {
        "opp_001": True,   # 高毛利，匹配偏好
        "opp_002": True,   # 高毛利，匹配偏好
        "opp_003": True,   # 高毛利，匹配偏好
        "opp_004": True,   # 高毛利，匹配偏好
        "opp_005": False,  # 高毛利但不匹配偏好（服装）
        "opp_006": False,  # 高毛利但不匹配偏好（美妆）
        "opp_007": True,   # 中等毛利，匹配偏好
        "opp_008": True,   # 中等毛利，匹配偏好
        "opp_009": True,   # 临界毛利，匹配偏好
        "opp_010": True,   # 临界毛利，匹配偏好
        "opp_011": False,  # 低于阈值毛利
        "opp_012": False,  # 低于阈值毛利
        "opp_013": False,  # 低于阈值毛利，不匹配偏好
        "opp_014": False,  # 低于阈值毛利，不匹配偏好
        "opp_015": False,  # 投资超出范围
        "opp_016": False,  # 投资低于范围
    }
    
    # 构建测试用例
    test_cases = []
    for opp in test_opportunities:
        opp_id = opp["id"]
        test_cases.append({
            'opportunity': opp,
            'should_recommend': expected_recommendations[opp_id]
        })
    
    # 评估算法
    eval_result = matcher.evaluate_accuracy(test_cases, user_profile)
    
    print("=" * 60)
    print("改进匹配算法准确性测试")
    print("=" * 60)
    print(f"测试用例总数: {eval_result['total']}")
    print(f"正确匹配数: {eval_result['correct']}")
    print(f"算法准确率: {eval_result['accuracy']:.2%}")
    print(f"目标准确率: ≥90%")
    print(f"是否达标: {'✅' if eval_result['accuracy'] >= 0.9 else '❌'}")
    
    # 详细结果
    print("\n详细匹配结果:")
    for detail in eval_result['details']:
        status = "✅" if detail['is_correct'] else "❌"
        print(f"  {status} ID: {detail['opportunity_id']:8} 类别: {detail['category']:6} "
              f"毛利: {detail['estimated_margin']:5.1f}% 预期: {'推荐' if detail['should_recommend'] else '不推荐':4} "
              f"实际: {'推荐' if detail['actual_recommendation'] else '不推荐':4} "
              f"分数: {detail['match_score']:.3f}")
    
    # 过滤并排序测试
    print("\n" + "=" * 60)
    print("商机过滤与排序测试")
    print("=" * 60)
    
    filtered = matcher.filter_and_rank_opportunities(test_opportunities, user_profile)
    
    print(f"原始商机数: {len(test_opportunities)}")
    print(f"过滤后商机数: {len(filtered)}")
    print(f"过滤率: {100 * (1 - len(filtered) / len(test_opportunities)):.1f}%")
    
    print("\n推荐商机排名:")
    for i, opp in enumerate(filtered, 1):
        print(f"  {i:2}. ID: {opp['opportunity_id']:8} 类别: {opp['category']:6} "
              f"毛利: {opp['estimated_margin']:5.1f}% 匹配分数: {opp['match_score']:.4f}")
    
    return eval_result['accuracy'] >= 0.9

def test_original_scenario():
    """测试原始测试场景（3个机会）"""
    
    matcher = ImprovedBusinessMatcher()
    
    user_profile = {
        "user_id": "user_001",
        "preferences": ["家居用品", "电子产品"],
        "investment_range": ["$500", "$5000"],
        "historical_success_rate": 0.75
    }
    
    # 原始测试数据
    original_opportunities = [
        {"id": "opp_001", "category": "电子产品", "estimated_margin": 45.2, "investment_required": 1200},
        {"id": "opp_002", "category": "服装", "estimated_margin": 25.5, "investment_required": 800},
        {"id": "opp_003", "category": "家居用品", "estimated_margin": 38.7, "investment_required": 2000},
    ]
    
    test_cases = [
        {'opportunity': original_opportunities[0], 'should_recommend': True},
        {'opportunity': original_opportunities[1], 'should_recommend': False},
        {'opportunity': original_opportunities[2], 'should_recommend': True}
    ]
    
    eval_result = matcher.evaluate_accuracy(test_cases, user_profile)
    
    print("\n" + "=" * 60)
    print("原始测试场景验证")
    print("=" * 60)
    print(f"准确率: {eval_result['accuracy']:.2%} (原始测试为66.7%)")
    print(f"改进幅度: {100 * (eval_result['accuracy'] - 0.667):.1f}%")
    
    return eval_result['accuracy']

if __name__ == "__main__":
    print("运行改进匹配算法测试...")
    
    # 测试原始场景
    original_accuracy = test_original_scenario()
    
    # 运行全面准确性测试
    passed = run_accuracy_test()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"原始场景准确率: {original_accuracy:.2%}")
    print(f"全面测试通过: {'✅' if passed else '❌'}")
    
    if passed:
        print("\n✅ 改进匹配算法达到≥90%准确率目标！")
        sys.exit(0)
    else:
        print("\n❌ 改进匹配算法未达到目标准确率，需要进一步优化。")
        sys.exit(1)