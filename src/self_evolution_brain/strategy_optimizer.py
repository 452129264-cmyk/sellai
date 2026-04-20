#!/usr/bin/env python3
"""
策略优化器
基于复盘结果自动优化商业策略、升级认知模型、补充能力缺口
实现长期自主进化能力
"""

import json
import time
import logging
import sqlite3
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np

# 尝试导入相关模块
try:
    from src.shared_state_manager import SharedStateManager
    HAS_SHARED_STATE = True
except ImportError:
    HAS_SHARED_STATE = False
    logging.warning("shared_state_manager 模块未找到，部分功能将受限")

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """优化类型"""
    STRATEGY_REFINEMENT = "strategy_refinement"       # 策略精炼
    CAPABILITY_ENHANCEMENT = "capability_enhancement" # 能力增强
    RESOURCE_REALLOCATION = "resource_reallocation"   # 资源重分配
    RISK_MITIGATION = "risk_mitigation"               # 风险缓解
    MODEL_UPGRADE = "model_upgrade"                   # 模型升级


@dataclass
class OptimizationResult:
    """优化结果"""
    optimization_id: str
    type: OptimizationType
    target_dimension: str
    before_score: float
    after_score: float
    improvement_rate: float
    optimization_details: Dict[str, Any]
    applied_actions: List[str]
    impact_assessment: Dict[str, float]
    generated_at: datetime
    applied_at: Optional[datetime] = None
    effectiveness_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyAdjustment:
    """策略调整"""
    adjustment_id: str
    strategy_name: str
    adjustment_type: str  # reinforce, modify, abandon, introduce
    reason: str
    evidence: List[Dict[str, Any]]
    expected_impact: float
    confidence_score: float
    implementation_steps: List[str]
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityGap:
    """能力缺口"""
    gap_id: str
    capability_area: str
    current_level: float
    required_level: float
    gap_size: float
    priority: str  # critical, high, medium, low
    impact_on_performance: float
    suggested_interventions: List[str]
    identified_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StrategyOptimizer:
    """策略优化器"""
    
    def __init__(self, config, db_path: str = "data/shared_state/state.db"):
        """
        初始化策略优化器
        
        Args:
            config: 配置对象
            db_path: 数据库路径
        """
        self.config = config
        self.db_path = db_path
        
        # 初始化组件
        self._init_components()
        
        # 优化历史
        self.optimization_history = []
        self.strategy_adjustments = []
        self.capability_gaps = []
        
        logger.info("策略优化器初始化完成")
    
    def _init_components(self):
        """初始化各功能组件"""
        # 共享状态管理器
        if HAS_SHARED_STATE:
            self.state_manager = SharedStateManager(self.db_path)
        else:
            self.state_manager = None
    
    def optimize_based_on_review(self, review_report) -> List[OptimizationResult]:
        """
        基于复盘报告进行优化
        
        Args:
            review_report: 每日复盘报告
            
        Returns:
            优化结果列表
        """
        logger.info("开始基于复盘报告进行策略优化")
        
        optimization_results = []
        
        try:
            # 1. 基于弱项进行策略精炼
            weaknesses = review_report.overall_assessment.get('weaknesses', [])
            for weakness in weaknesses:
                result = self._optimize_strategy_for_weakness(weakness, review_report)
                if result:
                    optimization_results.append(result)
            
            # 2. 基于风险预警进行风险缓解
            risk_warnings = review_report.risk_warnings
            for warning in risk_warnings:
                result = self._optimize_risk_mitigation(warning, review_report)
                if result:
                    optimization_results.append(result)
            
            # 3. 识别并补充能力缺口
            capability_gaps = self._identify_capability_gaps(review_report)
            for gap in capability_gaps:
                result = self._optimize_capability_enhancement(gap, review_report)
                if result:
                    optimization_results.append(result)
            
            # 4. 基于洞察进行模型升级
            key_insights = review_report.key_insights
            for insight in key_insights:
                result = self._optimize_model_upgrade(insight, review_report)
                if result:
                    optimization_results.append(result)
            
            # 5. 基于绩效数据进行资源重分配
            performance_data = review_report.metrics_summary
            result = self._optimize_resource_reallocation(performance_data, review_report)
            if result:
                optimization_results.append(result)
            
            # 保存优化历史
            self.optimization_history.extend(optimization_results)
            
            # 记录到数据库
            self._save_optimization_results(optimization_results)
            
            logger.info(f"策略优化完成，生成{len(optimization_results)}个优化结果")
            
        except Exception as e:
            logger.error(f"基于复盘报告进行优化时出错: {e}")
        
        return optimization_results
    
    def _optimize_strategy_for_weakness(self, weakness: Dict[str, Any], 
                                      review_report) -> Optional[OptimizationResult]:
        """
        针对弱项进行策略优化
        
        Args:
            weakness: 弱项信息
            review_report: 复盘报告
            
        Returns:
            优化结果
        """
        try:
            dimension = weakness.get('dimension')
            current_score = weakness.get('score', 0.5)
            improvement_rate = weakness.get('improvement', 0)
            
            # 确定优化类型
            optimization_type = OptimizationType.STRATEGY_REFINEMENT
            
            # 生成优化方案
            if dimension == 'market_trend':
                optimization_details = self._generate_market_strategy_optimization(
                    current_score, improvement_rate, review_report
                )
            elif dimension == 'business_performance':
                optimization_details = self._generate_business_strategy_optimization(
                    current_score, improvement_rate, review_report
                )
            elif dimension == 'ai_avatar_effectiveness':
                optimization_details = self._generate_ai_strategy_optimization(
                    current_score, improvement_rate, review_report
                )
            elif dimension == 'resource_utilization':
                optimization_details = self._generate_resource_strategy_optimization(
                    current_score, improvement_rate, review_report
                )
            elif dimension == 'user_satisfaction':
                optimization_details = self._generate_user_strategy_optimization(
                    current_score, improvement_rate, review_report
                )
            elif dimension == 'risk_exposure':
                optimization_details = self._generate_risk_strategy_optimization(
                    current_score, improvement_rate, review_report
                )
            else:
                optimization_details = self._generate_general_strategy_optimization(
                    dimension, current_score, improvement_rate, review_report
                )
            
            # 预估优化后得分
            estimated_improvement = self._estimate_strategy_improvement(
                optimization_details
            )
            after_score = min(1.0, current_score + estimated_improvement)
            
            # 构建优化结果
            result = OptimizationResult(
                optimization_id=f"opt_{int(time.time())}_{len(self.optimization_history)}",
                type=optimization_type,
                target_dimension=dimension,
                before_score=current_score,
                after_score=after_score,
                improvement_rate=(after_score - current_score) / current_score if current_score > 0 else 1.0,
                optimization_details=optimization_details,
                applied_actions=optimization_details.get('recommended_actions', []),
                impact_assessment={
                    'performance_impact': estimated_improvement,
                    'resource_impact': optimization_details.get('resource_impact', 0.3),
                    'time_impact': optimization_details.get('time_to_implement_days', 7)
                },
                generated_at=datetime.now()
            )
            
            logger.info(f"策略优化生成: {dimension} 预计从 {current_score:.2f} 提升到 {after_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"针对弱项进行策略优化时出错: {e}")
            return None
    
    def _generate_market_strategy_optimization(self, current_score: float, 
                                             improvement_rate: float,
                                             review_report) -> Dict[str, Any]:
        """生成市场策略优化方案"""
        market_insights = review_report.key_insights
        
        # 分析市场洞察
        market_opportunities = []
        market_risks = []
        
        for insight in market_insights:
            if insight.dimension.value == 'market_trend':
                if insight.insight_type == 'positive':
                    market_opportunities.append(insight)
                elif insight.insight_type == 'risk':
                    market_risks.append(insight)
        
        # 生成优化建议
        recommended_actions = []
        
        if market_opportunities:
            recommended_actions.append(
                f"重点把握{len(market_opportunities)}个市场机会，加大资源投入"
            )
        
        if market_risks:
            recommended_actions.append(
                f"针对{len(market_risks)}个市场风险，制定专项应对策略"
            )
        
        if current_score < 0.6:
            recommended_actions.extend([
                "加强市场数据分析频率，缩短决策周期",
                "优化市场情报收集机制，提升信息质量",
                "建立市场趋势预警系统，提前布局"
            ])
        
        if improvement_rate < 0:
            recommended_actions.append(
                "重新评估市场策略有效性，进行策略调整"
            )
        
        # 默认建议
        if not recommended_actions:
            recommended_actions = [
                "持续监测市场变化，保持策略灵活性",
                "加强竞争分析，识别差异化机会",
                "优化市场资源配置，提升投入产出比"
            ]
        
        return {
            'strategy_name': '市场拓展与趋势把握',
            'current_score': current_score,
            'improvement_rate': improvement_rate,
            'market_opportunities_count': len(market_opportunities),
            'market_risks_count': len(market_risks),
            'recommended_actions': recommended_actions,
            'resource_impact': 0.4,
            'time_to_implement_days': 14,
            'expected_performance_improvement': 0.15,
            'optimization_logic': '基于市场洞察识别机会与风险，针对性优化市场策略'
        }
    
    def _generate_business_strategy_optimization(self, current_score: float, 
                                               improvement_rate: float,
                                               review_report) -> Dict[str, Any]:
        """生成业务策略优化方案"""
        business_performance = review_report.metrics_summary.get('business_performance')
        
        # 分析业务绩效
        performance_issues = []
        if current_score < 0.7:
            performance_issues.append('整体绩效偏低')
        
        if improvement_rate < 0:
            performance_issues.append('绩效持续下降')
        
        # 生成优化建议
        recommended_actions = []
        
        if '整体绩效偏低' in performance_issues:
            recommended_actions.extend([
                "重新评估业务目标合理性，调整预期",
                "加强过程管理与指导，提升执行质量",
                "优化激励机制，提高团队积极性"
            ])
        
        if '绩效持续下降' in performance_issues:
            recommended_actions.extend([
                "深入分析绩效下降原因，制定针对性改进措施",
                "加强关键环节监控，及时发现并解决问题",
                "评估外部环境变化对业务的影响，调整策略"
            ])
        
        # 基于复盘洞察的优化
        business_insights = [i for i in review_report.key_insights 
                           if i.dimension.value == 'business_performance']
        
        for insight in business_insights:
            if insight.insight_type == 'negative':
                recommended_actions.extend(insight.recommended_actions)
        
        # 默认建议
        if not recommended_actions:
            recommended_actions = [
                "建立业务绩效监测体系，实时掌握绩效状况",
                "定期进行业务复盘，持续优化运营流程",
                "加强团队能力建设，提升整体执行能力"
            ]
        
        return {
            'strategy_name': '业务绩效提升',
            'current_score': current_score,
            'improvement_rate': improvement_rate,
            'performance_issues': performance_issues,
            'business_insights_count': len(business_insights),
            'recommended_actions': recommended_actions,
            'resource_impact': 0.3,
            'time_to_implement_days': 21,
            'expected_performance_improvement': 0.2,
            'optimization_logic': '基于业务绩效分析和复盘洞察，针对性优化业务策略'
        }
    
    def _generate_ai_strategy_optimization(self, current_score: float, 
                                         improvement_rate: float,
                                         review_report) -> Dict[str, Any]:
        """生成AI策略优化方案"""
        ai_records = review_report.metrics_summary.get('ai_avatar_effectiveness')
        
        # 分析AI效能
        ai_issues = []
        if current_score < 0.7:
            ai_issues.append('AI分身效能不足')
        
        if improvement_rate < 0.05:
            ai_issues.append('AI进化速度缓慢')
        
        # 生成优化建议
        recommended_actions = []
        
        if 'AI分身效能不足' in ai_issues:
            recommended_actions.extend([
                "优化分身训练数据质量，提升学习效果",
                "加强分身能力校准，确保任务匹配精度",
                "完善分身性能评估体系，持续优化"
            ])
        
        if 'AI进化速度缓慢' in ai_issues:
            recommended_actions.extend([
                "加速经验沉淀循环，缩短学习周期",
                "引入先进学习算法，提升进化效率",
                "加强分身间知识共享，促进集体智慧"
            ])
        
        # 基于AI洞察的优化
        ai_insights = [i for i in review_report.key_insights 
                     if i.dimension.value == 'ai_avatar_effectiveness']
        
        for insight in ai_insights:
            recommended_actions.extend(insight.recommended_actions)
        
        # 默认建议
        if not recommended_actions:
            recommended_actions = [
                "持续监控AI分身性能，及时发现并解决问题",
                "定期进行算法升级，保持技术先进性",
                "优化知识管理流程，提升经验复用效率"
            ]
        
        return {
            'strategy_name': 'AI分身效能提升',
            'current_score': current_score,
            'improvement_rate': improvement_rate,
            'ai_issues': ai_issues,
            'ai_insights_count': len(ai_insights),
            'recommended_actions': recommended_actions,
            'resource_impact': 0.5,
            'time_to_implement_days': 30,
            'expected_performance_improvement': 0.25,
            'optimization_logic': '基于AI分身效能分析和洞察，针对性优化AI策略'
        }
    
    def _generate_resource_strategy_optimization(self, current_score: float, 
                                               improvement_rate: float,
                                               review_report) -> Dict[str, Any]:
        """生成资源策略优化方案"""
        # 分析资源利用情况
        resource_issues = []
        if current_score < 0.7:
            resource_issues.append('资源利用效率偏低')
        
        if improvement_rate < 0:
            resource_issues.append('资源效率持续下降')
        
        # 生成优化建议
        recommended_actions = []
        
        if '资源利用效率偏低' in resource_issues:
            recommended_actions.extend([
                "重新评估资源分配策略，优化配置",
                "加强资源使用监控，减少浪费",
                "引入资源优化算法，提升利用效率"
            ])
        
        if '资源效率持续下降' in resource_issues:
            recommended_actions.extend([
                "深入分析效率下降原因，制定改进措施",
                "优化资源调度机制，提高响应速度",
                "评估外部因素对资源效率的影响"
            ])
        
        # 默认建议
        if not recommended_actions:
            recommended_actions = [
                "建立资源效率监测体系，实时掌握利用状况",
                "定期进行资源审计，发现优化机会",
                "加强资源管理能力建设，提升整体效率"
            ]
        
        return {
            'strategy_name': '资源利用优化',
            'current_score': current_score,
            'improvement_rate': improvement_rate,
            'resource_issues': resource_issues,
            'recommended_actions': recommended_actions,
            'resource_impact': 0.2,
            'time_to_implement_days': 14,
            'expected_performance_improvement': 0.15,
            'optimization_logic': '基于资源利用分析，针对性优化资源配置策略'
        }
    
    def _generate_user_strategy_optimization(self, current_score: float, 
                                           improvement_rate: float,
                                           review_report) -> Dict[str, Any]:
        """生成用户策略优化方案"""
        user_feedback = review_report.metrics_summary.get('user_satisfaction')
        
        # 分析用户满意度
        user_issues = []
        if current_score < 0.7:
            user_issues.append('用户满意度偏低')
        
        if improvement_rate < 0:
            user_issues.append('用户满意度持续下降')
        
        # 生成优化建议
        recommended_actions = []
        
        if '用户满意度偏低' in user_issues:
            recommended_actions.extend([
                "加强用户需求分析，提升服务匹配度",
                "优化用户体验设计，降低使用门槛",
                "完善用户反馈机制，及时响应诉求"
            ])
        
        if '用户满意度持续下降' in user_issues:
            recommended_actions.extend([
                "深入分析满意度下降原因，制定改进措施",
                "加强用户关系管理，提升用户粘性",
                "评估外部因素对用户满意度的影响"
            ])
        
        # 默认建议
        if not recommended_actions:
            recommended_actions = [
                "建立用户满意度监测体系，实时掌握用户感受",
                "定期进行用户体验评估，持续优化服务",
                "加强用户服务能力建设，提升整体满意度"
            ]
        
        return {
            'strategy_name': '用户满意度提升',
            'current_score': current_score,
            'improvement_rate': improvement_rate,
            'user_issues': user_issues,
            'recommended_actions': recommended_actions,
            'resource_impact': 0.3,
            'time_to_implement_days': 21,
            'expected_performance_improvement': 0.2,
            'optimization_logic': '基于用户满意度分析，针对性优化用户服务策略'
        }
    
    def _generate_risk_strategy_optimization(self, current_score: float, 
                                           improvement_rate: float,
                                           review_report) -> Dict[str, Any]:
        """生成风险策略优化方案"""
        risk_warnings = review_report.risk_warnings
        
        # 分析风险状况
        risk_issues = []
        if current_score < 0.6:
            risk_issues.append('风险暴露水平较高')
        
        if len(risk_warnings) > 3:
            risk_issues.append('风险预警数量偏多')
        
        # 生成优化建议
        recommended_actions = []
        
        if '风险暴露水平较高' in risk_issues:
            recommended_actions.extend([
                "加强风险识别与评估，提升风险意识",
                "完善风险控制措施，降低风险暴露",
                "建立风险应急响应机制，提高应对能力"
            ])
        
        if '风险预警数量偏多' in risk_issues:
            recommended_actions.extend([
                "深入分析风险高发原因，制定专项治理方案",
                "优化风险管理流程，提升管理效率",
                "加强风险文化建设和培训"
            ])
        
        # 基于风险预警的优化
        for warning in risk_warnings[:3]:  # 前3个高风险预警
            recommended_actions.extend(warning.get('immediate_actions', []))
        
        # 默认建议
        if not recommended_actions:
            recommended_actions = [
                "建立全面风险管理体系，覆盖各类风险",
                "定期进行风险评估与审计，持续改进",
                "加强风险管理能力建设，提升专业水平"
            ]
        
        return {
            'strategy_name': '风险控制优化',
            'current_score': current_score,
            'improvement_rate': improvement_rate,
            'risk_issues': risk_issues,
            'risk_warnings_count': len(risk_warnings),
            'recommended_actions': recommended_actions,
            'resource_impact': 0.4,
            'time_to_implement_days': 28,
            'expected_performance_improvement': 0.25,
            'optimization_logic': '基于风险分析和预警，针对性优化风险管理策略'
        }
    
    def _generate_general_strategy_optimization(self, dimension: str, 
                                              current_score: float, 
                                              improvement_rate: float,
                                              review_report) -> Dict[str, Any]:
        """生成通用策略优化方案"""
        return {
            'strategy_name': f'{dimension}优化',
            'current_score': current_score,
            'improvement_rate': improvement_rate,
            'recommended_actions': [
                f"加强{dimension}维度分析与监控",
                f"制定{dimension}专项改进计划",
                f"优化{dimension}相关资源配置",
                f"建立{dimension}持续改进机制"
            ],
            'resource_impact': 0.3,
            'time_to_implement_days': 21,
            'expected_performance_improvement': 0.15,
            'optimization_logic': f'基于{dimension}维度分析，针对性优化相关策略'
        }
    
    def _estimate_strategy_improvement(self, optimization_details: Dict[str, Any]) -> float:
        """预估策略改进效果"""
        base_improvement = optimization_details.get('expected_performance_improvement', 0.1)
        
        # 考虑资源投入影响
        resource_impact = optimization_details.get('resource_impact', 0.3)
        resource_factor = 1.0 + resource_impact * 0.5  # 资源投入越多，效果越好
        
        # 考虑实施时间影响
        time_to_implement = optimization_details.get('time_to_implement_days', 14)
        time_factor = 1.0 - (time_to_implement / 30) * 0.2  # 时间越长，短期效果越差
        
        # 考虑推荐行动数量
        actions_count = len(optimization_details.get('recommended_actions', []))
        actions_factor = min(1.0 + actions_count * 0.1, 1.5)  # 行动越多，效果越好
        
        estimated_improvement = base_improvement * resource_factor * time_factor * actions_factor
        
        # 添加随机性（±20%）
        random_factor = 0.8 + random.random() * 0.4
        estimated_improvement *= random_factor
        
        return min(estimated_improvement, 0.5)  # 最大改进0.5
    
    def _optimize_risk_mitigation(self, risk_warning: Dict[str, Any], 
                                review_report) -> Optional[OptimizationResult]:
        """
        针对风险预警进行风险缓解优化
        
        Args:
            risk_warning: 风险预警信息
            review_report: 复盘报告
            
        Returns:
            优化结果
        """
        try:
            dimension = risk_warning.get('dimension')
            risk_level = risk_warning.get('risk_level')
            
            # 确定优化类型
            optimization_type = OptimizationType.RISK_MITIGATION
            
            # 生成风险缓解方案
            optimization_details = {
                'risk_warning': risk_warning,
                'mitigation_strategy': self._generate_risk_mitigation_strategy(risk_level, dimension),
                'monitoring_plan': self._generate_risk_monitoring_plan(dimension),
                'contingency_plan': self._generate_contingency_plan(risk_level, dimension),
                'resource_requirements': self._assess_risk_mitigation_resources(risk_level)
            }
            
            # 预估风险降低效果
            risk_reduction = self._estimate_risk_reduction(risk_level, optimization_details)
            
            # 构建优化结果
            result = OptimizationResult(
                optimization_id=f"risk_opt_{int(time.time())}_{len(self.optimization_history)}",
                type=optimization_type,
                target_dimension=dimension,
                before_score=0.3 if risk_level == 'critical' else 0.5,  # 风险得分（越低越好）
                after_score=0.3 + risk_reduction,  # 风险降低
                improvement_rate=risk_reduction / 0.3 if risk_level == 'critical' else risk_reduction / 0.5,
                optimization_details=optimization_details,
                applied_actions=optimization_details.get('mitigation_strategy', {}).get('immediate_actions', []),
                impact_assessment={
                    'risk_reduction_impact': risk_reduction,
                    'resource_impact': optimization_details.get('resource_requirements', {}).get('estimated_cost', 0.3),
                    'time_to_effect_days': 7
                },
                generated_at=datetime.now()
            )
            
            logger.info(f"风险缓解优化生成: {dimension} 风险等级{risk_level}，预计降低{risk_reduction:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"针对风险预警进行优化时出错: {e}")
            return None
    
    def _generate_risk_mitigation_strategy(self, risk_level: str, dimension: str) -> Dict[str, Any]:
        """生成风险缓解策略"""
        strategies = {
            'critical': {
                'approach': '立即响应，全面控制',
                'key_actions': [
                    '成立专项应急小组',
                    '实施风险隔离措施',
                    '启动最高级别监控',
                    '制定全面恢复计划'
                ],
                'timeframe': '24小时内'
            },
            'high': {
                'approach': '重点突破，逐步化解',
                'key_actions': [
                    '制定专项治理方案',
                    '加强过程监控',
                    '优化资源配置',
                    '定期评估效果'
                ],
                'timeframe': '7天内'
            },
            'medium': {
                'approach': '系统改进，预防为主',
                'key_actions': [
                    '完善风险管理流程',
                    '加强风险识别培训',
                    '建立风险预警机制',
                    '定期风险评估'
                ],
                'timeframe': '30天内'
            },
            'low': {
                'approach': '持续监控，适时调整',
                'key_actions': [
                    '建立风险监测指标',
                    '定期风险回顾',
                    '优化风险控制措施',
                    '加强风险意识教育'
                ],
                'timeframe': '90天内'
            }
        }
        
        strategy = strategies.get(risk_level, strategies['medium'])
        
        return {
            'risk_level': risk_level,
            'dimension': dimension,
            'approach': strategy['approach'],
            'key_actions': strategy['key_actions'],
            'timeframe': strategy['timeframe'],
            'success_criteria': [
                f'{dimension}相关风险指标降低30%以上',
                '风险控制措施实施完成率100%',
                '风险监控覆盖率达到95%以上'
            ]
        }
    
    def _generate_risk_monitoring_plan(self, dimension: str) -> Dict[str, Any]:
        """生成风险监控计划"""
        return {
            'monitoring_frequency': 'daily' if dimension in ['risk_exposure', 'business_performance'] else 'weekly',
            'key_metrics': [
                f'{dimension}_score',
                f'{dimension}_improvement_rate',
                f'{dimension}_risk_incidents_count',
                f'{dimension}_warning_alerts'
            ],
            'alert_thresholds': {
                'critical_alert': 0.4,
                'high_alert': 0.6,
                'medium_alert': 0.7
            },
            'reporting_mechanism': {
                'daily_report': ['performance_dashboard', 'risk_alert_system'],
                'weekly_review': ['management_meeting', 'risk_committee'],
                'monthly_assessment': ['board_report', 'strategic_review']
            }
        }
    
    def _generate_contingency_plan(self, risk_level: str, dimension: str) -> Dict[str, Any]:
        """生成应急预案"""
        plans = {
            'critical': {
                'activation_criteria': f'{dimension}风险指标达到临界值或发生重大风险事件',
                'response_teams': ['应急指挥中心', '专业技术小组', '后勤保障团队'],
                'communication_protocol': '每小时更新风险状况，紧急情况下立即通报',
                'recovery_objectives': '24小时内控制风险扩大，72小时内恢复基本运营'
            },
            'high': {
                'activation_criteria': f'{dimension}风险指标持续恶化或出现多个风险信号',
                'response_teams': ['风险治理小组', '技术专家团队', '运营支持团队'],
                'communication_protocol': '每日更新风险状况，重要变化立即通报',
                'recovery_objectives': '7天内显著降低风险水平，30天内完成全面改进'
            }
        }
        
        return plans.get(risk_level, {
            'activation_criteria': f'{dimension}风险指标超出正常范围或出现持续恶化趋势',
            'response_teams': ['风险管理小组', '相关部门负责人'],
            'communication_protocol': '每周风险回顾，重要变化及时通报',
            'recovery_objectives': '30天内将风险指标恢复到正常水平'
        })
    
    def _assess_risk_mitigation_resources(self, risk_level: str) -> Dict[str, Any]:
        """评估风险缓解资源需求"""
        resource_levels = {
            'critical': {
                'estimated_cost': 0.8,
                'personnel_required': 10,
                'time_commitment_hours': 160,
                'priority': '最高'
            },
            'high': {
                'estimated_cost': 0.6,
                'personnel_required': 6,
                'time_commitment_hours': 80,
                'priority': '高'
            },
            'medium': {
                'estimated_cost': 0.4,
                'personnel_required': 3,
                'time_commitment_hours': 40,
                'priority': '中'
            },
            'low': {
                'estimated_cost': 0.2,
                'personnel_required': 1,
                'time_commitment_hours': 20,
                'priority': '低'
            }
        }
        
        return resource_levels.get(risk_level, resource_levels['medium'])
    
    def _estimate_risk_reduction(self, risk_level: str, optimization_details: Dict[str, Any]) -> float:
        """预估风险降低效果"""
        base_reduction = {
            'critical': 0.4,
            'high': 0.3,
            'medium': 0.2,
            'low': 0.1
        }.get(risk_level, 0.2)
        
        # 考虑策略复杂度
        strategy = optimization_details.get('mitigation_strategy', {})
        actions_count = len(strategy.get('key_actions', []))
        actions_factor = min(1.0 + actions_count * 0.1, 1.5)
        
        # 考虑资源投入
        resources = optimization_details.get('resource_requirements', {})
        cost_factor = 1.0 + resources.get('estimated_cost', 0.3) * 0.5
        
        estimated_reduction = base_reduction * actions_factor * cost_factor
        
        # 添加随机性（±15%）
        random_factor = 0.85 + random.random() * 0.3
        estimated_reduction *= random_factor
        
        return min(estimated_reduction, 0.7)  # 最大降低0.7
    
    def _identify_capability_gaps(self, review_report) -> List[CapabilityGap]:
        """
        识别能力缺口
        
        Args:
            review_report: 复盘报告
            
        Returns:
            能力缺口列表
        """
        gaps = []
        
        try:
            # 基于弱项识别能力缺口
            weaknesses = review_report.overall_assessment.get('weaknesses', [])
            
            for weakness in weaknesses:
                dimension = weakness.get('dimension')
                current_score = weakness.get('score', 0.5)
                required_score = 0.8  # 目标水平
                
                gap_size = required_score - current_score
                
                if gap_size > 0.1:  # 只关注显著缺口
                    priority = self._determine_capability_priority(gap_size, dimension)
                    
                    gap = CapabilityGap(
                        gap_id=f"gap_{int(time.time())}_{len(gaps)}",
                        capability_area=dimension,
                        current_level=current_score,
                        required_level=required_score,
                        gap_size=gap_size,
                        priority=priority,
                        impact_on_performance=self._assess_capability_impact(dimension, gap_size),
                        suggested_interventions=self._suggest_capability_interventions(dimension, gap_size),
                        identified_at=datetime.now()
                    )
                    
                    gaps.append(gap)
            
            # 保存识别的缺口
            self.capability_gaps.extend(gaps)
            
            logger.info(f"识别到{len(gaps)}个能力缺口")
            
        except Exception as e:
            logger.error(f"识别能力缺口时出错: {e}")
        
        return gaps
    
    def _determine_capability_priority(self, gap_size: float, dimension: str) -> str:
        """确定能力缺口优先级"""
        if gap_size > 0.3:
            return 'critical'
        elif gap_size > 0.2:
            return 'high'
        elif gap_size > 0.1:
            return 'medium'
        else:
            return 'low'
    
    def _assess_capability_impact(self, dimension: str, gap_size: float) -> float:
        """评估能力缺口对绩效的影响"""
        # 基于维度和缺口大小评估影响
        impact_factors = {
            'market_trend': 0.9,
            'business_performance': 1.0,
            'ai_avatar_effectiveness': 0.8,
            'resource_utilization': 0.7,
            'user_satisfaction': 0.6,
            'risk_exposure': 0.8
        }
        
        base_impact = impact_factors.get(dimension, 0.7)
        
        # 缺口越大，影响越大
        impact = base_impact * (0.5 + gap_size * 2)
        
        return min(impact, 1.0)
    
    def _suggest_capability_interventions(self, dimension: str, gap_size: float) -> List[str]:
        """建议能力提升干预措施"""
        interventions_map = {
            'market_trend': [
                "加强市场分析能力培训",
                "引入先进市场分析工具",
                "建立市场情报共享机制",
                "定期进行市场趋势研讨"
            ],
            'business_performance': [
                "优化业务流程设计",
                "加强绩效管理体系",
                "提升团队执行能力",
                "建立持续改进文化"
            ],
            'ai_avatar_effectiveness': [
                "完善分身训练体系",
                "引入先进学习算法",
                "加强分身能力评估",
                "建立知识共享平台"
            ],
            'resource_utilization': [
                "优化资源配置算法",
                "加强资源使用监控",
                "引入资源效率工具",
                "建立资源审计机制"
            ],
            'user_satisfaction': [
                "提升客户服务能力",
                "优化用户体验设计",
                "建立用户反馈闭环",
                "加强关系管理培训"
            ],
            'risk_exposure': [
                "完善风险管理体系",
                "加强风险识别培训",
                "引入风险监控工具",
                "建立应急响应机制"
            ]
        }
        
        base_interventions = interventions_map.get(dimension, [
            "制定专项能力提升计划",
            "加强相关技能培训",
            "引入专业工具和方法",
            "建立持续改进机制"
        ])
        
        # 根据缺口大小调整干预措施
        if gap_size > 0.3:
            # 重大缺口，需要强力干预
            base_interventions.insert(0, "立即成立能力提升专项小组")
            base_interventions.append("定期评估干预效果并调整策略")
        
        return base_interventions[:min(6, len(base_interventions))]  # 最多6个建议
    
    def _optimize_capability_enhancement(self, capability_gap: CapabilityGap, 
                                       review_report) -> Optional[OptimizationResult]:
        """
        针对能力缺口进行能力提升优化
        
        Args:
            capability_gap: 能力缺口信息
            review_report: 复盘报告
            
        Returns:
            优化结果
        """
        try:
            dimension = capability_gap.capability_area
            current_level = capability_gap.current_level
            gap_size = capability_gap.gap_size
            priority = capability_gap.priority
            
            # 确定优化类型
            optimization_type = OptimizationType.CAPABILITY_ENHANCEMENT
            
            # 生成能力提升方案
            optimization_details = {
                'capability_gap': capability_gap.to_dict(),
                'enhancement_strategy': self._generate_capability_enhancement_strategy(dimension, gap_size, priority),
                'training_plan': self._generate_training_plan(dimension, gap_size),
                'resource_allocation': self._assess_enhancement_resources(priority, gap_size),
                'success_metrics': self._define_capability_success_metrics(dimension)
            }
            
            # 预估能力提升效果
            expected_improvement = self._estimate_capability_improvement(gap_size, optimization_details)
            after_level = min(1.0, current_level + expected_improvement)
            
            # 构建优化结果
            result = OptimizationResult(
                optimization_id=f"cap_opt_{int(time.time())}_{len(self.optimization_history)}",
                type=optimization_type,
                target_dimension=dimension,
                before_score=current_level,
                after_score=after_level,
                improvement_rate=expected_improvement / current_level if current_level > 0 else 1.0,
                optimization_details=optimization_details,
                applied_actions=capability_gap.suggested_interventions,
                impact_assessment={
                    'capability_improvement': expected_improvement,
                    'performance_impact': capability_gap.impact_on_performance,
                    'resource_impact': optimization_details.get('resource_allocation', {}).get('estimated_cost', 0.4),
                    'time_to_improve_weeks': int(gap_size * 10)  # 粗略估算
                },
                generated_at=datetime.now()
            )
            
            logger.info(f"能力提升优化生成: {dimension} 预计从 {current_level:.2f} 提升到 {after_level:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"针对能力缺口进行优化时出错: {e}")
            return None
    
    def _generate_capability_enhancement_strategy(self, dimension: str, gap_size: float, 
                                                priority: str) -> Dict[str, Any]:
        """生成能力提升策略"""
        return {
            'dimension': dimension,
            'gap_size': gap_size,
            'priority': priority,
            'approach': '系统化能力建设与持续改进',
            'key_initiatives': [
                f"制定{dimension}能力提升专项计划",
                "建立能力评估与反馈机制",
                "引入专业培训与工具支持",
                "建立持续学习与改进文化"
            ],
            'implementation_phases': [
                {"phase": "评估诊断", "duration_weeks": 2, "key_output": "能力现状评估报告"},
                {"phase": "方案设计", "duration_weeks": 3, "key_output": "能力提升实施方案"},
                {"phase": "试点实施", "duration_weeks": 4, "key_output": "试点效果评估报告"},
                {"phase": "全面推广", "duration_weeks": 8, "key_output": "能力提升总结报告"}
            ]
        }
    
    def _generate_training_plan(self, dimension: str, gap_size: float) -> Dict[str, Any]:
        """生成培训计划"""
        training_topics = {
            'market_trend': [
                "市场分析方法论",
                "竞争情报收集与分析",
                "趋势预测模型应用",
                "数据驱动的市场决策"
            ],
            'business_performance': [
                "绩效管理体系设计",
                "业务流程优化方法",
                "数据化运营管理",
                "持续改进机制建设"
            ],
            'ai_avatar_effectiveness': [
                "机器学习算法原理",
                "分身训练数据准备",
                "模型评估与优化",
                "AI伦理与合规"
            ],
            'resource_utilization': [
                "资源优化理论",
                "效率分析工具应用",
                "成本效益评估方法",
                "可持续发展资源管理"
            ],
            'user_satisfaction': [
                "用户体验设计原则",
                "客户服务技巧",
                "反馈收集与分析",
                "关系管理策略"
            ],
            'risk_exposure': [
                "全面风险管理框架",
                "风险识别与评估技术",
                "风险控制措施设计",
                "应急响应与恢复"
            ]
        }
        
        topics = training_topics.get(dimension, [
            "专业领域知识",
            "技能提升方法",
            "工具应用技巧",
            "最佳实践分享"
        ])
        
        return {
            'target_audience': f"{dimension}相关岗位人员",
            'training_topics': topics,
            'delivery_methods': ["线上课程", "工作坊", "实战演练", "导师指导"],
            'duration': f"{int(gap_size * 20)}小时",  # 粗略估算
            'success_criteria': [
                f"{dimension}能力评估提升30%以上",
                "培训满意度达到90%以上",
                "知识应用率达到80%以上"
            ]
        }
    
    def _assess_enhancement_resources(self, priority: str, gap_size: float) -> Dict[str, Any]:
        """评估能力提升资源需求"""
        resource_levels = {
            'critical': {
                'estimated_cost': 0.9,
                'trainers_required': 3,
                'duration_weeks': 12,
                'priority': '最高'
            },
            'high': {
                'estimated_cost': 0.7,
                'trainers_required': 2,
                'duration_weeks': 8,
                'priority': '高'
            },
            'medium': {
                'estimated_cost': 0.5,
                'trainers_required': 1,
                'duration_weeks': 6,
                'priority': '中'
            },
            'low': {
                'estimated_cost': 0.3,
                'trainers_required': 1,
                'duration_weeks': 4,
                'priority': '低'
            }
        }
        
        base_resources = resource_levels.get(priority, resource_levels['medium'])
        
        # 根据缺口大小调整
        adjusted_cost = base_resources['estimated_cost'] * (1 + gap_size)
        adjusted_duration = base_resources['duration_weeks'] * (1 + gap_size * 0.5)
        
        return {
            **base_resources,
            'estimated_cost': min(adjusted_cost, 1.0),
            'duration_weeks': int(adjusted_duration),
            'gap_size_factor': gap_size
        }
    
    def _define_capability_success_metrics(self, dimension: str) -> List[Dict[str, Any]]:
        """定义能力提升成功指标"""
        metrics_map = {
            'market_trend': [
                {"metric": "market_analysis_accuracy", "target": "≥85%", "weight": 0.4},
                {"metric": "trend_prediction_timeliness", "target": "提前30天", "weight": 0.3},
                {"metric": "competitor_intelligence_quality", "target": "评分≥4.5/5", "weight": 0.3}
            ],
            'business_performance': [
                {"metric": "task_completion_rate", "target": "≥95%", "weight": 0.4},
                {"metric": "performance_score_average", "target": "≥0.8", "weight": 0.3},
                {"metric": "process_efficiency_improvement", "target": "≥20%", "weight": 0.3}
            ],
            'ai_avatar_effectiveness': [
                {"metric": "avatar_capability_score", "target": "≥0.85", "weight": 0.4},
                {"metric": "task_success_rate", "target": "≥90%", "weight": 0.3},
                {"metric": "response_time_improvement", "target": "降低30%", "weight": 0.3}
            ]
        }
        
        return metrics_map.get(dimension, [
            {"metric": "capability_assessment_score", "target": "提升30%", "weight": 0.5},
            {"metric": "skill_application_rate", "target": "≥80%", "weight": 0.5}
        ])
    
    def _estimate_capability_improvement(self, gap_size: float, 
                                       optimization_details: Dict[str, Any]) -> float:
        """预估能力提升效果"""
        base_improvement = min(gap_size * 0.8, 0.6)  # 最多能弥补80%的缺口
        
        # 考虑资源投入影响
        resources = optimization_details.get('resource_allocation', {})
        cost_factor = 0.8 + resources.get('estimated_cost', 0.5) * 0.4
        
        # 考虑实施计划影响
        strategy = optimization_details.get('enhancement_strategy', {})
        phases_count = len(strategy.get('implementation_phases', []))
        phases_factor = min(1.0 + phases_count * 0.2, 1.5)
        
        estimated_improvement = base_improvement * cost_factor * phases_factor
        
        # 添加随机性（±25%）
        random_factor = 0.75 + random.random() * 0.5
        estimated_improvement *= random_factor
        
        return min(estimated_improvement, 0.8)  # 最大提升0.8
    
    def _optimize_model_upgrade(self, key_insight, review_report) -> Optional[OptimizationResult]:
        """
        针对关键洞察进行模型升级优化
        
        Args:
            key_insight: 关键洞察信息
            review_report: 复盘报告
            
        Returns:
            优化结果
        """
        try:
            dimension = key_insight.dimension.value
            insight_type = key_insight.insight_type
            impact_score = key_insight.impact_score
            
            # 确定优化类型
            optimization_type = OptimizationType.MODEL_UPGRADE
            
            # 生成模型升级方案
            optimization_details = {
                'key_insight': key_insight.to_dict(),
                'upgrade_strategy': self._generate_model_upgrade_strategy(dimension, insight_type, impact_score),
                'implementation_plan': self._generate_model_implementation_plan(dimension, impact_score),
                'validation_plan': self._generate_model_validation_plan(dimension),
                'rollout_strategy': self._generate_rollout_strategy(impact_score)
            }
            
            # 预估模型升级效果
            expected_improvement = self._estimate_model_upgrade_improvement(impact_score, optimization_details)
            
            # 获取当前维度得分
            current_metric = review_report.metrics_summary.get(dimension)
            current_score = current_metric.current_value if current_metric else 0.5
            after_score = min(1.0, current_score + expected_improvement)
            
            # 构建优化结果
            result = OptimizationResult(
                optimization_id=f"model_opt_{int(time.time())}_{len(self.optimization_history)}",
                type=optimization_type,
                target_dimension=dimension,
                before_score=current_score,
                after_score=after_score,
                improvement_rate=expected_improvement / current_score if current_score > 0 else 1.0,
                optimization_details=optimization_details,
                applied_actions=optimization_details.get('upgrade_strategy', {}).get('key_actions', []),
                impact_assessment={
                    'model_improvement': expected_improvement,
                    'dimension_impact': impact_score,
                    'resource_impact': optimization_details.get('implementation_plan', {}).get('estimated_cost', 0.6),
                    'time_to_upgrade_weeks': 8
                },
                generated_at=datetime.now()
            )
            
            logger.info(f"模型升级优化生成: {dimension} 预计从 {current_score:.2f} 提升到 {after_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"针对关键洞察进行模型升级时出错: {e}")
            return None
    
    def _generate_model_upgrade_strategy(self, dimension: str, insight_type: str, 
                                       impact_score: float) -> Dict[str, Any]:
        """生成模型升级策略"""
        upgrade_focus = {
            'positive': "强化成功模式，扩大优势效应",
            'negative': "改进薄弱环节，提升整体性能",
            'opportunity': "增强机会识别，优化响应机制",
            'risk': "加强风险防控，提高系统韧性"
        }.get(insight_type, "系统性能优化")
        
        return {
            'dimension': dimension,
            'insight_type': insight_type,
            'impact_score': impact_score,
            'upgrade_focus': upgrade_focus,
            'key_actions': [
                f"更新{dimension}维度算法模型",
                "优化模型参数与特征工程",
                "加强模型训练与验证",
                "建立模型持续改进机制"
            ],
            'technical_approach': "集成先进机器学习算法，结合领域专业知识，构建自适应优化模型",
            'expected_outcomes': [
                f"{dimension}维度性能提升{int(impact_score * 100)}%以上",
                "模型预测准确率达到90%以上",
                "系统响应时间降低30%以上"
            ]
        }
    
    def _generate_model_implementation_plan(self, dimension: str, impact_score: float) -> Dict[str, Any]:
        """生成模型实施计划"""
        return {
            'dimension': dimension,
            'impact_score': impact_score,
            'phases': [
                {"phase": "模型设计", "duration_weeks": 2, "key_deliverables": ["需求规格", "架构设计"]},
                {"phase": "开发实现", "duration_weeks": 4, "key_deliverables": ["核心代码", "单元测试"]},
                {"phase": "测试验证", "duration_weeks": 3, "key_deliverables": ["测试报告", "性能评估"]},
                {"phase": "部署上线", "duration_weeks": 2, "key_deliverables": ["部署文档", "运维指南"]}
            ],
            'resource_requirements': {
                'data_scientists': 2,
                'software_engineers': 3,
                'domain_experts': 1,
                'estimated_cost': 0.7
            },
            'risk_mitigation': [
                "建立分阶段验证机制",
                "准备回滚方案",
                "加强监控与告警",
                "建立应急响应流程"
            ]
        }
    
    def _generate_model_validation_plan(self, dimension: str) -> Dict[str, Any]:
        """生成模型验证计划"""
        return {
            'validation_methods': [
                "交叉验证",
                "A/B测试",
                "离线评估",
                "在线监控"
            ],
            'key_metrics': [
                f"{dimension}_score",
                "prediction_accuracy",
                "response_time",
                "resource_utilization"
            ],
            'success_criteria': [
                "模型性能提升≥20%",
                "预测准确率≥85%",
                "系统稳定性≥99%",
                "用户满意度提升≥15%"
            ],
            'monitoring_plan': {
                'real_time_monitoring': ["系统健康度", "性能指标", "异常检测"],
                'periodic_review': ["每周性能分析", "每月模型评估", "季度优化规划"]
            }
        }
    
    def _generate_rollout_strategy(self, impact_score: float) -> Dict[str, Any]:
        """生成部署策略"""
        rollout_scope = 'full' if impact_score > 0.7 else 'phased'
        
        return {
            'rollout_scope': rollout_scope,
            'approach': '渐进式部署' if rollout_scope == 'phased' else '全面部署',
            'stages': [
                {"stage": "内部测试", "duration_days": 7, "coverage": "10%"},
                {"stage": "小范围试点", "duration_days": 14, "coverage": "30%"},
                {"stage": "全面推广", "duration_days": 30, "coverage": "100%"}
            ] if rollout_scope == 'phased' else [
                {"stage": "全面部署", "duration_days": 14, "coverage": "100%"}
            ],
            'rollback_plan': {
                'triggers': ["性能下降20%以上", "用户投诉率上升50%", "系统稳定性低于95%"],
                'procedures': ["立即停止新模型", "切换回旧版本", "问题分析与修复"],
                'time_target': "2小时内完成回滚"
            }
        }
    
    def _estimate_model_upgrade_improvement(self, impact_score: float, 
                                          optimization_details: Dict[str, Any]) -> float:
        """预估模型升级改进效果"""
        base_improvement = impact_score * 0.5  # 最多能实现50%的潜在影响
        
        # 考虑实施计划影响
        implementation = optimization_details.get('implementation_plan', {})
        resource_factor = 0.7 + implementation.get('resource_requirements', {}).get('estimated_cost', 0.5) * 0.6
        
        # 考虑验证计划影响
        validation = optimization_details.get('validation_plan', {})
        validation_factor = 1.0 + len(validation.get('validation_methods', [])) * 0.2
        
        estimated_improvement = base_improvement * resource_factor * validation_factor
        
        # 添加随机性（±30%）
        random_factor = 0.7 + random.random() * 0.6
        estimated_improvement *= random_factor
        
        return min(estimated_improvement, 0.7)  # 最大改进0.7
    
    def _optimize_resource_reallocation(self, performance_data: Dict[str, Any], 
                                      review_report) -> Optional[OptimizationResult]:
        """
        基于绩效数据进行资源重分配优化
        
        Args:
            performance_data: 绩效数据
            review_report: 复盘报告
            
        Returns:
            优化结果
        """
        try:
            # 分析各维度绩效表现
            dimension_scores = {}
            for dim_name, metric in performance_data.items():
                dimension_scores[dim_name] = {
                    'score': metric.current_value,
                    'improvement': metric.improvement_rate
                }
            
            # 识别资源配置机会
            allocation_analysis = self._analyze_resource_allocation(dimension_scores, review_report)
            
            # 生成资源重分配方案
            optimization_details = {
                'dimension_scores': dimension_scores,
                'allocation_analysis': allocation_analysis,
                'reallocation_plan': self._generate_reallocation_plan(allocation_analysis),
                'expected_benefits': self._estimate_reallocation_benefits(allocation_analysis),
                'implementation_guidelines': self._generate_implementation_guidelines(allocation_analysis)
            }
            
            # 预估整体绩效提升
            estimated_improvement = self._estimate_overall_performance_improvement(allocation_analysis)
            
            # 构建优化结果
            result = OptimizationResult(
                optimization_id=f"resource_opt_{int(time.time())}_{len(self.optimization_history)}",
                type=OptimizationType.RESOURCE_REALLOCATION,
                target_dimension='all',
                before_score=self._calculate_overall_score(dimension_scores),
                after_score=self._calculate_overall_score(dimension_scores) + estimated_improvement,
                improvement_rate=estimated_improvement / self._calculate_overall_score(dimension_scores) 
                               if self._calculate_overall_score(dimension_scores) > 0 else 1.0,
                optimization_details=optimization_details,
                applied_actions=optimization_details.get('reallocation_plan', {}).get('key_actions', []),
                impact_assessment={
                    'overall_improvement': estimated_improvement,
                    'resource_efficiency_gain': allocation_analysis.get('efficiency_gain', 0.2),
                    'time_to_effect_weeks': 4
                },
                generated_at=datetime.now()
            )
            
            logger.info(f"资源重分配优化生成: 预计整体绩效提升{estimated_improvement:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"基于绩效数据进行资源重分配优化时出错: {e}")
            return None
    
    def _analyze_resource_allocation(self, dimension_scores: Dict[str, Any], 
                                   review_report) -> Dict[str, Any]:
        """分析资源配置情况"""
        # 识别资源配置不合理之处
        allocation_issues = []
        
        for dim_name, scores in dimension_scores.items():
            current_score = scores['score']
            
            if current_score < 0.6:
                allocation_issues.append({
                    'dimension': dim_name,
                    'issue': '资源配置严重不足',
                    'current_score': current_score,
                    'recommended_action': f'增加{dimension}维度资源投入'
                })
            elif current_score > 0.9:
                allocation_issues.append({
                    'dimension': dim_name,
                    'issue': '可能存在资源配置过剩',
                    'current_score': current_score,
                    'recommended_action': f'评估{dimension}维度资源使用效率'
                })
        
        # 识别资源优化机会
        optimization_opportunities = []
        
        # 基于绩效差异识别优化机会
        sorted_dimensions = sorted(dimension_scores.items(), key=lambda x: x[1]['score'])
        
        if len(sorted_dimensions) >= 2:
            lowest_dim = sorted_dimensions[0]
            highest_dim = sorted_dimensions[-1]
            
            score_gap = highest_dim[1]['score'] - lowest_dim[1]['score']
            
            if score_gap > 0.3:
                optimization_opportunities.append({
                    'opportunity': f'从{highest_dim[0]}向{lowest_dim[0]}适度转移资源',
                    'rationale': f'{highest_dim[0]}绩效优异({highest_dim[1]["score"]:.2f})，'
                               f'{lowest_dim[0]}绩效偏低({lowest_dim[1]["score"]:.2f})',
                    'expected_impact': f'提升整体资源利用效率{score_gap*0.3:.1%}'
                })
        
        return {
            'allocation_issues': allocation_issues,
            'optimization_opportunities': optimization_opportunities,
            'efficiency_gain': self._calculate_efficiency_gain(allocation_issues, optimization_opportunities),
            'recommended_priority': self._determine_allocation_priority(allocation_issues)
        }
    
    def _calculate_efficiency_gain(self, allocation_issues: List[Dict[str, Any]], 
                                 optimization_opportunities: List[Dict[str, Any]]) -> float:
        """计算效率提升潜力"""
        # 基于问题和机会评估效率提升
        base_gain = 0.1
        
        # 问题越严重，提升潜力越大
        critical_issues = sum(1 for issue in allocation_issues 
                            if issue.get('current_score', 1) < 0.6)
        base_gain += critical_issues * 0.05
        
        # 机会越多，提升潜力越大
        base_gain += len(optimization_opportunities) * 0.03
        
        return min(base_gain, 0.5)
    
    def _determine_allocation_priority(self, allocation_issues: List[Dict[str, Any]]) -> List[str]:
        """确定资源配置优先级"""
        # 按问题严重程度排序
        critical_issues = [issue for issue in allocation_issues 
                          if issue.get('current_score', 1) < 0.6]
        
        priorities = []
        for issue in critical_issues:
            priorities.append(f"立即增加{issue['dimension']}资源投入")
        
        # 添加通用建议
        if not priorities:
            priorities = [
                "优化现有资源配置结构",
                "加强资源使用效率监控",
                "建立动态资源调整机制"
            ]
        
        return priorities
    
    def _generate_reallocation_plan(self, allocation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成资源重分配计划"""
        issues = allocation_analysis.get('allocation_issues', [])
        opportunities = allocation_analysis.get('optimization_opportunities', [])
        
        key_actions = []
        
        # 针对严重问题制定行动
        for issue in issues:
            if issue.get('current_score', 1) < 0.6:
                key_actions.append(issue.get('recommended_action', ''))
        
        # 基于机会制定行动
        for opp in opportunities[:2]:  # 最多2个关键机会
            key_actions.append(opp.get('opportunity', ''))
        
        # 默认行动
        if not key_actions:
            key_actions = [
                "分析各维度资源使用效率",
                "优化资源配置结构",
                "建立动态调整机制"
            ]
        
        return {
            'key_actions': key_actions,
            'implementation_steps': [
                "评估当前资源配置状况",
                "识别资源配置不合理之处",
                "制定资源优化方案",
                "实施资源重新分配",
                "监控优化效果并调整"
            ],
            'success_indicators': [
                "整体绩效提升≥15%",
                "资源使用效率提升≥20%",
                "各维度绩效均衡度改善≥10%"
            ],
            'monitoring_metrics': [
                "各维度绩效得分",
                "资源投入产出比",
                "绩效均衡度指数",
                "资源使用效率指标"
            ]
        }
    
    def _estimate_reallocation_benefits(self, allocation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """预估重分配效益"""
        efficiency_gain = allocation_analysis.get('efficiency_gain', 0.2)
        
        return {
            'performance_improvement': efficiency_gain * 0.6,
            'resource_efficiency_gain': efficiency_gain,
            'cost_reduction_potential': efficiency_gain * 0.3,
            'time_to_benefit_weeks': 8,
            'return_on_reallocation': 3.5  # 投资回报倍数
        }
    
    def _generate_implementation_guidelines(self, allocation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成实施指南"""
        return {
            'approach': '分阶段渐进式实施',
            'key_principles': [
                "数据驱动的决策",
                "渐进式调整",
                "持续监控与反馈",
                "灵活适应变化"
            ],
            'implementation_phases': [
                {"phase": "准备阶段", "duration_weeks": 2, "key_tasks": ["现状评估", "方案设计", "资源准备"]},
                {"phase": "试点阶段", "duration_weeks": 4, "key_tasks": ["小范围实施", "效果评估", "方案优化"]},
                {"phase": "推广阶段", "duration_weeks": 6, "key_tasks": ["全面推广", "过程监控", "持续改进"]}
            ],
            'risk_management': [
                "建立风险识别与评估机制",
                "准备应急预案",
                "加强过程监控",
                "建立快速响应能力"
            ],
            'success_factors': [
                "领导支持与推动",
                "团队能力与配合",
                "数据质量与可用性",
                "持续改进文化"
            ]
        }
    
    def _estimate_overall_performance_improvement(self, allocation_analysis: Dict[str, Any]) -> float:
        """预估整体绩效提升"""
        efficiency_gain = allocation_analysis.get('efficiency_gain', 0.2)
        
        # 效率增益的30%转化为绩效提升
        estimated_improvement = efficiency_gain * 0.3
        
        # 添加随机性（±25%）
        random_factor = 0.75 + random.random() * 0.5
        estimated_improvement *= random_factor
        
        return min(estimated_improvement, 0.4)  # 最大提升0.4
    
    def _calculate_overall_score(self, dimension_scores: Dict[str, Any]) -> float:
        """计算整体得分"""
        if not dimension_scores:
            return 0.5
        
        total_score = 0
        dimension_count = 0
        
        for scores in dimension_scores.values():
            total_score += scores.get('score', 0.5)
            dimension_count += 1
        
        return total_score / dimension_count if dimension_count > 0 else 0.5
    
    def _save_optimization_results(self, optimization_results: List[OptimizationResult]):
        """保存优化结果到数据库"""
        if not self.state_manager or not optimization_results:
            return
        
        try:
            conn = self.state_manager.connect()
            cursor = conn.cursor()
            
            # 创建优化结果表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimization_results (
                    optimization_id TEXT PRIMARY KEY,
                    type TEXT,
                    target_dimension TEXT,
                    before_score REAL,
                    after_score REAL,
                    improvement_rate REAL,
                    optimization_details TEXT,
                    applied_actions TEXT,
                    impact_assessment TEXT,
                    generated_at DATETIME,
                    applied_at DATETIME,
                    effectiveness_score REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入优化结果
            for result in optimization_results:
                cursor.execute("""
                    INSERT OR REPLACE INTO optimization_results 
                    (optimization_id, type, target_dimension, before_score, after_score, 
                     improvement_rate, optimization_details, applied_actions, 
                     impact_assessment, generated_at, applied_at, effectiveness_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.optimization_id,
                    result.type.value,
                    result.target_dimension,
                    result.before_score,
                    result.after_score,
                    result.improvement_rate,
                    json.dumps(result.optimization_details, default=str),
                    json.dumps(result.applied_actions, default=str),
                    json.dumps(result.impact_assessment, default=str),
                    result.generated_at.isoformat(),
                    result.applied_at.isoformat() if result.applied_at else None,
                    result.effectiveness_score
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"优化结果已保存到数据库，共{len(optimization_results)}条")
            
        except Exception as e:
            logger.error(f"保存优化结果到数据库时出错: {e}")
    
    def apply_optimization(self, optimization_result: OptimizationResult) -> bool:
        """
        应用优化结果
        
        Args:
            optimization_result: 优化结果
            
        Returns:
            应用是否成功
        """
        try:
            logger.info(f"开始应用优化结果: {optimization_result.optimization_id}")
            
            # 标记为已应用
            optimization_result.applied_at = datetime.now()
            
            # 在实际系统中应用优化措施
            success = self._implement_optimization_actions(optimization_result.applied_actions)
            
            if success:
                # 更新优化历史
                for i, opt in enumerate(self.optimization_history):
                    if opt.optimization_id == optimization_result.optimization_id:
                        self.optimization_history[i] = optimization_result
                        break
                
                # 更新数据库
                self._save_optimization_results([optimization_result])
                
                logger.info(f"优化结果应用成功: {optimization_result.optimization_id}")
                return True
            else:
                logger.warning(f"优化结果应用部分失败: {optimization_result.optimization_id}")
                return False
            
        except Exception as e:
            logger.error(f"应用优化结果时出错: {e}")
            return False
    
    def _implement_optimization_actions(self, actions: List[str]) -> bool:
        """实施优化行动"""
        # 在实际系统中实施优化行动
        # 这里应该是具体的实现逻辑
        
        # 简化实现：记录日志并返回成功
        for action in actions:
            logger.info(f"实施优化行动: {action}")
        
        return True
    
    def evaluate_optimization_effectiveness(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """
        评估优化效果
        
        Args:
            optimization_id: 优化结果ID
            
        Returns:
            效果评估结果
        """
        try:
            # 查找优化结果
            optimization_result = None
            for opt in self.optimization_history:
                if opt.optimization_id == optimization_id:
                    optimization_result = opt
                    break
            
            if not optimization_result:
                logger.warning(f"未找到优化结果: {optimization_id}")
                return None
            
            # 模拟效果评估
            effectiveness_score = self._simulate_effectiveness_evaluation(optimization_result)
            
            evaluation_result = {
                'optimization_id': optimization_id,
                'evaluation_date': datetime.now().isoformat(),
                'effectiveness_score': effectiveness_score,
                'improvement_realized': self._calculate_improvement_realized(optimization_result, effectiveness_score),
                'recommendations': self._generate_evaluation_recommendations(effectiveness_score)
            }
            
            logger.info(f"优化效果评估完成: {optimization_id}，得分: {effectiveness_score:.2f}")
            return evaluation_result
            
        except Exception as e:
            logger.error(f"评估优化效果时出错: {e}")
            return None
    
    def _simulate_effectiveness_evaluation(self, optimization_result: OptimizationResult) -> float:
        """模拟效果评估"""
        # 简化实现：基于优化类型和预估改进模拟效果
        base_score = optimization_result.improvement_rate * 0.7
        
        # 添加随机性
        random_factor = 0.6 + random.random() * 0.8
        final_score = base_score * random_factor
        
        return min(max(final_score, 0), 1)
    
    def _calculate_improvement_realized(self, optimization_result: OptimizationResult, 
                                      effectiveness_score: float) -> float:
        """计算实际实现的改进"""
        estimated_improvement = optimization_result.after_score - optimization_result.before_score
        realized_improvement = estimated_improvement * effectiveness_score
        
        return realized_improvement
    
    def _generate_evaluation_recommendations(self, effectiveness_score: float) -> List[str]:
        """生成评估建议"""
        if effectiveness_score >= 0.8:
            return [
                "优化措施效果显著，建议继续保持",
                "考虑将成功经验推广到其他领域",
                "建立长效监控机制，确保效果持续"
            ]
        elif effectiveness_score >= 0.6:
            return [
                "优化措施有一定效果，建议进一步改进",
                "分析实施过程中的问题并优化",
                "加强过程监控，及时调整措施"
            ]
        else:
            return [
                "优化措施效果不理想，建议重新评估方案",
                "深入分析失败原因，制定改进方案",
                "考虑采用替代方案或调整实施策略"
            ]
    
    def generate_optimization_report(self, optimization_results: List[OptimizationResult]) -> str:
        """
        生成优化报告
        
        Args:
            optimization_results: 优化结果列表
            
        Returns:
            报告内容（JSON格式）
        """
        report_data = {
            'report_id': f"optimization_report_{int(time.time())}_{self.config.node_id}",
            'generated_at': datetime.now().isoformat(),
            'generated_by': self.config.node_id,
            'total_optimizations': len(optimization_results),
            'optimizations_by_type': {},
            'expected_overall_improvement': 0.0,
            'key_recommendations': [],
            'optimization_details': []
        }
        
        # 统计按类型分布
        type_counts = {}
        total_improvement = 0
        
        for result in optimization_results:
            opt_type = result.type.value
            type_counts[opt_type] = type_counts.get(opt_type, 0) + 1
            
            # 计算预期改进
            improvement = result.after_score - result.before_score
            total_improvement += improvement
            
            # 添加详细信息
            report_data['optimization_details'].append({
                'id': result.optimization_id,
                'type': opt_type,
                'target': result.target_dimension,
                'before': result.before_score,
                'after': result.after_score,
                'improvement': improvement,
                'key_actions': result.applied_actions[:3]  # 前3个关键行动
            })
        
        report_data['optimizations_by_type'] = type_counts
        report_data['expected_overall_improvement'] = total_improvement / len(optimization_results) if optimization_results else 0
        
        # 生成关键建议
        report_data['key_recommendations'] = self._generate_key_recommendations(optimization_results)
        
        return json.dumps(report_data, default=str, indent=2, ensure_ascii=False)
    
    def _generate_key_recommendations(self, optimization_results: List[OptimizationResult]) -> List[str]:
        """生成关键建议"""
        recommendations = []
        
        # 基于优化类型生成建议
        type_actions = {}
        for result in optimization_results:
            opt_type = result.type.value
            if opt_type not in type_actions:
                type_actions[opt_type] = []
            type_actions[opt_type].extend(result.applied_actions)
        
        # 针对每种类型生成建议
        for opt_type, actions in type_actions.items():
            if actions:
                # 取最常见的前3个行动
                from collections import Counter
                common_actions = Counter(actions).most_common(3)
                common_text = "、".join([action for action, _ in common_actions[:2]])
                
                recommendations.append(
                    f"针对{opt_type}优化，重点实施: {common_text}等措施"
                )
        
        # 通用建议
        if not recommendations:
            recommendations = [
                "持续监控各维度绩效表现，及时发现并解决问题",
                "建立优化措施效果评估机制，持续改进",
                "加强跨维度协同，提升整体绩效水平"
            ]
        
        return recommendations[:5]  # 最多5条建议


if __name__ == "__main__":
    # 测试策略优化器
    from .config_manager import SelfEvolutionConfig
    
    # 模拟复盘报告数据
    class MockReviewReport:
        overall_assessment = {
            'weaknesses': [
                {'dimension': 'business_performance', 'score': 0.55, 'improvement': -0.1},
                {'dimension': 'user_satisfaction', 'score': 0.65, 'improvement': 0.05}
            ]
        }
        risk_warnings = [
            {'dimension': 'risk_exposure', 'risk_level': 'high'}
        ]
        key_insights = [
            MockObject(dimension=MockObject(value='business_performance'), 
                      insight_type='negative', 
                      impact_score=0.7)
        ]
        metrics_summary = {
            'business_performance': MockObject(current_value=0.55),
            'user_satisfaction': MockObject(current_value=0.65)
        }
    
    class MockObject:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    config = SelfEvolutionConfig()
    optimizer = StrategyOptimizer(config)
    
    # 模拟复盘报告
    mock_report = MockReviewReport()
    
    # 执行优化
    results = optimizer.optimize_based_on_review(mock_report)
    
    print(f"生成{len(results)}个优化结果")
    for result in results[:2]:
        print(f"- {result.type.value}: {result.target_dimension} "
              f"({result.before_score:.2f} → {result.after_score:.2f})")