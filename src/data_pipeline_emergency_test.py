#!/usr/bin/env python3
"""
数据管道紧急验证脚本
立即执行7个数据源（TikTok、Instagram、Amazon、Google Trends、Reddit、全球创业商机、绍兴&杭州政府补贴）的HTTP爬取验证
确保数据可稳定获取，统计成功率，提供问题诊断和优化建议
"""

import requests
import json
import time
import concurrent.futures
from datetime import datetime
import os
import sys
from typing import Dict, List, Any, Tuple
import socket
import ssl

def check_network_connectivity() -> Dict[str, Any]:
    """检查网络连接和SSL配置"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "network_checks": {},
        "ssl_issues": []
    }
    
    # 测试基本网络连接
    test_domains = [
        ("www.tiktok.com", 443),
        ("www.instagram.com", 443),
        ("www.amazon.com", 443),
        ("trends.google.com", 443),
        ("www.reddit.com", 443),
        ("www.entrepreneur.com", 443),
        ("www.shaoxing.gov.cn", 80)
    ]
    
    for domain, port in test_domains:
        try:
            sock = socket.create_connection((domain, port), timeout=10)
            sock.close()
            results["network_checks"][domain] = "连接成功"
        except Exception as e:
            results["network_checks"][domain] = f"连接失败: {str(e)}"
            if port == 443:
                results["ssl_issues"].append(f"{domain}: {str(e)}")
    
    return results

def make_request(url: str, headers: Dict[str, str] = None, 
                 params: Dict[str, str] = None, platform: str = "未知平台") -> Dict[str, Any]:
    """执行HTTP请求，返回标准化结果"""
    result = {
        "platform": platform,
        "url": url,
        "headers": headers or {},
        "params": params or {},
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "status_code": None,
        "response_time_ms": None,
        "response_size_bytes": None,
        "content_type": None,
        "data_sample": None,
        "error": None,
        "antibot_signs": []
    }
    
    try:
        start_time = time.time()
        
        # 添加默认User-Agent如果未提供
        request_headers = headers.copy() if headers else {}
        if 'User-Agent' not in request_headers:
            request_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        response = requests.get(url, headers=request_headers, params=params, timeout=30)
        response_time = (time.time() - start_time) * 1000
        
        result["status_code"] = response.status_code
        result["response_time_ms"] = response_time
        result["response_size_bytes"] = len(response.content)
        result["content_type"] = response.headers.get('content-type', '')
        
        # 检查反爬迹象
        if response.status_code == 403:
            result["antibot_signs"].append("HTTP 403 - 访问被拒绝")
        elif response.status_code == 429:
            result["antibot_signs"].append("HTTP 429 - 请求过多")
        elif response.status_code == 503:
            result["antibot_signs"].append("HTTP 503 - 服务不可用")
        
        if "captcha" in response.text.lower():
            result["antibot_signs"].append("检测到验证码")
        if "access denied" in response.text.lower():
            result["antibot_signs"].append("访问被拒绝")
        if "robot" in response.text.lower() or "bot" in response.text.lower():
            result["antibot_signs"].append("被识别为机器人")
        
        response.raise_for_status()
        
        # 处理响应数据
        content_type = response.headers.get('content-type', '').lower()
        
        if 'application/json' in content_type:
            data = response.json()
            result["data_sample"] = str(data)[:500]  # 只取前500字符作为样本
        else:
            # 对于HTML响应，取前1000字符
            result["data_sample"] = response.text[:1000]
        
        result["success"] = True
        
    except requests.exceptions.SSLError as e:
        result["error"] = f"SSL错误: {str(e)}"
        result["antibot_signs"].append("SSL握手失败")
    except requests.exceptions.ProxyError as e:
        result["error"] = f"代理错误: {str(e)}"
        result["antibot_signs"].append("代理连接失败")
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"连接错误: {str(e)}"
        result["antibot_signs"].append("网络连接失败")
    except requests.exceptions.Timeout as e:
        result["error"] = f"超时错误: {str(e)}"
        result["antibot_signs"].append("请求超时")
    except requests.exceptions.RequestException as e:
        result["error"] = f"请求异常: {str(e)}"
    except Exception as e:
        result["error"] = f"未知错误: {str(e)}"
    
    return result

def test_tiktok() -> Dict[str, Any]:
    """测试TikTok数据源"""
    url = "https://www.tiktok.com/api/trending/item/list/"
    params = {
        "region": "US",
        "count": "5",
        "from_page": "trending",
        "aid": "1988"
    }
    headers = {
        "Referer": "https://www.tiktok.com/trending",
        "Accept": "application/json, text/plain, */*"
    }
    return make_request(url, headers, params, "TikTok")

def test_instagram() -> Dict[str, Any]:
    """测试Instagram数据源"""
    url = "https://www.instagram.com/explore/tags/entrepreneur/"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
    }
    return make_request(url, headers, None, "Instagram")

def test_amazon() -> Dict[str, Any]:
    """测试Amazon数据源"""
    url = "https://www.amazon.com/s"
    params = {
        "k": "wireless+earbuds",
        "i": "electronics",
        "s": "price-desc-rank",
        "page": "1",
        "qid": str(int(time.time())),
        "ref": "sr_pg_1"
    }
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    return make_request(url, headers, params, "Amazon")

def test_google_trends() -> Dict[str, Any]:
    """测试Google Trends数据源"""
    url = "https://trends.google.com/trends/api/explore"
    params = {
        "hl": "en-US",
        "tz": "-480",
        "req": json.dumps({
            "comparisonItem": [{
                "keyword": "dropshipping",
                "geo": "US",
                "time": "now 7-d"
            }],
            "category": 0,
            "property": ""
        })
    }
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9"
    }
    return make_request(url, headers, params, "Google Trends")

def test_reddit() -> Dict[str, Any]:
    """测试Reddit数据源"""
    url = "https://www.reddit.com/r/Entrepreneur/hot.json"
    params = {
        "limit": "5",
        "t": "day"
    }
    headers = {
        "Accept": "application/json"
    }
    return make_request(url, headers, params, "Reddit")

def test_entrepreneur() -> Dict[str, Any]:
    """测试全球创业商机数据源 (Entrepreneur.com)"""
    url = "https://www.entrepreneur.com/api/v1/articles"
    params = {
        "category": "business-ideas",
        "limit": "5",
        "page": "1",
        "sort": "latest"
    }
    return make_request(url, None, params, "Entrepreneur.com")

def test_shaoxing_gov() -> Dict[str, Any]:
    """测试绍兴政府补贴数据源"""
    url = "http://www.shaoxing.gov.cn/col/col1229452808/index.html"
    return make_request(url, None, None, "绍兴政府补贴")

def run_all_tests() -> Dict[str, Any]:
    """并行执行所有测试"""
    print("=== 数据管道紧急验证 ===\n")
    print("1. 检查网络环境...")
    network_check = check_network_connectivity()
    
    print("2. 执行7个数据源并行测试...")
    test_functions = [
        test_tiktok,
        test_instagram,
        test_amazon,
        test_google_trends,
        test_reddit,
        test_entrepreneur,
        test_shaoxing_gov
    ]
    
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
        future_to_test = {executor.submit(func): func.__name__ for func in test_functions}
        
        for future in concurrent.futures.as_completed(future_to_test):
            test_name = future_to_test[future]
            try:
                result = future.result()
                all_results.append(result)
                status = "✓" if result["success"] else "✗"
                print(f"  {status} {result['platform']}: {result['status_code'] or '错误'} - {result.get('error', '成功')}")
            except Exception as e:
                print(f"  ✗ {test_name}: 执行异常 - {str(e)}")
    
    # 计算统计信息
    successful_tests = [r for r in all_results if r["success"]]
    total_tests = len(all_results)
    success_rate = (len(successful_tests) / total_tests * 100) if total_tests > 0 else 0
    
    # 收集问题诊断
    failed_tests = [r for r in all_results if not r["success"]]
    problem_analysis = []
    for test in failed_tests:
        analysis = {
            "platform": test["platform"],
            "error": test.get("error", "未知错误"),
            "antibot_signs": test.get("antibot_signs", []),
            "suggested_solutions": []
        }
        
        # 根据错误类型建议解决方案
        error = test.get("error", "")
        if "SSL" in error:
            analysis["suggested_solutions"].append("使用requests的verify=False参数绕过SSL验证（仅测试环境）")
            analysis["suggested_solutions"].append("更新系统根证书")
        elif "Proxy" in error:
            analysis["suggested_solutions"].append("检查代理配置或尝试直接连接")
        elif "Connection" in error:
            analysis["suggested_solutions"].append("检查网络连接和防火墙设置")
        elif "Timeout" in error:
            analysis["suggested_solutions"].append("增加超时时间或重试机制")
        elif "403" in error or "429" in error:
            analysis["suggested_solutions"].append("添加请求间隔（3-5秒）和User-Agent轮换")
            analysis["suggested_solutions"].append("可能需要登录Cookie或官方API权限")
        
        problem_analysis.append(analysis)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "network_check": network_check,
        "test_results": all_results,
        "statistics": {
            "total_platforms": total_tests,
            "successful_platforms": len(successful_tests),
            "success_rate_percent": success_rate,
            "target_success_rate": 70.0,
            "meets_target": success_rate >= 70.0
        },
        "problem_analysis": problem_analysis,
        "platform_success_map": {r["platform"]: r["success"] for r in all_results}
    }

def generate_report(results: Dict[str, Any]) -> str:
    """生成详细的验证报告"""
    stats = results["statistics"]
    problem_analysis = results["problem_analysis"]
    
    report = f"""# 数据管道紧急验证报告

**验证时间**: {results['timestamp']}
**测试平台**: 7个数据源
**测试目标**: 确保数据可稳定获取，为后续压力测试准备

## 执行摘要

| 指标 | 数值 |
|------|------|
| 测试平台总数 | {stats['total_platforms']} |
| 成功爬取平台 | {stats['successful_platforms']} |
| 整体成功率 | {stats['success_rate_percent']:.1f}% |
| 目标成功率 | 70% |
| **是否达标** | **{'✓ 达标' if stats['meets_target'] else '✗ 未达标'}** |

## 分平台测试详情

"""
    
    for test in results["test_results"]:
        status = "✓" if test["success"] else "✗"
        status_code = test.get("status_code", "N/A")
        response_time = test.get("response_time_ms", "N/A")
        error = test.get("error", "无")
        
        report += f"### {test['platform']} {status}\n\n"
        report += f"- **URL**: {test['url'][:100]}...\n"
        report += f"- **状态码**: {status_code}\n"
        report += f"- **响应时间**: {response_time}ms\n"
        report += f"- **响应大小**: {test.get('response_size_bytes', 'N/A')}字节\n"
        report += f"- **内容类型**: {test.get('content_type', 'N/A')}\n"
        
        if test.get("antibot_signs"):
            report += f"- **反爬迹象**: {', '.join(test['antibot_signs'])}\n"
        
        if error and error != "无":
            report += f"- **错误信息**: {error}\n"
        
        data_sample = test.get("data_sample")
        if data_sample:
            report += f"- **数据样本**: {data_sample[:200]}...\n"
        
        report += "\n"
    
    # 问题诊断与优化建议
    report += "## 问题诊断与优化建议\n\n"
    
    if not problem_analysis:
        report += "所有平台测试成功，无需优化。\n\n"
    else:
        report += "### 失败平台详细分析\n\n"
        for analysis in problem_analysis:
            report += f"#### {analysis['platform']}\n\n"
            report += f"- **错误类型**: {analysis['error']}\n"
            if analysis['antibot_signs']:
                report += f"- **反爬检测**: {', '.join(analysis['antibot_signs'])}\n"
            report += "- **建议解决方案**:\n"
            for solution in analysis['suggested_solutions']:
                report += f"  - {solution}\n"
            report += "\n"
    
    # 网络环境检查结果
    report += "## 网络环境检查结果\n\n"
    for domain, status in results["network_check"]["network_checks"].items():
        report += f"- **{domain}**: {status}\n"
    
    if results["network_check"]["ssl_issues"]:
        report += "\n### SSL相关问题\n\n"
        for issue in results["network_check"]["ssl_issues"]:
            report += f"- {issue}\n"
    
    # 总体建议
    report += "\n## 总体优化建议\n\n"
    
    if stats["meets_target"]:
        report += "1. **数据管道稳定性达标**，可继续进行压力测试\n"
        report += "2. 针对仍然失败的平台，按上述建议逐一优化\n"
        report += "3. 建议增加监控机制，实时跟踪各平台爬取状态\n"
    else:
        report += "1. **数据管道稳定性未达标**，需优先解决以下问题：\n"
        report += "   - 网络连接问题（检查代理和防火墙）\n"
        report += "   - SSL证书问题（更新根证书或使用验证绕过）\n"
        report += "   - 反爬机制（添加请求间隔和User-Agent轮换）\n"
        report += "2. 优先保障核心数据源（Amazon、Google Trends）稳定性\n"
        report += "3. 建议配置备用数据源或使用官方API\n"
    
    report += "\n## 下一步行动\n\n"
    report += "1. 根据问题诊断结果，优化相应数据源的爬取配置\n"
    report += "2. 重新执行验证测试，确保成功率≥70%\n"
    report += "3. 成功后立即触发全链路压力测试（任务43）\n"
    
    report += f"\n---\n\n*报告生成时间: {datetime.now().isoformat()}*\n*验证批次ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}*\n"
    
    return report

def save_results(results: Dict[str, Any], report_content: str):
    """保存测试结果和报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 创建目录
    os.makedirs("temp/emergency_test", exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    
    # 保存原始结果
    raw_data_path = f"temp/emergency_test/data_pipeline_test_{timestamp}.json"
    with open(raw_data_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n原始测试数据已保存: {raw_data_path}")
    
    # 保存报告
    report_path = f"docs/数据管道紧急验证报告.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"详细报告已保存: {report_path}")
    
    return raw_data_path, report_path

def main():
    """主函数"""
    print("开始数据管道紧急验证...\n")
    
    # 执行所有测试
    results = run_all_tests()
    
    # 生成报告
    report_content = generate_report(results)
    
    # 保存结果
    raw_path, report_path = save_results(results, report_content)
    
    # 打印关键结论
    stats = results["statistics"]
    print(f"\n=== 验证完成 ===\n")
    print(f"整体成功率: {stats['success_rate_percent']:.1f}%")
    print(f"目标成功率: 70%")
    print(f"是否达标: {'✓ 达标' if stats['meets_target'] else '✗ 未达标'}")
    
    if stats["meets_target"]:
        print("\n✅ 数据管道稳定性达标，可以继续进行压力测试。")
    else:
        print("\n❌ 数据管道稳定性未达标，需根据报告建议进行优化。")
    
    return results

if __name__ == "__main__":
    main()