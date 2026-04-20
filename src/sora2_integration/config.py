"""
Sora2视频生成API配置模块
预配置固定参数定义
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class Sora2ModelType(Enum):
    """Sora2模型类型"""
    # 官方模型
    SORA_2 = "sora-2"
    SORA_2_PRO = "sora-2-pro"
    
    # 第三方兼容模型
    SORA_2_LANDSCAPE_15S = "sora-2-landscape-15s"
    SORA_2_PORTRAIT_15S = "sora-2-portrait-15s"
    SORA_2_CHARACTERS = "sora-2-characters"


@dataclass
class Sora2OutputSpec:
    """输出规格配置"""
    # 画面比例
    aspect_ratio: str = "9:16"
    
    # 分辨率
    width: int = 1080
    height: int = 1920
    
    # 时长（秒）
    duration_seconds: int = 15
    
    # 画质
    quality: str = "Cinematic Ultra HD"
    
    # 帧率
    fps: int = 30
    
    @property
    def size_str(self) -> str:
        """返回API需要的尺寸字符串"""
        return f"{self.width}x{self.height}"
    
    @property
    def orientation(self) -> str:
        """返回方向（portrait/landscape）"""
        if self.width < self.height:
            return "portrait"
        else:
            return "landscape"


@dataclass
class Sora2WorkflowConfig:
    """自动化工作流配置"""
    # sellai推送产品信息→调用Sora2生成视频→回传sellai素材库→自动上架独立站/社媒
    enable_full_pipeline: bool = True
    
    # 各环节配置
    product_info_receiver_enabled: bool = True
    sora2_generator_enabled: bool = True
    material_library_enabled: bool = True
    auto_publish_enabled: bool = True
    
    # 工作流参数
    max_concurrent_jobs: int = 5
    default_timeout_seconds: int = 600
    enable_checkpoints: bool = True
    checkpoint_dir: str = "data/sora2_checkpoints"


@dataclass
class Sora2RetryConfig:
    """容错机制配置"""
    # 失败自动重试3次，每次间隔30秒
    max_retry_count: int = 3
    retry_interval_seconds: int = 30
    
    # 批量任务排队调度，支持并发控制
    max_concurrent_tasks: int = 5
    queue_timeout_seconds: int = 3600
    
    # 网络异常处理
    network_timeout_seconds: int = 60
    ssl_verify: bool = False  # 当前环境SSL证书不兼容，需设为False
    
    # 质量检查回退方案
    enable_quality_fallback: bool = True
    fallback_resolution: str = "720x1280"
    fallback_duration: int = 12


@dataclass
class Sora2APIEndpoint:
    """API端点配置"""
    # OpenAI官方端点
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_VIDEO_CREATE: str = "/videos"
    OPENAI_VIDEO_RETRIEVE: str = "/videos/{video_id}"
    OPENAI_VIDEO_REMIX: str = "/videos/{video_id}/remix"
    OPENAI_VIDEO_CONTENT: str = "/videos/{video_id}/content"
    
    # 第三方兼容端点（Mountsea AI）
    MOUNTSEA_BASE_URL: str = "https://api.mountsea.ai"
    MOUNTSEA_SORA_GENERATE: str = "/sora/generate"
    MOUNTSEA_SORA_TASK: str = "/sora/task"
    
    # Sora2API（第三方）
    SORA2API_BASE_URL: str = "https://api.sora2api.com/v1"
    SORA2API_VIDEOS: str = "/videos"
    SORA2API_MODELS: str = "/models"


@dataclass
class Sora2SecurityConfig:
    """安全认证配置"""
    # API密钥配置（需用户后续提供）
    api_key: Optional[str] = None
    api_key_env_var: str = "SORA2_API_KEY"
    
    # 认证头配置
    auth_header_prefix: str = "Bearer"
    
    # 请求签名（可选）
    enable_request_signing: bool = False
    signing_secret: Optional[str] = None
    
    # 使用环境变量自动加载
    @property
    def get_api_key(self) -> Optional[str]:
        """获取API密钥，优先使用显式配置，其次环境变量"""
        if self.api_key:
            return self.api_key
        
        import os
        return os.getenv(self.api_key_env_var)


@dataclass
class Sora2IntegrationConfig:
    """Sora2集成总配置"""
    # 预配置固定参数
    protocol: str = "OpenAI Video兼容协议"
    
    # 输出规格
    output_spec: Sora2OutputSpec = field(default_factory=Sora2OutputSpec)
    
    # 自动化工作流
    workflow: Sora2WorkflowConfig = field(default_factory=Sora2WorkflowConfig)
    
    # 容错机制
    retry: Sora2RetryConfig = field(default_factory=Sora2RetryConfig)
    
    # API端点
    endpoints: Sora2APIEndpoint = field(default_factory=Sora2APIEndpoint)
    
    # 安全认证
    security: Sora2SecurityConfig = field(default_factory=Sora2SecurityConfig)
    
    # 模型选择
    default_model: Sora2ModelType = Sora2ModelType.SORA_2_PORTRAIT_15S
    
    # 兼容性配置
    use_openai_official: bool = True  # 优先使用OpenAI官方API
    fallback_to_third_party: bool = True  # 官方不可用时回退第三方
    
    # 当前环境网络限制配置
    network_restricted: bool = True  # 基于任务133-135验证结果
    generate_config_only: bool = True  # 仅生成配置文档，不实际调用API
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/sora2_integration.log"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于JSON序列化"""
        return {
            "protocol": self.protocol,
            "output_spec": {
                "aspect_ratio": self.output_spec.aspect_ratio,
                "width": self.output_spec.width,
                "height": self.output_spec.height,
                "duration_seconds": self.output_spec.duration_seconds,
                "quality": self.output_spec.quality,
                "fps": self.output_spec.fps,
                "size_str": self.output_spec.size_str,
                "orientation": self.output_spec.orientation
            },
            "workflow": {
                "enable_full_pipeline": self.workflow.enable_full_pipeline,
                "product_info_receiver_enabled": self.workflow.product_info_receiver_enabled,
                "sora2_generator_enabled": self.workflow.sora2_generator_enabled,
                "material_library_enabled": self.workflow.material_library_enabled,
                "auto_publish_enabled": self.workflow.auto_publish_enabled,
                "max_concurrent_jobs": self.workflow.max_concurrent_jobs,
                "default_timeout_seconds": self.workflow.default_timeout_seconds,
                "enable_checkpoints": self.workflow.enable_checkpoints,
                "checkpoint_dir": self.workflow.checkpoint_dir
            },
            "retry": {
                "max_retry_count": self.retry.max_retry_count,
                "retry_interval_seconds": self.retry.retry_interval_seconds,
                "max_concurrent_tasks": self.retry.max_concurrent_tasks,
                "queue_timeout_seconds": self.retry.queue_timeout_seconds,
                "network_timeout_seconds": self.retry.network_timeout_seconds,
                "ssl_verify": self.retry.ssl_verify,
                "enable_quality_fallback": self.retry.enable_quality_fallback,
                "fallback_resolution": self.retry.fallback_resolution,
                "fallback_duration": self.retry.fallback_duration
            },
            "default_model": self.default_model.value,
            "use_openai_official": self.use_openai_official,
            "fallback_to_third_party": self.fallback_to_third_party,
            "network_restricted": self.network_restricted,
            "generate_config_only": self.generate_config_only,
            "log_level": self.log_level,
            "log_file": self.log_file
        }


# 默认配置实例
DEFAULT_CONFIG = Sora2IntegrationConfig()