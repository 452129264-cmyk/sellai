#!/usr/bin/env python3
"""
SellAI 拼多多开放平台 API集成模块
==================================
支持拼多多多多进宝API调用

功能：
- 多多进宝商品搜索
- 订单管理
- 链接转换
- 签名生成

Author: SellAI Team
Version: 1.0.0
"""

import os
import time
import json
import hashlib
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# 拼多多API基础URL
PDD_API_BASE = "https://gw-api.pinduoduo.com/api/router"


class PddAPI:
    """拼多多开放平台API客户端"""
    
    def __init__(self, client_id: str = "", client_secret: str = "",
                 access_token: str = ""):
        """
        初始化拼多多API客户端
        
        Args:
            client_id: 拼多多开放平台应用的Client ID
            client_secret: 拼多多开放平台应用的Client Secret
            access_token: 用户访问令牌
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.api_base = PDD_API_BASE
        
    def is_configured(self) -> bool:
        """检查API是否已配置"""
        return bool(self.client_id and self.client_secret)
    
    def generate_sign(self, params: Dict[str, Any]) -> str:
        """
        生成拼多多API签名（MD5）
        
        签名规则：
        1. 将所有参数按key字母排序（不含sign）
        2. 拼接成key1value1key2value2格式
        3. 在字符串头部拼接client_secret
        4. 使用MD5加密
        5. 结果转为大写
        
        Args:
            params: API参数字典
            
        Returns:
            签名字符串
        """
        # 按key字母排序
        sorted_keys = sorted(params.keys())
        # 拼接字符串（不含sign字段）
        sign_str = "".join(f"{k}{params[k]}" for k in sorted_keys if k != "sign")
        # 头部拼接client_secret
        sign_str = self.client_secret + sign_str + self.client_secret
        # MD5加密并转大写
        signature = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
        return signature
    
    def build_params(self, type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        构建API请求参数
        
        Args:
            type: API类型码
            params: 业务参数
            
        Returns:
            完整的请求参数字典
        """
        timestamp = str(int(time.time()))
        
        base_params = {
            "client_id": self.client_id,
            "access_token": self.access_token,
            "type": type,
            "timestamp": timestamp,
            "version": "V1",
            "sign_method": "md5"
        }
        
        if params:
            base_params.update(params)
        
        # 生成签名
        sign = self.generate_sign(base_params)
        base_params["sign"] = sign
        
        return base_params
    
    def request(self, type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            type: API类型码
            params: 业务参数
            
        Returns:
            API响应结果
        """
        if not self.is_configured():
            logger.warning("拼多多API未配置，请先配置client_id和client_secret")
            return {
                "success": False,
                "error": "API_NOT_CONFIGURED",
                "message": "请配置拼多多API凭证"
            }
            
        url_params = self.build_params(type, params)
        
        try:
            response = requests.post(
                self.api_base,
                json=url_params,  # 拼多多使用JSON body
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # 拼多多API错误处理
            if result.get("error_response"):
                error = result["error_response"]
                logger.error(f"拼多多API错误: {error}")
                return {
                    "success": False,
                    "error": error.get("error_code", "UNKNOWN"),
                    "message": error.get("error_msg", "未知错误")
                }
                
            return {
                "success": True,
                "data": result
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"拼多多API请求失败: {e}")
            return {
                "success": False,
                "error": "REQUEST_FAILED",
                "message": str(e)
            }
    
    def get_access_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        通过授权码获取访问令牌
        
        Args:
            code: OAuth授权码
            redirect_uri: 回调地址
            
        Returns:
            访问令牌信息
        """
        token_url = "https://open-api.pinduoduo.com/oauth/token"
        
        params = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri
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
    
    # ==================== 多多进宝商品API ====================
    
    def pdd_ddk_goods_search(self, keyword: str = "", 
                            cat_id: int = 0,
                            page: int = 1,
                            page_size: int = 20,
                            sort_type: int = 0,
                            with_coupon: bool = False,
                            pid: str = "",
                            custom_params: str = "") -> Dict[str, Any]:
        """
        多多进宝商品搜索
        
        Args:
            keyword: 搜索关键词
            cat_id: 商品类目ID
            page: 页码（默认1）
            page_size: 每页数量（最大100）
            sort_type: 排序类型：
                - 0：综合排序
                - 1：按佣金比例升序
                - 2：按佣金比例降序
                - 3：按销量升序
                - 4：按销量降序
                - 5：按价格升序
                - 6：按价格降序
            with_coupon: 是否只返回有优惠券的商品
            pid: 推广位ID
            custom_params: 自定义参数
            
        Returns:
            搜索结果
        """
        params = {
            "keyword": keyword,
            "cat_id": cat_id,
            "page": page,
            "page_size": min(page_size, 100),
            "sort_type": sort_type,
            "with_coupon": "true" if with_coupon else "false",
            "p_id": pid,
            "custom_parameters": custom_params
        }
        
        result = self.request("pdd.ddk.goods.search", params)
        
        if result["success"] and "goods_search_response" in result["data"]:
            response_data = result["data"]["goods_search_response"]
            return {
                "success": True,
                "total_count": response_data.get("total_count", 0),
                "page_size": page_size,
                "page": page,
                "goods_list": response_data.get("goods_list", [])
            }
            
        return result
    
    def pdd_ddk_goods_detail(self, goods_id_list: List[str],
                            pid: str = "",
                            plan_type: int = 0) -> Dict[str, Any]:
        """
        多多进宝商品详情
        
        Args:
            goods_id_list: 商品ID列表
            pid: 推广位ID
            plan_type: 推广类型（0:通用推广）
            
        Returns:
            商品详情
        """
        params = {
            "goods_id_list": json.dumps(goods_id_list),
            "p_id": pid,
            "plan_type": plan_type
        }
        
        result = self.request("pdd.ddk.goods.detail", params)
        
        if result["success"] and "goods_details_response" in result["data"]:
            return {
                "success": True,
                "goods_details": result["data"]["goods_details_response"].get("goods_details", [])
            }
            
        return result
    
    def pdd_ddk_goods_coupon_url_generate(self, goods_id_list: List[str],
                                         pid: str = "",
                                         generate_weapp_webview: bool = True,
                                         generate_short_link: bool = True) -> Dict[str, Any]:
        """
        生成带优惠券的推广链接
        
        Args:
            goods_id_list: 商品ID列表
            pid: 推广位ID
            generate_weapp_webview: 是否生成小程序webview链接
            generate_short_link: 是否生成短链接
            
        Returns:
            推广链接
        """
        params = {
            "goods_id_list": json.dumps(goods_id_list),
            "p_id": pid,
            "generate_weapp_webview_url": "true" if generate_weapp_webview else "false",
            "generate_short_url": "true" if generate_short_link else "false"
        }
        
        result = self.request("pdd.ddk.goods.coupon.url.generate", params)
        
        if result["success"] and "goods_coupon_url_response" in result["data"]:
            return {
                "success": True,
                "url_list": result["data"]["goods_coupon_url_response"].get("url_list", [])
            }
            
        return result
    
    def pdd_ddk_goods_promotion_url_generate(self, goods_id_list: List[str],
                                            p_id: str = "",
                                            generate_short_link: bool = True,
                                            generate_weapp: bool = True) -> Dict[str, Any]:
        """
        生成推广链接（无优惠券）
        
        Args:
            goods_id_list: 商品ID列表
            p_id: 推广位ID
            generate_short_link: 是否生成短链接
            generate_weapp: 是否生成小程序链接
            
        Returns:
            推广链接
        """
        params = {
            "goods_id_list": json.dumps(goods_id_list),
            "p_id": p_id,
            "generate_short_url": "true" if generate_short_link else "false",
            "generate_we_app": "true" if generate_weapp else "false"
        }
        
        result = self.request("pdd.ddk.goods.promotion.url.generate", params)
        
        if result["success"] and "goods_promotion_url_generate_response" in result["data"]:
            return {
                "success": True,
                "url_list": result["data"]["goods_promotion_url_generate_response"].get("url_list", [])
            }
            
        return result
    
    # ==================== 订单API ====================
    
    def pdd_order_list_get(self, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          page_size: int = 50,
                          page: int = 1,
                          order_status: int = 0,
                          refunde_status: int = 0) -> Dict[str, Any]:
        """
        订单列表查询
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            page_size: 每页数量
            page: 页码
            order_status: 订单状态（0:全部, 1:待支付, 2:已支付, 3:已成团, 4:确认收货, 5:审核成功, 6:审核失败）
            refunde_status: 退款状态
            
        Returns:
            订单列表
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(days=7)
        if end_time is None:
            end_time = datetime.now()
            
        params = {
            "start_update_time": int(start_time.timestamp()),
            "end_update_time": int(end_time.timestamp()),
            "page_size": min(page_size, 100),
            "page": page,
            "order_status": order_status,
            "refund_status": refunde_status
        }
        
        result = self.request("pdd.ddk.order.list.get", params)
        
        if result["success"] and "order_list_get_response" in result["data"]:
            response_data = result["data"]["order_list_get_response"]
            return {
                "success": True,
                "total_count": response_data.get("total_count", 0),
                "order_list": response_data.get("order_list", [])
            }
            
        return result
    
    def pdd_order_detail(self, order_sn: str) -> Dict[str, Any]:
        """
        订单详情查询
        
        Args:
            order_sn: 订单编号
            
        Returns:
            订单详情
        """
        params = {
            "order_sn": order_sn
        }
        
        result = self.request("pdd.ddk.order.detail", params)
        
        if result["success"] and "order_detail_response" in result["data"]:
            return {
                "success": True,
                "order_detail": result["data"]["order_detail_response"].get("order_detail")
            }
            
        return result
    
    # ==================== 推广位API ====================
    
    def pdd_ddk_member_authority_query(self) -> Dict[str, Any]:
        """
        查询是否授权多多客知识广场
        
        Returns:
            授权状态
        """
        result = self.request("pdd.ddk.member.authority.query", {})
        
        if result["success"] and "authority_query_response" in result["data"]:
            return {
                "success": True,
                "authorized": result["data"]["authority_query_response"].get("authorized", False)
            }
            
        return result
    
    def pdd_ddk_rp_prom_url_generate(self, 
                                    amount: int = 0,
                                    pid: str = "",
                                    generate_short_link: bool = True) -> Dict[str, Any]:
        """
        生成红包推广链接
        
        Args:
            amount: 红包金额（单位：分）
            pid: 推广位ID
            generate_short_link: 是否生成短链接
            
        Returns:
            红包推广链接
        """
        params = {
            "amount": amount,
            "p_id": pid,
            "generate_short_url": "true" if generate_short_link else "false"
        }
        
        result = self.request("pdd.ddk.rp.prom.url.generate", params)
        
        if result["success"] and "rp_prom_url_generate_response" in result["data"]:
            return {
                "success": True,
                "url_list": result["data"]["rp_prom_url_generate_response"].get("url_list", [])
            }
            
        return result
    
    # ==================== 转链API ====================
    
    def pdd_ddk_goods_zs_unit_url_generate(self, source_url: str,
                                           pid: str = "") -> Dict[str, Any]:
        """
        招商推广链接转链
        
        Args:
            source_url: 招商推广链接
            pid: 推广位ID
            
        Returns:
            转链后的推广链接
        """
        params = {
            "source_url": source_url,
            "pid": pid
        }
        
        result = self.request("pdd.ddk.goods.zs.unit.url.generate", params)
        
        if result["success"] and "zs_unit_generate_response" in result["data"]:
            return {
                "success": True,
                "url_list": result["data"]["zs_unit_generate_response"].get("url_list", [])
            }
            
        return result


# 工厂函数
def create_pdd_api(config: Optional[Dict[str, str]] = None) -> PddAPI:
    """
    创建拼多多API客户端实例
    
    Args:
        config: 配置字典，包含client_id, client_secret, access_token等
        
    Returns:
        PddAPI实例
    """
    if config is None:
        # 从环境变量或配置文件加载
        config = {
            "client_id": os.getenv("PDD_CLIENT_ID", ""),
            "client_secret": os.getenv("PDD_CLIENT_SECRET", ""),
            "access_token": os.getenv("PDD_ACCESS_TOKEN", "")
        }
    
    return PddAPI(
        client_id=config.get("client_id", ""),
        client_secret=config.get("client_secret", ""),
        access_token=config.get("access_token", "")
    )


if __name__ == "__main__":
    # 测试代码
    api = PddAPI()
    
    # 测试配置检查
    print(f"API已配置: {api.is_configured()}")
    
    # 测试签名生成
    if api.client_secret:
        test_params = {"client_id": "test", "type": "pdd.ddk.goods.search"}
        sign = api.generate_sign(test_params)
        print(f"签名测试: {sign}")
