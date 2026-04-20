#!/usr/bin/env python3
"""
Banana生图内核全局素材库流水线主模块

整合图片处理与记忆同步，实现自动化归档流水线，
确保所有生成图片自动存入长期记忆。
"""

import os
import json
import time
import threading
import queue
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
import logging
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import (
    ImageMetadata, AssetCategory, ImageQualityGrade,
    PipelineConfig, DEFAULT_CONFIG, generate_image_id,
    validate_metadata, MetadataSchema
)
from .image_processor import ImageProcessor, BatchImageProcessor
from .memory_sync import MemorySyncManager, AsyncMemorySyncManager

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class ProcessingJob:
    """处理任务"""
    job_id: str
    image_path: str
    generation_params: Dict[str, Any]
    avatar_id: str
    task_id: str
    scene: str
    submitted_at: str
    priority: int = 0  # 0=普通，1=高优先级
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessingResult:
    """处理结果"""
    job_id: str
    image_id: Optional[str]
    metadata: Optional[ImageMetadata]
    success: bool
    processing_time_ms: float
    warnings: List[str]
    errors: List[str]
    memory_sync_success: Optional[bool] = None
    memory_sync_result: Optional[str] = None
    memory_sync_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data['metadata']:
            data['metadata'] = data['metadata'].to_dict()
        return data


class AssetPipeline:
    """资产流水线"""
    
    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG):
        self.config = config
        config.ensure_directories()
        
        # 初始化组件
        self.image_processor = ImageProcessor(config)
        self.batch_processor = BatchImageProcessor(config)
        self.memory_sync = MemorySyncManager(config)
        
        # 任务队列
        self.job_queue = queue.PriorityQueue()  # (priority, timestamp, job)
        self.results_queue = queue.Queue()
        
        # 状态跟踪
        self.stats = {
            "jobs_submitted": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "avg_processing_time_ms": 0,
            "memory_sync_success_rate": 0,
            "last_processed_at": None,
            "pipeline_status": "idle",  # idle, running, paused, error
        }
        
        # 性能监控
        self.processing_times = []
        self.memory_sync_times = []
        
        # 工作线程
        self.worker_threads = []
        self.is_running = False
        self.thread_pool = ThreadPoolExecutor(max_workers=config.max_concurrent)
        
        # 错误处理
        self.error_handlers = []
        self.retry_queue = queue.Queue()
        
        logger.info("资产流水线初始化完成")
    
    def start(self) -> bool:
        """启动流水线"""
        if self.is_running:
            logger.warning("流水线已在运行中")
            return False
        
        try:
            self.is_running = True
            self.stats["pipeline_status"] = "running"
            
            # 启动工作线程
            for i in range(self.config.max_concurrent):
                thread = threading.Thread(
                    target=self._worker_loop,
                    name=f"PipelineWorker-{i}",
                    daemon=True
                )
                thread.start()
                self.worker_threads.append(thread)
            
            # 启动重试线程
            retry_thread = threading.Thread(
                target=self._retry_loop,
                name="PipelineRetryWorker",
                daemon=True
            )
            retry_thread.start()
            self.worker_threads.append(retry_thread)
            
            logger.info("资产流水线已启动")
            return True
            
        except Exception as e:
            logger.error(f"流水线启动失败: {str(e)}")
            self.stats["pipeline_status"] = "error"
            return False
    
    def stop(self) -> bool:
        """停止流水线"""
        if not self.is_running:
            logger.warning("流水线未运行")
            return False
        
        try:
            self.is_running = False
            self.stats["pipeline_status"] = "idle"
            
            # 等待工作线程结束
            for thread in self.worker_threads:
                if thread.is_alive():
                    thread.join(timeout=5)
            
            # 清理线程池
            self.thread_pool.shutdown(wait=True)
            
            # 清理内存同步
            self.memory_sync.cleanup()
            
            logger.info("资产流水线已停止")
            return True
            
        except Exception as e:
            logger.error(f"流水线停止失败: {str(e)}")
            return False
    
    def submit_job(self, image_path: str,
                  generation_params: Dict[str, Any],
                  avatar_id: str,
                  task_id: str,
                  scene: str,
                  priority: int = 0) -> str:
        """
        提交处理任务
        
        Returns:
            任务ID
        """
        # 验证文件存在性
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 生成任务ID
        job_id = f"job_{generate_image_id(avatar_id)}"
        
        # 创建任务
        job = ProcessingJob(
            job_id=job_id,
            image_path=image_path,
            generation_params=generation_params,
            avatar_id=avatar_id,
            task_id=task_id,
            scene=scene,
            submitted_at=datetime.now().isoformat(),
            priority=priority,
        )
        
        # 加入队列（优先级队列）
        timestamp = time.time()
        self.job_queue.put((priority, timestamp, job))
        
        # 更新统计
        self.stats["jobs_submitted"] += 1
        
        logger.info(f"任务提交成功: {job_id}, 优先级: {priority}")
        return job_id
    
    def submit_batch(self, jobs: List[Dict[str, Any]]) -> List[str]:
        """
        批量提交任务
        
        Args:
            jobs: 任务列表，每个元素包含:
                - image_path: 图片路径
                - generation_params: 生成参数
                - avatar_id: 分身ID
                - task_id: 任务ID
                - scene: 使用场景
                - priority: 优先级（可选）
        
        Returns:
            任务ID列表
        """
        job_ids = []
        
        for job_data in jobs:
            priority = job_data.get("priority", 0)
            
            job_id = self.submit_job(
                image_path=job_data["image_path"],
                generation_params=job_data["generation_params"],
                avatar_id=job_data["avatar_id"],
                task_id=job_data["task_id"],
                scene=job_data["scene"],
                priority=priority,
            )
            
            job_ids.append(job_id)
        
        logger.info(f"批量提交完成: {len(job_ids)} 个任务")
        return job_ids
    
    def get_result(self, job_id: str, timeout: Optional[float] = None) -> Optional[ProcessingResult]:
        """获取任务结果"""
        # 检查是否有匹配的结果
        results = self._get_all_results()
        
        for result in results:
            if result.job_id == job_id:
                return result
        
        return None
    
    def get_all_results(self) -> List[ProcessingResult]:
        """获取所有结果"""
        return self._get_all_results()
    
    def _get_all_results(self) -> List[ProcessingResult]:
        """从结果队列获取所有结果"""
        results = []
        
        while not self.results_queue.empty():
            try:
                result = self.results_queue.get_nowait()
                results.append(result)
            except queue.Empty:
                break
        
        return results
    
    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self.is_running:
            try:
                # 获取任务（带超时）
                try:
                    priority, timestamp, job = self.job_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 处理任务
                result = self._process_job(job)
                
                # 结果入队
                self.results_queue.put(result)
                
                # 更新统计
                self._update_stats(result)
                
                # 标记任务完成
                self.job_queue.task_done()
                
            except Exception as e:
                logger.error(f"工作线程异常: {str(e)}", exc_info=True)
                time.sleep(1)  # 避免CPU忙等待
    
    def _retry_loop(self) -> None:
        """重试线程循环"""
        while self.is_running:
            try:
                # 获取重试任务
                try:
                    retry_job = self.retry_queue.get(timeout=5.0)
                except queue.Empty:
                    continue
                
                # 检查重试次数
                retry_count = getattr(retry_job, 'retry_count', 0)
                if retry_count >= 3:  # 最多重试3次
                    logger.warning(f"任务重试次数超限: {retry_job.job_id}")
                    continue
                
                # 等待一段时间后重试
                time.sleep(2 ** retry_count)  # 指数退避
                
                # 更新重试计数
                retry_job.retry_count = retry_count + 1
                
                # 重新加入处理队列
                timestamp = time.time()
                self.job_queue.put((retry_job.priority + 1, timestamp, retry_job))
                
                logger.info(f"任务重新排队: {retry_job.job_id}, 重试次数: {retry_job.retry_count}")
                
            except Exception as e:
                logger.error(f"重试线程异常: {str(e)}", exc_info=True)
                time.sleep(5)
    
    def _process_job(self, job: ProcessingJob) -> ProcessingResult:
        """处理单个任务"""
        start_time = time.time()
        processing_result = None
        memory_sync_success = None
        memory_sync_result = None
        memory_sync_time = None
        
        try:
            # 步骤1: 图片处理
            metadata, warnings = self.image_processor.process_image_file(
                image_path=job.image_path,
                generation_params=job.generation_params,
                avatar_id=job.avatar_id,
                task_id=job.task_id,
                scene=job.scene,
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            if not metadata:
                # 处理失败
                return ProcessingResult(
                    job_id=job.job_id,
                    image_id=None,
                    metadata=None,
                    success=False,
                    processing_time_ms=processing_time,
                    warnings=[],
                    errors=warnings,
                )
            
            # 步骤2: 记忆同步
            memory_start = time.time()
            sync_success, sync_result = self.memory_sync.sync_image_metadata(metadata)
            memory_sync_time = (time.time() - memory_start) * 1000
            
            # 更新结果
            processing_result = ProcessingResult(
                job_id=job.job_id,
                image_id=metadata.image_id,
                metadata=metadata,
                success=True,
                processing_time_ms=processing_time,
                warnings=warnings,
                errors=[],
                memory_sync_success=sync_success,
                memory_sync_result=sync_result,
                memory_sync_time_ms=memory_sync_time,
            )
            
            # 检查性能
            total_time = processing_time + (memory_sync_time or 0)
            if total_time > self.config.max_processing_delay_ms:
                logger.warning(f"任务处理延迟 {total_time:.0f}ms 超过限制 {self.config.max_processing_delay_ms}ms: {job.job_id}")
            
            return processing_result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"任务处理异常: {job.job_id}, 错误: {str(e)}", exc_info=True)
            
            # 加入重试队列（除非是文件不存在等不可恢复错误）
            if isinstance(e, FileNotFoundError):
                error_type = "fatal"
            else:
                error_type = "retryable"
                self.retry_queue.put(job)
            
            return ProcessingResult(
                job_id=job.job_id,
                image_id=None,
                metadata=None,
                success=False,
                processing_time_ms=processing_time,
                warnings=[],
                errors=[f"{error_type}: {str(e)}"],
                memory_sync_success=None,
                memory_sync_result=None,
                memory_sync_time_ms=None,
            )
    
    def _update_stats(self, result: ProcessingResult) -> None:
        """更新统计信息"""
        self.stats["jobs_completed"] += 1
        
        if not result.success:
            self.stats["jobs_failed"] += 1
        
        # 记录处理时间
        self.processing_times.append(result.processing_time_ms)
        
        # 计算平均处理时间（滑动窗口，最近100个任务）
        if len(self.processing_times) > 100:
            self.processing_times = self.processing_times[-100:]
        
        if self.processing_times:
            self.stats["avg_processing_time_ms"] = sum(self.processing_times) / len(self.processing_times)
        
        # 记录记忆同步时间
        if result.memory_sync_time_ms is not None:
            self.memory_sync_times.append(result.memory_sync_time_ms)
            
            if len(self.memory_sync_times) > 100:
                self.memory_sync_times = self.memory_sync_times[-100:]
        
        # 计算记忆同步成功率
        if result.memory_sync_success is not None:
            recent_results = [r for r in self._get_all_results() 
                             if r.memory_sync_success is not None][-50:]
            
            if recent_results:
                success_count = sum(1 for r in recent_results if r.memory_sync_success)
                self.stats["memory_sync_success_rate"] = success_count / len(recent_results) * 100
        
        # 更新最后处理时间
        self.stats["last_processed_at"] = datetime.now().isoformat()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取流水线统计信息"""
        return {
            **self.stats,
            "queue_size": self.job_queue.qsize(),
            "results_count": self.results_queue.qsize(),
            "retry_queue_size": self.retry_queue.qsize(),
            "config": {
                "max_processing_delay_ms": self.config.max_processing_delay_ms,
                "max_concurrent": self.config.max_concurrent,
                "batch_size": self.config.batch_size,
            }
        }
    
    def register_error_handler(self, handler: Callable[[ProcessingJob, Exception], None]) -> None:
        """注册错误处理器"""
        self.error_handlers.append(handler)
    
    def clear_queue(self) -> int:
        """清空任务队列"""
        count = 0
        
        while not self.job_queue.empty():
            try:
                self.job_queue.get_nowait()
                self.job_queue.task_done()
                count += 1
            except queue.Empty:
                break
        
        logger.info(f"已清空 {count} 个待处理任务")
        return count


class AsyncAssetPipeline:
    """异步资产流水线"""
    
    def __init__(self, config: PipelineConfig = DEFAULT_CONFIG):
        self.config = config
        config.ensure_directories()
        
        # 初始化异步组件
        self.async_memory_sync = AsyncMemorySyncManager(config)
        
        # 异步任务队列
        self.job_queue = asyncio.Queue()
        self.results_queue = asyncio.Queue()
        
        # 状态
        self.is_running = False
        self.worker_tasks = []
        
        logger.info("异步资产流水线初始化完成")
    
    async def start(self) -> bool:
        """启动异步流水线"""
        if self.is_running:
            return False
        
        try:
            self.is_running = True
            
            # 启动工作协程
            for i in range(self.config.max_concurrent):
                task = asyncio.create_task(
                    self._async_worker_loop(),
                    name=f"AsyncPipelineWorker-{i}"
                )
                self.worker_tasks.append(task)
            
            logger.info("异步资产流水线已启动")
            return True
            
        except Exception as e:
            logger.error(f"异步流水线启动失败: {str(e)}")
            return False
    
    async def stop(self) -> bool:
        """停止异步流水线"""
        if not self.is_running:
            return False
        
        try:
            self.is_running = False
            
            # 等待工作协程结束
            for task in self.worker_tasks:
                if not task.done():
                    task.cancel()
            
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            
            # 关闭异步内存同步
            self.async_memory_sync.close()
            
            logger.info("异步资产流水线已停止")
            return True
            
        except Exception as e:
            logger.error(f"异步流水线停止失败: {str(e)}")
            return False
    
    async def submit_job_async(self, job: ProcessingJob) -> str:
        """异步提交任务"""
        await self.job_queue.put(job)
        return job.job_id
    
    async def _async_worker_loop(self) -> None:
        """异步工作协程循环"""
        while self.is_running:
            try:
                # 获取任务
                job = await asyncio.wait_for(self.job_queue.get(), timeout=1.0)
                
                # 处理任务
                result = await self._async_process_job(job)
                
                # 结果入队
                await self.results_queue.put(result)
                
                # 标记任务完成
                self.job_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"异步工作协程异常: {str(e)}", exc_info=True)
                await asyncio.sleep(1)
    
    async def _async_process_job(self, job: ProcessingJob) -> ProcessingResult:
        """异步处理单个任务"""
        from .image_processor import ImageProcessor
        
        start_time = time.time()
        
        try:
            # 图片处理（同步，在线程池中运行）
            loop = asyncio.get_event_loop()
            processor = ImageProcessor(self.config)
            
            metadata, warnings = await loop.run_in_executor(
                None,
                lambda: processor.process_image_file(
                    image_path=job.image_path,
                    generation_params=job.generation_params,
                    avatar_id=job.avatar_id,
                    task_id=job.task_id,
                    scene=job.scene,
                )
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            if not metadata:
                return ProcessingResult(
                    job_id=job.job_id,
                    image_id=None,
                    metadata=None,
                    success=False,
                    processing_time_ms=processing_time,
                    warnings=[],
                    errors=warnings,
                )
            
            # 异步记忆同步
            memory_start = time.time()
            sync_success, sync_result = await self.async_memory_sync.async_sync_image_metadata(metadata)
            memory_sync_time = (time.time() - memory_start) * 1000
            
            total_time = processing_time + memory_sync_time
            if total_time > self.config.max_processing_delay_ms:
                logger.warning(f"异步任务处理延迟 {total_time:.0f}ms 超过限制: {job.job_id}")
            
            return ProcessingResult(
                job_id=job.job_id,
                image_id=metadata.image_id,
                metadata=metadata,
                success=True,
                processing_time_ms=processing_time,
                warnings=warnings,
                errors=[],
                memory_sync_success=sync_success,
                memory_sync_result=sync_result,
                memory_sync_time_ms=memory_sync_time,
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"异步任务处理异常: {job.job_id}, 错误: {str(e)}")
            
            return ProcessingResult(
                job_id=job.job_id,
                image_id=None,
                metadata=None,
                success=False,
                processing_time_ms=processing_time,
                warnings=[],
                errors=[str(e)],
                memory_sync_success=None,
                memory_sync_result=None,
                memory_sync_time_ms=None,
            )


# 全局流水线实例
_global_pipeline = None
_global_async_pipeline = None


def get_global_pipeline() -> AssetPipeline:
    """获取全局流水线实例"""
    global _global_pipeline
    if _global_pipeline is None:
        _global_pipeline = AssetPipeline()
    return _global_pipeline


def get_global_async_pipeline() -> AsyncAssetPipeline:
    """获取全局异步流水线实例"""
    global _global_async_pipeline
    if _global_async_pipeline is None:
        _global_async_pipeline = AsyncAssetPipeline()
    return _global_async_pipeline


def process_and_sync_image(image_path: str,
                          generation_params: Dict[str, Any],
                          avatar_id: str,
                          task_id: str,
                          scene: str,
                          use_async: bool = False) -> Tuple[bool, Optional[str], Optional[ImageMetadata]]:
    """
    便捷函数：处理并同步单张图片
    
    Args:
        use_async: 是否使用异步流水线
    
    Returns:
        (成功, 结果信息, 元数据)
    """
    if use_async:
        pipeline = get_global_async_pipeline()
        
        # 创建任务
        job = ProcessingJob(
            job_id=f"quick_{generate_image_id(avatar_id)}",
            image_path=image_path,
            generation_params=generation_params,
            avatar_id=avatar_id,
            task_id=task_id,
            scene=scene,
            submitted_at=datetime.now().isoformat(),
        )
        
        # 异步处理
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 提交并等待结果
            loop.run_until_complete(pipeline.submit_job_async(job))
            
            # 等待结果（简化实现，实际应更复杂）
            time.sleep(0.5)
            
            # 获取结果（简化）
            result = None
            while not pipeline.results_queue.empty():
                result = loop.run_until_complete(pipeline.results_queue.get())
                if result.job_id == job.job_id:
                    break
            
            if result and result.success:
                return True, f"同步成功，文档ID: {result.memory_sync_result}", result.metadata
            else:
                return False, f"处理失败: {result.errors if result else '未知错误'}", None
                
        finally:
            loop.close()
    
    else:
        # 使用同步流水线
        pipeline = get_global_pipeline()
        job_id = pipeline.submit_job(
            image_path=image_path,
            generation_params=generation_params,
            avatar_id=avatar_id,
            task_id=task_id,
            scene=scene,
        )
        
        # 等待处理（简化）
        for _ in range(50):  # 最多等待5秒
            result = pipeline.get_result(job_id)
            if result is not None:
                break
            time.sleep(0.1)
        
        if result and result.success:
            return True, f"同步成功，文档ID: {result.memory_sync_result}", result.metadata
        else:
            return False, f"处理失败: {result.errors if result else '任务未完成'}", None


if __name__ == "__main__":
    # 模块测试
    print("流水线主模块测试")
    
    # 创建测试配置
    config = PipelineConfig(
        base_storage_dir="test_outputs/images",
        temp_processing_dir="test_temp/processing",
        metadata_dir="test_data/metadata",
        notebook_lm_sync_enabled=False,
    )
    
    # 创建测试图片
    test_image_path = os.path.join(config.temp_processing_dir, "pipeline_test.png")
    os.makedirs(config.temp_processing_dir, exist_ok=True)
    
    try:
        if IMAGE_LIB_AVAILABLE:
            from PIL import ImageDraw
            img = Image.new('RGB', (512, 512), color='white')
            d = ImageDraw.Draw(img)
            d.text((10, 10), "Pipeline Test", fill='black')
            img.save(test_image_path)
            print(f"测试图片已创建: {test_image_path}")
    except Exception as e:
        print(f"创建测试图片失败: {str(e)}")
        test_image_path = None
    
    if test_image_path and os.path.exists(test_image_path):
        # 测试同步流水线
        pipeline = AssetPipeline(config)
        
        # 提交任务
        test_params = {
            "prompt": "Pipeline test image",
            "negative_prompt": "blurry",
            "model_name": "test_model",
            "model_version": "1.0",
        }
        
        job_id = pipeline.submit_job(
            image_path=test_image_path,
            generation_params=test_params,
            avatar_id="test_avatar",
            task_id="test_task",
            scene="test_scene",
        )
        
        print(f"任务提交成功: {job_id}")
        
        # 启动流水线
        pipeline.start()
        
        # 等待处理
        time.sleep(2)
        
        # 获取结果
        result = pipeline.get_result(job_id)
        
        if result:
            print(f"\n处理结果:")
            print(f"  成功: {result.success}")
            print(f"  图片ID: {result.image_id}")
            print(f"  处理时间: {result.processing_time_ms:.0f}ms")
            
            if result.success and result.metadata:
                print(f"  分类: {result.metadata.category.value}")
                print(f"  质量等级: {result.metadata.quality_grade.value}")
        
        # 获取统计
        stats = pipeline.get_stats()
        print(f"\n流水线统计:")
        print(f"  提交任务: {stats['jobs_submitted']}")
        print(f"  完成任务: {stats['jobs_completed']}")
        print(f"  平均处理时间: {stats['avg_processing_time_ms']:.0f}ms")
        
        # 停止流水线
        pipeline.stop()
    
    print("\n模块测试完成")