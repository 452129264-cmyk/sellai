#!/usr/bin/env python3
"""
KAIROS自主运维守护系统
对标顶级自主运维标准，提供完整的服务守护、健康检查与故障自愈能力。
与无限分身架构、Memory V2记忆系统深度集成。
"""

import json
import time
import logging
import threading
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

from src.health_monitor import HealthMonitor, NodeStatus, HealthCheckType, RecoveryAction
from src.undercover_auditor import UndercoverAuditor, SecurityLevel
from src.buddy_system import BuddySystem, get_global_buddy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - KAIROS - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GuardianMode(Enum):
    """守护模式枚举"""
    STANDARD = "standard"  # 标准模式
    AGGRESSIVE = "aggressive"  # 激进模式（快速恢复）
    CONSERVATIVE = "conservative"  # 保守模式（避免误操作）
    ADAPTIVE = "adaptive"  # 自适应模式（根据系统负载调整）

class SystemComponent(Enum):
    """系统组件枚举"""
    INFINITE_AVATARS = "infinite_avatars"  # 无限分身系统
    MEMORY_V2 = "memory_v2"  # 分层记忆系统
    BUSINESS_BRAIN = "business_brain"  # 全域商业大脑
    DATA_PIPELINE = "data_pipeline"  # 数据管道
    NEGOTIATION_ENGINE = "negotiation_engine"  # AI谈判引擎
    TRAFFIC_BURST = "traffic_burst"  # 流量爆破军团
    INFLUENCER_NETWORK = "influencer_network"  # 达人洽谈军团
    VIDEO_MARKETING = "video_marketing"  # 短视频引流军团
    SHOPIFY_INTEGRATION = "shopify_integration"  # Shopify集成

class KAIROSGuardian:
    """KAIROS自主运维守护系统"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化KAIROS守护系统
        
        Args:
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.mode = GuardianMode.ADAPTIVE
        self.health_monitor = HealthMonitor(db_path)
        self.security_auditor = UndercoverAuditor(db_path)
        self.buddy_system = get_global_buddy()
        self.auto_recovery_enabled = True
        self.performance_thresholds = self._load_performance_thresholds()
        self.component_dependencies = self._load_component_dependencies()
        
        # 监控状态
        self.monitoring_active = False
        self.monitor_thread = None
        
        # 初始化系统组件注册
        self._register_system_components()
        
        logger.info("KAIROS守护系统初始化完成")
    
    def _load_performance_thresholds(self) -> Dict[str, Dict[str, float]]:
        """加载性能阈值配置"""
        return {
            "infinite_avatars": {
                "task_success_rate": 0.85,
                "response_time_ms": 5000,
                "memory_usage_mb": 512,
                "concurrent_tasks": 50
            },
            "memory_v2": {
                "write_success_rate": 0.99,
                "query_response_time_ms": 1000,
                "data_consistency_rate": 0.999,
                "index_build_time_ms": 5000
            },
            "business_brain": {
                "analysis_success_rate": 0.9,
                "market_data_freshness_hours": 24,
                "prediction_accuracy": 0.7
            },
            "data_pipeline": {
                "crawl_success_rate": 0.7,
                "data_processing_time_ms": 30000,
                "api_availability": 0.8
            },
            "negotiation_engine": {
                "proposal_success_rate": 0.9,
                "counter_offer_quality": 0.8,
                "negotiation_duration_seconds": 300
            }
        }
    
    def _load_component_dependencies(self) -> Dict[str, List[str]]:
        """加载组件依赖关系"""
        return {
            "business_brain": ["memory_v2", "data_pipeline"],
            "negotiation_engine": ["memory_v2", "business_brain"],
            "traffic_burst": ["data_pipeline", "memory_v2"],
            "influencer_network": ["memory_v2", "data_pipeline"],
            "video_marketing": ["memory_v2"]
        }
    
    def _register_system_components(self):
        """注册系统组件"""
        # 注册四中枢
        self.health_monitor.register_node("情报官", "central")
        self.health_monitor.register_node("内容官", "central")
        self.health_monitor.register_node("运营官", "central")
        self.health_monitor.register_node("增长官", "central")
        
        # 注册关键组件
        components = [
            ("无限分身系统", "infinite_avatars"),
            ("Memory V2记忆系统", "memory_v2"),
            ("全域商业大脑", "business_brain"),
            ("数据管道", "data_pipeline"),
            ("AI谈判引擎", "negotiation_engine"),
            ("流量爆破军团", "traffic_burst"),
            ("达人洽谈军团", "influencer_network"),
            ("短视频引流军团", "video_marketing")
        ]
        
        for name, component_type in components:
            self.health_monitor.register_node(name, component_type)
        
        logger.info(f"已注册{len(components) + 4}个系统组件")
    
    def set_mode(self, mode: GuardianMode):
        """
        设置守护模式
        
        Args:
            mode: 守护模式
        """
        self.mode = mode
        
        # 根据模式调整参数
        if mode == GuardianMode.AGGRESSIVE:
            self.health_monitor.health_thresholds["consecutive_failures"] = 2
            self.health_monitor.health_thresholds["task_success_rate"] = 0.9
        elif mode == GuardianMode.CONSERVATIVE:
            self.health_monitor.health_thresholds["consecutive_failures"] = 5
            self.health_monitor.health_thresholds["task_success_rate"] = 0.7
        
        logger.info(f"守护模式已设置为: {mode.value}")
    
    def start_guardian_service(self):
        """启动守护服务"""
        if self.monitoring_active:
            logger.warning("守护服务已在运行中")
            return
        
        self.monitoring_active = True
        
        # 启动健康监控
        self.health_monitor.start_monitoring()
        
        # 启动安全审计
        self.security_auditor.start_audit_service()
        
        # 启动Buddy交互系统
        self.buddy_system.start_interaction_service()
        
        # 启动守护循环
        self.monitor_thread = threading.Thread(target=self._guardian_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("KAIROS守护服务已启动")
    
    def stop_guardian_service(self):
        """停止守护服务"""
        self.monitoring_active = False
        
        # 停止健康监控
        self.health_monitor.stop_monitoring()
        
        # 停止安全审计
        self.security_auditor.stop_audit_service()
        
        # 停止Buddy交互系统
        self.buddy_system.stop_interaction_service()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("KAIROS守护服务已停止")
    
    def _guardian_loop(self):
        """守护循环"""
        logger.info("守护循环开始")
        
        check_intervals = {
            "quick": 30,  # 快速检查间隔（秒）
            "standard": 60,  # 标准检查间隔
            "deep": 300  # 深度检查间隔
        }
        
        last_quick_check = datetime.now()
        last_standard_check = datetime.now()
        last_deep_check = datetime.now()
        
        while self.monitoring_active:
            current_time = datetime.now()
            
            # 快速检查（每30秒）
            if (current_time - last_quick_check).total_seconds() >= check_intervals["quick"]:
                self._perform_quick_checks()
                last_quick_check = current_time
            
            # 标准检查（每60秒）
            if (current_time - last_standard_check).total_seconds() >= check_intervals["standard"]:
                self._perform_standard_checks()
                last_standard_check = current_time
            
            # 深度检查（每5分钟）
            if (current_time - last_deep_check).total_seconds() >= check_intervals["deep"]:
                self._perform_deep_checks()
                last_deep_check = current_time
            
            # 生成系统状态报告
            if (current_time - last_standard_check).total_seconds() >= 300:
                self._generate_system_status_report()
            
            time.sleep(5)  # 循环间隔
    
    def _perform_quick_checks(self):
        """执行快速检查"""
        # 检查关键组件心跳
        critical_components = ["情报官", "内容官", "运营官", "增长官", "Memory V2记忆系统"]
        
        for component in critical_components:
            # 更新心跳
            self.health_monitor.update_heartbeat(component)
            
            # 检查数据库连接
            self.health_monitor.perform_health_check(
                component,
                HealthCheckType.DATABASE_CONNECTION,
                {"description": f"快速数据库检查 - {component}"}
            )
    
    def _perform_standard_checks(self):
        """执行标准检查"""
        # 检查所有注册节点的任务成功率
        nodes = self.health_monitor._get_all_nodes()
        
        for node_id, node_type in nodes:
            # 任务成功率检查
            self.health_monitor.perform_health_check(
                node_id,
                HealthCheckType.TASK_SUCCESS_RATE,
                {
                    "description": f"标准任务成功率检查 - {node_id}",
                    "hours": 24
                }
            )
            
            # 根据节点类型执行特定检查
            if node_type == "data_pipeline":
                self._check_data_pipeline(node_id)
            elif node_type == "memory_v2":
                self._check_memory_v2(node_id)
    
    def _perform_deep_checks(self):
        """执行深度检查"""
        # 网络连通性检查
        critical_nodes = ["情报官", "内容官", "运营官", "增长官"]
        
        for node in critical_nodes:
            self.health_monitor.perform_health_check(
                node,
                HealthCheckType.NETWORK_CONNECTIVITY,
                {
                    "test_urls": [
                        "https://www.google.com",
                        "https://www.baidu.com",
                        "https://api.coze.com"
                    ],
                    "timeout": 10
                }
            )
        
        # 组件依赖关系检查
        self._check_component_dependencies()
        
        # 性能指标检查
        self._check_performance_metrics()
    
    def _check_data_pipeline(self, node_id: str):
        """检查数据管道"""
        try:
            # 检查最近的数据采集成功率
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查crawl_history表（假设存在）
                cursor.execute('''
                    SELECT 
                        source_type,
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success
                    FROM crawl_history 
                    WHERE crawl_time >= datetime('now', '-1 hour')
                    GROUP BY source_type
                ''')
                
                results = cursor.fetchall()
                
                if results:
                    for source_type, total, success in results:
                        success_rate = success / total if total > 0 else 0
                        
                        # 如果成功率低于阈值，记录警告
                        threshold = self.performance_thresholds.get("data_pipeline", {}).get("crawl_success_rate", 0.7)
                        if success_rate < threshold:
                            logger.warning(f"数据源{source_type}采集成功率低: {success_rate:.1%}")
                
        except Exception as e:
            logger.debug(f"检查数据管道时表不存在或出错: {e}")
    
    def _check_memory_v2(self, node_id: str):
        """检查Memory V2记忆系统"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查记忆验证状态
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_memories,
                        SUM(CASE WHEN verification_status = 'verified' THEN 1 ELSE 0 END) as verified_memories
                    FROM memory_validation_status
                    WHERE updated_at >= datetime('now', '-1 hour')
                ''')
                
                result = cursor.fetchone()
                if result and result[0] > 0:
                    total, verified = result
                    verification_rate = verified / total
                    
                    # 如果验证率低于阈值，记录警告
                    threshold = self.performance_thresholds.get("memory_v2", {}).get("write_success_rate", 0.99)
                    if verification_rate < threshold:
                        logger.warning(f"Memory V2记忆验证率低: {verification_rate:.1%}")
                
        except Exception as e:
            logger.debug(f"检查Memory V2时出错: {e}")
    
    def _check_component_dependencies(self):
        """检查组件依赖关系"""
        logger.info("检查组件依赖关系...")
        
        for component, dependencies in self.component_dependencies.items():
            component_node = None
            
            # 查找对应的节点
            nodes = self.health_monitor._get_all_nodes()
            for node_id, node_type in nodes:
                if node_type == component:
                    component_node = node_id
                    break
            
            if not component_node:
                continue
            
            # 检查组件状态
            component_status = self._get_node_status(component_node)
            
            if component_status == NodeStatus.HEALTHY.value:
                # 健康组件，检查其依赖
                for dep in dependencies:
                    dep_node = None
                    
                    for node_id, node_type in nodes:
                        if node_type == dep:
                            dep_node = node_id
                            break
                    
                    if dep_node:
                        dep_status = self._get_node_status(dep_node)
                        
                        if dep_status in [NodeStatus.UNHEALTHY.value, NodeStatus.OFFLINE.value]:
                            logger.warning(f"组件{component_node}依赖{dep_node}状态不佳: {dep_status}")
    
    def _check_performance_metrics(self):
        """检查性能指标"""
        # 这里可以扩展为检查具体的性能指标
        # 例如：响应时间、吞吐量、错误率等
        
        # 获取系统健康度仪表板
        dashboard = self.health_monitor.get_system_health_dashboard()
        
        if dashboard and "summary" in dashboard:
            health_percentage = dashboard["summary"].get("health_percentage", 1.0)
            
            if health_percentage < 0.8:
                logger.warning(f"系统整体健康度偏低: {health_percentage:.1%}")
            
            # 记录关键指标
            logger.info(f"系统健康状态: 健康节点{dashboard['summary'].get('healthy_nodes', 0)}/"
                       f"总节点{dashboard['summary'].get('total_nodes', 0)}")
    
    def _get_node_status(self, node_id: str) -> str:
        """获取节点状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT status FROM node_health_status WHERE node_id = ?', (node_id,))
                result = cursor.fetchone()
                return result[0] if result else NodeStatus.UNKNOWN.value
        except Exception as e:
            logger.error(f"获取节点状态失败: {e}")
            return NodeStatus.UNKNOWN.value
    
    def _generate_system_status_report(self):
        """生成系统状态报告"""
        try:
            # 获取健康监控仪表板
            dashboard = self.health_monitor.get_system_health_dashboard()
            
            if not dashboard or "error" in dashboard:
                return
            
            # 创建状态报告
            report = {
                "timestamp": datetime.now().isoformat(),
                "guardian_mode": self.mode.value,
                "auto_recovery_enabled": self.auto_recovery_enabled,
                "system_summary": dashboard["summary"],
                "critical_alerts": self._get_critical_alerts(),
                "recommendations": self._generate_recommendations(dashboard)
            }
            
            # 保存报告到文件
            report_file = f"temp/kairos_status_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"系统状态报告已生成: {report_file}")
            
            # 如果存在严重问题，发送警报
            if report["critical_alerts"]:
                self._send_critical_alert(report)
                
        except Exception as e:
            logger.error(f"生成系统状态报告失败: {e}")
    
    def _get_critical_alerts(self) -> List[Dict[str, Any]]:
        """获取严重警报"""
        alerts = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查找状态为unhealthy或offline的节点
                cursor.execute('''
                    SELECT node_id, node_type, status, last_error, updated_at
                    FROM node_health_status
                    WHERE status IN (?, ?)
                    AND updated_at >= datetime('now', '-1 hour')
                ''', (NodeStatus.UNHEALTHY.value, NodeStatus.OFFLINE.value))
                
                unhealthy_nodes = cursor.fetchall()
                
                for node in unhealthy_nodes:
                    alerts.append({
                        "type": "node_unhealthy",
                        "node_id": node[0],
                        "node_type": node[1],
                        "status": node[2],
                        "last_error": node[3],
                        "last_update": node[4],
                        "severity": "critical"
                    })
                
                # 查找连续失败次数高的节点
                cursor.execute('''
                    SELECT node_id, node_type, consecutive_failures, last_error
                    FROM node_health_status
                    WHERE consecutive_failures >= ?
                ''', (self.health_monitor.health_thresholds["consecutive_failures"],))
                
                high_failure_nodes = cursor.fetchall()
                
                for node in high_failure_nodes:
                    alerts.append({
                        "type": "high_failure_rate",
                        "node_id": node[0],
                        "node_type": node[1],
                        "consecutive_failures": node[2],
                        "last_error": node[3],
                        "severity": "high"
                    })
        
        except Exception as e:
            logger.error(f"获取严重警报失败: {e}")
        
        return alerts
    
    def _generate_recommendations(self, dashboard: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于系统健康度生成建议
        health_percentage = dashboard["summary"].get("health_percentage", 1.0)
        
        if health_percentage < 0.7:
            recommendations.append("系统健康度严重偏低，建议立即检查关键组件状态")
        elif health_percentage < 0.8:
            recommendations.append("系统健康度偏低，建议优化资源分配或重启不健康节点")
        
        # 基于节点状态生成建议
        unhealthy_count = dashboard["summary"].get("unhealthy_nodes", 0)
        if unhealthy_count > 0:
            recommendations.append(f"发现{unhealthy_count}个不健康节点，建议执行深度诊断")
        
        # 基于守护模式生成建议
        if self.mode == GuardianMode.AGGRESSIVE and health_percentage < 0.9:
            recommendations.append("激进模式下系统健康度仍偏低，建议检查根本原因")
        elif self.mode == GuardianMode.CONSERVATIVE and health_percentage > 0.95:
            recommendations.append("保守模式下系统健康度良好，可考虑切换到标准模式")
        
        return recommendations
    
    def _send_critical_alert(self, report: Dict[str, Any]):
        """发送严重警报"""
        alert_count = len(report["critical_alerts"])
        
        if alert_count > 0:
            logger.critical(f"⚠️ 检测到{alert_count}个严重警报！")
            
            # 这里可以集成到现有的通知系统
            # 例如：发送邮件、微信消息、短信等
            
            # 记录到数据库
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    for alert in report["critical_alerts"]:
                        cursor.execute('''
                            INSERT INTO critical_alerts 
                            (alert_type, node_id, severity, alert_data, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            alert["type"],
                            alert["node_id"],
                            alert["severity"],
                            json.dumps(alert),
                            datetime.now()
                        ))
                    
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"记录严重警报失败: {e}")
    
    def manual_diagnostic(self, node_id: str) -> Dict[str, Any]:
        """
        手动执行节点诊断
        
        Args:
            node_id: 节点ID
            
        Returns:
            诊断报告
        """
        logger.info(f"执行手动诊断: {node_id}")
        
        diagnostic_report = {
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "checks_performed": [],
            "overall_status": "unknown",
            "recommendations": []
        }
        
        # 执行全面的健康检查
        check_types = [
            HealthCheckType.DATABASE_CONNECTION,
            HealthCheckType.NETWORK_CONNECTIVITY,
            HealthCheckType.TASK_SUCCESS_RATE
        ]
        
        all_passed = True
        failed_checks = []
        
        for check_type in check_types:
            result = self.health_monitor.perform_health_check(
                node_id,
                check_type,
                {"description": f"手动诊断 - {check_type.value}"}
            )
            
            diagnostic_report["checks_performed"].append({
                "type": check_type.value,
                "status": result["status"],
                "success": result["success"],
                "error_message": result.get("error_message", "")
            })
            
            if not result["success"]:
                all_passed = False
                failed_checks.append(check_type.value)
        
        # 更新总体状态
        if all_passed:
            diagnostic_report["overall_status"] = "healthy"
        elif len(failed_checks) == len(check_types):
            diagnostic_report["overall_status"] = "critical"
        else:
            diagnostic_report["overall_status"] = "degraded"
        
        # 生成建议
        if not all_passed:
            diagnostic_report["recommendations"].append(
                f"节点存在以下问题: {', '.join(failed_checks)}，建议执行相应恢复动作"
            )
        
        if diagnostic_report["overall_status"] == "critical":
            diagnostic_report["recommendations"].append(
                "节点处于严重故障状态，建议立即重启或联系系统管理员"
            )
        
        return diagnostic_report
    
    def force_recovery(self, node_id: str, recovery_plan: List[str] = None) -> Dict[str, Any]:
        """
        强制执行恢复计划
        
        Args:
            node_id: 节点ID
            recovery_plan: 恢复计划列表（动作序列）
            
        Returns:
            恢复结果
        """
        logger.info(f"强制恢复节点: {node_id}")
        
        recovery_report = {
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "actions_performed": [],
            "overall_result": "failed",
            "final_status": "unknown"
        }
        
        # 如果没有提供恢复计划，使用默认序列
        if not recovery_plan:
            recovery_plan = [
                "cleanup_resources",
                "restart_node",
                "notify_admin"
            ]
        
        # 获取当前节点状态作为检查结果
        check_result = {
            "status": self._get_node_status(node_id),
            "success": False,
            "error_message": f"手动触发强制恢复 - {node_id}"
        }
        
        # 执行恢复动作
        for action_name in recovery_plan:
            action = None
            
            # 映射动作名称
            if action_name == "restart_node":
                action = RecoveryAction.RESTART_NODE
            elif action_name == "rerun_task":
                action = RecoveryAction.RERUN_TASK
            elif action_name == "switch_data_source":
                action = RecoveryAction.SWITCH_DATA_SOURCE
            elif action_name == "cleanup_resources":
                action = RecoveryAction.CLEANUP_RESOURCES
            elif action_name == "notify_admin":
                action = RecoveryAction.NOTIFY_ADMIN
            elif action_name == "escalate":
                action = RecoveryAction.ESCALATE
            
            if action:
                start_time = datetime.now()
                
                success = self.health_monitor._execute_recovery_action(
                    node_id, action, check_result
                )
                
                action_time = (datetime.now() - start_time).total_seconds()
                
                recovery_report["actions_performed"].append({
                    "action": action.value,
                    "success": success,
                    "execution_time_seconds": action_time
                })
                
                # 如果动作成功，更新恢复结果
                if success:
                    recovery_report["overall_result"] = "partially_succeeded"
                    
                    # 验证恢复效果
                    time.sleep(2)  # 给系统一点时间
                    new_status = self._get_node_status(node_id)
                    
                    if new_status == NodeStatus.HEALTHY.value:
                        recovery_report["overall_result"] = "succeeded"
                        recovery_report["final_status"] = "healthy"
                        break
        
        logger.info(f"强制恢复完成: {node_id} - {recovery_report['overall_result']}")
        return recovery_report
    
    def get_guardian_status(self) -> Dict[str, Any]:
        """
        获取守护系统状态
        
        Returns:
            守护系统状态报告
        """
        dashboard = self.health_monitor.get_system_health_dashboard()
        
        # 获取安全审计状态
        security_report = self.security_auditor.get_security_report(1) if hasattr(self, 'security_auditor') else {}
        
        # 获取Buddy系统状态
        buddy_summary = self.buddy_system.get_interaction_summary() if hasattr(self, 'buddy_system') else {}
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "guardian_mode": self.mode.value,
            "monitoring_active": self.monitoring_active,
            "auto_recovery_enabled": self.auto_recovery_enabled,
            "registered_nodes": len(self.health_monitor._get_all_nodes()),
            "performance_thresholds": self.performance_thresholds,
            "system_health": dashboard.get("summary", {}) if dashboard else {},
            "security_audit_status": {
                "audit_service_active": self.security_auditor.audit_active if hasattr(self, 'security_auditor') else False,
                "recent_security_events": security_report.get("summary", {}).get("total_events", 0) if security_report else 0,
                "active_alerts": security_report.get("alert_statistics", {}) if security_report else {}
            },
            "buddy_system_status": {
                "interaction_enabled": self.buddy_system.interaction_enabled if hasattr(self, 'buddy_system') else False,
                "total_interactions": buddy_summary.get("total_interactions", 0),
                "active_interactions": buddy_summary.get("active_interactions", 0),
                "user_mood": buddy_summary.get("user_state", {}).get("current_mood", "unknown")
            }
        }
        
        return status


# 全局守护系统实例
_global_guardian = None

def get_global_guardian() -> KAIROSGuardian:
    """获取全局守护系统实例"""
    global _global_guardian
    if _global_guardian is None:
        _global_guardian = KAIROSGuardian()
    return _global_guardian

def start_global_guardian():
    """启动全局守护系统"""
    guardian = get_global_guardian()
    guardian.start_guardian_service()
    return guardian

def stop_global_guardian():
    """停止全局守护系统"""
    guardian = get_global_guardian()
    guardian.stop_guardian_service()

def check_system_health_with_guardian() -> Dict[str, Any]:
    """使用守护系统检查系统健康度"""
    guardian = get_global_guardian()
    return guardian.get_guardian_status()

if __name__ == "__main__":
    # 测试KAIROS守护系统
    print("启动KAIROS守护系统测试...")
    
    guardian = KAIROSGuardian()
    
    # 设置模式
    guardian.set_mode(GuardianMode.STANDARD)
    
    # 启动服务
    guardian.start_guardian_service()
    
    # 等待监控运行一会儿
    print("监控运行中，等待10秒...")
    time.sleep(10)
    
    # 获取状态
    status = guardian.get_guardian_status()
    print(f"守护系统状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
    
    # 执行手动诊断
    diagnostic = guardian.manual_diagnostic("情报官")
    print(f"节点诊断报告: {json.dumps(diagnostic, indent=2, ensure_ascii=False)}")
    
    # 停止服务
    guardian.stop_guardian_service()
    
    print("\nKAIROS守护系统测试完成")