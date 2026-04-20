#!/usr/bin/env python3
"""
Cookie管理模块
用于管理TikTok、Instagram等平台的登录状态Cookie
"""

import json
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import os

class CookieManager:
    """Cookie管理器"""
    
    def __init__(self, storage_path: str = "memory/cookies.json"):
        self.storage_path = storage_path
        self.cookies = self.load_cookies()
        
    def load_cookies(self) -> Dict[str, Dict]:
        """从存储加载Cookie"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cookies(self):
        """保存Cookie到存储"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.cookies, f, ensure_ascii=False, indent=2)
    
    def get_cookie(self, platform: str, account_id: str = "default") -> Optional[Dict[str, str]]:
        """获取指定平台和账号的Cookie"""
        key = f"{platform}_{account_id}"
        if key not in self.cookies:
            return None
            
        cookie_data = self.cookies[key]
        
        # 检查Cookie是否过期
        expires = cookie_data.get('expires')
        if expires:
            expires_dt = datetime.fromisoformat(expires)
            if datetime.now() > expires_dt:
                print(f"Cookie for {platform}({account_id}) has expired")
                return None
        
        return cookie_data.get('cookies', {})
    
    def set_cookie(self, platform: str, cookies: Dict[str, str], 
                  account_id: str = "default", expires_days: int = 7):
        """设置Cookie"""
        key = f"{platform}_{account_id}"
        
        expires = None
        if expires_days > 0:
            expires = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        self.cookies[key] = {
            'platform': platform,
            'account_id': account_id,
            'cookies': cookies,
            'expires': expires,
            'updated_at': datetime.now().isoformat()
        }
        
        self.save_cookies()
        print(f"Cookie for {platform}({account_id}) saved, expires in {expires_days} days")
    
    def check_validity(self, platform: str, account_id: str = "default") -> Dict[str, any]:
        """检查Cookie有效性"""
        key = f"{platform}_{account_id}"
        
        if key not in self.cookies:
            return {
                'valid': False,
                'reason': 'No cookie found',
                'action_required': True
            }
        
        cookie_data = self.cookies[key]
        expires = cookie_data.get('expires')
        
        if expires:
            expires_dt = datetime.fromisoformat(expires)
            days_remaining = (expires_dt - datetime.now()).days
            
            if days_remaining <= 0:
                return {
                    'valid': False,
                    'reason': f'Cookie expired {abs(days_remaining)} days ago',
                    'action_required': True
                }
            elif days_remaining <= 2:
                return {
                    'valid': True,
                    'reason': f'Cookie expires in {days_remaining} days',
                    'action_required': True,
                    'warning': 'Renew cookie soon'
                }
            else:
                return {
                    'valid': True,
                'reason': f'Cookie valid for {days_remaining} more days',
                    'action_required': False
                }
        else:
            # 无过期时间，假设永久有效（但建议定期更新）
            return {
                'valid': True,
                'reason': 'Cookie has no expiration date',
                'action_required': False,
                'warning': 'Consider setting expiration for security'
            }
    
    def get_all_platforms(self) -> List[str]:
        """获取所有已配置的平台"""
        platforms = set()
        for key in self.cookies.keys():
            platform = key.split('_')[0]
            platforms.add(platform)
        return list(platforms)
    
    def delete_cookie(self, platform: str, account_id: str = "default"):
        """删除Cookie"""
        key = f"{platform}_{account_id}"
        if key in self.cookies:
            del self.cookies[key]
            self.save_cookies()
            print(f"Cookie for {platform}({account_id}) deleted")


# 平台特定的Cookie配置
PLATFORM_COOKIE_CONFIGS = {
    "tiktok": {
        "required_cookies": ["sessionid", "tt_chain_token"],
        "description": "TikTok登录态Cookie，需从浏览器开发者工具获取",
        "expires_days": 7,
        "validation_url": "https://www.tiktok.com/api/user/check/"
    },
    "instagram": {
        "required_cookies": ["sessionid", "csrftoken"],
        "description": "Instagram登录态Cookie",
        "expires_days": 3,
        "validation_url": "https://www.instagram.com/api/v1/users/check_username/"
    },
    "amazon": {
        "required_cookies": ["session-id", "ubid-main"],
        "description": "Amazon会话Cookie",
        "expires_days": 30,
        "validation_url": "https://www.amazon.com/"
    }
}


def create_cookie_template(platform: str) -> Dict[str, any]:
    """创建Cookie配置模板"""
    if platform not in PLATFORM_COOKIE_CONFIGS:
        return {
            "platform": platform,
            "required_cookies": ["session_id", "token"],
            "description": "通用平台Cookie配置",
            "expires_days": 7
        }
    
    config = PLATFORM_COOKIE_CONFIGS[platform].copy()
    config["platform"] = platform
    
    # 添加示例值
    config["example"] = {}
    for cookie in config["required_cookies"]:
        config["example"][cookie] = f"YOUR_{cookie.upper()}_VALUE"
    
    return config


if __name__ == "__main__":
    # 测试Cookie管理器
    manager = CookieManager()
    
    # 创建示例Cookie
    sample_tiktok_cookies = {
        "sessionid": "1234567890abcdef",
        "tt_chain_token": "token_value_here"
    }
    
    manager.set_cookie("tiktok", sample_tiktok_cookies, expires_days=7)
    
    # 检查有效性
    validity = manager.check_validity("tiktok")
    print(f"TikTok Cookie validity: {validity}")
    
    # 获取Cookie
    cookies = manager.get_cookie("tiktok")
    print(f"Retrieved cookies: {cookies}")
    
    # 保存配置模板
    templates = {}
    for platform in ["tiktok", "instagram", "amazon"]:
        templates[platform] = create_cookie_template(platform)
    
    with open("src/cookie_templates.json", "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)
    
    print("\nCookie templates saved to src/cookie_templates.json")