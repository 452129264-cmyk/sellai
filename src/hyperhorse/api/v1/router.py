#!/usr/bin/env python3
"""
HyperHorse OpenAI Video兼容API路由器
提供/v1/video/generations、/v1/video/variations、/v1/video/edits接口
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from enum import Enum

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field, validator

from src.hyperhorse.api_adapter import (
    HyperHorseAPIAdapter,
    VideoGenerationRequest,
    VideoGenerationResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/video", tags=["video"])

# ====================== OpenAI Video兼容请求/响应模型 ======================

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

class OpenAIVideoGenerationRequest(BaseModel):
    """OpenAI Video兼容的生成请求"""
    model: VideoGenerationModel = Field(
        default=VideoGenerationModel.HYPERHORSE_V1,
        description="视频生成模型"
    )
    prompt: str = Field(
        ...,
        description="视频内容描述，支持详细指令",
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
        description="视频风格，如'cinematic', 'documentary', 'vlog'等"
    )
    language: Optional[str] = Field(
        default="en",
        description="目标语言代码，默认英语(en)"
    )
    aspect_ratio: Optional[str] = Field(
        default=None,
        description="宽高比，如'9:16', '16:9', '1:1'，优先使用size参数"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="自定义元数据"
    )
    
    @validator('aspect_ratio')
    def validate_aspect_ratio(cls, v, values):
        if v and 'size' in values and values['size']:
            # size参数优先级更高
            logger.warning(f"aspect_ratio参数被忽略，使用size参数: {values['size']}")
            return None
        return v

class OpenAIVideoGenerationResponse(BaseModel):
    """OpenAI Video兼容的生成响应"""
    id: str = Field(..., description="视频任务ID")
    object: str = Field(default="video", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    data: List[Dict[str, str]] = Field(
        ...,
        description="生成的视频数据列表，包含视频URL等信息"
    )

class OpenAIVideoVariationRequest(BaseModel):
    """OpenAI Video兼容的变体生成请求"""
    model: VideoGenerationModel = Field(
        default=VideoGenerationModel.HYPERHORSE_V1,
        description="视频生成模型"
    )
    video: str = Field(
        ...,
        description="原始视频URL或base64编码",
        min_length=1
    )
    prompt: Optional[str] = Field(
        default=None,
        description="变体描述，如未提供则自动生成"
    )
    n: int = Field(
        default=1,
        description="生成变体数量，最多5个",
        ge=1,
        le=5
    )
    size: VideoSize = Field(
        default=VideoSize._1080x1920,
        description="视频分辨率"
    )

class OpenAIVideoEditRequest(BaseModel):
    """OpenAI Video兼容的编辑请求"""
    model: VideoGenerationModel = Field(
        default=VideoGenerationModel.HYPERHORSE_V1,
        description="视频生成模型"
    )
    video: str = Field(
        ...,
        description="原始视频URL或base64编码",
        min_length=1
    )
    prompt: str = Field(
        ...,
        description="编辑指令描述",
        min_length=1,
        max_length=1000
    )
    instruction: Optional[str] = Field(
        default=None,
        description="具体编辑指令，如'裁剪前5秒'、'添加字幕'等"
    )
    n: int = Field(
        default=1,
        description="生成编辑视频数量，最多5个",
        ge=1,
        le=5
    )
    size: VideoSize = Field(
        default=VideoSize._1080x1920,
        description="视频分辨率"
    )

# ====================== 辅助函数 ======================

def _create_hyperhorse_adapter() -> HyperHorseAPIAdapter:
    """创建HyperHorse API适配器实例"""
    return HyperHorseAPIAdapter()

def _convert_to_openai_format(
    response: VideoGenerationResponse,
    model: str,
    created: int
) -> OpenAIVideoGenerationResponse:
    """将HyperHorse响应转换为OpenAI格式"""
    
    data = []
    if response.video_urls:
        for i, url in enumerate(response.video_urls):
            data.append({
                "url": url,
                "format": "mp4",
                "resolution": response.resolution,
                "duration_seconds": response.duration_seconds
            })
    
    return OpenAIVideoGenerationResponse(
        id=response.request_id,
        object="video",
        created=created,
        model=model,
        data=data
    )

def _parse_prompt_to_category(prompt: str) -> str:
    """将prompt解析为品类分类"""
    # 简单实现：根据关键词映射
    prompt_lower = prompt.lower()
    
    category_map = {
        "服装": ["clothing", "fashion", "apparel", "dress", "shirt", "pants"],
        "电子产品": ["electronics", "phone", "laptop", "camera", "gadget"],
        "家居": ["home", "furniture", "decor", "kitchen", "bedroom"],
        "美妆": ["beauty", "cosmetics", "makeup", "skincare", "perfume"],
        "食品": ["food", "snack", "drink", "beverage", "recipe"],
        "运动": ["sports", "fitness", "exercise", "outdoor", "gym"]
    }
    
    for category, keywords in category_map.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                return category
    
    # 默认返回"综合"
    return "综合"

def _map_size_to_platform(size: VideoSize) -> List[str]:
    """根据尺寸映射推荐平台"""
    if size == VideoSize._1080x1920:
        return ["tiktok", "instagram", "youtube_shorts"]
    elif size == VideoSize._1920x1080:
        return ["youtube", "facebook", "bilibili"]
    else:
        return ["instagram", "pinterest", "tiktok"]

def _map_quality_to_level(quality: VideoQuality) -> str:
    """质量等级映射"""
    mapping = {
        VideoQuality.STANDARD: "standard",
        VideoQuality.HD: "premium",
        VideoQuality.ULTRA_HD: "ultra"
    }
    return mapping.get(quality, "premium")

# ====================== API端点 ======================

@router.post("/generations", response_model=OpenAIVideoGenerationResponse)
async def create_video_generation(
    request: OpenAIVideoGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    生成新视频
    兼容OpenAI Video API格式
    """
    
    logger.info(f"收到视频生成请求，模型: {request.model}, prompt长度: {len(request.prompt)}")
    
    try:
        # 解析参数
        category = _parse_prompt_to_category(request.prompt)
        
        # 尺寸解析
        size_parts = request.size.value.split('x')
        if len(size_parts) == 2:
            width, height = size_parts
        else:
            width, height = 1080, 1920
        
        # 映射平台
        target_platforms = _map_size_to_platform(request.size)
        
        # 创建HyperHorse请求
        hyperhorse_request = VideoGenerationRequest(
            category=category,
            target_regions=["global"],  # 全球市场
            duration_seconds=request.duration,
            quality_level=_map_quality_to_level(request.quality),
            target_platforms=target_platforms,
            target_language=request.language or "en",
            style_guidelines={
                "prompt": request.prompt,
                "style": request.style,
                "aspect_ratio": request.aspect_ratio,
                "resolution": f"{width}x{height}"
            },
            metadata=request.metadata or {}
        )
        
        # 设置请求ID（使用OpenAI格式）
        hyperhorse_request.request_id = f"vid_{uuid.uuid4().hex[:24]}"
        
        # 调用HyperHorse引擎
        adapter = _create_hyperhorse_adapter()
        
        # 异步处理（实际可放入后台任务）
        def generate_task():
            return adapter.generate_video(hyperhorse_request)
        
        # 立即执行（简化版，实际应异步）
        response = generate_task()
        
        # 转换为OpenAI格式
        created = int(datetime.now().timestamp())
        openai_response = _convert_to_openai_format(
            response,
            request.model.value,
            created
        )
        
        logger.info(f"视频生成任务创建成功，ID: {openai_response.id}")
        
        return openai_response
        
    except Exception as e:
        logger.error(f"视频生成失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"视频生成失败: {str(e)}")

@router.post("/variations", response_model=OpenAIVideoGenerationResponse)
async def create_video_variation(
    request: OpenAIVideoVariationRequest,
    background_tasks: BackgroundTasks
):
    """
    生成视频变体
    兼容OpenAI Video API格式
    """
    
    logger.info(f"收到视频变体生成请求，原始视频: {request.video[:50]}...")
    
    try:
        # 这里需要实现变体生成逻辑
        # 简化实现：基于原始视频生成类似内容
        
        # 使用HyperHorse引擎的变体功能（假设core.py中有相关方法）
        adapter = _create_hyperhorse_adapter()
        
        # 解析prompt或自动生成
        prompt = request.prompt or "基于原始视频生成的变体版本"
        
        # 创建生成请求（简化）
        hyperhorse_request = VideoGenerationRequest(
            category="视频变体",
            target_regions=["global"],
            duration_seconds=15,  # 默认15秒
            quality_level="premium",
            target_platforms=_map_size_to_platform(request.size),
            target_language="en",
            style_guidelines={
                "original_video": request.video,
                "prompt": prompt
            }
        )
        
        hyperhorse_request.request_id = f"vid_{uuid.uuid4().hex[:24]}"
        
        # 调用生成（简化）
        response = adapter.generate_video(hyperhorse_request)
        
        # 转换为OpenAI格式
        created = int(datetime.now().timestamp())
        openai_response = _convert_to_openai_format(
            response,
            request.model.value,
            created
        )
        
        logger.info(f"视频变体生成成功，ID: {openai_response.id}")
        
        return openai_response
        
    except Exception as e:
        logger.error(f"视频变体生成失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"视频变体生成失败: {str(e)}")

@router.post("/edits", response_model=OpenAIVideoGenerationResponse)
async def create_video_edit(
    request: OpenAIVideoEditRequest,
    background_tasks: BackgroundTasks
):
    """
    编辑视频
    兼容OpenAI Video API格式
    """
    
    logger.info(f"收到视频编辑请求，指令: {request.instruction or request.prompt}")
    
    try:
        # 这里需要实现视频编辑逻辑
        # 简化实现：将编辑视为特殊生成
        
        adapter = _create_hyperhorse_adapter()
        
        # 创建编辑请求
        hyperhorse_request = VideoGenerationRequest(
            category="视频编辑",
            target_regions=["global"],
            duration_seconds=15,
            quality_level="premium",
            target_platforms=_map_size_to_platform(request.size),
            target_language="en",
            style_guidelines={
                "original_video": request.video,
                "edit_prompt": request.prompt,
                "edit_instruction": request.instruction
            }
        )
        
        hyperhorse_request.request_id = f"vid_{uuid.uuid4().hex[:24]}"
        
        # 调用生成（简化）
        response = adapter.generate_video(hyperhorse_request)
        
        # 转换为OpenAI格式
        created = int(datetime.now().timestamp())
        openai_response = _convert_to_openai_format(
            response,
            request.model.value,
            created
        )
        
        logger.info(f"视频编辑任务创建成功，ID: {openai_response.id}")
        
        return openai_response
        
    except Exception as e:
        logger.error(f"视频编辑失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"视频编辑失败: {str(e)}")

@router.get("/generations/{task_id}")
async def get_video_generation_status(
    task_id: str,
    include_urls: bool = Query(default=True, description="是否包含视频URL")
):
    """
    获取视频生成任务状态
    """
    
    logger.info(f"查询视频生成任务状态，ID: {task_id}")
    
    try:
        adapter = _create_hyperhorse_adapter()
        
        # 这里需要实现状态查询（假设api_adapter有相关方法）
        # 简化实现：返回模拟状态
        
        # 实际应查询数据库
        status = {
            "id": task_id,
            "status": "completed",  # 模拟已完成
            "progress": 100,
            "created_at": int(datetime.now().timestamp()) - 300,
            "completed_at": int(datetime.now().timestamp()) - 60,
            "video_count": 1
        }
        
        if include_urls:
            status["videos"] = [
                {
                    "url": f"https://hyperhorse.example.com/videos/{task_id}/video.mp4",
                    "format": "mp4",
                    "duration": 15,
                    "size": "1080x1920"
                }
            ]
        
        return status
        
    except Exception as e:
        logger.error(f"查询任务状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"任务未找到: {task_id}")