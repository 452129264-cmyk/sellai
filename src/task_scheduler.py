#!/usr/bin/env python3
"""
任务调度引擎
支持优先级队列、资源预留、冲突检测和死锁预防机制
"""

import json
import time
import logging
import sqlite3
import threading
import heapq
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import uuid
import random

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - TASK-SCHEDULER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchedulerMode(Enum):
    """调度模式枚举"""
    FIFO = "fifo"  # 先入先出
    PRIORITY = "priority"  # 优先级调度
    LOAD_BALANCED = "load_balanced"  # 负载均衡
    ADAPTIVE = "adaptive"  # 自适应调度

class ResourceType(Enum):
    """资源类型枚举"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"
    API_QUOTA = "api_quota"
    DATABASE_CONNECTION = "database_connection"

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

@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: str
    avatar_id: str
    priority: int
    estimated_duration_seconds: float
    resource_requirements: List[TaskResourceRequirement]
    dependencies: List[str]  # 依赖的其他任务ID
    deadline: Optional[datetime]
    status: TaskStatus
    scheduled_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ResourceAllocation:
    """资源分配"""
    resource_id: str
    resource_type: ResourceType
    allocated_amount: float
    task_id: str
    avatar_id: str
    allocation_time: datetime
    expected_release_time: Optional[datetime] = None

@dataclass
class ConflictResolution:
    """冲突解决结果"""
    conflict_id: str
    task_id: str
    conflict_type: str
    resolution: str
    resolved_at: datetime
    details: Dict[str, Any]

class TaskScheduler:
    """任务调度引擎"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化任务调度器
        
        Args:
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.scheduler_mode = SchedulerMode.ADAPTIVE
        
        # 任务队列
        self.pending_tasks: Dict[int, List[ScheduledTask]] = defaultdict(list)
        self.running_tasks: Dict[str, ScheduledTask] = {}
        self.completed_tasks: Dict[str, ScheduledTask] = {}
        
        # 资源管理
        self.resource_pool: Dict[ResourceType, Dict[str, float]] = defaultdict(dict)
        self.allocated_resources: List[ResourceAllocation] = []
        self.resource_locks: Dict[str, threading.Lock] = {}
        
        # 冲突检测
        self.conflict_history: List[ConflictResolution] = []
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # 性能监控
        self.scheduler_stats = {
            'total_tasks_scheduled': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'avg_scheduling_time_ms': 0.0,
            'avg_task_duration_seconds': 0.0,
            'resource_utilization': defaultdict(float),
            'conflicts_resolved': 0
        }
        
        # 初始化
        self._init_resource_pool()
        self._init_database_tables()
        
        # 启动调度线程
        self.scheduler_active = True
        self.scheduler_thread = threading.Thread(target=self._scheduling_loop, daemon=True)
        self.scheduler_thread.start()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_system_performance, daemon=True)
        self.monitor_thread.start()
        
        logger.info("任务调度引擎初始化完成")
    
    def _init_resource_pool(self):
        """初始化资源池"""
        # 定义系统资源
        resources = {
            ResourceType.CPU: {"cores": 8.0, "threads": 16.0},
            ResourceType.MEMORY: {"total_gb": 32.0, "available_gb": 16.0},
            ResourceType.NETWORK: {"bandwidth_mbps": 1000.0, "connections": 100.0},
            ResourceType.STORAGE: {"total_gb": 1024.0, "available_gb": 512.0},
            ResourceType.API_QUOTA: {"requests_per_minute": 1000.0, "tokens_per_hour": 1000000.0},
            ResourceType.DATABASE_CONNECTION: {"max_connections": 50.0, "available_connections": 30.0}
        }
        
        for resource_type, resource_dict in resources.items():
            for resource_name, amount in resource_dict.items():
                resource_id = f"{resource_type.value}_{resource_name}"
                self.resource_pool[resource_type][resource_id] = amount
        
        logger.info(f"资源池初始化完成，{len(self.resource_pool)} 种资源类型")
    
    def _init_database_tables(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 调度任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    task_id TEXT PRIMARY KEY,
                    avatar_id TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    estimated_duration_seconds REAL NOT NULL,
                    resource_requirements TEXT NOT NULL,  -- JSON格式
                    dependencies TEXT NOT NULL,  -- JSON数组
                    deadline TIMESTAMP,
                    status TEXT NOT NULL CHECK(status IN 
                        ('pending', 'scheduled', 'running', 'completed', 'failed', 'blocked', 'timeout')),
                    scheduled_time TIMESTAMP,
                    start_time TIMESTAMP,
                    completion_time TIMESTAMP,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. 资源分配表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resource_allocations (
                    allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    allocated_amount REAL NOT NULL,
                    task_id TEXT NOT NULL,
                    avatar_id TEXT NOT NULL,
                    allocation_time TIMESTAMP NOT NULL,
                    expected_release_time TIMESTAMP,
                    actual_release_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 3. 冲突解决记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conflict_resolutions (
                    resolution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conflict_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    conflict_type TEXT NOT NULL,
                    resolution TEXT NOT NULL,
                    resolved_at TIMESTAMP NOT NULL,
                    resolution_details TEXT NOT NULL,  -- JSON格式
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. 调度性能表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduler_performance (
                    performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pending_tasks_count INTEGER,
                    running_tasks_count INTEGER,
                    avg_scheduling_time_ms REAL,
                    avg_task_duration_seconds REAL,
                    resource_utilization TEXT,  -- JSON格式
                    conflicts_resolved_count INTEGER,
                    scheduler_mode TEXT
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status ON scheduled_tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_avatar ON scheduled_tasks(avatar_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_priority ON scheduled_tasks(priority)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_allocations_task ON resource_allocations(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_task ON conflict_resolutions(task_id)")
            
            conn.commit()
            logger.info("调度数据库表初始化完成")
            
        except Exception as e:
            logger.error(f"初始化数据库表失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def submit_task(self, avatar_id: str, priority: int, 
                   estimated_duration_seconds: float,
                   resource_requirements: List[TaskResourceRequirement],
                   dependencies: List[str] = None,
                   deadline: Optional[datetime] = None) -> Optional[str]:
        """
        提交任务到调度器
        
        Returns:
            任务ID，如提交失败则返回None
        """
        try:
            # 生成任务ID
            task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # 创建调度任务
            task = ScheduledTask(
                task_id=task_id,
                avatar_id=avatar_id,
                priority=priority,
                estimated_duration_seconds=estimated_duration_seconds,
                resource_requirements=resource_requirements,
                dependencies=dependencies or [],
                deadline=deadline,
                status=TaskStatus.PENDING
            )
            
            # 检查资源可用性
            if not self._check_resource_availability(task):
                logger.warning(f"任务 {task_id} 资源不可用，标记为阻塞")
                task.status = TaskStatus.BLOCKED
            
            # 加入对应优先级队列
            self.pending_tasks[priority].append(task)
            
            # 更新依赖图
            for dep in task.dependencies:
                self.dependency_graph[dep].add(task_id)
            
            # 记录到数据库
            self._save_task_to_db(task)
            
            self.scheduler_stats['total_tasks_scheduled'] += 1
            
            logger.info(f"任务提交成功: {task_id} (优先级: {priority}, 分身: {avatar_id})")
            
            return task_id
            
        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            return None
    
    def _check_resource_availability(self, task: ScheduledTask) -> bool:
        """检查任务资源可用性"""
        # 检查每种资源
        for req in task.resource_requirements:
            resource_type = req.resource_type
            
            if resource_type not in self.resource_pool:
                logger.warning(f"资源类型 {resource_type.value} 不存在")
                return False
            
            # 检查该类型下是否有足够资源
            total_available = 0.0
            for resource_id, amount in self.resource_pool[resource_type].items():
                # 减去已分配的资源
                allocated = sum(
                    alloc.allocated_amount 
                    for alloc in self.allocated_resources 
                    if alloc.resource_id == resource_id
                )
                available = amount - allocated
                
                if available >= req.required_amount:
                    return True  # 找到足够资源的实例
                
                total_available += available
            
            # 总可用资源不足
            if total_available < req.required_amount:
                logger.debug(f"资源 {resource_type.value} 不足: 需要 {req.required_amount}, 可用 {total_available}")
                return False
        
        return True
    
    def _allocate_resources(self, task: ScheduledTask) -> bool:
        """为任务分配资源"""
        allocations = []
        
        try:
            for req in task.resource_requirements:
                resource_type = req.resource_type
                required_amount = req.required_amount
                
                # 寻找可用资源
                allocated = False
                for resource_id, total_amount in self.resource_pool[resource_type].items():
                    # 计算当前已分配
                    currently_allocated = sum(
                        alloc.allocated_amount 
                        for alloc in self.allocated_resources 
                        if alloc.resource_id == resource_id
                    )
                    
                    available = total_amount - currently_allocated
                    
                    if available >= required_amount:
                        # 创建分配记录
                        allocation = ResourceAllocation(
                            resource_id=resource_id,
                            resource_type=resource_type,
                            allocated_amount=required_amount,
                            task_id=task.task_id,
                            avatar_id=task.avatar_id,
                            allocation_time=datetime.now(),
                            expected_release_time=datetime.now() + timedelta(seconds=task.estimated_duration_seconds)
                        )
                        
                        allocations.append(allocation)
                        allocated = True
                        break
                
                if not allocated:
                    # 分配失败，回滚已分配的资源
                    logger.error(f"无法为任务 {task.task_id} 分配资源 {resource_type.value}")
                    
                    # 清理已分配的资源
                    for alloc in allocations:
                        self._release_resource(alloc.resource_id, task.task_id)
                    
                    return False
            
            # 所有资源分配成功，添加到已分配列表
            self.allocated_resources.extend(allocations)
            
            # 记录到数据库
            for alloc in allocations:
                self._save_allocation_to_db(alloc)
            
            return True
            
        except Exception as e:
            logger.error(f"分配资源失败: {e}")
            
            # 清理
            for alloc in allocations:
                self._release_resource(alloc.resource_id, task.task_id)
            
            return False
    
    def _release_resources(self, task_id: str):
        """释放任务占用的资源"""
        to_release = []
        
        for i, alloc in enumerate(self.allocated_resources):
            if alloc.task_id == task_id:
                to_release.append(i)
        
        # 逆序删除，避免索引变化
        for i in sorted(to_release, reverse=True):
            alloc = self.allocated_resources.pop(i)
            
            # 更新数据库
            self._update_allocation_release_time(alloc)
        
        logger.debug(f"释放了任务 {task_id} 的资源")
    
    def _scheduling_loop(self):
        """调度循环"""
        logger.info("调度循环开始")
        
        while self.scheduler_active:
            try:
                # 检查依赖满足的任务
                self._check_dependencies()
                
                # 按优先级调度任务
                scheduled_count = 0
                
                for priority in sorted(self.pending_tasks.keys(), reverse=True):  # 高优先级先处理
                    tasks = self.pending_tasks[priority]
                    
                    if not tasks:
                        continue
                    
                    # 筛选可执行的任务
                    executable_tasks = []
                    for task in tasks:
                        if task.status == TaskStatus.PENDING:
                            # 检查资源
                            if self._check_resource_availability(task):
                                executable_tasks.append(task)
                        elif task.status == TaskStatus.BLOCKED:
                            # 检查是否已满足条件
                            if self._check_resource_availability(task):
                                task.status = TaskStatus.PENDING
                                executable_tasks.append(task)
                    
                    # 为可执行任务分配资源并启动
                    for task in executable_tasks:
                        if self._allocate_resources(task):
                            # 启动任务
                            self._start_task(task)
                            scheduled_count += 1
                        
                        # 移出待处理队列
                        tasks.remove(task)
                
                # 检查超时任务
                self._check_timeouts()
                
                # 记录性能指标
                if scheduled_count > 0:
                    self._record_performance_metrics()
                
                # 等待下一轮调度
                time.sleep(1)  # 1秒调度一次
                
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
                time.sleep(5)
    
    def _check_dependencies(self):
        """检查任务依赖是否满足"""
        # 找出已完成的任务
        completed_tasks = set(self.completed_tasks.keys())
        
        # 检查依赖这些任务的待处理任务
        for dep_task_id in list(completed_tasks):
            if dep_task_id in self.dependency_graph:
                dependent_tasks = self.dependency_graph[dep_task_id]
                
                for task_id in list(dependent_tasks):
                    # 找到对应的任务
                    for priority, tasks in self.pending_tasks.items():
                        for task in tasks:
                            if task.task_id == task_id and dep_task_id in task.dependencies:
                                task.dependencies.remove(dep_task_id)
                                
                                if not task.dependencies:
                                    task.status = TaskStatus.PENDING
                                    logger.debug(f"任务 {task_id} 的依赖已满足")
                
                # 清理依赖图
                del self.dependency_graph[dep_task_id]
    
    def _start_task(self, task: ScheduledTask):
        """启动任务"""
        task.status = TaskStatus.RUNNING
        task.scheduled_time = datetime.now()
        task.start_time = datetime.now()
        
        # 更新数据库
        self._update_task_status(task)
        
        # 启动任务执行线程
        task_thread = threading.Thread(
            target=self._execute_task,
            args=(task,),
            daemon=True
        )
        task_thread.start()
        
        # 加入运行中任务列表
        self.running_tasks[task.task_id] = task
        
        logger.info(f"任务启动: {task.task_id} (分身: {task.avatar_id})")
    
    def _execute_task(self, task: ScheduledTask):
        """执行任务"""
        try:
            # 模拟任务执行
            time.sleep(task.estimated_duration_seconds)
            
            # 任务完成
            self._complete_task(task.task_id, success=True)
            
        except Exception as e:
            logger.error(f"任务执行失败: {task.task_id}, 错误: {e}")
            self._complete_task(task.task_id, success=False)
    
    def _complete_task(self, task_id: str, success: bool = True):
        """完成任务"""
        if task_id not in self.running_tasks:
            logger.warning(f"任务不存在或未运行: {task_id}")
            return
        
        task = self.running_tasks[task_id]
        
        # 更新状态
        if success:
            task.status = TaskStatus.COMPLETED
            self.scheduler_stats['tasks_completed'] += 1
        else:
            task.status = TaskStatus.FAILED
            self.scheduler_stats['tasks_failed'] += 1
        
        task.completion_time = datetime.now()
        
        # 释放资源
        self._release_resources(task_id)
        
        # 移到已完成列表
        self.completed_tasks[task_id] = task
        del self.running_tasks[task_id]
        
        # 更新数据库
        self._update_task_status(task)
        
        logger.info(f"任务完成: {task_id}, 状态: {task.status.value}")
    
    def _check_timeouts(self):
        """检查超时任务"""
        current_time = datetime.now()
        
        # 检查运行中任务
        for task_id, task in list(self.running_tasks.items()):
            # 检查任务超时
            if task.deadline and current_time > task.deadline:
                logger.warning(f"任务超时: {task_id}")
                task.status = TaskStatus.TIMEOUT
                
                # 释放资源
                self._release_resources(task_id)
                
                # 移到已完成列表
                self.completed_tasks[task_id] = task
                del self.running_tasks[task_id]
                
                # 更新数据库
                self._update_task_status(task)
            
            # 检查预估时间超时
            elif task.start_time and task.estimated_duration_seconds:
                estimated_completion = task.start_time + timedelta(seconds=task.estimated_duration_seconds * 1.5)
                if current_time > estimated_completion:
                    logger.warning(f"任务执行时间过长: {task_id}")
    
    def detect_conflicts(self, task: ScheduledTask) -> List[ConflictResolution]:
        """
        检测任务冲突
        
        Returns:
            冲突列表
        """
        conflicts = []
        
        # 1. 资源冲突检测
        resource_conflicts = self._detect_resource_conflicts(task)
        conflicts.extend(resource_conflicts)
        
        # 2. 死锁检测
        deadlock_conflicts = self._detect_deadlocks(task)
        conflicts.extend(deadlock_conflicts)
        
        # 3. 优先级反转检测
        priority_conflicts = self._detect_priority_inversion(task)
        conflicts.extend(priority_conflicts)
        
        # 记录冲突
        for conflict in conflicts:
            self.conflict_history.append(conflict)
            self.scheduler_stats['conflicts_resolved'] += 1
            
            # 保存到数据库
            self._save_conflict_to_db(conflict)
        
        return conflicts
    
    def _detect_resource_conflicts(self, task: ScheduledTask) -> List[ConflictResolution]:
        """检测资源冲突"""
        conflicts = []
        
        # 检查任务间的资源竞争
        for running_task in self.running_tasks.values():
            # 如果两个任务需要相同类型的资源
            task_resource_types = {req.resource_type for req in task.resource_requirements}
            running_resource_types = {req.resource_type for req in running_task.resource_requirements}
            
            common_types = task_resource_types & running_resource_types
            
            for resource_type in common_types:
                # 检查具体资源
                task_req = next((req for req in task.resource_requirements if req.resource_type == resource_type), None)
                running_req = next((req for req in running_task.resource_requirements if req.resource_type == resource_type), None)
                
                if task_req and running_req:
                    # 检查是否可能发生冲突
                    if self._resources_may_conflict(resource_type, task_req, running_req):
                        conflict = ConflictResolution(
                            conflict_id=f"conflict_{int(time.time())}_{len(conflicts)}",
                            task_id=task.task_id,
                            conflict_type="resource_competition",
                            resolution="priority_based_allocation",
                            resolved_at=datetime.now(),
                            details={
                                "resource_type": resource_type.value,
                                "task_requirement": task_req.required_amount,
                                "running_task_requirement": running_req.required_amount,
                                "running_task_id": running_task.task_id,
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                        
                        conflicts.append(conflict)
        
        return conflicts
    
    def _resources_may_conflict(self, resource_type: ResourceType, req1: TaskResourceRequirement, 
                              req2: TaskResourceRequirement) -> bool:
        """判断资源是否可能冲突"""
        # 简单的冲突检测：如果两种需求都较大，可能冲突
        threshold = 0.7  # 70%的资源使用率阈值
        
        total_resource = 0.0
        for resource_id, amount in self.resource_pool[resource_type].items():
            total_resource += amount
        
        if total_resource > 0:
            # 如果两个任务的总需求超过阈值
            total_requirement = req1.required_amount + req2.required_amount
            return total_requirement / total_resource > threshold
        
        return False
    
    def _detect_deadlocks(self, task: ScheduledTask) -> List[ConflictResolution]:
        """检测死锁"""
        conflicts = []
        
        # 构建资源分配图
        allocation_graph = self._build_allocation_graph(task)
        
        # 检测循环等待（死锁的核心条件）
        if self._has_cycle(allocation_graph):
            conflict = ConflictResolution(
                conflict_id=f"deadlock_{int(time.time())}",
                task_id=task.task_id,
                conflict_type="deadlock_potential",
                resolution="resource_preemption_or_rollback",
                resolved_at=datetime.now(),
                details={
                    "detection_method": "cycle_detection",
                    "graph_nodes": list(allocation_graph.keys()),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            conflicts.append(conflict)
        
        return conflicts
    
    def _build_allocation_graph(self, new_task: ScheduledTask) -> Dict[str, Set[str]]:
        """构建资源分配图"""
        graph = defaultdict(set)
        
        # 添加新任务的资源需求
        for req in new_task.resource_requirements:
            # 检查哪些运行中任务占用了这些资源
            for alloc in self.allocated_resources:
                if (alloc.resource_type == req.resource_type and 
                    alloc.allocated_amount >= req.required_amount * 0.3):  # 占用30%以上视为竞争
                    
                    graph[new_task.task_id].add(alloc.task_id)
        
        # 添加现有任务的依赖关系
        for dep_task_id, dependents in self.dependency_graph.items():
            for dependent_id in dependents:
                graph[dependent_id].add(dep_task_id)
        
        return graph
    
    def _has_cycle(self, graph: Dict[str, Set[str]]) -> bool:
        """检测图中是否存在环（死锁检测）"""
        visited = set()
        recursion_stack = set()
        
        def dfs(node: str) -> bool:
            if node in recursion_stack:
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            recursion_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if dfs(neighbor):
                    return True
            
            recursion_stack.remove(node)
            return False
        
        for node in graph.keys():
            if dfs(node):
                return True
        
        return False
    
    def _detect_priority_inversion(self, task: ScheduledTask) -> List[ConflictResolution]:
        """检测优先级反转"""
        conflicts = []
        
        # 检查是否存在低优先级任务持有高优先级任务需要的资源
        if task.priority >= 3:  # 高优先级任务
            for alloc in self.allocated_resources:
                running_task = self.running_tasks.get(alloc.task_id)
                
                if running_task and running_task.priority < task.priority:
                    # 检查是否持有新任务需要的资源
                    for req in task.resource_requirements:
                        if (alloc.resource_type == req.resource_type and 
                            alloc.allocated_amount >= req.required_amount * 0.5):
                            
                            conflict = ConflictResolution(
                                conflict_id=f"priority_inversion_{int(time.time())}",
                                task_id=task.task_id,
                                conflict_type="priority_inversion",
                                resolution="priority_inheritance_or_ceiling",
                                resolved_at=datetime.now(),
                                details={
                                    "high_priority_task": task.task_id,
                                    "low_priority_task": running_task.task_id,
                                    "resource_type": req.resource_type.value,
                                    "timestamp": datetime.now().isoformat()
                                }
                            )
                            
                            conflicts.append(conflict)
        
        return conflicts
    
    def _record_performance_metrics(self):
        """记录性能指标"""
        try:
            # 计算资源利用率
            resource_utilization = {}
            
            for resource_type, resources in self.resource_pool.items():
                total_capacity = 0.0
                total_allocated = 0.0
                
                for resource_id, capacity in resources.items():
                    total_capacity += capacity
                    
                    allocated = sum(
                        alloc.allocated_amount 
                        for alloc in self.allocated_resources 
                        if alloc.resource_id == resource_id
                    )
                    
                    total_allocated += allocated
                
                if total_capacity > 0:
                    utilization = total_allocated / total_capacity
                    resource_utilization[resource_type.value] = utilization
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO scheduler_performance 
                (pending_tasks_count, running_tasks_count, avg_scheduling_time_ms, 
                 avg_task_duration_seconds, resource_utilization, conflicts_resolved_count, scheduler_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                sum(len(tasks) for tasks in self.pending_tasks.values()),
                len(self.running_tasks),
                self.scheduler_stats['avg_scheduling_time_ms'],
                self.scheduler_stats['avg_task_duration_seconds'],
                json.dumps(resource_utilization),
                self.scheduler_stats['conflicts_resolved'],
                self.scheduler_mode.value
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"调度性能指标已记录: {len(self.running_tasks)} 个运行中任务")
            
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
    
    def _monitor_system_performance(self):
        """监控系统性能"""
        while self.scheduler_active:
            try:
                # 自适应调整调度策略
                self._adaptive_scheduling_adjustment()
                
                # 定期清理
                self._periodic_cleanup()
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                logger.error(f"系统性能监控失败: {e}")
                time.sleep(60)
    
    def _adaptive_scheduling_adjustment(self):
        """自适应调整调度策略"""
        # 检查系统负载
        running_task_count = len(self.running_tasks)
        total_resources = sum(
            sum(amount for amount in resources.values())
            for resources in self.resource_pool.values()
        )
        
        if running_task_count == 0:
            # 系统空闲，可以接受更多任务
            self.scheduler_mode = SchedulerMode.FIFO
            logger.debug("系统空闲，切换到FIFO模式")
        
        elif running_task_count > 10:
            # 高负载，切换到负载均衡模式
            self.scheduler_mode = SchedulerMode.LOAD_BALANCED
            logger.debug("系统高负载，切换到负载均衡模式")
        
        elif any(util > 0.8 for util in self.scheduler_stats['resource_utilization'].values()):
            # 资源紧张，切换到优先级模式
            self.scheduler_mode = SchedulerMode.PRIORITY
            logger.debug("资源紧张，切换到优先级模式")
        
        else:
            # 正常负载，使用自适应模式
            self.scheduler_mode = SchedulerMode.ADAPTIVE
    
    def _periodic_cleanup(self):
        """定期清理"""
        # 清理旧的冲突记录（保留最近7天）
        cutoff = datetime.now() - timedelta(days=7)
        self.conflict_history = [c for c in self.conflict_history if c.resolved_at > cutoff]
    
    def _save_task_to_db(self, task: ScheduledTask):
        """保存任务到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO scheduled_tasks 
                (task_id, avatar_id, priority, estimated_duration_seconds, 
                 resource_requirements, dependencies, deadline, status, 
                 scheduled_time, start_time, completion_time, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.avatar_id,
                task.priority,
                task.estimated_duration_seconds,
                json.dumps([asdict(req) for req in task.resource_requirements]),
                json.dumps(task.dependencies),
                task.deadline.isoformat() if task.deadline else None,
                task.status.value,
                task.scheduled_time.isoformat() if task.scheduled_time else None,
                task.start_time.isoformat() if task.start_time else None,
                task.completion_time.isoformat() if task.completion_time else None,
                task.created_at.isoformat()
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"保存任务失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _update_task_status(self, task: ScheduledTask):
        """更新任务状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE scheduled_tasks 
                SET status = ?, scheduled_time = ?, start_time = ?, completion_time = ?
                WHERE task_id = ?
            """, (
                task.status.value,
                task.scheduled_time.isoformat() if task.scheduled_time else None,
                task.start_time.isoformat() if task.start_time else None,
                task.completion_time.isoformat() if task.completion_time else None,
                task.task_id
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _save_allocation_to_db(self, allocation: ResourceAllocation):
        """保存资源分配到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO resource_allocations 
                (resource_id, resource_type, allocated_amount, task_id, avatar_id, allocation_time, expected_release_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                allocation.resource_id,
                allocation.resource_type.value,
                allocation.allocated_amount,
                allocation.task_id,
                allocation.avatar_id,
                allocation.allocation_time.isoformat(),
                allocation.expected_release_time.isoformat() if allocation.expected_release_time else None
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"保存资源分配失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _update_allocation_release_time(self, allocation: ResourceAllocation):
        """更新资源分配的释放时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE resource_allocations 
                SET actual_release_time = ?
                WHERE resource_id = ? AND task_id = ?
            """, (
                datetime.now().isoformat(),
                allocation.resource_id,
                allocation.task_id
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"更新资源释放时间失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _save_conflict_to_db(self, conflict: ConflictResolution):
        """保存冲突解决记录到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO conflict_resolutions 
                (conflict_id, task_id, conflict_type, resolution, resolved_at, resolution_details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                conflict.conflict_id,
                conflict.task_id,
                conflict.conflict_type,
                conflict.resolution,
                conflict.resolved_at.isoformat(),
                json.dumps(conflict.details)
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"保存冲突记录失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_scheduler_report(self) -> Dict[str, Any]:
        """获取调度器报告"""
        return {
            "scheduler_mode": self.scheduler_mode.value,
            "pending_tasks": sum(len(tasks) for tasks in self.pending_tasks.values()),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "conflicts_resolved": self.scheduler_stats['conflicts_resolved'],
            "resource_utilization": dict(self.scheduler_stats['resource_utilization']),
            "timestamp": datetime.now().isoformat()
        }


# 全局调度器实例
_global_scheduler = None

def get_global_scheduler() -> TaskScheduler:
    """获取全局调度器实例"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = TaskScheduler()
    return _global_scheduler


def create_sample_task_requirements() -> List[TaskResourceRequirement]:
    """创建示例任务资源需求"""
    return [
        TaskResourceRequirement(
            resource_type=ResourceType.CPU,
            required_amount=2.0,
            max_wait_time_seconds=30.0,
            priority=3
        ),
        TaskResourceRequirement(
            resource_type=ResourceType.MEMORY,
            required_amount=4.0,
            max_wait_time_seconds=45.0,
            priority=2
        ),
        TaskResourceRequirement(
            resource_type=ResourceType.API_QUOTA,
            required_amount=100.0,
            max_wait_time_seconds=60.0,
            priority=1
        )
    ]


def main():
    """测试任务调度器"""
    scheduler = TaskScheduler()
    
    print("任务调度器测试开始...")
    
    # 提交几个测试任务
    task_ids = []
    
    for i in range(3):
        task_id = scheduler.submit_task(
            avatar_id=f"avatar_{i+1}",
            priority=random.randint(1, 4),
            estimated_duration_seconds=random.uniform(2.0, 10.0),
            resource_requirements=create_sample_task_requirements(),
            dependencies=[],
            deadline=datetime.now() + timedelta(hours=1)
        )
        
        if task_id:
            task_ids.append(task_id)
            print(f"提交任务 {i+1}: {task_id}")
    
    print(f"共提交 {len(task_ids)} 个任务")
    
    # 等待任务执行
    time.sleep(5)
    
    # 获取调度器报告
    report = scheduler.get_scheduler_report()
    print(f"\n调度器报告:")
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")
    
    # 停止调度器
    scheduler.scheduler_active = False
    
    print("\n任务调度器测试完成")


if __name__ == "__main__":
    main()