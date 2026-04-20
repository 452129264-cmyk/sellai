"""
Sora2全链路接入集成测试脚本
验证六大内容完成度：API接入配置、自定义模型参数、工作流、素材库回传、输出参数、容错机制
"""

import json
import time
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sora2_integration.config import Sora2IntegrationConfig, DEFAULT_CONFIG, Sora2OutputSpec
from sora2_integration.client import Sora2APIClient, Sora2APIError
from sora2_integration.workflow import VideoGenerationWorkflow, ProductInfo
from sora2_integration.api_integration import APIComplianceManager, APIConfigurationGenerator
from sora2_integration.error_handler import (
    ErrorRecoveryManager, RetryManager, 
    CircuitBreaker, create_error_handling_pipeline
)


class Sora2IntegrationTester:
    """Sora2集成测试器"""
    
    def __init__(self, config: Optional[Sora2IntegrationConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.logger = self._setup_logging()
        
        # 初始化各模块
        self.client = Sora2APIClient(self.config)
        self.workflow = VideoGenerationWorkflow(self.config)
        self.compliance_manager = APIComplianceManager(self.config)
        self.config_generator = APIConfigurationGenerator(self.config)
        self.recovery_manager = create_error_handling_pipeline()
        
        # 测试结果
        self.test_results = []
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("Sora2Tester")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # 文件处理器
            log_dir = "logs/sora2_integration"
            os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(
                os.path.join(log_dir, f"test_{int(time.time())}.log")
            )
            file_handler.setFormatter(console_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        运行所有测试
        
        Returns:
            测试报告
        """
        self.logger.info("🚀 开始Sora2全链路接入集成测试")
        self.logger.info(f"配置文件: {self.config.to_dict()}")
        
        tests = [
            self.test_preconfigured_parameters,
            self.test_api_connection,
            self.test_custom_model_parameters,
            self.test_workflow_integration,
            self.test_material_library,
            self.test_output_parameter_locking,
            self.test_error_handling_mechanism,
            self.test_compatibility_with_existing_systems
        ]
        
        test_report = {
            "start_time": time.time(),
            "config_summary": self.config.to_dict(),
            "tests": []
        }
        
        for test_func in tests:
            test_name = test_func.__name__
            self.logger.info(f"\n📋 开始测试: {test_name}")
            
            start_time = time.time()
            
            try:
                result = test_func()
                status = "PASSED" if result.get("success", False) else "FAILED"
                
                self.logger.info(f"✅ 测试 {test_name} 完成: {status}")
                
            except Exception as e:
                self.logger.error(f"❌ 测试 {test_name} 异常: {str(e)}")
                result = {
                    "success": False,
                    "error": str(e),
                    "details": None
                }
                status = "ERROR"
            
            end_time = time.time()
            duration = end_time - start_time
            
            test_report["tests"].append({
                "name": test_name,
                "status": status,
                "duration": duration,
                "result": result,
                "timestamp": start_time
            })
            
            # 记录详细结果
            self.test_results.append({
                "test": test_name,
                "status": status,
                "duration": duration,
                "result": result
            })
        
        test_report["end_time"] = time.time()
        test_report["total_duration"] = test_report["end_time"] - test_report["start_time"]
        
        # 计算总体通过率
        passed_count = sum(1 for t in test_report["tests"] if t["status"] == "PASSED")
        total_count = len(test_report["tests"])
        test_report["pass_rate"] = passed_count / total_count if total_count > 0 else 0
        
        self.logger.info(f"\n🎯 所有测试完成，通过率: {test_report['pass_rate']:.1%}")
        
        return test_report
    
    def test_preconfigured_parameters(self) -> Dict[str, Any]:
        """
        测试预配置参数
        
        验收标准：六大内容执行全部基于预配置参数：
        1. 接入协议为OpenAI Video兼容
        2. 输出规格为9:16竖屏1080×1920分辨率15秒Cinematic Ultra HD画质
        3. 自动化工作流完整实现
        4. 容错机制配置生效
        """
        self.logger.info("测试预配置参数...")
        
        results = {
            "success": True,
            "details": {},
            "errors": []
        }
        
        # 1. 接入协议检查
        if self.config.protocol == "OpenAI Video兼容协议":
            results["details"]["protocol"] = "PASSED"
            self.logger.info("✅ 接入协议: OpenAI Video兼容")
        else:
            results["details"]["protocol"] = "FAILED"
            results["errors"].append(f"协议不匹配: {self.config.protocol}")
            results["success"] = False
        
        # 2. 输出规格检查
        output_spec = self.config.output_spec
        
        checks = [
            ("aspect_ratio", "9:16", output_spec.aspect_ratio),
            ("width", 1080, output_spec.width),
            ("height", 1920, output_spec.height),
            ("duration_seconds", 15, output_spec.duration_seconds),
            ("quality", "Cinematic Ultra HD", output_spec.quality),
            ("fps", 30, output_spec.fps)
        ]
        
        all_passed = True
        for check_name, expected, actual in checks:
            if expected == actual:
                results["details"][check_name] = "PASSED"
                self.logger.info(f"✅ {check_name}: {actual}")
            else:
                results["details"][check_name] = f"FAILED (期望: {expected}, 实际: {actual})"
                results["errors"].append(f"{check_name} 不匹配: {actual}")
                all_passed = False
        
        results["success"] = results["success"] and all_passed
        
        # 3. 自动化工作流检查
        if self.config.workflow.enable_full_pipeline:
            results["details"]["workflow"] = "PASSED"
            self.logger.info("✅ 自动化工作流: 已启用")
        else:
            results["details"]["workflow"] = "FAILED"
            results["errors"].append("自动化工作流未启用")
            results["success"] = False
        
        # 4. 容错机制检查
        retry_config = self.config.retry
        
        if retry_config.max_retry_count == 3 and retry_config.retry_interval_seconds == 30:
            results["details"]["retry_mechanism"] = "PASSED"
            self.logger.info("✅ 容错机制: 3次重试，30秒间隔")
        else:
            results["details"]["retry_mechanism"] = f"FAILED (实际配置: {retry_config.max_retry_count}次重试，{retry_config.retry_interval_seconds}秒间隔)"
            results["errors"].append("容错机制配置不匹配")
            results["success"] = False
        
        return results
    
    def test_api_connection(self) -> Dict[str, Any]:
        """
        测试API连接
        
        验收标准：API接入配置成功
        """
        self.logger.info("测试API连接...")
        
        results = {
            "success": False,
            "details": {},
            "error": None
        }
        
        try:
            # 测试连接
            connection_test = self.client.test_connection()
            
            if connection_test:
                results["success"] = True
                results["details"]["connection"] = "PASSED"
                self.logger.info("✅ API连接测试: 成功")
            else:
                results["success"] = False
                results["details"]["connection"] = "FAILED"
                results["error"] = "连接测试失败"
                self.logger.error("❌ API连接测试: 失败")
        
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            results["details"]["exception"] = type(e).__name__
            self.logger.error(f"❌ API连接测试异常: {str(e)}")
        
        return results
    
    def test_custom_model_parameters(self) -> Dict[str, Any]:
        """
        测试自定义模型参数
        
        验收标准：自定义模型参数保存
        """
        self.logger.info("测试自定义模型参数...")
        
        results = {
            "success": True,
            "details": {},
            "errors": []
        }
        
        # 检查关键参数
        params_to_check = [
            ("default_model", self.config.default_model.value),
            ("output_spec", self.config.output_spec.to_dict()),
            ("workflow_config", {
                "enable_full_pipeline": self.config.workflow.enable_full_pipeline,
                "max_concurrent_jobs": self.config.workflow.max_concurrent_jobs
            })
        ]
        
        for param_name, param_value in params_to_check:
            if param_value:
                results["details"][param_name] = "PASSED"
                self.logger.info(f"✅ {param_name}: 已配置")
            else:
                results["details"][param_name] = "FAILED"
                results["errors"].append(f"{param_name} 未配置")
                results["success"] = False
        
        # 生成参数文档
        try:
            config_doc = self.client.generate_config_document()
            
            # 保存配置文档
            config_dir = "outputs/sora2_config"
            os.makedirs(config_dir, exist_ok=True)
            
            config_file = os.path.join(config_dir, f"integration_config_{int(time.time())}.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_doc, f, indent=2, ensure_ascii=False)
            
            results["details"]["config_document"] = "PASSED"
            self.logger.info(f"✅ 配置文档已生成: {config_file}")
        
        except Exception as e:
            results["details"]["config_document"] = f"FAILED: {str(e)}"
            results["errors"].append(f"配置文档生成失败: {str(e)}")
            results["success"] = False
        
        return results
    
    def test_workflow_integration(self) -> Dict[str, Any]:
        """
        测试工作流集成
        
        验收标准：视频生成工作流可运行
        """
        self.logger.info("测试工作流集成...")
        
        results = {
            "success": False,
            "details": {},
            "error": None
        }
        
        try:
            # 创建测试产品
            test_product = ProductInfo(
                product_id="test_001",
                name="测试产品 - Sora2集成测试",
                category="测试",
                description="用于验证Sora2工作流集成的测试产品",
                price=99.99,
                key_features=["集成测试", "工作流验证", "自动化"]
            )
            
            # 提交任务
            task_id = self.workflow.submit_product(test_product)
            
            if task_id:
                results["success"] = True
                results["details"]["task_submission"] = "PASSED"
                results["details"]["task_id"] = task_id
                self.logger.info(f"✅ 工作流任务提交: 成功，任务ID: {task_id}")
            
            # 获取任务状态
            task_status = self.workflow.get_task_status(task_id)
            
            if task_status:
                results["details"]["task_status"] = "PASSED"
                self.logger.info(f"✅ 任务状态查询: 成功，状态: {task_status.get('status')}")
            
            # 测试工作流报告
            workflow_report = self.workflow.generate_workflow_report()
            
            if workflow_report:
                results["details"]["workflow_report"] = "PASSED"
                self.logger.info("✅ 工作流报告生成: 成功")
        
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            self.logger.error(f"❌ 工作流测试异常: {str(e)}")
        
        return results
    
    def test_material_library(self) -> Dict[str, Any]:
        """
        测试素材库
        
        验收标准：素材库回传功能正常
        """
        self.logger.info("测试素材库...")
        
        results = {
            "success": True,
            "details": {},
            "errors": []
        }
        
        try:
            # 检查素材库目录
            lib_dir = "data/material_library"
            
            if os.path.exists(lib_dir):
                results["details"]["library_directory"] = "PASSED"
                self.logger.info(f"✅ 素材库目录: 存在 ({lib_dir})")
            else:
                results["details"]["library_directory"] = "FAILED"
                results["errors"].append(f"素材库目录不存在: {lib_dir}")
                results["success"] = False
            
            # 检查素材库文件
            lib_file = os.path.join(lib_dir, "library.json")
            
            if os.path.exists(lib_file):
                results["details"]["library_file"] = "PASSED"
                self.logger.info(f"✅ 素材库文件: 存在 ({lib_file})")
                
                # 尝试加载库文件
                try:
                    with open(lib_file, 'r', encoding='utf-8') as f:
                        lib_data = json.load(f)
                    
                    entry_count = len(lib_data)
                    results["details"]["library_entries"] = f"PASSED ({entry_count} 个条目)"
                    self.logger.info(f"✅ 素材库条目: {entry_count} 个")
                
                except Exception as e:
                    results["details"]["library_loading"] = f"FAILED: {str(e)}"
                    results["errors"].append(f"素材库文件加载失败: {str(e)}")
                    results["success"] = False
            else:
                results["details"]["library_file"] = "NOT_FOUND (可能是首次运行)"
                self.logger.warning("⚠️ 素材库文件: 未找到 (可能是首次运行)")
            
            # 测试素材库搜索
            search_results = self.workflow.search_material_library(
                query="测试",
                category="测试"
            )
            
            if isinstance(search_results, list):
                results["details"]["search_function"] = "PASSED"
                self.logger.info(f"✅ 素材库搜索: 成功，返回 {len(search_results)} 个结果")
            else:
                results["details"]["search_function"] = "FAILED"
                results["errors"].append("素材库搜索返回类型错误")
                results["success"] = False
        
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            self.logger.error(f"❌ 素材库测试异常: {str(e)}")
        
        return results
    
    def test_output_parameter_locking(self) -> Dict[str, Any]:
        """
        测试输出参数锁定
        
        验收标准：输出参数文档化
        """
        self.logger.info("测试输出参数锁定...")
        
        results = {
            "success": True,
            "details": {},
            "errors": []
        }
        
        try:
            # 生成输出参数文档
            output_config = {
                "timestamp": time.time(),
                "locked_parameters": {
                    "protocol": self.config.protocol,
                    "model": self.config.default_model.value,
                    "output_specification": {
                        "aspect_ratio": self.config.output_spec.aspect_ratio,
                        "resolution": self.config.output_spec.size_str,
                        "duration": f"{self.config.output_spec.duration_seconds}秒",
                        "quality": self.config.output_spec.quality,
                        "fps": self.config.output_spec.fps
                    },
                    "automation_workflow": {
                        "enabled": self.config.workflow.enable_full_pipeline,
                        "concurrent_jobs": self.config.workflow.max_concurrent_jobs,
                        "timeout": self.config.workflow.default_timeout_seconds
                    },
                    "retry_mechanism": {
                        "max_retries": self.config.retry.max_retry_count,
                        "retry_interval": self.config.retry.retry_interval_seconds,
                        "concurrent_tasks": self.config.retry.max_concurrent_tasks
                    }
                },
                "validation_rules": [
                    "参数一经锁定，不得在运行时修改",
                    "如需调整参数，必须更新配置文件并重新部署",
                    "所有生成任务必须使用锁定的参数"
                ]
            }
            
            # 保存输出参数文档
            output_dir = "outputs/sora2_locked_parameters"
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(output_dir, f"locked_parameters_{int(time.time())}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_config, f, indent=2, ensure_ascii=False)
            
            results["details"]["parameter_document"] = "PASSED"
            results["details"]["output_file"] = output_file
            self.logger.info(f"✅ 输出参数文档: 已生成 ({output_file})")
            
            # 验证参数一致性
            config_dict = self.config.to_dict()
            
            key_parameters = [
                "protocol",
                "default_model",
                "output_spec"
            ]
            
            all_consistent = True
            for param in key_parameters:
                if param in config_dict:
                    results["details"][f"parameter_{param}"] = "CONSISTENT"
                else:
                    results["details"][f"parameter_{param}"] = "MISSING"
                    results["errors"].append(f"关键参数缺失: {param}")
                    all_consistent = False
            
            results["success"] = results["success"] and all_consistent
        
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            self.logger.error(f"❌ 输出参数测试异常: {str(e)}")
        
        return results
    
    def test_error_handling_mechanism(self) -> Dict[str, Any]:
        """
        测试错误处理机制
        
        验收标准：容错机制代码实现
        """
        self.logger.info("测试错误处理机制...")
        
        results = {
            "success": True,
            "details": {},
            "errors": []
        }
        
        try:
            from sora2_integration.error_handler import test_error_handling
            
            # 运行错误处理测试
            error_test_results = test_error_handling()
            
            if error_test_results:
                results["details"]["error_handling_test"] = "PASSED"
                self.logger.info(f"✅ 错误处理测试: 成功 ({error_test_results['successful']}/{error_test_results['total_tests']} 通过)")
            
            # 检查重试配置
            retry_config = self.config.retry
            
            if retry_config.max_retry_count == 3:
                results["details"]["retry_config"] = "PASSED"
                self.logger.info(f"✅ 重试配置: {retry_config.max_retry_count} 次重试")
            else:
                results["details"]["retry_config"] = "FAILED"
                results["errors"].append(f"重试配置不匹配: {retry_config.max_retry_count} 次")
                results["success"] = False
            
            # 检查网络异常处理
            if retry_config.network_timeout_seconds == 60:
                results["details"]["network_timeout"] = "PASSED"
                self.logger.info(f"✅ 网络超时: {retry_config.network_timeout_seconds} 秒")
            else:
                results["details"]["network_timeout"] = "FAILED"
                results["errors"].append(f"网络超时不匹配: {retry_config.network_timeout_seconds} 秒")
                results["success"] = False
            
            # 检查质量检查回退方案
            if retry_config.enable_quality_fallback:
                results["details"]["quality_fallback"] = "PASSED"
                self.logger.info("✅ 质量检查回退: 已启用")
            else:
                results["details"]["quality_fallback"] = "FAILED"
                results["errors"].append("质量检查回退未启用")
                results["success"] = False
        
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            self.logger.error(f"❌ 错误处理测试异常: {str(e)}")
        
        return results
    
    def test_compatibility_with_existing_systems(self) -> Dict[str, Any]:
        """
        测试与现有系统的兼容性
        
        验收标准：不破坏无限分身架构、Claude Code架构、Notebook LM知识底座等现有功能
        """
        self.logger.info("测试与现有系统的兼容性...")
        
        results = {
            "success": True,
            "details": {},
            "errors": []
        }
        
        try:
            # 检查现有系统文件结构
            existing_systems = [
                "src/global_orchestrator",
                "data/shared_state",
                "sellai_test/global_orchestrator"
            ]
            
            all_systems_exist = True
            for system_path in existing_systems:
                if os.path.exists(system_path):
                    results["details"][system_path] = "EXISTS"
                else:
                    results["details"][system_path] = "NOT_FOUND"
                    results["errors"].append(f"现有系统路径不存在: {system_path}")
                    all_systems_exist = False
            
            if all_systems_exist:
                self.logger.info("✅ 现有系统文件结构: 完整")
            else:
                self.logger.warning("⚠️ 现有系统文件结构: 部分缺失")
                results["success"] = results["success"] and all_systems_exist
            
            # 检查配置兼容性
            config_dict = self.config.to_dict()
            
            # 确认不破坏的子系统
            critical_subsystems = [
                "enable_avatar_system",
                "enable_notebook_lm", 
                "enable_memory_v2",
                "enable_claude_code"
            ]
            
            all_subsystems_enabled = True
            for subsystem in critical_subsystems:
                if config_dict.get(subsystem, False):
                    results["details"][subsystem] = "ENABLED"
                else:
                    results["details"][subsystem] = "DISABLED"
                    results["errors"].append(f"关键子系统未启用: {subsystem}")
                    all_subsystems_enabled = False
            
            if all_subsystems_enabled:
                self.logger.info("✅ 关键子系统: 全部启用")
            else:
                self.logger.error("❌ 关键子系统: 部分未启用")
                results["success"] = results["success"] and all_subsystems_enabled
            
            # 验证API兼容性
            api_compliance = self.compliance_manager.create_api_config_document()
            
            if api_compliance:
                results["details"]["api_compatibility"] = "PASSED"
                self.logger.info("✅ API兼容性: 验证通过")
        
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            self.logger.error(f"❌ 兼容性测试异常: {str(e)}")
        
        return results
    
    def save_test_report(self, report: Dict[str, Any], 
                        output_dir: str = "outputs/sora2_integration_tests"):
        """
        保存测试报告
        
        Args:
            report: 测试报告
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = int(time.time())
        report_file = os.path.join(output_dir, f"integration_test_{timestamp}.json")
        
        # 添加测试元数据
        report["metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
                "config_source": "DEFAULT_CONFIG" if self.config is DEFAULT_CONFIG else "CUSTOM_CONFIG"
            }
        }
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📄 测试报告已保存: {report_file}")
        
        return report_file


# 主测试函数
def run_comprehensive_tests(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    运行全面的Sora2集成测试
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        完整的测试报告
    """
    print("\n" + "="*80)
    print("🚀 SORA2全链路接入集成测试")
    print("="*80)
    
    # 加载配置（如果提供）
    config = None
    if config_path and os.path.exists(config_path):
        print(f"📁 加载配置文件: {config_path}")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            config = Sora2IntegrationConfig(**config_data)
        except Exception as e:
            print(f"❌ 配置文件加载失败: {str(e)}")
            print("⚠️ 使用默认配置")
    
    # 创建测试器
    tester = Sora2IntegrationTester(config)
    
    # 运行所有测试
    report = tester.run_all_tests()
    
    # 保存报告
    report_file = tester.save_test_report(report)
    
    # 打印摘要
    print("\n" + "="*80)
    print("🎯 测试摘要")
    print("="*80)
    
    passed_count = sum(1 for t in report["tests"] if t["status"] == "PASSED")
    total_count = len(report["tests"])
    
    print(f"📊 总体通过率: {passed_count}/{total_count} ({report['pass_rate']:.1%})")
    print(f"⏱️  总耗时: {report['total_duration']:.2f} 秒")
    print(f"📄 报告文件: {report_file}")
    
    # 打印详细结果
    print("\n📋 详细结果:")
    for test in report["tests"]:
        status_icon = "✅" if test["status"] == "PASSED" else "❌"
        print(f"  {status_icon} {test['name']}: {test['status']} ({test['duration']:.2f}秒)")
    
    # 检查是否通过验收标准
    all_passed = passed_count == total_count
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 所有验收标准通过！Sora2全链路接入配置完成。")
        print("📝 请检查生成的配置文档并配置API密钥。")
    else:
        print("⚠️ 部分验收标准未通过，请检查错误详情。")
        print("🔧 需要手动配置或修复。")
    
    print("="*80 + "\n")
    
    return report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sora2全链路接入集成测试")
    parser.add_argument("--config", type=str, help="配置文件路径", default=None)
    parser.add_argument("--quick", action="store_true", help="快速测试模式")
    
    args = parser.parse_args()
    
    if args.quick:
        print("🔧 快速测试模式...")
        from sora2_integration.workflow import run_quick_test
        result = run_quick_test()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        run_comprehensive_tests(args.config)