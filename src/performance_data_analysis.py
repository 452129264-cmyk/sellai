"""
SellAI系统性能数据分析脚本
基于共享状态库中的实际运行数据，分析分身协同效率与资源使用情况
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP']
plt.rcParams['axes.unicode_minus'] = False

class PerformanceDataAnalyzer:
    def __init__(self, db_path='data/shared_state/state.db'):
        """初始化分析器，连接到数据库"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.analysis_results = {}
        
    def analyze_task_completion_metrics(self):
        """分析任务完成指标"""
        print("=== 任务完成指标分析 ===")
        
        # 读取任务分配表
        query = """
        SELECT assignment_id, opportunity_hash, assigned_avatar, 
               assignment_time, completion_status, completion_time
        FROM task_assignments
        ORDER BY assignment_time
        """
        
        df = pd.read_sql_query(query, self.conn)
        print(f"总任务数: {len(df)}")
        
        # 计算完成率
        completed_tasks = df[df['completion_status'] == 'completed']
        pending_tasks = df[df['completion_status'] == 'pending']
        
        completion_rate = len(completed_tasks) / len(df) * 100 if len(df) > 0 else 0
        
        print(f"已完成任务数: {len(completed_tasks)}")
        print(f"待处理任务数: {len(pending_tasks)}")
        print(f"任务完成率: {completion_rate:.1f}%")
        
        # 计算任务处理时间（如果有完成时间）
        if len(completed_tasks) > 0:
            completed_tasks['assignment_time'] = pd.to_datetime(completed_tasks['assignment_time'])
            completed_tasks['completion_time'] = pd.to_datetime(completed_tasks['completion_time'])
            completed_tasks['processing_time_seconds'] = (
                completed_tasks['completion_time'] - completed_tasks['assignment_time']
            ).dt.total_seconds()
            
            avg_processing_time = completed_tasks['processing_time_seconds'].mean()
            print(f"平均任务处理时间: {avg_processing_time:.2f}秒")
        else:
            avg_processing_time = None
            
        self.analysis_results['task_metrics'] = {
            'total_tasks': len(df),
            'completed_tasks': len(completed_tasks),
            'pending_tasks': len(pending_tasks),
            'completion_rate': completion_rate,
            'avg_processing_time': avg_processing_time
        }
        
        return df
    
    def analyze_communication_efficiency(self):
        """分析通信效率"""
        print("\n=== 通信效率分析 ===")
        
        query = """
        SELECT operation_type, source_node, target_node, 
               message_size_bytes, processing_time_ms, timestamp
        FROM communication_metrics
        ORDER BY timestamp
        """
        
        df = pd.read_sql_query(query, self.conn)
        print(f"通信记录数: {len(df)}")
        
        if len(df) > 0:
            # 按操作类型分组分析
            operation_stats = df.groupby('operation_type').agg({
                'message_size_bytes': ['mean', 'min', 'max'],
                'processing_time_ms': ['mean', 'min', 'max', 'count']
            }).round(2)
            
            print("\n按操作类型统计:")
            print(operation_stats.to_string())
            
            # 计算平均通信延迟
            avg_processing_time = df['processing_time_ms'].mean()
            avg_message_size = df['message_size_bytes'].mean()
            
            print(f"\n平均通信延迟: {avg_processing_time:.2f}ms")
            print(f"平均消息大小: {avg_message_size:.2f}字节")
            
            # 计算通信开销分布
            processing_time_stats = {
                'mean': df['processing_time_ms'].mean(),
                'std': df['processing_time_ms'].std(),
                'min': df['processing_time_ms'].min(),
                'max': df['processing_time_ms'].max(),
                'p50': df['processing_time_ms'].quantile(0.5),
                'p95': df['processing_time_ms'].quantile(0.95)
            }
            
            self.analysis_results['communication_metrics'] = {
                'total_records': len(df),
                'avg_processing_time_ms': avg_processing_time,
                'avg_message_size_bytes': avg_message_size,
                'processing_time_stats': processing_time_stats,
                'operation_stats': operation_stats.to_dict()
            }
        else:
            print("无通信记录数据")
            self.analysis_results['communication_metrics'] = {
                'total_records': 0,
                'avg_processing_time_ms': None,
                'avg_message_size_bytes': None,
                'processing_time_stats': None,
                'operation_stats': None
            }
        
        return df
    
    def analyze_avatar_capabilities(self):
        """分析分身能力画像"""
        print("\n=== 分身能力分析 ===")
        
        query = """
        SELECT avatar_id, avatar_name, template_id, 
               capability_scores, specialization_tags,
               success_rate, total_tasks_completed,
               current_load, last_active, created_at
        FROM avatar_capability_profiles
        """
        
        df = pd.read_sql_query(query, self.conn)
        print(f"分身数量: {len(df)}")
        
        # 解析JSON格式的能力分数
        capability_data = []
        for _, row in df.iterrows():
            try:
                scores = json.loads(row['capability_scores'])
                scores['avatar_id'] = row['avatar_id']
                scores['avatar_name'] = row['avatar_name']
                scores['success_rate'] = row['success_rate']
                scores['total_tasks'] = row['total_tasks_completed']
                scores['current_load'] = row['current_load']
                capability_data.append(scores)
            except json.JSONDecodeError:
                print(f"警告: 无法解析分身 {row['avatar_id']} 的能力分数")
        
        if capability_data:
            capability_df = pd.DataFrame(capability_data)
            
            # 计算各能力维度的平均值
            capability_columns = [col for col in capability_df.columns if col not in 
                                 ['avatar_id', 'avatar_name', 'success_rate', 'total_tasks', 'current_load']]
            
            avg_capabilities = capability_df[capability_columns].mean().sort_values(ascending=False)
            
            print("\n平均能力分数（降序排列）:")
            for capability, score in avg_capabilities.items():
                print(f"  {capability}: {score:.3f}")
            
            # 分析负载分布
            load_distribution = df['current_load'].value_counts().sort_index()
            print(f"\n负载分布:")
            for load, count in load_distribution.items():
                print(f"  负载{load}: {count}个分身")
            
            # 识别能力短板
            min_capabilities = capability_df[capability_columns].min()
            capability_gaps = min_capabilities[min_capabilities < 0.7]
            
            if len(capability_gaps) > 0:
                print(f"\n能力短板（分数<0.7）:")
                for capability, score in capability_gaps.items():
                    print(f"  {capability}: {score:.3f}")
            
            self.analysis_results['avatar_analysis'] = {
                'total_avatars': len(df),
                'avg_capabilities': avg_capabilities.to_dict(),
                'load_distribution': load_distribution.to_dict(),
                'capability_gaps': capability_gaps.to_dict() if len(capability_gaps) > 0 else {}
            }
        else:
            print("无法解析分身能力数据")
            self.analysis_results['avatar_analysis'] = {
                'total_avatars': len(df),
                'avg_capabilities': {},
                'load_distribution': {},
                'capability_gaps': {}
            }
        
        return df
    
    def analyze_cost_efficiency(self):
        """分析成本效率"""
        print("\n=== 成本效率分析 ===")
        
        query = """
        SELECT avatar_id, cost_type, amount, unit_price, total_cost,
               currency, country_code, logistics_cost, tax_rate,
               local_operations_cost, period_start, period_end
        FROM cost_consumption_logs
        """
        
        df = pd.read_sql_query(query, self.conn)
        print(f"成本记录数: {len(df)}")
        
        if len(df) > 0:
            # 按分身统计成本
            cost_by_avatar = df.groupby('avatar_id').agg({
                'total_cost': 'sum',
                'amount': 'sum'
            }).round(4)
            
            print("\n按分身统计成本（降序排列）:")
            print(cost_by_avatar.sort_values('total_cost', ascending=False).to_string())
            
            # 按成本类型统计
            cost_by_type = df.groupby('cost_type').agg({
                'total_cost': 'sum',
                'amount': 'sum'
            }).round(4)
            
            print("\n按成本类型统计:")
            print(cost_by_type.to_string())
            
            # 计算平均成本和效率指标
            total_cost = df['total_cost'].sum()
            avg_cost_per_avatar = df.groupby('avatar_id')['total_cost'].mean().mean()
            
            print(f"\n总成本: ${total_cost:.4f}")
            print(f"平均每个分身成本: ${avg_cost_per_avatar:.4f}")
            
            # 分析成本构成
            cost_breakdown = {
                'direct_tokens': df[df['cost_type'] == 'tokens']['total_cost'].sum(),
                'api_calls': df[df['cost_type'] == 'api_calls']['total_cost'].sum(),
                'workflow_executions': df[df['cost_type'] == 'workflow_executions']['total_cost'].sum()
            }
            
            self.analysis_results['cost_analysis'] = {
                'total_cost': total_cost,
                'avg_cost_per_avatar': avg_cost_per_avatar,
                'cost_by_avatar': cost_by_avatar.to_dict(),
                'cost_by_type': cost_by_type.to_dict(),
                'cost_breakdown': cost_breakdown
            }
        else:
            print("无成本记录数据")
            self.analysis_results['cost_analysis'] = {
                'total_cost': 0,
                'avg_cost_per_avatar': 0,
                'cost_by_avatar': {},
                'cost_by_type': {},
                'cost_breakdown': {}
            }
        
        return df
    
    def analyze_system_health(self):
        """分析系统健康状态"""
        print("\n=== 系统健康状态分析 ===")
        
        query = """
        SELECT node_id, node_type, status, last_heartbeat,
               task_success_rate, response_time_avg_ms, error_count
        FROM node_health_status
        """
        
        df = pd.read_sql_query(query, self.conn)
        print(f"健康状态记录数: {len(df)}")
        
        if len(df) > 0:
            # 统计状态分布
            status_distribution = df['status'].value_counts()
            print(f"\n节点状态分布:")
            for status, count in status_distribution.items():
                print(f"  {status}: {count}个节点")
            
            # 分析成功率
            avg_success_rate = df['task_success_rate'].mean()
            success_rate_stats = df['task_success_rate'].describe()
            
            print(f"\n平均任务成功率: {avg_success_rate:.3f}")
            print(f"成功率统计: min={success_rate_stats['min']:.3f}, "
                  f"max={success_rate_stats['max']:.3f}, "
                  f"mean={success_rate_stats['mean']:.3f}")
            
            # 识别问题节点
            problem_nodes = df[(df['status'] != 'healthy') & (df['status'] != 'unknown')]
            if len(problem_nodes) > 0:
                print(f"\n问题节点列表:")
                for _, node in problem_nodes.iterrows():
                    print(f"  {node['node_id']}: {node['status']}, "
                          f"错误数={node['error_count']}")
            
            self.analysis_results['health_analysis'] = {
                'total_nodes': len(df),
                'status_distribution': status_distribution.to_dict(),
                'avg_success_rate': avg_success_rate,
                'success_rate_stats': success_rate_stats.to_dict(),
                'problem_nodes_count': len(problem_nodes),
                'problem_nodes': problem_nodes[['node_id', 'status', 'error_count']].to_dict('records')
            }
        else:
            print("无健康状态记录数据")
            self.analysis_results['health_analysis'] = {
                'total_nodes': 0,
                'status_distribution': {},
                'avg_success_rate': 0,
                'success_rate_stats': {},
                'problem_nodes_count': 0,
                'problem_nodes': []
            }
        
        return df
    
    def identify_performance_bottlenecks(self):
        """识别性能瓶颈"""
        print("\n=== 性能瓶颈识别 ===")
        
        bottlenecks = []
        
        # 1. 分析通信延迟瓶颈
        if 'communication_metrics' in self.analysis_results:
            comm_data = self.analysis_results['communication_metrics']
            if comm_data['avg_processing_time_ms'] and comm_data['avg_processing_time_ms'] > 500:
                bottlenecks.append({
                    'category': '通信延迟',
                    'description': f"平均通信延迟过高: {comm_data['avg_processing_time_ms']:.2f}ms，目标应小于500ms",
                    'severity': '高',
                    'impact': '影响分身协同效率和任务响应速度'
                })
        
        # 2. 分析任务分配不平衡
        if 'task_metrics' in self.analysis_results:
            task_data = self.analysis_results['task_metrics']
            if task_data['completed_tasks'] > 0 and task_data['pending_tasks'] > 0:
                pending_ratio = task_data['pending_tasks'] / task_data['total_tasks']
                if pending_ratio > 0.3:
                    bottlenecks.append({
                        'category': '任务堆积',
                        'description': f"待处理任务比例过高: {pending_ratio:.1%}，目标应小于30%",
                        'severity': '中',
                        'impact': '降低系统整体吞吐量'
                    })
        
        # 3. 分析分身负载不均
        if 'avatar_analysis' in self.analysis_results:
            avatar_data = self.analysis_results['avatar_analysis']
            if avatar_data['load_distribution']:
                # 检查是否有分身负载过高
                high_load_avatars = sum(1 for load, count in avatar_data['load_distribution'].items() 
                                       if int(load) > 2)
                if high_load_avatars > 0:
                    bottlenecks.append({
                        'category': '负载不均衡',
                        'description': f"有{high_load_avatars}个分身负载过高（>2）",
                        'severity': '中',
                        'impact': '可能导致某些分身响应延迟，其他分身闲置'
                    })
        
        # 4. 分析能力短板
        if 'avatar_analysis' in self.analysis_results:
            avatar_data = self.analysis_results['avatar_analysis']
            if avatar_data['capability_gaps']:
                bottlenecks.append({
                    'category': '能力短板',
                    'description': f"发现{len(avatar_data['capability_gaps'])}项能力短板（分数<0.7）",
                    'severity': '中',
                    'impact': '影响特定类型任务的执行质量'
                })
        
        # 5. 分析系统健康状态
        if 'health_analysis' in self.analysis_results:
            health_data = self.analysis_results['health_analysis']
            if health_data['problem_nodes_count'] > 0:
                bottlenecks.append({
                    'category': '节点健康问题',
                    'description': f"发现{health_data['problem_nodes_count']}个问题节点",
                    'severity': '高',
                    'impact': '可能影响系统稳定性和可靠性'
                })
        
        if bottlenecks:
            print(f"识别到{len(bottlenecks)}个性能瓶颈:")
            for i, bottleneck in enumerate(bottlenecks, 1):
                print(f"\n{i}. [{bottleneck['severity']}]{bottleneck['category']}")
                print(f"   描述: {bottleneck['description']}")
                print(f"   影响: {bottleneck['impact']}")
        else:
            print("未识别到明显的性能瓶颈")
        
        self.analysis_results['performance_bottlenecks'] = bottlenecks
        return bottlenecks
    
    def generate_optimization_recommendations(self):
        """生成优化建议"""
        print("\n=== 优化建议 ===")
        
        recommendations = []
        
        # 基于性能瓶颈生成建议
        if 'performance_bottlenecks' in self.analysis_results:
            bottlenecks = self.analysis_results['performance_bottlenecks']
            
            for bottleneck in bottlenecks:
                if bottleneck['category'] == '通信延迟':
                    recommendations.append({
                        'priority': '高',
                        'area': '通信优化',
                        'recommendation': '优化消息传递路径，减少中间转发节点，实现直接通信',
                        'expected_improvement': '通信延迟减少≥30%',
                        'implementation': '基于任务74智能路由模块，进一步优化路由算法'
                    })
                
                elif bottleneck['category'] == '任务堆积':
                    recommendations.append({
                        'priority': '中',
                        'area': '任务调度',
                        'recommendation': '改进任务分配算法，基于分身实时负载动态分配任务',
                        'expected_improvement': '任务分配准确率提升≥10%，任务完成时间减少≥20%',
                        'implementation': '扩展enhanced_task_allocator.py，增加负载感知调度'
                    })
                
                elif bottleneck['category'] == '负载不均衡':
                    recommendations.append({
                        'priority': '中',
                        'area': '资源调度',
                        'recommendation': '实现自动负载均衡，动态调整分身任务分配',
                        'expected_improvement': '分身负载均衡度提升≥40%，资源利用率提升≥15%',
                        'implementation': '开发负载均衡模块，集成到任务调度器'
                    })
                
                elif bottleneck['category'] == '能力短板':
                    recommendations.append({
                        'priority': '中',
                        'area': '能力提升',
                        'recommendation': '针对性训练分身能力短板，提高专项任务执行质量',
                        'expected_improvement': '短板能力分数提升≥0.2，相关任务成功率提升≥15%',
                        'implementation': '创建能力训练模块，基于历史任务数据进行强化学习'
                    })
                
                elif bottleneck['category'] == '节点健康问题':
                    recommendations.append({
                        'priority': '高',
                        'area': '系统健康',
                        'recommendation': '加强健康检查机制，实现自动故障恢复',
                        'expected_improvement': '节点健康率提升至≥95%，自动恢复成功率≥90%',
                        'implementation': '集成健康检查与自动恢复体系，完善监控告警机制'
                    })
        
        # 通用优化建议
        if not recommendations:
            # 如果没有识别到具体瓶颈，提供通用建议
            recommendations.extend([
                {
                    'priority': '高',
                    'area': '通信优化',
                    'recommendation': '基于任务74智能路由模块，进一步优化消息传递路径，减少通信开销',
                    'expected_improvement': '通信延迟减少≥10%',
                    'implementation': '优化src/smart_router.py中的路由算法'
                },
                {
                    'priority': '中',
                    'area': '任务分配',
                    'recommendation': '增强任务分配器的动态匹配能力，基于分身实时状态调整任务分配',
                    'expected_improvement': '任务匹配准确率提升≥5%',
                    'implementation': '扩展src/enhanced_task_allocator.py，增加实时状态感知'
                },
                {
                    'priority': '中',
                    'area': '成本优化',
                    'recommendation': '分析成本消耗模式，优化资源使用策略，降低运行成本',
                    'expected_improvement': '运行成本降低≥10%',
                    'implementation': '开发成本优化模块，基于历史数据智能调度资源'
                }
            ])
        
        print(f"\n生成{len(recommendations)}条优化建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. [{rec['priority']}优先级] {rec['area']}")
            print(f"   建议: {rec['recommendation']}")
            print(f"   预期改进: {rec['expected_improvement']}")
            print(f"   实施方案: {rec['implementation']}")
        
        self.analysis_results['optimization_recommendations'] = recommendations
        return recommendations
    
    def save_analysis_report(self, output_path='temp/performance_analysis_report.json'):
        """保存分析报告到JSON文件"""
        import json
        
        # 添加分析时间戳
        self.analysis_results['analysis_timestamp'] = datetime.now().isoformat()
        self.analysis_results['database_path'] = self.db_path
        
        # 保存到文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n分析报告已保存到: {output_path}")
        return output_path
    
    def run_full_analysis(self):
        """运行完整分析流程"""
        print("开始SellAI系统性能数据分析...")
        print("=" * 60)
        
        # 执行各项分析
        self.analyze_task_completion_metrics()
        self.analyze_communication_efficiency()
        self.analyze_avatar_capabilities()
        self.analyze_cost_efficiency()
        self.analyze_system_health()
        
        # 识别瓶颈和生成建议
        self.identify_performance_bottlenecks()
        self.generate_optimization_recommendations()
        
        # 保存报告
        report_path = self.save_analysis_report()
        
        print("\n数据分析完成!")
        print("=" * 60)
        
        return self.analysis_results

def main():
    """主函数"""
    analyzer = PerformanceDataAnalyzer()
    results = analyzer.run_full_analysis()
    
    # 打印关键发现总结
    print("\n=== 关键发现总结 ===")
    
    if 'task_metrics' in results:
        tm = results['task_metrics']
        print(f"任务完成率: {tm.get('completion_rate', 0):.1f}%")
    
    if 'communication_metrics' in results:
        cm = results['communication_metrics']
        print(f"平均通信延迟: {cm.get('avg_processing_time_ms', 0):.2f}ms")
    
    if 'performance_bottlenecks' in results:
        bottlenecks = results['performance_bottlenecks']
        print(f"性能瓶颈数量: {len(bottlenecks)}")
    
    if 'optimization_recommendations' in results:
        recommendations = results['optimization_recommendations']
        high_priority = [r for r in recommendations if r['priority'] == '高']
        print(f"高优先级优化建议: {len(high_priority)}条")

if __name__ == "__main__":
    main()