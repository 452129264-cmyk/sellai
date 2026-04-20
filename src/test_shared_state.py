"""
共享状态库测试脚本
验证共享状态库的各项功能：去重、任务分配、分身能力匹配、成本记录等。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import tempfile
import json
from datetime import datetime, timedelta
from src.shared_state_manager import SharedStateManager


class TestSharedStateManager(unittest.TestCase):
    """共享状态管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 使用临时数据库文件
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.manager = SharedStateManager(db_path=self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        self.manager.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_01_database_initialization(self):
        """测试数据库初始化"""
        # 检查表是否存在
        conn = self.manager.connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'processed_opportunities',
            'task_assignments', 
            'avatar_capability_profiles',
            'cost_consumption_logs'
        ]
        
        for table in expected_tables:
            self.assertIn(table, tables, f"表 '{table}' 不存在")
        
        self.manager.close()
        print("✓ 数据库初始化测试通过")
    
    def test_02_opportunity_deduplication(self):
        """测试商机去重功能"""
        # 第一次检查 - 应该是新商机
        is_new1, hash1 = self.manager.check_and_record_opportunity(
            source_platform="Amazon",
            original_id="B08N5WRWNW",
            title="男士牛仔裤 - 高品质牛仔布料"
        )
        self.assertTrue(is_new1, "第一次检查应为新商机")
        
        # 第二次检查相同商机 - 应该不是新商机
        is_new2, hash2 = self.manager.check_and_record_opportunity(
            source_platform="Amazon",
            original_id="B08N5WRWNW",
            title="男士牛仔裤 - 高品质牛仔布料"
        )
        self.assertFalse(is_new2, "第二次检查应不是新商机")
        self.assertEqual(hash1, hash2, "相同商机应产生相同哈希值")
        
        # 检查不同商机 - 应该是新商机
        is_new3, hash3 = self.manager.check_and_record_opportunity(
            source_platform="TikTok",
            original_id="video_123456",
            title="牛仔穿搭教程爆款视频"
        )
        self.assertTrue(is_new3, "不同商机应为新商机")
        self.assertNotEqual(hash1, hash3, "不同商机应产生不同哈希值")
        
        print("✓ 商机去重测试通过")
    
    def test_03_task_assignment_and_completion(self):
        """测试任务分配与完成"""
        # 注册测试分身
        self.manager.register_or_update_avatar_profile(
            avatar_id="test_avatar_01",
            avatar_name="测试分身01",
            template_id="vertical_001",
            capability_scores={
                "data_crawling": 0.8,
                "financial_analysis": 0.9
            },
            specialization_tags=["测试", "分析"]
        )
        
        # 记录一个新商机
        is_new, opportunity_hash = self.manager.check_and_record_opportunity(
            source_platform="测试平台",
            original_id="test_001",
            title="测试商机"
        )
        
        # 分配任务
        assignment_id = self.manager.record_task_assignment(
            opportunity_hash=opportunity_hash,
            assigned_avatar="test_avatar_01",
            priority=2
        )
        
        self.assertIsNotNone(assignment_id, "分配ID不应为空")
        self.assertGreater(assignment_id, 0, "分配ID应大于0")
        
        # 检查任务记录
        assignments = self.manager.get_task_assignments(
            avatar_id="test_avatar_01",
            status="pending"
        )
        
        self.assertEqual(len(assignments), 1, "应找到1个待处理任务")
        self.assertEqual(assignments[0]['assignment_id'], assignment_id, "任务ID应匹配")
        
        # 检查分身负载
        profiles = self.manager.get_avatar_profiles(["test_avatar_01"])
        self.assertEqual(len(profiles), 1, "应找到1个分身")
        self.assertEqual(profiles[0]['current_load'], 1, "分身负载应为1")
        
        # 标记任务完成
        result_summary = "测试任务完成，结果良好"
        self.manager.update_task_completion(
            assignment_id=assignment_id,
            completion_status="completed",
            result_summary=result_summary
        )
        
        # 检查任务状态更新
        assignments = self.manager.get_task_assignments(
            avatar_id="test_avatar_01",
            status="completed"
        )
        
        self.assertEqual(len(assignments), 1, "应找到1个已完成任务")
        self.assertEqual(assignments[0]['result_summary'], result_summary, "结果摘要应匹配")
        
        # 检查分身负载减少
        profiles = self.manager.get_avatar_profiles(["test_avatar_01"])
        self.assertEqual(profiles[0]['current_load'], 0, "分身负载应为0")
        self.assertEqual(profiles[0]['total_tasks_completed'], 1, "完成任务数应为1")
        self.assertGreater(profiles[0]['success_rate'], 0, "成功率应大于0")
        
        print("✓ 任务分配与完成测试通过")
    
    def test_04_avatar_capability_matching(self):
        """测试分身能力匹配"""
        # 注册多个测试分身
        self.manager.register_or_update_avatar_profile(
            avatar_id="avatar_data",
            avatar_name="数据爬取专家",
            template_id="vertical_002",
            capability_scores={
                "data_crawling": 0.95,
                "trend_prediction": 0.7,
                "financial_analysis": 0.6
            },
            specialization_tags=["数据爬取", "分析"]
        )
        
        self.manager.register_or_update_avatar_profile(
            avatar_id="avatar_content",
            avatar_name="内容创作专家",
            template_id="vertical_003",
            capability_scores={
                "content_creation": 0.92,
                "trend_prediction": 0.8,
                "data_crawling": 0.5
            },
            specialization_tags=["内容创作", "营销"]
        )
        
        self.manager.register_or_update_avatar_profile(
            avatar_id="avatar_finance",
            avatar_name="财务分析专家",
            template_id="vertical_004",
            capability_scores={
                "financial_analysis": 0.96,
                "data_crawling": 0.6,
                "content_creation": 0.4
            },
            specialization_tags=["财务分析", "投资"]
        )
        
        # 测试1：需要数据爬取能力
        best_avatar1 = self.manager.find_best_avatar_for_task(
            required_capabilities=["data_crawling"]
        )
        self.assertEqual(best_avatar1, "avatar_data", "数据爬取任务应分配给数据爬取专家")
        
        # 测试2：需要内容创作能力
        best_avatar2 = self.manager.find_best_avatar_for_task(
            required_capabilities=["content_creation"]
        )
        self.assertEqual(best_avatar2, "avatar_content", "内容创作任务应分配给内容创作专家")
        
        # 测试3：需要财务分析能力
        best_avatar3 = self.manager.find_best_avatar_for_task(
            required_capabilities=["financial_analysis"]
        )
        self.assertEqual(best_avatar3, "avatar_finance", "财务分析任务应分配给财务分析专家")
        
        # 测试4：需要多种能力
        best_avatar4 = self.manager.find_best_avatar_for_task(
            required_capabilities=["data_crawling", "trend_prediction"]
        )
        # avatar_data的数据爬取0.95，趋势预测0.7，综合分数可能最高
        # avatar_content的数据爬取0.5，趋势预测0.8
        # avatar_finance的数据爬取0.6，趋势预测可能没有或低
        self.assertEqual(best_avatar4, "avatar_data", "数据爬取+趋势预测任务应分配给数据爬取专家")
        
        # 测试5：考虑负载因素
        # 给avatar_data增加负载
        self.manager.register_or_update_avatar_profile(
            avatar_id="avatar_data",
            avatar_name="数据爬取专家",
            template_id="vertical_002",
            capability_scores={
                "data_crawling": 0.95,
                "trend_prediction": 0.7,
                "financial_analysis": 0.6
            },
            specialization_tags=["数据爬取", "分析"],
            # 注意：当前API不支持直接设置负载，这里简化测试
        )
        
        # 在实际场景中，负载高的分身分数会降低
        
        print("✓ 分身能力匹配测试通过")
    
    def test_05_cost_recording_and_summary(self):
        """测试成本记录与汇总"""
        # 注册测试分身
        self.manager.register_or_update_avatar_profile(
            avatar_id="cost_avatar_01",
            avatar_name="成本测试分身01",
            template_id="vertical_005"
        )
        
        # 记录不同成本类型
        now = datetime.now().isoformat()
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        # 记录token消耗
        self.manager.record_cost_consumption(
            avatar_id="cost_avatar_01",
            cost_type="tokens",
            amount=15000,  # 15k tokens
            period_start=one_hour_ago,
            period_end=now,
            notes="测试对话消耗"
        )
        
        # 记录工作流执行
        self.manager.record_cost_consumption(
            avatar_id="cost_avatar_01",
            cost_type="workflow_executions",
            amount=50,  # 50次执行
            period_start=one_hour_ago,
            period_end=now,
            notes="测试工作流执行"
        )
        
        # 记录API调用
        self.manager.record_cost_consumption(
            avatar_id="cost_avatar_01",
            cost_type="api_calls",
            amount=20,  # 20次API调用
            period_start=one_hour_ago,
            period_end=now,
            notes="测试Amazon PAAPI调用"
        )
        
        # 获取成本汇总
        cost_summary = self.manager.get_cost_summary(
            start_date=one_hour_ago,
            end_date=now
        )
        
        self.assertIn("total_cost", cost_summary, "汇总应包含总成本")
        self.assertIn("breakdown", cost_summary, "汇总应包含成本明细")
        self.assertIn("avatar_ranking", cost_summary, "汇总应包含分身成本排名")
        
        total_cost = cost_summary["total_cost"]
        self.assertGreater(total_cost, 0, "总成本应大于0")
        
        breakdown = cost_summary["breakdown"]
        self.assertGreater(len(breakdown), 0, "成本明细不应为空")
        
        # 检查每种成本类型都有记录
        cost_types = [item["cost_type"] for item in breakdown]
        self.assertIn("tokens", cost_types, "应有token成本记录")
        self.assertIn("workflow_executions", cost_types, "应有工作流执行成本记录")
        self.assertIn("api_calls", cost_types, "应有API调用成本记录")
        
        print("✓ 成本记录与汇总测试通过")
    
    def test_06_system_statistics(self):
        """测试系统统计"""
        # 注册分身
        self.manager.register_or_update_avatar_profile(
            avatar_id="stats_avatar_01",
            avatar_name="统计测试分身01"
        )
        
        # 记录几个商机
        for i in range(3):
            is_new, _ = self.manager.check_and_record_opportunity(
                source_platform=f"平台_{i}",
                original_id=f"id_{i}",
                title=f"测试商机_{i}"
            )
        
        # 分配并完成一个任务
        _, hash_val = self.manager.check_and_record_opportunity(
            source_platform="完成测试",
            original_id="complete_001",
            title="待完成任务"
        )
        
        assignment_id = self.manager.record_task_assignment(
            opportunity_hash=hash_val,
            assigned_avatar="stats_avatar_01"
        )
        
        self.manager.update_task_completion(
            assignment_id=assignment_id,
            completion_status="completed",
            result_summary="测试完成"
        )
        
        # 获取统计
        stats = self.manager.get_statistics()
        
        self.assertIn("total_opportunities", stats, "统计应包含总商机数")
        self.assertIn("completed_opportunities", stats, "统计应包含已完成商机数")
        self.assertIn("total_tasks", stats, "统计应包含总任务数")
        self.assertIn("total_avatars", stats, "统计应包含总分身数")
        
        self.assertEqual(stats["total_opportunities"], 4, "总商机数应为4")
        self.assertEqual(stats["completed_opportunities"], 1, "已完成商机数应为1")
        self.assertEqual(stats["total_tasks"], 1, "总任务数应为1")
        self.assertEqual(stats["total_avatars"], 1, "总分身数应为1")
        
        print("✓ 系统统计测试通过")
    
    def test_07_avatar_profile_management(self):
        """测试分身画像管理"""
        # 注册分身
        self.manager.register_or_update_avatar_profile(
            avatar_id="profile_avatar_01",
            avatar_name="画像测试分身01",
            template_id="vertical_006",
            capability_scores={
                "data_crawling": 0.85,
                "content_creation": 0.75
            },
            specialization_tags=["测试", "管理"]
        )
        
        # 获取分身列表
        profiles = self.manager.get_avatar_profiles()
        self.assertGreater(len(profiles), 0, "分身列表不应为空")
        
        # 查找特定分身
        target_profile = None
        for profile in profiles:
            if profile["avatar_id"] == "profile_avatar_01":
                target_profile = profile
                break
        
        self.assertIsNotNone(target_profile, "应找到测试分身")
        self.assertEqual(target_profile["avatar_name"], "画像测试分身01", "分身名称应匹配")
        self.assertEqual(target_profile["template_id"], "vertical_006", "模板ID应匹配")
        
        # 检查能力分数解析
        self.assertIsInstance(target_profile["capability_scores"], dict, "能力分数应为字典")
        self.assertEqual(target_profile["capability_scores"]["data_crawling"], 0.85, "数据爬取分数应匹配")
        self.assertEqual(target_profile["capability_scores"]["content_creation"], 0.75, "内容创作分数应匹配")
        
        # 检查专业标签解析
        self.assertIsInstance(target_profile["specialization_tags"], list, "专业标签应为列表")
        self.assertIn("测试", target_profile["specialization_tags"], "应包含测试标签")
        self.assertIn("管理", target_profile["specialization_tags"], "应包含管理标签")
        
        # 更新分身信息
        self.manager.register_or_update_avatar_profile(
            avatar_id="profile_avatar_01",
            avatar_name="更新后的分身01",
            template_id="vertical_006_updated",
            capability_scores={
                "data_crawling": 0.90,
                "content_creation": 0.80,
                "financial_analysis": 0.70
            },
            specialization_tags=["测试", "管理", "更新"]
        )
        
        # 验证更新
        profiles = self.manager.get_avatar_profiles(["profile_avatar_01"])
        self.assertEqual(len(profiles), 1, "应找到更新后的分身")
        self.assertEqual(profiles[0]["avatar_name"], "更新后的分身01", "分身名称应已更新")
        self.assertEqual(profiles[0]["template_id"], "vertical_006_updated", "模板ID应已更新")
        self.assertEqual(profiles[0]["capability_scores"]["financial_analysis"], 0.70, "应新增财务分析能力")
        
        print("✓ 分身画像管理测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("共享状态库测试开始")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试用例
    test_cases = [
        TestSharedStateManager('test_01_database_initialization'),
        TestSharedStateManager('test_02_opportunity_deduplication'),
        TestSharedStateManager('test_03_task_assignment_and_completion'),
        TestSharedStateManager('test_04_avatar_capability_matching'),
        TestSharedStateManager('test_05_cost_recording_and_summary'),
        TestSharedStateManager('test_06_system_statistics'),
        TestSharedStateManager('test_07_avatar_profile_management'),
    ]
    
    suite.addTests(test_cases)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print("共享状态库测试完成")
    print("=" * 60)
    
    # 输出测试统计
    print(f"测试总数: {result.testsRun}")
    print(f"失败数: {len(result.failures)}")
    print(f"错误数: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ 所有测试通过！")
        return True
    else:
        print("❌ 测试失败！")
        # 输出失败详情
        for test, traceback in result.failures + result.errors:
            print(f"\n失败测试: {test}")
            print(f"错误详情:\n{traceback}")
        return False


if __name__ == "__main__":
    # 运行测试
    success = run_all_tests()
    
    # 输出测试报告文件
    test_report = {
        "test_timestamp": datetime.now().isoformat(),
        "tests_run": 7,
        "success": success,
        "components_tested": [
            "database_initialization",
            "opportunity_deduplication", 
            "task_assignment_and_completion",
            "avatar_capability_matching",
            "cost_recording_and_summary",
            "system_statistics",
            "avatar_profile_management"
        ],
        "recommendations": [
            "共享状态库核心功能测试完成",
            "建议集成到工作流前进行端到端测试",
            "生产环境部署前进行压力测试"
        ]
    }
    
    # 保存测试报告
    report_file = "outputs/共享状态库测试报告.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(test_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n测试报告已保存: {report_file}")
    
    # 返回状态码
    sys.exit(0 if success else 1)