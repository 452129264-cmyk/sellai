#!/usr/bin/env python3
"""
监控系统验证脚本
验证全局监控系统的核心功能
"""

import sys
import os
import time
import json
from datetime import datetime

# 添加路径以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.global_orchestrator.config import OrchestratorConfig
from src.global_orchestrator.monitoring_system import (
    GlobalMonitoringSystem,
    PerformanceMonitor,
    NodeHealthMonitor,
    ServiceAvailabilityMonitor,
    AlertManager,
    RecoveryExecutor,
    MonitorType,
    SeverityLevel,
    RecoveryActionType
)


def test_performance_monitor():
    """测试性能监控器"""
    print("=== 测试性能监控器 ===")
    
    config = OrchestratorConfig()
    monitor = PerformanceMonitor(config)
    
    # 测试指标收集
    metrics = monitor.collect_metrics()
    print(f"收集到 {len(metrics)} 项性能指标")
    print(f"CPU使用率: {metrics.get('cpu_percent', 'N/A')}%")
    print(f"内存使用: {metrics.get('memory_percent', 'N/A')}%")
    print(f"响应时间: {metrics.get('response_time_ms', 'N/A')}ms")
    print(f"队列长度: {metrics.get('queue_length', 'N/A')}")
    
    # 测试健康检查
    health = monitor.check_health()
    print(f"性能健康状态: {health.get('status', 'unknown')}")
    print(f"检测到问题: {len(health.get('issues', []))} 个")
    
    # 测试异常检测
    anomalies = monitor.detect_anomalies(metrics)
    print(f"检测到异常: {len(anomalies)} 个")
    
    return True


def test_node_health_monitor():
    """测试节点健康监控器"""
    print("\n=== 测试节点健康监控器 ===")
    
    config = OrchestratorConfig()
    monitor = NodeHealthMonitor(config)
    
    # 测试指标收集
    metrics = monitor.collect_metrics()
    print(f"监控节点数: {metrics.get('total_nodes', 0)}")
    
    # 测试健康检查
    health = monitor.check_health()
    print(f"节点健康状态: {health.get('status', 'unknown')}")
    print(f"健康节点比例: {health.get('health_ratio', 0.0):.2%}")
    
    return True


def test_service_availability_monitor():
    """测试服务可用性监控器"""
    print("\n=== 测试服务可用性监控器 ===")
    
    config = OrchestratorConfig()
    monitor = ServiceAvailabilityMonitor(config)
    
    # 测试指标收集
    metrics = monitor.collect_metrics()
    print(f"配置服务数: {metrics.get('total_services', 0)}")
    print(f"可用服务数: {metrics.get('available_services', 0)}")
    
    # 测试健康检查
    health = monitor.check_health()
    print(f"服务可用性状态: {health.get('status', 'unknown')}")
    
    return True


def test_alert_manager():
    """测试告警管理器"""
    print("\n=== 测试告警管理器 ===")
    
    manager = AlertManager(":memory:")  # 使用内存数据库测试
    
    # 创建测试告警
    alert_id = manager.create_alert(
        monitor_type=MonitorType.PERFORMANCE,
        severity=SeverityLevel.ERROR,
        message="测试告警: CPU使用率过高",
        details={
            "cpu_percent": 95.5,
            "threshold": 80
        }
    )
    
    if alert_id:
        print(f"告警创建成功: {alert_id}")
        
        # 获取活跃告警
        active_alerts = manager.get_active_alerts()
        print(f"活跃告警数: {len(active_alerts)}")
        
        # 确认告警
        if active_alerts:
            success = manager.acknowledge_alert(active_alerts[0].alert_id, "test_user")
            print(f"告警确认: {'成功' if success else '失败'}")
            
            # 解决告警
            success = manager.resolve_alert(active_alerts[0].alert_id, "test_user", "已处理")
            print(f"告警解决: {'成功' if success else '失败'}")
    
    return True


def test_recovery_executor():
    """测试恢复执行器"""
    print("\n=== 测试恢复执行器 ===")
    
    executor = RecoveryExecutor(":memory:")  # 使用内存数据库测试
    
    # 测试重启服务动作
    success, message = executor.execute_action(
        RecoveryActionType.RESTART_SERVICE,
        "test_service",
        {"force": True}
    )
    
    print(f"重启服务: {'成功' if success else '失败'} - {message}")
    
    # 测试通知管理员动作
    success, message = executor.execute_action(
        RecoveryActionType.NOTIFY_ADMIN,
        "system",
        {"alert_level": "critical"}
    )
    
    print(f"通知管理员: {'成功' if success else '失败'} - {message}")
    
    return True


def test_global_monitoring_system():
    """测试全局监控系统"""
    print("\n=== 测试全局监控系统 ===")
    
    config = OrchestratorConfig()
    system = GlobalMonitoringSystem(config)
    
    # 测试获取系统状态
    status = system.get_system_status()
    print(f"系统整体状态: {status.get('overall_status', 'unknown')}")
    
    # 测试获取详细指标
    metrics = system.get_detailed_metrics()
    print(f"收集到性能指标: {len(metrics.get('performance', {}))} 项")
    
    # 测试模拟故障场景
    print("\n模拟5种故障场景:")
    scenarios = [
        "high_cpu_usage",
        "node_unhealthy", 
        "service_unavailable",
        "slow_response",
        "high_error_rate"
    ]
    
    for scenario in scenarios:
        success = system.simulate_failure_scenario(scenario)
        print(f"  - {scenario}: {'成功' if success else '失败'}")
    
    return True


def main():
    """主测试函数"""
    print("开始监控系统验证...")
    
    test_results = []
    
    try:
        test_results.append(("性能监控器", test_performance_monitor()))
    except Exception as e:
        print(f"性能监控器测试失败: {e}")
        test_results.append(("性能监控器", False))
    
    try:
        test_results.append(("节点健康监控器", test_node_health_monitor()))
    except Exception as e:
        print(f"节点健康监控器测试失败: {e}")
        test_results.append(("节点健康监控器", False))
    
    try:
        test_results.append(("服务可用性监控器", test_service_availability_monitor()))
    except Exception as e:
        print(f"服务可用性监控器测试失败: {e}")
        test_results.append(("服务可用性监控器", False))
    
    try:
        test_results.append(("告警管理器", test_alert_manager()))
    except Exception as e:
        print(f"告警管理器测试失败: {e}")
        test_results.append(("告警管理器", False))
    
    try:
        test_results.append(("恢复执行器", test_recovery_executor()))
    except Exception as e:
        print(f"恢复执行器测试失败: {e}")
        test_results.append(("恢复执行器", False))
    
    try:
        test_results.append(("全局监控系统", test_global_monitoring_system()))
    except Exception as e:
        print(f"全局监控系统测试失败: {e}")
        test_results.append(("全局监控系统", False))
    
    # 输出测试结果
    print("\n" + "="*50)
    print("监控系统验证结果:")
    print("="*50)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("所有测试通过! 监控系统功能正常。")
    else:
        print("部分测试失败，需要检查监控系统实现。")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)