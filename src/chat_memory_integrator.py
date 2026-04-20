#!/usr/bin/env python3
"""
聊天记录永久记忆集成主控制器

此模块负责：
1. 初始化聊天记录永久记忆系统
2. 提供RESTful API接口供办公室界面调用
3. 管理后台同步服务
4. 协调与现有系统的集成
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

from flask import Flask, request, jsonify
from flask_cors import CORS

# 导入聊天永久记忆模块
try:
    from src.chat_permanent_memory import ChatPermanentMemory, initialize_chat_permanent_memory
    HAS_CHAT_MEMORY = True
except ImportError:
    HAS_CHAT_MEMORY = False
    print("警告: 未找到chat_permanent_memory模块，永久记忆功能将不可用")

# 导入社交关系管理器
try:
    from src.social_relationship_manager import SocialRelationshipManager
    HAS_SOCIAL_MANAGER = True
except ImportError:
    HAS_SOCIAL_MANAGER = False
    print("警告: 未找到social_relationship_manager，社交关系同步功能将受限")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CHAT_MEMORY_INTEGRATOR - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatMemoryIntegrator:
    """
    聊天记录永久记忆集成控制器
    
    功能：
    1. 管理ChatPermanentMemory实例
    2. 提供API接口
    3. 处理后台同步
    4. 与现有系统集成
    """
    
    def __init__(self, config_file: str = "configs/chat_memory_config.json"):
        """
        初始化集成控制器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
        
        # 初始化聊天永久记忆系统
        self.chat_memory = None
        if HAS_CHAT_MEMORY:
            try:
                self.chat_memory = initialize_chat_permanent_memory()
                logger.info("聊天记录永久记忆系统初始化成功")
            except Exception as e:
                logger.error(f"聊天记录永久记忆系统初始化失败: {e}")
        else:
            logger.warning("聊天记录永久记忆模块不可用，相关功能将受限")
        
        # 初始化社交关系管理器
        self.social_manager = None
        if HAS_SOCIAL_MANAGER:
            try:
                self.social_manager = SocialRelationshipManager()
                logger.info("社交关系管理器初始化成功")
            except Exception as e:
                logger.error(f"社交关系管理器初始化失败: {e}")
        
        # 后台同步状态
        self.sync_thread = None
        self.sync_active = False
        self.sync_interval = self.config.get('sync', {}).get('sync_interval_minutes', 5) * 60
        
        # API应用
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_api_routes()
        
        logger.info("聊天记录永久记忆集成控制器初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            # 创建默认配置
            default_config = {
                'notebook_lm': {
                    'api_key': os.getenv('NOTEBOOKLM_API_KEY', ''),
                    'base_url': 'https://api.notebooklm.com/v1'
                },
                'encryption': {
                    'enabled': True
                },
                'sync': {
                    'auto_sync_enabled': True,
                    'sync_interval_minutes': 5,
                    'batch_size': 100
                }
            }
            
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"创建默认配置文件: {self.config_file}")
            return default_config
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"加载配置文件: {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _setup_api_routes(self):
        """设置API路由"""
        
        @self.app.route('/api/chat-memory/health', methods=['GET'])
        def health_check():
            """健康检查"""
            status = {
                'timestamp': datetime.now().isoformat(),
                'chat_memory_available': bool(self.chat_memory),
                'social_manager_available': bool(self.social_manager),
                'sync_active': self.sync_active,
                'config_loaded': bool(self.config)
            }
            
            # 检查知识库状态
            if self.chat_memory:
                try:
                    stats = self.chat_memory.get_sync_stats()
                    status['sync_stats'] = stats
                except Exception as e:
                    status['sync_stats_error'] = str(e)
            
            return jsonify(status)
        
        @self.app.route('/api/chat-memory/sync/start', methods=['POST'])
        def start_sync():
            """启动同步服务"""
            if not self.chat_memory:
                return jsonify({'error': '聊天记忆系统未初始化'}), 503
            
            if self.sync_active:
                return jsonify({'warning': '同步服务已在运行中'}), 200
            
            try:
                # 启动后台同步
                self.sync_active = True
                self.sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
                self.sync_thread.start()
                
                return jsonify({
                    'success': True,
                    'message': '后台同步服务已启动',
                    'sync_interval_seconds': self.sync_interval
                })
                
            except Exception as e:
                self.sync_active = False
                return jsonify({'error': f'启动同步服务失败: {str(e)}'}), 500
        
        @self.app.route('/api/chat-memory/sync/stop', methods=['POST'])
        def stop_sync():
            """停止同步服务"""
            if not self.sync_active:
                return jsonify({'warning': '同步服务未运行'}), 200
            
            try:
                self.sync_active = False
                if self.sync_thread:
                    self.sync_thread.join(timeout=10)
                
                return jsonify({
                    'success': True,
                    'message': '后台同步服务已停止'
                })
                
            except Exception as e:
                return jsonify({'error': f'停止同步服务失败: {str(e)}'}), 500
        
        @self.app.route('/api/chat-memory/sync/now', methods=['POST'])
        def sync_now():
            """立即执行同步"""
            if not self.chat_memory:
                return jsonify({'error': '聊天记忆系统未初始化'}), 503
            
            try:
                # 导入聊天记录
                chat_result = self.chat_memory.import_chat_messages(limit=500, days_back=7)
                
                # 导入社交关系
                relationship_result = self.chat_memory.import_social_relationships(limit=200)
                
                return jsonify({
                    'success': True,
                    'message': '手动同步完成',
                    'chat_result': chat_result,
                    'relationship_result': relationship_result
                })
                
            except Exception as e:
                return jsonify({'error': f'同步失败: {str(e)}'}), 500
        
        @self.app.route('/api/chat-memory/messages/search', methods=['POST'])
        def search_messages():
            """搜索聊天记录"""
            if not self.chat_memory:
                return jsonify({'error': '聊天记忆系统未初始化'}), 503
            
            try:
                data = request.get_json()
                query = data.get('query', '')
                filters = data.get('filters', {})
                limit = data.get('limit', 20)
                
                if not query:
                    return jsonify({'error': '查询关键词不能为空'}), 400
                
                results = self.chat_memory.search_chat_messages(
                    query=query,
                    filters=filters,
                    limit=limit
                )
                
                return jsonify({
                    'success': True,
                    'query': query,
                    'results': results,
                    'count': len(results)
                })
                
            except Exception as e:
                return jsonify({'error': f'搜索失败: {str(e)}'}), 500
        
        @self.app.route('/api/chat-memory/user/history', methods=['GET'])
        def get_user_history():
            """获取用户聊天历史"""
            if not self.chat_memory:
                return jsonify({'error': '聊天记忆系统未初始化'}), 503
            
            try:
                user_id = request.args.get('user_id')
                days_back = int(request.args.get('days_back', 30))
                limit = int(request.args.get('limit', 50))
                
                if not user_id:
                    return jsonify({'error': 'user_id参数必填'}), 400
                
                history = self.chat_memory.get_user_chat_history(
                    user_id=user_id,
                    days_back=days_back,
                    limit=limit
                )
                
                return jsonify({
                    'success': True,
                    'user_id': user_id,
                    'history': history,
                    'count': len(history)
                })
                
            except Exception as e:
                return jsonify({'error': f'获取历史失败: {str(e)}'}), 500
        
        @self.app.route('/api/chat-memory/stats', methods=['GET'])
        def get_memory_stats():
            """获取记忆统计信息"""
            if not self.chat_memory:
                return jsonify({'error': '聊天记忆系统未初始化'}), 503
            
            try:
                stats = self.chat_memory.get_sync_stats()
                
                return jsonify({
                    'success': True,
                    'stats': stats,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({'error': f'获取统计失败: {str(e)}'}), 500
        
        @self.app.route('/api/chat-memory/test/encryption', methods=['POST'])
        def test_encryption():
            """测试加密功能"""
            if not self.chat_memory:
                return jsonify({'error': '聊天记忆系统未初始化'}), 503
            
            try:
                data = request.get_json()
                test_content = data.get('content', '这是一条测试消息')
                test_metadata = data.get('metadata', {'test': True})
                
                encrypted, updated_metadata = self.chat_memory.encrypt_chat_content(
                    test_content, test_metadata
                )
                
                return jsonify({
                    'success': True,
                    'original_content': test_content,
                    'encrypted_content': encrypted,
                    'metadata': updated_metadata,
                    'encrypted_length': len(encrypted)
                })
                
            except Exception as e:
                return jsonify({'error': f'加密测试失败: {str(e)}'}), 500
    
    def _sync_worker(self):
        """后台同步工作线程"""
        logger.info("后台同步工作线程启动")
        
        while self.sync_active:
            try:
                if self.chat_memory:
                    # 导入新聊天记录
                    chat_result = self.chat_memory.import_chat_messages(
                        limit=self.config.get('sync', {}).get('batch_size', 100),
                        days_back=1  # 只同步最近1天的
                    )
                    
                    # 导入新社交关系
                    relationship_result = self.chat_memory.import_social_relationships(
                        limit=self.config.get('sync', {}).get('batch_size', 100) // 2
                    )
                    
                    logger.info(f"后台同步完成: "
                               f"聊天={chat_result.get('imported', 0)}条, "
                               f"关系={relationship_result.get('imported', 0)}条")
                
                # 等待下次同步
                time.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"后台同步异常: {e}")
                time.sleep(60)  # 出错后等待1分钟再重试
    
    def start_api_server(self, host: str = '0.0.0.0', port: int = 8080):
        """
        启动API服务器
        
        Args:
            host: 监听地址
            port: 监听端口
        """
        logger.info(f"启动API服务器: {host}:{port}")
        
        try:
            self.app.run(
                host=host,
                port=port,
                debug=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"API服务器启动失败: {e}")
            raise
    
    def start_background_sync(self):
        """启动后台同步服务"""
        if not self.chat_memory:
            logger.error("聊天记忆系统未初始化，无法启动后台同步")
            return False
        
        if self.sync_active:
            logger.warning("后台同步服务已在运行中")
            return True
        
        try:
            self.sync_active = True
            self.sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
            self.sync_thread.start()
            
            logger.info("后台同步服务已启动")
            return True
            
        except Exception as e:
            self.sync_active = False
            logger.error(f"启动后台同步服务失败: {e}")
            return False
    
    def stop_background_sync(self):
        """停止后台同步服务"""
        if not self.sync_active:
            return True
        
        try:
            self.sync_active = False
            if self.sync_thread:
                self.sync_thread.join(timeout=10)
            
            logger.info("后台同步服务已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止后台同步服务失败: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'chat_memory_available': bool(self.chat_memory),
            'social_manager_available': bool(self.social_manager),
            'sync_active': self.sync_active,
            'config_loaded': bool(self.config)
        }
        
        if self.chat_memory:
            try:
                stats = self.chat_memory.get_sync_stats()
                status['sync_stats'] = stats
            except Exception as e:
                status['sync_stats_error'] = str(e)
        
        return status


# 全局实例
_integrator_instance = None

def get_chat_memory_integrator(config_file: Optional[str] = None) -> ChatMemoryIntegrator:
    """
    获取聊天记忆集成控制器实例（单例模式）
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        ChatMemoryIntegrator实例
    """
    global _integrator_instance
    
    if _integrator_instance is None:
        config_path = config_file or "configs/chat_memory_config.json"
        _integrator_instance = ChatMemoryIntegrator(config_path)
    
    return _integrator_instance


def start_chat_memory_service(host: str = '0.0.0.0', port: int = 8080):
    """
    启动聊天记忆服务（API服务器 + 后台同步）
    
    Args:
        host: API服务器监听地址
        port: API服务器监听端口
    """
    logger.info("启动聊天记录永久记忆服务")
    
    # 获取集成控制器
    integrator = get_chat_memory_integrator()
    
    # 启动后台同步
    integrator.start_background_sync()
    
    # 启动API服务器
    integrator.start_api_server(host=host, port=port)


if __name__ == "__main__":
    print("聊天记录永久记忆集成控制器")
    print("=" * 60)
    
    # 创建集成控制器
    integrator = ChatMemoryIntegrator()
    
    # 获取状态
    status = integrator.get_status()
    print(f"系统状态:")
    print(f"  聊天记忆系统: {'可用' if status['chat_memory_available'] else '不可用'}")
    print(f"  社交关系管理器: {'可用' if status['social_manager_available'] else '不可用'}")
    print(f"  后台同步: {'运行中' if status['sync_active'] else '未运行'}")
    
    if 'sync_stats' in status:
        stats = status['sync_stats']
        print(f"\n同步统计:")
        print(f"  已同步: {stats.get('total_synced', 0)}条")
        print(f"  待同步: {stats.get('total_pending', 0)}条")
        print(f"  失败: {stats.get('total_failed', 0)}条")
    
    print("\n服务启动命令: python src/chat_memory_integrator.py start")
    print("API端点: /api/chat-memory/*")
    print("后台同步间隔: 5分钟")
    
    # 如果是作为独立服务启动
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'start':
        print("\n启动聊天记忆服务...")
        integrator.start_background_sync()
        
        # 保持主线程运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n收到停止信号，优雅停止服务...")
            integrator.stop_background_sync()
            print("服务已停止")