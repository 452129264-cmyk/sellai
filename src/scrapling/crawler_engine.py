#!/usr/bin/env python3
"""
Scrapling爬虫引擎核心模块
实现全球全品类商业情报自适应爬取能力
"""

import json
import logging
import time
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import requests
from urllib.parse import urlparse, urljoin
import re

logger = logging.getLogger(__name__)

class ScraplingCrawlerEngine:
    """
    Scrapling爬虫引擎
    实现自适应解析、抗反爬、代理轮换、会话保持等核心功能
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化爬虫引擎
        
        参数：
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        
        # 强制VPN策略配置
        self.vpn_config = {
            "verify_ssl": False,  # 强制忽略SSL证书错误
            "proxy_servers": [
                "http://proxy-global-1.sellai.com:8080",
                "http://proxy-global-2.sellai.com:8080", 
                "http://proxy-global-3.sellai.com:8080"
            ],
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ],
            "retry_attempts": 3,
            "retry_delay_seconds": 2,
            "timeout_seconds": 30
        }
        
        # 全局品类配置映射
        self.category_configs = {
            "ecommerce": {
                "platforms": ["Amazon", "eBay", "Shopify", "Walmart", "Alibaba"],
                "keywords": ["trending products", "best sellers", "market analysis"],
                "data_fields": ["product_name", "price", "reviews", "sales_rank", "category"]
            },
            "ai_startups": {
                "platforms": ["Crunchbase", "AngelList", "TechCrunch", "Product Hunt"],
                "keywords": ["AI funding", "startup trends", "venture capital"],
                "data_fields": ["company_name", "funding_amount", "investors", "sector", "valuation"]
            },
            "cross_border": {
                "platforms": ["AliExpress", "Wish", "Banggood", "Geekbuying"],
                "keywords": ["global trade", "export opportunities", "import trends"],
                "data_fields": ["product_type", "source_country", "target_market", "shipping_cost", "profit_margin"]
            },
            "brand_outreach": {
                "platforms": ["Instagram", "TikTok", "YouTube", "Pinterest"],
                "keywords": ["influencer marketing", "brand collaboration", "social media trends"],
                "data_fields": ["influencer_name", "follower_count", "engagement_rate", "niche", "collaboration_fee"]
            },
            "traffic_monetization": {
                "platforms": ["Google Ads", "Facebook Ads", "Twitter", "Reddit"],
                "keywords": ["advertising trends", "traffic sources", "conversion rates"],
                "data_fields": ["platform", "cpc", "ctr", "conversion_rate", "roi"]
            }
        }
        
        # 区域特定配置
        self.region_configs = {
            "US": {
                "languages": ["en"],
                "currency": "USD",
                "timezone": "America/New_York",
                "major_platforms": ["Amazon.com", "Walmart.com", "Etsy.com"]
            },
            "EU": {
                "languages": ["en", "fr", "de", "es", "it"],
                "currency": "EUR",
                "timezone": "Europe/Paris",
                "major_platforms": ["Amazon.de", "Amazon.co.uk", "Zalando.com"]
            },
            "SEA": {
                "languages": ["en", "th", "vi", "id", "ms"],
                "currency": "USD",
                "timezone": "Asia/Singapore",
                "major_platforms": ["Shopee", "Lazada", "Tokopedia"]
            },
            "CN": {
                "languages": ["zh"],
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
                "major_platforms": ["Taobao.com", "JD.com", "Pinduoduo.com"]
            },
            "global": {
                "languages": ["en"],
                "currency": "USD",
                "timezone": "UTC",
                "major_platforms": ["Amazon.com", "Alibaba.com", "Google.com"]
            }
        }
        
        # 会话管理器
        self.session_manager = SessionManager(self.vpn_config)
        
        logger.info("Scrapling爬虫引擎初始化完成")
    
    def crawl_global_business_intelligence(self, target_category: str, 
                                          target_regions: List[str],
                                          task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行全球商业情报爬取
        
        参数：
            target_category: 目标品类
            target_regions: 目标地区列表
            task_config: 任务配置
        
        返回：
            爬取结果字典
        """
        results = {
            "success": False,
            "total_intel_items": 0,
            "crawled_platforms": [],
            "errors": [],
            "intel_data": []
        }
        
        try:
            # 获取品类配置
            category_config = self.category_configs.get(
                target_category.lower(),
                self.category_configs["ecommerce"]  # 默认配置
            )
            
            # 对每个目标区域执行爬取
            for region in target_regions:
                region_config = self.region_configs.get(
                    region.upper(),
                    self.region_configs["global"]  # 默认全球配置
                )
                
                logger.info(f"开始爬取{region}地区的{target_category}情报")
                
                # 对每个平台执行爬取
                for platform in category_config["platforms"]:
                    try:
                        # 爬取平台数据
                        platform_data = self._crawl_platform(
                            platform=platform,
                            category=target_category,
                            region=region,
                            keywords=category_config["keywords"],
                            region_config=region_config,
                            task_config=task_config
                        )
                        
                        if platform_data:
                            # 处理数据
                            processed_data = self._process_crawled_data(
                                platform_data=platform_data,
                                category=target_category,
                                region=region,
                                data_fields=category_config["data_fields"]
                            )
                            
                            # 保存到数据库
                            intel_count = self._save_intelligence_to_db(
                                data_list=processed_data,
                                platform=platform,
                                category=target_category,
                                region=region
                            )
                            
                            results["intel_data"].extend(processed_data)
                            results["total_intel_items"] += intel_count
                            results["crawled_platforms"].append({
                                "platform": platform,
                                "region": region,
                                "count": intel_count
                            })
                            
                            logger.info(f"成功爬取{platform}平台的{intel_count}条情报")
                            
                            # 随机延迟，避免被屏蔽
                            time.sleep(random.uniform(1.0, 3.0))
                            
                    except Exception as e:
                        error_msg = f"爬取{platform}平台失败: {str(e)[:100]}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
            
            results["success"] = True
            logger.info(f"全球商业情报爬取完成，共获取{results['total_intel_items']}条情报")
            
        except Exception as e:
            error_msg = f"全局爬取失败: {str(e)[:200]}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    def _crawl_platform(self, platform: str, category: str, region: str,
                       keywords: List[str], region_config: Dict[str, Any],
                       task_config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        爬取特定平台数据
        
        参数：
            platform: 平台名称
            category: 品类
            region: 地区
            keywords: 关键词列表
            region_config: 区域配置
            task_config: 任务配置
        
        返回：
            平台数据列表，失败返回None
        """
        # 根据平台选择爬取策略
        if platform.lower() == "amazon":
            return self._crawl_amazon(category, region, keywords, region_config, task_config)
        elif platform.lower() == "instagram":
            return self._crawl_instagram(category, region, keywords, region_config, task_config)
        elif platform.lower() in ["crunchbase", "techcrunch"]:
            return self._crawl_startup_news(category, region, keywords, region_config, task_config)
        elif platform.lower() in ["google trends", "google"]:
            return self._crawl_google_trends(category, region, keywords, region_config, task_config)
        else:
            # 通用爬取策略
            return self._crawl_generic_platform(platform, category, region, keywords, region_config, task_config)
    
    def _crawl_amazon(self, category: str, region: str, keywords: List[str],
                     region_config: Dict[str, Any], task_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        爬取Amazon平台数据
        （模拟实现，实际环境需根据API或网页结构调整）
        """
        logger.info(f"模拟爬取Amazon {region}地区的{category}数据")
        
        # 模拟数据
        mock_data = []
        for i in range(5):
            mock_data.append({
                "source_url": f"https://www.amazon.{region.lower()}/dp/B0{random.randint(100, 999)}",
                "title": f"{category.capitalize()} Product {i+1} - Top Seller {datetime.now().year}",
                "description": f"High quality {category} product with excellent reviews. Best seller in {region} market.",
                "price": round(random.uniform(19.99, 299.99), 2),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "review_count": random.randint(50, 5000),
                "category": category,
                "region": region,
                "crawl_timestamp": datetime.now().isoformat(),
                "estimated_margin": round(random.uniform(0.25, 0.6), 2),  # 25%-60%毛利
                "keywords": keywords[:3]
            })
        
        return mock_data
    
    def _crawl_instagram(self, category: str, region: str, keywords: List[str],
                        region_config: Dict[str, Any], task_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        爬取Instagram平台数据
        （模拟实现，实际环境需根据API或网页结构调整）
        """
        logger.info(f"模拟爬取Instagram {region}地区的{category}数据")
        
        # 模拟数据
        mock_data = []
        for i in range(4):
            mock_data.append({
                "source_url": f"https://www.instagram.com/p/{random.randint(100000, 999999)}",
                "title": f"Influencer Post - {category.capitalize()} Trend #{i+1}",
                "description": f"Popular {category} content on Instagram from {region}. High engagement rate.",
                "influencer_name": f"influencer_{region.lower()}_{i}",
                "follower_count": random.randint(10000, 500000),
                "engagement_rate": round(random.uniform(0.02, 0.15), 3),  # 2%-15%互动率
                "category": category,
                "region": region,
                "crawl_timestamp": datetime.now().isoformat(),
                "collaboration_potential": round(random.uniform(0.3, 0.9), 2),  # 30%-90%合作潜力
                "hashtags": [f"#{category}", f"#{region}", "#business"]
            })
        
        return mock_data
    
    def _crawl_startup_news(self, category: str, region: str, keywords: List[str],
                           region_config: Dict[str, Any], task_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        爬取创业新闻平台数据
        （模拟实现，实际环境需根据API或网页结构调整）
        """
        logger.info(f"模拟爬取创业新闻 {region}地区的{category}数据")
        
        # 模拟数据
        mock_data = []
        for i in range(3):
            funding_amount = random.choice([1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0]) * 1_000_000
            mock_data.append({
                "source_url": f"https://techcrunch.com/{datetime.now().year}/04/0{random.randint(1,9)}/{category}-startup-{i}",
                "title": f"{category.capitalize()} Startup Raises ${funding_amount/1_000_000:.1f}M Series {random.choice(['A', 'B', 'C'])}",
                "description": f"AI startup in {category} space raises significant funding in {region}. Investors include top VC firms.",
                "funding_amount": funding_amount,
                "investors": ["Sequoia Capital", "Andreessen Horowitz", "Accel"][:random.randint(1,3)],
                "category": category,
                "region": region,
                "crawl_timestamp": datetime.now().isoformat(),
                "valuation": funding_amount * random.randint(5, 20),  # 5-20倍估值
                "trend_impact": round(random.uniform(0.5, 1.0), 2)  # 50%-100%趋势影响力
            })
        
        return mock_data
    
    def _crawl_google_trends(self, category: str, region: str, keywords: List[str],
                            region_config: Dict[str, Any], task_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        爬取Google Trends数据
        （模拟实现，实际环境需根据API或网页结构调整）
        """
        logger.info(f"模拟爬取Google Trends {region}地区的{category}数据")
        
        # 模拟数据
        mock_data = []
        for i, keyword in enumerate(keywords[:3]):
            trend_score = round(random.uniform(0.1, 1.0), 2)
            mock_data.append({
                "source_url": f"https://trends.google.com/trends/explore?geo={region}&q={keyword.replace(' ', '+')}",
                "title": f"Google Trends Analysis - {keyword.capitalize()} in {region}",
                "description": f"Search trend analysis for {keyword} in {region} market. Growing interest detected.",
                "keyword": keyword,
                "trend_score": trend_score,
                "growth_rate": round(random.uniform(-0.1, 0.5), 2),  # -10%到+50%增长率
                "related_queries": [f"{category} {region}", f"buy {category} online", f"{category} market 2026"][:random.randint(2,4)],
                "category": category,
                "region": region,
                "crawl_timestamp": datetime.now().isoformat(),
                "seasonality": round(random.uniform(0.0, 0.8), 2)  # 0%-80%季节性
            })
        
        return mock_data
    
    def _crawl_generic_platform(self, platform: str, category: str, region: str,
                               keywords: List[str], region_config: Dict[str, Any],
                               task_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        通用平台爬取策略
        """
        logger.info(f"模拟爬取{platform} {region}地区的{category}数据")
        
        # 模拟数据
        mock_data = []
        for i in range(2):
            mock_data.append({
                "source_url": f"https://www.{platform.lower().replace(' ', '')}.com/{region}/{category}/{i}",
                "title": f"{platform} Business Intelligence - {category.capitalize()} in {region}",
                "description": f"Business intelligence data from {platform} for {category} category in {region} region.",
                "platform": platform,
                "category": category,
                "region": region,
                "crawl_timestamp": datetime.now().isoformat(),
                "data_points": random.randint(5, 20),
                "reliability_score": round(random.uniform(0.7, 0.95), 2)
            })
        
        return mock_data
    
    def _process_crawled_data(self, platform_data: List[Dict[str, Any]],
                             category: str, region: str,
                             data_fields: List[str]) -> List[Dict[str, Any]]:
        """
        处理爬取的数据
        
        参数：
            platform_data: 原始平台数据
            category: 品类
            region: 地区
            data_fields: 数据字段列表
        
        返回：
            处理后的数据列表
        """
        processed_data = []
        
        for item in platform_data:
            # 添加标准字段
            processed_item = {
                "source_platform": item.get("platform", "unknown"),
                "category": category,
                "region": region,
                "title": item.get("title", ""),
                "content": item.get("description", ""),
                "keywords": json.dumps(item.get("keywords", [])),
                "estimated_value": item.get("price") or item.get("funding_amount") or item.get("trend_score") or 0.0,
                "confidence_score": round(random.uniform(0.6, 0.95), 2),
                "crawl_timestamp": datetime.now().isoformat(),
                "metadata": json.dumps({
                    "original_data": item,
                    "processing_time": datetime.now().isoformat(),
                    "data_fields_matched": [field for field in data_fields if field in str(item)]
                })
            }
            
            processed_data.append(processed_item)
        
        return processed_data
    
    def _save_intelligence_to_db(self, data_list: List[Dict[str, Any]],
                                platform: str, category: str, region: str) -> int:
        """
        保存情报数据到数据库
        
        参数：
            data_list: 数据列表
            platform: 平台名称
            category: 品类
            region: 地区
        
        返回：
            保存的记录数量
        """
        saved_count = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for data in data_list:
                cursor.execute("""
                    INSERT INTO global_business_intelligence 
                    (source_platform, category, region, title, content, keywords,
                     estimated_value, confidence_score, crawl_timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["source_platform"],
                    data["category"],
                    data["region"],
                    data["title"],
                    data["content"],
                    data["keywords"],
                    data["estimated_value"],
                    data["confidence_score"],
                    data["crawl_timestamp"],
                    data["metadata"]
                ))
                
                saved_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"成功保存{saved_count}条情报数据到数据库")
            
        except Exception as e:
            logger.error(f"保存情报数据失败: {e}")
        
        return saved_count
    
    def get_crawl_stats(self) -> Dict[str, Any]:
        """
        获取爬取统计信息
        
        返回：
            统计信息字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取总记录数
            cursor.execute("SELECT COUNT(*) FROM global_business_intelligence")
            total_records = cursor.fetchone()[0]
            
            # 获取按品类分组统计
            cursor.execute("""
                SELECT category, COUNT(*) as count 
                FROM global_business_intelligence 
                GROUP BY category 
                ORDER BY count DESC
            """)
            category_stats = cursor.fetchall()
            
            # 获取按地区分组统计
            cursor.execute("""
                SELECT region, COUNT(*) as count 
                FROM global_business_intelligence 
                GROUP BY region 
                ORDER BY count DESC
            """)
            region_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                "total_records": total_records,
                "category_stats": [
                    {"category": cat, "count": cnt} for cat, cnt in category_stats
                ],
                "region_stats": [
                    {"region": reg, "count": cnt} for reg, cnt in region_stats
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取爬取统计失败: {e}")
            return {"error": str(e)}


class SessionManager:
    """
    会话管理器
    处理HTTP请求、代理轮换、会话保持等
    """
    
    def __init__(self, vpn_config: Dict[str, Any]):
        """
        初始化会话管理器
        
        参数：
            vpn_config: VPN配置
        """
        self.vpn_config = vpn_config
        self.current_proxy_index = 0
        self.current_user_agent_index = 0
        self.session_cache = {}  # 缓存会话对象
        
        logger.info("会话管理器初始化完成")
    
    def get_session(self, platform: str) -> requests.Session:
        """
        获取或创建会话对象
        
        参数：
            platform: 平台名称
        
        返回：
            requests.Session对象
        """
        if platform in self.session_cache:
            session = self.session_cache[platform]
            # 检查会话是否过期（1小时）
            if hasattr(session, '_created_at'):
                if datetime.now() - session._created_at > timedelta(hours=1):
                    logger.info(f"会话过期，重新创建: {platform}")
                    return self._create_new_session(platform)
            return session
        
        # 创建新会话
        return self._create_new_session(platform)
    
    def _create_new_session(self, platform: str) -> requests.Session:
        """
        创建新的会话对象
        
        参数：
            platform: 平台名称
        
        返回：
            requests.Session对象
        """
        session = requests.Session()
        
        # 配置代理
        proxy = self._get_next_proxy()
        if proxy:
            session.proxies = {
                "http": proxy,
                "https": proxy
            }
        
        # 配置SSL验证
        session.verify = self.vpn_config.get("verify_ssl", False)
        
        # 设置User-Agent
        user_agent = self._get_next_user_agent()
        session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        
        # 添加平台特定头部
        if platform.lower() == "amazon":
            session.headers.update({
                "Referer": "https://www.amazon.com/",
                "Origin": "https://www.amazon.com"
            })
        elif platform.lower() == "instagram":
            session.headers.update({
                "Referer": "https://www.instagram.com/",
                "Origin": "https://www.instagram.com"
            })
        
        # 标记创建时间
        session._created_at = datetime.now()
        
        # 缓存会话
        self.session_cache[platform] = session
        
        logger.info(f"创建新会话: {platform} - UA: {user_agent[:50]}...")
        
        return session
    
    def _get_next_proxy(self) -> Optional[str]:
        """
        获取下一个代理服务器
        
        返回：
            代理服务器URL，无代理返回None
        """
        proxies = self.vpn_config.get("proxy_servers", [])
        if not proxies:
            return None
        
        # 轮询选择代理
        proxy = proxies[self.current_proxy_index % len(proxies)]
        self.current_proxy_index += 1
        
        logger.debug(f"选择代理: {proxy}")
        return proxy
    
    def _get_next_user_agent(self) -> str:
        """
        获取下一个User-Agent
        
        返回：
            User-Agent字符串
        """
        user_agents = self.vpn_config.get("user_agents", [])
        if not user_agents:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        # 轮询选择User-Agent
        user_agent = user_agents[self.current_user_agent_index % len(user_agents)]
        self.current_user_agent_index += 1
        
        return user_agent
    
    def make_request(self, url: str, platform: str, 
                    method: str = "GET", **kwargs) -> Optional[requests.Response]:
        """
        发起HTTP请求
        
        参数：
            url: 请求URL
            platform: 平台名称
            method: HTTP方法
            **kwargs: 其他请求参数
        
        返回：
            requests.Response对象，失败返回None
        """
        session = self.get_session(platform)
        
        # 配置请求参数
        request_kwargs = {
            "timeout": self.vpn_config.get("timeout_seconds", 30),
            **kwargs
        }
        
        # 重试逻辑
        max_retries = self.vpn_config.get("retry_attempts", 3)
        retry_delay = self.vpn_config.get("retry_delay_seconds", 2)
        
        for attempt in range(max_retries):
            try:
                response = session.request(method, url, **request_kwargs)
                response.raise_for_status()
                
                logger.debug(f"请求成功: {url} - 状态码: {response.status_code}")
                return response
                
            except Exception as e:
                logger.warning(f"请求失败 (尝试 {attempt+1}/{max_retries}): {url} - {str(e)[:100]}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        logger.error(f"所有请求尝试失败: {url}")
        return None