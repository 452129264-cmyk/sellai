#!/usr/bin/env python3
"""
反馈循环系统
实现脚本效果的持续优化闭环，基于实际数据自动调整生成算法
建立从数据采集、分析、优化到验证的完整反馈循环
"""

import json
import logging
import time
import uuid
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
from collections import defaultdict
import threading
import queue

from ..script_generator.script_generator import ScriptGenerator, VideoScript
from ..script_generator.feedback_optimizer import (
    FeedbackOptimizer, PerformanceMetric, OptimizationSuggestion
)

logger = logging.getLogger(__name__)

class FeedbackCycleStage(str, Enum):
    """反馈循环阶段"""
    DATA_COLLECTION = "data_collection"      # 数据采集
    ANALYSIS = "analysis"                    # 数据分析
    OPTIMIZATION = "optimization"            # 算法优化
    VALIDATION = "validation"                # 效果验证
    DEPLOYMENT = "deployment"                # 部署更新

@dataclass
class FeedbackCycle:
    """反馈循环实例"""
    cycle_id: str
    stage: FeedbackCycleStage
    scripts_analyzed: List[str]
    optimizations_applied: List[Dict[str, Any]]
    performance_improvements: Dict[str, float]
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

@dataclass
class OptimizationResult:
    """优化结果"""
    optimization_id: str
    parameter_changes: List[Dict[str, Any]]
    expected_improvement: float
    actual_improvement: Optional[float] = None
    confidence_score: float = 0.0
    applied_at: datetime = field(default_factory=datetime.now)

class FeedbackLoopSystem:
    """反馈循环系统"""
    
    def __init__(self,
                 script_generator: ScriptGenerator,
                 feedback_optimizer: Optional[FeedbackOptimizer] = None,
                 db_path: Optional[str] = None):
        """
        初始化反馈循环系统
        
        Args:
            script_generator: 脚本生成器实例
            feedback_optimizer: 反馈优化器实例，可选
            db_path: 数据库路径，可选
        """
        self.script_generator = script_generator
        self.feedback_optimizer = feedback_optimizer or FeedbackOptimizer(db_path)
        
        # 反馈循环状态
        self.active_cycle: Optional[FeedbackCycle] = None
        self.cycle_history: List[FeedbackCycle] = []
        
        # 性能监控
        self.performance_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # 优化队列
        self.optimization_queue = queue.Queue()
        
        # 启动监控线程
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("反馈循环系统初始化完成")
    
    def start_optimization_cycle(self,
                                script_ids: Optional[List[str]] = None,
                                metrics: Optional[List[PerformanceMetric]] = None) -> str:
        """
        启动优化循环
        
        Args:
            script_ids: 要分析的脚本ID列表，可选
            metrics: 要优化的指标列表，可选
            
        Returns:
            str: 循环ID
        """
        cycle_id = f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        if script_ids is None:
            # 获取最近生成的脚本
            script_ids = self._get_recent_scripts(limit=50)
        
        if metrics is None:
            metrics = [
                PerformanceMetric.VIEWS,
                PerformanceMetric.ENGAGEMENT_RATE,
                PerformanceMetric.CONVERSION_RATE
            ]
        
        # 创建新的循环
        self.active_cycle = FeedbackCycle(
            cycle_id=cycle_id,
            stage=FeedbackCycleStage.DATA_COLLECTION,
            scripts_analyzed=script_ids,
            optimizations_applied=[],
            performance_improvements={}
        )
        
        # 启动异步优化
        optimization_thread = threading.Thread(
            target=self._run_optimization_cycle,
            args=(cycle_id, script_ids, metrics),
            daemon=True
        )
        optimization_thread.start()
        
        logger.info(f"启动优化循环：{cycle_id}，分析{len(script_ids)}个脚本")
        return cycle_id
    
    def record_performance_batch(self,
                                performance_records: List[Dict[str, Any]]) -> bool:
        """
        批量记录性能数据
        
        Args:
            performance_records: 性能记录列表
            
        Returns:
            bool: 记录是否成功
        """
        try:
            for record in performance_records:
                self.feedback_optimizer.record_performance(
                    script_id=record['script_id'],
                    metric=record['metric'],
                    value=record['value'],
                    platform=record.get('platform', 'unknown'),
                    audience_segment=record.get('audience_segment', 'general'),
                    context=record.get('context', {})
                )
            
            logger.info(f"批量记录性能数据：{len(performance_records)}条记录")
            return True
            
        except Exception as e:
            logger.error(f"批量记录性能数据失败：{e}")
            return False
    
    def apply_optimization_suggestions(self,
                                      suggestions: List[OptimizationSuggestion]) -> List[OptimizationResult]:
        """
        应用优化建议
        
        Args:
            suggestions: 优化建议列表
            
        Returns:
            List[OptimizationResult]: 应用结果列表
        """
        results = []
        
        for suggestion in suggestions:
            try:
                # 应用参数调整
                parameter_changes = []
                
                for change in suggestion.suggested_changes:
                    if change['type'] == 'parameter_adjustment':
                        param_name = change['parameter']
                        adjustment = change['adjustment']
                        
                        success = self.feedback_optimizer.adjust_algorithm_parameters(
                            parameter_name=param_name,
                            adjustment_direction=adjustment,
                            adjustment_factor=1.0
                        )
                        
                        if success:
                            parameter_changes.append({
                                'parameter': param_name,
                                'adjustment': adjustment,
                                'status': 'applied'
                            })
                        else:
                            parameter_changes.append({
                                'parameter': param_name,
                                'adjustment': adjustment,
                                'status': 'failed'
                            })
                
                # 记录优化结果
                result = OptimizationResult(
                    optimization_id=str(uuid.uuid4()),
                    parameter_changes=parameter_changes,
                    expected_improvement=suggestion.confidence_score * 0.2,  # 简化估算
                    confidence_score=suggestion.confidence_score
                )
                
                results.append(result)
                
                # 更新活动循环
                if self.active_cycle:
                    self.active_cycle.optimizations_applied.append({
                        'suggestion_id': suggestion.suggestion_id,
                        'issue_type': suggestion.issue_type,
                        'applied_at': datetime.now().isoformat()
                    })
                
                logger.info(f"应用优化建议：{suggestion.issue_type}")
                
            except Exception as e:
                logger.error(f"应用优化建议失败：{suggestion.suggestion_id}，错误：{e}")
        
        return results
    
    def evaluate_optimization_impact(self,
                                    cycle_id: str,
                                    validation_period_days: int = 7) -> Dict[str, Any]:
        """
        评估优化影响
        
        Args:
            cycle_id: 循环ID
            validation_period_days: 验证天数
            
        Returns:
            Dict[str, Any]: 影响评估结果
        """
        try:
            # 获取循环信息
            cycle = self._get_cycle_by_id(cycle_id)
            if not cycle:
                return {"error": f"循环不存在：{cycle_id}"}
            
            # 收集验证数据
            validation_data = self._collect_validation_data(
                script_ids=cycle.scripts_analyzed,
                days_back=validation_period_days
            )
            
            # 计算改进指标
            improvements = self._calculate_improvements(validation_data)
            
            # 更新循环状态
            cycle.performance_improvements = improvements
            cycle.completed_at = datetime.now()
            cycle.stage = FeedbackCycleStage.DEPLOYMENT
            
            # 保存到历史
            self.cycle_history.append(cycle)
            self.active_cycle = None
            
            # 记录优化成功
            logger.info(f"优化循环完成：{cycle_id}，改进：{improvements}")
            
            return {
                'cycle_id': cycle_id,
                'improvements': improvements,
                'validation_period': validation_period_days,
                'completed_at': cycle.completed_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"评估优化影响失败：{e}")
            return {"error": str(e)}
    
    def get_performance_dashboard(self,
                                  days_back: int = 30) -> Dict[str, Any]:
        """
        获取性能仪表板
        
        Args:
            days_back: 回溯天数
            
        Returns:
            Dict[str, Any]: 仪表板数据
        """
        try:
            # 获取趋势数据
            trends = self.feedback_optimizer.get_performance_trends(days_back=days_back)
            
            # 获取优化历史
            optimization_history = self.feedback_optimizer.get_optimization_history(limit=20)
            
            # 计算关键指标
            key_metrics = self._calculate_key_metrics(trends)
            
            # 识别改进机会
            improvement_opportunities = self._identify_improvement_opportunities(trends)
            
            dashboard = {
                'time_range': f"最近{days_back}天",
                'key_metrics': key_metrics,
                'trends': trends,
                'optimization_history': optimization_history[:10],  # 只返回前10条
                'improvement_opportunities': improvement_opportunities,
                'active_cycle': self.active_cycle.cycle_id if self.active_cycle else None,
                'total_cycles_completed': len(self.cycle_history)
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"获取性能仪表板失败：{e}")
            return {"error": str(e)}
    
    def schedule_periodic_optimization(self,
                                      interval_hours: int = 24,
                                      max_scripts_per_cycle: int = 100) -> str:
        """
        安排定期优化
        
        Args:
            interval_hours: 间隔小时数
            max_scripts_per_cycle: 每周期最大脚本数
            
        Returns:
            str: 调度ID
        """
        scheduler_id = f"scheduler_{uuid.uuid4().hex[:8]}"
        
        def periodic_task():
            while self.monitoring_active:
                try:
                    # 等待间隔
                    time.sleep(interval_hours * 3600)
                    
                    # 执行优化循环
                    recent_scripts = self._get_recent_scripts(limit=max_scripts_per_cycle)
                    
                    if recent_scripts:
                        cycle_id = self.start_optimization_cycle(
                            script_ids=recent_scripts,
                            metrics=[
                                PerformanceMetric.VIEWS,
                                PerformanceMetric.CONVERSION_RATE
                            ]
                        )
                        
                        logger.info(f"定期优化执行：{scheduler_id} -> {cycle_id}")
                        
                except Exception as e:
                    logger.error(f"定期优化任务失败：{e}")
        
        # 启动调度线程
        scheduler_thread = threading.Thread(target=periodic_task, daemon=True)
        scheduler_thread.start()
        
        logger.info(f"安排定期优化：{scheduler_id}，间隔{interval_hours}小时")
        return scheduler_id
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("反馈循环监控已停止")
    
    def _run_optimization_cycle(self,
                               cycle_id: str,
                               script_ids: List[str],
                               metrics: List[PerformanceMetric]):
        """运行优化循环"""
        try:
            # 阶段1: 数据采集
            self._update_cycle_stage(cycle_id, FeedbackCycleStage.DATA_COLLECTION)
            performance_data = self._collect_performance_data(script_ids, metrics)
            
            # 阶段2: 数据分析
            self._update_cycle_stage(cycle_id, FeedbackCycleStage.ANALYSIS)
            suggestions = self._analyze_performance_data(performance_data)
            
            # 阶段3: 算法优化
            self._update_cycle_stage(cycle_id, FeedbackCycleStage.OPTIMIZATION)
            optimization_results = self._apply_optimizations(suggestions)
            
            # 阶段4: 效果验证
            self._update_cycle_stage(cycle_id, FeedbackCycleStage.VALIDATION)
            
            # 等待验证数据
            time.sleep(3600 * 24)  # 等待1天收集验证数据
            
            # 阶段5: 部署更新
            self._update_cycle_stage(cycle_id, FeedbackCycleStage.DEPLOYMENT)
            
            # 评估影响
            impact_report = self.evaluate_optimization_impact(cycle_id)
            
            logger.info(f"优化循环{cycle_id}完成，报告：{impact_report}")
            
        except Exception as e:
            logger.error(f"优化循环{cycle_id}执行失败：{e}")
            # 更新循环状态为失败
            if self.active_cycle and self.active_cycle.cycle_id == cycle_id:
                self.active_cycle.stage = FeedbackCycleStage.DEPLOYMENT
                self.active_cycle.completed_at = datetime.now()
    
    def _collect_performance_data(self,
                                 script_ids: List[str],
                                 metrics: List[PerformanceMetric]) -> Dict[str, Any]:
        """收集性能数据"""
        performance_data = {}
        
        for script_id in script_ids:
            script_data = {}
            
            for metric in metrics:
                # 从数据库获取性能数据
                avg_value = self._get_average_performance(script_id, metric)
                if avg_value is not None:
                    script_data[metric.value] = avg_value
            
            if script_data:
                performance_data[script_id] = script_data
        
        return performance_data
    
    def _analyze_performance_data(self,
                                 performance_data: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """分析性能数据"""
        suggestions = []
        
        # 分析每个脚本
        for script_id, metrics in performance_data.items():
            # 获取脚本信息
            script_info = self._get_script_info(script_id)
            if not script_info:
                continue
            
            # 创建简化的脚本对象用于分析
            script = VideoScript(
                script_id=script_id,
                title=script_info.get('title', ''),
                script_type=script_info.get('script_type', 'product_demo')
            )
            
            # 构建反馈数据
            feedback_data = {
                'views': {'count': metrics.get(PerformanceMetric.VIEWS.value, 0)},
                'engagement': {'rate': metrics.get(PerformanceMetric.ENGAGEMENT_RATE.value, 0)},
                'conversions': {'rate': metrics.get(PerformanceMetric.CONVERSION_RATE.value, 0)}
            }
            
            # 分析反馈
            script_suggestions = self.feedback_optimizer.analyze_feedback(
                script=script,
                feedback_data=feedback_data
            )
            
            suggestions.extend(script_suggestions)
        
        return suggestions
    
    def _apply_optimizations(self,
                            suggestions: List[OptimizationSuggestion]) -> List[OptimizationResult]:
        """应用优化"""
        return self.apply_optimization_suggestions(suggestions)
    
    def _collect_validation_data(self,
                                script_ids: List[str],
                                days_back: int) -> Dict[str, Any]:
        """收集验证数据"""
        validation_data = {}
        
        for script_id in script_ids:
            # 获取最近几天的性能数据
            recent_performance = self._get_recent_performance(script_id, days_back)
            validation_data[script_id] = recent_performance
        
        return validation_data
    
    def _calculate_improvements(self,
                               validation_data: Dict[str, Any]) -> Dict[str, float]:
        """计算改进指标"""
        improvements = {}
        
        # 简化的改进计算
        total_scripts = len(validation_data)
        if total_scripts == 0:
            return improvements
        
        # 计算平均观看增长
        total_view_growth = 0
        for script_id, performance in validation_data.items():
            if 'views' in performance:
                total_view_growth += performance['views'].get('growth_rate', 0)
        
        if total_scripts > 0:
            improvements['average_view_growth'] = total_view_growth / total_scripts
        
        # 计算平均互动增长
        total_engagement_growth = 0
        for script_id, performance in validation_data.items():
            if 'engagement_rate' in performance:
                total_engagement_growth += performance['engagement_rate'].get('growth_rate', 0)
        
        if total_scripts > 0:
            improvements['average_engagement_growth'] = total_engagement_growth / total_scripts
        
        # 计算平均转化增长
        total_conversion_growth = 0
        for script_id, performance in validation_data.items():
            if 'conversion_rate' in performance:
                total_conversion_growth += performance['conversion_rate'].get('growth_rate', 0)
        
        if total_scripts > 0:
            improvements['average_conversion_growth'] = total_conversion_growth / total_scripts
        
        return improvements
    
    def _calculate_key_metrics(self,
                              trends: Dict[str, Any]) -> Dict[str, Any]:
        """计算关键指标"""
        key_metrics = {}
        
        # 总体表现
        if 'views' in trends:
            key_metrics['average_views'] = trends['views'].get('average', 0)
        
        if 'engagement_rate' in trends:
            key_metrics['average_engagement'] = trends['engagement_rate'].get('average', 0)
        
        if 'conversion_rate' in trends:
            key_metrics['average_conversion'] = trends['conversion_rate'].get('average', 0)
        
        # 改进趋势
        improvement_trends = {}
        for metric, data in trends.items():
            direction = data.get('trend_direction', 'stable')
            improvement_trends[metric] = direction
        
        key_metrics['improvement_trends'] = improvement_trends
        
        # 稳定性指标
        stability_scores = {}
        for metric, data in trends.items():
            sample_count = data.get('sample_count', 0)
            avg_value = data.get('average', 0)
            
            # 简化的稳定性计算
            if sample_count > 10 and avg_value > 0:
                stability = min(1.0, sample_count / 100)  # 样本越多越稳定
                stability_scores[metric] = stability
        
        key_metrics['stability_scores'] = stability_scores
        
        return key_metrics
    
    def _identify_improvement_opportunities(self,
                                          trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别改进机会"""
        opportunities = []
        
        for metric, data in trends.items():
            avg_value = data.get('average', 0)
            trend_direction = data.get('trend_direction', 'stable')
            
            # 确定改进优先级
            if trend_direction == 'declining':
                priority = 'high'
                description = f"{metric}呈下降趋势，需要立即优化"
            elif avg_value < 0.5:  # 低于基准的50%
                priority = 'medium'
                description = f"{metric}表现不佳，建议优化"
            else:
                continue
            
            opportunities.append({
                'metric': metric,
                'current_value': avg_value,
                'trend_direction': trend_direction,
                'priority': priority,
                'description': description,
                'suggested_actions': [
                    f"分析{metric}低下的原因",
                    f"调整相关算法参数",
                    f"测试不同的内容策略"
                ]
            })
        
        return opportunities
    
    def _get_recent_scripts(self, limit: int = 100) -> List[str]:
        """获取最近生成的脚本ID"""
        try:
            conn = sqlite3.connect(self.feedback_optimizer.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT script_id FROM script_generations
                ORDER BY generated_at DESC
                LIMIT ?
            ''', (limit,))
            
            script_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return script_ids
            
        except Exception as e:
            logger.error(f"获取最近脚本失败：{e}")
            return []
    
    def _get_script_info(self, script_id: str) -> Optional[Dict[str, Any]]:
        """获取脚本信息"""
        try:
            conn = sqlite3.connect(self.feedback_optimizer.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM script_generations
                WHERE script_id = ?
            ''', (script_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                columns = ['script_id', 'title', 'script_type', 'language', 
                          'profit_margin', 'commercial_score', 'generated_at']
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            logger.error(f"获取脚本信息失败：{e}")
            return None
    
    def _get_average_performance(self,
                                script_id: str,
                                metric: PerformanceMetric) -> Optional[float]:
        """获取平均性能数据"""
        try:
            conn = sqlite3.connect(self.feedback_optimizer.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT AVG(value) FROM performance_data
                WHERE script_id = ? AND metric = ?
            ''', (script_id, metric.value))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] is not None:
                return float(result[0])
            
            return None
            
        except Exception as e:
            logger.error(f"获取平均性能失败：{e}")
            return None
    
    def _get_recent_performance(self,
                               script_id: str,
                               days_back: int) -> Dict[str, Any]:
        """获取最近性能数据"""
        try:
            start_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            conn = sqlite3.connect(self.feedback_optimizer.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT metric, AVG(value), COUNT(*)
                FROM performance_data
                WHERE script_id = ? AND timestamp >= ?
                GROUP BY metric
            ''', (script_id, start_date))
            
            performance = {}
            for metric, avg_value, count in cursor.fetchall():
                performance[metric] = {
                    'average': avg_value,
                    'sample_count': count
                }
            
            conn.close()
            
            # 计算增长（简化）
            for metric, data in performance.items():
                # 获取之前的数据作为基准
                historical_avg = self._get_historical_average(script_id, metric, days_back * 2)
                if historical_avg and historical_avg > 0:
                    growth_rate = (data['average'] - historical_avg) / historical_avg
                    data['growth_rate'] = growth_rate
            
            return performance
            
        except Exception as e:
            logger.error(f"获取最近性能失败：{e}")
            return {}
    
    def _get_historical_average(self,
                               script_id: str,
                               metric: str,
                               days_back: int) -> Optional[float]:
        """获取历史平均数据"""
        try:
            start_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            end_date = (datetime.now() - timedelta(days=days_back//2)).isoformat()
            
            conn = sqlite3.connect(self.feedback_optimizer.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT AVG(value) FROM performance_data
                WHERE script_id = ? AND metric = ? 
                AND timestamp >= ? AND timestamp < ?
            ''', (script_id, metric, start_date, end_date))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] is not None:
                return float(result[0])
            
            return None
            
        except Exception as e:
            logger.error(f"获取历史平均失败：{e}")
            return None
    
    def _update_cycle_stage(self, cycle_id: str, stage: FeedbackCycleStage):
        """更新循环阶段"""
        if self.active_cycle and self.active_cycle.cycle_id == cycle_id:
            self.active_cycle.stage = stage
            
            logger.info(f"更新循环{cycle_id}阶段：{stage.value}")
    
    def _get_cycle_by_id(self, cycle_id: str) -> Optional[FeedbackCycle]:
        """根据ID获取循环"""
        if self.active_cycle and self.active_cycle.cycle_id == cycle_id:
            return self.active_cycle
        
        for cycle in self.cycle_history:
            if cycle.cycle_id == cycle_id:
                return cycle
        
        return None
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                # 检查是否有待处理的优化
                if self.active_cycle:
                    # 监控循环进度
                    cycle_duration = datetime.now() - self.active_cycle.started_at
                    
                    if cycle_duration > timedelta(hours=48):
                        logger.warning(f"循环{self.active_cycle.cycle_id}已运行超过48小时，强制完成")
                        self.evaluate_optimization_impact(self.active_cycle.cycle_id)
                
                # 收集系统状态
                self._collect_system_metrics()
                
                # 等待下一次检查
                time.sleep(3600)  # 每小时检查一次
                
            except Exception as e:
                logger.error(f"监控循环错误：{e}")
                time.sleep(300)  # 错误后等待5分钟
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        # 简化实现
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'active_scripts': len(self._get_recent_scripts(limit=1000)),
            'performance_records': self._get_performance_record_count(),
            'optimization_cycles': len(self.cycle_history)
        }
        
        # 保存到数据库
        self._save_system_metrics(metrics)
    
    def _get_performance_record_count(self) -> int:
        """获取性能记录数量"""
        try:
            conn = sqlite3.connect(self.feedback_optimizer.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM performance_data')
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"获取性能记录数量失败：{e}")
            return 0
    
    def _save_system_metrics(self, metrics: Dict[str, Any]):
        """保存系统指标"""
        try:
            conn = sqlite3.connect(self.feedback_optimizer.db_path)
            cursor = conn.cursor()
            
            # 创建系统指标表（如果不存在）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    metric_name TEXT,
                    metric_value TEXT,
                    recorded_at TEXT
                )
            ''')
            
            # 保存指标
            for name, value in metrics.items():
                if name != 'timestamp':
                    cursor.execute('''
                        INSERT INTO system_metrics 
                        (timestamp, metric_name, metric_value, recorded_at)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        metrics['timestamp'],
                        name,
                        str(value),
                        datetime.now().isoformat()
                    ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存系统指标失败：{e}")