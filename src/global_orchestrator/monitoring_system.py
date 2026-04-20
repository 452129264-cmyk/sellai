#!/usr/bin/env python3
"""
统一调度器全局监控与异常处理系统

实现系统状态实时监控、故障自动检测与恢复，包含：
1. 性能指标收集（CPU、内存、响应时间、队列长度）
2. 分身节点健康状态检查
3. 八大能力服务可用性监控
4. 自动异常检测与分类
5. 告警通知机制
6. 自愈机制实现
"""

import json
import time
import logging
import threading
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import uuid
import sys
import os

# 添加父目录到路径以便导入其他模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.global_orchestrator.config import CapabilityType, OrchestratorConfig
from src.global_orchestrator.core_scheduler import CoreScheduler, TaskType

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - GLOBAL-MONITOR - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitorType(Enum):
    """监控类型枚举"""
    PERFORMANCE = "performance"
    NODE_HEALTH = "node_health"
    SERVICE_AVAILABILITY = "service_availability"
    QUEUE_STATUS = "queue_status"
    DATA_FLOW = "data_flow"


class SeverityLevel(Enum):
    """严重级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态枚举"""
    PENDING = "pending"
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class RecoveryActionType(Enum):
    """恢复动作类型枚举"""
    RESTART_SERVICE = "restart_service"
    SWITCH_BACKUP = "switch_backup"
    SCALE_RESOURCES = "scale_resources"
    NOTIFY_ADMIN = "notify_admin"
    EXECUTE_SCRIPT = "execute_script"


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_percent: float
    response_time_ms: float
    queue_length: int
    active_tasks: int
    error_rate: float


@dataclass
class NodeHealthStatus:
    """节点健康状态数据类"""
    node_id: str
    node_type: str
    status: str  # healthy, degraded, unhealthy, offline
    last_heartbeat: Optional[datetime]
    task_success_rate: float
    response_time_avg_ms: float
    error_count: int
    consecutive_failures: int


@dataclass
class ServiceAvailability:
    """服务可用性数据类"""
    service_type: CapabilityType
    endpoint: str
    is_available: bool
    last_check: datetime
    response_time_ms: float
    error_message: str = ""


@dataclass
class Alert:
    """告警数据类"""
    alert_id: str
    monitor_type: MonitorType
    severity: SeverityLevel
    message: str
    details: Dict[str, Any]
    triggered_at: datetime
    status: AlertStatus = AlertStatus.PENDING
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


@dataclass
class RecoveryAction:
    """恢复动作数据类"""
    action_id: str
    action_type: RecoveryActionType
    target_id: str  # 节点ID或服务类型
    parameters: Dict[str, Any]
    executed_at: Optional[datetime] = None
    success: Optional[bool] = None
    result_message: str = ""


class BaseMonitor:
    """监控器基类"""
    
    def __init__(self, monitor_type: MonitorType, config: OrchestratorConfig):
        self.monitor_type = monitor_type
        self.config = config
        self.last_check_time = None
        self.check_interval = 30  # 默认检查间隔30秒
        self.enabled = True
    
    def collect_metrics(self) -> Dict[str, Any]:
        """收集指标（子类实现）"""
        raise NotImplementedError
    
    def check_health(self) -> Dict[str, Any]:
        """检查健康状态（子类实现）"""
        raise NotImplementedError
    
    def detect_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测异常（子类实现）"""
        raise NotImplementedError
    
    def should_trigger_alert(self, anomaly: Dict[str, Any]) -> bool:
        """判断是否触发告警"""
        # 默认实现：所有异常都触发告警
        return True
    
    def get_alert_details(self, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """获取告警详情"""
        return {
            "monitor_type": self.monitor_type.value,
            "anomaly_type": anomaly.get("type", "unknown"),
            "severity": anomaly.get("severity", "warning"),
            "details": anomaly.get("details", {})
        }


class PerformanceMonitor(BaseMonitor):
    """性能监控器"""
    
    def __init__(self, config: OrchestratorConfig):
        super().__init__(MonitorType.PERFORMANCE, config)
        self.check_interval = 10  # 性能监控更频繁
    
    def collect_metrics(self) -> Dict[str, Any]:
        """收集系统性能指标"""
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存使用
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            
            # 磁盘使用
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 获取调度器状态（如果可用）
            scheduler = self._get_scheduler_instance()
            queue_length = 0
            active_tasks = 0
            
            if scheduler:
                # 计算总队列长度
                for priority in range(5):
                    queue_length += len(scheduler.task_queues.get(priority, []))
                
                # 计算活跃任务数（状态为processing）
                active_tasks = len([t for t in scheduler.task_history 
                                   if t.status == "processing"])
            
            # 响应时间（模拟）
            response_time_ms = self._measure_response_time()
            
            # 错误率（模拟）
            error_rate = self._calculate_error_rate()
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                disk_percent=disk_percent,
                response_time_ms=response_time_ms,
                queue_length=queue_length,
                active_tasks=active_tasks,
                error_rate=error_rate
            )
            
            return asdict(metrics)
            
        except ImportError:
            logger.warning("psutil模块未安装，使用模拟性能数据")
            return self._get_simulated_metrics()
        except Exception as e:
            logger.error(f"收集性能指标失败: {e}")
            return self._get_simulated_metrics()
    
    def _get_scheduler_instance(self) -> Optional[CoreScheduler]:
        """获取调度器实例（如果可用）"""
        # 在实际实现中，这里会通过依赖注入或其他方式获取调度器实例
        # 这里返回None表示不可用
        return None
    
    def _measure_response_time(self) -> float:
        """测量响应时间（模拟）"""
        try:
            # 模拟响应时间测量
            start_time = time.time()
            time.sleep(0.001)  # 模拟操作
            return (time.time() - start_time) * 1000
        except:
            return 100.0  # 默认值
    
    def _calculate_error_rate(self) -> float:
        """计算错误率（模拟）"""
        # 模拟错误率计算
        return 0.05  # 5%错误率
    
    def _get_simulated_metrics(self) -> Dict[str, Any]:
        """获取模拟性能指标"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": 25.5,
            "memory_percent": 45.2,
            "memory_used_mb": 512.3,
            "disk_percent": 60.8,
            "response_time_ms": 120.5,
            "queue_length": 3,
            "active_tasks": 2,
            "error_rate": 0.05
        }
    
    def check_health(self) -> Dict[str, Any]:
        """检查性能健康状态"""
        metrics = self.collect_metrics()
        
        # 分析指标
        issues = []
        
        # CPU使用率过高
        if metrics.get("cpu_percent", 0) > 80:
            issues.append({
                "type": "high_cpu_usage",
                "severity": SeverityLevel.WARNING.value,
                "details": {
                    "current": metrics["cpu_percent"],
                    "threshold": 80
                }
            })
        
        # 内存使用率过高
        if metrics.get("memory_percent", 0) > 85:
            issues.append({
                "type": "high_memory_usage",
                "severity": SeverityLevel.WARNING.value,
                "details": {
                    "current": metrics["memory_percent"],
                    "threshold": 85
                }
            })
        
        # 响应时间过长
        if metrics.get("response_time_ms", 0) > 5000:
            issues.append({
                "type": "slow_response",
                "severity": SeverityLevel.WARNING.value,
                "details": {
                    "current": metrics["response_time_ms"],
                    "threshold": 5000
                }
            })
        
        # 队列过长
        if metrics.get("queue_length", 0) > 50:
            issues.append({
                "type": "long_queue",
                "severity": SeverityLevel.WARNING.value,
                "details": {
                    "current": metrics["queue_length"],
                    "threshold": 50
                }
            })
        
        # 错误率过高
        if metrics.get("error_rate", 0) > 0.2:
            issues.append({
                "type": "high_error_rate",
                "severity": SeverityLevel.ERROR.value,
                "details": {
                    "current": metrics["error_rate"],
                    "threshold": 0.2
                }
            })
        
        return {
            "status": "healthy" if not issues else "degraded",
            "issues": issues,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    def detect_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测性能异常"""
        health_result = self.check_health()
        anomalies = []
        
        for issue in health_result.get("issues", []):
            anomalies.append({
                "type": issue["type"],
                "severity": issue["severity"],
                "details": issue["details"],
                "detected_at": datetime.now().isoformat()
            })
        
        return anomalies


class NodeHealthMonitor(BaseMonitor):
    """分身节点健康监控器"""
    
    def __init__(self, config: OrchestratorConfig):
        super().__init__(MonitorType.NODE_HEALTH, config)
    
    def collect_metrics(self) -> Dict[str, Any]:
        """收集节点健康指标"""
        try:
            # 从数据库获取节点状态
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT node_id, node_type, status, last_heartbeat, 
                           task_success_rate, response_time_avg_ms, 
                           error_count, consecutive_failures
                    FROM node_health_status
                ''')
                
                nodes = cursor.fetchall()
                
                node_metrics = []
                for node in nodes:
                    node_health = NodeHealthStatus(
                        node_id=node[0],
                        node_type=node[1],
                        status=node[2],
                        last_heartbeat=datetime.fromisoformat(node[3]) if node[3] else None,
                        task_success_rate=node[4] or 1.0,
                        response_time_avg_ms=node[5] or 0.0,
                        error_count=node[6] or 0,
                        consecutive_failures=node[7] or 0
                    )
                    node_metrics.append(asdict(node_health))
                
                return {
                    "nodes": node_metrics,
                    "total_nodes": len(node_metrics),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"收集节点健康指标失败: {e}")
            return {
                "nodes": [],
                "total_nodes": 0,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def check_health(self) -> Dict[str, Any]:
        """检查节点健康状态"""
        metrics = self.collect_metrics()
        
        issues = []
        healthy_nodes = 0
        total_nodes = metrics.get("total_nodes", 0)
        
        for node in metrics.get("nodes", []):
            node_id = node.get("node_id", "unknown")
            status = node.get("status", "unknown")
            
            if status == "healthy":
                healthy_nodes += 1
            elif status == "degraded":
                issues.append({
                    "type": "node_degraded",
                    "severity": SeverityLevel.WARNING.value,
                    "details": {
                        "node_id": node_id,
                        "status": status,
                        "last_heartbeat": node.get("last_heartbeat")
                    }
                })
            elif status in ["unhealthy", "offline"]:
                issues.append({
                    "type": "node_unhealthy",
                    "severity": SeverityLevel.ERROR.value,
                    "details": {
                        "node_id": node_id,
                        "status": status,
                        "consecutive_failures": node.get("consecutive_failures", 0)
                    }
                })
        
        # 计算健康节点比例
        health_ratio = healthy_nodes / total_nodes if total_nodes > 0 else 1.0
        
        # 如果健康节点比例过低
        if health_ratio < 0.5:
            issues.append({
                "type": "system_health_degraded",
                "severity": SeverityLevel.CRITICAL.value,
                "details": {
                    "healthy_nodes": healthy_nodes,
                    "total_nodes": total_nodes,
                    "health_ratio": health_ratio
                }
            })
        
        return {
            "status": "healthy" if not issues else "degraded",
            "health_ratio": health_ratio,
            "healthy_nodes": healthy_nodes,
            "total_nodes": total_nodes,
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
    
    def detect_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测节点异常"""
        health_result = self.check_health()
        anomalies = []
        
        for issue in health_result.get("issues", []):
            anomalies.append({
                "type": issue["type"],
                "severity": issue["severity"],
                "details": issue["details"],
                "detected_at": datetime.now().isoformat()
            })
        
        return anomalies


class ServiceAvailabilityMonitor(BaseMonitor):
    """八大能力服务可用性监控器"""
    
    def __init__(self, config: OrchestratorConfig):
        super().__init__(MonitorType.SERVICE_AVAILABILITY, config)
        self.check_interval = 60  # 服务检查间隔60秒
    
    def collect_metrics(self) -> Dict[str, Any]:
        """收集服务可用性指标"""
        services = []
        
        for cap_type, cap_config in self.config.capabilities.items():
            if not cap_config.enabled:
                continue
                
            # 检查服务可用性
            is_available, response_time, error_msg = self._check_service_availability(cap_type, cap_config)
            
            service_avail = ServiceAvailability(
                service_type=cap_type,
                endpoint=cap_config.endpoint or f"{cap_type.value}_service",
                is_available=is_available,
                last_check=datetime.now(),
                response_time_ms=response_time,
                error_message=error_msg
            )
            
            services.append(asdict(service_avail))
        
        return {
            "services": services,
            "total_services": len(services),
            "available_services": sum(1 for s in services if s.get("is_available", False)),
            "timestamp": datetime.now().isoformat()
        }
    
    def _check_service_availability(self, cap_type: CapabilityType, 
                                  cap_config: Any) -> Tuple[bool, float, str]:
        """检查特定服务可用性"""
        start_time = time.time()
        
        try:
            # 根据能力类型选择不同的检查方式
            if cap_type == CapabilityType.FIRECRAWL:
                # Firecrawl服务检查
                success, response_time = self._check_firecrawl_service(cap_config)
            elif cap_type == CapabilityType.DEEPL:
                # DeepL服务检查
                success, response_time = self._check_deepl_service(cap_config)
            elif cap_type == CapabilityType.MULTILINGUAL:
                # Multilingual服务检查
                success, response_time = self._check_multilingual_service(cap_config)
            elif cap_type == CapabilityType.RISK_COMPLIANCE:
                # 风控合规服务检查
                success, response_time = self._check_risk_compliance_service(cap_config)
            elif cap_type == CapabilityType.BUSINESS_ANALYSIS:
                # 商业分析服务检查
                success, response_time = self._check_business_analysis_service(cap_config)
            elif cap_type == CapabilityType.VISUAL_GENERATION:
                # 视觉生成服务检查
                success, response_time = self._check_visual_generation_service(cap_config)
            elif cap_type == CapabilityType.VIDEO_GENERATION:
                # 视频生成服务检查
                success, response_time = self._check_video_generation_service(cap_config)
            elif cap_type == CapabilityType.SELF_EVOLUTION:
                # 自主进化服务检查
                success, response_time = self._check_self_evolution_service(cap_config)
            else:
                success = False
                response_time = 0
        
        except Exception as e:
            success = False
            response_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.warning(f"服务检查异常 {cap_type.value}: {error_msg}")
            
            # 如果是网络连接错误，记录特定错误信息
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                error_msg = f"网络连接失败: {str(e)}"
            elif "ssl" in str(e).lower():
                error_msg = f"SSL证书错误: {str(e)}"
            
            return False, response_time, error_msg
        
        response_time = (time.time() - start_time) * 1000
        return success, response_time, ""
    
    def _check_firecrawl_service(self, cap_config: Any) -> Tuple[bool, float]:
        """检查Firecrawl服务（强制VPN模式）"""
        # 强制VPN模式：忽略SSL验证，使用代理池模拟全局网络访问
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # 配置会话，忽略SSL验证
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # 强制忽略SSL证书验证
            session.verify = False
            
            # 设置代理（模拟VPN）
            proxy_config = self._get_vpn_proxy_config()
            if proxy_config:
                session.proxies.update(proxy_config)
            
            if cap_config.endpoint:
                response = session.get(cap_config.endpoint, timeout=15)
                success = response.status_code < 400
                response_time = response.elapsed.total_seconds() * 1000
                
                # 记录网络诊断信息
                if not success:
                    logger.warning(f"Firecrawl服务检查失败: {response.status_code}")
                
                return success, response_time
            else:
                # 无端点配置，假设服务不可用
                return False, 0
                
        except Exception as e:
            logger.warning(f"Firecrawl服务检查异常（强制VPN模式）: {e}")
            return False, 0
    
    def _check_deepl_service(self, cap_config: Any) -> Tuple[bool, float]:
        """检查DeepL服务"""
        # 类似实现，模拟检查
        return False, 0  # 假设由于网络限制不可用
    
    def _check_multilingual_service(self, cap_config: Any) -> Tuple[bool, float]:
        """检查Multilingual服务"""
        return False, 0
    
    def _check_risk_compliance_service(self, cap_config: Any) -> Tuple[bool, float]:
        """检查风控合规服务"""
        return False, 0
    
    def _check_business_analysis_service(self, cap_config: Any) -> Tuple[bool, float]:
        """检查商业分析服务"""
        return False, 0
    
    def _check_visual_generation_service(self, cap_config: Any) -> Tuple[bool, float]:
        """检查视觉生成服务"""
        return False, 0
    
    def _check_video_generation_service(self, cap_config: Any) -> Tuple[bool, float]:
        """检查视频生成服务"""
        return False, 0
    
    def _check_self_evolution_service(self, cap_config: Any) -> Tuple[bool, float]:
        """检查自主进化服务"""
        return False, 0
    
    def check_health(self) -> Dict[str, Any]:
        """检查服务健康状态"""
        metrics = self.collect_metrics()
        
        issues = []
        available_services = metrics.get("available_services", 0)
        total_services = metrics.get("total_services", 0)
        
        if total_services == 0:
            issues.append({
                "type": "no_services_configured",
                "severity": SeverityLevel.WARNING.value,
                "details": {
                    "message": "未配置任何服务"
                }
            })
        else:
            # 计算可用服务比例
            availability_ratio = available_services / total_services
            
            # 如果可用服务比例过低
            if availability_ratio < 0.5:
                issues.append({
                    "type": "low_service_availability",
                    "severity": SeverityLevel.CRITICAL.value,
                    "details": {
                        "available_services": available_services,
                        "total_services": total_services,
                        "availability_ratio": availability_ratio
                    }
                })
            
            # 检查单个服务状态
            for service in metrics.get("services", []):
                if not service.get("is_available", False):
                    issues.append({
                        "type": "service_unavailable",
                        "severity": SeverityLevel.ERROR.value,
                        "details": {
                            "service_type": service.get("service_type"),
                            "endpoint": service.get("endpoint"),
                            "error_message": service.get("error_message", "")
                        }
                    })
        
        return {
            "status": "healthy" if not issues else "degraded",
            "availability_ratio": available_services / total_services if total_services > 0 else 0,
            "available_services": available_services,
            "total_services": total_services,
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
    
    def detect_anomalies(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测服务异常"""
        health_result = self.check_health()
        anomalies = []
        
        for issue in health_result.get("issues", []):
            anomalies.append({
                "type": issue["type"],
                "severity": issue["severity"],
                "details": issue["details"],
                "detected_at": datetime.now().isoformat()
            })
        
        return anomalies


class AlertManager:
    """告警管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化告警数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建告警表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        alert_id TEXT PRIMARY KEY,
                        monitor_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT,
                        triggered_at TIMESTAMP NOT NULL,
                        status TEXT DEFAULT 'pending',
                        acknowledged_at TIMESTAMP,
                        resolved_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建告警历史表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alert_history (
                        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        performed_by TEXT,
                        notes TEXT,
                        performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_status ON alerts(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_severity ON alerts(severity)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_timestamp ON alerts(triggered_at)')
                
                conn.commit()
                logger.debug("告警数据库初始化完成")
                
        except Exception as e:
            logger.error(f"初始化告警数据库失败: {e}")
            raise
    
    def create_alert(self, monitor_type: MonitorType, severity: SeverityLevel,
                    message: str, details: Dict[str, Any]) -> Optional[str]:
        """创建告警"""
        try:
            # 辅助函数：递归转换不可JSON序列化的对象
            def _serialize(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, CapabilityType):
                    return obj.value
                elif isinstance(obj, Enum):
                    return obj.value
                elif isinstance(obj, dict):
                    return {k: _serialize(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [_serialize(item) for item in obj]
                else:
                    return obj
            
            # 序列化details
            serialized_details = _serialize(details)
            
            alert_id = f"alert_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            alert = Alert(
                alert_id=alert_id,
                monitor_type=monitor_type,
                severity=severity,
                message=message,
                details=serialized_details,
                triggered_at=datetime.now()
            )
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO alerts 
                    (alert_id, monitor_type, severity, message, details, triggered_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert.alert_id,
                    alert.monitor_type.value,
                    alert.severity.value,
                    alert.message,
                    json.dumps(alert.details),
                    alert.triggered_at,
                    alert.status.value
                ))
                
                conn.commit()
            
            logger.info(f"告警创建成功: {alert_id} - {message}")
            
            # 发送通知
            self._send_notification(alert)
            
            return alert_id
            
        except Exception as e:
            logger.error(f"创建告警失败: {e}")
            return None
    
    def _send_notification(self, alert: Alert):
        """发送告警通知"""
        try:
            # 尝试导入推送通知管理器
            from src.push_notification_manager import PushNotificationManager
            
            manager = PushNotificationManager()
            
            notification_data = {
                'alert_id': alert.alert_id,
                'monitor_type': alert.monitor_type.value,
                'severity': alert.severity.value,
                'message': alert.message,
                'details': alert.details,
                'timestamp': datetime.now().isoformat()
            }
            
            result = manager.send_notification('system_alert', notification_data)
            
            if result.get('success', False):
                logger.info(f"告警通知发送成功: {alert.alert_id}")
            else:
                logger.warning(f"告警通知发送失败: {alert.alert_id}")
                
        except ImportError:
            logger.warning("推送通知管理器未找到，告警仅记录到数据库")
        except Exception as e:
            logger.error(f"发送告警通知失败: {e}")
    
    def get_active_alerts(self, severity: Optional[SeverityLevel] = None) -> List[Alert]:
        """获取活跃告警"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM alerts WHERE status != 'resolved'"
                params = []
                
                if severity:
                    query += " AND severity = ?"
                    params.append(severity.value)
                
                query += " ORDER BY triggered_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                alerts = []
                for row in rows:
                    alert = Alert(
                        alert_id=row[0],
                        monitor_type=MonitorType(row[1]),
                        severity=SeverityLevel(row[2]),
                        message=row[3],
                        details=json.loads(row[4]) if row[4] else {},
                        triggered_at=datetime.fromisoformat(row[5]),
                        status=AlertStatus(row[6]),
                        acknowledged_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        resolved_at=datetime.fromisoformat(row[8]) if row[8] else None
                    )
                    alerts.append(alert)
                
                return alerts
                
        except Exception as e:
            logger.error(f"获取活跃告警失败: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """确认告警"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE alerts 
                    SET status = 'acknowledged', acknowledged_at = ?
                    WHERE alert_id = ? AND status = 'pending'
                ''', (datetime.now(), alert_id))
                
                conn.commit()
                
                # 记录历史
                cursor.execute('''
                    INSERT INTO alert_history (alert_id, action, performed_by)
                    VALUES (?, ?, ?)
                ''', (alert_id, 'acknowledged', acknowledged_by))
                
                conn.commit()
                
                logger.info(f"告警已确认: {alert_id}")
                return True
                
        except Exception as e:
            logger.error(f"确认告警失败: {e}")
            return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str = "system", 
                     notes: str = "") -> bool:
        """解决告警"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE alerts 
                    SET status = 'resolved', resolved_at = ?
                    WHERE alert_id = ?
                ''', (datetime.now(), alert_id))
                
                conn.commit()
                
                # 记录历史
                cursor.execute('''
                    INSERT INTO alert_history (alert_id, action, performed_by, notes)
                    VALUES (?, ?, ?, ?)
                ''', (alert_id, 'resolved', resolved_by, notes))
                
                conn.commit()
                
                logger.info(f"告警已解决: {alert_id}")
                return True
                
        except Exception as e:
            logger.error(f"解决告警失败: {e}")
            return False


class RecoveryExecutor:
    """恢复执行器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化恢复动作数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建恢复动作表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS recovery_actions (
                        action_id TEXT PRIMARY KEY,
                        action_type TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        parameters TEXT,
                        executed_at TIMESTAMP,
                        success INTEGER,
                        result_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"初始化恢复动作数据库失败: {e}")
            raise
    
    def execute_action(self, action_type: RecoveryActionType, target_id: str,
                      parameters: Dict[str, Any] = None) -> Tuple[bool, str]:
        """执行恢复动作"""
        action_id = f"recovery_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        try:
            # 根据动作类型执行相应恢复操作
            if action_type == RecoveryActionType.RESTART_SERVICE:
                success, result_msg = self._restart_service(target_id, parameters or {})
            elif action_type == RecoveryActionType.SWITCH_BACKUP:
                success, result_msg = self._switch_to_backup(target_id, parameters or {})
            elif action_type == RecoveryActionType.SCALE_RESOURCES:
                success, result_msg = self._scale_resources(target_id, parameters or {})
            elif action_type == RecoveryActionType.NOTIFY_ADMIN:
                success, result_msg = self._notify_admin(target_id, parameters or {})
            elif action_type == RecoveryActionType.EXECUTE_SCRIPT:
                success, result_msg = self._execute_custom_script(target_id, parameters or {})
            else:
                success = False
                result_msg = f"未知的恢复动作类型: {action_type.value}"
            
            # 记录恢复动作
            recovery_action = RecoveryAction(
                action_id=action_id,
                action_type=action_type,
                target_id=target_id,
                parameters=parameters or {},
                executed_at=datetime.now(),
                success=success,
                result_message=result_msg
            )
            
            self._record_recovery_action(recovery_action)
            
            logger.info(f"恢复动作执行完成: {action_id} - {action_type.value} - 结果: {success}")
            
            return success, result_msg
            
        except Exception as e:
            error_msg = f"执行恢复动作失败: {str(e)}"
            logger.error(error_msg)
            
            # 记录失败动作
            recovery_action = RecoveryAction(
                action_id=action_id,
                action_type=action_type,
                target_id=target_id,
                parameters=parameters or {},
                executed_at=datetime.now(),
                success=False,
                result_message=error_msg
            )
            
            self._record_recovery_action(recovery_action)
            
            return False, error_msg
    
    def _restart_service(self, target_id: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """重启服务"""
        logger.info(f"模拟重启服务: {target_id}, 参数: {parameters}")
        
        # 模拟重启操作
        time.sleep(0.5)
        
        # 模拟成功
        return True, f"服务 {target_id} 已成功重启"
    
    def _switch_to_backup(self, target_id: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """切换到备份"""
        logger.info(f"模拟切换到备份: {target_id}, 参数: {parameters}")
        
        # 模拟切换操作
        time.sleep(0.3)
        
        # 模拟成功
        return True, f"已成功切换到 {target_id} 的备份服务"
    
    def _scale_resources(self, target_id: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """扩展资源"""
        logger.info(f"模拟扩展资源: {target_id}, 参数: {parameters}")
        
        # 模拟资源扩展
        time.sleep(0.8)
        
        # 模拟成功
        return True, f"{target_id} 的资源已成功扩展"
    
    def _notify_admin(self, target_id: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """通知管理员"""
        logger.info(f"模拟通知管理员: {target_id}, 参数: {parameters}")
        
        # 模拟通知发送
        try:
            from src.push_notification_manager import PushNotificationManager
            
            manager = PushNotificationManager()
            
            notification_data = {
                'target_id': target_id,
                'parameters': parameters,
                'timestamp': datetime.now().isoformat()
            }
            
            result = manager.send_notification('recovery_action', notification_data)
            
            if result.get('success', False):
                return True, f"管理员通知已发送: {target_id}"
            else:
                return False, f"管理员通知发送失败: {target_id}"
                
        except ImportError:
            # 无推送管理器，模拟成功
            return True, f"模拟管理员通知: {target_id}"
    
    def _execute_custom_script(self, target_id: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """执行自定义脚本"""
        logger.info(f"模拟执行自定义脚本: {target_id}, 参数: {parameters}")
        
        # 模拟脚本执行
        script_path = parameters.get('script_path', '')
        if script_path and os.path.exists(script_path):
            time.sleep(1)
            return True, f"自定义脚本 {script_path} 执行成功"
        else:
            return False, f"脚本不存在或路径无效: {script_path}"
    
    def _record_recovery_action(self, action: RecoveryAction):
        """记录恢复动作到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO recovery_actions 
                    (action_id, action_type, target_id, parameters, executed_at, success, result_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    action.action_id,
                    action.action_type.value,
                    action.target_id,
                    json.dumps(action.parameters),
                    action.executed_at,
                    1 if action.success else 0,
                    action.result_message
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"记录恢复动作失败: {e}")


class GlobalMonitoringSystem:
    """全局监控系统主类"""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.running = False
        self.monitor_thread = None
        
        # 初始化监控器
        self.performance_monitor = PerformanceMonitor(config)
        self.node_health_monitor = NodeHealthMonitor(config)
        self.service_availability_monitor = ServiceAvailabilityMonitor(config)
        
        # 初始化告警管理器
        self.alert_manager = AlertManager(config.db_path)
        
        # 初始化恢复执行器
        self.recovery_executor = RecoveryExecutor(config.db_path)
        
        # 监控历史
        self.monitoring_history = []
        
        logger.info("全局监控系统初始化完成")
    
    def start_monitoring(self):
        """开始监控"""
        if self.running:
            logger.warning("监控已在运行中")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("全局监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        logger.info("全局监控已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        logger.info("监控循环开始")
        
        while self.running:
            try:
                # 收集所有监控指标
                monitoring_results = {
                    "performance": self.performance_monitor.collect_metrics(),
                    "node_health": self.node_health_monitor.collect_metrics(),
                    "service_availability": self.service_availability_monitor.collect_metrics(),
                    "timestamp": datetime.now().isoformat()
                }
                
                # 检测异常
                anomalies = []
                
                # 性能异常
                perf_anomalies = self.performance_monitor.detect_anomalies(
                    monitoring_results["performance"]
                )
                anomalies.extend(perf_anomalies)
                
                # 节点健康异常
                node_anomalies = self.node_health_monitor.detect_anomalies(
                    monitoring_results["node_health"]
                )
                anomalies.extend(node_anomalies)
                
                # 服务可用性异常
                service_anomalies = self.service_availability_monitor.detect_anomalies(
                    monitoring_results["service_availability"]
                )
                anomalies.extend(service_anomalies)
                
                # 处理异常
                for anomaly in anomalies:
                    self._handle_anomaly(anomaly)
                
                # 记录监控历史
                self.monitoring_history.append(monitoring_results)
                
                # 保持最近100条记录
                if len(self.monitoring_history) > 100:
                    self.monitoring_history = self.monitoring_history[-100:]
                
                # 等待下一个监控周期
                time.sleep(self.performance_monitor.check_interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(10)  # 异常后等待10秒再重试
    
    def _handle_anomaly(self, anomaly: Dict[str, Any]):
        """处理异常"""
        try:
            # 确定监控类型
            monitor_type_str = anomaly.get("monitor_type", "unknown")
            monitor_type = MonitorType(monitor_type_str) if monitor_type_str != "unknown" else MonitorType.PERFORMANCE
            
            # 确定严重级别
            severity_str = anomaly.get("severity", "warning")
            severity = SeverityLevel(severity_str)
            
            # 生成告警消息
            message = self._generate_alert_message(anomaly)
            
            # 创建告警
            alert_id = self.alert_manager.create_alert(
                monitor_type=monitor_type,
                severity=severity,
                message=message,
                details=anomaly.get("details", {})
            )
            
            if alert_id and severity in [SeverityLevel.ERROR, SeverityLevel.CRITICAL]:
                # 对于严重异常，触发恢复流程
                self._trigger_recovery(anomaly)
            
        except Exception as e:
            logger.error(f"处理异常失败: {e}")
    
    def _generate_alert_message(self, anomaly: Dict[str, Any]) -> str:
        """生成告警消息"""
        anomaly_type = anomaly.get("type", "unknown")
        
        messages = {
            "high_cpu_usage": "CPU使用率过高",
            "high_memory_usage": "内存使用率过高",
            "slow_response": "响应时间过长",
            "long_queue": "任务队列过长",
            "high_error_rate": "错误率过高",
            "node_degraded": "分身节点状态降级",
            "node_unhealthy": "分身节点不健康",
            "system_health_degraded": "系统健康度下降",
            "no_services_configured": "未配置任何服务",
            "low_service_availability": "服务可用性过低",
            "service_unavailable": "服务不可用"
        }
        
        return messages.get(anomaly_type, f"未知异常: {anomaly_type}")
    
    def _trigger_recovery(self, anomaly: Dict[str, Any]):
        """触发恢复流程"""
        try:
            anomaly_type = anomaly.get("type", "")
            details = anomaly.get("details", {})
            
            # 根据异常类型确定恢复动作
            if anomaly_type in ["high_cpu_usage", "high_memory_usage", "resource_exhaustion_cpu"]:
                # 资源问题，扩展资源
                target_id = details.get("node_id", "system")
                success, msg = self.recovery_executor.execute_action(
                    RecoveryActionType.SCALE_RESOURCES,
                    target_id,
                    {"resource_type": "cpu_memory", "increase_percent": 50}
                )
                
            elif anomaly_type in ["node_unhealthy", "node_offline"]:
                # 节点问题，重启服务
                target_id = details.get("node_id", "unknown_node")
                success, msg = self.recovery_executor.execute_action(
                    RecoveryActionType.RESTART_SERVICE,
                    target_id,
                    {"force": True}
                )
                
            elif anomaly_type in ["service_unavailable", "low_service_availability"]:
                # 服务问题，切换到备份
                target_id = details.get("service_type", "unknown_service")
                success, msg = self.recovery_executor.execute_action(
                    RecoveryActionType.SWITCH_BACKUP,
                    target_id,
                    {"backup_endpoint": "backup.example.com"}
                )
                
            else:
                # 其他异常，通知管理员
                success, msg = self.recovery_executor.execute_action(
                    RecoveryActionType.NOTIFY_ADMIN,
                    "system",
                    {"anomaly_type": anomaly_type, "details": details}
                )
            
            if success:
                logger.info(f"恢复流程执行成功: {msg}")
            else:
                logger.warning(f"恢复流程执行失败: {msg}")
                
        except Exception as e:
            logger.error(f"触发恢复流程失败: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态摘要"""
        try:
            # 收集当前状态
            perf_health = self.performance_monitor.check_health()
            node_health = self.node_health_monitor.check_health()
            service_health = self.service_availability_monitor.check_health()
            
            # 计算整体状态
            statuses = [
                perf_health.get("status", "unknown"),
                node_health.get("status", "unknown"),
                service_health.get("status", "unknown")
            ]
            
            if any(s == "degraded" for s in statuses):
                overall_status = "degraded"
            elif all(s == "healthy" for s in statuses):
                overall_status = "healthy"
            else:
                overall_status = "unknown"
            
            # 获取活跃告警
            active_alerts = self.alert_manager.get_active_alerts()
            
            return {
                "overall_status": overall_status,
                "performance": perf_health,
                "node_health": node_health,
                "service_availability": service_health,
                "active_alerts": len(active_alerts),
                "critical_alerts": len([a for a in active_alerts if a.severity == SeverityLevel.CRITICAL]),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                "overall_status": "unknown",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """获取详细监控指标"""
        return {
            "performance": self.performance_monitor.collect_metrics(),
            "node_health": self.node_health_monitor.collect_metrics(),
            "service_availability": self.service_availability_monitor.collect_metrics(),
            "monitoring_history_count": len(self.monitoring_history),
            "timestamp": datetime.now().isoformat()
        }
    
    def simulate_failure_scenario(self, scenario_type: str) -> bool:
        """模拟故障场景（用于测试）"""
        logger.info(f"模拟故障场景: {scenario_type}")
        
        # 创建模拟异常
        anomaly = {
            "type": scenario_type,
            "severity": SeverityLevel.ERROR.value,
            "details": {
                "simulated": True,
                "scenario": scenario_type,
                "timestamp": datetime.now().isoformat()
            },
            "detected_at": datetime.now().isoformat()
        }
        
        # 触发告警和恢复
        self._handle_anomaly(anomaly)
        
        return True


def main():
    """主函数：测试监控系统"""
    print("=== 全局监控系统测试 ===")
    
    # 加载配置
    config = OrchestratorConfig()
    
    # 创建监控系统
    monitoring_system = GlobalMonitoringSystem(config)
    
    # 启动监控
    monitoring_system.start_monitoring()
    
    print("监控系统已启动，运行30秒进行测试...")
    
    # 运行一段时间
    time.sleep(10)
    
    # 获取系统状态
    status = monitoring_system.get_system_status()
    print(f"\n系统状态: {status['overall_status']}")
    print(f"活跃告警: {status['active_alerts']}")
    print(f"严重告警: {status['critical_alerts']}")
    
    # 模拟故障场景
    print("\n模拟CPU使用率过高故障...")
    monitoring_system.simulate_failure_scenario("high_cpu_usage")
    
    time.sleep(5)
    
    # 获取详细指标
    metrics = monitoring_system.get_detailed_metrics()
    print(f"\n性能指标收集: {len(metrics['performance'])} 项")
    print(f"节点健康状态: {metrics['node_health']['total_nodes']} 个节点")
    print(f"服务可用性: {metrics['service_availability']['available_services']}/{metrics['service_availability']['total_services']} 可用")
    
    # 停止监控
    time.sleep(15)
    monitoring_system.stop_monitoring()
    
    print("\n监控系统测试完成")


if __name__ == "__main__":
    main()