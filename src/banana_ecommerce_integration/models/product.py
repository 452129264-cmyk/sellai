#!/usr/bin/env python3
"""
电商产品数据模型
定义跨平台统一的产品数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class ProductStatus(Enum):
    """产品状态枚举"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 已发布
    ARCHIVED = "archived"  # 已归档
    DELETED = "deleted"  # 已删除


class InventoryPolicy(Enum):
    """库存策略枚举"""
    DENY = "deny"  # 无库存时拒绝销售
    CONTINUE = "continue"  # 无库存时继续销售


@dataclass
class ProductImage:
    """产品图片模型"""
    image_id: str  # 图片唯一标识
    url: str  # 图片URL
    alt_text: Optional[str] = None  # ALT文本
    position: int = 0  # 图片位置
    width: Optional[int] = None  # 图片宽度
    height: Optional[int] = None  # 图片高度
    file_size: Optional[int] = None  # 文件大小
    local_path: Optional[str] = None  # 本地文件路径
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "image_id": self.image_id,
            "url": self.url,
            "alt_text": self.alt_text,
            "position": self.position,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
            "local_path": self.local_path,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductImage':
        """从字典创建"""
        return cls(
            image_id=data.get("image_id", ""),
            url=data.get("url", ""),
            alt_text=data.get("alt_text"),
            position=data.get("position", 0),
            width=data.get("width"),
            height=data.get("height"),
            file_size=data.get("file_size"),
            local_path=data.get("local_path"),
            metadata=data.get("metadata", {})
        )


@dataclass
class ProductVariant:
    """产品变体模型"""
    variant_id: str  # 变体唯一标识
    sku: Optional[str] = None  # SKU编码
    price: float = 0.0  # 价格
    compare_at_price: Optional[float] = None  # 原价/对比价
    cost: Optional[float] = None  # 成本价
    inventory_quantity: int = 0  # 库存数量
    inventory_policy: InventoryPolicy = InventoryPolicy.DENY  # 库存策略
    weight: Optional[float] = None  # 重量
    weight_unit: str = "kg"  # 重量单位
    option1: Optional[str] = None  # 选项1
    option2: Optional[str] = None  # 选项2
    option3: Optional[str] = None  # 选项3
    barcode: Optional[str] = None  # 条形码
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "variant_id": self.variant_id,
            "sku": self.sku,
            "price": self.price,
            "compare_at_price": self.compare_at_price,
            "cost": self.cost,
            "inventory_quantity": self.inventory_quantity,
            "inventory_policy": self.inventory_policy.value,
            "weight": self.weight,
            "weight_unit": self.weight_unit,
            "option1": self.option1,
            "option2": self.option2,
            "option3": self.option3,
            "barcode": self.barcode,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductVariant':
        """从字典创建"""
        inventory_policy = InventoryPolicy(data.get("inventory_policy", "deny"))
        return cls(
            variant_id=data.get("variant_id", ""),
            sku=data.get("sku"),
            price=float(data.get("price", 0)),
            compare_at_price=data.get("compare_at_price"),
            cost=data.get("cost"),
            inventory_quantity=int(data.get("inventory_quantity", 0)),
            inventory_policy=inventory_policy,
            weight=data.get("weight"),
            weight_unit=data.get("weight_unit", "kg"),
            option1=data.get("option1"),
            option2=data.get("option2"),
            option3=data.get("option3"),
            barcode=data.get("barcode"),
            metadata=data.get("metadata", {})
        )


@dataclass
class EcommerceProduct:
    """电商产品模型"""
    product_id: str  # 产品唯一标识
    title: str  # 产品标题
    description: str  # 产品描述
    handle: Optional[str] = None  # 产品URL句柄
    product_type: Optional[str] = None  # 产品类型
    vendor: Optional[str] = None  # 供应商
    tags: List[str] = field(default_factory=list)  # 标签
    status: ProductStatus = ProductStatus.DRAFT  # 状态
    images: List[ProductImage] = field(default_factory=list)  # 图片列表
    variants: List[ProductVariant] = field(default_factory=list)  # 变体列表
    collections: List[str] = field(default_factory=list)  # 所属集合
    seo_title: Optional[str] = None  # SEO标题
    seo_description: Optional[str] = None  # SEO描述
    created_at: Optional[datetime] = None  # 创建时间
    updated_at: Optional[datetime] = None  # 更新时间
    published_at: Optional[datetime] = None  # 发布时间
    platform_specific: Dict[str, Any] = field(default_factory=dict)  # 平台特定数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "product_id": self.product_id,
            "title": self.title,
            "description": self.description,
            "handle": self.handle,
            "product_type": self.product_type,
            "vendor": self.vendor,
            "tags": self.tags,
            "status": self.status.value,
            "images": [img.to_dict() for img in self.images],
            "variants": [var.to_dict() for var in self.variants],
            "collections": self.collections,
            "seo_title": self.seo_title,
            "seo_description": self.seo_description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "platform_specific": self.platform_specific
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EcommerceProduct':
        """从字典创建"""
        # 解析日期字段
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        published_at = data.get("published_at")
        
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        
        if published_at and isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        
        # 解析状态
        status = ProductStatus(data.get("status", "draft"))
        
        # 解析图片列表
        images = [ProductImage.from_dict(img) for img in data.get("images", [])]
        
        # 解析变体列表
        variants = [ProductVariant.from_dict(var) for var in data.get("variants", [])]
        
        return cls(
            product_id=data.get("product_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            handle=data.get("handle"),
            product_type=data.get("product_type"),
            vendor=data.get("vendor"),
            tags=data.get("tags", []),
            status=status,
            images=images,
            variants=variants,
            collections=data.get("collections", []),
            seo_title=data.get("seo_title"),
            seo_description=data.get("seo_description"),
            created_at=created_at,
            updated_at=updated_at,
            published_at=published_at,
            platform_specific=data.get("platform_specific", {})
        )
    
    def add_image(self, image: ProductImage) -> None:
        """添加图片"""
        self.images.append(image)
        # 按位置排序
        self.images.sort(key=lambda x: x.position)
    
    def add_variant(self, variant: ProductVariant) -> None:
        """添加变体"""
        self.variants.append(variant)
    
    def get_main_image(self) -> Optional[ProductImage]:
        """获取主图（位置为0的图片）"""
        for image in self.images:
            if image.position == 0:
                return image
        return self.images[0] if self.images else None
    
    def update_from_banana_image(self, image_path: str, metadata: Dict[str, Any]) -> None:
        """
        从Banana生图结果更新产品图片
        
        Args:
            image_path: 生成的图片路径
            metadata: Banana生图元数据
        """
        image_id = metadata.get("image_id", f"banana_{datetime.now().timestamp()}")
        
        image = ProductImage(
            image_id=image_id,
            url=f"file://{image_path}",  # 临时URL，实际使用时需要上传
            alt_text=metadata.get("prompt", self.title),
            position=len(self.images),
            local_path=image_path,
            metadata=metadata
        )
        
        self.add_image(image)
        
        # 更新产品描述（如果包含生成提示）
        if "prompt" in metadata and metadata["prompt"]:
            if metadata["prompt"] not in self.description:
                self.description += f"\n\n{metadata['prompt']}"