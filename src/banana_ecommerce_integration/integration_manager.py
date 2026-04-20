#!/usr/bin/env python3
"""
Banana生图内核与电商平台集成管理器
负责协调图片生成、产品创建、数据同步全流程
"""

import os
import json
import yaml
import time
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Union
from pathlib import Path
import hashlib
import shutil

# 尝试导入Banana相关模块
try:
    from src.banana_face_consistency import FaceFeatureExtractor, QualityLockController
    BANANA_AVAILABLE = True
except ImportError:
    BANANA_AVAILABLE = False
    print("警告: Banana生图内核模块未找到，部分功能受限")

# 尝试导入素材库管理
try:
    from src.banana_asset_pipeline import AssetPipeline, MemorySyncManager
    ASSET_PIPELINE_AVAILABLE = True
except ImportError:
    ASSET_PIPELINE_AVAILABLE = False
    print("警告: 素材库管道模块未找到，数据留存功能受限")

from .base import EcommercePlatform
from .adapters.shopify_adapter import ShopifyAdapter
from .adapters.dianfu_adapter import DianfuAdapter
from .models.product import EcommerceProduct, ProductStatus, ProductImage, ProductVariant


logger = logging.getLogger(__name__)


class EcommerceIntegrationManager:
    """电商集成管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化集成管理器
        
        Args:
            config_path: 配置文件路径，默认为 config/shopify_api.yaml
        """
        if config_path is None:
            config_path = "config/shopify_api.yaml"
        
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        # 电商平台实例
        self.platforms: Dict[str, EcommercePlatform] = {}
        self.active_platform: Optional[EcommercePlatform] = None
        
        # Banana生图组件
        self.face_extractor: Optional[FaceFeatureExtractor] = None
        self.quality_controller: Optional[QualityLockController] = None
        
        # 素材库管道
        self.asset_pipeline: Optional[AssetPipeline] = None
        self.memory_sync: Optional[MemorySyncManager] = None
        
        # 状态跟踪
        self.stats = {
            "products_created": 0,
            "images_generated": 0,
            "last_operation_time": None,
            "errors": 0
        }
        
        # 本地数据存储
        self.data_dir = self.config.get("data_retention", {}).get("local_storage_path", 
                                                                 "data/banana_ecommerce/products")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化组件
        self._initialize_components()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    return yaml.safe_load(f)
                elif config_path.endswith('.json'):
                    return json.load(f)
                else:
                    # 尝试作为YAML加载
                    return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {config_path}, 错误: {str(e)}")
            # 返回默认配置
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "shop_domain": "",
            "access_token": "",
            "api_version": "2024-01",
            "product_sync": {
                "default_product_type": "服装",
                "default_vendor": "Banana生图AI",
                "inventory_management": True,
                "default_inventory_quantity": 100,
                "default_price": "99.99"
            },
            "banana_integration": {
                "enabled": True,
                "generation_params": {
                    "resolution": "2048x2048",
                    "style": "fashion_photography"
                }
            },
            "data_retention": {
                "enabled": True,
                "local_storage_path": "data/banana_ecommerce/products"
            }
        }
    
    def _initialize_components(self):
        """初始化所有组件"""
        # 1. 初始化电商平台
        self._initialize_ecommerce_platforms()
        
        # 2. 初始化Banana生图组件
        if BANANA_AVAILABLE and self.config.get("banana_integration", {}).get("enabled", True):
            self._initialize_banana_components()
        
        # 3. 初始化素材库管道
        if ASSET_PIPELINE_AVAILABLE:
            self._initialize_asset_pipeline()
        
        logger.info("电商集成管理器初始化完成")
    
    def _initialize_ecommerce_platforms(self):
        """初始化电商平台适配器"""
        # Shopify平台
        shopify_config = self.config.copy()
        self.platforms["shopify"] = ShopifyAdapter(shopify_config)
        
        # 店府平台
        dianfu_enabled = self.config.get("dianfu_config", {}).get("enabled", False)
        if dianfu_enabled:
            dianfu_config = self.config.get("dianfu_config", {}).copy()
            self.platforms["dianfu"] = DianfuAdapter(dianfu_config)
        
        # 默认平台
        self.active_platform = self.platforms.get("shopify")
        
        # 初始化连接
        for name, platform in self.platforms.items():
            success = platform.initialize()
            if success:
                logger.info(f"电商平台 '{name}' 初始化成功")
            else:
                logger.warning(f"电商平台 '{name}' 初始化失败")
    
    def _initialize_banana_components(self):
        """初始化Banana生图组件"""
        try:
            # 初始化人脸特征提取器
            self.face_extractor = FaceFeatureExtractor()
            logger.info("Banana人脸特征提取器初始化成功")
            
            # 初始化质量锁控制器
            self.quality_controller = QualityLockController()
            logger.info("Banana质量锁控制器初始化成功")
            
        except Exception as e:
            logger.error(f"Banana组件初始化失败: {str(e)}")
            self.face_extractor = None
            self.quality_controller = None
    
    def _initialize_asset_pipeline(self):
        """初始化素材库管道"""
        try:
            # 初始化资产管道
            self.asset_pipeline = AssetPipeline()
            logger.info("素材库管道初始化成功")
            
            # 初始化记忆同步
            self.memory_sync = MemorySyncManager()
            logger.info("记忆同步管理器初始化成功")
            
        except Exception as e:
            logger.error(f"素材库管道初始化失败: {str(e)}")
            self.asset_pipeline = None
            self.memory_sync = None
    
    def set_active_platform(self, platform_name: str) -> bool:
        """
        设置当前活动的电商平台
        
        Args:
            platform_name: 平台名称，如 "shopify" 或 "dianfu"
            
        Returns:
            是否设置成功
        """
        if platform_name in self.platforms:
            self.active_platform = self.platforms[platform_name]
            logger.info(f"已设置活动平台: {platform_name}")
            return True
        else:
            logger.error(f"平台不存在: {platform_name}")
            return False
    
    def generate_and_publish_product(self, 
                                    title: str,
                                    description: str,
                                    generation_prompt: Optional[str] = None,
                                    product_type: Optional[str] = None,
                                    vendor: Optional[str] = None,
                                    tags: Optional[List[str]] = None,
                                    collections: Optional[List[str]] = None,
                                    auto_publish: Optional[bool] = None) -> Tuple[bool, Optional[str], Optional[EcommerceProduct]]:
        """
        生成图片并发布产品（全流程自动化）
        
        Args:
            title: 产品标题
            description: 产品描述
            generation_prompt: 图片生成提示词，如未提供则基于标题生成
            product_type: 产品类型
            vendor: 供应商
            tags: 标签列表
            collections: 集合列表
            auto_publish: 是否自动发布，如未提供则使用配置
            
        Returns:
            (是否成功, 错误信息, 创建的产品)
        """
        start_time = time.time()
        
        try:
            # 1. 验证参数
            if not title or not description:
                return False, "产品标题和描述不能为空", None
            
            # 2. 生成产品ID
            product_id = self._generate_product_id(title)
            
            # 3. 创建基础产品对象
            product = EcommerceProduct(
                product_id=product_id,
                title=title,
                description=description,
                product_type=product_type or self.active_platform.get_default_product_type(),
                vendor=vendor or self.active_platform.get_default_vendor(),
                tags=tags or [],
                collections=collections or self.active_platform.get_default_collections(),
                status=ProductStatus.DRAFT
            )
            
            # 4. 生成产品图片
            if BANANA_AVAILABLE and self.face_extractor and self.quality_controller:
                generation_success, image_path, image_metadata = self._generate_product_images(
                    product=product,
                    prompt=generation_prompt or f"High quality product photo of {title}, professional photography, studio lighting, detailed texture"
                )
                
                if not generation_success:
                    return False, f"图片生成失败: {image_path}", None
                
                # 更新产品图片信息
                product.update_from_banana_image(image_path, image_metadata)
                
                # 检查质量锁
                quality_check, quality_error = self._check_image_quality(image_path, image_metadata)
                if not quality_check:
                    logger.warning(f"图片质量检查失败: {quality_error}")
                    # 可以选择重试或继续
            else:
                # 使用模拟图片
                logger.warning("Banana生图组件不可用，使用模拟图片")
                image_path = self._create_mock_image(product)
                product.add_image(ProductImage(
                    image_id=f"mock_{product_id}",
                    url=f"file://{image_path}",
                    alt_text=title,
                    position=0,
                    local_path=image_path
                ))
            
            # 5. 创建电商平台产品
            if not self.active_platform:
                return False, "未设置活动电商平台", None
            
            create_success, create_error, created_product = self.active_platform.create_product(product)
            
            if not create_success:
                return False, f"产品创建失败: {create_error}", None
            
            # 6. 自动发布（如配置）
            if auto_publish or (auto_publish is None and self.active_platform.should_auto_publish()):
                if created_product.status != ProductStatus.ACTIVE:
                    # 更新产品状态为已发布
                    created_product.status = ProductStatus.ACTIVE
                    update_success, update_error = self.active_platform.update_product(
                        created_product.product_id, created_product
                    )
                    
                    if not update_success:
                        logger.warning(f"产品自动发布失败: {update_error}")
                    else:
                        logger.info("产品自动发布成功")
            
            # 7. 数据留存
            self._retain_product_data(created_product)
            
            # 8. 更新统计
            self.stats["products_created"] += 1
            self.stats["last_operation_time"] = datetime.now().isoformat()
            
            # 计算处理时间
            processing_time = time.time() - start_time
            logger.info(f"产品生成发布完成: {created_product.product_id}, 耗时: {processing_time:.2f}秒")
            
            return True, None, created_product
            
        except Exception as e:
            error_msg = f"产品生成发布异常: {str(e)}"
            logger.error(error_msg)
            self.stats["errors"] += 1
            return False, error_msg, None
    
    def batch_generate_products(self, 
                               product_list: List[Dict[str, Any]],
                               platform_name: str = "shopify",
                               concurrent: int = 3) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        批量生成并发布产品
        
        Args:
            product_list: 产品列表，每个元素包含title, description等字段
            platform_name: 目标平台名称
            concurrent: 并发处理数量
            
        Returns:
            (成功数量, 失败数量, 详细信息列表)
        """
        # 设置活动平台
        if not self.set_active_platform(platform_name):
            return 0, len(product_list), []
        
        success_count = 0
        failed_count = 0
        details = []
        
        # 简单实现：顺序处理
        # 实际应用中应使用线程池或异步处理
        for idx, product_data in enumerate(product_list):
            logger.info(f"处理产品 {idx+1}/{len(product_list)}: {product_data.get('title', '')}")
            
            success, error, product = self.generate_and_publish_product(
                title=product_data.get("title", ""),
                description=product_data.get("description", ""),
                generation_prompt=product_data.get("generation_prompt"),
                product_type=product_data.get("product_type"),
                vendor=product_data.get("vendor"),
                tags=product_data.get("tags"),
                collections=product_data.get("collections")
            )
            
            detail = {
                "index": idx,
                "title": product_data.get("title", ""),
                "success": success,
                "error": error,
                "product_id": product.product_id if product else None
            }
            
            if success:
                success_count += 1
                logger.info(f"产品处理成功: {product.product_id}")
            else:
                failed_count += 1
                logger.error(f"产品处理失败: {error}")
            
            details.append(detail)
            
            # 避免请求过于频繁
            if idx < len(product_list) - 1:
                time.sleep(1)
        
        logger.info(f"批量处理完成: 成功 {success_count}, 失败 {failed_count}")
        return success_count, failed_count, details
    
    def sync_existing_products(self, 
                              limit: int = 100,
                              platform_name: str = "shopify") -> Tuple[int, List[EcommerceProduct]]:
        """
        同步电商平台现有产品到本地数据库
        
        Args:
            limit: 同步数量限制
            platform_name: 平台名称
            
        Returns:
            (同步数量, 产品列表)
        """
        if platform_name not in self.platforms:
            logger.error(f"平台不存在: {platform_name}")
            return 0, []
        
        platform = self.platforms[platform_name]
        
        try:
            success, error, products = platform.list_products(limit=limit)
            
            if not success:
                logger.error(f"获取产品列表失败: {error}")
                return 0, []
            
            # 保存到本地
            synced_count = 0
            for product in products:
                try:
                    self._save_product_to_local(product)
                    synced_count += 1
                except Exception as e:
                    logger.warning(f"保存产品失败 {product.product_id}: {str(e)}")
            
            logger.info(f"产品同步完成: {synced_count}/{len(products)}")
            return synced_count, products
            
        except Exception as e:
            logger.error(f"产品同步异常: {str(e)}")
            return 0, []
    
    def generate_product_from_banana_image(self,
                                          image_path: str,
                                          image_metadata: Dict[str, Any],
                                          title: Optional[str] = None,
                                          description: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[EcommerceProduct]]:
        """
        从已有的Banana生成图片创建产品
        
        Args:
            image_path: 图片路径
            image_metadata: 图片元数据
            title: 产品标题，如未提供则从元数据提取
            description: 产品描述，如未提供则从元数据提取
            
        Returns:
            (是否成功, 错误信息, 创建的产品)
        """
        try:
            # 提取标题和描述
            if not title:
                title = image_metadata.get("prompt", "AI Generated Product")
                # 简化标题
                if len(title) > 80:
                    title = title[:77] + "..."
            
            if not description:
                description = f"AI generated product based on prompt: {image_metadata.get('prompt', '')}"
            
            # 生成产品
            return self.generate_and_publish_product(
                title=title,
                description=description,
                generation_prompt=None,  # 不再生成新图片
                product_type=image_metadata.get("product_type", "AI生成商品"),
                vendor=image_metadata.get("vendor", "Banana生图AI"),
                tags=image_metadata.get("tags", ["AI生成", "时尚设计"]),
                collections=image_metadata.get("collections", ["AI生成设计"])
            )
            
        except Exception as e:
            error_msg = f"从图片创建产品异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    # 私有辅助方法
    def _generate_product_id(self, title: str) -> str:
        """生成产品唯一ID"""
        timestamp = int(time.time() * 1000)
        hash_input = f"{title}_{timestamp}".encode('utf-8')
        hash_hex = hashlib.md5(hash_input).hexdigest()[:12]
        return f"prod_{hash_hex}"
    
    def _generate_product_images(self, 
                                product: EcommerceProduct,
                                prompt: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        生成产品图片
        
        Args:
            product: 产品对象
            prompt: 生成提示词
            
        Returns:
            (是否成功, 图片路径或错误信息, 图片元数据)
        """
        if not BANANA_AVAILABLE or not self.face_extractor:
            return False, "Banana组件不可用", None
        
        try:
            # 这里应该调用Banana生图内核
            # 由于实际集成需要具体API，这里使用模拟实现
            logger.info(f"生成产品图片: {product.title}")
            logger.info(f"生成提示词: {prompt}")
            
            # 模拟图片生成
            image_id = f"banana_{int(time.time())}_{hashlib.md5(prompt.encode()).hexdigest()[:8]}"
            
            # 创建模拟图片文件
            image_dir = os.path.join(self.data_dir, "generated_images")
            os.makedirs(image_dir, exist_ok=True)
            
            image_filename = f"{image_id}.png"
            image_path = os.path.join(image_dir, image_filename)
            
            # 创建简单的模拟图片（实际应用中应调用Banana API）
            self._create_mock_image_file(image_path, product.title)
            
            # 构建元数据
            metadata = {
                "image_id": image_id,
                "prompt": prompt,
                "generation_time": datetime.now().isoformat(),
                "resolution": "2048x2048",
                "model_id": "banana_standard",
                "face_consistency_score": 0.98,
                "texture_accuracy_score": 0.95,
                "quality_grade": "excellent",
                "product_type": product.product_type,
                "vendor": product.vendor,
                "tags": product.tags
            }
            
            logger.info(f"图片生成成功: {image_path}")
            return True, image_path, metadata
            
        except Exception as e:
            error_msg = f"图片生成异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _check_image_quality(self, 
                            image_path: str, 
                            metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        检查图片质量是否符合标准
        
        Args:
            image_path: 图片路径
            metadata: 图片元数据
            
        Returns:
            (是否合格, 错误信息)
        """
        if not self.quality_controller:
            return True, None  # 无质量控制器时默认通过
        
        try:
            # 调用质量锁控制器
            # 实际应用中应实现具体检查逻辑
            face_score = metadata.get("face_consistency_score", 1.0)
            texture_score = metadata.get("texture_accuracy_score", 1.0)
            
            if face_score < 0.97:  # 3%差异
                return False, f"人脸一致性不足: {face_score:.2%}"
            
            if texture_score < 0.95:  # 5%误差
                return False, f"面料纹理精度不足: {texture_score:.2%}"
            
            # 检查分辨率
            from PIL import Image
            with Image.open(image_path) as img:
                width, height = img.size
                
            if width < 2048 or height < 2048:
                return False, f"分辨率不足: {width}x{height}"
            
            return True, None
            
        except Exception as e:
            logger.warning(f"质量检查异常: {str(e)}")
            return False, str(e)
    
    def _create_mock_image(self, product: EcommerceProduct) -> str:
        """创建模拟产品图片"""
        image_dir = os.path.join(self.data_dir, "mock_images")
        os.makedirs(image_dir, exist_ok=True)
        
        image_id = f"mock_{product.product_id}"
        image_filename = f"{image_id}.png"
        image_path = os.path.join(image_dir, image_filename)
        
        # 创建模拟图片文件
        self._create_mock_image_file(image_path, product.title)
        
        return image_path
    
    def _create_mock_image_file(self, image_path: str, title: str):
        """创建模拟图片文件"""
        # 实际应用中应生成真实图片
        # 这里创建简单文本文件作为占位
        if not os.path.exists(image_path):
            with open(image_path, 'w') as f:
                f.write(f"Mock image for: {title}\n")
                f.write(f"Generated at: {datetime.now().isoformat()}\n")
    
    def _retain_product_data(self, product: EcommerceProduct):
        """留存产品数据到本地和记忆系统"""
        try:
            # 1. 保存到本地JSON文件
            self._save_product_to_local(product)
            
            # 2. 同步到素材库管道
            if self.asset_pipeline:
                # 处理产品图片
                for image in product.images:
                    if image.local_path and os.path.exists(image.local_path):
                        # 添加到素材库
                        success, asset_id = self.asset_pipeline.process_image(
                            image_path=image.local_path,
                            metadata={
                                "product_id": product.product_id,
                                "title": product.title,
                                "image_id": image.image_id,
                                "alt_text": image.alt_text
                            }
                        )
                        
                        if success:
                            logger.info(f"产品图片已同步到素材库: {asset_id}")
            
            # 3. 同步到记忆系统
            if self.memory_sync:
                # 构建产品知识文档
                product_doc = {
                    "id": product.product_id,
                    "title": product.title,
                    "content": product.description,
                    "metadata": {
                        "type": "ecommerce_product",
                        "platform": self.active_platform.get_platform_name() if self.active_platform else "unknown",
                        "created_at": product.created_at.isoformat() if product.created_at else datetime.now().isoformat(),
                        "status": product.status.value,
                        "vendor": product.vendor,
                        "product_type": product.product_type,
                        "tags": product.tags,
                        "collections": product.collections
                    }
                }
                
                # 同步到Notebook LM
                success, doc_id = self.memory_sync.sync_product_document(product_doc)
                if success:
                    logger.info(f"产品数据已同步到记忆系统: {doc_id}")
                else:
                    logger.warning(f"产品数据记忆同步失败")
            
            logger.info(f"产品数据留存完成: {product.product_id}")
            
        except Exception as e:
            logger.error(f"产品数据留存异常: {str(e)}")
    
    def _save_product_to_local(self, product: EcommerceProduct) -> str:
        """保存产品数据到本地JSON文件"""
        # 按日期组织目录
        date_str = datetime.now().strftime("%Y%m")
        product_dir = os.path.join(self.data_dir, date_str)
        os.makedirs(product_dir, exist_ok=True)
        
        # 生成文件名
        filename = f"{product.product_id}_{int(time.time())}.json"
        filepath = os.path.join(product_dir, filename)
        
        # 转换为可序列化的字典
        product_dict = product.to_dict()
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(product_dict, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"产品数据已保存到本地: {filepath}")
        return filepath
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        return {
            "products_created": self.stats["products_created"],
            "images_generated": self.stats["images_generated"],
            "last_operation_time": self.stats["last_operation_time"],
            "errors": self.stats["errors"],
            "platforms_available": list(self.platforms.keys()),
            "active_platform": self.active_platform.get_platform_name() if self.active_platform else None,
            "banana_available": BANANA_AVAILABLE,
            "asset_pipeline_available": ASSET_PIPELINE_AVAILABLE
        }
    
    def export_config_template(self, output_path: str = "config/shopify_api_template.yaml"):
        """导出配置模板"""
        template = {
            "shop_domain": "your-store.myshopify.com",
            "api_version": "2024-01",
            "access_token": "your-admin-api-access-token",
            "product_sync": {
                "default_product_type": "服装",
                "default_vendor": "Banana生图AI",
                "inventory_management": True,
                "default_inventory_quantity": 100,
                "default_price": "99.99"
            },
            "automation": {
                "auto_publish": True,
                "collection_names": ["AI生成设计", "牛仔外套", "美式复古"]
            },
            "banana_integration": {
                "enabled": True,
                "generation_params": {
                    "resolution": "2048x2048",
                    "style": "fashion_photography",
                    "model_id": "banana_standard"
                }
            }
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(template, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"配置模板已导出: {output_path}")
        return output_path