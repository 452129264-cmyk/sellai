#!/usr/bin/env python3
"""
数据管道修复测试脚本
针对网络连通性问题进行优化
"""

import requests
import json
import time
from datetime import datetime
import os
import sys
from urllib.parse import urlencode

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def make_request_fixed(url, headers=None, params=None, method="GET", platform_name="未知平台", timeout=60, max_retries=3):
    """执行HTTP请求，增加重试机制和网络优化"""
    
    # 禁用代理，直接连接
    session = requests.Session()
    session.trust_env = False  # 不读取环境变量中的代理配置
    
    test_result = {
        "platform": platform_name,
        "url": url,
        "method": method,
        "timestamp": datetime.now().isoformat(),
        "headers": headers,
        "params": params,
        "success": False,
        "status_code": None,
        "response_time_ms": None,
        "data_sample": None,
        "error": None,
        "antibot_issues": [],
        "data_quality": {
            "has_price_info": False,
            "has_cost_info": False,
            "has_margin_info": False,
            "parsable": False
        }
    }
    
    last_error = None
    for retry in range(max_retries):
        try:
            start_time = time.time()
            
            # 配置请求参数
            request_kwargs = {
                "headers": headers,
                "timeout": timeout,
                "verify": False,  # 禁用SSL验证
                "proxies": {'http': None, 'https': None}  # 禁用代理
            }
            
            if params:
                if method.upper() == "GET":
                    request_kwargs["params"] = params
                else:
                    request_kwargs["json"] = params
            
            if method.upper() == "GET":
                response = session.get(url, **request_kwargs)
            else:
                response = session.post(url, **request_kwargs)
            
            response_time = (time.time() - start_time) * 1000
            
            test_result["status_code"] = response.status_code
            test_result["response_time_ms"] = response_time
            
            # 检查反爬迹象
            if response.status_code == 403 or response.status_code == 429:
                test_result["antibot_issues"].append(f"HTTP {response.status_code} - 访问被拒绝")
            elif "captcha" in response.text.lower():
                test_result["antibot_issues"].append("检测到验证码")
            elif "access denied" in response.text.lower():
                test_result["antibot_issues"].append("访问被拒绝")
            
            response.raise_for_status()
            
            # 处理响应数据
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type:
                data = response.json()
                test_result["data_quality"]["parsable"] = True
                data_str = json.dumps(data).lower()
            else:
                data = response.text
                test_result["data_sample"] = data[:500]
                data_str = data.lower()
            
            # 检查数据质量
            price_keywords = ["price", "cost", "$", "usd", "fee", "amount", "价值", "价格", "成本", "售价"]
            cost_keywords = ["cost", "expense", "production", "manufacturing", "wholesale", "成本", "费用", "进货价"]
            margin_keywords = ["margin", "profit", "毛利率", "利润率", "profitability"]
            
            for keyword in price_keywords:
                if keyword in data_str:
                    test_result["data_quality"]["has_price_info"] = True
                    break
                    
            for keyword in cost_keywords:
                if keyword in data_str:
                    test_result["data_quality"]["has_cost_info"] = True
                    break
                    
            for keyword in margin_keywords:
                if keyword in data_str:
                    test_result["data_quality"]["has_margin_info"] = True
                    break
            
            test_result["success"] = True
            test_result["data_sample"] = str(data)[:500] if not isinstance(data, str) else data[:500]
            
            # 成功则跳出重试循环
            break
            
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            test_result["error"] = last_error
            test_result["antibot_issues"].append(f"请求异常(重试{retry+1}/{max_retries}): {str(e)}")
            
            # 等待后重试
            if retry < max_retries - 1:
                wait_time = (retry + 1) * 3  # 递增等待时间
                print(f"  等待{wait_time}秒后重试...")
                time.sleep(wait_time)
        except Exception as e:
            last_error = str(e)
            test_result["error"] = last_error
            break
    
    return test_result

def test_amazon_fixed():
    """测试Amazon商品数据爬取"""
    url = "https://www.amazon.com/s"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    params = {
        "k": "wireless+earbuds",
        "i": "electronics",
        "s": "price-desc-rank",
        "page": "1",
        "qid": str(int(time.time())),
        "ref": "sr_pg_1"
    }
    
    print(f"测试Amazon搜索: {url}")
    result = make_request_fixed(url, headers, params, platform_name="Amazon")
    
    return result

def test_google_trends_fixed():
    """测试Google Trends搜索趋势爬取"""
    url = "https://trends.google.com/trends/api/explore"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req_data = {
        "comparisonItem": [{
            "keyword": "dropshipping",
            "geo": "US",
            "time": "now 7-d"
        }],
        "category": 0,
        "property": ""
    }
    params = {
        "hl": "en-US",
        "tz": "-480",
        "req": json.dumps(req_data)
    }
    
    print(f"测试Google Trends API: {url}")
    result = make_request_fixed(url, headers, params, platform_name="Google Trends")
    
    return result

def test_reddit_fixed():
    """测试Reddit热门讨论爬取"""
    url = "https://www.reddit.com/r/Entrepreneur/hot.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9"
    }
    params = {
        "limit": "5",
        "t": "day"
    }
    
    print(f"测试Reddit API: {url}")
    result = make_request_fixed(url, headers, params, platform_name="Reddit")
    
    return result

def main():
    """主函数：执行修复后的数据管道测试"""
    print("=== 数据管道修复测试 ===\n")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("测试平台: 3个关键平台 (Amazon, Google Trends, Reddit)\n")
    
    all_results = []
    
    # 1. Amazon
    print("1. 测试 Amazon...")
    result = test_amazon_fixed()
    all_results.append(result)
    print(f"   状态: {'✅ 成功' if result['success'] else '❌ 失败'}")
    time.sleep(2)
    
    # 2. Google Trends
    print("\n2. 测试 Google Trends...")
    result = test_google_trends_fixed()
    all_results.append(result)
    print(f"   状态: {'✅ 成功' if result['success'] else '❌ 失败'}")
    time.sleep(2)
    
    # 3. Reddit
    print("\n3. 测试 Reddit...")
    result = test_reddit_fixed()
    all_results.append(result)
    print(f"   状态: {'✅ 成功' if result['success'] else '❌ 失败'}")
    
    print(f"\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 统计结果
    successful_crawls = sum(1 for r in all_results if r["success"])
    total_platforms = len(all_results)
    success_rate = (successful_crawls / total_platforms) * 100
    
    print(f"\n=== 测试摘要 ===")
    print(f"测试平台总数: {total_platforms}")
    print(f"成功爬取平台: {successful_crawls}")
    print(f"整体成功率: {success_rate:.1f}%")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_data = {
        "metadata": {
            "test_time": datetime.now().isoformat(),
            "platforms_tested": [r["platform"] for r in all_results],
            "successful_platforms": [r["platform"] for r in all_results if r["success"]],
            "test_type": "修复测试-禁用代理和SSL验证"
        },
        "test_results": all_results
    }
    
    os.makedirs("temp/test_results", exist_ok=True)
    raw_data_path = f"temp/test_results/data_pipeline_fixed_{timestamp}.json"
    
    with open(raw_data_path, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    
    print(f"原始数据已保存: {raw_data_path}")
    
    return all_results

if __name__ == "__main__":
    main()