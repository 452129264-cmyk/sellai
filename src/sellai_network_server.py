"""
跨SellAI网络服务器模块
提供HTTP API接口，处理其他节点的网络请求。
"""

import json
import time
import logging
import threading
from typing import Optional, Dict, List, Any, Callable, Tuple
from datetime import datetime, timezone
import sqlite3
import hashlib
import hmac
import base64
from functools import wraps

# 尝试导入Flask，如果不可用则使用备用方案
try:
    from flask import Flask, request, jsonify, Response
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    # 简化版HTTP服务器
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

logger = logging.getLogger(__name__)

class NetworkServerError(Exception):
    """网络服务器错误基类"""
    pass

class MessageValidationError(NetworkServerError):
    """消息验证错误"""
    pass

class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self._init_api_key_table()
    
    def _init_api_key_table(self):
        """初始化API密钥表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_api_keys (
                key_id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                secret_key TEXT NOT NULL,
                permissions TEXT NOT NULL,  -- JSON格式权限列表
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                last_used TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        """)
        
        # 创建节点信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_nodes (
                node_id TEXT PRIMARY KEY,
                base_url TEXT NOT NULL,
                capabilities TEXT NOT NULL,  -- JSON格式能力描述
                status TEXT CHECK(status IN ('online', 'offline', 'maintenance')) DEFAULT 'online',
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_secret_key(self, key_id: str) -> Optional[str]:
        """获取API密钥"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT secret_key FROM network_api_keys 
            WHERE key_id = ? AND is_active = 1 
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        """, (key_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def register_node(self, node_id: str, base_url: str, capabilities: Dict) -> bool:
        """注册节点"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO network_nodes 
                (node_id, base_url, capabilities, status, last_heartbeat, updated_at)
                VALUES (?, ?, ?, 'online', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (node_id, base_url, json.dumps(capabilities)))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"注册节点失败: {e}")
            return False
        finally:
            conn.close()


class MessageValidator:
    """消息验证器"""
    
    def __init__(self, api_key_manager: APIKeyManager):
        self.api_key_manager = api_key_manager
        # 防重放攻击缓存（message_id -> timestamp）
        self.replay_cache = {}
        self.max_cache_size = 10000
        self.cache_lock = threading.Lock()
    
    def validate_message(self, message_data: Dict) -> Tuple[Dict, Dict]:
        """
        验证消息完整性和签名
        
        Returns:
            (header, body) 元组
            
        Raises:
            MessageValidationError: 验证失败
        """
        # 检查基本结构
        if not isinstance(message_data, dict):
            raise MessageValidationError("消息必须是JSON对象")
        
        header = message_data.get('header', {})
        body = message_data.get('body', {})
        signature_info = message_data.get('signature', {})
        
        if not header or not body or not signature_info:
            raise MessageValidationError("消息缺少必要字段")
        
        # 检查消息头必填字段
        required_fields = ['message_id', 'message_type', 'protocol_version', 
                          'timestamp', 'sender_node_id']
        
        for field in required_fields:
            if field not in header:
                raise MessageValidationError(f"消息头缺少字段: {field}")
        
        # 检查协议版本
        if header['protocol_version'] != '1.0':
            raise MessageValidationError(f"不支持的协议版本: {header['protocol_version']}")
        
        # 检查消息是否过期
        self._check_expiry(header)
        
        # 检查重放攻击
        self._check_replay_attack(header)
        
        # 验证签名
        self._verify_signature(header, body, signature_info)
        
        return header, body
    
    def _check_expiry(self, header: Dict):
        """检查消息是否过期"""
        timestamp_str = header['timestamp']
        ttl = header.get('ttl', 300)
        
        try:
            msg_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age = (now - msg_time).total_seconds()
            
            if age > ttl:
                raise MessageValidationError(f"消息已过期，年龄: {age}秒，TTL: {ttl}秒")
        except ValueError as e:
            raise MessageValidationError(f"无效的时间戳格式: {timestamp_str}")
    
    def _check_replay_attack(self, header: Dict):
        """检查重放攻击"""
        message_id = header['message_id']
        timestamp_str = header['timestamp']
        
        with self.cache_lock:
            # 清理旧缓存项（超过5分钟）
            current_time = time.time()
            expired_keys = [
                key for key, cached_time in self.replay_cache.items()
                if current_time - cached_time > 300
            ]
            
            for key in expired_keys:
                del self.replay_cache[key]
            
            # 检查是否已处理过
            if message_id in self.replay_cache:
                raise MessageValidationError(f"消息ID已处理过: {message_id}")
            
            # 添加到缓存
            self.replay_cache[message_id] = current_time
            
            # 限制缓存大小
            if len(self.replay_cache) > self.max_cache_size:
                # 删除最旧的项
                oldest_key = min(self.replay_cache.items(), key=lambda x: x[1])[0]
                del self.replay_cache[oldest_key]
    
    def _verify_signature(self, header: Dict, body: Dict, signature_info: Dict):
        """验证签名"""
        algorithm = signature_info.get('algorithm')
        key_id = signature_info.get('key_id')
        signature = signature_info.get('signature')
        
        if not algorithm or not key_id or not signature:
            raise MessageValidationError("签名信息不完整")
        
        if algorithm != 'HMAC-SHA256':
            raise MessageValidationError(f"不支持的签名算法: {algorithm}")
        
        # 获取发送方的密钥
        secret_key = self.api_key_manager.get_secret_key(key_id)
        if not secret_key:
            raise MessageValidationError(f"无效的API密钥ID: {key_id}")
        
        # 重新计算签名
        header_json = json.dumps(header, sort_keys=True, separators=(',', ':'))
        body_json = json.dumps(body, sort_keys=True, separators=(',', ':'))
        
        message = f"{header_json}.{body_json}".encode('utf-8')
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            message,
            hashlib.sha256
        ).digest()
        
        expected_b64 = base64.b64encode(expected_signature).decode('utf-8')
        
        if not hmac.compare_digest(expected_b64, signature):
            raise MessageValidationError("签名验证失败")


class RequestHandler:
    """请求处理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self.api_key_manager = APIKeyManager(db_path)
        self.validator = MessageValidator(self.api_key_manager)
        
        # 注册消息处理器
        self.handlers = {
            'node_register_request': self.handle_node_register,
            'resource_sync_request': self.handle_resource_sync,
            'match_query_request': self.handle_match_query,
            'task_delegation_request': self.handle_task_delegation,
            'node_heartbeat': self.handle_heartbeat,
            'node_discovery_request': self.handle_node_discovery,
        }
    
    def process_request(self, message_data: Dict) -> Dict:
        """
        处理请求消息
        
        Returns:
            响应消息
        """
        try:
            # 验证消息
            header, body = self.validator.validate_message(message_data)
            
            message_type = header['message_type']
            sender_node_id = header['sender_node_id']
            
            logger.info(f"处理消息: {message_type} 来自: {sender_node_id}")
            
            # 查找处理器
            handler = self.handlers.get(message_type)
            if not handler:
                return self._build_error_response(
                    header,
                    f"不支持的消息类型: {message_type}",
                    'NETWORK_004'
                )
            
            # 处理请求
            response_body = handler(header, body)
            
            # 构建响应
            response_header = {
                'message_id': self._generate_response_id(header['message_id']),
                'message_type': f"{message_type}_response",
                'protocol_version': '1.0',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'sender_node_id': 'self',  # 实际应为本节点ID
                'receiver_node_id': sender_node_id,
                'ttl': 300
            }
            
            return self._build_message(response_header, response_body)
            
        except MessageValidationError as e:
            logger.warning(f"消息验证失败: {e}")
            return self._build_error_response(
                message_data.get('header', {}),
                str(e),
                'NETWORK_001'
            )
        except Exception as e:
            logger.error(f"处理请求时出错: {e}", exc_info=True)
            return self._build_error_response(
                message_data.get('header', {}),
                f"服务器内部错误: {str(e)}",
                'NETWORK_005'
            )
    
    def handle_node_register(self, header: Dict, body: Dict) -> Dict:
        """处理节点注册请求"""
        node_id = body.get('node_id')
        capabilities = body.get('capabilities', {})
        contact_info = body.get('contact_info', {})
        
        if not node_id:
            return {
                'status': 'error',
                'error_message': '缺少node_id字段'
            }
        
        # 从contact_info中提取base_url
        base_url = contact_info.get('base_url', f"https://{node_id}.sellai.network")
        
        # 注册节点
        success = self.api_key_manager.register_node(node_id, base_url, capabilities)
        
        if success:
            # 返回邻居节点列表
            neighbor_nodes = self._get_neighbor_nodes(node_id)
            
            return {
                'status': 'registered',
                'node_id': node_id,
                'registration_time': datetime.now(timezone.utc).isoformat(),
                'neighbor_nodes': neighbor_nodes
            }
        else:
            return {
                'status': 'failed',
                'error_message': '节点注册失败'
            }
    
    def handle_resource_sync(self, header: Dict, body: Dict) -> Dict:
        """处理资源同步请求"""
        from .network_data_sync import DataSyncManager
        
        sync_domain = body.get('sync_domain', 'industry_resources')
        filters = body.get('filters', {})
        pagination = body.get('pagination', {})
        sync_mode = body.get('sync_mode', 'incremental')
        last_sync_token = body.get('last_sync_token')
        
        limit = pagination.get('limit', 100)
        offset = pagination.get('offset', 0)
        
        try:
            sync_manager = DataSyncManager(self.db_path)
            result = sync_manager.sync_resources(
                sync_domain=sync_domain,
                filters=filters,
                limit=limit,
                offset=offset,
                sync_mode=sync_mode,
                last_sync_token=last_sync_token
            )
            
            return result
            
        except Exception as e:
            logger.error(f"资源同步处理失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'resources': [],
                'total_count': 0,
                'sync_token': None
            }
    
    def handle_match_query(self, header: Dict, body: Dict) -> Dict:
        """处理匹配查询请求"""
        from .network_data_sync import DataSyncManager
        
        query_resource = body.get('query_resource', {})
        match_criteria = body.get('match_criteria', {})
        preferred_nodes = body.get('preferred_nodes', [])
        
        min_score = match_criteria.get('min_score', 0.7)
        max_results = match_criteria.get('max_results', 20)
        
        try:
            sync_manager = DataSyncManager(self.db_path)
            matches = sync_manager.find_cross_instance_matches(
                query_resource=query_resource,
                min_score=min_score,
                max_results=max_results
            )
            
            return {
                'success': True,
                'matches': matches,
                'total_matches': len(matches),
                'query_summary': {
                    'min_score': min_score,
                    'max_results': max_results
                }
            }
            
        except Exception as e:
            logger.error(f"匹配查询处理失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'matches': [],
                'total_matches': 0
            }
    
    def handle_task_delegation(self, header: Dict, body: Dict) -> Dict:
        """处理任务委托请求"""
        # 简化实现，实际应集成任务系统
        task_description = body.get('task_description', {})
        deadline = body.get('deadline')
        priority = body.get('priority', 3)
        
        # 生成任务ID
        task_id = f"task_{int(time.time())}_{hashlib.md5(json.dumps(task_description).encode()).hexdigest()[:8]}"
        
        return {
            'status': 'accepted',
            'task_id': task_id,
            'accepted_at': datetime.now(timezone.utc).isoformat(),
            'estimated_completion_time': None,  # 实际应估算
            'message': '任务已接受，等待处理'
        }
    
    def handle_heartbeat(self, header: Dict, body: Dict) -> Dict:
        """处理心跳请求"""
        sender_node_id = header['sender_node_id']
        timestamp = body.get('timestamp')
        load_level = body.get('load_level', 'normal')
        
        # 更新节点最后心跳时间
        self._update_node_heartbeat(sender_node_id)
        
        return {
            'status': 'alive',
            'received_at': datetime.now(timezone.utc).isoformat(),
            'server_time': datetime.now(timezone.utc).isoformat(),
            'load_status': 'normal',  # 本节点负载状态
            'active_connections': 0   # 实际应统计
        }
    
    def handle_node_discovery(self, header: Dict, body: Dict) -> Dict:
        """处理节点发现请求"""
        target_node_id = body.get('target_node_id')
        
        if not target_node_id:
            return {
                'status': 'error',
                'error_message': '缺少target_node_id字段'
            }
        
        # 查询节点信息
        node_info = self._get_node_info(target_node_id)
        
        if node_info:
            return {
                'status': 'found',
                'node_info': node_info
            }
        else:
            return {
                'status': 'not_found',
                'error_message': f'未找到节点: {target_node_id}'
            }
    
    def _get_neighbor_nodes(self, exclude_node_id: str) -> List[Dict]:
        """获取邻居节点列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT node_id, base_url, capabilities, status, last_heartbeat
            FROM network_nodes
            WHERE node_id != ? AND status = 'online'
            ORDER BY last_heartbeat DESC
            LIMIT 10
        """, (exclude_node_id,))
        
        nodes = []
        for row in cursor.fetchall():
            nodes.append({
                'node_id': row[0],
                'base_url': row[1],
                'capabilities': json.loads(row[2]),
                'status': row[3],
                'last_heartbeat': row[4]
            })
        
        conn.close()
        return nodes
    
    def _update_node_heartbeat(self, node_id: str):
        """更新节点心跳时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE network_nodes 
            SET last_heartbeat = CURRENT_TIMESTAMP,
                status = 'online',
                updated_at = CURRENT_TIMESTAMP
            WHERE node_id = ?
        """, (node_id,))
        
        conn.commit()
        conn.close()
    
    def _get_node_info(self, node_id: str) -> Optional[Dict]:
        """获取节点信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT node_id, base_url, capabilities, status, last_heartbeat
            FROM network_nodes
            WHERE node_id = ?
        """, (node_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'node_id': row[0],
                'base_url': row[1],
                'capabilities': json.loads(row[2]),
                'status': row[3],
                'last_heartbeat': row[4]
            }
        
        return None
    
    def _generate_response_id(self, request_id: str) -> str:
        """生成响应消息ID"""
        timestamp = int(time.time() * 1000)
        return f"resp_{timestamp}_{hashlib.md5(request_id.encode()).hexdigest()[:8]}"
    
    def _build_message(self, header: Dict, body: Dict) -> Dict:
        """构建消息（简化版，实际应签名）"""
        return {
            'header': header,
            'body': body,
            'signature': {
                'algorithm': 'HMAC-SHA256',
                'key_id': 'server_key',
                'signature': 'placeholder'  # 实际应计算签名
            }
        }
    
    def _build_error_response(self, request_header: Dict, 
                             error_message: str, error_code: str) -> Dict:
        """构建错误响应"""
        response_header = {
            'message_id': self._generate_response_id(request_header.get('message_id', 'unknown')),
            'message_type': 'error_response',
            'protocol_version': '1.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'sender_node_id': 'self',
            'receiver_node_id': request_header.get('sender_node_id', 'unknown'),
            'ttl': 300
        }
        
        return self._build_message(response_header, {
            'success': False,
            'error_code': error_code,
            'error_message': error_message,
            'request_id': request_header.get('message_id')
        })


# Flask服务器实现
if FLASK_AVAILABLE:
    class FlaskNetworkServer:
        """基于Flask的网络服务器"""
        
        def __init__(self, db_path: str = "data/shared_state/state.db",
                    host: str = '0.0.0.0', port: int = 8443):
            self.app = Flask(__name__)
            self.host = host
            self.port = port
            self.request_handler = RequestHandler(db_path)
            
            self._setup_routes()
            
            # 配置日志
            logging.basicConfig(level=logging.INFO)
            logger.setLevel(logging.INFO)
        
        def _setup_routes(self):
            """设置路由"""
            
            @self.app.route('/api/network/v1/message', methods=['POST'])
            def handle_message():
                """通用消息处理端点"""
                try:
                    message_data = request.get_json()
                    if not message_data:
                        return jsonify({
                            'error': '请求体必须是JSON格式'
                        }), 400
                    
                    response = self.request_handler.process_request(message_data)
                    return jsonify(response)
                    
                except Exception as e:
                    logger.error(f"处理请求时异常: {e}", exc_info=True)
                    return jsonify({
                        'error': '服务器内部错误',
                        'message': str(e)
                    }), 500
            
            @self.app.route('/api/network/v1/nodes/register', methods=['POST'])
            def register_node():
                """节点注册端点"""
                return handle_message()
            
            @self.app.route('/api/network/v1/sync/request', methods=['POST'])
            def sync_request():
                """资源同步端点"""
                return handle_message()
            
            @self.app.route('/api/network/v1/match/query', methods=['POST'])
            def match_query():
                """匹配查询端点"""
                return handle_message()
            
            @self.app.route('/api/network/v1/tasks/delegate', methods=['POST'])
            def task_delegate():
                """任务委托端点"""
                return handle_message()
            
            @self.app.route('/api/network/v1/nodes/heartbeat', methods=['POST'])
            def heartbeat():
                """心跳端点"""
                return handle_message()
            
            @self.app.route('/api/network/v1/health', methods=['GET'])
            def health_check():
                """健康检查端点"""
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'service': 'sellai_network_server'
                })
        
        def run(self, debug: bool = False):
            """运行服务器"""
            logger.info(f"启动网络服务器，监听 {self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)
        
        def get_app(self):
            """获取Flask应用实例"""
            return self.app

else:
    # 简化版HTTP服务器
    class SimpleNetworkServer:
        """基于http.server的简化网络服务器"""
        
        def __init__(self, db_path: str = "data/shared_state/state.db",
                    host: str = '0.0.0.0', port: int = 8443):
            self.host = host
            self.port = port
            self.request_handler = RequestHandler(db_path)
            
            class NetworkRequestHandler(BaseHTTPRequestHandler):
                server_instance = self
                
                def do_POST(self):
                    self.handle_post()
                
                def do_GET(self):
                    self.handle_get()
                
                def handle_post(self):
                    content_length = int(self.headers.get('Content-Length', 0))
                    if content_length == 0:
                        self.send_error(400, "请求体为空")
                        return
                    
                    try:
                        body = self.rfile.read(content_length)
                        message_data = json.loads(body.decode('utf-8'))
                        
                        response = self.server_instance.request_handler.process_request(message_data)
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                        
                    except json.JSONDecodeError:
                        self.send_error(400, "无效的JSON格式")
                    except Exception as e:
                        logger.error(f"处理请求时异常: {e}")
                        self.send_error(500, f"服务器内部错误: {str(e)}")
                
                def handle_get(self):
                    if self.path == '/api/network/v1/health':
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        
                        response = {
                            'status': 'healthy',
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'service': 'sellai_network_server'
                        }
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                    else:
                        self.send_error(404, "未找到资源")
                
                def log_message(self, format, *args):
                    logger.info(f"{self.address_string()} - {format % args}")
            
            self.handler_class = NetworkRequestHandler
        
        def run(self):
            """运行服务器"""
            server = HTTPServer((self.host, self.port), self.handler_class)
            logger.info(f"启动简化网络服务器，监听 {self.host}:{self.port}")
            server.serve_forever()


# 服务器工厂函数
def create_network_server(db_path: str = "data/shared_state/state.db",
                         host: str = '0.0.0.0', port: int = 8443,
                         use_flask: Optional[bool] = None):
    """
    创建网络服务器实例
    
    Args:
        db_path: 数据库路径
        host: 监听主机
        port: 监听端口
        use_flask: 是否使用Flask（None时自动选择）
        
    Returns:
        服务器实例
    """
    if use_flask is None:
        use_flask = FLASK_AVAILABLE
    
    if use_flask and FLASK_AVAILABLE:
        return FlaskNetworkServer(db_path, host, port)
    else:
        return SimpleNetworkServer(db_path, host, port)


# 命令行接口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='SellAI网络服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听主机')
    parser.add_argument('--port', type=int, default=8443, help='监听端口')
    parser.add_argument('--db-path', default='data/shared_state/state.db',
                       help='数据库路径')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--use-flask', action='store_true', 
                       help='使用Flask（如果可用）')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建并运行服务器
    server = create_network_server(
        db_path=args.db_path,
        host=args.host,
        port=args.port,
        use_flask=args.use_flask
    )
    
    try:
        if hasattr(server, 'run'):
            server.run(debug=args.debug)
        else:
            server.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
    except Exception as e:
        logger.error(f"服务器运行错误: {e}", exc_info=True)