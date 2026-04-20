#!/usr/bin/env python3
"""
智能调度器核心模块
实现无上限并行处理、动态资源分配、负载均衡、容错处理四大核心能力
"""

import json
import time
import logging
import sqlite3
import threading
import heapq
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from enum import Enum
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
import random
import math

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - INTELLIGENT-SCHEDULER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskType(Enum):
    """任务类型枚举"""
    DATA_CRAWLING = "data_crawling"
    FINANCIAL_ANALYSIS = "financial_analysis"
    CONTENT_CREATION = "content_creation"
    ACCOUNT_OPERATION = "account_operation"
    NEGOTIATION = "negotiation"
    SEO_OPTIMIZATION = "seo_optimization"
    VIDEO_PRODUCTION = "video_production"
    SOCIAL_MEDIA = "social_media"
    CUSTOMER_SERVICE = "customer_service"
    LOGISTICS = "logistics"
    GENERAL = "general"

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class ResourceType(Enum):
    """资源类型枚举"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"
    API_QUOTA = "api_quota"
    DATABASE_CONNECTION = "db_conn"

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"

@dataclass
class TaskResourceRequirement:
    """任务资源需求"""
    resource_type: ResourceType
    required_amount: float
    max_wait_time_seconds: float = 60.0
    priority: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            'resource_type': self.resource_type.value,
            'required_amount': self.required_amount,
            'max_wait_time_seconds': self.max_wait_time_seconds,
            'priority': self.priority
        }

@dataclass
class TaskRequirements:
    """任务需求描述"""
    task_type: TaskType
    required_capabilities: List[str]
    priority: TaskPriority
    estimated_complexity: float
    target_regions: List[str]
    deadline: Optional[datetime] = None
    batch_size: int = 1
    max_cost: Optional[float] = None
    min_success_rate: float = 0.0
    
    # 优化字段
    quality_requirement: float = 0.7
    time_sensitivity: float = 0.5
    collaboration_needed: bool = False
    specialized_expertise: List[str] = field(default_factory=list)
    avoid_shortcomings: bool = True
    load_balance_preference: float = 0.8
    
    def __post_init__(self):
        if self.required_capabilities is None:
            self.required_capabilities = []
        if self.target_regions is None:
            self.target_regions = []

@dataclass
class AvatarProfile:
    """分身能力画像"""
    avatar_id: str
    avatar_name: str
    template_id: Optional[str] = None
    capability_scores: Dict[str, float] = field(default_factory=dict)
    specialization_tags: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    total_tasks_completed: int = 0
    avg_completion_time_seconds: float = 0.0
    current_load: int = 0
    last_active: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    region_expertise: List[str] = field(default_factory=list)
    cost_efficiency: float = 1.0
    reliability_score: float = 1.0
    response_speed_score: float = 1.0
    
    # 健康状态字段
    health_status: str = "unknown"  # healthy, degraded, unknown
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0
    task_success_rate: float = 1.0
    
    # 负载均衡字段
    max_capacity: int = 5
    load_history: List[Tuple[datetime, int]] = field(default_factory=list)
    
    @property
    def availability_score(self) -> float:
        """计算可用性分数，考虑健康和负载"""
        # 健康状态权重
        health_weight = 0.6
        load_weight = 0.4
        
        # 健康状态分数映射
        health_scores = {
            "healthy": 1.0,
            "degraded": 0.5,
            "unknown": 0.3
        }
        
        health_score = health_scores.get(self.health_status, 0.3)
        
        # 负载分数（负载越低分数越高）
        load_ratio = self.current_load / self.max_capacity if self.max_capacity > 0 else 1.0
        load_score = 1.0 - min(load_ratio, 1.0)
        
        # 综合分数
        return health_weight * health_score + load_weight * load_score
    
    def can_handle_task(self, required_capabilities: List[str], min_score: float = 0.7) -> bool:
        """检查分身是否能处理特定任务"""
        # 检查健康状态
        if self.health_status not in ["healthy", "unknown"]:
            return False
        
        # 检查负载
        if self.current_load >= self.max_capacity:
            return False
        
        # 检查能力要求
        for capability in required_capabilities:
            if capability not in self.capability_scores:
                return False
            if self.capability_scores[capability] < min_score:
                return False
        
        return True

@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: str
    avatar_id: str
    priority: int
    estimated_duration_seconds: float
    resource_requirements: List[TaskResourceRequirement]
    dependencies: List[str]
    deadline: Optional[datetime]
    status: TaskStatus
    scheduled_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        # 手动转换资源需求，确保枚举值被正确序列化
        serializable_resource_reqs = []
        for req in self.resource_requirements:
            serializable_req = {
                'resource_type': req.resource_type.value,
                'required_amount': req.required_amount,
                'max_wait_time_seconds': req.max_wait_time_seconds,
                'priority': req.priority
            }
            serializable_resource_reqs.append(serializable_req)
        
        return {
            "task_id": self.task_id,
            "avatar_id": self.avatar_id,
            "priority": self.priority,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "resource_requirements": json.dumps(serializable_resource_reqs),
            "dependencies": json.dumps(self.dependencies),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status.value,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "created_at": self.created_at.isoformat()
        }

class IntelligentScheduler:
    """智能调度器核心类"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化智能调度器
        
        参数：
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.task_queue = defaultdict(list)  # 按优先级组织的任务队列
        self.running_tasks: Dict[str, ScheduledTask] = {}
        self.completed_tasks: Dict[str, ScheduledTask] = {}
        self.avatar_profiles_cache: Dict[str, AvatarProfile] = {}
        self.cache_expiry = 60  # 秒
        self.last_cache_update = 0
        
        # 性能监控
        self.scheduler_stats = {
            'total_tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'avg_scheduling_time_ms': 0.0,
            'avg_task_duration_seconds': 0.0,
            'resource_utilization': defaultdict(float),
            'load_balance_score': 0.0
        }
        
        # 任务计数器
        self.task_counter = 0
        
        # 锁和同步
        self.queue_lock = threading.RLock()
        self.cache_lock = threading.RLock()
        
        # 启动后台线程
        self.cleanup_active = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("智能调度器初始化完成")
    
    def _load_avatar_profiles(self, force_refresh: bool = False) -> Dict[str, AvatarProfile]:
        """
        加载分身能力画像，支持缓存
        
        参数：
            force_refresh: 强制刷新缓存
            
        返回：
            分身画像字典
        """
        current_time = time.time()
        
        with self.cache_lock:
            if not force_refresh and current_time - self.last_cache_update < self.cache_expiry:
                if self.avatar_profiles_cache:
                    return self.avatar_profiles_cache
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT avatar_id, avatar_name, template_id, capability_scores, 
                       specialization_tags, success_rate, total_tasks_completed,
                       avg_completion_time_seconds, current_load, last_active, 
                       created_at
                FROM avatar_capability_profiles
            """)
            
            profiles = {}
            for row in cursor.fetchall():
                avatar_id = row[0]
                
                # 解析JSON字段
                capability_scores = {}
                if row[3]:
                    try:
                        capability_scores = json.loads(row[3])
                    except:
                        capability_scores = {}
                
                specialization_tags = []
                if row[4]:
                    try:
                        specialization_tags = json.loads(row[4])
                    except:
                        specialization_tags = []
                
                # 转换时间戳
                last_active = datetime.now()
                if row[9]:
                    try:
                        last_active = datetime.fromisoformat(row[9].replace('Z', '+00:00'))
                    except:
                        pass
                
                created_at = datetime.now()
                if row[10]:
                    try:
                        created_at = datetime.fromisoformat(row[10].replace('Z', '+00:00'))
                    except:
                        pass
                
                # 从资源池表获取分身资源配额
                cursor.execute("""
                    SELECT resource_type, allocated_amount, max_amount
                    FROM avatar_virtual_pools
                    WHERE avatar_id = ?
                """, (avatar_id,))
                
                region_expertise = []
                cost_efficiency = 1.0
                reliability_score = 1.0
                response_speed_score = 1.0
                
                profile = AvatarProfile(
                    avatar_id=avatar_id,
                    avatar_name=row[1],
                    template_id=row[2],
                    capability_scores=capability_scores,
                    specialization_tags=specialization_tags,
                    success_rate=row[5] or 0.0,
                    total_tasks_completed=row[6] or 0,
                    avg_completion_time_seconds=row[7] or 0.0,
                    current_load=row[8] or 0,
                    last_active=last_active,
                    created_at=created_at,
                    region_expertise=region_expertise,
                    cost_efficiency=cost_efficiency,
                    reliability_score=reliability_score,
                    response_speed_score=response_speed_score
                )
                
                profiles[avatar_id] = profile
            
            with self.cache_lock:
                self.avatar_profiles_cache = profiles
                self.last_cache_update = current_time
            
            logger.debug(f"加载了 {len(profiles)} 个分身画像")
            return profiles
            
        except Exception as e:
            logger.error(f"加载分身画像失败: {e}")
            return {}
        finally:
            conn.close()
    
    def submit_task(self, task_req: TaskRequirements, opportunity_data: Dict[str, Any]) -> Optional[str]:
        """
        提交新任务到调度系统
        
        参数：
            task_req: 任务需求描述
            opportunity_data: 商机数据
            
        返回：
            任务ID，提交失败返回None
        """
        start_time = time.time()
        
        try:
            # 生成唯一任务ID
            task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # 寻找最适合的分身
            best_avatar = self._find_best_avatar_for_task(task_req)
            if not best_avatar:
                logger.warning(f"未找到适合处理任务的分身: {task_req.task_type.value}")
                return None
            
            # 转换资源需求
            resource_requirements = self._convert_resource_requirements(task_req)
            
            # 创建调度任务
            scheduled_task = ScheduledTask(
                task_id=task_id,
                avatar_id=best_avatar,
                priority=task_req.priority.value,
                estimated_duration_seconds=task_req.estimated_complexity * 60,  # 假设复杂度转换为分钟
                resource_requirements=resource_requirements,
                dependencies=opportunity_data.get('dependencies', []),
                deadline=task_req.deadline,
                status=TaskStatus.PENDING,
                created_at=datetime.now()
            )
            
            # 将任务加入队列
            with self.queue_lock:
                self.task_queue[scheduled_task.priority].append(scheduled_task)
                self.scheduler_stats['total_tasks_submitted'] += 1
            
            # 保存到数据库
            self._save_task_to_db(scheduled_task, opportunity_data)
            
            # 记录调度决策
            self._record_scheduling_decision(task_id, best_avatar, task_req)
            
            # 立即尝试调度
            self._schedule_pending_tasks()
            
            # 更新性能指标
            scheduling_time = (time.time() - start_time) * 1000
            self.scheduler_stats['avg_scheduling_time_ms'] = (
                self.scheduler_stats['avg_scheduling_time_ms'] * 0.9 + scheduling_time * 0.1
            )
            
            logger.info(f"任务提交成功: {task_id} -> {best_avatar} (调度时间: {scheduling_time:.2f}ms)")
            return task_id
            
        except Exception as e:
            logger.error(f"任务提交失败: {e}")
            return None
    
    def _find_best_avatar_for_task(self, task_req: TaskRequirements) -> Optional[str]:
        """
        为任务寻找最适合的分身
        
        参数：
            task_req: 任务需求
            
        返回：
            最适合的分身ID，找不到返回None
        """
        profiles = self._load_avatar_profiles()
        if not profiles:
            logger.warning("没有可用的分身画像")
            return None
        
        best_avatar_id = None
        best_score = -1.0
        
        for avatar_id, profile in profiles.items():
            # 检查分身是否能处理任务
            if not profile.can_handle_task(task_req.required_capabilities, task_req.min_success_rate):
                continue
            
            # 计算匹配分数
            match_score = self._calculate_avatar_task_match(profile, task_req)
            
            if match_score > best_score:
                best_score = match_score
                best_avatar_id = avatar_id
        
        if best_avatar_id:
            logger.debug(f"找到最佳分身: {best_avatar_id} (分数: {best_score:.3f})")
        
        return best_avatar_id
    
    def _calculate_avatar_task_match(self, profile: AvatarProfile, 
                                    task_req: TaskRequirements) -> float:
        """
        计算分身与任务的匹配分数
        
        参数：
            profile: 分身画像
            task_req: 任务需求
            
        返回：
            匹配分数（0-1）
        """
        # 各维度分数
        scores = {}
        
        # 1. 能力匹配度（权重0.3）
        capability_score = 0.0
        if task_req.required_capabilities:
            relevant_scores = []
            for capability in task_req.required_capabilities:
                if capability in profile.capability_scores:
                    score = profile.capability_scores[capability]
                    relevant_scores.append(score)
                else:
                    relevant_scores.append(0.0)
            
            if relevant_scores:
                capability_score = sum(relevant_scores) / len(relevant_scores)
        
        scores['capability_match'] = capability_score
        
        # 2. 专长标签匹配（权重0.2）
        specialization_score = 0.0
        if task_req.task_type != TaskType.GENERAL and profile.specialization_tags:
            task_type_str = task_req.task_type.value.lower()
            tag_match = False
            
            for tag in profile.specialization_tags:
                tag_lower = tag.lower()
                if task_type_str in tag_lower or tag_lower in task_type_str:
                    tag_match = True
                    break
            
            if tag_match:
                specialization_score = 1.0
            elif profile.specialization_tags:
                specialization_score = 0.3
        
        scores['specialization_match'] = specialization_score
        
        # 3. 地域匹配度（权重0.15）
        region_score = 0.0
        if task_req.target_regions and profile.region_expertise:
            # 检查地域匹配
            matching_regions = set(task_req.target_regions) & set(profile.region_expertise)
            if matching_regions:
                region_score = len(matching_regions) / len(task_req.target_regions)
        
        scores['region_match'] = region_score
        
        # 4. 成功率（权重0.15）
        success_score = profile.success_rate or 0.0
        scores['success_rate'] = success_score
        
        # 5. 负载因子（权重0.1）- 负载越低越好
        load_factor = 1.0 / (1.0 + profile.current_load)
        scores['load_factor'] = load_factor
        
        # 6. 响应速度（权重0.1）- 完成时间越短越好
        response_score = 1.0
        if profile.avg_completion_time_seconds and profile.avg_completion_time_seconds > 0:
            # 假设合理完成时间在300秒内
            response_score = max(0, 1.0 - (profile.avg_completion_time_seconds / 300))
        
        scores['response_speed'] = response_score
        
        # 加权计算总分
        weights = {
            'capability_match': 0.30,
            'specialization_match': 0.20,
            'region_match': 0.15,
            'success_rate': 0.15,
            'load_factor': 0.10,
            'response_speed': 0.10
        }
        
        total_score = 0.0
        weight_sum = 0.0
        
        for key, weight in weights.items():
            if key in scores:
                total_score += scores[key] * weight
                weight_sum += weight
        
        if weight_sum > 0:
            total_score /= weight_sum
        
        return total_score
    
    def _convert_resource_requirements(self, task_req: TaskRequirements) -> List[TaskResourceRequirement]:
        """
        转换任务需求为资源需求
        
        参数：
            task_req: 任务需求
            
        返回：
            资源需求列表
        """
        # 基于任务类型估算资源需求
        requirements = []
        
        # CPU需求
        cpu_requirement = TaskResourceRequirement(
            resource_type=ResourceType.CPU,
            required_amount=min(4.0, task_req.estimated_complexity * 0.8),
            max_wait_time_seconds=30.0,
            priority=task_req.priority.value
        )
        requirements.append(cpu_requirement)
        
        # 内存需求
        memory_requirement = TaskResourceRequirement(
            resource_type=ResourceType.MEMORY,
            required_amount=min(8.0, task_req.estimated_complexity * 2.0),
            max_wait_time_seconds=30.0,
            priority=task_req.priority.value
        )
        requirements.append(memory_requirement)
        
        # 网络需求
        network_requirement = TaskResourceRequirement(
            resource_type=ResourceType.NETWORK,
            required_amount=min(100.0, task_req.estimated_complexity * 20.0),
            max_wait_time_seconds=45.0,
            priority=task_req.priority.value
        )
        requirements.append(network_requirement)
        
        # API配额需求
        api_requirement = TaskResourceRequirement(
            resource_type=ResourceType.API_QUOTA,
            required_amount=min(50.0, task_req.estimated_complexity * 10.0),
            max_wait_time_seconds=45.0,
            priority=task_req.priority.value
        )
        requirements.append(api_requirement)
        
        return requirements
    
    def _save_task_to_db(self, task: ScheduledTask, opportunity_data: Dict[str, Any]):
        """保存任务到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 使用to_dict方法，它已经正确处理了序列化
            task_dict = task.to_dict()
            
            cursor.execute("""
                INSERT INTO scheduler_task_queue 
                (task_id, task_type, priority, estimated_duration_seconds, 
                 resource_requirements, dependencies, deadline, status, 
                 assigned_avatar, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task_dict.get('task_type', 'general'),
                task.priority,
                task.estimated_duration_seconds,
                task_dict['resource_requirements'],
                task_dict['dependencies'],
                task_dict['deadline'],
                task.status.value,
                task.avatar_id,
                task.created_at.isoformat()
            ))
            
            # 如果有机会哈希，同步到机会表
            if '_metadata' in opportunity_data and 'opportunity_hash' in opportunity_data['_metadata']:
                opp_hash = opportunity_data['_metadata']['opportunity_hash']
                cursor.execute("""
                    INSERT OR REPLACE INTO processed_opportunities 
                    (opportunity_hash, source_platform, original_id, title, 
                     first_examined, last_examined, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    opp_hash,
                    opportunity_data.get('source_platform', 'unknown'),
                    opportunity_data.get('original_id', ''),
                    opportunity_data.get('title', ''),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    'processing'
                ))
                
                # 记录任务分配
                cursor.execute("""
                    INSERT INTO task_assignments 
                    (opportunity_hash, assigned_avatar, assignment_time, 
                     priority, completion_status)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    opp_hash,
                    task.avatar_id,
                    datetime.now().isoformat(),
                    task.priority,
                    'pending'
                ))
            
            conn.commit()
            logger.debug(f"任务已保存到数据库: {task.task_id}")
            
        except Exception as e:
            logger.error(f"保存任务到数据库失败: {e}")
            raise
        finally:
            conn.close()
    
    def _record_scheduling_decision(self, task_id: str, avatar_id: str, 
                                   task_req: TaskRequirements):
        """记录调度决策"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 计算匹配分数用于记录
            profiles = self._load_avatar_profiles()
            profile = profiles.get(avatar_id)
            if profile:
                match_score = self._calculate_avatar_task_match(profile, task_req)
            else:
                match_score = 0.0
            
            cursor.execute("""
                INSERT INTO scheduler_decision_history 
                (task_id, avatar_id, decision_time, decision_type, match_score)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task_id,
                avatar_id,
                datetime.now().isoformat(),
                'initial_assignment',
                match_score
            ))
            
            conn.commit()
            logger.debug(f"调度决策已记录: {task_id} -> {avatar_id}")
            
        except Exception as e:
            logger.error(f"记录调度决策失败: {e}")
        finally:
            conn.close()
    
    def _schedule_pending_tasks(self):
        """调度待处理任务"""
        with self.queue_lock:
            # 按优先级从高到低处理
            priorities = sorted(self.task_queue.keys(), reverse=True)
            
            for priority in priorities:
                tasks = self.task_queue[priority]
                if not tasks:
                    continue
                
                # 尝试为每个任务分配资源
                for task in tasks[:]:  # 使用副本进行迭代
                    if task.status == TaskStatus.PENDING:
                        success = self._allocate_resources_for_task(task)
                        if success:
                            # 更新任务状态
                            task.status = TaskStatus.SCHEDULED
                            task.scheduled_time = datetime.now()
                            
                            # 从待处理队列移除
                            tasks.remove(task)
                            
                            # 添加到运行中任务
                            self.running_tasks[task.task_id] = task
                            
                            logger.info(f"任务已调度: {task.task_id}")
                
                # 更新队列
                self.task_queue[priority] = tasks
    
    def _allocate_resources_for_task(self, task: ScheduledTask) -> bool:
        """
        为任务分配资源
        
        参数：
            task: 调度任务
            
        返回：
            分配成功返回True，否则False
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查全局资源池
            for req in task.resource_requirements:
                resource_type = req.resource_type.value
                required_amount = req.required_amount
                
                # 查询可用资源
                cursor.execute("""
                    SELECT resource_name, available_amount
                    FROM scheduler_resource_pool
                    WHERE resource_type = ?
                """, (resource_type,))
                
                resources = cursor.fetchall()
                
                # 检查是否有足够资源
                total_available = sum(res[1] for res in resources)
                if total_available < required_amount:
                    logger.warning(f"资源不足: {resource_type} 需要{required_amount}, 可用{total_available}")
                    return False
            
            # 分配资源
            allocation_ids = []
            for req in task.resource_requirements:
                resource_type = req.resource_type.value
                required_amount = req.required_amount
                
                # 查找合适资源
                cursor.execute("""
                    SELECT resource_name, available_amount
                    FROM scheduler_resource_pool
                    WHERE resource_type = ? AND available_amount >= ?
                    ORDER BY available_amount DESC
                    LIMIT 1
                """, (resource_type, required_amount))
                
                resource = cursor.fetchone()
                if not resource:
                    # 尝试从多个资源中分配
                    cursor.execute("""
                        SELECT resource_name, available_amount
                        FROM scheduler_resource_pool
                        WHERE resource_type = ? AND available_amount > 0
                        ORDER BY available_amount DESC
                    """, (resource_type,))
                    
                    resources = cursor.fetchall()
                    
                    # 从多个资源中组合分配
                    allocated = 0
                    for res in resources:
                        resource_name = res[0]
                        available = res[1]
                        
                        allocate_from_this = min(required_amount - allocated, available)
                        if allocate_from_this > 0:
                            # 更新资源池
                            cursor.execute("""
                                UPDATE scheduler_resource_pool
                                SET available_amount = available_amount - ?,
                                    updated_at = ?
                                WHERE resource_name = ?
                            """, (allocate_from_this, datetime.now().isoformat(), resource_name))
                            
                            # 记录资源分配
                            cursor.execute("""
                                INSERT INTO scheduler_resource_allocations
                                (resource_id, resource_type, allocated_amount, task_id, avatar_id,
                                 allocation_time, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                f"{resource_type}_{resource_name}",
                                resource_type,
                                allocate_from_this,
                                task.task_id,
                                task.avatar_id,
                                datetime.now().isoformat(),
                                'active'
                            ))
                            
                            allocation_ids.append(cursor.lastrowid)
                            allocated += allocate_from_this
                            
                            if allocated >= required_amount:
                                break
                    
                    if allocated < required_amount:
                        # 分配失败，回滚已分配的资源
                        self._release_resources(allocation_ids)
                        return False
                else:
                    resource_name, available = resource
                    
                    # 更新资源池
                    cursor.execute("""
                        UPDATE scheduler_resource_pool
                        SET available_amount = available_amount - ?,
                            updated_at = ?
                        WHERE resource_name = ?
                    """, (required_amount, datetime.now().isoformat(), resource_name))
                    
                    # 记录资源分配
                    cursor.execute("""
                        INSERT INTO scheduler_resource_allocations
                        (resource_id, resource_type, allocated_amount, task_id, avatar_id,
                         allocation_time, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"{resource_type}_{resource_name}",
                        resource_type,
                        required_amount,
                        task.task_id,
                        task.avatar_id,
                        datetime.now().isoformat(),
                        'active'
                    ))
                    
                    allocation_ids.append(cursor.lastrowid)
            
            conn.commit()
            logger.debug(f"资源分配成功: 任务{task.task_id}, 分配ID {allocation_ids}")
            return True
            
        except Exception as e:
            logger.error(f"资源分配失败: {e}")
            return False
        finally:
            conn.close()
    
    def _release_resources(self, allocation_ids: List[int]):
        """释放已分配的资源"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for allocation_id in allocation_ids:
                # 获取分配信息
                cursor.execute("""
                    SELECT resource_id, allocated_amount
                    FROM scheduler_resource_allocations
                    WHERE allocation_id = ?
                """, (allocation_id,))
                
                allocation = cursor.fetchone()
                if not allocation:
                    continue
                
                resource_id, allocated_amount = allocation
                
                # 解析资源名称
                if '_' in resource_id:
                    resource_type, resource_name = resource_id.split('_', 1)
                    
                    # 释放回资源池
                    cursor.execute("""
                        UPDATE scheduler_resource_pool
                        SET available_amount = available_amount + ?,
                            updated_at = ?
                        WHERE resource_name = ?
                    """, (allocated_amount, datetime.now().isoformat(), resource_name))
                
                # 更新分配状态
                cursor.execute("""
                    UPDATE scheduler_resource_allocations
                    SET status = 'released',
                        actual_release_time = ?
                    WHERE allocation_id = ?
                """, (datetime.now().isoformat(), allocation_id))
            
            conn.commit()
            logger.debug(f"资源释放完成: {len(allocation_ids)} 个分配")
            
        except Exception as e:
            logger.error(f"资源释放失败: {e}")
        finally:
            conn.close()
    
    def _cleanup_loop(self):
        """清理循环，定期清理过期任务和更新状态"""
        while self.cleanup_active:
            try:
                time.sleep(30)  # 每30秒执行一次清理
                
                # 清理过期任务
                self._cleanup_expired_tasks()
                
                # 更新负载指标
                self._update_load_metrics()
                
                # 刷新缓存
                self._load_avatar_profiles(force_refresh=True)
                
            except Exception as e:
                logger.error(f"清理循环异常: {e}")
    
    def _cleanup_expired_tasks(self):
        """清理过期任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now()
            
            # 查找过期任务
            cursor.execute("""
                SELECT task_id
                FROM scheduler_task_queue
                WHERE deadline IS NOT NULL 
                  AND deadline < ?
                  AND status IN ('pending', 'scheduled', 'running')
            """, (now.isoformat(),))
            
            expired_tasks = cursor.fetchall()
            
            for task_row in expired_tasks:
                task_id = task_row[0]
                
                # 更新任务状态为超时
                cursor.execute("""
                    UPDATE scheduler_task_queue
                    SET status = 'timeout',
                        updated_at = ?
                    WHERE task_id = ?
                """, (now.isoformat(), task_id))
                
                # 释放关联的资源
                cursor.execute("""
                    SELECT allocation_id
                    FROM scheduler_resource_allocations
                    WHERE task_id = ? AND status = 'active'
                """, (task_id,))
                
                allocations = cursor.fetchall()
                allocation_ids = [alloc[0] for alloc in allocations]
                
                if allocation_ids:
                    self._release_resources(allocation_ids)
                
                logger.info(f"任务超时清理: {task_id}")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"清理过期任务失败: {e}")
        finally:
            conn.close()
    
    def _update_load_metrics(self):
        """更新负载指标"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有分身当前状态
            cursor.execute("""
                SELECT avatar_id, current_load, last_active
                FROM avatar_capability_profiles
            """)
            
            avatars = cursor.fetchall()
            
            for avatar_row in avatars:
                avatar_id, current_load, last_active = avatar_row
                
                # 模拟计算CPU和内存使用率
                cpu_usage = min(100.0, current_load * 15.0 + random.uniform(5.0, 15.0))
                memory_usage = min(100.0, current_load * 8.0 + random.uniform(10.0, 30.0))
                
                # 估算任务成功率
                task_success_rate = 0.95 - (current_load * 0.05)
                
                # 确定健康状态
                health_status = "healthy"
                if current_load > 4:
                    health_status = "degraded"
                
                # 记录负载指标
                cursor.execute("""
                    INSERT INTO scheduler_load_metrics
                    (avatar_id, timestamp, cpu_usage_percent, memory_usage_mb,
                     active_tasks, queued_tasks, avg_response_time_ms,
                     task_success_rate, health_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    avatar_id,
                    datetime.now().isoformat(),
                    cpu_usage,
                    memory_usage,
                    current_load,
                    0,  # queued_tasks 暂不实现
                    500.0 / (current_load + 1),  # 模拟响应时间
                    task_success_rate,
                    health_status
                ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"更新负载指标失败: {e}")
        finally:
            conn.close()
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        返回：
            系统状态字典
        """
        with self.queue_lock:
            # 计算各种状态任务数
            pending_tasks = sum(len(tasks) for tasks in self.task_queue.values())
            running_tasks = len(self.running_tasks)
            completed_tasks = len(self.completed_tasks)
            
            # 计算系统负载
            total_tasks = pending_tasks + running_tasks
            total_capacity = sum(1 for profile in self.avatar_profiles_cache.values() 
                               if profile.health_status in ['healthy', 'unknown'])
            
            load_percentage = 0.0
            if total_capacity > 0:
                load_percentage = (total_tasks / total_capacity) * 100.0
            
            status = {
                'timestamp': datetime.now().isoformat(),
                'pending_tasks': pending_tasks,
                'running_tasks': running_tasks,
                'completed_tasks': completed_tasks,
                'total_avatars': len(self.avatar_profiles_cache),
                'system_load_percentage': round(load_percentage, 2),
                'scheduler_stats': self.scheduler_stats.copy(),
                'task_queue_sizes': {priority: len(tasks) 
                                   for priority, tasks in self.task_queue.items()}
            }
            
            return status
    
    def shutdown(self):
        """关闭调度器"""
        self.cleanup_active = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5.0)
        
        logger.info("智能调度器已关闭")

def main():
    """测试主函数"""
    scheduler = IntelligentScheduler()
    
    try:
        # 创建测试任务需求
        task_req = TaskRequirements(
            task_type=TaskType.FINANCIAL_ANALYSIS,
            required_capabilities=['data_crawling', 'financial_analysis'],
            priority=TaskPriority.NORMAL,
            estimated_complexity=5.0,
            target_regions=['US', 'CA'],
            deadline=datetime.now() + timedelta(hours=1)
        )
        
        # 创建测试商机数据
        opportunity_data = {
            'source_platform': 'Amazon',
            'original_id': 'B08N5WRWNW',
            'title': '男士牛仔裤 - 高品质牛仔布料',
            'estimated_margin': 35,
            '_metadata': {
                'opportunity_hash': 'test_hash_12345'
            }
        }
        
        # 提交任务
        task_id = scheduler.submit_task(task_req, opportunity_data)
        
        if task_id:
            print(f"任务提交成功: {task_id}")
            
            # 获取系统状态
            status = scheduler.get_system_status()
            print(f"\n系统状态:")
            print(f"  待处理任务: {status['pending_tasks']}")
            print(f"  运行中任务: {status['running_tasks']}")
            print(f"  完成的任务: {status['completed_tasks']}")
            print(f"  总分身数: {status['total_avatars']}")
            print(f"  系统负载: {status['system_load_percentage']}%")
        
        # 等待一会
        time.sleep(2)
        
    finally:
        scheduler.shutdown()

if __name__ == "__main__":
    main()