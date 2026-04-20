#!/usr/bin/env python3
"""
电商平台抽象基类
定义所有电商平台适配器必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from .models.product import EcommerceProduct, ProductStatus


class EcommercePlatform(ABC):
    """电商平台抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化电商平台
        
        Args:
            config: 平台配置字典
        """
        self.config = config
        self._initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化平台连接
        
        Returns:
            是否初始化成功
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        测试平台连接
        
        Returns:
            (是否成功, 错误信息)
        """
        pass
    
    @abstractmethod
    def create_product(self, product: EcommerceProduct) -> Tuple[bool, Optional[str], Optional[EcommerceProduct]]:
        """
        创建新产品
        
        Args:
            product: 产品数据
            
        Returns:
            (是否成功, 错误信息, 创建的产品)
        """
        pass
    
    @abstractmethod
    def update_product(self, product_id: str, product: EcommerceProduct) -> Tuple[bool, Optional[str]]:
        """
        更新现有产品
        
        Args:
            product_id: 产品ID
            product: 更新后的产品数据
            
        Returns:
            (是否成功, 错误信息)
        """
        pass
    
    @abstractmethod
    def get_product(self, product_id: str) -> Tuple[bool, Optional[str], Optional[EcommerceProduct]]:
        """
        获取产品详情
        
        Args:
            product_id: 产品ID
            
        Returns:
            (是否成功, 错误信息, 产品数据)
        """
        pass
    
    @abstractmethod
    def list_products(self, limit: int = 50, status: Optional[ProductStatus] = None) -> Tuple[bool, Optional[str], List[EcommerceProduct]]:
        """
        列出产品
        
        Args:
            limit: 返回数量限制
            status: 筛选状态
            
        Returns:
            (是否成功, 错误信息, 产品列表)
        """
        pass
    
    @abstractmethod
    def delete_product(self, product_id: str) -> Tuple[bool, Optional[str]]:
        """
        删除产品
        
        Args:
            product_id: 产品ID
            
        Returns:
            (是否成功, 错误信息)
        """
        pass
    
    @abstractmethod
    def upload_image(self, image_path: str, product_id: Optional[str] = None, 
                    alt_text: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        上传图片到平台
        
        Args:
            image_path: 本地图片路径
            product_id: 关联产品ID（可选）
            alt_text: ALT文本（可选）
            
        Returns:
            (是否成功, 错误信息, 图片URL)
        """
        pass
    
    @abstractmethod
    def create_collection(self, name: str, description: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        创建产品集合/分类
        
        Args:
            name: 集合名称
            description: 集合描述
            
        Returns:
            (是否成功, 错误信息, 集合ID)
        """
        pass
    
    @abstractmethod
    def add_product_to_collection(self, product_id: str, collection_id: str) -> Tuple[bool, Optional[str]]:
        """
        添加产品到集合
        
        Args:
            product_id: 产品ID
            collection_id: 集合ID
            
        Returns:
            (是否成功, 错误信息)
        """
        pass
    
    @abstractmethod
    def update_inventory(self, variant_id: str, quantity: int) -> Tuple[bool, Optional[str]]:
        """
        更新库存
        
        Args:
            variant_id: 变体ID
            quantity: 库存数量
            
        Returns:
            (是否成功, 错误信息)
        """
        pass
    
    @abstractmethod
    def get_orders(self, limit: int = 50, status: Optional[str] = None) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
        """
        获取订单列表
        
        Args:
            limit: 返回数量限制
            status: 订单状态筛选
            
        Returns:
            (是否成功, 错误信息, 订单列表)
        """
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        获取订单详情
        
        Args:
            order_id: 订单ID
            
        Returns:
            (是否成功, 错误信息, 订单详情)
        """
        pass
    
    # 可选方法：平台特定功能
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return self.__class__.__name__.replace("Adapter", "")
    
    def get_default_product_type(self) -> str:
        """获取默认产品类型"""
        return self.config.get("product_sync", {}).get("default_product_type", "General")
    
    def get_default_vendor(self) -> str:
        """获取默认供应商"""
        return self.config.get("product_sync", {}).get("default_vendor", "Banana生图AI")
    
    def should_auto_publish(self) -> bool:
        """是否自动发布产品"""
        return self.config.get("automation", {}).get("auto_publish", True)
    
    def get_default_collections(self) -> List[str]:
        """获取默认集合列表"""
        return self.config.get("automation", {}).get("collection_names", ["AI生成设计"])
    
    # 通用工具方法
    def generate_sku(self, product_title: str, variant_options: Dict[str, str] = None) -> str:
        """
        生成SKU编码
        
        Args:
            product_title: 产品标题
            variant_options: 变体选项字典
            
        Returns:
            SKU编码
        """
        # 提取标题中的字母和数字
        import re
        base_sku = re.sub(r'[^A-Z0-9]', '', product_title.upper())[:8]
        
        if variant_options:
            # 添加变体标识
            option_codes = []
            for key, value in variant_options.items():
                if value:
                    # 取前两个字符
                    code = re.sub(r'[^A-Z0-9]', '', value.upper())[:2]
                    option_codes.append(code)
            
            if option_codes:
                base_sku += "_" + "_".join(option_codes)
        
        return base_sku
    
    def validate_product(self, product: EcommerceProduct) -> Tuple[bool, Optional[str]]:
        """
        验证产品数据有效性
        
        Args:
            product: 产品数据
            
        Returns:
            (是否有效, 错误信息)
        """
        if not product.title or len(product.title.strip()) == 0:
            return False, "产品标题不能为空"
        
        if not product.description or len(product.description.strip()) == 0:
            return False, "产品描述不能为空"
        
        if len(product.images) == 0:
            return False, "产品必须至少有一张图片"
        
        # 检查图片格式
        allowed_formats = self.config.get("image_upload", {}).get("allowed_formats", ["jpg", "jpeg", "png"])
        for image in product.images:
            if image.local_path:
                import os
                ext = os.path.splitext(image.local_path)[1].lower().lstrip('.')
                if ext not in allowed_formats:
                    return False, f"图片格式不支持: {ext}"
        
        return True, None
    
    def get_banana_integration_config(self) -> Dict[str, Any]:
        """获取Banana集成配置"""
        return self.config.get("banana_integration", {})