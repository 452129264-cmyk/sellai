#!/usr/bin/env python3
"""
Banana生图内核全局素材库配置模块

定义图片归档流水线的配置参数、目录结构、元数据标准。
"""

import os
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple
import json


class AssetCategory(Enum):
    """资产类别枚举"""
    PRODUCT_IMAGE = "product_image"          # 产品图
    MODEL_PHOTO = "model_photo"              # 模特图
    MARKETING_MATERIAL = "marketing_material"  # 营销素材
    UI_COMPONENT = "ui_component"            # UI组件
    BRAND_ASSET = "brand_asset"              # 品牌资产
    TEMPLATE = "template"                    # 模板
    OTHER = "other"                          # 其他


class ImageQualityGrade(Enum):
    """图片质量等级"""
    EXCELLENT = "excellent"      # 优秀：完全符合原版Banana标准
    GOOD = "good"                # 良好：基本符合，微小差异
    ACCEPTABLE = "acceptable"    # 可接受：有差异但可用
    REJECTED = "rejected"        # 拒绝：存在质量问题


@dataclass
class ImageMetadata:
    """图片元数据核心结构"""
    # 基础信息
    image_id: str                       # 图片唯一ID
    file_name: str                      # 文件名
    file_path: str                      # 存储路径（相对路径）
    file_size: int                      # 文件大小（字节）
    dimensions: Tuple[int, int]         # 尺寸（宽, 高）
    format: str                         # 格式（png/jpg/webp等）
    
    # 生成信息
    prompt: str                         # 生成提示词
    negative_prompt: str                # 负向提示词
    model_name: str                     # 模型名称
    model_version: str                  # 模型版本
    generation_params: Dict[str, Any]   # 其他生成参数
    
    # 业务上下文
    avatar_id: str                      # 生成分身ID
    task_id: str                        # 关联任务ID
    scene: str                          # 使用场景
    category: AssetCategory             # 资产类别
    tags: List[str]                     # 标签列表
    
    # 质量信息
    quality_grade: ImageQualityGrade    # 质量等级
    quality_metrics: Dict[str, float]   # 质量指标（清晰度、一致性等）
    has_issues: bool                    # 是否存在问题
    issue_details: Optional[str]        # 问题详情
    
    # 版权与权限
    creator: str                        # 创建者（SellAI系统）
    created_at: str                     # 创建时间戳
    copyright: str                      # 版权信息
    usage_rights: Dict[str, Any]        # 使用权限
    
    # 索引与检索
    semantic_description: str           # 语义描述
    embedding_vector: Optional[List[float]] = None  # 向量嵌入（可选）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 处理枚举类型
        data['category'] = self.category.value
        data['quality_grade'] = self.quality_grade.value
        # 处理元组
        if isinstance(data['dimensions'], tuple):
            data['dimensions'] = list(data['dimensions'])
        return data
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageMetadata':
        """从字典创建实例"""
        # 转换枚举类型
        if 'category' in data and isinstance(data['category'], str):
            data['category'] = AssetCategory(data['category'])
        if 'quality_grade' in data and isinstance(data['quality_grade'], str):
            data['quality_grade'] = ImageQualityGrade(data['quality_grade'])
        # 转换元组
        if 'dimensions' in data and isinstance(data['dimensions'], list):
            data['dimensions'] = tuple(data['dimensions'])
        return cls(**data)


@dataclass
class PipelineConfig:
    """流水线配置"""
    # 目录配置
    base_storage_dir: str = "outputs/global_assets/images"
    temp_processing_dir: str = "temp/banana_processing"
    metadata_dir: str = "data/banana_asset_metadata"
    
    # 性能配置
    max_processing_delay_ms: int = 500      # 最大处理延迟
    batch_size: int = 10                    # 批量处理大小
    max_concurrent: int = 5                 # 最大并发数
    processing_timeout_sec: int = 30        # 处理超时时间
    
    # 质量配置
    min_quality_grade: ImageQualityGrade = ImageQualityGrade.ACCEPTABLE
    required_resolution: Tuple[int, int] = (2048, 2048)  # 最小分辨率
    max_face_variance: float = 0.03         # 人脸差异<3%
    max_texture_error: float = 0.05         # 面料误差<5%
    
    # 记忆系统配置
    notebook_lm_kb_name: str = "Banana生图素材库"
    notebook_lm_kb_description: str = "存储Banana生图内核生成的所有图片素材及其元数据"
    notebook_lm_sync_enabled: bool = True
    notebook_lm_batch_size: int = 50        # Notebook LM批量写入大小
    
    # 归档规则
    enable_auto_classification: bool = True
    enable_face_consistency_check: bool = True
    enable_texture_analysis: bool = True
    enable_semantic_indexing: bool = True
    
    def get_date_based_path(self, date_str: Optional[str] = None) -> str:
        """获取基于日期的路径"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.base_storage_dir, date_str)
    
    def get_avatar_path(self, date_str: str, scene: str, avatar_id: str) -> str:
        """获取分身特定路径"""
        date_path = self.get_date_based_path(date_str)
        return os.path.join(date_path, scene, avatar_id)
    
    def ensure_directories(self) -> None:
        """确保所有必要目录存在"""
        dirs = [
            self.base_storage_dir,
            self.temp_processing_dir,
            self.metadata_dir,
            os.path.join(self.metadata_dir, "images"),
            os.path.join(self.metadata_dir, "index"),
        ]
        
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)


# 默认配置实例
DEFAULT_CONFIG = PipelineConfig()


class MetadataSchema:
    """元数据模式定义"""
    
    @staticmethod
    def get_required_fields() -> List[str]:
        """获取必填字段列表"""
        return [
            "image_id",
            "file_name",
            "file_path",
            "dimensions",
            "prompt",
            "avatar_id",
            "task_id",
            "scene",
            "category",
            "quality_grade",
            "creator",
            "created_at",
        ]
    
    @staticmethod
    def get_validation_rules() -> Dict[str, Any]:
        """获取验证规则"""
        return {
            "dimensions": {
                "type": list,
                "min_length": 2,
                "max_length": 2,
                "min_values": [1024, 1024],  # 最小分辨率
            },
            "file_size": {
                "type": int,
                "min": 1024,  # 最小1KB
                "max": 50 * 1024 * 1024,  # 最大50MB
            },
            "quality_grade": {
                "type": str,
                "allowed": [grade.value for grade in ImageQualityGrade],
            },
            "category": {
                "type": str,
                "allowed": [cat.value for cat in AssetCategory],
            },
        }


# 工具函数
def generate_image_id(avatar_id: str, timestamp: Optional[str] = None) -> str:
    """生成图片唯一ID"""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    import hashlib
    import random
    random_suffix = random.randint(1000, 9999)
    base_str = f"{avatar_id}_{timestamp}_{random_suffix}"
    return f"img_{hashlib.md5(base_str.encode()).hexdigest()[:16]}"


def validate_metadata(metadata: ImageMetadata) -> Tuple[bool, List[str]]:
    """验证元数据完整性"""
    errors = []
    
    # 检查必填字段
    required_fields = MetadataSchema.get_required_fields()
    for field in required_fields:
        value = getattr(metadata, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"必填字段 '{field}' 为空")
    
    # 检查分辨率
    width, height = metadata.dimensions
    config = DEFAULT_CONFIG
    min_width, min_height = config.required_resolution
    if width < min_width or height < min_height:
        errors.append(f"分辨率不足: {width}x{height}，最小要求: {min_width}x{min_height}")
    
    # 检查质量等级
    if metadata.quality_grade.value not in [grade.value for grade in ImageQualityGrade]:
        errors.append(f"无效的质量等级: {metadata.quality_grade}")
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    # 配置测试
    config = DEFAULT_CONFIG
    config.ensure_directories()
    
    print("配置测试:")
    print(f"基础存储目录: {config.base_storage_dir}")
    print(f"临时处理目录: {config.temp_processing_dir}")
    print(f"元数据目录: {config.metadata_dir}")
    
    # 测试路径生成
    test_path = config.get_avatar_path("2024-01-01", "product_shoot", "avatar_001")
    print(f"测试路径: {test_path}")
    
    # 测试ID生成
    test_id = generate_image_id("avatar_001")
    print(f"测试图片ID: {test_id}")
    
    print("\n配置测试完成")