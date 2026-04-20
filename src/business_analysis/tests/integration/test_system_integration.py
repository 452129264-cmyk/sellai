"""
系统集成测试
测试全品类商业数据分析系统的各个组件集成工作
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pytest
from datetime import datetime

from business_analysis.services.industry_service import IndustryAnalysisService
from business_analysis.services.profit_service import ProfitCalculationService
from business_analysis.services.trend_service import TrendAnalysisService
from business_analysis.models.data_models import (
    ProfitAnalysisRequest, TrendAnalysisRequest,
    CostStructure, PricingStrategy,
    GrowthTrend, RiskLevel
)


class TestSystemIntegration:
    """系统集成测试类"""
    
    @pytest.fixture
    def industry_service(self):
        """创建行业分析服务实例"""
        return IndustryAnalysisService()
    
    @pytest.fixture
    def profit_service(self):
        """创建利润测算服务实例"""
        return ProfitCalculationService()
    
    @pytest.fixture
    def trend_service(self):
        """创建趋势分析服务实例"""
        return TrendAnalysisService()
    
    def test_services_initialization(self, industry_service, profit_service, trend_service):
        """测试服务初始化"""
        assert industry_service is not None
        assert profit_service is not None
        assert trend_service is not None
        
        # 验证服务内部组件初始化
        assert hasattr(industry_service, 'classifier')
        assert hasattr(industry_service, 'trend_predictor')
        assert hasattr(profit_service, 'calculator')
        assert hasattr(trend_service, 'predictor')
    
    def test_industry_classifier_integration(self, industry_service):
        """测试行业分类器集成"""
        # 测试行业分类获取
        primary_categories = industry_service.get_primary_categories()
        assert isinstance(primary_categories, list)
        assert len(primary_categories) >= 20
        
        # 测试二级行业获取
        secondary_categories = industry_service.get_secondary_categories()
        assert isinstance(secondary_categories, list)
        assert len(secondary_categories) >= 100
        
        # 测试行业画像获取
        for category in primary_categories[:5]:  # 测试前5个行业
            profile = industry_service.get_industry_profile(category.id)
            assert profile is not None
            assert profile.industry_id == category.id
    
    def test_profit_calculator_integration(self, profit_service):
        """测试利润测算器集成"""
        # 创建利润分析请求
        request = ProfitAnalysisRequest(
            industry_id="information_technology",
            product_type="enterprise_software",
            production_location="global",
            target_markets=["global", "china"],
            expected_sales_volume=5000,
            target_profit_margin=25.0
        )
        
        # 执行利润分析
        result = profit_service.analyze_profit(request)
        
        # 验证分析结果
        assert result is not None
        assert isinstance(result.net_profit, float)
        assert isinstance(result.gross_margin, float)
        assert isinstance(result.confidence_score, float)
        
        # 验证风险评估
        assert result.profit_risk_level in [
            RiskLevel.LOW,
            RiskLevel.MEDIUM, 
            RiskLevel.HIGH,
            RiskLevel.CRITICAL
        ]
    
    def test_trend_predictor_integration(self, trend_service):
        """测试趋势预测器集成"""
        # 创建趋势分析请求
        request = TrendAnalysisRequest(
            industry_ids=["information_technology", "financial_services"],
            timeframe="6m",
            analysis_type="market_trends",
            include_forecast=True
        )
        
        # 执行趋势分析
        result = trend_service.analyze_market_trends(
            industry_ids=request.industry_ids,
            timeframe=request.timeframe
        )
        
        # 验证分析结果
        assert result is not None
        assert isinstance(result.growth_trends, dict)
        assert isinstance(result.momentum_scores, dict)
        assert isinstance(result.emerging_trends, list)
        
        # 验证包含所有行业
        for industry_id in request.industry_ids:
            assert industry_id in result.growth_trends
            assert industry_id in result.momentum_scores
    
    def test_end_to_end_analysis_flow(self, industry_service, profit_service, trend_service):
        """测试端到端分析流程"""
        # 第一步：获取行业信息
        industries = industry_service.get_primary_categories()
        assert len(industries) > 0
        
        # 选择前两个行业进行深入分析
        target_industries = [ind.id for ind in industries[:2]]
        
        # 第二步：趋势分析
        trend_request = TrendAnalysisRequest(
            industry_ids=target_industries,
            timeframe="1y",
            analysis_type="market_trends",
            include_forecast=True
        )
        
        trend_result = trend_service.analyze_market_trends(
            industry_ids=trend_request.industry_ids,
            timeframe=trend_request.timeframe
        )
        
        # 验证趋势分析结果
        assert len(trend_result.growth_trends) == len(target_industries)
        assert len(trend_result.momentum_scores) == len(target_industries)
        
        # 第三步：利润分析
        profit_requests = []
        for industry_id in target_industries:
            # 基于趋势分析结果制定利润分析策略
            momentum_score = trend_result.momentum_scores.get(industry_id, 50.0)
            
            # 动量越高，预期利润率越高
            expected_profit_margin = 20.0 + (momentum_score / 100 * 15.0)
            
            request = ProfitAnalysisRequest(
                industry_id=industry_id,
                product_type="premium_product",
                production_location="global",
                target_markets=["global"],
                expected_sales_volume=10000,
                target_profit_margin=expected_profit_margin
            )
            profit_requests.append(request)
        
        # 批量利润分析
        profit_results = profit_service.batch_analyze_profits(profit_requests)
        assert len(profit_results) == len(profit_requests)
        
        # 验证每个分析结果
        for result in profit_results:
            assert result.is_profitable is True or False
            assert result.confidence_score >= 0 and result.confidence_score <= 100
    
    def test_batch_analysis_integration(self, profit_service, trend_service):
        """测试批量分析集成"""
        # 创建批量分析请求
        profit_requests = [
            ProfitAnalysisRequest(
                industry_id="information_technology",
                product_type=f"software_product_{i}",
                production_location="global",
                target_markets=["global"],
                expected_sales_volume=5000 * (i + 1),
                target_profit_margin=20.0 + i
            )
            for i in range(3)
        ]
        
        trend_requests = [
            TrendAnalysisRequest(
                industry_ids=["information_technology", "financial_services"],
                timeframe="6m",
                analysis_type="market_trends",
                include_forecast=True
            )
        ]
        
        # 执行批量分析
        profit_results = profit_service.batch_analyze_profits(profit_requests)
        assert len(profit_results) == len(profit_requests)
        
        for result in profit_results:
            assert result.profit_risk_level in [
                RiskLevel.LOW,
                RiskLevel.MEDIUM, 
                RiskLevel.HIGH,
                RiskLevel.CRITICAL
            ]
        
        # 验证趋势分析集成
        for request in trend_requests:
            result = trend_service.analyze_market_trends(
                industry_ids=request.industry_ids,
                timeframe=request.timeframe
            )
            assert result is not None
    
    def test_data_consistency_validation(self, industry_service):
        """测试数据一致性验证"""
        # 验证行业分类与行业画像的一致性
        industries = industry_service.get_primary_categories()
        
        for industry in industries[:10]:  # 测试前10个行业
            # 获取行业分类
            category = industry_service.classifier.get_category(industry.id)
            assert category is not None
            
            # 获取行业画像
            profile = industry_service.get_industry_profile(industry.id)
            assert profile is not None
            
            # 验证ID一致性
            assert category.id == profile.industry_id
    
    def test_error_handling_integration(self, profit_service):
        """测试错误处理集成"""
        # 测试无效请求
        invalid_requests = [
            ProfitAnalysisRequest(
                industry_id="nonexistent_industry",
                product_type="product",
                production_location="global",
                target_markets=["global"],
                expected_sales_volume=0,  # 无效销量
                target_profit_margin=-10.0  # 无效利润率
            )
        ]
        
        # 应该能够处理无效请求
        results = profit_service.batch_analyze_profits(invalid_requests)
        assert len(results) == 1
        
        # 验证错误处理
        result = results[0]
        assert result.confidence_score < 50  # 置信度应较低
        assert result.profit_risk_level in [
            RiskLevel.HIGH,
            RiskLevel.CRITICAL
        ]
    
    def test_performance_analysis_integration(self, trend_service):
        """测试性能分析集成"""
        # 创建多行业请求
        industry_ids = [
            "information_technology",
            "financial_services", 
            "healthcare",
            "consumer_goods",
            "industrial_manufacturing"
        ]
        
        # 测试机会识别
        opportunities = trend_service.identify_hot_opportunities(
            industry_ids=industry_ids,
            min_confidence=0.7,
            limit=10
        )
        
        # 验证结果
        assert isinstance(opportunities, list)
        assert len(opportunities) <= 10
        
        # 验证每个机会的置信度
        for opportunity in opportunities:
            assert opportunity["confidence"] >= 0.7
    
    def test_report_generation_integration(self, trend_service):
        """测试报告生成集成"""
        # 创建测试数据
        industry_ids = [
            "information_technology",
            "financial_services"
        ]
        
        # 生成趋势报告
        report = trend_service.generate_trend_report(
            industry_ids=industry_ids,
            report_period="6m"
        )
        
        # 验证报告结构
        assert isinstance(report, dict)
        assert "report_type" in report
        assert "executive_summary" in report
        assert "trend_analysis" in report
        assert "opportunity_landscape" in report
        assert "risk_assessment" in report
        assert "strategic_recommendations" in report
        
        # 验证必要字段存在
        summary = report["executive_summary"]
        assert "total_industries" in summary
        assert "emerging_trends_count" in summary
        assert "high_risk_industries" in summary
    
    def test_risk_assessment_integration(self, trend_service):
        """测试风险评估集成"""
        # 创建行业列表
        industry_ids = [
            "information_technology",
            "financial_services"
        ]
        
        # 生成风险警告
        risk_warnings = trend_service.generate_risk_warnings(industry_ids)
        
        # 验证返回类型
        assert isinstance(risk_warnings, dict)
        assert len(risk_warnings) == len(industry_ids)
        
        # 验证每个行业都有风险警告数据
        for industry_id in industry_ids:
            assert industry_id in risk_warnings
            warnings = risk_warnings[industry_id]
            assert isinstance(warnings, list)
    
    def test_performance_prediction_integration(self, trend_service):
        """测试表现预测集成"""
        # 创建行业列表
        industry_ids = [
            "information_technology",
            "financial_services"
        ]
        
        # 生成表现预测
        predictions = trend_service.predict_industry_performance(
            industry_ids=industry_ids,
            prediction_period="1y"
        )
        
        # 验证返回类型
        assert isinstance(predictions, dict)
        assert len(predictions) == len(industry_ids)
        
        # 验证每个行业的预测数据
        for industry_id in industry_ids:
            assert industry_id in predictions
            prediction = predictions[industry_id]
            assert isinstance(prediction, dict)
            assert "growth_forecast" in prediction
            assert "confidence" in prediction
    
    def test_comprehensive_analysis_workflow(self, industry_service, profit_service, trend_service):
        """测试综合分析工作流"""
        # 第一步：识别高潜力行业
        industries = industry_service.get_primary_categories()
        high_potential_industries = []
        
        for industry in industries[:5]:
            profile = industry_service.get_industry_profile(industry.id)
            if profile and profile.growth_rate >= 10:
                high_potential_industries.append(industry.id)
        
        assert len(high_potential_industries) > 0
        
        # 第二步：分析市场趋势
        trend_analysis = trend_service.analyze_market_trends(
            industry_ids=high_potential_industries,
            timeframe="1y"
        )
        
        # 第三步：识别热门机会
        opportunities = trend_service.identify_hot_opportunities(
            industry_ids=high_potential_industries,
            min_confidence=0.7
        )
        
        # 第四步：针对机会进行利润分析
        if opportunities:
            top_opportunity = opportunities[0]
            profit_request = ProfitAnalysisRequest(
                industry_id=top_opportunity["industry_id"],
                product_type="premium_solution",
                production_location="global",
                target_markets=["global"],
                expected_sales_volume=20000,
                target_profit_margin=25.0
            )
            
            profit_result = profit_service.analyze_profit(profit_request)
            
            # 验证结果
            assert profit_result is not None
            assert profit_result.confidence_score >= 0
            assert profit_result.net_profit >= 0
    
    def test_error_recovery_and_continuity(self, profit_service):
        """测试错误恢复和连续性"""
        # 创建混合请求（有效+无效）
        mixed_requests = [
            ProfitAnalysisRequest(
                industry_id="information_technology",
                product_type="valid_product",
                production_location="global",
                target_markets=["global"],
                expected_sales_volume=10000,
                target_profit_margin=20.0
            ),
            ProfitAnalysisRequest(
                industry_id="nonexistent_industry",
                product_type="invalid_product", 
                production_location="global",
                target_markets=["global"],
                expected_sales_volume=0,
                target_profit_margin=-100.0
            ),
            ProfitAnalysisRequest(
                industry_id="financial_services",
                product_type="valid_product_2",
                production_location="global",
                target_markets=["global"],
                expected_sales_volume=15000,
                target_profit_margin=18.0
            )
        ]
        
        # 批量分析应该能够处理混合请求
        results = profit_service.batch_analyze_profits(mixed_requests)
        assert len(results) == len(mixed_requests)
        
        # 验证错误处理结果
        for i, result in enumerate(results):
            if i == 1:  # 无效请求
                assert result.confidence_score < 50
                assert result.profit_risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            else:  # 有效请求
                assert result.confidence_score >= 50
    
    def test_system_status_monitoring(self, industry_service, profit_service, trend_service):
        """测试系统状态监控"""
        # 获取各服务状态
        industry_status = industry_service.get_system_status()
        profit_status = profit_service.get_calibration_status()
        trend_status = trend_service.get_calibration_status()
        
        # 验证状态数据结构
        assert isinstance(industry_status, dict)
        assert isinstance(profit_status, dict)
        assert isinstance(trend_status, dict)
        
        # 验证必要字段
        assert "service_status" in industry_status
        assert "total_industries" in industry_status
        assert "total_profiles" in industry_status
        
        assert "calibration_factors" in profit_status
        assert "target_error_rate" in profit_status
        
        assert "calibration_params" in trend_status
        assert "target_accuracy" in trend_status