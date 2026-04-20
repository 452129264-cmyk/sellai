#!/usr/bin/env python3
"""
权限集成版聊天服务器
基于chat_server_with_memory.py，集成权限管控功能

主要增强：
1. 消息发送前检查发送者权限
2. 消息接收前检查接收者隐私设置
3. 阅后即焚消息自动处理
4. 消息清理自动化
5. 安全审计集成
"""

import os
import sys
import json
import uuid
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask_cors import CORS

# 添加src目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入聊天记忆桥接
try:
    from src.chat_memory_bridge import ChatMemoryBridge, get_chat_memory_bridge
    HAS_MEMORY_BRIDGE = True
except ImportError:
    HAS_MEMORY_BRIDGE = False
    print("警告: 未找到chat_memory_bridge，永久记忆功能将不可用")

# 导入共享状态管理器
try:
    from src.shared_state_manager import SharedStateManager
    HAS_SHARED_STATE = True
except ImportError:
    HAS_SHARED_STATE = False
    print("警告: 未找到shared_state_manager，聊天记录将仅保存在内存中")

# 导入权限管理器
try:
    from src.permission_manager import (
        PermissionManager, 
        get_permission_manager,
        UserRole,
        PermissionType
    )
    HAS_PERMISSION_MANAGER = True
except ImportError:
    HAS_PERMISSION_MANAGER = False
    print("警告: 未找到permission_manager，权限管控功能将不可用")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CHAT_SERVER_WITH_PERMISSIONS - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sellai-chat-permissions-secret-2026')

# 配置CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# 创建SocketIO实例
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 聊天记忆桥接实例
memory_bridge = None
if HAS_MEMORY_BRIDGE:
    try:
        memory_bridge = get_chat_memory_bridge()
        logger.info("聊天记忆桥接初始化成功")
    except Exception as e:
        memory_bridge = None
        logger.error(f"聊天记忆桥接初始化失败: {e}")

# 权限管理器实例
permission_manager = None
if HAS_PERMISSION_MANAGER:
    try:
        permission_manager = get_permission_manager()
        logger.info("权限管理器初始化成功")
    except Exception as e:
        permission_manager = None
        logger.error(f"权限管理器初始化失败: {e}")

# 后台任务线程
cleanup_thread = None
cleanup_active = False

def start_background_tasks():
    """启动后台任务"""
    global cleanup_thread, cleanup_active
    
    if not cleanup_active:
        cleanup_active = True
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        logger.info("后台清理任务已启动")

def stop_background_tasks():
    """停止后台任务"""
    global cleanup_active
    
    cleanup_active = False
    if cleanup_thread:
        cleanup_thread.join(timeout=5)
    logger.info("后台清理任务已停止")

def cleanup_loop():
    """清理循环：处理阅后即焚消息和过期消息"""
    while cleanup_active:
        try:
            # 处理阅后即焚消息
            if permission_manager:
                permission_manager.check_and_destruct_messages()
            
            # 清理过期的聊天记录（每小时检查一次）
            current_hour = datetime.now().hour
            if current_hour == 0:  # 每天凌晨执行
                # 获取所有用户并清理聊天记录
                if permission_manager:
                    # 这里简化处理：在实际系统中需要获取用户列表
                    pass
            
            time.sleep(60)  # 每分钟检查一次
            
        except Exception as e:
            logger.error(f"清理循环出错: {e}")
            time.sleep(300)  # 出错后等待5分钟

# ===================== SocketIO事件处理器 =====================

@socketio.on('connect')
def handle_connect():
    """客户端连接事件"""
    logger.info(f"客户端连接: {request.sid}")
    
    # 发送连接确认
    emit('connected', {
        'status': 'success',
        'sid': request.sid,
        'timestamp': datetime.now().isoformat(),
        'memory_enabled': bool(memory_bridge),
        'permission_enabled': bool(permission_manager)
    })

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接事件"""
    logger.info(f"客户端断开连接: {request.sid}")

@socketio.on('join')
def handle_join(data):
    """加入房间事件"""
    try:
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        
        if not room_id or not user_id:
            emit('error', {'message': '缺少room_id或user_id'})
            return
        
        # 检查用户是否有加入房间的权限
        if permission_manager:
            # 检查用户角色和权限
            user_role = permission_manager.get_user_role(user_id)
            
            # 如果用户是访客，可能需要特殊处理
            if user_role == UserRole.GUEST.value:
                # 访客可能需要特殊权限才能加入某些房间
                # 这里可以根据实际业务需求扩展
                pass
        
        # 加入SocketIO房间
        join_room(room_id)
        
        logger.info(f"用户 {user_id} 加入房间 {room_id}")
        
        # 发送加入确认
        emit('joined', {
            'room_id': room_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })
        
        # 广播给房间内其他用户
        emit('user_joined', {
            'room_id': room_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }, room=room_id, skip_sid=request.sid)
        
    except Exception as e:
        logger.error(f"处理加入事件失败: {e}")
        emit('error', {'message': str(e)})

@socketio.on('leave')
def handle_leave(data):
    """离开房间事件"""
    try:
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        
        if not room_id or not user_id:
            emit('error', {'message': '缺少room_id或user_id'})
            return
        
        # 离开SocketIO房间
        leave_room(room_id)
        
        logger.info(f"用户 {user_id} 离开房间 {room_id}")
        
        # 发送离开确认
        emit('left', {
            'room_id': room_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })
        
        # 广播给房间内其他用户
        emit('user_left', {
            'room_id': room_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }, room=room_id, skip_sid=request.sid)
        
    except Exception as e:
        logger.error(f"处理离开事件失败: {e}")
        emit('error', {'message': str(e)})

@socketio.on('message')
def handle_message(data):
    """处理聊天消息事件"""
    try:
        room_id = data.get('room_id')
        sender_id = data.get('sender_id')
        content = data.get('content')
        message_type = data.get('type', 'text')
        metadata = data.get('metadata', {})
        
        if not room_id or not sender_id or not content:
            emit('error', {'message': '缺少必要参数'})
            return
        
        # 检查发送者权限
        if permission_manager:
            # 1. 检查发送者是否有发送消息的权限
            can_send = permission_manager.check_permission(
                sender_id, 
                PermissionType.AI_INITIATED_CHAT.value if sender_id.startswith('ai_') else "send_message"
            )
            
            if not can_send:
                emit('error', {'message': '您没有发送消息的权限'})
                logger.warning(f"用户 {sender_id} 尝试发送消息但权限不足")
                return
            
            # 2. 如果是AI主动发起聊天，检查接收者是否允许
            if sender_id.startswith('ai_') and message_type == 'initiative_chat':
                # 检查接收者隐私设置
                allow_ai_chat = permission_manager.can_ai_initiate_chat(room_id)  # 这里简化：房间ID代表接收者
                if not allow_ai_chat:
                    emit('error', {'message': '接收者不允许AI主动发起聊天'})
                    logger.warning(f"AI {sender_id} 尝试主动发起聊天但被接收者禁止")
                    return
            
            # 3. 检查当前时间是否允许接收消息
            if not permission_manager.can_receive_message(room_id):
                emit('error', {'message': '当前时段不允许接收消息'})
                logger.warning(f"消息在禁止时段发送给 {room_id}")
                return
        
        # 处理阅后即焚消息
        self_destruct_seconds = metadata.get('self_destruct_seconds', 0)
        if self_destruct_seconds > 0 and permission_manager:
            # 记录阅后即焚消息
            permission_manager.add_self_destruct_message(
                message_id=str(uuid.uuid4()),  # 实际应该使用消息ID
                room_id=room_id,
                sender_id=sender_id,
                self_destruct_seconds=self_destruct_seconds
            )
        
        # 如果有聊天记忆桥接，使用它处理消息（自动同步）
        if memory_bridge:
            message = memory_bridge.add_message(
                room_id=room_id,
                sender_id=sender_id,
                content=content,
                message_type=message_type,
                metadata=metadata
            )
            logger.info(f"消息已通过记忆桥接处理: {message['id'][:8]}")
        else:
            # 简化处理（如果没有桥接）
            message = {
                'id': str(uuid.uuid4()),
                'room_id': room_id,
                'sender_id': sender_id,
                'content': content,
                'type': message_type,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata
            }
            logger.info(f"消息简化处理: {message['id'][:8]}")
        
        # 广播消息给房间内所有用户（包括发送者）
        emit('new_message', message, room=room_id)
        
        logger.info(f"消息广播: {sender_id} -> {room_id}, 类型: {message_type}")
        
    except Exception as e:
        logger.error(f"处理消息事件失败: {e}")
        emit('error', {'message': str(e)})

@socketio.on('get_privacy_settings')
def handle_get_privacy_settings(data):
    """获取用户隐私设置"""
    try:
        user_id = data.get('user_id')
        
        if not user_id:
            emit('error', {'message': '缺少user_id'})
            return
        
        if not permission_manager:
            emit('error', {'message': '权限管理器不可用'})
            return
        
        settings = permission_manager.get_user_privacy_settings(user_id)
        
        emit('privacy_settings', {
            'user_id': user_id,
            'settings': settings,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"用户 {user_id} 获取隐私设置")
        
    except Exception as e:
        logger.error(f"获取隐私设置失败: {e}")
        emit('error', {'message': str(e)})

@socketio.on('update_privacy_settings')
def handle_update_privacy_settings(data):
    """更新用户隐私设置"""
    try:
        user_id = data.get('user_id')
        settings = data.get('settings', {})
        
        if not user_id or not settings:
            emit('error', {'message': '缺少user_id或settings'})
            return
        
        if not permission_manager:
            emit('error', {'message': '权限管理器不可用'})
            return
        
        permission_manager.update_privacy_settings(user_id, settings)
        
        emit('privacy_settings_updated', {
            'user_id': user_id,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"用户 {user_id} 更新隐私设置")
        
    except Exception as e:
        logger.error(f"更新隐私设置失败: {e}")
        emit('error', {'message': str(e)})

@socketio.on('get_user_role')
def handle_get_user_role(data):
    """获取用户角色"""
    try:
        user_id = data.get('user_id')
        
        if not user_id:
            emit('error', {'message': '缺少user_id'})
            return
        
        if not permission_manager:
            emit('error', {'message': '权限管理器不可用'})
            return
        
        role = permission_manager.get_user_role(user_id)
        
        emit('user_role', {
            'user_id': user_id,
            'role': role,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"获取用户 {user_id} 角色: {role}")
        
    except Exception as e:
        logger.error(f"获取用户角色失败: {e}")
        emit('error', {'message': str(e)})

@socketio.on('set_user_role')
def handle_set_user_role(data):
    """设置用户角色（需要管理员权限）"""
    try:
        admin_user_id = data.get('admin_user_id')
        target_user_id = data.get('target_user_id')
        role = data.get('role')
        
        if not admin_user_id or not target_user_id or not role:
            emit('error', {'message': '缺少必要参数'})
            return
        
        if not permission_manager:
            emit('error', {'message': '权限管理器不可用'})
            return
        
        # 检查管理员权限
        can_manage_users = permission_manager.check_permission(
            admin_user_id,
            PermissionType.MANAGE_USERS.value
        )
        
        if not can_manage_users:
            emit('error', {'message': '您没有管理用户的权限'})
            logger.warning(f"用户 {admin_user_id} 尝试设置用户角色但权限不足")
            return
        
        permission_manager.set_user_role(target_user_id, role, admin_user_id)
        
        emit('user_role_set', {
            'target_user_id': target_user_id,
            'role': role,
            'admin_user_id': admin_user_id,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"管理员 {admin_user_id} 将用户 {target_user_id} 角色设置为 {role}")
        
    except Exception as e:
        logger.error(f"设置用户角色失败: {e}")
        emit('error', {'message': str(e)})

@socketio.on('check_permission')
def handle_check_permission(data):
    """检查用户权限"""
    try:
        user_id = data.get('user_id')
        permission_type = data.get('permission_type')
        
        if not user_id or not permission_type:
            emit('error', {'message': '缺少user_id或permission_type'})
            return
        
        if not permission_manager:
            emit('error', {'message': '权限管理器不可用'})
            return
        
        has_permission = permission_manager.check_permission(user_id, permission_type)
        
        emit('permission_result', {
            'user_id': user_id,
            'permission_type': permission_type,
            'has_permission': has_permission,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"检查用户 {user_id} 权限 {permission_type}: {has_permission}")
        
    except Exception as e:
        logger.error(f"检查权限失败: {e}")
        emit('error', {'message': str(e)})

# ===================== HTTP API =====================

@app.route('/api/permissions/user/<user_id>/settings', methods=['GET'])
def get_user_privacy_settings_api(user_id):
    """获取用户隐私设置（HTTP API）"""
    try:
        if not permission_manager:
            return jsonify({
                'status': 'error',
                'message': '权限管理器不可用'
            }), 500
        
        settings = permission_manager.get_user_privacy_settings(user_id)
        
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': user_id,
                'settings': settings,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"API获取隐私设置失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/permissions/user/<user_id>/settings', methods=['POST'])
def update_user_privacy_settings_api(user_id):
    """更新用户隐私设置（HTTP API）"""
    try:
        if not permission_manager:
            return jsonify({
                'status': 'error',
                'message': '权限管理器不可用'
            }), 500
        
        settings = request.json.get('settings', {})
        
        if not settings:
            return jsonify({
                'status': 'error',
                'message': '缺少settings参数'
            }), 400
        
        permission_manager.update_privacy_settings(user_id, settings)
        
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': user_id,
                'updated': True,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"API更新隐私设置失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/permissions/user/<user_id>/role', methods=['GET'])
def get_user_role_api(user_id):
    """获取用户角色（HTTP API）"""
    try:
        if not permission_manager:
            return jsonify({
                'status': 'error',
                'message': '权限管理器不可用'
            }), 500
        
        role = permission_manager.get_user_role(user_id)
        
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': user_id,
                'role': role,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"API获取用户角色失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/permissions/user/<target_user_id>/role', methods=['POST'])
def set_user_role_api(target_user_id):
    """设置用户角色（HTTP API，需要管理员权限）"""
    try:
        if not permission_manager:
            return jsonify({
                'status': 'error',
                'message': '权限管理器不可用'
            }), 500
        
        admin_user_id = request.json.get('admin_user_id')
        role = request.json.get('role')
        
        if not admin_user_id or not role:
            return jsonify({
                'status': 'error',
                'message': '缺少admin_user_id或role参数'
            }), 400
        
        # 检查管理员权限
        can_manage_users = permission_manager.check_permission(
            admin_user_id,
            PermissionType.MANAGE_USERS.value
        )
        
        if not can_manage_users:
            return jsonify({
                'status': 'error',
                'message': '您没有管理用户的权限'
            }), 403
        
        permission_manager.set_user_role(target_user_id, role, admin_user_id)
        
        return jsonify({
            'status': 'success',
            'data': {
                'target_user_id': target_user_id,
                'role': role,
                'admin_user_id': admin_user_id,
                'updated': True,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"API设置用户角色失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ===================== 启动函数 =====================

def start_server(host='0.0.0.0', port=5001):
    """启动服务器"""
    try:
        # 启动后台任务
        start_background_tasks()
        
        logger.info(f"启动权限集成版聊天服务器: {host}:{port}")
        logger.info(f"权限管控: {bool(permission_manager)}")
        logger.info(f"永久记忆: {bool(memory_bridge)}")
        
        socketio.run(app, host=host, port=port, debug=False)
        
    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
    finally:
        stop_background_tasks()
        logger.info("服务器已停止")

if __name__ == "__main__":
    start_server()