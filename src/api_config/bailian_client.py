"""
百炼 API 客户端
用于图片生成、文本生成等
"""

import json
import logging
import requests
import hashlib
import hmac
import base64
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class BailianClient:
    """阿里云百炼 API客户端"""
    
    def __init__(self, config):
        """
        初始化客户端
        
        Args:
            config: BailianConfig 实例
        """
        self.api_key = config.api_key
        self.access_key_id = config.access_key_id
        self.access_key_secret = config.access_key_secret
        self.region = config.region
        
        self.image_model = config.image_model
        self.image_size = config.image_size
        self.text_model = config.text_model
        self.timeout = config.timeout
        
        # API 端点
        self.image_endpoint = f"https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        self.text_endpoint = f"https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        if not self.api_key and not (self.access_key_id and self.access_key_secret):
            raise ValueError("百炼 API 未配置，请设置 BAILIAN_API_KEY 或 BAILIAN_ACCESS_KEY_ID + BAILIAN_ACCESS_KEY_SECRET")
    
    def _get_headers(self, use_api_key: bool = True) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if use_api_key and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.access_key_id and self.access_key_secret:
            # 使用 AccessKey 签名
            headers["X-DashScope-Async"] = "enable"
            # 签名逻辑（简化版）
            headers["Authorization"] = self._sign_request()
        
        return headers
    
    def _sign_request(self) -> str:
        """生成签名（简化版，实际使用需要完整签名逻辑）"""
        # 这里是简化版，实际百炼API需要完整的签名流程
        # 参考: https://help.aliyun.com/document_detail/311536.html
        return f"ACCESSTOKEN {self.access_key_id}:{self.access_key_secret[:8]}..."
    
    # ============================================================
    # 图片生成
    # ============================================================
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        size: Optional[str] = None,
        n: int = 1,
        style: str = "<auto>"
    ) -> Dict[str, Any]:
        """
        生成图片
        
        Args:
            prompt: 图片描述
            negative_prompt: 负向提示词
            size: 图片尺寸，如 "1024x1024"
            n: 生成数量
            style: 风格
            
        Returns:
            生成结果
        """
        headers = self._get_headers()
        
        payload = {
            "model": self.image_model,
            "input": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
            },
            "parameters": {
                "size": size or self.image_size,
                "n": n,
                "style": style
            }
        }
        
        try:
            response = requests.post(
                self.image_endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"百炼图片生成失败: {e}")
            raise
    
    def generate_product_image(
        self,
        product_name: str,
        product_desc: str,
        style: str = "电商产品图",
        background: str = "纯白背景"
    ) -> Dict[str, Any]:
        """
        生成电商产品图
        
        Args:
            product_name: 产品名称
            product_desc: 产品描述
            style: 风格
            background: 背景
            
        Returns:
            生成结果
        """
        prompt = f"""{style}，{product_name}，{product_desc}，
{background}，高清，专业摄影，产品展示，光线柔和，细节清晰"""
        
        return self.generate_image(
            prompt=prompt,
            negative_prompt="模糊,低质量,变形,水印",
            size="1024x1024"
        )
    
    def generate_poster(
        self,
        theme: str,
        text: str,
        style: str = "电商海报"
    ) -> Dict[str, Any]:
        """
        生成营销海报
        
        Args:
            theme: 主题
            text: 海报文字
            style: 风格
            
        Returns:
            生成结果
        """
        prompt = f"""{style}，{theme}，{text}，
创意设计，吸引眼球，商业级质量，高清"""
        
        return self.generate_image(
            prompt=prompt,
            size="1024x1792"  # 竖版海报
        )
    
    # ============================================================
    # 文本生成（可选）
    # ============================================================
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        文本对话（使用通义千问）
        
        Args:
            messages: 消息列表
            model: 模型名称
            
        Returns:
            对话结果
        """
        headers = self._get_headers()
        
        payload = {
            "model": model or self.text_model,
            "input": {
                "messages": messages
            }
        }
        
        try:
            response = requests.post(
                self.text_endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"百炼文本生成失败: {e}")
            raise
    
    # ============================================================
    # 任务状态查询
    # ============================================================
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        查询异步任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态
        """
        headers = self._get_headers()
        
        url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"查询任务状态失败: {e}")
            raise
    
    def wait_for_image(self, task_id: str, max_wait: int = 120) -> Dict[str, Any]:
        """
        等待图片生成完成
        
        Args:
            task_id: 任务ID
            max_wait: 最大等待秒数
            
        Returns:
            最终结果
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = self.get_task_status(task_id)
            
            if status.get("output", {}).get("task_status") == "SUCCEEDED":
                return status
            elif status.get("output", {}).get("task_status") == "FAILED":
                raise Exception(f"图片生成失败: {status}")
            
            time.sleep(2)
        
        raise TimeoutError(f"图片生成超时（{max_wait}秒）")


# ============================================================
# 便捷函数
# ============================================================

def get_bailian_client() -> BailianClient:
    """获取百炼客户端实例"""
    from .config import api_config
    return BailianClient(api_config.bailian)
