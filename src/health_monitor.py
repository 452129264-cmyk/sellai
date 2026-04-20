#!/usr/bin/env python3
"""
健康监控与自动恢复系统
对标KAIROS自主运维标准，提供实时监控分身节点状态、故障自愈能力。
"""

import sqlite3
import time
import json
import os
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - HEALTH - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """节点状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"

class HealthCheckType(Enum):
    """健康检查类型枚举"""
    DATABASE_CONNECTION = "database_connection"
    NETWORK_CONNECTIVITY = "network_connectivity"
    API_AVAILABILITY = "api_availability"
    TASK_PERFORMANCE = "task_performance"
    RESOURCE_USAGE = "resource_usage"
    SYSTEM_STABILITY = "system_stability"

class RecoveryAction(Enum):
    """恢复动作枚举"""
    RESTART_NODE = "restart_node"
    RERUN_TASK = "rerun_task"
    SWITCH_DATA_SOURCE = "switch_data_source"
    CLEANUP_RESOURCES = "cleanup_resources"
    NOTIFY_ADMIN = "notify_admin"
    ESCALATE = "escalate"

class HealthMonitor:
    """健康监控器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化健康监控器
        
        Args:
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.monitoring_interval = 30  # 监控间隔（秒），满足任务要求≤30秒
        self.running = False
        self.monitor_thread = None
        
        # 健康阈值配置
        self.health_thresholds = {
            "consecutive_failures": 3,  # 连续失败次数阈值
            "response_time_ms": 5000,   # 响应时间阈值（毫秒）
            "heartbeat_timeout_s": 90,   # 心跳超时阈值（秒），3个监控周期
            "resource_cpu_percent": 80,  # CPU使用率阈值
            "resource_memory_percent": 85,  # 内存使用率阈值
            "task_success_rate": 0.8,    # 任务成功率阈值
            "api_success_rate": 0.8      # API成功率阈值
        }
        
        # 初始化数据库
        self._init_database()
        
        logger.info(f"健康监控器初始化完成，数据库路径: {db_path}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建节点健康状态表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS node_health_status (
                        node_id TEXT PRIMARY KEY,
                        node_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        last_heartbeat TIMESTAMP,
                        task_success_rate REAL DEFAULT 1.0,
                        response_time_avg_ms REAL,
                        error_count INTEGER DEFAULT 0,
                        consecutive_failures INTEGER DEFAULT 0,
                        last_error TEXT,
                        last_check_time TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建健康检查历史表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS health_check_history (
                        check_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        node_id TEXT NOT NULL,
                        check_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        result_data TEXT,
                        response_time_ms REAL,
                        error_message TEXT,
                        performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建恢复动作历史表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS recovery_action_history (
                        action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        node_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        trigger_reason TEXT,
                        action_data TEXT,
                        status TEXT DEFAULT 'pending',
                        result_message TEXT,
                        performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                ''')
                
                # 创建健康检查记录表（存储详细的健康指标）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS health_check_records (
                        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        node_id TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        online_status INTEGER DEFAULT 1,
                        response_time_ms REAL DEFAULT 0,
                        cpu_usage_percent REAL DEFAULT 0,
                        memory_usage_mb REAL DEFAULT 0,
                        task_success_rate REAL DEFAULT 1.0,
                        api_success_rate REAL DEFAULT 1.0,
                        overall_status TEXT DEFAULT 'unknown'
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_node_status ON node_health_status(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_check_history ON health_check_history(node_id, performed_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_recovery_history ON recovery_action_history(node_id, performed_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_health_records ON health_check_records(node_id, timestamp)')
                
                conn.commit()
                logger.debug("数据库表结构初始化完成")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def register_node(self, node_id: str, node_type: str) -> bool:
        """
        注册监控节点
        
        Args:
            node_id: 节点ID
            node_type: 节点类型
            
        Returns:
            是否注册成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO node_health_status 
                    (node_id, node_type, status, last_check_time, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    node_id,
                    node_type,
                    NodeStatus.UNKNOWN.value,
                    datetime.now(),
                    datetime.now()
                ))
                
                conn.commit()
                logger.info(f"节点注册成功: {node_id} ({node_type})")
                return True
                
        except Exception as e:
            logger.error(f"节点注册失败: {e}")
            return False
    
    def update_heartbeat(self, node_id: str) -> bool:
        """
        更新节点心跳
        
        Args:
            node_id: 节点ID
            
        Returns:
            是否更新成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE node_health_status 
                    SET last_heartbeat = ?, updated_at = ?
                    WHERE node_id = ?
                ''', (datetime.now(), datetime.now(), node_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"更新心跳失败: {e}")
            return False
    
    def perform_health_check(self, node_id: str, check_type: HealthCheckType, 
                           check_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行健康检查
        
        Args:
            node_id: 节点ID
            check_type: 检查类型
            check_params: 检查参数
            
        Returns:
            检查结果
        """
        start_time = time.time()
        
        try:
            # 根据检查类型执行相应的检查
            if check_type == HealthCheckType.DATABASE_CONNECTION:
                result = self._check_database_connection(node_id, check_params)
            elif check_type == HealthCheckType.NETWORK_CONNECTIVITY:
                result = self._check_network_connectivity(node_id, check_params)
            elif check_type == HealthCheckType.API_AVAILABILITY:
                result = self._check_api_availability(node_id, check_params)
            else:
                result = {
                    "status": NodeStatus.UNKNOWN.value,
                    "success": True,
                    "error_message": f"未实现的检查类型: {check_type.value}",
                    "result_data": {}
                }
            
            # 计算响应时间
            response_time_ms = (time.time() - start_time) * 1000
            result["response_time_ms"] = response_time_ms
            
            # 记录检查历史
            self._record_health_check(node_id, check_type, result)
            
            # 更新节点状态
            self._update_node_status(node_id, result)
            
            return result
            
        except Exception as e:
            end_time = time.time()
            error_result = {
                "status": NodeStatus.UNHEALTHY.value,
                "success": False,
                "error_message": str(e),
                "response_time_ms": (end_time - start_time) * 1000,
                "result_data": {}
            }
            
            # 记录错误检查历史
            self._record_health_check(node_id, check_type, error_result)
            
            # 更新节点状态为不健康
            self._update_node_status(node_id, error_result)
            
            return error_result
    
    def _check_database_connection(self, node_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    return {
                        "status": NodeStatus.HEALTHY.value,
                        "success": True,
                        "error_message": "",
                        "result_data": {
                            "database": "connected",
                            "query_result": result[0]
                        }
                    }
                else:
                    return {
                        "status": NodeStatus.UNHEALTHY.value,
                        "success": False,
                        "error_message": "数据库查询失败",
                        "result_data": {}
                    }
                    
        except Exception as e:
            return {
                "status": NodeStatus.UNHEALTHY.value,
                "success": False,
                "error_message": f"数据库连接失败: {e}",
                "result_data": {}
            }
    
    def _check_network_connectivity(self, node_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """检查网络连通性"""
        import requests
        
        test_urls = params.get("test_urls", ["https://www.google.com"])
        timeout = params.get("timeout", 10)
        
        test_results = {}
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=timeout)
                test_results[url] = {
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() * 1000,
                    "success": response.status_code < 400
                }
            except Exception as e:
                test_results[url] = {
                    "status_code": None,
                    "response_time": None,
                    "success": False,
                    "error": str(e)
                }
        
        # 计算成功率
        success_count = sum(1 for r in test_results.values() if r.get("success", False))
        success_rate = success_count / len(test_urls) if test_urls else 1.0
        
        if success_rate >= 0.8:
            status = NodeStatus.HEALTHY.value
        elif success_rate >= 0.5:
            status = NodeStatus.DEGRADED.value
        else:
            status = NodeStatus.UNHEALTHY.value
        
        return {
            "status": status,
            "success": success_rate >= 0.5,
            "error_message": "" if success_rate >= 0.5 else "网络连通性不足",
            "result_data": {
                "test_results": test_results,
                "success_rate": success_rate,
                "success_count": success_count,
                "total_tests": len(test_urls)
            }
        }
    
    def _record_health_check(self, node_id: str, check_type: HealthCheckType, 
                           result: Dict[str, Any]) -> bool:
        """记录健康检查历史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO health_check_history 
                    (node_id, check_type, status, result_data, response_time_ms, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    node_id,
                    check_type.value,
                    result.get("status", NodeStatus.UNKNOWN.value),
                    json.dumps(result.get("result_data", {})),
                    result.get("response_time_ms", 0),
                    result.get("error_message", "")
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"记录健康检查失败: {e}")
            return False
    
    def _update_node_status(self, node_id: str, check_result: Dict[str, Any]):
        """更新节点状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取当前状态
                cursor.execute('SELECT status, error_count, consecutive_failures FROM node_health_status WHERE node_id = ?', (node_id,))
                current_data = cursor.fetchone()
                
                if not current_data:
                    logger.warning(f"节点不存在: {node_id}")
                    return
                
                current_status = current_data[0]
                current_error_count = current_data[1]
                current_consecutive_failures = current_data[2]
                
                # 确定新状态
                check_success = check_result.get("success", False)
                
                if check_success:
                    new_error_count = max(0, current_error_count - 1)  # 成功时减少错误计数
                    new_consecutive_failures = 0
                    
                    if check_result.get("status") == NodeStatus.HEALTHY.value:
                        new_status = NodeStatus.HEALTHY.value
                    elif check_result.get("status") == NodeStatus.DEGRADED.value:
                        new_status = NodeStatus.DEGRADED.value
                    else:
                        new_status = NodeStatus.HEALTHY.value  # 成功但状态未知时设为健康
                else:
                    new_error_count = current_error_count + 1
                    new_consecutive_failures = current_consecutive_failures + 1
                    
                    if new_consecutive_failures >= self.health_thresholds["consecutive_failures"]:
                        new_status = NodeStatus.UNHEALTHY.value
                    else:
                        new_status = NodeStatus.DEGRADED.value
                
                # 更新节点状态
                cursor.execute('''
                    UPDATE node_health_status 
                    SET status = ?, error_count = ?, consecutive_failures = ?, 
                        last_error = ?, last_check_time = ?, updated_at = ?
                    WHERE node_id = ?
                ''', (
                    new_status,
                    new_error_count,
                    new_consecutive_failures,
                    check_result.get("error_message", ""),
                    datetime.now(),
                    datetime.now(),
                    node_id
                ))
                
                conn.commit()
                
                # 记录健康指标
                # 获取资源使用情况
                resource_usage = self._get_resource_usage()
                
                metrics = {
                    'online_status': 1 if new_status != NodeStatus.OFFLINE.value else 0,
                    'response_time_ms': check_result.get('response_time_ms', 0),
                    'cpu_usage_percent': resource_usage['cpu_usage_percent'],
                    'memory_usage_mb': resource_usage['memory_usage_mb'],
                    'task_success_rate': self._get_task_success_rate(node_id),
                    'api_success_rate': self._get_api_success_rate(node_id),
                    'overall_status': new_status
                }
                self._record_health_metrics(node_id, metrics)
                
                # 如果状态变化，记录日志
                if current_status != new_status:
                    logger.info(f"节点状态变化: {node_id} {current_status} -> {new_status}")
                    
                    # 如果不健康，触发恢复流程
                    if new_status == NodeStatus.UNHEALTHY.value:
                        self._trigger_recovery(node_id, check_result)
                        
        except Exception as e:
            logger.error(f"更新节点状态失败: {e}")
    
    def _record_health_metrics(self, node_id: str, metrics: Dict[str, Any]) -> bool:
        """
        记录健康指标到health_check_records表
        
        Args:
            node_id: 节点ID
            metrics: 健康指标字典，包含以下字段（可选）：
                - online_status: 在线状态（1在线，0离线）
                - response_time_ms: 响应时间（毫秒）
                - cpu_usage_percent: CPU使用率（百分比）
                - memory_usage_mb: 内存使用量（MB）
                - task_success_rate: 任务成功率（0.0-1.0）
                - api_success_rate: API成功率（0.0-1.0）
                - overall_status: 总体状态（healthy/degraded/unhealthy/offline/unknown）
        
        Returns:
            是否记录成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO health_check_records 
                    (node_id, online_status, response_time_ms, cpu_usage_percent, 
                     memory_usage_mb, task_success_rate, api_success_rate, overall_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    node_id,
                    metrics.get('online_status', 1),
                    metrics.get('response_time_ms', 0),
                    metrics.get('cpu_usage_percent', 0),
                    metrics.get('memory_usage_mb', 0),
                    metrics.get('task_success_rate', 1.0),
                    metrics.get('api_success_rate', 1.0),
                    metrics.get('overall_status', 'unknown')
                ))
                
                conn.commit()
                logger.debug(f"健康指标记录成功: {node_id}")
                return True
                
        except Exception as e:
            logger.error(f"记录健康指标失败: {e}")
            return False
    
    def _get_task_success_rate(self, node_id: str) -> float:
        """
        获取节点的任务成功率
        
        Args:
            node_id: 节点ID
            
        Returns:
            任务成功率（0.0-1.0）
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查询最近24小时的任务执行记录
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_tasks,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_tasks
                    FROM task_execution 
                    WHERE node_id = ? AND executed_at >= ?
                ''', (node_id, cutoff_time))
                
                data = cursor.fetchone()
                if data and data[0] > 0:
                    total_tasks = data[0]
                    success_tasks = data[1] if data[1] is not None else 0
                    return success_tasks / total_tasks if total_tasks > 0 else 1.0
                    
        except Exception as e:
            logger.debug(f"获取任务成功率失败: {e}")
            
        return 1.0  # 默认值
    
    def _get_api_success_rate(self, node_id: str) -> float:
        """
        获取节点的API调用成功率
        
        Args:
            node_id: 节点ID
            
        Returns:
            API成功率（0.0-1.0）
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查询最近24小时的API调用记录
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_calls,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_calls
                    FROM api_call_history 
                    WHERE node_id = ? AND called_at >= ?
                ''', (node_id, cutoff_time))
                
                data = cursor.fetchone()
                if data and data[0] > 0:
                    total_calls = data[0]
                    success_calls = data[1] if data[1] is not None else 0
                    return success_calls / total_calls if total_calls > 0 else 1.0
                    
        except Exception as e:
            logger.debug(f"获取API成功率失败: {e}")
            
        return 1.0  # 默认值
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """
        获取系统资源使用情况
        
        Returns:
            包含CPU、内存、磁盘使用率的字典
        """
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_usage_percent': cpu_percent,
                'memory_usage_mb': memory.used / (1024 * 1024),
                'memory_total_mb': memory.total / (1024 * 1024),
                'memory_percent': memory.percent,
                'disk_usage_percent': disk.percent
            }
        except ImportError:
            logger.warning("psutil模块未安装，无法获取资源使用率")
        except Exception as e:
            logger.error(f"获取资源使用率失败: {e}")
            
        return {
            'cpu_usage_percent': 0,
            'memory_usage_mb': 0,
            'memory_total_mb': 0,
            'memory_percent': 0,
            'disk_usage_percent': 0
        }
    
    def _trigger_recovery(self, node_id: str, check_result: Dict[str, Any]):
        """触发恢复流程"""
        logger.info(f"触发节点恢复: {node_id}")
        
        # 根据节点类型和错误类型选择恢复动作
        recovery_actions = self._determine_recovery_actions(node_id, check_result)
        
        # 执行恢复动作
        for action in recovery_actions:
            success = self._execute_recovery_action(node_id, action, check_result)
            if success:
                logger.info(f"恢复动作执行成功: {node_id} - {action.value}")
                break
            else:
                logger.warning(f"恢复动作执行失败: {node_id} - {action.value}")
    
    def _determine_recovery_actions(self, node_id: str, check_result: Dict[str, Any]) -> List[RecoveryAction]:
        """确定恢复动作"""
        error_msg = check_result.get("error_message", "").lower()
        
        if "database" in error_msg or "connection" in error_msg:
            # 数据库问题优先清理和重启
            actions = [
                RecoveryAction.CLEANUP_RESOURCES,
                RecoveryAction.RESTART_NODE,
                RecoveryAction.NOTIFY_ADMIN
            ]
        elif "network" in error_msg or "timeout" in error_msg:
            # 网络问题尝试切换数据源
            actions = [
                RecoveryAction.SWITCH_DATA_SOURCE,
                RecoveryAction.CLEANUP_RESOURCES,
                RecoveryAction.NOTIFY_ADMIN
            ]
        elif "api" in error_msg or "service" in error_msg:
            # API服务问题尝试重启和通知
            actions = [
                RecoveryAction.RESTART_NODE,
                RecoveryAction.SWITCH_DATA_SOURCE,
                RecoveryAction.NOTIFY_ADMIN
            ]
        else:
            # 其他问题默认尝试重启
            actions = [
                RecoveryAction.RESTART_NODE,
                RecoveryAction.NOTIFY_ADMIN
            ]
        
        return actions
    
    def _execute_recovery_action(self, node_id: str, action: RecoveryAction, 
                               check_result: Dict[str, Any]) -> bool:
        """执行恢复动作"""
        try:
            if action == RecoveryAction.RESTART_NODE:
                success = self._restart_node(node_id)
            elif action == RecoveryAction.RERUN_TASK:
                success = self._rerun_task(node_id)
            elif action == RecoveryAction.SWITCH_DATA_SOURCE:
                success = self._switch_data_source(node_id)
            elif action == RecoveryAction.CLEANUP_RESOURCES:
                success = self._cleanup_resources(node_id)
            elif action == RecoveryAction.NOTIFY_ADMIN:
                success = self._notify_admin(node_id, check_result)
            elif action == RecoveryAction.ESCALATE:
                success = self._escalate_issue(node_id, check_result)
            else:
                success = False
            
            # 记录恢复动作历史
            self._record_recovery_action(
                node_id=node_id,
                action_type=action.value,
                trigger_reason=check_result.get("error_message", "未知错误"),
                action_data=json.dumps({"result": "success" if success else "failed"}),
                status="success" if success else "failed",
                result_message=f"恢复动作执行{'成功' if success else '失败'}"
            )
            
            return success
            
        except Exception as e:
            logger.error(f"执行恢复动作失败: {e}")
            return False
    
    def _restart_node(self, node_id: str) -> bool:
        """重启节点"""
        logger.info(f"模拟重启节点: {node_id}")
        # 实际实现中，这里会调用系统API或执行重启命令
        # 模拟成功重启
        return True
    
    def _rerun_task(self, node_id: str) -> bool:
        """重新运行任务"""
        logger.info(f"模拟重新运行任务: {node_id}")
        # 实际实现中，这里会重新触发失败的任务
        return True
    
    def _switch_data_source(self, node_id: str) -> bool:
        """切换数据源"""
        logger.info(f"模拟切换数据源: {node_id}")
        # 实际实现中，这里会切换到备用数据源
        return True
    
    def _cleanup_resources(self, node_id: str) -> bool:
        """清理资源"""
        logger.info(f"模拟清理资源: {node_id}")
        # 实际实现中，这里会清理临时文件、释放内存等
        return True
    
    def _notify_admin(self, node_id: str, check_result: Dict[str, Any]) -> bool:
        """通知管理员"""
        logger.info(f"模拟通知管理员: {node_id}，错误: {check_result.get('error_message')}")
        # 实际实现中，这里会发送邮件、微信通知等
        # 使用推送通知管理器
        try:
            # 尝试导入推送通知管理器
            from src.push_notification_manager import PushNotificationManager
            manager = PushNotificationManager()
            
            notification_data = {
                'node_id': node_id,
                'status': check_result.get('status', 'unknown'),
                'error_message': check_result.get('error_message', ''),
                'timestamp': datetime.now().isoformat(),
                'severity': 'high' if check_result.get('status') == NodeStatus.UNHEALTHY.value else 'medium'
            }
            
            result = manager.send_notification('health_check_failure', notification_data)
            return result.get('success', False)
            
        except ImportError:
            logger.warning("推送通知管理器未找到，使用模拟通知")
            return True
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            return False
    
    def _escalate_issue(self, node_id: str, check_result: Dict[str, Any]) -> bool:
        """升级问题"""
        logger.info(f"模拟升级问题: {node_id}")
        # 实际实现中，这里会将问题升级到更高级别的处理流程
        return True
    
    def _record_recovery_action(self, node_id: str, action_type: str, trigger_reason: str,
                              action_data: str, status: str, result_message: str) -> bool:
        """记录恢复动作历史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO recovery_action_history 
                    (node_id, action_type, trigger_reason, action_data, status, result_message, performed_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    node_id,
                    action_type,
                    trigger_reason,
                    action_data,
                    status,
                    result_message,
                    datetime.now(),
                    datetime.now() if status in ['success', 'failed'] else None
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"记录恢复动作失败: {e}")
            return False
    
    def _detect_failure_scenarios(self, node_id: str) -> List[Dict[str, Any]]:
        """
        检测节点的故障场景
        
        Args:
            node_id: 节点ID
            
        Returns:
            故障场景列表，每个场景包含type（故障类型）、severity（严重程度）、details（详细信息）
        """
        detected_failures = []
        
        try:
            # 1. 检测节点离线（心跳超时）
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT last_heartbeat, status FROM node_health_status WHERE node_id = ?', (node_id,))
                result = cursor.fetchone()
                
                if result and result[0]:
                    last_heartbeat = datetime.fromisoformat(result[0])
                    current_status = result[1]
                    time_diff = (datetime.now() - last_heartbeat).total_seconds()
                    
                    # 如果心跳超时（超过3个监控周期）且状态不是离线，则检测到离线故障
                    if time_diff > self.monitoring_interval * 3 and current_status != NodeStatus.OFFLINE.value:
                        detected_failures.append({
                            'type': 'node_offline',
                            'severity': 'critical',
                            'details': {
                                'last_heartbeat': last_heartbeat.isoformat(),
                                'timeout_seconds': time_diff,
                                'threshold_seconds': self.monitoring_interval * 3
                            }
                        })
            
            # 2. 检测响应超时
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT response_time_avg_ms FROM node_health_status WHERE node_id = ?', (node_id,))
                result = cursor.fetchone()
                
                if result and result[0]:
                    response_time_avg = result[0]
                    threshold = self.health_thresholds.get('response_time_ms', 5000)
                    
                    if response_time_avg > threshold:
                        detected_failures.append({
                            'type': 'response_timeout',
                            'severity': 'high',
                            'details': {
                                'response_time_ms': response_time_avg,
                                'threshold_ms': threshold
                            }
                        })
            
            # 3. 检测资源耗尽（基于系统整体资源）
            resource_usage = self._get_resource_usage()
            
            # CPU使用率超过80%视为资源紧张
            if resource_usage['cpu_usage_percent'] > 80:
                detected_failures.append({
                    'type': 'resource_exhaustion_cpu',
                    'severity': 'high',
                    'details': {
                        'cpu_usage_percent': resource_usage['cpu_usage_percent'],
                        'threshold_percent': 80
                    }
                })
            
            # 内存使用率超过85%视为资源紧张
            if resource_usage['memory_percent'] > 85:
                detected_failures.append({
                    'type': 'resource_exhaustion_memory',
                    'severity': 'high',
                    'details': {
                        'memory_usage_percent': resource_usage['memory_percent'],
                        'threshold_percent': 85
                    }
                })
            
            # 4. 检测API调用失败
            api_success_rate = self._get_api_success_rate(node_id)
            if api_success_rate < 0.8:  # API成功率低于80%
                detected_failures.append({
                    'type': 'api_failure',
                    'severity': 'medium',
                    'details': {
                        'api_success_rate': api_success_rate,
                        'threshold_rate': 0.8
                    }
                })
            
            # 5. 检测数据不一致
            # 这里可以检查数据同步状态、数据一致性校验等
            # 暂时模拟检查，后续根据实际数据模型实现
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM memory_validation_status WHERE verification_status != ?', ('verified',))
                result = cursor.fetchone()
                
                if result and result[0] > 10:  # 超过10条未验证的记忆
                    detected_failures.append({
                        'type': 'data_inconsistency',
                        'severity': 'medium',
                        'details': {
                            'unverified_memories_count': result[0],
                            'threshold_count': 10
                        }
                    })
            
        except Exception as e:
            logger.error(f"检测故障场景失败: {e}")
        
        return detected_failures
    
    def _get_recovery_plan_for_failure(self, failure_type: str) -> List[str]:
        """
        根据故障类型获取恢复计划
        
        Args:
            failure_type: 故障类型
            
        Returns:
            恢复动作序列（字符串列表）
        """
        # 故障类型到恢复计划的映射
        recovery_plans = {
            'node_offline': ['restart_node', 'notify_admin'],
            'response_timeout': ['switch_data_source', 'cleanup_resources', 'restart_node'],
            'resource_exhaustion_cpu': ['cleanup_resources', 'escalate'],
            'resource_exhaustion_memory': ['cleanup_resources', 'restart_node', 'escalate'],
            'api_failure': ['switch_data_source', 'restart_node'],
            'data_inconsistency': ['rerun_task', 'switch_data_source', 'escalate']
        }
        
        return recovery_plans.get(failure_type, ['restart_node', 'notify_admin'])
    
    def _execute_recovery_plan(self, node_id: str, recovery_plan: List[str], failure: Dict[str, Any]) -> bool:
        """
        执行恢复计划
        
        Args:
            node_id: 节点ID
            recovery_plan: 恢复动作序列
            failure: 故障信息
            
        Returns:
            是否成功执行至少一个恢复动作
        """
        logger.info(f"对节点{node_id}执行恢复计划: {recovery_plan}")
        
        # 创建模拟的check_result用于触发恢复动作
        check_result = {
            'status': NodeStatus.UNHEALTHY.value,
            'success': False,
            'error_message': f"检测到故障: {failure['type']}，严重程度: {failure['severity']}",
            'response_time_ms': 0,
            'result_data': failure['details']
        }
        
        # 执行恢复动作序列
        for action_name in recovery_plan:
            # 将动作名称映射到RecoveryAction枚举
            action_map = {
                'restart_node': RecoveryAction.RESTART_NODE,
                'rerun_task': RecoveryAction.RERUN_TASK,
                'switch_data_source': RecoveryAction.SWITCH_DATA_SOURCE,
                'cleanup_resources': RecoveryAction.CLEANUP_RESOURCES,
                'notify_admin': RecoveryAction.NOTIFY_ADMIN,
                'escalate': RecoveryAction.ESCALATE
            }
            
            action = action_map.get(action_name)
            if action:
                success = self._execute_recovery_action(node_id, action, check_result)
                if success:
                    logger.info(f"恢复动作执行成功: {node_id} - {action.value}")
                    return True
                else:
                    logger.warning(f"恢复动作执行失败: {node_id} - {action.value}")
        
        logger.error(f"所有恢复动作均失败: {node_id}")
        return False
    
    def start_monitoring(self):
        """开始监控"""
        if self.running:
            logger.warning("监控已在运行中")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("健康监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("健康监控已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        logger.info("监控循环开始")
        
        while self.running:
            try:
                # 获取所有注册的节点
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT node_id, node_type FROM node_health_status')
                    nodes = cursor.fetchall()
                
                for node in nodes:
                    node_id = node[0]
                    node_type = node[1]
                    
                    # 执行基础健康检查
                    self._perform_basic_checks(node_id)
                    
                    # 检查心跳是否超时
                    self._check_heartbeat_timeout(node_id)
                    
                    # 检测故障场景
                    detected_failures = self._detect_failure_scenarios(node_id)
                    
                    # 对每个检测到的故障触发相应的恢复动作
                    for failure in detected_failures:
                        recovery_plan = self._get_recovery_plan_for_failure(failure['type'])
                        if recovery_plan:
                            logger.warning(f"节点{node_id}检测到故障: {failure['type']}，严重程度: {failure['severity']}")
                            self._execute_recovery_plan(node_id, recovery_plan, failure)
                
                # 等待下一个监控周期
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(10)  # 异常后等待10秒再重试
    
    def _perform_basic_checks(self, node_id: str):
        """执行基础健康检查"""
        # 执行数据库连接检查
        db_check = self.perform_health_check(
            node_id,
            HealthCheckType.DATABASE_CONNECTION,
            {"description": "定期数据库健康检查"}
        )
        
        # 执行网络连通性检查
        network_check = self.perform_health_check(
            node_id,
            HealthCheckType.NETWORK_CONNECTIVITY,
            {
                "test_urls": ["https://www.google.com", "https://www.baidu.com"],
                "timeout": 10
            }
        )
    
    def _check_heartbeat_timeout(self, node_id: str):
        """检查心跳是否超时"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT last_heartbeat, status FROM node_health_status WHERE node_id = ?', (node_id,))
                result = cursor.fetchone()
                
                if result and result[0]:
                    last_heartbeat = datetime.fromisoformat(result[0])
                    current_status = result[1]
                    time_diff = (datetime.now() - last_heartbeat).total_seconds()
                    
                    # 如果心跳超时且当前状态不是离线，则更新为离线
                    if time_diff > self.health_thresholds["heartbeat_timeout_s"] and current_status != NodeStatus.OFFLINE.value:
                        cursor.execute('''
                            UPDATE node_health_status 
                            SET status = ?, updated_at = ?
                            WHERE node_id = ?
                        ''', (NodeStatus.OFFLINE.value, datetime.now(), node_id))
                        conn.commit()
                        
                        logger.warning(f"节点心跳超时: {node_id} ({time_diff:.0f}秒)")
                        
        except Exception as e:
            logger.error(f"检查心跳超时失败: {e}")
    
    def _generate_monitoring_report(self):
        """生成监控报告"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 统计节点状态
                cursor.execute('''
                    SELECT 
                        status,
                        COUNT(*) as node_count
                    FROM node_health_status
                    GROUP BY status
                ''')
                
                status_stats = cursor.fetchall()
                
                # 统计最近24小时的健康检查
                cutoff_time = datetime.now() - timedelta(hours=24)
                cursor.execute('''
                    SELECT 
                        check_type,
                        COUNT(*) as total_checks,
                        SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as healthy_checks
                    FROM health_check_history
                    WHERE performed_at >= ?
                    GROUP BY check_type
                ''', (NodeStatus.HEALTHY.value, cutoff_time))
                
                check_stats = cursor.fetchall()
                
                # 统计恢复动作历史
                cursor.execute('''
                    SELECT 
                        action_type,
                        COUNT(*) as total_actions,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_actions
                    FROM recovery_action_history
                    WHERE performed_at >= ?
                    GROUP BY action_type
                ''', (cutoff_time,))
                
                recovery_stats = cursor.fetchall()
                
                report = {
                    "timestamp": datetime.now().isoformat(),
                    "node_statistics": {
                        "total_nodes": sum(s[1] for s in status_stats),
                        "by_status": {s[0]: s[1] for s in status_stats}
                    },
                    "health_check_statistics": {
                        "total_checks_24h": sum(c[1] for c in check_stats),
                        "success_rate_24h": {
                            c[0]: c[2] / c[1] if c[1] > 0 else 0
                            for c in check_stats
                        }
                    },
                    "recovery_action_statistics": {
                        "total_actions_24h": sum(r[1] for r in recovery_stats),
                        "success_rate_24h": {
                            r[0]: r[2] / r[1] if r[1] > 0 else 0
                            for r in recovery_stats
                        }
                    },
                    "system_status": "healthy" if all(s[0] != NodeStatus.UNHEALTHY.value for s in status_stats) else "degraded"
                }
                
                return report
                
        except Exception as e:
            logger.error(f"生成监控报告失败: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "system_status": "unknown"
            }
    
    def get_system_health_dashboard(self) -> Dict[str, Any]:
        """
        获取系统健康仪表板
        
        Returns:
            健康仪表板数据
        """
        try:
            report = self._generate_monitoring_report()
            
            # 构建仪表板数据
            dashboard = {
                "timestamp": datetime.now().isoformat(),
                "system_status": report.get("system_status", "unknown"),
                "node_statistics": report.get("node_statistics", {}),
                "health_check_summary": {
                    "total_checks_24h": report.get("health_check_statistics", {}).get("total_checks_24h", 0),
                    "overall_success_rate": self._calculate_overall_success_rate(report)
                },
                "recovery_actions_summary": {
                    "total_actions_24h": report.get("recovery_action_statistics", {}).get("total_actions_24h", 0),
                    "overall_success_rate": self._calculate_recovery_success_rate(report)
                },
                "alert_level": self._determine_alert_level(report),
                "recommended_actions": self._get_recommended_actions(report)
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"获取健康仪表板失败: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "system_status": "error",
                "error": str(e),
                "alert_level": "critical"
            }
    
    def _calculate_overall_success_rate(self, report: Dict[str, Any]) -> float:
        """计算总体成功率"""
        stats = report.get("health_check_statistics", {})
        success_rates = stats.get("success_rate_24h", {})
        
        if not success_rates:
            return 1.0
            
        rates = list(success_rates.values())
        return sum(rates) / len(rates) if rates else 1.0
    
    def _calculate_recovery_success_rate(self, report: Dict[str, Any]) -> float:
        """计算恢复动作成功率"""
        stats = report.get("recovery_action_statistics", {})
        success_rates = stats.get("success_rate_24h", {})
        
        if not success_rates:
            return 1.0
            
        rates = list(success_rates.values())
        return sum(rates) / len(rates) if rates else 1.0
    
    def _determine_alert_level(self, report: Dict[str, Any]) -> str:
        """确定警报级别"""
        system_status = report.get("system_status", "unknown")
        node_stats = report.get("node_statistics", {})
        
        if system_status == "healthy":
            return "normal"
        elif system_status == "degraded":
            unhealthy_count = node_stats.get(NodeStatus.UNHEALTHY.value, 0)
            if unhealthy_count > 3:
                return "high"
            else:
                return "medium"
        else:
            return "critical"
    
    def _get_recommended_actions(self, report: Dict[str, Any]) -> List[Dict[str, str]]:
        """获取推荐动作"""
        actions = []
        
        node_stats = report.get("node_statistics", {})
        
        # 检查是否有不健康的节点
        unhealthy_count = node_stats.get(NodeStatus.UNHEALTHY.value, 0)
        if unhealthy_count > 0:
            actions.append({
                "action": "检查不健康节点",
                "priority": "high",
                "description": f"发现 {unhealthy_count} 个不健康节点，建议立即检查"
            })
        
        # 检查健康检查成功率
        success_rate = self._calculate_overall_success_rate(report)
        if success_rate < 0.8:
            actions.append({
                "action": "优化健康检查配置",
                "priority": "medium",
                "description": f"健康检查成功率较低: {success_rate:.1%}，建议调整阈值"
            })
        
        # 检查节点总数
        total_nodes = node_stats.get("total_nodes", 0)
        if total_nodes == 0:
            actions.append({
                "action": "注册系统节点",
                "priority": "high",
                "description": "系统中没有注册的监控节点"
            })
        
        # 默认动作
        if not actions:
            actions.append({
                "action": "监控系统运行正常",
                "priority": "low",
                "description": "系统运行良好，继续保持"
            })
        
        return actions


def create_health_monitor() -> HealthMonitor:
    """创建健康监控器实例"""
    return HealthMonitor()

def start_global_monitoring():
    """启动全局监控"""
    monitor = create_health_monitor()
    monitor.start_monitoring()
    return monitor