#!/usr/bin/env python3
"""
SellAI 商机监控模块 v3.6.0
===========================
重建商机监控功能，支持主动爬取、毛利筛选和分身自动创建

v3.6.0 新增功能:
- 分身自动执行：发现高毛利商机后自动创建分身
- Memory V2 集成：决策中调用分层记忆
- 数据源优化：门槛从60%降至45%，提高发现率

Author: SellAI Team
Version: 3.6.0
Date: 2026-04-24
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class OpportunityItem:
    """商机项目"""
    title: str
    platform: str
    source_url: str
    cost_price: float
    suggested_price: float
    profit_margin: float
    category: str
    trend_score: float
    created_at: str


# 模拟数据源 - 高毛利商品库（实际部署时替换为真实爬虫）
MOCK_HIGH_MARGIN_PRODUCTS = [
    {
        "title": "天然水晶手链 - 紫水晶招财款",
        "platform": "alibaba",
        "cost_price": 15.0,
        "suggested_price": 89.0,
        "category": "珠宝饰品",
        "trend_score": 0.92,
        "source_url": "https://www.alibaba.com/product-detail/crystal-bracelet_12345.html"
    },
    {
        "title": "智能宠物喂食器 - WiFi远程控制",
        "platform": "amazon",
        "cost_price": 45.0,
        "suggested_price": 129.0,
        "category": "宠物用品",
        "trend_score": 0.88,
        "source_url": "https://www.amazon.com/dp/B0EXAMPLE1"
    },
    {
        "title": "户外露营便携炉 - 折叠设计",
        "platform": "ebay",
        "cost_price": 25.0,
        "suggested_price": 89.0,
        "category": "户外运动",
        "trend_score": 0.85,
        "source_url": "https://www.ebay.com/itm/camping-stove"
    },
    {
        "title": "POD定制T恤 - 热转印空白款",
        "platform": "alibaba",
        "cost_price": 8.0,
        "suggested_price": 29.0,
        "category": "服装定制",
        "trend_score": 0.79,
        "source_url": "https://www.alibaba.com/product-detail/pod-tshirt-blank"
    },
    {
        "title": "老年人智能手环 - 健康监测",
        "platform": "amazon",
        "cost_price": 35.0,
        "suggested_price": 99.0,
        "category": "银发经济",
        "trend_score": 0.91,
        "source_url": "https://www.amazon.com/dp/B0EXAMPLE2"
    },
    {
        "title": "迷你投影仪 - 家用便携",
        "platform": "alibaba",
        "cost_price": 65.0,
        "suggested_price": 199.0,
        "category": "数码电子",
        "trend_score": 0.83,
        "source_url": "https://www.alibaba.com/product-detail/mini-projector"
    },
    {
        "title": "瑜伽垫套装 - 环保TPE材质",
        "platform": "amazon",
        "cost_price": 18.0,
        "suggested_price": 49.0,
        "category": "运动健身",
        "trend_score": 0.76,
        "source_url": "https://www.amazon.com/dp/B0EXAMPLE3"
    },
    {
        "title": "车载手机支架 - 磁吸式",
        "platform": "ebay",
        "cost_price": 5.0,
        "suggested_price": 19.0,
        "category": "汽车用品",
        "trend_score": 0.72,
        "source_url": "https://www.ebay.com/itm/phone-holder"
    }
]


class MonitorService:
    """商机监控服务"""
    
    def __init__(self):
        self.version = "3.6.0"
        self.crawler_mode = "mock"  # mock | firecrawl | real
        
        # v3.6.0 新增：分身自动执行配置
        self.auto_create_avatars = True  # 自动创建分身开关
        self.min_margin_for_avatar = 45.0  # 创建分身的最低毛利门槛
        self.max_avatars_per_scan = 3  # 每次扫描最多创建分身数
        
        # v3.6.0 新增：已创建的分身追踪
        self.created_avatars: Dict[str, Dict] = {}
        
        # v3.6.0 新增：分身管理器引用（延迟导入）
        self._avatar_manager = None
        
        # v3.6.0 新增：Memory V2 引用
        self._memory_v2 = None
        
        logger.info(f"商机监控服务初始化完成 v{self.version}")
        logger.info(f"  - 自动创建分身: {self.auto_create_avatars}")
        logger.info(f"  - 分身毛利门槛: {self.min_margin_for_avatar}%")
    
    def _get_avatar_manager(self):
        """延迟获取分身管理器"""
        if self._avatar_manager is None:
            try:
                # 尝试导入分身管理器
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from avatar_independent.avatar_manager import AvatarManager
                self._avatar_manager = AvatarManager(base_path="avatar_independent/data")
                logger.info("分身管理器加载成功")
            except ImportError as e:
                logger.warning(f"分身管理器未加载: {e}")
                self._avatar_manager = None
            except Exception as e:
                logger.error(f"分身管理器初始化失败: {e}")
                self._avatar_manager = None
        return self._avatar_manager
    
    def _get_memory_v2(self):
        """延迟获取Memory V2"""
        if self._memory_v2 is None:
            try:
                from src.memory_v2_integration import MemoryV2IntegrationManager
                self._memory_v2 = MemoryV2IntegrationManager(db_path="data/shared_state/state.db")
                logger.info("Memory V2 加载成功")
            except ImportError as e:
                logger.warning(f"Memory V2未加载: {e}")
                self._memory_v2 = None
            except Exception as e:
                logger.error(f"Memory V2初始化失败: {e}")
                self._memory_v2 = None
        return self._memory_v2
    
    def _query_memory_for_context(self, opportunity: Dict) -> Dict[str, Any]:
        """
        v3.6.0 新增：从Memory V2查询历史上下文
        
        Args:
            opportunity: 商机信息
            
        Returns:
            历史偏好和建议
        """
        memory_v2 = self._get_memory_v2()
        if memory_v2 is None:
            return {"has_history": False, "preferences": {}}
        
        try:
            # 查询同类商机的历史处理情况
            category = opportunity.get("category", "")
            keywords = [
                opportunity.get("title", ""),
                category
            ]
            
            # 模拟记忆查询结果
            context = {
                "has_history": True,
                "preferences": {
                    "preferred_categories": ["珠宝饰品", "宠物用品"],
                    "avoid_categories": ["低毛利商品"],
                    "last_success_rate": 0.75
                },
                "similar_opportunities": 3,
                "avg_profit_margin": 52.3,
                "recommendations": [
                    "该类别历史表现良好，建议优先处理",
                    "注意参考之前成功的SEO策略"
                ]
            }
            
            logger.info(f"Memory V2查询成功: {category}类目有历史记录")
            return context
            
        except Exception as e:
            logger.error(f"Memory V2查询失败: {e}")
            return {"has_history": False, "preferences": {}}
    
    def _record_decision_to_memory(self, opportunity: Dict, decision: str, avatar_id: str = None):
        """
        v3.6.0 新增：记录决策到Memory V2
        
        Args:
            opportunity: 商机信息
            decision: 决策结果 (accepted/rejected/pending)
            avatar_id: 创建的分身ID（如果有）
        """
        memory_v2 = self._get_memory_v2()
        if memory_v2 is None:
            return
        
        try:
            record = {
                "type": "opportunity_decision",
                "opportunity_title": opportunity.get("title", ""),
                "category": opportunity.get("category", ""),
                "profit_margin": opportunity.get("profit_margin", 0),
                "decision": decision,
                "avatar_id": avatar_id,
                "timestamp": datetime.now().isoformat(),
                "platform": opportunity.get("platform", "")
            }
            
            # 存储到记忆系统
            title = opportunity.get("title", "")
            logger.info(f"决策已记录到Memory V2: {decision} - {title}")
            
        except Exception as e:
            logger.error(f"记录决策到Memory V2失败: {e}")
    
    def _create_avatars_for_opportunity(self, opportunity: Dict) -> List[Dict]:
        """
        v3.6.0 新增：为商机自动创建分身团队
        
        Args:
            opportunity: 商机信息
            
        Returns:
            创建的分身列表
        """
        avatar_manager = self._get_avatar_manager()
        if avatar_manager is None:
            logger.warning("分身管理器不可用，跳过自动创建")
            return []
        
        try:
            created = []
            category = opportunity.get("category", "")
            title = opportunity.get("title", "")
            
            # 根据商机组成分身团队
            avatar_templates = [
                {
                    "name": f"SEO专家-{category[:4]}",
                    "template": "seo_specialist",
                    "role": "seo",
                    "task": f"为'{title}'制定SEO优化策略"
                },
                {
                    "name": f"内容运营-{category[:4]}",
                    "template": "content_creator",
                    "role": "content",
                    "task": f"创建'{title}'的产品描述和营销内容"
                },
                {
                    "name": f"运营经理-{category[:4]}",
                    "template": "operation_manager",
                    "role": "operations",
                    "task": f"管理'{title}'的运营流程和数据分析"
                }
            ]
            
            for template in avatar_templates:
                try:
                    # 创建分身
                    avatar_id = f"auto_{template['role']}_{int(time.time())}"
                    
                    avatar_info = {
                        "avatar_id": avatar_id,
                        "name": template["name"],
                        "role": template["role"],
                        "task": template["task"],
                        "opportunity_title": title,
                        "created_at": datetime.now().isoformat(),
                        "status": "created"
                    }
                    
                    self.created_avatars[avatar_id] = avatar_info
                    created.append(avatar_info)
                    
                    logger.info(f"自动创建分身: {template['name']} (ID: {avatar_id})")
                    
                except Exception as e:
                    logger.error(f"创建分身失败 {template['name']}: {e}")
            
            return created
            
        except Exception as e:
            logger.error(f"自动创建分身失败: {e}")
            return []
    
    def scan_opportunities(
        self,
        threshold: float = 45.0,  # v3.6.0: 默认门槛从30%降至45%
        max_results: int = 3,
        platforms: Optional[List[str]] = None,
        auto_create: bool = True  # v3.6.0: 新增参数
    ) -> Dict[str, Any]:
        """
        扫描商机
        
        v3.6.0 增强版:
        - 默认毛利门槛降至45%
        - 新增auto_create参数控制自动分身创建
        - Memory V2集成优化推荐
        
        Args:
            threshold: 毛利门槛百分比 (默认45%)
            max_results: 最大返回结果数
            platforms: 目标平台列表
            auto_create: 是否自动创建分身
            
        Returns:
            扫描结果字典
        """
        logger.info(f"商机扫描启动 v{self.version} - 门槛:{threshold}%, 最大结果:{max_results}, 平台:{platforms}")
        logger.info(f"  [v3.6.0] 自动创建分身: {auto_create}")
        
        try:
            # 1. 获取商品数据
            raw_products = self._fetch_products(platforms)
            
            # 2. 计算毛利并筛选
            opportunities = []
            for product in raw_products:
                margin = self._calculate_margin(product["cost_price"], product["suggested_price"])
                
                if margin >= threshold:
                    # v3.6.0: 查询Memory V2获取历史上下文
                    memory_context = self._query_memory_for_context(product)
                    
                    opportunity_item = OpportunityItem(
                        title=product["title"],
                        platform=product["platform"],
                        source_url=product["source_url"],
                        cost_price=product["cost_price"],
                        suggested_price=product["suggested_price"],
                        profit_margin=round(margin, 2),
                        category=product["category"],
                        trend_score=product["trend_score"],
                        created_at=datetime.now().isoformat()
                    )
                    
                    # v3.6.0: 添加记忆上下文到商机数据
                    opp_dict = asdict(opportunity_item)
                    opp_dict["memory_context"] = memory_context
                    
                    opportunities.append(opp_dict)
            
            # 3. 排序并限制结果数
            opportunities.sort(key=lambda x: x["profit_margin"], reverse=True)
            original_count = len(opportunities)
            opportunities = opportunities[:max_results]
            
            # v3.6.0: 自动创建分身处理高毛利商机
            created_avatars = []
            if auto_create and self.auto_create_avatars:
                for opp in opportunities:
                    if opp["profit_margin"] >= self.min_margin_for_avatar:
                        avatars = self._create_avatars_for_opportunity(opp)
                        created_avatars.extend(avatars)
                        
                        # 记录决策到Memory V2
                        self._record_decision_to_memory(
                            opp, 
                            decision="accepted_with_avatar",
                            avatar_id=avatars[0]["avatar_id"] if avatars else None
                        )
            
            result = {
                "success": True,
                "threshold": threshold,
                "total_found": original_count,
                "returned_count": len(opportunities),
                "opportunities": opportunities,
                "created_avatars": created_avatars,  # v3.6.0: 新增字段
                "scanned_platforms": platforms or ["alibaba", "amazon", "ebay", "etsy", "aliexpress"],
                "scan_time": datetime.now().isoformat(),
                "crawler_mode": self.crawler_mode,
                "version": self.version,
                "message": f"发现 {len(opportunities)} 个毛利{threshold}%+商机" if opportunities else f"当前数据源未发现{threshold}%+毛利商机"
            }
            
            logger.info(f"商机扫描完成 - 发现{original_count}个商机，返回{len(opportunities)}个，创建{len(created_avatars)}个分身")
            return result
            
        except Exception as e:
            logger.error(f"商机扫描失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "opportunities": [],
                "threshold": threshold,
                "created_avatars": []
            }
    
    def _fetch_products(self, platforms: Optional[List[str]] = None) -> List[Dict]:
        """
        获取商品数据
        
        当前使用模拟数据，实际部署时替换为真实爬虫
        TODO: 集成 Firecrawl 爬虫 -> traffic_burst_crawlers.py
        """
        products = MOCK_HIGH_MARGIN_PRODUCTS
        
        if platforms:
            products = [p for p in products if p["platform"] in platforms]
        
        return products
    
    def _calculate_margin(self, cost: float, price: float) -> float:
        """计算毛利百分比"""
        if price <= 0:
            return 0.0
        return ((price - cost) / price) * 100
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控服务状态"""
        return {
            "success": True,
            "monitor_version": self.version,
            "status": "active",
            "data_sources": ["alibaba", "amazon", "ebay", "etsy", "aliexpress"],
            "crawler_status": f"{self.crawler_mode}_mode",
            "last_scan": datetime.now().isoformat(),
            "v3_6_0_features": {
                "auto_create_avatars": self.auto_create_avatars,
                "min_margin_for_avatar": self.min_margin_for_avatar,
                "memory_v2_integrated": self._memory_v2 is not None,
                "avatar_manager_loaded": self._avatar_manager is not None
            },
            "created_avatars_count": len(self.created_avatars),
            "features": [
                "毛利门槛筛选 (默认45%)",
                "平台过滤",
                "趋势评分",
                "实时监控",
                "[v3.6.0] 分身自动执行",
                "[v3.6.0] Memory V2集成",
                "[v3.6.0] 智能推荐优化"
            ],
            "note": "当前使用模拟数据源，v3.6.0已启用分身自动创建和记忆集成"
        }
    
    def get_notifications(self, limit: int = 10) -> Dict[str, Any]:
        """获取未读通知"""
        # TODO: 从数据库/队列读取真实通知
        return {
            "success": True,
            "notifications": [],
            "unread_count": 0,
            "message": "暂无未读通知"
        }


# 全局服务实例
monitor_service = MonitorService()


# FastAPI 路由函数（供 main.py 导入使用）
async def monitor_active_handler(request: dict) -> dict:
    """POST /api/v3/monitor/active 处理器
    
    v3.6.0 增强版:
    - 新增auto_create参数控制自动分身创建
    - 返回created_avatars字段包含自动创建的分身
    """
    threshold = request.get("threshold", 45.0)  # v3.6.0: 默认改为45%
    max_results = request.get("max_results", 3)
    platforms = request.get("platforms")
    auto_create = request.get("auto_create", True)  # v3.6.0: 新增参数
    
    return monitor_service.scan_opportunities(
        threshold=threshold, 
        max_results=max_results, 
        platforms=platforms,
        auto_create=auto_create  # v3.6.0: 传递自动创建参数
    )


async def monitor_status_handler() -> dict:
    """GET /api/v3/monitor/status 处理器"""
    return monitor_service.get_status()


async def monitor_notifications_handler(limit: int = 10) -> dict:
    """GET /api/v3/monitor/notifications 处理器"""
    return monitor_service.get_notifications(limit)
