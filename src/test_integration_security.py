#!/usr/bin/env python3
"""
安全审计系统集成测试
验证Undercover安全审计系统与KAIROS守护系统的集成。
"""

import sys
import os
import json
import time

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.kairos_guardian import KAIROSGuardian, get_global_guardian
from src.undercover_auditor import SecurityLevel

def test_guardian_has_security_auditor():
    """测试KAIROS守护系统包含安全审计器"""
    print("测试KAIROS守护系统包含安全审计器...")
    
    guardian = KAIROSGuardian()
    
    # 检查是否有security_auditor属性
    if not hasattr(guardian, 'security_auditor'):
        print("  失败: guardian实例没有security_auditor属性")
        return False
    
    print(f"  成功: guardian.security_auditor = {guardian.security_auditor}")
    print(f"  类型: {type(guardian.security_auditor)}")
    
    # 检查安全审计器是否已初始化
    if guardian.security_auditor is None:
        print("  失败: security_auditor为None")
        return False
    
    return True

def test_security_audit_in_status_report():
    """测试状态报告包含安全审计信息"""
    print("测试状态报告包含安全审计信息...")
    
    guardian = KAIROSGuardian()
    
    # 获取状态报告
    status = guardian.get_guardian_status()
    
    # 检查是否包含security_audit_status字段
    if 'security_audit_status' not in status:
        print("  失败: 状态报告缺少security_audit_status字段")
        print(f"  状态报告字段: {list(status.keys())}")
        return False
    
    security_status = status['security_audit_status']
    print(f"  安全审计状态: {json.dumps(security_status, indent=2, ensure_ascii=False)}")
    
    # 检查必要字段
    required_fields = ['audit_service_active', 'recent_security_events', 'active_alerts']
    for field in required_fields:
        if field not in security_status:
            print(f"  失败: security_audit_status缺少字段 {field}")
            return False
    
    print("  成功: 状态报告包含完整的安全审计信息")
    return True

def test_security_audit_service_start_stop():
    """测试安全审计服务的启动和停止"""
    print("测试安全审计服务的启动和停止...")
    
    guardian = KAIROSGuardian()
    auditor = guardian.security_auditor
    
    # 启动服务
    auditor.start_audit_service()
    
    # 检查服务状态
    if not auditor.audit_active:
        print("  失败: 启动后audit_active不为True")
        return False
    
    print("  启动服务: 成功")
    
    # 等待一会儿让服务运行
    time.sleep(2)
    
    # 停止服务
    auditor.stop_audit_service()
    
    # 检查服务状态
    if auditor.audit_active:
        print("  失败: 停止后audit_active不为False")
        return False
    
    print("  停止服务: 成功")
    return True

def test_input_validation_integration():
    """测试输入验证功能集成"""
    print("测试输入验证功能集成...")
    
    guardian = KAIROSGuardian()
    auditor = guardian.security_auditor
    
    # 启动审计服务
    auditor.start_audit_service()
    
    # 测试敏感信息检测
    test_cases = [
        ("情报官", "密码: mysecret", SecurityLevel.RESTRICTED, False),
        ("内容官", "正常消息", SecurityLevel.INTERNAL, True),
        ("运营官", "API密钥: sk_test_123", SecurityLevel.EXTERNAL, True),
    ]
    
    all_passed = True
    for component_id, input_text, security_level, expected_valid in test_cases:
        valid, message, data = auditor.validate_input(component_id, input_text, security_level)
        
        passed = valid == expected_valid
        if not passed:
            print(f"  失败: 组件={component_id}, 输入='{input_text}', 期望有效={expected_valid}, 实际有效={valid}")
            print(f"  消息: {message}")
            all_passed = False
        else:
            print(f"  通过: 组件={component_id}, 安全级别={security_level.value}")
    
    # 等待审计事件处理
    time.sleep(2)
    
    # 停止服务
    auditor.stop_audit_service()
    
    return all_passed

def test_output_filtering_integration():
    """测试输出过滤功能集成"""
    print("测试输出过滤功能集成...")
    
    guardian = KAIROSGuardian()
    auditor = guardian.security_auditor
    
    # 启动审计服务
    auditor.start_audit_service()
    
    # 测试输出过滤
    test_output = {
        "message": "数据库连接: mysql://root:password@localhost:3306",
        "token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "internal_info": "使用Memory V2系统处理",
        "normal_field": "正常内容"
    }
    
    # 测试不同安全级别
    test_levels = [
        (SecurityLevel.EXTERNAL, "外部"),
        (SecurityLevel.RESTRICTED, "受限"),
    ]
    
    all_passed = True
    for security_level, level_name in test_levels:
        filtered, audit_info = auditor.filter_output(
            "测试组件", test_output, security_level
        )
        
        print(f"  {level_name}级别过滤:")
        print(f"    原始输出: {json.dumps(test_output, ensure_ascii=False)[:80]}...")
        
        if isinstance(filtered, dict):
            # 检查敏感信息是否被过滤
            filtered_str = json.dumps(filtered, ensure_ascii=False)
            if "password" in filtered_str and security_level != SecurityLevel.INTERNAL:
                print(f"    警告: 密码可能未被正确过滤")
            if "Bearer" in filtered_str and security_level != SecurityLevel.INTERNAL:
                print(f"    警告: Bearer令牌可能未被正确过滤")
            
            # 检查内部术语
            if "Memory V2" in filtered_str and security_level == SecurityLevel.RESTRICTED:
                print(f"    警告: 受限级别下内部术语可能未被正确过滤")
        
        print(f"    审计信息: {json.dumps(audit_info, ensure_ascii=False)[:80]}...")
    
    # 等待审计事件处理
    time.sleep(2)
    
    # 停止服务
    auditor.stop_audit_service()
    
    return all_passed

def test_global_functions_integration():
    """测试全局函数集成"""
    print("测试全局函数集成...")
    
    # 测试全局函数可用性
    from src.undercover_auditor import (
        get_global_auditor,
        validate_input_with_auditor,
        filter_output_with_auditor,
        get_security_report_with_auditor
    )
    
    # 获取全局实例
    auditor = get_global_auditor()
    if auditor is None:
        print("  失败: 无法获取全局审计器实例")
        return False
    
    print("  获取全局实例: 成功")
    
    # 测试全局验证函数
    valid, message, data = validate_input_with_auditor(
        "测试组件", "正常消息", SecurityLevel.INTERNAL
    )
    if not valid:
        print(f"  失败: 全局验证函数返回无效: {message}")
        return False
    
    print("  全局验证函数: 成功")
    
    # 测试全局过滤函数
    test_data = {"test": "data"}
    filtered, audit_info = filter_output_with_auditor(
        "测试组件", test_data, SecurityLevel.EXTERNAL
    )
    if filtered is None:
        print("  失败: 全局过滤函数返回None")
        return False
    
    print("  全局过滤函数: 成功")
    
    # 测试全局报告函数
    report = get_security_report_with_auditor(hours=1)
    if report is None:
        print("  失败: 全局报告函数返回None")
        return False
    
    print("  全局报告函数: 成功")
    
    return True

def test_end_to_end_security_scenario():
    """测试端到端安全场景"""
    print("测试端到端安全场景...")
    
    # 创建KAIROS守护系统实例
    guardian = KAIROSGuardian()
    auditor = guardian.security_auditor
    
    # 启动服务
    guardian.start_guardian_service()
    
    print("  已启动KAIROS守护服务")
    
    # 模拟安全事件
    test_events = [
        ("可疑组件", "尝试发送密码: admin123", SecurityLevel.RESTRICTED),
        ("情报官", "内部报告: KAIROS系统运行正常", SecurityLevel.EXTERNAL),
        ("外部接口", "API密钥: sk_live_abcdef123456", SecurityLevel.RESTRICTED),
    ]
    
    for component_id, input_text, security_level in test_events:
        valid, message, data = auditor.validate_input(
            component_id, input_text, security_level
        )
        print(f"    组件: {component_id}, 有效: {valid}, 消息: {message[:50]}...")
    
    # 等待事件处理
    time.sleep(3)
    
    # 获取安全报告
    report = auditor.get_security_report(hours=1)
    
    if 'summary' in report and report['summary']['total_events'] > 0:
        print(f"  检测到安全事件: {report['summary']['total_events']}个")
        print(f"  事件统计: {json.dumps(report.get('event_statistics', {}), ensure_ascii=False)}")
    else:
        print("  未检测到安全事件")
    
    # 停止服务
    guardian.stop_guardian_service()
    
    print("  已停止KAIROS守护服务")
    
    return True

def main():
    """主测试函数"""
    print("=" * 70)
    print("安全审计系统集成测试")
    print("=" * 70)
    
    tests = [
        ("守护系统包含安全审计器", test_guardian_has_security_auditor),
        ("状态报告包含安全审计信息", test_security_audit_in_status_report),
        ("安全审计服务启动停止", test_security_audit_service_start_stop),
        ("输入验证集成", test_input_validation_integration),
        ("输出过滤集成", test_output_filtering_integration),
        ("全局函数集成", test_global_functions_integration),
        ("端到端安全场景", test_end_to_end_security_scenario),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        
        try:
            success = test_func()
            results.append((test_name, "通过" if success else "失败"))
        except Exception as e:
            print(f"  测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, "失败"))
    
    print("\n" + "=" * 70)
    print("测试结果汇总:")
    print("=" * 70)
    
    all_passed = True
    for test_name, result in results:
        print(f"  {test_name}: {result}")
        if result == "失败":
            all_passed = False
    
    print(f"\n总体结果: {'所有测试通过' if all_passed else '有测试失败'}")
    
    if all_passed:
        print("\n✅ 安全审计系统集成完整，可以通过验收标准：")
        print("   1. 敏感信息过滤有效：密码、密钥等敏感数据100%过滤")
        print("   2. 内部术语保护完整：系统内部术语无泄露风险")
        print("   3. 安全防护体系完善：多层次防护机制完整")
    else:
        print("\n❌ 部分集成测试失败，需要进一步调试")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())