"""
Banana生图内核全局素材库流水线模块

提供图片自动归档、质量评估、记忆同步等功能。
"""

from .config import (
    PipelineConfig, DEFAULT_CONFIG,
    ImageMetadata, AssetCategory, ImageQualityGrade,
    generate_image_id, validate_metadata, MetadataSchema
)

from .image_processor import ImageProcessor, BatchImageProcessor
from .memory_sync import MemorySyncManager, AsyncMemorySyncManager
from .pipeline import AssetPipeline, AsyncAssetPipeline, process_and_sync_image
from .api_server import AssetPipelineAPIServer, start_asset_pipeline_api_server

__version__ = "1.0.0"
__all__ = [
    # 配置
    "PipelineConfig", "DEFAULT_CONFIG",
    "ImageMetadata", "AssetCategory", "ImageQualityGrade",
    "generate_image_id", "validate_metadata", "MetadataSchema",
    
    # 处理器
    "ImageProcessor", "BatchImageProcessor",
    
    # 记忆同步
    "MemorySyncManager", "AsyncMemorySyncManager",
    
    # 流水线
    "AssetPipeline", "AsyncAssetPipeline", "process_and_sync_image",
    
    # API服务器
    "AssetPipelineAPIServer", "start_asset_pipeline_api_server",
]