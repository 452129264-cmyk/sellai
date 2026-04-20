#!/usr/bin/env python3
"""
快速安全功能测试
验证增强后的敏感信息过滤和内部术语保护功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from undercover_auditor import UndercoverAuditor, SecurityLevel
import re

def test_single_pattern(pattern_name: str, pattern_str: str, test_cases: list):
    """测试单个正则表达式模式"""
    print(f"\n测试模式: {pattern_name}")
    print("-" * 40)
    
    pattern = re.compile(pattern_str, re.IGNORECASE)
    
    for i, (input_text, should_match) in enumerate(test_cases, 1):
        matches = pattern.findall(input_text)
        matched = len(matches) > 0
        status = "✅ 正确" if matched == should_match else "❌ 错误"
        
        print(f"测试 {i}: {status}")
        print(f"  输入: {input_text}")
        print(f"  匹配: {matched} (期望: {should_match})")
        if matches:
            print(f"  匹配结果: {matches}")

def main():
    """主测试函数"""
    print("快速安全功能测试")
    print("=" * 80)
    
    # 测试API密钥模式
    test_single_pattern("API密钥", r'(api[_-]?key|apikey|access[_-]?key)[\s=:]+[\'\"]([a-zA-Z0-9_-]{15,})[\'\"]', [
        ("api_key: sk_live_1234567890abcdef", True),
        ("apikey='abcdefghijklmnopqrst'", True),
        ("access_key: short", False),  # 太短
        ("API密钥: 'test123'", False),  # 太短
    ])
    
    # 测试密码模式
    test_single_pattern("密码", r'(password|passwd|pwd|pass|secret)[\s=:]+[\'\"]([^\s\'\"]+)[\'\"]', [
        ("password: mypass123", True),
        ("pass='secret'", True),
        ("pwd: test", True),
        ("something else", False),
    ])
    
    # 创建审计器实例
    print("\n" + "=" * 80)
    print("完整审计功能测试")
    print("=" * 80)
    
    auditor = UndercoverAuditor()
    auditor.start_audit_service()
    
    # 测试敏感信息过滤
    test_cases = [
        ("API密钥: sk_live_abcdef1234567890", ["[FILTERED]"]),
        ("密码: mypassword123", ["******"]),
        ("access_token: abcdef123456", ["[FILTERED]"]),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", ["[FILTERED]"]),
        ("AWS密钥: AKIAIOSFODNN7EXAMPLE", ["[AWS_KEY_FILTERED]"]),
        ("Google API密钥: AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw", ["[GOOGLE_API_KEY_FILTERED]"]),
    ]
    
    print("\n敏感信息过滤测试:")
    for input_text, expected_keywords in test_cases:
        filtered_output, audit_info = auditor.filter_output(
            component_id="快速测试",
            output_data=input_text,
            security_level=SecurityLevel.RESTRICTED
        )
        
        passed = all(keyword in filtered_output for keyword in expected_keywords)
        status = "✅ 通过" if passed else "❌ 失败"
        
        print(f"{status} - {input_text[:30]}...")
        print(f"  过滤后: {filtered_output[:50]}...")
        if not passed:
            print(f"  期望关键词: {expected_keywords}")
    
    # 测试内部术语保护
    print("\n内部术语保护测试:")
    internal_test_cases = [
        ("系统使用KAIROS守护标准", ["[INTERNAL_TERM]"]),
        ("Memory V2记忆系统运行正常", ["[INTERNAL_TERM]"]),
        ("情报官处理数据中", ["[INTERNAL_TERM]"]),
    ]
    
    for input_text, expected_keywords in internal_test_cases:
        filtered_output, audit_info = auditor.filter_output(
            component_id="快速测试",
            output_data=input_text,
            security_level=SecurityLevel.RESTRICTED
        )
        
        passed = all(keyword in filtered_output for keyword in expected_keywords)
        status = "✅ 通过" if passed else "❌ 失败"
        
        print(f"{status} - {input_text}")
        print(f"  过滤后: {filtered_output}")
        if not passed:
            print(f"  期望关键词: {expected_keywords}")
    
    # 停止审计服务
    auditor.stop_audit_service()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()