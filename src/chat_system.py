#!/usr/bin/env python3
"""
SellAI v3.0.0 - 聊天系统
Chat System with Permanent Memory
实时聊天与持久化记忆

功能：
- 聊天服务器
- 聊天管理
- 持久化记忆
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"
    COMMAND = "command"


@dataclass
class Message:
    message_id: str
    chat_id: str
    sender_id: str
    message_type: MessageType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    edited_at: Optional[str] = None
    read_by: List[str] = field(default_factory=list)


@dataclass
class Chat:
    chat_id: str
    name: str
    chat_type: str  # direct, group, channel
    members: List[str] = field(default_factory=list)
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_message_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChatServer:
    """聊天服务器"""
    
    def __init__(self, db_path: str = "data/shared_state/chat_server.db"):
        self.db_path = db_path
        self.chats: Dict[str, Chat] = {}
        self.messages: Dict[str, Message] = {}
        self.online_users: Dict[str, str] = {}  # user_id -> connection_id
        self._ensure_data_dir()
        logger.info("聊天服务器初始化完成")
    
    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def create_chat(self, name: str, chat_type: str, created_by: str,
                    members: List[str] = None) -> Chat:
        chat_id = f"chat_{uuid.uuid4().hex[:12]}"
        chat = Chat(
            chat_id=chat_id,
            name=name,
            chat_type=chat_type,
            created_by=created_by,
            members=members or [created_by]
        )
        self.chats[chat_id] = chat
        return chat
    
    def send_message(self, chat_id: str, sender_id: str,
                     message_type: MessageType, content: str,
                     metadata: Dict = None) -> Message:
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        message = Message(
            message_id=message_id,
            chat_id=chat_id,
            sender_id=sender_id,
            message_type=message_type,
            content=content,
            metadata=metadata or {}
        )
        self.messages[message_id] = message
        
        chat = self.chats.get(chat_id)
        if chat:
            chat.last_message_at = message.created_at
        
        return message
    
    def get_chat_messages(self, chat_id: str, limit: int = 50,
                          before: Optional[str] = None) -> List[Message]:
        messages = [m for m in self.messages.values() if m.chat_id == chat_id]
        if before:
            messages = [m for m in messages if m.created_at < before]
        messages.sort(key=lambda x: x.created_at, reverse=True)
        return messages[:limit]
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": "ChatServer",
            "total_chats": len(self.chats),
            "total_messages": len(self.messages),
            "online_users": len(self.online_users)
        }


class ChatPermanentMemory:
    """聊天持久化记忆"""
    
    def __init__(self, db_path: str = "data/shared_state/chat_memory.db"):
        self.db_path = db_path
        self.conversation_memories: Dict[str, List[Dict]] = {}
        self.user_preferences: Dict[str, Dict] = {}
        self.context_windows: Dict[str, List[str]] = {}
        self.max_context = 20
        self._ensure_data_dir()
        logger.info("聊天持久化记忆初始化完成")
    
    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def store_message(self, chat_id: str, sender_id: str,
                      content: str, metadata: Dict = None):
        if chat_id not in self.conversation_memories:
            self.conversation_memories[chat_id] = []
        
        memory = {
            "message_id": f"mem_{uuid.uuid4().hex[:8]}",
            "sender_id": sender_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.conversation_memories[chat_id].append(memory)
        
        # 维护上下文窗口
        if chat_id not in self.context_windows:
            self.context_windows[chat_id] = []
        self.context_windows[chat_id].append(memory["message_id"])
        
        # 限制上下文大小
        if len(self.context_windows[chat_id]) > self.max_context:
            old_id = self.context_windows[chat_id].pop(0)
    
    def get_conversation_context(self, chat_id: str,
                                 limit: int = 10) -> List[Dict]:
        memories = self.conversation_memories.get(chat_id, [])
        return memories[-limit:]
    
    def search_memories(self, chat_id: str, query: str,
                        limit: int = 10) -> List[Dict]:
        memories = self.conversation_memories.get(chat_id, [])
        query_lower = query.lower()
        results = [m for m in memories if query_lower in m["content"].lower()]
        return results[:limit]
    
    def get_user_preference(self, user_id: str, key: str,
                            default: Any = None) -> Any:
        return self.user_preferences.get(user_id, {}).get(key, default)
    
    def set_user_preference(self, user_id: str, key: str, value: Any):
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        self.user_preferences[user_id][key] = value


class ChatManager:
    """聊天管理器"""
    
    def __init__(self):
        self.server = ChatServer()
        self.memory = ChatPermanentMemory()
        logger.info("聊天管理器初始化完成")
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "module": "ChatManager",
            "server": self.server.get_status(),
            "memory": {
                "stored_conversations": len(self.memory.conversation_memories),
                "user_preferences": len(self.memory.user_preferences)
            }
        }


__all__ = ["ChatServer", "ChatPermanentMemory", "ChatManager", "Message", "Chat", "MessageType"]
