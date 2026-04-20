#!/usr/bin/env python3
"""
SellAI社交聊天实时通信服务器
基于Flask-SocketIO实现一对一私聊和群聊功能
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask_cors import CORS

# 导入共享状态管理器
try:
    from shared_state_manager import SharedStateManager
    HAS_SHARED_STATE = True
except ImportError:
    HAS_SHARED_STATE = False
    print("警告: 未找到shared_state_manager，聊天记录将仅保存在内存中")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sellai-chat-secret-key-2026')

# 配置CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# 创建SocketIO实例
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 聊天管理器
class ChatManager:
    """聊天消息管理器"""
    
    def __init__(self):
        self.messages: Dict[str, List[Dict]] = {}  # 房间ID -> 消息列表
        self.users: Dict[str, Dict] = {}  # 用户ID -> 用户信息
        self.user_rooms: Dict[str, List[str]] = {}  # 用户ID -> 房间列表
        self.room_users: Dict[str, List[str]] = {}  # 房间ID -> 用户列表
        
        # 初始化共享状态管理器
        self.shared_state = None
        if HAS_SHARED_STATE:
            try:
                self.shared_state = SharedStateManager()
                logger.info("聊天消息将持久化到共享状态库")
            except Exception as e:
                logger.error(f"初始化共享状态管理器失败: {e}")
                self.shared_state = None
    
    def register_user(self, user_id: str, user_info: Dict) -> bool:
        """注册用户"""
        self.users[user_id] = {
            **user_info,
            'last_seen': datetime.now().isoformat(),
            'online': True
        }
        logger.info(f"用户注册: {user_id} - {user_info.get('name', '未知')}")
        return True
    
    def unregister_user(self, user_id: str) -> bool:
        """注销用户"""
        if user_id in self.users:
            self.users[user_id]['online'] = False
            self.users[user_id]['last_seen'] = datetime.now().isoformat()
            logger.info(f"用户离线: {user_id}")
            return True
        return False
    
    def create_private_chat(self, user1_id: str, user2_id: str) -> str:
        """创建一对一私聊房间"""
        # 生成房间ID: private_user1_user2 (按字母顺序排序)
        sorted_ids = sorted([user1_id, user2_id])
        room_id = f"private_{sorted_ids[0]}_{sorted_ids[1]}"
        
        if room_id not in self.messages:
            self.messages[room_id] = []
            self.room_users[room_id] = []
            
            # 添加到用户房间列表
            for user_id in [user1_id, user2_id]:
                if user_id not in self.user_rooms:
                    self.user_rooms[user_id] = []
                if room_id not in self.user_rooms[user_id]:
                    self.user_rooms[user_id].append(room_id)
                
                # 添加到房间用户列表
                if user_id not in self.room_users[room_id]:
                    self.room_users[room_id].append(user_id)
            
            logger.info(f"创建私聊房间: {room_id} ({user1_id} <-> {user2_id})")
        
        return room_id
    
    def create_group_chat(self, creator_id: str, group_name: str, member_ids: List[str]) -> str:
        """创建群聊房间"""
        room_id = f"group_{uuid.uuid4().hex[:8]}"
        
        self.messages[room_id] = []
        self.room_users[room_id] = member_ids
        
        # 添加到用户房间列表
        for user_id in member_ids:
            if user_id not in self.user_rooms:
                self.user_rooms[user_id] = []
            if room_id not in self.user_rooms[user_id]:
                self.user_rooms[user_id].append(room_id)
        
        logger.info(f"创建群聊房间: {room_id} ({group_name}), 成员: {len(member_ids)}人")
        
        return room_id
    
    def add_message(self, room_id: str, sender_id: str, content: str, 
                   message_type: str = "text", metadata: Dict = None) -> Dict:
        """添加消息到聊天记录"""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        message = {
            'id': message_id,
            'room_id': room_id,
            'sender_id': sender_id,
            'content': content,
            'type': message_type,  # text, image, file, opportunity
            'timestamp': timestamp,
            'metadata': metadata or {}
        }
        
        # 添加到内存存储
        if room_id not in self.messages:
            self.messages[room_id] = []
        self.messages[room_id].append(message)
        
        # 持久化到共享状态库
        if self.shared_state:
            try:
                # 使用共享状态库记录聊天消息
                self.shared_state.record_chat_message(
                    message_id=message_id,
                    room_id=room_id,
                    sender_id=sender_id,
                    recipient_ids=self.room_users.get(room_id, []),
                    content=content,
                    message_type=message_type,
                    timestamp=timestamp,
                    metadata=metadata or {}
                )
                logger.debug(f"消息已持久化: {message_id}")
            except Exception as e:
                logger.error(f"持久化消息失败: {e}")
        
        logger.info(f"新消息: {sender_id} -> {room_id}, 类型: {message_type}")
        
        return message
    
    def get_messages(self, room_id: str, limit: int = 100, 
                    before_timestamp: str = None) -> List[Dict]:
        """获取聊天记录"""
        if room_id not in self.messages:
            return []
        
        messages = self.messages[room_id]
        
        # 按时间过滤
        if before_timestamp:
            messages = [msg for msg in messages if msg['timestamp'] < before_timestamp]
        
        # 按时间倒序排序（最新的在后）
        messages.sort(key=lambda x: x['timestamp'])
        
        # 限制数量
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_user_rooms(self, user_id: str) -> List[str]:
        """获取用户所在的房间列表"""
        return self.user_rooms.get(user_id, [])
    
    def get_room_info(self, room_id: str) -> Dict:
        """获取房间信息"""
        if room_id not in self.messages:
            return {}
        
        # 判断房间类型
        if room_id.startswith('private_'):
            room_type = 'private'
            user_ids = room_id.replace('private_', '').split('_')
            room_name = None  # 私聊不显示房间名，显示对方用户名
        elif room_id.startswith('group_'):
            room_type = 'group'
            room_name = f"群聊 {room_id[-8:]}"  # 简化显示
            user_ids = self.room_users.get(room_id, [])
        else:
            room_type = 'unknown'
            room_name = '未知房间'
            user_ids = []
        
        return {
            'room_id': room_id,
            'room_type': room_type,
            'room_name': room_name,
            'user_ids': user_ids,
            'message_count': len(self.messages.get(room_id, [])),
            'last_message': self.messages[room_id][-1] if self.messages.get(room_id) else None
        }

# 全局聊天管理器实例
chat_manager = ChatManager()

# REST API端点
@app.route('/api/chat/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'users_online': len([u for u in chat_manager.users.values() if u.get('online')]),
        'total_rooms': len(chat_manager.messages)
    })

@app.route('/api/chat/register', methods=['POST'])
def register_user():
    """注册用户"""
    data = request.get_json()
    
    user_id = data.get('user_id')
    user_info = data.get('user_info', {})
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    success = chat_manager.register_user(user_id, user_info)
    
    return jsonify({
        'success': success,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/chat/messages', methods=['GET'])
def get_chat_messages():
    """获取聊天记录"""
    room_id = request.args.get('room_id')
    limit = int(request.args.get('limit', 100))
    before_timestamp = request.args.get('before_timestamp')
    
    if not room_id:
        return jsonify({'error': 'room_id required'}), 400
    
    messages = chat_manager.get_messages(room_id, limit, before_timestamp)
    
    return jsonify({
        'room_id': room_id,
        'messages': messages,
        'count': len(messages)
    })

@app.route('/api/chat/rooms', methods=['GET'])
def get_user_rooms():
    """获取用户的房间列表"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    rooms = chat_manager.get_user_rooms(user_id)
    room_infos = [chat_manager.get_room_info(room_id) for room_id in rooms]
    
    return jsonify({
        'user_id': user_id,
        'rooms': room_infos,
        'count': len(rooms)
    })

@app.route('/api/chat/create_private', methods=['POST'])
def create_private_chat():
    """创建一对一私聊"""
    data = request.get_json()
    
    user1_id = data.get('user1_id')
    user2_id = data.get('user2_id')
    
    if not user1_id or not user2_id:
        return jsonify({'error': 'user1_id and user2_id required'}), 400
    
    room_id = chat_manager.create_private_chat(user1_id, user2_id)
    
    return jsonify({
        'room_id': room_id,
        'user_ids': [user1_id, user2_id],
        'room_type': 'private'
    })

@app.route('/api/chat/create_group', methods=['POST'])
def create_group_chat():
    """创建群聊"""
    data = request.get_json()
    
    creator_id = data.get('creator_id')
    group_name = data.get('group_name', '未命名群聊')
    member_ids = data.get('member_ids', [])
    
    if not creator_id:
        return jsonify({'error': 'creator_id required'}), 400
    
    # 确保创建者在成员列表中
    if creator_id not in member_ids:
        member_ids.append(creator_id)
    
    room_id = chat_manager.create_group_chat(creator_id, group_name, member_ids)
    
    return jsonify({
        'room_id': room_id,
        'group_name': group_name,
        'member_ids': member_ids,
        'room_type': 'group'
    })

# SocketIO事件处理
@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    user_id = request.args.get('user_id')
    if user_id:
        logger.info(f"客户端连接: {user_id}")
        emit('connected', {'user_id': user_id, 'status': 'connected'})
    else:
        logger.info("匿名客户端连接")

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    user_id = request.args.get('user_id')
    if user_id:
        chat_manager.unregister_user(user_id)
        logger.info(f"客户端断开连接: {user_id}")

@socketio.on('join')
def handle_join(data):
    """加入房间"""
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    
    if room_id and user_id:
        join_room(room_id)
        logger.info(f"用户 {user_id} 加入房间 {room_id}")
        emit('joined', {'room_id': room_id, 'user_id': user_id}, room=room_id)

@socketio.on('leave')
def handle_leave(data):
    """离开房间"""
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    
    if room_id and user_id:
        leave_room(room_id)
        logger.info(f"用户 {user_id} 离开房间 {room_id}")
        emit('left', {'room_id': room_id, 'user_id': user_id}, room=room_id)

@socketio.on('send_message')
def handle_send_message(data):
    """发送消息"""
    room_id = data.get('room_id')
    sender_id = data.get('sender_id')
    content = data.get('content')
    message_type = data.get('type', 'text')
    metadata = data.get('metadata', {})
    
    if not all([room_id, sender_id, content]):
        emit('error', {'message': 'Missing required fields'})
        return
    
    # 创建消息
    message = chat_manager.add_message(room_id, sender_id, content, message_type, metadata)
    
    # 广播消息给房间内的所有用户
    emit('new_message', message, room=room_id)
    logger.info(f"消息广播: {sender_id} -> {room_id}")

# 启动服务器
if __name__ == '__main__':
    logger.info("启动SellAI社交聊天服务器...")
    logger.info(f"共享状态库支持: {HAS_SHARED_STATE}")
    
    # 在调试模式下运行
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)