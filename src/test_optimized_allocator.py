#!/usr/bin/env python3
"""
测试优化任务分配器
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.optimized_task_allocator import OptimizedTaskAllocator

def main():
    print("=== 测试优化任务分配器 ===\n")
    
    # 初始化分配器
    allocator = OptimizedTaskAllocator()
    
    # 测试1: 基本分配
    print("1. 测试基本任务分配...")
    avatar_id = allocator.find_best_avatar_for_task(
        required_capabilities=['data_crawling', 'financial_analysis']
    )
    
    if avatar_id:
        print(f"   分配成功: {avatar_id}")
    else:
        print("   分配失败")
    
    # 测试2: 带优先级的分配
    print("\n2. 测试带优先级的任务分配...")
    avatar_id = allocator.find_best_avatar_for_task(
        required_capabilities=['data_crawling', 'financial_analysis'],
        priority=3,  # HIGH
        complexity=7.0,
        target_regions=['US', 'CA']
    )
    
    if avatar_id:
        print(f"   分配成功: {avatar_id}")
    else:
        print("   分配失败")
    
    # 测试3: 获取性能报告
    print("\n3. 测试性能报告...")
    report = allocator.get_allocation_performance(hours=1)
    
    if report and report.get('status') != 'no_data':
        print(f"   报告生成成功:")
        print(f"   - 决策总数: {report.get('total_decisions', 0)}")
        print(f"   - 平均分数: {report.get('avg_total_score', 0):.3f}")
    else:
        print("   无性能数据")
    
    # 测试4: 兼容旧版接口
    print("\n4. 测试兼容旧版接口...")
    from src.optimized_task_allocator import find_best_avatar_for_task_compat
    
    old_avatar = find_best_avatar_for_task_compat(
        required_capabilities=['data_crawling', 'financial_analysis'],
        min_score_threshold=0.6
    )
    
    if old_avatar:
        print(f"   兼容接口分配成功: {old_avatar}")
    else:
        print("   兼容接口分配失败")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()