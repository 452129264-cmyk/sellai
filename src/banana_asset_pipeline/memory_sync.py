#!/usr/bin/env python3
"""
Banana生图内核记忆同步模块

负责将图片元数据同步到Notebook LM永久记忆系统，
建立图片-知识双向索引，支持跨任务语义检索。
"""

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 尝试导入Notebook LM集成
try:
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType,
        initialize_notebook_lm_integration,
        NotebookLMConfig,
    )
    NOTEBOOK_LM_AVAILABLE = True
except ImportError:
    NOTEBOOK_LM_AVAILABLE = False
    print("警告: Notebook LM集成模块未找到，记忆同步功能受限")

from .config import (
    ImageMetadata, AssetCategory, ImageQualityGrade,
    PipelineConfig, DEFAULT_CONFIG, generate_image_id,
    validate_metadata
)

# 配置日志
logger = logging.getLogger(__name__)


class MemorySyncManager:
    """记忆同步管理器"""
    
    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG):
        self.config = config
        
        # Notebook LM集成实例
        self.notebook_lm = None
        self.knowledge_base_id = None
        
        # 性能优化
        self.batch_queue = []
        self.max_batch_size = config.notebook_lm_batch_size
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent)
        
        # 状态跟踪
        self.stats = {
            "total_synced": 0,
            "last_sync_time": None,
            "sync_errors": 0,
        }
        
        # 初始化
        self._initialize()
    
    def _initialize(self) -> None:
        """初始化记忆系统连接"""
        if not self.config.notebook_lm_sync_enabled:
            logger.info("记忆同步功能已禁用")
            return
        
        if not NOTEBOOK_LM_AVAILABLE:
            logger.warning("Notebook LM集成不可用，记忆同步功能受限")
            return
        
        try:
            # 初始化Notebook LM集成
            self.notebook_lm = initialize_notebook_lm_integration()
            logger.info("Notebook LM集成初始化成功")
            
            # 确保知识库存在
            self._ensure_knowledge_base()
            
        except Exception as e:
            logger.error(f"记忆系统初始化失败: {str(e)}")
            self.notebook_lm = None
    
    def _ensure_knowledge_base(self) -> None:
        """确保Banana生图知识库存在"""
        if not self.notebook_lm:
            return
        
        try:
            # 查找现有知识库
            kb_list = self.notebook_lm.list_knowledge_bases()
            
            target_kb = None
            for kb in kb_list:
                if kb.get("name") == self.config.notebook_lm_kb_name:
                    target_kb = kb
                    break
            
            if target_kb:
                self.knowledge_base_id = target_kb["id"]
                logger.info(f"找到现有知识库: {self.knowledge_base_id}")
            else:
                # 创建新知识库
                self.knowledge_base_id = self.notebook_lm.create_knowledge_base(
                    name=self.config.notebook_lm_kb_name,
                    description=self.config.notebook_lm_kb_description,
                    tags=["banana_ai", "image_generation", "asset_management", "sellai"]
                )
                logger.info(f"创建新知识库: {self.knowledge_base_id}")
                
        except Exception as e:
            logger.error(f"知识库检查失败: {str(e)}")
            self.knowledge_base_id = None
    
    def sync_image_metadata(self, metadata: ImageMetadata) -> Tuple[bool, Optional[str]]:
        """
        同步单张图片元数据到记忆系统
        
        Args:
            metadata: 图片元数据
            
        Returns:
            (是否成功, 文档ID或错误信息)
        """
        if not self.config.notebook_lm_sync_enabled:
            return True, "记忆同步已禁用"
        
        if not self.notebook_lm or not self.knowledge_base_id:
            return False, "记忆系统未就绪"
        
        try:
            # 创建知识文档
            document = self._create_document_from_metadata(metadata)
            
            # 添加到知识库
            start_time = time.time()
            doc_id = self.notebook_lm.add_document(
                knowledge_base_id=self.knowledge_base_id,
                document=document,
                validate=True
            )
            
            processing_time = (time.time() - start_time) * 1000
            if processing_time > self.config.max_processing_delay_ms:
                logger.warning(f"记忆同步延迟 {processing_time:.0f}ms 超过限制 {self.config.max_processing_delay_ms}ms")
            
            # 更新统计
            self.stats["total_synced"] += 1
            self.stats["last_sync_time"] = datetime.now().isoformat()
            
            logger.info(f"图片元数据同步成功: {metadata.image_id} -> 文档ID: {doc_id}")
            return True, doc_id
            
        except Exception as e:
            self.stats["sync_errors"] += 1
            logger.error(f"图片元数据同步失败: {metadata.image_id}, 错误: {str(e)}")
            return False, str(e)
    
    def sync_image_metadata_batch(self, metadata_list: List[ImageMetadata]) -> Dict[str, Any]:
        """
        批量同步图片元数据到记忆系统
        
        Args:
            metadata_list: 图片元数据列表
            
        Returns:
            批量同步结果
        """
        if not self.config.notebook_lm_sync_enabled:
            return {
                "status": "skipped",
                "reason": "记忆同步已禁用",
                "total": len(metadata_list),
                "success": 0,
                "failed": 0,
            }
        
        if not self.notebook_lm or not self.knowledge_base_id:
            return {
                "status": "failed",
                "reason": "记忆系统未就绪",
                "total": len(metadata_list),
                "success": 0,
                "failed": len(metadata_list),
            }
        
        results = {
            "status": "processing",
            "total": len(metadata_list),
            "success": 0,
            "failed": 0,
            "details": [],
            "processing_time_ms": 0,
        }
        
        start_time = time.time()
        
        try:
            # 创建文档列表
            documents = []
            for metadata in metadata_list:
                try:
                    document = self._create_document_from_metadata(metadata)
                    documents.append(document)
                    results["details"].append({
                        "image_id": metadata.image_id,
                        "status": "prepared",
                        "error": None,
                    })
                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "image_id": metadata.image_id,
                        "status": "preparation_failed",
                        "error": str(e),
                    })
            
            # 批量添加文档
            if documents:
                batch_results = self.notebook_lm.batch_add_documents(
                    knowledge_base_id=self.knowledge_base_id,
                    documents=documents,
                    batch_size=self.max_batch_size
                )
                
                # 统计结果
                for i, batch_result in enumerate(batch_results):
                    metadata = metadata_list[i]
                    
                    if batch_result["status"] == "success":
                        results["success"] += 1
                        results["details"][i]["status"] = "synced"
                        results["details"][i]["document_id"] = batch_result["document_id"]
                        
                        # 更新全局统计
                        self.stats["total_synced"] += 1
                    else:
                        results["failed"] += 1
                        results["details"][i]["status"] = "sync_failed"
                        results["details"][i]["error"] = batch_result.get("error", "未知错误")
                        
                        self.stats["sync_errors"] += 1
            
            # 更新最后同步时间
            self.stats["last_sync_time"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"批量同步失败: {str(e)}")
            results["status"] = "error"
            results["error"] = str(e)
        
        # 计算处理时间
        processing_time = (time.time() - start_time) * 1000
        results["processing_time_ms"] = processing_time
        
        # 检查性能
        if metadata_list:
            avg_time = processing_time / len(metadata_list)
            if avg_time > self.config.max_processing_delay_ms:
                logger.warning(f"批量同步平均延迟 {avg_time:.0f}ms 超过限制 {self.config.max_processing_delay_ms}ms")
        
        logger.info(f"批量同步完成: 成功 {results['success']}/{results['total']}, 耗时 {processing_time:.0f}ms")
        return results
    
    def _create_document_from_metadata(self, metadata: ImageMetadata) -> KnowledgeDocument:
        """从图片元数据创建知识文档"""
        # 构建文档内容
        content_parts = []
        
        # 基础信息
        content_parts.append(f"# 图片资产: {metadata.image_id}")
        content_parts.append(f"")
        content_parts.append(f"## 基本信息")
        content_parts.append(f"- **文件名**: {metadata.file_name}")
        content_parts.append(f"- **文件路径**: {metadata.file_path}")
        content_parts.append(f"- **尺寸**: {metadata.dimensions[0]}x{metadata.dimensions[1]}")
        content_parts.append(f"- **格式**: {metadata.format}")
        content_parts.append(f"- **文件大小**: {metadata.file_size:,} 字节")
        content_parts.append(f"")
        
        # 生成信息
        content_parts.append(f"## 生成信息")
        content_parts.append(f"- **生成提示**: {metadata.prompt}")
        content_parts.append(f"- **负向提示**: {metadata.negative_prompt}")
        content_parts.append(f"- **模型**: {metadata.model_name} v{metadata.model_version}")
        content_parts.append(f"- **生成时间**: {metadata.created_at}")
        content_parts.append(f"")
        
        # 业务上下文
        content_parts.append(f"## 业务上下文")
        content_parts.append(f"- **生成分身**: {metadata.avatar_id}")
        content_parts.append(f"- **关联任务**: {metadata.task_id}")
        content_parts.append(f"- **使用场景**: {metadata.scene}")
        content_parts.append(f"- **资产类别**: {metadata.category.value}")
        content_parts.append(f"")
        
        # 质量信息
        content_parts.append(f"## 质量评估")
        content_parts.append(f"- **质量等级**: {metadata.quality_grade.value}")
        content_parts.append(f"- **整体评分**: {metadata.quality_metrics.get('overall_score', 0):.2f}/1.0")
        content_parts.append(f"- **清晰度**: {metadata.quality_metrics.get('clarity_score', 0):.2f}/1.0")
        content_parts.append(f"- **人脸差异**: {metadata.quality_metrics.get('face_variance', 0):.2%}")
        content_parts.append(f"- **面料误差**: {metadata.quality_metrics.get('texture_error', 0):.2%}")
        content_parts.append(f"- **存在问题**: {'是' if metadata.has_issues else '否'}")
        if metadata.issue_details:
            content_parts.append(f"- **问题详情**: {metadata.issue_details}")
        content_parts.append(f"")
        
        # 标签与索引
        content_parts.append(f"## 标签与索引")
        content_parts.append(f"- **标签**: {', '.join(metadata.tags)}")
        content_parts.append(f"- **语义描述**: {metadata.semantic_description}")
        content_parts.append(f"- **版权信息**: {metadata.copyright}")
        content_parts.append(f"")
        
        # 生成参数详情
        content_parts.append(f"## 详细生成参数")
        for key, value in metadata.generation_params.items():
            if key not in ["prompt", "negative_prompt", "model_name", "model_version"]:
                content_parts.append(f"- **{key}**: {value}")
        
        content = "\n".join(content_parts)
        
        # 创建知识文档
        return KnowledgeDocument(
            title=f"Banana生图资产 - {metadata.image_id}",
            content=content,
            content_type=ContentType.MARKDOWN,
            source_type=SourceType.CONTENT_OUTPUT,
            source_id=metadata.image_id,
            tags=metadata.tags + [
                "banana_ai",
                "image_generation",
                "asset_management",
                f"avatar:{metadata.avatar_id}",
                f"scene:{metadata.scene}",
                f"quality:{metadata.quality_grade.value}",
            ],
            metadata={
                "image_id": metadata.image_id,
                "avatar_id": metadata.avatar_id,
                "task_id": metadata.task_id,
                "scene": metadata.scene,
                "category": metadata.category.value,
                "dimensions": list(metadata.dimensions),
                "file_size": metadata.file_size,
                "quality_grade": metadata.quality_grade.value,
                "quality_metrics": metadata.quality_metrics,
                "has_issues": metadata.has_issues,
                "issue_details": metadata.issue_details,
                "generation_params": metadata.generation_params,
                "creator": metadata.creator,
                "created_at": metadata.created_at,
                "synced_at": datetime.now().isoformat(),
            }
        )
    
    def search_similar_images(self, query: str, 
                             filter_tags: Optional[List[str]] = None,
                             limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索相似图片
        
        Args:
            query: 搜索查询
            filter_tags: 过滤标签
            limit: 返回结果限制
            
        Returns:
            搜索结果列表
        """
        if not self.notebook_lm or not self.knowledge_base_id:
            logger.warning("记忆系统未就绪，无法搜索")
            return []
        
        try:
            # 搜索知识库
            search_results = self.notebook_lm.search_documents(
                knowledge_base_id=self.knowledge_base_id,
                query=query,
                filter_tags=filter_tags,
                limit=limit
            )
            
            # 转换结果格式
            results = []
            for doc in search_results:
                metadata = doc.get("metadata", {})
                
                result_item = {
                    "document_id": doc.get("id"),
                    "image_id": metadata.get("image_id"),
                    "title": doc.get("title"),
                    "avatar_id": metadata.get("avatar_id"),
                    "scene": metadata.get("scene"),
                    "category": metadata.get("category"),
                    "quality_grade": metadata.get("quality_grade"),
                    "file_path": metadata.get("file_path"),
                    "dimensions": metadata.get("dimensions"),
                    "similarity_score": doc.get("similarity_score", 0),
                    "tags": doc.get("tags", []),
                }
                
                results.append(result_item)
            
            logger.info(f"图片搜索完成: 查询 '{query}', 返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"图片搜索失败: {str(e)}")
            return []
    
    def query_knowledge_base(self, question: str,
                            context: Optional[str] = None,
                            max_results: int = 5) -> Dict[str, Any]:
        """
        查询知识库
        
        Args:
            question: 问题
            context: 上下文
            max_results: 最大结果数
            
        Returns:
            查询结果
        """
        if not self.notebook_lm or not self.knowledge_base_id:
            return {
                "status": "error",
                "error": "记忆系统未就绪",
            }
        
        try:
            result = self.notebook_lm.query_knowledge_base(
                knowledge_base_id=self.knowledge_base_id,
                question=question,
                context=context,
                max_results=max_results,
                include_sources=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"知识库查询失败: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        return {
            **self.stats,
            "system_ready": bool(self.notebook_lm and self.knowledge_base_id),
            "sync_enabled": self.config.notebook_lm_sync_enabled,
            "knowledge_base_id": self.knowledge_base_id,
            "config": {
                "max_processing_delay_ms": self.config.max_processing_delay_ms,
                "max_concurrent": self.config.max_concurrent,
                "batch_size": self.max_batch_size,
            }
        }
    
    def cleanup(self) -> None:
        """清理资源"""
        if self.executor:
            self.executor.shutdown(wait=True)


# 异步处理支持
class AsyncMemorySyncManager:
    """异步记忆同步管理器"""
    
    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG):
        self.config = config
        self.sync_manager = MemorySyncManager(config)
        self.loop = asyncio.new_event_loop()
    
    async def async_sync_image_metadata(self, metadata: ImageMetadata) -> Tuple[bool, Optional[str]]:
        """异步同步单张图片元数据"""
        return await self.loop.run_in_executor(
            None,
            self.sync_manager.sync_image_metadata,
            metadata
        )
    
    async def async_sync_batch(self, metadata_list: List[ImageMetadata]) -> Dict[str, Any]:
        """异步批量同步"""
        return await self.loop.run_in_executor(
            None,
            self.sync_manager.sync_image_metadata_batch,
            metadata_list
        )
    
    async def async_search(self, query: str, 
                          filter_tags: Optional[List[str]] = None,
                          limit: int = 10) -> List[Dict[str, Any]]:
        """异步搜索"""
        return await self.loop.run_in_executor(
            None,
            self.sync_manager.search_similar_images,
            query,
            filter_tags,
            limit
        )
    
    def close(self) -> None:
        """关闭异步管理器"""
        self.sync_manager.cleanup()
        self.loop.close()


# 便捷函数
def sync_image_to_memory(image_path: str,
                        generation_params: Dict[str, Any],
                        avatar_id: str,
                        task_id: str,
                        scene: str,
                        config: Optional[PipelineConfig] = None) -> Tuple[bool, Optional[str], Optional[ImageMetadata]]:
    """
    便捷函数：处理并同步单张图片
    
    Args:
        image_path: 图片路径
        generation_params: 生成参数
        avatar_id: 分身ID
        task_id: 任务ID
        scene: 使用场景
        config: 配置（可选）
    
    Returns:
        (同步是否成功, 文档ID或错误信息, 图片元数据)
    """
    from .image_processor import ImageProcessor
    
    config = config or DEFAULT_CONFIG
    
    # 处理图片
    processor = ImageProcessor(config)
    metadata, warnings = processor.process_image_file(
        image_path=image_path,
        generation_params=generation_params,
        avatar_id=avatar_id,
        task_id=task_id,
        scene=scene,
    )
    
    if not metadata:
        return False, f"图片处理失败: {warnings}", None
    
    # 同步到记忆系统
    sync_manager = MemorySyncManager(config)
    success, result = sync_manager.sync_image_metadata(metadata)
    
    sync_manager.cleanup()
    
    return success, result, metadata


if __name__ == "__main__":
    # 模块测试
    print("记忆同步模块测试")
    
    # 创建测试配置
    config = PipelineConfig(
        base_storage_dir="test_outputs/images",
        temp_processing_dir="test_temp/processing",
        metadata_dir="test_data/metadata",
        notebook_lm_sync_enabled=False,  # 测试时禁用实际同步
    )
    config.ensure_directories()
    
    # 创建测试元数据
    test_metadata = ImageMetadata(
        image_id=generate_image_id("test_avatar"),
        file_name="test_image.png",
        file_path="test_outputs/images/2024-01-01/product_shoot/test_avatar/test_image.png",
        file_size=1024 * 1024,  # 1MB
        dimensions=(2048, 2048),
        format="png",
        prompt="A beautiful product image for testing",
        negative_prompt="blurry, low quality",
        model_name="banana_model",
        model_version="2.1",
        generation_params={
            "seed": 12345,
            "steps": 50,
            "cfg_scale": 7.5,
            "sampler": "euler_a",
        },
        avatar_id="test_avatar_001",
        task_id="test_task_001",
        scene="product_shoot",
        category=AssetCategory.PRODUCT_IMAGE,
        tags=["category:product_image", "scene:product_shoot", "avatar:test_avatar_001", "test"],
        quality_grade=ImageQualityGrade.EXCELLENT,
        quality_metrics={
            "overall_score": 0.92,
            "clarity_score": 0.95,
            "brightness_score": 0.88,
            "contrast_score": 0.85,
            "face_variance": 0.01,
            "texture_error": 0.02,
        },
        has_issues=False,
        issue_details=None,
        creator="SellAI系统",
        created_at=datetime.now().isoformat(),
        copyright="Copyright © 2024 SellAI系统",
        usage_rights={
            "commercial_use": True,
            "modification_allowed": True,
            "attribution_required": False,
            "redistribution_allowed": True,
        },
        semantic_description="这是一张2048x2048分辨率的产品展示图。用于product_shoot场景。生成提示词: A beautiful product image for testing。",
        embedding_vector=None,
    )
    
    # 测试记忆同步管理器
    sync_manager = MemorySyncManager(config)
    
    # 测试文档创建
    if NOTEBOOK_LM_AVAILABLE:
        try:
            document = sync_manager._create_document_from_metadata(test_metadata)
            print(f"文档创建成功:")
            print(f"  标题: {document.title}")
            print(f"  内容长度: {len(document.content)} 字符")
            print(f"  标签: {', '.join(document.tags[:5])}")
        except Exception as e:
            print(f"文档创建失败: {str(e)}")
    
    # 测试统计
    stats = sync_manager.get_stats()
    print(f"\n同步统计:")
    print(f"  系统就绪: {stats['system_ready']}")
    print(f"  同步启用: {stats['sync_enabled']}")
    print(f"  总同步数: {stats['total_synced']}")
    
    sync_manager.cleanup()
    
    print("\n模块测试完成")