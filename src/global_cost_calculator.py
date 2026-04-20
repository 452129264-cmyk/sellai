#!/usr/bin/env python3
"""
全球成本测算工具 - 交互式脚本
支持与共享状态库集成，进行多国家成本测算并生成JSON报告
"""

import sys
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import argparse
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 尝试导入共享状态管理器
try:
    from src.shared_state_manager import SharedStateManager, get_system_statistics
except ImportError:
    print("警告：无法导入共享状态管理器，将使用独立模式运行")
    SharedStateManager = None

class GlobalCostCalculator:
    """全球成本测算器"""
    
    # 全球区域定义
    REGIONS = {
        "北美": ["US", "CA", "MX"],
        "欧洲": ["DE", "FR", "GB", "IT", "ES", "NL", "SE"],
        "东南亚": ["SG", "MY", "TH", "ID", "VN", "PH"],
        "中东": ["AE", "SA", "QA", "BH", "OM"],
        "拉美": ["BR", "MX", "AR", "CL", "CO", "PE"],
        "非洲": ["ZA", "NG", "KE", "GH", "EG"]
    }
    
    # 国家默认参数
    COUNTRY_PARAMS = {
        "US": {"logistics_cost": 5.0, "tax_rate": 10.0, "local_ops": 500.0, "shipping_days": 7},
        "DE": {"logistics_cost": 4.5, "tax_rate": 19.0, "local_ops": 450.0, "shipping_days": 5},
        "SG": {"logistics_cost": 3.5, "tax_rate": 7.0, "local_ops": 400.0, "shipping_days": 3},
        "JP": {"logistics_cost": 6.0, "tax_rate": 10.0, "local_ops": 600.0, "shipping_days": 10},
        "GB": {"logistics_cost": 5.5, "tax_rate": 20.0, "local_ops": 550.0, "shipping_days": 7},
        "AU": {"logistics_cost": 8.0, "tax_rate": 10.0, "local_ops": 700.0, "shipping_days": 14},
        "IN": {"logistics_cost": 2.5, "tax_rate": 18.0, "local_ops": 300.0, "shipping_days": 10},
        "CN": {"logistics_cost": 4.0, "tax_rate": 13.0, "local_ops": 400.0, "shipping_days": 10},
    }
    
    # 成本类型单价（美元）
    DEFAULT_UNIT_PRICES = {
        "tokens": 0.000002,
        "workflow_executions": 0.0001,
        "api_calls": 0.01,
        "memory_storage": 0.000023,
    }
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """初始化测算器"""
        self.db_path = db_path
        self.params = self.get_default_params()
        
    def get_default_params(self) -> Dict[str, Any]:
        """获取默认测算参数"""
        return {
            "avatar_count": 10,
            "avg_messages_per_day": 100,
            "operating_countries": ["US", "DE", "SG"],
            "api_unit_price": 0.01,
            "token_unit_price": 0.000002,
            "workflow_unit_price": 0.0001,
            "storage_unit_price": 0.000023,
            "avg_logistics_cost": 5.0,
            "avg_tax_rate": 10.0,
            "local_operations_cost": 500.0,
            "shipping_days": 7,
            "months": 12,
            "currency": "USD"
        }
    
    def load_historical_data(self, days: int = 30) -> Dict[str, Any]:
        """
        从共享状态库加载历史成本数据用于校准
        
        Args:
            days: 最近多少天的数据
            
        Returns:
            历史数据摘要
        """
        if not os.path.exists(self.db_path):
            print(f"数据库文件不存在: {self.db_path}")
            return {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 查询成本记录
            cursor.execute("""
                SELECT 
                    cost_type,
                    SUM(amount) as total_amount,
                    AVG(unit_price) as avg_unit_price,
                    SUM(total_cost) as total_cost
                FROM cost_consumption_logs
                WHERE period_start >= ?
                GROUP BY cost_type
            """, (start_date.isoformat(),))
            
            rows = cursor.fetchall()
            historical = {}
            for row in rows:
                cost_type = row['cost_type']
                historical[cost_type] = {
                    'total_amount': row['total_amount'],
                    'avg_unit_price': row['avg_unit_price'],
                    'total_cost': row['total_cost']
                }
            
            # 查询分身统计
            cursor.execute("SELECT COUNT(*) as count FROM avatar_capability_profiles")
            avatar_count = cursor.fetchone()['count']
            
            conn.close()
            
            return {
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'historical_costs': historical,
                'avatar_count': avatar_count
            }
        except Exception as e:
            print(f"加载历史数据失败: {e}")
            return {}
    
    def calculate_costs(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        计算全球成本
        
        Args:
            params: 测算参数，如未提供则使用默认参数
            
        Returns:
            测算结果
        """
        if params is None:
            params = self.params
        
        # 提取参数
        avatar_count = params['avatar_count']
        avg_messages = params['avg_messages_per_day']
        countries = params['operating_countries']
        months = params['months']
        
        # 计算每个国家的分身分配（按国家数量平均分配）
        country_allocations = {}
        base_per_country = avatar_count // len(countries)
        remainder = avatar_count % len(countries)
        
        for i, country in enumerate(countries):
            count = base_per_country
            if i < remainder:
                count += 1
            country_allocations[country] = count
        
        # 计算每个国家的成本明细
        country_details = {}
        total_costs = {
            'api_calls': 0.0,
            'tokens': 0.0,
            'workflow_executions': 0.0,
            'storage': 0.0,
            'logistics': 0.0,
            'tax': 0.0,
            'local_operations': 0.0,
            'total': 0.0
        }
        
        for country, avatar_count in country_allocations.items():
            # 获取国家特定参数
            country_param = self.COUNTRY_PARAMS.get(country, {
                'logistics_cost': params['avg_logistics_cost'],
                'tax_rate': params['avg_tax_rate'],
                'local_ops': params['local_operations_cost'],
                'shipping_days': params['shipping_days']
            })
            
            # API调用成本（假设每个消息触发1次API调用）
            api_calls = avatar_count * avg_messages * 30 * months
            api_cost = api_calls * params['api_unit_price']
            
            # Token成本（假设每个消息消耗1000 tokens）
            tokens = avatar_count * avg_messages * 1000 * 30 * months
            token_cost = tokens * params['token_unit_price']
            
            # 工作流执行成本（假设每个分身每天执行50次工作流）
            workflows = avatar_count * 50 * 30 * months
            workflow_cost = workflows * params['workflow_unit_price']
            
            # 存储成本（假设每个分身占用2GB存储）
            storage = avatar_count * 2 * months
            storage_cost = storage * params['storage_unit_price']
            
            # 物流成本（假设每个分身每月产生10个订单）
            logistics_orders = avatar_count * 10 * months
            logistics_cost = logistics_orders * country_param['logistics_cost']
            
            # 关税成本（基于物流成本）
            tax_cost = logistics_cost * (country_param['tax_rate'] / 100)
            
            # 本地运营费用
            local_ops_cost = country_param['local_ops'] * months
            
            # 国家总成本
            country_total = (
                api_cost + token_cost + workflow_cost + 
                storage_cost + logistics_cost + tax_cost + local_ops_cost
            )
            
            country_details[country] = {
                'avatar_count': avatar_count,
                'api_calls': api_calls,
                'api_cost': api_cost,
                'tokens': tokens,
                'token_cost': token_cost,
                'workflow_executions': workflows,
                'workflow_cost': workflow_cost,
                'storage_gb': storage,
                'storage_cost': storage_cost,
                'logistics_orders': logistics_orders,
                'logistics_cost': logistics_cost,
                'tax_rate': country_param['tax_rate'],
                'tax_cost': tax_cost,
                'local_operations_cost': local_ops_cost,
                'total_cost': country_total,
                'shipping_days': country_param['shipping_days']
            }
            
            # 累加总成本
            total_costs['api_calls'] += api_cost
            total_costs['tokens'] += token_cost
            total_costs['workflow_executions'] += workflow_cost
            total_costs['storage'] += storage_cost
            total_costs['logistics'] += logistics_cost
            total_costs['tax'] += tax_cost
            total_costs['local_operations'] += local_ops_cost
            total_costs['total'] += country_total
        
        # 生成优化建议
        optimization_suggestions = self.generate_optimization_suggestions(
            params, country_details, total_costs
        )
        
        # 计算关键指标
        cost_per_avatar = total_costs['total'] / avatar_count if avatar_count > 0 else 0
        cost_per_month = total_costs['total'] / months if months > 0 else 0
        cost_per_message = total_costs['total'] / (avatar_count * avg_messages * 30 * months) if avatar_count * avg_messages * 30 * months > 0 else 0
        
        return {
            'calculation_timestamp': datetime.now().isoformat(),
            'input_parameters': params,
            'country_allocations': country_allocations,
            'country_details': country_details,
            'cost_breakdown': total_costs,
            'key_metrics': {
                'total_cost_usd': total_costs['total'],
                'cost_per_avatar_usd': cost_per_avatar,
                'cost_per_month_usd': cost_per_month,
                'cost_per_message_usd': cost_per_message,
                'avatar_count': sum(country_allocations.values()),
                'operating_months': months,
                'total_messages': avatar_count * avg_messages * 30 * months
            },
            'optimization_suggestions': optimization_suggestions,
            'historical_calibration': self.load_historical_data(30)
        }
    
    def generate_optimization_suggestions(self, params: Dict[str, Any], 
                                        country_details: Dict[str, Dict[str, Any]],
                                        total_costs: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        生成成本优化建议
        
        Returns:
            优化建议列表
        """
        suggestions = []
        
        # 分析成本构成
        total = total_costs['total']
        if total == 0:
            return suggestions
        
        # 1. 物流成本优化建议
        logistics_percent = (total_costs['logistics'] / total) * 100
        if logistics_percent > 15:
            suggestions.append({
                'category': '物流优化',
                'title': '降低物流成本占比',
                'description': f'当前物流成本占比{logistics_percent:.1f}%，建议考虑：1) 使用集中仓储 2) 与物流商谈判批量折扣 3) 优化包装减少重量',
                'estimated_saving_percent': 20,
                'implementation_difficulty': '中'
            })
        
        # 2. 关税优化建议
        tax_percent = (total_costs['tax'] / total) * 100
        if tax_percent > 10:
            suggestions.append({
                'category': '关税优化',
                'title': '利用自由贸易协定',
                'description': f'当前关税成本占比{tax_percent:.1f}%，建议：1) 研究目标国家的自由贸易协定 2) 优化商品分类 3) 考虑在低关税地区设立分公司',
                'estimated_saving_percent': 30,
                'implementation_difficulty': '高'
            })
        
        # 3. 分身分布优化
        # 找出成本最高的国家
        country_costs = [(country, details['total_cost']) for country, details in country_details.items()]
        country_costs.sort(key=lambda x: x[1], reverse=True)
        
        if len(country_costs) > 1:
            highest_country, highest_cost = country_costs[0]
            lowest_country, lowest_cost = country_costs[-1]
            cost_ratio = highest_cost / lowest_cost if lowest_cost > 0 else 1
            
            if cost_ratio > 1.5:
                suggestions.append({
                    'category': '地域优化',
                    'title': '调整分身地域分布',
                    'description': f'{highest_country}的成本是{lowest_country}的{cost_ratio:.1f}倍，建议将更多分身部署到低成本区域',
                    'estimated_saving_percent': 15,
                    'implementation_difficulty': '低'
                })
        
        # 4. 消息频率优化
        avg_messages = params['avg_messages_per_day']
        if avg_messages > 150:
            suggestions.append({
                'category': '效率优化',
                'title': '优化消息处理效率',
                'description': f'当前平均消息频率{avg_messages}条/天/分身，建议：1) 使用消息批量处理 2) 优化工作流减少冗余步骤 3) 设置消息优先级',
                'estimated_saving_percent': 10,
                'implementation_difficulty': '中'
            })
        
        # 5. 存储成本优化
        storage_percent = (total_costs['storage'] / total) * 100
        if storage_percent > 5:
            suggestions.append({
                'category': '存储优化',
                'title': '压缩存储数据',
                'description': f'当前存储成本占比{storage_percent:.1f}%，建议：1) 使用数据压缩 2) 定期清理历史数据 3) 使用低成本存储方案',
                'estimated_saving_percent': 40,
                'implementation_difficulty': '低'
            })
        
        return suggestions
    
    def calculate_comparison_scenarios(self, base_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算不同场景的成本对比
        
        Args:
            base_params: 基础参数
            
        Returns:
            场景对比结果
        """
        scenarios = {
            '基础场景': base_params,
            '低成本国家': base_params.copy(),
            '高扩张': base_params.copy(),
            '成本优化': base_params.copy()
        }
        
        # 场景1: 低成本国家（只在新加坡和德国运营）
        scenarios['低成本国家']['operating_countries'] = ['SG', 'DE']
        
        # 场景2: 高扩张（分身数量翻倍）
        scenarios['高扩张']['avatar_count'] = base_params['avatar_count'] * 2
        
        # 场景3: 成本优化（降低消息频率，使用更便宜的API）
        scenarios['成本优化']['avg_messages_per_day'] = max(50, base_params['avg_messages_per_day'] * 0.7)
        scenarios['成本优化']['api_unit_price'] = base_params['api_unit_price'] * 0.8
        scenarios['成本优化']['token_unit_price'] = base_params['token_unit_price'] * 0.9
        
        # 计算每个场景
        results = {}
        for scenario_name, scenario_params in scenarios.items():
            results[scenario_name] = self.calculate_costs(scenario_params)
        
        return results
    
    def save_report(self, result: Dict[str, Any], output_dir: str = "outputs/成本控制") -> str:
        """
        保存测算报告为JSON文件
        
        Args:
            result: 测算结果
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"全球成本测算报告_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"测算报告已保存: {filepath}")
        return filepath
    
    def interactive_input(self) -> Dict[str, Any]:
        """
        交互式输入参数
        
        Returns:
            输入的参数
        """
        print("\n" + "="*60)
        print("全球成本测算工具 - 参数输入")
        print("="*60)
        
        params = self.get_default_params()
        
        print("\n1. 基本参数")
        print(f"   当前目标分身数量: {params['avatar_count']}")
        try:
            avatar_count = int(input("   请输入新的目标分身数量 (默认10): ") or "10")
            params['avatar_count'] = max(1, avatar_count)
        except ValueError:
            print("   输入无效，使用默认值10")
        
        print(f"\n   当前平均消息频率: {params['avg_messages_per_day']} 条/天/分身")
        try:
            messages = int(input("   请输入平均消息频率 (默认100): ") or "100")
            params['avg_messages_per_day'] = max(1, messages)
        except ValueError:
            print("   输入无效，使用默认值100")
        
        print(f"\n   当前运营月份: {params['months']} 个月")
        try:
            months = int(input("   请输入运营月份 (默认12): ") or "12")
            params['months'] = max(1, months)
        except ValueError:
            print("   输入无效，使用默认值12")
        
        print("\n2. 国家选择")
        print("   可选的全球区域:")
        for i, region in enumerate(self.REGIONS.keys(), 1):
            countries = self.REGIONS[region]
            print(f"   {i}. {region}: {', '.join(countries)}")
        
        print(f"\n   当前运营国家: {', '.join(params['operating_countries'])}")
        country_input = input("   请输入国家代码（用逗号分隔，如 US,DE,SG）: ")
        if country_input.strip():
            countries = [c.strip().upper() for c in country_input.split(',')]
            # 验证国家代码
            valid_countries = []
            all_countries = []
            for region_countries in self.REGIONS.values():
                all_countries.extend(region_countries)
            
            for country in countries:
                if country in all_countries:
                    valid_countries.append(country)
                else:
                    print(f"   警告: 国家代码 {country} 不在支持列表中，已跳过")
            
            if valid_countries:
                params['operating_countries'] = valid_countries
        
        print("\n3. 成本参数")
        print(f"   API调用单价: ${params['api_unit_price']:.4f}/次")
        try:
            api_price = float(input("   请输入API调用单价 (默认0.01): ") or "0.01")
            params['api_unit_price'] = max(0.0001, api_price)
        except ValueError:
            print("   输入无效，使用默认值0.01")
        
        print(f"\n   Token单价: ${params['token_unit_price']:.6f}/token")
        try:
            token_price = float(input("   请输入Token单价 (默认0.000002): ") or "0.000002")
            params['token_unit_price'] = max(0.0000001, token_price)
        except ValueError:
            print("   输入无效，使用默认值0.000002")
        
        print(f"\n   平均物流成本: ${params['avg_logistics_cost']:.2f}/订单")
        try:
            logistics = float(input("   请输入平均物流成本 (默认5.0): ") or "5.0")
            params['avg_logistics_cost'] = max(0.1, logistics)
        except ValueError:
            print("   输入无效，使用默认值5.0")
        
        print(f"\n   平均关税税率: {params['avg_tax_rate']:.1f}%")
        try:
            tax_rate = float(input("   请输入平均关税税率 (默认10.0): ") or "10.0")
            params['avg_tax_rate'] = max(0.0, min(100.0, tax_rate))
        except ValueError:
            print("   输入无效，使用默认值10.0")
        
        return params

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='全球成本测算工具')
    parser.add_argument('--mode', choices=['interactive', 'quick', 'scenarios', 'calibrate'], 
                       default='interactive', help='运行模式')
    parser.add_argument('--output', default='outputs/成本控制', help='输出目录')
    parser.add_argument('--params', help='JSON格式的参数文件')
    
    args = parser.parse_args()
    
    # 创建测算器
    calculator = GlobalCostCalculator()
    
    # 加载参数（如有）
    if args.params and os.path.exists(args.params):
        with open(args.params, 'r') as f:
            custom_params = json.load(f)
        calculator.params.update(custom_params)
    
    print("\n" + "="*60)
    print("全域无边界·全球商业大脑 - 成本控制工具")
    print("="*60)
    
    if args.mode == 'interactive':
        # 交互式模式
        params = calculator.interactive_input()
        result = calculator.calculate_costs(params)
        
        # 显示摘要
        print("\n" + "="*60)
        print("测算结果摘要")
        print("="*60)
        
        metrics = result['key_metrics']
        print(f"总成本: ${metrics['total_cost_usd']:,.2f} USD")
        print(f"分身数量: {metrics['avatar_count']} 个")
        print(f"运营周期: {metrics['operating_months']} 个月")
        print(f"每个分身成本: ${metrics['cost_per_avatar_usd']:,.2f} USD")
        print(f"每月成本: ${metrics['cost_per_month_usd']:,.2f} USD")
        print(f"每条消息成本: ${metrics['cost_per_message_usd']:.6f} USD")
        
        # 显示国家详情
        print("\n国家成本详情:")
        for country, details in result['country_details'].items():
            print(f"  {country}: {details['avatar_count']}个分身, ${details['total_cost']:,.2f}")
        
        # 显示优化建议
        suggestions = result['optimization_suggestions']
        if suggestions:
            print(f"\n优化建议 ({len(suggestions)}条):")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. [{suggestion['category']}] {suggestion['title']}")
                print(f"     预计节省: {suggestion['estimated_saving_percent']}%")
        
        # 保存报告
        report_path = calculator.save_report(result, args.output)
        
        print(f"\n详细报告已保存至: {report_path}")
        print("您可以通过Excel模板进一步分析和优化成本。")
    
    elif args.mode == 'quick':
        # 快速模式使用默认参数
        print("\n快速模式 - 使用默认参数")
        result = calculator.calculate_costs()
        report_path = calculator.save_report(result, args.output)
        
        print(f"测算完成，报告保存至: {report_path}")
    
    elif args.mode == 'scenarios':
        # 多场景对比
        print("\n多场景对比模式")
        scenarios = calculator.calculate_comparison_scenarios(calculator.params)
        
        # 汇总对比
        print("\n场景对比结果:")
        print("-" * 80)
        print(f"{'场景':<15} {'总成本(USD)':>15} {'分身数量':>12} {'成本/分身':>15}")
        print("-" * 80)
        
        for scenario_name, scenario_result in scenarios.items():
            metrics = scenario_result['key_metrics']
            print(f"{scenario_name:<15} ${metrics['total_cost_usd']:>14,.2f} "
                  f"{metrics['avatar_count']:>12} ${metrics['cost_per_avatar_usd']:>14,.2f}")
        
        # 保存所有场景
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scenario_file = os.path.join(args.output, f"多场景对比报告_{timestamp}.json")
        with open(scenario_file, 'w', encoding='utf-8') as f:
            json.dump(scenarios, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细对比报告已保存: {scenario_file}")
    
    elif args.mode == 'calibrate':
        # 校准模式：加载历史数据并校准模型
        print("\n校准模式 - 基于历史数据调整参数")
        historical = calculator.load_historical_data(90)
        
        if historical and historical.get('historical_costs'):
            print(f"加载到 {historical['period_days']} 天的历史数据")
            
            # 显示历史成本
            for cost_type, data in historical['historical_costs'].items():
                print(f"  {cost_type}: {data['total_amount']:.0f}单位, 总成本${data['total_cost']:.2f}")
            
            # 基于历史数据调整默认单价
            for cost_type, data in historical['historical_costs'].items():
                if data['total_amount'] > 0:
                    actual_price = data['total_cost'] / data['total_amount']
                    if cost_type in calculator.DEFAULT_UNIT_PRICES:
                        old_price = calculator.DEFAULT_UNIT_PRICES[cost_type]
                        print(f"  {cost_type}: 历史单价${actual_price:.6f}, 原默认${old_price:.6f}")
                        # 使用历史平均单价作为新默认
                        calculator.params[f'{cost_type}_unit_price'] = actual_price
        else:
            print("未找到足够的历史数据，使用默认参数")
        
        # 使用校准后的参数进行测算
        result = calculator.calculate_costs()
        report_path = calculator.save_report(result, args.output)
        
        print(f"\n校准后的测算报告已保存: {report_path}")
    
    print("\n" + "="*60)
    print("全球成本测算完成")
    print("="*60)

if __name__ == "__main__":
    main()