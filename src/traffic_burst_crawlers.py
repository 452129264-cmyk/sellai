#!/usr/bin/env python3
"""
流量爆破军团 - 穿搭垂直数据源爬虫配置
专门抓取美区穿搭热搜、谷歌精准长尾词、TikTok爆款标签三类数据源
集成现有无限分身爬虫框架，复用防封策略和Cookie管理
"""

import requests
import json
import time
from datetime import datetime, timedelta
import os
import sys
from urllib.parse import urlencode, quote
import re
from typing import Dict, List, Optional, Tuple, Any

# 导入现有Cookie管理
try:
    from cookie_manager import CookieManager
except ImportError:
    # 如果无法导入，提供简化版本
    class CookieManager:
        def __init__(self, storage_path="memory/cookies.json"):
            self.storage_path = storage_path
            self.cookies = {}
            
        def get_cookie(self, platform: str, account_id: str = "default") -> Optional[Dict[str, str]]:
            return None
            
        def save_cookie(self, platform: str, cookies: Dict[str, str], account_id: str = "default", expires_hours: int = 24):
            pass

class TrafficBurstCrawler:
    """流量爆破爬虫主类"""
    
    def __init__(self, cookie_manager: Optional[CookieManager] = None):
        self.cookie_manager = cookie_manager or CookieManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def make_request(self, url: str, headers: Optional[Dict] = None, 
                     params: Optional[Dict] = None, method: str = "GET",
                     platform: str = "unknown", use_cookie: bool = True,
                     timeout: int = 30, proxy_control: str = "auto", verify_ssl: bool = True) -> Dict[str, Any]:
        """
        执行HTTP请求，集成防封策略
        返回标准化结果字典
        """
        result = {
            "platform": platform,
            "url": url,
            "method": method,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "status_code": None,
            "response_time_ms": None,
            "data": None,
            "error": None,
            "antibot_issues": [],
            "data_metrics": {
                "trend_count": 0,
                "keyword_count": 0,
                "hashtag_count": 0,
                "volume_estimate": 0
            }
        }
        
        try:
            # 应用平台特定Cookie
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)
                
            if use_cookie:
                cookie_data = self.cookie_manager.get_cookie(platform)
                if cookie_data and 'cookies' in cookie_data:
                    # 将Cookie字典转换为requests可用的格式
                    for key, value in cookie_data['cookies'].items():
                        self.session.cookies.set(key, value)
            
            # 随机延迟避免请求过快
            time.sleep(3 + (hash(platform) % 3))  # 3-6秒延迟
            
            start_time = time.time()
            
            
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
                                            json=params, **request_kwargs)
            
            response_time = (time.time() - start_time) * 1000
            
            result["status_code"] = response.status_code
            result["response_time_ms"] = response_time
            
            # 检查反爬迹象
            if response.status_code == 403 or response.status_code == 429:
                result["antibot_issues"].append(f"HTTP {response.status_code} - 访问被拒绝")
            elif "captcha" in response.text.lower():
                result["antibot_issues"].append("检测到验证码")
            elif "access denied" in response.text.lower():
                result["antibot_issues"].append("访问被拒绝")
            elif "robot" in response.text.lower() or "bot" in response.text.lower():
                result["antibot_issues"].append("被识别为机器人")
            
            response.raise_for_status()
            
            # 处理响应数据
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type:
                data = response.json()
            else:
                data = response.text
            
            result["success"] = True
            result["data"] = data
            
        except requests.exceptions.RequestException as e:
            result["error"] = str(e)
            result["antibot_issues"].append(f"请求异常: {str(e)}")
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def crawl_tiktok_fashion_trends(self, region: str = "US") -> Dict[str, Any]:
        """
        抓取TikTok时尚趋势标签
        返回热门标签、浏览量、参与度等数据
        """
        # TikTok趋势API（可能需要登录）
        url = "https://www.tiktok.com/api/trending/hashtag/list/"
        headers = {
            "Referer": f"https://www.tiktok.com/tag/fashion",
            "Accept": "application/json, text/plain, */*",
        }
        params = {
            "region": region,
            "category": "fashion",
            "count": "20",
            "language": "en"
        }
        
        result = self.make_request(url, headers, params, platform="TikTok_Fashion")
        
        if result["success"] and result["data"]:
            try:
                data = result["data"]
                # 解析TikTok响应，提取标签数据
                hashtags = []
                if isinstance(data, dict) and 'hashtag_list' in data:
                    for item in data['hashtag_list']:
                        hashtags.append({
                            "hashtag": item.get('hashtag_name', '').strip('#'),
                            "views": item.get('view_count', 0),
                            "videos": item.get('video_count', 0),
                            "trend_score": item.get('score', 0)
                        })
                elif isinstance(data, str):
                    # 使用正则表达式从HTML中提取趋势标签
                    pattern = r'\"hashtagName\":\"([^\"]+)\".*?\"viewCount\":(\d+)'
                    matches = re.findall(pattern, data)
                    for match in matches:
                        hashtags.append({
                            "hashtag": match[0],
                            "views": int(match[1]) if match[1].isdigit() else 0,
                            "videos": 0,
                            "trend_score": 0
                        })
                
                result["data_metrics"]["hashtag_count"] = len(hashtags)
                result["data_metrics"]["volume_estimate"] = sum(h.get("views", 0) for h in hashtags)
                result["parsed_data"] = hashtags
                
            except Exception as e:
                result["error"] = f"解析失败: {str(e)}"
                result["parsed_data"] = []
        
        return result
    
    def crawl_instagram_fashion_hashtags(self) -> Dict[str, Any]:
        """
        抓取Instagram时尚相关热门标签
        使用公开页面或GraphQL端点
        """
        # Instagram公开标签页面
        url = "https://www.instagram.com/explore/tags/fashion/"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        }
        
        result = self.make_request(url, headers, platform="Instagram_Fashion")
        
        if result["success"] and result["data"]:
            try:
                html_content = result["data"]
                hashtags = []
                
                # 提取页面中的相关标签
                # Instagram在meta标签或脚本中嵌入数据
                pattern = r'\"hashtag\":\{[^}]*\"name\":\"([^\"]+)\"[^}]*\"media_count\":(\d+)'
                matches = re.findall(pattern, html_content)
                
                for match in matches:
                    hashtags.append({
                        "hashtag": match[0],
                        "posts": int(match[1]) if match[1].isdigit() else 0,
                        "platform": "Instagram"
                    })
                
                # 如果没有找到，尝试提取常见时尚标签
                if not hashtags:
                    fashion_keywords = ["ootd", "fashion", "style", "outfit", "look", "trend"]
                    # 从HTML中提取所有标签
                    all_hashtags = re.findall(r'#([a-zA-Z0-9_]+)', html_content)
                    for tag in all_hashtags:
                        if any(kw in tag.lower() for kw in fashion_keywords):
                            hashtags.append({
                                "hashtag": tag,
                                "posts": 1000,  # 估计值
                                "platform": "Instagram"
                            })
                        if len(hashtags) >= 15:
                            break
                
                result["data_metrics"]["hashtag_count"] = len(hashtags)
                result["data_metrics"]["volume_estimate"] = sum(h.get("posts", 0) for h in hashtags)
                result["parsed_data"] = hashtags
                
            except Exception as e:
                result["error"] = f"解析失败: {str(e)}"
                result["parsed_data"] = []
        
        return result
    
    def crawl_google_trends_longtail(self, base_keywords: List[str] = None) -> Dict[str, Any]:
        """
        抓取谷歌趋势相关长尾关键词
        基于基础关键词扩展相关搜索词
        """
        if base_keywords is None:
            base_keywords = ["denim jacket", "vintage outfit", "fashion trends"]
        
        all_keywords = []
        
        for keyword in base_keywords:
            # 模拟谷歌相关搜索API
            url = "https://suggestqueries.google.com/complete/search"
            params = {
                "client": "chrome",
                "q": keyword,
                "hl": "en",
                "gl": "us"
            }
            
            result = self.make_request(url, params=params, platform="Google_Trends")
            
            if result["success"] and result["data"]:
                try:
                    if isinstance(result["data"], list) and len(result["data"]) > 1:
                        suggestions = result["data"][1]
                        for suggestion in suggestions:
                            if isinstance(suggestion, str) and suggestion.strip():
                                all_keywords.append({
                                    "keyword": suggestion.strip(),
                                    "base_keyword": keyword,
                                    "search_volume": 1000,  # 估计值
                                    "competition": "medium"
                                })
                except Exception as e:
                    # 如果解析失败，添加基础关键词
                    all_keywords.append({
                        "keyword": keyword,
                        "base_keyword": keyword,
                        "search_volume": 5000,
                        "competition": "high"
                    })
            
            time.sleep(2)  # 避免请求过快
        
        # 去重
        seen = set()
        unique_keywords = []
        for kw in all_keywords:
            key = kw["keyword"].lower()
            if key not in seen:
                seen.add(key)
                unique_keywords.append(kw)
        
        return {
            "success": len(unique_keywords) > 0,
            "platform": "Google_Trends_Longtail",
            "timestamp": datetime.now().isoformat(),
            "data_metrics": {
                "keyword_count": len(unique_keywords),
                "volume_estimate": sum(k.get("search_volume", 0) for k in unique_keywords)
            },
            "parsed_data": unique_keywords
        }
    
    def crawl_pinterest_fashion(self) -> Dict[str, Any]:
        """
        抓取Pinterest时尚趋势
        返回热门关键词和趋势主题
        """
        # Pinterest趋势API端点
        url = "https://www.pinterest.com/resource/TopicFeedResource/get/"
        headers = {
            "Referer": "https://www.pinterest.com/today/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        params = {
            "source_url": "/today/",
            "data": json.dumps({
                "options": {
                    "add_vase": False,
                    "category": "fashion",
                    "filter_stories": False,
                    "page_size": 20,
                    "sort": "popular"
                },
                "context": {}
            })
        }
        
        result = self.make_request(url, headers, params, platform="Pinterest_Fashion", method="POST")
        
        if result["success"] and result["data"]:
            try:
                data = result["data"]
                trends = []
                
                if isinstance(data, dict) and 'resource_response' in data:
                    items = data['resource_response'].get('data', [])
                    for item in items:
                        title = item.get('title', '')
                        pins = item.get('pin_count', 0)
                        if title:
                            trends.append({
                                "trend": title,
                                "pins": pins,
                                "platform": "Pinterest"
                            })
                
                result["data_metrics"]["trend_count"] = len(trends)
                result["data_metrics"]["volume_estimate"] = sum(t.get("pins", 0) for t in trends)
                result["parsed_data"] = trends
                
            except Exception as e:
                result["error"] = f"解析失败: {str(e)}"
                result["parsed_data"] = []
        
        return result
    
    def crawl_all_sources(self) -> Dict[str, Any]:
        """
        抓取所有三类数据源，返回整合结果
        """
        print("开始抓取流量爆破数据源...")
        
        all_results = {
            "tiktok_fashion": self.crawl_tiktok_fashion_trends(),
            "instagram_fashion": self.crawl_instagram_fashion_hashtags(),
            "google_longtail": self.crawl_google_trends_longtail(["denim jacket", "vintage fashion", "outfit ideas"]),
            "pinterest_fashion": self.crawl_pinterest_fashion(),
            "timestamp": datetime.now().isoformat(),
            "total_metrics": {
                "trends_count": 0,
                "keywords_count": 0,
                "hashtags_count": 0,
                "total_volume": 0
            }
        }
        
        # 汇总指标
        for key in ["tiktok_fashion", "instagram_fashion", "google_longtail", "pinterest_fashion"]:
            if key in all_results and isinstance(all_results[key], dict):
                metrics = all_results[key].get("data_metrics", {})
                all_results["total_metrics"]["trends_count"] += metrics.get("trend_count", 0)
                all_results["total_metrics"]["keywords_count"] += metrics.get("keyword_count", 0)
                all_results["total_metrics"]["hashtags_count"] += metrics.get("hashtag_count", 0)
                all_results["total_metrics"]["total_volume"] += metrics.get("volume_estimate", 0)
        
        print(f"抓取完成: {all_results['total_metrics']['trends_count']}趋势, "
              f"{all_results['total_metrics']['keywords_count']}关键词, "
              f"{all_results['total_metrics']['hashtags_count']}标签")
        
        return all_results
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        保存抓取结果到文件
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/traffic_burst_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存到: {filename}")
        return filename


def main():
    """主函数：执行完整抓取流程"""
    print("=== 流量爆破军团 - 数据源抓取测试 ===\n")
    
    crawler = TrafficBurstCrawler()
    
    # 抓取所有数据源
    results = crawler.crawl_all_sources()
    
    # 保存结果
    saved_path = crawler.save_results(results)
    
    # 打印摘要
    print("\n=== 抓取摘要 ===")
    for key, result in results.items():
        if key not in ["timestamp", "total_metrics"] and isinstance(result, dict):
            status = "✓" if result.get("success") else "✗"
            metrics = result.get("data_metrics", {})
            print(f"{key}: {status} - "
                  f"趋势: {metrics.get('trend_count', 0)}, "
                  f"关键词: {metrics.get('keyword_count', 0)}, "
                  f"标签: {metrics.get('hashtag_count', 0)}")
    
    print(f"\n总计: {results['total_metrics']['trends_count']}趋势, "
          f"{results['total_metrics']['keywords_count']}关键词, "
          f"{results['total_metrics']['hashtags_count']}标签, "
          f"总预估流量: {results['total_metrics']['total_volume']:,}")
    
    print(f"\n详细结果保存于: {saved_path}")
    
    return results


if __name__ == "__main__":
    main()