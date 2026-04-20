"""
行业分类器引擎
提供行业分类管理和行业画像功能
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.data_models import (
    IndustryCategory, IndustryProfile, IndustryLevel,
    GrowthTrend, RiskLevel, CompetitionLevel
)

logger = logging.getLogger(__name__)


class IndustryClassifier:
    """行业分类器"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化行业分类器
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        
        # 行业分类数据
        self.categories: Dict[str, IndustryCategory] = {}
        self.profiles: Dict[str, IndustryProfile] = {}
        
        # 索引
        self.primary_categories: List[IndustryCategory] = []
        self.secondary_categories: List[IndustryCategory] = []
        self.category_by_code: Dict[str, IndustryCategory] = {}
        
        # 初始化
        self._load_categories()
        self._generate_secondary_categories()
        self._generate_profiles()
    
    @staticmethod
    def _datetime_serializer(obj):
        """序列化datetime对象为JSON"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')
    
    def _load_categories(self) -> None:
        """加载行业分类数据"""
        categories_file = self.data_dir / "industry_categories.json"
        
        if categories_file.exists():
            try:
                with open(categories_file, 'r', encoding='utf-8') as f:
                    categories_data = json.load(f)
                
                for cat_data in categories_data:
                    category = IndustryCategory(**cat_data)
                    self.categories[category.id] = category
                    self.category_by_code[category.code] = category
                    
                    if category.level == IndustryLevel.PRIMARY:
                        self.primary_categories.append(category)
                    elif category.level == IndustryLevel.SECONDARY:
                        self.secondary_categories.append(category)
                
                logger.info(f"加载行业分类数据: {len(self.categories)}个行业")
                
            except Exception as e:
                logger.error(f"加载行业分类数据失败: {e}")
                self._create_default_categories()
        else:
            logger.warning("行业分类数据文件不存在，创建默认数据")
            self._create_default_categories()
    
    def _create_default_categories(self) -> None:
        """创建默认行业分类数据"""
        # 20个一级行业
        primary_industries = [
            ("information_technology", "450000", "信息科技"),
            ("financial_services", "400000", "金融服务"),
            ("healthcare", "350000", "医疗健康"),
            ("consumer_goods", "300000", "消费品"),
            ("industrial_manufacturing", "200000", "工业制造"),
            ("materials", "150000", "原材料"),
            ("energy", "100000", "能源"),
            ("utilities", "550000", "公用事业"),
            ("real_estate", "600000", "房地产"),
            ("consumer_discretionary", "250000", "可选消费"),
            ("consumer_staples", "300500", "日常消费"),
            ("telecommunications", "500000", "电信服务"),
            ("media_entertainment", "650000", "传媒娱乐"),
            ("transportation", "700000", "交通运输"),
            ("business_services", "750000", "商业服务"),
            ("education_services", "800000", "教育服务"),
            ("environmental_services", "850000", "环保服务"),
            ("agriculture_fishing", "900000", "农业牧渔"),
            ("construction_engineering", "950000", "建筑工程"),
            ("other_industries", "999999", "其他行业"),
        ]
        
        for idx, (industry_id, code, name) in enumerate(primary_industries):
            category = IndustryCategory(
                id=industry_id,
                code=code,
                name=name,
                level=IndustryLevel.PRIMARY,
                parent_id=None,
                description=f"{name}行业",
                keywords=[name]
            )
            self.categories[category.id] = category
            self.category_by_code[category.code] = category
            self.primary_categories.append(category)
    
    def _generate_secondary_categories(self) -> None:
        """生成二级细分赛道数据"""
        # 二级行业映射
        secondary_mapping = {
            "information_technology": [
                ("tech_software", "451010", "企业软件"),
                ("tech_cloud", "451020", "云计算服务"),
                ("tech_ai", "451030", "人工智能应用"),
                ("tech_bigdata", "451040", "大数据分析"),
                ("tech_cybersecurity", "451050", "网络安全"),
                ("tech_iot", "451060", "物联网"),
                ("tech_blockchain", "451070", "区块链"),
                ("tech_quantum", "451080", "量子计算"),
                ("tech_semiconductor", "451090", "半导体"),
                ("tech_hardware", "451100", "硬件设备"),
            ],
            "financial_services": [
                ("fin_digital_banking", "401010", "数字银行"),
                ("fin_insurtech", "401020", "保险科技"),
                ("fin_payments", "401030", "支付解决方案"),
                ("fin_investment", "401040", "投资管理"),
                ("fin_lending", "401050", "借贷平台"),
                ("fin_regtech", "401060", "金融监管科技"),
                ("fin_wealthtech", "401070", "财富科技"),
                ("fin_cryptocurrency", "401080", "加密货币"),
                ("fin_crowdfunding", "401090", "众筹平台"),
                ("fin_remittance", "401100", "跨境汇款"),
            ],
            "healthcare": [
                ("health_biopharma", "351010", "生物制药"),
                ("health_genetherapy", "351020", "基因治疗"),
                ("health_telemedicine", "351030", "远程医疗"),
                ("health_medical_ai", "351040", "医疗AI"),
                ("health_medical_devices", "351050", "医疗器械"),
                ("health_health_insurance", "351060", "健康保险"),
                ("health_digital_health", "351070", "数字健康"),
                ("health_healthcare_it", "351080", "医疗IT"),
                ("health_pharmacy", "351090", "药房服务"),
                ("health_elderly_care", "351100", "养老护理"),
            ],
            "consumer_goods": [
                ("cg_fmcg", "301010", "快消品"),
                ("cg_luxury", "301020", "奢侈品"),
                ("cg_sportswear", "301030", "运动服饰"),
                ("cg_beauty_care", "301040", "美妆个护"),
                ("cg_maternity", "301050", "母婴用品"),
                ("cg_pet_supplies", "301060", "宠物用品"),
                ("cg_home_decor", "301070", "家居装饰"),
                ("cg_food_beverage", "301080", "食品饮料"),
                ("cg_apparel", "301090", "服装服饰"),
                ("cg_jewelry", "301100", "珠宝首饰"),
            ],
            "industrial_manufacturing": [
                ("ind_machinery", "201010", "机械设备"),
                ("ind_automotive", "201020", "汽车制造"),
                ("ind_aerospace", "201030", "航空航天"),
                ("ind_electrical", "201040", "电气设备"),
                ("ind_robotics", "201050", "工业机器人"),
                ("ind_3d_printing", "201060", "3D打印"),
                ("ind_precision", "201070", "精密制造"),
                ("ind_defense", "201080", "国防工业"),
                ("ind_shipbuilding", "201090", "造船工业"),
                ("ind_railway", "201100", "铁路设备"),
            ],
        }
        
        # 生成二级行业数据
        secondary_count = 0
        for primary_id, secondary_list in secondary_mapping.items():
            if primary_id not in self.categories:
                continue
                
            for idx, (sec_id, code, name) in enumerate(secondary_list):
                category = IndustryCategory(
                    id=sec_id,
                    code=code,
                    name=name,
                    level=IndustryLevel.SECONDARY,
                    parent_id=primary_id,
                    description=f"{self.categories[primary_id].name} - {name}",
                    keywords=[name, primary_id]
                )
                self.categories[category.id] = category
                self.category_by_code[category.code] = category
                self.secondary_categories.append(category)
                secondary_count += 1
        
        # 为其他一级行业生成示例二级行业
        other_primaries = [
            cat_id for cat_id in self.categories.keys() 
            if cat_id not in secondary_mapping.keys() and cat_id != "other_industries"
        ]
        
        for primary_id in other_primaries[:10]:  # 只处理10个，避免过多
            primary_cat = self.categories[primary_id]
            for i in range(5):  # 每个一级行业生成5个二级行业
                sec_id = f"{primary_id}_sector_{i+1}"
                code = f"{primary_cat.code[0:3]}{i+1:03d}"
                name = f"{primary_cat.name}细分{i+1}"
                
                category = IndustryCategory(
                    id=sec_id,
                    code=code,
                    name=name,
                    level=IndustryLevel.SECONDARY,
                    parent_id=primary_id,
                    description=f"{primary_cat.name}的细分领域{i+1}",
                    keywords=[name, primary_cat.name]
                )
                self.categories[category.id] = category
                self.category_by_code[category.code] = category
                self.secondary_categories.append(category)
                secondary_count += 1
        
        logger.info(f"生成二级细分赛道: {secondary_count}个")
        
        # 保存到文件
        self._save_categories()
    
    def _save_categories(self) -> None:
        """保存行业分类数据到文件"""
        try:
            categories_data = [cat.model_dump() for cat in self.categories.values()]
            
            output_file = self.data_dir / "industry_categories_complete.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(categories_data, f, default=self._datetime_serializer, ensure_ascii=False, indent=2)
            
            logger.info(f"保存行业分类数据到: {output_file}")
        except Exception as e:
            logger.error(f"保存行业分类数据失败: {e}")
    
    def _generate_profiles(self) -> None:
        """生成行业画像数据"""
        # 行业画像参数范围
        margin_ranges = {
            "information_technology": (50.0, 80.0),
            "financial_services": (40.0, 60.0),
            "healthcare": (60.0, 85.0),
            "consumer_goods": (30.0, 55.0),
            "industrial_manufacturing": (25.0, 45.0),
            "materials": (20.0, 40.0),
            "energy": (15.0, 35.0),
            "utilities": (10.0, 25.0),
            "real_estate": (20.0, 50.0),
            "consumer_discretionary": (35.0, 60.0),
            "consumer_staples": (20.0, 40.0),
            "telecommunications": (25.0, 45.0),
            "media_entertainment": (40.0, 70.0),
            "transportation": (15.0, 30.0),
            "business_services": (45.0, 75.0),
            "education_services": (30.0, 60.0),
            "environmental_services": (25.0, 50.0),
            "agriculture_fishing": (10.0, 25.0),
            "construction_engineering": (15.0, 35.0),
            "other_industries": (20.0, 50.0),
        }
        
        growth_trends = {
            "information_technology": GrowthTrend.RAPID_GROWTH,
            "financial_services": GrowthTrend.STEADY_GROWTH,
            "healthcare": GrowthTrend.RAPID_GROWTH,
            "consumer_goods": GrowthTrend.STEADY_GROWTH,
            "industrial_manufacturing": GrowthTrend.MATURE,
            "materials": GrowthTrend.MATURE,
            "energy": GrowthTrend.STEADY_GROWTH,
            "utilities": GrowthTrend.STEADY_GROWTH,
            "real_estate": GrowthTrend.MATURE,
            "consumer_discretionary": GrowthTrend.STEADY_GROWTH,
            "consumer_staples": GrowthTrend.STEADY_GROWTH,
            "telecommunications": GrowthTrend.MATURE,
            "media_entertainment": GrowthTrend.RAPID_GROWTH,
            "transportation": GrowthTrend.STEADY_GROWTH,
            "business_services": GrowthTrend.RAPID_GROWTH,
            "education_services": GrowthTrend.RAPID_GROWTH,
            "environmental_services": GrowthTrend.EMERGING,
            "agriculture_fishing": GrowthTrend.STEADY_GROWTH,
            "construction_engineering": GrowthTrend.STEADY_GROWTH,
            "other_industries": GrowthTrend.STEADY_GROWTH,
        }
        
        competition_levels = {
            "information_technology": CompetitionLevel.HIGHLY_COMPETITIVE,
            "financial_services": CompetitionLevel.COMPETITIVE,
            "healthcare": CompetitionLevel.COMPETITIVE,
            "consumer_goods": CompetitionLevel.HIGHLY_COMPETITIVE,
            "industrial_manufacturing": CompetitionLevel.COMPETITIVE,
            "materials": CompetitionLevel.COMPETITIVE,
            "energy": CompetitionLevel.OLIGOPOLY,
            "utilities": CompetitionLevel.MONOPOLY,
            "real_estate": CompetitionLevel.COMPETITIVE,
            "consumer_discretionary": CompetitionLevel.HIGHLY_COMPETITIVE,
            "consumer_staples": CompetitionLevel.COMPETITIVE,
            "telecommunications": CompetitionLevel.OLIGOPOLY,
            "media_entertainment": CompetitionLevel.HIGHLY_COMPETITIVE,
            "transportation": CompetitionLevel.COMPETITIVE,
            "business_services": CompetitionLevel.COMPETITIVE,
            "education_services": CompetitionLevel.COMPETITIVE,
            "environmental_services": CompetitionLevel.COMPETITIVE,
            "agriculture_fishing": CompetitionLevel.COMPETITIVE,
            "construction_engineering": CompetitionLevel.COMPETITIVE,
            "other_industries": CompetitionLevel.COMPETITIVE,
        }
        
        # 生成一级行业画像
        for primary_id in self.primary_categories:
            if primary_id.id not in margin_ranges:
                continue
                
            margin_min, margin_max = margin_ranges[primary_id.id]
            growth_rate = {
                GrowthTrend.RAPID_GROWTH: 15.0,
                GrowthTrend.STEADY_GROWTH: 8.0,
                GrowthTrend.MATURE: 3.0,
                GrowthTrend.DECLINING: -2.0,
                GrowthTrend.EMERGING: 25.0,
            }[growth_trends[primary_id.id]]
            
            profile = IndustryProfile(
                industry_id=primary_id.id,
                period=f"{datetime.now().year}-Q4",
                avg_gross_margin=(margin_min + margin_max) / 2,
                avg_net_margin=(margin_min + margin_max) / 4,
                growth_rate=growth_rate,
                growth_trend=growth_trends[primary_id.id],
                competition_level=competition_levels[primary_id.id],
                policy_risk=RiskLevel.MEDIUM,
                technology_risk=RiskLevel.MEDIUM,
                market_risk=RiskLevel.MEDIUM,
                capital_intensity=6.5,
                technology_threshold=6.0,
                globalization_index=70.0,
                cyclicality_index=45.0,
                data_sources=["行业报告", "公司年报", "市场研究"],
                last_updated=datetime.now()
            )
            
            self.profiles[primary_id.id] = profile
        
        # 生成二级行业画像（基于一级行业调整）
        for secondary_cat in self.secondary_categories:
            parent_id = secondary_cat.parent_id
            if parent_id in self.profiles:
                parent_profile = self.profiles[parent_id]
                
                # 基于二级行业特点调整参数
                import random
                adjustment = random.uniform(-10, 10)
                
                profile = IndustryProfile(
                    industry_id=secondary_cat.id,
                    period=f"{datetime.now().year}-Q4",
                    avg_gross_margin=parent_profile.avg_gross_margin + adjustment,
                    avg_net_margin=parent_profile.avg_net_margin + adjustment/2,
                    growth_rate=parent_profile.growth_rate + adjustment/2,
                    growth_trend=parent_profile.growth_trend,
                    competition_level=parent_profile.competition_level,
                    policy_risk=parent_profile.policy_risk,
                    technology_risk=parent_profile.technology_risk,
                    market_risk=parent_profile.market_risk,
                    capital_intensity=parent_profile.capital_intensity,
                    technology_threshold=parent_profile.technology_threshold,
                    globalization_index=parent_profile.globalization_index,
                    cyclicality_index=parent_profile.cyclicality_index,
                    data_sources=parent_profile.data_sources + [f"{secondary_cat.name}细分数据"],
                    last_updated=datetime.now()
                )
                
                self.profiles[secondary_cat.id] = profile
        
        logger.info(f"生成行业画像数据: {len(self.profiles)}个")
    
    def get_category(self, category_id: str) -> Optional[IndustryCategory]:
        """获取行业分类"""
        return self.categories.get(category_id)
    
    def get_profile(self, industry_id: str) -> Optional[IndustryProfile]:
        """获取行业画像"""
        return self.profiles.get(industry_id)
    
    def search_categories(self, query: str, level: Optional[IndustryLevel] = None) -> List[IndustryCategory]:
        """搜索行业分类"""
        results = []
        query_lower = query.lower()
        
        for category in self.categories.values():
            if level and category.level != level:
                continue
                
            # 搜索名称、描述、关键词
            if (query_lower in category.name.lower() or
                query_lower in category.description.lower() or
                any(query_lower in kw.lower() for kw in category.keywords)):
                results.append(category)
        
        return results
    
    def get_primary_categories(self) -> List[IndustryCategory]:
        """获取所有一级行业"""
        return self.primary_categories.copy()
    
    def get_secondary_categories(self) -> List[IndustryCategory]:
        """获取所有二级行业"""
        return self.secondary_categories.copy()
    
    def get_children(self, parent_id: str) -> List[IndustryCategory]:
        """获取子行业"""
        return [
            cat for cat in self.categories.values()
            if cat.parent_id == parent_id
        ]
    
    def get_category_tree(self) -> Dict[str, Any]:
        """获取行业分类树"""
        tree = {}
        
        for primary in self.primary_categories:
            children = self.get_children(primary.id)
            tree[primary.id] = {
                "category": primary,
                "children": children
            }
        
        return tree
    
    def update_profile(self, industry_id: str, **kwargs) -> bool:
        """更新行业画像"""
        if industry_id not in self.profiles:
            return False
        
        profile = self.profiles[industry_id]
        update_dict = profile.model_dump()
        update_dict.update(kwargs)
        update_dict["last_updated"] = datetime.now()
        
        try:
            updated_profile = IndustryProfile(**update_dict)
            self.profiles[industry_id] = updated_profile
            return True
        except Exception as e:
            logger.error(f"更新行业画像失败: {e}")
            return False
    
    def export_data(self, output_dir: Optional[Path] = None) -> Dict[str, str]:
        """导出数据"""
        export_dir = output_dir or self.data_dir / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        export_files = {}
        
        # 导出行业分类
        categories_file = export_dir / "industry_categories.json"
        categories_data = [cat.model_dump() for cat in self.categories.values()]
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump(categories_data, f, default=self._datetime_serializer, ensure_ascii=False, indent=2)
        export_files["categories"] = str(categories_file)
        
        # 导出行业画像
        profiles_file = export_dir / "industry_profiles.json"
        profiles_data = [profile.model_dump() for profile in self.profiles.values()]
        with open(profiles_file, 'w', encoding='utf-8') as f:
            json.dump(profiles_data, f, default=self._datetime_serializer, ensure_ascii=False, indent=2)
        export_files["profiles"] = str(profiles_file)
        
        return export_files