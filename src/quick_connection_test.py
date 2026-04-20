#!/usr/bin/env python3
"""
快速连接测试 - 检查Amazon和Google Trends的可达性
"""

import requests
import socket
import ssl
import os
import sys
from datetime import datetime
import warnings

# 禁用SSL警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

def test_direct_connection(host: str, port: int = 443) -> bool:
    """测试直接TCP/SSL连接"""
    try:
        sock = socket.create_connection((host, port), timeout=10)
        if port == 443:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            ssl_sock = context.wrap_socket(sock, server_hostname=host)
            ssl_sock.close()
        sock.close()
        return True
    except Exception as e:
        print(f"  ✗ 直接连接错误: {e}")
        return False

def test_http_request(host: str, use_proxy: bool = True) -> bool:
    """测试HTTP请求"""
    url = f"https://{host}"
    try:
        if not use_proxy:
            # 临时移除代理
            http_proxy = os.environ.pop('HTTP_PROXY', None)
            https_proxy = os.environ.pop('HTTPS_PROXY', None)
        
        response = requests.get(url, timeout=15, verify=False)
        
        if not use_proxy:
            # 恢复代理
            if http_proxy:
                os.environ['HTTP_PROXY'] = http_proxy
            if https_proxy:
                os.environ['HTTPS_PROXY'] = https_proxy
        
        return response.status_code == 200
    except Exception as e:
        print(f"  ✗ HTTP请求错误: {e}")
        return False

def main():
    print("=== 快速连接测试 ===\n")
    
    test_hosts = [
        ("www.amazon.com", "Amazon"),
        ("trends.google.com", "Google Trends"),
        ("www.tiktok.com", "TikTok"),
        ("www.reddit.com", "Reddit"),
    ]
    
    all_results = []
    
    for host, name in test_hosts:
        print(f"测试 {name} ({host})...")
        
        # 测试直接连接
        direct_ok = test_direct_connection(host, 443)
        
        # 测试HTTP请求（使用代理）
        http_with_proxy = test_http_request(host, use_proxy=True)
        
        # 测试HTTP请求（不使用代理）
        http_without_proxy = test_http_request(host, use_proxy=False)
        
        success = direct_ok or http_with_proxy or http_without_proxy
        
        result = {
            "name": name,
            "host": host,
            "direct_connection": direct_ok,
            "http_with_proxy": http_with_proxy,
            "http_without_proxy": http_without_proxy,
            "success": success
        }
        
        all_results.append(result)
        
        if success:
            print(f"  ✓ {name} 可达")
        else:
            print(f"  ✗ {name} 不可达")
        print()
    
    # 打印总结
    print("=== 测试总结 ===")
    success_count = sum(1 for r in all_results if r["success"])
    total = len(all_results)
    
    print(f"\n成功连接: {success_count}/{total}")
    
    for result in all_results:
        status = "✓" if result["success"] else "✗"
        methods = []
        if result["direct_connection"]:
            methods.append("直接连接")
        if result["http_with_proxy"]:
            methods.append("代理HTTP")
        if result["http_without_proxy"]:
            methods.append("无代理HTTP")
        
        methods_str = ", ".join(methods) if methods else "无"
        print(f"{status} {result['name']}: {methods_str}")
    
    # 核心平台检查
    print(f"\n=== 核心平台状态 ===")
    amazon_ok = any(r["success"] for r in all_results if r["name"] == "Amazon")
    google_ok = any(r["success"] for r in all_results if r["name"] == "Google Trends")
    
    print(f"Amazon: {'✅ 可达' if amazon_ok else '❌ 不可达'}")
    print(f"Google Trends: {'✅ 可达' if google_ok else '❌ 不可达'}")
    
    if amazon_ok and google_ok:
        print("\n✅ 两个核心平台均可达，可以进行修复实施")
    else:
        print("\n⚠️  核心平台存在问题，需要针对性修复")
    
    return all_results

if __name__ == "__main__":
    main()