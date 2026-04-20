#!/usr/bin/env python3
"""
优化分配器API模块

提供命令行接口，供工作流节点调用。
支持单任务分配和批量分配。
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List

# 添加路径以便导入其他模块
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.optimized_task_allocator import OptimizedTaskAllocator, TaskPriority


def allocate_single_task():
    """分配单个任务"""
    parser = argparse.ArgumentParser(description='优化任务分配器API')
    parser.add_argument('--required_capabilities', type=str, help='JSON格式的所需能力列表')
    parser.add_argument('--task_type', type=str, help='任务类型')
    parser.add_argument('--priority', type=int, default=2, help='任务优先级')
    parser.add_argument('--complexity', type=float, default=1.0, help='任务复杂度')
    parser.add_argument('--target_regions', type=str, help='JSON格式的目标地域列表')
    parser.add_argument('--min_score_threshold', type=float, default=0.6, help='最低分数阈值')
    
    args = parser.parse_args()
    
    # 解析JSON参数
    required_capabilities = []
    if args.required_capabilities:
        required_capabilities = json.loads(args.required_capabilities)
    
    target_regions = []
    if args.target_regions:
        target_regions = json.loads(args.target_regions)
    
    # 初始化分配器
    allocator = OptimizedTaskAllocator()
    
    # 执行分配
    avatar_id = allocator.find_best_avatar_for_task(
        required_capabilities=required_capabilities,
        task_type=args.task_type,
        priority=args.priority,
        complexity=args.complexity,
        target_regions=target_regions,
        min_score_threshold=args.min_score_threshold
    )
    
    # 返回结果
    result = {
        'success': avatar_id is not None,
        'avatar_id': avatar_id,
        'timestamp': datetime.now().isoformat()
    }
    
    print(json.dumps(result, ensure_ascii=False))
    return 0 if avatar_id else 1


def allocate_batch_tasks():
    """批量分配任务"""
    parser = argparse.ArgumentParser(description='批量任务分配API')
    parser.add_argument('--tasks_file', type=str, required=True, help='任务数据JSON文件路径')
    
    args = parser.parse_args()
    
    # 读取任务数据
    with open(args.tasks_file, 'r', encoding='utf-8') as f:
        tasks_data = json.load(f)
    
    # 初始化分配器
    allocator = OptimizedTaskAllocator()
    
    # 执行批量分配
    assignments = allocator.allocate_batch_tasks(tasks_data)
    
    # 返回结果
    result = {
        'success': len(assignments) > 0,
        'assignments': assignments,
        'total_assigned': len(assignments),
        'timestamp': datetime.now().isoformat()
    }
    
    print(json.dumps(result, ensure_ascii=False))
    return 0 if assignments else 1


def get_performance_report():
    """获取性能报告"""
    parser = argparse.ArgumentParser(description='获取性能报告API')
    parser.add_argument('--hours', type=int, default=24, help='统计小时数')
    
    args = parser.parse_args()
    
    # 初始化分配器
    allocator = OptimizedTaskAllocator()
    
    # 获取报告
    report = allocator.get_allocation_performance(hours=args.hours)
    
    print(json.dumps(report, ensure_ascii=False))
    return 0


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python optimized_allocator_api.py <command> [options]")
        print("Commands:")
        print("  allocate_single   分配单个任务")
        print("  allocate_batch    批量分配任务")
        print("  performance       获取性能报告")
        return 1
    
    command = sys.argv[1]
    sys.argv = sys.argv[1:]  # 调整参数以便argparse正确处理
    
    if command == 'allocate_single':
        return allocate_single_task()
    elif command == 'allocate_batch':
        return allocate_batch_tasks()
    elif command == 'performance':
        return get_performance_report()
    else:
        print(f"未知命令: {command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())