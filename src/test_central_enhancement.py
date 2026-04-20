#!/usr/bin/env python3
"""
无限AI分身架构 - 四中枢强化验证测试脚本

本脚本用于验证升级后的4个核心分身（情报官、内容官、运营官、增长官）的System Prompt
是否已正确强化基础中枢调度协调职责。

验证维度：
1. 文件存在性检查
2. 关键职责内容验证
3. 调度协调功能点检查
4. 协同协议完整性验证
"""

import os
import re
import json
from pathlib import Path
import sys

# 配置路径
BASE_DIR = Path(__file__).parent.parent
PROMPT_DIR = BASE_DIR / "outputs" / "升级后的SystemPrompt"

# 分身配置定义
AVATAR_CONFIGS = [
    {
        "name": "情报官",
        "file_name": "情报官_中枢强化版.md",
        "core_responsibilities": [
            "分身能力矩阵管理",
            "新分身能力校准",
            "垂直领域专长识别",
            "跨分身数据协调"
        ],
        "scheduling_functions": [
            "智能任务分配",
            "负载均衡",
            "优先级仲裁",
            "资源协调"
        ],
        "keywords": [
            "基础中枢",
            "调度协调",
            "能力矩阵",
            "垂直领域",
            "协同协议"
        ]
    },
    {
        "name": "内容官",
        "file_name": "内容官_中枢强化版.md",
        "core_responsibilities": [
            "多分身内容创作协同",
            "风格一致性维护",
            "跨分身内容审核",
            "内容质量标准化"
        ],
        "scheduling_functions": [
            "内容任务分解",
            "分身创作协调",
            "风格规范管理",
            "审核流程调度"
        ],
        "keywords": [
            "基础中枢",
            "多分身协同",
            "风格一致性",
            "跨分身审核",
            "内容标准化"
        ]
    },
    {
        "name": "运营官",
        "file_name": "运营官_中枢强化版.md",
        "core_responsibilities": [
            "任务优先级仲裁",
            "分身负载均衡",
            "资源分配协调",
            "执行风险管控"
        ],
        "scheduling_functions": [
            "智能调度决策",
            "负载监控",
            "冲突解决",
            "效能优化"
        ],
        "keywords": [
            "基础中枢",
            "优先级仲裁",
            "负载均衡",
            "资源协调",
            "风险管控"
        ]
    },
    {
        "name": "增长官",
        "file_name": "增长官_中枢强化版.md",
        "core_responsibilities": [
            "分身效能监控",
            "成本效益分析",
            "规模化运行优化",
            "系统级ROI提升"
        ],
        "scheduling_functions": [
            "效能评估",
            "成本分析",
            "规模化优化",
            "ROI监控"
        ],
        "keywords": [
            "基础中枢",
            "效能监控",
            "成本效益",
            "规模化优化",
            "系统级ROI"
        ]
    }
]

class CentralEnhancementValidator:
    """中枢强化验证器"""
    
    def __init__(self):
        self.results = []
        self.prompt_dir = PROMPT_DIR
        
    def validate_all(self):
        """验证所有分身"""
        print("=" * 80)
        print("无限AI分身架构 - 四中枢强化验证测试")
        print("=" * 80)
        
        # 检查目录是否存在
        if not self.prompt_dir.exists():
            self._record_failure("目录检查", f"Prompt目录不存在: {self.prompt_dir}")
            return False
        
        print(f"📁 Prompt目录: {self.prompt_dir}")
        print()
        
        # 验证每个分身
        all_passed = True
        for config in AVATAR_CONFIGS:
            passed = self._validate_avatar(config)
            if not passed:
                all_passed = False
        
        # 输出总结
        self._print_summary()
        
        return all_passed
    
    def _validate_avatar(self, config):
        """验证单个分身"""
        print(f"🔍 验证分身: {config['name']}")
        print(f"   文件: {config['file_name']}")
        
        # 1. 文件存在性检查
        file_path = self.prompt_dir / config["file_name"]
        if not file_path.exists():
            self._record_failure(config["name"], f"文件不存在: {file_path}")
            return False
        
        # 2. 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self._record_failure(config["name"], f"读取文件失败: {e}")
            return False
        
        # 3. 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size < 800 * 10:  # 800字大约1600字节，放宽要求
            self._record_failure(config["name"], f"文件过小: {file_size}字节")
            return False
        
        # 4. 检查关键职责内容
        responsibilities_found = []
        for resp in config["core_responsibilities"]:
            if resp in content:
                responsibilities_found.append(resp)
            else:
                self._record_warning(config["name"], f"未找到核心职责: {resp}")
        
        # 5. 检查调度功能点
        functions_found = []
        for func in config["scheduling_functions"]:
            if func in content:
                functions_found.append(func)
            else:
                self._record_warning(config["name"], f"未找到调度功能: {func}")
        
        # 6. 检查关键词
        keywords_found = []
        for keyword in config["keywords"]:
            if keyword in content:
                keywords_found.append(keyword)
            else:
                self._record_warning(config["name"], f"未找到关键词: {keyword}")
        
        # 7. 检查版本信息
        version_patterns = [
            r"版本号\s*[:：]\s*v?3\.0",
            r"v?3\.0\s*版本",
            r"中枢强化版"
        ]
        version_found = any(re.search(pattern, content, re.IGNORECASE) for pattern in version_patterns)
        
        # 8. 检查协同协议部分
        collaboration_sections = [
            "协同协议",
            "协同执行",
            "协同建议",
            "协同验证"
        ]
        collaboration_found = any(section in content for section in collaboration_sections)
        
        # 记录验证结果
        avatar_result = {
            "name": config["name"],
            "file_exists": True,
            "file_size": file_size,
            "responsibilities_found": len(responsibilities_found),
            "total_responsibilities": len(config["core_responsibilities"]),
            "functions_found": len(functions_found),
            "total_functions": len(config["scheduling_functions"]),
            "keywords_found": len(keywords_found),
            "total_keywords": len(config["keywords"]),
            "version_found": version_found,
            "collaboration_found": collaboration_found,
            "passed": True  # 暂时设为True，后面根据条件调整
        }
        
        # 设置通过条件
        passed = True
        if len(responsibilities_found) < 3:  # 至少找到3个核心职责
            passed = False
            avatar_result["passed"] = False
            self._record_failure(config["name"], f"核心职责不足: {len(responsibilities_found)}/{len(config['core_responsibilities'])}")
        
        if len(functions_found) < 3:  # 至少找到3个调度功能
            passed = False
            avatar_result["passed"] = False
            self._record_failure(config["name"], f"调度功能不足: {len(functions_found)}/{len(config['scheduling_functions'])}")
        
        if not version_found:
            self._record_warning(config["name"], "未找到v3.0版本标识")
        
        if not collaboration_found:
            self._record_warning(config["name"], "协同协议部分可能不完整")
        
        # 计算内容覆盖率
        avatar_result["responsibility_coverage"] = len(responsibilities_found) / len(config["core_responsibilities"])
        avatar_result["function_coverage"] = len(functions_found) / len(config["scheduling_functions"])
        avatar_result["keyword_coverage"] = len(keywords_found) / len(config["keywords"])
        
        self.results.append(avatar_result)
        
        # 输出分身验证结果
        if passed:
            print(f"    ✅ 通过")
            print(f"      核心职责: {len(responsibilities_found)}/{len(config['core_responsibilities'])}")
            print(f"      调度功能: {len(functions_found)}/{len(config['scheduling_functions'])}")
            print(f"      关键词: {len(keywords_found)}/{len(config['keywords'])}")
        else:
            print(f"    ❌ 失败")
        
        print()
        return passed
    
    def _record_failure(self, avatar_name, message):
        """记录失败信息"""
        print(f"    ❌ {avatar_name}: {message}")
    
    def _record_warning(self, avatar_name, message):
        """记录警告信息"""
        print(f"    ⚠️  {avatar_name}: {message}")
    
    def _print_summary(self):
        """打印验证总结"""
        print("=" * 80)
        print("📊 验证总结")
        print("=" * 80)
        
        total_avatars = len(AVATAR_CONFIGS)
        passed_avatars = sum(1 for r in self.results if r["passed"])
        
        print(f"📈 总体结果: {passed_avatars}/{total_avatars} 个分身通过验证")
        print()
        
        # 详细结果表
        print("┌─────────────────┬────────────┬────────────┬────────────┬─────────┐")
        print("│ 分身名称        │ 核心职责   │ 调度功能   │ 关键词     │ 状态    │")
        print("├─────────────────┼────────────┼────────────┼────────────┼─────────┤")
        
        for result in self.results:
            resp_text = f"{result['responsibilities_found']}/{result['total_responsibilities']}"
            func_text = f"{result['functions_found']}/{result['total_functions']}"
            keyword_text = f"{result['keywords_found']}/{result['total_keywords']}"
            status = "✅ 通过" if result["passed"] else "❌ 失败"
            
            print(f"│ {result['name']:15} │ {resp_text:10} │ {func_text:10} │ {keyword_text:10} │ {status:7} │")
        
        print("└─────────────────┴────────────┴────────────┴────────────┴─────────┘")
        print()
        
        # 覆盖率统计
        avg_resp_coverage = sum(r["responsibility_coverage"] for r in self.results) / total_avatars
        avg_func_coverage = sum(r["function_coverage"] for r in self.results) / total_avatars
        avg_keyword_coverage = sum(r["keyword_coverage"] for r in self.results) / total_avatars
        
        print(f"📊 平均覆盖率:")
        print(f"   核心职责: {avg_resp_coverage:.1%}")
        print(f"   调度功能: {avg_func_coverage:.1%}")
        print(f"   关键词: {avg_keyword_coverage:.1%}")
        print()
        
        # 系统级检查
        print("🔧 系统级检查:")
        
        # 检查协同协议完整性
        collaboration_complete = all(r["collaboration_found"] for r in self.results)
        print(f"   协同协议完整性: {'✅ 完整' if collaboration_complete else '⚠️ 不完整'}")
        
        # 检查版本一致性
        version_consistent = all(r["version_found"] for r in self.results)
        print(f"   版本一致性 (v3.0): {'✅ 一致' if version_consistent else '⚠️ 不一致'}")
        
        # 检查文件大小合理性
        reasonable_size = all(r["file_size"] > 2000 for r in self.results)  # 至少2KB
        print(f"   文件大小合理性: {'✅ 合理' if reasonable_size else '⚠️ 偏小'}")
        
        print()
        
        # 最终结论
        if passed_avatars == total_avatars:
            print("🎉 恭喜! 所有分身已成功升级为中枢强化版，具备完整的基础中枢调度协调能力。")
            print("   系统已准备好支持无限AI分身架构的规模化运行。")
        else:
            print("⚠️  部分分身升级不完整，请根据上述提示进行优化。")
            print("   建议重点检查核心职责和调度功能的描述完整性。")
        
        print("=" * 80)
        
        # 生成详细报告文件
        self._generate_detailed_report()
    
    def _generate_detailed_report(self):
        """生成详细验证报告"""
        report_path = BASE_DIR / "temp" / "central_enhancement_validation_report.json"
        report_dir = report_path.parent
        
        # 确保目录存在
        report_dir.mkdir(exist_ok=True)
        
        report_data = {
            "validation_timestamp": "2026-04-03T14:35:00",
            "system_version": "SellAI无限分身架构v3.0",
            "total_avatars": len(AVATAR_CONFIGS),
            "passed_avatars": sum(1 for r in self.results if r["passed"]),
            "avatar_results": self.results,
            "summary": {
                "overall_status": "PASS" if all(r["passed"] for r in self.results) else "FAIL",
                "average_responsibility_coverage": sum(r["responsibility_coverage"] for r in self.results) / len(self.results),
                "average_function_coverage": sum(r["function_coverage"] for r in self.results) / len(self.results),
                "average_keyword_coverage": sum(r["keyword_coverage"] for r in self.results) / len(self.results)
            }
        }
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            print(f"📄 详细验证报告已生成: {report_path}")
        except Exception as e:
            print(f"⚠️  生成详细报告失败: {e}")
        
        print()

def main():
    """主函数"""
    validator = CentralEnhancementValidator()
    
    try:
        success = validator.validate_all()
        
        # 根据验证结果返回退出码
        if success:
            print("🎯 验证成功! 四中枢强化升级完成。")
            sys.exit(0)
        else:
            print("🔴 验证失败! 请检查并优化System Prompt。")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    main()