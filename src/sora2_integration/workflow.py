"""
Sora2视频生成自动化工作流
实现从产品信息输入到高质量带货视频的全自动流水线
"""

import json
import time
import logging
import uuid
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass, asdict
import threading
from queue import Queue, Empty

from .config import Sora2IntegrationConfig, DEFAULT_CONFIG
from .client import Sora2APIClient, Sora2APIError


@dataclass
class ProductInfo:
    """产品信息"""
    product_id: str
    name: str
    category: str
    description: str
    price: float
    currency: str = "USD"
    image_urls: List[str] = None
    target_audience: str = ""
    key_features: List[str] = None
    brand: str = ""
    
    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []
        if self.key_features is None:
            self.key_features = []


@dataclass
class VideoGenerationTask:
    """视频生成任务"""
    task_id: str
    product_info: ProductInfo
    prompt: str
    status: str  # pending, processing, completed, failed
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    generation_params: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "product_info": {
                "product_id": self.product_info.product_id,
                "name": self.product_info.name,
                "category": self.product_info.category,
                "description": self.product_info.description,
                "price": self.product_info.price,
                "currency": self.product_info.currency,
                "image_urls": self.product_info.image_urls,
                "target_audience": self.product_info.target_audience,
                "key_features": self.product_info.key_features,
                "brand": self.product_info.brand
            },
            "prompt": self.prompt,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "video_id": self.video_id,
            "video_url": self.video_url,
            "error_message": self.error_message,
            "generation_params": self.generation_params
        }


@dataclass
class MaterialLibraryEntry:
    """素材库条目"""
    entry_id: str
    product_id: str
    video_id: str
    video_url: str
    generated_at: float
    prompt_used: str
    metadata: Dict[str, Any]
    tags: List[str] = None
    usage_count: int = 0
    last_used_at: Optional[float] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class VideoGenerationWorkflow:
    """视频生成工作流主类"""
    
    def __init__(self, config: Optional[Sora2IntegrationConfig] = None):
        """
        初始化工作流
        
        Args:
            config: 配置对象
        """
        self.config = config or DEFAULT_CONFIG
        self.client = Sora2APIClient(config)
        
        # 任务队列和状态跟踪
        self.task_queue = Queue()
        self.active_tasks: Dict[str, VideoGenerationTask] = {}
        self.completed_tasks: Dict[str, VideoGenerationTask] = {}
        
        # 素材库
        self.material_library: Dict[str, MaterialLibraryEntry] = {}
        
        # 工作线程
        self.worker_threads = []
        self.running = False
        
        # 日志
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # 初始化素材库目录
        self._init_material_library()
    
    def _init_material_library(self):
        """初始化素材库目录结构"""
        import os
        
        # 创建素材库目录
        lib_dir = "data/material_library"
        os.makedirs(lib_dir, exist_ok=True)
        
        # 创建子目录
        subdirs = ["videos", "metadata", "thumbnails", "exports"]
        for subdir in subdirs:
            os.makedirs(os.path.join(lib_dir, subdir), exist_ok=True)
        
        # 加载现有素材库（如果存在）
        lib_file = os.path.join(lib_dir, "library.json")
        if os.path.exists(lib_file):
            try:
                with open(lib_file, 'r', encoding='utf-8') as f:
                    lib_data = json.load(f)
                
                # 转换为MaterialLibraryEntry对象
                for entry_id, entry_data in lib_data.items():
                    entry = MaterialLibraryEntry(
                        entry_id=entry_id,
                        product_id=entry_data.get("product_id", ""),
                        video_id=entry_data.get("video_id", ""),
                        video_url=entry_data.get("video_url", ""),
                        generated_at=entry_data.get("generated_at", 0),
                        prompt_used=entry_data.get("prompt_used", ""),
                        metadata=entry_data.get("metadata", {}),
                        tags=entry_data.get("tags", []),
                        usage_count=entry_data.get("usage_count", 0),
                        last_used_at=entry_data.get("last_used_at")
                    )
                    self.material_library[entry_id] = entry
                
                self.logger.info(f"已加载 {len(self.material_library)} 个素材库条目")
            except Exception as e:
                self.logger.error(f"加载素材库失败: {str(e)}")
    
    def _save_material_library(self):
        """保存素材库到文件"""
        import os
        
        lib_dir = "data/material_library"
        os.makedirs(lib_dir, exist_ok=True)
        
        lib_file = os.path.join(lib_dir, "library.json")
        
        # 转换为字典
        lib_data = {}
        for entry_id, entry in self.material_library.items():
            lib_data[entry_id] = {
                "product_id": entry.product_id,
                "video_id": entry.video_id,
                "video_url": entry.video_url,
                "generated_at": entry.generated_at,
                "prompt_used": entry.prompt_used,
                "metadata": entry.metadata,
                "tags": entry.tags,
                "usage_count": entry.usage_count,
                "last_used_at": entry.last_used_at
            }
        
        # 保存到文件
        try:
            with open(lib_file, 'w', encoding='utf-8') as f:
                json.dump(lib_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"素材库已保存，共 {len(lib_data)} 个条目")
        except Exception as e:
            self.logger.error(f"保存素材库失败: {str(e)}")
    
    def _generate_prompt(self, product_info: ProductInfo) -> str:
        """
        根据产品信息生成视频提示词
        
        Args:
            product_info: 产品信息
            
        Returns:
            视频生成提示词
        """
        # 基础提示词模板
        template = """Cinematic Ultra HD video, 9:16 portrait aspect ratio, {duration}s duration.

Product: {product_name}
Category: {category}
Key Features: {features}

Scene: {scene_description}

Visual Style: {visual_style}
Camera Movement: {camera_movement}
Lighting: {lighting}

Target Audience: {target_audience}
Brand Voice: {brand_voice}

Additional Notes: Must showcase product in realistic usage scenario, with natural lighting and professional composition."""
        
        # 根据产品类别定制场景
        category_scenes = {
            "fashion": "Stylish model wearing the product in an urban environment, showcasing fit and texture",
            "electronics": "Product in use with interactive elements, highlighting features and user experience",
            "home": "Product in a well-decorated home setting, showing practical application and aesthetics",
            "beauty": "Close-up shots demonstrating application and results, with focus on texture and finish",
            "sports": "Athlete using product during activity, showing performance and durability"
        }
        
        # 默认场景
        scene = category_scenes.get(product_info.category.lower(), 
                                   f"Professional showcase of {product_info.name} in appropriate setting")
        
        # 构建特征字符串
        features = ", ".join(product_info.key_features) if product_info.key_features else "High quality, premium materials"
        
        # 填充模板
        prompt = template.format(
            duration=self.config.output_spec.duration_seconds,
            product_name=product_info.name,
            category=product_info.category,
            features=features,
            scene_description=scene,
            visual_style="Cinematic, professional, high-end commercial",
            camera_movement="Smooth camera movements, dynamic angles, professional framing",
            lighting="Natural lighting, cinematic lighting setup, professional studio quality",
            target_audience=product_info.target_audience or "Young professionals, fashion-conscious consumers",
            brand_voice=product_info.brand or "Modern, sophisticated, trustworthy"
        )
        
        return prompt
    
    def _create_generation_params(self, product_info: ProductInfo) -> Dict[str, Any]:
        """
        创建视频生成参数
        
        Args:
            product_info: 产品信息
            
        Returns:
            生成参数
        """
        params = {
            "model": self.config.default_model.value,
            "seconds": str(self.config.output_spec.duration_seconds),
            "size": self.config.output_spec.size_str,
            "aspect_ratio": self.config.output_spec.aspect_ratio,
            "quality": self.config.output_spec.quality,
            "orientation": self.config.output_spec.orientation
        }
        
        # 如果有产品图片，添加参考图片
        if product_info.image_urls:
            params["image"] = product_info.image_urls[0]
        
        return params
    
    def submit_product(self, product_info: ProductInfo) -> str:
        """
        提交产品信息，创建视频生成任务
        
        Args:
            product_info: 产品信息
            
        Returns:
            任务ID
        """
        # 生成任务ID
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # 生成提示词
        prompt = self._generate_prompt(product_info)
        
        # 创建任务
        task = VideoGenerationTask(
            task_id=task_id,
            product_info=product_info,
            prompt=prompt,
            status="pending",
            created_at=time.time(),
            generation_params=self._create_generation_params(product_info)
        )
        
        # 添加到队列
        self.task_queue.put(task)
        self.active_tasks[task_id] = task
        
        self.logger.info(f"视频生成任务已提交: {task_id} - {product_info.name}")
        self.logger.debug(f"生成提示词: {prompt[:100]}...")
        
        return task_id
    
    def _worker_loop(self, worker_id: int):
        """
        工作线程主循环
        
        Args:
            worker_id: 工作线程ID
        """
        self.logger.debug(f"工作线程 {worker_id} 启动")
        
        while self.running:
            try:
                # 从队列获取任务（阻塞，可超时）
                task = self.task_queue.get(timeout=1.0)
                
                # 处理任务
                self._process_task(task, worker_id)
                
                # 标记任务完成
                self.task_queue.task_done()
                
            except Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                self.logger.error(f"工作线程 {worker_id} 异常: {str(e)}")
        
        self.logger.debug(f"工作线程 {worker_id} 停止")
    
    def _process_task(self, task: VideoGenerationTask, worker_id: int):
        """
        处理单个视频生成任务
        
        Args:
            task: 任务对象
            worker_id: 工作线程ID
        """
        task_id = task.task_id
        
        try:
            # 更新任务状态
            task.status = "processing"
            task.started_at = time.time()
            self.active_tasks[task_id] = task
            
            self.logger.info(f"开始处理任务 {task_id} (工作线程 {worker_id})")
            
            # 调用Sora2 API生成视频
            response = self.client.create_video(
                prompt=task.prompt,
                custom_params=task.generation_params
            )
            
            # 提取视频ID和URL
            video_id = response.get("id")
            video_url = response.get("video_url")
            
            if not video_id:
                raise ValueError("API响应中缺少视频ID")
            
            # 更新任务信息
            task.video_id = video_id
            task.video_url = video_url
            task.status = "completed"
            task.completed_at = time.time()
            
            # 添加到素材库
            self._add_to_material_library(task)
            
            # 移动任务到已完成
            self.completed_tasks[task_id] = task
            del self.active_tasks[task_id]
            
            self.logger.info(f"任务完成: {task_id} - 视频ID: {video_id}")
            
        except Exception as e:
            # 处理失败
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = time.time()
            
            # 移动任务到已完成（失败）
            self.completed_tasks[task_id] = task
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            self.logger.error(f"任务失败: {task_id} - 错误: {str(e)}")
    
    def _add_to_material_library(self, task: VideoGenerationTask):
        """
        将生成的视频添加到素材库
        
        Args:
            task: 已完成的任务
        """
        entry_id = f"entry_{uuid.uuid4().hex[:8]}"
        
        entry = MaterialLibraryEntry(
            entry_id=entry_id,
            product_id=task.product_info.product_id,
            video_id=task.video_id,
            video_url=task.video_url,
            generated_at=task.completed_at,
            prompt_used=task.prompt,
            metadata={
                "product_info": asdict(task.product_info),
                "generation_params": task.generation_params,
                "task_info": {
                    "task_id": task.task_id,
                    "created_at": task.created_at,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at
                }
            },
            tags=[
                task.product_info.category,
                "auto_generated",
                f"duration_{self.config.output_spec.duration_seconds}s"
            ]
        )
        
        self.material_library[entry_id] = entry
        
        # 保存素材库
        self._save_material_library()
        
        self.logger.debug(f"已添加到素材库: {entry_id}")
    
    def start_workers(self, num_workers: Optional[int] = None):
        """
        启动工作线程
        
        Args:
            num_workers: 工作线程数量，如为None则使用配置
        """
        if self.running:
            self.logger.warning("工作线程已在运行")
            return
        
        # 确定工作线程数量
        if num_workers is None:
            num_workers = min(self.config.workflow.max_concurrent_jobs, 5)
        
        self.running = True
        
        # 创建工作线程
        for i in range(num_workers):
            thread = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                name=f"Sora2Worker-{i}",
                daemon=True
            )
            thread.start()
            self.worker_threads.append(thread)
        
        self.logger.info(f"已启动 {num_workers} 个工作线程")
    
    def stop_workers(self):
        """停止工作线程"""
        if not self.running:
            return
        
        self.running = False
        
        # 等待工作线程结束
        for thread in self.worker_threads:
            thread.join(timeout=5.0)
        
        self.worker_threads.clear()
        self.logger.info("工作线程已停止")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字典，如任务不存在则返回None
        """
        task = None
        
        # 查找任务
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
        elif task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
        
        if task:
            return task.to_dict()
        
        return None
    
    def list_active_tasks(self) -> List[Dict]:
        """列出所有活动任务"""
        return [task.to_dict() for task in self.active_tasks.values()]
    
    def list_completed_tasks(self) -> List[Dict]:
        """列出所有已完成任务"""
        return [task.to_dict() for task in self.completed_tasks.values()]
    
    def search_material_library(self, query: Optional[str] = None, 
                               category: Optional[str] = None,
                               tags: Optional[List[str]] = None) -> List[Dict]:
        """
        搜索素材库
        
        Args:
            query: 搜索关键词
            category: 产品类别
            tags: 标签列表
            
        Returns:
            匹配的素材库条目
        """
        results = []
        
        for entry in self.material_library.values():
            match = True
            
            # 按关键词搜索
            if query:
                query_lower = query.lower()
                text_to_search = f"{entry.metadata.get('product_info', {}).get('name', '')} "
                text_to_search += f"{entry.metadata.get('product_info', {}).get('description', '')} "
                text_to_search += f"{entry.prompt_used}"
                
                if query_lower not in text_to_search.lower():
                    match = False
            
            # 按类别筛选
            if category and match:
                entry_category = entry.metadata.get('product_info', {}).get('category', '').lower()
                if category.lower() != entry_category:
                    match = False
            
            # 按标签筛选
            if tags and match:
                entry_tags = set(tag.lower() for tag in entry.tags)
                search_tags = set(tag.lower() for tag in tags)
                if not search_tags.issubset(entry_tags):
                    match = False
            
            if match:
                results.append({
                    "entry_id": entry.entry_id,
                    "product_id": entry.product_id,
                    "video_id": entry.video_id,
                    "video_url": entry.video_url,
                    "generated_at": entry.generated_at,
                    "prompt_used": entry.prompt_used[:200] + "..." if len(entry.prompt_used) > 200 else entry.prompt_used,
                    "tags": entry.tags,
                    "usage_count": entry.usage_count,
                    "last_used_at": entry.last_used_at
                })
        
        return results
    
    def get_material_entry(self, entry_id: str) -> Optional[MaterialLibraryEntry]:
        """
        获取素材库条目
        
        Args:
            entry_id: 条目ID
            
        Returns:
            素材库条目对象，如不存在则返回None
        """
        return self.material_library.get(entry_id)
    
    def mark_material_used(self, entry_id: str):
        """
        标记素材已使用
        
        Args:
            entry_id: 条目ID
        """
        if entry_id in self.material_library:
            entry = self.material_library[entry_id]
            entry.usage_count += 1
            entry.last_used_at = time.time()
            
            # 更新素材库文件
            self._save_material_library()
    
    def generate_workflow_report(self) -> Dict[str, Any]:
        """
        生成工作流报告
        
        Returns:
            工作流状态报告
        """
        report = {
            "timestamp": time.time(),
            "workflow_status": {
                "running": self.running,
                "active_workers": len(self.worker_threads),
                "queue_size": self.task_queue.qsize(),
                "active_tasks": len(self.active_tasks),
                "completed_tasks": len(self.completed_tasks),
                "material_library_entries": len(self.material_library)
            },
            "task_summary": {
                "total_submitted": len(self.active_tasks) + len(self.completed_tasks),
                "active_by_status": {},
                "completed_by_status": {}
            },
            "performance_metrics": {
                "average_processing_time": self._calculate_average_processing_time(),
                "success_rate": self._calculate_success_rate()
            },
            "configuration": self.config.to_dict()
        }
        
        # 按状态统计任务
        for task in self.active_tasks.values():
            status = task.status
            report["task_summary"]["active_by_status"][status] = \
                report["task_summary"]["active_by_status"].get(status, 0) + 1
        
        for task in self.completed_tasks.values():
            status = task.status
            report["task_summary"]["completed_by_status"][status] = \
                report["task_summary"]["completed_by_status"].get(status, 0) + 1
        
        return report
    
    def _calculate_average_processing_time(self) -> Optional[float]:
        """计算平均处理时间"""
        completed_tasks = [t for t in self.completed_tasks.values() 
                          if t.status == "completed" and t.started_at and t.completed_at]
        
        if not completed_tasks:
            return None
        
        total_time = sum(t.completed_at - t.started_at for t in completed_tasks)
        return total_time / len(completed_tasks)
    
    def _calculate_success_rate(self) -> Optional[float]:
        """计算成功率"""
        completed_count = len(self.completed_tasks)
        if completed_count == 0:
            return None
        
        successful_count = sum(1 for t in self.completed_tasks.values() 
                              if t.status == "completed")
        
        return successful_count / completed_count
    
    def run_demo(self, num_products: int = 3):
        """
        运行演示工作流
        
        Args:
            num_products: 要生成的产品数量
        """
        self.logger.info(f"启动演示工作流，生成 {num_products} 个产品视频")
        
        # 确保工作线程运行
        if not self.running:
            self.start_workers(2)
        
        # 创建示例产品
        example_products = [
            ProductInfo(
                product_id="prod_001",
                name="Classic Denim Jacket",
                category="Fashion",
                description="750g premium denim jacket with vintage wash and modern fit",
                price=89.99,
                image_urls=["https://example.com/denim_jacket.jpg"],
                key_features=["Premium cotton denim", "Vintage wash finish", "Modern slim fit", 
                            "Metal button closure", "Multiple pockets"],
                target_audience="Fashion-conscious young adults",
                brand="Urban Denim Co."
            ),
            ProductInfo(
                product_id="prod_002",
                name="Wireless Noise-Cancelling Headphones",
                category="Electronics",
                description="High-fidelity audio with adaptive noise cancellation",
                price=249.99,
                image_urls=["https://example.com/headphones.jpg"],
                key_features=["Adaptive noise cancellation", "40mm drivers", "30-hour battery", 
                            "Bluetooth 5.3", "Voice assistant support"],
                target_audience="Audiophiles and commuters",
                brand="AudioTech Pro"
            ),
            ProductInfo(
                product_id="prod_003",
                name="Organic Matcha Green Tea",
                category="Food",
                description="Ceremonial grade matcha powder from Uji, Japan",
                price=34.99,
                image_urls=["https://example.com/matcha.jpg"],
                key_features=["Ceremonial grade", "Stone-ground", "Organic certified", 
                            "Rich umami flavor", "Antioxidant rich"],
                target_audience="Health-conscious consumers",
                brand="Zen Tea Gardens"
            )
        ]
        
        # 限制数量
        products_to_process = example_products[:num_products]
        
        # 提交任务
        task_ids = []
        for product in products_to_process:
            task_id = self.submit_product(product)
            task_ids.append(task_id)
        
        self.logger.info(f"已提交 {len(task_ids)} 个任务: {', '.join(task_ids)}")
        
        # 等待任务完成（简化演示）
        import time
        max_wait = 30  # 最大等待秒数
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            active_count = len(self.active_tasks)
            if active_count == 0:
                break
            
            self.logger.info(f"等待任务完成... 剩余 {active_count} 个活动任务")
            time.sleep(2)
        
        # 生成报告
        report = self.generate_workflow_report()
        
        # 输出摘要
        self.logger.info("演示工作流完成")
        self.logger.info(f"总任务数: {report['task_summary']['total_submitted']}")
        self.logger.info(f"成功任务: {report['task_summary']['completed_by_status'].get('completed', 0)}")
        self.logger.info(f"失败任务: {report['task_summary']['completed_by_status'].get('failed', 0)}")
        
        return report


# 便捷函数
def create_default_workflow() -> VideoGenerationWorkflow:
    """创建默认工作流实例"""
    return VideoGenerationWorkflow()

def run_quick_test() -> Dict:
    """运行快速测试"""
    workflow = VideoGenerationWorkflow()
    
    # 创建示例产品
    test_product = ProductInfo(
        product_id="test_001",
        name="Test Product",
        category="Test",
        description="A test product for Sora2 integration",
        price=19.99,
        key_features=["Test feature 1", "Test feature 2"]
    )
    
    # 提交任务
    task_id = workflow.submit_product(test_product)
    
    # 启动单个工作线程处理
    workflow.start_workers(1)
    
    # 等待一小段时间
    import time
    time.sleep(5)
    
    # 停止工作线程
    workflow.stop_workers()
    
    # 获取状态
    status = workflow.get_task_status(task_id)
    
    return {
        "task_id": task_id,
        "status": status,
        "workflow_report": workflow.generate_workflow_report()
    }