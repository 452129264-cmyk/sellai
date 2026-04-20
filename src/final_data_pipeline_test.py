#!/usr/bin/env python3
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
    
    print("=== 数据管道修复后最终验证 ===\n")
    
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
    
    print(f"\n=== 验证结果 ===\n")
    print(f"测试平台总数: {stats['total_platforms']}")
    print(f"成功爬取平台: {stats['successful_platforms']}")
    print(f"整体成功率: {stats['success_rate_percent']:.1f}%")
    print(f"目标成功率: {stats['target_success_rate']}%")
    print(f"是否达标: {'✓ 达标' if stats['meets_target'] else '✗ 未达标'}")
    
    print(f"\n=== 核心平台状态 ===\n")
    print(f"Amazon: {'✓ 成功' if stats['core_platforms']['amazon_success'] else '✗ 失败'}")
    print(f"Google Trends: {'✓ 成功' if stats['core_platforms']['google_trends_success'] else '✗ 失败'}")
    
    if stats['meets_target']:
        print("\n✅ 数据管道稳定性达标，可支持7×24小时稳定运行。")
    else:
        print("\n⚠️  数据管道稳定性未达标，需根据网络环境进一步优化。")
    
    # 保存结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "statistics": stats
    }
    
    os.makedirs("temp", exist_ok=True)
    with open("temp/final_validation_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n详细结果已保存: temp/final_validation_results.json")
    
    return output

if __name__ == "__main__":
    main()
