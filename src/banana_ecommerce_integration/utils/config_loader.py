#!/usr/bin/env python3
"""
配置加载工具
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                config = yaml.safe_load(f)
            elif config_path.endswith('.json'):
                config = json.load(f)
            else:
                # 尝试作为YAML加载，然后JSON
                try:
                    config = yaml.safe_load(f)
                except:
                    f.seek(0)
                    config = json.load(f)
        
        if not isinstance(config, dict):
            raise ValueError(f"配置文件格式错误，应为字典格式: {config_path}")
        
        logger.info(f"配置文件加载成功: {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"配置文件加载失败: {config_path}, 错误: {str(e)}")
        raise


def validate_shopify_config(config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    验证Shopify配置
    
    Args:
        config: 配置字典
        
    Returns:
        (是否有效, 错误信息)
    """
    # 检查必需字段
    required_fields = ["shop_domain", "access_token"]
    
    for field in required_fields:
        if field not in config or not config[field]:
            return False, f"缺少必需字段: {field}"
    
    # 检查域名格式
    shop_domain = config["shop_domain"]
    if not shop_domain.endswith(".myshopify.com"):
        return False, "Shopify域名格式错误，应以 '.myshopify.com' 结尾"
    
    # 检查API版本
    api_version = config.get("api_version", "2024-01")
    if not re.match(r'^\d{4}-\d{2}$', api_version):
        return False, "API版本格式错误，应为 'YYYY-MM' 格式"
    
    return True, None


def create_default_config() -> Dict[str, Any]:
    """
    创建默认配置
    
    Returns:
        默认配置字典
    """
    return {
        "shop_domain": "",
        "api_version": "2024-01",
        "access_token": "",
        "image_upload": {
            "max_file_size_mb": 20,
            "allowed_formats": ["jpg", "jpeg", "png", "gif", "webp"],
            "resize_dimensions": {
                "thumbnail": {"width": 100, "height": 100},
                "medium": {"width": 400, "height": 400},
                "large": {"width": 800, "height": 800}
            }
        },
        "product_sync": {
            "default_product_type": "服装",
            "default_vendor": "Banana生图AI",
            "inventory_management": True,
            "default_inventory_quantity": 100,
            "default_price": "99.99",
            "tax_exempt": False
        },
        "automation": {
            "auto_publish": True,
            "auto_add_to_collections": True,
            "collection_names": ["AI生成设计", "牛仔外套", "美式复古"],
            "auto_generate_variants": True,
            "default_variants": [
                {"name": "颜色", "options": ["经典蓝", "黑色", "水洗白"]},
                {"name": "尺寸", "options": ["S", "M", "L", "XL"]}
            ]
        },
        "banana_integration": {
            "enabled": True,
            "generation_params": {
                "resolution": "2048x2048",
                "style": "fashion_photography",
                "model_id": "banana_standard",
                "background": "studio_white"
            },
            "processing_params": {
                "quality_check": True,
                "face_consistency_threshold": 0.03,
                "texture_error_threshold": 0.05,
                "resolution_minimum": "2048x2048"
            }
        },
        "data_retention": {
            "enabled": True,
            "local_storage_path": "data/banana_ecommerce/products",
            "backup_to_memory": True,
            "memory_sync_batch_size": 50
        },
        "performance": {
            "request_timeout_seconds": 30,
            "max_retries": 3,
            "retry_delay_seconds": 2,
            "concurrent_uploads": 5
        },
        "dianfu_config": {
            "enabled": False,
            "api_endpoint": "https://api.dianfu.com/v1",
            "api_key": "",
            "api_secret": "",
            "store_id": "",
            "platform_specific": {
                "category_id": "服装",
                "shipping_template": "标准配送"
            }
        }
    }


def save_config(config: Dict[str, Any], config_path: str) -> bool:
    """
    保存配置到文件
    
    Args:
        config: 配置字典
        config_path: 配置文件路径
        
    Returns:
        是否成功
    """
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            elif config_path.endswith('.json'):
                json.dump(config, f, ensure_ascii=False, indent=2)
            else:
                # 默认使用YAML格式
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"配置文件保存成功: {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"配置文件保存失败: {config_path}, 错误: {str(e)}")
        return False


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个配置字典
    
    Args:
        base_config: 基础配置
        override_config: 覆盖配置
        
    Returns:
        合并后的配置
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result