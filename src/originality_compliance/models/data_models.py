"""
原创合规校验系统数据模型定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum


class ContentType(Enum):
    """内容类型枚举"""
    MARKETING = "marketing"          # 营销文案
    ADVERTISEMENT = "advertisement"  # 广告宣传
    PRODUCT = "product"              # 产品描述
    SOCIAL_MEDIA = "social_media"    # 社媒内容
    EMAIL = "email"                  # 邮件营销
    WEBSITE = "website"              # 网站内容
    VIDEO = "video"                  # 视频脚本
    AUDIO = "audio"                  # 音频内容


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"          # 低风险
    MEDIUM = "medium"    # 中风险
    HIGH = "high"        # 高风险
    CRITICAL = "critical"  # 严重风险


class CountryCode(Enum):
    """国家代码枚举"""
    US = "US"  # 美国
    CN = "CN"  # 中国
    EU = "EU"  # 欧盟
    JP = "JP"  # 日本
    KR = "KR"  # 韩国
    UK = "UK"  # 英国
    CA = "CA"  # 加拿大
    AU = "AU"  # 澳大利亚
    GLOBAL = "global"  # 全球通用


@dataclass
class OriginalityRequest:
    """原创性检测请求"""
    text: str                    # 待检测文本
    content_type: ContentType   # 内容类型
    language: str = "auto"      # 文本语言（auto自动检测）
    target_countries: List[CountryCode] = field(default_factory=lambda: [CountryCode.GLOBAL])  # 目标国家
    check_type: str = "all"     # 检测类型（originality/compliance/risk/all）
    user_id: Optional[str] = None  # 用户ID（可选）
    project_id: Optional[str] = None  # 项目ID（可选）
    
    
@dataclass
class ComplianceRequest:
    """合规性校验请求"""
    text: str                    # 待检查文本
    content_type: ContentType   # 内容类型
    target_country: CountryCode  # 目标国家
    industry: str = "general"    # 行业分类
    check_trademark: bool = True  # 是否检查商标
    check_copyright: bool = True  # 是否检查版权
    check_patent: bool = False   # 是否检查专利（默认关闭）
    user_context: Optional[Dict[str, Any]] = None  # 用户上下文信息


@dataclass
class SimilarityItem:
    """相似内容项"""
    source_id: str              # 来源ID（Notebook LM知识项ID或其他）
    source_type: str           # 来源类型（notebooklm/external/database）
    similarity_score: float    # 相似度分数（0.0-1.0）
    matched_text: str          # 匹配的文本片段
    source_url: Optional[str] = None  # 来源URL（如果可用）
    risk_level: RiskLevel = RiskLevel.LOW  # 风险等级
    recommendations: List[str] = field(default_factory=list)  # 改进建议


@dataclass
class ViolationItem:
    """违规项"""
    rule_code: str            # 规则代码（如FTC_001）
    rule_name: str           # 规则名称
    description: str         # 违规描述
    risk_level: RiskLevel    # 风险等级
    suggested_fix: str       # 修复建议
    reference_url: Optional[str] = None  # 参考链接


@dataclass
class RiskItem:
    """风险项"""
    risk_type: str           # 风险类型（trademark/copyright/patent）
    risk_name: str          # 风险名称
    description: str        # 风险描述
    risk_level: RiskLevel   # 风险等级
    confidence: float = 0.0  # 置信度（0.0-1.0）
    source: Optional[str] = None  # 风险来源
    suggested_action: str = ""  # 建议行动


@dataclass
class OriginalityResult:
    """原创性检测结果"""
    originality_score: float                # 原创性分数（0.0-1.0）
    plagiarism_risk: RiskLevel              # 抄袭风险等级
    similarity_items: List[SimilarityItem]  # 相似内容列表
    recommendations: List[str]              # 综合建议
    processing_time_ms: float               # 处理时间（毫秒）
    detection_method: str = "composite"     # 检测方法（semantic/fingerprint/composite）
    language_detected: Optional[str] = None  # 检测到的语言


@dataclass
class ComplianceResult:
    """合规性校验结果"""
    compliance_score: float               # 合规分数（0.0-1.0）
    violations: List[ViolationItem]       # 违规项列表
    risk_items: List[RiskItem]            # 风险项列表
    recommendations: List[str]            # 改进建议
    processing_time_ms: float             # 处理时间（毫秒）
    overall_risk: RiskLevel = RiskLevel.LOW  # 总体风险等级
    passed: bool = True                   # 是否通过


@dataclass
class SystemConfig:
    """系统配置"""
    # 原创检测配置
    semantic_threshold: float = 0.85      # 语义相似度阈值（高于此值认为高风险）
    fingerprint_threshold: float = 0.7    # 指纹相似度阈值
    min_text_length: int = 10             # 最小检测文本长度
    
    # 合规检查配置
    enabled_countries: List[CountryCode] = field(default_factory=lambda: [
        CountryCode.US, CountryCode.CN, CountryCode.EU, CountryCode.JP, CountryCode.KR
    ])
    
    # 集成配置
    notebooklm_enabled: bool = True       # Notebook LM集成开关
    deepl_enabled: bool = True           # DeepL集成开关
    external_api_timeout: int = 30        # 外部API超时时间（秒）
    
    # 缓存配置
    cache_enabled: bool = True           # 缓存开关
    cache_ttl_seconds: int = 3600        # 缓存生存时间（秒）
    
    # 风险处理配置
    auto_block_high_risk: bool = True    # 自动拦截高风险内容
    notify_on_medium_risk: bool = True   # 中风险内容通知
    review_threshold: float = 0.6        # 需要人工审核的阈值