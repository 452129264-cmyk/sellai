#!/usr/bin/env python3
"""
SellAI 淘宝/天猫开放平台 API集成模块
=====================================
支持淘宝/天猫开放平台API调用

功能：
- 商品详情查询
- 商品搜索
- 订单管理
- 签名生成

Author: SellAI Team
Version: 1.0.0
"""

import os
import time
import json
import hashlib
import hmac
import urllib.parse
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# 淘宝API基础URL
TAOBAO_API_BASE = "https://eco.taobao.com/router/rest"


class TaobaoAPI:
    """淘宝/天猫开放平台API客户端"""
    
    def __init__(self, app_key: str = "", app_secret: str = "", 
                 access_token: str = "", redirect_uri: str = ""):
        """
        初始化淘宝API客户端
        
        Args:
            app_key: 淘宝开放平台应用的AppKey
            app_secret: 淘宝开放平台应用的AppSecret
            access_token: 用户访问令牌（OAuth2.0获取）
            redirect_uri: OAuth回调地址
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token
        self.redirect_uri = redirect_uri
        self.api_base = TAOBAO_API_BASE
        
    def is_configured(self) -> bool:
        """检查API是否已配置"""
        return bool(self.app_key and self.app_secret)
    
    def generate_sign(self, params: Dict[str, Any]) -> str:
        """
        生成淘宝API签名（HMAC-MD5）
        
        签名规则：
        1. 将所有参数按key字母排序
        2. 拼接成key1value1key2value2格式
        3. 使用app_secret作为key进行HMAC-MD5加密
        4. 结果转为大写
        
        Args:
            params: API参数字典
            
        Returns:
            签名字符串
        """
        # 按key字母排序
        sorted_params = sorted(params.items())
        # 拼接字符串
        sign_str = "".join(f"{k}{v}" for k, v in sorted_params)
        # HMAC-MD5加密
        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.md5
        ).hexdigest().upper()
        return signature
    
    def build_params(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        构建API请求参数
        
        Args:
            method: API方法名
            params: 业务参数
            
        Returns:
            完整的请求参数字典
        """
        base_params = {
            "app_key": self.app_key,
            "method": method,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "format": "json",
            "v": "2.0",
            "sign_method": "hmac",
        }
        
        if self.access_token:
            base_params["access_token"] = self.access_token
            
        if params:
            base_params["biz_extand_params"] = json.dumps(params, ensure_ascii=False)
            base_params["biz_type"] = "item"
            
        # 生成签名
        sign = self.generate_sign(base_params)
        base_params["sign"] = sign
        
        return base_params
    
    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            method: API方法名
            params: 业务参数
            
        Returns:
            API响应结果
        """
        if not self.is_configured():
            logger.warning("淘宝API未配置，请先配置app_key和app_secret")
            return {
                "success": False,
                "error": "API_NOT_CONFIGURED",
                "message": "请配置淘宝API凭证"
            }
            
        url_params = self.build_params(method, params)
        
        try:
            response = requests.get(
                self.api_base,
                params=url_params,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # 淘宝API错误处理
            if "error_response" in result:
                error = result["error_response"]
                logger.error(f"淘宝API错误: {error}")
                return {
                    "success": False,
                    "error": error.get("code", "UNKNOWN"),
                    "message": error.get("msg", "未知错误")
                }
                
            return {
                "success": True,
                "data": result
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"淘宝API请求失败: {e}")
            return {
                "success": False,
                "error": "REQUEST_FAILED",
                "message": str(e)
            }
    
    def get_oauth_url(self, state: str = "") -> str:
        """
        获取OAuth授权URL
        
        Args:
            state: 状态参数，用于防止CSRF攻击
            
        Returns:
            授权跳转URL
        """
        params = {
            "client_id": self.app_key,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state or str(int(time.time()))
        }
        
        query = urllib.parse.urlencode(params)
        return f"https://oauth.taobao.com/authorize?{query}"
    
    def get_access_token(self, code: str) -> Dict[str, Any]:
        """
        通过授权码获取访问令牌
        
        Args:
            code: OAuth授权码
            
        Returns:
            访问令牌信息
        """
        token_url = "https://oauth.taobao.com/token"
        
        params = {
            "grant_type": "authorization_code",
            "client_id": self.app_key,
            "client_secret": self.app_secret,
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        try:
            response = requests.post(token_url, data=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                return {
                    "success": True,
                    "access_token": result["access_token"],
                    "refresh_token": result.get("refresh_token"),
                    "expires_in": result.get("expires_in")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "TOKEN_ERROR"),
                    "message": result.get("error_description", "获取令牌失败")
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"获取访问令牌失败: {e}")
            return {
                "success": False,
                "error": "TOKEN_REQUEST_FAILED",
                "message": str(e)
            }
    
    # ==================== 商品API ====================
    
    def get_item_detail(self, item_id: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        获取商品详情
        
        Args:
            item_id: 商品ID（数字ID）
            fields: 需要返回的字段列表
            
        Returns:
            商品详情信息
        """
        if fields is None:
            fields = [
                "num_iid", "title", "pict_url", "reserve_price",
                "zk_final_price", "provcity", "item_url", "shop_name",
                "nick", "seller_id", "volume", "npx"
            ]
        
        params = {
            "num_iids": item_id,
            "fields": ",".join(fields),
            "ip": ""  # 客户端IP，用于排行榜统计
        }
        
        result = self.request("taobao.tbk.item.info.get", params)
        
        if result["success"] and "tbk_item_info_get_response" in result["data"]:
            items = result["data"]["tbk_item_info_get_response"]["results"]["n_tbk_item"]
            if items:
                return {
                    "success": True,
                    "item": items[0]
                }
                
        return result
    
    def search_items(self, keyword: str, page: int = 1, page_size: int = 20,
                    sort: str = "tk_total_sales_desc", 
                    is_tmall: bool = False,
                    is_overseas: bool = False,
                    start_price: int = 0,
                    end_price: int = 0) -> Dict[str, Any]:
        """
        淘宝客商品搜索
        
        Args:
            keyword: 搜索关键词
            page: 页码（默认1）
            page_size: 每页数量（最大100）
            sort: 排序规则：
                - tk_total_sales_desc（推荐销量从高到低）
                - tk_total_sales_asc（销量从低到高）
                - tk_rate_desc（佣金率从高到低）
                - tk_total_commi_desc（累计佣金从高到低）
                - price_asc（价格从低到高）
                - price_desc（价格从高到低）
            is_tmall: 是否天猫商品
            is_overseas: 是否海外商品
            start_price: 最低价格（单位：元）
            end_price: 最高价格（单位：元）
            
        Returns:
            搜索结果
        """
        params = {
            "q": keyword,
            "page_no": page,
            "page_size": min(page_size, 100),
            "sort": sort,
            "is_tmall": "true" if is_tmall else "false",
            "is_overseas": "true" if is_overseas else "false",
        }
        
        if start_price > 0:
            params["start_price"] = start_price
        if end_price > 0:
            params["end_price"] = end_price
            
        result = self.request("taobao.tbk.material.optimals", params)
        
        if result["success"] and "tbk_material_optimals_response" in result["data"]:
            response_data = result["data"]["tbk_material_optimals_response"]
            return {
                "success": True,
                "total_results": response_data.get("total_results", 0),
                "page_size": page_size,
                "page": page,
                "items": response_data.get("result_list", {}).get("map_data", [])
            }
            
        return result
    
    def get_dtk_links(self, item_urls: List[str], platform: int = 1) -> Dict[str, Any]:
        """
        淘宝联盟链接转换（口令转链接）
        
        Args:
            item_urls: 商品链接列表
            platform: 链接类型（1:PC, 2:无线）
            
        Returns:
            转换后的淘链接
        """
        params = {
            "click_url": ",".join(item_urls),
            "platform": platform
        }
        
        result = self.request("taobao.tbk.link.convert", params)
        
        if result["success"] and "tbk_link_convert_response" in result["data"]:
            return {
                "success": True,
                "results": result["data"]["tbk_link_convert_response"].get("results", {})
            }
            
        return result
    
    def get_item_coupon(self, item_id: str) -> Dict[str, Any]:
        """
        获取商品优惠券信息
        
        Args:
            item_id: 商品ID
            
        Returns:
            优惠券信息
        """
        params = {
            "item_id": item_id
        }
        
        result = self.request("taobao.tbk.coupon.get", params)
        
        if result["success"] and "tbk_coupon_get_response" in result["data"]:
            return {
                "success": True,
                "coupon": result["data"]["tbk_coupon_get_response"].get("data")
            }
            
        return result
    
    # ==================== 订单API ====================
    
    def get_order_list(self, status: str = "paid", 
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      page: int = 1,
                      page_size: int = 50) -> Dict[str, Any]:
        """
        获取订单列表
        
        Args:
            status: 订单状态
                - paid（已付款）
                - settled（已结算）
                -跳转到订单页面看所有状态
            start_time: 开始时间
            end_time: 结束时间
            page: 页码
            page_size: 每页数量
            
        Returns:
            订单列表
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(days=7)
        if end_time is None:
            end_time = datetime.now()
            
        params = {
            "order_status": status,
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "page_no": page,
            "page_size": min(page_size, 100)
        }
        
        result = self.request("taobao.tbk.order.get", params)
        
        if result["success"] and "tbk_order_get_response" in result["data"]:
            response_data = result["data"]["tbk_order_get_response"]
            return {
                "success": True,
                "total_results": response_data.get("total_results", 0),
                "orders": response_data.get("orders", {}).get("order", [])
            }
            
        return result
    
    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        获取订单详情
        
        Args:
            order_id: 订单号
            
        Returns:
            订单详情
        """
        params = {
            "order_id": order_id
        }
        
        result = self.request("taobao.tbk.order.details.get", params)
        
        if result["success"] and "tbk_order_details_get_response" in result["data"]:
            return {
                "success": True,
                "order": result["data"]["tbk_order_details_get_response"].get("data")
            }
            
        return result
    
    # ==================== 活动API ====================
    
    def get_activity_list(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        获取官方活动列表
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            活动列表
        """
        params = {
            "page": page,
            "page_size": page_size
        }
        
        result = self.request("taobao.tbk.activity.list.get", params)
        
        if result["success"] and "tbk_activity_list_get_response" in result["data"]:
            response_data = result["data"]["tbk_activity_list_get_response"]
            return {
                "success": True,
                "activities": response_data.get("results", [])
            }
            
        return result
    
    def get_activity_info(self, activity_id: str) -> Dict[str, Any]:
        """
        获取活动详情
        
        Args:
            activity_id: 活动ID
            
        Returns:
            活动详情
        """
        params = {
            "activity_id": activity_id
        }
        
        result = self.request("taobao.tbk.activity.info.get", params)
        
        if result["success"] and "tbk_activity_info_get_response" in result["data"]:
            return {
                "success": True,
                "activity": result["data"]["tbk_activity_info_get_response"].get("data")
            }
            
        return result


# 工厂函数
def create_taobao_api(config: Optional[Dict[str, str]] = None) -> TaobaoAPI:
    """
    创建淘宝API客户端实例
    
    Args:
        config: 配置字典，包含app_key, app_secret, access_token等
        
    Returns:
        TaobaoAPI实例
    """
    if config is None:
        # 从环境变量或配置文件加载
        config = {
            "app_key": os.getenv("TAOBAO_APP_KEY", ""),
            "app_secret": os.getenv("TAOBAO_APP_SECRET", ""),
            "access_token": os.getenv("TAOBAO_ACCESS_TOKEN", ""),
            "redirect_uri": os.getenv("TAOBAO_REDIRECT_URI", "")
        }
    
    return TaobaoAPI(
        app_key=config.get("app_key", ""),
        app_secret=config.get("app_secret", ""),
        access_token=config.get("access_token", ""),
        redirect_uri=config.get("redirect_uri", "")
    )


if __name__ == "__main__":
    # 测试代码
    api = TaobaoAPI()
    
    # 测试配置检查
    print(f"API已配置: {api.is_configured()}")
    print(f"OAuth URL生成: {api.get_oauth_url() if api.is_configured() else 'N/A'}")
