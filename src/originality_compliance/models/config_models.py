"""
系统配置模型定义
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CacheBackend(Enum):
    """缓存后端"""
    MEMORY = "memory"
    REDIS = "redis"
    SQLITE = "sqlite"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"                    # 数据库类型（sqlite/postgresql/mysql）
    host: str = "localhost"                 # 数据库主机
    port: int = 5432                        # 数据库端口
    name: str = "originality_compliance"    # 数据库名称
    username: Optional[str] = None          # 用户名
    password: Optional[str] = None          # 密码
    path: str = "data/originality_compliance.db"  # SQLite数据库路径
    
    def get_connection_string(self) -> str:
        """获取数据库连接字符串"""
        if self.type == "sqlite":
            return f"sqlite:///{self.path}"
        elif self.type == "postgresql":
            auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
            return f"postgresql://{auth}{self.host}:{self.port}/{self.name}"
        elif self.type == "mysql":
            auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
            return f"mysql://{auth}{self.host}:{self.port}/{self.name}"
        else:
            raise ValueError(f"不支持的数据库类型: {self.type}")


@dataclass
class CacheConfig:
    """缓存配置"""
    backend: CacheBackend = CacheBackend.MEMORY  # 缓存后端
    ttl_seconds: int = 3600                     # 缓存生存时间（秒）
    redis_host: str = "localhost"               # Redis主机
    redis_port: int = 6379                      # Redis端口
    redis_password: Optional[str] = None        # Redis密码
    redis_db: int = 0                           # Redis数据库
    memory_max_items: int = 10000               # 内存缓存最大项数
    
    def get_redis_url(self) -> str:
        """获取Redis连接URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@dataclass
class APIConfig:
    """外部API配置"""
    # DeepL API配置
    deepl_api_key: str = os.getenv("DEEPL_API_KEY", "")
    deepl_api_endpoint: str = "https://api.deepl.com/v2"
    deepl_plan_type: str = "free"  # free/pro
    
    # Notebook LM API配置
    notebooklm_api_key: str = os.getenv("NOTEBOOKLM_API_KEY", "")
    notebooklm_api_endpoint: str = "https://api.notebooklm.com/v1"
    
    # 商标数据库API配置（示例）
    trademark_api_key: str = os.getenv("TRADEMARK_API_KEY", "")
    trademark_api_endpoint: str = "https://api.trademark.com/v1"
    
    # 通用API配置
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 1


@dataclass
class ModelConfig:
    """AI模型配置"""
    # 语义相似度模型配置
    semantic_model_name: str = "bert-base-multilingual-cased"
    semantic_model_path: Optional[str] = None
    use_gpu: bool = False
    batch_size: int = 32
    
    # 文本指纹配置
    fingerprint_simhash_bits: int = 64
    fingerprint_ngram_size: int = 3
    fingerprint_hash_func: str = "md5"
    
    # 风险识别模型配置
    trademark_model_path: Optional[str] = None
    copyright_model_path: Optional[str] = None
    patent_model_path: Optional[str] = None


@dataclass
class RuleConfig:
    """规则引擎配置"""
    # 原创检测规则
    originality_threshold_low: float = 0.9     # 低于此值为高风险
    originality_threshold_medium: float = 0.7  # 低于此值为中风险
    similarity_count_threshold: int = 3        # 相似项数量阈值
    
    # 合规检查规则
    compliance_threshold_pass: float = 0.8     # 合规分数通过阈值
    max_violations_allowed: int = 1            # 允许的最大违规数量
    
    # 侵权风险规则
    trademark_risk_threshold: float = 0.7      # 商标风险阈值
    copyright_risk_threshold: float = 0.8      # 版权风险阈值
    patent_risk_threshold: float = 0.9         # 专利风险阈值
    
    # 国家特定规则文件路径
    us_rules_path: str = "rules/us_compliance_rules.json"
    cn_rules_path: str = "rules/cn_compliance_rules.json"
    eu_rules_path: str = "rules/eu_compliance_rules.json"
    jp_rules_path: str = "rules/jp_compliance_rules.json"
    kr_rules_path: str = "rules/kr_compliance_rules.json"


@dataclass
class LoggingConfig:
    """日志配置"""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/originality_compliance.log"
    max_file_size_mb: int = 10
    backup_count: int = 5
    console_enabled: bool = True


@dataclass
class SecurityConfig:
    """安全配置"""
    # 数据安全
    encrypt_sensitive_data: bool = True
    encryption_key: Optional[str] = os.getenv("ENCRYPTION_KEY", "")
    data_retention_days: int = 90
    
    # API安全
    enable_api_key_auth: bool = True
    api_key_header: str = "X-API-Key"
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # 隐私保护
    anonymize_user_data: bool = True
    pii_detection_enabled: bool = True
    gdpr_compliant: bool = True


@dataclass
class SystemSettings:
    """系统整体设置"""
    # 组件配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    api: APIConfig = field(default_factory=APIConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    rule: RuleConfig = field(default_factory=RuleConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # 系统行为配置
    enable_auto_learning: bool = False          # 启用自动学习
    enable_fallback_mode: bool = True          # 启用降级模式
    maintenance_mode: bool = False             # 维护模式
    debug_mode: bool = False                   # 调试模式
    
    @classmethod
    def from_env(cls) -> "SystemSettings":
        """从环境变量创建配置"""
        return cls(
            database=DatabaseConfig(
                type=os.getenv("DB_TYPE", "sqlite"),
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                name=os.getenv("DB_NAME", "originality_compliance"),
                username=os.getenv("DB_USERNAME"),
                password=os.getenv("DB_PASSWORD"),
                path=os.getenv("DB_PATH", "data/originality_compliance.db")
            ),
            cache=CacheConfig(
                backend=CacheBackend(os.getenv("CACHE_BACKEND", "memory")),
                ttl_seconds=int(os.getenv("CACHE_TTL", "3600")),
                redis_host=os.getenv("REDIS_HOST", "localhost"),
                redis_port=int(os.getenv("REDIS_PORT", "6379")),
                redis_password=os.getenv("REDIS_PASSWORD"),
                redis_db=int(os.getenv("REDIS_DB", "0")),
                memory_max_items=int(os.getenv("CACHE_MAX_ITEMS", "10000"))
            ),
            api=APIConfig(
                deepl_api_key=os.getenv("DEEPL_API_KEY", ""),
                deepl_plan_type=os.getenv("DEEPL_PLAN_TYPE", "free"),
                notebooklm_api_key=os.getenv("NOTEBOOKLM_API_KEY", ""),
                trademark_api_key=os.getenv("TRADEMARK_API_KEY", ""),
                timeout_seconds=int(os.getenv("API_TIMEOUT", "30")),
                max_retries=int(os.getenv("API_MAX_RETRIES", "3"))
            )
        )