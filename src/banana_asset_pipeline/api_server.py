#!/usr/bin/env python3
"""
Banana生图内核归档流水线API服务器

提供RESTful API接口，供Banana生图内核调用，
实现图片自动归档与记忆同步。
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import base64
import hashlib
import tempfile

try:
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("警告: FastAPI不可用，API服务器功能受限")

from .config import (
    ImageMetadata, AssetCategory, ImageQualityGrade,
    PipelineConfig, DEFAULT_CONFIG, generate_image_id,
    validate_metadata, MetadataSchema
)
from .pipeline import AssetPipeline, get_global_pipeline

# 配置日志
logger = logging.getLogger(__name__)

# Pydantic模型
class ImageGenerationRequest(BaseModel):
    """图片生成请求"""
    prompt: str = Field(..., description="生成提示词")
    negative_prompt: Optional[str] = Field("", description="负向提示词")
    model_name: str = Field("banana_model", description="模型名称")
    model_version: str = Field("1.0", description="模型版本")
    generation_params: Dict[str, Any] = Field(default_factory=dict, description="其他生成参数")
    avatar_id: str = Field(..., description="生成分身ID")
    task_id: str = Field(..., description="关联任务ID")
    scene: str = Field(..., description="使用场景")
    priority: int = Field(0, description="处理优先级（0=普通，1=高）")

class BatchImageGenerationRequest(BaseModel):
    """批量图片生成请求"""
    jobs: List[ImageGenerationRequest] = Field(..., description="任务列表")
    batch_id: Optional[str] = Field(None, description="批次ID")

class ImageUploadRequest(BaseModel):
    """图片上传请求"""
    image_data: str = Field(..., description="Base64编码的图片数据")
    generation_request: ImageGenerationRequest = Field(..., description="生成请求信息")

class PipelineStatusResponse(BaseModel):
    """流水线状态响应"""
    status: str = Field(..., description="流水线状态")
    stats: Dict[str, Any] = Field(..., description="统计信息")
    timestamp: str = Field(..., description="时间戳")

class ImageProcessingResultResponse(BaseModel):
    """图片处理结果响应"""
    job_id: str = Field(..., description="任务ID")
    success: bool = Field(..., description="是否成功")
    image_id: Optional[str] = Field(None, description="图片ID")
    processing_time_ms: float = Field(..., description="处理时间")
    memory_sync_success: Optional[bool] = Field(None, description="记忆同步是否成功")
    memory_sync_result: Optional[str] = Field(None, description="记忆同步结果")
    warnings: List[str] = Field(default_factory=list, description="警告信息")
    errors: List[str] = Field(default_factory=list, description="错误信息")

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索查询")
    filter_tags: Optional[List[str]] = Field(None, description="过滤标签")
    limit: int = Field(10, description="返回结果限制")

class SearchResultItem(BaseModel):
    """搜索结果项"""
    document_id: str = Field(..., description="文档ID")
    image_id: str = Field(..., description="图片ID")
    title: str = Field(..., description="标题")
    avatar_id: str = Field(..., description="分身ID")
    scene: str = Field(..., description="场景")
    category: str = Field(..., description="分类")
    quality_grade: str = Field(..., description="质量等级")
    file_path: str = Field(..., description="文件路径")
    dimensions: List[int] = Field(..., description="尺寸")
    similarity_score: float = Field(..., description="相似度分数")
    tags: List[str] = Field(default_factory=list, description="标签列表")

class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResultItem] = Field(default_factory=list, description="搜索结果")
    total: int = Field(0, description="总结果数")


class AssetPipelineAPIServer:
    """资产流水线API服务器"""
    
    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG, host: str = "0.0.0.0", port: int = 8080):
        self.config = config
        self.host = host
        self.port = port
        
        # 初始化流水线
        self.pipeline = get_global_pipeline()
        
        # 初始化FastAPI应用
        if FASTAPI_AVAILABLE:
            self.app = FastAPI(
                title="Banana生图内核归档流水线API",
                description="提供图片自动归档与记忆同步的RESTful API接口",
                version="1.0.0",
            )
            
            # 注册路由
            self._setup_routes()
        else:
            self.app = None
            logger.warning("FastAPI不可用，API服务器无法启动")
    
    def _setup_routes(self) -> None:
        """设置API路由"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "Banana生图内核归档流水线API",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "健康检查": "/health",
                    "提交图片处理": "/process/image",
                    "批量提交": "/process/batch",
                    "上传图片": "/upload/image",
                    "获取结果": "/result/{job_id}",
                    "搜索图片": "/search/images",
                    "流水线状态": "/status",
                    "启动流水线": "/start",
                    "停止流水线": "/stop",
                }
            }
        
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            pipeline_status = self.pipeline.get_stats()["pipeline_status"]
            
            return {
                "status": "healthy" if pipeline_status != "error" else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "pipeline_status": pipeline_status,
                "memory_sync_ready": self.pipeline.memory_sync.notebook_lm is not None,
            }
        
        @self.app.post("/process/image", response_model=ImageProcessingResultResponse)
        async def process_image(request: ImageGenerationRequest):
            """
            处理图片文件
            
            需要图片文件已存在本地文件系统，通过路径引用。
            实际使用中，Banana生图内核先生成图片文件，然后调用此API。
            """
            # 在实际实现中，这里需要从请求中获取图片文件路径
            # 由于API设计限制，这里使用简化实现
            
            raise HTTPException(
                status_code=501,
                detail="此端点需要图片文件路径，请使用/upload/image端点或确保文件已存在"
            )
        
        @self.app.post("/upload/image", response_model=ImageProcessingResultResponse)
        async def upload_image(
            image_file: UploadFile = File(...),
            prompt: str = Form(...),
            negative_prompt: str = Form(""),
            model_name: str = Form("banana_model"),
            model_version: str = Form("1.0"),
            generation_params: str = Form("{}"),
            avatar_id: str = Form(...),
            task_id: str = Form(...),
            scene: str = Form(...),
            priority: int = Form(0),
        ):
            """
            上传并处理图片
            
            支持Multipart表单上传，包含图片文件和生成参数。
            """
            try:
                # 解析生成参数
                try:
                    gen_params = json.loads(generation_params)
                except json.JSONDecodeError:
                    gen_params = {}
                
                # 添加基础参数
                gen_params.update({
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "model_name": model_name,
                    "model_version": model_version,
                })
                
                # 保存上传文件到临时目录
                temp_dir = self.config.temp_processing_dir
                os.makedirs(temp_dir, exist_ok=True)
                
                # 生成唯一文件名
                timestamp = int(time.time() * 1000)
                file_ext = os.path.splitext(image_file.filename)[1] or ".png"
                temp_filename = f"upload_{timestamp}_{hashlib.md5(prompt.encode()).hexdigest()[:8]}{file_ext}"
                temp_path = os.path.join(temp_dir, temp_filename)
                
                # 保存文件
                with open(temp_path, "wb") as f:
                    content = await image_file.read()
                    f.write(content)
                
                logger.info(f"图片上传保存: {temp_path}, 大小: {len(content)} 字节")
                
                # 提交处理任务
                job_id = self.pipeline.submit_job(
                    image_path=temp_path,
                    generation_params=gen_params,
                    avatar_id=avatar_id,
                    task_id=task_id,
                    scene=scene,
                    priority=priority,
                )
                
                # 等待处理结果（简化实现）
                for _ in range(30):  # 最多等待3秒
                    result = self.pipeline.get_result(job_id)
                    if result is not None:
                        break
                    await asyncio.sleep(0.1)
                
                if result is None:
                    return ImageProcessingResultResponse(
                        job_id=job_id,
                        success=False,
                        image_id=None,
                        processing_time_ms=0,
                        errors=["处理超时，请稍后查询结果"],
                    )
                
                # 转换为响应模型
                return ImageProcessingResultResponse(
                    job_id=result.job_id,
                    success=result.success,
                    image_id=result.image_id,
                    processing_time_ms=result.processing_time_ms,
                    memory_sync_success=result.memory_sync_success,
                    memory_sync_result=result.memory_sync_result,
                    warnings=result.warnings,
                    errors=result.errors,
                )
                
            except Exception as e:
                logger.error(f"图片上传处理失败: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
        
        @self.app.post("/upload/image_base64", response_model=ImageProcessingResultResponse)
        async def upload_image_base64(request: ImageUploadRequest):
            """
            上传Base64编码的图片
            
            适用于前端直接传递Base64图片数据。
            """
            try:
                # 解码Base64图片数据
                image_data = base64.b64decode(request.image_data)
                
                # 生成临时文件
                temp_dir = self.config.temp_processing_dir
                os.makedirs(temp_dir, exist_ok=True)
                
                timestamp = int(time.time() * 1000)
                file_hash = hashlib.md5(image_data).hexdigest()[:8]
                temp_filename = f"base64_{timestamp}_{file_hash}.png"
                temp_path = os.path.join(temp_dir, temp_filename)
                
                # 保存文件
                with open(temp_path, "wb") as f:
                    f.write(image_data)
                
                logger.info(f"Base64图片保存: {temp_path}, 大小: {len(image_data)} 字节")
                
                # 获取生成请求
                gen_request = request.generation_request
                gen_params = gen_request.generation_params.copy()
                gen_params.update({
                    "prompt": gen_request.prompt,
                    "negative_prompt": gen_request.negative_prompt or "",
                    "model_name": gen_request.model_name,
                    "model_version": gen_request.model_version,
                })
                
                # 提交处理任务
                job_id = self.pipeline.submit_job(
                    image_path=temp_path,
                    generation_params=gen_params,
                    avatar_id=gen_request.avatar_id,
                    task_id=gen_request.task_id,
                    scene=gen_request.scene,
                    priority=gen_request.priority,
                )
                
                # 等待结果
                for _ in range(30):
                    result = self.pipeline.get_result(job_id)
                    if result is not None:
                        break
                    await asyncio.sleep(0.1)
                
                if result is None:
                    return ImageProcessingResultResponse(
                        job_id=job_id,
                        success=False,
                        image_id=None,
                        processing_time_ms=0,
                        errors=["处理超时"],
                    )
                
                return ImageProcessingResultResponse(
                    job_id=result.job_id,
                    success=result.success,
                    image_id=result.image_id,
                    processing_time_ms=result.processing_time_ms,
                    memory_sync_success=result.memory_sync_success,
                    memory_sync_result=result.memory_sync_result,
                    warnings=result.warnings,
                    errors=result.errors,
                )
                
            except Exception as e:
                logger.error(f"Base64图片上传失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
        
        @self.app.post("/process/batch")
        async def process_batch(request: BatchImageGenerationRequest):
            """
            批量处理图片
            
            适用于一次性生成多张图片的场景。
            """
            try:
                jobs = []
                
                for job_request in request.jobs:
                    # 在实际实现中，需要图片文件路径
                    # 这里简化处理，返回需要文件路径的错误
                    
                    jobs.append({
                        "image_path": None,  # 实际需要提供
                        "generation_params": job_request.generation_params.copy(),
                        "avatar_id": job_request.avatar_id,
                        "task_id": job_request.task_id,
                        "scene": job_request.scene,
                        "priority": job_request.priority,
                    })
                
                # 实际批量提交
                # job_ids = self.pipeline.submit_batch(jobs)
                
                return {
                    "status": "pending",
                    "batch_id": request.batch_id or f"batch_{int(time.time())}",
                    "total_jobs": len(jobs),
                    "message": "批量任务已接收，请为每个任务提供图片文件路径",
                    "timestamp": datetime.now().isoformat(),
                }
                
            except Exception as e:
                logger.error(f"批量处理失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"批量处理失败: {str(e)}")
        
        @self.app.get("/result/{job_id}", response_model=ImageProcessingResultResponse)
        async def get_result(job_id: str):
            """获取任务结果"""
            result = self.pipeline.get_result(job_id)
            
            if result is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"任务ID '{job_id}' 不存在或尚未完成"
                )
            
            return ImageProcessingResultResponse(
                job_id=result.job_id,
                success=result.success,
                image_id=result.image_id,
                processing_time_ms=result.processing_time_ms,
                memory_sync_success=result.memory_sync_success,
                memory_sync_result=result.memory_sync_result,
                warnings=result.warnings,
                errors=result.errors,
            )
        
        @self.app.post("/search/images", response_model=SearchResponse)
        async def search_images(request: SearchRequest):
            """搜索相似图片"""
            try:
                # 使用记忆同步管理器搜索
                search_results = self.pipeline.memory_sync.search_similar_images(
                    query=request.query,
                    filter_tags=request.filter_tags,
                    limit=request.limit,
                )
                
                # 转换为响应模型
                result_items = []
                for item in search_results:
                    result_items.append(SearchResultItem(
                        document_id=item.get("document_id", ""),
                        image_id=item.get("image_id", ""),
                        title=item.get("title", ""),
                        avatar_id=item.get("avatar_id", ""),
                        scene=item.get("scene", ""),
                        category=item.get("category", ""),
                        quality_grade=item.get("quality_grade", ""),
                        file_path=item.get("file_path", ""),
                        dimensions=item.get("dimensions", [0, 0]),
                        similarity_score=item.get("similarity_score", 0),
                        tags=item.get("tags", []),
                    ))
                
                return SearchResponse(
                    results=result_items,
                    total=len(result_items),
                )
                
            except Exception as e:
                logger.error(f"图片搜索失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
        
        @self.app.get("/status", response_model=PipelineStatusResponse)
        async def get_status():
            """获取流水线状态"""
            stats = self.pipeline.get_stats()
            
            return PipelineStatusResponse(
                status=stats["pipeline_status"],
                stats=stats,
                timestamp=datetime.now().isoformat(),
            )
        
        @self.app.post("/start")
        async def start_pipeline():
            """启动流水线"""
            if self.pipeline.is_running:
                return {"status": "already_running", "message": "流水线已在运行中"}
            
            success = self.pipeline.start()
            
            if success:
                return {"status": "started", "message": "流水线启动成功"}
            else:
                raise HTTPException(status_code=500, detail="流水线启动失败")
        
        @self.app.post("/stop")
        async def stop_pipeline():
            """停止流水线"""
            if not self.pipeline.is_running:
                return {"status": "already_stopped", "message": "流水线已停止"}
            
            success = self.pipeline.stop()
            
            if success:
                return {"status": "stopped", "message": "流水线停止成功"}
            else:
                raise HTTPException(status_code=500, detail="流水线停止失败")
    
    def start_server(self) -> None:
        """启动API服务器"""
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPI不可用，无法启动API服务器")
            return
        
        try:
            import uvicorn
            
            # 确保流水线已启动
            if not self.pipeline.is_running:
                self.pipeline.start()
            
            logger.info(f"启动API服务器: {self.host}:{self.port}")
            
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info",
            )
            
        except KeyboardInterrupt:
            logger.info("API服务器接收到中断信号，正在停止...")
        except Exception as e:
            logger.error(f"API服务器启动失败: {str(e)}", exc_info=True)
        finally:
            # 停止流水线
            if self.pipeline.is_running:
                self.pipeline.stop()
    
    def get_openapi_schema(self) -> Dict[str, Any]:
        """获取OpenAPI模式"""
        if self.app is None:
            return {}
        
        return self.app.openapi()


# 便捷启动函数
def start_asset_pipeline_api_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    config: Optional[PipelineConfig] = None,
) -> None:
    """
    启动资产流水线API服务器
    
    Args:
        host: 监听主机
        port: 监听端口
        config: 配置
    """
    config = config or DEFAULT_CONFIG
    
    server = AssetPipelineAPIServer(config, host, port)
    server.start_server()


if __name__ == "__main__":
    # 模块测试
    print("API服务器模块测试")
    
    # 创建测试配置
    config = PipelineConfig(
        base_storage_dir="test_outputs/images",
        temp_processing_dir="test_temp/processing",
        metadata_dir="test_data/metadata",
        notebook_lm_sync_enabled=False,
    )
    
    print("模块测试完成")
    print("注意: 完整API服务器测试需要安装FastAPI和Uvicorn")