#!/usr/bin/env python3
"""
SellAI v3.0.0 - 任务调度与分发系统
Task Scheduler & Dispatcher
智能任务调度、队列管理、异步执行

功能：
- 定时任务调度
- 任务队列管理
- 异步任务执行
- 优先级调度
"""

import os
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0  # 最高
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4  # 最低


class TaskType(Enum):
    """任务类型"""
    SYNC = "sync"
    ASYNC = "async"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"
    WEBHOOK = "webhook"


@dataclass
class Task:
    """任务"""
    task_id: str
    task_type: str
    name: str
    description: str
    payload: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus
    handler: str  # 处理函数名
    timeout: int = 300  # 超时秒数
    retry_count: int = 0
    max_retries: int = 3
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduledTask:
    """定时任务"""
    schedule_id: str
    name: str
    handler: str
    cron_expression: str  # cron表达式
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskScheduler:
    """
    任务调度器
    
    管理定时任务和调度规则
    """
    
    def __init__(self, db_path: str = "data/shared_state/task_scheduler.db"):
        self.db_path = db_path
        self.tasks: Dict[str, Task] = {}
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.task_queue: List[str] = []  # 按优先级排序的任务ID
        self.handlers: Dict[str, Callable] = {}
        self._ensure_data_dir()
        logger.info("任务调度器初始化完成")
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def register_handler(self, name: str, handler: Callable):
        """注册任务处理器"""
        self.handlers[name] = handler
        logger.info(f"注册任务处理器: {name}")
    
    # ============================================================
    # 任务管理
    # ============================================================
    
    def create_task(
        self,
        name: str,
        handler: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        task_type: str = "sync",
        timeout: int = 300,
        scheduled_at: Optional[str] = None,
        **kwargs
    ) -> Task:
        """创建任务"""
        task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        if isinstance(priority, int):
            priority = TaskPriority(priority)
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            name=name,
            description=kwargs.get("description", ""),
            payload=payload,
            priority=priority,
            status=TaskStatus.PENDING,
            handler=handler,
            timeout=timeout,
            max_retries=kwargs.get("max_retries", 3),
            scheduled_at=scheduled_at,
            metadata=kwargs.get("metadata", {})
        )
        
        self.tasks[task_id] = task
        self._add_to_queue(task_id)
        
        logger.info(f"创建任务: {task_id} - {name} (优先级: {priority.name})")
        return task
    
    def _add_to_queue(self, task_id: str):
        """添加任务到队列"""
        task = self.tasks[task_id]
        
        if task.status != TaskStatus.PENDING:
            return
        
        # 按优先级插入
        inserted = False
        for i, q_task_id in enumerate(self.task_queue):
            q_task = self.tasks.get(q_task_id)
            if q_task and task.priority.value < q_task.priority.value:
                self.task_queue.insert(i, task_id)
                inserted = True
                break
        
        if not inserted:
            self.task_queue.append(task_id)
        
        task.status = TaskStatus.QUEUED
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        task.status = TaskStatus.CANCELLED
        if task_id in self.task_queue:
            self.task_queue.remove(task_id)
        
        logger.info(f"取消任务: {task_id}")
        return True
    
    def retry_task(self, task_id: str) -> Optional[Task]:
        """重试任务"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        if task.status != TaskStatus.FAILED:
            return None
        
        if task.retry_count >= task.max_retries:
            logger.warning(f"任务 {task_id} 已达最大重试次数")
            return None
        
        task.status = TaskStatus.PENDING
        task.retry_count += 1
        task.error = None
        self._add_to_queue(task_id)
        
        logger.info(f"重试任务: {task_id} (第{task.retry_count}次)")
        return task
    
    # ============================================================
    # 任务执行
    # ============================================================
    
    async def execute_task(self, task_id: str) -> Task:
        """执行任务"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        if task.status not in [TaskStatus.PENDING, TaskStatus.QUEUED]:
            raise ValueError(f"任务状态不可执行: {task.status.value}")
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        logger.info(f"开始执行任务: {task_id}")
        
        try:
            handler = self.handlers.get(task.handler)
            if not handler:
                raise ValueError(f"处理器不存在: {task.handler}")
            
            # 执行处理函数
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**task.payload)
            else:
                result = handler(**task.payload)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.result = result if isinstance(result, dict) else {"data": result}
            
            logger.info(f"任务完成: {task_id}")
        
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now().isoformat()
            task.error = str(e)
            
            logger.error(f"任务失败: {task_id} - {e}")
            
            # 触发自动重试
            if task.retry_count < task.max_retries:
                self.retry_task(task_id)
        
        return task
    
    def get_next_task(self) -> Optional[Task]:
        """获取下一个待执行任务"""
        while self.task_queue:
            task_id = self.task_queue.pop(0)
            task = self.tasks.get(task_id)
            
            if task and task.status == TaskStatus.QUEUED:
                return task
        
        return None
    
    # ============================================================
    # 定时任务
    # ============================================================
    
    def create_scheduled_task(
        self,
        name: str,
        handler: str,
        cron_expression: str,
        **kwargs
    ) -> ScheduledTask:
        """创建定时任务"""
        schedule_id = f"sched_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        scheduled = ScheduledTask(
            schedule_id=schedule_id,
            name=name,
            handler=handler,
            cron_expression=cron_expression,
            **kwargs
        )
        
        self.scheduled_tasks[schedule_id] = scheduled
        logger.info(f"创建定时任务: {schedule_id} - {name}")
        return scheduled
    
    def get_pending_tasks(
        self,
        priority: Optional[TaskPriority] = None,
        limit: int = 10
    ) -> List[Task]:
        """获取待处理任务"""
        tasks = [t for t in self.tasks.values() 
                if t.status in [TaskStatus.PENDING, TaskStatus.QUEUED]]
        
        if priority:
            if isinstance(priority, int):
                priority = TaskPriority(priority)
            tasks = [t for t in tasks if t.priority == priority]
        
        tasks.sort(key=lambda x: (x.priority.value, x.created_at))
        return tasks[:limit]
    
    # ============================================================
    # 统计
    # ============================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        tasks = list(self.tasks.values())
        
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = len([t for t in tasks if t.status == status])
        
        return {
            "total_tasks": len(tasks),
            "status_breakdown": status_counts,
            "queue_length": len(self.task_queue),
            "scheduled_tasks": len(self.scheduled_tasks),
            "active_handlers": len(self.handlers)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "module": "TaskScheduler",
            "version": "3.0.0",
            "status": "active",
            **self.get_stats()
        }


class TaskDispatcher:
    """
    任务分发器
    
    将任务分发到不同的工作器
    """
    
    def __init__(self):
        self.workers: Dict[str, Dict] = {}
        self.assignments: Dict[str, str] = {}  # task_id -> worker_id
        logger.info("任务分发器初始化完成")
    
    def register_worker(self, worker_id: str, capabilities: List[str],
                        capacity: int = 10):
        """注册工作器"""
        self.workers[worker_id] = {
            "worker_id": worker_id,
            "capabilities": capabilities,
            "capacity": capacity,
            "current_load": 0,
            "status": "available"
        }
        logger.info(f"注册工作器: {worker_id}")
    
    def assign_task(self, task_id: str, worker_id: str) -> bool:
        """分配任务到工作器"""
        worker = self.workers.get(worker_id)
        if not worker:
            return False
        
        if worker["current_load"] >= worker["capacity"]:
            return False
        
        worker["current_load"] += 1
        self.assignments[task_id] = worker_id
        
        logger.info(f"分配任务 {task_id} -> {worker_id}")
        return True
    
    def find_best_worker(self, required_capabilities: List[str]) -> Optional[str]:
        """找到最佳工作器"""
        available = [w for w in self.workers.values() 
                    if w["status"] == "available" and w["current_load"] < w["capacity"]]
        
        for cap in required_capabilities:
            candidates = [w for w in available if cap in w["capabilities"]]
            if candidates:
                # 选择负载最低的
                return min(candidates, key=lambda x: x["current_load"])["worker_id"]
        
        return None
    
    def complete_task(self, task_id: str):
        """任务完成"""
        worker_id = self.assignments.get(task_id)
        if worker_id and worker_id in self.workers:
            self.workers[worker_id]["current_load"] = max(0, self.workers[worker_id]["current_load"] - 1)
        
        if task_id in self.assignments:
            del self.assignments[task_id]
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "module": "TaskDispatcher",
            "version": "3.0.0",
            "status": "active",
            "total_workers": len(self.workers),
            "active_assignments": len(self.assignments)
        }


# 导出
__all__ = [
    "TaskScheduler",
    "TaskDispatcher",
    "Task",
    "ScheduledTask",
    "TaskStatus",
    "TaskPriority",
    "TaskType"
]
