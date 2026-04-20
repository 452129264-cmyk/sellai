#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试推送管理器基本功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.push_notification_manager import PushNotificationManager
from datetime import datetime
import json

def test_basic():
    print("=== 测试推送管理器基本功能 ===")
    
    # 初始化管理器
    manager = PushNotificationManager()
    
    print("1. 配置加载测试...")
    print(f"   配置路径: {manager.config_path}")
    print(f"   配置内容: {json.dumps(manager.config, ensure_ascii=False, indent=2)}")
    
    print("\n2. 模板加载测试...")
    print(f"   模板数量: {len(manager.templates)}")
    for scene, template in manager.templates.items():
        print(f"   - {scene}: {template.get('title', '无标题')}")
    
    print("\n3. 模拟推送测试...")
    test_data = {
        "avatar_name": "测试分身",
        "previous_status": "离线",
        "new_status": "在线",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "office_url": "https://sellai-office.example.com"
    }
    
    result = manager.send_notification('avatar_status', test_data)
    print(f"   发送结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    print("\n4. 配置更新测试...")
    update_result = manager.update_config(
        wechat_openid="test_openid_123",
        email="test@example.com",
        enabled_scenes={"avatar_status": True, "new_opportunity": False}
    )
    print(f"   更新结果: {update_result}")
    print(f"   更新后配置: {json.dumps(manager.config, ensure_ascii=False, indent=2)}")
    
    print("\n5. 获取统计测试...")
    stats = manager.get_statistics(days=7)
    print(f"   统计信息: {json.dumps(stats, ensure_ascii=False, indent=2)}")
    
    print("\n6. 获取最近记录测试...")
    logs = manager.get_recent_logs(limit=3)
    print(f"   最近记录:")
    for log in logs:
        print(f"   - [{log['timestamp']}] {log['scene_type']} ({log['channel']}): {log['status']}")
    
    print("\n=== 测试完成 ===")
    
    # 恢复配置
    manager.update_config(
        wechat_openid="",
        email="",
        enabled_scenes={"avatar_status": True, "new_opportunity": True,
                       "match_recommendation": True, "chat_message": True}
    )

if __name__ == "__main__":
    test_basic()