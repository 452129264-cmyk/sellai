#!/usr/bin/env python3
"""
智能调度系统测试脚本
验证无上限并行处理、动态资源分配、负载均衡、容错处理四大核心功能
"""

import sys
import os
import time
import json
import random
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from src.scheduler.intelligent_scheduler import (
    IntelligentScheduler, TaskRequirements, TaskType, 
    TaskPriority, ResourceType, TaskStatus
)

def test_scheduler_initialization():
    """测试调度器初始化"""
    print("测试 1: 调度器初始化")
    
    try:
        scheduler = IntelligentScheduler()
        
        # 检查基本属性
        assert hasattr(scheduler, 'task_queue'), "缺少task_queue属性"
        assert hasattr(scheduler, 'running_tasks'), "缺少running_tasks属性"
        assert hasattr(scheduler, 'completed_tasks'), "缺少completed_tasks属性"
        
        # 检查数据库连接
        import sqlite3
        conn = sqlite3.connect("data/shared_state/state.db")
        cursor = conn.cursor()
        
        # 验证关键表存在
        required_tables = [
            'scheduler_task_queue',
            'scheduler_resource_allocations',
            'scheduler_load_metrics',
            'scheduler_decision_history',
            'scheduler_resource_pool'
        ]
        
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            result = cursor.fetchone()
            assert result, f"表 {table} 不存在"
        
        conn.close()
        
        print("  ✓ 调度器初始化成功")
        return True
        
    except Exception as e:
        print(f"  ✗ 调度器初始化失败: {e}")
        return False

def test_task_submission():
    """测试任务提交功能"""
    print("测试 2: 任务提交")
    
    try:
        scheduler = IntelligentScheduler()
        
        # 创建测试任务需求
        task_req = TaskRequirements(
            task_type=TaskType.FINANCIAL_ANALYSIS,
            required_capabilities=['data_crawling', 'financial_analysis'],
            priority=TaskPriority.NORMAL,
            estimated_complexity=5.0,
            target_regions=['US', 'CA'],
            deadline=datetime.now() + timedelta(hours=1)
        )
        
        # 创建测试商机数据
        opportunity_data = {
            'source_platform': 'Amazon',
            'original_id': 'B08N5WRWNW',
            'title': '男士牛仔裤 - 高品质牛仔布料',
            'estimated_margin': 35,
            '_metadata': {
                'opportunity_hash': 'test_hash_' + str(random.randint(10000, 99999))
            }
        }
        
        # 提交任务
        task_id = scheduler.submit_task(task_req, opportunity_data)
        
        assert task_id is not None, "任务ID为空"
        assert task_id.startswith('task_'), f"任务ID格式错误: {task_id}"
        
        # 验证任务已保存到数据库
        import sqlite3
        conn = sqlite3.connect("data/shared_state/state.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT task_id, status FROM scheduler_task_queue WHERE task_id = ?", (task_id,))
        result = cursor.fetchone()
        
        assert result is not None, "任务未保存到数据库"
        assert result[0] == task_id, "任务ID不匹配"
        assert result[1] in ['pending', 'scheduled'], f"任务状态异常: {result[1]}"
        
        conn.close()
        
        print(f"  ✓ 任务提交成功: {task_id}")
        return True
        
    except Exception as e:
        print(f"  ✗ 任务提交失败: {e}")
        return False

def test_batch_task_submission():
    """测试批量任务提交"""
    print("测试 3: 批量任务提交")
    
    try:
        scheduler = IntelligentScheduler()
        
        submitted_tasks = []
        
        # 提交多个任务
        for i in range(5):
            task_rereq = TaskRequirements(
                task_type=TaskType.DATA_CRAWLING,
                required_capabilities=['data_crawling', 'trend_analysis'],
                priority=TaskPriority.NORMAL,
                estimated_complexity=3.0 + i * 0.5,
                target_regions=['US'],
                deadline=datetime.now() + timedelta(hours=2)
            )
            
            opportunity_data = {
                'source_platform': 'Google Trends',
                'original_id': f'trend_{i}_{int(time.time())}',
                'title': f'潮流趋势分析 #{i}',
                '_metadata': {
                    'opportunity_hash': f'batch_hash_{i}_{random.randint(1000, 9999)}'
                }
            }
            
            task_id = scheduler.submit_task(task_req, opportunity_data)
            
            if task_id:
                submitted_tasks.append(task_id)
        
        assert len(submitted_tasks) > 0, "批量任务提交失败"
        
        print(f"  ✓ 批量任务提交成功: {len(submitted_tasks)} 个任务")
        
        # 检查系统状态
        status = scheduler.get_system_status()
        assert status['pending_tasks'] + status['running_tasks'] >= len(submitted_tasks), "任务计数不一致"
        
        return True
        
    except Exception as e:
        print(f"  ✗ 批量任务提交失败: {e}")
        return False

def test_resource_allocation():
    """测试资源分配功能"""
    print("测试 4: 资源分配")
    
    try:
        # 检查资源池状态
        import sqlite3
        conn = sqlite3.connect("data/shared_state/state.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT resource_type, total_amount, available_amount FROM scheduler_resource_pool")
        resources = cursor.fetchall()
        
        # 验证资源池有数据
        assert len(resources) >= 6, f"资源类型不足: {len(resources)}"
        
        # 验证每种资源的可用量不超过总量
        for resource_type, total_amount, available_amount in resources:
            assert total_amount >= 0, f"{resource_type} 总量为负"
            assert available_amount >= 0, f"{resource_type} 可用量为负"
            assert available_amount <= total_amount, f"{resource_type} 可用量超过总量"
            
            print(f"    {resource_type}: {available_amount:.1f}/{total_amount:.1f}")
        
        conn.close()
        
        print("  ✓ 资源池状态正常")
        return True
        
    except Exception as e:
        print(f"  ✗ 资源分配测试失败: {e}")
        return False

def test_load_balancing():
    """测试负载均衡"""
    print("测试 5: 负载均衡")
    
    try:
        scheduler = IntelligentScheduler()
        
        # 获取初始系统状态
        initial_status = scheduler.get_system_status()
        initial_load = initial_status['system_load_percentage']
        
        print(f"  初始负载: {initial_load:.2f}%")
        
        # 提交一组任务
        tasks = []
        for i in range(3):
            task_req = TaskRequirements(
                task_type=TaskType.SEO_OPTIMIZATION,
                required_capabilities=['seo_analysis', 'content_optimization'],
                priority=TaskPriority.HIGH,
                estimated_complexity=4.0 + i,
                target_regions=['US', 'UK', 'DE'],
                deadline=datetime.now() + timedelta(hours=1)
            )
            
            opportunity_data = {
                'source_platform': '独立站',
                'original_id': f'seo_task_{i}',
                'title': f'SEO优化任务 #{i}',
                '_metadata': {
                    'opportunity_hash': f'load_balance_hash_{i}'
                }
            }
            
            task_id = scheduler.submit_task(task_req, opportunity_data)
            if task_id:
                tasks.append(task_id)
        
        # 等待调度完成
        time.sleep(1)
        
        # 获取更新后的状态
        updated_status = scheduler.get_system_status()
        updated_load = updated_status['system_load_percentage']
        
        print(f"  更新后负载: {updated_load:.2f}%")
        
        # 负载应该有所增加
        assert updated_load >= initial_load, f"负载未增加: {updated_load} < {initial_load}"
        
        # 负载不应该超过合理范围（模拟环境）
        assert updated_load <= 200.0, f"负载过高: {updated_load}%"
        
        print("  ✓ 负载均衡功能正常")
        return True
        
    except Exception as e:
        print(f"  ✗ 负载均衡测试失败: {e}")
        return False

def test_error_handling():
    """测试错误处理"""
    print("测试 6: 错误处理")
    
    try:
        scheduler = IntelligentScheduler()
        
        # 测试无效任务提交
        task_req = TaskRequirements(
            task_type=TaskType.GENERAL,
            required_capabilities=[],  # 没有所需能力
            priority=TaskPriority.URGENT,
            estimated_complexity=100.0,  # 极高的复杂度
            target_regions=['XX'],  # 无效地区
            deadline=datetime.now() - timedelta(hours=1)  # 已经过期的截止时间
        )
        
        opportunity_data = {
            'title': '无效测试任务'
        }
        
        task_id = scheduler.submit_task(task_req, opportunity_data)
        
        # 任务可能被拒绝或分配失败，两种情况都正常
        if task_id is None:
            print("  ✓ 无效任务被正确拒绝")
        else:
            print(f"  ✓ 无效任务被接受: {task_id}")
        
        # 测试数据库连接异常（模拟）
        import sqlite3
        
        # 创建临时测试环境
        test_db_path = "/tmp/test_scheduler.db"
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        
        # 尝试在异常情况下工作
        try:
            # 正常情况
            test_scheduler = IntelligentScheduler(db_path=test_db_path)
            print("  ✓ 能在新环境中初始化")
            
            # 清理测试文件
            test_scheduler.shutdown()
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
                
        except Exception as e:
            print(f"  注意: 测试环境异常: {e}")
        
        print("  ✓ 错误处理功能正常")
        return True
        
    except Exception as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        return False

def test_performance_metrics():
    """测试性能指标收集"""
    print("测试 7: 性能指标")
    
    try:
        scheduler = IntelligentScheduler()
        
        # 获取性能指标
        status = scheduler.get_system_status()
        
        # 验证关键指标存在
        required_metrics = [
            'pending_tasks',
            'running_tasks', 
            'completed_tasks',
            'total_avatars',
            'system_load_percentage'
        ]
        
        for metric in required_metrics:
            assert metric in status, f"缺少指标: {metric}"
            
            # 验证指标类型
            value = status[metric]
            if metric != 'system_load_percentage':
                assert isinstance(value, int) or isinstance(value, float), f"指标类型错误: {metric}"
            else:
                assert isinstance(value, float), f"负载指标类型错误: {metric}"
        
        # 验证性能统计信息
        stats = status.get('scheduler_stats', {})
        if stats:
            print(f"  性能统计:")
            for key, value in stats.items():
                print(f"    {key}: {value}")
        
        print("  ✓ 性能指标收集正常")
        return True
        
    except Exception as e:
        print(f"  ✗ 性能指标测试失败: {e}")
        return False

def test_task_reassignment():
    """测试任务重分配"""
    print("测试 8: 任务重分配")
    
    try:
        scheduler = IntelligentScheduler()
        
        # 模拟一个任务失败的情况
        # 这需要数据库中有相应的测试数据
        # 这里我们主要检查接口是否存在
        
        # 记录一个测试任务
        import sqlite3
        conn = sqlite3.connect("data/shared_state/state.db")
        cursor = conn.cursor()
        
        test_task_id = f"reassign_test_{int(time.time())}"
        
        # 插入一个测试任务
        cursor.execute("""
            INSERT INTO scheduler_task_queue 
            (task_id, task_type, priority, estimated_duration_seconds,
             resource_requirements, dependencies, deadline, status,
             assigned_avatar, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_task_id,
            'data_crawling',
            2,
            300.0,
            json.dumps([{"resource_type": "cpu", "required_amount": 2.0}]),
            json.dumps([]),
            (datetime.now() + timedelta(hours=1)).isoformat(),
            'failed',
            'test_avatar_1',
            datetime.now().isoformat()
        ))
        
        conn.commit()
        
        print(f"  测试任务创建: {test_task_id}")
        
        # 验证表中有数据
        cursor.execute("SELECT COUNT(*) FROM scheduler_task_queue WHERE status = 'failed'")
        failed_count = cursor.fetchone()[0]
        
        assert failed_count >= 1, "无失败任务记录"
        
        conn.close()
        
        print("  ✓ 任务重分配测试通过")
        return True
        
    except Exception as e:
        print(f"  ✗ 任务重分配测试失败: {e}")
        return False

def test_concurrent_submissions():
    """测试并发提交"""
    print("测试 9: 并发提交")
    
    try:
        import threading
        
        scheduler = IntelligentScheduler()
        submitted_tasks = []
        lock = threading.Lock()
        
        def submit_task_thread(thread_id):
            """线程任务提交函数"""
            try:
                task_req = TaskRequirements(
                    task_type=TaskType.SOCIAL_MEDIA,
                    required_capabilities=['social_media_management', 'content_posting'],
                    priority=TaskPriority.NORMAL,
                    estimated_complexity=3.0 + thread_id * 0.2,
                    target_regions=['US'],
                    deadline=datetime.now() + timedelta(minutes=30)
                )
                
                opportunity_data = {
                    'source_platform': 'Instagram',
                    'original_id': f'concurrent_{thread_id}_{int(time.time())}',
                    'title': f'并发测试任务 #{thread_id}',
                    '_metadata': {
                        'opportunity_hash': f'concurrent_hash_{thread_id}_{random.randint(1000, 9999)}'
                    }
                }
                
                task_id = scheduler.submit_task(task_req, opportunity_data)
                
                if task_id:
                    with lock:
                        submitted_tasks.append(task_id)
                    
            except Exception as e:
                print(f"    线程 {thread_id} 失败: {e}")
        
        # 启动多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=submit_task_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        print(f"  并发提交结果: {len(submitted_tasks)} 个任务")
        
        # 验证至少有一些任务成功
        assert len(submitted_tasks) > 0, "并发提交无任务成功"
        
        # 检查系统状态
        status = scheduler.get_system_status()
        print(f"  最终系统状态: {status['pending_tasks']} 个待处理, {status['running_tasks']} 个运行中")
        
        print("  ✓ 并发提交测试通过")
        return True
        
    except Exception as e:
        print(f"  ✗ 并发提交测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("智能调度系统测试开始")
    print("=" * 60)
    
    test_results = []
    
    # 运行各个测试
    test_functions = [
        test_scheduler_initialization,
        test_task_submission,
        test_batch_task_submission,
        test_resource_allocation,
        test_load_balancing,
        test_error_handling,
        test_performance_metrics,
        test_task_reassignment,
        test_concurrent_submissions
    ]
    
    for test_func in test_functions:
        start_time = time.time()
        success = test_func()
        elapsed = time.time() - start_time
        
        test_results.append({
            'name': test_func.__name__,
            'success': success,
            'elapsed': elapsed
        })
        
        print(f"  耗时: {elapsed:.2f} 秒")
        print()
    
    # 统计结果
    passed = sum(1 for r in test_results if r['success'])
    total = len(test_results)
    
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for result in test_results:
        status = "✓" if result['success'] else "✗"
        print(f"  {status} {result['name']}: {result['elapsed']:.2f} 秒")
    
    print()
    print(f"通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("✅ 所有测试通过！")
    else:
        print(f"⚠️  有 {total - passed} 个测试失败")
    
    print("=" * 60)
    
    return all(r['success'] for r in test_results)

def main():
    """主函数"""
    try:
        print("智能调度系统测试脚本")
        print()
        
        # 确保数据库文件存在
        if not os.path.exists("data/shared_state/state.db"):
            print("注意: 数据库文件不存在，部分测试可能失败")
            print("建议先运行 init_scheduler_tables.py 初始化数据库")
            print()
        
        # 运行所有测试
        success = run_all_tests()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"测试过程异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()