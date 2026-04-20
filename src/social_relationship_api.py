#!/usr/bin/env python3
"""
社交关系API服务
提供用户与AI分身社交关系、AI-AI通信、隐私设置等功能的RESTful API
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS

# 导入社交关系管理器
try:
    from social_relationship_manager import get_social_relationship_manager
    HAS_SOCIAL_MANAGER = True
except ImportError:
    HAS_SOCIAL_MANAGER = False
    print("警告: 未找到social_relationship_manager，社交功能将不可用")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 社交关系管理器实例
social_manager = None
if HAS_SOCIAL_MANAGER:
    social_manager = get_social_relationship_manager()
    logger.info("社交关系管理器初始化完成")
else:
    logger.warning("社交关系管理器不可用，相关功能将受限")

# ===================== API端点 =====================

@app.route('/api/social/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy' if social_manager else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'social_manager_available': bool(social_manager)
    })

# 用户-AI社交关系管理
@app.route('/api/social/friends/add', methods=['POST'])
def add_ai_friend_api():
    """添加AI分身为好友"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    data = request.get_json()
    user_id = data.get('user_id')
    avatar_id = data.get('avatar_id')
    metadata = data.get('metadata')
    
    if not user_id or not avatar_id:
        return jsonify({'error': 'user_id和avatar_id必填'}), 400
    
    success = social_manager.add_ai_friend(user_id, avatar_id, metadata)
    
    return jsonify({
        'success': success,
        'user_id': user_id,
        'avatar_id': avatar_id,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/social/friends/remove', methods=['POST'])
def remove_ai_friend_api():
    """移除AI分身好友"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    data = request.get_json()
    user_id = data.get('user_id')
    avatar_id = data.get('avatar_id')
    
    if not user_id or not avatar_id:
        return jsonify({'error': 'user_id和avatar_id必填'}), 400
    
    success = social_manager.remove_ai_friend(user_id, avatar_id)
    
    return jsonify({
        'success': success,
        'user_id': user_id,
        'avatar_id': avatar_id,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/social/friends/block', methods=['POST'])
def block_ai_api():
    """屏蔽AI分身"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    data = request.get_json()
    user_id = data.get('user_id')
    avatar_id = data.get('avatar_id')
    
    if not user_id or not avatar_id:
        return jsonify({'error': 'user_id和avatar_id必填'}), 400
    
    success = social_manager.block_ai(user_id, avatar_id)
    
    return jsonify({
        'success': success,
        'user_id': user_id,
        'avatar_id': avatar_id,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/social/friends/list', methods=['GET'])
def list_ai_friends_api():
    """获取用户的AI分身好友列表"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id必填'}), 400
    
    friends = social_manager.get_user_ai_friends(user_id)
    
    return jsonify({
        'user_id': user_id,
        'friends': friends,
        'count': len(friends),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/social/friends/can_chat', methods=['GET'])
def can_ai_initiate_chat_api():
    """检查AI分身是否可以主动向用户发起聊天"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    avatar_id = request.args.get('avatar_id')
    user_id = request.args.get('user_id')
    
    if not avatar_id or not user_id:
        return jsonify({'error': 'avatar_id和user_id必填'}), 400
    
    can_chat = social_manager.can_ai_initiate_chat(avatar_id, user_id)
    
    return jsonify({
        'can_chat': can_chat,
        'avatar_id': avatar_id,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    })

# AI-AI通信管理
@app.route('/api/social/communications/record', methods=['POST'])
def record_ai_ai_communication_api():
    """记录AI-AI私下通信"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    data = request.get_json()
    sender_avatar_id = data.get('sender_avatar_id')
    receiver_avatar_id = data.get('receiver_avatar_id')
    content = data.get('content')
    content_type = data.get('content_type', 'text')
    metadata = data.get('metadata')
    
    if not all([sender_avatar_id, receiver_avatar_id, content]):
        return jsonify({'error': 'sender_avatar_id、receiver_avatar_id和content必填'}), 400
    
    try:
        communication_id = social_manager.record_ai_ai_communication(
            sender_avatar_id=sender_avatar_id,
            receiver_avatar_id=receiver_avatar_id,
            content=content,
            content_type=content_type,
            metadata=metadata
        )
        
        return jsonify({
            'success': True,
            'communication_id': communication_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"记录AI-AI通信失败: {e}")
        return jsonify({'error': f'记录失败: {str(e)}'}), 500

@app.route('/api/social/communications/list', methods=['GET'])
def list_ai_ai_communications_api():
    """获取AI-AI通信记录"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    sender_avatar_id = request.args.get('sender_avatar_id')
    receiver_avatar_id = request.args.get('receiver_avatar_id')
    content_type = request.args.get('content_type')
    limit = int(request.args.get('limit', 100))
    
    communications = social_manager.get_ai_ai_communications(
        sender_avatar_id=sender_avatar_id,
        receiver_avatar_id=receiver_avatar_id,
        content_type=content_type,
        limit=limit
    )
    
    return jsonify({
        'communications': communications,
        'count': len(communications),
        'timestamp': datetime.now().isoformat()
    })

# 高价值商机同步
@app.route('/api/social/opportunities/high_value', methods=['GET'])
def get_high_value_opportunities_api():
    """获取AI-AI通信中的高价值商机"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    user_id = request.args.get('user_id')
    min_priority = int(request.args.get('min_priority', 3))
    
    if not user_id:
        return jsonify({'error': 'user_id必填'}), 400
    
    opportunities = social_manager.get_high_value_opportunities_from_ai(
        user_id=user_id,
        min_priority=min_priority
    )
    
    return jsonify({
        'user_id': user_id,
        'opportunities': opportunities,
        'count': len(opportunities),
        'min_priority': min_priority,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/social/opportunities/sync', methods=['POST'])
def sync_opportunity_to_user_api():
    """将高价值商机同步给用户"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    data = request.get_json()
    communication_id = data.get('communication_id')
    user_id = data.get('user_id')
    
    if not communication_id or not user_id:
        return jsonify({'error': 'communication_id和user_id必填'}), 400
    
    success = social_manager.sync_opportunity_to_user(
        communication_id=communication_id,
        user_id=user_id
    )
    
    return jsonify({
        'success': success,
        'communication_id': communication_id,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    })

# 用户隐私设置管理
@app.route('/api/social/privacy/set', methods=['POST'])
def set_privacy_settings_api():
    """设置用户隐私选项"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id必填'}), 400
    
    # 提取隐私设置
    settings = {}
    for key in ['allow_ai_initiated_chat', 'show_opportunity_push', 
                'allow_ai_ai_collaboration_visibility', 'auto_add_ai_friends']:
        if key in data:
            settings[key] = data[key]
    
    if not settings:
        return jsonify({'error': '至少提供一个隐私设置'}), 400
    
    success = social_manager.set_user_privacy_settings(user_id, **settings)
    
    return jsonify({
        'success': success,
        'user_id': user_id,
        'settings': settings,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/social/privacy/get', methods=['GET'])
def get_privacy_settings_api():
    """获取用户隐私设置"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id必填'}), 400
    
    settings = social_manager.get_user_privacy_settings(user_id)
    
    return jsonify({
        'user_id': user_id,
        'settings': settings,
        'timestamp': datetime.now().isoformat()
    })

# 社交关系统计
@app.route('/api/social/statistics', methods=['GET'])
def get_social_statistics_api():
    """获取社交关系统计信息"""
    if not social_manager:
        return jsonify({'error': '社交功能不可用'}), 503
    
    user_id = request.args.get('user_id')
    
    statistics = social_manager.get_social_statistics(user_id)
    
    return jsonify({
        'user_id': user_id if user_id else 'system',
        'statistics': statistics,
        'timestamp': datetime.now().isoformat()
    })

# 启动服务器
if __name__ == '__main__':
    logger.info("启动社交关系API服务...")
    logger.info(f"社交关系管理器: {'可用' if social_manager else '不可用'}")
    
    # 运行Flask应用
    app.run(host='0.0.0.0', port=5003, debug=True)