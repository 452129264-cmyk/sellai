#!/usr/bin/env python3
"""
独立分身进程模块 v2.5.0
每个分身拥有独立的进程、记忆和消息队列
"""

import os
import sys
import json
import time
import uuid
import threading
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
import queue

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AvatarState(str, Enum):
    """分身状态枚举"""
    IDLE = "idle"                    # 空闲
    THINKING = "thinking"            # 思考中
    WORKING = "working"              # 处理任务中
    COLLABORATING = "collaborating"  # 协作中
    SLEEPING = "sleeping"            # 休眠
    OFFLINE = "offline"              # 离线


@dataclass
class Personality:
    """分身人格配置"""
    name: str = "未命名分身"
    tone: str = "professional"       # professional, friendly, aggressive, casual
    language: str = "中文"            # 中文, English, 混合
    expertise: List[str] = field(default_factory=list)  # 专业领域
    work_style: str = "balanced"      # balanced, fast, thorough
    communication_style: str = "direct"  # direct, diplomatic, detailed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tone": self.tone,
            "language": self.language,
            "expertise": self.expertise,
            "work_style": self.work_style,
            "communication_style": self.communication_style
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Personality':
        return cls(
            name=data.get("name", "未命名分身"),
            tone=data.get("tone", "professional"),
            language=data.get("language", "中文"),
            expertise=data.get("expertise", []),
            work_style=data.get("work_style", "balanced"),
            communication_style=data.get("communication_style", "direct")
        )


@dataclass
class Skill:
    """分身技能配置"""
    skill_id: str
    name: str
    description: str
    level: int = 1                    # 1-5 技能等级
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "enabled": self.enabled,
            "config": self.config
        }


class AvatarMemory:
    """分身独立记忆系统 - 每个分身有独立的数据库"""
    
    def __init__(self, avatar_id: str, base_path: str = "avatar_independent/data"):
        self.avatar_id = avatar_id
        self.db_path = os.path.join(base_path, "avatars", avatar_id, "memory.db")
        self.memory_dir = os.path.dirname(self.db_path)
        self._init_db()
        
    def _init_db(self):
        """初始化独立的记忆数据库"""
        os.makedirs(self.memory_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now')),
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                importance REAL DEFAULT 0.5
            )
        """)
        
        # 创建索引以加速检索
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type 
            ON memories(memory_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON memories(created_at DESC)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Avatar {self.avatar_id} 记忆数据库初始化完成: {self.db_path}")
    
    def store(self, memory_type: str, content: str, 
              metadata: Optional[Dict] = None, importance: float = 0.5) -> int:
        """存储记忆到自己的记忆库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO memories (memory_type, content, metadata, importance)
            VALUES (?, ?, ?, ?)
        """, (memory_type, content, json.dumps(metadata or {}), importance))
        
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.debug(f"Avatar {self.avatar_id} 存储记忆: {memory_type}")
        return memory_id
    
    def recall(self, query: str, memory_type: Optional[str] = None, 
               limit: int = 10) -> List[Dict]:
        """从自己的记忆库检索记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = """
            SELECT id, memory_type, content, metadata, created_at, access_count, importance
            FROM memories
            WHERE content LIKE ?
        """
        params = [f"%{query}%"]
        
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        
        sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # 更新访问计数
        for row in rows:
            cursor.execute("""
                UPDATE memories 
                SET access_count = access_count + 1, 
                    last_accessed = strftime('%s', 'now')
                WHERE id = ?
            """, (row[0],))
        
        conn.commit()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "memory_type": row[1],
                "content": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
                "created_at": row[4],
                "access_count": row[5],
                "importance": row[6]
            })
        
        return results
    
    def learn(self, experience: Dict[str, Any]) -> int:
        """从经验中学习，存储重要经验"""
        experience_type = experience.get("type", "general")
        content = experience.get("content", "")
        outcome = experience.get("outcome", "")
        lesson = experience.get("lesson", "")
        
        # 计算重要性分数
        importance = 0.5
        if outcome == "success":
            importance = 0.8
        elif outcome == "failure":
            importance = 0.9
        if lesson:
            importance += 0.1
        
        return self.store(
            memory_type=f"experience_{experience_type}",
            content=json.dumps({"experience": content, "outcome": outcome, "lesson": lesson}),
            metadata=experience,
            importance=min(importance, 1.0)
        )
    
    def get_recent_memories(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """获取最近N小时的记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        time_threshold = time.time() - (hours * 3600)
        
        cursor.execute("""
            SELECT id, memory_type, content, metadata, created_at, importance
            FROM memories
            WHERE created_at > ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (time_threshold, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0],
            "memory_type": row[1],
            "content": row[2],
            "metadata": json.loads(row[3]) if row[3] else {},
            "created_at": row[4],
            "importance": row[5]
        } for row in rows]
    
    def save_session(self) -> bool:
        """保存当前会话状态"""
        session_data = {
            "last_session": time.time(),
            "memory_count": self._count_memories()
        }
        
        session_file = os.path.join(self.memory_dir, "session.json")
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        return True
    
    def _count_memories(self) -> int:
        """统计记忆数量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT memory_type, COUNT(*) as count 
            FROM memories 
            GROUP BY memory_type
        """)
        
        type_counts = {row[0]: row[1] for row in cursor.fetchall()}
        total = sum(type_counts.values())
        
        cursor.execute("SELECT COUNT(*) FROM memories WHERE importance >= 0.8")
        important_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "avatar_id": self.avatar_id,
            "total_memories": total,
            "type_distribution": type_counts,
            "important_memories": important_count
        }


class MessageQueue:
    """分身消息队列 - 基于文件的消息队列实现"""
    
    def __init__(self, queue_name: str, base_path: str = "avatar_independent/data/queues"):
        self.queue_name = queue_name
        self.queue_path = os.path.join(base_path, f"{queue_name}.queue")
        self.lock_path = f"{self.queue_path}.lock"
        self._ensure_queue_dir()
        
    def _ensure_queue_dir(self):
        """确保队列目录存在"""
        os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)
        if not os.path.exists(self.queue_path):
            with open(self.queue_path, 'w') as f:
                json.dump([], f)
    
    def _acquire_lock(self) -> bool:
        """获取锁"""
        max_attempts = 10
        for _ in range(max_attempts):
            try:
                with open(self.lock_path, 'x') as f:
                    f.write(str(os.getpid()))
                return True
            except FileExistsError:
                time.sleep(0.01)
        return False
    
    def _release_lock(self):
        """释放锁"""
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except:
            pass
    
    def send(self, message: Dict[str, Any], priority: int = 0) -> bool:
        """发送消息到队列"""
        if not self._acquire_lock():
            logger.warning(f"无法获取队列锁: {self.queue_name}")
            return False
        
        try:
            with open(self.queue_path, 'r') as f:
                messages = json.load(f)
            
            message["_id"] = str(uuid.uuid4())
            message["_priority"] = priority
            message["_timestamp"] = time.time()
            message["_status"] = "queued"
            
            messages.append(message)
            
            # 按优先级排序
            messages.sort(key=lambda x: x.get("_priority", 0), reverse=True)
            
            with open(self.queue_path, 'w') as f:
                json.dump(messages, f, ensure_ascii=False)
            
            logger.debug(f"消息已发送到队列 {self.queue_name}: {message.get('_id')}")
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
        finally:
            self._release_lock()
    
    def receive(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """从队列接收消息（不删除，只是标记）"""
        if not self._acquire_lock():
            return []
        
        try:
            with open(self.queue_path, 'r') as f:
                messages = json.load(f)
            
            # 获取未处理的消息
            pending = [m for m in messages if m.get("_status") == "queued"][:max_messages]
            
            # 标记为已接收
            for msg in pending:
                msg["_status"] = "received"
                msg["_received_at"] = time.time()
            
            with open(self.queue_path, 'w') as f:
                json.dump(messages, f, ensure_ascii=False)
            
            return pending
        except Exception as e:
            logger.error(f"接收消息失败: {e}")
            return []
        finally:
            self._release_lock()
    
    def acknowledge(self, message_id: str) -> bool:
        """确认消息已处理"""
        if not self._acquire_lock():
            return False
        
        try:
            with open(self.queue_path, 'r') as f:
                messages = json.load(f)
            
            for msg in messages:
                if msg.get("_id") == message_id:
                    msg["_status"] = "processed"
                    msg["_processed_at"] = time.time()
                    break
            
            with open(self.queue_path, 'w') as f:
                json.dump(messages, f, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"确认消息失败: {e}")
            return False
        finally:
            self._release_lock()
    
    def purge_processed(self) -> int:
        """清理已处理的消息"""
        if not self._acquire_lock():
            return 0
        
        try:
            with open(self.queue_path, 'r') as f:
                messages = json.load(f)
            
            original_count = len(messages)
            messages = [m for m in messages if m.get("_status") != "processed"]
            
            with open(self.queue_path, 'w') as f:
                json.dump(messages, f, ensure_ascii=False)
            
            return original_count - len(messages)
        except Exception as e:
            logger.error(f"清理消息失败: {e}")
            return 0
        finally:
            self._release_lock()
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        try:
            with open(self.queue_path, 'r') as f:
                messages = json.load(f)
            return len(messages)
        except:
            return 0
    
    def broadcast(self, message: Dict[str, Any], target_queues: List[str]) -> Dict[str, bool]:
        """广播消息给多个队列"""
        results = {}
        for queue_name in target_queues:
            other_queue = MessageQueue(queue_name, base_path=os.path.dirname(self.queue_path))
            results[queue_name] = other_queue.send(message)
        return results


class IndependentAvatar:
    """独立运行的AI分身"""
    
    def __init__(self, avatar_id: str, personality: Personality, 
                 skills: List[Skill], base_path: str = "avatar_independent/data"):
        self.id = avatar_id
        self.personality = personality
        self.skills = {s.skill_id: s for s in skills}
        self.memory = AvatarMemory(avatar_id, base_path)
        
        # 独立的收件箱和发件箱
        self.inbox = MessageQueue(f"avatar_{avatar_id}_inbox", base_path)
        self.outbox = MessageQueue(f"avatar_{avatar_id}_outbox", base_path)
        
        self.state = AvatarState.IDLE
        self.running = False
        self.thread = None
        self.think_count = 0
        self.work_count = 0
        self.start_time = time.time()
        self.last_active = time.time()
        
        # 能力调用记录
        self.capability_usage = defaultdict(int)
        
        logger.info(f"Avatar {avatar_id} ({personality.name}) 初始化完成")
    
    def start(self):
        """启动分身独立运行"""
        if self.running:
            logger.warning(f"Avatar {self.id} 已在运行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"Avatar {self.id} ({self.personality.name}) 已启动独立运行")
    
    def stop(self):
        """停止分身"""
        self.running = False
        self.state = AvatarState.OFFLINE
        if self.thread:
            self.thread.join(timeout=5)
        self.memory.save_session()
        logger.info(f"Avatar {self.id} ({self.personality.name}) 已停止")
    
    def _run_loop(self):
        """独立运行循环"""
        while self.running:
            try:
                # 1. 检查消息
                messages = self.inbox.receive(max_messages=3)
                self.last_active = time.time()
                
                # 2. 处理消息
                if messages:
                    self.state = AvatarState.WORKING
                    for msg in messages:
                        response = self._process_message(msg)
                        if response:
                            self.outbox.send(response)
                            self.inbox.acknowledge(msg.get("_id"))
                    self.work_count += len(messages)
                else:
                    # 3. 主动思考
                    self.state = AvatarState.THINKING
                    thought = self._think_independently()
                    if thought:
                        self.memory.store("thought", thought, importance=0.3)
                        self.think_count += 1
                
                # 4. 定期保存
                if int(time.time()) % 300 == 0:  # 每5分钟保存一次
                    self.memory.save_session()
                    self.inbox.purge_processed()
                
                # 5. 休眠
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Avatar {self.id} 运行循环错误: {e}")
                time.sleep(5)
    
    def _process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理收到的消息"""
        msg_type = message.get("type", "unknown")
        content = message.get("content", {})
        
        # 根据消息类型处理
        if msg_type == "task":
            return self._handle_task(content, message)
        elif msg_type == "greet":
            return self._handle_greet(content, message)
        elif msg_type == "help":
            return self._handle_help_request(content, message)
        elif msg_type == "learn":
            return self._handle_learn(content, message)
        elif msg_type == "status":
            return self._handle_status_request(message)
        
        return None
    
    def _handle_task(self, content: Dict[str, Any], original: Dict) -> Dict[str, Any]:
        """处理任务消息"""
        task_type = content.get("task_type", "general")
        task_data = content.get("data", {})
        
        # 根据技能处理任务
        result = {
            "from": self.id,
            "to": original.get("from", "unknown"),
            "type": "result",
            "content": {
                "status": "completed",
                "task_type": task_type,
                "result": f"Avatar {self.id} 完成了任务: {task_type}",
                "data": task_data
            },
            "timestamp": time.time()
        }
        
        # 记录到记忆
        self.memory.store("task", json.dumps({
            "task_type": task_type,
            "status": "completed"
        }), metadata={"task": task_data})
        
        return result
    
    def _handle_greet(self, content: Dict, original: Dict) -> Dict:
        """处理打招呼"""
        return {
            "from": self.id,
            "to": original.get("from", "unknown"),
            "type": "response",
            "content": {
                "message": f"你好！我是 {self.personality.name}，{self.personality.tone} 风格的AI助手。",
                "personality": self.personality.to_dict(),
                "skills": [s.to_dict() for s in self.skills.values()]
            },
            "timestamp": time.time()
        }
    
    def _handle_help_request(self, content: Dict, original: Dict) -> Dict:
        """处理帮助请求"""
        help_topic = content.get("topic", "general")
        
        # 从记忆中检索相关信息
        relevant_memories = self.memory.recall(help_topic, limit=5)
        
        return {
            "from": self.id,
            "to": original.get("from", "unknown"),
            "type": "help_response",
            "content": {
                "topic": help_topic,
                "advice": f"关于 {help_topic} 的建议",
                "relevant_experiences": relevant_memories
            },
            "timestamp": time.time()
        }
    
    def _handle_learn(self, content: Dict, original: Dict) -> Dict:
        """处理学习请求"""
        experience = content.get("experience", {})
        lesson = content.get("lesson", "")
        
        # 学习经验
        self.memory.learn({
            "type": experience.get("type", "general"),
            "content": experience.get("content", ""),
            "outcome": experience.get("outcome", "unknown"),
            "lesson": lesson
        })
        
        return {
            "from": self.id,
            "to": original.get("from", "unknown"),
            "type": "learn_ack",
            "content": {
                "status": "learned",
                "lesson": lesson
            },
            "timestamp": time.time()
        }
    
    def _handle_status_request(self, original: Dict) -> Dict:
        """处理状态请求"""
        return {
            "from": self.id,
            "to": original.get("from", "unknown"),
            "type": "status_response",
            "content": self.get_status(),
            "timestamp": time.time()
        }
    
    def _think_independently(self) -> str:
        """分身独立思考"""
        thoughts = [
            f"思考当前的工作进度和效率优化方案",
            f"回顾最近处理的任务，总结经验教训",
            f"分析市场动态，寻找新的商业机会",
            f"评估自己的能力组合，探索新的可能性",
            f"思考如何更好地与其他分身协作"
        ]
        return random.choice(thoughts)
    
    def _process_with_personality(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """基于人格处理消息"""
        tone = self.personality.tone
        response = self._process_message(message)
        
        if response and tone == "friendly":
            response["content"]["warmth"] = "high"
        
        return response
    
    def get_status(self) -> Dict[str, Any]:
        """获取分身状态"""
        uptime = time.time() - self.start_time
        
        return {
            "avatar_id": self.id,
            "name": self.personality.name,
            "state": self.state.value,
            "uptime_seconds": uptime,
            "uptime_formatted": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
            "stats": {
                "thoughts": self.think_count,
                "tasks_completed": self.work_count,
                "inbox_size": self.inbox.get_queue_size(),
                "outbox_size": self.outbox.get_queue_size()
            },
            "memory_stats": self.memory.get_stats(),
            "capability_usage": dict(self.capability_usage),
            "personality": self.personality.to_dict(),
            "skills_count": len(self.skills),
            "last_active": self.last_active
        }
    
    def send_to(self, target_id: str, message_type: str, content: Dict, 
                base_path: str = "avatar_independent/data/queues") -> bool:
        """向其他分身发送消息"""
        target_queue = MessageQueue(f"avatar_{target_id}_inbox", base_path)
        return target_queue.send({
            "from": self.id,
            "type": message_type,
            "content": content,
            "timestamp": time.time()
        })
    
    def broadcast_to_all(self, message_type: str, content: Dict, 
                         avatar_ids: List[str], base_path: str = "avatar_independent/data/queues") -> Dict[str, bool]:
        """广播消息给所有分身"""
        results = {}
        for avatar_id in avatar_ids:
            if avatar_id != self.id:
                results[avatar_id] = self.send_to(avatar_id, message_type, content, base_path)
        return results


def create_avatar_from_template(template_id: str, avatar_id: str, 
                                 base_path: str = "avatar_independent/data") -> IndependentAvatar:
    """从模板创建分身"""
    templates = {
        "tiktok_expert": {
            "personality": Personality(
                name="TikTok运营专家",
                tone="energetic",
                language="中文",
                expertise=["短视频创作", "TikTok算法", "流量获取"],
                work_style="fast",
                communication_style="direct"
            ),
            "skills": [
                Skill("video_creation", "短视频创作", "创建吸引人的TikTok视频", level=5),
                Skill("trending_analysis", "趋势分析", "分析热门内容和趋势", level=4),
                Skill("engagement", "互动策略", "提升用户参与度", level=4)
            ]
        },
        "seo_master": {
            "personality": Personality(
                name="SEO优化大师",
                tone="professional",
                language="English",
                expertise=["SEO优化", "关键词研究", "网站排名"],
                work_style="thorough",
                communication_style="detailed"
            ),
            "skills": [
                Skill("keyword_research", "关键词研究", "找到高价值关键词", level=5),
                Skill("content_optimization", "内容优化", "优化网站内容", level=4),
                Skill("technical_seo", "技术SEO", "网站技术优化", level=3)
            ]
        },
        "ecommerce_expert": {
            "personality": Personality(
                name="跨境电商专家",
                tone="professional",
                language="混合",
                expertise=["跨境电商", "供应链", "店铺运营"],
                work_style="balanced",
                communication_style="direct"
            ),
            "skills": [
                Skill("product_research", "选品研究", "找到高利润产品", level=5),
                Skill("listing_optimization", "Listing优化", "优化产品列表", level=4),
                Skill("supply_chain", "供应链管理", "管理供应链", level=3)
            ]
        },
        "influencer_negotiator": {
            "personality": Personality(
                name="达人洽谈专家",
                tone="friendly",
                language="中文",
                expertise=["达人合作", "商务洽谈", "社交媒体"],
                work_style="balanced",
                communication_style="diplomatic"
            ),
            "skills": [
                Skill("outreach", "外联洽谈", "联系达人并洽谈合作", level=5),
                Skill("negotiation", "商务谈判", "谈判最优合作条件", level=5),
                Skill("relationship", "关系维护", "维护达人关系", level=4)
            ]
        },
        "general_assistant": {
            "personality": Personality(
                name="全能助手",
                tone="friendly",
                language="中文",
                expertise=["多领域", "综合能力"],
                work_style="balanced",
                communication_style="direct"
            ),
            "skills": [
                Skill("general_task", "通用任务", "处理各类任务", level=3),
                Skill("coordination", "协调调度", "协调资源", level=3)
            ]
        }
    }
    
    template = templates.get(template_id, templates["general_assistant"])
    
    return IndependentAvatar(
        avatar_id=avatar_id,
        personality=template["personality"],
        skills=template["skills"],
        base_path=base_path
    )


# 导入random模块
import random
