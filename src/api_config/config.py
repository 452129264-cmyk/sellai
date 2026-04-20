"""
API配置管理
统一管理 DeepSeek 和百炼 API 的配置
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class APIProvider(Enum):
    """API提供商枚举"""
    DEEPSEEK = "deepseek"
    BAILIAN = "bailian"
    OPENAI = "openai"  # 保留兼容


@dataclass
class DeepSeekConfig:
    """DeepSeek API配置"""
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"  # 或 deepseek-reasoner
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    
    def __post_init__(self):
        # 从环境变量读取
        if not self.api_key:
            self.api_key = os.getenv("DEEPSEEK_API_KEY", "")


@dataclass
class BailianConfig:
    """百炼 API配置"""
    api_key: str = ""
    access_key_id: str = ""
    access_key_secret: str = ""
    region: str = "cn-hangzhou"
    
    # 文生图模型
    image_model: str = "wanx-v1"  # 通义万相
    image_size: str = "1024x1024"
    
    # 文本模型（可选）
    text_model: str = "qwen-turbo"
    
    timeout: int = 120
    
    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("BAILIAN_API_KEY", "")
        if not self.access_key_id:
            self.access_key_id = os.getenv("BAILIAN_ACCESS_KEY_ID", "")
        if not self.access_key_secret:
            self.access_key_secret = os.getenv("BAILIAN_ACCESS_KEY_SECRET", "")


@dataclass
class APIConfig:
    """统一API配置"""
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)
    bailian: BailianConfig = field(default_factory=BailianConfig)
    
    # 默认使用 DeepSeek 作为推理引擎
    default_llm_provider: APIProvider = APIProvider.DEEPSEEK
    default_image_provider: APIProvider = APIProvider.BAILIAN
    
    def is_deepseek_available(self) -> bool:
        return bool(self.deepseek.api_key)
    
    def is_bailian_available(self) -> bool:
        return bool(self.bailian.api_key) or (
            bool(self.bailian.access_key_id) and bool(self.bailian.access_key_secret)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "deepseek": {
                "available": self.is_deepseek_available(),
                "model": self.deepseek.model,
                "base_url": self.deepseek.base_url
            },
            "bailian": {
                "available": self.is_bailian_available(),
                "image_model": self.bailian.image_model
            },
            "default_llm": self.default_llm_provider.value,
            "default_image": self.default_image_provider.value
        }


# 全局配置实例
api_config = APIConfig()


def get_llm_client():
    """获取默认LLM客户端"""
    if api_config.is_deepseek_available():
        from .deepseek_client import DeepSeekClient
        return DeepSeekClient(api_config.deepseek)
    raise ValueError("没有可用的LLM API配置，请设置 DEEPSEEK_API_KEY")


def get_image_client():
    """获取默认图片生成客户端"""
    if api_config.is_bailian_available():
        from .bailian_client import BailianClient
        return BailianClient(api_config.bailian)
    raise ValueError("没有可用的图片API配置，请设置 BAILIAN_API_KEY")
