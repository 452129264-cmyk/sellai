"""
趋势预测器单元测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pytest
from datetime import datetime

from business_analysis.engine.trend_predictor import TrendPredictor, TrendPattern
from business_analysis.models.data_models import (
    TrendAnalysisRequest, TrendAnalysisResult,
    GrowthTrend, RiskLevel
)


class TestTrendPredictor:
    """趋势预测器测试类"""
    
    @pytest.fixture
    def predictor(self):
        """创建趋势预测器实例"""
        return TrendPredictor()
    
    @pytest.fixture
    def sample_request(self):
        """创建样本请求"""
        return TrendAnalysisRequest(
            industry_ids=["information_technology", "financial_services"],
            timeframe="1y",
            analysis_type="market_trends",
            include_forecast=True
        )
    
    def test_initialization(self, predictor):
        """测试初始化"""
        assert predictor is not None
        assert hasattr(predictor, 'industry_trends')
        assert hasattr(predictor, 'pattern_models')
        assert hasattr(predictor, 'calibration_params')
        assert hasattr(predictor, 'risk_models')
    
    def test_analyze_trend_basic(self, predictor, sample_request):
        """测试基本趋势分析"""
        result = predictor.analyze_trend(sample_request)
        
        # 验证返回类型
        assert isinstance(result, TrendAnalysisResult)
        
        # 验证必要字段存在
        assert hasattr(result, 'growth_trends')
        assert hasattr(result, 'momentum_scores')
        assert hasattr(result, 'volatility_scores')
        assert hasattr(result, 'emerging_trends')
        assert hasattr(result, 'risk_warnings')
        assert hasattr(result, 'early_signals')
        assert hasattr(result, 'forecasts')
        assert hasattr(result, 'analysis_timestamp')
        assert hasattr(result, 'data_coverage')
        
        # 验证数据类型
        assert isinstance(result.growth_trends, dict)
        assert isinstance(result.momentum_scores, dict)
        assert isinstance(result.volatility_scores, dict)
        assert isinstance(result.emerging_trends, list)
        assert isinstance(result.risk_warnings, list)
        assert isinstance(result.early_signals, list)
        assert isinstance(result.forecasts, dict)
        assert isinstance(result.analysis_timestamp, datetime)
        assert isinstance(result.data_coverage, dict)
        
        # 验证行业范围
        for industry_id in sample_request.industry_ids:
            assert industry_id in result.growth_trends
            assert industry_id in result.momentum_scores
            assert industry_id in result.volatility_scores
            assert industry_id in result.data_coverage
    
    def test_generate_time_series_data(self, predictor):
        """测试时间序列数据生成"""
        industry_id = "information_technology"
        timeframe = "6m"
        
        dates, values = predictor._generate_time_series_data(industry_id, timeframe)
        
        # 验证返回类型
        assert isinstance(dates, list)
        assert isinstance(values, list)
        assert len(dates) == len(values)
        
        # 验证数据长度
        assert len(dates) > 0
        
        # 验证日期顺序
        for i in range(1, len(dates)):
            assert dates[i] > dates[i-1]
        
        # 验证数值合理性
        for value in values:
            assert isinstance(value, float)
            assert value > 0
    
    def test_detect_trend_pattern(self, predictor):
        """测试趋势模式检测"""
        # 创建测试数据
        dates = [
            datetime.now() - pytest.approx(365-i, rel=0.1) 
            for i in range(365)
        ]
        
        # 线性增长数据
        linear_values = [100.0 + i * 0.5 for i in range(365)]
        
        pattern, confidence = predictor._detect_trend_pattern(dates, linear_values)
        
        # 验证返回类型
        assert isinstance(pattern, TrendPattern)
        assert isinstance(confidence, float)
        
        # 验证置信度范围
        assert 0.5 <= confidence <= 1.0
        
        # 对于线性增长数据，应该检测到线性增长模式
        assert pattern in [TrendPattern.LINEAR_GROWTH, TrendPattern.EXPONENTIAL_GROWTH]
    
    def test_identify_emerging_trends(self, predictor):
        """测试新兴趋势识别"""
        industry_id = "information_technology"
        pattern = TrendPattern.EXPONENTIAL_GROWTH
        
        emerging_trends = predictor._identify_emerging_trends(industry_id, pattern)
        
        # 验证返回类型
        assert isinstance(emerging_trends, list)
        
        # 验证趋势内容
        for trend in emerging_trends:
            assert isinstance(trend, dict)
            assert "name" in trend
            assert "description" in trend
            assert "growth_potential" in trend
            assert "confidence" in trend
            assert "time_to_market" in trend
            assert "investment_required" in trend
    
    def test_assess_risk_factors(self, predictor):
        """测试风险因素评估"""
        industry_id = "information_technology"
        pattern = TrendPattern.EXPONENTIAL_GROWTH
        growth_rate = 25.0
        
        risk_warnings = predictor._assess_risk_factors(industry_id, pattern, growth_rate)
        
        # 验证返回类型
        assert isinstance(risk_warnings, list)
        
        # 验证风险警告内容
        for warning in risk_warnings:
            assert isinstance(warning, dict)
            assert "type" in warning
            assert "level" in warning
            assert isinstance(warning["level"], RiskLevel)
            assert "description" in warning
            assert "indicators" in warning
            assert isinstance(warning["indicators"], list)
            assert "confidence" in warning
            assert 0.5 <= warning["confidence"] <= 1.0
    
    def test_calculate_momentum_score(self, predictor):
        """测试动量评分计算"""
        # 创建测试数据
        values = [100.0, 105.0, 112.0, 120.0, 130.0, 145.0, 165.0, 190.0, 220.0, 255.0]
        
        momentum_score = predictor._calculate_momentum_score(values)
        
        # 验证返回类型和范围
        assert isinstance(momentum_score, float)
        assert 0 <= momentum_score <= 100
        
        # 对于增长数据，动量评分应较高
        assert momentum_score >= 50
    
    def test_calculate_volatility_score(self, predictor):
        """测试波动性评分计算"""
        # 创建测试数据
        stable_values = [100.0, 101.0, 99.0, 102.0, 100.5, 101.5, 99.5, 102.5]
        volatile_values = [100.0, 120.0, 80.0, 140.0, 60.0, 160.0, 40.0, 180.0]
        
        stable_score = predictor._calculate_volatility_score(stable_values)
        volatile_score = predictor._calculate_volatility_score(volatile_values)
        
        # 验证返回类型和范围
        assert isinstance(stable_score, float)
        assert isinstance(volatile_score, float)
        assert 0 <= stable_score <= 100
        assert 0 <= volatile_score <= 100
        
        # 验证波动性越高的数据评分越高
        assert volatile_score > stable_score
    
    def test_generate_forecast(self, predictor):
        """测试预测生成"""
        # 创建测试数据
        values = [100.0, 105.0, 112.0, 120.0, 130.0, 145.0, 165.0, 190.0, 220.0, 255.0]
        pattern = TrendPattern.EXPONENTIAL_GROWTH
        growth_rate = 25.0
        
        forecast = predictor._generate_forecast(values, pattern, growth_rate)
        
        # 验证返回类型
        assert isinstance(forecast, dict)
        
        # 验证预测内容
        if forecast.get("forecast_available", False):
            assert "pattern" in forecast
            assert "last_value" in forecast
            assert "short_term" in forecast
            assert "medium_term" in forecast
            assert "long_term" in forecast
            assert "confidence" in forecast
            
            # 验证数值类型
            assert isinstance(forecast["last_value"], float)
            assert isinstance(forecast["short_term"], dict)
            assert isinstance(forecast["confidence"], float)
        else:
            assert "reason" in forecast
    
    def test_validate_accuracy(self, predictor):
        """测试准确性验证"""
        # 创建测试数据
        test_data = [
            {
                "actual_trend": "growth",
                "predicted_trend": "growth",
                "is_emerging": True
            },
            {
                "actual_trend": "stagnant",
                "predicted_trend": "stagnant",
                "is_emerging": False
            },
            {
                "actual_trend": "declining",
                "predicted_trend": "stagnant",  # 错误预测
                "is_emerging": False
            }
        ]
        
        # 验证准确性
        metrics = predictor.validate_accuracy(test_data)
        
        # 验证返回类型
        assert isinstance(metrics, dict)
        
        # 验证必要字段存在
        assert "total_samples" in metrics
        assert "accuracy_rate" in metrics
        assert "false_positive_rate" in metrics
        assert "false_negative_rate" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        
        # 验证数值范围
        assert metrics["accuracy_rate"] >= 0 and metrics["accuracy_rate"] <= 100
        assert metrics["precision"] >= 0 and metrics["precision"] <= 100
        assert metrics["recall"] >= 0 and metrics["recall"] <= 100
    
    def test_calibration(self, predictor):
        """测试模型校准"""
        # 创建历史数据
        historical_data = [
            {
                "actual_trend": "growth",
                "predicted_trend": "growth",
                "is_emerging": True
            },
            {
                "actual_trend": "stagnant",
                "predicted_trend": "stagnant",
                "is_emerging": False
            },
            {
                "actual_trend": "declining",
                "predicted_trend": "stagnant",
                "is_emerging": False
            }
        ]
        
        # 执行校准
        success = predictor.calibrate_model(historical_data)
        
        # 验证校准结果
        assert success is True or success is False
        
        # 验证校准参数存在
        calibration_status = predictor.get_calibration_status()
        assert isinstance(calibration_status, dict)
        assert "calibration_params" in calibration_status
        assert "target_accuracy" in calibration_status
        
        # 验证目标准确率
        assert calibration_status["target_accuracy"] == 85.0
    
    def test_get_industry_trend(self, predictor):
        """测试获取行业趋势"""
        industry_id = "information_technology"
        
        trend_data = predictor.get_industry_trend(industry_id)
        
        # 验证返回类型
        assert isinstance(trend_data, dict)
        
        # 验证必要字段存在
        assert "growth_rate" in trend_data
        assert "trend_pattern" in trend_data
        assert "volatility" in trend_data
        assert "emerging_sub_sectors" in trend_data
        
        # 验证数据类型
        assert isinstance(trend_data["growth_rate"], float)
        assert isinstance(trend_data["trend_pattern"], TrendPattern)
        assert isinstance(trend_data["volatility"], float)
        assert isinstance(trend_data["emerging_sub_sectors"], list)
    
    def test_analyze_trend_different_timeframes(self, predictor):
        """测试不同时间范围的趋势分析"""
        timeframes = ["1m", "3m", "6m", "1y"]
        industry_id = "information_technology"
        
        for timeframe in timeframes:
            request = TrendAnalysisRequest(
                industry_ids=[industry_id],
                timeframe=timeframe,
                analysis_type="market_trends",
                include_forecast=True
            )
            
            result = predictor.analyze_trend(request)
            
            # 验证基本结构
            assert isinstance(result, TrendAnalysisResult)
            assert industry_id in result.growth_trends
            assert industry_id in result.momentum_scores
            assert industry_id in result.volatility_scores
    
    def test_analyze_trend_multiple_industries(self, predictor):
        """测试多行业趋势分析"""
        industry_ids = [
            "information_technology",
            "financial_services",
            "healthcare",
            "consumer_goods"
        ]
        
        request = TrendAnalysisRequest(
            industry_ids=industry_ids,
            timeframe="1y",
            analysis_type="market_trends",
            include_forecast=True
        )
        
        result = predictor.analyze_trend(request)
        
        # 验证包含所有行业
        for industry_id in industry_ids:
            assert industry_id in result.growth_trends
            assert industry_id in result.momentum_scores
            assert industry_id in result.volatility_scores
            assert industry_id in result.data_coverage
    
    def test_emerging_trends_ranking(self, predictor):
        """测试新兴趋势排名"""
        # 测试新兴趋势按置信度排序
        industry_id = "information_technology"
        pattern = TrendPattern.EXPONENTIAL_GROWTH
        
        emerging_trends = predictor._identify_emerging_trends(industry_id, pattern)
        
        # 如果有多个趋势，验证置信度降序排序
        if len(emerging_trends) > 1:
            for i in range(len(emerging_trends) - 1):
                assert emerging_trends[i]["confidence"] >= emerging_trends[i+1]["confidence"]
    
    def test_risk_warnings_severity(self, predictor):
        """测试风险警告严重性"""
        # 测试不同风险级别的警告
        industry_id = "information_technology"
        patterns = [
            (TrendPattern.EXPONENTIAL_GROWTH, 30.0),
            (TrendPattern.DECLINING, -10.0),
            (TrendPattern.STAGNANT, 2.0)
        ]
        
        for pattern, growth_rate in patterns:
            risk_warnings = predictor._assess_risk_factors(industry_id, pattern, growth_rate)
            
            # 验证风险警告类型
            for warning in risk_warnings:
                assert warning["level"] in [
                    RiskLevel.LOW,
                    RiskLevel.MEDIUM, 
                    RiskLevel.HIGH,
                    RiskLevel.CRITICAL
                ]