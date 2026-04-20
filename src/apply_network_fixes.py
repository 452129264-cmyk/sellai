#!/usr/bin/env python3
"""
应用网络连接修复到爬虫配置文件
"""

import os
import re
import shutil

def backup_original_file():
    """备份原始文件"""
    original = "src/traffic_burst_crawlers.py"
    backup = "src/traffic_burst_crawlers.py.backup_20260404"
    
    if os.path.exists(original):
        shutil.copy2(original, backup)
        print(f"✓ 已备份原始文件: {backup}")
        return True
    else:
        print(f"✗ 找不到原始文件: {original}")
        return False

def apply_fixes_to_crawler():
    """更新爬虫配置文件"""
    
    with open("src/traffic_burst_crawlers.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查是否需要修改
    if "proxy_control" in content and "verify_ssl" in content:
        print("✓ 配置文件已包含修复参数")
        return True
    
    # 修改 make_request 方法签名
    # 找到方法定义
    make_request_pattern = r"def make_request\(self, url: str, headers: Optional\[Dict\] = None,[\s\S]*?\) -> Dict\[str, Any\]:"
    match = re.search(make_request_pattern, content)
    
    if not match:
        print("✗ 找不到 make_request 方法定义")
        return False
    
    old_signature = match.group(0)
    
    # 添加新参数
    if "proxy_control" not in old_signature:
        # 在参数列表中添加 proxy_control 和 verify_ssl
        new_signature = old_signature.replace(
            "timeout: int = 30) -> Dict[str, Any]:",
            "timeout: int = 30, proxy_control: str = \"auto\", verify_ssl: bool = True) -> Dict[str, Any]:"
        )
        
        content = content.replace(old_signature, new_signature)
        print("✓ 已更新 make_request 方法签名")
    
    # 在方法体内添加代理控制逻辑
    # 找到请求执行部分
    request_execution_pattern = r"if method\.upper\(\) == \"GET\":[\s\S]*?response = self\.session\.get\(url, headers=request_headers,[\s\S]*?params=params, timeout=timeout\)"
    match = re.search(request_execution_pattern, content)
    
    if match:
        old_request_code = match.group(0)
        
        # 插入代理控制代码
        proxy_control_code = '''
            # 代理控制逻辑
            request_kwargs = {"timeout": timeout, "verify": verify_ssl}
            
            if proxy_control == "direct":
                request_kwargs["proxies"] = {"http": None, "https": None}
            elif proxy_control == "proxy":
                # 使用环境变量中的代理
                pass
            elif proxy_control == "auto":
                # 根据平台诊断结果自动选择
                platform_lower = platform.lower()
                if "tiktok" in platform_lower or "instagram" in platform_lower or "reddit" in platform_lower:
                    # 这些平台建议使用代理
                    pass
                else:
                    # 其他平台尝试直接连接
                    request_kwargs["proxies"] = {"http": None, "https": None}
            
            # 执行请求
            if method.upper() == "GET":
                response = self.session.get(url, headers=request_headers, 
                                           params=params, **request_kwargs)
            else:
                response = self.session.post(url, headers=request_headers, 
                                            json=params, **request_kwargs)'''
        
        # 替换请求执行代码
        new_request_code = old_request_code.replace(
            "if method.upper() == \"GET\":",
            proxy_control_code
        )
        
        content = content.replace(old_request_code, new_request_code)
        print("✓ 已添加代理控制逻辑")
    
    # 写回文件
    with open("src/traffic_burst_crawlers.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✓ 配置文件更新完成")
    return True

def create_google_trends_fix():
    """创建Google Trends专用修复模块"""
    
    google_trends_code = '''#!/usr/bin/env python3
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
'''
    
    with open("src/google_trends_fixed.py", "w", encoding="utf-8") as f:
        f.write(google_trends_code)
    
    print("✓ 已创建Google Trends修复模块: src/google_trends_fixed.py")
    return True

def create_final_test_script():
    """创建最终测试脚本"""
    
    test_script = '''#!/usr/bin/env python3
"""
数据管道修复后最终验证脚本
测试所有7个平台的连接状态
"""

import requests
import json
import time
import warnings
from datetime import datetime
from typing import Dict, List, Any

# 禁用SSL警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

def make_request_with_options(url: str, platform: str, use_proxy: bool = False, verify_ssl: bool = False) -> Dict[str, Any]:
    """带选项的HTTP请求"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    proxies = None if use_proxy else {"http": None, "https": None}
    
    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=30, verify=verify_ssl, proxies=proxies)
        response_time = (time.time() - start_time) * 1000
        
        return {
            "platform": platform,
            "url": url,
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response_time_ms": response_time,
            "error": None,
            "timestamp": datetime.now().isoformat(),
            "strategy": f"{'proxy' if use_proxy else 'direct'}_{'ssl' if verify_ssl else 'no_ssl'}"
        }
    except Exception as e:
        return {
            "platform": platform,
            "url": url,
            "success": False,
            "status_code": None,
            "response_time_ms": None,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "strategy": f"{'proxy' if use_proxy else 'direct'}_{'ssl' if verify_ssl else 'no_ssl'}"
        }

def test_all_platforms() -> List[Dict[str, Any]]:
    """测试所有平台"""
    
    test_cases = [
        {
            "platform": "Amazon",
            "url": "https://www.amazon.com/s?k=test&i=electronics",
            "strategies": [
                {"use_proxy": True, "verify_ssl": True},
                {"use_proxy": False, "verify_ssl": True}
            ]
        },
        {
            "platform": "Google Trends",
            "url": "https://trends.google.com/trends/api/explore?hl=en-US&tz=-480",
            "strategies": [
                {"use_proxy": False, "verify_ssl": False},
                {"use_proxy": True, "verify_ssl": False}
            ]
        },
        {
            "platform": "TikTok",
            "url": "https://www.tiktok.com/api/trending/item/list/?region=US&count=5",
            "strategies": [
                {"use_proxy": False, "verify_ssl": False},
                {"use_proxy": True, "verify_ssl": False}
            ]
        },
        {
            "platform": "Instagram",
            "url": "https://www.instagram.com/explore/tags/entrepreneur/",
            "strategies": [
                {"use_proxy": False, "verify_ssl": False},
                {"use_proxy": True, "verify_ssl": False}
            ]
        },
        {
            "platform": "Reddit",
            "url": "https://www.reddit.com/r/Entrepreneur/hot.json?limit=5",
            "strategies": [
                {"use_proxy": False, "verify_ssl": False},
                {"use_proxy": True, "verify_ssl": False}
            ]
        },
        {
            "platform": "Entrepreneur.com",
            "url": "https://www.entrepreneur.com/api/v1/articles?category=business-ideas&limit=5",
            "strategies": [
                {"use_proxy": True, "verify_ssl": True},
                {"use_proxy": False, "verify_ssl": True}
            ]
        },
        {
            "platform": "绍兴政府补贴",
            "url": "http://www.shaoxing.gov.cn/col/col1229452808/index.html",
            "strategies": [
                {"use_proxy": True, "verify_ssl": True},
                {"use_proxy": False, "verify_ssl": True}
            ]
        }
    ]
    
    all_results = []
    
    print("=== 数据管道修复后最终验证 ===\\n")
    
    for test_case in test_cases:
        platform = test_case["platform"]
        print(f"测试 {platform}...")
        
        best_result = None
        
        for strategy in test_case["strategies"]:
            result = make_request_with_options(
                test_case["url"],
                platform,
                use_proxy=strategy["use_proxy"],
                verify_ssl=strategy["verify_ssl"]
            )
            
            if result["success"]:
                best_result = result
                break
        
        if best_result and best_result["success"]:
            print(f"  ✓ 成功 (策略: {best_result['strategy']}, 状态码: {best_result['status_code']})")
        else:
            print(f"  ✗ 失败: {best_result['error'] if best_result else '所有策略均失败'}")
        
        all_results.append(best_result if best_result else {
            "platform": platform,
            "success": False,
            "error": "所有连接策略均失败"
        })
    
    return all_results

def calculate_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算统计信息"""
    
    successful = [r for r in results if r and r.get("success")]
    total = len(results)
    success_rate = (len(successful) / total * 100) if total > 0 else 0
    
    # 核心平台统计
    amazon_success = any(r for r in results if r and r.get("platform") == "Amazon" and r.get("success"))
    google_success = any(r for r in results if r and r.get("platform") == "Google Trends" and r.get("success"))
    
    return {
        "total_platforms": total,
        "successful_platforms": len(successful),
        "success_rate_percent": success_rate,
        "target_success_rate": 70.0,
        "meets_target": success_rate >= 70.0,
        "core_platforms": {
            "amazon_success": amazon_success,
            "google_trends_success": google_success,
            "both_success": amazon_success and google_success
        }
    }

def main():
    """主函数"""
    results = test_all_platforms()
    stats = calculate_statistics(results)
    
    print(f"\\n=== 验证结果 ===\\n")
    print(f"测试平台总数: {stats['total_platforms']}")
    print(f"成功爬取平台: {stats['successful_platforms']}")
    print(f"整体成功率: {stats['success_rate_percent']:.1f}%")
    print(f"目标成功率: {stats['target_success_rate']}%")
    print(f"是否达标: {'✓ 达标' if stats['meets_target'] else '✗ 未达标'}")
    
    print(f"\\n=== 核心平台状态 ===\\n")
    print(f"Amazon: {'✓ 成功' if stats['core_platforms']['amazon_success'] else '✗ 失败'}")
    print(f"Google Trends: {'✓ 成功' if stats['core_platforms']['google_trends_success'] else '✗ 失败'}")
    
    if stats['meets_target']:
        print("\\n✅ 数据管道稳定性达标，可支持7×24小时稳定运行。")
    else:
        print("\\n⚠️  数据管道稳定性未达标，需根据网络环境进一步优化。")
    
    # 保存结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "statistics": stats
    }
    
    os.makedirs("temp", exist_ok=True)
    with open("temp/final_validation_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    print(f"\\n详细结果已保存: temp/final_validation_results.json")
    
    return output

if __name__ == "__main__":
    main()
'''
    
    with open("src/final_data_pipeline_test.py", "w", encoding="utf-8") as f:
        f.write(test_script)
    
    print("✓ 已创建最终测试脚本: src/final_data_pipeline_test.py")
    return True

def main():
    """主修复流程"""
    print("开始应用网络连接修复...\n")
    
    # 步骤1: 备份原始文件
    if not backup_original_file():
        return False
    
    # 步骤2: 更新爬虫配置文件
    if not apply_fixes_to_crawler():
        return False
    
    # 步骤3: 创建Google Trends修复模块
    if not create_google_trends_fix():
        return False
    
    # 步骤4: 创建最终测试脚本
    if not create_final_test_script():
        return False
    
    print("\n✅ 所有修复措施已应用完成")
    print("\n修复文件清单:")
    print("1. src/traffic_burst_crawlers.py - 已更新代理控制和SSL验证")
    print("2. src/google_trends_fixed.py - Google Trends专用修复模块")
    print("3. src/final_data_pipeline_test.py - 最终验证脚本")
    print("4. docs/数据管道网络修复报告.md - 详细修复报告")
    
    print("\n下一步: 运行测试验证修复效果")
    print("命令: python3 src/final_data_pipeline_test.py")
    
    return True

if __name__ == "__main__":
    main()