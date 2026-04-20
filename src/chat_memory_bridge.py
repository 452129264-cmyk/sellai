#!/usr/bin/env python3
"""
聊天记忆桥接模块

此模块作为现有聊天系统与永久记忆系统的桥梁：
1. 拦截聊天消息存储请求，自动加密并同步到Notebook LM
2. 提供实时同步与后台批量同步
3. 确保与Memory V2系统兼容
4. 提供API接口供聊天服务器调用
"""

import os
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Callable, TYPE_CHECKING
from functools import wraps

# 导入现有聊天管理器
try:
    from src.chat_manager import ChatManager as BaseChatManager
    HAS_BASE_CHAT_MANAGER = True
except ImportError:
    HAS_BASE_CHAT_MANAGER = False
    print("警告: 未找到基础chat_manager，将使用简化实现")

# 导入永久记忆系统
if TYPE_CHECKING:
    from src.chat_permanent_memory import ChatPermanentMemory

try:
    from src.chat_permanent_memory import ChatPermanentMemory as _ChatPermanentMemory
    HAS_PERMANENT_MEMORY = True
except ImportError:
    HAS_PERMANENT_MEMORY = False
    _ChatPermanentMemory = None
    print("警告: 未找到chat_permanent_memory，永久记忆功能将不可用")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CHAT_MEMORY_BRIDGE - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatMemoryBridge:
    """
    聊天记忆桥接类
    
    功能：
    1. 包装现有的聊天管理器，拦截消息存储
    2. 自动加密并同步消息到Notebook LM
    3. 提供实时和批量同步
    4. 确保数据一致性
    """
    
    def __init__(self, 
                 base_chat_manager: Optional[Any] = None,
                 memory_system: Optional[Any] = None):
        """
        初始化聊天记忆桥接
        
        Args:
            base_chat_manager: 基础聊天管理器实例
            memory_system: 永久记忆系统实例
        """
        # 基础聊天管理器
        if base_chat_manager:
            self.base_manager = base_chat_manager
        elif HAS_BASE_CHAT_MANAGER:
            self.base_manager = BaseChatManager()
        else:
            self.base_manager = None
            logger.warning("未提供基础聊天管理器，聊天记忆桥接功能受限")
        
        # 永久记忆系统
        if memory_system:
            self.memory = memory_system
        elif HAS_PERMANENT_MEMORY:
            try:
                self.memory = _ChatPermanentMemory()
                logger.info("聊天永久记忆系统初始化成功")
            except Exception as e:
                self.memory = None
                logger.error(f"聊天永久记忆系统初始化失败: {e}")
        else:
            self.memory = None
            logger.warning("永久记忆系统不可用，记忆同步功能将不可用")
        
        # 同步队列
        self.sync_queue = []
        self.queue_lock = threading.Lock()
        self.sync_thread = None
        self.sync_active = False
        
        # 同步统计
        self.sync_stats = {
            'total_messages': 0,
            'synced_messages': 0,
            'failed_messages': 0,
            'last_sync_time': None
        }
        
        # 启动后台同步线程
        self.start_background_sync()
        
        logger.info("聊天记忆桥接初始化完成")
    
    def add_message(self, room_id: str, sender_id: str, content: str,
                   message_type: str = "text", metadata: Dict = None) -> Dict:
        """
        添加聊天消息（重写基础方法）
        
        功能：
        1. 调用基础聊天管理器存储消息
        2. 将消息加入同步队列
        3. 实时同步（可选）
        """
        # 调用基础管理器存储消息
        if self.base_manager:
            try:
                message = self.base_manager.add_message(
                    room_id, sender_id, content, message_type, metadata
                )
            except Exception as e:
                logger.error(f"基础聊天管理器存储消息失败: {e}")
                # 创建简化消息对象
                message = {
                    'id': str(uuid.uuid4()),
                    'room_id': room_id,
                    'sender_id': sender_id,
                    'content': content,
                    'type': message_type,
                    'timestamp': datetime.now().isoformat(),
                    'metadata': metadata or {}
                }
        else:
            # 如果没有基础管理器，创建简化消息
            message = {
                'id': str(uuid.uuid4()),
                'room_id': room_id,
                'sender_id': sender_id,
                'content': content,
                'type': message_type,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
        
        # 将消息加入同步队列
        sync_task = {
            'type': 'chat_message',
            'data': message,
            'timestamp': datetime.now().isoformat(),
            'attempts': 0
        }
        
        with self.queue_lock:
            self.sync_queue.append(sync_task)
        
        logger.info(f"消息加入同步队列: {message['id'][:8]}, 发送者: {sender_id}")
        
        # 触发即时同步（如果启用）
        if self.memory and hasattr(self, 'immediate_sync'):
            threading.Thread(target=self._sync_single_message, args=(message,), daemon=True).start()
        
        return message
    
    def _sync_single_message(self, message: Dict):
        """同步单条消息"""
        if not self.memory:
            return
        
        try:
            # 确保知识库存在
            self.memory.ensure_knowledge_bases()
            
            # 解析元数据
            metadata = message.get('metadata', {})
            metadata.update({
                'room_id': message['room_id'],
                'sender_id': message['sender_id'],
            })
            
            # 加密聊天内容
            encrypted_content, updated_metadata = self.memory.encrypt_chat_content(
                message['content'], metadata
            )
            
            # 创建知识文档
            from src.notebook_lm_integration import KnowledgeDocument, ContentType, SourceType
            
            document = KnowledgeDocument(
                title=f"聊天消息_{message['id'][:8]}",
                content=encrypted_content,
                content_type=ContentType.JSON,
                source_type=SourceType.USER_INTERACTION,
                source_id=message['id'],
                tags=["chat", "message", message.get('type', 'text')],
                metadata=updated_metadata
            )
            
            # 导入到知识库
            if self.memory.chat_kb_id:
                doc_id = self.memory.nli.add_document(
                    knowledge_base_id=self.memory.chat_kb_id,
                    document=document
                )
                
                # 更新同步状态
                self.sync_stats['synced_messages'] += 1
                logger.info(f"消息实时同步成功: {message['id'][:8]} -> {doc_id[:8]}")
            else:
                logger.warning("聊天记录知识库ID不可用，消息同步跳过")
                
        except Exception as e:
            self.sync_stats['failed_messages'] += 1
            logger.error(f"消息实时同步失败: {message.get('id', 'unknown')} - {e}")
    
    def get_messages(self, room_id: str, limit: int = 100,
                    before_timestamp: str = None) -> List[Dict]:
        """
        获取聊天记录（重写基础方法）
        """
        if self.base_manager:
            return self.base_manager.get_messages(room_id, limit, before_timestamp)
        else:
            logger.warning("基础聊天管理器不可用，返回空消息列表")
            return []
    
    def get_user_chat_history(self, user_id: str, 
                            days_back: int = 30,
                            limit: int = 50) -> List[Dict]:
        """
        获取用户聊天历史
        
        Args:
            user_id: 用户ID
            days_back: 获取最近N天的记录
            limit: 最大返回数量
            
        Returns:
            聊天历史列表
        """
        # 如果有永久记忆系统，优先使用其搜索功能
        if self.memory:
            try:
                return self.memory.get_user_chat_history(user_id, days_back, limit)
            except Exception as e:
                logger.error(f"使用永久记忆系统获取用户历史失败: {e}")
        
        # 回退到基础管理器
        if self.base_manager:
            # 需要实现获取用户历史的功能
            # 这里简化处理，返回空列表
            logger.warning("基础聊天管理器的用户历史功能未实现")
        
        return []
    
    def search_chat_messages(self, query: str,
                           filters: Optional[Dict] = None,
                           limit: int = 20) -> List[Dict]:
        """
        搜索聊天记录
        
        Args:
            query: 搜索关键词
            filters: 过滤条件
            limit: 返回结果限制
            
        Returns:
            搜索结果列表
        """
        if self.memory:
            return self.memory.search_chat_messages(query, filters, limit)
        else:
            logger.warning("永久记忆系统不可用，搜索功能不可用")
            return []
    
    def start_background_sync(self, interval_seconds: int = 300):
        """
        启动后台批量同步
        
        Args:
            interval_seconds: 同步间隔（秒）
        """
        if not self.memory:
            logger.warning("永久记忆系统不可用，无法启动后台同步")
            return
        
        def sync_worker():
            logger.info(f"后台批量同步服务启动，间隔: {interval_seconds}秒")
            
            while self.sync_active:
                try:
                    # 处理同步队列
                    with self.queue_lock:
                        if self.sync_queue:
                            tasks_to_sync = self.sync_queue[:]
                            self.sync_queue = []
                        else:
                            tasks_to_sync = []
                    
                    # 如果有待同步任务
                    if tasks_to_sync:
                        logger.info(f"批量同步 {len(tasks_to_sync)} 条消息")
                        
                        # 这里可以实现批量同步逻辑
                        # 暂时简化处理
                        for task in tasks_to_sync:
                            if task['type'] == 'chat_message':
                                self._sync_single_message(task['data'])
                    
                    # 执行增量同步（从数据库读取新消息）
                    if self.memory and hasattr(self.memory, 'import_chat_messages'):
                        result = self.memory.import_chat_messages(limit=100, days_back=1)
                        logger.info(f"增量同步完成: {result.get('imported', 0)}条消息")
                    
                    # 等待下次同步
                    time.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error(f"后台同步异常: {e}")
                    time.sleep(60)  # 出错后等待1分钟再重试
        
        if not self.sync_active:
            self.sync_active = True
            self.sync_thread = threading.Thread(target=sync_worker, daemon=True)
            self.sync_thread.start()
            logger.info("后台批量同步服务已启动")
        else:
            logger.warning("后台同步服务已在运行中")
    
    def stop_background_sync(self):
        """停止后台同步"""
        if self.sync_active:
            self.sync_active = False
            if self.sync_thread:
                self.sync_thread.join(timeout=10)
            logger.info("后台同步服务已停止")
        else:
            logger.warning("后台同步服务未运行")
    
    def sync_relationships(self) -> Dict[str, Any]:
        """
        同步社交关系
        
        Returns:
            同步结果统计
        """
        if not self.memory:
            return {"error": "永久记忆系统不可用", "imported": 0}
        
        try:
            result = self.memory.import_social_relationships(limit=200)
            logger.info(f"社交关系同步完成: {result}")
            return result
        except Exception as e:
            logger.error(f"社交关系同步失败: {e}")
            return {"error": str(e), "imported": 0}
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """
        获取同步统计信息
        
        Returns:
            同步统计数据
        """
        stats = self.sync_stats.copy()
        
        if self.memory:
            try:
                memory_stats = self.memory.get_sync_stats()
                stats['memory_stats'] = memory_stats
            except Exception as e:
                stats['memory_stats_error'] = str(e)
        
        stats['queue_size'] = len(self.sync_queue)
        stats['timestamp'] = datetime.now().isoformat()
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            系统健康状态
        """
        health = {
            'timestamp': datetime.now().isoformat(),
            'base_manager_available': bool(self.base_manager),
            'memory_system_available': bool(self.memory),
            'sync_active': self.sync_active,
            'queue_size': len(self.sync_queue)
        }
        
        # 检查内存系统状态
        if self.memory:
            try:
                stats = self.memory.get_sync_stats()
                health['memory_stats'] = stats
            except Exception as e:
                health['memory_stats_error'] = str(e)
        
        return health


# 便捷装饰器
def with_memory_sync(func: Callable) -> Callable:
    """
    装饰器：自动同步聊天消息到永久记忆
    
    用法：
    @with_memory_sync
    def add_message(...):
        ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 调用原始函数
        result = func(*args, **kwargs)
        
        # 提取消息信息
        # 这里假设函数返回消息字典
        if isinstance(result, dict) and 'id' in result:
            # 异步同步
            threading.Thread(
                target=_async_sync_message,
                args=(result,),
                daemon=True
            ).start()
        
        return result
    
    return wrapper


def _async_sync_message(message: Dict):
    """异步同步消息"""
    # 这里简化实现
    logger.info(f"异步同步消息: {message.get('id', 'unknown')[:8]}")


# 全局桥接实例
_bridge_instance = None

def get_chat_memory_bridge() -> ChatMemoryBridge:
    """
    获取聊天记忆桥接实例（单例模式）
    
    Returns:
        ChatMemoryBridge实例
    """
    global _bridge_instance
    
    if _bridge_instance is None:
        _bridge_instance = ChatMemoryBridge()
    
    return _bridge_instance


if __name__ == "__main__":
    print("聊天记忆桥接模块测试")
    print("=" * 60)
    
    # 创建桥接实例
    bridge = ChatMemoryBridge()
    
    # 健康检查
    health = bridge.health_check()
    print(f"系统状态:")
    print(f"  基础聊天管理器: {'可用' if health['base_manager_available'] else '不可用'}")
    print(f"  永久记忆系统: {'可用' if health['memory_system_available'] else '不可用'}")
    print(f"  后台同步: {'运行中' if health['sync_active'] else '未运行'}")
    print(f"  同步队列大小: {health['queue_size']}")
    
    if 'memory_stats' in health:
        stats = health['memory_stats']
        print(f"\n记忆系统统计:")
        print(f"  已同步: {stats.get('total_synced', 0)}条")
        print(f"  待同步: {stats.get('total_pending', 0)}条")
    
    print("\n桥接模块测试完成")
    print("注意：完整功能需要配置有效的Notebook LM API密钥和数据库连接")