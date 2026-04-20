#!/usr/bin/env python3
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.global_cost_calculator import GlobalCostCalculator

def validate_single_country(country_code):
    """验证单个国家的成本测算"""
    calculator = GlobalCostCalculator()
    params = calculator.get_default_params()
    # 只设置一个国家
    params['operating_countries'] = [country_code]
    
    try:
        result = calculator.calculate_costs(params)
        
        # 检查结果
        if country_code not in result['country_details']:
            return False, f"国家 {country_code} 未出现在结果中"
        
        country_detail = result['country_details'][country_code]
        
        # 基本验证
        checks = []
        if country_detail['avatar_count'] <= 0:
            checks.append("分身数量非正数")
        if country_detail['total_cost'] <= 0:
            checks.append("总成本非正数")
        if country_detail['logistics_cost'] < 0:
            checks.append("物流成本为负")
        if country_detail['tax_cost'] < 0:
            checks.append("关税成本为负")
        
        # 验证国家参数是否使用预设值
        expected_params = calculator.COUNTRY_PARAMS.get(country_code, {})
        if expected_params:
            actual_logistics = country_detail['logistics_cost'] / (country_detail['logistics_orders'] if country_detail['logistics_orders'] > 0 else 1)
            expected_logistics = expected_params['logistics_cost']
            logistics_error = abs(actual_logistics - expected_logistics) / expected_logistics * 100 if expected_logistics > 0 else 0
            
            actual_tax_rate = country_detail['tax_rate']
            expected_tax_rate = expected_params['tax_rate']
            tax_error = abs(actual_tax_rate - expected_tax_rate) / expected_tax_rate * 100 if expected_tax_rate > 0 else 0
            
            if logistics_error > 20:
                checks.append(f"物流成本误差率{logistics_error:.1f}% > 20%")
            if tax_error > 20:
                checks.append(f"关税税率误差率{tax_error:.1f}% > 20%")
        
        if checks:
            return False, "; ".join(checks)
        else:
            return True, "验证通过"
            
    except Exception as e:
        return False, f"计算异常: {str(e)}"

def main():
    # 需要验证的五个国家
    target_countries = ['US', 'DE', 'SG', 'JP', 'CN']
    
    validation_results = {}
    all_passed = True
    
    print("开始五国成本测算验证...")
    print("="*60)
    
    for country in target_countries:
        print(f"验证国家 {country}...")
        passed, message = validate_single_country(country)
        validation_results[country] = {
            'passed': passed,
            'message': message
        }
        
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {status}: {message}")
        
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    print("验证总结:")
    
    for country, result in validation_results.items():
        print(f"  {country}: {'通过' if result['passed'] else '失败'} - {result['message']}")
    
    # 生成验证报告
    report = {
        'validation_timestamp': '2026-04-03T18:45:00',
        'target_countries': target_countries,
        'validation_results': validation_results,
        'overall_passed': all_passed,
        'tool_version': '1.1',
        'notes': '验证包括基本计算正确性、参数使用准确性、误差率≤20%等检查'
    }
    
    # 保存报告
    os.makedirs('outputs/成本控制', exist_ok=True)
    report_path = 'outputs/成本控制/五国参数完整验证报告_20260403.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n验证报告已保存: {report_path}")
    
    if all_passed:
        print("\n✅ 所有国家验证通过，成本控制工具参数完整。")
        return 0
    else:
        print("\n❌ 部分国家验证失败，请检查参数配置。")
        return 1

if __name__ == '__main__':
    sys.exit(main())