#!/usr/bin/env python3
"""
AI分身个性化定制市场服务

支持用户自定义专属AI分身（人设、能力、任务模板）、
一键部署、共享模板，建立完整的AI分身生态系统。
"""

import os
import json
import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import re

# 导入现有系统模块
try:
    from src.global_orchestrator.core_scheduler import TaskType, TaskStatus
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False
    logging.warning("统一调度器模块未找到，相关功能将受限")

try:
    from src.business_analysis.avatar_analysis import AvatarAnalyzer
    HAS_AVATAR_ANALYSIS = True
except ImportError:
    HAS_AVATAR_ANALYSIS = False
    logging.warning("分身分析模块未找到，相关功能将受限")


class AvatarCategory(Enum):
    """分身类别枚举"""
    ECOMMERCE = "ecommerce"  # 电商运营
    CONTENT_CREATION = "content_creation"  # 内容创作
    SOCIAL_MEDIA = "social_media"  # 社交媒体
    CUSTOMER_SERVICE = "customer_service"  # 客户服务
    BUSINESS_DEVELOPMENT = "business_development"  # 业务开发
    DATA_ANALYSIS = "data_analysis"  # 数据分析
    CREATIVE_DESIGN = "creative_design"  # 创意设计
    TECHNICAL_SUPPORT = "technical_support"  # 技术支持


class AvatarSkillLevel(Enum):
    """技能等级枚举"""
    BEGINNER = "beginner"  # 初级
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"  # 高级
    EXPERT = "expert"  # 专家


class AvatarLicenseType(Enum):
    """许可类型枚举"""
    FREE = "free"  # 免费
    PREMIUM = "premium"  # 高级
    ENTERPRISE = "enterprise"  # 企业
    CUSTOM = "custom"  # 定制


@dataclass
class AvatarSkill:
    """分身技能"""
    skill_id: str
    name: str
    category: str
    level: AvatarSkillLevel
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AvatarTemplate:
    """分身模板"""
    template_id: str
    name: str
    description: str
    category: AvatarCategory
    skills: List[AvatarSkill]
    creator_id: str
    creator_name: str
    license_type: AvatarLicenseType
    price_usd: float = 0.0
    rating: float = 5.0
    rating_count: int = 0
    downloads: int = 0
    tags: List[str] = field(default_factory=list)
    config_json: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    is_public: bool = True
    is_official: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['skills'] = [skill.to_dict() for skill in self.skills]
        return data


@dataclass
class AvatarCustomization:
    """分身定制配置"""
    avatar_id: str
    name: str
    persona: Dict[str, Any]  # 人设配置
    capabilities: List[Dict[str, Any]]  # 能力配置
    task_templates: List[Dict[str, Any]]  # 任务模板
    style_preferences: Dict[str, Any]  # 风格偏好
    integration_config: Dict[str, Any]  # 集成配置
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class MarketplaceListing:
    """市场列表项"""
    listing_id: str
    template_id: str
    seller_id: str
    seller_name: str
    title: str
    description: str
    price_usd: float
    currency: str = "USD"
    category: str = AvatarCategory.ECOMMERCE.value
    tags: List[str] = field(default_factory=list)
    reviews: List[Dict[str, Any]] = field(default_factory=list)
    average_rating: float = 0.0
    review_count: int = 0
    sales_count: int = 0
    is_featured: bool = False
    is_verified: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class AvatarPurchase:
    """分身购买记录"""
    purchase_id: str
    listing_id: str
    buyer_id: str
    seller_id: str
    template_id: str
    price_usd: float
    transaction_id: Optional[str] = None
    status: str = "completed"
    purchased_at: float = field(default_factory=time.time)
    activated_at: Optional[float] = None
    license_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AvatarMarketplaceService:
    """AI分身个性化定制市场服务"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化市场服务
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.is_running = False
        self.start_time = time.time()
        
        # 数据存储
        self.templates: Dict[str, AvatarTemplate] = {}
        self.listings: Dict[str, MarketplaceListing] = {}
        self.purchases: Dict[str, AvatarPurchase] = {}
        self.customizations: Dict[str, AvatarCustomization] = {}
        
        # 初始化官方模板
        self._init_official_templates()
        
        # 初始化分析服务
        self.avatar_analyzer = None
        if HAS_AVATAR_ANALYSIS:
            self.avatar_analyzer = AvatarAnalyzer()
        
        self._setup_logging()
        self._load_data()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置"""
        default_config = {
            'marketplace_name': 'SellAI Avatar Marketplace',
            'commission_rate': 0.15,  # 15%平台佣金
            'min_listing_price': 9.99,
            'max_listing_price': 999.99,
            'default_currency': 'USD',
            'supported_categories': [cat.value for cat in AvatarCategory],
            'rating_system': {
                'min_rating': 1,
                'max_rating': 5,
                'require_verification': True
            },
            'license_terms': {
                'free': {'usage_limit': 'non-commercial', 'redistribution': False},
                'premium': {'usage_limit': 'commercial', 'redistribution': False},
                'enterprise': {'usage_limit': 'unlimited', 'redistribution': True},
                'custom': {'usage_limit': 'negotiable', 'redistribution': 'negotiable'}
            },
            'data_storage': {
                'backup_interval': 3600,  # 每小时备份
                'encryption_enabled': True
            },
            'logging_level': 'INFO'
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logging.warning(f"加载配置文件失败: {str(e)}")
        
        return default_config
    
    def _init_official_templates(self):
        """初始化官方模板"""
        official_templates = [
            {
                'template_id': 'official_ecommerce_001',
                'name': '电商全能运营专家',
                'description': '专为电商场景定制的全能运营分身，支持产品选品、营销策划、客户服务、数据分析等全流程',
                'category': AvatarCategory.ECOMMERCE,
                'skills': [
                    AvatarSkill('skill_001', '产品选品分析', 'ecommerce', AvatarSkillLevel.EXPERT,
                               '基于市场趋势和竞品分析的智能选品'),
                    AvatarSkill('skill_002', '营销活动策划', 'marketing', AvatarSkillLevel.ADVANCED,
                               '节日促销、品牌日、限时折扣等营销活动策划'),
                    AvatarSkill('skill_003', '客户关系管理', 'customer_service', AvatarSkillLevel.ADVANCED,
                               '客户咨询、投诉处理、满意度提升')
                ],
                'creator_id': 'sellai_official',
                'creator_name': 'SellAI官方',
                'license_type': AvatarLicenseType.FREE,
                'price_usd': 0.0,
                'is_official': True
            },
            {
                'template_id': 'official_content_001',
                'name': '多平台内容创作大师',
                'description': '专业的内容创作分身，支持多平台（TikTok、YouTube、小红书等）的内容策划、文案撰写、视觉设计',
                'category': AvatarCategory.CONTENT_CREATION,
                'skills': [
                    AvatarSkill('skill_101', '短视频脚本创作', 'content', AvatarSkillLevel.EXPERT,
                               '爆款短视频脚本，适配平台算法'),
                    AvatarSkill('skill_102', '图文内容策划', 'content', AvatarSkillLevel.ADVANCED,
                               '小红书、公众号等图文平台的内容策划'),
                    AvatarSkill('skill_103', '视觉设计指导', 'design', AvatarSkillLevel.INTERMEDIATE,
                               '图片风格、排版、色彩搭配指导')
                ],
                'creator_id': 'sellai_official',
                'creator_name': 'SellAI官方',
                'license_type': AvatarLicenseType.PREMIUM,
                'price_usd': 49.99,
                'is_official': True
            },
            {
                'template_id': 'official_social_001',
                'name': '社交媒体增长黑客',
                'description': '专为社交媒体增长定制的分身，支持多平台账号运营、粉丝互动、热点追蹤、增长策略',
                'category': AvatarCategory.SOCIAL_MEDIA,
                'skills': [
                    AvatarSkill('skill_201', '粉丝互动策略', 'social', AvatarSkillLevel.ADVANCED,
                               '提升粉丝活跃度和忠诚度的互动策略'),
                    AvatarSkill('skill_202', '热点内容创作', 'content', AvatarSkillLevel.ADVANCED,
                               '基于实时热点的快速内容创作'),
                    AvatarSkill('skill_203', '增长数据分析', 'analytics', AvatarSkillLevel.INTERMEDIATE,
                               '社交媒体增长数据分析和优化建议')
                ],
                'creator_id': 'sellai_official',
                'creator_name': 'SellAI官方',
                'license_type': AvatarLicenseType.PREMIUM,
                'price_usd': 79.99,
                'is_official': True
            }
        ]
        
        for template_data in official_templates:
            template = AvatarTemplate(**template_data)
            self.templates[template.template_id] = template
    
    def _setup_logging(self):
        """设置日志"""
        log_level = getattr(logging, self.config['logging_level'].upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - AVATAR-MARKET - %(levelname)s - %(message)s'
        )
    
    def _load_data(self):
        """加载数据"""
        data_dir = "data/avatar_market"
        os.makedirs(data_dir, exist_ok=True)
        
        # 加载模板数据
        templates_file = os.path.join(data_dir, "templates.json")
        if os.path.exists(templates_file):
            try:
                with open(templates_file, 'r') as f:
                    templates_data = json.load(f)
                for template_id, template_data in templates_data.items():
                    # 转换技能数据
                    skills_data = template_data.get('skills', [])
                    skills = []
                    for skill_data in skills_data:
                        skill_data['level'] = AvatarSkillLevel(skill_data['level'])
                        skills.append(AvatarSkill(**skill_data))
                    
                    template_data['skills'] = skills
                    template_data['category'] = AvatarCategory(template_data['category'])
                    template_data['license_type'] = AvatarLicenseType(template_data['license_type'])
                    self.templates[template_id] = AvatarTemplate(**template_data)
            except Exception as e:
                logging.warning(f"加载模板数据失败: {str(e)}")
        
        # 加载列表数据
        listings_file = os.path.join(data_dir, "listings.json")
        if os.path.exists(listings_file):
            try:
                with open(listings_file, 'r') as f:
                    listings_data = json.load(f)
                for listing_id, listing_data in listings_data.items():
                    self.listings[listing_id] = MarketplaceListing(**listing_data)
            except Exception as e:
                logging.warning(f"加载列表数据失败: {str(e)}")
        
        # 加载购买记录
        purchases_file = os.path.join(data_dir, "purchases.json")
        if os.path.exists(purchases_file):
            try:
                with open(purchases_file, 'r') as f:
                    purchases_data = json.load(f)
                for purchase_id, purchase_data in purchases_data.items():
                    self.purchases[purchase_id] = AvatarPurchase(**purchase_data)
            except Exception as e:
                logging.warning(f"加载购买记录失败: {str(e)}")
    
    def _save_data(self):
        """保存数据"""
        data_dir = "data/avatar_market"
        os.makedirs(data_dir, exist_ok=True)
        
        # 保存模板数据
        templates_data = {}
        for template_id, template in self.templates.items():
            template_dict = template.to_dict()
            template_dict['category'] = template_dict['category'].value
            template_dict['license_type'] = template_dict['license_type'].value
            templates_data[template_id] = template_dict
        
        with open(os.path.join(data_dir, "templates.json"), 'w') as f:
            json.dump(templates_data, f, indent=2, default=str)
        
        # 保存列表数据
        listings_data = {lid: asdict(listing) for lid, listing in self.listings.items()}
        with open(os.path.join(data_dir, "listings.json"), 'w') as f:
            json.dump(listings_data, f, indent=2, default=str)
        
        # 保存购买记录
        purchases_data = {pid: asdict(purchase) for pid, purchase in self.purchases.items()}
        with open(os.path.join(data_dir, "purchases.json"), 'w') as f:
            json.dump(purchases_data, f, indent=2, default=str)
    
    def start(self) -> bool:
        """启动市场服务"""
        if self.is_running:
            return True
        
        try:
            self.is_running = True
            self.start_time = time.time()
            logging.info(f"AI分身个性化定制市场服务启动成功，模板数量: {len(self.templates)}")
            return True
            
        except Exception as e:
            logging.error(f"市场服务启动失败: {str(e)}")
            return False
    
    def create_template(self, template_data: Dict[str, Any]) -> Optional[AvatarTemplate]:
        """
        创建分身模板
        
        Args:
            template_data: 模板数据
            
        Returns:
            创建的模板，失败返回None
        """
        try:
            # 验证数据
            required_fields = ['name', 'description', 'category', 'creator_id', 'creator_name', 'license_type']
            for field in required_fields:
                if field not in template_data:
                    raise ValueError(f"缺少必要字段: {field}")
            
            # 生成ID
            template_id = f"template_{uuid.uuid4().hex[:8]}"
            if 'template_id' not in template_data:
                template_data['template_id'] = template_id
            
            # 转换枚举
            template_data['category'] = AvatarCategory(template_data['category'])
            template_data['license_type'] = AvatarLicenseType(template_data['license_type'])
            
            # 处理技能
            skills_data = template_data.get('skills', [])
            skills = []
            for skill_data in skills_data:
                skill_data['level'] = AvatarSkillLevel(skill_data['level'])
                skills.append(AvatarSkill(**skill_data))
            template_data['skills'] = skills
            
            # 创建模板
            template = AvatarTemplate(**template_data)
            self.templates[template.template_id] = template
            
            # 保存数据
            self._save_data()
            
            logging.info(f"创建分身模板成功: {template.name} (ID: {template.template_id})")
            return template
            
        except Exception as e:
            logging.error(f"创建分身模板失败: {str(e)}")
            return None
    
    def list_template(self, template_id: str, seller_id: str, seller_name: str, 
                      title: str, description: str, price_usd: float) -> Optional[MarketplaceListing]:
        """
        将模板上架到市场
        
        Args:
            template_id: 模板ID
            seller_id: 卖家ID
            seller_name: 卖家名称
            title: 列表标题
            description: 列表描述
            price_usd: 价格（美元）
            
        Returns:
            创建的列表，失败返回None
        """
        try:
            # 验证模板存在
            if template_id not in self.templates:
                raise ValueError(f"模板不存在: {template_id}")
            
            # 验证价格
            if price_usd < self.config['min_listing_price']:
                raise ValueError(f"价格不能低于 {self.config['min_listing_price']} USD")
            if price_usd > self.config['max_listing_price']:
                raise ValueError(f"价格不能高于 {self.config['max_listing_price']} USD")
            
            # 生成列表ID
            listing_id = f"listing_{uuid.uuid4().hex[:8]}"
            
            # 获取模板信息
            template = self.templates[template_id]
            
            # 创建列表
            listing = MarketplaceListing(
                listing_id=listing_id,
                template_id=template_id,
                seller_id=seller_id,
                seller_name=seller_name,
                title=title,
                description=description,
                price_usd=price_usd,
                category=template.category.value,
                tags=template.tags
            )
            
            self.listings[listing.listing_id] = listing
            
            # 保存数据
            self._save_data()
            
            logging.info(f"模板上架成功: {title} (价格: {price_usd} USD)")
            return listing
            
        except Exception as e:
            logging.error(f"模板上架失败: {str(e)}")
            return None
    
    def purchase_avatar(self, listing_id: str, buyer_id: str, 
                        payment_method: str = "stripe") -> Optional[AvatarPurchase]:
        """
        购买分身
        
        Args:
            listing_id: 列表ID
            buyer_id: 买家ID
            payment_method: 支付方式
            
        Returns:
            购买记录，失败返回None
        """
        try:
            # 验证列表存在
            if listing_id not in self.listings:
                raise ValueError(f"列表不存在: {listing_id}")
            
            listing = self.listings[listing_id]
            
            # 模拟支付处理
            time.sleep(0.5)
            
            # 生成购买记录
            purchase_id = f"purchase_{uuid.uuid4().hex[:8]}"
            transaction_id = f"txn_{uuid.uuid4().hex[:16]}"
            license_key = f"LIC_{uuid.uuid4().hex[:12]}"
            
            purchase = AvatarPurchase(
                purchase_id=purchase_id,
                listing_id=listing_id,
                buyer_id=buyer_id,
                seller_id=listing.seller_id,
                template_id=listing.template_id,
                price_usd=listing.price_usd,
                transaction_id=transaction_id,
                status="completed",
                license_key=license_key,
                metadata={
                    'payment_method': payment_method,
                    'purchase_time': datetime.now().isoformat()
                }
            )
            
            self.purchases[purchase.purchase_id] = purchase
            
            # 更新列表销售数据
            listing.sales_count += 1
            
            # 保存数据
            self._save_data()
            
            logging.info(f"分身购买成功: {listing.title} (买家: {buyer_id}, 价格: {listing.price_usd} USD)")
            return purchase
            
        except Exception as e:
            logging.error(f"分身购买失败: {str(e)}")
            return None
    
    def customize_avatar(self, template_id: str, user_id: str,
                        customization_data: Dict[str, Any]) -> Optional[AvatarCustomization]:
        """
        定制分身
        
        Args:
            template_id: 模板ID
            user_id: 用户ID
            customization_data: 定制配置
            
        Returns:
            定制配置，失败返回None
        """
        try:
            # 验证模板存在
            if template_id not in self.templates:
                raise ValueError(f"模板不存在: {template_id}")
            
            # 生成分身ID
            avatar_id = f"avatar_{uuid.uuid4().hex[:8]}"
            
            # 创建定制配置
            customization = AvatarCustomization(
                avatar_id=avatar_id,
                name=customization_data.get('name', f"定制分身_{avatar_id}"),
                persona=customization_data.get('persona', {}),
                capabilities=customization_data.get('capabilities', []),
                task_templates=customization_data.get('task_templates', []),
                style_preferences=customization_data.get('style_preferences', {}),
                integration_config=customization_data.get('integration_config', {}),
                metadata={
                    'template_id': template_id,
                    'user_id': user_id,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            self.customizations[avatar_id] = customization
            
            # 保存数据
            self._save_data()
            
            logging.info(f"分身定制成功: {customization.name} (用户: {user_id})")
            return customization
            
        except Exception as e:
            logging.error(f"分身定制失败: {str(e)}")
            return None
    
    def deploy_avatar(self, avatar_id: str) -> Optional[Dict[str, Any]]:
        """
        一键部署分身
        
        Args:
            avatar_id: 分身ID
            
        Returns:
            部署结果，失败返回None
        """
        try:
            # 验证定制配置存在
            if avatar_id not in self.customizations:
                raise ValueError(f"分身不存在: {avatar_id}")
            
            customization = self.customizations[avatar_id]
            
            # 模拟部署过程
            time.sleep(1.0)
            
            # 生成部署配置
            deployment_config = {
                'deployment_id': f"deploy_{uuid.uuid4().hex[:8]}",
                'avatar_id': avatar_id,
                'template_id': customization.metadata['template_id'],
                'user_id': customization.metadata['user_id'],
                'deployed_at': time.time(),
                'endpoints': {
                    'api_endpoint': f"/api/avatars/{avatar_id}",
                    'chat_endpoint': f"/chat/{avatar_id}",
                    'status_endpoint': f"/status/{avatar_id}"
                },
                'resources': {
                    'memory_limit': '512MB',
                    'cpu_limit': '0.5',
                    'storage_limit': '1GB'
                },
                'monitoring': {
                    'enabled': True,
                    'metrics_endpoint': f"/metrics/{avatar_id}"
                }
            }
            
            logging.info(f"分身部署成功: {customization.name} (部署ID: {deployment_config['deployment_id']})")
            return deployment_config
            
        except Exception as e:
            logging.error(f"分身部署失败: {str(e)}")
            return None
    
    def search_templates(self, query: Optional[str] = None,
                        category: Optional[str] = None,
                        min_price: Optional[float] = None,
                        max_price: Optional[float] = None,
                        min_rating: Optional[float] = None,
                        limit: int = 20) -> List[AvatarTemplate]:
        """
        搜索模板
        
        Args:
            query: 搜索关键词
            category: 类别过滤
            min_price: 最低价格
            max_price: 最高价格
            min_rating: 最低评分
            limit: 返回数量限制
            
        Returns:
            模板列表
        """
        results = []
        
        for template in self.templates.values():
            # 类别过滤
            if category and template.category.value != category:
                continue
            
            # 价格过滤
            if min_price is not None and template.price_usd < min_price:
                continue
            if max_price is not None and template.price_usd > max_price:
                continue
            
            # 评分过滤
            if min_rating is not None and template.rating < min_rating:
                continue
            
            # 关键词搜索
            if query:
                search_fields = [template.name, template.description, ' '.join(template.tags)]
                search_text = ' '.join([str(f) for f in search_fields]).lower()
                if query.lower() not in search_text:
                    continue
            
            results.append(template)
        
        # 排序：官方优先，然后按评分降序，再按下载量降序
        results.sort(key=lambda t: (
            -1 if t.is_official else 0,
            t.rating,
            t.downloads
        ), reverse=True)
        
        return results[:limit]
    
    def get_template_stats(self) -> Dict[str, Any]:
        """获取模板统计信息"""
        total_templates = len(self.templates)
        official_templates = sum(1 for t in self.templates.values() if t.is_official)
        user_templates = total_templates - official_templates
        
        # 按类别统计
        category_stats = {}
        for template in self.templates.values():
            cat = template.category.value
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        # 按许可类型统计
        license_stats = {}
        for template in self.templates.values():
            lic = template.license_type.value
            license_stats[lic] = license_stats.get(lic, 0) + 1
        
        return {
            'total_templates': total_templates,
            'official_templates': official_templates,
            'user_templates': user_templates,
            'category_distribution': category_stats,
            'license_distribution': license_stats,
            'total_downloads': sum(t.downloads for t in self.templates.values())
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'is_running': self.is_running,
            'start_time': self.start_time,
            'uptime': time.time() - self.start_time,
            'templates_count': len(self.templates),
            'listings_count': len(self.listings),
            'purchases_count': len(self.purchases),
            'customizations_count': len(self.customizations),
            'marketplace_name': self.config['marketplace_name']
        }
    
    def stop(self):
        """停止服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        logging.info("AI分身个性化定制市场服务已停止")


# 工厂函数
def create_marketplace_service(config_path: Optional[str] = None) -> AvatarMarketplaceService:
    """创建市场服务实例"""
    return AvatarMarketplaceService(config_path)


if __name__ == "__main__":
    """测试市场服务"""
    
    print("AI分身个性化定制市场服务测试")
    print("=" * 60)
    
    # 创建服务实例
    marketplace = create_marketplace_service()
    
    # 启动服务
    if marketplace.start():
        print("✅ 市场服务启动成功")
        
        # 测试服务状态
        status = marketplace.get_service_status()
        print(f"服务状态: 运行中={status['is_running']}, 模板数量={status['templates_count']}")
        
        # 测试模板创建
        new_template_data = {
            'name': '跨境电商营销专家',
            'description': '专为跨境电商设计的营销分身，支持多平台广告投放、内容本地化、跨境支付整合',
            'category': AvatarCategory.ECOMMERCE.value,
            'creator_id': 'user_001',
            'creator_name': '开发者用户',
            'license_type': AvatarLicenseType.PREMIUM.value,
            'price_usd': 89.99,
            'skills': [
                {
                    'skill_id': 'user_skill_001',
                    'name': '跨境广告投放',
                    'category': 'marketing',
                    'level': AvatarSkillLevel.ADVANCED.value,
                    'description': 'Facebook、Google、TikTok跨境广告投放策略'
                },
                {
                    'skill_id': 'user_skill_002',
                    'name': '多语种内容本地化',
                    'category': 'content',
                    'level': AvatarSkillLevel.INTERMEDIATE.value,
                    'description': '英文、西班牙语、法语内容本地化适配'
                }
            ]
        }
        
        new_template = marketplace.create_template(new_template_data)
        if new_template:
            print(f"\n✅ 用户模板创建成功: {new_template.name}")
            print(f"   模板ID: {new_template.template_id}")
            print(f"   技能数量: {len(new_template.skills)}")
        
        # 测试模板上架
        if new_template:
            listing = marketplace.list_template(
                template_id=new_template.template_id,
                seller_id='user_001',
                seller_name='开发者用户',
                title='跨境电商营销专家 - 专业版',
                description='专为跨境电商设计的全能营销分身，包含广告投放、内容本地化、支付整合等高级功能',
                price_usd=89.99
            )
            
            if listing:
                print(f"\n✅ 模板上架成功: {listing.title}")
                print(f"   列表ID: {listing.listing_id}")
                print(f"   价格: {listing.price_usd} USD")
        
        # 测试分身购买
        if listing:
            purchase = marketplace.purchase_avatar(
                listing_id=listing.listing_id,
                buyer_id='buyer_001'
            )
            
            if purchase:
                print(f"\n✅ 分身购买成功: 购买ID {purchase.purchase_id}")
                print(f"   交易ID: {purchase.transaction_id}")
                print(f"   价格: {purchase.price_usd} USD")
                print(f"   许可密钥: {purchase.license_key}")
        
        # 测试分身定制
        customization = marketplace.customize_avatar(
            template_id='official_ecommerce_001',
            user_id='user_001',
            customization_data={
                'name': '我的专属电商助手',
                'persona': {
                    'name': '电商专家Alex',
                    'gender': 'male',
                    'age': 35,
                    'specialty': '跨境电商运营'
                },
                'capabilities': [
                    {'name': '产品选品', 'level': 'expert'},
                    {'name': '广告投放', 'level': 'advanced'},
                    {'name': '客户服务', 'level': 'intermediate'}
                ],
                'style_preferences': {
                    'communication_style': 'professional_friendly',
                    'response_speed': 'fast',
                    'detail_level': 'comprehensive'
                }
            }
        )
        
        if customization:
            print(f"\n✅ 分身定制成功: {customization.name}")
            print(f"   分身ID: {customization.avatar_id}")
        
        # 测试分身部署
        if customization:
            deployment = marketplace.deploy_avatar(customization.avatar_id)
            if deployment:
                print(f"\n✅ 分身部署成功: 部署ID {deployment['deployment_id']}")
                print(f"   API端点: {deployment['endpoints']['api_endpoint']}")
        
        # 获取统计信息
        stats = marketplace.get_template_stats()
        print(f"\n📊 市场统计:")
        print(f"   总模板数: {stats['total_templates']}")
        print(f"   官方模板: {stats['official_templates']}")
        print(f"   用户模板: {stats['user_templates']}")
        print(f"   总下载量: {stats['total_downloads']}")
        
        # 停止服务
        marketplace.stop()
        print("\n🛑 市场服务已停止")
        
    else:
        print("❌ 市场服务启动失败")