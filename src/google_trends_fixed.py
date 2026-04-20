#!/usr/bin/env python3
"""
Google Trends专用修复模块
针对SSL握手错误的优化方案
"""

import requests
import json
import time
import warnings
from datetime import datetime
from typing import Dict, Any

def get_google_trends_data_fixed(keyword: str = "dropshipping", 
                                 region: str = "US", 
                                 time_range: str = "now 7-d") -> Dict[str, Any]:
    """
    修复后的Google Trends数据获取函数
    采用多重连接策略解决SSL和代理问题
    """
    
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    
    url = "https://trends.google.com/trends/api/explore"
    params = {
        "hl": "en-US",
        "tz": "-480",
        "req": json.dumps({
            "comparisonItem": [{
                "keyword": keyword,
                "geo": region,
                "time": time_range
            }],
            "category": 0,
            "property": ""
        })
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    connection_strategies = [
        {"name": "direct_no_ssl", "proxies": {"http": None, "https": None}, "verify": False, "timeout": 30},
        {"name": "direct_with_ssl", "proxies": {"http": None, "https": None}, "verify": True, "timeout": 30},
        {"name": "proxy_no_ssl", "proxies": None, "verify": False, "timeout": 30},
        {"name": "proxy_with_ssl", "proxies": None, "verify": True, "timeout": 30},
    ]
    
    for strategy in connection_strategies:
        try:
            start_time = time.time()
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                proxies=strategy["proxies"],
                verify=strategy["verify"],
                timeout=strategy["timeout"]
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "strategy": strategy["name"],
                    "status_code": response.status_code,
                    "response_time_ms": response_time,
                    "data": response.text[:1000] if response.text else "",
                    "error": None,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            # 继续尝试下一个策略
            continue
    
    # 所有策略都失败
    return {
        "success": False,
        "error": "所有连接策略均失败，可能受网络环境限制",
        "timestamp": datetime.now().isoformat()
    }

def test_google_trends_connection():
    """测试Google Trends连接"""
    print("测试Google Trends连接...")
    result = get_google_trends_data_fixed()
    
    if result["success"]:
        print(f"  ✓ 连接成功 (策略: {result.get('strategy', '未知')})")
        print(f"     状态码: {result.get('status_code', 'N/A')}")
        print(f"     响应时间: {result.get('response_time_ms', 0):.1f}ms")
    else:
        print(f"  ✗ 连接失败: {result.get('error', '未知错误')}")
    
    return result

if __name__ == "__main__":
    test_google_trends_connection()
