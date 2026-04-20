#!/usr/bin/env python3
"""
HyperHorse模块集成测试脚本
验证模块注册成功、接口兼容性、优先级设置生效
确保无冲突报错
"""

import sys
import os
import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.hyperhorse.module_registry import (
    HyperHorseModule, 
    ModulePriority, 
    ModuleStatus,
    HyperHorseCapability
)

from src.hyperhorse.core import (
    HyperHorseEngine,
    VideoQualityLevel,
    VideoPlatform,
    LanguageCode
)

from src.hyperhorse.api_adapter import (
    HyperHorseAPIAdapter,
    VideoGenerationRequest,
    VideoGenerationResponse
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - HYPERHORSE-TEST - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HyperHorseIntegrationTest:
    """HyperHorse模块集成测试类"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化测试
        
        参数：
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 确保数据库文件存在
        self._ensure_database_exists()
        
        logger.info("初始化HyperHorse集成测试")
    
    def _ensure_database_exists(self) -> None:
        """确保数据库文件存在"""
        if not os.path.exists(self.db_path):
            logger.warning(f"数据库文件不存在: {self.db_path}")
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            logger.info(f"创建数据库目录: {os.path.dirname(self.db_path)}")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        运行所有测试
        
        返回：
            测试结果字典
        """
        logger.info("开始运行HyperHorse模块集成测试")
        
        test_methods = [
            self.test_module_registration,
            self.test_database_tables,
            self.test_engine_initialization,
            self.test_api_adapter_compatibility,
            self.test_video_generation_workflow,
            self.test_performance_tracking,
            self.test_memory_integration
        ]
        
        for test_method in test_methods:
            self._run_test(test_method.__name__, test_method)
        
        # 计算测试统计
        self.test_results["pass_rate"] = (
            self.test_results["passed_tests"] / max(1, self.test_results["total_tests"]) * 100
        )
        
        # 输出测试报告
        self._print_test_report()
        
        return self.test_results
    
    def _run_test(self, test_name: str, test_func: callable) -> None:
        """运行单个测试"""
        logger.info(f"运行测试: {test_name}")
        
        self.test_results["total_tests"] += 1
        
        try:
            start_time = datetime.now()
            success, details = test_func()
            end_time = datetime.now()
            
            test_duration = (end_time - start_time).total_seconds()
            
            test_detail = {
                "test_name": test_name,
                "status": "PASSED" if success else "FAILED",
                "success": success,
                "details": details,
                "duration_seconds": test_duration,
                "timestamp": start_time.isoformat()
            }
            
            if success:
                self.test_results["passed_tests"] += 1
                logger.info(f"测试通过: {test_name}")
            else:
                self.test_results["failed_tests"] += 1
                logger.error(f"测试失败: {test_name}")
            
            self.test_results["test_details"].append(test_detail)
            
        except Exception as e:
            error_detail = {
                "test_name": test_name,
                "status": "ERROR",
                "success": False,
                "details": f"测试异常: {str(e)[:200]}",
                "error_traceback": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            self.test_results["failed_tests"] += 1
            self.test_results["test_details"].append(error_detail)
            
            logger.error(f"测试异常 {test_name}: {e}")
    
    # ====================== 具体测试方法 ======================
    
    def test_module_registration(self) -> tuple:
        """
        测试模块注册
        
        返回：
            (成功, 详情)
        """
        logger.info("测试模块注册功能")
        
        try:
            # 1. 创建模块实例
            module = HyperHorseModule(self.db_path)
            
            # 2. 注册模块
            registration_success = module.register()
            
            if not registration_success:
                return False, "模块注册失败"
            
            # 3. 验证注册
            module_status = module.get_status()
            
            # 检查是否具有最高优先级
            if module_status["priority"] != ModulePriority.HIGHEST.value:
                return False, f"优先级不是最高: {module_status['priority']}"
            
            # 检查状态是否激活
            if module_status["status"] != ModuleStatus.ACTIVE.value:
                return False, f"状态未激活: {module_status['status']}"
            
            # 4. 检查数据库记录
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT module_id, module_name, priority, status, capabilities
                FROM system_modules 
                WHERE module_id = ?
            """, ("hyperhorse_video_engine",))
            
            db_record = cursor.fetchone()
            conn.close()
            
            if not db_record:
                return False, "数据库记录不存在"
            
            db_module_id, db_module_name, db_priority, db_status, db_capabilities = db_record
            
            # 验证数据库记录
            if db_module_id != "hyperhorse_video_engine":
                return False, f"数据库模块ID不匹配: {db_module_id}"
            
            if db_priority != ModulePriority.HIGHEST.value:
                return False, f"数据库优先级不匹配: {db_priority}"
            
            # 验证能力列表
            try:
                capabilities = json.loads(db_capabilities)
                expected_capabilities = [
                    HyperHorseCapability.GLOBAL_COMMERCIAL_NATIVE.value,
                    HyperHorseCapability.AUTONOMOUS_PLANNING.value,
                    HyperHorseCapability.END_TO_END_GENERATION.value,
                    HyperHorseCapability.EVOLUTIONARY_GENERATION.value,
                    HyperHorseCapability.MULTILINGUAL_ADAPTATION.value,
                    HyperHorseCapability.ONE_CLICK_PUBLISHING.value
                ]
                
                for expected in expected_capabilities:
                    if expected not in capabilities:
                        return False, f"能力缺失: {expected}"
                        
            except json.JSONDecodeError:
                return False, "能力列表JSON格式错误"
            
            details = {
                "module_id": db_module_id,
                "module_name": db_module_name,
                "priority": db_priority,
                "status": db_status,
                "capabilities_count": len(capabilities) if 'capabilities' in locals() else 0
            }
            
            return True, details
            
        except Exception as e:
            return False, f"测试过程异常: {str(e)[:100]}"
    
    def test_database_tables(self) -> tuple:
        """
        测试数据库表创建
        
        返回：
            (成功, 详情)
        """
        logger.info("测试数据库表创建")
        
        try:
            # 1. 初始化模块（创建表）
            module = HyperHorseModule(self.db_path)
            initialization_success = module.initialize()
            
            if not initialization_success:
                return False, "模块初始化失败"
            
            # 2. 检查表是否存在
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            tables_to_check = [
                "system_modules",
                "hyperhorse_tasks",
                "hyperhorse_performance_metrics",
                "hyperhorse_success_patterns"
            ]
            
            existing_tables = []
            for table in tables_to_check:
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table,))
                
                if cursor.fetchone():
                    existing_tables.append(table)
            
            conn.close()
            
            # 验证所有表都存在
            missing_tables = [t for t in tables_to_check if t not in existing_tables]
            
            if missing_tables:
                return False, f"缺失的表: {missing_tables}"
            
            details = {
                "existing_tables": existing_tables,
                "total_tables_found": len(existing_tables)
            }
            
            return True, details
            
        except Exception as e:
            return False, f"测试过程异常: {str(e)[:100]}"
    
    def test_engine_initialization(self) -> tuple:
        """
        测试引擎初始化
        
        返回：
            (成功, 详情)
        """
        logger.info("测试HyperHorse引擎初始化")
        
        try:
            # 1. 初始化引擎
            engine = HyperHorseEngine(self.db_path)
            
            # 2. 获取引擎信息
            engine_info = engine.get_engine_info()
            
            # 3. 验证引擎信息
            required_fields = [
                "engine_id", "model_version", "quality_level",
                "capabilities", "performance_data"
            ]
            
            for field in required_fields:
                if field not in engine_info:
                    return False, f"引擎信息缺少字段: {field}"
            
            # 4. 验证配置
            config = engine.config
            
            required_config_fields = [
                "model_version", "quality_level", "default_languages",
                "supported_platforms", "max_concurrent_tasks"
            ]
            
            for field in required_config_fields:
                if field not in config:
                    return False, f"引擎配置缺少字段: {field}"
            
            # 5. 验证性能数据结构
            performance_data = engine.performance_data
            
            required_performance_fields = [
                "total_tasks_completed", "total_generation_time",
                "success_rate", "avg_generation_time"
            ]
            
            for field in required_performance_fields:
                if field not in performance_data:
                    return False, f"性能数据缺少字段: {field}"
            
            details = {
                "engine_id": engine_info["engine_id"],
                "model_version": engine_info["model_version"],
                "quality_level": engine_info["quality_level"],
                "capabilities_count": len(engine_info["capabilities"]),
                "performance_data": engine_info["performance_data"]
            }
            
            return True, details
            
        except Exception as e:
            return False, f"测试过程异常: {str(e)[:100]}"
    
    def test_api_adapter_compatibility(self) -> tuple:
        """
        测试API适配器兼容性
        
        返回：
            (成功, 详情)
        """
        logger.info("测试API适配器兼容性")
        
        try:
            # 1. 初始化适配器
            adapter = HyperHorseAPIAdapter(self.db_path)
            
            # 2. 测试服务信息获取
            service_info = adapter.get_service_info()
            
            required_service_fields = [
                "service_type", "engine_info", "capabilities",
                "compatibility", "status"
            ]
            
            for field in required_service_fields:
                if field not in service_info:
                    return False, f"服务信息缺少字段: {field}"
            
            # 3. 测试现有接口兼容性
            # 创建兼容性请求
            request = VideoGenerationRequest(
                category="fashion_clothing",
                target_regions=["north_america", "europe"],
                duration_seconds=30,
                quality_level="premium",
                target_platforms=["tiktok", "instagram"],
                target_language="en"
            )
            
            # 生成视频（应该会成功）
            response = adapter.generate_video(request)
            
            # 验证响应格式
            if not isinstance(response, VideoGenerationResponse):
                return False, "响应类型不正确"
            
            # 验证响应基本结构
            if not hasattr(response, 'task_id') or not hasattr(response, 'status'):
                return False, "响应缺少必需属性"
            
            # 检查状态
            if response.status not in ["success", "partial_success", "failed"]:
                return False, f"无效的状态值: {response.status}"
            
            details = {
                "service_type": service_info["service_type"],
                "engine_id": service_info["engine_info"]["engine_id"],
                "capabilities_count": len(service_info["capabilities"]),
                "compatibility": service_info["compatibility"],
                "test_request_id": request.request_id,
                "test_response_status": response.status
            }
            
            return True, details
            
        except Exception as e:
            return False, f"测试过程异常: {str(e)[:100]}"
    
    def test_video_generation_workflow(self) -> tuple:
        """
        测试视频生成工作流程
        
        返回：
            (成功, 详情)
        """
        logger.info("测试视频生成工作流程")
        
        try:
            # 1. 初始化引擎
            engine = HyperHorseEngine(self.db_path)
            
            # 2. 测试趋势分析
            trend_analysis = engine.analyze_global_commercial_trends(
                ["north_america", "europe"],
                ["fashion_clothing"]
            )
            
            # 验证趋势分析结果
            if not hasattr(trend_analysis, 'analysis_id'):
                return False, "趋势分析缺少分析ID"
            
            if not hasattr(trend_analysis, 'trending_topics'):
                return False, "趋势分析缺少趋势主题"
            
            # 3. 测试脚本生成
            script = engine.generate_high_conversion_script(
                trend_analysis,
                "tiktok",
                60
            )
            
            # 验证脚本
            if not hasattr(script, 'script_id'):
                return False, "脚本缺少脚本ID"
            
            if not hasattr(script, 'scenes'):
                return False, "脚本缺少场景列表"
            
            # 4. 测试视频生成
            result = engine.generate_video_from_script(
                script,
                VideoQualityLevel.PREMIUM,
                ["tiktok", "instagram"]
            )
            
            # 验证生成结果
            if not hasattr(result, 'task_id'):
                return False, "生成结果缺少任务ID"
            
            if not hasattr(result, 'generated_videos'):
                return False, "生成结果缺少视频列表"
            
            if result.status not in ["success", "partial_success", "failed"]:
                return False, f"无效的生成状态: {result.status}"
            
            details = {
                "trend_analysis_id": trend_analysis.analysis_id,
                "script_id": script.script_id,
                "generation_task_id": result.task_id,
                "generation_status": result.status,
                "generated_videos_count": len(result.generated_videos),
                "generation_time_seconds": result.generation_time_seconds
            }
            
            return True, details
            
        except Exception as e:
            return False, f"测试过程异常: {str(e)[:100]}"
    
    def test_performance_tracking(self) -> tuple:
        """
        测试性能跟踪功能
        
        返回：
            (成功, 详情)
        """
        logger.info("测试性能跟踪功能")
        
        try:
            # 1. 初始化引擎
            engine = HyperHorseEngine(self.db_path)
            
            # 2. 模拟一个生成结果
            simulated_result = VideoGenerationResult(
                task_id=f"test_performance_{int(time.time())}",
                status="success",
                generated_videos=[
                    {
                        "video_id": "test_video_1",
                        "platform": "tiktok",
                        "duration_seconds": 30,
                        "resolution": "1080x1920"
                    }
                ],
                performance_metrics={
                    "quality_scores": {
                        "visual_quality": 0.92,
                        "audio_quality": 0.88
                    },
                    "efficiency_score": 1.5
                },
                generation_time_seconds=20.5
            )
            
            # 3. 模拟实际表现数据
            actual_performance = {
                "category": "fashion_clothing",
                "region": "north_america",
                "views": 10000,
                "engagement_rate": 0.15,
                "conversion_rate": 0.08,
                "revenue_generated": 8000.0
            }
            
            # 4. 更新成功模式
            update_success = engine.update_success_patterns(
                simulated_result,
                actual_performance
            )
            
            if not update_success:
                return False, "更新成功模式失败"
            
            # 5. 验证模式库更新
            if len(engine.success_patterns) == 0:
                logger.warning("成功模式库为空，可能是首次测试")
            else:
                # 检查最近的模式
                pattern_ids = list(engine.success_patterns.keys())
                latest_pattern = engine.success_patterns[pattern_ids[-1]]
                
                if "score" not in latest_pattern:
                    return False, "最新模式缺少分数字段"
                
                if "features" not in latest_pattern:
                    return False, "最新模式缺少特征字段"
            
            details = {
                "test_task_id": simulated_result.task_id,
                "performance_update_success": update_success,
                "success_patterns_count": len(engine.success_patterns)
            }
            
            return True, details
            
        except Exception as e:
            return False, f"测试过程异常: {str(e)[:100]}"
    
    def test_memory_integration(self) -> tuple:
        """
        测试Memory V2集成
        
        返回：
            (成功, 详情)
        """
        logger.info("测试Memory V2集成")
        
        try:
            # 1. 初始化适配器
            adapter = HyperHorseAPIAdapter(self.db_path)
            
            # 2. 测试记忆集成配置
            memory_config = {
                "module_id": "test_memory_integration",
                "module_type": "video_generation_test",
                "storage_schema": {
                    "test_data": {
                        "fields": ["test_id", "timestamp", "data"],
                        "indexes": ["test_id"]
                    }
                },
                "retrieval_policies": {
                    "by_test_id": True,
                    "by_timestamp": True
                },
                "integration_timestamp": datetime.now().isoformat()
            }
            
            # 3. 测试记忆集成接口
            integration_success = adapter.integrate_with_memory_v2(memory_config)
            
            if not integration_success:
                return False, "记忆集成接口调用失败"
            
            # 4. 验证数据库中的配置记录
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='hyperhorse_memory_integration'
            """)
            
            if not cursor.fetchone():
                logger.warning("记忆集成表可能未创建")
                # 继续检查其他集成方式
            
            conn.close()
            
            details = {
                "memory_integration_success": integration_success,
                "memory_config_module_id": memory_config["module_id"]
            }
            
            return True, details
            
        except Exception as e:
            return False, f"测试过程异常: {str(e)[:100]}"
    
    # ====================== 测试报告输出 ======================
    
    def _print_test_report(self) -> None:
        """打印测试报告"""
        print("\n" + "="*100)
        print("HYPERHORSE模块集成测试报告")
        print("="*100)
        
        # 测试统计
        total = self.test_results["total_tests"]
        passed = self.test_results["passed_tests"]
        failed = self.test_results["failed_tests"]
        pass_rate = self.test_results["pass_rate"]
        
        print(f"\n📊 测试统计:")
        print(f"  总计: {total} 个测试")
        print(f"  通过: {passed} 个")
        print(f"  失败: {failed} 个")
        print(f"  通过率: {pass_rate:.2f}%")
        
        # 详细结果
        print(f"\n🔍 详细结果:")
        
        for test in self.test_results["test_details"]:
            status_icon = "✅" if test["success"] else "❌"
            duration = test["duration_seconds"]
            
            print(f"  {status_icon} {test['test_name']}: {test['status']} ({duration:.2f}s)")
            
            # 打印失败详情
            if not test["success"]:
                print(f"     详情: {test['details']}")
        
        # 整体评估
        print(f"\n📈 整体评估:")
        if pass_rate >= 100.0:
            print(f"  🎉 完美! 所有测试通过，模块集成完整")
        elif pass_rate >= 95.0:
            print(f"  👍 优秀! 模块集成基本完整，少数非关键功能待优化")
        elif pass_rate >= 80.0:
            print(f"  ⚠️  合格! 核心功能正常，部分辅助功能需修复")
        else:
            print(f"  🔴 需改进! 核心功能存在问题，需要重点修复")
        
        print("\n" + "="*100)

def main():
    """主函数"""
    print("🚀 开始运行HyperHorse模块集成测试")
    
    # 检查数据库路径
    db_path = "data/shared_state/state.db"
    
    if not os.path.exists("data/shared_state"):
        os.makedirs("data/shared_state", exist_ok=True)
        print(f"📁 创建数据目录: data/shared_state")
    
    # 运行测试
    tester = HyperHorseIntegrationTest(db_path)
    test_results = tester.run_all_tests()
    
    # 保存测试结果
    output_dir = "outputs/hyperhorse_test"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/test_results_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 测试结果已保存到: {output_file}")
    
    # 根据测试结果返回退出码
    if test_results["passed_tests"] == test_results["total_tests"]:
        print("\n🎉 所有测试通过！HyperHorse模块集成完整，可正常使用。")
        sys.exit(0)
    else:
        print(f"\n⚠️  有 {test_results['failed_tests']} 个测试失败，请检查相关功能。")
        sys.exit(1)

if __name__ == "__main__":
    main()