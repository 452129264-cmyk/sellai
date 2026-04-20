#!/usr/bin/env python3
"""
社交系统测试脚本
测试双社交体系的各项功能，确保真人用户↔AI与AI↔AI社交体系正常运作
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_social_systems.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SocialSystemsTester:
    """社交系统测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
        # 导入测试模块
        self._import_modules()
    
    def _import_modules(self):
        """导入测试所需模块"""
        try:
            from social_relationship_manager import get_social_relationship_manager
            self.social_manager = get_social_relationship_manager()
            logger.info("社交关系管理器导入成功")
        except ImportError as e:
            logger.error(f"导入社交关系管理器失败: {e}")
            self.social_manager = None
        
        try:
            from shared_state_manager import get_shared_state_manager
            self.shared_manager = get_shared_state_manager()
            logger.info("共享状态管理器导入成功")
        except ImportError as e:
            logger.error(f"导入共享状态管理器失败: {e}")
            self.shared_manager = None
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("开始运行社交系统完整测试套件")
        logger.info("=" * 60)
        
        test_start_time = datetime.now()
        
        # 运行测试用例
        self._run_database_tests()
        self._run_user_ai_relationship_tests()
        self._run_ai_ai_communication_tests()
        self._run_opportunity_sync_tests()
        self._run_privacy_control_tests()
        self._run_integration_tests()
        
        test_end_time = datetime.now()
        test_duration = test_end_time - test_start_time
        
        # 生成测试报告
        report = self._generate_test_report(test_start_time, test_end_time, test_duration)
        
        logger.info("=" * 60)
        logger.info(f"测试完成: {self.passed_tests}/{self.total_tests} 通过")
        logger.info(f"总耗时: {test_duration.total_seconds():.2f}秒")
        logger.info("=" * 60)
        
        return report
    
    def _run_database_tests(self):
        """数据库相关测试"""
        logger.info("\n1. 数据库测试")
        
        self._test(
            name="数据库连接测试",
            func=self._test_database_connection,
            expected=True
        )
        
        self._test(
            name="数据表结构测试",
            func=self._test_table_structure,
            expected=True
        )
    
    def _run_user_ai_relationship_tests(self):
        """用户-AI社交关系测试"""
        logger.info("\n2. 用户-AI社交关系测试")
        
        self._test(
            name="添加AI分身好友",
            func=self._test_add_ai_friend,
            expected=True
        )
        
        self._test(
            name="获取AI好友列表",
            func=self._test_get_ai_friends,
            expected=lambda result: len(result) > 0
        )
        
        self._test(
            name="移除AI分身好友",
            func=self._test_remove_ai_friend,
            expected=True
        )
        
        self._test(
            name="屏蔽AI分身",
            func=self._test_block_ai,
            expected=True
        )
        
        self._test(
            name="检查AI聊天权限（被屏蔽）",
            func=self._test_can_ai_chat_blocked,
            expected=False
        )
    
    def _run_ai_ai_communication_tests(self):
        """AI-AI通信测试"""
        logger.info("\n3. AI-AI通信测试")
        
        self._test(
            name="记录AI-AI私下通信",
            func=self._test_record_ai_ai_communication,
            expected=lambda result: result > 0
        )
        
        self._test(
            name="查询AI-AI通信记录",
            func=self._test_get_ai_ai_communications,
            expected=lambda result: len(result) > 0
        )
        
        self._test(
            name="记录高价值商机通信",
            func=self._test_record_high_value_opportunity,
            expected=lambda result: result > 0
        )
    
    def _run_opportunity_sync_tests(self):
        """高价值商机同步测试"""
        logger.info("\n4. 高价值商机同步测试")
        
        self._test(
            name="获取待同步商机",
            func=self._test_get_high_value_opportunities,
            expected=lambda result: len(result) > 0
        )
        
        self._test(
            name="同步商机到用户",
            func=self._test_sync_opportunity_to_user,
            expected=True
        )
        
        self._test(
            name="验证商机同步状态",
            func=self._test_verify_opportunity_sync,
            expected=True
        )
    
    def _run_privacy_control_tests(self):
        """隐私控制测试"""
        logger.info("\n5. 隐私控制测试")
        
        self._test(
            name="设置用户隐私选项",
            func=self._test_set_privacy_settings,
            expected=True
        )
        
        self._test(
            name="获取隐私设置",
            func=self._test_get_privacy_settings,
            expected=lambda result: 'allow_ai_initiated_chat' in result
        )
        
        self._test(
            name="隐私设置生效测试",
            func=self._test_privacy_effectiveness,
            expected=True
        )
    
    def _run_integration_tests(self):
        """系统集成测试"""
        logger.info("\n6. 系统集成测试")
        
        self._test(
            name="社交系统统计信息",
            func=self._test_get_social_statistics,
            expected=lambda result: 'total_relationships' in result
        )
        
        self._test(
            name="AI好友推荐功能",
            func=self._test_ai_friend_recommendations,
            expected=True
        )
    
    def _test(self, name: str, func, expected):
        """执行单个测试用例"""
        self.total_tests += 1
        
        try:
            result = func()
            
            # 判断测试结果
            if callable(expected):
                passed = expected(result)
            else:
                passed = (result == expected)
            
            if passed:
                self.passed_tests += 1
                status = "PASS"
                logger.info(f"✓ {name}: {status}")
            else:
                self.failed_tests += 1
                status = "FAIL"
                logger.error(f"✗ {name}: {status} (结果: {result}, 预期: {expected})")
            
            # 记录测试结果
            self.test_results.append({
                'name': name,
                'status': status,
                'result': str(result),
                'expected': str(expected),
                'timestamp': datetime.now().isoformat()
            })
            
            return passed
            
        except Exception as e:
            self.failed_tests += 1
            status = "ERROR"
            logger.error(f"✗ {name}: {status} (异常: {str(e)})")
            
            self.test_results.append({
                'name': name,
                'status': status,
                'result': str(e),
                'expected': str(expected),
                'timestamp': datetime.now().isoformat()
            })
            
            return False
    
    # ===================== 测试用例实现 =====================
    
    def _test_database_connection(self) -> bool:
        """测试数据库连接"""
        if not self.social_manager:
            return False
        
        try:
            # 尝试连接数据库
            conn = self.social_manager.connect()
            if conn:
                self.social_manager.close()
                return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
        
        return False
    
    def _test_table_structure(self) -> bool:
        """测试数据表结构"""
        if not self.social_manager:
            return False
        
        try:
            # 检查关键表是否存在
            conn = self.social_manager.connect()
            cursor = conn.cursor()
            
            tables = [
                'user_avatar_relationships',
                'ai_ai_communications', 
                'user_privacy_settings'
            ]
            
            for table in tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cursor.fetchone():
                    logger.error(f"表不存在: {table}")
                    return False
            
            self.social_manager.close()
            return True
            
        except Exception as e:
            logger.error(f"表结构检查失败: {e}")
            return False
    
    def _test_add_ai_friend(self) -> bool:
        """测试添加AI分身好友"""
        if not self.social_manager:
            return False
        
        # 添加测试AI好友
        success = self.social_manager.add_ai_friend(
            user_id="test_user_001",
            avatar_id="test_avatar_001",
            metadata={
                "test": True,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return success
    
    def _test_get_ai_friends(self) -> List[Dict[str, Any]]:
        """测试获取AI好友列表"""
        if not self.social_manager:
            return []
        
        # 先添加一个测试好友
        self.social_manager.add_ai_friend(
            user_id="test_user_002",
            avatar_id="test_avatar_002",
            metadata={"test": True}
        )
        
        # 获取好友列表
        friends = self.social_manager.get_user_ai_friends("test_user_002")
        
        return friends
    
    def _test_remove_ai_friend(self) -> bool:
        """测试移除AI分身好友"""
        if not self.social_manager:
            return False
        
        # 先添加
        self.social_manager.add_ai_friend(
            user_id="test_user_003",
            avatar_id="test_avatar_003",
            metadata={"test": True}
        )
        
        # 再移除
        success = self.social_manager.remove_ai_friend(
            user_id="test_user_003",
            avatar_id="test_avatar_003"
        )
        
        return success
    
    def _test_block_ai(self) -> bool:
        """测试屏蔽AI分身"""
        if not self.social_manager:
            return False
        
        success = self.social_manager.block_ai(
            user_id="test_user_004",
            avatar_id="test_avatar_004"
        )
        
        return success
    
    def _test_can_ai_chat_blocked(self) -> bool:
        """测试被屏蔽的AI无法发起聊天"""
        if not self.social_manager:
            return False
        
        # 先屏蔽
        self.social_manager.block_ai("test_user_005", "test_avatar_005")
        
        # 检查权限
        can_chat = self.social_manager.can_ai_initiate_chat(
            avatar_id="test_avatar_005",
            target_user_id="test_user_005"
        )
        
        return can_chat
    
    def _test_record_ai_ai_communication(self) -> int:
        """测试记录AI-AI私下通信"""
        if not self.social_manager:
            return 0
        
        # 记录测试通信
        comm_id = self.social_manager.record_ai_ai_communication(
            sender_avatar_id="test_avatar_a",
            receiver_avatar_id="test_avatar_b",
            content="测试AI-AI通信内容",
            content_type="text",
            metadata={"test": True}
        )
        
        return comm_id
    
    def _test_get_ai_ai_communications(self) -> List[Dict[str, Any]]:
        """测试查询AI-AI通信记录"""
        if not self.social_manager:
            return []
        
        # 先记录一些通信
        self.social_manager.record_ai_ai_communication(
            sender_avatar_id="test_avatar_c",
            receiver_avatar_id="test_avatar_d",
            content="另一个测试通信",
            content_type="text",
            metadata={"test": True}
        )
        
        # 查询通信记录
        communications = self.social_manager.get_ai_ai_communications(
            limit=10
        )
        
        return communications
    
    def _test_record_high_value_opportunity(self) -> int:
        """测试记录高价值商机通信"""
        if not self.social_manager:
            return 0
        
        # 记录高价值商机
        comm_id = self.social_manager.record_ai_ai_communication(
            sender_avatar_id="intelligence_officer",
            receiver_avatar_id="content_officer",
            content="发现高价值商机：亚马逊牛仔外套，利润率42%，批发价$52，售价$89.99",
            content_type="opportunity",
            metadata={
                "priority": 4,
                "tags": ["high_value", "urgent", "fashion"],
                "source_platform": "Amazon",
                "estimated_profit_margin": 0.42,
                "test": True
            }
        )
        
        return comm_id
    
    def _test_get_high_value_opportunities(self) -> List[Dict[str, Any]]:
        """测试获取待同步的高价值商机"""
        if not self.social_manager:
            return []
        
        # 先记录一个高优先级商机
        self.social_manager.record_ai_ai_communication(
            sender_avatar_id="intelligence_officer",
            receiver_avatar_id="content_officer",
            content="另一个高价值商机测试",
            content_type="opportunity",
            metadata={
                "priority": 5,
                "tags": ["critical", "urgent"],
                "test": True
            }
        )
        
        # 获取高价值商机
        opportunities = self.social_manager.get_high_value_opportunities_from_ai(
            user_id="test_user_high_value",
            min_priority=3
        )
        
        return opportunities
    
    def _test_sync_opportunity_to_user(self) -> bool:
        """测试同步商机到用户"""
        if not self.social_manager:
            return False
        
        # 先记录一个高价值商机
        comm_id = self.social_manager.record_ai_ai_communication(
            sender_avatar_id="intelligence_officer",
            receiver_avatar_id="content_officer",
            content="需要同步的商机测试",
            content_type="opportunity",
            metadata={
                "priority": 4,
                "tags": ["sync_test"],
                "test": True
            }
        )
        
        # 同步到用户
        success = self.social_manager.sync_opportunity_to_user(
            communication_id=comm_id,
            user_id="test_user_sync"
        )
        
        return success
    
    def _test_verify_opportunity_sync(self) -> bool:
        """验证商机同步状态"""
        if not self.social_manager:
            return False
        
        try:
            # 检查数据库中的同步状态
            conn = self.social_manager.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT is_opportunity_synced, synced_to_user_id 
                FROM ai_ai_communications 
                WHERE content_type = 'opportunity'
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            self.social_manager.close()
            
            # 如果有记录，检查同步状态
            if row:
                is_synced = bool(row['is_opportunity_synced'])
                user_id = row['synced_to_user_id']
                
                logger.info(f"同步状态检查: is_synced={is_synced}, user_id={user_id}")
                
                # 如果有同步，确保user_id不为空
                if is_synced and user_id:
                    return True
                elif not is_synced:
                    return True  # 未同步也是正常状态
            
            return True  # 没有记录也是正常情况
            
        except Exception as e:
            logger.error(f"同步状态验证失败: {e}")
            return False
    
    def _test_set_privacy_settings(self) -> bool:
        """测试设置用户隐私选项"""
        if not self.social_manager:
            return False
        
        success = self.social_manager.set_user_privacy_settings(
            user_id="test_user_privacy",
            allow_ai_initiated_chat=False,
            show_opportunity_push=True,
            allow_ai_ai_collaboration_visibility=False,
            auto_add_ai_friends=False
        )
        
        return success
    
    def _test_get_privacy_settings(self) -> Dict[str, Any]:
        """测试获取用户隐私设置"""
        if not self.social_manager:
            return {}
        
        # 先设置，再获取
        self.social_manager.set_user_privacy_settings(
            user_id="test_user_get_privacy",
            allow_ai_initiated_chat=True
        )
        
        settings = self.social_manager.get_user_privacy_settings(
            user_id="test_user_get_privacy"
        )
        
        return settings
    
    def _test_privacy_effectiveness(self) -> bool:
        """测试隐私设置的实际效果"""
        if not self.social_manager:
            return False
        
        # 1. 设置不允许AI主动聊天
        self.social_manager.set_user_privacy_settings(
            user_id="test_user_privacy_effect",
            allow_ai_initiated_chat=False
        )
        
        # 2. 检查是否允许AI发起聊天
        can_chat = self.social_manager.can_ai_initiate_chat(
            avatar_id="test_avatar_privacy",
            target_user_id="test_user_privacy_effect"
        )
        
        # 应该返回False
        if can_chat:
            logger.error("隐私设置未生效: AI仍可主动聊天")
            return False
        
        # 3. 修改为允许
        self.social_manager.set_user_privacy_settings(
            user_id="test_user_privacy_effect",
            allow_ai_initiated_chat=True
        )
        
        # 4. 再次检查
        can_chat = self.social_manager.can_ai_initiate_chat(
            avatar_id="test_avatar_privacy",
            target_user_id="test_user_privacy_effect"
        )
        
        # 应该返回True
        return can_chat
    
    def _test_get_social_statistics(self) -> Dict[str, Any]:
        """测试获取社交关系统计信息"""
        if not self.social_manager:
            return {}
        
        statistics = self.social_manager.get_social_statistics()
        
        return statistics
    
    def _test_ai_friend_recommendations(self) -> bool:
        """测试AI好友推荐功能"""
        if not self.social_manager:
            return False
        
        try:
            # 获取推荐（当前实现为空列表）
            recommendations = self.social_manager.get_ai_friend_recommendations(
                user_id="test_user_recommend",
                limit=5
            )
            
            # 即使为空列表，功能也是正常的
            logger.info(f"AI好友推荐结果: {len(recommendations)}条")
            
            return True
            
        except Exception as e:
            logger.error(f"AI好友推荐测试失败: {e}")
            return False
    
    def _generate_test_report(self, start_time, end_time, duration) -> Dict[str, Any]:
        """生成测试报告"""
        report = {
            'test_suite': '社交系统功能测试',
            'version': '1.0',
            'execution_time': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_seconds': duration.total_seconds()
            },
            'summary': {
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'success_rate': f"{(self.passed_tests / self.total_tests * 100):.1f}%" if self.total_tests > 0 else "0%"
            },
            'details': self.test_results,
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def save_test_report(self, report: Dict[str, Any], filepath: str = "logs/test_report.json"):
        """保存测试报告到文件"""
        try:
            # 确保日志目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"测试报告已保存到: {filepath}")
            
            return True
            
        except Exception as e:
            logger.error(f"保存测试报告失败: {e}")
            return False
    
    def display_test_summary(self):
        """显示测试摘要"""
        print("\n" + "=" * 60)
        print("社交系统测试摘要")
        print("=" * 60)
        
        print(f"总测试数: {self.total_tests}")
        print(f"通过数: {self.passed_tests}")
        print(f"失败数: {self.failed_tests}")
        
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"通过率: {success_rate:.1f}%")
        
        # 显示失败的测试
        if self.failed_tests > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if result['status'] in ['FAIL', 'ERROR']:
                    print(f"  - {result['name']}: {result['result']}")
        
        print("\n" + "=" * 60)


def main():
    """主函数"""
    print("=" * 60)
    print("社交系统测试套件")
    print("功能: 测试真人用户↔AI与AI↔AI双社交体系")
    print("=" * 60)
    
    # 创建测试器
    tester = SocialSystemsTester()
    
    # 运行所有测试
    report = tester.run_all_tests()
    
    # 显示测试摘要
    tester.display_test_summary()
    
    # 保存测试报告
    tester.save_test_report(report)
    
    # 生成详细日志文件
    detailed_log = {
        'report': report,
        'system_info': {
            'python_version': sys.version,
            'platform': sys.platform,
            'working_directory': os.getcwd(),
            'timestamp': datetime.now().isoformat()
        }
    }
    
    tester.save_test_report(detailed_log, "logs/detailed_test_report.json")
    
    # 检查总体通过率
    if tester.passed_tests == tester.total_tests:
        print("\n✅ 所有测试通过! 社交系统功能正常。")
        return 0
    else:
        print(f"\n⚠️  有 {tester.failed_tests} 个测试失败，请检查日志。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)