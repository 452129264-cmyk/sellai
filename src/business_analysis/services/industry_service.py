"""
行业分析服务
提供行业分类、行业画像、趋势分析等核心服务功能
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..engine.industry_classifier import IndustryClassifier
from ..engine.trend_predictor import TrendPredictor
from ..models.data_models import (
    IndustryCategory, IndustryProfile, IndustryLevel,
    TrendAnalysisRequest, TrendAnalysisResult,
    GrowthTrend, RiskLevel
)

logger = logging.getLogger(__name__)


class IndustryAnalysisService:
    """行业分析服务"""
    
    def __init__(self):
        """初始化行业分析服务"""
        self.classifier = IndustryClassifier()
        self.trend_predictor = TrendPredictor()
        
        logger.info("行业分析服务初始化完成")
    
    def get_industry_categories(self, level: Optional[IndustryLevel] = None) -> List[IndustryCategory]:
        """
        获取行业分类
        
        Args:
            level: 行业级别，可选
            
        Returns:
            行业分类列表
        """
        if level == IndustryLevel.PRIMARY:
            return self.classifier.get_primary_categories()
        elif level == IndustryLevel.SECONDARY:
            return self.classifier.get_secondary_categories()
        else:
            return list(self.classifier.categories.values())
    
    def get_industry_profile(self, industry_id: str) -> Optional[IndustryProfile]:
        """
        获取行业画像
        
        Args:
            industry_id: 行业ID
            
        Returns:
            行业画像，如果不存在则返回None
        """
        return self.classifier.get_profile(industry_id)
    
    def search_industries(self, query: str, level: Optional[IndustryLevel] = None) -> List[IndustryCategory]:
        """
        搜索行业
        
        Args:
            query: 搜索关键词
            level: 行业级别，可选
            
        Returns:
            匹配的行业分类列表
        """
        return self.classifier.search_categories(query, level)
    
    def get_industry_tree(self) -> Dict[str, Any]:
        """
        获取行业分类树
        
        Returns:
            行业分类树结构
        """
        return self.classifier.get_category_tree()
    
    def update_industry_profile(self, industry_id: str, **kwargs) -> bool:
        """
        更新行业画像
        
        Args:
            industry_id: 行业ID
            **kwargs: 更新的字段
            
        Returns:
            更新是否成功
        """
        return self.classifier.update_profile(industry_id, **kwargs)
    
    def analyze_trend(self, request: TrendAnalysisRequest) -> TrendAnalysisResult:
        """
        分析行业趋势
        
        Args:
            request: 趋势分析请求
            
        Returns:
            趋势分析结果
        """
        return self.trend_predictor.analyze_trend(request)
    
    def identify_emerging_trends(self, industry_ids: List[str], 
                                timeframe: str = "1y") -> List[Dict[str, Any]]:
        """
        识别新兴趋势
        
        Args:
            industry_ids: 行业ID列表
            timeframe: 时间范围
            
        Returns:
            新兴趋势列表
        """
        all_emerging_trends = []
        
        for industry_id in industry_ids:
            # 分析行业趋势
            request = TrendAnalysisRequest(
                industry_ids=[industry_id],
                timeframe=timeframe,
                analysis_type="emerging_trends",
                include_forecast=True
            )
            
            try:
                result = self.trend_predictor.analyze_trend(request)
                
                # 提取新兴趋势
                for trend in result.emerging_trends:
                    trend["source_industry"] = industry_id
                    all_emerging_trends.append(trend)
                    
            except Exception as e:
                logger.error(f"分析行业{industry_id}趋势失败: {e}")
                continue
        
        # 按置信度排序
        all_emerging_trends.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return all_emerging_trends
    
    def assess_industry_risks(self, industry_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        评估行业风险
        
        Args:
            industry_ids: 行业ID列表
            
        Returns:
            按行业分组的风险警告
        """
        risks_by_industry = {}
        
        for industry_id in industry_ids:
            # 获取行业画像
            profile = self.classifier.get_profile(industry_id)
            
            if not profile:
                logger.warning(f"行业{industry_id}画像不存在")
                continue
            
            # 分析趋势
            request = TrendAnalysisRequest(
                industry_ids=[industry_id],
                timeframe="1y",
                analysis_type="risk_assessment",
                include_forecast=True
            )
            
            try:
                result = self.trend_predictor.analyze_trend(request)
                risks_by_industry[industry_id] = result.risk_warnings
                
            except Exception as e:
                logger.error(f"评估行业{industry_id}风险失败: {e}")
                continue
        
        return risks_by_industry
    
    def get_industry_benchmark(self, industry_id: str) -> Optional[Dict[str, Any]]:
        """
        获取行业基准数据
        
        Args:
            industry_id: 行业ID
            
        Returns:
            行业基准数据
        """
        # 从趋势预测器获取行业趋势数据
        trend_data = self.trend_predictor.get_industry_trend(industry_id)
        
        if not trend_data:
            logger.warning(f"行业{industry_id}趋势数据不存在")
            return None
        
        # 从分类器获取行业画像
        profile = self.classifier.get_profile(industry_id)
        
        # 综合基准数据
        benchmark = {
            "industry_id": industry_id,
            "trend_pattern": trend_data.get("trend_pattern"),
            "growth_rate": trend_data.get("growth_rate"),
            "volatility": trend_data.get("volatility"),
            "emerging_sub_sectors": trend_data.get("emerging_sub_sectors", []),
            "profile": profile.dict() if profile else None,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return benchmark
    
    def export_industry_data(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        导出行业数据
        
        Args:
            output_dir: 输出目录，可选
            
        Returns:
            导出文件路径
        """
        return self.classifier.export_data(output_dir)
    
    def validate_trend_accuracy(self, test_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        验证趋势分析准确性
        
        Args:
            test_data: 测试数据
            
        Returns:
            准确性指标
        """
        return self.trend_predictor.validate_accuracy(test_data)
    
    def calibrate_trend_models(self, historical_data: List[Dict[str, Any]]) -> bool:
        """
        校准趋势分析模型
        
        Args:
            historical_data: 历史数据
            
        Returns:
            校准是否成功
        """
        return self.trend_predictor.calibrate_model(historical_data)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            系统状态信息
        """
        return {
            "service_status": "running",
            "total_industries": len(self.classifier.categories),
            "total_profiles": len(self.classifier.profiles),
            "trend_accuracy_target": 85.0,
            "last_updated": datetime.now().isoformat(),
            "components": {
                "industry_classifier": "active",
                "trend_predictor": "active"
            }
        }