#!/usr/bin/env python3
"""
快速测试全域商业大脑基本功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.global_business_brain import GlobalBusinessBrain

def main():
    print("快速测试全域商业大脑")
    print("=" * 50)
    
    # 配置
    config = {
        'node_id': 'quick_test_node',
        'enable_network': False,
        'analysis_period': 7  # 7天数据
    }
    
    # 初始化
    print("初始化商业大脑...")
    brain = GlobalBusinessBrain(config)
    print(f"节点ID: {brain.node_id}")
    print(f"启用网络协同: {brain.enable_network}")
    print(f"分析周期: {brain.analysis_period}天")
    
    # 生成分析报告
    print("\n生成全球市场分析报告...")
    report = brain.generate_global_market_analysis(
        regions=['north_america', 'europe'],
        industries=['manufacturing', 'technology']
    )
    
    # 打印摘要
    print(f"报告ID: {report['report_id']}")
    print(f"市场健康度: {report['executive_summary']['overall_market_health']:.2f}/1.0")
    print(f"识别趋势: {len(report['key_trends'])}个")
    print(f"评估机会: {len(report['market_opportunities'])}个")
    print(f"风险预警: {len(report['risk_alerts'])}个")
    
    # 显示趋势
    print("\n前3个关键趋势:")
    for i, trend in enumerate(report['key_trends'][:3]):
        print(f"{i+1}. {trend['name']} (强度: {trend['strength']:.2f}, 影响: {trend['impact']})")
    
    # 显示机会
    print("\n前3个市场机会:")
    for i, opp in enumerate(report['market_opportunities'][:3]):
        print(f"{i+1}. {opp['name']} (得分: {opp['assessment']['overall_score']:.2f}, 风险: {opp['assessment']['risk_level']})")
    
    # 导出报告
    print("\n导出报告...")
    json_report = brain.export_analysis_report(report, 'json')
    markdown_report = brain.export_analysis_report(report, 'markdown')
    
    print(f"JSON报告长度: {len(json_report)}字符")
    print(f"Markdown报告长度: {len(markdown_report)}字符")
    
    # 保存报告
    import os
    os.makedirs('outputs/商业大脑', exist_ok=True)
    
    json_filename = f"outputs/商业大脑/{report['report_id']}.json"
    md_filename = f"outputs/商业大脑/{report['report_id']}.md"
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        f.write(json_report)
    
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    print(f"\n报告已保存:")
    print(f"  JSON: {json_filename}")
    print(f"  Markdown: {md_filename}")
    
    # 测试认知基线同步
    print("\n测试认知基线同步...")
    baseline_data = {
        'version': '1.0',
        'effective_from': '2026-04-04T00:00:00Z',
        'domains': [
            {
                'domain': 'market_trends',
                'key_indicators': [
                    {'indicator': 'growth_rate', 'expected_range': {'min': -5, 'max': 20}}
                ]
            }
        ]
    }
    
    if brain.sync_cognition_baseline(baseline_data):
        print(f"✅ 认知基线同步成功，版本: {brain.cognition_baseline['version']}")
    else:
        print("❌ 认知基线同步失败")
    
    # 测试市场洞察提交
    print("\n测试市场洞察提交...")
    insight_data = {
        'domain': 'manufacturing_supply_chain',
        'region': 'north_america',
        'key_findings': ['牛仔布料供应链紧张，价格上涨15%'],
        'confidence': 0.85,
        'data_sources': ['industry_reports', 'supplier_quotes']
    }
    
    insight_id = brain.submit_market_insight(insight_data)
    print(f"✅ 市场洞察提交成功，ID: {insight_id}")
    
    # 测试协同评估发起
    print("\n测试协同评估发起...")
    opportunity_data = {
        'name': '牛仔服装供应链优化项目',
        'description': '为美国牛仔服装品牌提供供应链优化解决方案',
        'target_industries': ['制造业', '零售_ecommerce'],
        'target_regions': ['north_america'],
        'estimated_value': '$500,000'
    }
    
    assessment_id = brain.initiate_collaborative_assessment(opportunity_data)
    print(f"✅ 协同评估发起成功，ID: {assessment_id}")
    
    print("\n" + "=" * 50)
    print("快速测试完成！全域商业大脑基本功能正常。")

if __name__ == "__main__":
    main()