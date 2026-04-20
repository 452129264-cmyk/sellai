#!/usr/bin/env python3
"""
Scrapling全球全品类配置管理器
实现自适应配置生成、管理、持久化功能
"""

import json
import logging
import sqlite3
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
import os

logger = logging.getLogger(__name__)

@dataclass
class GlobalCategoryConfig:
    """全球品类配置"""
    category_id: str
    category_name: str
    description: str
    target_regions: List[str]
    keywords: List[str]
    data_fields: List[str]
    platforms: List[str]
    crawl_depth: int = 3
    max_pages: int = 100
    priority: int = 5  # 最高优先级
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

@dataclass
class AntiAntiCrawlConfig:
    """反反爬配置"""
    user_agent_rotation: bool = True
    proxy_rotation: bool = True
    request_delay_seconds: Tuple[float, float] = (1.0, 3.0)
    max_concurrent_requests: int = 3
    respect_robots_txt: bool = True
    obey_rate_limits: bool = True
    cookie_management: bool = True
    javascript_rendering: bool = False  # 注意：当前环境可能不支持
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

@dataclass
class VPNStrategyConfig:
    """VPN策略配置"""
    verify_ssl: bool = False  # 强制忽略SSL证书错误
    proxy_servers: List[str] = field(default_factory=lambda: [
        "http://proxy-global-1.sellai.com:8080",
        "http://proxy-global-2.sellai.com:8080",
        "http://proxy-global-3.sellai.com:8080"
    ])
    proxy_rotation_interval_minutes: int = 5
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ])
    retry_attempts: int = 3
    retry_delay_seconds: int = 2
    timeout_seconds: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

@dataclass
class DataProcessingConfig:
    """数据处理配置"""
    extraction_rules: Dict[str, str] = field(default_factory=dict)
    normalization_rules: Dict[str, Any] = field(default_factory=dict)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    transformation_pipeline: List[str] = field(default_factory=list)
    output_format: str = "json"
    compression_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

class GlobalConfigManager:
    """
    全局配置管理器
    负责Scrapling模块的配置管理、持久化、验证
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化配置管理器
        
        参数：
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.config_cache = {}
        
        # 默认全局品类配置
        self.default_categories = [
            GlobalCategoryConfig(
                category_id="ecommerce",
                category_name="电子商务",
                description="全球电商平台商品趋势、销售数据、市场分析",
                target_regions=["US", "EU", "SEA", "CN", "global"],
                keywords=["trending products", "best sellers", "market analysis", "sales rank", "reviews"],
                data_fields=["product_name", "price", "reviews", "sales_rank", "category", "estimated_margin"],
                platforms=["Amazon", "eBay", "Shopify", "Walmart", "Alibaba"]
            ),
            GlobalCategoryConfig(
                category_id="ai_startups",
                category_name="AI创业公司",
                description="AI领域创业公司融资、技术趋势、市场机会",
                target_regions=["US", "EU", "CN", "global"],
                keywords=["AI funding", "startup trends", "venture capital", "tech innovation", "market disruption"],
                data_fields=["company_name", "funding_amount", "investors", "sector", "valuation", "technology_focus"],
                platforms=["Crunchbase", "AngelList", "TechCrunch", "Product Hunt", "PitchBook"]
            ),
            GlobalCategoryConfig(
                category_id="cross_border",
                category_name="跨境贸易",
                description="全球跨境贸易机会、供应链、物流成本",
                target_regions=["global", "US", "EU", "SEA", "CN"],
                keywords=["global trade", "export opportunities", "import trends", "supply chain", "logistics cost"],
                data_fields=["product_type", "source_country", "target_market", "shipping_cost", "profit_margin", "tariff_rate"],
                platforms=["AliExpress", "Wish", "Banggood", "Geekbuying", "MadeInChina"]
            ),
            GlobalCategoryConfig(
                category_id="brand_outreach",
                category_name="品牌营销",
                description="全球品牌营销趋势、红人合作、社交媒体策略",
                target_regions=["US", "EU", "SEA", "CN", "global"],
                keywords=["influencer marketing", "brand collaboration", "social media trends", "content strategy", "audience engagement"],
                data_fields=["influencer_name", "follower_count", "engagement_rate", "niche", "collaboration_fee", "content_type"],
                platforms=["Instagram", "TikTok", "YouTube", "Pinterest", "Twitter"]
            ),
            GlobalCategoryConfig(
                category_id="traffic_monetization",
                category_name="流量变现",
                description="全球流量变现模式、广告趋势、转化优化",
                target_regions=["US", "EU", "SEA", "CN", "global"],
                keywords=["advertising trends", "traffic sources", "conversion rates", "monetization models", "ROI optimization"],
                data_fields=["platform", "cpc", "ctr", "conversion_rate", "roi", "audience_demographics"],
                platforms=["Google Ads", "Facebook Ads", "Twitter", "Reddit", "LinkedIn"]
            )
        ]
        
        # 默认反反爬配置
        self.default_anti_anti_crawl = AntiAntiCrawlConfig()
        
        # 默认VPN策略配置
        self.default_vpn_strategy = VPNStrategyConfig()
        
        # 默认数据处理配置
        self.default_data_processing = DataProcessingConfig()
        
        logger.info("全局配置管理器初始化完成")
    
    def initialize_config_tables(self) -> bool:
        """
        初始化配置数据库表
        
        返回：
            初始化成功返回True，失败返回False
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. 创建全球品类配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrapling_global_categories (
                    category_id TEXT PRIMARY KEY,
                    category_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    target_regions TEXT NOT NULL,  -- JSON数组格式
                    keywords TEXT NOT NULL,         -- JSON数组格式
                    data_fields TEXT NOT NULL,      -- JSON数组格式
                    platforms TEXT NOT NULL,        -- JSON数组格式
                    crawl_depth INTEGER NOT NULL DEFAULT 3,
                    max_pages INTEGER NOT NULL DEFAULT 100,
                    priority INTEGER NOT NULL DEFAULT 5,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            """)
            
            # 2. 创建反反爬配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrapling_anti_anti_crawl_config (
                    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_agent_rotation BOOLEAN NOT NULL DEFAULT TRUE,
                    proxy_rotation BOOLEAN NOT NULL DEFAULT TRUE,
                    request_delay_min REAL NOT NULL DEFAULT 1.0,
                    request_delay_max REAL NOT NULL DEFAULT 3.0,
                    max_concurrent_requests INTEGER NOT NULL DEFAULT 3,
                    respect_robots_txt BOOLEAN NOT NULL DEFAULT TRUE,
                    obey_rate_limits BOOLEAN NOT NULL DEFAULT TRUE,
                    cookie_management BOOLEAN NOT NULL DEFAULT TRUE,
                    javascript_rendering BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 3. 创建VPN策略配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrapling_vpn_strategy_config (
                    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    verify_ssl BOOLEAN NOT NULL DEFAULT FALSE,
                    proxy_servers TEXT NOT NULL,  -- JSON数组格式
                    proxy_rotation_interval_minutes INTEGER NOT NULL DEFAULT 5,
                    user_agents TEXT NOT NULL,     -- JSON数组格式
                    retry_attempts INTEGER NOT NULL DEFAULT 3,
                    retry_delay_seconds INTEGER NOT NULL DEFAULT 2,
                    timeout_seconds INTEGER NOT NULL DEFAULT 30,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. 创建数据处理配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrapling_data_processing_config (
                    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extraction_rules TEXT NOT NULL,  -- JSON格式
                    normalization_rules TEXT NOT NULL,  -- JSON格式
                    validation_rules TEXT NOT NULL,  -- JSON格式
                    transformation_pipeline TEXT NOT NULL,  -- JSON数组格式
                    output_format TEXT NOT NULL DEFAULT 'json',
                    compression_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 5. 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_categories_enabled 
                ON scrapling_global_categories(enabled, priority)
            """)
            
            conn.commit()
            
            # 6. 插入默认配置
            self._insert_default_configs(cursor)
            
            conn.commit()
            conn.close()
            
            logger.info("Scrapling配置表初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"配置表初始化失败: {e}")
            return False
    
    def _insert_default_configs(self, cursor: sqlite3.Cursor) -> None:
        """插入默认配置"""
        
        # 插入默认品类配置
        for category in self.default_categories:
            cursor.execute("""
                INSERT OR REPLACE INTO scrapling_global_categories 
                (category_id, category_name, description, target_regions, keywords,
                 data_fields, platforms, crawl_depth, max_pages, priority, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                category.category_id,
                category.category_name,
                category.description,
                json.dumps(category.target_regions),
                json.dumps(category.keywords),
                json.dumps(category.data_fields),
                json.dumps(category.platforms),
                category.crawl_depth,
                category.max_pages,
                category.priority,
                category.enabled
            ))
        
        # 插入反反爬配置
        anti_config = self.default_anti_anti_crawl
        cursor.execute("""
            INSERT OR REPLACE INTO scrapling_anti_anti_crawl_config 
            (user_agent_rotation, proxy_rotation, request_delay_min, request_delay_max,
             max_concurrent_requests, respect_robots_txt, obey_rate_limits,
             cookie_management, javascript_rendering)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            anti_config.user_agent_rotation,
            anti_config.proxy_rotation,
            anti_config.request_delay_seconds[0],
            anti_config.request_delay_seconds[1],
            anti_config.max_concurrent_requests,
            anti_config.respect_robots_txt,
            anti_config.obey_rate_limits,
            anti_config.cookie_management,
            anti_config.javascript_rendering
        ))
        
        # 插入VPN策略配置
        vpn_config = self.default_vpn_strategy
        cursor.execute("""
            INSERT OR REPLACE INTO scrapling_vpn_strategy_config 
            (verify_ssl, proxy_servers, proxy_rotation_interval_minutes,
             user_agents, retry_attempts, retry_delay_seconds, timeout_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            vpn_config.verify_ssl,
            json.dumps(vpn_config.proxy_servers),
            vpn_config.proxy_rotation_interval_minutes,
            json.dumps(vpn_config.user_agents),
            vpn_config.retry_attempts,
            vpn_config.retry_delay_seconds,
            vpn_config.timeout_seconds
        ))
        
        # 插入数据处理配置
        data_config = self.default_data_processing
        cursor.execute("""
            INSERT OR REPLACE INTO scrapling_data_processing_config 
            (extraction_rules, normalization_rules, validation_rules,
             transformation_pipeline, output_format, compression_enabled)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            json.dumps(data_config.extraction_rules),
            json.dumps(data_config.normalization_rules),
            json.dumps(data_config.validation_rules),
            json.dumps(data_config.transformation_pipeline),
            data_config.output_format,
            data_config.compression_enabled
        ))
    
    def get_category_config(self, category_id: str) -> Optional[Dict[str, Any]]:
        """
        获取品类配置
        
        参数：
            category_id: 品类ID
        
        返回：
            品类配置字典，不存在返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM scrapling_global_categories 
                WHERE category_id = ? AND enabled = TRUE
            """, (category_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.warning(f"未找到启用的品类配置: {category_id}")
                return None
            
            # 解析JSON字段
            config = {
                "category_id": row[0],
                "category_name": row[1],
                "description": row[2],
                "target_regions": json.loads(row[3]),
                "keywords": json.loads(row[4]),
                "data_fields": json.loads(row[5]),
                "platforms": json.loads(row[6]),
                "crawl_depth": row[7],
                "max_pages": row[8],
                "priority": row[9],
                "enabled": row[10] == 1,
                "created_at": row[11],
                "updated_at": row[12],
                "last_used": row[13]
            }
            
            # 更新最后使用时间
            self._update_last_used(category_id)
            
            return config
            
        except Exception as e:
            logger.error(f"获取品类配置失败: {category_id} - {e}")
            return None
    
    def _update_last_used(self, category_id: str) -> None:
        """更新最后使用时间"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE scrapling_global_categories 
                SET last_used = CURRENT_TIMESTAMP
                WHERE category_id = ?
            """, (category_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"更新最后使用时间失败: {e}")
    
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """
        获取所有启用的品类配置
        
        返回：
            品类配置列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT category_id, category_name, description, target_regions,
                       priority, enabled
                FROM scrapling_global_categories 
                WHERE enabled = TRUE
                ORDER BY priority DESC, category_name
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            categories = []
            for row in rows:
                categories.append({
                    "category_id": row[0],
                    "category_name": row[1],
                    "description": row[2],
                    "target_regions": json.loads(row[3]),
                    "priority": row[4],
                    "enabled": row[5] == 1
                })
            
            return categories
            
        except Exception as e:
            logger.error(f"获取所有品类配置失败: {e}")
            return []
    
    def get_anti_anti_crawl_config(self) -> Dict[str, Any]:
        """
        获取反反爬配置
        
        返回：
            反反爬配置字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM scrapling_anti_anti_crawl_config")
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.warning("未找到反反爬配置，返回默认配置")
                return asdict(self.default_anti_anti_crawl)
            
            config = {
                "user_agent_rotation": row[1] == 1,
                "proxy_rotation": row[2] == 1,
                "request_delay_seconds": (row[3], row[4]),
                "max_concurrent_requests": row[5],
                "respect_robots_txt": row[6] == 1,
                "obey_rate_limits": row[7] == 1,
                "cookie_management": row[8] == 1,
                "javascript_rendering": row[9] == 1
            }
            
            return config
            
        except Exception as e:
            logger.error(f"获取反反爬配置失败: {e}")
            return asdict(self.default_anti_anti_crawl)
    
    def get_vpn_strategy_config(self) -> Dict[str, Any]:
        """
        获取VPN策略配置
        
        返回：
            VPN策略配置字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM scrapling_vpn_strategy_config")
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.warning("未找到VPN策略配置，返回默认配置")
                return asdict(self.default_vpn_strategy)
            
            config = {
                "verify_ssl": row[1] == 1,
                "proxy_servers": json.loads(row[2]),
                "proxy_rotation_interval_minutes": row[3],
                "user_agents": json.loads(row[4]),
                "retry_attempts": row[5],
                "retry_delay_seconds": row[6],
                "timeout_seconds": row[7]
            }
            
            return config
            
        except Exception as e:
            logger.error(f"获取VPN策略配置失败: {e}")
            return asdict(self.default_vpn_strategy)
    
    def get_data_processing_config(self) -> Dict[str, Any]:
        """
        获取数据处理配置
        
        返回：
            数据处理配置字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM scrapling_data_processing_config")
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.warning("未找到数据处理配置，返回默认配置")
                return asdict(self.default_data_processing)
            
            config = {
                "extraction_rules": json.loads(row[1]),
                "normalization_rules": json.loads(row[2]),
                "validation_rules": json.loads(row[3]),
                "transformation_pipeline": json.loads(row[4]),
                "output_format": row[5],
                "compression_enabled": row[6] == 1
            }
            
            return config
            
        except Exception as e:
            logger.error(f"获取数据处理配置失败: {e}")
            return asdict(self.default_data_processing)
    
    def update_category_config(self, category_id: str, 
                              updates: Dict[str, Any]) -> bool:
        """
        更新品类配置
        
        参数：
            category_id: 品类ID
            updates: 更新字段字典
        
        返回：
            更新成功返回True，失败返回False
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建SET子句
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key in ["target_regions", "keywords", "data_fields", "platforms"]:
                    # JSON字段需要序列化
                    set_clauses.append(f"{key} = ?")
                    params.append(json.dumps(value))
                elif key in ["enabled"]:
                    # 布尔字段转换
                    set_clauses.append(f"{key} = ?")
                    params.append(1 if value else 0)
                else:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            # 添加更新时间
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            # 构建完整SQL
            sql = f"""
                UPDATE scrapling_global_categories 
                SET {', '.join(set_clauses)}
                WHERE category_id = ?
            """
            
            params.append(category_id)
            
            cursor.execute(sql, params)
            
            conn.commit()
            conn.close()
            
            logger.info(f"更新品类配置成功: {category_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新品类配置失败: {category_id} - {e}")
            return False
    
    def export_config_yaml(self, output_path: str) -> bool:
        """
        导出配置为YAML文件
        
        参数：
            output_path: 输出文件路径
        
        返回：
            导出成功返回True，失败返回False
        """
        try:
            config_data = {
                "timestamp": datetime.now().isoformat(),
                "categories": self.get_all_categories(),
                "anti_anti_crawl": self.get_anti_anti_crawl_config(),
                "vpn_strategy": self.get_vpn_strategy_config(),
                "data_processing": self.get_data_processing_config()
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"配置导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"配置导出失败: {e}")
            return False
    
    def import_config_yaml(self, input_path: str) -> bool:
        """
        从YAML文件导入配置
        
        参数：
            input_path: 输入文件路径
        
        返回：
            导入成功返回True，失败返回False
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                logger.error("YAML文件内容为空")
                return False
            
            # 更新品类配置
            if "categories" in config_data:
                for category in config_data["categories"]:
                    self.update_category_config(
                        category_id=category["category_id"],
                        updates=category
                    )
            
            logger.info(f"配置导入成功: {input_path}")
            return True
            
        except Exception as e:
            logger.error(f"配置导入失败: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要
        
        返回：
            配置摘要字典
        """
        categories = self.get_all_categories()
        
        return {
            "total_categories": len(categories),
            "enabled_categories": len([c for c in categories if c["enabled"]]),
            "categories_by_priority": {
                "highest": len([c for c in categories if c["priority"] == 5]),
                "high": len([c for c in categories if c["priority"] == 4]),
                "normal": len([c for c in categories if c["priority"] == 3]),
                "low": len([c for c in categories if c["priority"] == 2]),
                "lowest": len([c for c in categories if c["priority"] == 1])
            },
            "timestamp": datetime.now().isoformat()
        }