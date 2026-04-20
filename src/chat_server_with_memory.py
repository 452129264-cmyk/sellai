#!/usr/bin/env python3
"""
增强版聊天服务器 - 集成永久记忆功能

此服务器扩展了原有chat_server.py功能，添加：
1. 聊天消息自动同步到Notebook LM永久记忆
2. 社交关系记忆集成
3. 实时加密存储
4. 与Memory V2系统兼容
"""

import os
import sys
import json
import uuid
import logging
import threading
import time
from datetime import datetime
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CHAT_SERVER_WITH_MEMORY - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sellai-chat-memory-secret-2026')

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
        'memory_enabled': bool(memory_bridge)
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

@socketio.on('search_messages')
def handle_search_messages(data):
    """搜索聊天消息"""
    try:
        query = data.get('query', '')
        filters = data.get('filters', {})
        limit = data.get('limit', 20)
        
        if not query:
            emit('search_results', {
                'success': False,
                'error': '查询关键词不能为空'
            })
            return
        
        # 如果有聊天记忆桥接，使用其搜索功能
        if memory_bridge:
            results = memory_bridge.search_chat_messages(
                query=query,
                filters=filters,
                limit=limit
            )
            
            emit('search_results', {
                'success': True,
                'query': query,
                'results': results,
                'count': len(results),
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('search_results', {
                'success': False,
                'error': '永久记忆系统不可用，搜索功能不可用'
            })
        
    except Exception as e:
        logger.error(f"处理搜索事件失败: {e}")
        emit('search_results', {
            'success': False,
            'error': str(e)
        })

# ===================== RESTful API端点 =====================

@app.route('/api/chat-memory/health', methods=['GET'])
def api_health_check():
    """API健康检查"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'status': 'running',
        'memory_bridge_available': bool(memory_bridge),
        'socketio_connections': len(socketio.server.manager.rooms.get('/', {}))
    }
    
    if memory_bridge:
        try:
            health = memory_bridge.health_check()
            status['memory_health'] = health
        except Exception as e:
            status['memory_health_error'] = str(e)
    
    return jsonify(status)

@app.route('/api/chat-memory/sync/start', methods=['POST'])
def api_start_sync():
    """API启动同步服务"""
    if not memory_bridge:
        return jsonify({'error': '聊天记忆桥接不可用'}), 503
    
    try:
        memory_bridge.start_background_sync()
        
        return jsonify({
            'success': True,
            'message': '后台同步服务已启动',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'启动同步服务失败: {str(e)}'}), 500

@app.route('/api/chat-memory/sync/stop', methods=['POST'])
def api_stop_sync():
    """API停止同步服务"""
    if not memory_bridge:
        return jsonify({'error': '聊天记忆桥接不可用'}), 503
    
    try:
        memory_bridge.stop_background_sync()
        
        return jsonify({
            'success': True,
            'message': '后台同步服务已停止',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'停止同步服务失败: {str(e)}'}), 500

@app.route('/api/chat-memory/sync/now', methods=['POST'])
def api_sync_now():
    """API立即同步"""
    if not memory_bridge:
        return jsonify({'error': '聊天记忆桥接不可用'}), 503
    
    try:
        # 执行同步
        result = memory_bridge.sync_relationships()
        
        return jsonify({
            'success': True,
            'message': '立即同步完成',
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'同步失败: {str(e)}'}), 500

@app.route('/api/chat-memory/stats', methods=['GET'])
def api_get_stats():
    """API获取统计信息"""
    if not memory_bridge:
        return jsonify({'error': '聊天记忆桥接不可用'}), 503
    
    try:
        stats = memory_bridge.get_sync_stats()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'获取统计失败: {str(e)}'}), 500

@app.route('/api/chat-memory/test/encryption', methods=['POST'])
def api_test_encryption():
    """API测试加密功能"""
    if not memory_bridge or not memory_bridge.memory:
        return jsonify({'error': '永久记忆系统不可用'}), 503
    
    try:
        data = request.get_json()
        test_content = data.get('content', '这是一条测试消息')
        test_metadata = data.get('metadata', {'test': True})
        
        encrypted, updated_metadata = memory_bridge.memory.encrypt_chat_content(
            test_content, test_metadata
        )
        
        return jsonify({
            'success': True,
            'original_content': test_content,
            'encrypted_content': encrypted,
            'metadata': updated_metadata,
            'encrypted_length': len(encrypted),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'加密测试失败: {str(e)}'}), 500

@app.route('/api/chat-memory/user/history', methods=['GET'])
def api_get_user_history():
    """API获取用户聊天历史"""
    if not memory_bridge:
        return jsonify({'error': '聊天记忆桥接不可用'}), 503
    
    try:
        user_id = request.args.get('user_id')
        days_back = int(request.args.get('days_back', 30))
        limit = int(request.args.get('limit', 50))
        
        if not user_id:
            return jsonify({'error': 'user_id参数必填'}), 400
        
        history = memory_bridge.get_user_chat_history(
            user_id=user_id,
            days_back=days_back,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'history': history,
            'count': len(history),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'获取历史失败: {str(e)}'}), 500

# ===================== 启动与停止函数 =====================

def start_server(host: str = '0.0.0.0', port: int = 5000):
    """
    启动增强版聊天服务器
    
    Args:
        host: 监听地址
        port: 监听端口
    """
    logger.info(f"启动增强版聊天服务器: {host}:{port}")
    
    # 检查永久记忆系统
    if memory_bridge:
        logger.info("永久记忆功能已启用")
    else:
        logger.warning("永久记忆功能未启用，聊天记录将不会同步到Notebook LM")
    
    try:
        # 启动SocketIO服务器
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        raise

def stop_server():
    """停止服务器"""
    logger.info("停止增强版聊天服务器")
    # SocketIO服务器停止逻辑
    # 这里可以添加清理逻辑

# ===================== 主函数 =====================

if __name__ == "__main__":
    print("增强版聊天服务器 - 集成永久记忆功能")
    print("=" * 70)
    
    # 显示系统状态
    status = {
        'memory_bridge': '可用' if memory_bridge else '不可用',
        'shared_state': '可用' if HAS_SHARED_STATE else '不可用',
        'timestamp': datetime.now().isoformat()
    }
    
    print("系统状态:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 如果桥接可用，显示健康状态
    if memory_bridge:
        try:
            health = memory_bridge.health_check()
            print(f"\n永久记忆系统状态:")
            print(f"  基础聊天管理器: {'可用' if health['base_manager_available'] else '不可用'}")
            print(f"  记忆系统: {'可用' if health['memory_system_available'] else '不可用'}")
            print(f"  后台同步: {'运行中' if health['sync_active'] else '未运行'}")
            
            if 'memory_stats' in health:
                stats = health['memory_stats']
                print(f"  已同步消息: {stats.get('total_synced', 0)}条")
                print(f"  待同步消息: {stats.get('total_pending', 0)}条")
        except Exception as e:
            print(f"  获取健康状态失败: {e}")
    
    print("\n" + "=" * 70)
    print("服务器配置:")
    print(f"  主机: 0.0.0.0")
    print(f"  端口: 5000")
    print(f"  API端点: /api/chat-memory/*")
    print(f"  SocketIO端点: /")
    
    print("\n启动命令: python src/chat_server_with_memory.py run")
    print("或: python -m src.chat_server_with_memory")
    
    # 如果命令行参数包含"run"，则启动服务器
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        print("\n启动服务器...")
        start_server(host='0.0.0.0', port=5000)