"""
跨SellAI网络客户端模块
实现与其他SellAI节点的通信功能，包括资源同步、匹配查询、任务协作等。
"""

import json
import time
import uuid
import base64
import hashlib
import hmac
from typing import Optional, Dict, List, Any, Tuple, Callable
import requests
from datetime import datetime, timezone
from urllib.parse import urljoin
import logging
import threading
from queue import Queue, Empty

logger = logging.getLogger(__name__)

class NetworkClientError(Exception):
    """网络客户端错误基类"""
    pass

class AuthenticationError(NetworkClientError):
    """认证错误"""
    pass

class MessageExpiredError(NetworkClientError):
    """消息过期错误"""
    pass

class NodeUnavailableError(NetworkClientError):
    """节点不可用错误"""
    pass


class SellAINetworkClient:
    """SellAI网络客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化网络客户端
        
        Args:
            config: 配置字典，包含：
                - node_id: 本节点ID
                - api_key_id: API密钥ID
                - api_secret: API密钥
                - coordinator_url: 协调器URL（可选）
                - default_timeout: 默认超时时间（秒）
                - max_retries: 最大重试次数
                - enable_compression: 是否启用gzip压缩
        """
        self.node_id = config.get('node_id', 'unknown_node')
        self.api_key_id = config.get('api_key_id')
        self.api_secret = config.get('api_secret')
        self.coordinator_url = config.get('coordinator_url')
        self.default_timeout = config.get('default_timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.enable_compression = config.get('enable_compression', True)
        
        # 节点缓存：node_id -> (base_url, last_seen, status)
        self.node_cache = {}
        # 连接池
        self.session = requests.Session()
        # 消息ID生成器
        self.message_counter = 0
        # 回调函数注册表：message_id -> callback
        self.callback_registry = {}
        # 异步消息队列
        self.message_queue = Queue()
        # 是否运行异步处理线程
        self._running = False
        self._processing_thread = None
        
        # 设置默认请求头
        self.session.headers.update({
            'User-Agent': f'SellAI-Network-Client/1.0 ({self.node_id})',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip' if self.enable_compression else 'identity'
        })
        
        logger.info(f"网络客户端初始化完成，节点ID: {self.node_id}")
    
    def _generate_message_id(self) -> str:
        """生成全局唯一消息ID"""
        timestamp = int(time.time() * 1000)
        random_part = uuid.uuid4().hex[:8]
        self.message_counter += 1
        return f"msg_{timestamp}_{random_part}_{self.message_counter}"
    
    def _sign_message(self, header: Dict, body: Dict) -> str:
        """
        对消息进行HMAC-SHA256签名
        
        Args:
            header: 消息头
            body: 消息体
            
        Returns:
            Base64编码的签名
        """
        if not self.api_secret:
            raise AuthenticationError("API密钥未配置，无法签名")
        
        # 确保时间戳存在
        if 'timestamp' not in header:
            header['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # 序列化header和body
        header_json = json.dumps(header, sort_keys=True, separators=(',', ':'))
        body_json = json.dumps(body, sort_keys=True, separators=(',', ':'))
        
        # 计算签名
        message = f"{header_json}.{body_json}".encode('utf-8')
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message,
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _verify_message(self, header: Dict, body: Dict, signature: str, secret: str) -> bool:
        """验证消息签名"""
        try:
            # 重新计算签名
            header_json = json.dumps(header, sort_keys=True, separators=(',', ':'))
            body_json = json.dumps(body, sort_keys=True, separators=(',', ':'))
            message = f"{header_json}.{body_json}".encode('utf-8')
            
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                message,
                hashlib.sha256
            ).digest()
            
            expected_b64 = base64.b64encode(expected_signature).decode('utf-8')
            return hmac.compare_digest(expected_b64, signature)
        except Exception as e:
            logger.error(f"验证签名时出错: {e}")
            return False
    
    def _check_message_expiry(self, timestamp: str, ttl: int = 300) -> bool:
        """检查消息是否过期"""
        try:
            msg_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age = (now - msg_time).total_seconds()
            return age <= ttl
        except Exception as e:
            logger.error(f"解析时间戳失败: {timestamp}, 错误: {e}")
            return False
    
    def _build_message(self, message_type: str, body: Dict, 
                      receiver_node_id: Optional[str] = None,
                      priority: int = 3, ttl: int = 300) -> Dict:
        """
        构建标准消息
        
        Returns:
            完整的消息字典
        """
        header = {
            'message_id': self._generate_message_id(),
            'message_type': message_type,
            'protocol_version': '1.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'sender_node_id': self.node_id,
            'ttl': ttl,
            'priority': priority
        }
        
        if receiver_node_id:
            header['receiver_node_id'] = receiver_node_id
        
        signature = self._sign_message(header, body)
        
        return {
            'header': header,
            'body': body,
            'signature': {
                'algorithm': 'HMAC-SHA256',
                'key_id': self.api_key_id,
                'signature': signature
            }
        }
    
    def _parse_response(self, response_data: Dict) -> Tuple[Dict, Dict]:
        """
        解析响应消息，验证签名
        
        Returns:
            (header, body) 元组
            
        Raises:
            AuthenticationError: 签名验证失败
            MessageExpiredError: 消息已过期
        """
        header = response_data.get('header', {})
        body = response_data.get('body', {})
        signature_info = response_data.get('signature', {})
        
        # 验证消息完整性
        if not header or not body or not signature_info:
            raise NetworkClientError("响应消息格式不完整")
        
        # 检查消息过期
        timestamp = header.get('timestamp')
        ttl = header.get('ttl', 300)
        if not self._check_message_expiry(timestamp, ttl):
            raise MessageExpiredError(f"消息已过期，时间戳: {timestamp}")
        
        # 注意：这里应该根据signature_info['key_id']查找对方的API密钥
        # 由于我们不知道对方的secret，暂时跳过签名验证
        # 实际部署时需要建立密钥交换机制
        
        return header, body
    
    def send_request(self, target_node_id: str, message_type: str, body: Dict,
                    base_url: Optional[str] = None, timeout: Optional[int] = None) -> Dict:
        """
        发送请求到指定节点
        
        Args:
            target_node_id: 目标节点ID
            message_type: 消息类型
            body: 消息体
            base_url: 目标节点基础URL（如未提供则从缓存查找）
            timeout: 超时时间（秒）
            
        Returns:
            响应消息体
            
        Raises:
            NodeUnavailableError: 节点不可用
            NetworkClientError: 网络通信错误
        """
        # 获取目标节点URL
        if not base_url:
            node_info = self.node_cache.get(target_node_id)
            if not node_info:
                # 尝试从协调器获取节点信息
                node_info = self._discover_node(target_node_id)
                if not node_info:
                    raise NodeUnavailableError(f"无法找到节点: {target_node_id}")
            base_url = node_info[0]
        
        # 构建完整URL
        endpoint_map = {
            'resource_sync_request': '/api/network/v1/sync/request',
            'match_query_request': '/api/network/v1/match/query',
            'task_delegation_request': '/api/network/v1/tasks/delegate',
            'node_heartbeat': '/api/network/v1/nodes/heartbeat',
        }
        
        endpoint = endpoint_map.get(message_type, '/api/network/v1/message')
        url = urljoin(base_url, endpoint)
        
        # 构建消息
        message = self._build_message(message_type, body, target_node_id)
        
        # 发送请求
        timeout = timeout or self.default_timeout
        headers = {
            'Content-Type': 'application/json',
            'X-Node-ID': self.node_id,
            'X-Timestamp': message['header']['timestamp']
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.post(
                    url,
                    json=message,
                    headers=headers,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    _, response_body = self._parse_response(response_data)
                    return response_body
                elif response.status_code == 404:
                    raise NodeUnavailableError(f"节点端点不存在: {url}")
                elif response.status_code >= 500:
                    logger.warning(f"服务器错误，重试 {attempt + 1}/{self.max_retries}")
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)  # 指数退避
                        continue
                    else:
                        raise NetworkClientError(f"服务器错误: {response.status_code}")
                else:
                    # 客户端错误，不重试
                    error_body = response.json() if response.content else {}
                    error_msg = error_body.get('body', {}).get('error_message', '未知错误')
                    raise NetworkClientError(f"请求失败 [{response.status_code}]: {error_msg}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时，重试 {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise NetworkClientError("请求超时，达到最大重试次数")
            except requests.exceptions.ConnectionError:
                logger.warning(f"连接错误，重试 {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise NodeUnavailableError(f"无法连接到节点: {target_node_id}")
        
        # 理论上不会执行到这里
        raise NetworkClientError("未知错误")
    
    def sync_resources(self, target_node_id: str, sync_domain: str = 'industry_resources',
                      filters: Optional[Dict] = None, limit: int = 100) -> Dict:
        """
        从目标节点同步资源
        
        Args:
            target_node_id: 目标节点ID
            sync_domain: 同步域
            filters: 过滤条件
            limit: 每批次最大记录数
            
        Returns:
            同步结果
        """
        body = {
            'sync_domain': sync_domain,
            'filters': filters or {},
            'pagination': {
                'limit': limit,
                'offset': 0
            },
            'sync_mode': 'incremental',
            'last_sync_token': None
        }
        
        try:
            return self.send_request(
                target_node_id,
                'resource_sync_request',
                body
            )
        except Exception as e:
            logger.error(f"资源同步失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'resources': [],
                'total_count': 0
            }
    
    def query_match(self, target_node_id: str, query_resource: Dict, 
                   min_score: float = 0.7, max_results: int = 20) -> Dict:
        """
        查询目标节点的匹配资源
        
        Args:
            target_node_id: 目标节点ID
            query_resource: 查询资源描述
            min_score: 最小匹配分数
            max_results: 最大返回结果数
            
        Returns:
            匹配结果
        """
        body = {
            'query_resource': query_resource,
            'match_criteria': {
                'min_score': min_score,
                'max_results': max_results
            }
        }
        
        try:
            return self.send_request(
                target_node_id,
                'match_query_request',
                body
            )
        except Exception as e:
            logger.error(f"匹配查询失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'matches': [],
                'total_matches': 0
            }
    
    def send_heartbeat(self, target_node_id: str) -> bool:
        """
        发送心跳到目标节点
        
        Returns:
            是否成功
        """
        body = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'load_level': 'normal',  # normal, high, overload
            'available_services': ['sync', 'match', 'task']
        }
        
        try:
            response = self.send_request(
                target_node_id,
                'node_heartbeat',
                body
            )
            return response.get('status') == 'alive'
        except Exception as e:
            logger.warning(f"心跳发送失败: {e}")
            return False
    
    def register_with_coordinator(self) -> bool:
        """
        向协调器注册本节点
        
        Returns:
            是否成功
        """
        if not self.coordinator_url:
            logger.warning("未配置协调器URL，跳过注册")
            return False
        
        body = {
            'node_id': self.node_id,
            'capabilities': {
                'sync_domains': ['industry_resources', 'resource_categories'],
                'max_connections': 100,
                'supported_protocols': ['HTTP/1.1']
            },
            'contact_info': {
                'base_url': f"https://{self.node_id}.sellai.network",  # 示例
                'admin_email': 'admin@example.com'
            }
        }
        
        try:
            # 直接使用requests发送，避免循环依赖
            message = self._build_message('node_register_request', body)
            response = requests.post(
                urljoin(self.coordinator_url, '/api/network/v1/nodes/register'),
                json=message,
                timeout=self.default_timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                _, response_body = self._parse_response(response_data)
                if response_body.get('status') == 'registered':
                    # 更新节点缓存
                    neighbor_nodes = response_body.get('neighbor_nodes', [])
                    for node in neighbor_nodes:
                        self.node_cache[node['node_id']] = (
                            node['base_url'],
                            time.time(),
                            'online'
                        )
                    logger.info(f"节点注册成功，邻居节点数: {len(neighbor_nodes)}")
                    return True
            return False
        except Exception as e:
            logger.error(f"节点注册失败: {e}")
            return False
    
    def _discover_node(self, node_id: str) -> Optional[Tuple[str, float, str]]:
        """
        发现节点信息
        
        Returns:
            (base_url, last_seen, status) 或 None
        """
        if self.coordinator_url:
            try:
                body = {'target_node_id': node_id}
                message = self._build_message('node_discovery_request', body)
                response = requests.post(
                    urljoin(self.coordinator_url, '/api/network/v1/nodes/discover'),
                    json=message,
                    timeout=self.default_timeout
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    _, response_body = self._parse_response(response_data)
                    node_info = response_body.get('node_info')
                    if node_info:
                        return (
                            node_info['base_url'],
                            time.time(),
                            node_info.get('status', 'online')
                        )
            except Exception:
                pass
        
        # 尝试通过DNS或其他方式发现
        # 示例：假设节点URL遵循固定模式
        base_url = f"https://{node_id}.sellai.network"
        # 简单检查是否可达（这里不实际连接）
        return (base_url, time.time(), 'unknown')
    
    def start_async_processing(self):
        """启动异步消息处理线程"""
        if self._running:
            return
        
        self._running = True
        self._processing_thread = threading.Thread(
            target=self._process_message_queue,
            daemon=True
        )
        self._processing_thread.start()
        logger.info("异步消息处理线程已启动")
    
    def stop_async_processing(self):
        """停止异步消息处理线程"""
        self._running = False
        if self._processing_thread:
            self._processing_thread.join(timeout=5)
            self._processing_thread = None
        logger.info("异步消息处理线程已停止")
    
    def _process_message_queue(self):
        """处理异步消息队列"""
        while self._running:
            try:
                # 从队列获取消息，最多等待1秒
                item = self.message_queue.get(timeout=1)
                if item is None:
                    continue
                
                message_type, body, callback, target_node_id = item
                
                try:
                    response = self.send_request(target_node_id, message_type, body)
                    if callback:
                        callback(response)
                except Exception as e:
                    logger.error(f"异步消息处理失败: {e}")
                    if callback:
                        callback({'success': False, 'error': str(e)})
                
                self.message_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"消息队列处理异常: {e}")
    
    def send_async(self, target_node_id: str, message_type: str, body: Dict,
                  callback: Optional[Callable[[Dict], None]] = None):
        """
        异步发送消息
        
        Args:
            target_node_id: 目标节点ID
            message_type: 消息类型
            body: 消息体
            callback: 回调函数，接收响应
        """
        self.message_queue.put((message_type, body, callback, target_node_id))
    
    def broadcast_to_neighbors(self, message_type: str, body: Dict,
                              exclude_nodes: Optional[List[str]] = None):
        """
        广播消息给所有邻居节点
        
        Args:
            message_type: 消息类型
            body: 消息体
            exclude_nodes: 排除的节点ID列表
        """
        exclude_set = set(exclude_nodes or [])
        
        for node_id, (base_url, _, status) in self.node_cache.items():
            if node_id == self.node_id or node_id in exclude_set:
                continue
            
            if status != 'online':
                continue
            
            # 异步发送，不等待响应
            self.send_async(node_id, message_type, body)


# 配置示例和快捷函数
def create_default_client(node_id: str, api_key: str, secret: str,
                         coordinator_url: Optional[str] = None) -> SellAINetworkClient:
    """
    创建默认配置的网络客户端
    
    Args:
        node_id: 节点ID
        api_key: API密钥ID
        secret: API密钥
        coordinator_url: 协调器URL
        
    Returns:
        网络客户端实例
    """
    config = {
        'node_id': node_id,
        'api_key_id': api_key,
        'api_secret': secret,
        'coordinator_url': coordinator_url,
        'default_timeout': 30,
        'max_retries': 3,
        'enable_compression': True
    }
    
    client = SellAINetworkClient(config)
    
    # 自动注册到协调器
    if coordinator_url:
        client.register_with_coordinator()
    
    # 启动异步处理
    client.start_async_processing()
    
    return client


if __name__ == '__main__':
    # 示例用法
    logging.basicConfig(level=logging.INFO)
    
    # 创建客户端
    client = create_default_client(
        node_id='test_node_1',
        api_key='test_key',
        secret='test_secret',
        coordinator_url='https://coordinator.example.com'
    )
    
    # 示例：同步资源
    filters = {
        'resource_type': [1, 2],
        'updated_since': '2026-04-01T00:00:00Z'
    }
    
    try:
        result = client.sync_resources(
            target_node_id='node_us_east_1',
            sync_domain='industry_resources',
            filters=filters,
            limit=50
        )
        print(f"同步结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"同步失败: {e}")
    
    # 清理
    client.stop_async_processing()