#!/usr/bin/env python3
"""
调度器集成测试
测试SellAI任务调度与工具调用链路
"""

import sys
import os
from datetime import datetime

# 添加全局调度器路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from global_orchestrator.core_scheduler import CoreScheduler, TaskType, TaskStatus

def test_basic_scheduler():
    """测试基础调度器功能"""
    print("=== 调度器基础功能测试 ===")
    
    # 创建调度器实例
    scheduler = CoreScheduler()
    
    # 1. 测试分身注册
    print("\n1. 测试分身注册:")
    success = scheduler.register_avatar(
        avatar_id="test_avatar_1",
        name="测试分身",
        capabilities=["voice", "payment", "market"]
    )
    print(f"   分身注册结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 2. 测试任务提交
    print("\n2. 测试任务提交:")
    task_id = scheduler.submit_task(
        task_type=TaskType.VOICE,
        priority=2,
        payload={"message": "测试语音任务", "user_id": "test_user_123"}
    )
    print(f"   任务提交结果: {'✅ 成功' if task_id else '❌ 失败'}")
    if task_id:
        print(f"   任务ID: {task_id}")
    
    # 3. 测试任务获取
    print("\n3. 测试任务获取:")
    task = scheduler.get_next_task()
    if task:
        print(f"   ✅ 获取到任务: {task.task_id}")
        print(f"      类型: {task.task_type.value}")
        print(f"      优先级: {task.priority}")
        print(f"      状态: {task.status.value}")
    else:
        print("   ❌ 未获取到任务")
    
    # 4. 测试调度统计
    print("\n4. 测试调度统计:")
    stats = scheduler.stats
    print(f"   总接收任务数: {stats['total_tasks_received']}")
    print(f"   总完成任务数: {stats['total_tasks_completed']}")
    print(f"   总失败任务数: {stats['total_tasks_failed']}")
    print(f"   平均处理时间: {stats['avg_processing_time_seconds']:.2f}秒")
    print(f"   成功率: {stats['success_rate']:.2%}")
    
    print("\n=== 基础功能测试完成 ===")
    return task_id is not None

def test_tool_integration():
    """测试工具集成链路"""
    print("\n=== 工具集成链路测试 ===")
    
    # 检查是否有工具调用模块
    tool_modules = []
    
    # 检查八大能力适配器
    adapter_dir = os.path.join(os.path.dirname(__file__), "global_orchestrator", "adapters")
    if os.path.exists(adapter_dir):
        adapters = os.listdir(adapter_dir)
        python_adapters = [a for a in adapters if a.endswith('.py') and not a.startswith('__')]
        tool_modules.extend([f"adapters.{a[:-3]}" for a in python_adapters])
    
    print(f"1. 发现适配器模块: {len(tool_modules)}个")
    for module in tool_modules[:5]:  # 只显示前5个
        print(f"   • {module}")
    if len(tool_modules) > 5:
        print(f"   ... 还有{len(tool_modules)-5}个")
    
    # 检查配置
    print("\n2. 检查配置:")
    config_path = os.path.join(os.path.dirname(__file__), "global_orchestrator", "config.py")
    if os.path.exists(config_path):
        print("   ✅ 配置模块存在")
        # 尝试导入配置
        try:
            sys.path.insert(0, os.path.dirname(config_path))
            from global_orchestrator.config import DEFAULT_CONFIG
            print(f"   ✅ 默认配置加载成功")
            print(f"      能力数量: {len(DEFAULT_CONFIG.capabilities)}")
            print(f"      已启用能力: {sum(1 for c in DEFAULT_CONFIG.capabilities.values() if c.enabled)}")
        except Exception as e:
            print(f"   ⚠️  配置加载失败: {e}")
    else:
        print("   ❌ 配置模块不存在")
    
    # 检查网络可达性
    print("\n3. 网络可达性检查:")
    test_endpoints = [
        ("本地数据库", "data/shared_state/state.db"),
        ("调度器核心", "global_orchestrator/core_scheduler.py"),
    ]
    
    all_accessible = True
    for name, path in test_endpoints:
        full_path = os.path.join(os.path.dirname(__file__), path) if not os.path.isabs(path) else path
        if os.path.exists(full_path):
            print(f"   ✅ {name}: 可访问")
        else:
            print(f"   ❌ {name}: 不可访问")
            all_accessible = False
    
    print("\n=== 工具集成测试完成 ===")
    return all_accessible

if __name__ == "__main__":
    print(f"测试开始时间: {datetime.now()}")
    print(f"当前工作目录: {os.getcwd()}")
    
    basic_ok = False
    integration_ok = False
    
    try:
        basic_ok = test_basic_scheduler()
    except Exception as e:
        print(f"❌ 基础调度器测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        integration_ok = test_tool_integration()
    except Exception as e:
        print(f"❌ 工具集成测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*50}")
    print("测试总结:")
    print(f"  基础调度器功能: {'✅ 通过' if basic_ok else '❌ 失败'}")
    print(f"  工具集成链路: {'✅ 通过' if integration_ok else '❌ 失败'}")
    
    # 总体评估
    if basic_ok and integration_ok:
        print("✅ 整体测试通过 - 调度器核心功能正常")
        sys.exit(0)
    else:
        print("⚠️  测试存在问题 - 需要进一步检查")
        sys.exit(1)