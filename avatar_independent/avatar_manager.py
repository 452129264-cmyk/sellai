#!/usr/bin/env python3
"""
分身管理器 v2.5.0
管理多个独立分身，负责创建、调度和协调
"""

import os
import sys
import json
import time
import uuid
import threading
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入独立分身模块
from avatar_process import (
    IndependentAvatar, AvatarMemory, MessageQueue,
    Personality, Skill, AvatarState,
    create_avatar_from_template
)
from avatar_protocol import (
    AvatarProtocol, AvatarMessage, MessageType, Priority,
    ProtocolHandler, CollaborationPattern
)


class ManagerState(str, Enum):
    """管理器状态"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class AvatarProfile:
    """分身档案"""
    avatar_id: str
    name: str
    template: str
    personality: Dict[str, Any]
    skills: List[Dict[str, Any]]
    created_at: float
    status: str
    metrics: Dict[str, Any] = field(default_factory=dict)


class AvatarManager:
    """分身管理器 - 管理多个独立分身"""
    
    def __init__(self, base_path: str = "avatar_independent/data"):
        self.base_path = base_path
        self.avatars: Dict[str, IndependentAvatar] = {}
        self.profiles: Dict[str, AvatarProfile] = {}
        self.global_queue = MessageQueue("global", base_path)
        self.state = ManagerState.INITIALIZING
        
        # 协作关系图
        self.collaboration_graph: Dict[str, List[str]] = defaultdict(list)
        
        # 协议处理器
        self.protocol_handler = ProtocolHandler()
        
        # 线程锁
        self.lock = threading.RLock()
        
        # 历史记录
        self.message_history: List[Dict[str, Any]] = []
        self.max_history = 1000
        
        # 确保目录存在
        self._ensure_directories()
        
        # 启动管理器
        self._start()
        
        logger.info("AvatarManager 初始化完成")
    
    def _ensure_directories(self):
        """确保必要目录存在"""
        os.makedirs(os.path.join(self.base_path, "avatars"), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "queues"), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "logs"), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "profiles"), exist_ok=True)
    
    def _start(self):
        """启动管理器"""
        self.state = ManagerState.RUNNING
        logger.info("AvatarManager 已启动")
    
    def _stop(self):
        """停止管理器"""
        self.state = ManagerState.STOPPED
        for avatar in self.avatars.values():
            avatar.stop()
        logger.info("AvatarManager 已停止")
    
    # ============================================================
    # 分身创建与管理
    # ============================================================
    
    def create_avatar(self, name: str, template: str = "general_assistant",
                     personality: Optional[Dict[str, Any]] = None,
                     skills: Optional[List[Dict[str, Any]]] = None) -> str:
        """创建新的独立分身"""
        with self.lock:
            avatar_id = f"avatar_{uuid.uuid4().hex[:8]}"
            
            # 如果提供了自定义人格，使用自定义人格
            if personality:
                pers = Personality(
                    name=name,
                    tone=personality.get("tone", "professional"),
                    language=personality.get("language", "中文"),
                    expertise=personality.get("expertise", []),
                    work_style=personality.get("work_style", "balanced"),
                    communication_style=personality.get("communication_style", "direct")
                )
                skill_objects = []
                if skills:
                    for s in skills:
                        skill_objects.append(Skill(
                            skill_id=s.get("skill_id", str(uuid.uuid4())[:8]),
                            name=s.get("name", "未命名技能"),
                            description=s.get("description", ""),
                            level=s.get("level", 3),
                            enabled=s.get("enabled", True),
                            config=s.get("config", {})
                        ))
                
                avatar = IndependentAvatar(
                    avatar_id=avatar_id,
                    personality=pers,
                    skills=skill_objects,
                    base_path=self.base_path
                )
            else:
                # 从模板创建
                avatar = create_avatar_from_template(
                    template_id=template,
                    avatar_id=avatar_id,
                    base_path=self.base_path
                )
                avatar.personality.name = name
            
            # 启动独立运行
            avatar.start()
            
            # 保存到管理器
            self.avatars[avatar_id] = avatar
            
            # 创建档案
            self.profiles[avatar_id] = AvatarProfile(
                avatar_id=avatar_id,
                name=avatar.personality.name,
                template=template,
                personality=avatar.personality.to_dict(),
                skills=[s.to_dict() for s in avatar.skills.values()],
                created_at=time.time(),
                status="running",
                metrics={
                    "tasks_completed": 0,
                    "thoughts": 0,
                    "collaborations": 0
                }
            )
            
            # 保存档案到文件
            self._save_profile(avatar_id)
            
            logger.info(f"创建新分身: {avatar_id} ({name})")
            return avatar_id
    
    def remove_avatar(self, avatar_id: str) -> bool:
        """移除分身"""
        with self.lock:
            if avatar_id not in self.avatars:
                return False
            
            # 停止分身
            self.avatars[avatar_id].stop()
            
            # 从管理器移除
            del self.avatars[avatar_id]
            del self.profiles[avatar_id]
            
            # 删除档案文件
            profile_path = os.path.join(self.base_path, "profiles", f"{avatar_id}.json")
            if os.path.exists(profile_path):
                os.remove(profile_path)
            
            logger.info(f"移除分身: {avatar_id}")
            return True
    
    def get_avatar(self, avatar_id: str) -> Optional[IndependentAvatar]:
        """获取分身实例"""
        return self.avatars.get(avatar_id)
    
    def list_avatars(self) -> List[Dict[str, Any]]:
        """列出所有分身"""
        return [
            {
                "avatar_id": pid,
                "name": p.name,
                "template": p.template,
                "status": p.status,
                "created_at": p.created_at,
                "metrics": p.metrics
            }
            for pid, p in self.profiles.items()
        ]
    
    def get_avatar_status(self, avatar_id: str) -> Optional[Dict[str, Any]]:
        """获取分身详细状态"""
        avatar = self.avatars.get(avatar_id)
        if not avatar:
            return None
        return avatar.get_status()
    
    # ============================================================
    # 任务分配与调度
    # ============================================================
    
    def assign_task(self, avatar_id: str, task_type: str, 
                   task_data: Dict[str, Any],
                   priority: int = 1) -> Optional[str]:
        """给指定分身分配任务"""
        avatar = self.avatars.get(avatar_id)
        if not avatar:
            logger.warning(f"分身不存在: {avatar_id}")
            return None
        
        message = AvatarProtocol.create_task_message(
            from_id="manager",
            to_id=avatar_id,
            task_type=task_type,
            task_data=task_data,
            priority=Priority(priority),
            correlation_id=str(uuid.uuid4())
        )
        
        # 通过消息队列发送
        success = avatar.inbox.send(message.to_dict(), priority=priority)
        
        if success:
            logger.info(f"任务已分配给 {avatar_id}: {task_type}")
            return message.message_id
        return None
    
    def assign_task_auto(self, task_type: str, task_data: Dict[str, Any],
                        required_skills: Optional[List[str]] = None,
                        priority: int = 1) -> Optional[str]:
        """自动分配任务给最合适的分身"""
        candidates = []
        
        for avatar_id, avatar in self.avatars.items():
            if avatar.state != AvatarState.OFFLINE:
                # 计算匹配度
                match_score = self._calculate_match_score(
                    avatar, task_type, required_skills
                )
                if match_score > 0:
                    candidates.append((avatar_id, match_score, avatar))
        
        if not candidates:
            # 如果没有合适的分身，随机选择一个
            if self.avatars:
                avatar = list(self.avatars.values())[0]
                avatar_id = list(self.avatars.keys())[0]
            else:
                return None
        else:
            # 选择匹配度最高的
            candidates.sort(key=lambda x: x[1], reverse=True)
            avatar_id, _, avatar = candidates[0]
        
        return self.assign_task(avatar_id, task_type, task_data, priority)
    
    def _calculate_match_score(self, avatar: IndependentAvatar,
                              task_type: str,
                              required_skills: Optional[List[str]]) -> float:
        """计算分身与任务的匹配度"""
        score = 0.0
        
        # 基于技能的匹配
        if required_skills:
            matched_skills = 0
            for skill_id in required_skills:
                if skill_id in avatar.skills:
                    matched_skills += avatar.skills[skill_id].level
            score += matched_skills / len(required_skills) * 50
        
        # 基于任务类型的历史表现
        memory_stats = avatar.memory.get_stats()
        task_key = f"task_{task_type}"
        if task_key in memory_stats.get("type_distribution", {}):
            score += 20
        
        # 基于当前负载（负载低的优先）
        inbox_size = avatar.inbox.get_queue_size()
        score += max(0, 30 - inbox_size * 5)
        
        return score
    
    def broadcast(self, message_type: str, content: Dict[str, Any],
                 exclude_ids: Optional[List[str]] = None) -> Dict[str, bool]:
        """广播消息给所有分身"""
        results = {}
        exclude_ids = exclude_ids or []
        
        for avatar_id, avatar in self.avatars.items():
            if avatar_id not in exclude_ids:
                message = AvatarProtocol.create_message(
                    from_id="manager",
                    to_id=avatar_id,
                    msg_type=MessageType(message_type),
                    content=content
                )
                success = avatar.inbox.send(message.to_dict())
                results[avatar_id] = success
        
        logger.info(f"广播消息给 {len(results)} 个分身")
        return results
    
    # ============================================================
    # 分身协作
    # ============================================================
    
    def setup_collaboration(self, avatar_ids: List[str],
                           pattern: str = "peer_to_peer") -> bool:
        """设置分身协作关系"""
        if pattern == "peer_to_peer":
            collab = CollaborationPattern.peer_to_peer(avatar_ids)
        elif pattern == "master_worker":
            collab = CollaborationPattern.master_worker(
                master_id=avatar_ids[0],
                worker_ids=avatar_ids[1:]
            )
        elif pattern == "hub_spoke":
            collab = CollaborationPattern.hub_spoke(
                hub_id=avatar_ids[0],
                spoke_ids=avatar_ids[1:]
            )
        else:
            return False
        
        # 保存协作关系
        for avatar_id in avatar_ids:
            self.collaboration_graph[avatar_id] = avatar_ids
        
        logger.info(f"设置协作关系: {pattern}, 参与者: {avatar_ids}")
        return True
    
    def request_collaboration(self, from_id: str, to_ids: List[str],
                            collaboration_type: str,
                            task_data: Dict[str, Any]) -> Optional[str]:
        """请求分身协作"""
        from_avatar = self.avatars.get(from_id)
        if not from_avatar:
            return None
        
        message = AvatarProtocol.create_collaboration_message(
            from_id=from_id,
            to_id=to_ids,
            collaboration_type=collaboration_type,
            task_data=task_data
        )
        
        results = {}
        for to_id in to_ids:
            to_avatar = self.avatars.get(to_id)
            if to_avatar:
                success = to_avatar.inbox.send(message.to_dict())
                results[to_id] = success
        
        logger.info(f"协作请求 from {from_id} to {to_ids}: {collaboration_type}")
        return message.message_id
    
    def share_learning(self, from_id: str, experience: Dict[str, Any],
                      lesson: str, share_with_all: bool = True) -> Dict[str, bool]:
        """分享学习经验给其他分身"""
        from_avatar = self.avatars.get(from_id)
        if not from_avatar:
            return {}
        
        targets = list(self.avatars.keys()) if share_with_all else []
        if from_id in targets:
            targets.remove(from_id)
        
        message = AvatarProtocol.create_learn_message(
            from_id=from_id,
            to_id=targets,
            experience=experience,
            lesson=lesson
        )
        
        results = {}
        for to_id in targets:
            to_avatar = self.avatars.get(to_id)
            if to_avatar:
                success = to_avatar.inbox.send(message.to_dict())
                results[to_id] = success
        
        # 自己也学习
        from_avatar.memory.learn(experience)
        
        return results
    
    # ============================================================
    # 消息与对话
    # ============================================================
    
    def send_message(self, from_id: str, to_id: str,
                    message_type: str, content: Dict[str, Any]) -> bool:
        """分身之间发送消息"""
        from_avatar = self.avatars.get(from_id)
        to_avatar = self.avatars.get(to_id)
        
        if not from_avatar or not to_avatar:
            return False
        
        message = AvatarProtocol.create_message(
            from_id=from_id,
            to_id=to_id,
            msg_type=MessageType(message_type),
            content=content
        )
        
        success = to_avatar.inbox.send(message.to_dict())
        
        # 记录到历史
        self._record_message(message)
        
        return success
    
    def get_conversation_history(self, avatar_id: Optional[str] = None,
                                limit: int = 50) -> List[Dict[str, Any]]:
        """获取对话历史"""
        history = self.message_history
        
        if avatar_id:
            history = [
                m for m in history
                if m.get("from") == avatar_id or m.get("to") == avatar_id
            ]
        
        return history[-limit:]
    
    def _record_message(self, message: AvatarMessage):
        """记录消息到历史"""
        self.message_history.append(message.to_dict())
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
    
    # ============================================================
    # 记忆与知识
    # ============================================================
    
    def get_avatar_memory(self, avatar_id: str, 
                         query: Optional[str] = None,
                         memory_type: Optional[str] = None,
                         limit: int = 10) -> List[Dict[str, Any]]:
        """获取分身记忆"""
        avatar = self.avatars.get(avatar_id)
        if not avatar:
            return []
        
        if query:
            return avatar.memory.recall(query, memory_type, limit)
        else:
            return avatar.memory.get_recent_memories(hours=24, limit=limit)
    
    def get_collective_knowledge(self, topic: str, 
                                 limit_per_avatar: int = 3) -> Dict[str, List]:
        """获取所有分身的集体知识"""
        results = {}
        for avatar_id, avatar in self.avatars.items():
            memories = avatar.memory.recall(topic, limit=limit_per_avatar)
            if memories:
                results[avatar_id] = memories
        return results
    
    # ============================================================
    # 档案管理
    # ============================================================
    
    def _save_profile(self, avatar_id: str):
        """保存分身档案到文件"""
        profile = self.profiles.get(avatar_id)
        if not profile:
            return
        
        profile_path = os.path.join(self.base_path, "profiles", f"{avatar_id}.json")
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump({
                "avatar_id": profile.avatar_id,
                "name": profile.name,
                "template": profile.template,
                "personality": profile.personality,
                "skills": profile.skills,
                "created_at": profile.created_at,
                "status": profile.status,
                "metrics": profile.metrics
            }, f, ensure_ascii=False, indent=2)
    
    def load_profiles(self):
        """加载所有分身档案"""
        profile_dir = os.path.join(self.base_path, "profiles")
        if not os.path.exists(profile_dir):
            return
        
        for filename in os.listdir(profile_dir):
            if filename.endswith('.json'):
                profile_path = os.path.join(profile_dir, filename)
                try:
                    with open(profile_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    avatar_id = data.get("avatar_id")
                    if avatar_id and avatar_id not in self.avatars:
                        # 重新创建分身
                        avatar = create_avatar_from_template(
                            template_id=data.get("template", "general_assistant"),
                            avatar_id=avatar_id,
                            base_path=self.base_path
                        )
                        avatar.start()
                        self.avatars[avatar_id] = avatar
                        self.profiles[avatar_id] = AvatarProfile(**data)
                        
                        logger.info(f"加载分身档案: {avatar_id}")
                except Exception as e:
                    logger.error(f"加载档案失败 {filename}: {e}")
    
    def update_metrics(self, avatar_id: str, metrics: Dict[str, Any]):
        """更新分身指标"""
        if avatar_id in self.profiles:
            self.profiles[avatar_id].metrics.update(metrics)
            self._save_profile(avatar_id)
    
    # ============================================================
    # 状态与统计
    # ============================================================
    
    def get_manager_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        total_tasks = sum(p.metrics.get("tasks_completed", 0) 
                         for p in self.profiles.values())
        total_thoughts = sum(p.metrics.get("thoughts", 0) 
                           for p in self.profiles.values())
        total_collaborations = sum(p.metrics.get("collaborations", 0) 
                                  for p in self.profiles.values())
        
        return {
            "state": self.state.value,
            "avatar_count": len(self.avatars),
            "total_tasks_completed": total_tasks,
            "total_thoughts": total_thoughts,
            "total_collaborations": total_collaborations,
            "global_queue_size": self.global_queue.get_queue_size(),
            "message_history_size": len(self.message_history),
            "collaboration_patterns": len(self.collaboration_graph)
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        avatar_stats = []
        for avatar_id, avatar in self.avatars.items():
            status = avatar.get_status()
            avatar_stats.append(status)
        
        return {
            "manager": self.get_manager_status(),
            "avatars": avatar_stats
        }


# 全局管理器实例
_global_manager: Optional[AvatarManager] = None


def get_manager(base_path: str = "avatar_independent/data") -> AvatarManager:
    """获取全局管理器实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = AvatarManager(base_path)
    return _global_manager


def reset_manager():
    """重置全局管理器"""
    global _global_manager
    if _global_manager:
        _global_manager._stop()
    _global_manager = None
