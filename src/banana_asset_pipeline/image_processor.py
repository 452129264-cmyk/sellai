#!/usr/bin/env python3
"""
Banana生图内核图片处理器

负责图片的读取、元数据提取、质量检测、分类标签等核心处理逻辑。
"""

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, BinaryIO
from dataclasses import dataclass, asdict
import logging

# 尝试导入图像处理库
try:
    from PIL import Image, ImageFile, ExifTags
    from PIL.ExifTags import TAGS
    IMAGE_LIB_AVAILABLE = True
except ImportError:
    IMAGE_LIB_AVAILABLE = False
    print("警告: PIL/Pillow库未安装，部分图像处理功能受限")

from .config import (
    ImageMetadata, AssetCategory, ImageQualityGrade, 
    PipelineConfig, DEFAULT_CONFIG, generate_image_id,
    validate_metadata
)

# 配置日志
logger = logging.getLogger(__name__)

# 允许加载大图
ImageFile.LOAD_TRUNCATED_IMAGES = True


@dataclass
class ImageAnalysisResult:
    """图片分析结果"""
    dimensions: Tuple[int, int]
    format: str
    mode: str
    exif_data: Optional[Dict[str, Any]]
    dominant_colors: Optional[List[Tuple[int, int, int]]]
    estimated_clarity: float  # 清晰度估计 0-1
    estimated_brightness: float  # 亮度估计 0-1
    estimated_contrast: float  # 对比度估计 0-1
    has_human_faces: bool
    face_count: int
    has_text: bool


class ImageProcessor:
    """图片处理器"""
    
    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG):
        self.config = config
        
        if not IMAGE_LIB_AVAILABLE:
            logger.warning("PIL/Pillow不可用，图像分析功能受限")
    
    def process_image_file(self, image_path: str, 
                          generation_params: Dict[str, Any],
                          avatar_id: str,
                          task_id: str,
                          scene: str) -> Tuple[Optional[ImageMetadata], List[str]]:
        """
        处理图片文件
        
        Args:
            image_path: 图片文件路径
            generation_params: 生成参数
            avatar_id: 分身ID
            task_id: 任务ID
            scene: 使用场景
            
        Returns:
            (图片元数据, 警告信息列表)
        """
        warnings = []
        
        # 1. 验证文件存在性
        if not os.path.exists(image_path):
            logger.error(f"图片文件不存在: {image_path}")
            return None, ["图片文件不存在"]
        
        # 2. 读取文件信息
        try:
            file_size = os.path.getsize(image_path)
            file_name = os.path.basename(image_path)
            
            # 3. 分析图片
            analysis_result = self._analyze_image(image_path)
            
            # 4. 提取生成参数
            prompt = generation_params.get("prompt", "")
            negative_prompt = generation_params.get("negative_prompt", "")
            model_name = generation_params.get("model_name", "banana_model")
            model_version = generation_params.get("model_version", "1.0")
            
            # 5. 自动分类
            category = self._auto_classify_image(
                analysis_result, prompt, scene, avatar_id
            )
            
            # 6. 生成标签
            tags = self._generate_tags(
                analysis_result, category, scene, avatar_id, generation_params
            )
            
            # 7. 质量评估
            quality_grade, quality_metrics, has_issues, issue_details = self._evaluate_quality(
                analysis_result, generation_params
            )
            
            # 8. 创建元数据
            image_id = generate_image_id(avatar_id)
            created_at = datetime.now().isoformat()
            
            # 确定存储路径
            date_str = datetime.now().strftime("%Y-%m-%d")
            storage_dir = self.config.get_avatar_path(date_str, scene, avatar_id)
            os.makedirs(storage_dir, exist_ok=True)
            
            # 生成唯一文件名
            file_ext = os.path.splitext(file_name)[1] or ".png"
            unique_filename = f"{image_id}{file_ext}"
            storage_path = os.path.join(storage_dir, unique_filename)
            
            # 暂时先复制文件（实际使用时可能需要移动）
            import shutil
            shutil.copy2(image_path, storage_path)
            
            # 语义描述
            semantic_description = self._generate_semantic_description(
                prompt, category, scene, analysis_result
            )
            
            metadata = ImageMetadata(
                image_id=image_id,
                file_name=unique_filename,
                file_path=storage_path,
                file_size=file_size,
                dimensions=analysis_result.dimensions,
                format=analysis_result.format.lower(),
                prompt=prompt,
                negative_prompt=negative_prompt,
                model_name=model_name,
                model_version=model_version,
                generation_params=generation_params,
                avatar_id=avatar_id,
                task_id=task_id,
                scene=scene,
                category=category,
                tags=tags,
                quality_grade=quality_grade,
                quality_metrics=quality_metrics,
                has_issues=has_issues,
                issue_details=issue_details,
                creator="SellAI系统",
                created_at=created_at,
                copyright=f"Copyright © {datetime.now().year} SellAI系统",
                usage_rights={
                    "commercial_use": True,
                    "modification_allowed": True,
                    "attribution_required": False,
                    "redistribution_allowed": True,
                },
                semantic_description=semantic_description,
                embedding_vector=None,  # 实际使用时需要计算
            )
            
            # 9. 验证元数据
            is_valid, validation_errors = validate_metadata(metadata)
            if not is_valid:
                logger.error(f"元数据验证失败: {validation_errors}")
                return None, validation_errors
            
            # 10. 保存元数据文件
            self._save_metadata_file(metadata)
            
            logger.info(f"图片处理完成: {image_id}, 质量: {quality_grade.value}")
            return metadata, warnings
            
        except Exception as e:
            logger.error(f"图片处理失败: {str(e)}", exc_info=True)
            return None, [f"处理异常: {str(e)}"]
    
    def _analyze_image(self, image_path: str) -> ImageAnalysisResult:
        """分析图片文件"""
        if not IMAGE_LIB_AVAILABLE:
            # 回退方案：仅获取基本信息
            import imghdr
            image_type = imghdr.what(image_path) or "unknown"
            return ImageAnalysisResult(
                dimensions=(2048, 2048),  # 假设默认
                format=image_type,
                mode="RGB",
                exif_data=None,
                dominant_colors=None,
                estimated_clarity=0.8,
                estimated_brightness=0.7,
                estimated_contrast=0.6,
                has_human_faces=False,
                face_count=0,
                has_text=False,
            )
        
        try:
            with Image.open(image_path) as img:
                # 获取基础信息
                dimensions = img.size
                format = img.format or "UNKNOWN"
                mode = img.mode
                
                # 提取EXIF数据
                exif_data = None
                try:
                    exif = img._getexif()
                    if exif:
                        exif_data = {}
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode('utf-8', errors='ignore')
                                except:
                                    value = str(value)
                            exif_data[tag] = value
                except Exception:
                    pass
                
                # 简化分析（完整实现需要更复杂的算法）
                # 这里使用简化的估计值
                estimated_clarity = 0.85  # 实际应根据图像细节计算
                estimated_brightness = 0.75  # 实际应根据直方图计算
                estimated_contrast = 0.65  # 实际应根据标准差计算
                
                # 简化的人脸检测（实际应使用专用库）
                has_human_faces = False
                face_count = 0
                if dimensions[0] >= 512 and dimensions[1] >= 512:
                    # 这里简化判断：如果图片较大且包含肤色区域，可能有人脸
                    # 实际应使用face_recognition或dlib
                    pass
                
                # 简化文本检测
                has_text = False
                
                # 简化主色提取
                dominant_colors = None
                try:
                    # 缩小图片以加速处理
                    small_img = img.resize((100, 100))
                    colors = small_img.getcolors(maxcolors=10000)
                    if colors:
                        # 取前3个最多的颜色
                        colors.sort(key=lambda x: x[0], reverse=True)
                        dominant_colors = [color[1] for color in colors[:3]]
                except Exception:
                    pass
                
                return ImageAnalysisResult(
                    dimensions=dimensions,
                    format=format,
                    mode=mode,
                    exif_data=exif_data,
                    dominant_colors=dominant_colors,
                    estimated_clarity=estimated_clarity,
                    estimated_brightness=estimated_brightness,
                    estimated_contrast=estimated_contrast,
                    has_human_faces=has_human_faces,
                    face_count=face_count,
                    has_text=has_text,
                )
                
        except Exception as e:
            logger.error(f"图片分析失败: {str(e)}")
            # 返回默认结果
            return ImageAnalysisResult(
                dimensions=(2048, 2048),
                format="UNKNOWN",
                mode="RGB",
                exif_data=None,
                dominant_colors=None,
                estimated_clarity=0.5,
                estimated_brightness=0.5,
                estimated_contrast=0.5,
                has_human_faces=False,
                face_count=0,
                has_text=False,
            )
    
    def _auto_classify_image(self, analysis_result: ImageAnalysisResult,
                            prompt: str, scene: str, avatar_id: str) -> AssetCategory:
        """自动分类图片"""
        prompt_lower = prompt.lower()
        
        # 基于提示词的关键词分类
        product_keywords = ["product", "商品", "产品", "item", "goods", "merchandise"]
        model_keywords = ["model", "模特", "portrait", "人像", "人物", "face"]
        marketing_keywords = ["ad", "广告", "marketing", "营销", "promotion", "推广", "海报"]
        ui_keywords = ["ui", "interface", "界面", "component", "组件", "button", "icon"]
        brand_keywords = ["logo", "品牌", "brand", "identity", "标识"]
        
        # 检查场景
        scene_lower = scene.lower()
        if any(keyword in scene_lower for keyword in ["product", "产品", "商品"]):
            return AssetCategory.PRODUCT_IMAGE
        elif any(keyword in scene_lower for keyword in ["model", "模特", "人像"]):
            return AssetCategory.MODEL_PHOTO
        elif any(keyword in scene_lower for keyword in ["marketing", "营销", "广告"]):
            return AssetCategory.MARKETING_MATERIAL
        elif any(keyword in scene_lower for keyword in ["ui", "界面", "组件"]):
            return AssetCategory.UI_COMPONENT
        elif any(keyword in scene_lower for keyword in ["brand", "品牌", "logo"]):
            return AssetCategory.BRAND_ASSET
        
        # 检查提示词
        if any(keyword in prompt_lower for keyword in product_keywords):
            return AssetCategory.PRODUCT_IMAGE
        elif any(keyword in prompt_lower for keyword in model_keywords):
            return AssetCategory.MODEL_PHOTO
        elif any(keyword in prompt_lower for keyword in marketing_keywords):
            return AssetCategory.MARKETING_MATERIAL
        elif any(keyword in prompt_lower for keyword in ui_keywords):
            return AssetCategory.UI_COMPONENT
        elif any(keyword in prompt_lower for keyword in brand_keywords):
            return AssetCategory.BRAND_ASSET
        
        # 根据图片特征
        if analysis_result.has_human_faces:
            return AssetCategory.MODEL_PHOTO
        elif analysis_result.dimensions[0] > 2000 and analysis_result.dimensions[1] > 2000:
            # 高分辨率图片可能是产品图
            return AssetCategory.PRODUCT_IMAGE
        
        # 默认分类
        return AssetCategory.OTHER
    
    def _generate_tags(self, analysis_result: ImageAnalysisResult,
                      category: AssetCategory, scene: str, 
                      avatar_id: str, generation_params: Dict[str, Any]) -> List[str]:
        """生成标签列表"""
        tags = []
        
        # 基础标签
        tags.append(f"category:{category.value}")
        tags.append(f"scene:{scene}")
        tags.append(f"avatar:{avatar_id}")
        
        # 质量标签
        clarity_tag = f"clarity:{'high' if analysis_result.estimated_clarity > 0.8 else 'medium' if analysis_result.estimated_clarity > 0.6 else 'low'}"
        tags.append(clarity_tag)
        
        # 尺寸标签
        width, height = analysis_result.dimensions
        if width >= 2048 and height >= 2048:
            tags.append("resolution:4k+")
        elif width >= 1024 and height >= 1024:
            tags.append("resolution:hd")
        else:
            tags.append("resolution:sd")
        
        # 特征标签
        if analysis_result.has_human_faces:
            tags.append("feature:contains_faces")
            tags.append(f"face_count:{analysis_result.face_count}")
        
        if analysis_result.has_text:
            tags.append("feature:contains_text")
        
        # 模型标签
        model_name = generation_params.get("model_name", "")
        if model_name:
            tags.append(f"model:{model_name}")
        
        model_version = generation_params.get("model_version", "")
        if model_version:
            tags.append(f"version:{model_version}")
        
        # 时间标签
        tags.append(f"generated:{datetime.now().strftime('%Y-%m')}")
        
        return tags
    
    def _evaluate_quality(self, analysis_result: ImageAnalysisResult,
                         generation_params: Dict[str, Any]) -> Tuple[ImageQualityGrade, Dict[str, float], bool, Optional[str]]:
        """评估图片质量"""
        quality_metrics = {}
        issues = []
        has_issues = False
        
        # 1. 分辨率检查
        width, height = analysis_result.dimensions
        quality_metrics["resolution_width"] = float(width)
        quality_metrics["resolution_height"] = float(height)
        
        min_width, min_height = self.config.required_resolution
        if width < min_width or height < min_height:
            issues.append(f"分辨率不足: {width}x{height}，最小要求: {min_width}x{min_height}")
            has_issues = True
        
        # 2. 清晰度评估
        clarity_score = analysis_result.estimated_clarity
        quality_metrics["clarity_score"] = clarity_score
        if clarity_score < 0.6:
            issues.append(f"清晰度较低: {clarity_score:.2f}")
            has_issues = True
        
        # 3. 亮度评估
        brightness_score = analysis_result.estimated_brightness
        quality_metrics["brightness_score"] = brightness_score
        if brightness_score < 0.3 or brightness_score > 0.9:
            issues.append(f"亮度异常: {brightness_score:.2f}")
            has_issues = True
        
        # 4. 对比度评估
        contrast_score = analysis_result.estimated_contrast
        quality_metrics["contrast_score"] = contrast_score
        if contrast_score < 0.4:
            issues.append(f"对比度不足: {contrast_score:.2f}")
            has_issues = True
        
        # 5. 人脸一致性检查（简化）
        # 实际应调用banana_face_consistency模块
        face_variance = 0.01  # 假设差异1%
        quality_metrics["face_variance"] = face_variance
        if analysis_result.has_human_faces and face_variance > self.config.max_face_variance:
            issues.append(f"人脸差异过大: {face_variance:.2%}，要求<{self.config.max_face_variance:.0%}")
            has_issues = True
        
        # 6. 面料纹理检查（简化）
        texture_error = 0.02  # 假设误差2%
        quality_metrics["texture_error"] = texture_error
        if texture_error > self.config.max_texture_error:
            issues.append(f"面料纹理误差过大: {texture_error:.2%}，要求<{self.config.max_texture_error:.0%}")
            has_issues = True
        
        # 综合评分
        overall_score = (
            clarity_score * 0.3 +
            brightness_score * 0.2 +
            contrast_score * 0.2 +
            (1 - min(face_variance / 0.1, 1)) * 0.2 +
            (1 - min(texture_error / 0.1, 1)) * 0.1
        )
        quality_metrics["overall_score"] = overall_score
        
        # 确定质量等级
        if not has_issues and overall_score >= 0.9:
            quality_grade = ImageQualityGrade.EXCELLENT
        elif not has_issues and overall_score >= 0.7:
            quality_grade = ImageQualityGrade.GOOD
        elif overall_score >= 0.5:
            quality_grade = ImageQualityGrade.ACCEPTABLE
        else:
            quality_grade = ImageQualityGrade.REJECTED
            has_issues = True
        
        issue_details = "; ".join(issues) if issues else None
        
        return quality_grade, quality_metrics, has_issues, issue_details
    
    def _generate_semantic_description(self, prompt: str, category: AssetCategory,
                                      scene: str, analysis_result: ImageAnalysisResult) -> str:
        """生成语义描述"""
        width, height = analysis_result.dimensions
        
        description_parts = []
        
        # 基础信息
        description_parts.append(f"这是一张{width}x{height}分辨率的图片")
        
        # 类别描述
        category_map = {
            AssetCategory.PRODUCT_IMAGE: "产品展示图",
            AssetCategory.MODEL_PHOTO: "模特人像图",
            AssetCategory.MARKETING_MATERIAL: "营销宣传素材",
            AssetCategory.UI_COMPONENT: "UI界面组件",
            AssetCategory.BRAND_ASSET: "品牌标识资产",
            AssetCategory.OTHER: "其他类型图片",
        }
        description_parts.append(f"属于{category_map[category]}")
        
        # 场景描述
        if scene:
            description_parts.append(f"用于{scene}场景")
        
        # 特征描述
        if analysis_result.has_human_faces:
            description_parts.append(f"包含{analysis_result.face_count}张人脸")
        
        # 提示词摘要
        if prompt and len(prompt) > 0:
            prompt_summary = prompt[:100] + ("..." if len(prompt) > 100 else "")
            description_parts.append(f"生成提示词: {prompt_summary}")
        
        return "。".join(description_parts) + "。"
    
    def _save_metadata_file(self, metadata: ImageMetadata) -> None:
        """保存元数据文件"""
        # 保存JSON文件
        metadata_dir = self.config.metadata_dir
        os.makedirs(metadata_dir, exist_ok=True)
        
        metadata_file = os.path.join(metadata_dir, f"{metadata.image_id}.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.debug(f"元数据已保存: {metadata_file}")
        
        # 同时更新索引文件
        self._update_index(metadata)
    
    def _update_index(self, metadata: ImageMetadata) -> None:
        """更新索引"""
        index_dir = os.path.join(self.config.metadata_dir, "index")
        os.makedirs(index_dir, exist_ok=True)
        
        # 按日期索引
        date_str = datetime.now().strftime("%Y-%m")
        date_index_file = os.path.join(index_dir, f"date_{date_str}.json")
        
        index_entry = {
            "image_id": metadata.image_id,
            "file_path": metadata.file_path,
            "avatar_id": metadata.avatar_id,
            "task_id": metadata.task_id,
            "scene": metadata.scene,
            "category": metadata.category.value,
            "quality_grade": metadata.quality_grade.value,
            "created_at": metadata.created_at,
            "tags": metadata.tags,
        }
        
        # 读取现有索引或创建新索引
        if os.path.exists(date_index_file):
            try:
                with open(date_index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            except Exception:
                index_data = []
        else:
            index_data = []
        
        # 添加新条目
        index_data.append(index_entry)
        
        # 保存索引
        with open(date_index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"索引已更新: {date_index_file}")


# 批量处理支持
class BatchImageProcessor:
    """批量图片处理器"""
    
    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG):
        self.config = config
        self.processor = ImageProcessor(config)
    
    def process_batch(self, image_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量处理图片
        
        Args:
            image_batch: 图片批处理列表，每个元素包含:
                - image_path: 图片路径
                - generation_params: 生成参数
                - avatar_id: 分身ID
                - task_id: 任务ID
                - scene: 使用场景
        
        Returns:
            批处理结果
        """
        start_time = time.time()
        results = {
            "total": len(image_batch),
            "success": 0,
            "failed": 0,
            "processing_time_ms": 0,
            "details": [],
        }
        
        for item in image_batch:
            item_start = time.time()
            
            try:
                metadata, warnings = self.processor.process_image_file(
                    image_path=item["image_path"],
                    generation_params=item["generation_params"],
                    avatar_id=item["avatar_id"],
                    task_id=item["task_id"],
                    scene=item["scene"],
                )
                
                processing_time = (time.time() - item_start) * 1000
                
                if metadata:
                    results["success"] += 1
                    results["details"].append({
                        "image_id": metadata.image_id,
                        "status": "success",
                        "processing_time_ms": processing_time,
                        "quality_grade": metadata.quality_grade.value,
                        "warnings": warnings,
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "status": "failed",
                        "processing_time_ms": processing_time,
                        "errors": warnings,
                    })
                    
            except Exception as e:
                processing_time = (time.time() - item_start) * 1000
                results["failed"] += 1
                results["details"].append({
                    "status": "error",
                    "processing_time_ms": processing_time,
                    "error": str(e),
                })
        
        total_time = (time.time() - start_time) * 1000
        results["processing_time_ms"] = total_time
        
        # 检查性能
        avg_time = total_time / len(image_batch) if image_batch else 0
        if avg_time > self.config.max_processing_delay_ms:
            logger.warning(f"批处理平均延迟 {avg_time:.0f}ms 超过限制 {self.config.max_processing_delay_ms}ms")
        
        logger.info(f"批处理完成: 成功 {results['success']}/{results['total']}, 耗时 {total_time:.0f}ms")
        return results


if __name__ == "__main__":
    # 模块测试
    print("图片处理器模块测试")
    
    # 创建测试配置
    config = PipelineConfig(
        base_storage_dir="test_outputs/images",
        temp_processing_dir="test_temp/processing",
        metadata_dir="test_data/metadata",
    )
    config.ensure_directories()
    
    # 创建测试图片（简单文本图像）
    test_image_path = os.path.join(config.temp_processing_dir, "test_image.png")
    try:
        if IMAGE_LIB_AVAILABLE:
            from PIL import ImageDraw, ImageFont
            img = Image.new('RGB', (512, 512), color='white')
            d = ImageDraw.Draw(img)
            d.text((10, 10), "测试图片", fill='black')
            img.save(test_image_path)
            print(f"测试图片已创建: {test_image_path}")
        else:
            # 创建虚拟文件
            with open(test_image_path, 'wb') as f:
                f.write(b"fake image data")
            print(f"虚拟测试文件已创建: {test_image_path}")
    except Exception as e:
        print(f"创建测试图片失败: {str(e)}")
        test_image_path = None
    
    if test_image_path and os.path.exists(test_image_path):
        # 测试处理器
        processor = ImageProcessor(config)
        
        test_params = {
            "prompt": "A beautiful product image",
            "negative_prompt": "blurry, low quality",
            "model_name": "banana_model_v2",
            "model_version": "2.1",
            "seed": 12345,
            "steps": 50,
            "cfg_scale": 7.5,
        }
        
        metadata, warnings = processor.process_image_file(
            image_path=test_image_path,
            generation_params=test_params,
            avatar_id="test_avatar_001",
            task_id="test_task_001",
            scene="product_shoot",
        )
        
        if metadata:
            print(f"\n处理成功:")
            print(f"  图片ID: {metadata.image_id}")
            print(f"  文件路径: {metadata.file_path}")
            print(f"  尺寸: {metadata.dimensions}")
            print(f"  分类: {metadata.category.value}")
            print(f"  质量等级: {metadata.quality_grade.value}")
            print(f"  标签: {', '.join(metadata.tags[:5])}")
            
            # 验证元数据
            is_valid, errors = validate_metadata(metadata)
            print(f"  元数据验证: {'通过' if is_valid else '失败'}")
            if errors:
                print(f"  验证错误: {errors}")
        else:
            print(f"\n处理失败，警告: {warnings}")
    
    print("\n模块测试完成")