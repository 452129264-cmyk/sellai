"""
利润测算服务
提供全行业精细化利润预测服务
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..engine.profit_calculator import ProfitCalculator
from ..models.data_models import (
    ProfitAnalysisRequest, ProfitAnalysisResult,
    CostStructure, PricingStrategy, RiskLevel
)

logger = logging.getLogger(__name__)


class ProfitCalculationService:
    """利润测算服务"""
    
    def __init__(self):
        """初始化利润测算服务"""
        self.calculator = ProfitCalculator()
        
        logger.info("利润测算服务初始化完成")
    
    def analyze_profit(self, request: ProfitAnalysisRequest) -> ProfitAnalysisResult:
        """
        分析利润
        
        Args:
            request: 利润分析请求
            
        Returns:
            利润分析结果
        """
        return self.calculator.analyze_profit(request)
    
    def batch_analyze_profits(self, requests: List[ProfitAnalysisRequest]) -> List[ProfitAnalysisResult]:
        """
        批量分析利润
        
        Args:
            requests: 利润分析请求列表
            
        Returns:
            利润分析结果列表
        """
        results = []
        
        for request in requests:
            try:
                result = self.calculator.analyze_profit(request)
                results.append(result)
            except Exception as e:
                logger.error(f"分析请求失败: {e}")
                # 创建错误结果
                error_result = ProfitAnalysisResult(
                    request=request,
                    estimated_total_cost=0.0,
                    cost_breakdown={},
                    cost_per_unit=0.0,
                    recommended_price=0.0,
                    competitive_price_range={},
                    gross_profit=0.0,
                    net_profit=0.0,
                    gross_margin=0.0,
                    net_margin=0.0,
                    sensitivity_analysis={},
                    break_even_point=0.0,
                    profit_risk_level=RiskLevel.CRITICAL,
                    key_risk_factors=["分析失败", str(e)],
                    confidence_score=0.0
                )
                results.append(error_result)
        
        return results
    
    def estimate_cost_structure(self, industry_id: str, product_type: str, 
                               expected_volume: float = 1000) -> CostStructure:
        """
        估算成本结构
        
        Args:
            industry_id: 行业ID
            product_type: 产品类型
            expected_volume: 预期销量
            
        Returns:
            成本结构
        """
        # 创建请求对象
        request = ProfitAnalysisRequest(
            industry_id=industry_id,
            product_type=product_type,
            production_location="global",  # 默认全球生产
            target_markets=["global"],     # 默认全球市场
            expected_sales_volume=expected_volume
        )
        
        return self.calculator._estimate_cost_structure(request)
    
    def calculate_break_even_point(self, fixed_cost: float, selling_price: float, 
                                  variable_cost_per_unit: float) -> float:
        """
        计算盈亏平衡点
        
        Args:
            fixed_cost: 固定成本
            selling_price: 售价
            variable_cost_per_unit: 单位变动成本
            
        Returns:
            盈亏平衡点销量
        """
        if selling_price - variable_cost_per_unit <= 0:
            return float('inf')
        
        break_even_volume = fixed_cost / (selling_price - variable_cost_per_unit)
        return max(0, round(break_even_volume, 2))
    
    def assess_profit_risk(self, request: ProfitAnalysisRequest, 
                          analysis_data: Dict[str, Any]) -> RiskLevel:
        """
        评估利润风险
        
        Args:
            request: 利润分析请求
            analysis_data: 分析数据
            
        Returns:
            风险等级
        """
        return self.calculator._assess_profit_risk(request, analysis_data)
    
    def get_profit_benchmark(self, industry_id: str) -> Optional[Dict[str, float]]:
        """
        获取行业利润基准
        
        Args:
            industry_id: 行业ID
            
        Returns:
            行业利润基准数据
        """
        return self.calculator.get_industry_benchmark(industry_id)
    
    def get_cost_model(self, product_type: str) -> Dict[str, float]:
        """
        获取成本模型
        
        Args:
            product_type: 产品类型
            
        Returns:
            成本模型参数
        """
        return self.calculator.get_cost_model(product_type)
    
    def validate_profit_accuracy(self, test_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        验证利润测算准确性
        
        Args:
            test_data: 测试数据
            
        Returns:
            准确性指标
        """
        return self.calculator.validate_accuracy(test_data)
    
    def calibrate_profit_models(self, historical_data: List[Dict[str, Any]]) -> bool:
        """
        校准利润测算模型
        
        Args:
            historical_data: 历史数据
            
        Returns:
            校准是否成功
        """
        return self.calculator.calibrate_model(historical_data)
    
    def generate_profit_report(self, results: List[ProfitAnalysisResult]) -> Dict[str, Any]:
        """
        生成利润分析报告
        
        Args:
            results: 利润分析结果列表
            
        Returns:
            利润分析报告
        """
        if not results:
            return {"error": "无分析结果"}
        
        # 汇总统计
        total_analyses = len(results)
        profitable_count = sum(1 for r in results if r.is_profitable)
        profitability_rate = (profitable_count / total_analyses * 100) if total_analyses > 0 else 0
        
        # 风险分布
        risk_distribution = {
            "low": sum(1 for r in results if r.profit_risk_level == RiskLevel.LOW),
            "medium": sum(1 for r in results if r.profit_risk_level == RiskLevel.MEDIUM),
            "high": sum(1 for r in results if r.profit_risk_level == RiskLevel.HIGH),
            "critical": sum(1 for r in results if r.profit_risk_level == RiskLevel.CRITICAL)
        }
        
        # 置信度统计
        confidence_scores = [r.confidence_score for r in results]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # 利润率统计
        net_margins = [r.net_margin for r in results]
        avg_net_margin = sum(net_margins) / len(net_margins) if net_margins else 0
        
        # 行业分布
        industries = {}
        for result in results:
            industry_id = result.request.industry_id
            if industry_id not in industries:
                industries[industry_id] = {
                    "count": 0,
                    "profitable": 0,
                    "avg_net_margin": 0,
                    "total_confidence": 0
                }
            
            industries[industry_id]["count"] += 1
            if result.is_profitable:
                industries[industry_id]["profitable"] += 1
            industries[industry_id]["avg_net_margin"] += result.net_margin
            industries[industry_id]["total_confidence"] += result.confidence_score
        
        # 计算行业平均值
        for industry_id, data in industries.items():
            count = data["count"]
            data["profitability_rate"] = (data["profitable"] / count * 100) if count > 0 else 0
            data["avg_net_margin"] = data["avg_net_margin"] / count if count > 0 else 0
            data["avg_confidence"] = data["total_confidence"] / count if count > 0 else 0
            del data["total_confidence"]
        
        # 生成报告
        report = {
            "report_type": "profit_analysis_summary",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_analyses": total_analyses,
                "profitable_count": profitable_count,
                "profitability_rate": round(profitability_rate, 2),
                "avg_net_margin": round(avg_net_margin, 2),
                "avg_confidence": round(avg_confidence, 2)
            },
            "risk_distribution": risk_distribution,
            "industry_analysis": industries,
            "top_recommendations": self._generate_top_recommendations(results),
            "key_findings": self._extract_key_findings(results)
        }
        
        return report
    
    def _generate_top_recommendations(self, results: List[ProfitAnalysisResult]) -> List[Dict[str, Any]]:
        """生成顶级推荐"""
        # 筛选高利润、低风险、高置信度的结果
        good_results = []
        
        for result in results:
            # 筛选条件：盈利、非高风险、置信度高
            if (result.is_profitable and 
                result.profit_risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM] and
                result.confidence_score >= 80):
                
                good_results.append(result)
        
        # 按净利润和置信度排序
        good_results.sort(
            key=lambda r: (r.net_profit, r.confidence_score),
            reverse=True
        )
        
        # 生成推荐列表
        recommendations = []
        for result in good_results[:5]:  # 只返回前5个
            recommendation = {
                "industry_id": result.request.industry_id,
                "product_type": result.request.product_type,
                "net_margin": round(result.net_margin, 2),
                "net_profit": round(result.net_profit, 2),
                "confidence": round(result.confidence_score, 2),
                "risk_level": result.profit_risk_level.value,
                "key_factors": result.key_risk_factors,
                "action_items": self._generate_action_items(result)
            }
            recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_action_items(self, result: ProfitAnalysisResult) -> List[str]:
        """生成行动项"""
        actions = []
        
        # 基于分析结果生成建议
        if result.net_margin < 10:
            actions.append("考虑提高售价或降低单位成本以提高利润率")
        
        if result.profit_risk_level == RiskLevel.HIGH:
            actions.append("进行详细风险评估并建立风险缓解计划")
        
        if result.break_even_point > result.request.expected_sales_volume * 2:
            actions.append("重新评估预期销量或考虑降低固定成本")
        
        # 通用建议
        actions.append("定期监控市场变化和成本变动")
        actions.append("建立利润敏感性分析机制")
        
        return actions
    
    def _extract_key_findings(self, results: List[ProfitAnalysisResult]) -> List[str]:
        """提取关键发现"""
        findings = []
        
        if not results:
            return ["无分析数据"]
        
        # 统计信息
        profitable_count = sum(1 for r in results if r.is_profitable)
        profitability_rate = profitable_count / len(results) * 100
        
        # 风险统计
        high_risk_count = sum(1 for r in results if r.profit_risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL])
        high_risk_rate = high_risk_count / len(results) * 100
        
        # 利润率统计
        avg_net_margin = sum(r.net_margin for r in results) / len(results)
        
        # 生成发现
        findings.append(f"总体盈利能力: {profitability_rate:.1f}%的项目可实现盈利")
        findings.append(f"平均净利润率: {avg_net_margin:.1f}%")
        findings.append(f"高风险项目占比: {high_risk_rate:.1f}%")
        
        # 行业特定发现
        industry_results = {}
        for result in results:
            industry_id = result.request.industry_id
            if industry_id not in industry_results:
                industry_results[industry_id] = []
            industry_results[industry_id].append(result)
        
        # 分析各行业表现
        for industry_id, industry_data in industry_results.items():
            industry_profitable = sum(1 for r in industry_data if r.is_profitable)
            industry_rate = industry_profitable / len(industry_data) * 100
            
            if industry_rate >= 80:
                findings.append(f"{industry_id}: 行业盈利能力强劲 ({industry_rate:.1f}%盈利)")
            elif industry_rate <= 50:
                findings.append(f"{industry_id}: 行业盈利能力较弱 ({industry_rate:.1f}%盈利)")
        
        return findings
    
    def get_calibration_status(self) -> Dict[str, Any]:
        """
        获取校准状态
        
        Returns:
            校准状态信息
        """
        return self.calculator.get_calibration_status()