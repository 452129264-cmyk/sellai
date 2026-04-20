#!/usr/bin/env python3
"""
SellAI 抖音电商开放平台 API集成模块
====================================
支持抖音电商开放平台API调用

功能：
- 商品列表查询
- 订单管理
- 账号管理
- 签名生成

Author: SellAI Team
Version: 1.0.0
"""

import os
import time
import json
import hashlib
import hmac
import base64
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# 抖音API基础URL
DOUYIN_API_BASE = "https://open.douyin.com"
DOUYIN_SANDBOX_API_BASE = "https://open-sandbox.douyin.com"


class DouyinAPI:
    """抖音电商开放平台API客户端"""
    
    def __init__(self, app_id: str = "", app_secret: str = "",
                 access_token: str = "", sandbox_mode: bool = False):
        """
        初始化抖音API客户端
        
        Args:
            app_id: 抖音开放平台应用的App ID
            app_secret: 抖音开放平台应用的App Secret
            access_token: 用户访问令牌
            sandbox_mode: 是否使用沙箱环境
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = access_token
        self.sandbox_mode = sandbox_mode
        self.api_base = DOUYIN_SANDBOX_API_BASE if sandbox_mode else DOUYIN_API_BASE
        
    def is_configured(self) -> bool:
        """检查API是否已配置"""
        return bool(self.app_id and self.app_secret)
    
    def generate_sign(self, params: Dict[str, Any]) -> str:
        """
        生成抖音API签名（HMAC-SHA256）
        
        签名规则：
        1. 将所有参数（不含sign）按key字母排序
        2. 拼接成key1=value1&key2=value2格式
        3. 使用app_secret作为key进行HMAC-SHA256加密
        4. 结果进行Base64编码
        
        Args:
            params: API参数字典
            
        Returns:
            签名字符串
        """
        # 排除sign字段
        filtered_params = {k: v for k, v in params.items() if k != "sign" and v}
        # 按key字母排序
        sorted_params = sorted(filtered_params.items())
        # 拼接字符串
        sign_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        # HMAC-SHA256加密
        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).digest()
        # Base64编码
        return base64.b64encode(signature).decode('utf-8')
    
    def get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """
        获取请求头
        
        Args:
            content_type: 内容类型
            
        Returns:
            请求头字典
        """
        headers = {
            "Content-Type": content_type
        }
        if self.access_token:
            headers["Access-Token"] = self.access_token
        return headers
    
    def request(self, method: str, endpoint: str, 
                params: Optional[Dict[str, Any]] = None,
                data: Optional[Dict[str, Any]] = None,
                need_sign: bool = True) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            method: 请求方法（GET/POST）
            endpoint: API端点
            params: URL参数
            data: 请求体数据
            need_sign: 是否需要签名
            
        Returns:
            API响应结果
        """
        if not self.is_configured():
            logger.warning("抖音API未配置，请先配置app_id和app_secret")
            return {
                "success": False,
                "error": "API_NOT_CONFIGURED",
                "message": "请配置抖音API凭证"
            }
        
        url = f"{self.api_base}{endpoint}"
        
        # 构建请求参数
        request_params = params or {}
        if need_sign and request_params:
            request_params["sign"] = self.generate_sign(request_params)
        
        try:
            if method.upper() == "GET":
                response = requests.get(
                    url,
                    params=request_params,
                    headers=self.get_headers(),
                    timeout=30
                )
            else:  # POST
                response = requests.post(
                    url,
                    params=request_params,
                    json=data,
                    headers=self.get_headers(),
                    timeout=30
                )
            
            response.raise_for_status()
            result = response.json()
            
            # 抖音API错误处理
            if result.get("err_no") and result["err_no"] != 0:
                logger.error(f"抖音API错误: {result.get('err_no')} - {result.get('err_msg')}")
                return {
                    "success": False,
                    "error": str(result.get("err_no")),
                    "message": result.get("err_msg", "未知错误")
                }
                
            return {
                "success": True,
                "data": result.get("data", {})
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"抖音API请求失败: {e}")
            return {
                "success": False,
                "error": "REQUEST_FAILED",
                "message": str(e)
            }
    
    def get_access_token(self, code: str, grant_type: str = "authorization_code") -> Dict[str, Any]:
        """
        获取访问令牌
        
        Args:
            code: 授权码（authorization_code）或刷新令牌（refresh_token）
            grant_type: 授权类型
            
        Returns:
            访问令牌信息
        """
        endpoint = "/oauth/access_token/"
        
        params = {
            "client_key": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": grant_type
        }
        
        if grant_type == "authorization_code":
            params["code"] = code
        else:
            params["refresh_token"] = code
        
        result = self.request("GET", endpoint, params, need_sign=False)
        
        if result["success"] and "data" in result:
            data = result["data"]
            if "access_token" in data:
                self.access_token = data["access_token"]
                return {
                    "success": True,
                    "access_token": data["access_token"],
                    "refresh_token": data.get("refresh_token"),
                    "expires_in": data.get("expires_in"),
                    "open_id": data.get("open_id")
                }
                
        return result
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        刷新访问令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            新的访问令牌信息
        """
        return self.get_access_token(refresh_token, grant_type="refresh_token")
    
    # ==================== 商品API ====================
    
    def product_list(self, page: int = 1, size: int = 20, 
                    status: Optional[int] = None,
                    product_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        获取商品列表
        
        Args:
            page: 页码（从1开始）
            size: 每页数量（最大100）
            status: 商品状态（0:全部, 1:上架, 2:下架）
            product_ids: 指定商品ID列表（最多10个）
            
        Returns:
            商品列表
        """
        endpoint = "/product/search/"
        
        params = {
            "page": page,
            "size": size
        }
        
        data = {}
        if status is not None:
            data["status"] = status
        if product_ids:
            data["product_ids"] = product_ids
            
        result = self.request("POST", endpoint, params, data)
        
        if result["success"]:
            return {
                "success": True,
                "page": page,
                "size": size,
                "products": result["data"].get("products", []),
                "total": result["data"].get("total", 0)
            }
            
        return result
    
    def product_detail(self, product_id: str) -> Dict[str, Any]:
        """
        获取商品详情
        
        Args:
            product_id: 商品ID
            
        Returns:
            商品详情
        """
        endpoint = "/product/detail/"
        
        params = {
            "product_id": product_id
        }
        
        result = self.request("GET", endpoint, params)
        
        if result["success"]:
            return {
                "success": True,
                "product": result["data"]
            }
            
        return result
    
    def product_submit(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        提交商品
        
        Args:
            product_info: 商品信息
            
        Returns:
            提交结果
        """
        endpoint = "/product/create/"
        
        result = self.request("POST", endpoint, {}, product_info)
        
        if result["success"]:
            return {
                "success": True,
                "product_id": result["data"].get("product_id")
            }
            
        return result
    
    def product_update(self, product_id: str, 
                       product_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新商品
        
        Args:
            product_id: 商品ID
            product_info: 更新的商品信息
            
        Returns:
            更新结果
        """
        endpoint = "/product/update/"
        
        params = {"product_id": product_id}
        
        result = self.request("POST", endpoint, params, product_info)
        
        if result["success"]:
            return {
                "success": True,
                "message": "商品更新成功"
            }
            
        return result
    
    def product_delete(self, product_id: str) -> Dict[str, Any]:
        """
        删除商品
        
        Args:
            product_id: 商品ID
            
        Returns:
            删除结果
        """
        endpoint = "/product/delete/"
        
        params = {"product_id": product_id}
        
        result = self.request("POST", endpoint, params)
        
        if result["success"]:
            return {
                "success": True,
                "message": "商品删除成功"
            }
            
        return result
    
    def product_listing(self, product_id: str) -> Dict[str, Any]:
        """
        上架商品
        
        Args:
            product_id: 商品ID
            
        Returns:
            上架结果
        """
        endpoint = "/product/listing/"
        
        params = {"product_id": product_id}
        
        result = self.request("POST", endpoint, params)
        
        if result["success"]:
            return {
                "success": True,
                "message": "商品上架成功"
            }
            
        return result
    
    def product_delisting(self, product_id: str) -> Dict[str, Any]:
        """
        下架商品
        
        Args:
            product_id: 商品ID
            
        Returns:
            下架结果
        """
        endpoint = "/product/delisting/"
        
        params = {"product_id": product_id}
        
        result = self.request("POST", endpoint, params)
        
        if result["success"]:
            return {
                "success": True,
                "message": "商品下架成功"
            }
            
        return result
    
    # ==================== 订单API ====================
    
    def order_list(self, start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None,
                  page: int = 1,
                  size: int = 20,
                  order_status: Optional[int] = None) -> Dict[str, Any]:
        """
        获取订单列表
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            page: 页码
            size: 每页数量
            order_status: 订单状态（2:待发货, 3:已发货, 5:已完成, 6:已取消）
            
        Returns:
            订单列表
        """
        endpoint = "/order/list/"
        
        if start_time is None:
            start_time = datetime.now() - timedelta(days=7)
        if end_time is None:
            end_time = datetime.now()
        
        params = {
            "start_time": int(start_time.timestamp()),
            "end_time": int(end_time.timestamp()),
            "page": page,
            "size": size
        }
        
        data = {}
        if order_status is not None:
            data["order_status"] = order_status
            
        result = self.request("POST", endpoint, params, data)
        
        if result["success"]:
            return {
                "success": True,
                "page": page,
                "size": size,
                "orders": result["data"].get("orders", []),
                "total": result["data"].get("total", 0)
            }
            
        return result
    
    def order_detail(self, order_id: str) -> Dict[str, Any]:
        """
        获取订单详情
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单详情
        """
        endpoint = "/order/detail/"
        
        params = {"order_id": order_id}
        
        result = self.request("GET", endpoint, params)
        
        if result["success"]:
            return {
                "success": True,
                "order": result["data"]
            }
            
        return result
    
    def order_deliver(self, order_id: str, 
                     express_company: str,
                     express_no: str) -> Dict[str, Any]:
        """
        订单发货
        
        Args:
            order_id: 订单ID
            express_company: 快递公司编码
            express_no: 快递单号
            
        Returns:
            发货结果
        """
        endpoint = "/order/deliver/"
        
        params = {"order_id": order_id}
        
        data = {
            "express_company": express_company,
            "express_no": express_no
        }
        
        result = self.request("POST", endpoint, params, data)
        
        if result["success"]:
            return {
                "success": True,
                "message": "订单发货成功"
            }
            
        return result
    
    def order_cancel(self, order_id: str, 
                    cancel_reason: str = "") -> Dict[str, Any]:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            cancel_reason: 取消原因
            
        Returns:
            取消结果
        """
        endpoint = "/order/cancel/"
        
        params = {"order_id": order_id}
        
        data = {"cancel_reason": cancel_reason}
        
        result = self.request("POST", endpoint, params, data)
        
        if result["success"]:
            return {
                "success": True,
                "message": "订单取消成功"
            }
            
        return result
    
    # ==================== 账号API ====================
    
    def fans_list(self, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """
        获取粉丝列表
        
        Args:
            page: 页码
            size: 每页数量
            
        Returns:
            粉丝列表
        """
        endpoint = "/fans/list/"
        
        params = {
            "page": page,
            "size": size
        }
        
        result = self.request("GET", endpoint, params)
        
        if result["success"]:
            return {
                "success": True,
                "fans": result["data"].get("fans", []),
                "total": result["data"].get("total", 0)
            }
            
        return result
    
    def merchant_info(self) -> Dict[str, Any]:
        """
        获取商家信息
        
        Returns:
            商家信息
        """
        endpoint = "/shop/detail/"
        
        result = self.request("GET", endpoint)
        
        if result["success"]:
            return {
                "success": True,
                "shop": result["data"]
            }
            
        return result


# 工厂函数
def create_douyin_api(config: Optional[Dict[str, str]] = None) -> DouyinAPI:
    """
    创建抖音API客户端实例
    
    Args:
        config: 配置字典，包含app_id, app_secret, access_token等
        
    Returns:
        DouyinAPI实例
    """
    if config is None:
        # 从环境变量或配置文件加载
        config = {
            "app_id": os.getenv("DOUYIN_APP_ID", ""),
            "app_secret": os.getenv("DOUYIN_APP_SECRET", ""),
            "access_token": os.getenv("DOUYIN_ACCESS_TOKEN", ""),
            "sandbox_mode": os.getenv("DOUYIN_SANDBOX_MODE", "false").lower() == "true"
        }
    
    return DouyinAPI(
        app_id=config.get("app_id", ""),
        app_secret=config.get("app_secret", ""),
        access_token=config.get("access_token", ""),
        sandbox_mode=config.get("sandbox_mode", False)
    )


if __name__ == "__main__":
    # 测试代码
    api = DouyinAPI()
    
    # 测试配置检查
    print(f"API已配置: {api.is_configured()}")
    
    # 测试签名生成
    if api.app_secret:
        test_params = {"client_key": "test", "grant_type": "test"}
        sign = api.generate_sign(test_params)
        print(f"签名测试: {sign}")
