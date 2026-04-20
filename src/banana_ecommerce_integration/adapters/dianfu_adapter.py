#!/usr/bin/env python3
"""
店府平台适配器（中国电商平台）
针对店府平台特性的定制化实现
"""

import os
import json
import time
import requests
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging

from ..base import EcommercePlatform
from ..models.product import EcommerceProduct, ProductStatus, ProductImage, ProductVariant


logger = logging.getLogger(__name__)


class DianfuAdapter(EcommercePlatform):
    """店府平台适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 提取店府配置
        self.api_endpoint = config.get("api_endpoint", "https://api.dianfu.com/v1")
        self.api_key = config.get("api_key", "")
        self.api_secret = config.get("api_secret", "")
        self.store_id = config.get("store_id", "")
        
        # 平台特定配置
        platform_config = config.get("platform_specific", {})
        self.default_category = platform_config.get("category_id", "服装")
        self.shipping_template = platform_config.get("shipping_template", "标准配送")
        
        # 请求会话
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        })
        
        # 状态跟踪
        self.stats = {
            "requests_made": 0,
            "errors": 0
        }
    
    def initialize(self) -> bool:
        """初始化店府平台连接"""
        if not self.api_key or not self.api_secret:
            logger.error("未配置店府API密钥")
            return False
        
        if not self.store_id:
            logger.error("未配置店铺ID")
            return False
        
        # 测试连接
        success, error = self.test_connection()
        if success:
            self._initialized = True
            logger.info("店府适配器初始化成功")
        else:
            logger.error(f"店府适配器初始化失败: {error}")
        
        return success
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """测试店府API连接"""
        try:
            # 店府平台通常有店铺信息接口
            endpoint = f"{self.api_endpoint}/store/info"
            
            # 生成签名
            timestamp = str(int(time.time()))
            sign = self._generate_signature(timestamp, "")
            
            headers = {
                "X-API-Key": self.api_key,
                "X-Timestamp": timestamp,
                "X-Signature": sign
            }
            
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                store_info = response.json()
                logger.info(f"店府连接测试成功: {store_info.get('store_name', '未知店铺')}")
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
        在店府平台创建新产品
        
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
            # 构建店府API请求数据
            product_data = self._convert_to_dianfu_product(product)
            
            # 调用API
            endpoint = f"{self.api_endpoint}/products/create"
            response = self._make_request("POST", endpoint, json=product_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("code") == 0:
                    # 提取产品ID
                    dianfu_product_id = str(result.get("data", {}).get("product_id", ""))
                    
                    # 转换为统一模型
                    created_product = product
                    created_product.product_id = dianfu_product_id
                    
                    # 更新平台特定数据
                    created_product.platform_specific = {
                        "dianfu_data": result.get("data", {}),
                        "created_at": datetime.now().isoformat()
                    }
                    
                    logger.info(f"店府产品创建成功: {dianfu_product_id} - {product.title}")
                    return True, None, created_product
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg, None
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
        更新店府产品
        
        Args:
            product_id: 产品ID
            product: 更新后的产品数据
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 构建更新数据
            update_data = self._convert_to_dianfu_product(product)
            update_data["product_id"] = product_id
            
            # 调用API
            endpoint = f"{self.api_endpoint}/products/update"
            response = self._make_request("POST", endpoint, json=update_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("code") == 0:
                    logger.info(f"店府产品更新成功: {product_id}")
                    return True, None
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg
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
        获取店府产品详情
        
        Args:
            product_id: 产品ID
            
        Returns:
            (是否成功, 错误信息, 产品数据)
        """
        try:
            endpoint = f"{self.api_endpoint}/products/detail"
            params = {"product_id": product_id}
            
            response = self._make_request("GET", endpoint, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("code") == 0:
                    # 转换为统一模型
                    product_data = result.get("data", {})
                    product = self._convert_from_dianfu_product(product_data)
                    return True, None, product
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg, None
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
        列出店府产品
        
        Args:
            limit: 返回数量限制
            status: 筛选状态
            
        Returns:
            (是否成功, 错误信息, 产品列表)
        """
        try:
            endpoint = f"{self.api_endpoint}/products/list"
            params = {
                "store_id": self.store_id,
                "page": 1,
                "page_size": limit
            }
            
            if status:
                # 店府状态映射
                status_map = {
                    ProductStatus.ACTIVE: "on_sale",
                    ProductStatus.DRAFT: "draft",
                    ProductStatus.ARCHIVED: "off_shelf"
                }
                if status in status_map:
                    params["status"] = status_map[status]
            
            response = self._make_request("GET", endpoint, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("code") == 0:
                    products_data = result.get("data", {}).get("list", [])
                    products = []
                    
                    for dianfu_product in products_data:
                        product = self._convert_from_dianfu_product(dianfu_product)
                        products.append(product)
                    
                    return True, None, products
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg, []
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
        删除店府产品
        
        Args:
            product_id: 产品ID
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            endpoint = f"{self.api_endpoint}/products/delete"
            data = {"product_id": product_id}
            
            response = self._make_request("POST", endpoint, json=data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("code") == 0:
                    logger.info(f"店府产品删除成功: {product_id}")
                    return True, None
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg
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
        上传图片到店府平台
        
        Args:
            image_path: 本地图片路径
            product_id: 关联产品ID（可选）
            alt_text: ALT文本（可选）
            
        Returns:
            (是否成功, 错误信息, 图片URL)
        """
        if not os.path.exists(image_path):
            return False, f"图片文件不存在: {image_path}", None
        
        try:
            # 店府平台通常需要分两步：上传图片获取ID，然后关联到产品
            
            # 1. 上传图片
            upload_endpoint = f"{self.api_endpoint}/images/upload"
            
            with open(image_path, 'rb') as f:
                files = {'image': (os.path.basename(image_path), f, 'image/jpeg')}
                
                timestamp = str(int(time.time()))
                sign = self._generate_signature(timestamp, "")
                
                headers = {
                    "X-API-Key": self.api_key,
                    "X-Timestamp": timestamp,
                    "X-Signature": sign
                }
                
                response = requests.post(upload_endpoint, files=files, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("code") == 0:
                    image_data = result.get("data", {})
                    image_url = image_data.get("url", "")
                    image_id = str(image_data.get("image_id", ""))
                    
                    # 2. 如果提供了产品ID，关联图片到产品
                    if product_id and image_id:
                        associate_success = self._associate_image_to_product(image_id, product_id, alt_text)
                        
                        if associate_success:
                            logger.info(f"店府图片上传并关联成功: {image_url} -> {product_id}")
                            return True, None, image_url
                        else:
                            logger.warning(f"图片上传成功但关联失败: {image_id}")
                            return True, "图片上传成功但关联失败", image_url
                    else:
                        logger.info(f"店府图片上传成功: {image_url}")
                        return True, None, image_url
                else:
                    error_msg = f"店府图片上传失败: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg, None
            else:
                error_msg = f"图片上传失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"图片上传异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def create_collection(self, name: str, description: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        创建店府集合（分类）
        
        Args:
            name: 集合名称
            description: 集合描述
            
        Returns:
            (是否成功, 错误信息, 集合ID)
        """
        try:
            endpoint = f"{self.api_endpoint}/categories/create"
            
            category_data = {
                "store_id": self.store_id,
                "category_name": name,
                "description": description or ""
            }
            
            response = self._make_request("POST", endpoint, json=category_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("code") == 0:
                    category_id = str(result.get("data", {}).get("category_id", ""))
                    logger.info(f"店府分类创建成功: {category_id} - {name}")
                    return True, None, category_id
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg, None
            else:
                error_msg = f"分类创建失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"分类创建异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def add_product_to_collection(self, product_id: str, collection_id: str) -> Tuple[bool, Optional[str]]:
        """
        添加产品到店府集合
        
        Args:
            product_id: 产品ID
            collection_id: 集合ID
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            endpoint = f"{self.api_endpoint}/products/category/update"
            
            update_data = {
                "product_id": product_id,
                "category_id": collection_id
            }
            
            response = self._make_request("POST", endpoint, json=update_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("code") == 0:
                    logger.info(f"店府产品分类更新成功: {product_id} -> {collection_id}")
                    return True, None
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg
            else:
                error_msg = f"产品分类更新失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"产品分类更新异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def update_inventory(self, variant_id: str, quantity: int) -> Tuple[bool, Optional[str]]:
        """
        更新店府库存
        
        Args:
            variant_id: 变体ID
            quantity: 库存数量
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            endpoint = f"{self.api_endpoint}/inventory/update"
            
            inventory_data = {
                "sku_id": variant_id,  # 假设variant_id对应SKU ID
                "quantity": quantity
            }
            
            response = self._make_request("POST", endpoint, json=inventory_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("code") == 0:
                    logger.info(f"店府库存更新成功: {variant_id} -> {quantity}")
                    return True, None
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg
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
        获取店府订单
        
        Args:
            limit: 返回数量限制
            status: 订单状态筛选
            
        Returns:
            (是否成功, 错误信息, 订单列表)
        """
        try:
            endpoint = f"{self.api_endpoint}/orders/list"
            
            params = {
                "store_id": self.store_id,
                "page": 1,
                "page_size": limit
            }
            
            if status:
                params["order_status"] = status
            
            response = self._make_request("GET", endpoint, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("code") == 0:
                    orders = result.get("data", {}).get("list", [])
                    return True, None, orders
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg, []
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
        获取店府订单详情
        
        Args:
            order_id: 订单ID
            
        Returns:
            (是否成功, 错误信息, 订单详情)
        """
        try:
            endpoint = f"{self.api_endpoint}/orders/detail"
            
            params = {
                "store_id": self.store_id,
                "order_id": order_id
            }
            
            response = self._make_request("GET", endpoint, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("code") == 0:
                    order = result.get("data", {})
                    return True, None, order
                else:
                    error_msg = f"店府API业务错误: {result.get('msg', '未知错误')}"
                    logger.error(error_msg)
                    return False, error_msg, None
            else:
                error_msg = f"获取订单详情失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"获取订单详情异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    # 店府平台特定方法
    def _generate_signature(self, timestamp: str, body: str) -> str:
        """
        生成店府API签名
        
        Args:
            timestamp: 时间戳
            body: 请求体内容
            
        Returns:
            签名字符串
        """
        # 店府平台的典型签名算法
        sign_str = f"{self.api_key}{timestamp}{body}{self.api_secret}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        发送店府API请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 请求参数
            
        Returns:
            HTTP响应
        """
        url = endpoint if endpoint.startswith("http") else f"{self.api_endpoint}{endpoint}"
        
        # 生成签名
        timestamp = str(int(time.time()))
        body = json.dumps(kwargs.get("json", {})) if kwargs.get("json") else ""
        signature = self._generate_signature(timestamp, body)
        
        headers = kwargs.get("headers", {})
        headers.update({
            "X-API-Key": self.api_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature
        })
        
        kwargs["headers"] = headers
        kwargs["timeout"] = kwargs.get("timeout", 30)
        
        try:
            response = requests.request(method, url, **kwargs)
            self.stats["requests_made"] += 1
            return response
            
        except Exception as e:
            logger.error(f"店府API请求失败: {str(e)}")
            raise
    
    def _convert_to_dianfu_product(self, product: EcommerceProduct) -> Dict[str, Any]:
        """将统一产品模型转换为店府API格式"""
        # 状态映射
        status_map = {
            ProductStatus.ACTIVE: "on_sale",
            ProductStatus.DRAFT: "draft",
            ProductStatus.ARCHIVED: "off_shelf"
        }
        
        dianfu_product = {
            "store_id": self.store_id,
            "product_name": product.title,
            "product_desc": product.description,
            "category_id": self.default_category,
            "shipping_template": self.shipping_template,
            "status": status_map.get(product.status, "draft"),
            "tags": ",".join(product.tags) if product.tags else ""
        }
        
        # 添加变体信息
        if product.variants:
            skus = []
            for variant in product.variants:
                sku_info = {
                    "sku_code": variant.sku or self.generate_sku(product.title, 
                                                               {"option1": variant.option1}),
                    "price": variant.price,
                    "stock": variant.inventory_quantity,
                    "specs": {}
                }
                
                if variant.option1:
                    sku_info["specs"]["规格"] = variant.option1
                
                if variant.weight:
                    sku_info["weight"] = variant.weight
                
                skus.append(sku_info)
            
            dianfu_product["skus"] = skus
        
        return dianfu_product
    
    def _convert_from_dianfu_product(self, dianfu_product: Dict[str, Any]) -> EcommerceProduct:
        """将店府API响应转换为统一产品模型"""
        # 状态映射
        status_map = {
            "on_sale": ProductStatus.ACTIVE,
            "draft": ProductStatus.DRAFT,
            "off_shelf": ProductStatus.ARCHIVED
        }
        
        # 创建产品实例
        product = EcommerceProduct(
            product_id=str(dianfu_product.get("product_id", "")),
            title=dianfu_product.get("product_name", ""),
            description=dianfu_product.get("product_desc", ""),
            product_type=dianfu_product.get("category_name", ""),
            vendor=self.store_id,
            tags=dianfu_product.get("tags", "").split(",") if dianfu_product.get("tags") else [],
            status=status_map.get(dianfu_product.get("status", "draft"), ProductStatus.DRAFT),
            platform_specific=dianfu_product
        )
        
        # 添加图片
        images_data = dianfu_product.get("images", [])
        for idx, img_data in enumerate(images_data):
            image = ProductImage(
                image_id=str(img_data.get("image_id", "")),
                url=img_data.get("image_url", ""),
                alt_text=img_data.get("alt_text"),
                position=idx
            )
            product.add_image(image)
        
        # 添加变体
        skus_data = dianfu_product.get("skus", [])
        for sku_data in skus_data:
            variant = ProductVariant(
                variant_id=str(sku_data.get("sku_id", "")),
                sku=sku_data.get("sku_code"),
                price=float(sku_data.get("price", 0)),
                inventory_quantity=int(sku_data.get("stock", 0)),
                option1=sku_data.get("specs", {}).get("规格")
            )
            product.add_variant(variant)
        
        return product
    
    def _associate_image_to_product(self, image_id: str, product_id: str, alt_text: Optional[str] = None) -> bool:
        """
        关联图片到产品
        
        Args:
            image_id: 图片ID
            product_id: 产品ID
            alt_text: ALT文本
            
        Returns:
            是否成功
        """
        try:
            endpoint = f"{self.api_endpoint}/products/images/add"
            
            data = {
                "product_id": product_id,
                "image_id": image_id
            }
            
            if alt_text:
                data["alt_text"] = alt_text
            
            response = self._make_request("POST", endpoint, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("code") == 0
            else:
                return False
                
        except Exception:
            return False