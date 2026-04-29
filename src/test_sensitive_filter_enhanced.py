#!/usr/bin/env python3
"""
增强版敏感信息过滤测试
测试扩展后的敏感信息过滤功能，验证100%过滤准确率
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from undercover_auditor import UndercoverAuditor, SecurityLevel
import json

def test_sensitive_info_filtering():
    """测试敏感信息过滤功能"""
    print("=" * 80)
    print("增强版敏感信息过滤测试")
    print("=" * 80)
    
    auditor = UndercoverAuditor()
    auditor.start_audit_service()
    
    # 测试数据集 - 包含各种敏感信息
    test_cases = [
        # (输入文本, 期望过滤后的关键词, 测试说明)
        ("API密钥是 sk_live_1234567890abcdef", ["[FILTERED]"], "API密钥过滤"),
        ("密码: mypassword123", ["******"], "密码过滤"),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", 
         ["[FILTERED]", "[JWT_TOKEN_FILTERED]"], "Bearer令牌和JWT过滤"),
        ("access_token: abcdef123456", ["[FILTERED]"], "访问令牌过滤"),
        ("数据库连接: mysql://root:password@localhost:3306/mydb", 
         ["[FILTERED]", "[DB_CONNECTION_FILTERED]"], "数据库连接字符串过滤"),
        ("SSH私钥: -----BEGIN RSA PRIVATE KEY-----", ["[FILTERED]"], "SSH密钥过滤"),
        ("信用卡号: 4111111111111111", ["[CREDIT_CARD_FILTERED]"], "信用卡号过滤"),
        ("AWS访问密钥: AKIAIOSFODNN7EXAMPLE", ["[AWS_KEY_FILTERED]"], "AWS访问密钥过滤"),
        ("AWS秘密密钥: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", ["[AWS_KEY_FILTERED]"], "AWS秘密密钥过滤"),
        ("Google API密钥: AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw", ["[GOOGLE_API_KEY_FILTERED]"], "Google API密钥过滤"),
        ("加密私钥: -----BEGIN ENCRYPTED PRIVATE KEY-----", ["[PRIVATE_KEY_FILTERED]"], "加密私钥过滤"),
        ("身份证号: 110101199003078888", ["[PII_FILTERED]"], "身份证号过滤"),
        ("手机号: 13800138000", ["[PII_FILTERED]"], "手机号过滤"),
        ("邮箱: user@example.com", ["[PII_FILTERED]"], "邮箱过滤"),
        ("会话Cookie: session_id=abc123def456ghi789jkl012mno345pqr678stu901", ["[FILTERED]"], "会话Cookie过滤"),
        ("环境变量: DB_PASSWORD=secret123", ["[FILTERED]"], "环境变量过滤"),
        ("Slack令牌: xoxb-123456789012-1234567890123-abcdefghijklmnopqrstuvwx", ["[FILTERED]"], "Slack令牌过滤"),
        ("GitHub令牌: ghp_abcdefghijklmnopqrstuvwxyz0123456789", ["[FILTERED]"], "GitHub令牌过滤"),
        ("Stripe密钥: sk_live_abcdefghijklmnopqrstuvwx", ["[FILTERED]"], "Stripe密钥过滤"),
        ("通用令牌: abcdefghijklmnopqrstuvwxyz0123456789", ["[GENERIC_TOKEN_FILTERED]"], "通用令牌过滤"),
    ]
    
    results = []
    total_cases = len(test_cases)
    passed_cases = 0
    
    print(f"\n开始测试 {total_cases} 个敏感信息过滤场景...")
    print("-" * 80)
    
    for i, (input_text, expected_keywords, description) in enumerate(test_cases, 1):
        # 过滤输出
        filtered_output, audit_info = auditor.filter_output(
            component_id="测试组件",
            output_data=input_text,
            security_level=SecurityLevel.RESTRICTED
        )
        
        # 检查是否包含期望的过滤标记
        passed = all(keyword in filtered_output for keyword in expected_keywords)
        
        # 同时检查原始敏感信息是否被移除
        sensitive_present = any(
            keyword.lower() in filtered_output.lower() 
            for keyword in ["sk_live", "mypassword123", "eyJ", "abcdef123456", 
                          "password@localhost", "RSA PRIVATE KEY", "4111111111111111",
                          "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI", "AIzaSyBOti4mM",
                          "ENCRYPTED PRIVATE KEY", "110101199003078888", "13800138000",
                          "user@example.com", "session_id=abc123", "DB_PASSWORD=secret123",
                          "xoxb-123456789012", "ghp_abcdefghijklmnop", "sk_live_abcdefghijklmnop",
                          "abcdefghijklmnopqrstuvwxyz0123456789"]
        )
        
        if sensitive_present:
            passed = False
            
        status = "通过" if passed else "失败"
        if passed:
            passed_cases += 1
            
        result = {
            "序号": i,
            "测试场景": description,
            "输入文本": input_text[:50] + "..." if len(input_text) > 50 else input_text,
            "过滤后输出": filtered_output[:80] + "..." if len(filtered_output) > 80 else filtered_output,
            "期望关键词": expected_keywords,
            "状态": status,
            "过滤详情": audit_info.get("filtered_parts", [])
        }
        results.append(result)
        
        print(f"测试 {i:2d}/{total_cases}: {description:20s} - {status}")
        if not passed:
            print(f"    输入: {input_text}")
            print(f"    输出: {filtered_output}")
            print(f"    期望: {expected_keywords}")
    
    print("-" * 80)
    success_rate = (passed_cases / total_cases) * 100
    print(f"测试完成: {passed_cases}/{total_cases} 通过，成功率: {success_rate:.2f}%")
    
    # 生成详细报告
    report = {
        "测试名称": "增强版敏感信息过滤测试",
        "测试时间": "2026-04-04 11:30:00",
        "测试环境": "SellAI封神版A - Undercover安全审计系统",
        "测试结果": {
            "总测试场景": total_cases,
            "通过场景": passed_cases,
            "失败场景": total_cases - passed_cases,
            "成功率": f"{success_rate:.2f}%"
        },
        "详细测试结果": results,
        "结论": f"敏感信息过滤准确率达到{success_rate:.2f}%，{'满足100%过滤准确率要求' if success_rate == 100 else '未达到100%过滤准确率要求，需进一步优化'}"
    }
    
    # 保存报告到文件
    report_file = "outputs/安全审计系统/敏感信息过滤测试报告.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细测试报告已保存至: {report_file}")
    
    # 停止审计服务
    auditor.stop_audit_service()
    
    return success_rate == 100

def test_internal_term_protection():
    """测试内部术语保护功能"""
    print("\n" + "=" * 80)
    print("内部术语保护功能测试")
    print("=" * 80)
    
    auditor = UndercoverAuditor()
    auditor.start_audit_service()
    
    # 测试内部术语过滤
    test_cases = [
        ("这是KAIROS守护系统", ["[INTERNAL_TERM]"], "KAIROS术语过滤"),
        ("使用Memory V2记忆系统", ["[INTERNAL_TERM]"], "Memory V2术语过滤"),
        ("全域商业大脑分析", ["[INTERNAL_TERM]"], "商业大脑术语过滤"),
        ("情报官处理数据", ["[INTERNAL_TERM]"], "四中枢术语过滤"),
        ("流量爆破军团执行任务", ["[INTERNAL_TERM]"], "引流军团术语过滤"),
        ("共享状态数据库state.db", ["[INTERNAL_TERM]"], "内部表名过滤"),
        ("审计事件表audit_events", ["[INTERNAL_TERM]"], "审计表名过滤"),
        ("安全警报表security_alerts", ["[INTERNAL_TERM]"], "安全表名过滤"),
    ]
    
    results = []
    total_cases = len(test_cases)
    passed_cases = 0
    
    print(f"开始测试 {total_cases} 个内部术语过滤场景...")
    print("-" * 80)
    
    for i, (input_text, expected_keywords, description) in enumerate(test_cases, 1):
        # 过滤输出（使用RESTRICTED级别过滤内部术语）
        filtered_output, audit_info = auditor.filter_output(
            component_id="测试组件",
            output_data=input_text,
            security_level=SecurityLevel.RESTRICTED
        )
        
        # 检查是否包含期望的过滤标记
        passed = all(keyword in filtered_output for keyword in expected_keywords)
        
        # 同时检查原始内部术语是否被移除
        term_present = any(
            term.lower() in filtered_output.lower() 
            for term in ["KAIROS", "Memory V2", "全域商业大脑", "情报官", 
                        "流量爆破军团", "state.db", "audit_events", "security_alerts"]
        )
        
        if term_present:
            passed = False
            
        status = "通过" if passed else "失败"
        if passed:
            passed_cases += 1
            
        result = {
            "序号": i,
            "测试场景": description,
            "输入文本": input_text,
            "过滤后输出": filtered_output[:80] + "..." if len(filtered_output) > 80 else filtered_output,
            "期望关键词": expected_keywords,
            "状态": status
        }
        results.append(result)
        
        print(f"测试 {i:2d}/{total_cases}: {description:20s} - {status}")
    
    print("-" * 80)
    success_rate = (passed_cases / total_cases) * 100
    print(f"测试完成: {passed_cases}/{total_cases} 通过，成功率: {success_rate:.2f}%")
    
    # 生成详细报告
    report = {
        "测试名称": "内部术语保护功能测试",
        "测试时间": "2026-04-04 11:30:00",
        "测试环境": "SellAI封神版A - Undercover安全审计系统",
        "测试结果": {
            "总测试场景": total_cases,
            "通过场景": passed_cases,
            "失败场景": total_cases - passed_cases,
            "成功率": f"{success_rate:.2f}%"
        },
        "详细测试结果": results,
        "结论": f"内部术语保护准确率达到{success_rate:.2f}%，{'满足100%保护要求' if success_rate == 100 else '未达到100%保护要求，需进一步优化'}"
    }
    
    # 保存报告到文件
    report_file = "outputs/安全审计系统/内部术语保护测试报告.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细测试报告已保存至: {report_file}")
    
    # 停止审计服务
    auditor.stop_audit_service()
    
    return success_rate == 100

def main():
    """主测试函数"""
    print("SellAI封神版A - Undercover安全审计系统增强版测试")
    print("测试时间: 2026-04-04 11:30:00")
    print()
    
    # 测试敏感信息过滤
    sensitive_passed = test_sensitive_info_filtering()
    
    # 测试内部术语保护
    internal_term_passed = test_internal_term_protection()
    
    # 总体结论
    print("\n" + "=" * 80)
    print("总体测试结论")
    print("=" * 80)
    
    if sensitive_passed and internal_term_passed:
        print("✅ 所有测试通过！")
        print("✅ 敏感信息过滤准确率: 100%")
        print("✅ 内部术语保护准确率: 100%")
        print("✅ 满足Claude Code AI架构升级标准")
    else:
        print("❌ 部分测试未通过:")
        if not sensitive_passed:
            print("   - 敏感信息过滤未达到100%准确率")
        if not internal_term_passed:
            print("   - 内部术语保护未达到100%准确率")
        print("❌ 需进一步优化以满足Claude Code AI架构升级标准")
    
    return sensitive_passed and internal_term_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)