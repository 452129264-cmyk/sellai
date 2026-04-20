#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')
from src.global_cost_calculator import GlobalCostCalculator
import json

def test_5_countries():
    """测试5个国家（US, DE, SG, JP, CN）的成本测算支持"""
    calculator = GlobalCostCalculator()
    
    expected_countries = ['US', 'DE', 'SG', 'JP', 'CN']
    
    # 检查COUNTRY_PARAMS
    missing_in_params = []
    for country in expected_countries:
        if country not in calculator.COUNTRY_PARAMS:
            missing_in_params.append(country)
    
    if missing_in_params:
        print(f"⚠️  以下国家不在COUNTRY_PARAMS中: {missing_in_params}")
        print(f"   现有国家: {list(calculator.COUNTRY_PARAMS.keys())}")
    else:
        print(f"✅ 所有5个国家都在COUNTRY_PARAMS中")
    
    # 测试成本测算
    params = {
        'avatar_count': 10,
        'avg_messages_per_day': 100,
        'operating_countries': expected_countries,
        'months': 1,
        'currency': 'USD'
    }
    
    try:
        result = calculator.calculate_costs(params)
        print(f"✅ 5国成本测算成功")
        print(f"   总成本: {result['total_cost_usd']} USD")
        
        # 检查国家详情
        country_details = result.get('country_details', {})
        detail_countries = list(country_details.keys())
        print(f"   包含的国家详情: {detail_countries}")
        
        missing_in_details = list(set(expected_countries) - set(detail_countries))
        if missing_in_details:
            print(f"❌ 以下国家在结果中缺失: {missing_in_details}")
            return False
        else:
            print(f"✅ 所有5个国家都有成本详情")
            
        # 检查成本构成
        for country, detail in country_details.items():
            print(f"   {country}: 总成本={detail.get('total_cost', 'N/A')} USD")
        
        return True
    except Exception as e:
        print(f"❌ 5国成本测算失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_5_countries()
    sys.exit(0 if success else 1)