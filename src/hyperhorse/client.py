#!/usr/bin/env python3
"""
HyperHorse视频引擎客户端
提供OpenAI Video兼容的Python SDK接口
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Iterator
from enum import Enum
import logging

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ====================== 客户端模型定义 ======================

class VideoGenerationModel(str, Enum):
    """支持的视频生成模型"""
    HYPERHORSE_V1 = "hyperhorse-video-v1"
    HYPERHORSE_V2 = "hyperhorse-video-v2"

class VideoSize(str, Enum):
    """视频尺寸"""
    _1080x1920 = "1080x1920"  # 竖屏
    _1920x1080 = "1920x1080"  # 横屏
    _1080x1080 = "1080x1080"  # 方形

class VideoQuality(str, Enum):
    """视频质量"""
    STANDARD = "standard"
    HD = "hd"
    ULTRA_HD = "ultra_hd"

class VideoGenerationRequest(BaseModel):
    """视频生成请求"""
    model: VideoGenerationModel = Field(
        default=VideoGenerationModel.HYPERHORSE_V1,
        description="视频生成模型"
    )
    prompt: str = Field(
        ...,
        description="视频内容描述",
        min_length=1,
        max_length=1000
    )
    size: VideoSize = Field(
        default=VideoSize._1080x1920,
        description="视频分辨率"
    )
    duration: int = Field(
        default=15,
        description="视频时长（秒），范围5-60",
        ge=5,
        le=60
    )
    quality: VideoQuality = Field(
        default=VideoQuality.HD,
        description="视频质量"
    )
    n: int = Field(
        default=1,
        description="生成视频数量，最多5个",
        ge=1,
        le=5
    )
    style: Optional[str] = Field(
        default=None,
        description="视频风格"
    )
    language: Optional[str] = Field(
        default="en",
        description="目标语言代码"
    )
    aspect_ratio: Optional[str] = Field(
        default=None,
        description="宽高比"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="自定义元数据"
    )

class VideoVariationRequest(BaseModel):
    """视频变体生成请求"""
    model: VideoGenerationModel = Field(
        default=VideoGenerationModel.HYPERHORSE_V1,
        description="视频生成模型"
    )
    video: str = Field(
        ...,
        description="原始视频URL或base64编码"
    )
    prompt: Optional[str] = Field(
        default=None,
        description="变体描述"
    )
    n: int = Field(
        default=1,
        description="生成变体数量"
    )
    size: VideoSize = Field(
        default=VideoSize._1080x1920,
        description="视频分辨率"
    )

class VideoEditRequest(BaseModel):
    """视频编辑请求"""
    model: VideoGenerationModel = Field(
        default=VideoGenerationModel.HYPERHORSE_V1,
        description="视频生成模型"
    )
    video: str = Field(
        ...,
        description="原始视频URL或base64编码"
    )
    prompt: str = Field(
        ...,
        description="编辑指令描述"
    )
    instruction: Optional[str] = Field(
        default=None,
        description="具体编辑指令"
    )
    n: int = Field(
        default=1,
        description="生成编辑视频数量"
    )
    size: VideoSize = Field(
        default=VideoSize._1080x1920,
        description="视频分辨率"
    )

class VideoGenerationResponse(BaseModel):
    """视频生成响应"""
    id: str = Field(..., description="视频任务ID")
    object: str = Field(default="video", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    data: List[Dict[str, str]] = Field(
        ...,
        description="生成的视频数据列表"
    )

# ====================== 客户端主类 ======================

class HyperHorseClient:
    """
    HyperHorse视频引擎客户端
    
    使用示例:
    ```python
    client = HyperHorseClient(base_url="http://localhost:8000")
    
    # 生成视频
    response = client.video.generations.create(
        model="hyperhorse-video-v1",
        prompt="时尚服装展示视频",
        size="1080x1920",
        duration=15
    )
    
    # 查询状态
    status = client.video.generations.retrieve(response.id)
    ```
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        初始化客户端
        
        参数:
            base_url: API基础URL，默认http://localhost:8000
            api_key: API密钥（可选）
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        # 初始化子客户端
        self.video = VideoClient(self)
        
        logger.info(f"初始化HyperHorse客户端，基础URL: {self.base_url}")
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        参数:
            method: HTTP方法
            endpoint: API端点路径
            data: 请求体数据
            params: 查询参数
        
        返回:
            响应数据字典
        """
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "HyperHorse-Python-Client/1.0.0"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {str(e)}")
            raise
    
    def create_video_generation(
        self,
        request: VideoGenerationRequest
    ) -> VideoGenerationResponse:
        """
        创建视频生成任务
        
        参数:
            request: 生成请求
        
        返回:
            生成响应
        """
        endpoint = "/v1/video/generations"
        
        data = request.dict(exclude_none=True)
        
        response_data = self._request("POST", endpoint, data=data)
        
        return VideoGenerationResponse(**response_data)
    
    def create_video_variation(
        self,
        request: VideoVariationRequest
    ) -> VideoGenerationResponse:
        """
        创建视频变体生成任务
        
        参数:
            request: 变体生成请求
        
        返回:
            生成响应
        """
        endpoint = "/v1/video/variations"
        
        data = request.dict(exclude_none=True)
        
        response_data = self._request("POST", endpoint, data=data)
        
        return VideoGenerationResponse(**response_data)
    
    def create_video_edit(
        self,
        request: VideoEditRequest
    ) -> VideoGenerationResponse:
        """
        创建视频编辑任务
        
        参数:
            request: 编辑请求
        
        返回:
            生成响应
        """
        endpoint = "/v1/video/edits"
        
        data = request.dict(exclude_none=True)
        
        response_data = self._request("POST", endpoint, data=data)
        
        return VideoGenerationResponse(**response_data)
    
    def get_video_generation_status(
        self,
        task_id: str,
        include_urls: bool = True
    ) -> Dict[str, Any]:
        """
        获取视频生成任务状态
        
        参数:
            task_id: 任务ID
            include_urls: 是否包含视频URL
        
        返回:
            状态信息字典
        """
        endpoint = f"/v1/video/generations/{task_id}"
        
        params = {"include_urls": include_urls}
        
        return self._request("GET", endpoint, params=params)

class VideoClient:
    """视频相关API的客户端"""
    
    def __init__(self, client: HyperHorseClient):
        self._client = client
        self.generations = VideoGenerationsClient(client)

class VideoGenerationsClient:
    """视频生成相关API的客户端"""
    
    def __init__(self, client: HyperHorseClient):
        self._client = client
    
    def create(
        self,
        model: Union[str, VideoGenerationModel] = "hyperhorse-video-v1",
        prompt: Optional[str] = None,
        size: Union[str, VideoSize] = "1080x1920",
        duration: int = 15,
        quality: Union[str, VideoQuality] = "hd",
        n: int = 1,
        style: Optional[str] = None,
        language: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> VideoGenerationResponse:
        """
        创建视频生成任务（兼容OpenAI SDK接口）
        
        参数:
            model: 模型名称
            prompt: 视频内容描述
            size: 视频分辨率
            duration: 视频时长（秒）
            quality: 视频质量
            n: 生成数量
            style: 视频风格
            language: 目标语言
            aspect_ratio: 宽高比
            metadata: 自定义元数据
            **kwargs: 其他参数（将合并到metadata中）
        
        返回:
            视频生成响应
        
        示例:
        ```python
        response = client.video.generations.create(
            prompt="时尚服装展示",
            size="1080x1920"
        )
        ```
        """
        if prompt is None:
            raise ValueError("prompt参数是必需的")
        
        # 合并metadata和kwargs
        final_metadata = metadata or {}
        if kwargs:
            final_metadata.update(kwargs)
        
        # 创建请求对象
        request = VideoGenerationRequest(
            model=VideoGenerationModel(model) if isinstance(model, str) else model,
            prompt=prompt,
            size=VideoSize(size) if isinstance(size, str) else size,
            duration=duration,
            quality=VideoQuality(quality) if isinstance(quality, str) else quality,
            n=n,
            style=style,
            language=language,
            aspect_ratio=aspect_ratio,
            metadata=final_metadata if final_metadata else None
        )
        
        return self._client.create_video_generation(request)
    
    def retrieve(self, task_id: str) -> Dict[str, Any]:
        """
        获取视频生成任务状态（兼容OpenAI SDK接口）
        
        参数:
            task_id: 任务ID
        
        返回:
            状态信息字典
        
        示例:
        ```python
        status = client.video.generations.retrieve("vid_abc123")
        ```
        """
        return self._client.get_video_generation_status(task_id)

# ====================== 辅助函数 ======================

def create_video_generation(
    prompt: str,
    model: str = "hyperhorse-video-v1",
    size: str = "1080x1920",
    duration: int = 15,
    quality: str = "hd",
    n: int = 1,
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
    **kwargs
) -> VideoGenerationResponse:
    """
    快速创建视频生成任务（简化接口）
    
    参数:
        prompt: 视频内容描述
        model: 模型名称
        size: 视频分辨率
        duration: 视频时长（秒）
        quality: 视频质量
        n: 生成数量
        base_url: API基础URL
        api_key: API密钥
        **kwargs: 其他参数（将合并到metadata中）
    
    返回:
        视频生成响应
    
    示例:
    ```python
    response = create_video_generation(
        prompt="时尚服装展示",
        size="1080x1920"
    )
    ```
    """
    client = HyperHorseClient(base_url=base_url, api_key=api_key)
    
    request = VideoGenerationRequest(
        model=VideoGenerationModel(model),
        prompt=prompt,
        size=VideoSize(size),
        duration=duration,
        quality=VideoQuality(quality),
        n=n,
        metadata=kwargs if kwargs else None
    )
    
    return client.create_video_generation(request)

# ====================== 异步客户端（可选） ======================

try:
    import aiohttp
    import asyncio
    
    class AsyncHyperHorseClient:
        """
        HyperHorse异步客户端
        
        使用示例:
        ```python
        async with AsyncHyperHorseClient() as client:
            response = await client.video.generations.create(
                prompt="时尚服装展示"
            )
        ```
        """
        
        def __init__(
            self,
            base_url: str = "http://localhost:8000",
            api_key: Optional[str] = None,
            timeout: int = 30
        ):
            self.base_url = base_url.rstrip('/')
            self.api_key = api_key
            self.timeout = timeout
            self.session = None
            
            self.video = AsyncVideoClient(self)
        
        async def __aenter__(self):
            self.session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "HyperHorse-Async-Client/1.0.0"
                }
            )
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.session:
                await self.session.close()
        
        async def _request(
            self,
            method: str,
            endpoint: str,
            data: Optional[Dict[str, Any]] = None,
            params: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            url = f"{self.base_url}{endpoint}"
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=self.timeout
            ) as response:
                response.raise_for_status()
                return await response.json()
        
        async def create_video_generation(
            self,
            request: VideoGenerationRequest
        ) -> VideoGenerationResponse:
            endpoint = "/v1/video/generations"
            data = request.dict(exclude_none=True)
            
            response_data = await self._request("POST", endpoint, data=data)
            
            return VideoGenerationResponse(**response_data)
    
    class AsyncVideoClient:
        def __init__(self, client: AsyncHyperHorseClient):
            self._client = client
            self.generations = AsyncVideoGenerationsClient(client)
    
    class AsyncVideoGenerationsClient:
        def __init__(self, client: AsyncHyperHorseClient):
            self._client = client
        
        async def create(
            self,
            model: Union[str, VideoGenerationModel] = "hyperhorse-video-v1",
            prompt: Optional[str] = None,
            size: Union[str, VideoSize] = "1080x1920",
            duration: int = 15,
            quality: Union[str, VideoQuality] = "hd",
            n: int = 1,
            **kwargs
        ) -> VideoGenerationResponse:
            if prompt is None:
                raise ValueError("prompt参数是必需的")
            
            request = VideoGenerationRequest(
                model=VideoGenerationModel(model) if isinstance(model, str) else model,
                prompt=prompt,
                size=VideoSize(size) if isinstance(size, str) else size,
                duration=duration,
                quality=VideoQuality(quality) if isinstance(quality, str) else quality,
                n=n,
                metadata=kwargs if kwargs else None
            )
            
            return await self._client.create_video_generation(request)
    
except ImportError:
    # aiohttp不可用，不提供异步客户端
    pass