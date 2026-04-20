#!/usr/bin/env python3
"""
测试健康监控器导入和基本功能
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 尝试导入 HealthMonitor
    from health_monitor import HealthMonitor, NodeStatus, HealthCheckType, RecoveryAction
    print("✅ 健康监控器模块导入成功")
    print(f"✅ NodeStatus 枚举值: {[e.value for e in NodeStatus]}")
    print(f"✅ HealthCheckType 枚举值: {[e.value for e in HealthCheckType]}")
    print(f"✅ RecoveryAction 枚举值: {[e.value for e in RecoveryAction]}")
    
    # 尝试创建实例
    try:
        monitor = HealthMonitor()
        print("✅ HealthMonitor 实例创建成功")
        print(f"✅ 数据库路径: {monitor.db_path}")
    except Exception as e:
        print(f"❌ HealthMonitor 实例创建失败: {e}")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 意外错误: {e}")
    sys.exit(1)

print("\n✅ 健康监控器核心代码验证通过")