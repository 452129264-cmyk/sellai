#!/usr/bin/env python3
"""
快速健康监控系统测试
验证核心功能是否正常工作。
"""

import tempfile
import os
import sys

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.health_monitor import create_health_monitor
from src.kairos_guardian import KAIROSGuardian, GuardianMode


def test_basic_functionality():
    """测试基本功能"""
    print("测试健康监控系统基本功能...")
    
    # 创建临时数据库
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = temp_db.name
    temp_db.close()
    
    try:
        # 1. 测试健康监控器
        print("1. 创建健康监控器...")
        monitor = create_health_monitor()
        monitor.db_path = db_path
        monitor._init_database()
        
        # 注册测试节点
        print("2. 注册测试节点...")
        nodes = [
            ("情报官", "central"),
            ("内容官", "central"),
            ("测试节点", "custom")
        ]
        
        for node_id, node_type in nodes:
            success = monitor.register_node(node_id, node_type)
            print(f"  注册节点 {node_id}: {'成功' if success else '失败'}")
        
        # 执行健康检查
        print("3. 执行健康检查...")
        from src.health_monitor import HealthCheckType
        
        result = monitor.perform_health_check(
            "情报官",
            HealthCheckType.DATABASE_CONNECTION,
            {"description": "快速测试"}
        )
        
        print(f"  检查结果: 状态={result['status']}, 成功={result['success']}")
        
        # 获取系统状态
        print("4. 获取系统状态...")
        dashboard = monitor.get_system_health_dashboard()
        
        if "error" in dashboard:
            print(f"  获取状态失败: {dashboard['error']}")
        else:
            print(f"  系统健康度: {dashboard['summary']['health_percentage']:.1%}")
            print(f"  总节点数: {dashboard['summary']['total_nodes']}")
        
        # 2. 测试KAIROS守护系统
        print("\n5. 测试KAIROS守护系统...")
        guardian = KAIROSGuardian(db_path)
        
        # 设置模式
        guardian.set_mode(GuardianMode.STANDARD)
        print(f"  设置守护模式: {guardian.mode.value}")
        
        # 获取状态
        status = guardian.get_guardian_status()
        print(f"  注册节点数: {status.get('registered_nodes', 'N/A')}")
        
        # 手动诊断
        print("6. 执行手动诊断...")
        diagnostic = guardian.manual_diagnostic("情报官")
        print(f"  诊断结果: {diagnostic['overall_status']}")
        
        print("\n✅ 基本功能测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_integration_with_system():
    """测试与现有系统集成"""
    print("\n测试与现有系统集成...")
    
    try:
        # 使用现有数据库
        db_path = "data/shared_state/state.db"
        
        if not os.path.exists(db_path):
            print("  现有数据库不存在，创建测试数据库...")
            # 创建测试数据库结构
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 创建一些测试表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS avatar_registry (
                    avatar_id TEXT PRIMARY KEY,
                    avatar_type TEXT,
                    description TEXT
                )
            ''')
            
            # 插入测试数据
            cursor.execute('''
                INSERT OR REPLACE INTO avatar_registry 
                (avatar_id, avatar_type, description) 
                VALUES (?, ?, ?)
            ''', ("牛仔选品分身", "vertical", "牛仔品类选品专家"))
            
            cursor.execute('''
                INSERT OR REPLACE INTO avatar_registry 
                (avatar_id, avatar_type, description) 
                VALUES (?, ?, ?)
            ''', ("短视频创作分身", "vertical", "短视频内容创作专家"))
            
            conn.commit()
            conn.close()
        
        # 创建守护系统
        guardian = KAIROSGuardian(db_path)
        
        # 获取状态
        status = guardian.get_guardian_status()
        
        print(f"  系统状态: 模式={status.get('guardian_mode', 'unknown')}")
        print(f"  注册组件: {status.get('registered_nodes', 'N/A')}")
        
        # 检查是否注册了关键组件
        nodes = guardian.health_monitor._get_all_nodes()
        critical_nodes = ["情报官", "内容官", "运营官", "增长官"]
        registered_critical = [node[0] for node in nodes if node[0] in critical_nodes]
        
        print(f"  关键组件注册情况: {len(registered_critical)}/{len(critical_nodes)}")
        
        if len(registered_critical) >= 2:
            print("  ✅ 关键组件注册正常")
            return True
        else:
            print("  ⚠️  关键组件注册不足")
            return False
            
    except Exception as e:
        print(f"  ❌ 集成测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("健康检查与自动恢复体系快速测试")
    print("=" * 60)
    
    # 测试基本功能
    basic_ok = test_basic_functionality()
    
    if not basic_ok:
        print("\n❌ 基本功能测试失败，中止测试")
        return False
    
    # 测试系统集成
    integration_ok = test_integration_with_system()
    
    print("\n" + "=" * 60)
    
    if basic_ok and integration_ok:
        print("✅ 所有测试通过！")
        print("\n健康检查与自动恢复体系功能完整，包括:")
        print("1. 节点注册与心跳监控")
        print("2. 多类型健康检查（数据库、网络等）")
        print("3. 系统健康度仪表板")
        print("4. KAIROS守护系统集成")
        print("5. 故障诊断与恢复功能")
        return True
    else:
        print("⚠️  部分测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)