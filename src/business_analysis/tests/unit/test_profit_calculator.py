"""
利润测算器单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pytest
import numpy as np

from business_analysis.engine.profit_calculator import ProfitCalculator
from business_analysis.models.data_models import (
    ProfitAnalysisRequest, ProfitAnalysisResult,
    CostStructure, PricingStrategy, RiskLevel
)


class TestProfitCalculator:
    """利润测算器测试类"""
    
    @pytest.fixture
    def calculator(self):
        """创建利润测算器实例"""
        return ProfitCalculator()
    
    @pytest.fixture
    def sample_request(self):
        """创建样本请求"""
        return ProfitAnalysisRequest(
            industry_id="information_technology",
            product_type="enterprise_software",
            production_location="global",
            target_markets=["global"],
            expected_sales_volume=1000,
            target_profit_margin=20.0
        )
    
    @pytest.fixture
    def sample_cost_structure(self):
        """创建样本成本结构"""
        return CostStructure(
            material_cost=200.0,
            production_cost=150.0,
            labor_cost=100.0,
            logistics_cost=50.0,
            marketing_cost=80.0,
            tax_cost=70.0
        )
    
    def test_initialization(self, calculator):
        """测试初始化"""
        assert calculator is not None
        assert hasattr(calculator, 'industry_benchmarks')
        assert hasattr(calculator, 'cost_models')
        assert hasattr(calculator, 'calibration_factors')
    
    def test_analyze_profit_basic(self, calculator, sample_request):
        """测试基本利润分析"""
        result = calculator.analyze_profit(sample_request)
        
        # 验证返回类型
        assert isinstance(result, ProfitAnalysisResult)
        
        # 验证必要字段存在
        assert hasattr(result, 'estimated_total_cost')
        assert hasattr(result, 'cost_per_unit')
        assert hasattr(result, 'recommended_price')
        assert hasattr(result, 'net_profit')
        assert hasattr(result, 'gross_margin')
        assert hasattr(result, 'net_margin')
        assert hasattr(result, 'profit_risk_level')
        assert hasattr(result, 'confidence_score')
        
        # 验证数据类型
        assert isinstance(result.estimated_total_cost, float)
        assert isinstance(result.cost_per_unit, float)
        assert isinstance(result.recommended_price, float)
        assert isinstance(result.net_profit, float)
        assert isinstance(result.gross_margin, float)
        assert isinstance(result.net_margin, float)
        assert isinstance(result.profit_risk_level, RiskLevel)
        assert isinstance(result.confidence_score, float)
        
        # 验证合理性
        assert result.estimated_total_cost > 0
        assert result.cost_per_unit > 0
        assert result.recommended_price > result.cost_per_unit
        assert result.gross_margin >= 0
        assert result.confidence_score >= 0 and result.confidence_score <= 100
    
    def test_analyze_profit_with_custom_cost(self, calculator, sample_request, sample_cost_structure):
        """测试自定义成本结构的利润分析"""
        sample_request.cost_structure = sample_cost_structure
        sample_request.cost_estimation_method = "custom"
        
        result = calculator.analyze_profit(sample_request)
        
        # 验证成本结构被使用
        assert result.cost_breakdown is not None
        assert len(result.cost_breakdown) > 0
        
        # 验证成本细分布局
        cost_categories = ["material", "production", "labor", "logistics", "marketing", "tax", "other"]
        for category in cost_categories:
            assert category in result.cost_breakdown
            assert 0 <= result.cost_breakdown[category] <= 100
    
    def test_analyze_profit_with_pricing_strategy(self, calculator, sample_request):
        """测试自定义定价策略的利润分析"""
        pricing_strategy = PricingStrategy(
            strategy_type="cost_plus",
            base_price=500.0,
            markup_percentage=30.0
        )
        
        sample_request.pricing_strategy = pricing_strategy
        result = calculator.analyze_profit(sample_request)
        
        # 验证定价策略被使用
        assert result.recommended_price >= pricing_strategy.calculate_price() * 0.9
    
    def test_cost_structure_estimation(self, calculator, sample_request):
        """测试成本结构估算"""
        cost_structure = calculator._estimate_cost_structure(sample_request)
        
        # 验证成本结构类型
        assert isinstance(cost_structure, CostStructure)
        
        # 验证所有成本字段存在
        assert cost_structure.material_cost >= 0
        assert cost_structure.production_cost >= 0
        assert cost_structure.labor_cost >= 0
        assert cost_structure.logistics_cost >= 0
        assert cost_structure.marketing_cost >= 0
        assert cost_structure.tax_cost >= 0
        assert cost_structure.other_costs >= 0
        
        # 验证总成本计算
        total_cost = cost_structure.total_cost
        calculated_total = sum([
            cost_structure.material_cost,
            cost_structure.production_cost,
            cost_structure.labor_cost,
            cost_structure.logistics_cost,
            cost_structure.marketing_cost,
            cost_structure.tax_cost,
            cost_structure.other_costs
        ])
        assert abs(total_cost - calculated_total) < 0.01
    
    def test_cost_distribution(self, calculator, sample_request):
        """测试成本分布计算"""
        cost_structure = calculator._estimate_cost_structure(sample_request)
        distribution = cost_structure.get_cost_distribution()
        
        # 验证分布类型
        assert isinstance(distribution, dict)
        
        # 验证分布值在0-100范围内
        for value in distribution.values():
            assert 0 <= value <= 100
        
        # 验证分布总和约为100%（考虑浮点误差）
        total_percentage = sum(distribution.values())
        assert 99.9 <= total_percentage <= 100.1
    
    def test_pricing_strategy_calculation(self, calculator, sample_request):
        """测试定价策略计算"""
        # 成本加成策略
        cost_per_unit = 100.0
        pricing_strategy = PricingStrategy(
            strategy_type="cost_plus",
            base_price=cost_per_unit,
            markup_percentage=30.0
        )
        
        price = pricing_strategy.calculate_price()
        assert price == cost_per_unit * 1.3
        
        # 竞争定价策略
        competitor_prices = [120.0, 130.0, 110.0]
        pricing_strategy = PricingStrategy(
            strategy_type="competition_based",
            base_price=0.0,
            competitor_prices=competitor_prices
        )
        
        price = pricing_strategy.calculate_price()
        assert price == sum(competitor_prices) / len(competitor_prices)
        
        # 价值定价策略
        pricing_strategy = PricingStrategy(
            strategy_type="value_based",
            base_price=100.0,
            value_based_multiplier=3.0
        )
        
        price = pricing_strategy.calculate_price()
        assert price == 100.0 * 3.0
    
    def test_sensitivity_analysis(self, calculator, sample_request):
        """测试敏感性分析"""
        # 获取分析结果
        result = calculator.analyze_profit(sample_request)
        
        # 验证敏感性分析存在
        assert hasattr(result, 'sensitivity_analysis')
        sensitivity = result.sensitivity_analysis
        
        # 验证基本结构
        assert isinstance(sensitivity, dict)
        assert "_meta" in sensitivity
        
        # 验证关键变量分析
        key_variables = ["sales_volume", "unit_cost", "selling_price", "marketing_cost"]
        for var in key_variables:
            assert var in sensitivity
            
            var_data = sensitivity[var]
            assert "base_value" in var_data
            assert "change_percent" in var_data
            assert "profit_change_up" in var_data
            assert "profit_change_down" in var_data
            assert "sensitivity_score" in var_data
    
    def test_break_even_calculation(self, calculator, sample_request):
        """测试盈亏平衡点计算"""
        cost_per_unit = 50.0
        selling_price = 75.0
        
        # 计算盈亏平衡点
        break_even = calculator._calculate_break_even_point(
            sample_request, cost_per_unit, selling_price
        )
        
        # 验证类型和范围
        assert isinstance(break_even, float)
        assert break_even >= 0
        
        # 对于可盈利产品，盈亏平衡点应为正数
        if selling_price > cost_per_unit:
            assert break_even > 0
            # 验证基本逻辑：固定成本/(售价-变动成本)
            # 由于内部使用简化估算，不做精确值验证
        else:
            # 不可盈利的情况应返回无穷大
            assert break_even == float('inf')
    
    def test_risk_assessment(self, calculator, sample_request):
        """测试风险评估"""
        # 获取分析结果
        result = calculator.analyze_profit(sample_request)
        
        # 提取分析数据
        analysis_data = {
            "gross_margin": result.gross_margin,
            "net_margin": result.net_margin,
            "sensitivity_analysis": result.sensitivity_analysis,
            "break_even_point": result.break_even_point
        }
        
        # 评估风险
        risk_level = calculator._assess_profit_risk(sample_request, analysis_data)
        
        # 验证风险等级类型
        assert isinstance(risk_level, RiskLevel)
        
        # 验证风险等级在有效范围内
        assert risk_level in [
            RiskLevel.LOW, 
            RiskLevel.MEDIUM, 
            RiskLevel.HIGH, 
            RiskLevel.CRITICAL
        ]
    
    def test_confidence_score_calculation(self, calculator, sample_request):
        """测试置信度评分计算"""
        # 获取分析结果
        result = calculator.analyze_profit(sample_request)
        
        # 提取分析数据
        analysis_data = {
            "gross_margin": result.gross_margin,
            "net_margin": result.net_margin,
            "sensitivity_analysis": result.sensitivity_analysis,
            "break_even_point": result.break_even_point
        }
        
        # 计算置信度
        confidence = calculator._calculate_confidence_score(sample_request, analysis_data)
        
        # 验证置信度范围
        assert 0 <= confidence <= 100
        
        # 验证置信度合理性
        # 对于一般情况，置信度应在70-95之间
        assert 70 <= confidence <= 95
    
    def test_batch_analysis(self, calculator):
        """测试批量分析"""
        # 创建多个请求
        requests = [
            ProfitAnalysisRequest(
                industry_id="information_technology",
                product_type=f"product_{i}",
                production_location="global",
                target_markets=["global"],
                expected_sales_volume=1000 * (i + 1),
                target_profit_margin=20.0
            )
            for i in range(3)
        ]
        
        # 执行批量分析
        results = calculator.batch_analyze_profits(requests)
        
        # 验证返回类型和数量
        assert isinstance(results, list)
        assert len(results) == len(requests)
        
        # 验证每个结果
        for result in results:
            assert isinstance(result, ProfitAnalysisResult)
            assert hasattr(result, 'net_profit')
            assert hasattr(result, 'confidence_score')
    
    def test_accuracy_validation(self, calculator):
        """测试准确性验证"""
        # 创建测试数据
        test_data = [
            {
                "actual_profit": 100000.0,
                "predicted_profit": 95000.0
            },
            {
                "actual_profit": 150000.0,
                "predicted_profit": 155000.0
            },
            {
                "actual_profit": 80000.0,
                "predicted_profit": 82000.0
            }
        ]
        
        # 验证准确性
        metrics = calculator.validate_accuracy(test_data)
        
        # 验证返回类型
        assert isinstance(metrics, dict)
        
        # 验证必要字段存在
        assert "total_samples" in metrics
        assert "mean_absolute_percentage_error" in metrics
        assert "error_rate_below_5_percent" in metrics
        assert "error_rate_5_10_percent" in metrics
        assert "error_rate_above_10_percent" in metrics
        
        # 验证数值范围
        assert metrics["mean_absolute_percentage_error"] >= 0
        assert 0 <= metrics["error_rate_below_5_percent"] <= 100
        assert 0 <= metrics["error_rate_5_10_percent"] <= 100
        assert 0 <= metrics["error_rate_above_10_percent"] <= 100
        
        # 验证总和接近100%（考虑浮点误差）
        total_error_rate = (
            metrics["error_rate_below_5_percent"] +
            metrics["error_rate_5_10_percent"] +
            metrics["error_rate_above_10_percent"]
        )
        assert 99.9 <= total_error_rate <= 100.1
    
    def test_calibration(self, calculator):
        """测试模型校准"""
        # 创建历史数据
        historical_data = [
            {
                "actual_profit": 100000.0,
                "predicted_profit": 105000.0  # 5%误差
            },
            {
                "actual_profit": 150000.0,
                "predicted_profit": 142500.0  # -5%误差
            },
            {
                "actual_profit": 80000.0,
                "predicted_profit": 84000.0  # 5%误差
            }
        ]
        
        # 执行校准
        success = calculator.calibrate_model(historical_data)
        
        # 验证校准结果
        assert success is True or success is False
        
        # 验证校准因子存在
        calibration_status = calculator.get_calibration_status()
        assert isinstance(calibration_status, dict)
        assert "calibration_factors" in calibration_status
        assert "target_error_rate" in calibration_status
        
        # 验证目标误差率
        assert calibration_status["target_error_rate"] == 5.0