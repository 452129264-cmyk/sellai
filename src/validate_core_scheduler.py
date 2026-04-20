#!/usr/bin/env python3
"""
验证核心调度器框架
"""

import sys
import os
import json

def validate_import():
    """验证模块导入"""
    print("=" * 60)
    print("验证模块导入")
    print("=" * 60)
    
    try:
        from global_orchestrator.core_scheduler import CoreScheduler, TaskType, TaskStatus
        print("✅ 核心模块导入成功")
        
        # 测试类型
        print(f"✅ 任务类型枚举: {[t.value for t in TaskType]}")
        print(f"✅ 任务状态枚举: {[s.value for s in TaskStatus]}")
        
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def validate_scheduler_functionality():
    """验证调度器功能"""
    print("\n" + "=" * 60)
    print("验证调度器核心功能")
    print("=" * 60)
    
    try:
        from global_orchestrator.core_scheduler import CoreScheduler, TaskType
        
        # 初始化调度器
        scheduler = CoreScheduler()
        print("✅ 调度器初始化成功")
        
        # 测试分身注册
        reg_result = scheduler.register_avatar(
            avatar_id="test_avatar_001",
            name="测试分身001",
            capabilities=["voice_processing", "payment"]
        )
        print(f"✅ 分身注册: {reg_result}")
        
        # 测试任务提交
        task_id = scheduler.submit_task(
            task_type=TaskType.VOICE,
            priority=1,
            payload={"test": "data"}
        )
        print(f"✅ 任务提交: {task_id}")
        
        # 测试任务分配
        assign_result = scheduler.assign_task(task_id, "test_avatar_001")
        print(f"✅ 任务分配: {assign_result}")
        
        # 测试任务完成
        complete_result = scheduler.complete_task(task_id, success=True, result={"output": "验证通过"})
        print(f"✅ 任务完成: {complete_result}")
        
        # 测试系统状态
        status = scheduler.get_system_status()
        print(f"✅ 系统状态获取: {len(status)} 项数据")
        
        # 输出关键统计
        print(f"\n📊 调度器统计:")
        print(f"  接收任务数: {scheduler.stats['total_tasks_received']}")
        print(f"  完成任务数: {scheduler.stats['total_tasks_completed']}")
        print(f"  失败任务数: {scheduler.stats['total_tasks_failed']}")
        print(f"  成功率: {scheduler.stats['success_rate']:.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 功能验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_test_suite():
    """验证测试套件"""
    print("\n" + "=" * 60)
    print("验证测试套件")
    print("=" * 60)
    
    try:
        # 添加当前目录到路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(current_dir, 'src')
        sys.path.insert(0, src_dir)
        
        # 运行测试
        import unittest
        
        # 加载测试
        loader = unittest.TestLoader()
        start_dir = os.path.join(current_dir, 'tests')
        suite = loader.discover(start_dir, pattern='test_core_scheduler.py')
        
        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        print(f"\n📊 测试结果:")
        print(f"  运行测试数: {result.testsRun}")
        print(f"  失败数: {len(result.failures)}")
        print(f"  错误数: {len(result.errors)}")
        
        if result.wasSuccessful():
            print("✅ 所有测试通过！")
            return True
        else:
            print("❌ 部分测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试套件验证失败: {e}")
        return False

def validate_sync_capability():
    """验证同步能力"""
    print("\n" + "=" * 60)
    print("验证同步接口")
    print("=" * 60)
    
    try:
        from global_orchestrator.core_scheduler import CoreScheduler
        
        scheduler = CoreScheduler()
        
        # 测试同步接口
        sync_result = scheduler.sync_to_shared_state()
        print(f"✅ 同步到共享状态库: {sync_result}")
        
        load_result = scheduler.load_from_shared_state()
        print(f"✅ 从共享状态库加载: {load_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 同步接口验证失败: {e}")
        return False

def create_validation_summary(results):
    """创建验证总结"""
    print("\n" + "=" * 60)
    print("验证总结报告")
    print("=" * 60)
    
    summary = {
        "timestamp": "2026-04-06T10:20:00",
        "validation_results": results,
        "overall_status": "PASS" if all(results.values()) else "FAIL",
        "components_validated": len(results),
        "components_passed": sum(1 for r in results.values() if r),
        "components_failed": sum(1 for r in results.values() if not r)
    }
    
    print(f"🕒 验证时间: {summary['timestamp']}")
    print(f"📋 验证组件数: {summary['components_validated']}")
    print(f"✅ 通过组件数: {summary['components_passed']}")
    print(f"❌ 失败组件数: {summary['components_failed']}")
    print(f"🎯 总体状态: {summary['overall_status']}")
    
    print("\n🔍 详细结果:")
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    # 保存验证报告
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs', '统一调度器框架')
    os.makedirs(report_dir, exist_ok=True)
    
    report_path = os.path.join(report_dir, '框架验证报告.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 验证报告已保存: {report_path}")
    
    return summary['overall_status'] == "PASS"

def main():
    """主验证流程"""
    print("统一调度器框架验证开始")
    print("=" * 60)
    
    # 执行各项验证
    results = {
        "模块导入": validate_import(),
        "核心功能": validate_scheduler_functionality(),
        "测试套件": validate_test_suite(),
        "同步接口": validate_sync_capability()
    }
    
    # 创建总结
    overall_pass = create_validation_summary(results)
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)
    
    if overall_pass:
        print("🎉 所有验证项目通过！")
        print("框架已准备就绪，可用于后续能力集成。")
        return 0
    else:
        print("⚠️  部分验证项目失败，请检查问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())