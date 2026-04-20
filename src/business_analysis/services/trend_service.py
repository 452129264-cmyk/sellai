"""
趋势分析服务
提供行业风口识别、风险预警、趋势预测等综合服务
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..engine.trend_predictor import TrendPredictor
from ..models.data_models import (
    TrendAnalysisRequest, TrendAnalysisResult,
    GrowthTrend, RiskLevel
)

logger = logging.getLogger(__name__)


class TrendAnalysisService:
    """趋势分析服务"""
    
    def __init__(self):
        """初始化趋势分析服务"""
        self.predictor = TrendPredictor()
        
        logger.info("趋势分析服务初始化完成")
    
    def analyze_market_trends(self, industry_ids: List[str], 
                             timeframe: str = "1y") -> TrendAnalysisResult:
        """
        分析市场趋势
        
        Args:
            industry_ids: 行业ID列表
            timeframe: 时间范围
            
        Returns:
            趋势分析结果
        """
        request = TrendAnalysisRequest(
            industry_ids=industry_ids,
            timeframe=timeframe,
            analysis_type="market_trends",
            include_forecast=True
        )
        
        return self.predictor.analyze_trend(request)
    
    def identify_hot_opportunities(self, industry_ids: List[str],
                                  min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """
        识别热门机会
        
        Args:
            industry_ids: 行业ID列表
            min_confidence: 最小置信度
            
        Returns:
            热门机会列表
        """
        all_opportunities = []
        
        for industry_id in industry_ids:
            try:
                # 分析趋势
                request = TrendAnalysisRequest(
                    industry_ids=[industry_id],
                    timeframe="6m",
                    analysis_type="opportunity_identification",
                    include_forecast=True
                )
                
                result = self.predictor.analyze_trend(request)
                
                # 筛选高置信度机会
                for trend in result.emerging_trends:
                    if trend.get("confidence", 0) >= min_confidence:
                        opportunity = {
                            "industry_id": industry_id,
                            "opportunity_name": trend.get("name"),
                            "description": trend.get("description"),
                            "growth_potential": trend.get("growth_potential"),
                            "time_to_market": trend.get("time_to_market"),
                            "investment_required": trend.get("investment_required"),
                            "confidence": trend.get("confidence"),
                            "key_players": trend.get("key_players", []),
                            "risk_assessment": self._assess_opportunity_risk(trend)
                        }
                        all_opportunities.append(opportunity)
                        
            except Exception as e:
                logger.error(f"识别行业{industry_id}机会失败: {e}")
                continue
        
        # 按置信度和增长潜力排序
        all_opportunities.sort(
            key=lambda x: (x["confidence"], 
                          self._growth_potential_score(x["growth_potential"])),
            reverse=True
        )
        
        return all_opportunities[:20]  # 只返回前20个机会
    
    def _assess_opportunity_risk(self, trend: Dict[str, Any]) -> Dict[str, Any]:
        """评估机会风险"""
        risk_score = 0
        risk_factors = []
        
        # 基于增长潜力评估
        growth_potential = trend.get("growth_potential", "medium")
        if growth_potential == "very_high":
            risk_score += 3  # 高风险但高回报
            risk_factors.append("极高增长潜力伴随高风险")
        elif growth_potential == "high":
            risk_score += 2
            risk_factors.append("高增长潜力伴随中等风险")
        
        # 基于市场时间评估
        time_to_market = trend.get("time_to_market", "mid_term")
        if time_to_market == "long_term":
            risk_score += 2
            risk_factors.append("长期市场窗口存在不确定性")
        elif time_to_market == "short_term":
            risk_score -= 1  # 短期机会风险较低
        
        # 基于投资需求评估
        investment_required = trend.get("investment_required", "medium")
        if investment_required == "high":
            risk_score += 2
            risk_factors.append("高投资需求增加财务风险")
        
        # 确定风险等级
        if risk_score <= 2:
            risk_level = RiskLevel.LOW
        elif risk_score <= 4:
            risk_level = RiskLevel.MEDIUM
        elif risk_score <= 6:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "mitigation_strategies": self._generate_mitigation_strategies(risk_level)
        }
    
    def _growth_potential_score(self, growth_potential: str) -> int:
        """增长潜力评分"""
        scores = {
            "very_high": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return scores.get(growth_potential, 2)
    
    def _generate_mitigation_strategies(self, risk_level: RiskLevel) -> List[str]:
        """生成风险缓解策略"""
        strategies = []
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            strategies.append("分阶段投资，降低初期投入风险")
            strategies.append("建立风险储备金，应对市场波动")
            strategies.append("多元化市场布局，分散风险")
            strategies.append("建立实时监控机制，及时调整策略")
        elif risk_level == RiskLevel.MEDIUM:
            strategies.append("进行试点项目，验证市场可行性")
            strategies.append("建立灵活的运营模式，适应变化")
            strategies.append("加强市场研究和客户反馈收集")
        else:  # LOW
            strategies.append("保持市场敏感性，关注新兴趋势")
            strategies.append("建立持续改进机制")
        
        return strategies
    
    def generate_risk_warnings(self, industry_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        生成风险警告
        
        Args:
            industry_ids: 行业ID列表
            
        Returns:
            风险警告
        """
        warnings_by_industry = {}
        
        for industry_id in industry_ids:
            try:
                # 分析趋势
                request = TrendAnalysisRequest(
                    industry_ids=[industry_id],
                    timeframe="3m",
                    analysis_type="risk_assessment",
                    include_forecast=True
                )
                
                result = self.predictor.analyze_trend(request)
                
                # 处理风险警告
                industry_warnings = []
                for warning in result.risk_warnings:
                    processed_warning = {
                        "type": warning.get("type"),
                        "severity": warning.get("level").value,
                        "description": warning.get("description"),
                        "indicators": warning.get("indicators", []),
                        "confidence": warning.get("confidence", 0.7),
                        "suggested_actions": warning.get("suggested_actions", []),
                        "monitoring_metrics": self._get_monitoring_metrics(warning.get("type"))
                    }
                    industry_warnings.append(processed_warning)
                
                warnings_by_industry[industry_id] = industry_warnings
                
            except Exception as e:
                logger.error(f"生成行业{industry_id}风险警告失败: {e}")
                continue
        
        return warnings_by_industry
    
    def _get_monitoring_metrics(self, risk_type: str) -> List[str]:
        """获取监控指标"""
        metrics_map = {
            "market_saturation": [
                "行业增长率",
                "价格竞争强度",
                "市场集中度变化",
                "新进入者数量"
            ],
            "technology_disruption": [
                "研发投入增长率",
                "专利申请数量",
                "新技术采用率",
                "颠覆性创新出现频率"
            ],
            "policy_risk": [
                "监管政策变动频率",
                "行业合规成本变化",
                "政府补贴政策调整",
                "国际贸易政策影响"
            ],
            "economic_cycle": [
                "GDP增长率",
                "通货膨胀率",
                "利率变化",
                "消费者信心指数"
            ]
        }
        
        return metrics_map.get(risk_type, ["通用市场指标"])
    
    def predict_industry_performance(self, industry_ids: List[str],
                                    prediction_period: str = "1y") -> Dict[str, Dict[str, Any]]:
        """
        预测行业表现
        
        Args:
            industry_ids: 行业ID列表
            prediction_period: 预测周期
            
        Returns:
            行业表现预测
        """
        predictions = {}
        
        for industry_id in industry_ids:
            try:
                # 分析趋势
                request = TrendAnalysisRequest(
                    industry_ids=[industry_id],
                    timeframe=prediction_period,
                    analysis_type="performance_prediction",
                    include_forecast=True
                )
                
                result = self.predictor.analyze_trend(request)
                
                # 提取预测数据
                if result.forecasts and result.forecasts.get("forecast_available", False):
                    forecast = result.forecasts
                    
                    # 生成综合预测
                    prediction = {
                        "industry_id": industry_id,
                        "prediction_period": prediction_period,
                        "growth_forecast": {
                            "short_term": forecast.get("short_term", {}),
                            "medium_term": forecast.get("medium_term", {}),
                            "long_term": forecast.get("long_term", {})
                        },
                        "risk_assessment": {
                            "level": RiskLevel.MEDIUM.value,
                            "factors": [w.get("type") for w in result.risk_warnings[:3]]
                        },
                        "opportunity_indicators": [
                            {
                                "name": trend.get("name"),
                                "confidence": trend.get("confidence")
                            }
                            for trend in result.emerging_trends[:3]
                        ],
                        "recommendations": self._generate_performance_recommendations(
                            forecast, result.risk_warnings
                        ),
                        "confidence": forecast.get("confidence", 0.7),
                        "last_updated": datetime.now().isoformat()
                    }
                    
                    predictions[industry_id] = prediction
                    
            except Exception as e:
                logger.error(f"预测行业{industry_id}表现失败: {e}")
                continue
        
        return predictions
    
    def _generate_performance_recommendations(self, forecast: Dict[str, Any],
                                             risk_warnings: List[Dict[str, Any]]) -> List[str]:
        """生成表现建议"""
        recommendations = []
        
        # 基于增长预测
        growth_rates = []
        if forecast.get("short_term", {}).get("growth_rate"):
            growth_rates.append(forecast["short_term"]["growth_rate"])
        if forecast.get("medium_term", {}).get("growth_rate"):
            growth_rates.append(forecast["medium_term"]["growth_rate"])
        
        if growth_rates:
            avg_growth = sum(growth_rates) / len(growth_rates)
            
            if avg_growth > 15:
                recommendations.append("积极扩大市场份额，抢占增长红利")
            elif avg_growth > 5:
                recommendations.append("稳健扩张，优化运营效率")
            else:
                recommendations.append("聚焦核心业务，控制成本，等待市场转机")
        
        # 基于风险等级
        if risk_warnings:
            high_risk_count = sum(1 for w in risk_warnings 
                                 if w.get("level") in [RiskLevel.HIGH, RiskLevel.CRITICAL])
            
            if high_risk_count >= 3:
                recommendations.append("建立全面风险管理体系，分散投资风险")
            elif high_risk_count >= 1:
                recommendations.append("加强市场监测，制定应急预案")
        
        # 通用建议
        recommendations.append("持续关注行业创新和技术发展")
        recommendations.append("建立灵活的组织结构，适应市场变化")
        recommendations.append("加强人才培养和技术储备")
        
        return recommendations
    
    def monitor_early_signals(self, industry_ids: List[str],
                             monitoring_window: str = "1m") -> Dict[str, List[Dict[str, Any]]]:
        """
        监控早期信号
        
        Args:
            industry_ids: 行业ID列表
            monitoring_window: 监控窗口
            
        Returns:
            早期信号监控结果
        """
        signals_by_industry = {}
        
        for industry_id in industry_ids:
            try:
                # 分析趋势
                request = TrendAnalysisRequest(
                    industry_ids=[industry_id],
                    timeframe=monitoring_window,
                    analysis_type="signal_monitoring",
                    include_forecast=False
                )
                
                result = self.predictor.analyze_trend(request)
                
                # 处理早期信号
                industry_signals = []
                for signal in result.early_signals:
                    processed_signal = {
                        "signal_type": signal.get("type"),
                        "description": signal.get("description"),
                        "confidence": signal.get("confidence", 0.6),
                        "severity": signal.get("severity", "medium"),
                        "detected_at": datetime.now().isoformat(),
                        "recommended_actions": self._generate_signal_actions(signal.get("type"))
                    }
                    industry_signals.append(processed_signal)
                
                signals_by_industry[industry_id] = industry_signals
                
            except Exception as e:
                logger.error(f"监控行业{industry_id}早期信号失败: {e}")
                continue
        
        return signals_by_industry
    
    def _generate_signal_actions(self, signal_type: str) -> List[str]:
        """生成信号行动"""
        actions_map = {
            "positive_breakout": [
                "确认突破的有效性",
                "考虑增加投资或扩大业务",
                "监控后续发展，适时调整策略"
            ],
            "negative_breakout": [
                "评估风险程度",
                "考虑减少投资或收缩业务",
                "制定风险缓解计划"
            ],
            "trend_change": [
                "分析变化原因",
                "调整业务策略以适应新趋势",
                "加强市场监测，捕捉新机会"
            ]
        }
        
        return actions_map.get(signal_type, ["保持监测，谨慎行动"])
    
    def generate_trend_report(self, industry_ids: List[str],
                             report_period: str = "1y") -> Dict[str, Any]:
        """
        生成趋势报告
        
        Args:
            industry_ids: 行业ID列表
            report_period: 报告周期
            
        Returns:
            趋势报告
        """
        # 收集分析数据
        trend_analysis = self.analyze_market_trends(industry_ids, report_period)
        hot_opportunities = self.identify_hot_opportunities(industry_ids)
        risk_warnings = self.generate_risk_warnings(industry_ids)
        predictions = self.predict_industry_performance(industry_ids, "6m")
        
        # 生成报告
        report = {
            "report_type": "comprehensive_trend_analysis",
            "generated_at": datetime.now().isoformat(),
            "report_period": report_period,
            "industries_analyzed": industry_ids,
            
            "executive_summary": {
                "total_industries": len(industry_ids),
                "emerging_trends_count": len(trend_analysis.emerging_trends),
                "high_risk_industries": sum(
                    1 for industry_id, warnings in risk_warnings.items()
                    if any(w.get("severity") in ["high", "critical"] for w in warnings)
                ),
                "key_opportunities": len(hot_opportunities)
            },
            
            "trend_analysis": {
                "growth_trends": trend_analysis.growth_trends,
                "momentum_scores": trend_analysis.momentum_scores,
                "volatility_scores": trend_analysis.volatility_scores
            },
            
            "opportunity_landscape": {
                "top_opportunities": hot_opportunities[:10],
                "opportunity_distribution": self._analyze_opportunity_distribution(hot_opportunities)
            },
            
            "risk_assessment": {
                "risk_by_industry": risk_warnings,
                "overall_risk_profile": self._assess_overall_risk(risk_warnings)
            },
            
            "performance_forecast": {
                "predictions": predictions,
                "forecast_confidence": self._calculate_forecast_confidence(predictions)
            },
            
            "strategic_recommendations": {
                "investment_priorities": self._identify_investment_priorities(hot_opportunities),
                "risk_management_strategies": self._generate_risk_management_strategies(risk_warnings),
                "innovation_focus_areas": self._identify_innovation_focus_areas(trend_analysis.emerging_trends)
            },
            
            "monitoring_indicators": {
                "key_metrics": self._get_key_monitoring_metrics(),
                "early_warning_signals": self._get_early_warning_indicators()
            }
        }
        
        return report
    
    def _analyze_opportunity_distribution(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析机会分布"""
        distribution = {
            "by_growth_potential": {
                "very_high": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "by_time_to_market": {
                "short_term": 0,
                "mid_term": 0,
                "long_term": 0
            },
            "by_investment_required": {
                "low": 0,
                "medium": 0,
                "high": 0
            }
        }
        
        for opportunity in opportunities:
            # 增长潜力分布
            growth = opportunity.get("growth_potential", "medium")
            if growth in distribution["by_growth_potential"]:
                distribution["by_growth_potential"][growth] += 1
            
            # 市场时间分布
            time = opportunity.get("time_to_market", "mid_term")
            if time in distribution["by_time_to_market"]:
                distribution["by_time_to_market"][time] += 1
            
            # 投资需求分布
            investment = opportunity.get("investment_required", "medium")
            if investment in distribution["by_investment_required"]:
                distribution["by_investment_required"][investment] += 1
        
        return distribution
    
    def _assess_overall_risk(self, risk_warnings: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """评估总体风险"""
        total_industries = len(risk_warnings)
        if total_industries == 0:
            return {"level": "low", "score": 0}
        
        risk_score = 0
        high_risk_count = 0
        
        for industry_id, warnings in risk_warnings.items():
            industry_risk = 0
            for warning in warnings:
                severity = warning.get("severity", "medium")
                if severity == "critical":
                    industry_risk += 3
                elif severity == "high":
                    industry_risk += 2
                elif severity == "medium":
                    industry_risk += 1
            
            risk_score += industry_risk
            
            if industry_risk >= 4:  # 高风险行业阈值
                high_risk_count += 1
        
        # 计算平均风险
        avg_risk = risk_score / total_industries
        
        # 确定总体风险等级
        if avg_risk <= 2:
            risk_level = "low"
        elif avg_risk <= 3:
            risk_level = "medium"
        elif avg_risk <= 4:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        return {
            "level": risk_level,
            "score": round(avg_risk, 2),
            "high_risk_industries": high_risk_count,
            "high_risk_percentage": round(high_risk_count / total_industries * 100, 2) if total_industries > 0 else 0
        }
    
    def _calculate_forecast_confidence(self, predictions: Dict[str, Dict[str, Any]]) -> float:
        """计算预测置信度"""
        if not predictions:
            return 0.0
        
        confidences = [pred.get("confidence", 0.7) for pred in predictions.values()]
        return sum(confidences) / len(confidences)
    
    def _identify_investment_priorities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别投资优先级"""
        priorities = []
        
        for opp in opportunities[:5]:  # 只考虑前5个机会
            priority = {
                "industry_id": opp.get("industry_id"),
                "opportunity_name": opp.get("opportunity_name"),
                "priority_score": self._calculate_priority_score(opp),
                "investment_timing": opp.get("time_to_market"),
                "expected_roi": self._estimate_roi(opp),
                "risk_adjusted_return": self._calculate_risk_adjusted_return(opp)
            }
            priorities.append(priority)
        
        # 按优先级评分排序
        priorities.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return priorities
    
    def _calculate_priority_score(self, opportunity: Dict[str, Any]) -> float:
        """计算优先级评分"""
        score = 0
        
        # 增长潜力权重
        growth_weights = {
            "very_high": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        
        # 置信度权重
        confidence = opportunity.get("confidence", 0.7)
        
        # 风险调整
        risk_score = opportunity.get("risk_assessment", {}).get("risk_score", 0)
        risk_factor = max(0.5, 1 - risk_score / 10)  # 风险越高，因子越低
        
        growth = opportunity.get("growth_potential", "medium")
        growth_weight = growth_weights.get(growth, 2)
        
        score = growth_weight * confidence * risk_factor
        
        return round(score, 2)
    
    def _estimate_roi(self, opportunity: Dict[str, Any]) -> Dict[str, float]:
        """估算投资回报率"""
        growth = opportunity.get("growth_potential", "medium")
        investment = opportunity.get("investment_required", "medium")
        
        # 简化的ROI估算模型
        roi_baseline = {
            ("very_high", "low"): 5.0,
            ("very_high", "medium"): 4.0,
            ("very_high", "high"): 3.0,
            ("high", "low"): 4.0,
            ("high", "medium"): 3.0,
            ("high", "high"): 2.5,
            ("medium", "low"): 3.0,
            ("medium", "medium"): 2.0,
            ("medium", "high"): 1.5,
            ("low", "low"): 2.0,
            ("low", "medium"): 1.5,
            ("low", "high"): 1.2
        }
        
        baseline = roi_baseline.get((growth, investment), 2.0)
        
        # 基于置信度调整
        confidence = opportunity.get("confidence", 0.7)
        adjusted = baseline * (0.5 + confidence / 2)
        
        return {
            "baseline_roi": baseline,
            "confidence_adjusted_roi": round(adjusted, 2),
            "expected_payback_period": round(1 / adjusted, 2) if adjusted > 0 else float('inf')
        }
    
    def _calculate_risk_adjusted_return(self, opportunity: Dict[str, Any]) -> float:
        """计算风险调整后回报"""
        roi_data = self._estimate_roi(opportunity)
        roi = roi_data["confidence_adjusted_roi"]
        
        # 风险因子（风险越高，调整越大）
        risk_score = opportunity.get("risk_assessment", {}).get("risk_score", 0)
        risk_factor = 1 / (1 + risk_score / 5)  # 风险分5-10，因子0.5-0.33
        
        risk_adjusted_return = roi * risk_factor
        
        return round(risk_adjusted_return, 2)
    
    def _generate_risk_management_strategies(self, risk_warnings: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """生成风险管理策略"""
        strategies = []
        
        # 识别主要风险类型
        risk_types = {}
        for warnings in risk_warnings.values():
            for warning in warnings:
                risk_type = warning.get("type", "general")
                if risk_type not in risk_types:
                    risk_types[risk_type] = 0
                risk_types[risk_type] += 1
        
        # 基于风险类型生成策略
        for risk_type, count in sorted(risk_types.items(), key=lambda x: x[1], reverse=True):
            if risk_type == "market_saturation":
                strategies.append("实施差异化战略，避免同质化竞争")
            elif risk_type == "technology_disruption":
                strategies.append("建立技术监测机制，及时应对技术变革")
            elif risk_type == "policy_risk":
                strategies.append("加强政府关系管理，保持政策敏感性")
            elif risk_type == "economic_cycle":
                strategies.append("建立反周期投资策略，平滑经济波动影响")
        
        # 通用策略
        strategies.append("建立多元化投资组合，分散风险")
        strategies.append("定期进行风险评估和压力测试")
        strategies.append("建立应急预案和快速响应机制")
        
        return strategies
    
    def _identify_innovation_focus_areas(self, emerging_trends: List[Dict[str, Any]]) -> List[str]:
        """识别创新重点领域"""
        focus_areas = []
        
        # 按趋势类型分类
        trend_categories = {}
        for trend in emerging_trends:
            name = trend.get("name", "")
            description = trend.get("description", "")
            
            # 简化的分类逻辑
            if "AI" in name or "人工智能" in description:
                category = "人工智能"
            elif "区块链" in name or "加密货币" in description:
                category = "区块链"
            elif "新能源" in name or "可持续发展" in description:
                category = "绿色科技"
            elif "远程" in name or "数字" in description:
                category = "数字健康"
            elif "电商" in name or "在线" in description:
                category = "电子商务"
            else:
                category = "通用科技"
            
            if category not in trend_categories:
                trend_categories[category] = 0
            trend_categories[category] += 1
        
        # 选择出现频率高的领域
        for category, count in sorted(trend_categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            focus_areas.append(category)
        
        return focus_areas
    
    def _get_key_monitoring_metrics(self) -> Dict[str, List[str]]:
        """获取关键监控指标"""
        return {
            "market_indicators": [
                "行业增长率",
                "市场份额变化",
                "价格趋势",
                "竞争强度"
            ],
            "financial_indicators": [
                "利润率变化",
                "投资回报率",
                "现金流状况",
                "成本结构"
            ],
            "risk_indicators": [
                "政策变动频率",
                "技术更新速度",
                "市场波动率",
                "供应链稳定性"
            ]
        }
    
    def _get_early_warning_indicators(self) -> Dict[str, List[str]]:
        """获取早期预警指标"""
        return {
            "market_saturation": [
                "新增用户增长率下降",
                "价格竞争加剧",
                "产品差异化程度降低",
                "用户满意度下降"
            ],
            "technology_disruption": [
                "新兴技术专利数量激增",
                "替代技术成本下降",
                "传统技术市场份额下降",
                "跨界竞争者出现"
            ],
            "regulatory_risk": [
                "行业监管政策密集出台",
                "合规成本显著上升",
                "市场准入门槛提高",
                "国际贸易摩擦加剧"
            ]
        }