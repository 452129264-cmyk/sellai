"""
商业数据分析数据模型
定义行业分类、行业画像、利润测算、风口研判等核心数据结构
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class IndustryLevel(str, Enum):
    """行业级别"""
    PRIMARY = "primary"  # 一级行业
    SECONDARY = "secondary"  # 二级细分赛道
    TERTIARY = "tertiary"  # 三级细分领域


class GrowthTrend(str, Enum):
    """增长趋势"""
    RAPID_GROWTH = "rapid_growth"  # 快速增长
    STEADY_GROWTH = "steady_growth"  # 稳定增长
    MATURE = "mature"  # 成熟期
    DECLINING = "declining"  # 衰退期
    EMERGING = "emerging"  # 新兴期


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中等风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 极高风险


class CompetitionLevel(str, Enum):
    """竞争强度"""
    MONOPOLY = "monopoly"  # 垄断
    OLIGOPOLY = "oligopoly"  # 寡头垄断
    COMPETITIVE = "competitive"  # 充分竞争
    HIGHLY_COMPETITIVE = "highly_competitive"  # 高度竞争


class IndustryCategory(BaseModel):
    """行业分类"""
    id: str = Field(..., description="行业ID")
    code: str = Field(..., description="行业代码")
    name: str = Field(..., description="行业名称")
    level: IndustryLevel = Field(..., description="行业级别")
    parent_id: Optional[str] = Field(None, description="父级行业ID")
    description: Optional[str] = Field(None, description="行业描述")
    keywords: List[str] = Field(default_factory=list, description="行业关键词")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "tech_software",
                "code": "451010",
                "name": "企业软件",
                "level": "secondary",
                "parent_id": "information_technology",
                "description": "为企业提供各类软件解决方案和服务",
                "keywords": ["SaaS", "ERP", "CRM", "企业管理软件"]
            }
        }


class IndustryProfile(BaseModel):
    """行业画像"""
    industry_id: str = Field(..., description="行业ID")
    period: str = Field(..., description="分析周期，如2024-Q4")
    
    # 核心指标
    avg_gross_margin: float = Field(..., description="平均毛利率，百分比")
    avg_net_margin: float = Field(..., description="平均净利率，百分比")
    growth_rate: float = Field(..., description="增长率，百分比")
    growth_trend: GrowthTrend = Field(..., description="增长趋势")
    competition_level: CompetitionLevel = Field(..., description="竞争强度")
    
    # 风险评估
    policy_risk: RiskLevel = Field(..., description="政策风险")
    technology_risk: RiskLevel = Field(..., description="技术风险")
    market_risk: RiskLevel = Field(..., description="市场风险")
    
    # 其他指标
    capital_intensity: float = Field(..., description="资本密集度，1-10分")
    technology_threshold: float = Field(..., description="技术门槛，1-10分")
    globalization_index: float = Field(..., description="全球化指数，0-100")
    cyclicality_index: float = Field(..., description="周期性指数，0-100")
    
    # 数据来源
    data_sources: List[str] = Field(default_factory=list, description="数据来源")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    
    @validator('avg_gross_margin', 'avg_net_margin', 'growth_rate')
    def validate_percentage(cls, v):
        """验证百分比值"""
        if not -100 <= v <= 100:
            raise ValueError('百分比必须在-100到100之间')
        return v
    
    @validator('capital_intensity', 'technology_threshold')
    def validate_score(cls, v):
        """验证分数值"""
        if not 1 <= v <= 10:
            raise ValueError('分数必须在1-10之间')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "industry_id": "tech_software",
                "period": "2024-Q4",
                "avg_gross_margin": 65.5,
                "avg_net_margin": 18.2,
                "growth_rate": 15.3,
                "growth_trend": "rapid_growth",
                "competition_level": "highly_competitive",
                "policy_risk": "low",
                "technology_risk": "medium",
                "market_risk": "medium",
                "capital_intensity": 6.5,
                "technology_threshold": 7.2,
                "globalization_index": 85.3,
                "cyclicality_index": 42.1,
                "data_sources": ["IDC报告", "Gartner数据", "公司年报"],
                "last_updated": "2024-12-11T10:30:00"
            }
        }


class CostStructure(BaseModel):
    """成本结构"""
    material_cost: float = Field(..., description="物料成本")
    production_cost: float = Field(..., description="生产成本")
    labor_cost: float = Field(..., description="人工成本")
    logistics_cost: float = Field(..., description="物流成本")
    marketing_cost: float = Field(..., description="营销成本")
    tax_cost: float = Field(..., description="税费成本")
    other_costs: float = Field(default=0.0, description="其他成本")
    
    @property
    def total_cost(self) -> float:
        """总成本"""
        return sum([
            self.material_cost,
            self.production_cost,
            self.labor_cost,
            self.logistics_cost,
            self.marketing_cost,
            self.tax_cost,
            self.other_costs
        ])
    
    def get_cost_distribution(self) -> Dict[str, float]:
        """获取成本分布"""
        total = self.total_cost
        if total == 0:
            return {}
        
        return {
            "material": self.material_cost / total * 100,
            "production": self.production_cost / total * 100,
            "labor": self.labor_cost / total * 100,
            "logistics": self.logistics_cost / total * 100,
            "marketing": self.marketing_cost / total * 100,
            "tax": self.tax_cost / total * 100,
            "other": self.other_costs / total * 100
        }


class PricingStrategy(BaseModel):
    """定价策略"""
    strategy_type: str = Field(..., description="定价策略类型")
    base_price: float = Field(..., description="基准价格")
    markup_percentage: Optional[float] = Field(None, description="加成百分比")
    competitor_prices: Optional[List[float]] = Field(None, description="竞品价格")
    value_based_multiplier: Optional[float] = Field(None, description="价值乘数")
    dynamic_factors: Optional[Dict[str, Any]] = Field(None, description="动态定价因素")
    
    def calculate_price(self) -> float:
        """计算最终价格"""
        if self.strategy_type == "cost_plus":
            if self.markup_percentage is None:
                raise ValueError("成本加成策略需要markup_percentage")
            return self.base_price * (1 + self.markup_percentage / 100)
        
        elif self.strategy_type == "competition_based":
            if not self.competitor_prices:
                raise ValueError("竞争定价策略需要competitor_prices")
            return sum(self.competitor_prices) / len(self.competitor_prices)
        
        elif self.strategy_type == "value_based":
            if self.value_based_multiplier is None:
                raise ValueError("价值定价策略需要value_based_multiplier")
            return self.base_price * self.value_based_multiplier
        
        else:
            return self.base_price


class ProfitAnalysisRequest(BaseModel):
    """利润测算请求"""
    industry_id: str = Field(..., description="行业ID")
    product_type: str = Field(..., description="产品类型")
    production_location: str = Field(..., description="生产地")
    target_markets: List[str] = Field(..., description="目标市场")
    expected_sales_volume: float = Field(..., description="预期销量")
    
    # 成本参数
    cost_structure: Optional[CostStructure] = Field(None, description="成本结构")
    cost_estimation_method: str = Field("industry_average", description="成本估算方法")
    
    # 定价参数
    pricing_strategy: Optional[PricingStrategy] = Field(None, description="定价策略")
    target_profit_margin: float = Field(20.0, description="目标利润率百分比")
    
    # 其他参数
    currency: str = Field("USD", description="货币单位")
    analysis_period: str = Field("monthly", description="分析周期")
    
    @validator('target_profit_margin')
    def validate_profit_margin(cls, v):
        """验证利润率"""
        if v < 0 or v > 100:
            raise ValueError('利润率必须在0-100之间')
        return v


class ProfitAnalysisResult(BaseModel):
    """利润测算结果"""
    request: ProfitAnalysisRequest = Field(..., description="原始请求")
    
    # 成本分析
    estimated_total_cost: float = Field(..., description="估计总成本")
    cost_breakdown: Dict[str, float] = Field(..., description="成本细分")
    cost_per_unit: float = Field(..., description="单位成本")
    
    # 定价分析
    recommended_price: float = Field(..., description="建议售价")
    competitive_price_range: Dict[str, float] = Field(..., description="竞品价格范围")
    
    # 利润分析
    gross_profit: float = Field(..., description="毛利")
    net_profit: float = Field(..., description="净利润")
    gross_margin: float = Field(..., description="毛利率百分比")
    net_margin: float = Field(..., description="净利率百分比")
    
    # 敏感性分析
    sensitivity_analysis: Dict[str, Any] = Field(..., description="敏感性分析结果")
    break_even_point: float = Field(..., description="盈亏平衡点销量")
    
    # 风险评估
    profit_risk_level: RiskLevel = Field(..., description="利润风险等级")
    key_risk_factors: List[str] = Field(default_factory=list, description="关键风险因素")
    
    # 元数据
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="分析时间")
    confidence_score: float = Field(..., description="置信度评分，0-100")
    
    @property
    def is_profitable(self) -> bool:
        """是否盈利"""
        return self.net_margin > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        return {
            "industry": self.request.industry_id,
            "profitability": self.is_profitable,
            "net_margin": f"{self.net_margin:.1f}%",
            "gross_margin": f"{self.gross_margin:.1f}%",
            "break_even": self.break_even_point,
            "risk_level": self.profit_risk_level.value,
            "confidence": f"{self.confidence_score:.1f}%"
        }


class TrendAnalysisRequest(BaseModel):
    """趋势分析请求"""
    industry_ids: List[str] = Field(..., description="行业ID列表")
    timeframe: str = Field("1y", description="时间范围")
    analysis_type: str = Field("growth_trend", description="分析类型")
    include_forecast: bool = Field(True, description="是否包含预测")
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        """验证时间范围格式"""
        valid_formats = ['1m', '3m', '6m', '1y', '3y', '5y']
        if v not in valid_formats:
            raise ValueError(f'时间范围必须是{valid_formats}之一')
        return v


class TrendAnalysisResult(BaseModel):
    """趋势分析结果"""
    request: TrendAnalysisRequest = Field(..., description="原始请求")
    
    # 趋势分析
    growth_trends: Dict[str, GrowthTrend] = Field(..., description="增长趋势")
    momentum_scores: Dict[str, float] = Field(..., description="动量评分，0-100")
    volatility_scores: Dict[str, float] = Field(..., description="波动性评分，0-100")
    
    # 风口识别
    emerging_trends: List[Dict[str, Any]] = Field(default_factory=list, description="新兴趋势")
    hot_opportunities: List[Dict[str, Any]] = Field(default_factory=list, description="热门机会")
    
    # 风险预警
    risk_warnings: List[Dict[str, Any]] = Field(default_factory=list, description="风险预警")
    early_signals: List[Dict[str, Any]] = Field(default_factory=list, description="早期信号")
    
    # 预测数据
    forecasts: Dict[str, Any] = Field(default_factory=dict, description="预测数据")
    
    # 元数据
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="分析时间")
    data_coverage: Dict[str, float] = Field(..., description="数据覆盖度，0-100")


class ComprehensiveAnalysisRequest(BaseModel):
    """综合分析请求"""
    industry_id: str = Field(..., description="行业ID")
    business_concept: str = Field(..., description="商业概念")
    investment_size: float = Field(..., description="投资规模")
    time_horizon: str = Field("3y", description="时间跨度")
    
    # 分析选项
    include_profit_analysis: bool = Field(True, description="包含利润分析")
    include_trend_analysis: bool = Field(True, description="包含趋势分析")
    include_risk_assessment: bool = Field(True, description="包含风险评估")
    
    # 用户偏好
    risk_tolerance: RiskLevel = Field(RiskLevel.MEDIUM, description="风险承受能力")
    growth_preference: GrowthTrend = Field(GrowthTrend.RAPID_GROWTH, description="增长偏好")


class ComprehensiveAnalysisResult(BaseModel):
    """综合分析结果"""
    request: ComprehensiveAnalysisRequest = Field(..., description="原始请求")
    
    # 行业概况
    industry_profile: IndustryProfile = Field(..., description="行业画像")
    
    # 利润分析（如包含）
    profit_analysis: Optional[ProfitAnalysisResult] = Field(None, description="利润分析")
    
    # 趋势分析（如包含）
    trend_analysis: Optional[TrendAnalysisResult] = Field(None, description="趋势分析")
    
    # 综合评估
    overall_score: float = Field(..., description="综合评分，0-100")
    investment_recommendation: str = Field(..., description="投资建议")
    key_considerations: List[str] = Field(default_factory=list, description="关键考虑因素")
    
    # 执行建议
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list, description="建议行动")
    potential_challenges: List[str] = Field(default_factory=list, description="潜在挑战")
    
    # 元数据
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="分析时间")
    analyst_notes: Optional[str] = Field(None, description="分析师备注")


class SystemConfig(BaseModel):
    """系统配置"""
    # 数据库配置
    database_url: str = Field("postgresql://user:pass@localhost:5432/business_analysis", description="数据库连接URL")
    redis_url: str = Field("redis://localhost:6379/0", description="Redis连接URL")
    
    # API配置
    notebooklm_api_url: str = Field("http://localhost:8001/api", description="Notebook LM API地址")
    notebooklm_api_key: Optional[str] = Field(None, description="Notebook LM API密钥")
    
    global_brain_api_url: str = Field("http://localhost:8002/api", description="全球商业大脑API地址")
    
    # 分析配置
    default_confidence_threshold: float = Field(80.0, description="默认置信度阈值")
    max_analysis_history: int = Field(1000, description="最大分析历史记录数")
    
    # 性能配置
    cache_ttl_seconds: int = Field(3600, description="缓存有效期（秒）")
    max_concurrent_analyses: int = Field(10, description="最大并发分析数")
    
    class Config:
        env_prefix = "BUSINESS_ANALYSIS_"
        json_schema_extra = {
            "example": {
                "database_url": "postgresql://user:pass@localhost:5432/business_analysis",
                "redis_url": "redis://localhost:6379/0",
                "notebooklm_api_url": "http://localhost:8001/api",
                "global_brain_api_url": "http://localhost:8002/api",
                "default_confidence_threshold": 80.0,
                "max_analysis_history": 1000,
                "cache_ttl_seconds": 3600,
                "max_concurrent_analyses": 10
            }
        }