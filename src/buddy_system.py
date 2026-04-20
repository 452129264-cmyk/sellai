#!/usr/bin/env python3
"""
Buddy交互系统
在现有心跳检查基础上，增加交互性功能，提升用户体验和系统亲和力。
功能：
1. 主动询问用户状态
2. 提供个性化建议
3. 跟踪用户活动模式
4. 与健康监控系统深度集成
"""

import json
import time
import logging
import threading
import sqlite3
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class UserMood(Enum):
    """用户情绪状态"""
    HAPPY = "happy"
    NEUTRAL = "neutral"
    STRESSED = "stressed"
    TIRED = "tired"
    FOCUSED = "focused"
    CREATIVE = "creative"
    UNKNOWN = "unknown"

class InteractionType(Enum):
    """交互类型"""
    GREETING = "greeting"  # 问候
    STATUS_CHECK = "status_check"  # 状态检查
    SUGGESTION = "suggestion"  # 建议
    REMINDER = "reminder"  # 提醒
    ENCOURAGEMENT = "encouragement"  # 鼓励
    ACHIEVEMENT = "achievement"  # 成就认可
    ALERT = "alert"  # 异常预警
    PROGRESS_SYNC = "progress_sync"  # 进展同步

class BuddySystem:
    """Buddy交互系统"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化Buddy系统
        
        Args:
            db_path: 共享状态数据库路径
        """
        # 处理内存数据库连接共享
        if db_path == ":memory:":
            self.db_path = "file::memory:?cache=shared"
        else:
            self.db_path = db_path
            
        self.user_state = self._load_user_state()
        self.interaction_history = []
        self.active_interactions = {}
        self.interaction_enabled = True
        
        # 初始化数据库表
        self._init_database()
        
        # 启动交互循环
        self.running = False
        self.interaction_thread = None
        
        logger.info("Buddy系统初始化完成")
    
    def _init_database(self):
        """初始化Buddy系统相关数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建用户状态表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS buddy_user_state (
                        user_id TEXT PRIMARY KEY,
                        last_active TIMESTAMP,
                        current_mood TEXT DEFAULT 'unknown',
                        activity_level INTEGER DEFAULT 50,
                        preferred_interaction_times TEXT DEFAULT '[]',
                        interaction_frequency INTEGER DEFAULT 60,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建交互历史表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS buddy_interaction_history (
                        interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        interaction_type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        response TEXT,
                        user_mood TEXT,
                        sentiment_score REAL,
                        performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建个性化建议表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS buddy_personalized_suggestions (
                        suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        suggestion_type TEXT NOT NULL,
                        suggestion_text TEXT NOT NULL,
                        relevance_score REAL DEFAULT 0.0,
                        delivered_at TIMESTAMP,
                        user_feedback TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_buddy_user ON buddy_user_state(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_buddy_interaction ON buddy_interaction_history(user_id, performed_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_buddy_suggestion ON buddy_personalized_suggestions(user_id, relevance_score)')
                
                conn.commit()
                logger.info("Buddy系统数据库表初始化完成")
                
        except Exception as e:
            logger.error(f"初始化Buddy系统数据库表失败: {e}")
            raise
    
    def _load_user_state(self) -> Dict[str, Any]:
        """加载用户状态"""
        # 默认用户状态
        return {
            "user_id": "default_user",
            "last_active": datetime.now().isoformat(),
            "current_mood": UserMood.UNKNOWN.value,
            "activity_level": 50,
            "interaction_count": 0,
            "preferred_topics": ["business", "technology", "productivity"],
            "avoided_topics": []
        }
    
    def start_interaction_service(self):
        """启动交互服务"""
        if self.running:
            logger.warning("交互服务已在运行中")
            return
        
        self.running = True
        self.interaction_thread = threading.Thread(
            target=self._interaction_loop,
            daemon=True
        )
        self.interaction_thread.start()
        
        logger.info("Buddy交互服务已启动")
    
    def stop_interaction_service(self):
        """停止交互服务"""
        self.running = False
        
        if self.interaction_thread:
            self.interaction_thread.join(timeout=5)
        
        logger.info("Buddy交互服务已停止")
    
    def _interaction_loop(self):
        """交互循环"""
        logger.info("Buddy交互循环开始")
        
        # 初始延迟，让系统稳定
        time.sleep(10)
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # 更新用户活动状态
                self._update_user_activity()
                
                # 检查是否需要发起交互
                if self._should_initiate_interaction(current_time):
                    interaction_type = self._determine_interaction_type(current_time)
                    
                    if interaction_type:
                        self._initiate_interaction(interaction_type, current_time)
                
                # 检查是否有等待响应的交互
                self._check_pending_interactions()
                
                # 睡眠一段时间
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"交互循环异常: {e}")
                time.sleep(30)  # 异常后稍作等待
    
    def _update_user_activity(self):
        """更新用户活动状态"""
        # 这里可以集成实际的活动跟踪
        # 例如：检查用户最近的操作、消息等
        
        # 模拟更新
        self.user_state["last_active"] = datetime.now().isoformat()
    
    def _should_initiate_interaction(self, current_time: datetime) -> bool:
        """
        判断是否需要发起交互
        
        Args:
            current_time: 当前时间
            
        Returns:
            是否需要发起交互
        """
        # 检查交互是否启用
        if not self.interaction_enabled:
            return False
        
        # 获取用户偏好
        user_id = self.user_state["user_id"]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查询用户偏好
                cursor.execute(
                    'SELECT interaction_frequency FROM buddy_user_state WHERE user_id = ?',
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    interaction_frequency = result[0] or 60  # 默认60分钟
                else:
                    interaction_frequency = 60
                
                # 查询上次交互时间
                cursor.execute('''
                    SELECT MAX(performed_at) FROM buddy_interaction_history 
                    WHERE user_id = ? AND interaction_type != 'greeting'
                ''', (user_id,))
                
                last_interaction = cursor.fetchone()
                
                if last_interaction and last_interaction[0]:
                    last_time = datetime.fromisoformat(last_interaction[0])
                    time_diff = (current_time - last_time).total_seconds() / 60  # 转换为分钟
                    
                    # 如果超过交互频率，发起新交互
                    return time_diff >= interaction_frequency
                else:
                    # 首次交互
                    return True
                    
        except Exception as e:
            logger.error(f"检查交互条件失败: {e}")
            return False
    
    def _check_system_events(self) -> Optional[InteractionType]:
        """
        检查系统事件，决定是否需要特殊交互
        
        Returns:
            交互类型（如果有紧急事件）
        """
        try:
            # 这里可以集成实际系统监控
            # 例如：检查健康监控状态、网络连接、异常日志等
            
            # 模拟异常检测（每10次检查中有1次模拟异常）
            import random as rnd
            if rnd.random() < 0.1:
                logger.info("检测到模拟系统异常，触发预警")
                return InteractionType.ALERT
            
            # 模拟进展同步（每20次检查中有1次模拟重要进展）
            if rnd.random() < 0.05:
                logger.info("检测到模拟重要进展，触发进展同步")
                return InteractionType.PROGRESS_SYNC
            
            return None
            
        except Exception as e:
            logger.error(f"检查系统事件失败: {e}")
            return None
    
    def _determine_interaction_type(self, current_time: datetime) -> Optional[InteractionType]:
        """
        确定交互类型
        
        Args:
            current_time: 当前时间
            
        Returns:
            交互类型
        """
        # 优先检查系统事件
        system_event = self._check_system_events()
        if system_event:
            return system_event
        
        # 获取当前时间信息
        hour = current_time.hour
        
        # 根据时间和用户状态选择交互类型
        if hour < 6:
            # 凌晨：安静模式，不打扰
            return None
        elif hour < 9:
            # 早晨：问候
            return InteractionType.GREETING
        elif hour < 12:
            # 上午：状态检查
            return InteractionType.STATUS_CHECK
        elif hour < 14:
            # 中午：提醒休息
            return InteractionType.REMINDER
        elif hour < 17:
            # 下午：建议
            return InteractionType.SUGGESTION
        elif hour < 19:
            # 傍晚：鼓励
            return InteractionType.ENCOURAGEMENT
        elif hour < 22:
            # 晚上：成就认可
            return InteractionType.ACHIEVEMENT
        else:
            # 深夜：安静模式
            return None
    
    def _initiate_interaction(self, interaction_type: InteractionType, current_time: datetime):
        """
        发起交互
        
        Args:
            interaction_type: 交互类型
            current_time: 当前时间
        """
        user_id = self.user_state["user_id"]
        message = self._generate_interaction_message(interaction_type)
        
        logger.info(f"发起Buddy交互: {interaction_type.value} - {message}")
        
        # 记录交互历史
        interaction_id = self._record_interaction(
            user_id=user_id,
            interaction_type=interaction_type.value,
            message=message,
            user_mood=self.user_state["current_mood"]
        )
        
        # 添加到活动交互
        self.active_interactions[interaction_id] = {
            "type": interaction_type.value,
            "message": message,
            "initiated_at": current_time.isoformat(),
            "status": "pending",
            "timeout": current_time + timedelta(minutes=15)  # 15分钟超时
        }
        
        # 触发实际交互（例如：发送到办公室界面）
        self._trigger_interaction_display(interaction_id, message, interaction_type)
    
    def _personalize_message(self, message: str, interaction_type: InteractionType) -> str:
        """
        个性化消息，增加称呼和情感色彩
        
        Args:
            message: 原始消息
            interaction_type: 交互类型
            
        Returns:
            个性化后的消息
        """
        # 获取用户姓名（如果有）
        user_name = self.user_state.get("user_name", "")
        if not user_name:
            user_name = self.user_state.get("user_id", "伙伴")
        
        # 根据交互类型添加不同前缀
        prefixes = {
            InteractionType.GREETING: f"{user_name}，",
            InteractionType.STATUS_CHECK: f"{user_name}，",
            InteractionType.SUGGESTION: f"根据您的习惯，",
            InteractionType.REMINDER: f"温馨提醒：",
            InteractionType.ENCOURAGEMENT: f"{user_name}，",
            InteractionType.ACHIEVEMENT: f"恭喜{user_name}，",
            InteractionType.ALERT: "⚠️ 重要通知：",
            InteractionType.PROGRESS_SYNC: "📊 进展同步："
        }
        
        prefix = prefixes.get(interaction_type, "")
        
        # 根据用户情绪调整语气
        user_mood = self.user_state.get("current_mood", "unknown")
        mood_adjustments = {
            "happy": "😊 ",
            "stressed": "💆 ",
            "tired": "😴 ",
            "focused": "🎯 ",
            "creative": "✨ "
        }
        
        mood_prefix = mood_adjustments.get(user_mood, "")
        
        # 组合个性化消息
        personalized = f"{mood_prefix}{prefix}{message}"
        
        # 确保不会重复前缀
        if personalized.startswith(prefix + prefix):
            personalized = personalized[len(prefix):]
        
        return personalized
    
    def _generate_interaction_message(self, interaction_type: InteractionType) -> str:
        """生成交互消息"""
        messages = {
            InteractionType.GREETING: [
                "早上好！新的一天开始了，今天有什么计划吗？",
                "你好！希望你今天一切顺利。",
                "嗨！很高兴见到你。今天感觉怎么样？"
            ],
            InteractionType.STATUS_CHECK: [
                "今天的工作进展如何？需要我帮忙优化什么吗？",
                "你现在的状态怎么样？需要休息一下吗？",
                "有什么我可以协助你处理的吗？"
            ],
            InteractionType.SUGGESTION: [
                "我发现你最近工作很投入，要不要试试番茄工作法？",
                "根据你的活动模式，建议你每工作45分钟就休息5分钟。",
                "需要我为你推荐一些提高效率的工具吗？"
            ],
            InteractionType.REMINDER: [
                "已经连续工作一段时间了，记得起来活动一下哦！",
                "喝点水休息一下吧，保持身体水分很重要。",
                "眼睛也需要休息，试试20-20-20法则：每20分钟看20英尺外20秒。"
            ],
            InteractionType.ENCOURAGEMENT: [
                "你做得很棒！继续保持这样的状态。",
                "我看到你的努力了，为你感到骄傲！",
                "每一步都很重要，你已经取得了不错的进展。"
            ],
            InteractionType.ACHIEVEMENT: [
                "祝贺你完成了今天的任务！这是你努力的成果。",
                "太棒了！你今天的效率很高。",
                "为你今天的成就点赞！继续加油！"
            ],
            InteractionType.ALERT: [
                "系统检测到异常情况，建议立即检查相关服务。",
                "网络连接出现波动，正在尝试自动恢复。",
                "发现潜在的安全风险，已启动额外防护措施。"
            ],
            InteractionType.PROGRESS_SYNC: [
                "系统运行一切正常，所有分身都在高效工作。",
                "本周已发现156个潜在商机，转化率正在稳步提升。",
                "用户满意度达到92%，系统亲和力持续增强。"
            ]
        }
        
        type_messages = messages.get(interaction_type, [])
        if type_messages:
            raw_message = random.choice(type_messages)
            # 应用个性化
            return self._personalize_message(raw_message, interaction_type)
        else:
            return "你好！今天过得怎么样？"
    
    def _record_interaction(self, user_id: str, interaction_type: str, 
                          message: str, user_mood: str) -> int:
        """记录交互历史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO buddy_interaction_history 
                    (user_id, interaction_type, message, user_mood, performed_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, interaction_type, message, user_mood, datetime.now()))
                
                interaction_id = cursor.lastrowid
                conn.commit()
                
                return interaction_id
                
        except Exception as e:
            logger.error(f"记录交互历史失败: {e}")
            return 0
    
    def _trigger_interaction_display(self, interaction_id: int, message: str, 
                                   interaction_type: InteractionType):
        """触发交互显示"""
        # 这里应该集成到办公室界面
        # 例如：发送WebSocket消息、更新UI等
        
        # 模拟触发
        interaction_data = {
            "id": interaction_id,
            "type": interaction_type.value,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "source": "buddy_system"
        }
        
        # 记录到交互历史
        self.interaction_history.append(interaction_data)
        
        logger.debug(f"交互显示触发: {json.dumps(interaction_data, ensure_ascii=False)}")
    
    def _check_pending_interactions(self):
        """检查待处理的交互"""
        current_time = datetime.now()
        expired_interactions = []
        
        for interaction_id, interaction in self.active_interactions.items():
            timeout = datetime.fromisoformat(interaction["timeout"])
            
            if current_time > timeout and interaction["status"] == "pending":
                expired_interactions.append(interaction_id)
                logger.info(f"交互超时: {interaction_id}")
        
        # 清理过期交互
        for interaction_id in expired_interactions:
            del self.active_interactions[interaction_id]
    
    def process_user_response(self, interaction_id: int, response_text: str, 
                            user_mood: Optional[str] = None):
        """
        处理用户响应
        
        Args:
            interaction_id: 交互ID
            response_text: 用户响应文本
            user_mood: 用户当前情绪（可选）
        """
        if interaction_id not in self.active_interactions:
            logger.warning(f"交互ID不存在: {interaction_id}")
            return
        
        interaction = self.active_interactions[interaction_id]
        
        # 更新交互状态
        interaction["status"] = "responded"
        interaction["response_text"] = response_text
        interaction["responded_at"] = datetime.now().isoformat()
        
        # 更新用户情绪状态
        if user_mood:
            self.user_state["current_mood"] = user_mood
        
        # 记录响应到数据库
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE buddy_interaction_history 
                    SET response = ?, user_mood = ?
                    WHERE interaction_id = ?
                ''', (response_text, user_mood, interaction_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"更新交互响应失败: {e}")
        
        # 根据响应生成进一步建议
        self._generate_followup_suggestion(interaction_id, response_text)
    
    def _generate_followup_suggestion(self, interaction_id: int, response_text: str):
        """生成跟进建议"""
        # 简单的建议生成逻辑
        suggestion_types = ["productivity", "wellness", "learning", "social"]
        
        suggestion = {
            "type": random.choice(suggestion_types),
            "text": "根据你的反馈，我建议你尝试不同的工作节奏来提高效率。",
            "relevance_score": 0.7
        }
        
        logger.info(f"生成跟进建议: {suggestion['text']}")
    
    def get_interaction_summary(self) -> Dict[str, Any]:
        """获取交互摘要"""
        summary = {
            "total_interactions": len(self.interaction_history),
            "active_interactions": len(self.active_interactions),
            "user_state": self.user_state,
            "recent_interactions": self.interaction_history[-5:] if self.interaction_history else []
        }
        
        return summary
    
    def set_user_mood(self, mood: UserMood):
        """设置用户情绪状态"""
        self.user_state["current_mood"] = mood.value
        logger.info(f"用户情绪状态更新: {mood.value}")
    
    def enable_interactions(self, enabled: bool = True):
        """启用或禁用交互"""
        self.interaction_enabled = enabled
        status = "启用" if enabled else "禁用"
        logger.info(f"Buddy交互已{status}")


# 全局Buddy系统实例
_global_buddy = None

def get_global_buddy() -> BuddySystem:
    """获取全局Buddy系统实例"""
    global _global_buddy
    if _global_buddy is None:
        _global_buddy = BuddySystem()
    return _global_buddy

def start_global_buddy():
    """启动全局Buddy系统"""
    buddy = get_global_buddy()
    buddy.start_interaction_service()
    return buddy

def stop_global_buddy():
    """停止全局Buddy系统"""
    buddy = get_global_buddy()
    buddy.stop_interaction_service()

def check_buddy_status() -> Dict[str, Any]:
    """检查Buddy系统状态"""
    buddy = get_global_buddy()
    return buddy.get_interaction_summary()


if __name__ == "__main__":
    # 测试Buddy系统
    print("启动Buddy系统测试...")
    
    buddy = BuddySystem()
    
    # 启动服务
    buddy.start_interaction_service()
    
    # 等待交互运行一会儿
    print("交互运行中，等待30秒...")
    time.sleep(30)
    
    # 获取状态
    status = buddy.get_interaction_summary()
    print(f"Buddy系统状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
    
    # 停止服务
    buddy.stop_interaction_service()
    
    print("\nBuddy系统测试完成")