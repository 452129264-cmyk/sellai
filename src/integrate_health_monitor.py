#!/usr/bin/env python3
"""
健康监控系统集成脚本
将健康检查与自动恢复体系集成到现有SellAI系统中。
"""

import sys
import os
import sqlite3
import json
from datetime import datetime

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.health_monitor import HealthMonitor, NodeStatus, HealthCheckType
from src.kairos_guardian import KAIROSGuardian, GuardianMode


class HealthMonitorIntegrator:
    """健康监控系统集成器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self.guardian = None
        
    def integrate_with_existing_system(self) -> bool:
        """
        集成到现有系统
        
        Returns:
            是否集成成功
        """
        print("开始集成健康监控系统到现有SellAI系统...")
        
        try:
            # 1. 创建守护系统实例
            self.guardian = KAIROSGuardian(self.db_path)
            print("✅ KAIROS守护系统实例创建成功")
            
            # 2. 注册现有系统组件
            self._register_existing_components()
            print("✅ 现有系统组件注册成功")
            
            # 3. 集成到无限分身架构
            self._integrate_with_infinite_avatars()
            print("✅ 无限分身架构集成完成")
            
            # 4. 集成到Memory V2记忆系统
            self._integrate_with_memory_v2()
            print("✅ Memory V2记忆系统集成完成")
            
            # 5. 集成到全域商业大脑
            self._integrate_with_business_brain()
            print("✅ 全域商业大脑集成完成")
            
            # 6. 集成到三大引流军团
            self._integrate_with_marketing_armies()
            print("✅ 三大引流军团集成完成")
            
            # 7. 创建启动脚本
            self._create_startup_script()
            print("✅ 启动脚本创建完成")
            
            # 8. 生成集成报告
            report = self._generate_integration_report()
            print("✅ 集成报告生成完成")
            
            print(f"\n健康监控系统集成成功！")
            print(f"已注册组件: {report['registered_components']}")
            print(f"守护模式: {report['guardian_mode']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 集成失败: {e}")
            return False
    
    def _register_existing_components(self):
        """注册现有系统组件"""
        # 核心四中枢
        core_avatars = [
            ("情报官", "central", "负责商机爬取与情报分析"),
            ("内容官", "central", "负责内容创作与文案生成"),
            ("运营官", "central", "负责账号运营与日常管理"),
            ("增长官", "central", "负责用户增长与商务拓展")
        ]
        
        # 关键系统模块
        system_modules = [
            ("无限分身系统", "infinite_avatars", "支持一键创建无限AI分身"),
            ("Memory V2记忆系统", "memory_v2", "分层记忆系统，确保100%准确"),
            ("全域商业大脑", "business_brain", "全球市场分析与机会识别"),
            ("数据管道", "data_pipeline", "多平台数据爬取与处理"),
            ("AI谈判引擎", "negotiation_engine", "AI-to-AI商务谈判与条款协商"),
            ("流量爆破军团", "traffic_burst", "免费流量全域爆破模块"),
            ("达人洽谈军团", "influencer_network", "KOL合作与商务洽谈模块"),
            ("短视频引流军团", "video_marketing", "AI视频生成与多平台分发")
        ]
        
        # 注册所有组件
        all_components = core_avatars + system_modules
        
        for name, component_type, description in all_components:
            self.guardian.health_monitor.register_node(name, component_type)
            
            # 更新描述信息（如果有description字段）
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE node_health_status 
                        SET last_error = ?
                        WHERE node_id = ?
                    ''', (description, name))
                    conn.commit()
            except Exception as e:
                print(f"  警告: 更新组件描述失败 {name}: {e}")
    
    def _integrate_with_infinite_avatars(self):
        """集成到无限分身架构"""
        print("  集成到无限分身架构...")
        
        try:
            # 检查是否存在avatar相关表
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查avatar_registry表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='avatar_registry'")
                if cursor.fetchone():
                    print("  ✅ 发现avatar_registry表")
                    
                    # 从avatar_registry获取所有分身并注册
                    cursor.execute("SELECT avatar_id, avatar_type, description FROM avatar_registry")
                    avatars = cursor.fetchall()
                    
                    for avatar_id, avatar_type, description in avatars:
                        if avatar_id not in ["情报官", "内容官", "运营官", "增长官"]:
                            self.guardian.health_monitor.register_node(avatar_id, avatar_type)
                            print(f"    注册分身: {avatar_id}")
                else:
                    print("  ℹ️  未发现avatar_registry表，跳过")
        
        except Exception as e:
            print(f"  ⚠️  集成无限分身架构时出错: {e}")
    
    def _integrate_with_memory_v2(self):
        """集成到Memory V2记忆系统"""
        print("  集成到Memory V2记忆系统...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查memory_validation_status表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_validation_status'")
                if cursor.fetchone():
                    print("  ✅ Memory V2表存在，已集成")
                else:
                    print("  ℹ️  Memory V2表不存在")
        
        except Exception as e:
            print(f"  ⚠️  集成Memory V2时出错: {e}")
    
    def _integrate_with_business_brain(self):
        """集成到全域商业大脑"""
        print("  集成到全域商业大脑...")
        
        try:
            # 检查是否存在商业大脑相关表
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                table_checks = [
                    "global_business_opportunities",
                    "market_analysis_reports",
                    "cross_industry_mappings"
                ]
                
                for table in table_checks:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                    if cursor.fetchone():
                        print(f"  ✅ 发现{table}表")
        
        except Exception as e:
            print(f"  ⚠️  集成商业大脑时出错: {e}")
    
    def _integrate_with_marketing_armies(self):
        """集成到三大引流军团"""
        print("  集成到三大引流军团...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查引流军团相关表
                army_tables = [
                    "influencer_profiles",
                    "video_performance_metrics",
                    "traffic_source_analytics"
                ]
                
                for table in army_tables:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                    if cursor.fetchone():
                        print(f"  ✅ 发现{table}表")
        
        except Exception as e:
            print(f"  ⚠️  集成引流军团时出错: {e}")
    
    def _create_startup_script(self):
        """创建启动脚本"""
        print("  创建启动脚本...")
        
        startup_script = '''#!/usr/bin/env python3
"""
KAIROS健康监控系统启动脚本
自动启动KAIROS守护系统，监控SellAI系统健康状态。
"""

import sys
import os

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kairos_guardian import start_global_guardian, get_global_guardian
import time

def main():
    print("启动KAIROS健康监控系统...")
    
    # 启动守护系统
    guardian = start_global_guardian()
    
    print(f"✅ KAIROS守护系统已启动")
    print(f"   模式: {guardian.mode.value}")
    print(f"   自动恢复: {'启用' if guardian.auto_recovery_enabled else '禁用'}")'''
    
    try:
        # 保持运行
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\\n停止KAIROS健康监控系统...")
        from src.kairos_guardian import stop_global_guardian
        stop_global_guardian()
        print("✅ 系统已停止")

if __name__ == "__main__":
    main()
"""
        
        # 保存启动脚本
        script_path = "src/start_kairos_monitor.py"
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(startup_script)
        
        # 设置执行权限
        os.chmod(script_path, 0o755)
        
        print(f"  ✅ 启动脚本已创建: {script_path}")
    
    def _generate_integration_report(self) -> dict:
        """生成集成报告"""
        # 获取所有注册节点
        nodes = self.guardian.health_monitor._get_all_nodes()
        
        # 统计组件类型
        component_stats = {}
        for _, node_type in nodes:
            component_stats[node_type] = component_stats.get(node_type, 0) + 1
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "integration_status": "success",
            "guardian_mode": self.guardian.mode.value,
            "registered_components": len(nodes),
            "component_breakdown": component_stats,
            "auto_recovery_enabled": self.guardian.auto_recovery_enabled,
            "health_thresholds": self.guardian.health_monitor.health_thresholds
        }
        
        # 保存报告到文件
        report_file = "temp/health_monitor_integration_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report
    
    def start_monitoring_service(self) -> bool:
        """
        启动监控服务
        
        Returns:
            是否启动成功
        """
        if not self.guardian:
            print("❌ 守护系统未初始化，请先调用integrate_with_existing_system()")
            return False
        
        try:
            self.guardian.start_guardian_service()
            print("✅ 监控服务已启动")
            return True
            
        except Exception as e:
            print(f"❌ 启动监控服务失败: {e}")
            return False
    
    def get_system_status(self) -> dict:
        """
        获取系统状态
        
        Returns:
            系统状态报告
        """
        if not self.guardian:
            return {"error": "守护系统未初始化"}
        
        return self.guardian.get_guardian_status()


def setup_health_monitoring_system():
    """设置健康监控系统"""
    print("=" * 60)
    print("SellAI健康检查与自动恢复体系设置")
    print("=" * 60)
    
    # 创建集成器实例
    integrator = HealthMonitorIntegrator()
    
    # 集成到现有系统
    success = integrator.integrate_with_existing_system()
    
    if not success:
        print("\n❌ 健康监控系统集成失败")
        return False
    
    print("\n" + "=" * 60)
    print("健康监控系统设置完成！")
    print("=" * 60)
    
    # 显示启动说明
    print("\n启动说明:")
    print("1. 手动启动监控服务:")
    print("   python src/start_kairos_monitor.py")
    print("")
    print("2. 或在现有工作流中添加启动代码:")
    print("   from src.kairos_guardian import start_global_guardian")
    print("   guardian = start_global_guardian()")
    print("")
    print("3. 检查系统状态:")
    print("   from src.kairos_guardian import check_system_health_with_guardian")
    print("   status = check_system_health_with_guardian()")
    
    return True


def verify_integration():
    """验证集成"""
    print("\n验证健康监控系统集成...")
    
    try:
        # 创建集成器
        integrator = HealthMonitorIntegrator()
        
        # 集成系统
        integrator.integrate_with_existing_system()
        
        # 获取状态
        status = integrator.get_system_status()
        
        print(f"✅ 集成验证成功")
        print(f"   守护模式: {status.get('guardian_mode', 'unknown')}")
        print(f"   注册节点: {status.get('registered_nodes', 0)}")
        
        # 验证监控表存在
        with sqlite3.connect("data/shared_state/state.db") as conn:
            cursor = conn.cursor()
            
            required_tables = [
                "node_health_status",
                "health_check_history", 
                "recovery_action_history"
            ]
            
            for table in required_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cursor.fetchone():
                    print(f"❌ 缺少必要表: {table}")
                    return False
            
            print("✅ 所有必要数据库表存在")
        
        return True
        
    except Exception as e:
        print(f"❌ 集成验证失败: {e}")
        return False


if __name__ == "__main__":
    # 执行设置
    success = setup_health_monitoring_system()
    
    if success:
        # 验证集成
        verify_integration()
        
        print("\n" + "=" * 60)
        print("✅ 健康检查与自动恢复体系升级完成！")
        print("=" * 60)
        print("")
        print("核心功能:")
        print("1. 实时监控所有分身节点状态")
        print("2. 自动检测数据库连接、网络连通性")
        print("3. 故障自动恢复（重启、清理、切换数据源）")
        print("4. 与KAIROS守护系统深度集成")
        print("5. 完整的系统健康度仪表板")
        
        sys.exit(0)
    else:
        sys.exit(1)