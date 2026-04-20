#!/usr/bin/env python3
"""
最小可验证的统一调度器框架
基于任务123失败经验简化设计，只包含核心功能：
1. 任务队列管理与优先级调度
2. 分身注册与发现机制
3. 基础消息路由功能
4. 状态同步接口定义
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import uuid


# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - CORE-SCHEDULER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型枚举"""
    VOICE = "voice"  # 语音任务
    PAYMENT = "payment"  # 支付任务
    MARKET = "market"  # 市场任务
    AVATAR = "avatar"  # 分身任务
    ARMY = "army"  # 军团任务
    # 八大能力
    FIRECRAWL = "firecrawl"  # Firecrawl全域爬虫强化
    DEEPL = "deepl"  # DeepL全域多语种原生润色
    MULTILINGUAL = "multilingual"  # Multilingual原创合规校验
    RISK_COMPLIANCE = "risk_compliance"  # 智能风控合规系统
    BUSINESS_ANALYSIS = "business_analysis"  # 全品类商业数据分析模型
    VISUAL_GENERATION = "visual_generation"  # 高端全场景视觉生成能力
    VIDEO_CREATION = "video_creation"  # 全域短视频创作引擎
    SELF_EVOLUTION = "self_evolution"  # 自主迭代进化大脑


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """调度任务"""
    task_id: str
    task_type: TaskType
    priority: int  # 0-4: 紧急-高-中-低-后台
    payload: Dict[str, Any]
    created_at: datetime = None
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None  # 分身ID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Avatar:
    """分身信息"""
    avatar_id: str
    name: str
    capabilities: List[str]  # 能力列表
    status: str = "idle"  # idle, busy, offline
    load_factor: float = 0.0  # 负载因子 0.0-1.0
    last_heartbeat: Optional[datetime] = None


class CoreScheduler:
    """核心调度器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化核心调度器
        
        Args:
            db_path: 共享状态数据库路径（仅接口定义，实际不直接使用）
        """
        self.db_path = db_path
        
        # 任务队列：按优先级分组
        self.task_queues: Dict[int, List[Task]] = {
            0: [],  # 紧急
            1: [],  # 高
            2: [],  # 中
            3: [],  # 低
            4: []   # 后台
        }
        
        # 分身注册表
        self.avatar_registry: Dict[str, Avatar] = {}
        
        # 任务历史
        self.task_history: List[Task] = []
        
        # 性能统计
        self.stats = {
            "total_tasks_received": 0,
            "total_tasks_completed": 0,
            "total_tasks_failed": 0,
            "avg_processing_time_seconds": 0.0,
            "success_rate": 1.0
        }
        
        logger.info("核心调度器初始化完成")
    
    def register_avatar(self, avatar_id: str, name: str, capabilities: List[str]) -> bool:
        """
        注册分身
        
        Args:
            avatar_id: 分身ID
            name: 分身名称
            capabilities: 能力列表
            
        Returns:
            注册是否成功
        """
        if avatar_id in self.avatar_registry:
            logger.warning(f"分身已存在: {avatar_id}")
            return False
        
        avatar = Avatar(
            avatar_id=avatar_id,
            name=name,
            capabilities=capabilities,
            status="idle",
            load_factor=0.0,
            last_heartbeat=datetime.now()
        )
        
        self.avatar_registry[avatar_id] = avatar
        logger.info(f"分身注册成功: {avatar_id} ({name})，能力: {capabilities}")
        return True
    
    def submit_task(self, task_type: TaskType, priority: int, payload: Dict[str, Any]) -> Optional[str]:
        """
        提交任务
        
        Args:
            task_type: 任务类型
            priority: 优先级 0-4
            payload: 任务载荷
            
        Returns:
            任务ID，如提交失败则返回None
        """
        try:
            # 生成任务ID
            task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # 创建任务
            task = Task(
                task_id=task_id,
                task_type=task_type,
                priority=max(0, min(4, priority)),  # 确保在0-4范围内
                payload=payload
            )
            
            # 加入对应优先级队列
            queue_key = task.priority
            self.task_queues[queue_key].append(task)
            
            # 更新统计
            self.stats["total_tasks_received"] += 1
            
            logger.info(f"任务提交成功: {task_id}，类型: {task_type.value}，优先级: {priority}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            return None
    
    def get_next_task(self) -> Optional[Task]:
        """
        获取下一个待处理任务（按优先级）
        
        Returns:
            下一个任务，如无任务则返回None
        """
        # 按优先级从高到低检查
        for priority in [0, 1, 2, 3, 4]:
            queue = self.task_queues[priority]
            if queue:
                # 返回队列中的第一个任务
                return queue.pop(0)
        
        return None
    
    def assign_task(self, task_id: str, avatar_id: str) -> bool:
        """
        分配任务给分身
        
        Args:
            task_id: 任务ID
            avatar_id: 分身ID
            
        Returns:
            分配是否成功
        """
        # 查找任务（在所有优先级队列中查找）
        task = None
        for priority, queue in self.task_queues.items():
            for t in queue:
                if t.task_id == task_id:
                    task = t
                    break
            if task:
                break
        
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        if avatar_id not in self.avatar_registry:
            logger.error(f"分身不存在: {avatar_id}")
            return False
        
        # 更新任务状态
        task.status = TaskStatus.PROCESSING
        task.assigned_to = avatar_id
        task.started_at = datetime.now()
        
        # 更新分身状态
        avatar = self.avatar_registry[avatar_id]
        avatar.status = "busy"
        avatar.load_factor = min(1.0, avatar.load_factor + 0.2)  # 增加负载
        
        logger.info(f"任务分配成功: {task_id} → {avatar_id}")
        return True
    
    def complete_task(self, task_id: str, success: bool = True, result: Optional[Dict[str, Any]] = None) -> bool:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            success: 是否成功
            result: 任务结果
            
        Returns:
            完成操作是否成功
        """
        # 这里简化处理：直接将任务从队列移动到历史
        # 实际实现中需要根据任务状态查找
        
        # 查找任务（模拟查找）
        task_found = False
        for priority, queue in self.task_queues.items():
            for i, task in enumerate(queue):
                if task.task_id == task_id:
                    task_found = True
                    # 更新任务状态
                    task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    
                    # 如果有结果，保存到payload
                    if result:
                        task.payload["result"] = result
                    
                    # 移动到历史
                    self.task_history.append(task)
                    queue.pop(i)
                    
                    # 更新分身状态
                    if task.assigned_to:
                        avatar = self.avatar_registry.get(task.assigned_to)
                        if avatar:
                            avatar.status = "idle"
                            avatar.load_factor = max(0.0, avatar.load_factor - 0.2)
                    
                    # 更新统计
                    if success:
                        self.stats["total_tasks_completed"] += 1
                    else:
                        self.stats["total_tasks_failed"] += 1
                    
                    # 计算成功率和平均处理时间
                    total_processed = self.stats["total_tasks_completed"] + self.stats["total_tasks_failed"]
                    if total_processed > 0:
                        self.stats["success_rate"] = self.stats["total_tasks_completed"] / total_processed
                        
                        # 简化计算平均处理时间
                        if task.started_at and task.completed_at:
                            processing_time = (task.completed_at - task.started_at).total_seconds()
                            self.stats["avg_processing_time_seconds"] = (
                                self.stats["avg_processing_time_seconds"] * (total_processed - 1) + processing_time
                            ) / total_processed
                    
                    logger.info(f"任务完成: {task_id}，状态: {'成功' if success else '失败'}")
                    return True
        
        if not task_found:
            logger.warning(f"任务未找到: {task_id}")
            return False
        
        return True
    
    def find_best_avatar(self, required_capabilities: List[str]) -> Optional[str]:
        """
        查找最适合处理任务的分身
        
        Args:
            required_capabilities: 所需能力列表
            
        Returns:
            最佳分身ID，如无合适分身则返回None
        """
        best_avatar_id = None
        best_score = -1
        
        for avatar_id, avatar in self.avatar_registry.items():
            # 检查分身是否在线
            if avatar.status == "offline":
                continue
            
            # 计算能力匹配分数
            score = self._calculate_capability_match_score(avatar.capabilities, required_capabilities)
            
            # 如果分数为0，表示没有任何匹配能力，跳过这个分身
            if score == 0.0:
                continue
            
            # 考虑负载因子（负载越低越好）
            load_factor = avatar.load_factor
            adjusted_score = score * (1.0 - load_factor)
            
            if adjusted_score > best_score:
                best_score = adjusted_score
                best_avatar_id = avatar_id
        
        if best_avatar_id:
            logger.debug(f"找到最佳分身: {best_avatar_id}，匹配分数: {best_score:.2f}")
        
        return best_avatar_id
    
    def _calculate_capability_match_score(self, avatar_capabilities: List[str], 
                                         required_capabilities: List[str]) -> float:
        """
        计算能力匹配分数
        
        Args:
            avatar_capabilities: 分身能力列表
            required_capabilities: 所需能力列表
            
        Returns:
            匹配分数 0.0-1.0
        """
        if not required_capabilities:
            return 1.0
        
        matched = 0
        for req_cap in required_capabilities:
            if req_cap in avatar_capabilities:
                matched += 1
        
        # 如果没有任何匹配，返回0.0
        if matched == 0:
            return 0.0
        
        return matched / len(required_capabilities)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            系统状态信息
        """
        # 计算队列长度
        queue_lengths = {}
        total_queued = 0
        for priority, queue in self.task_queues.items():
            queue_lengths[f"priority_{priority}"] = len(queue)
            total_queued += len(queue)
        
        # 统计分身状态
        avatar_status = {"total": len(self.avatar_registry)}
        for status in ["idle", "busy", "offline"]:
            count = sum(1 for avatar in self.avatar_registry.values() if avatar.status == status)
            avatar_status[status] = count
        
        return {
            "timestamp": datetime.now().isoformat(),
            "queues": queue_lengths,
            "total_queued_tasks": total_queued,
            "avatar_status": avatar_status,
            "stats": self.stats,
            "task_history_count": len(self.task_history)
        }
    
    def sync_to_shared_state(self) -> bool:
        """
        同步状态到共享状态库（接口定义）
        
        Returns:
            同步是否成功（简化版本总是返回True）
        """
        # 实际实现中，这里会将关键状态信息写入共享状态库
        # 简化版本仅记录日志
        logger.info("状态同步到共享状态库（接口调用）")
        return True
    
    def load_from_shared_state(self) -> bool:
        """
        从共享状态库加载状态（接口定义）
        
        Returns:
            加载是否成功（简化版本总是返回True）
        """
        # 实际实现中，这里会从共享状态库加载关键状态信息
        # 简化版本仅记录日志
        logger.info("从共享状态库加载状态（接口调用）")
        return True


# 全局调度器实例
_global_core_scheduler = None


def get_global_core_scheduler() -> CoreScheduler:
    """获取全局核心调度器实例"""
    global _global_core_scheduler
    if _global_core_scheduler is None:
        _global_core_scheduler = CoreScheduler()
    return _global_core_scheduler


def create_sample_task() -> Dict[str, Any]:
    """创建示例任务载荷"""
    return {
        "description": "示例语音识别任务",
        "audio_data": "base64_encoded_audio_or_url",
        "language": "zh-CN",
        "callback_url": "http://example.com/callback"
    }


if __name__ == "__main__":
    """简单的功能验证"""
    print("核心调度器简单验证开始...")
    
    # 初始化调度器
    scheduler = CoreScheduler()
    
    # 注册几个分身
    scheduler.register_avatar("avatar_1", "语音助手", ["voice_recognition", "chinese", "english"])
    scheduler.register_avatar("avatar_2", "支付专家", ["payment_processing", "tax_calculation", "currency_conversion"])
    scheduler.register_avatar("avatar_3", "市场运营", ["market_analysis", "template_creation", "community_management"])
    
    # 提交几个任务
    task1_id = scheduler.submit_task(TaskType.VOICE, 1, create_sample_task())
    task2_id = scheduler.submit_task(TaskType.PAYMENT, 2, {"amount": 100, "currency": "USD"})
    
    print(f"提交的任务ID: {task1_id}, {task2_id}")
    
    # 获取下一个任务
    next_task = scheduler.get_next_task()
    if next_task:
        print(f"下一个任务: {next_task.task_id}, 类型: {next_task.task_type.value}")
        
        # 查找最佳分身
        best_avatar = scheduler.find_best_avatar(["voice_recognition", "chinese"])
        if best_avatar:
            print(f"最佳分身: {best_avatar}")
            # 分配任务
            scheduler.assign_task(next_task.task_id, best_avatar)
    
    # 获取系统状态
    status = scheduler.get_system_status()
    print(f"系统状态 - 总任务数: {status['total_queued_tasks']}, 分身状态: {status['avatar_status']}")
    
    print("核心调度器简单验证完成")