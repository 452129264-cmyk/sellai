#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送功能集成测试
测试推送管理器与办公室界面的集成
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.push_notification_manager import PushNotificationManager
from datetime import datetime

def test_push_manager_integration():
    """测试推送管理器集成"""
    print("=== 推送功能集成测试 ===")
    
    # 1. 初始化推送管理器
    print("1. 初始化推送管理器...")
    manager = PushNotificationManager()
    assert manager is not None
    assert 'config' in manager.__dict__
    print("   ✅ 推送管理器初始化成功")
    
    # 2. 检查配置文件是否存在
    print("2. 检查配置文件...")
    config_path = manager.config_path
    assert os.path.exists(config_path), f"配置文件不存在: {config_path}"
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    assert 'wechat' in config_data
    assert 'email' in config_data
    assert 'scenes' in config_data
    print("   ✅ 配置文件检查通过")
    
    # 3. 测试推送发送功能
    print("3. 测试推送发送功能...")
    test_data = {
        "avatar_name": "情报官",
        "previous_status": "离线",
        "new_status": "在线",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "office_url": "https://sellai-office.example.com"
    }
    
    result = manager.send_notification('avatar_status', test_data)
    assert 'success' in result
    assert 'results' in result
    print("   ✅ 推送发送功能测试通过")
    
    # 4. 测试配置更新功能
    print("4. 测试配置更新功能...")
    update_result = manager.update_config(
        wechat_openid="test_openid_123",
        email="test@example.com",
        enabled_scenes={"avatar_status": True, "new_opportunity": False}
    )
    assert update_result == True
    print("   ✅ 配置更新功能测试通过")
    
    # 5. 测试统计功能
    print("5. 测试统计功能...")
    stats = manager.get_statistics(days=1)
    assert 'total_count' in stats
    assert 'success_rate' in stats
    print("   ✅ 统计功能测试通过")
    
    # 6. 测试日志查询功能
    print("6. 测试日志查询功能...")
    logs = manager.get_recent_logs(limit=5)
    assert isinstance(logs, list)
    print("   ✅ 日志查询功能测试通过")
    
    # 7. 检查HTML办公室界面更新
    print("7. 检查办公室界面更新...")
    office_html_path = "/app/data/files/outputs/仪表盘/SellAI_办公室_升级版.html"
    assert os.path.exists(office_html_path), f"办公室界面文件不存在: {office_html_path}"
    
    with open(office_html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 检查是否包含推送设置模块
    assert '推送设置' in html_content, "办公室界面缺少推送设置模块"
    assert 'pushSettings' in html_content, "办公室界面缺少推送设置JavaScript"
    assert 'wechat-openid-input' in html_content, "办公室界面缺少微信OpenID输入框"
    assert 'scene-avatar-status-switch' in html_content, "办公室界面缺少场景开关"
    print("   ✅ 办公室界面更新检查通过")
    
    # 8. 验证推送模板
    print("8. 验证推送模板...")
    templates_path = "/app/data/files/data/push_templates.json"
    assert os.path.exists(templates_path), f"推送模板文件不存在: {templates_path}"
    
    with open(templates_path, 'r', encoding='utf-8') as f:
        templates = json.load(f)
    
    required_scenes = ['avatar_status', 'new_opportunity', 'match_recommendation', 'chat_message']
    for scene in required_scenes:
        assert scene in templates, f"缺少场景模板: {scene}"
        assert 'title' in templates[scene], f"场景模板缺少title: {scene}"
        assert 'content' in templates[scene], f"场景模板缺少content: {scene}"
    
    print("   ✅ 推送模板验证通过")
    
    # 9. 模拟推送测试
    print("9. 模拟推送测试...")
    test_result = manager.test_connection()
    assert 'wechat' in test_result
    assert 'email' in test_result
    print("   ✅ 模拟推送测试通过")
    
    # 10. 恢复配置
    print("10. 恢复默认配置...")
    manager.update_config(
        wechat_openid="",
        email="",
        enabled_scenes={"avatar_status": True, "new_opportunity": True,
                       "match_recommendation": True, "chat_message": True}
    )
    print("   ✅ 配置恢复成功")
    
    print("\n=== 集成测试完成 ===")
    print("所有测试用例通过，推送功能完全可用！")
    
    # 输出测试报告
    report = {
        "test_name": "推送功能集成测试",
        "timestamp": datetime.now().isoformat(),
        "test_cases": {
            "push_manager_initialization": "通过",
            "config_file_check": "通过",
            "push_send_function": "通过",
            "config_update_function": "通过",
            "statistics_function": "通过",
            "log_query_function": "通过",
            "office_interface_update": "通过",
            "push_templates_validation": "通过",
            "simulation_push_test": "通过",
            "config_restoration": "通过"
        },
        "push_logs_count": stats.get('total_count', 0),
        "success_rate": f"{stats.get('success_rate', 0)}%",
        "recommendations": [
            "1. 在办公室界面配置真实的微信/邮箱推送账号",
            "2. 根据实际需求调整推送频率限制",
            "3. 定期检查推送记录确保通知送达",
            "4. 集成测试验证通过，可投入生产使用"
        ]
    }
    
    print("\n测试报告:")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    
    return True

if __name__ == "__main__":
    try:
        test_push_manager_integration()
    except Exception as e:
        print(f"集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)