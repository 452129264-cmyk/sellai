#!/usr/bin/env python3
"""
Shopify平台适配器
实现与Shopify Admin API的深度集成
"""

import os
import json
import time
import requests
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging

from ..base import EcommercePlatform
from ..models.product import EcommerceProduct, ProductStatus, ProductImage, ProductVariant, InventoryPolicy


logger = logging.getLogger(__name__)


class ShopifyAdapter(EcommercePlatform):
    """Shopify平台适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 提取Shopify配置
        self.shop_domain = config.get("shop_domain", "")
        self.api_version = config.get("api_version", "2024-01")
        self.access_token = config.get("access_token", "")
        self.api_key = config.get("api_key", "")
        self.api_password = config.get("api_password", "")
        
        # 构建基础URL
        if self.shop_domain:
            self.base_url = f"https://{self.shop_domain}/admin/api/{self.api_version}"
        else:
            self.base_url = None
        
        # 请求会话
        self.session = requests.Session()
        if self.access_token:
            self.session.headers.update({
                "X-Shopify-Access-Token": self.access_token,
                "Content-Type": "application/json"
            })
        elif self.api_key and self.api_password:
            self.session.auth = (self.api_key, self.api_password)
        
        # 性能配置
        self.request_timeout = config.get("performance", {}).get("request_timeout_seconds", 30)
        self.max_retries = config.get("performance", {}).get("max_retries", 3)
        self.retry_delay = config.get("performance", {}).get("retry_delay_seconds", 2)
        
        # 状态跟踪
        self.stats = {
            "requests_made": 0,
            "errors": 0,
            "last_request_time": None
        }
    
    def initialize(self) -> bool:
        """初始化Shopify连接"""
        if not self.base_url:
            logger.error("未配置Shopify店铺域名")
            return False
        
        if not self.access_token and not (self.api_key and self.api_password):
            logger.error("未配置API认证信息")
            return False
        
        # 测试连接
        success, error = self.test_connection()
        if success:
            self._initialized = True
            logger.info(f"Shopify适配器初始化成功: {self.shop_domain}")
        else:
            logger.error(f"Shopify适配器初始化失败: {error}")
        
        return success
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """测试Shopify API连接"""
        if not self.base_url:
            return False, "未配置基础URL"
        
        try:
            response = self._make_request("GET", "/shop.json", retry=False)
            
            if response.status_code == 200:
                shop_data = response.json().get("shop", {})
                logger.info(f"Shopify连接测试成功: {shop_data.get('name')}")
                return True, None
            else:
                error_msg = f"API响应错误: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"连接测试异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def create_product(self, product: EcommerceProduct) -> Tuple[bool, Optional[str], Optional[EcommerceProduct]]:
        """
        在Shopify创建新产品
        
        Args:
            product: 产品数据
            
        Returns:
            (是否成功, 错误信息, 创建的产品)
        """
        # 验证产品数据
        is_valid, error = self.validate_product(product)
        if not is_valid:
            return False, error, None
        
        try:
            # 构建Shopify API请求数据
            product_data = self._convert_to_shopify_product(product)
            
            # 调用API
            response = self._make_request("POST", "/products.json", json={"product": product_data})
            
            if response.status_code in [200, 201]:
                shopify_product = response.json().get("product", {})
                
                # 转换为统一模型
                created_product = self._convert_from_shopify_product(shopify_product)
                
                # 添加到集合
                if self.should_auto_publish() and product.status == ProductStatus.ACTIVE:
                    self._add_to_default_collections(created_product.product_id)
                
                logger.info(f"产品创建成功: {created_product.product_id} - {created_product.title}")
                return True, None, created_product
            else:
                error_msg = f"产品创建失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"产品创建异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def update_product(self, product_id: str, product: EcommerceProduct) -> Tuple[bool, Optional[str]]:
        """
        更新Shopify产品
        
        Args:
            product_id: 产品ID
            product: 更新后的产品数据
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 构建更新数据
            update_data = self._convert_to_shopify_product(product)
            
            # 调用API
            response = self._make_request("PUT", f"/products/{product_id}.json", 
                                         json={"product": update_data})
            
            if response.status_code in [200, 201]:
                logger.info(f"产品更新成功: {product_id}")
                return True, None
            else:
                error_msg = f"产品更新失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"产品更新异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_product(self, product_id: str) -> Tuple[bool, Optional[str], Optional[EcommerceProduct]]:
        """
        获取Shopify产品详情
        
        Args:
            product_id: 产品ID
            
        Returns:
            (是否成功, 错误信息, 产品数据)
        """
        try:
            response = self._make_request("GET", f"/products/{product_id}.json")
            
            if response.status_code == 200:
                shopify_product = response.json().get("product", {})
                product = self._convert_from_shopify_product(shopify_product)
                return True, None, product
            else:
                error_msg = f"获取产品失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"获取产品异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def list_products(self, limit: int = 50, status: Optional[ProductStatus] = None) -> Tuple[bool, Optional[str], List[EcommerceProduct]]:
        """
        列出Shopify产品
        
        Args:
            limit: 返回数量限制
            status: 筛选状态
            
        Returns:
            (是否成功, 错误信息, 产品列表)
        """
        try:
            params = {"limit": limit}
            if status:
                # Shopify状态映射
                status_map = {
                    ProductStatus.ACTIVE: "active",
                    ProductStatus.DRAFT: "draft",
                    ProductStatus.ARCHIVED: "archived"
                }
                if status in status_map:
                    params["status"] = status_map[status]
            
            response = self._make_request("GET", "/products.json", params=params)
            
            if response.status_code == 200:
                products_data = response.json().get("products", [])
                products = []
                
                for shopify_product in products_data:
                    product = self._convert_from_shopify_product(shopify_product)
                    products.append(product)
                
                return True, None, products
            else:
                error_msg = f"列出产品失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, []
                
        except Exception as e:
            error_msg = f"列出产品异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, []
    
    def delete_product(self, product_id: str) -> Tuple[bool, Optional[str]]:
        """
        删除Shopify产品
        
        Args:
            product_id: 产品ID
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            response = self._make_request("DELETE", f"/products/{product_id}.json")
            
            if response.status_code == 200:
                logger.info(f"产品删除成功: {product_id}")
                return True, None
            else:
                error_msg = f"产品删除失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"产品删除异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def upload_image(self, image_path: str, product_id: Optional[str] = None, 
                    alt_text: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        上传图片到Shopify
        
        Args:
            image_path: 本地图片路径
            product_id: 关联产品ID（可选）
            alt_text: ALT文本（可选）
            
        Returns:
            (是否成功, 错误信息, 图片URL)
        """
        if not os.path.exists(image_path):
            return False, f"图片文件不存在: {image_path}", None
        
        # 检查文件大小
        max_size_mb = self.config.get("image_upload", {}).get("max_file_size_mb", 20)
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            return False, f"图片文件过大: {file_size_mb:.2f}MB > {max_size_mb}MB", None
        
        try:
            # 读取图片文件
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 构建请求
            import base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            image_data = {
                "image": {
                    "attachment": encoded_image,
                    "filename": os.path.basename(image_path)
                }
            }
            
            if alt_text:
                image_data["image"]["alt"] = alt_text
            
            if product_id:
                # 上传到特定产品
                response = self._make_request("POST", f"/products/{product_id}/images.json", 
                                             json=image_data)
                
                if response.status_code in [200, 201]:
                    image_result = response.json().get("image", {})
                    image_url = image_result.get("src")
                    
                    logger.info(f"产品图片上传成功: {product_id} - {image_url}")
                    return True, None, image_url
                else:
                    error_msg = f"产品图片上传失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return False, error_msg, None
            else:
                # 上传到文件API（独立图片）
                response = self._make_request("POST", "/files.json", 
                                             json={"file": image_data})
                
                if response.status_code in [200, 201]:
                    file_result = response.json().get("file", {})
                    image_url = file_result.get("url")
                    
                    logger.info(f"独立图片上传成功: {image_url}")
                    return True, None, image_url
                else:
                    error_msg = f"独立图片上传失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return False, error_msg, None
                
        except Exception as e:
            error_msg = f"图片上传异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def create_collection(self, name: str, description: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        创建Shopify集合
        
        Args:
            name: 集合名称
            description: 集合描述
            
        Returns:
            (是否成功, 错误信息, 集合ID)
        """
        try:
            collection_data = {
                "custom_collection": {
                    "title": name,
                    "body_html": description or ""
                }
            }
            
            response = self._make_request("POST", "/custom_collections.json", 
                                         json=collection_data)
            
            if response.status_code in [200, 201]:
                collection = response.json().get("custom_collection", {})
                collection_id = str(collection.get("id"))
                
                logger.info(f"集合创建成功: {collection_id} - {name}")
                return True, None, collection_id
            else:
                error_msg = f"集合创建失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"集合创建异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def add_product_to_collection(self, product_id: str, collection_id: str) -> Tuple[bool, Optional[str]]:
        """
        添加产品到Shopify集合
        
        Args:
            product_id: 产品ID
            collection_id: 集合ID
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            collect_data = {
                "collect": {
                    "product_id": product_id,
                    "collection_id": collection_id
                }
            }
            
            response = self._make_request("POST", "/collects.json", json=collect_data)
            
            if response.status_code in [200, 201]:
                logger.info(f"产品添加到集合成功: {product_id} -> {collection_id}")
                return True, None
            else:
                error_msg = f"产品添加到集合失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"产品添加到集合异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def update_inventory(self, variant_id: str, quantity: int) -> Tuple[bool, Optional[str]]:
        """
        更新Shopify库存
        
        Args:
            variant_id: 变体ID
            quantity: 库存数量
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 获取库存项目ID
            location_response = self._make_request("GET", "/locations.json")
            if location_response.status_code != 200:
                return False, f"获取库存位置失败: {location_response.text}"
            
            locations = location_response.json().get("locations", [])
            if not locations:
                return False, "未找到库存位置"
            
            location_id = locations[0].get("id")  # 使用第一个位置
            
            # 获取变体的库存项目
            inventory_response = self._make_request("GET", 
                                                   f"/variants/{variant_id}/inventory_levels.json?location_ids={location_id}")
            
            if inventory_response.status_code != 200:
                return False, f"获取库存信息失败: {inventory_response.text}"
            
            inventory_levels = inventory_response.json().get("inventory_levels", [])
            if not inventory_levels:
                return False, "未找到库存项目"
            
            inventory_item_id = inventory_levels[0].get("inventory_item_id")
            
            # 更新库存
            update_data = {
                "location_id": location_id,
                "inventory_item_id": inventory_item_id,
                "available": quantity
            }
            
            response = self._make_request("POST", "/inventory_levels/set.json", 
                                         json=update_data)
            
            if response.status_code in [200, 201]:
                logger.info(f"库存更新成功: {variant_id} -> {quantity}")
                return True, None
            else:
                error_msg = f"库存更新失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"库存更新异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_orders(self, limit: int = 50, status: Optional[str] = None) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
        """
        获取Shopify订单
        
        Args:
            limit: 返回数量限制
            status: 订单状态筛选
            
        Returns:
            (是否成功, 错误信息, 订单列表)
        """
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status
            
            response = self._make_request("GET", "/orders.json", params=params)
            
            if response.status_code == 200:
                orders = response.json().get("orders", [])
                return True, None, orders
            else:
                error_msg = f"获取订单失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, []
                
        except Exception as e:
            error_msg = f"获取订单异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, []
    
    def get_order(self, order_id: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        获取Shopify订单详情
        
        Args:
            order_id: 订单ID
            
        Returns:
            (是否成功, 错误信息, 订单详情)
        """
        try:
            response = self._make_request("GET", f"/orders/{order_id}.json")
            
            if response.status_code == 200:
                order = response.json().get("order", {})
                return True, None, order
            else:
                error_msg = f"获取订单详情失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"获取订单详情异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    # 私有辅助方法
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        发送API请求，包含重试逻辑
        
        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 请求参数
            
        Returns:
            HTTP响应
        """
        url = f"{self.base_url}{endpoint}"
        
        # 设置默认超时
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.request_timeout
        
        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                self.stats["requests_made"] += 1
                self.stats["last_request_time"] = datetime.now().isoformat()
                
                # 检查速率限制
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", self.retry_delay))
                    logger.warning(f"API速率限制，等待{retry_after}秒后重试")
                    time.sleep(retry_after)
                    continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"请求失败，{self.retry_delay}秒后重试: {str(e)}")
                    time.sleep(self.retry_delay)
                else:
                    raise
        
        # 所有重试都失败
        raise requests.exceptions.RequestException(f"所有{self.max_retries}次重试均失败")
    
    def _convert_to_shopify_product(self, product: EcommerceProduct) -> Dict[str, Any]:
        """将统一产品模型转换为Shopify API格式"""
        # 状态映射
        status_map = {
            ProductStatus.ACTIVE: "active",
            ProductStatus.DRAFT: "draft",
            ProductStatus.ARCHIVED: "archived"
        }
        
        shopify_product = {
            "title": product.title,
            "body_html": product.description,
            "vendor": product.vendor or self.get_default_vendor(),
            "product_type": product.product_type or self.get_default_product_type(),
            "tags": ", ".join(product.tags) if product.tags else "",
            "status": status_map.get(product.status, "draft")
        }
        
        # 添加图片
        if product.images:
            shopify_product["images"] = []
            for image in product.images:
                image_data = {
                    "src": image.url if image.url else f"file://{image.local_path}",
                    "position": image.position
                }
                if image.alt_text:
                    image_data["alt"] = image.alt_text
                shopify_product["images"].append(image_data)
        
        # 添加变体
        if product.variants:
            shopify_product["variants"] = []
            for variant in product.variants:
                variant_data = {
                    "price": str(variant.price),
                    "sku": variant.sku or self.generate_sku(product.title, 
                                                          {"option1": variant.option1, 
                                                           "option2": variant.option2}),
                    "inventory_quantity": variant.inventory_quantity,
                    "inventory_policy": variant.inventory_policy.value,
                    "option1": variant.option1 or "",
                    "option2": variant.option2 or "",
                    "option3": variant.option3 or ""
                }
                
                if variant.compare_at_price:
                    variant_data["compare_at_price"] = str(variant.compare_at_price)
                
                if variant.weight:
                    variant_data["weight"] = variant.weight
                    variant_data["weight_unit"] = variant.weight_unit
                
                if variant.barcode:
                    variant_data["barcode"] = variant.barcode
                
                shopify_product["variants"].append(variant_data)
        
        # SEO字段
        if product.seo_title:
            shopify_product["metafields_global_title_tag"] = product.seo_title
        
        if product.seo_description:
            shopify_product["metafields_global_description_tag"] = product.seo_description
        
        return shopify_product
    
    def _convert_from_shopify_product(self, shopify_product: Dict[str, Any]) -> EcommerceProduct:
        """将Shopify API响应转换为统一产品模型"""
        # 状态映射
        status_map = {
            "active": ProductStatus.ACTIVE,
            "draft": ProductStatus.DRAFT,
            "archived": ProductStatus.ARCHIVED
        }
        
        # 解析日期
        created_at = None
        updated_at = None
        published_at = None
        
        if shopify_product.get("created_at"):
            created_at = datetime.fromisoformat(shopify_product["created_at"].replace('Z', '+00:00'))
        
        if shopify_product.get("updated_at"):
            updated_at = datetime.fromisoformat(shopify_product["updated_at"].replace('Z', '+00:00'))
        
        if shopify_product.get("published_at"):
            published_at = datetime.fromisoformat(shopify_product["published_at"].replace('Z', '+00:00'))
        
        # 创建产品实例
        product = EcommerceProduct(
            product_id=str(shopify_product.get("id", "")),
            title=shopify_product.get("title", ""),
            description=shopify_product.get("body_html", ""),
            handle=shopify_product.get("handle"),
            product_type=shopify_product.get("product_type"),
            vendor=shopify_product.get("vendor"),
            tags=shopify_product.get("tags", "").split(", ") if shopify_product.get("tags") else [],
            status=status_map.get(shopify_product.get("status", "draft"), ProductStatus.DRAFT),
            seo_title=shopify_product.get("metafields_global_title_tag"),
            seo_description=shopify_product.get("metafields_global_description_tag"),
            created_at=created_at,
            updated_at=updated_at,
            published_at=published_at,
            platform_specific=shopify_product
        )
        
        # 添加图片
        for shopify_image in shopify_product.get("images", []):
            image = ProductImage(
                image_id=str(shopify_image.get("id", "")),
                url=shopify_image.get("src", ""),
                alt_text=shopify_image.get("alt"),
                position=shopify_image.get("position", 0),
                width=shopify_image.get("width"),
                height=shopify_image.get("height"),
                file_size=shopify_image.get("file_size")
            )
            product.add_image(image)
        
        # 添加变体
        for shopify_variant in shopify_product.get("variants", []):
            variant = ProductVariant(
                variant_id=str(shopify_variant.get("id", "")),
                sku=shopify_variant.get("sku"),
                price=float(shopify_variant.get("price", 0)),
                compare_at_price=shopify_variant.get("compare_at_price"),
                cost=shopify_variant.get("cost"),
                inventory_quantity=int(shopify_variant.get("inventory_quantity", 0)),
                inventory_policy=InventoryPolicy(shopify_variant.get("inventory_policy", "deny")),
                weight=shopify_variant.get("weight"),
                weight_unit=shopify_variant.get("weight_unit", "kg"),
                option1=shopify_variant.get("option1"),
                option2=shopify_variant.get("option2"),
                option3=shopify_variant.get("option3"),
                barcode=shopify_variant.get("barcode")
            )
            product.add_variant(variant)
        
        return product
    
    def _add_to_default_collections(self, product_id: str) -> None:
        """添加产品到默认集合"""
        default_collections = self.get_default_collections()
        
        for collection_name in default_collections:
            try:
                # 首先查找集合是否存在
                response = self._make_request("GET", f"/custom_collections.json?title={collection_name}")
                
                if response.status_code == 200:
                    collections = response.json().get("custom_collections", [])
                    
                    if collections:
                        # 集合已存在，添加产品
                        collection_id = str(collections[0].get("id"))
                        self.add_product_to_collection(product_id, collection_id)
                    else:
                        # 创建新集合
                        success, error, new_collection_id = self.create_collection(collection_name)
                        if success and new_collection_id:
                            self.add_product_to_collection(product_id, new_collection_id)
                
            except Exception as e:
                logger.warning(f"添加到集合失败: {collection_name}, 错误: {str(e)}")
                continue