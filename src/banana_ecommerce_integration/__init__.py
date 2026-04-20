#!/usr/bin/env python3
"""
Banana生图内核与电商平台集成模块
"""

from .base import EcommercePlatform
from .adapters.shopify_adapter import ShopifyAdapter
from .adapters.dianfu_adapter import DianfuAdapter
from .models.product import (
    EcommerceProduct, ProductStatus, ProductImage, ProductVariant,
    InventoryPolicy
)
from .integration_manager import EcommerceIntegrationManager

__version__ = "1.0.0"
__all__ = [
    "EcommercePlatform",
    "ShopifyAdapter",
    "DianfuAdapter",
    "EcommerceProduct",
    "ProductStatus",
    "ProductImage",
    "ProductVariant",
    "InventoryPolicy",
    "EcommerceIntegrationManager"
]