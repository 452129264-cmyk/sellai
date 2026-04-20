#!/usr/bin/env python3
"""
SellAI社交聊天API服务
提供RESTful API支持一对一私聊、群聊功能
"""

import os
import json
import uuid
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from queue import Queue

from flask import Flask, request, jsonify
from flask_cors import CORS

# 导入聊天管理器
try:
    from chat_manager import ChatManager
    HAS_CHAT_MANAGER = True
except ImportError:
    HAS_CHAT_MANAGER = False
    print("警告: 未找到chat_manager，聊天记录将仅保存在内存中")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 聊天管理器实例
chat_manager = None
if HAS_CHAT_MANAGER:
    try:
        chat_manager = ChatManager()
        logger.info("聊天消息将持久化到数据库")
    except Exception as e:
        logger.error(f"初始化聊天管理器失败: {e}")
        chat_manager = None

# 内存存储（备用）
class MemoryChatStore:
    """内存聊天存储（当数据库不可用时使用）"""
    
    def __init__(self):
        self.rooms = {}  # room_id -> room_info
        self.messages = defaultdict(list)  # room_id -> message_list
        self.users = {}  # user_id -> user_info
        self.user_rooms = defaultdict(list)  # user_id -> room_list
        self.room_users = defaultdict(list)  # room_id -> user_list
        self.message_status = defaultdict(dict)  # (message_id, user_id) -> status
        
        # 存储消息ID到房间的映射
        self.message_to_room = {}
    
    def create_private_room(self, user1_id: str, user2_id: str) -> str:
        """创建一对一私聊房间"""
        sorted_ids = sorted([user1_id, user2_id])
        room_id = f"private_{sorted_ids[0]}_{sorted_ids[1]}"
        
        if room_id not in self.rooms:
            now = datetime.now().isoformat()
            self.rooms[room_id] = {
                'room_id': room_id,
                'room_type': 'private',
                'room_name': None,
                'creator_id': user1_id,
                'created_at': now,
                'last_activity': now
            }
            
            # 添加成员
            for user_id in [user1_id, user2_id]:
                if user_id not in self.room_users[room_id]:
                    self.room_users[room_id].append(user_id)
                if room_id not in self.user_rooms[user_id]:
                    self.user_rooms[user_id].append(room_id)
            
            logger.info(f"内存存储: 创建私聊房间 {room_id}")
        
        return room_id
    
    def create_group_room(self, creator_id: str, room_name: str, member_ids: List[str]) -> str:
        """创建群聊房间"""
        room_id = f"group_{uuid.uuid4().hex[:8]}"
        
        now = datetime.now().isoformat()
        self.rooms[room_id] = {
            'room_id': room_id,
            'room_type': 'group',
            'room_name': room_name,
            'creator_id': creator_id,
            'created_at': now,
            'last_activity': now
        }
        
        # 添加所有成员
        for user_id in member_ids:
            if user_id not in self.room_users[room_id]:
                self.room_users[room_id].append(user_id)
            if room_id not in self.user_rooms[user_id]:
                self.user_rooms[user_id].append(room_id)
        
        logger.info(f"内存存储: 创建群聊房间 {room_id} ({room_name}), 成员数: {len(member_ids)}")
        
        return room_id
    
    def add_message(self, room_id: str, sender_id: str, content: str,
                   message_type: str = "text", metadata: Dict = None) -> Dict:
        """添加消息"""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        message = {
            'id': message_id,
            'room_id': room_id,
            'sender_id': sender_id,
            'content': content,
            'type': message_type,
            'timestamp': timestamp,
            'metadata': metadata or {}
        }
        
        # 存储消息
        self.messages[room_id].append(message)
        self.message_to_room[message_id] = room_id
        
        # 更新房间活动时间
        if room_id in self.rooms:
            self.rooms[room_id]['last_activity'] = timestamp
        
        # 初始化消息状态
        if room_id in self.room_users:
            for user_id in self.room_users[room_id]:
                status = 'delivered' if user_id == sender_id else 'sent'
                self.message_status[message_id][user_id] = status
        
        logger.info(f"内存存储: 添加消息 {message_id} 到房间 {room_id}")
        
        return message
    
    def get_messages(self, room_id: str, limit: int = 100,
                    before_timestamp: str = None) -> List[Dict]:
        """获取消息"""
        if room_id not in self.messages:
            return []
        
        messages = self.messages[room_id]
        
        # 按时间过滤
        if before_timestamp:
            messages = [msg for msg in messages if msg['timestamp'] < before_timestamp]
        
        # 按时间排序（最早的在前）
        messages.sort(key=lambda x: x['timestamp'])
        
        # 限制数量
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_user_rooms(self, user_id: str) -> List[Dict]:
        """获取用户房间列表"""
        room_ids = self.user_rooms.get(user_id, [])
        rooms = []
        
        for room_id in room_ids:
            if room_id in self.rooms:
                room_info = self.rooms[room_id].copy()
                # 添加成员数量
                room_info['member_count'] = len(self.room_users.get(room_id, []))
                # 添加最后消息时间
                if self.messages.get(room_id):
                    room_info['last_message_time'] = self.messages[room_id][-1]['timestamp']
                else:
                    room_info['last_message_time'] = room_info['created_at']
                
                rooms.append(room_info)
        
        return rooms

# 内存存储实例
memory_store = MemoryChatStore()

# 使用聊天管理器或内存存储
def get_store():
    """获取存储实例"""
    if chat_manager:
        return chat_manager
    return memory_store

# API端点
@app.route('/api/chat/health', methods=['GET'])
def health_check():
    """健康检查"""
    store = get_store()
    
    if hasattr(store, 'get_online_users'):
        online_users = store.get_online_users()
    else:
        online_users = []
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'storage_type': 'database' if chat_manager else 'memory',
        'online_users': len(online_users),
        'total_rooms': len(memory_store.rooms) if not chat_manager else 'N/A'
    })

@app.route('/api/chat/register', methods=['POST'])
def register_user():
    """注册用户（更新在线状态）"""
    data = request.get_json()
    
    user_id = data.get('user_id')
    user_info = data.get('user_info', {})
    device_info = data.get('device_info')
    socket_id = data.get('socket_id')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    # 更新用户在线状态
    store = get_store()
    if hasattr(store, 'update_user_presence'):
        store.update_user_presence(
            user_id=user_id,
            is_online=True,
            device_info=device_info,
            socket_id=socket_id
        )
    
    # 在内存存储中记录用户
    if store == memory_store:
        memory_store.users[user_id] = {
            **user_info,
            'last_seen': datetime.now().isoformat(),
            'online': True
        }
    
    logger.info(f"用户注册/上线: {user_id}")
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/unregister', methods=['POST'])
def unregister_user():
    """用户离线"""
    data = request.get_json()
    
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    # 更新用户在线状态
    store = get_store()
    if hasattr(store, 'update_user_presence'):
        store.update_user_presence(
            user_id=user_id,
            is_online=False
        )
    
    logger.info(f"用户离线: {user_id}")
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/rooms', methods=['GET'])
def get_user_rooms():
    """获取用户的房间列表"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    store = get_store()
    
    if hasattr(store, 'get_user_rooms'):
        rooms = store.get_user_rooms(user_id)
    else:
        rooms = memory_store.get_user_rooms(user_id)
    
    return jsonify({
        'user_id': user_id,
        'rooms': rooms,
        'count': len(rooms),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/rooms/private', methods=['POST'])
def create_private_room():
    """创建一对一私聊房间"""
    data = request.get_json()
    
    user1_id = data.get('user1_id')
    user2_id = data.get('user2_id')
    
    if not user1_id or not user2_id:
        return jsonify({'error': 'user1_id and user2_id required'}), 400
    
    store = get_store()
    
    if hasattr(store, 'create_private_room'):
        room_id = store.create_private_room(user1_id, user2_id)
    else:
        room_id = memory_store.create_private_room(user1_id, user2_id)
    
    return jsonify({
        'room_id': room_id,
        'user_ids': [user1_id, user2_id],
        'room_type': 'private',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/rooms/group', methods=['POST'])
def create_group_room():
    """创建群聊房间"""
    data = request.get_json()
    
    creator_id = data.get('creator_id')
    room_name = data.get('room_name', '未命名群聊')
    member_ids = data.get('member_ids', [])
    
    if not creator_id:
        return jsonify({'error': 'creator_id required'}), 400
    
    # 确保创建者在成员列表中
    if creator_id not in member_ids:
        member_ids.append(creator_id)
    
    store = get_store()
    
    if hasattr(store, 'create_group_room'):
        room_id = store.create_group_room(creator_id, room_name, member_ids)
    else:
        room_id = memory_store.create_group_room(creator_id, room_name, member_ids)
    
    return jsonify({
        'room_id': room_id,
        'group_name': room_name,
        'member_ids': member_ids,
        'room_type': 'group',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/rooms/<room_id>/info', methods=['GET'])
def get_room_info(room_id):
    """获取房间信息"""
    store = get_store()
    
    if hasattr(store, 'get_room_info'):
        room_info = store.get_room_info(room_id)
    else:
        room_info = memory_store.rooms.get(room_id, {})
    
    return jsonify({
        'room_id': room_id,
        'info': room_info,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/rooms/<room_id>/messages', methods=['GET'])
def get_room_messages(room_id):
    """获取房间消息"""
    limit = int(request.args.get('limit', 100))
    before_timestamp = request.args.get('before_timestamp')
    user_id = request.args.get('user_id')  # 用于获取用户特定状态
    
    store = get_store()
    
    if hasattr(store, 'get_messages_for_user') and user_id:
        messages = store.get_messages_for_user(
            room_id=room_id,
            user_id=user_id,
            limit=limit,
            before_timestamp=before_timestamp
        )
    elif hasattr(store, 'get_messages'):
        messages = store.get_messages(
            room_id=room_id,
            limit=limit,
            before_timestamp=before_timestamp
        )
    else:
        messages = memory_store.get_messages(
            room_id=room_id,
            limit=limit,
            before_timestamp=before_timestamp
        )
    
    return jsonify({
        'room_id': room_id,
        'messages': messages,
        'count': len(messages),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/messages', methods=['POST'])
def send_message():
    """发送消息"""
    data = request.get_json()
    
    room_id = data.get('room_id')
    sender_id = data.get('sender_id')
    content = data.get('content')
    message_type = data.get('type', 'text')
    metadata = data.get('metadata', {})
    
    if not all([room_id, sender_id, content]):
        return jsonify({'error': 'room_id, sender_id and content required'}), 400
    
    store = get_store()
    
    if hasattr(store, 'add_message'):
        message = store.add_message(
            room_id=room_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            metadata=metadata
        )
    else:
        message = memory_store.add_message(
            room_id=room_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            metadata=metadata
        )
    
    return jsonify({
        'success': True,
        'message': message,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/messages/<message_id>/status', methods=['POST'])
def update_message_status(message_id):
    """更新消息状态（已读/已送达）"""
    data = request.get_json()
    
    user_id = data.get('user_id')
    status = data.get('status')  # 'read' 或 'delivered'
    
    if not user_id or not status:
        return jsonify({'error': 'user_id and status required'}), 400
    
    if status not in ['sent', 'delivered', 'read']:
        return jsonify({'error': 'status must be sent, delivered or read'}), 400
    
    store = get_store()
    
    if hasattr(store, 'update_message_status'):
        success = store.update_message_status(
            message_id=message_id,
            user_id=user_id,
            status=status
        )
    else:
        # 内存存储更新
        if message_id in memory_store.message_status:
            memory_store.message_status[message_id][user_id] = status
            success = True
        else:
            success = False
    
    return jsonify({
        'success': success,
        'message_id': message_id,
        'user_id': user_id,
        'status': status,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/users/online', methods=['GET'])
def get_online_users():
    """获取在线用户列表"""
    store = get_store()
    
    if hasattr(store, 'get_online_users'):
        online_users = store.get_online_users()
    else:
        # 从内存存储获取
        online_users = [
            uid for uid, user in memory_store.users.items() 
            if user.get('online', False)
        ]
    
    return jsonify({
        'online_users': online_users,
        'count': len(online_users),
        'timestamp': datetime.now().isoformat()
    })

# 启动服务器
if __name__ == '__main__':
    logger.info("启动SellAI社交聊天API服务...")
    logger.info(f"数据库存储: {'可用' if chat_manager else '不可用，使用内存存储'}")
    
    # 运行Flask应用
    app.run(host='0.0.0.0', port=5002, debug=True)