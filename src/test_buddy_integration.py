#!/usr/bin/env python3
"""
Buddy系统集成测试
测试Buddy系统与KAIROS守护系统的深度集成
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock, patch

# 导入要测试的模块
from src.buddy_system import BuddySystem, UserMood, InteractionType
from src.kairos_guardian import KAIROSGuardian, GuardianMode
from src.health_monitor import HealthMonitor, NodeStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestBuddySystem(unittest.TestCase):
    """Buddy系统基本功能测试"""
    
    def setUp(self):
        """测试前准备"""
        # 使用内存数据库进行测试
        self.db_path = ":memory:"
        self.buddy = BuddySystem(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        if self.buddy.running:
            self.buddy.stop_interaction_service()
    
    def test_buddy_initialization(self):
        """测试Buddy系统初始化"""
        self.assertIsNotNone(self.buddy)
        self.assertIsInstance(self.buddy, BuddySystem)
        self.assertEqual(self.buddy.user_state["user_id"], "default_user")
    
    def test_interaction_message_generation(self):
        """测试交互消息生成"""
        message = self.buddy._generate_interaction_message(InteractionType.GREETING)
        self.assertIsInstance(message, str)
        self.assertGreater(len(message), 0)
        
        message = self.buddy._generate_interaction_message(InteractionType.STATUS_CHECK)
        self.assertIsInstance(message, str)
        self.assertGreater(len(message), 0)
    
    def test_user_mood_setting(self):
        """测试用户情绪设置"""
        self.buddy.set_user_mood(UserMood.HAPPY)
        self.assertEqual(self.buddy.user_state["current_mood"], "happy")
        
        self.buddy.set_user_mood(UserMood.FOCUSED)
        self.assertEqual(self.buddy.user_state["current_mood"], "focused")
    
    def test_interaction_enable_disable(self):
        """测试交互启用/禁用"""
        self.buddy.enable_interactions(False)
        self.assertFalse(self.buddy.interaction_enabled)
        
        self.buddy.enable_interactions(True)
        self.assertTrue(self.buddy.interaction_enabled)


class TestBuddyKAIROSIntegration(unittest.TestCase):
    """Buddy与KAIROS集成测试"""
    
    def setUp(self):
        """测试前准备"""
        # 使用内存数据库进行测试
        self.db_path = ":memory:"
        self.guardian = KAIROSGuardian(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        if self.guardian.monitoring_active:
            self.guardian.stop_guardian_service()
    
    def test_guardian_buddy_integration(self):
        """测试Guardian与Buddy系统集成"""
        # 验证Buddy系统被正确集成
        self.assertIsNotNone(self.guardian.buddy_system)
        self.assertIsInstance(self.guardian.buddy_system, BuddySystem)
    
    def test_service_start_stop_integration(self):
        """测试服务启动停止集成"""
        # 启动守护服务
        self.guardian.start_guardian_service()
        self.assertTrue(self.guardian.monitoring_active)
        
        # 验证Buddy服务也被启动
        time.sleep(0.5)  # 给线程启动一点时间
        self.assertTrue(self.guardian.buddy_system.running)
        
        # 停止守护服务
        self.guardian.stop_guardian_service()
        self.assertFalse(self.guardian.monitoring_active)
        
        # 验证Buddy服务也被停止
        time.sleep(0.5)
        self.assertFalse(self.guardian.buddy_system.running)
    
    def test_guardian_status_includes_buddy(self):
        """测试Guardian状态包含Buddy系统信息"""
        # 获取状态报告
        status = self.guardian.get_guardian_status()
        
        # 验证包含Buddy系统状态
        self.assertIn("buddy_system_status", status)
        buddy_status = status["buddy_system_status"]
        
        self.assertIn("interaction_enabled", buddy_status)
        self.assertIn("total_interactions", buddy_status)
        self.assertIn("active_interactions", buddy_status)
        self.assertIn("user_mood", buddy_status)


class TestBuddyUserInteraction(unittest.TestCase):
    """Buddy用户交互测试"""
    
    def setUp(self):
        """测试前准备"""
        self.db_path = ":memory:"
        self.buddy = BuddySystem(self.db_path)
        self.buddy.start_interaction_service()
        
        # 等待服务启动
        time.sleep(1)
    
    def tearDown(self):
        """测试后清理"""
        self.buddy.stop_interaction_service()
    
    def test_interaction_initiation(self):
        """测试交互发起"""
        # 模拟触发交互
        with patch.object(self.buddy, '_should_initiate_interaction', return_value=True):
            with patch.object(self.buddy, '_determine_interaction_type', 
                            return_value=InteractionType.GREETING):
                self.buddy._interaction_loop_iteration()
                
        # 验证交互历史记录
        summary = self.buddy.get_interaction_summary()
        self.assertGreater(summary["total_interactions"], 0)
    
    def test_user_response_processing(self):
        """测试用户响应处理"""
        # 模拟一个交互
        interaction_id = 1
        self.buddy.active_interactions[interaction_id] = {
            "type": InteractionType.STATUS_CHECK.value,
            "message": "今天感觉怎么样？",
            "initiated_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # 处理用户响应
        response_text = "我今天感觉不错，工作效率很高！"
        self.buddy.process_user_response(interaction_id, response_text, "happy")
        
        # 验证交互状态更新
        interaction = self.buddy.active_interactions.get(interaction_id)
        if interaction:
            self.assertEqual(interaction["status"], "responded")
            self.assertEqual(interaction["response_text"], response_text)


class TestBuddyHealthMonitorIntegration(unittest.TestCase):
    """Buddy与健康监控集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.db_path = ":memory:"
        self.health_monitor = HealthMonitor(self.db_path)
        self.buddy = BuddySystem(self.db_path)
        
        # 注册测试节点
        self.health_monitor.register_node("情报官", "central")
        self.health_monitor.register_node("Buddy系统", "interaction")
    
    def test_health_monitor_buddy_awareness(self):
        """测试健康监控对Buddy系统的感知"""
        # 更新Buddy系统心跳
        self.health_monitor.update_heartbeat("Buddy系统")
        
        # 检查节点状态
        nodes = self.health_monitor._get_all_nodes()
        node_ids = [node[0] for node in nodes]
        
        self.assertIn("Buddy系统", node_ids)
    
    def test_buddy_health_check_integration(self):
        """测试Buddy健康检查集成"""
        # 执行健康检查
        result = self.health_monitor.perform_health_check(
            "Buddy系统",
            "数据库连接检查"
        )
        
        # 验证检查结果基本结构
        self.assertIn("status", result)
        self.assertIn("success", result)


def run_comprehensive_test():
    """运行综合测试"""
    print("=" * 60)
    print("Buddy系统集成综合测试")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTest(unittest.makeSuite(TestBuddySystem))
    suite.addTest(unittest.makeSuite(TestBuddyKAIROSIntegration))
    suite.addTest(unittest.makeSuite(TestBuddyUserInteraction))
    suite.addTest(unittest.makeSuite(TestBuddyHealthMonitorIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"总测试数: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ 所有测试通过！")
        return True
    else:
        print("\n❌ 测试失败！")
        if result.failures:
            print("\n失败详情:")
            for test, traceback in result.failures:
                print(f"\n{test}:")
                print(traceback)
        return False


def test_buddy_system_in_production():
    """模拟生产环境测试"""
    print("\n" + "=" * 60)
    print("模拟生产环境测试")
    print("=" * 60)
    
    # 使用实际数据库路径
    db_path = "data/shared_state/state.db"
    
    print("1. 初始化Buddy系统...")
    buddy = BuddySystem(db_path)
    
    print("2. 启动交互服务...")
    buddy.start_interaction_service()
    
    print("3. 模拟用户交互...")
    
    # 设置用户情绪
    buddy.set_user_mood(UserMood.FOCUSED)
    
    # 模拟触发一个交互
    buddy._initiate_interaction(
        InteractionType.STATUS_CHECK,
        datetime.now()
    )
    
    # 等待交互处理
    time.sleep(2)
    
    print("4. 检查系统状态...")
    summary = buddy.get_interaction_summary()
    print(f"   总交互数: {summary['total_interactions']}")
    print(f"   活跃交互: {summary['active_interactions']}")
    print(f"   用户情绪: {summary['user_state']['current_mood']}")
    
    print("5. 停止服务...")
    buddy.stop_interaction_service()
    
    print("\n✅ 生产环境模拟测试完成")


if __name__ == "__main__":
    print("Buddy系统集成测试开始")
    print("-" * 60)
    
    # 运行单元测试
    unit_test_passed = run_comprehensive_test()
    
    if unit_test_passed:
        # 运行生产环境模拟测试
        test_buddy_system_in_production()
        
        print("\n" + "=" * 60)
        print("Buddy系统集成测试全部完成 ✅")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Buddy系统集成测试失败，请检查问题 ❌")
        print("=" * 60)