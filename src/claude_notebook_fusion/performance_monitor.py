#!/usr/bin/env python3
"""
性能监控器模块

监控Claude Code × Notebook LM融合架构的性能指标，
收集统计数据，计算执行效率提升，生成性能报告。
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
import threading
from collections import deque
import statistics
from contextlib import contextmanager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型枚举"""
    TASK_EXECUTION_TIME = "task_execution_time"
    KNOWLEDGE_QUERY_TIME = "knowledge_query_time"
    CACHE_HIT_RATE = "cache_hit_rate"
    SUBTASK_SUCCESS_RATE = "subtask_success_rate"
    COMMUNICATION_LATENCY = "communication_latency"
    SYSTEM_LOAD = "system_load"


@dataclass
class PerformanceMetric:
    """性能指标数据结构"""
    metric_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metric_id": self.metric_id,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class PerformanceReport:
    """性能报告数据结构"""
    report_id: str
    period_start: datetime
    period_end: datetime
    metrics_summary: Dict[str, Any]
    efficiency_improvement: float
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "metrics_summary": self.metrics_summary,
            "efficiency_improvement": self.efficiency_improvement,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat()
        }


class PerformanceMonitor:
    """
    性能监控器
    
    收集、存储和分析性能指标，计算执行效率提升。
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db",
                 sampling_interval: float = 60.0):
        """
        初始化性能监控器
        
        Args:
            db_path: 数据库路径
            sampling_interval: 采样间隔(秒)
        """
        self.db_path = db_path
        self.sampling_interval = sampling_interval
        
        # 初始化数据库
        self._init_database()
        
        # 内存缓存（最近数据）
        self.metric_buffer: Dict[MetricType, deque] = {
            metric_type: deque(maxlen=1000) 
            for metric_type in MetricType
        }
        
        # 性能基准（优化前）
        self.baseline_metrics: Dict[str, float] = {
            "avg_task_execution_time": 5.0,  # 假设基准5秒
            "avg_knowledge_query_time": 1.5,
            "cache_hit_rate": 0.0,
            "subtask_success_rate": 0.65,
            "avg_communication_latency": 0.2
        }
        
        # 统计锁
        self._lock = threading.Lock()
        
        # 监控线程
        self._monitoring_thread = None
        self._running = False
        
        # 性能告警阈值
        self.alert_thresholds = {
            MetricType.TASK_EXECUTION_TIME: 10.0,  # 任务执行时间>10秒告警
            MetricType.KNOWLEDGE_QUERY_TIME: 2.0,  # 知识查询时间>2秒告警
            MetricType.CACHE_HIT_RATE: 0.3,  # 缓存命中率<30%告警
            MetricType.SUBTASK_SUCCESS_RATE: 0.5,  # 子任务成功率<50%告警
            MetricType.COMMUNICATION_LATENCY: 0.5  # 通信延迟>500ms告警
        }
        
        logger.info(f"性能监控器初始化完成，采样间隔: {sampling_interval}秒")
    
    def start_monitoring(self):
        """启动监控"""
        if self._running:
            logger.warning("监控已在运行中")
            return
        
        self._running = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self._monitoring_thread.start()
        
        logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self._running = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        
        logger.info("性能监控已停止")
    
    def record_task_execution(self, task_id: str, execution_time: float,
                            success: bool, subtasks_count: int,
                            knowledge_queries: int = 1):
        """
        记录任务执行指标
        
        Args:
            task_id: 任务ID
            execution_time: 执行时间(秒)
            success: 是否成功
            subtasks_count: 子任务数量
            knowledge_queries: 知识查询次数
        """
        metric_id = f"task_{task_id}_{int(time.time())}"
        
        metric = PerformanceMetric(
            metric_id=metric_id,
            metric_type=MetricType.TASK_EXECUTION_TIME,
            value=execution_time,
            timestamp=datetime.now(),
            metadata={
                "task_id": task_id,
                "success": success,
                "subtasks_count": subtasks_count,
                "knowledge_queries": knowledge_queries
            }
        )
        
        self._store_metric(metric)
        
        # 检查告警
        if execution_time > self.alert_thresholds[MetricType.TASK_EXECUTION_TIME]:
            self._trigger_alert(
                MetricType.TASK_EXECUTION_TIME,
                f"任务执行时间过长: {execution_time:.2f}秒 > "
                f"{self.alert_thresholds[MetricType.TASK_EXECUTION_TIME]}秒",
                {"task_id": task_id, "execution_time": execution_time}
            )
    
    def record_knowledge_query(self, query_id: str, query_time: float,
                              cache_hit: bool, result_count: int):
        """
        记录知识查询指标
        
        Args:
            query_id: 查询ID
            query_time: 查询时间(秒)
            cache_hit: 是否缓存命中
            result_count: 结果数量
        """
        metric_id = f"query_{query_id}_{int(time.time())}"
        
        metric = PerformanceMetric(
            metric_id=metric_id,
            metric_type=MetricType.KNOWLEDGE_QUERY_TIME,
            value=query_time,
            timestamp=datetime.now(),
            metadata={
                "query_id": query_id,
                "cache_hit": cache_hit,
                "result_count": result_count
            }
        )
        
        self._store_metric(metric)
        
        # 记录缓存命中率
        cache_metric = PerformanceMetric(
            metric_id=f"cache_{query_id}_{int(time.time())}",
            metric_type=MetricType.CACHE_HIT_RATE,
            value=1.0 if cache_hit else 0.0,
            timestamp=datetime.now(),
            metadata={"query_id": query_id}
        )
        
        self._store_metric(cache_metric)
        
        # 检查告警
        if query_time > self.alert_thresholds[MetricType.KNOWLEDGE_QUERY_TIME]:
            self._trigger_alert(
                MetricType.KNOWLEDGE_QUERY_TIME,
                f"知识查询时间过长: {query_time:.2f}秒 > "
                f"{self.alert_thresholds[MetricType.KNOWLEDGE_QUERY_TIME]}秒",
                {"query_id": query_id, "query_time": query_time}
            )
    
    def record_subtask_result(self, subtask_id: str, success: bool,
                            execution_time: float):
        """
        记录子任务执行结果
        
        Args:
            subtask_id: 子任务ID
            success: 是否成功
            execution_time: 执行时间(秒)
        """
        metric_id = f"subtask_{subtask_id}_{int(time.time())}"
        
        metric = PerformanceMetric(
            metric_id=metric_id,
            metric_type=MetricType.SUBTASK_SUCCESS_RATE,
            value=1.0 if success else 0.0,
            timestamp=datetime.now(),
            metadata={
                "subtask_id": subtask_id,
                "execution_time": execution_time
            }
        )
        
        self._store_metric(metric)
    
    def record_communication_latency(self, source: str, target: str,
                                   latency: float, message_size: int):
        """
        记录通信延迟
        
        Args:
            source: 消息源
            target: 消息目标
            latency: 延迟时间(秒)
            message_size: 消息大小(字节)
        """
        metric_id = f"comm_{source}_{target}_{int(time.time())}"
        
        metric = PerformanceMetric(
            metric_id=metric_id,
            metric_type=MetricType.COMMUNICATION_LATENCY,
            value=latency,
            timestamp=datetime.now(),
            metadata={
                "source": source,
                "target": target,
                "message_size": message_size
            }
        )
        
        self._store_metric(metric)
        
        # 检查告警
        if latency > self.alert_thresholds[MetricType.COMMUNICATION_LATENCY]:
            self._trigger_alert(
                MetricType.COMMUNICATION_LATENCY,
                f"通信延迟过高: {latency:.3f}秒 > "
                f"{self.alert_thresholds[MetricType.COMMUNICATION_LATENCY]}秒",
                {"source": source, "target": target, "latency": latency}
            )
    
    def calculate_efficiency_improvement(self, period_hours: float = 24.0
                                       ) -> Dict[str, Any]:
        """
        计算执行效率提升
        
        Args:
            period_hours: 统计周期(小时)
            
        Returns:
            效率提升分析结果
        """
        period_end = datetime.now()
        period_start = period_end - timedelta(hours=period_hours)
        
        # 查询当前周期内的指标
        metrics = self._query_metrics(period_start, period_end)
        
        if not metrics:
            return {
                "success": False,
                "message": f"在{period_hours}小时内未找到足够的指标数据",
                "improvement_rate": 0.0
            }
        
        # 计算各项指标的平均值
        avg_metrics = self._calculate_average_metrics(metrics)
        
        # 计算相对于基准的提升率
        improvement_rates = {}
        for metric_type, avg_value in avg_metrics.items():
            baseline = self.baseline_metrics.get(metric_type)
            if baseline and baseline > 0:
                improvement_rate = (baseline - avg_value) / baseline * 100
                improvement_rates[metric_type] = improvement_rate
        
        # 计算整体效率提升（加权平均）
        weights = {
            "avg_task_execution_time": 0.4,
            "avg_knowledge_query_time": 0.25,
            "cache_hit_rate": 0.15,
            "subtask_success_rate": 0.15,
            "avg_communication_latency": 0.05
        }
        
        overall_improvement = 0.0
        total_weight = 0.0
        
        for metric_type, improvement in improvement_rates.items():
            weight = weights.get(metric_type, 0.0)
            overall_improvement += improvement * weight
            total_weight += weight
        
        if total_weight > 0:
            overall_improvement /= total_weight
        
        return {
            "success": True,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            "avg_metrics": avg_metrics,
            "improvement_rates": improvement_rates,
            "overall_improvement": overall_improvement,
            "baseline_metrics": self.baseline_metrics.copy(),
            "meets_target": overall_improvement >= 20.0
        }
    
    def generate_performance_report(self, period_hours: float = 24.0
                                  ) -> PerformanceReport:
        """
        生成性能报告
        
        Args:
            period_hours: 统计周期(小时)
            
        Returns:
            性能报告
        """
        period_end = datetime.now()
        period_start = period_end - timedelta(hours=period_hours)
        
        # 计算效率提升
        efficiency_data = self.calculate_efficiency_improvement(period_hours)
        
        # 生成报告ID
        report_id = f"perf_report_{period_start.strftime('%Y%m%d%H%M')}_{period_end.strftime('%H%M')}"
        
        # 生成建议
        recommendations = self._generate_recommendations(efficiency_data)
        
        report = PerformanceReport(
            report_id=report_id,
            period_start=period_start,
            period_end=period_end,
            metrics_summary=efficiency_data.get("avg_metrics", {}),
            efficiency_improvement=efficiency_data.get("overall_improvement", 0.0),
            recommendations=recommendations
        )
        
        return report
    
    def get_recent_metrics(self, metric_type: MetricType, 
                          limit: int = 100) -> List[PerformanceMetric]:
        """
        获取最近的指标数据
        
        Args:
            metric_type: 指标类型
            limit: 限制数量
            
        Returns:
            指标列表
        """
        with self._lock:
            if metric_type in self.metric_buffer:
                buffer = self.metric_buffer[metric_type]
                return list(buffer)[-limit:]
        
        return []
    
    def get_system_load(self) -> Dict[str, Any]:
        """
        获取系统负载情况
        
        Returns:
            系统负载信息
        """
        # 这里可以集成实际系统监控
        # 简化实现
        import psutil
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            
            metric = PerformanceMetric(
                metric_id=f"system_load_{int(time.time())}",
                metric_type=MetricType.SYSTEM_LOAD,
                value=cpu_percent,
                timestamp=datetime.now(),
                metadata={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_info.percent,
                    "memory_available": memory_info.available,
                    "memory_total": memory_info.total
                }
            )
            
            self._store_metric(metric)
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_info.percent,
                "memory_available": memory_info.available,
                "memory_total": memory_info.total,
                "timestamp": datetime.now().isoformat()
            }
            
        except ImportError:
            # psutil不可用，返回模拟数据
            return {
                "cpu_percent": 25.0,
                "memory_percent": 60.0,
                "memory_available": 8192000000,
                "memory_total": 17179869184,
                "timestamp": datetime.now().isoformat(),
                "note": "模拟数据，psutil未安装"
            }
    
    @contextmanager
    def measure_execution_time(self, metric_type: MetricType, 
                             metadata: Dict[str, Any] = None):
        """
        测量执行时间的上下文管理器
        
        Args:
            metric_type: 指标类型
            metadata: 附加元数据
        """
        start_time = time.time()
        metadata = metadata or {}
        
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            
            metric_id = f"measure_{metric_type.value}_{int(time.time())}"
            metric = PerformanceMetric(
                metric_id=metric_id,
                metric_type=metric_type,
                value=execution_time,
                timestamp=datetime.now(),
                metadata=metadata
            )
            
            self._store_metric(metric)
    
    def _init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建性能指标表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id TEXT PRIMARY KEY,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_metric_type_timestamp 
                ON performance_metrics(metric_type, timestamp)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("性能监控数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
    
    def _store_metric(self, metric: PerformanceMetric):
        """
        存储指标数据
        
        Args:
            metric: 性能指标
        """
        try:
            # 存储到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (metric_id, metric_type, value, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                metric.metric_id,
                metric.metric_type.value,
                metric.value,
                metric.timestamp.isoformat(),
                json.dumps(metric.metadata, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()
            
            # 存储到内存缓存
            with self._lock:
                self.metric_buffer[metric.metric_type].append(metric)
            
        except Exception as e:
            logger.error(f"存储指标数据失败: {str(e)}")
    
    def _query_metrics(self, start_time: datetime, end_time: datetime
                      ) -> List[PerformanceMetric]:
        """
        查询指标数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            指标列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT metric_id, metric_type, value, timestamp, metadata
                FROM performance_metrics
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            metrics = []
            for row in cursor.fetchall():
                metric_id, metric_type_str, value, timestamp_str, metadata_str = row
                
                try:
                    metric_type = MetricType(metric_type_str)
                    timestamp = datetime.fromisoformat(timestamp_str)
                    metadata = json.loads(metadata_str)
                    
                    metric = PerformanceMetric(
                        metric_id=metric_id,
                        metric_type=metric_type,
                        value=value,
                        timestamp=timestamp,
                        metadata=metadata
                    )
                    
                    metrics.append(metric)
                    
                except (ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"解析指标数据失败: {str(e)}")
                    continue
            
            conn.close()
            return metrics
            
        except Exception as e:
            logger.error(f"查询指标数据失败: {str(e)}")
            return []
    
    def _calculate_average_metrics(self, metrics: List[PerformanceMetric]
                                 ) -> Dict[str, float]:
        """
        计算平均指标
        
        Args:
            metrics: 指标列表
            
        Returns:
            平均指标字典
        """
        # 按指标类型分组
        grouped_metrics: Dict[MetricType, List[float]] = {}
        for metric in metrics:
            if metric.metric_type not in grouped_metrics:
                grouped_metrics[metric.metric_type] = []
            grouped_metrics[metric.metric_type].append(metric.value)
        
        # 计算平均值
        avg_metrics = {}
        
        for metric_type, values in grouped_metrics.items():
            if values:
                # 对于成功率类指标，使用加权平均
                if metric_type in [MetricType.SUBTASK_SUCCESS_RATE, 
                                 MetricType.CACHE_HIT_RATE]:
                    avg_metrics[f"avg_{metric_type.value}"] = sum(values) / len(values)
                else:
                    # 对于时间类指标，使用中位数减少异常值影响
                    try:
                        median_value = statistics.median(values)
                        avg_metrics[f"avg_{metric_type.value}"] = median_value
                    except statistics.StatisticsError:
                        avg_metrics[f"avg_{metric_type.value}"] = sum(values) / len(values)
        
        return avg_metrics
    
    def _generate_recommendations(self, efficiency_data: Dict[str, Any]
                                ) -> List[str]:
        """
        生成优化建议
        
        Args:
            efficiency_data: 效率分析数据
            
        Returns:
            建议列表
        """
        recommendations = []
        avg_metrics = efficiency_data.get("avg_metrics", {})
        improvement_rates = efficiency_data.get("improvement_rates", {})
        
        # 分析各项指标
        for metric_type_str, improvement in improvement_rates.items():
            if improvement < 0:  # 性能下降
                metric_type = None
                for mt in MetricType:
                    if f"avg_{mt.value}" == metric_type_str:
                        metric_type = mt
                        break
                
                if metric_type:
                    recommendations.append(
                        f"警告: {metric_type.value}性能下降{abs(improvement):.1f}%，"
                        f"需要优化相关模块"
                    )
        
        # 检查是否达到目标
        overall_improvement = efficiency_data.get("overall_improvement", 0.0)
        if overall_improvement < 20.0:
            recommendations.append(
                f"整体效率提升{overall_improvement:.1f}%，未达到20%目标。"
                f"建议重点优化任务分配算法和知识查询缓存策略"
            )
        
        # 基于具体指标的建议
        task_exec_time = avg_metrics.get("avg_task_execution_time", 0.0)
        if task_exec_time > 8.0:
            recommendations.append(
                f"任务平均执行时间{task_exec_time:.1f}秒过长，"
                f"建议优化任务分解策略和分身协同机制"
            )
        
        cache_hit_rate = avg_metrics.get("avg_cache_hit_rate", 0.0)
        if cache_hit_rate < 0.4:
            recommendations.append(
                f"知识查询缓存命中率{cache_hit_rate:.1%}较低，"
                f"建议优化缓存策略和查询频率分析"
            )
        
        subtask_success = avg_metrics.get("avg_subtask_success_rate", 0.0)
        if subtask_success < 0.7:
            recommendations.append(
                f"子任务平均成功率{subtask_success:.1%}不足，"
                f"建议优化分身能力匹配和任务复杂度评估"
            )
        
        # 默认建议
        if not recommendations:
            recommendations = [
                "当前性能表现良好，建议持续监控关键指标",
                "定期分析任务执行模式，优化资源分配策略",
                "扩展知识库覆盖范围，提升查询命中率"
            ]
        
        return recommendations
    
    def _trigger_alert(self, metric_type: MetricType, message: str,
                      context: Dict[str, Any]):
        """
        触发性能告警
        
        Args:
            metric_type: 指标类型
            message: 告警消息
            context: 上下文信息
        """
        alert_data = {
            "alert_id": f"alert_{metric_type.value}_{int(time.time())}",
            "metric_type": metric_type.value,
            "message": message,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "severity": "warning"
        }
        
        logger.warning(f"性能告警: {message}")
        
        # 可以扩展为发送告警通知（邮件、钉钉等）
        # 这里记录到日志
    
    def _monitoring_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 定期收集系统负载
                self.get_system_load()
                
                # 清理过期缓存
                self._cleanup_expired_cache()
                
                # 休眠指定间隔
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {str(e)}")
                time.sleep(self.sampling_interval)
    
    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        
        with self._lock:
            for metric_type, buffer in self.metric_buffer.items():
                # 清理过期条目（假设超过24小时）
                max_age = 24 * 3600  # 24小时
                
                # 由于使用deque，无法直接按时间清理
                # 在实际使用中，定期清空或使用更复杂的缓存策略
                pass  # 简化实现