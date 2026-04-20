#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')
from src.global_cost_calculator import GlobalCostCalculator

def test_japan_support():
    """测试日本成本测算支持"""
    calculator = GlobalCostCalculator()
    
    # 检查国家参数
    if 'JP' not in calculator.COUNTRY_PARAMS:
        print("❌ JP不在COUNTRY_PARAMS中")
        return False
    
    print(f"✅ JP在COUNTRY_PARAMS中: {calculator.COUNTRY_PARAMS['JP']}")
    
    # 测试日本成本测算
    params = {
        'avatar_count': 5,
        'avg_messages_per_day': 100,
        'operating_countries': ['JP'],
        'months': 1,
        'currency': 'USD'
    }
    
    try:
        result = calculator.calculate_costs(params)
        print(f"✅ 日本成本测算成功")
        print(f"   总成本: {result['total_cost_usd']} USD")
        print(f"   国家详情: {list(result['country_details'].keys())}")
        
        if 'JP' in result['country_details']:
            print(f"✅ JP成本详情可用")
            return True
        else:
            print("❌ JP成本详情缺失")
            return False
    except Exception as e:
        print(f"❌ 日本成本测算失败: {e}")
        return False

if __name__ == '__main__':
    success = test_japan_support()
    sys.exit(0 if success else 1)