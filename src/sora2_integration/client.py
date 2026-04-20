"""
Sora2视频生成API客户端
支持OpenAI官方API和第三方兼容API
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import asdict
import requests

from .config import (
    Sora2IntegrationConfig, 
    Sora2ModelType,
    Sora2OutputSpec,
    DEFAULT_CONFIG
)


class Sora2APIError(Exception):
    """Sora2 API异常基类"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class Sora2APIClient:
    """Sora2 API客户端主类"""
    
    def __init__(self, config: Optional[Sora2IntegrationConfig] = None):
        """
        初始化客户端
        
        Args:
            config: 配置对象，如为None则使用默认配置
        """
        self.config = config or DEFAULT_CONFIG
        self._setup_logging()
        
        # 当前环境网络限制判断
        if self.config.network_restricted:
            self.logger.warning("当前运行环境存在网络限制，API调用可能失败")
            self.logger.warning("模式设置为仅生成配置，不实际调用API")
        
        # 初始化会话
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "SellAI-Sora2-Integration/1.0"
        })
        
        # 设置超时
        self.timeout = self.config.retry.network_timeout_seconds
        
        # SSL验证配置
        if not self.config.retry.ssl_verify:
            self.session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(getattr(logging, self.config.log_level))
    
    def _get_api_key(self) -> Optional[str]:
        """获取API密钥"""
        return self.config.security.get_api_key
    
    def _get_base_url(self) -> str:
        """获取基础URL"""
        if self.config.use_openai_official:
            return self.config.endpoints.OPENAI_BASE_URL
        else:
            # 回退到第三方（按优先级）
            if self.config.fallback_to_third_party:
                # 尝试Mountsea AI
                return self.config.endpoints.MOUNTSEA_BASE_URL
            # 最后尝试Sora2API
            return self.config.endpoints.SORA2API_BASE_URL
    
    def _get_video_create_endpoint(self) -> str:
        """获取视频创建端点"""
        if self.config.use_openai_official:
            return self.config.endpoints.OPENAI_VIDEO_CREATE
        else:
            return self.config.endpoints.MOUNTSEA_SORA_GENERATE
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json"
        }
        
        # 添加认证头
        api_key = self._get_api_key()
        if api_key:
            headers["Authorization"] = f"{self.config.security.auth_header_prefix} {api_key}"
        
        return headers
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     files: Optional[Dict] = None) -> Dict:
        """
        发送API请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求数据
            files: 文件上传
            
        Returns:
            API响应
            
        Raises:
            Sora2APIError: API调用失败
        """
        # 检查网络限制模式
        if self.config.generate_config_only:
            self.logger.info("配置生成模式：模拟API调用，返回模拟响应")
            return self._mock_api_response(endpoint, data)
        
        url = self._get_base_url() + endpoint
        headers = self._build_headers()
        
        try:
            if method.upper() == "GET":
                response = self.session.get(
                    url, 
                    headers=headers, 
                    params=data,
                    timeout=self.timeout
                )
            elif method.upper() == "POST":
                if files:
                    # multipart/form-data
                    # 需要特殊处理headers
                    multipart_headers = {k: v for k, v in headers.items() 
                                        if k.lower() != "content-type"}
                    response = self.session.post(
                        url,
                        headers=multipart_headers,
                        data=data,
                        files=files,
                        timeout=self.timeout
                    )
                else:
                    response = self.session.post(
                        url,
                        headers=headers,
                        json=data,
                        timeout=self.timeout
                    )
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            # 检查响应状态
            if response.status_code >= 400:
                error_msg = f"API调用失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('error', {}).get('message', str(error_data))}"
                except:
                    error_msg += f" - {response.text[:200]}"
                
                raise Sora2APIError(
                    error_msg, 
                    status_code=response.status_code,
                    response=response.json() if response.headers.get('content-type') == 'application/json' else None
                )
            
            # 解析响应
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                # 非JSON响应（如文件下载）
                return {"content": response.content, "headers": dict(response.headers)}
                
        except requests.exceptions.Timeout:
            raise Sora2APIError(f"API请求超时（{self.timeout}秒）")
        except requests.exceptions.ConnectionError as e:
            raise Sora2APIError(f"网络连接错误: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Sora2APIError(f"请求异常: {str(e)}")
    
    def _mock_api_response(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        模拟API响应（用于配置生成模式）
        
        Args:
            endpoint: API端点
            data: 请求数据
            
        Returns:
            模拟响应
        """
        import uuid
        import time
        
        base_response = {
            "id": f"video_{uuid.uuid4().hex[:16]}",
            "object": "video",
            "created_at": int(time.time()),
            "model": self.config.default_model.value,
            "status": "queued",
            "progress": 0
        }
        
        # 根据端点定制响应
        if "/videos" in endpoint and "remix" not in endpoint:
            # 视频创建
            if data and "prompt" in data:
                base_response["prompt"] = data["prompt"]
            
            # 添加预配置参数
            base_response.update({
                "size": self.config.output_spec.size_str,
                "seconds": str(self.config.output_spec.duration_seconds),
                "quality": self.config.output_spec.quality,
                "aspect_ratio": self.config.output_spec.aspect_ratio,
                "orientation": self.config.output_spec.orientation
            })
            
            # 模拟任务状态（处理中）
            time.sleep(0.1)
            base_response["status"] = "in_progress"
            base_response["progress"] = 45
            
            # 模拟完成
            time.sleep(0.1)
            base_response["status"] = "completed"
            base_response["progress"] = 100
            base_response["completed_at"] = int(time.time())
            base_response["video_url"] = "https://cdn.example.com/mock_video.mp4"
            base_response["share_id"] = f"s_{uuid.uuid4().hex[:16]}"
            
        elif "/remix" in endpoint:
            # Remix视频
            base_response.update({
                "remixed_from_video_id": data.get("remix_target_id") if data else "video_unknown",
                "size": self.config.output_spec.size_str,
                "seconds": str(self.config.output_spec.duration_seconds)
            })
            
        elif "/models" in endpoint:
            # 列出模型
            return {
                "object": "list",
                "data": [
                    {"id": "sora-2", "object": "model", "description": "Standard video generation"},
                    {"id": "sora-2-pro", "object": "model", "description": "High quality video generation"},
                    {"id": "sora-2-landscape-15s", "object": "model", "description": "Landscape 15-second videos"},
                    {"id": "sora-2-portrait-15s", "object": "model", "description": "Portrait 15-second videos"},
                    {"id": "sora-2-characters", "object": "model", "description": "Character creation model"}
                ]
            }
        
        return base_response
    
    def create_video(self, prompt: str, 
                    model: Optional[Sora2ModelType] = None,
                    reference_image: Optional[str] = None,
                    reference_video: Optional[str] = None,
                    custom_params: Optional[Dict] = None) -> Dict:
        """
        创建视频生成任务
        
        Args:
            prompt: 视频描述文本
            model: 模型类型，如为None则使用默认模型
            reference_image: 参考图片URL/Base64
            reference_video: 参考视频URL/Base64（用于角色创建）
            custom_params: 自定义参数
            
        Returns:
            视频任务信息
            
        Raises:
            Sora2APIError: API调用失败
        """
        self.logger.info(f"创建视频生成任务: {prompt[:50]}...")
        
        # 构建请求数据
        data = {
            "model": (model or self.config.default_model).value,
            "prompt": prompt,
            "seconds": str(self.config.output_spec.duration_seconds),
            "size": self.config.output_spec.size_str
        }
        
        # 添加风格参数（如配置）
        if hasattr(self.config, 'style_id') and self.config.style_id:
            data["style_id"] = self.config.style_id
        
        # 添加参考媒体
        if reference_image:
            data["image"] = reference_image
        elif reference_video:
            data["video"] = reference_video
        
        # 添加自定义参数
        if custom_params:
            data.update(custom_params)
        
        # 发送请求
        endpoint = self._get_video_create_endpoint()
        
        # 处理文件上传
        files = None
        if reference_image and reference_image.startswith("@"):
            # 本地文件上传
            files = {"image": open(reference_image[1:], "rb")}
            data.pop("image", None)
        elif reference_video and reference_video.startswith("@"):
            files = {"video": open(reference_video[1:], "rb")}
            data.pop("video", None)
        
        try:
            response = self._make_request("POST", endpoint, data, files)
            self.logger.info(f"视频任务创建成功: {response.get('id')}")
            return response
        except Sora2APIError as e:
            self.logger.error(f"视频创建失败: {str(e)}")
            raise
    
    def get_video_status(self, video_id: str) -> Dict:
        """
        查询视频任务状态
        
        Args:
            video_id: 视频任务ID
            
        Returns:
            视频状态信息
        """
        self.logger.info(f"查询视频状态: {video_id}")
        
        # 构建端点
        if self.config.use_openai_official:
            endpoint = self.config.endpoints.OPENAI_VIDEO_RETRIEVE.format(video_id=video_id)
        else:
            # 第三方API通常使用任务ID查询
            endpoint = self.config.endpoints.MOUNTSEA_SORA_TASK
        
        # 构建查询参数
        params = {"taskId": video_id} if not self.config.use_openai_official else None
        
        try:
            response = self._make_request("GET", endpoint, params)
            return response
        except Sora2APIError as e:
            self.logger.error(f"状态查询失败: {str(e)}")
            raise
    
    def remix_video(self, video_id: str, prompt: str) -> Dict:
        """
        Remix现有视频
        
        Args:
            video_id: 原始视频ID
            prompt: 新的描述文本
            
        Returns:
            新的视频任务信息
        """
        self.logger.info(f"Remix视频: {video_id}")
        
        # 构建端点
        if self.config.use_openai_official:
            endpoint = self.config.endpoints.OPENAI_VIDEO_REMIX.format(video_id=video_id)
        else:
            # 第三方API可能使用不同端点
            endpoint = f"/videos/{video_id}/remix"
        
        data = {"prompt": prompt}
        
        try:
            response = self._make_request("POST", endpoint, data)
            return response
        except Sora2APIError as e:
            self.logger.error(f"Remix失败: {str(e)}")
            raise
    
    def download_video(self, video_id: str, output_path: Optional[str] = None) -> str:
        """
        下载视频文件
        
        Args:
            video_id: 视频ID
            output_path: 输出路径，如为None则生成临时路径
            
        Returns:
            下载的文件路径
        """
        self.logger.info(f"下载视频: {video_id}")
        
        # 构建端点
        if self.config.use_openai_official:
            endpoint = self.config.endpoints.OPENAI_VIDEO_CONTENT.format(video_id=video_id)
        else:
            # 第三方API可能不同
            endpoint = f"/videos/{video_id}/content"
        
        # 添加查询参数（如果需要）
        params = {"variant": "video"}
        
        try:
            response = self._make_request("GET", endpoint, params)
            
            # 处理响应
            if isinstance(response, dict) and "content" in response:
                content = response["content"]
            else:
                # 假设响应就是二进制内容
                content = response
            
            # 确定输出路径
            if output_path is None:
                import tempfile
                import os
                output_path = os.path.join(tempfile.gettempdir(), f"{video_id}.mp4")
            
            # 保存文件
            with open(output_path, "wb") as f:
                if isinstance(content, bytes):
                    f.write(content)
                else:
                    f.write(content.encode() if isinstance(content, str) else str(content).encode())
            
            self.logger.info(f"视频已下载: {output_path}")
            return output_path
            
        except Sora2APIError as e:
            self.logger.error(f"下载失败: {str(e)}")
            raise
    
    def list_models(self) -> List[Dict]:
        """
        列出可用模型
        
        Returns:
            模型列表
        """
        self.logger.info("列出可用模型")
        
        endpoint = self.config.endpoints.OPENAI_MODELS if self.config.use_openai_official else "/models"
        
        try:
            response = self._make_request("GET", endpoint)
            if isinstance(response, dict) and "data" in response:
                return response["data"]
            else:
                return response
        except Sora2APIError as e:
            self.logger.error(f"列出模型失败: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        self.logger.info("测试API连接")
        
        # 在配置生成模式下，返回模拟成功
        if self.config.generate_config_only:
            self.logger.info("配置生成模式：模拟连接测试成功")
            return True
        
        try:
            # 尝试列出模型（轻量级请求）
            self.list_models()
            self.logger.info("API连接测试成功")
            return True
        except Sora2APIError as e:
            self.logger.error(f"API连接测试失败: {str(e)}")
            return False
    
    def generate_config_document(self) -> Dict:
        """
        生成配置文档
        
        Returns:
            完整的配置文档
        """
        self.logger.info("生成配置文档")
        
        config_dict = self.config.to_dict()
        
        # 添加API端点示例
        examples = {
            "create_video_example": {
                "method": "POST",
                "endpoint": self._get_base_url() + self._get_video_create_endpoint(),
                "headers": self._build_headers(),
                "body": {
                    "model": self.config.default_model.value,
                    "prompt": "A cinematic shot of a cat playing piano in a concert hall",
                    "seconds": "15",
                    "size": "1080x1920"
                }
            },
            "get_status_example": {
                "method": "GET",
                "endpoint": self._get_base_url() + "/videos/video_abc123",
                "headers": self._build_headers()
            }
        }
        
        # 添加网络限制说明
        network_info = {
            "current_environment_restrictions": {
                "ssl_certificate_incompatible": True,
                "proxy_server_failed": True,
                "international_website_blocked": True,
                "recommendation": "Deploy in environment with normal international network access"
            }
        }
        
        # 合并所有信息
        full_document = {
            "timestamp": time.time(),
            "config": config_dict,
            "examples": examples,
            "network_info": network_info,
            "integration_status": "configuration_generated" if self.config.generate_config_only else "ready_for_api_calls"
        }
        
        return full_document


# 便捷函数
def create_default_client() -> Sora2APIClient:
    """创建默认客户端实例"""
    return Sora2APIClient()

def test_sora2_integration(config_path: Optional[str] = None) -> Dict:
    """
    测试Sora2集成
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        测试结果
    """
    from .config import Sora2IntegrationConfig
    
    if config_path:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        config = Sora2IntegrationConfig(**config_data)
    else:
        config = DEFAULT_CONFIG
    
    client = Sora2APIClient(config)
    
    results = {
        "connection_test": client.test_connection(),
        "config_document": client.generate_config_document(),
        "timestamp": time.time()
    }
    
    return results