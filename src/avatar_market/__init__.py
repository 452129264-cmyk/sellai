#!/usr/bin/env python3
"""
SellAI v3.0.0 - AI分身市场
Avatar Market Module
提供分身模板交易、能力租赁、技能订阅服务

功能：
- 分身模板市场
- 能力插件交易
- 技能订阅服务
- 评价与评分系统
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ListingType(Enum):
    """商品类型"""
    AVATAR_TEMPLATE = "avatar_template"
    CAPABILITY_PLUGIN = "capability_plugin"
    SKILL_SUBSCRIPTION = "skill_subscription"
    TRAINING_DATA = "training_data"


class PricingModel(Enum):
    """定价模型"""
    ONE_TIME = "one_time"          # 一次性购买
    SUBSCRIPTION = "subscription"  # 订阅
    PAY_PER_USE = "pay_per_use"    # 按次付费
    FREEMIUM = "freemium"          # 免费+增值


class ListingStatus(Enum):
    """商品状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


@dataclass
class AvatarListing:
    """分身商品"""
    listing_id: str
    seller_id: str
    title: str
    description: str
    listing_type: ListingType
    category: str
    tags: List[str]
    pricing_model: PricingModel
    price: float
    currency: str = "USD"
    preview_images: List[str] = field(default_factory=list)
    demo_url: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    compatibility: List[str] = field(default_factory=list)  # 兼容的平台
    rating: float = 0.0
    review_count: int = 0
    sales_count: int = 0
    status: ListingStatus = ListingStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Review:
    """商品评价"""
    review_id: str
    listing_id: str
    buyer_id: str
    rating: float  # 1-5
    title: str
    content: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    verified_purchase: bool = False
    helpful_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Transaction:
    """交易记录"""
    transaction_id: str
    listing_id: str
    buyer_id: str
    seller_id: str
    amount: float
    currency: str
    transaction_type: str  # purchase, subscription, refund
    status: str  # pending, completed, failed, refunded
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class AvatarMarket:
    """
    AI分身市场控制器
    
    提供分身模板和能力的交易平台
    """
    
    def __init__(self, db_path: str = "data/shared_state/avatar_market.db"):
        self.db_path = db_path
        self.listings: Dict[str, AvatarListing] = {}
        self.reviews: Dict[str, Review] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.categories = [
            "电商运营",
            "内容创作",
            "客户服务",
            "数据分析",
            "营销推广",
            "供应链管理",
            "财务管理",
            "人力资源"
        ]
        self._ensure_data_dir()
        self._load_sample_data()
        logger.info("AI分身市场初始化完成")
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _load_sample_data(self):
        """加载示例数据"""
        # 添加示例分身模板
        sample_listings = [
            AvatarListing(
                listing_id="listing_001",
                seller_id="system",
                title="电商全能运营助手",
                description="专为电商设计的多功能AI运营助手，支持商品上架、客服、数据分析等",
                listing_type=ListingType.AVATAR_TEMPLATE,
                category="电商运营",
                tags=["电商", "运营", "全能"],
                pricing_model=PricingModel.SUBSCRIPTION,
                price=99.99,
                capabilities=["商品管理", "客服", "数据分析", "营销推广"],
                compatibility=["Shopify", "Amazon", "eBay"],
                rating=4.8,
                review_count=156
            ),
            AvatarListing(
                listing_id="listing_002",
                seller_id="system",
                title="社交媒体内容大师",
                description="专业的社交媒体内容创作助手，支持多平台内容策划和发布",
                listing_type=ListingType.AVATAR_TEMPLATE,
                category="内容创作",
                tags=["社交媒体", "内容创作", "多平台"],
                pricing_model=PricingModel.ONE_TIME,
                price=149.99,
                capabilities=["内容策划", "文案创作", "排期发布", "数据分析"],
                compatibility=["TikTok", "Instagram", "Twitter"],
                rating=4.6,
                review_count=89
            )
        ]
        
        for listing in sample_listings:
            self.listings[listing.listing_id] = listing
    
    # ============================================================
    # 商品管理
    # ============================================================
    
    def create_listing(
        self,
        seller_id: str,
        title: str,
        description: str,
        listing_type: Union[str, ListingType],
        category: str,
        tags: List[str],
        pricing_model: Union[str, PricingModel],
        price: float,
        capabilities: Optional[List[str]] = None,
        **kwargs
    ) -> AvatarListing:
        """
        创建商品
        
        Args:
            seller_id: 卖家ID
            title: 标题
            description: 描述
            listing_type: 商品类型
            category: 分类
            tags: 标签
            pricing_model: 定价模型
            price: 价格
            capabilities: 能力列表
        
        Returns:
            AvatarListing: 创建的商品
        """
        listing_id = f"listing_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # 类型转换
        if isinstance(listing_type, str):
            listing_type = ListingType(listing_type)
        if isinstance(pricing_model, str):
            pricing_model = PricingModel(pricing_model)
        
        listing = AvatarListing(
            listing_id=listing_id,
            seller_id=seller_id,
            title=title,
            description=description,
            listing_type=listing_type,
            category=category,
            tags=tags,
            pricing_model=pricing_model,
            price=price,
            capabilities=capabilities or [],
            **kwargs
        )
        
        self.listings[listing_id] = listing
        logger.info(f"创建商品: {listing_id} - {title}")
        
        return listing
    
    def get_listing(self, listing_id: str) -> Optional[AvatarListing]:
        """获取商品详情"""
        return self.listings.get(listing_id)
    
    def search_listings(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        listing_type: Optional[Union[str, ListingType]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        sort_by: str = "rating",
        limit: int = 20
    ) -> List[AvatarListing]:
        """
        搜索商品
        
        Args:
            query: 搜索关键词
            category: 分类
            listing_type: 商品类型
            min_price: 最低价格
            max_price: 最高价格
            min_rating: 最低评分
            sort_by: 排序字段
            limit: 返回数量
        
        Returns:
            List[AvatarListing]: 商品列表
        """
        results = list(self.listings.values())
        
        # 过滤条件
        if query:
            query = query.lower()
            results = [
                r for r in results
                if query in r.title.lower() or query in r.description.lower()
            ]
        
        if category:
            results = [r for r in results if r.category == category]
        
        if listing_type:
            if isinstance(listing_type, str):
                listing_type = ListingType(listing_type)
            results = [r for r in results if r.listing_type == listing_type]
        
        if min_price is not None:
            results = [r for r in results if r.price >= min_price]
        
        if max_price is not None:
            results = [r for r in results if r.price <= max_price]
        
        if min_rating is not None:
            results = [r for r in results if r.rating >= min_rating]
        
        # 排序
        if sort_by == "rating":
            results.sort(key=lambda x: x.rating, reverse=True)
        elif sort_by == "price_low":
            results.sort(key=lambda x: x.price)
        elif sort_by == "price_high":
            results.sort(key=lambda x: x.price, reverse=True)
        elif sort_by == "sales":
            results.sort(key=lambda x: x.sales_count, reverse=True)
        
        return results[:limit]
    
    def get_featured_listings(self, limit: int = 10) -> List[AvatarListing]:
        """获取精选商品"""
        featured = [l for l in self.listings.values() if l.rating >= 4.5]
        featured.sort(key=lambda x: (x.rating, x.sales_count), reverse=True)
        return featured[:limit]
    
    def get_trending_listings(self, limit: int = 10) -> List[AvatarListing]:
        """获取热门商品"""
        trending = list(self.listings.values())
        trending.sort(key=lambda x: x.sales_count, reverse=True)
        return trending[:limit]
    
    # ============================================================
    # 评价管理
    # ============================================================
    
    def create_review(
        self,
        listing_id: str,
        buyer_id: str,
        rating: float,
        title: str,
        content: str,
        pros: Optional[List[str]] = None,
        cons: Optional[List[str]] = None,
        verified_purchase: bool = False
    ) -> Review:
        """
        创建评价
        
        Args:
            listing_id: 商品ID
            buyer_id: 买家ID
            rating: 评分
            title: 评价标题
            content: 评价内容
            pros: 优点
            cons: 缺点
            verified_purchase: 是否已验证购买
        
        Returns:
            Review: 创建的评价
        """
        review_id = f"review_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        review = Review(
            review_id=review_id,
            listing_id=listing_id,
            buyer_id=buyer_id,
            rating=rating,
            title=title,
            content=content,
            pros=pros or [],
            cons=cons or [],
            verified_purchase=verified_purchase
        )
        
        self.reviews[review_id] = review
        
        # 更新商品评分
        listing = self.listings.get(listing_id)
        if listing:
            listing_reviews = [r for r in self.reviews.values() if r.listing_id == listing_id]
            total_rating = sum(r.rating for r in listing_reviews)
            listing.rating = total_rating / len(listing_reviews)
            listing.review_count = len(listing_reviews)
        
        logger.info(f"创建评价: {review_id} for {listing_id}")
        return review
    
    def get_listing_reviews(
        self,
        listing_id: str,
        sort_by: str = "recent",
        limit: int = 20
    ) -> List[Review]:
        """获取商品评价"""
        reviews = [r for r in self.reviews.values() if r.listing_id == listing_id]
        
        if sort_by == "recent":
            reviews.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "rating_high":
            reviews.sort(key=lambda x: x.rating, reverse=True)
        elif sort_by == "helpful":
            reviews.sort(key=lambda x: x.helpful_count, reverse=True)
        
        return reviews[:limit]
    
    # ============================================================
    # 交易管理
    # ============================================================
    
    def create_purchase(
        self,
        listing_id: str,
        buyer_id: str,
        payment_method: str = "wallet"
    ) -> Transaction:
        """
        创建购买
        
        Args:
            listing_id: 商品ID
            buyer_id: 买家ID
            payment_method: 支付方式
        
        Returns:
            Transaction: 交易记录
        """
        listing = self.listings.get(listing_id)
        if not listing:
            raise ValueError(f"商品不存在: {listing_id}")
        
        transaction_id = f"txn_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        transaction = Transaction(
            transaction_id=transaction_id,
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=listing.seller_id,
            amount=listing.price,
            currency=listing.currency,
            transaction_type="purchase",
            status="completed"
        )
        
        self.transactions[transaction_id] = transaction
        
        # 更新销售数量
        listing.sales_count += 1
        
        logger.info(f"创建交易: {transaction_id}")
        return transaction
    
    # ============================================================
    # 统计与分析
    # ============================================================
    
    def get_market_stats(self) -> Dict[str, Any]:
        """获取市场统计"""
        listings = list(self.listings.values())
        
        total_sales = sum(l.sales_count for l in listings)
        avg_rating = sum(l.rating for l in listings) / len(listings) if listings else 0
        
        return {
            "total_listings": len(listings),
            "active_listings": len([l for l in listings if l.status == ListingStatus.ACTIVE]),
            "total_sales": total_sales,
            "average_rating": round(avg_rating, 2),
            "categories": {cat: len([l for l in listings if l.category == cat]) for cat in self.categories},
            "updated_at": datetime.now().isoformat()
        }
    
    # ============================================================
    # 状态查询
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "module": "AvatarMarket",
            "version": "3.0.0",
            "status": "active",
            "total_listings": len(self.listings),
            "total_reviews": len(self.reviews),
            "total_transactions": len(self.transactions),
            "categories": len(self.categories),
            "uptime": datetime.now().isoformat()
        }


# 导出类
__all__ = [
    "AvatarMarket",
    "AvatarListing",
    "Review",
    "Transaction",
    "ListingType",
    "PricingModel",
    "ListingStatus"
]
