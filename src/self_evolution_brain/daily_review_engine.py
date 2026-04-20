#!/usr/bin/env python3
"""
每日复盘引擎
实现全球商业数据、风口变化、落地效果的自动复盘功能
"""

import json
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
import hashlib
from enum import Enum

# 尝试导入相关模块
try:
    from src.shared_state_manager import SharedStateManager
    HAS_SHARED_STATE = True
except ImportError:
    HAS_SHARED_STATE = False
    logging.warning("shared_state_manager 模块未找到，部分功能将受限")

try:
    from src.global_business_brain import GlobalBusinessBrain
    HAS_GLOBAL_BRAIN = True
except ImportError:
    HAS_GLOBAL_BRAIN = False
    logging.warning("global_business_brain 模块未找到，市场分析功能将受限")

try:
    from src.ai_negotiation_engine import AINegotiationEngine
    HAS_NEGOTIATION_ENGINE = True
except ImportError:
    HAS_NEGOTIATION_ENGINE = False
    logging.warning("ai_negotiation_engine 模块未找到，谈判记录分析功能将受限")

logger = logging.getLogger(__name__)


class ReviewDimension(Enum):
    """复盘维度"""
    MARKET_TREND = "market_trend"           # 市场趋势
    BUSINESS_PERFORMANCE = "business_performance"  # 业务绩效
    AI_AVATAR_EFFECTIVENESS = "ai_avatar_effectiveness"  # AI分身效能
    RESOURCE_UTILIZATION = "resource_utilization"  # 资源利用
    USER_SATISFACTION = "user_satisfaction"  # 用户满意度
    RISK_EXPOSURE = "risk_exposure"         # 风险暴露


@dataclass
class ReviewMetrics:
    """复盘指标"""
    dimension: ReviewDimension
    current_value: float
    previous_value: float
    improvement_rate: float
    confidence_score: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewInsight:
    """复盘洞察"""
    insight_id: str
    dimension: ReviewDimension
    insight_type: str  # positive, negative, opportunity, risk
    title: str
    description: str
    supporting_data: List[Dict[str, Any]]
    impact_score: float
    confidence_score: float
    recommended_actions: List[str]
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DailyReviewReport:
    """每日复盘报告"""
    report_id: str
    review_period: Dict[str, str]  # start, end
    dimensions_covered: List[ReviewDimension]
    metrics_summary: Dict[str, ReviewMetrics]
    key_insights: List[ReviewInsight]
    overall_assessment: Dict[str, Any]
    improvement_opportunities: List[Dict[str, Any]]
    risk_warnings: List[Dict[str, Any]]
    generated_at: datetime
    generated_by: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, indent=2, ensure_ascii=False)


class DailyReviewEngine:
    """每日复盘引擎"""
    
    def __init__(self, config, db_path: str = "data/shared_state/state.db"):
        """
        初始化复盘引擎
        
        Args:
            config: 配置对象
            db_path: 数据库路径
        """
        self.config = config
        self.db_path = db_path
        
        # 初始化组件
        self._init_components()
        
        # 复盘状态
        self.last_review_time = None
        self.review_history = []
        
        logger.info("每日复盘引擎初始化完成")
    
    def _init_components(self):
        """初始化各功能组件"""
        # 共享状态管理器
        if HAS_SHARED_STATE:
            self.state_manager = SharedStateManager(self.db_path)
        else:
            self.state_manager = None
        
        # 全域商业大脑
        if HAS_GLOBAL_BRAIN:
            brain_config = {
                'db_path': self.db_path,
                'node_id': self.config.node_id,
                'enable_network': False,
                'analysis_period': self.config.review_strategy.review_period_days
            }
            self.global_brain = GlobalBusinessBrain(brain_config)
        else:
            self.global_brain = None
        
        # AI谈判引擎
        if HAS_NEGOTIATION_ENGINE:
            self.negotiation_engine = AINegotiationEngine(self.db_path)
        else:
            self.negotiation_engine = None
    
    def execute_daily_review(self, review_date: datetime = None) -> DailyReviewReport:
        """
        执行每日复盘
        
        Args:
            review_date: 复盘日期，默认为当前日期
            
        Returns:
            每日复盘报告
        """
        if review_date is None:
            review_date = datetime.now()
        
        logger.info(f"开始执行每日复盘，日期: {review_date.date()}")
        
        # 确定复盘时间范围
        period_start = review_date - timedelta(days=self.config.review_strategy.review_period_days)
        period_end = review_date
        
        # 收集复盘数据
        review_data = self._collect_review_data(period_start, period_end)
        
        # 分析各维度指标
        metrics_summary = self._analyze_review_metrics(review_data)
        
        # 生成关键洞察
        key_insights = self._generate_key_insights(metrics_summary, review_data)
        
        # 评估整体状况
        overall_assessment = self._assess_overall_performance(metrics_summary)
        
        # 识别改进机会
        improvement_opportunities = self._identify_improvement_opportunities(metrics_summary, key_insights)
        
        # 生成风险预警
        risk_warnings = self._generate_risk_warnings(metrics_summary, key_insights)
        
        # 构建报告
        report = DailyReviewReport(
            report_id=f"daily_review_{int(time.time())}_{self.config.node_id}",
            review_period={
                'start': period_start.isoformat(),
                'end': period_end.isoformat()
            },
            dimensions_covered=[dim for dim in ReviewDimension],
            metrics_summary=metrics_summary,
            key_insights=key_insights,
            overall_assessment=overall_assessment,
            improvement_opportunities=improvement_opportunities,
            risk_warnings=risk_warnings,
            generated_at=datetime.now(),
            generated_by=self.config.node_id
        )
        
        # 更新状态
        self.last_review_time = datetime.now()
        self.review_history.append(report)
        
        logger.info(f"每日复盘完成，报告ID: {report.report_id}")
        return report
    
    def _collect_review_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        收集复盘数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            复盘数据字典
        """
        data = {
            'market_analysis': [],
            'business_performance': [],
            'ai_avatar_records': [],
            'user_feedback': [],
            'risk_incidents': []
        }
        
        try:
            # 1. 市场分析数据
            if self.global_brain:
                market_report = self.global_brain.generate_global_market_analysis()
                data['market_analysis'].append(market_report)
            
            # 2. 业务绩效数据（从共享状态库获取）
            if self.state_manager:
                conn = self.state_manager.connect()
                cursor = conn.cursor()
                
                # 查询业务绩效记录
                cursor.execute("""
                    SELECT task_id, avatar_id, task_type, completion_status, 
                           performance_score, completion_time, created_at
                    FROM avatar_tasks
                    WHERE created_at >= ? AND created_at <= ?
                    ORDER BY created_at DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                
                rows = cursor.fetchall()
                for row in rows:
                    data['business_performance'].append(dict(row))
                
                # 查询AI分身记录
                cursor.execute("""
                    SELECT avatar_id, capability_score, success_rate, 
                           avg_response_time, created_at
                    FROM avatar_performance
                    WHERE created_at >= ? AND created_at <= ?
                    ORDER BY created_at DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                
                rows = cursor.fetchall()
                for row in rows:
                    data['ai_avatar_records'].append(dict(row))
                
                # 查询用户反馈
                cursor.execute("""
                    SELECT feedback_id, user_id, rating, feedback_text, 
                           category, sentiment_score, created_at
                    FROM user_feedback
                    WHERE created_at >= ? AND created_at <= ?
                    ORDER BY created_at DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                
                rows = cursor.fetchall()
                for row in rows:
                    data['user_feedback'].append(dict(row))
                
                # 查询风险事件
                cursor.execute("""
                    SELECT incident_id, incident_type, severity, 
                           impact_description, resolution_status, created_at
                    FROM risk_incidents
                    WHERE created_at >= ? AND created_at <= ?
                    ORDER BY created_at DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                
                rows = cursor.fetchall()
                for row in rows:
                    data['risk_incidents'].append(dict(row))
                
                conn.close()
            
            # 3. AI谈判记录
            if self.negotiation_engine:
                # 这里可以添加获取谈判历史的方法
                pass
        
        except Exception as e:
            logger.error(f"收集复盘数据时出错: {e}")
        
        # 记录数据统计
        logger.info(f"复盘数据收集完成: "
                   f"市场分析{len(data['market_analysis'])}条, "
                   f"业务绩效{len(data['business_performance'])}条, "
                   f"AI分身记录{len(data['ai_avatar_records'])}条, "
                   f"用户反馈{len(data['user_feedback'])}条, "
                   f"风险事件{len(data['risk_incidents'])}条")
        
        return data
    
    def _analyze_review_metrics(self, review_data: Dict[str, Any]) -> Dict[str, ReviewMetrics]:
        """
        分析复盘指标
        
        Args:
            review_data: 复盘数据
            
        Returns:
            指标摘要字典
        """
        metrics_summary = {}
        
        try:
            # 1. 市场趋势维度指标
            market_trend_score = self._calculate_market_trend_score(review_data['market_analysis'])
            market_previous_score = self._get_previous_market_score()
            
            metrics_summary[ReviewDimension.MARKET_TREND.value] = ReviewMetrics(
                dimension=ReviewDimension.MARKET_TREND,
                current_value=market_trend_score,
                previous_value=market_previous_score,
                improvement_rate=self._calculate_improvement_rate(market_trend_score, market_previous_score),
                confidence_score=0.85,
                timestamp=datetime.now()
            )
            
            # 2. 业务绩效维度指标
            business_performance_score = self._calculate_business_performance_score(review_data['business_performance'])
            business_previous_score = self._get_previous_business_score()
            
            metrics_summary[ReviewDimension.BUSINESS_PERFORMANCE.value] = ReviewMetrics(
                dimension=ReviewDimension.BUSINESS_PERFORMANCE,
                current_value=business_performance_score,
                previous_value=business_previous_score,
                improvement_rate=self._calculate_improvement_rate(business_performance_score, business_previous_score),
                confidence_score=0.8,
                timestamp=datetime.now()
            )
            
            # 3. AI分身效能维度指标
            ai_avatar_score = self._calculate_ai_avatar_score(review_data['ai_avatar_records'])
            ai_previous_score = self._get_previous_ai_score()
            
            metrics_summary[ReviewDimension.AI_AVATAR_EFFECTIVENESS.value] = ReviewMetrics(
                dimension=ReviewDimension.AI_AVATAR_EFFECTIVENESS,
                current_value=ai_avatar_score,
                previous_value=ai_previous_score,
                improvement_rate=self._calculate_improvement_rate(ai_avatar_score, ai_previous_score),
                confidence_score=0.75,
                timestamp=datetime.now()
            )
            
            # 4. 资源利用维度指标
            resource_utilization_score = self._calculate_resource_utilization_score(review_data['business_performance'])
            resource_previous_score = self._get_previous_resource_score()
            
            metrics_summary[ReviewDimension.RESOURCE_UTILIZATION.value] = ReviewMetrics(
                dimension=ReviewDimension.RESOURCE_UTILIZATION,
                current_value=resource_utilization_score,
                previous_value=resource_previous_score,
                improvement_rate=self._calculate_improvement_rate(resource_utilization_score, resource_previous_score),
                confidence_score=0.7,
                timestamp=datetime.now()
            )
            
            # 5. 用户满意度维度指标
            user_satisfaction_score = self._calculate_user_satisfaction_score(review_data['user_feedback'])
            user_previous_score = self._get_previous_user_score()
            
            metrics_summary[ReviewDimension.USER_SATISFACTION.value] = ReviewMetrics(
                dimension=ReviewDimension.USER_SATISFACTION,
                current_value=user_satisfaction_score,
                previous_value=user_previous_score,
                improvement_rate=self._calculate_improvement_rate(user_satisfaction_score, user_previous_score),
                confidence_score=0.8,
                timestamp=datetime.now()
            )
            
            # 6. 风险暴露维度指标
            risk_exposure_score = self._calculate_risk_exposure_score(review_data['risk_incidents'])
            risk_previous_score = self._get_previous_risk_score()
            
            metrics_summary[ReviewDimension.RISK_EXPOSURE.value] = ReviewMetrics(
                dimension=ReviewDimension.RISK_EXPOSURE,
                current_value=risk_exposure_score,
                previous_value=risk_previous_score,
                improvement_rate=self._calculate_improvement_rate(risk_exposure_score, risk_previous_score),
                confidence_score=0.75,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            logger.error(f"分析复盘指标时出错: {e}")
        
        return metrics_summary
    
    def _calculate_market_trend_score(self, market_analysis: List[Dict[str, Any]]) -> float:
        """计算市场趋势得分"""
        if not market_analysis:
            return 0.5  # 默认中等
        
        try:
            # 基于市场分析报告计算得分
            report = market_analysis[0] if market_analysis else {}
            health_score = report.get('executive_summary', {}).get('overall_market_health', 0.5)
            
            # 考虑机会数量
            opportunities = report.get('market_opportunities', [])
            opportunity_score = min(len(opportunities) / 10, 1.0)  # 最多10个机会为满分
            
            # 考虑风险数量
            risks = report.get('risk_alerts', [])
            risk_penalty = min(len(risks) / 5, 0.5)  # 最多5个风险，扣分0.5
            
            # 综合得分
            score = (health_score * 0.6 + opportunity_score * 0.4) * (1 - risk_penalty)
            return max(0, min(1, score))
            
        except Exception as e:
            logger.error(f"计算市场趋势得分时出错: {e}")
            return 0.5
    
    def _calculate_business_performance_score(self, performance_data: List[Dict[str, Any]]) -> float:
        """计算业务绩效得分"""
        if not performance_data:
            return 0.5
        
        try:
            # 计算任务完成率
            total_tasks = len(performance_data)
            completed_tasks = sum(1 for task in performance_data 
                                if task.get('completion_status') == 'completed')
            completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
            
            # 计算平均绩效得分
            scores = [task.get('performance_score', 0) for task in performance_data 
                     if task.get('performance_score') is not None]
            avg_score = sum(scores) / len(scores) if scores else 0.7
            
            # 综合得分
            score = (completion_rate * 0.6 + avg_score * 0.4)
            return max(0, min(1, score))
            
        except Exception as e:
            logger.error(f"计算业务绩效得分时出错: {e}")
            return 0.5
    
    def _calculate_ai_avatar_score(self, avatar_records: List[Dict[str, Any]]) -> float:
        """计算AI分身效能得分"""
        if not avatar_records:
            return 0.5
        
        try:
            # 计算平均能力得分
            capability_scores = [record.get('capability_score', 0) for record in avatar_records 
                               if record.get('capability_score') is not None]
            avg_capability = sum(capability_scores) / len(capability_scores) if capability_scores else 0.7
            
            # 计算平均成功率
            success_rates = [record.get('success_rate', 0) for record in avatar_records 
                           if record.get('success_rate') is not None]
            avg_success = sum(success_rates) / len(success_rates) if success_rates else 0.7
            
            # 综合得分
            score = (avg_capability * 0.5 + avg_success * 0.5)
            return max(0, min(1, score))
            
        except Exception as e:
            logger.error(f"计算AI分身效能得分时出错: {e}")
            return 0.5
    
    def _calculate_resource_utilization_score(self, performance_data: List[Dict[str, Any]]) -> float:
        """计算资源利用得分"""
        if not performance_data:
            return 0.5
        
        try:
            # 计算平均完成时间（越短越好）
            completion_times = [task.get('completion_time', 0) for task in performance_data 
                              if task.get('completion_time') is not None]
            
            if completion_times:
                avg_time = sum(completion_times) / len(completion_times)
                # 假设理想平均时间为60分钟
                time_score = max(0, 1 - (avg_time / 3600))  # 转换为小时
            else:
                time_score = 0.7
            
            return time_score
            
        except Exception as e:
            logger.error(f"计算资源利用得分时出错: {e}")
            return 0.5
    
    def _calculate_user_satisfaction_score(self, feedback_data: List[Dict[str, Any]]) -> float:
        """计算用户满意度得分"""
        if not feedback_data:
            return 0.5
        
        try:
            # 计算平均评分
            ratings = [fb.get('rating', 0) for fb in feedback_data 
                      if fb.get('rating') is not None]
            
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                # 假设评分范围0-5，转换为0-1
                score = avg_rating / 5
            else:
                # 计算平均情感得分
                sentiments = [fb.get('sentiment_score', 0) for fb in feedback_data 
                            if fb.get('sentiment_score') is not None]
                if sentiments:
                    avg_sentiment = sum(sentiments) / len(sentiments)
                    score = (avg_sentiment + 1) / 2  # 从-1到1转换为0到1
                else:
                    score = 0.7
            
            return max(0, min(1, score))
            
        except Exception as e:
            logger.error(f"计算用户满意度得分时出错: {e}")
            return 0.5
    
    def _calculate_risk_exposure_score(self, risk_incidents: List[Dict[str, Any]]) -> float:
        """计算风险暴露得分"""
        if not risk_incidents:
            return 0.9  # 无风险事件，得分高
        
        try:
            # 计算严重风险比例
            high_severity = sum(1 for incident in risk_incidents 
                              if incident.get('severity') in ['high', 'critical'])
            
            risk_ratio = high_severity / len(risk_incidents)
            
            # 风险暴露得分（风险越少得分越高）
            score = 1 - risk_ratio
            return max(0, min(1, score))
            
        except Exception as e:
            logger.error(f"计算风险暴露得分时出错: {e}")
            return 0.7
    
    def _get_previous_market_score(self) -> float:
        """获取前一周期市场趋势得分"""
        # 简化实现：从数据库或缓存获取
        return 0.5
    
    def _get_previous_business_score(self) -> float:
        """获取前一周期业务绩效得分"""
        return 0.5
    
    def _get_previous_ai_score(self) -> float:
        """获取前一周期AI分身效能得分"""
        return 0.5
    
    def _get_previous_resource_score(self) -> float:
        """获取前一周期资源利用得分"""
        return 0.5
    
    def _get_previous_user_score(self) -> float:
        """获取前一周期用户满意度得分"""
        return 0.5
    
    def _get_previous_risk_score(self) -> float:
        """获取前一周期风险暴露得分"""
        return 0.7
    
    def _calculate_improvement_rate(self, current: float, previous: float) -> float:
        """计算改进率"""
        if previous == 0:
            return 1.0 if current > 0 else 0.0
        return (current - previous) / previous
    
    def _generate_key_insights(self, metrics_summary: Dict[str, ReviewMetrics], 
                             review_data: Dict[str, Any]) -> List[ReviewInsight]:
        """
        生成关键洞察
        
        Args:
            metrics_summary: 指标摘要
            review_data: 复盘数据
            
        Returns:
            关键洞察列表
        """
        insights = []
        insight_id_base = f"insight_{int(time.time())}"
        
        try:
            # 1. 市场趋势洞察
            market_metrics = metrics_summary.get(ReviewDimension.MARKET_TREND.value)
            if market_metrics and market_metrics.improvement_rate > 0.1:
                insights.append(ReviewInsight(
                    insight_id=f"{insight_id_base}_market_positive",
                    dimension=ReviewDimension.MARKET_TREND,
                    insight_type="positive",
                    title="市场趋势持续向好",
                    description=f"市场健康度得分{market_metrics.current_value:.2f}，"
                              f"较前一周期提升{market_metrics.improvement_rate:.1%}",
                    supporting_data=review_data['market_analysis'],
                    impact_score=0.8,
                    confidence_score=market_metrics.confidence_score,
                    recommended_actions=[
                        "加大市场拓展力度",
                        "重点关注高增长细分市场",
                        "优化市场资源配置"
                    ],
                    generated_at=datetime.now()
                ))
            
            # 2. 业务绩效洞察
            business_metrics = metrics_summary.get(ReviewDimension.BUSINESS_PERFORMANCE.value)
            if business_metrics and business_metrics.current_value < 0.6:
                insights.append(ReviewInsight(
                    insight_id=f"{insight_id_base}_business_needs_improvement",
                    dimension=ReviewDimension.BUSINESS_PERFORMANCE,
                    insight_type="negative",
                    title="业务绩效有待提升",
                    description=f"业务绩效得分{business_metrics.current_value:.2f}，"
                              f"低于目标水平",
                    supporting_data=review_data['business_performance'][:5],  # 前5条记录
                    impact_score=0.7,
                    confidence_score=business_metrics.confidence_score,
                    recommended_actions=[
                        "优化任务分配机制",
                        "加强过程监控与指导",
                        "完善绩效评估标准"
                    ],
                    generated_at=datetime.now()
                ))
            
            # 3. AI分身效能洞察
            ai_metrics = metrics_summary.get(ReviewDimension.AI_AVATAR_EFFECTIVENESS.value)
            if ai_metrics and ai_metrics.current_value > 0.8:
                insights.append(ReviewInsight(
                    insight_id=f"{insight_id_base}_ai_excellent",
                    dimension=ReviewDimension.AI_AVATAR_EFFECTIVENESS,
                    insight_type="positive",
                    title="AI分身效能表现优异",
                    description=f"AI分身效能得分{ai_metrics.current_value:.2f}，"
                              f"处于优秀水平",
                    supporting_data=review_data['ai_avatar_records'][:5],
                    impact_score=0.6,
                    confidence_score=ai_metrics.confidence_score,
                    recommended_actions=[
                        "推广优秀分身的最佳实践",
                        "考虑增加同类分身数量",
                        "进一步优化任务匹配算法"
                    ],
                    generated_at=datetime.now()
                ))
            
            # 4. 风险暴露洞察
            risk_metrics = metrics_summary.get(ReviewDimension.RISK_EXPOSURE.value)
            if risk_metrics and risk_metrics.current_value < 0.7:
                insights.append(ReviewInsight(
                    insight_id=f"{insight_id_base}_risk_high",
                    dimension=ReviewDimension.RISK_EXPOSURE,
                    insight_type="risk",
                    title="风险暴露水平偏高",
                    description=f"风险暴露得分{risk_metrics.current_value:.2f}，"
                              f"存在明显风险隐患",
                    supporting_data=review_data['risk_incidents'],
                    impact_score=0.9,
                    confidence_score=risk_metrics.confidence_score,
                    recommended_actions=[
                        "立即开展风险排查",
                        "加强风险监控与预警",
                        "完善风险应对预案"
                    ],
                    generated_at=datetime.now()
                ))
        
        except Exception as e:
            logger.error(f"生成关键洞察时出错: {e}")
        
        return insights
    
    def _assess_overall_performance(self, metrics_summary: Dict[str, ReviewMetrics]) -> Dict[str, Any]:
        """
        评估整体绩效
        
        Args:
            metrics_summary: 指标摘要
            
        Returns:
            整体评估结果
        """
        try:
            # 计算总体得分
            total_score = 0
            dimension_count = 0
            
            for metric in metrics_summary.values():
                total_score += metric.current_value
                dimension_count += 1
            
            overall_score = total_score / dimension_count if dimension_count > 0 else 0.5
            
            # 评估等级
            if overall_score >= 0.8:
                performance_level = "优秀"
                color = "green"
            elif overall_score >= 0.7:
                performance_level = "良好"
                color = "blue"
            elif overall_score >= 0.6:
                performance_level = "合格"
                color = "yellow"
            else:
                performance_level = "需改进"
                color = "red"
            
            # 识别强项和弱项
            strengths = []
            weaknesses = []
            
            for dim_name, metric in metrics_summary.items():
                if metric.current_value >= 0.8:
                    strengths.append({
                        'dimension': dim_name,
                        'score': metric.current_value,
                        'improvement': metric.improvement_rate
                    })
                elif metric.current_value < 0.6:
                    weaknesses.append({
                        'dimension': dim_name,
                        'score': metric.current_value,
                        'improvement': metric.improvement_rate
                    })
            
            assessment = {
                'overall_score': overall_score,
                'performance_level': performance_level,
                'color_indicator': color,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'dimension_count': dimension_count,
                'assessment_time': datetime.now().isoformat()
            }
            
            return assessment
            
        except Exception as e:
            logger.error(f"评估整体绩效时出错: {e}")
            return {
                'overall_score': 0.5,
                'performance_level': '数据不足',
                'color_indicator': 'gray',
                'strengths': [],
                'weaknesses': [],
                'dimension_count': 0,
                'assessment_time': datetime.now().isoformat()
            }
    
    def _identify_improvement_opportunities(self, metrics_summary: Dict[str, ReviewMetrics],
                                          key_insights: List[ReviewInsight]) -> List[Dict[str, Any]]:
        """
        识别改进机会
        
        Args:
            metrics_summary: 指标摘要
            key_insights: 关键洞察
            
        Returns:
            改进机会列表
        """
        opportunities = []
        
        try:
            # 基于低分维度识别改进机会
            for dim_name, metric in metrics_summary.items():
                if metric.current_value < 0.7:
                    opportunity = {
                        'opportunity_id': f"opp_{int(time.time())}_{len(opportunities)}",
                        'dimension': dim_name,
                        'current_score': metric.current_value,
                        'target_score': 0.8,
                        'improvement_needed': 0.8 - metric.current_value,
                        'description': f"{dim_name}维度得分较低，需要重点改进",
                        'priority': 'high' if metric.current_value < 0.6 else 'medium',
                        'recommended_actions': [
                            f"制定{dim_name}专项改进计划",
                            "增加资源配置",
                            "加强过程监控与反馈"
                        ],
                        'expected_impact': 0.7,
                        'identified_at': datetime.now().isoformat()
                    }
                    opportunities.append(opportunity)
            
            # 基于洞察识别机会
            for insight in key_insights:
                if insight.insight_type == "negative":
                    opportunity = {
                        'opportunity_id': f"opp_{int(time.time())}_{len(opportunities)}",
                        'dimension': insight.dimension.value,
                        'current_score': 0.6,  # 估计值
                        'target_score': 0.8,
                        'improvement_needed': 0.2,
                        'description': insight.title,
                        'priority': 'high',
                        'recommended_actions': insight.recommended_actions,
                        'expected_impact': insight.impact_score,
                        'identified_at': datetime.now().isoformat()
                    }
                    opportunities.append(opportunity)
        
        except Exception as e:
            logger.error(f"识别改进机会时出错: {e}")
        
        return opportunities
    
    def _generate_risk_warnings(self, metrics_summary: Dict[str, ReviewMetrics],
                              key_insights: List[ReviewInsight]) -> List[Dict[str, Any]]:
        """
        生成风险预警
        
        Args:
            metrics_summary: 指标摘要
            key_insights: 关键洞察
            
        Returns:
            风险预警列表
        """
        warnings = []
        
        try:
            # 基于低分维度生成风险预警
            for dim_name, metric in metrics_summary.items():
                if metric.current_value < 0.5:
                    warning = {
                        'warning_id': f"warn_{int(time.time())}_{len(warnings)}",
                        'dimension': dim_name,
                        'risk_level': 'critical',
                        'description': f"{dim_name}维度得分极低，存在严重风险",
                        'trigger_factors': [
                            "资源严重不足",
                            "流程存在重大缺陷",
                            "外部环境剧烈变化"
                        ],
                        'potential_impact': "可能导致业务中断或重大损失",
                        'immediate_actions': [
                            f"立即成立{dim_name}风险应对小组",
                            "暂停相关高风险业务",
                            "启动应急预案"
                        ],
                        'generated_at': datetime.now().isoformat()
                    }
                    warnings.append(warning)
                elif metric.current_value < 0.6:
                    warning = {
                        'warning_id': f"warn_{int(time.time())}_{len(warnings)}",
                        'dimension': dim_name,
                        'risk_level': 'high',
                        'description': f"{dim_name}维度得分较低，存在较高风险",
                        'trigger_factors': [
                            "资源配置不足",
                            "流程效率低下",
                            "外部环境变化"
                        ],
                        'potential_impact': "可能影响业务绩效和用户满意度",
                        'immediate_actions': [
                            f"制定{dim_name}风险缓解计划",
                            "加强监控与预警",
                            "优化资源配置"
                        ],
                        'generated_at': datetime.now().isoformat()
                    }
                    warnings.append(warning)
            
            # 基于洞察生成风险预警
            for insight in key_insights:
                if insight.insight_type == "risk":
                    warning = {
                        'warning_id': f"warn_{int(time.time())}_{len(warnings)}",
                        'dimension': insight.dimension.value,
                        'risk_level': 'high',
                        'description': insight.title,
                        'trigger_factors': ["具体因素需进一步分析"],
                        'potential_impact': "存在显著风险隐患",
                        'immediate_actions': insight.recommended_actions,
                        'generated_at': datetime.now().isoformat()
                    }
                    warnings.append(warning)
        
        except Exception as e:
            logger.error(f"生成风险预警时出错: {e}")
        
        return warnings
    
    def export_review_report(self, report: DailyReviewReport, format: str = 'json') -> str:
        """
        导出复盘报告
        
        Args:
            report: 每日复盘报告
            format: 导出格式 (json, markdown, html)
            
        Returns:
            导出内容
        """
        if format == 'json':
            return report.to_json()
        elif format == 'markdown':
            return self._convert_report_to_markdown(report)
        elif format == 'html':
            return self._convert_report_to_html(report)
        else:
            logger.warning(f"不支持的导出格式: {format}，默认使用JSON")
            return report.to_json()
    
    def _convert_report_to_markdown(self, report: DailyReviewReport) -> str:
        """将报告转换为Markdown格式"""
        lines = []
        
        # 标题
        lines.append(f"# 每日复盘报告")
        lines.append(f"报告ID: {report.report_id}")
        lines.append(f"复盘周期: {report.review_period['start']} 至 {report.review_period['end']}")
        lines.append(f"生成时间: {report.generated_at}")
        lines.append(f"生成节点: {report.generated_by}")
        lines.append("")
        
        # 整体评估
        assessment = report.overall_assessment
        lines.append("## 整体绩效评估")
        lines.append(f"- **综合得分**: {assessment['overall_score']:.2f}/1.0")
        lines.append(f"- **绩效等级**: {assessment['performance_level']}")
        lines.append("")
        
        # 强项与弱项
        if assessment['strengths']:
            lines.append("### 强项")
            for strength in assessment['strengths']:
                lines.append(f"- **{strength['dimension']}**: {strength['score']:.2f} "
                           f"(改进: {strength['improvement']:.1%})")
            lines.append("")
        
        if assessment['weaknesses']:
            lines.append("### 需改进项")
            for weakness in assessment['weaknesses']:
                lines.append(f"- **{weakness['dimension']}**: {weakness['score']:.2f} "
                           f"(改进: {weakness['improvement']:.1%})")
            lines.append("")
        
        # 关键洞察
        if report.key_insights:
            lines.append("## 关键洞察")
            for insight in report.key_insights:
                lines.append(f"### {insight.title}")
                lines.append(f"**维度**: {insight.dimension.value}")
                lines.append(f"**类型**: {insight.insight_type}")
                lines.append(f"**描述**: {insight.description}")
                lines.append(f"**影响评分**: {insight.impact_score:.2f}")
                lines.append(f"**置信度**: {insight.confidence_score:.2f}")
                lines.append("**建议行动**:")
                for action in insight.recommended_actions:
                    lines.append(f"- {action}")
                lines.append("")
        
        # 改进机会
        if report.improvement_opportunities:
            lines.append("## 改进机会")
            for opp in report.improvement_opportunities:
                lines.append(f"### {opp['description']}")
                lines.append(f"- **当前得分**: {opp['current_score']:.2f}")
                lines.append(f"- **目标得分**: {opp['target_score']:.2f}")
                lines.append(f"- **优先级**: {opp['priority']}")
                lines.append(f"- **预期影响**: {opp['expected_impact']:.2f}")
                lines.append("**推荐行动**:")
                for action in opp['recommended_actions']:
                    lines.append(f"  - {action}")
                lines.append("")
        
        # 风险预警
        if report.risk_warnings:
            lines.append("## 风险预警")
            for warn in report.risk_warnings:
                lines.append(f"### {warn['description']}")
                lines.append(f"- **风险等级**: {warn['risk_level']}")
                lines.append(f"- **触发因素**:")
                for factor in warn['trigger_factors']:
                    lines.append(f"  - {factor}")
                lines.append(f"- **潜在影响**: {warn['potential_impact']}")
                lines.append("**立即行动**:")
                for action in warn['immediate_actions']:
                    lines.append(f"  - {action}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _convert_report_to_html(self, report: DailyReviewReport) -> str:
        """将报告转换为HTML格式"""
        markdown_content = self._convert_report_to_markdown(report)
        
        # 简化的HTML转换
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日复盘报告 - {report.report_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                line-height: 1.6; margin: 0; padding: 20px; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        .overall-score {{ font-size: 24px; font-weight: bold; margin: 20px 0; }}
        .score-green {{ color: #2ecc71; }}
        .score-blue {{ color: #3498db; }}
        .score-yellow {{ color: #f39c12; }}
        .score-red {{ color: #e74c3c; }}
        .insight-box {{ border-left: 4px solid; padding: 15px; margin: 15px 0; background: #f8f9fa; }}
        .insight-positive {{ border-color: #2ecc71; }}
        .insight-negative {{ border-color: #e74c3c; }}
        .insight-risk {{ border-color: #f39c12; }}
        .opportunity-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0; }}
        .risk-warning {{ border: 2px solid #e74c3c; border-radius: 8px; padding: 15px; margin: 15px 0; background: #ffeaea; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>每日复盘报告</h1>
        <p><strong>报告ID:</strong> {report.report_id}</p>
        <p><strong>复盘周期:</strong> {report.review_period['start']} 至 {report.review_period['end']}</p>
        <p><strong>生成时间:</strong> {report.generated_at}</p>
        <p><strong>生成节点:</strong> {report.generated_by}</p>
        
        <div class="overall-score score-{report.overall_assessment['color_indicator']}">
            综合得分: {report.overall_assessment['overall_score']:.2f}/1.0 
            ({report.overall_assessment['performance_level']})
        </div>
        
        <div id="content">
            {self._markdown_to_html(markdown_content)}
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _markdown_to_html(self, markdown: str) -> str:
        """简化的Markdown转HTML（仅支持基本语法）"""
        lines = markdown.split('\n')
        html_lines = []
        in_list = False
        
        for line in lines:
            if line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('- '):
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                html_lines.append(f'<li>{line[2:]}</li>')
            elif line.strip() == '':
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append('<br>')
            elif line.startswith('**') and line.endswith('**'):
                content = line[2:-2]
                html_lines.append(f'<strong>{content}</strong>')
            else:
                html_lines.append(f'<p>{line}</p>')
        
        if in_list:
            html_lines.append('</ul>')
        
        return '\n'.join(html_lines)


if __name__ == "__main__":
    # 测试复盘引擎
    from .config_manager import SelfEvolutionConfig
    
    config = SelfEvolutionConfig()
    engine = DailyReviewEngine(config)
    
    # 执行复盘
    report = engine.execute_daily_review()
    
    print("每日复盘报告生成完成")
    print(f"报告ID: {report.report_id}")
    print(f"整体得分: {report.overall_assessment['overall_score']:.2f}")
    
    # 导出JSON
    json_output = engine.export_review_report(report, 'json')
    print(f"报告长度: {len(json_output)} 字符")