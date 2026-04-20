"""
智能风控合规系统数据模型
定义法规数据库的核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from enum import Enum

# ==============================================
# 枚举类型定义
# ==============================================

class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RuleType(str, Enum):
    """规则类型枚举"""
    KEYWORD = "keyword"
    PATTERN = "pattern"
    SEMANTIC = "semantic"
    ML_MODEL = "ml_model"

class MatchLogic(str, Enum):
    """匹配逻辑枚举"""
    EXACT = "exact"
    PARTIAL = "partial"
    FUZZY = "fuzzy"

class ContentType(str, Enum):
    """内容类型枚举"""
    ADVERTISEMENT = "advertisement"
    PRODUCT_DESCRIPTION = "product"
    SOCIAL_MEDIA = "social"
    EMAIL_MARKETING = "email"
    WEB_CONTENT = "web"
    DOCUMENT = "document"

# ==============================================
# 核心数据模型
# ==============================================

@dataclass
class Country:
    """国家/地区信息"""
    id: str
    code: str  # ISO 3166-1 alpha-2代码，如US、CN、EU
    name: str
    region: Optional[str] = None
    currency_code: Optional[str] = None
    language_codes: List[str] = field(default_factory=list)  # 主要语言代码
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.code:
            raise ValueError("Country code is required")
        if not self.name:
            raise ValueError("Country name is required")

@dataclass
class RegulationCategory:
    """法规分类"""
    id: str
    name: str
    description: Optional[str] = None
    risk_weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class RegulationClause:
    """法规条款"""
    id: str
    country_id: str
    category_id: str
    clause_code: str  # 如FTC_001、GDPR_003
    title: str
    description: Optional[str] = None
    legal_text: Optional[str] = None
    simplified_text: Optional[str] = None  # 简化说明
    risk_level: RiskLevel = RiskLevel.MEDIUM
    keywords: List[str] = field(default_factory=list)
    penalty_info: Optional[str] = None
    effective_date: Optional[date] = None
    updated_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class RiskRule:
    """风险规则"""
    id: str
    clause_id: str
    rule_type: RuleType
    rule_content: Dict[str, Any]  # JSON格式规则定义
    match_logic: MatchLogic = MatchLogic.EXACT
    threshold: float = 0.8
    weight: float = 1.0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ComplianceCase:
    """合规案例"""
    id: str
    country_id: str
    category_id: str
    title: str
    description: str
    original_content: str
    violation_type: str
    corrected_content: Optional[str] = None
    penalty_amount: Optional[float] = None
    case_date: Optional[date] = None
    source_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

# ==============================================
# 检查相关模型
# ==============================================

@dataclass
class ComplianceRequest:
    """合规检查请求"""
    content_id: str
    text: str
    content_type: ContentType
    target_country: str
    industry: Optional[str] = None
    context: Optional[str] = None
    user_id: Optional[str] = None
    request_source: str = "ai_agent"
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Violation:
    """违规详情"""
    id: str
    clause_code: str
    description: str
    risk_level: RiskLevel
    matched_text: str
    position_start: int
    position_end: int
    confidence: float
    suggested_correction: Optional[str] = None
    rule_id: Optional[str] = None

@dataclass
class CaseReference:
    """案例引用"""
    case_id: str
    title: str
    similarity_score: float
    violation_type: str
    key_points: List[str]

@dataclass
class ComplianceResult:
    """合规检查结果"""
    content_id: str
    risk_level: RiskLevel
    risk_score: float  # 0.0-1.0
    violations: List[Violation]
    suggestions: List[str]
    similar_cases: List[CaseReference]
    processing_time_ms: float
    intercepted: bool = False
    interception_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

# ==============================================
# 配置模型
# ==============================================

@dataclass
class ComplianceConfig:
    """合规系统配置"""
    risk_threshold: float = 0.8
    cache_ttl_seconds: int = 3600
    max_text_length: int = 10000
    enable_ai_assessment: bool = True
    enable_realtime_alert: bool = True
    default_country: str = "US"
    supported_countries: List[str] = field(default_factory=lambda: [
        "US", "CN", "EU", "JP", "KR", "GB", "DE", "FR", "AU", "CA", "SG"
    ])

@dataclass
class RuleEngineConfig:
    """规则引擎配置"""
    enable_keyword_matching: bool = True
    enable_pattern_matching: bool = True
    enable_semantic_analysis: bool = True
    keyword_match_threshold: float = 0.7
    pattern_match_threshold: float = 0.6
    semantic_match_threshold: float = 0.5
    max_rules_per_request: int = 1000
    cache_size: int = 1000

# ==============================================
# 辅助函数
# ==============================================

def violation_to_dict(violation: Violation) -> Dict[str, Any]:
    """违规对象转换为字典"""
    return {
        "id": violation.id,
        "clause_code": violation.clause_code,
        "description": violation.description,
        "risk_level": violation.risk_level.value,
        "matched_text": violation.matched_text,
        "position_start": violation.position_start,
        "position_end": violation.position_end,
        "confidence": violation.confidence,
        "suggested_correction": violation.suggested_correction,
        "rule_id": violation.rule_id
    }

def result_to_dict(result: ComplianceResult) -> Dict[str, Any]:
    """检查结果转换为字典"""
    return {
        "content_id": result.content_id,
        "risk_level": result.risk_level.value,
        "risk_score": result.risk_score,
        "violations": [violation_to_dict(v) for v in result.violations],
        "suggestions": result.suggestions,
        "similar_cases": [
            {
                "case_id": c.case_id,
                "title": c.title,
                "similarity_score": c.similarity_score,
                "violation_type": c.violation_type,
                "key_points": c.key_points
            }
            for c in result.similar_cases
        ],
        "processing_time_ms": result.processing_time_ms,
        "intercepted": result.intercepted,
        "interception_reason": result.interception_reason,
        "timestamp": result.timestamp.isoformat()
    }