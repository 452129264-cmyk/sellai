#!/usr/bin/env python3
"""
智能路由模块
优化多Agent协作中的消息传递路径，减少通信开销和延迟
"""

import json
import time
import logging
import threading
import sqlite3
import heapq
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import random

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - SMART-ROUTER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """消息类型枚举"""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"
    DATA_SYNC = "data_sync"
    SYSTEM_EVENT = "system_event"

class RoutingStrategy(Enum):
    """路由策略枚举"""
    SHORTEST_PATH = "shortest_path"          # 最短路径
    LOWEST_LATENCY = "lowest_latency"        # 最低延迟
    LOAD_BALANCED = "load_balanced"          # 负载均衡
    RELIABILITY_FIRST = "reliability_first"  # 可靠性优先
    ADAPTIVE = "adaptive"                    # 自适应

@dataclass
class NetworkNode:
    """网络节点信息"""
    node_id: str
    node_type: str
    capabilities: List[str]
    last_seen: datetime
    status: str
    base_url: Optional[str] = None
    geographic_region: str = "global"
    current_load: int = 0
    avg_response_time_ms: float = 100.0
    reliability_score: float = 0.95
    network_distance: Dict[str, float] = None  # 到其他节点的网络距离

    def __post_init__(self):
        if self.network_distance is None:
            self.network_distance = {}

@dataclass
class Message:
    """消息对象"""
    message_id: str
    message_type: MessageType
    source_node: str
    target_node: str
    content: Dict[str, Any]
    priority: int = 2
    created_at: datetime = None
    size_bytes: int = 0
    ttl_seconds: int = 3600  # 生存时间（秒）
    require_ack: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        # 估算消息大小
        if self.size_bytes == 0:
            self.size_bytes = len(json.dumps(self.content).encode('utf-8'))

@dataclass
class RoutingDecision:
    """路由决策结果"""
    message_id: str
    source_node: str
    target_node: str
    path: List[str]  # 路径节点列表
    estimated_latency_ms: float
    routing_strategy: RoutingStrategy
    timestamp: datetime
    actual_latency_ms: Optional[float] = None
    success: Optional[bool] = None

class SmartRouter:
    """智能路由核心类"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化智能路由器
        
        Args:
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.network_nodes: Dict[str, NetworkNode] = {}
        self.message_queue = deque()
        self.batch_buffer: Dict[Tuple[str, str], List[Message]] = defaultdict(list)
        self.routing_history: List[RoutingDecision] = []
        self.latency_history: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        
        # 路由策略权重（自适应调整）
        self.strategy_weights = {
            RoutingStrategy.SHORTEST_PATH: 0.3,
            RoutingStrategy.LOWEST_LATENCY: 0.3,
            RoutingStrategy.LOAD_BALANCED: 0.2,
            RoutingStrategy.RELIABILITY_FIRST: 0.2
        }
        
        # 性能指标
        self.total_messages_sent = 0
        self.total_bytes_sent = 0
        self.avg_latency_ms = 0.0
        self.success_rate = 1.0
        
        # 初始化网络拓扑
        self._load_network_topology()
        
        # 启动路由监控
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_routing_performance, daemon=True)
        self.monitor_thread.start()
        
        # 启动批处理定时器
        self.batch_timer = threading.Timer(5.0, self._process_batch_buffer)
        self.batch_timer.start()
        
        logger.info(f"智能路由器初始化完成，已加载 {len(self.network_nodes)} 个网络节点")
    
    def _load_network_topology(self):
        """从数据库加载网络拓扑"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 加载网络节点
            cursor.execute("SELECT node_id, node_type, capabilities, last_seen, status, base_url, geographic_region FROM network_nodes")
            rows = cursor.fetchall()
            
            for row in rows:
                node_id, node_type, capabilities_json, last_seen_str, status, base_url, geographic_region = row
                
                # 解析能力列表
                capabilities = json.loads(capabilities_json) if capabilities_json else []
                
                # 转换时间戳
                last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
                
                # 创建网络节点
                node = NetworkNode(
                    node_id=node_id,
                    node_type=node_type,
                    capabilities=capabilities,
                    last_seen=last_seen,
                    status=status,
                    base_url=base_url,
                    geographic_region=geographic_region
                )
                
                self.network_nodes[node_id] = node
            
            # 加载通信指标历史，构建延迟矩阵
            cursor.execute("SELECT source_node, target_node, processing_time_ms FROM communication_metrics")
            for source_node, target_node, processing_time in cursor.fetchall():
                if source_node and target_node:
                    key = (source_node, target_node)
                    self.latency_history[key].append(processing_time)
                    
                    # 更新节点间的网络距离（基于历史延迟）
                    avg_latency = sum(self.latency_history[key]) / len(self.latency_history[key])
                    if source_node in self.network_nodes:
                        self.network_nodes[source_node].network_distance[target_node] = avg_latency
                    if target_node in self.network_nodes:
                        self.network_nodes[target_node].network_distance[source_node] = avg_latency
            
            logger.info(f"网络拓扑加载完成，{len(self.network_nodes)} 个节点，{len(self.latency_history)} 条延迟记录")
            
        except Exception as e:
            logger.error(f"加载网络拓扑失败: {e}")
        finally:
            conn.close()
    
    def find_optimal_path(self, source: str, target: str, message: Message) -> List[str]:
        """
        寻找最优传输路径
        
        Args:
            source: 源节点ID
            target: 目标节点ID
            message: 消息对象
            
        Returns:
            路径节点列表（包含源和目标）
        """
        # 如果源和目标相同，直接返回
        if source == target:
            return [source]
        
        # 检查直接连接
        if self._has_direct_connection(source, target):
            return [source, target]
        
        # 获取所有可能的路径
        all_paths = self._find_all_paths(source, target, max_depth=4)
        
        if not all_paths:
            logger.warning(f"未找到从 {source} 到 {target} 的路径，使用直接连接")
            return [source, target]
        
        # 评估每条路径
        scored_paths = []
        for path in all_paths:
            score, strategy = self._evaluate_path(path, message)
            scored_paths.append((score, path, strategy))
        
        # 选择最佳路径
        scored_paths.sort(key=lambda x: x[0], reverse=True)
        best_score, best_path, best_strategy = scored_paths[0]
        
        # 记录路由决策
        decision = RoutingDecision(
            message_id=message.message_id,
            source_node=source,
            target_node=target,
            path=best_path,
            estimated_latency_ms=self._estimate_path_latency(best_path),
            routing_strategy=best_strategy,
            timestamp=datetime.now()
        )
        
        self.routing_history.append(decision)
        logger.debug(f"为消息 {message.message_id} 选择路径: {best_path} (策略: {best_strategy.value}, 分数: {best_score:.3f})")
        
        return best_path
    
    def _find_all_paths(self, source: str, target: str, max_depth: int = 4) -> List[List[str]]:
        """
        查找所有可能的路径（深度优先搜索）
        
        Args:
            source: 源节点
            target: 目标节点
            max_depth: 最大搜索深度
            
        Returns:
            所有路径列表
        """
        paths = []
        visited = set()
        stack = [(source, [source])]
        
        while stack:
            node, path = stack.pop()
            
            # 限制搜索深度
            if len(path) > max_depth:
                continue
            
            if node == target:
                paths.append(path)
                continue
            
            if node in visited:
                continue
            
            visited.add(node)
            
            # 获取邻居节点
            neighbors = self._get_neighbors(node)
            for neighbor in neighbors:
                if neighbor not in visited:
                    stack.append((neighbor, path + [neighbor]))
        
        return paths
    
    def _get_neighbors(self, node_id: str) -> List[str]:
        """获取节点的邻居节点"""
        if node_id not in self.network_nodes:
            return []
        
        node = self.network_nodes[node_id]
        neighbors = []
        
        # 基于网络距离获取邻居
        for neighbor_id, distance in node.network_distance.items():
            if neighbor_id in self.network_nodes:
                neighbor = self.network_nodes[neighbor_id]
                if neighbor.status == "active" and distance < 1000:  # 延迟小于1秒
                    neighbors.append(neighbor_id)
        
        return neighbors
    
    def _evaluate_path(self, path: List[str], message: Message) -> Tuple[float, RoutingStrategy]:
        """
        评估路径的适用性
        
        Returns:
            (综合分数, 主要评估策略)
        """
        scores = {}
        
        # 1. 最短路径评估（跳数越少越好）
        hop_count = len(path) - 1
        shortest_path_score = 1.0 / (hop_count + 0.1)
        scores[RoutingStrategy.SHORTEST_PATH] = shortest_path_score
        
        # 2. 最低延迟评估
        total_latency = self._estimate_path_latency(path)
        lowest_latency_score = 1.0 / (total_latency / 100.0 + 0.1)  # 归一化
        scores[RoutingStrategy.LOWEST_LATENCY] = lowest_latency_score
        
        # 3. 负载均衡评估
        load_scores = []
        for node_id in path[1:-1]:  # 不包含源和目标
            if node_id in self.network_nodes:
                node = self.network_nodes[node_id]
                load_score = 1.0 / (node.current_load + 1.0)
                load_scores.append(load_score)
        
        load_balanced_score = sum(load_scores) / len(load_scores) if load_scores else 0.5
        scores[RoutingStrategy.LOAD_BALANCED] = load_balanced_score
        
        # 4. 可靠性优先评估
        reliability_scores = []
        for node_id in path:
            if node_id in self.network_nodes:
                node = self.network_nodes[node_id]
                reliability_scores.append(node.reliability_score)
        
        reliability_first_score = sum(reliability_scores) / len(reliability_scores)
        scores[RoutingStrategy.RELIABILITY_FIRST] = reliability_first_score
        
        # 根据消息类型调整权重
        adjusted_weights = self._adjust_strategy_weights(message)
        
        # 计算加权分数
        total_score = 0.0
        best_strategy = RoutingStrategy.SHORTEST_PATH
        best_strategy_score = 0.0
        
        for strategy, weight in adjusted_weights.items():
            if strategy in scores:
                strategy_score = scores[strategy] * weight
                total_score += strategy_score
                
                if strategy_score > best_strategy_score:
                    best_strategy_score = strategy_score
                    best_strategy = strategy
        
        return total_score, best_strategy
    
    def _adjust_strategy_weights(self, message: Message) -> Dict[RoutingStrategy, float]:
        """根据消息类型调整策略权重"""
        base_weights = self.strategy_weights.copy()
        
        # 根据消息类型调整
        if message.message_type == MessageType.TASK_ASSIGNMENT:
            # 任务分配：可靠性优先
            base_weights[RoutingStrategy.RELIABILITY_FIRST] *= 1.5
            base_weights[RoutingStrategy.LOWEST_LATENCY] *= 0.8
        elif message.message_type == MessageType.TASK_RESULT:
            # 任务结果：延迟优先
            base_weights[RoutingStrategy.LOWEST_LATENCY] *= 1.5
            base_weights[RoutingStrategy.LOAD_BALANCED] *= 0.8
        elif message.message_type == MessageType.HEARTBEAT:
            # 心跳：最短路径
            base_weights[RoutingStrategy.SHORTEST_PATH] *= 1.5
        
        # 归一化权重
        total_weight = sum(base_weights.values())
        if total_weight > 0:
            normalized = {k: v / total_weight for k, v in base_weights.items()}
            return normalized
        else:
            return base_weights
    
    def _estimate_path_latency(self, path: List[str]) -> float:
        """估算路径总延迟"""
        total_latency = 0.0
        
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            key = (source, target)
            
            if key in self.latency_history and self.latency_history[key]:
                # 使用历史延迟的75分位数（避免极端值）
                latencies = sorted(self.latency_history[key])
                idx = int(0.75 * len(latencies))
                total_latency += latencies[min(idx, len(latencies) - 1)]
            else:
                # 默认延迟
                total_latency += 200.0  # 默认200ms
        
        return total_latency
    
    def _has_direct_connection(self, source: str, target: str) -> bool:
        """检查是否存在直接连接"""
        # 检查延迟历史
        if (source, target) in self.latency_history:
            return True
        
        # 检查节点状态
        if source in self.network_nodes and target in self.network_nodes:
            source_node = self.network_nodes[source]
            target_node = self.network_nodes[target]
            
            # 如果两个节点都活跃，假设有直接连接
            return source_node.status == "active" and target_node.status == "active"
        
        return False
    
    def send_message(self, message: Message, async_mode: bool = True) -> Optional[RoutingDecision]:
        """
        发送消息
        
        Args:
            message: 消息对象
            async_mode: 是否异步发送
            
        Returns:
            路由决策（同步模式下返回）
        """
        # 寻找最优路径
        path = self.find_optimal_path(message.source_node, message.target_node, message)
        
        # 创建路由决策
        decision = RoutingDecision(
            message_id=message.message_id,
            source_node=message.source_node,
            target_node=message.target_node,
            path=path,
            estimated_latency_ms=self._estimate_path_latency(path),
            routing_strategy=RoutingStrategy.ADAPTIVE,
            timestamp=datetime.now()
        )
        
        if async_mode:
            # 异步发送：加入队列，立即返回
            self.message_queue.append((message, decision))
            logger.debug(f"异步发送消息 {message.message_id}，路径: {path}")
            return None
        else:
            # 同步发送：立即处理
            success = self._deliver_message(message, path)
            decision.success = success
            decision.actual_latency_ms = self._measure_delivery_latency(message, path) if success else None
            
            # 记录性能指标
            self._record_performance_metrics(decision)
            
            logger.info(f"同步发送消息 {message.message_id}，{'成功' if success else '失败'}，路径: {path}")
            return decision
    
    def send_batch(self, messages: List[Message]) -> List[RoutingDecision]:
        """
        批量发送消息
        
        Args:
            messages: 消息列表
            
        Returns:
            路由决策列表
        """
        decisions = []
        
        # 按目标节点分组
        grouped_messages = defaultdict(list)
        for msg in messages:
            grouped_messages[msg.target_node].append(msg)
        
        # 为每组消息寻找最优路径
        for target_node, msg_list in grouped_messages.items():
            if len(msg_list) == 0:
                continue
            
            # 取第一个消息的源节点作为代表
            source_node = msg_list[0].source_node
            
            # 寻找最优路径
            path = self.find_optimal_path(source_node, target_node, msg_list[0])
            
            # 创建路由决策
            decision = RoutingDecision(
                message_id=f"batch_{int(time.time())}_{hashlib.md5(str(msg_list).encode()).hexdigest()[:8]}",
                source_node=source_node,
                target_node=target_node,
                path=path,
                estimated_latency_ms=self._estimate_path_latency(path),
                routing_strategy=RoutingStrategy.ADAPTIVE,
                timestamp=datetime.now()
            )
            
            # 批量发送
            success = self._deliver_batch(msg_list, path)
            decision.success = success
            decision.actual_latency_ms = self._measure_batch_delivery_latency(msg_list, path) if success else None
            
            decisions.append(decision)
            
            # 记录性能指标
            self._record_performance_metrics(decision)
        
        logger.info(f"批量发送了 {len(messages)} 条消息，分组为 {len(grouped_messages)} 组")
        return decisions
    
    def _deliver_message(self, message: Message, path: List[str]) -> bool:
        """实际投递消息"""
        try:
            # 模拟网络延迟
            latency = self._estimate_path_latency(path)
            
            # 这里应该是实际的网络通信
            # 目前模拟成功投递
            time.sleep(latency / 1000.0)  # 转换为秒
            
            # 更新节点状态
            for node_id in path:
                if node_id in self.network_nodes:
                    self.network_nodes[node_id].last_seen = datetime.now()
            
            # 记录通信指标
            self._log_communication_metric(message, path, latency, success=True)
            
            return True
            
        except Exception as e:
            logger.error(f"投递消息 {message.message_id} 失败: {e}")
            
            # 记录失败
            self._log_communication_metric(message, path, 0, success=False)
            
            return False
    
    def _deliver_batch(self, messages: List[Message], path: List[str]) -> bool:
        """批量投递消息"""
        try:
            # 合并消息内容
            batch_content = {
                "batch_id": f"batch_{int(time.time())}",
                "message_count": len(messages),
                "messages": [asdict(msg) for msg in messages],
                "timestamp": datetime.now().isoformat()
            }
            
            # 估算总延迟（批量处理可能有优化）
            base_latency = self._estimate_path_latency(path)
            batch_latency = base_latency * 0.7  # 批量处理预计减少30%延迟
            
            # 模拟延迟
            time.sleep(batch_latency / 1000.0)
            
            # 更新节点状态
            for node_id in path:
                if node_id in self.network_nodes:
                    self.network_nodes[node_id].last_seen = datetime.now()
            
            # 记录批量通信指标
            self._log_batch_communication_metric(messages, path, batch_latency, success=True)
            
            return True
            
        except Exception as e:
            logger.error(f"批量投递失败: {e}")
            self._log_batch_communication_metric(messages, path, 0, success=False)
            return False
    
    def _log_communication_metric(self, message: Message, path: List[str], latency_ms: float, success: bool):
        """记录通信指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO communication_metrics 
                (operation_type, source_node, target_node, message_size_bytes, processing_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (
                message.message_type.value,
                message.source_node,
                message.target_node,
                message.size_bytes,
                latency_ms if success else -1  # -1表示失败
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"记录通信指标失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _log_batch_communication_metric(self, messages: List[Message], path: List[str], latency_ms: float, success: bool):
        """记录批量通信指标"""
        total_size = sum(msg.size_bytes for msg in messages)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for i, msg in enumerate(messages):
                cursor.execute("""
                    INSERT INTO communication_metrics 
                    (operation_type, source_node, target_node, message_size_bytes, processing_time_ms, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"batch_{msg.message_type.value}",
                    msg.source_node,
                    msg.target_node,
                    msg.size_bytes,
                    latency_ms / len(messages) if success else -1,
                    f"batch_size={len(messages)}, position={i+1}"
                ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"记录批量通信指标失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _measure_delivery_latency(self, message: Message, path: List[str]) -> float:
        """测量投递延迟"""
        # 模拟测量
        base_latency = self._estimate_path_latency(path)
        # 添加随机波动（±20%）
        variation = random.uniform(0.8, 1.2)
        return base_latency * variation
    
    def _measure_batch_delivery_latency(self, messages: List[Message], path: List[str]) -> float:
        """测量批量投递延迟"""
        base_latency = self._estimate_path_latency(path)
        # 批量处理有优化
        batch_efficiency = 0.7  # 30%优化
        variation = random.uniform(0.8, 1.2)
        return base_latency * batch_efficiency * variation
    
    def _record_performance_metrics(self, decision: RoutingDecision):
        """记录性能指标"""
        if decision.success and decision.actual_latency_ms:
            # 更新平均延迟
            self.total_messages_sent += 1
            self.total_bytes_sent += 1024  # 估算
            
            # 更新延迟历史
            key = (decision.source_node, decision.target_node)
            self.latency_history[key].append(decision.actual_latency_ms)
            
            # 保持最近1000条记录
            if len(self.latency_history[key]) > 1000:
                self.latency_history[key] = self.latency_history[key][-1000:]
    
    def _process_batch_buffer(self):
        """处理批处理缓冲区"""
        if not self.batch_buffer:
            return
        
        for (source, target), messages in list(self.batch_buffer.items()):
            if len(messages) >= 5 or time.time() - messages[0].created_at.timestamp() > 10.0:
                # 达到批量大小或超时，发送批量
                self.send_batch(messages)
                del self.batch_buffer[(source, target)]
        
        # 重新启动定时器
        self.batch_timer = threading.Timer(5.0, self._process_batch_buffer)
        self.batch_timer.start()
    
    def _monitor_routing_performance(self):
        """监控路由性能"""
        while self.monitoring_active:
            try:
                # 分析性能趋势
                self._analyze_performance_trends()
                
                # 自适应调整策略权重
                self._adaptive_strategy_adjustment()
                
                # 清理历史记录
                self._cleanup_old_records()
                
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"路由性能监控失败: {e}")
                time.sleep(30)
    
    def _analyze_performance_trends(self):
        """分析性能趋势"""
        if len(self.routing_history) < 10:
            return
        
        recent_decisions = self.routing_history[-100:]
        
        # 计算成功率
        successful = sum(1 for d in recent_decisions if d.success)
        total = len(recent_decisions)
        
        if total > 0:
            self.success_rate = successful / total
            
            # 计算平均延迟
            latencies = [d.actual_latency_ms for d in recent_decisions if d.success and d.actual_latency_ms]
            if latencies:
                self.avg_latency_ms = sum(latencies) / len(latencies)
        
        logger.debug(f"路由性能: 成功率={self.success_rate:.3f}, 平均延迟={self.avg_latency_ms:.1f}ms")
    
    def _adaptive_strategy_adjustment(self):
        """自适应调整策略权重"""
        # 根据成功率调整可靠性权重
        if self.success_rate < 0.9:
            # 成功率低，增加可靠性权重
            self.strategy_weights[RoutingStrategy.RELIABILITY_FIRST] *= 1.1
            logger.info(f"路由成功率较低 ({self.success_rate:.2f})，增加可靠性权重")
        
        # 根据延迟调整延迟权重
        if self.avg_latency_ms > 150:
            # 延迟高，增加延迟优化权重
            self.strategy_weights[RoutingStrategy.LOWEST_LATENCY] *= 1.1
            logger.info(f"路由延迟较高 ({self.avg_latency_ms:.1f}ms)，增加延迟优化权重")
        
        # 归一化权重
        total_weight = sum(self.strategy_weights.values())
        if total_weight > 0:
            self.strategy_weights = {k: v / total_weight for k, v in self.strategy_weights.items()}
    
    def _cleanup_old_records(self):
        """清理旧记录"""
        # 清理超过24小时的路由决策
        cutoff = datetime.now() - timedelta(hours=24)
        self.routing_history = [d for d in self.routing_history if d.timestamp > cutoff]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "total_messages_sent": self.total_messages_sent,
            "total_bytes_sent": self.total_bytes_sent,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "active_nodes": len([n for n in self.network_nodes.values() if n.status == "active"]),
            "routing_strategy_weights": {k.value: v for k, v in self.strategy_weights.items()},
            "timestamp": datetime.now().isoformat()
        }


# 全局路由器实例
_global_router = None

def get_global_router() -> SmartRouter:
    """获取全局路由器实例"""
    global _global_router
    if _global_router is None:
        _global_router = SmartRouter()
    return _global_router


def create_test_message() -> Message:
    """创建测试消息"""
    return Message(
        message_id=f"test_{int(time.time())}_{random.randint(1000, 9999)}",
        message_type=MessageType.TASK_ASSIGNMENT,
        source_node="intelligence_officer",
        target_node="content_officer",
        content={"task": "分析市场趋势", "priority": "high"},
        priority=3
    )


def main():
    """测试智能路由器"""
    router = SmartRouter()
    
    # 发送测试消息
    messages = [create_test_message() for _ in range(5)]
    
    print(f"发送 {len(messages)} 条测试消息...")
    
    # 批量发送
    decisions = router.send_batch(messages)
    
    print(f"批量发送完成，{len(decisions)} 组决策")
    
    # 获取性能报告
    report = router.get_performance_report()
    print(f"路由器性能报告:")
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")
    
    print("\n智能路由器测试完成")


if __name__ == "__main__":
    main()