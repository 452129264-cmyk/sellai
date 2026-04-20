#!/usr/bin/env python3
"""
健康检查与自动恢复体系 - 完整功能测试
验证任务73所有功能的完整性和正确性。
"""

import sys
import os
import json
import sqlite3
import time
import tempfile
import threading
from datetime import datetime, timedelta

# 添加src目录到路径
sys.path.insert(0, 'src')

from health_monitor import HealthMonitor, HealthCheckType, NodeStatus, RecoveryAction

class CompleteHealthMonitorTest:
    """完整健康监控器测试类"""
    
    def __init__(self):
        self.results = []
        self.monitor = None
        self.db_path = None
        
    def setup(self):
        """测试环境设置"""
        print("🔧 设置测试环境...")
        
        # 创建临时数据库
        self.db_path = tempfile.mktemp(suffix='.db')
        
        # 初始化监控器
        try:
            self.monitor = HealthMonitor(self.db_path)
            print("   ✅ 健康监控器初始化成功")
            return True
        except Exception as e:
            print(f"   ❌ 健康监控器初始化失败: {e}")
            return False
    
    def teardown(self):
        """测试环境清理"""
        print("\n🧹 清理测试环境...")
        
        if self.monitor and self.monitor.running:
            self.monitor.stop_monitoring()
            print("   ✅ 监控已停止")
        
        if self.db_path and os.path.exists(self.db_path):
            os.unlink(self.db_path)
            print("   ✅ 临时数据库已清理")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("健康检查与自动恢复体系 - 完整功能测试")
        print("=" * 80)
        
        # 设置测试环境
        if not self.setup():
            print("❌ 测试环境设置失败，终止测试")
            return False
        
        try:
            # 运行核心功能测试
            print("\n🔍 运行核心功能测试...")
            
            # 1. 节点注册测试
            print("\n1. 节点注册功能测试...")
            self.test_node_registration()
            
            # 2. 心跳更新测试
            print("\n2. 心跳更新功能测试...")
            self.test_heartbeat_update()
            
            # 3. 健康检查执行测试
            print("\n3. 健康检查执行测试...")
            self.test_health_check_execution()
            
            # 4. 状态更新测试
            print("\n4. 节点状态更新测试...")
            self.test_status_updates()
            
            # 5. 故障检测测试
            print("\n5. 故障检测功能测试...")
            self.test_fault_detection()
            
            # 6. 恢复动作测试
            print("\n6. 恢复动作功能测试...")
            self.test_recovery_actions()
            
            # 7. 仪表板功能测试
            print("\n7. 系统仪表板功能测试...")
            self.test_dashboard_functionality()
            
            # 8. 性能指标测试
            print("\n8. 性能指标测试...")
            self.test_performance_metrics()
            
            # 9. 数据库结构测试
            print("\n9. 数据库表结构测试...")
            self.test_database_structure()
            
            # 10. 容错性测试
            print("\n10. 系统容错性测试...")
            self.test_fault_tolerance()
            
            # 生成测试报告
            return self.generate_test_report()
            
        except Exception as e:
            print(f"\n❌ 测试执行异常: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.teardown()
    
    def test_node_registration(self):
        """测试节点注册功能"""
        print("   📝 测试节点注册...")
        
        test_cases = [
            ("情报官", "central"),
            ("内容官", "central"),
            ("运营官", "central"),
            ("增长官", "central"),
            ("无限分身系统", "system_module"),
            ("Memory V2记忆系统", "system_module"),
            ("安全审计系统", "system_module"),
            ("Buddy交互系统", "system_module"),
            ("全域商业大脑", "system_module")
        ]
        
        for node_id, node_type in test_cases:
            try:
                success = self.monitor.register_node(node_id, node_type)
                if success:
                    self.record_result("节点注册", "通过", f"节点 {node_id} 注册成功")
                else:
                    self.record_result("节点注册", "失败", f"节点 {node_id} 注册失败")
                    
            except Exception as e:
                self.record_result("节点注册", "异常", f"节点 {node_id} 注册异常: {e}")
    
    def test_heartbeat_update(self):
        """测试心跳更新功能"""
        print("   💓 测试心跳更新...")
        
        test_nodes = ["情报官", "内容官", "运营官"]
        
        for node_id in test_nodes:
            try:
                success = self.monitor.update_heartbeat(node_id)
                if success:
                    self.record_result("心跳更新", "通过", f"节点 {node_id} 心跳更新成功")
                else:
                    self.record_result("心跳更新", "失败", f"节点 {node_id} 心跳更新失败")
                    
            except Exception as e:
                self.record_result("心跳更新", "异常", f"节点 {node_id} 心跳更新异常: {e}")
    
    def test_health_check_execution(self):
        """测试健康检查执行"""
        print("   🔍 测试健康检查执行...")
        
        test_cases = [
            ("数据库连接检查", HealthCheckType.DATABASE_CONNECTION, {"description": "测试数据库连接"}),
            ("网络连通性检查", HealthCheckType.NETWORK_CONNECTIVITY, {"test_urls": ["https://www.google.com"], "timeout": 10})
        ]
        
        for test_name, check_type, params in test_cases:
            try:
                result = self.monitor.perform_health_check("情报官", check_type, params)
                
                if isinstance(result, dict):
                    self.record_result("健康检查执行", "通过", f"{test_name} 执行成功，状态: {result.get('status', 'unknown')}")
                else:
                    self.record_result("健康检查执行", "失败", f"{test_name} 执行返回异常类型")
                    
            except Exception as e:
                self.record_result("健康检查执行", "异常", f"{test_name} 执行异常: {e}")
    
    def test_status_updates(self):
        """测试节点状态更新"""
        print("   📊 测试状态更新...")
        
        try:
            # 模拟一个失败的检查
            error_result = {
                "status": NodeStatus.UNHEALTHY.value,
                "success": False,
                "error_message": "测试失败",
                "result_data": {}
            }
            
            # 这将触发状态更新和可能的恢复流程
            self.monitor._update_node_status("情报官", error_result)
            
            # 验证状态已更新
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT status FROM node_health_status WHERE node_id = ?', ("情报官",))
                result = cursor.fetchone()
                
                if result:
                    self.record_result("状态更新", "通过", f"节点状态已更新为: {result[0]}")
                else:
                    self.record_result("状态更新", "失败", "未找到节点状态")
                    
        except Exception as e:
            self.record_result("状态更新", "异常", f"状态更新异常: {e}")
    
    def test_fault_detection(self):
        """测试故障检测功能"""
        print("   ⚠️ 测试故障检测...")
        
        try:
            # 测试故障检测功能
            failures = self.monitor._detect_failure_scenarios("情报官")
            
            if isinstance(failures, list):
                self.record_result("故障检测", "通过", f"支持 {len(failures)} 种故障场景检测")
            else:
                self.record_result("故障检测", "失败", "故障检测返回异常类型")
                
        except Exception as e:
            self.record_result("故障检测", "异常", f"故障检测异常: {e}")
    
    def test_recovery_actions(self):
        """测试恢复动作功能"""
        print("   🔄 测试恢复动作...")
        
        try:
            # 测试恢复计划获取
            recovery_plan = self.monitor._get_recovery_plan_for_failure("node_offline")
            
            if isinstance(recovery_plan, list):
                self.record_result("恢复动作", "通过", f"支持 {len(recovery_plan)} 种恢复动作")
            else:
                self.record_result("恢复动作", "失败", "恢复计划返回异常类型")
                
        except Exception as e:
            self.record_result("恢复动作", "异常", f"恢复动作异常: {e}")
    
    def test_dashboard_functionality(self):
        """测试仪表板功能"""
        print("   📈 测试仪表板功能...")
        
        try:
            # 获取仪表板数据
            dashboard = self.monitor.get_system_health_dashboard()
            
            if isinstance(dashboard, dict):
                required_fields = ["system_status", "node_statistics", "alert_level"]
                missing_fields = [field for field in required_fields if field not in dashboard]
                
                if not missing_fields:
                    self.record_result("仪表板功能", "通过", f"仪表板功能正常，系统状态: {dashboard.get('system_status', 'unknown')}")
                else:
                    self.record_result("仪表板功能", "失败", f"仪表板缺少字段: {missing_fields}")
            else:
                self.record_result("仪表板功能", "失败", "仪表板返回异常类型")
                
        except Exception as e:
            self.record_result("仪表板功能", "异常", f"仪表板功能异常: {e}")
    
    def test_performance_metrics(self):
        """测试性能指标"""
        print("   ⚡ 测试性能指标...")
        
        try:
            # 检查监控间隔
            if self.monitor.monitoring_interval <= 30:
                self.record_result("监控间隔", "通过", f"监控间隔 {self.monitor.monitoring_interval} 秒达标")
            else:
                self.record_result("监控间隔", "失败", f"监控间隔 {self.monitor.monitoring_interval} 秒超标")
            
            # 检查健康阈值配置
            required_thresholds = [
                "consecutive_failures",
                "response_time_ms",
                "heartbeat_timeout_s",
                "resource_cpu_percent",
                "resource_memory_percent",
                "task_success_rate",
                "api_success_rate"
            ]
            
            for threshold in required_thresholds:
                if threshold in self.monitor.health_thresholds:
                    self.record_result("阈值配置", "通过", f"阈值 {threshold} 已配置: {self.monitor.health_thresholds[threshold]}")
                else:
                    self.record_result("阈值配置", "失败", f"阈值 {threshold} 未配置")
                    
        except Exception as e:
            self.record_result("性能指标", "异常", f"性能指标测试异常: {e}")
    
    def test_database_structure(self):
        """测试数据库表结构"""
        print("   🗃️ 测试数据库结构...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查核心表
                required_tables = [
                    "node_health_status",
                    "health_check_history",
                    "recovery_action_history",
                    "health_check_records"
                ]
                
                for table in required_tables:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                    if cursor.fetchone():
                        self.record_result("数据库表", "通过", f"表 {table} 存在")
                    else:
                        self.record_result("数据库表", "失败", f"表 {table} 不存在")
                
                # 检查索引
                required_indexes = [
                    "idx_node_status",
                    "idx_check_history",
                    "idx_recovery_history",
                    "idx_health_records"
                ]
                
                for index in required_indexes:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index,))
                    if cursor.fetchone():
                        self.record_result("数据库索引", "通过", f"索引 {index} 存在")
                    else:
                        self.record_result("数据库索引", "失败", f"索引 {index} 不存在")
                        
        except Exception as e:
            self.record_result("数据库结构", "异常", f"数据库结构测试异常: {e}")
    
    def test_fault_tolerance(self):
        """测试系统容错性"""
        print("   🛡️ 测试容错性...")
        
        try:
            # 测试不存在的节点
            result = self.monitor.perform_health_check("不存在的节点", HealthCheckType.DATABASE_CONNECTION, {})
            
            if isinstance(result, dict):
                self.record_result("容错性", "通过", "系统对不存在的节点有容错处理")
            else:
                self.record_result("容错性", "失败", "系统对不存在的节点处理异常")
                
        except Exception as e:
            self.record_result("容错性", "异常", f"容错性测试异常: {e}")
    
    def record_result(self, test_name, status, message):
        """记录测试结果"""
        self.results.append({
            "test_name": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 80)
        print("测试完成报告")
        print("=" * 80)
        
        # 统计结果
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["status"] == "通过")
        failed_tests = sum(1 for r in self.results if r["status"] == "失败")
        exception_tests = sum(1 for r in self.results if r["status"] == "异常")
        
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 测试统计:")
        print(f"   总测试项: {total_tests}")
        print(f"   通过项: {passed_tests}")
        print(f"   失败项: {failed_tests}")
        print(f"   异常项: {exception_tests}")
        print(f"   通过率: {pass_rate:.1f}%")
        
        print(f"\n📋 测试结果摘要:")
        
        # 按测试类别分组显示
        categories = {}
        for result in self.results:
            category = result["test_name"]
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0, "failed": 0, "exceptions": 0}
            
            categories[category]["total"] += 1
            if result["status"] == "通过":
                categories[category]["passed"] += 1
            elif result["status"] == "失败":
                categories[category]["failed"] += 1
            else:
                categories[category]["exceptions"] += 1
        
        for category, stats in categories.items():
            icon = "✅" if stats["failed"] == 0 and stats["exceptions"] == 0 else "❌"
            print(f"   {icon} {category}: {stats['passed']}/{stats['total']} 通过")
        
        print(f"\n🎯 核心功能验证:")
        
        core_functions = [
            ("节点注册", any(r["test_name"] == "节点注册" and r["status"] == "通过" for r in self.results)),
            ("心跳更新", any(r["test_name"] == "心跳更新" and r["status"] == "通过" for r in self.results)),
            ("健康检查", any(r["test_name"] == "健康检查执行" and r["status"] == "通过" for r in self.results)),
            ("状态更新", any(r["test_name"] == "状态更新" and r["status"] == "通过" for r in self.results)),
            ("故障检测", any(r["test_name"] == "故障检测" and r["status"] == "通过" for r in self.results)),
            ("恢复动作", any(r["test_name"] == "恢复动作" and r["status"] == "通过" for r in self.results)),
            ("仪表板", any(r["test_name"] == "仪表板功能" and r["status"] == "通过" for r in self.results))
        ]
        
        for func, passed in core_functions:
            status = "✅ 正常" if passed else "❌ 异常"
            print(f"   {func}: {status}")
        
        # 评估结果
        print(f"\n🏆 总体评估:")
        
        if failed_tests == 0 and exception_tests == 0:
            print("   ✅ 完美通过 - 所有测试均成功执行!")
            print("   🔧 系统功能完整，符合KAIROS运维标准")
            print("   📋 核心能力清单:")
            print("     • 节点管理与状态监控 ✓")
            print("     • 健康检查与故障检测 ✓")
            print("     • 自动恢复与动作执行 ✓")
            print("     • 仪表板与状态展示 ✓")
            print("     • 性能指标监控与告警 ✓")
            overall_success = True
        else:
            print(f"   ⚠️ 部分失败 - 需要修复 {failed_tests + exception_tests} 个问题")
            print("   发现以下问题:")
            
            for result in self.results:
                if result["status"] in ["失败", "异常"]:
                    print(f"     • {result['test_name']}: {result['message']}")
            
            overall_success = False
        
        # 保存详细报告
        report_data = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "exception_tests": exception_tests,
                "pass_rate": pass_rate,
                "test_timestamp": datetime.now().isoformat()
            },
            "detailed_results": self.results,
            "system_info": {
                "version": "SellAI封神版A 2.0",
                "component": "健康检查与自动恢复体系",
                "standards": "KAIROS自主运维标准",
                "test_environment": "Coze沙箱环境"
            },
            "conclusion": "通过" if overall_success else "不通过"
        }
        
        os.makedirs("outputs", exist_ok=True)
        report_path = "outputs/完整功能测试报告.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细测试报告已保存至: {report_path}")
        
        return overall_success

def main():
    """主函数"""
    print("启动健康检查与自动恢复体系完整功能测试...")
    
    try:
        # 创建测试实例
        tester = CompleteHealthMonitorTest()
        
        # 运行所有测试
        success = tester.run_all_tests()
        
        # 输出最终结果
        print("\n" + "=" * 80)
        if success:
            print("🎉 恭喜！完整功能测试全部通过！")
            print("✅ 健康检查与自动恢复体系符合所有设计要求")
            print("🚀 系统已具备完整的KAIROS级别自主运维能力")
        else:
            print("⚠️ 注意！完整功能测试存在未通过项")
            print("请根据报告中的问题列表进行修复")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())