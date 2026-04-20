#!/usr/bin/env python3
"""
SellAI 统一电商API网关
=======================
整合淘宝、拼多多、抖音三大电商平台的统一接口

功能：
- 统一接口封装
- 配置管理
- 自动平台选择
- 统一错误处理

Author: SellAI Team
Version: 1.0.0
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from .ecommerce_taobao import TaobaoAPI, create_taobao_api
from .ecommerce_pdd import PddAPI, create_pdd_api
from .ecommerce_douyin import DouyinAPI, create_douyin_api

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = "ecommerce_config.json"


class EcommerceGateway:
    """统一电商API网关"""
    
    def __init__(self, config_path: str = CONFIG_FILE):
        """
        初始化电商网关
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # 初始化各平台API客户端
        self.taobao = self._init_taobao()
        self.pdd = self._init_pdd()
        self.douyin = self._init_douyin()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_file = Path(self.config_path)
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
        
        # 返回默认配置
        return {
            "taobao": {
                "app_key": "",
                "app_secret": "",
                "access_token": "",
                "redirect_uri": "",
                "status": "pending"
            },
            "pdd": {
                "client_id": "",
                "client_secret": "",
                "access_token": "",
                "status": "pending"
            },
            "douyin": {
                "app_id": "",
                "app_secret": "",
                "access_token": "",
                "sandbox_mode": False,
                "status": "pending"
            }
        }
    
    def _save_config(self) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def _init_taobao(self) -> TaobaoAPI:
        """初始化淘宝API"""
        taobao_config = self.config.get("taobao", {})
        return create_taobao_api({
            "app_key": taobao_config.get("app_key", ""),
            "app_secret": taobao_config.get("app_secret", ""),
            "access_token": taobao_config.get("access_token", ""),
            "redirect_uri": taobao_config.get("redirect_uri", "")
        })
    
    def _init_pdd(self) -> PddAPI:
        """初始化拼多多API"""
        pdd_config = self.config.get("pdd", {})
        return create_pdd_api({
            "client_id": pdd_config.get("client_id", ""),
            "client_secret": pdd_config.get("client_secret", ""),
            "access_token": pdd_config.get("access_token", "")
        })
    
    def _init_douyin(self) -> DouyinAPI:
        """初始化抖音API"""
        douyin_config = self.config.get("douyin", {})
        return create_douyin_api({
            "app_id": douyin_config.get("app_id", ""),
            "app_secret": douyin_config.get("app_secret", ""),
            "access_token": douyin_config.get("access_token", ""),
            "sandbox_mode": douyin_config.get("sandbox_mode", False)
        })
    
    def update_config(self, platform: str, config: Dict[str, Any]) -> bool:
        """
        更新平台配置
        
        Args:
            platform: 平台名称（taobao/pdd/douyin）
            config: 配置信息
            
        Returns:
            是否成功
        """
        if platform in self.config:
            self.config[platform].update(config)
            return self._save_config()
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取所有平台状态"""
        return {
            "taobao": {
                "configured": self.taobao.is_configured(),
                "status": self.config.get("taobao", {}).get("status", "pending")
            },
            "pdd": {
                "configured": self.pdd.is_configured(),
                "status": self.config.get("pdd", {}).get("status", "pending")
            },
            "douyin": {
                "configured": self.douyin.is_configured(),
                "status": self.config.get("douyin", {}).get("status", "pending")
            }
        }
    
    # ==================== 统一商品API ====================
    
    def search_products(self, platform: str, keyword: str, 
                       page: int = 1, page_size: int = 20,
                       **kwargs) -> Dict[str, Any]:
        """
        统一商品搜索
        
        Args:
            platform: 平台（taobao/pdd/douyin/all）
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            **kwargs: 平台特定参数
            
        Returns:
            搜索结果
        """
        if platform == "taobao":
            return self.taobao.search_items(
                keyword=keyword,
                page=page,
                page_size=page_size,
                **kwargs
            )
        elif platform == "pdd":
            return self.pdd.pdd_ddk_goods_search(
                keyword=keyword,
                page=page,
                page_size=page_size,
                **kwargs
            )
        elif platform == "douyin":
            return self.douyin.product_list(
                page=page,
                size=page_size,
                **kwargs
            )
        elif platform == "all":
            # 多平台并行搜索
            results = {}
            
            if self.taobao.is_configured():
                results["taobao"] = self.taobao.search_items(
                    keyword=keyword, page=page, page_size=page_size, **kwargs
                )
            
            if self.pdd.is_configured():
                results["pdd"] = self.pdd.pdd_ddk_goods_search(
                    keyword=keyword, page=page, page_size=page_size, **kwargs
                )
            
            if self.douyin.is_configured():
                results["douyin"] = self.douyin.product_list(
                    page=page, size=page_size, **kwargs
                )
            
            return {
                "success": True,
                "results": results
            }
        
        return {
            "success": False,
            "error": "INVALID_PLATFORM",
            "message": f"不支持的平台: {platform}"
        }
    
    def get_product_detail(self, platform: str, item_id: str) -> Dict[str, Any]:
        """
        获取商品详情
        
        Args:
            platform: 平台（taobao/pdd/douyin）
            item_id: 商品ID
            
        Returns:
            商品详情
        """
        if platform == "taobao":
            return self.taobao.get_item_detail(item_id)
        elif platform == "pdd":
            return self.pdd.pdd_ddk_goods_detail([item_id])
        elif platform == "douyin":
            return self.douyin.product_detail(item_id)
        
        return {
            "success": False,
            "error": "INVALID_PLATFORM",
            "message": f"不支持的平台: {platform}"
        }
    
    # ==================== 统一订单API ====================
    
    def get_orders(self, platform: str, 
                  start_time: Optional[Any] = None,
                  end_time: Optional[Any] = None,
                  status: Optional[str] = None,
                  page: int = 1,
                  page_size: int = 50) -> Dict[str, Any]:
        """
        统一订单查询
        
        Args:
            platform: 平台（taobao/pdd/douyin/all）
            start_time: 开始时间
            end_time: 结束时间
            status: 订单状态
            page: 页码
            page_size: 每页数量
            
        Returns:
            订单列表
        """
        if platform == "taobao":
            return self.taobao.get_order_list(
                status=status or "paid",
                start_time=start_time,
                end_time=end_time,
                page=page,
                page_size=page_size
            )
        elif platform == "pdd":
            # 转换状态
            pdd_status = 0
            if status == "paid":
                pdd_status = 2
            elif status == "settled":
                pdd_status = 5
                
            return self.pdd.pdd_order_list_get(
                start_time=start_time,
                end_time=end_time,
                page=page,
                page_size=page_size,
                order_status=pdd_status
            )
        elif platform == "douyin":
            # 转换状态
            douyin_status = None
            if status == "paid":
                douyin_status = 2
            elif status == "shipped":
                douyin_status = 3
            elif status == "completed":
                douyin_status = 5
                
            return self.douyin.order_list(
                start_time=start_time,
                end_time=end_time,
                page=page,
                size=page_size,
                order_status=douyin_status
            )
        elif platform == "all":
            # 多平台并行查询
            results = {}
            
            if self.taobao.is_configured():
                results["taobao"] = self.taobao.get_order_list(
                    status=status or "paid",
                    start_time=start_time,
                    end_time=end_time,
                    page=page,
                    page_size=page_size
                )
            
            if self.pdd.is_configured():
                results["pdd"] = self.pdd.pdd_order_list_get(
                    start_time=start_time,
                    end_time=end_time,
                    page=page,
                    page_size=page_size
                )
            
            if self.douyin.is_configured():
                results["douyin"] = self.douyin.order_list(
                    start_time=start_time,
                    end_time=end_time,
                    page=page,
                    size=page_size
                )
            
            return {
                "success": True,
                "results": results
            }
        
        return {
            "success": False,
            "error": "INVALID_PLATFORM",
            "message": f"不支持的平台: {platform}"
        }
    
    def get_order_detail(self, platform: str, order_id: str) -> Dict[str, Any]:
        """
        获取订单详情
        
        Args:
            platform: 平台（taobao/pdd/douyin）
            order_id: 订单ID
            
        Returns:
            订单详情
        """
        if platform == "taobao":
            return self.taobao.get_order_details(order_id)
        elif platform == "pdd":
            return self.pdd.pdd_order_detail(order_id)
        elif platform == "douyin":
            return self.douyin.order_detail(order_id)
        
        return {
            "success": False,
            "error": "INVALID_PLATFORM",
            "message": f"不支持的平台: {platform}"
        }
    
    # ==================== 统一链接API ====================
    
    def generate_promotion_url(self, platform: str, 
                               item_id: str,
                               with_coupon: bool = True) -> Dict[str, Any]:
        """
        生成推广链接
        
        Args:
            platform: 平台（taobao/pdd/douyin）
            item_id: 商品ID
            with_coupon: 是否带优惠券
            
        Returns:
            推广链接
        """
        if platform == "taobao":
            return self.taobao.get_dtk_links([item_id])
        elif platform == "pdd":
            if with_coupon:
                return self.pdd.pdd_ddk_goods_coupon_url_generate([item_id])
            else:
                return self.pdd.pdd_ddk_goods_promotion_url_generate([item_id])
        elif platform == "douyin":
            # 抖音商品详情接口
            return self.douyin.product_detail(item_id)
        
        return {
            "success": False,
            "error": "INVALID_PLATFORM",
            "message": f"不支持的平台: {platform}"
        }
    
    # ==================== OAuth接口 ====================
    
    def get_oauth_url(self, platform: str, state: str = "") -> Dict[str, Any]:
        """
        获取OAuth授权URL
        
        Args:
            platform: 平台（taobao/pdd/douyin）
            state: 状态参数
            
        Returns:
            授权URL
        """
        if platform == "taobao":
            return {
                "success": True,
                "url": self.taobao.get_oauth_url(state)
            }
        elif platform == "douyin":
            return {
                "success": True,
                "url": f"https://open.douyin.com/platform/oauth/connect?client_key={self.douyin.app_id}&response_type=code&redirect_uri={self.douyin.redirect_uri or ''}&scope=user_info&state={state}"
            }
        
        return {
            "success": False,
            "error": "OAUTH_NOT_SUPPORTED",
            "message": f"平台 {platform} 不支持OAuth授权"
        }
    
    def handle_oauth_callback(self, platform: str, code: str) -> Dict[str, Any]:
        """
        处理OAuth回调
        
        Args:
            platform: 平台（taobao/pdd/douyin）
            code: 授权码
            
        Returns:
            处理结果
        """
        if platform == "taobao":
            result = self.taobao.get_access_token(code)
            if result["success"]:
                self.update_config("taobao", {
                    "access_token": result["access_token"],
                    "status": "active"
                })
            return result
        elif platform == "pdd":
            result = self.pdd.get_access_token(code, self.config.get("pdd", {}).get("redirect_uri", ""))
            if result["success"]:
                self.update_config("pdd", {
                    "access_token": result["access_token"],
                    "status": "active"
                })
            return result
        elif platform == "douyin":
            result = self.douyin.get_access_token(code)
            if result["success"]:
                self.update_config("douyin", {
                    "access_token": result["access_token"],
                    "status": "active"
                })
            return result
        
        return {
            "success": False,
            "error": "INVALID_PLATFORM",
            "message": f"不支持的平台: {platform}"
        }


# 全局单例
_gateway_instance = None

def get_ecommerce_gateway(config_path: str = CONFIG_FILE) -> EcommerceGateway:
    """
    获取电商网关单例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        EcommerceGateway实例
    """
    global _gateway_instance
    
    if _gateway_instance is None:
        _gateway_instance = EcommerceGateway(config_path)
    
    return _gateway_instance


def reset_gateway():
    """重置网关单例（用于测试或重新加载配置）"""
    global _gateway_instance
    _gateway_instance = None


if __name__ == "__main__":
    # 测试代码
    gateway = EcommerceGateway()
    
    # 获取状态
    status = gateway.get_status()
    print(f"电商网关状态: {json.dumps(status, ensure_ascii=False, indent=2)}")
