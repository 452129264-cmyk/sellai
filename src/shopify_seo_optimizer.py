#!/usr/bin/env python3
"""
Shopify独立站SEO优化引擎
全站页面扫描与SEO优化建议生成
集成流量爆破数据源，为产品页面、集合页面、博客页面提供标题、描述、ALT文本优化
"""

import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import os
from urllib.parse import urlparse, urljoin
import requests

class ShopifySEOOptimizer:
    """Shopify SEO优化引擎主类"""
    
    def __init__(self, shop_domain: str = None, access_token: str = None, 
                 api_version: str = "2024-01"):
        """
        初始化Shopify SEO优化引擎
        
        Args:
            shop_domain: Shopify店铺域名（如your-store.myshopify.com）
            access_token: Shopify Admin API访问令牌
            api_version: Shopify API版本
        """
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{shop_domain}/admin/api/{api_version}" if shop_domain else None
        self.session = requests.Session()
        
        if access_token:
            self.session.headers.update({
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json"
            })
        
        # SEO优化配置
        self.seo_config = {
            "title_length": {
                "optimal": 50,
                "max": 60
            },
            "description_length": {
                "optimal": 150,
                "max": 160
            },
            "alt_text_length": {
                "optimal": 125,
                "max": 125
            },
            "keyword_density": {
                "primary": 0.015,  # 1.5%
                "secondary": 0.008  # 0.8%
            },
            "stop_words": ["a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"]
        }
        
        # 缓存抓取的流量数据
        self.traffic_data = {
            "trends": [],
            "keywords": [],
            "hashtags": []
        }
    
    def load_traffic_data(self, data_file: Optional[str] = None) -> bool:
        """
        加载流量爆破数据源结果
        可以从文件加载，或从爬虫直接获取
        """
        if data_file and os.path.exists(data_file):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 解析不同数据源
                for source in ["tiktok_fashion", "instagram_fashion", "google_longtail", "pinterest_fashion"]:
                    if source in data and isinstance(data[source], dict):
                        parsed = data[source].get("parsed_data", [])
                        if parsed:
                            if source == "tiktok_fashion" or source == "instagram_fashion":
                                self.traffic_data["hashtags"].extend(parsed)
                            elif source == "google_longtail":
                                self.traffic_data["keywords"].extend(parsed)
                            elif source == "pinterest_fashion":
                                self.traffic_data["trends"].extend(parsed)
                
                print(f"已加载流量数据: {len(self.traffic_data['keywords'])}关键词, "
                      f"{len(self.traffic_data['hashtags'])}标签, "
                      f"{len(self.traffic_data['trends'])}趋势")
                return True
                
            except Exception as e:
                print(f"加载流量数据失败: {e}")
                return False
        
        # 如果没有文件，使用示例数据
        self.load_example_traffic_data()
        return True
    
    def load_example_traffic_data(self):
        """加载示例流量数据用于测试"""
        print("使用示例流量数据进行测试...")
        
        # 示例关键词数据
        self.traffic_data["keywords"] = [
            {"keyword": "vintage denim jacket", "search_volume": 5400, "competition": "medium"},
            {"keyword": "distressed jeans outfit", "search_volume": 3200, "competition": "low"},
            {"keyword": "retro fashion trends 2024", "search_volume": 8900, "competition": "high"},
            {"keyword": "men's casual outfit ideas", "search_volume": 12000, "competition": "high"},
            {"keyword": "oversized denim jacket styling", "search_volume": 2800, "competition": "medium"},
            {"keyword": "how to wear denim jacket", "search_volume": 4100, "competition": "medium"},
            {"keyword": "american vintage fashion", "search_volume": 3600, "competition": "low"},
            {"keyword": "streetwear outfit inspiration", "search_volume": 7500, "competition": "high"},
            {"keyword": "best denim jackets for men", "search_volume": 2900, "competition": "medium"},
            {"keyword": "casual weekend outfits", "search_volume": 8300, "competition": "high"}
        ]
        
        # 示例标签数据
        self.traffic_data["hashtags"] = [
            {"hashtag": "denimjacket", "views": 35000000, "platform": "TikTok"},
            {"hashtag": "vintagefashion", "views": 28000000, "platform": "TikTok"},
            {"hashtag": "outfitideas", "views": 42000000, "platform": "Instagram"},
            {"hashtag": "streetstyle", "views": 31000000, "platform": "Instagram"},
            {"hashtag": "fashiontrends", "views": 25000000, "platform": "TikTok"},
            {"hashtag": "mensfashion", "views": 19000000, "platform": "Instagram"},
            {"hashtag": "ootd", "views": 68000000, "platform": "Instagram"},
            {"hashtag": "styleinspiration", "views": 22000000, "platform": "TikTok"}
        ]
        
        # 示例趋势数据
        self.traffic_data["trends"] = [
            {"trend": "Y2K fashion revival", "pins": 150000, "platform": "Pinterest"},
            {"trend": "Sustainable denim", "pins": 89000, "platform": "Pinterest"},
            {"trend": "Gender-neutral fashion", "pins": 112000, "platform": "Pinterest"},
            {"trend": "Minimalist wardrobe", "pins": 210000, "platform": "Pinterest"}
        ]
    
    def scan_shopify_store(self) -> Dict[str, Any]:
        """
        扫描Shopify店铺所有页面
        包括产品、集合、博客文章等
        """
        if not self.base_url or not self.access_token:
            print("未配置Shopify API，使用模拟数据")
            return self.scan_mock_store()
        
        try:
            store_data = {
                "products": [],
                "collections": [],
                "articles": [],
                "pages": [],
                "scan_time": datetime.now().isoformat(),
                "shop_domain": self.shop_domain
            }
            
            # 获取产品列表
            print("扫描产品页面...")
            products = self._fetch_paginated("/products.json", "products")
            store_data["products"] = products
            
            # 获取集合列表
            print("扫描集合页面...")
            collections = self._fetch_paginated("/collections.json", "collections")
            store_data["collections"] = collections
            
            # 获取博客文章（需要先获取博客列表）
            print("扫描博客文章...")
            blogs = self._fetch_paginated("/blogs.json", "blogs")
            
            for blog in blogs:
                blog_id = blog.get("id")
                articles = self._fetch_paginated(f"/blogs/{blog_id}/articles.json", "articles")
                store_data["articles"].extend(articles)
            
            # 获取页面
            print("扫描静态页面...")
            pages = self._fetch_paginated("/pages.json", "pages")
            store_data["pages"] = pages
            
            print(f"扫描完成: {len(products)}产品, {len(collections)}集合, "
                  f"{len(store_data['articles'])}文章, {len(pages)}页面")
            
            return store_data
            
        except Exception as e:
            print(f"扫描Shopify店铺失败: {e}")
            return self.scan_mock_store()
    
    def scan_mock_store(self) -> Dict[str, Any]:
        """模拟扫描店铺，用于测试"""
        print("使用模拟店铺数据进行测试...")
        
        # 示例产品数据（750g美式复古牛仔外套）
        mock_products = [
            {
                "id": 123456789,
                "title": "750g American Vintage Denim Jacket",
                "handle": "750g-american-vintage-denim-jacket",
                "body_html": "<p>Heavyweight 750g denim jacket with vintage wash. Made from 100% cotton, featuring distressed details and classic button front.</p>",
                "vendor": "Vintage Denim Co.",
                "product_type": "Jacket",
                "tags": "denim, jacket, vintage, american, heavyweight, 750g",
                "images": [
                    {
                        "id": 987654321,
                        "src": "https://cdn.shopify.com/s/files/1/1234/5678/products/denim-jacket-front.jpg",
                        "alt": None
                    },
                    {
                        "id": 987654322,
                        "src": "https://cdn.shopify.com/s/files/1/1234/5678/products/denim-jacket-back.jpg",
                        "alt": None
                    }
                ],
                "variants": [
                    {
                        "id": 234567890,
                        "title": "S",
                        "price": "89.99",
                        "sku": "DJ-750G-S"
                    },
                    {
                        "id": 234567891,
                        "title": "M",
                        "price": "89.99",
                        "sku": "DJ-750G-M"
                    }
                ],
                "seo": {
                    "title": None,
                    "description": None
                }
            }
        ]
        
        # 示例集合数据
        mock_collections = [
            {
                "id": 345678901,
                "title": "Denim Collection",
                "handle": "denim-collection",
                "body_html": "<p>Our curated collection of premium denim wear.</p>",
                "seo": {
                    "title": None,
                    "description": None
                }
            }
        ]
        
        # 示例博客文章
        mock_articles = [
            {
                "id": 456789012,
                "title": "How to Style Your Denim Jacket",
                "handle": "how-to-style-denim-jacket",
                "body_html": "<p>Learn different ways to style your denim jacket for various occasions.</p>",
                "image": {
                    "src": "https://cdn.shopify.com/s/files/1/1234/5678/articles/style-guide.jpg",
                    "alt": None
                },
                "seo": {
                    "title": None,
                    "description": None
                }
            }
        ]
        
        return {
            "products": mock_products,
            "collections": mock_collections,
            "articles": mock_articles,
            "pages": [],
            "scan_time": datetime.now().isoformat(),
            "shop_domain": "mock-shop.myshopify.com",
            "is_mock": True
        }
    
    def _fetch_paginated(self, endpoint: str, data_key: str) -> List[Dict]:
        """获取分页数据"""
        results = []
        page = 1
        limit = 50
        
        while True:
            url = f"{self.base_url}{endpoint}"
            params = {
                "limit": limit,
                "page": page
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data_key in data:
                    items = data[data_key]
                    if not items:
                        break
                    
                    results.extend(items)
                    
                    # 检查是否还有更多页面
                    if len(items) < limit:
                        break
                    
                    page += 1
                    time.sleep(0.5)  # 避免API速率限制
                else:
                    break
                    
            except Exception as e:
                print(f"获取{endpoint}第{page}页失败: {e}")
                break
        
        return results
    
    def analyze_seo_issues(self, store_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析店铺SEO问题
        识别缺失的标题、描述、ALT文本等
        """
        analysis = {
            "product_issues": [],
            "collection_issues": [],
            "article_issues": [],
            "page_issues": [],
            "summary": {
                "total_products": len(store_data.get("products", [])),
                "products_without_title": 0,
                "products_without_description": 0,
                "products_without_alt": 0,
                "total_images": 0,
                "images_without_alt": 0
            }
        }
        
        # 分析产品
        for product in store_data.get("products", []):
            product_id = product.get("id")
            product_title = product.get("title", "")
            product_handle = product.get("handle", "")
            
            issues = []
            
            # 检查SEO标题
            seo_title = None
            if "seo" in product and product["seo"]:
                seo_title = product["seo"].get("title")
            
            if not seo_title:
                issues.append("missing_seo_title")
                analysis["summary"]["products_without_title"] += 1
            
            # 检查SEO描述
            seo_description = None
            if "seo" in product and product["seo"]:
                seo_description = product["seo"].get("description")
            
            if not seo_description:
                issues.append("missing_seo_description")
                analysis["summary"]["products_without_description"] += 1
            
            # 检查图片ALT文本
            images = product.get("images", [])
            alt_issues = 0
            
            for image in images:
                analysis["summary"]["total_images"] += 1
                alt_text = image.get("alt")
                if not alt_text or alt_text.strip() == "":
                    alt_issues += 1
                    analysis["summary"]["images_without_alt"] += 1
            
            if alt_issues > 0:
                issues.append(f"missing_alt_text_{alt_issues}_images")
            
            if issues:
                analysis["product_issues"].append({
                    "id": product_id,
                    "title": product_title,
                    "handle": product_handle,
                    "issues": issues
                })
        
        # 分析集合
        for collection in store_data.get("collections", []):
            collection_id = collection.get("id")
            collection_title = collection.get("title", "")
            collection_handle = collection.get("handle", "")
            
            issues = []
            
            # 检查SEO标题
            seo_title = None
            if "seo" in collection and collection["seo"]:
                seo_title = collection["seo"].get("title")
            
            if not seo_title:
                issues.append("missing_seo_title")
            
            # 检查SEO描述
            seo_description = None
            if "seo" in collection and collection["seo"]:
                seo_description = collection["seo"].get("description")
            
            if not seo_description:
                issues.append("missing_seo_description")
            
            if issues:
                analysis["collection_issues"].append({
                    "id": collection_id,
                    "title": collection_title,
                    "handle": collection_handle,
                    "issues": issues
                })
        
        # 分析文章
        for article in store_data.get("articles", []):
            article_id = article.get("id")
            article_title = article.get("title", "")
            article_handle = article.get("handle", "")
            
            issues = []
            
            # 检查SEO标题
            seo_title = None
            if "seo" in article and article["seo"]:
                seo_title = article["seo"].get("title")
            
            if not seo_title:
                issues.append("missing_seo_title")
            
            # 检查SEO描述
            seo_description = None
            if "seo" in article and article["seo"]:
                seo_description = article["seo"].get("description")
            
            if not seo_description:
                issues.append("missing_seo_description")
            
            # 检查文章图片ALT文本
            if "image" in article and article["image"]:
                alt_text = article["image"].get("alt")
                if not alt_text or alt_text.strip() == "":
                    issues.append("missing_image_alt_text")
            
            if issues:
                analysis["article_issues"].append({
                    "id": article_id,
                    "title": article_title,
                    "handle": article_handle,
                    "issues": issues
                })
        
        return analysis
    
    def generate_seo_recommendations(self, store_data: Dict[str, Any], 
                                    analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成SEO优化建议
        基于流量数据为每个页面提供具体的标题、描述、ALT文本优化方案
        """
        recommendations = {
            "products": [],
            "collections": [],
            "articles": [],
            "pages": [],
            "generated_time": datetime.now().isoformat(),
            "traffic_data_stats": {
                "keywords_count": len(self.traffic_data["keywords"]),
                "hashtags_count": len(self.traffic_data["hashtags"]),
                "trends_count": len(self.traffic_data["trends"])
            }
        }
        
        # 为每个有问题的产品生成建议
        for product_issue in analysis.get("product_issues", []):
            product_id = product_issue["id"]
            
            # 查找完整产品数据
            product = None
            for p in store_data.get("products", []):
                if p.get("id") == product_id:
                    product = p
                    break
            
            if not product:
                continue
            
            # 提取产品关键词
            product_keywords = self._extract_product_keywords(product)
            
            # 生成优化建议
            seo_suggestions = {
                "title": self._optimize_title(product["title"], product_keywords),
                "description": self._optimize_description(product.get("body_html", ""), product_keywords),
                "alt_texts": [],
                "keywords": product_keywords
            }
            
            # 为每个图片生成ALT文本建议
            for image in product.get("images", []):
                alt_suggestion = self._optimize_alt_text(product["title"], product_keywords)
                seo_suggestions["alt_texts"].append({
                    "image_id": image.get("id"),
                    "current_alt": image.get("alt"),
                    "suggested_alt": alt_suggestion
                })
            
            recommendations["products"].append({
                "id": product_id,
                "title": product["title"],
                "handle": product["handle"],
                "issues": product_issue["issues"],
                "suggestions": seo_suggestions
            })
        
        # 为集合生成建议
        for collection_issue in analysis.get("collection_issues", []):
            collection_id = collection_issue["id"]
            
            # 查找完整集合数据
            collection = None
            for c in store_data.get("collections", []):
                if c.get("id") == collection_id:
                    collection = c
                    break
            
            if not collection:
                continue
            
            # 提取集合关键词
            collection_keywords = self._extract_collection_keywords(collection)
            
            recommendations["collections"].append({
                "id": collection_id,
                "title": collection["title"],
                "handle": collection["handle"],
                "issues": collection_issue["issues"],
                "suggestions": {
                    "title": self._optimize_title(collection["title"], collection_keywords),
                    "description": self._optimize_description(collection.get("body_html", ""), collection_keywords),
                    "keywords": collection_keywords
                }
            })
        
        # 为文章生成建议
        for article_issue in analysis.get("article_issues", []):
            article_id = article_issue["id"]
            
            # 查找完整文章数据
            article = None
            for a in store_data.get("articles", []):
                if a.get("id") == article_id:
                    article = a
                    break
            
            if not article:
                continue
            
            # 提取文章关键词
            article_keywords = self._extract_article_keywords(article)
            
            recommendations["articles"].append({
                "id": article_id,
                "title": article["title"],
                "handle": article["handle"],
                "issues": article_issue["issues"],
                "suggestions": {
                    "title": self._optimize_title(article["title"], article_keywords),
                    "description": self._optimize_description(article.get("body_html", ""), article_keywords),
                    "image_alt": self._optimize_alt_text(article["title"], article_keywords) if article.get("image") else None,
                    "keywords": article_keywords
                }
            })
        
        return recommendations
    
    def _extract_product_keywords(self, product: Dict) -> List[str]:
        """从产品数据中提取关键词"""
        keywords = []
        
        # 从标题提取
        title = product.get("title", "").lower()
        keywords.extend(self._extract_meaningful_words(title))
        
        # 从标签提取
        tags = product.get("tags", "")
        if tags:
            tag_list = [tag.strip().lower() for tag in tags.split(",")]
            keywords.extend(tag_list)
        
        # 从产品类型提取
        product_type = product.get("product_type", "")
        if product_type:
            keywords.append(product_type.lower())
        
        # 从供应商提取
        vendor = product.get("vendor", "")
        if vendor:
            keywords.append(vendor.lower())
        
        # 添加流量数据中的相关关键词
        for traffic_kw in self.traffic_data["keywords"]:
            kw_text = traffic_kw.get("keyword", "").lower()
            # 检查是否与产品相关
            if any(word in kw_text for word in keywords[:5]) or any(word in title for word in kw_text.split()):
                if kw_text not in keywords:
                    keywords.append(kw_text)
        
        # 去重
        return list(dict.fromkeys(keywords))
    
    def _extract_collection_keywords(self, collection: Dict) -> List[str]:
        """从集合数据中提取关键词"""
        keywords = []
        
        # 从标题提取
        title = collection.get("title", "").lower()
        keywords.extend(self._extract_meaningful_words(title))
        
        # 从描述提取
        body_html = collection.get("body_html", "")
        if body_html:
            # 移除HTML标签
            text = re.sub(r'<[^>]+>', ' ', body_html)
            keywords.extend(self._extract_meaningful_words(text))
        
        return list(dict.fromkeys(keywords))
    
    def _extract_article_keywords(self, article: Dict) -> List[str]:
        """从文章数据中提取关键词"""
        keywords = []
        
        # 从标题提取
        title = article.get("title", "").lower()
        keywords.extend(self._extract_meaningful_words(title))
        
        # 从内容提取
        body_html = article.get("body_html", "")
        if body_html:
            # 移除HTML标签
            text = re.sub(r'<[^>]+>', ' ', body_html)
            keywords.extend(self._extract_meaningful_words(text))
        
        return list(dict.fromkeys(keywords))
    
    def _extract_meaningful_words(self, text: str) -> List[str]:
        """从文本中提取有意义的单词"""
        # 移除特殊字符，保留字母、数字和空格
        cleaned = re.sub(r'[^\w\s]', ' ', text)
        
        # 分割单词
        words = cleaned.lower().split()
        
        # 过滤停用词和短词
        meaningful = []
        for word in words:
            if (len(word) > 2 and 
                word not in self.seo_config["stop_words"] and
                not word.isdigit()):
                meaningful.append(word)
        
        return meaningful
    
    def _optimize_title(self, current_title: str, keywords: List[str]) -> str:
        """优化标题，包含关键词并控制长度"""
        # 移除当前标题中的品牌前缀等
        base_title = current_title
        
        # 选择最重要的关键词（基于搜索量或相关性）
        primary_kw = keywords[0] if keywords else ""
        
        # 构建优化标题
        optimized = f"{primary_kw} | {base_title}" if primary_kw else base_title
        
        # 确保长度不超过限制
        max_len = self.seo_config["title_length"]["max"]
        if len(optimized) > max_len:
            # 缩短基础标题部分
            base_max = max_len - len(primary_kw) - 3  # 3 for " | "
            if base_max > 10:  # 确保基础标题有意义
                shortened_base = base_title[:base_max].rstrip('.,! ')
                optimized = f"{primary_kw} | {shortened_base}..."
            else:
                optimized = optimized[:max_len]
        
        return optimized
    
    def _optimize_description(self, content: str, keywords: List[str]) -> str:
        """优化描述，包含关键词并控制长度"""
        # 从内容中提取摘要
        if content:
            # 移除HTML标签
            text = re.sub(r'<[^>]+>', ' ', content)
            # 取前200个字符作为基础
            base_desc = text[:200].strip()
        else:
            base_desc = ""
        
        # 如果没有内容，使用关键词构建描述
        if not base_desc and keywords:
            base_desc = f"Shop premium {keywords[0]} online. High quality materials and craftsmanship."
        
        # 确保包含主要关键词
        if keywords:
            primary_kw = keywords[0]
            if primary_kw not in base_desc.lower():
                base_desc = f"{primary_kw} - {base_desc}"
        
        # 确保长度符合SEO标准
        optimal_len = self.seo_config["description_length"]["optimal"]
        max_len = self.seo_config["description_length"]["max"]
        
        if len(base_desc) > max_len:
            base_desc = base_desc[:max_len].rstrip('.,! ') + "..."
        elif len(base_desc) < optimal_len and keywords:
            # 添加更多相关信息
            additional = f" Free shipping available. Browse our collection today."
            base_desc = base_desc + additional
        
        return base_desc
    
    def _optimize_alt_text(self, title: str, keywords: List[str]) -> str:
        """优化图片ALT文本"""
        # 使用标题和关键词构建ALT文本
        primary_kw = keywords[0] if keywords else ""
        
        if primary_kw:
            alt_text = f"{primary_kw} - {title}"
        else:
            alt_text = title
        
        # 控制长度
        max_len = self.seo_config["alt_text_length"]["max"]
        if len(alt_text) > max_len:
            alt_text = alt_text[:max_len].rstrip('.,! ')
        
        return alt_text
    
    def save_recommendations(self, recommendations: Dict[str, Any], 
                            filename: Optional[str] = None) -> str:
        """保存SEO建议到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"outputs/seo_recommendations_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2)
        
        print(f"SEO建议已保存到: {filename}")
        return filename
    
    def generate_report(self, store_data: Dict[str, Any], 
                       analysis: Dict[str, Any],
                       recommendations: Dict[str, Any]) -> str:
        """生成完整SEO分析报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        report = f"""# Shopify独立站SEO分析报告

**生成时间**: {report_date}
**店铺域名**: {store_data.get('shop_domain', '未知')}
**扫描类型**: {'模拟数据' if store_data.get('is_mock') else '实时扫描'}

## 执行摘要

### 店铺概况
- **产品数量**: {len(store_data.get('products', []))}
- **集合数量**: {len(store_data.get('collections', []))}
- **文章数量**: {len(store_data.get('articles', []))}
- **页面数量**: {len(store_data.get('pages', []))}

### SEO问题汇总
- **缺少SEO标题的产品**: {analysis['summary']['products_without_title']}
- **缺少SEO描述的产品**: {analysis['summary']['products_without_description']}
- **缺少ALT文本的图片**: {analysis['summary']['images_without_alt']} / {analysis['summary']['total_images']}

### 流量数据统计
- **关键词数量**: {recommendations['traffic_data_stats']['keywords_count']}
- **趋势标签数量**: {recommendations['traffic_data_stats']['hashtags_count']}
- **趋势主题数量**: {recommendations['traffic_data_stats']['trends_count']}

## 详细产品分析

"""
        
        # 添加产品建议
        for product_rec in recommendations.get("products", []):
            issues = ", ".join(product_rec["issues"]).replace("_", " ").title()
            suggestions = product_rec["suggestions"]
            
            report += f"""### {product_rec['title']}
**产品ID**: {product_rec['id']}
**问题**: {issues}

#### 优化建议
- **标题**: {suggestions['title']}
- **描述**: {suggestions['description']}
- **关键词**: {', '.join(suggestions['keywords'][:5])}

#### 图片ALT文本
"""
            
            for alt_info in suggestions.get("alt_texts", []):
                if alt_info["current_alt"]:
                    report += f"- 图片ID {alt_info['image_id']}: 当前 '{alt_info['current_alt']}' → 建议 '{alt_info['suggested_alt']}'\n"
                else:
                    report += f"- 图片ID {alt_info['image_id']}: 建议添加ALT文本 '{alt_info['suggested_alt']}'\n"
            
            report += "\n---\n\n"
        
        # 添加行动优先级
        report += """## 行动优先级

### 立即执行（高优先级）
1. **为所有产品添加SEO标题和描述** - 直接影响搜索排名
2. **为产品主图添加ALT文本** - 提升图片搜索可见性
3. **优化集合页面SEO元素** - 提高分类页面流量

### 中期优化（中优先级）
1. **基于流量数据优化关键词策略** - 持续跟踪关键词表现
2. **定期更新博客内容SEO** - 建立内容权威性
3. **监控竞争对手SEO策略** - 保持竞争优势

### 长期策略（低优先级）
1. **建立内部链接结构** - 提升网站整体权重
2. **创建产品使用指南内容** - 增强用户参与度
3. **拓展社交媒体SEO** - 多渠道引流

## 技术实施指南

### 1. 标题优化
- 确保每个产品标题包含1-2个核心关键词
- 标题长度控制在50-60字符之间
- 使用竖线符号分隔品牌和产品描述

### 2. 描述优化
- 描述长度控制在150-160字符
- 前25个字符必须包含核心关键词
- 包含行动号召（如"立即购买"、"免费配送"）

### 3. ALT文本优化
- 每张产品图片必须有描述性ALT文本
- 包含产品名称、颜色、尺寸等关键词
- 避免使用通用描述（如"产品图片"）

### 4. 关键词策略
- 主关键词：搜索量高，竞争中等
- 长尾关键词：搜索量较低，但转化率高
- 地域关键词：针对特定市场的搜索词

## 监测指标

### 短期指标（1-4周）
- 自然搜索流量增长百分比
- 关键词排名提升数量
- 点击率（CTR）改善

### 中期指标（1-3个月）
- 转化率提升
- 平均订单价值增加
- 跳出率降低

### 长期指标（3-6个月）
- 品牌搜索量增长
- 回头客比例提升
- 社交媒体提及增加

---

*报告版本: 1.0*
*生成批次ID: {timestamp}*
*系统: SellAI流量爆破军团SEO优化引擎*
"""
        
        # 保存报告
        report_dir = "docs"
        os.makedirs(report_dir, exist_ok=True)
        report_path = f"{report_dir}/shopify_seo_report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"SEO分析报告已生成: {report_path}")
        return report_path


def main():
    """主函数：执行完整SEO分析流程"""
    print("=== Shopify独立站SEO优化引擎 ===\n")
    
    # 初始化优化器
    optimizer = ShopifySEOOptimizer()
    
    # 加载流量数据
    optimizer.load_traffic_data()
    
    # 扫描店铺
    print("\n1. 扫描店铺数据...")
    store_data = optimizer.scan_shopify_store()
    
    # 分析SEO问题
    print("\n2. 分析SEO问题...")
    analysis = optimizer.analyze_seo_issues(store_data)
    
    # 生成优化建议
    print("\n3. 生成SEO优化建议...")
    recommendations = optimizer.generate_seo_recommendations(store_data, analysis)
    
    # 保存建议
    saved_recs = optimizer.save_recommendations(recommendations)
    
    # 生成完整报告
    print("\n4. 生成SEO分析报告...")
    report_path = optimizer.generate_report(store_data, analysis, recommendations)
    
    # 打印摘要
    print("\n=== 分析完成 ===")
    print(f"产品分析: {len(recommendations['products'])}个产品优化建议")
    print(f"集合分析: {len(recommendations['collections'])}个集合优化建议")
    print(f"文章分析: {len(recommendations['articles'])}篇文章优化建议")
    print(f"总计: {analysis['summary']['images_without_alt']}张图片需要ALT文本")
    print(f"\n报告保存于: {report_path}")
    print(f"建议保存于: {saved_recs}")
    
    return {
        "store_data": store_data,
        "analysis": analysis,
        "recommendations": recommendations,
        "report_path": report_path
    }


if __name__ == "__main__":
    main()