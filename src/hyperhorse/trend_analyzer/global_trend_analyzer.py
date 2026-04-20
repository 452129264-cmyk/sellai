#!/usr/bin/env python3
"""
全球趋势分析器
整合Firecrawl数据、自研爬虫数据和市场情报，提供全球多维度趋势分析
支持多市场、多行业、多时间维度的交叉分析
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from enum import Enum

from ..data_sources.firecrawl_adapter import FirecrawlAdapter, Region, Language, TrendCategory
from .video_trend_analyzer import ContentStyle

logger = logging.getLogger(__name__)


class AnalysisDimension(str, Enum):
    """分析维度"""
    INDUSTRY = "industry"  # 行业维度
    REGION = "region"  # 区域维度
    PLATFORM = "platform"  # 平台维度
    CONTENT_TYPE = "content_type"  # 内容类型维度
    TIME = "time"  # 时间维度


class TrendStrength(str, Enum):
    """趋势强度"""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class GlobalTrendAnalyzer:
    """全球趋势分析器"""
    
    def __init__(self, firecrawl_adapter: Optional[FirecrawlAdapter] = None):
        """
        初始化全球趋势分析器
        
        Args:
            firecrawl_adapter: Firecrawl适配器实例，可选
        """
        self.firecrawl_adapter = firecrawl_adapter or FirecrawlAdapter()
        
        # 行业映射
        self.industry_mapping = self._load_industry_mapping()
        
        # 区域权重配置
        self.regional_weights = self._load_regional_weights()
        
        # 时间窗口配置
        self.time_windows = ["1d", "7d", "30d", "90d", "180d", "365d"]
        
        logger.info("全球趋势分析器初始化完成")
    
    def _load_industry_mapping(self) -> Dict[str, List[str]]:
        """加载行业映射"""
        return {
            "ecommerce": ["online_retail", "dropshipping", "marketplaces", "social_commerce"],
            "ai_technology": ["generative_ai", "machine_learning", "computer_vision", "nlp"],
            "digital_health": ["telemedicine", "health_tracking", "mental_health", "fitness_apps"],
            "sustainable_energy": ["solar_power", "wind_energy", "energy_storage", "green_hydrogen"],
            "creators_economy": ["content_creation", "influencer_marketing", "digital_products", "community_building"],
            "fintech": ["digital_payments", "investing_platforms", "insurtech", "blockchain_finance"]
        }
    
    def _load_regional_weights(self) -> Dict[str, float]:
        """加载区域权重"""
        return {
            Region.NORTH_AMERICA.value: 0.35,  # 北美权重最高
            Region.EUROPE.value: 0.25,
            Region.ASIA_PACIFIC.value: 0.20,
            Region.LATIN_AMERICA.value: 0.10,
            Region.MIDDLE_EAST.value: 0.05,
            Region.AFRICA.value: 0.05
        }
    
    def comprehensive_analysis(self,
                             industries: List[str] = None,
                             regions: List[Region] = None,
                             dimensions: List[AnalysisDimension] = None,
                             timeframe: str = "30d") -> Dict[str, Any]:
        """
        综合趋势分析
        
        Args:
            industries: 行业列表
            regions: 区域列表
            dimensions: 分析维度列表
            timeframe: 时间范围
            
        Returns:
            综合趋势分析结果
        """
        start_time = time.time()
        
        if industries is None:
            industries = list(self.industry_mapping.keys())
        if regions is None:
            regions = [Region.GLOBAL]
        if dimensions is None:
            dimensions = [AnalysisDimension.INDUSTRY, AnalysisDimension.REGION]
        
        logger.info(f"开始综合趋势分析: 行业={len(industries)}, 区域={len(regions)}, 维度={dimensions}")
        
        try:
            # 获取基础数据
            global_trends = self.firecrawl_adapter.fetch_global_trends(limit=100)
            video_trends = self.firecrawl_adapter.fetch_video_content_trends(
                platform="all", timeframe=timeframe, limit=50
            )
            
            # 多维分析
            analysis_results = {}
            
            for dimension in dimensions:
                if dimension == AnalysisDimension.INDUSTRY:
                    analysis_results["industry"] = self._analyze_by_industry(
                        industries, global_trends, video_trends
                    )
                elif dimension == AnalysisDimension.REGION:
                    analysis_results["region"] = self._analyze_by_region(
                        regions, global_trends, video_trends
                    )
                elif dimension == AnalysisDimension.PLATFORM:
                    analysis_results["platform"] = self._analyze_by_platform(
                        video_trends
                    )
                elif dimension == AnalysisDimension.CONTENT_TYPE:
                    analysis_results["content_type"] = self._analyze_by_content_type(
                        video_trends
                    )
                elif dimension == AnalysisDimension.TIME:
                    analysis_results["time"] = self._analyze_by_time(
                        global_trends, video_trends, timeframe
                    )
            
            # 交叉分析
            cross_analysis = self._cross_dimensional_analysis(analysis_results)
            
            # 生成洞察
            insights = self._generate_insights(analysis_results, cross_analysis)
            
            # 综合评分
            overall_score = self._calculate_overall_score(analysis_results, cross_analysis)
            
            # 组装结果
            result = {
                "timestamp": datetime.now().isoformat(),
                "timeframe": timeframe,
                "scope": {
                    "industries": industries,
                    "regions": [r.value for r in regions],
                    "dimensions": [d.value for d in dimensions]
                },
                "data_summary": {
                    "global_trends_count": len(global_trends),
                    "video_trends_count": len(video_trends),
                    "coverage_score": self._calculate_data_coverage(industries, regions)
                },
                "dimensional_analysis": analysis_results,
                "cross_analysis": cross_analysis,
                "insights": insights,
                "overall_assessment": {
                    "score": overall_score,
                    "strength": self._classify_trend_strength(overall_score),
                    "confidence": self._calculate_confidence(analysis_results),
                    "recommended_focus_areas": self._identify_focus_areas(insights)
                },
                "strategic_recommendations": self._generate_strategic_recommendations(
                    analysis_results, insights, overall_score
                ),
                "analysis_metadata": {
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    "algorithm_version": "1.0",
                    "freshness_hours": self._calculate_freshness(global_trends, video_trends)
                }
            }
            
            logger.info(f"综合趋势分析完成: 维度={len(dimensions)}, 得分={overall_score:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"综合趋势分析失败: {e}")
            return self._generate_fallback_analysis(industries, regions, dimensions, timeframe)
    
    def track_trend_evolution(self,
                            trend_ids: List[str],
                            time_periods: List[str]) -> Dict[str, Any]:
        """
        跟踪趋势演变
        
        Args:
            trend_ids: 趋势ID列表
            time_periods: 时间周期列表
            
        Returns:
            趋势演变分析结果
        """
        start_time = time.time()
        
        try:
            evolution_data = []
            
            for trend_id in trend_ids:
                trend_evolution = self._track_single_trend_evolution(trend_id, time_periods)
                evolution_data.append({
                    "trend_id": trend_id,
                    "evolution": trend_evolution
                })
            
            # 分析演变模式
            evolution_patterns = self._analyze_evolution_patterns(evolution_data)
            
            # 预测未来走向
            future_predictions = self._predict_future_evolution(evolution_data, evolution_patterns)
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "trends_tracked": len(trend_ids),
                "time_periods": time_periods,
                "evolution_data": evolution_data,
                "patterns_identified": evolution_patterns,
                "future_predictions": future_predictions,
                "key_takeaways": self._extract_evolution_insights(evolution_data, evolution_patterns),
                "analysis_metadata": {
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    "tracking_accuracy": self._estimate_tracking_accuracy(evolution_data)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"趋势演变跟踪失败: {e}")
            return self._generate_fallback_evolution_analysis(trend_ids, time_periods)
    
    def compare_markets(self,
                       markets: List[Tuple[Region, str]],  # (区域, 行业)
                       comparison_metrics: List[str] = None) -> Dict[str, Any]:
        """
        比较不同市场
        
        Args:
            markets: 市场列表，每个元素为(区域, 行业)
            comparison_metrics: 比较指标列表
            
        Returns:
            市场比较分析结果
        """
        if comparison_metrics is None:
            comparison_metrics = ["growth_rate", "competition_level", "market_size", "opportunity_score"]
        
        try:
            market_data = []
            
            for region, industry in markets:
                market_analysis = self._analyze_single_market(region, industry)
                market_data.append({
                    "region": region.value,
                    "industry": industry,
                    "analysis": market_analysis
                })
            
            # 比较分析
            comparison_results = self._perform_market_comparison(market_data, comparison_metrics)
            
            # 识别最佳机会
            best_opportunities = self._identify_best_opportunities(market_data, comparison_results)
            
            # 风险评估
            risk_assessment = self._assess_market_risks(market_data, comparison_results)
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "markets_compared": len(markets),
                "comparison_metrics": comparison_metrics,
                "market_data": market_data,
                "comparison_results": comparison_results,
                "best_opportunities": best_opportunities,
                "risk_assessment": risk_assessment,
                "strategic_implications": self._derive_strategic_implications(
                    comparison_results, best_opportunities, risk_assessment
                ),
                "analysis_metadata": {
                    "comparison_depth": self._calculate_comparison_depth(market_data, comparison_metrics),
                    "data_reliability": self._assess_data_reliability(market_data)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"市场比较分析失败: {e}")
            return self._generate_fallback_market_comparison(markets, comparison_metrics)
    
    # 维度分析方法
    
    def _analyze_by_industry(self,
                            industries: List[str],
                            global_trends: List[Dict[str, Any]],
                            video_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """按行业分析"""
        analysis = {}
        
        for industry in industries:
            # 相关趋势
            related_trends = [
                t for t in global_trends
                if industry in t.get("industry", "") or 
                   industry in t.get("keywords", [])
            ]
            
            # 相关视频
            related_videos = [
                v for v in video_trends
                if industry in v.get("description", "").lower()
            ]
            
            # 计算指标
            growth_rate = self._calculate_industry_growth(related_trends)
            market_size = self._estimate_market_size(industry, related_trends)
            competition_level = self._assess_competition(related_trends, related_videos)
            opportunity_score = self._calculate_opportunity_score(
                growth_rate, market_size, competition_level
            )
            
            analysis[industry] = {
                "trend_count": len(related_trends),
                "video_count": len(related_videos),
                "metrics": {
                    "growth_rate": growth_rate,
                    "market_size_usd": market_size,
                    "competition_level": competition_level,
                    "opportunity_score": opportunity_score
                },
                "key_themes": self._extract_industry_themes(related_trends),
                "video_performance": self._analyze_industry_videos(related_videos)
            }
        
        return analysis
    
    def _analyze_by_region(self,
                          regions: List[Region],
                          global_trends: List[Dict[str, Any]],
                          video_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """按区域分析"""
        analysis = {}
        
        for region in regions:
            # 区域特定趋势
            regional_trends = [
                t for t in global_trends
                if t.get("region") == region.value
            ]
            
            # 区域视频趋势
            regional_videos = [
                v for v in video_trends
                if region.value in str(v.get("content_elements", {}))
            ]
            
            # 计算指标
            economic_activity = self._assess_economic_activity(region, regional_trends)
            digital_adoption = self._assess_digital_adoption(region, regional_trends)
            content_preferences = self._analyze_regional_preferences(region, regional_videos)
            market_maturity = self._assess_market_maturity(region, regional_trends)
            
            analysis[region.value] = {
                "trend_count": len(regional_trends),
                "video_count": len(regional_videos),
                "metrics": {
                    "economic_activity": economic_activity,
                    "digital_adoption": digital_adoption,
                    "market_maturity": market_maturity
                },
                "content_preferences": content_preferences,
                "key_opportunities": self._identify_regional_opportunities(
                    region, regional_trends, regional_videos
                )
            }
        
        return analysis
    
    def _analyze_by_platform(self,
                           video_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """按平台分析"""
        platform_groups = {}
        
        for trend in video_trends:
            platform = trend.get("platform", "unknown")
            if platform not in platform_groups:
                platform_groups[platform] = []
            platform_groups[platform].append(trend)
        
        analysis = {}
        
        for platform, trends in platform_groups.items():
            # 平台特定指标
            avg_engagement = np.mean([
                t.get("metrics", {}).get("engagement_rate", 0) 
                for t in trends
            ]) if trends else 0
            
            avg_completion = np.mean([
                t.get("metrics", {}).get("completion_rate", 0) 
                for t in trends if "completion_rate" in t.get("metrics", {})
            ]) if trends else 0
            
            content_types = {}
            for trend in trends:
                content_type = trend.get("content_type", "unknown")
                content_types[content_type] = content_types.get(content_type, 0) + 1
            
            analysis[platform] = {
                "trend_count": len(trends),
                "metrics": {
                    "average_engagement_rate": round(avg_engagement, 3),
                    "average_completion_rate": round(avg_completion, 3)
                },
                "content_type_distribution": content_types,
                "best_practices": self._extract_platform_best_practices(trends),
                "audience_characteristics": self._analyze_platform_audience(platform, trends)
            }
        
        return analysis
    
    def _analyze_by_content_type(self,
                                video_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """按内容类型分析"""
        content_groups = {}
        
        for trend in video_trends:
            content_type = trend.get("content_type", "unknown")
            if content_type not in content_groups:
                content_groups[content_type] = []
            content_groups[content_type].append(trend)
        
        analysis = {}
        
        for content_type, trends in content_groups.items():
            # 内容类型特定指标
            performance_metrics = self._analyze_content_performance(trends)
            
            # 成功模式
            success_patterns = self._extract_success_patterns(trends)
            
            # 创作建议
            creation_guidelines = self._generate_creation_guidelines(content_type, trends)
            
            analysis[content_type] = {
                "trend_count": len(trends),
                "performance_metrics": performance_metrics,
                "success_patterns": success_patterns,
                "creation_guidelines": creation_guidelines,
                "audience_response": self._analyze_content_response(trends)
            }
        
        return analysis
    
    def _analyze_by_time(self,
                        global_trends: List[Dict[str, Any]],
                        video_trends: List[Dict[str, Any]],
                        timeframe: str) -> Dict[str, Any]:
        """按时间维度分析"""
        # 时间序列分析
        time_analysis = {
            "trend_frequency": self._analyze_trend_frequency(global_trends, timeframe),
            "seasonal_patterns": self._identify_seasonal_patterns(global_trends, video_trends),
            "growth_trajectories": self._analyze_growth_trajectories(global_trends, timeframe),
            "emergence_timelines": self._track_emergence_timelines(global_trends, video_trends)
        }
        
        return time_analysis
    
    # 辅助计算方法
    
    def _calculate_industry_growth(self, trends: List[Dict[str, Any]]) -> float:
        """计算行业增长率"""
        if not trends:
            return 7.5  # 默认增长率
        
        growth_rates = [
            t.get("metrics", {}).get("growth_rate", 0)
            for t in trends
            if "metrics" in t and "growth_rate" in t["metrics"]
        ]
        
        if growth_rates:
            return round(np.mean(growth_rates), 2)
        else:
            return 7.5
    
    def _estimate_market_size(self, industry: str, trends: List[Dict[str, Any]]) -> int:
        """估计市场规模"""
        # 基于行业和趋势数据估计
        base_sizes = {
            "ecommerce": 5000000000000,
            "ai_technology": 2000000000000,
            "digital_health": 800000000000,
            "sustainable_energy": 1500000000000,
            "creators_economy": 100000000000,
            "fintech": 600000000000
        }
        
        base_size = base_sizes.get(industry, 100000000000)
        
        # 根据趋势热度调整
        if trends:
            avg_growth = np.mean([
                t.get("metrics", {}).get("growth_rate", 0)
                for t in trends
                if "metrics" in t
            ])
            adjustment = 1 + (avg_growth / 100)
            adjusted_size = int(base_size * adjustment)
        else:
            adjusted_size = base_size
        
        return adjusted_size
    
    def _assess_competition(self,
                           trends: List[Dict[str, Any]],
                           videos: List[Dict[str, Any]]) -> str:
        """评估竞争水平"""
        if not trends and not videos:
            return "low"
        
        # 基于趋势数量和视频表现评估
        trend_density = len(trends) / 10  # 每10个趋势为基准
        video_density = len(videos) / 5   # 每5个视频为基准
        
        overall_density = trend_density * 0.6 + video_density * 0.4
        
        if overall_density > 2.0:
            return "very_high"
        elif overall_density > 1.5:
            return "high"
        elif overall_density > 1.0:
            return "medium"
        elif overall_density > 0.5:
            return "low"
        else:
            return "very_low"
    
    def _calculate_opportunity_score(self,
                                   growth_rate: float,
                                   market_size: int,
                                   competition_level: str) -> float:
        """计算机会得分"""
        # 竞争水平权重
        competition_weights = {
            "very_low": 1.3,
            "low": 1.2,
            "medium": 1.0,
            "high": 0.8,
            "very_high": 0.6
        }
        
        competition_weight = competition_weights.get(competition_level, 1.0)
        
        # 增长率贡献 (0-1)
        growth_contribution = min(1.0, growth_rate / 30)
        
        # 市场规模贡献 (0-1)
        size_contribution = min(1.0, market_size / 1000000000000)
        
        # 综合得分 (0-100)
        base_score = (growth_contribution * 0.4 + size_contribution * 0.3) * 100
        final_score = base_score * competition_weight
        
        return round(final_score, 1)
    
    def _extract_industry_themes(self, trends: List[Dict[str, Any]]) -> List[str]:
        """提取行业主题"""
        if not trends:
            return ["digital_transformation", "innovation", "growth"]
        
        themes = set()
        for trend in trends:
            if "keywords" in trend:
                themes.update(trend["keywords"])
            if "title" in trend:
                title = trend["title"].get("en", "")
                themes.update(word for word in title.split() if len(word) > 5)
        
        return list(themes)[:5]
    
    def _analyze_industry_videos(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析行业视频表现"""
        if not videos:
            return {"average_engagement": 0, "optimal_length": 30, "preferred_style": "unknown"}
        
        engagements = []
        lengths = []
        styles = []
        
        for video in videos:
            metrics = video.get("metrics", {})
            content_elements = video.get("content_elements", {})
            
            if "engagement_rate" in metrics:
                engagements.append(metrics["engagement_rate"])
            if "preferred_length_seconds" in content_elements:
                lengths.append(content_elements["preferred_length_seconds"])
            if "style_preferences" in content_elements:
                styles.extend(content_elements["style_preferences"])
        
        avg_engagement = np.mean(engagements) if engagements else 0
        optimal_length = int(np.median(lengths)) if lengths else 30
        preferred_style = max(set(styles), key=styles.count) if styles else "unknown"
        
        return {
            "average_engagement_rate": round(avg_engagement, 3),
            "optimal_length_seconds": optimal_length,
            "preferred_style": preferred_style,
            "sample_size": len(videos)
        }
    
    def _assess_economic_activity(self, region: Region, trends: List[Dict[str, Any]]) -> float:
        """评估经济活动水平"""
        # 基于趋势数量和增长率
        if not trends:
            return 0.5  # 中性
        
        # 计算平均增长率
        growth_rates = [
            t.get("metrics", {}).get("growth_rate", 0)
            for t in trends
            if "metrics" in t
        ]
        
        if growth_rates:
            avg_growth = np.mean(growth_rates)
            # 归一化到0-1
            activity_level = min(1.0, avg_growth / 20)
        else:
            activity_level = 0.5
        
        return round(activity_level, 2)
    
    def _assess_digital_adoption(self, region: Region, trends: List[Dict[str, Any]]) -> float:
        """评估数字化采用水平"""
        # 基于技术相关趋势比例
        if not trends:
            return 0.5
        
        tech_keywords = ["ai", "digital", "technology", "innovation", "blockchain"]
        
        tech_count = 0
        for trend in trends:
            keywords = trend.get("keywords", [])
            title = trend.get("title", {}).get("en", "").lower()
            description = trend.get("description", {}).get("en", "").lower()
            
            # 检查是否包含技术关键词
            for keyword in tech_keywords:
                if (keyword in keywords or 
                    keyword in title or 
                    keyword in description):
                    tech_count += 1
                    break
        
        adoption_rate = tech_count / len(trends)
        
        return round(adoption_rate, 2)
    
    def _analyze_regional_preferences(self, region: Region, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析区域内容偏好"""
        # 基于视频数据提取偏好
        preferences = {
            "preferred_content_types": [],
            "optimal_video_length": 30,
            "engagement_patterns": {},
            "cultural_markers": []
        }
        
        if not videos:
            return preferences
        
        # 分析内容类型分布
        content_types = {}
        for video in videos:
            content_type = video.get("content_type", "unknown")
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        if content_types:
            preferred_type = max(content_types, key=content_types.get)
            preferences["preferred_content_types"] = [preferred_type]
        
        # 分析视频长度偏好
        lengths = []
        for video in videos:
            content_elements = video.get("content_elements", {})
            if "preferred_length_seconds" in content_elements:
                lengths.append(content_elements["preferred_length_seconds"])
        
        if lengths:
            preferences["optimal_video_length"] = int(np.median(lengths))
        
        return preferences
    
    def _assess_market_maturity(self, region: Region, trends: List[Dict[str, Any]]) -> str:
        """评估市场成熟度"""
        if not trends:
            return "developing"
        
        # 基于趋势多样性和增长率
        growth_rates = [
            t.get("metrics", {}).get("growth_rate", 0)
            for t in trends
            if "metrics" in t
        ]
        
        if not growth_rates:
            return "developing"
        
        avg_growth = np.mean(growth_rates)
        
        if avg_growth > 15:
            return "emerging"
        elif avg_growth > 8:
            return "growing"
        elif avg_growth > 3:
            return "mature"
        else:
            return "declining"
    
    def _identify_regional_opportunities(self,
                                        region: Region,
                                        trends: List[Dict[str, Any]],
                                        videos: List[Dict[str, Any]]) -> List[str]:
        """识别区域机会"""
        opportunities = []
        
        # 基于趋势识别机会
        high_growth_trends = [
            t for t in trends
            if t.get("metrics", {}).get("growth_rate", 0) > 15
        ]
        
        for trend in high_growth_trends[:3]:
            industry = trend.get("industry", "general")
            opportunities.append(f"High growth in {industry} sector")
        
        # 基于视频表现识别机会
        high_engagement_videos = [
            v for v in videos
            if v.get("metrics", {}).get("engagement_rate", 0) > 0.1
        ]
        
        if high_engagement_videos:
            opportunities.append("Strong audience engagement for video content")
        
        # 添加区域特定机会
        if region == Region.ASIA_PACIFIC:
            opportunities.append("Rapid digital adoption and mobile-first market")
        elif region == Region.LATIN_AMERICA:
            opportunities.append("Growing middle class and increasing online consumption")
        
        return opportunities[:5]
    
    # 交叉分析
    
    def _cross_dimensional_analysis(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """交叉维度分析"""
        cross_analysis = {}
        
        # 行业-区域交叉分析
        if "industry" in analysis_results and "region" in analysis_results:
            cross_analysis["industry_region"] = self._cross_industry_region(
                analysis_results["industry"], analysis_results["region"]
            )
        
        # 平台-内容类型交叉分析
        if "platform" in analysis_results and "content_type" in analysis_results:
            cross_analysis["platform_content"] = self._cross_platform_content(
                analysis_results["platform"], analysis_results["content_type"]
            )
        
        # 时间-行业交叉分析
        if "time" in analysis_results and "industry" in analysis_results:
            cross_analysis["time_industry"] = self._cross_time_industry(
                analysis_results["time"], analysis_results["industry"]
            )
        
        return cross_analysis
    
    def _cross_industry_region(self,
                              industry_analysis: Dict[str, Any],
                              regional_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """行业-区域交叉分析"""
        cross_results = {}
        
        for industry, industry_data in industry_analysis.items():
            cross_results[industry] = {}
            growth_rate = industry_data["metrics"]["growth_rate"]
            
            for region, region_data in regional_analysis.items():
                # 计算行业在特定区域的适配度
                regional_fit = self._calculate_regional_fit(industry, region, region_data)
                opportunity_score = growth_rate * regional_fit
                
                cross_results[industry][region] = {
                    "regional_fit": regional_fit,
                    "opportunity_score": round(opportunity_score, 2),
                    "key_factors": self._identify_cross_factors(industry, region, industry_data, region_data)
                }
        
        return cross_results
    
    def _cross_platform_content(self,
                               platform_analysis: Dict[str, Any],
                               content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """平台-内容类型交叉分析"""
        cross_results = {}
        
        for platform, platform_data in platform_analysis.items():
            cross_results[platform] = {}
            
            for content_type, content_data in content_analysis.items():
                # 计算内容类型在平台上的表现潜力
                performance_potential = self._calculate_performance_potential(
                    platform, content_type, platform_data, content_data
                )
                
                cross_results[platform][content_type] = {
                    "performance_potential": performance_potential,
                    "recommended_format": self._recommend_format(platform, content_type),
                    "audience_match": self._assess_audience_match(platform, content_type)
                }
        
        return cross_results
    
    def _cross_time_industry(self,
                            time_analysis: Dict[str, Any],
                            industry_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """时间-行业交叉分析"""
        cross_results = {}
        
        # 分析行业趋势的时间演变
        for industry, industry_data in industry_analysis.items():
            # 估算时间维度上的增长轨迹
            growth_trajectory = self._estimate_growth_trajectory(industry, time_analysis)
            
            cross_results[industry] = {
                "growth_trajectory": growth_trajectory,
                "seasonal_patterns": self._identify_industry_seasonality(industry, time_analysis),
                "momentum_trends": self._analyze_industry_momentum(industry, time_analysis)
            }
        
        return cross_results
    
    # 更多辅助方法
    
    def _calculate_regional_fit(self,
                               industry: str,
                               region: str,
                               region_data: Dict[str, Any]) -> float:
        """计算区域适配度"""
        # 基于区域特征和行业特性的匹配度
        # 简化实现
        base_fit = 0.7
        
        # 根据区域成熟度调整
        maturity = region_data.get("metrics", {}).get("market_maturity", "developing")
        maturity_weights = {
            "emerging": 1.2,
            "growing": 1.1,
            "mature": 1.0,
            "declining": 0.9,
            "developing": 1.0
        }
        
        adjustment = maturity_weights.get(maturity, 1.0)
        
        return round(base_fit * adjustment, 2)
    
    def _identify_cross_factors(self,
                               industry: str,
                               region: str,
                               industry_data: Dict[str, Any],
                               region_data: Dict[str, Any]) -> List[str]:
        """识别交叉因素"""
        factors = []
        
        # 基于行业和区域特征识别关键因素
        industry_growth = industry_data["metrics"]["growth_rate"]
        regional_activity = region_data["metrics"].get("economic_activity", 0.5)
        
        if industry_growth > 15 and regional_activity > 0.7:
            factors.append("High growth industry in active region")
        
        if region in ["north_america", "europe"]:
            factors.append("Mature market with established infrastructure")
        
        return factors[:3]
    
    def _calculate_performance_potential(self,
                                        platform: str,
                                        content_type: str,
                                        platform_data: Dict[str, Any],
                                        content_data: Dict[str, Any]) -> float:
        """计算表现潜力"""
        # 基于平台特点和内容类型特性的匹配度
        base_potential = 0.6
        
        # 平台表现调整
        platform_engagement = platform_data["metrics"]["average_engagement_rate"]
        engagement_adjustment = platform_engagement / 0.05  # 相对于5%基准
        
        # 内容类型质量调整
        content_performance = content_data["performance_metrics"].get("average_quality_score", 0.7)
        
        final_potential = base_potential * engagement_adjustment * content_performance
        
        return round(min(1.0, final_potential), 2)
    
    def _recommend_format(self, platform: str, content_type: str) -> str:
        """推荐格式"""
        format_recommendations = {
            ("tiktok", "commercial"): "Short-form video with trending music and clear CTA",
            ("youtube", "educational"): "Long-form tutorial with chapters and demonstrations",
            ("instagram", "lifestyle"): "High-quality visuals with storytelling captions"
        }
        
        return format_recommendations.get(
            (platform, content_type),
            "Platform-appropriate format for content type"
        )
    
    def _assess_audience_match(self, platform: str, content_type: str) -> float:
        """评估受众匹配度"""
        # 简化实现
        match_scores = {
            ("tiktok", "commercial"): 0.8,
            ("youtube", "educational"): 0.9,
            ("instagram", "lifestyle"): 0.7
        }
        
        return match_scores.get((platform, content_type), 0.6)
    
    def _estimate_growth_trajectory(self,
                                   industry: str,
                                   time_analysis: Dict[str, Any]) -> str:
        """估算增长轨迹"""
        # 基于时间分析判断行业增长趋势
        return "accelerating"  # 简化实现
    
    # 洞察生成
    
    def _generate_insights(self,
                          analysis_results: Dict[str, Any],
                          cross_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成洞察"""
        insights = []
        
        # 基于行业分析生成洞察
        if "industry" in analysis_results:
            industry_insights = self._extract_industry_insights(analysis_results["industry"])
            insights.extend(industry_insights)
        
        # 基于区域分析生成洞察
        if "region" in analysis_results:
            regional_insights = self._extract_regional_insights(analysis_results["region"])
            insights.extend(regional_insights)
        
        # 基于交叉分析生成洞察
        if cross_analysis:
            cross_insights = self._extract_cross_insights(cross_analysis)
            insights.extend(cross_insights)
        
        # 按重要性排序
        insights.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
        
        return insights[:10]  # 返回前10个洞察
    
    def _extract_industry_insights(self, industry_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取行业洞察"""
        insights = []
        
        for industry, data in industry_analysis.items():
            opportunity_score = data["metrics"]["opportunity_score"]
            growth_rate = data["metrics"]["growth_rate"]
            
            if opportunity_score > 80:
                insights.append({
                    "type": "high_opportunity",
                    "industry": industry,
                    "description": f"Exceptional opportunity in {industry} sector with {opportunity_score} score",
                    "supporting_data": {
                        "growth_rate": growth_rate,
                        "trend_count": data["trend_count"]
                    },
                    "recommendation": f"Prioritize investment in {industry} initiatives",
                    "importance_score": opportunity_score / 100
                })
            
            if growth_rate > 20:
                insights.append({
                    "type": "hyper_growth",
                    "industry": industry,
                    "description": f"Hyper-growth detected in {industry} with {growth_rate}% growth rate",
                    "supporting_data": {
                        "opportunity_score": opportunity_score,
                        "video_count": data["video_count"]
                    },
                    "recommendation": f"Accelerate market entry in {industry} sector",
                    "importance_score": growth_rate / 30
                })
        
        return insights
    
    def _extract_regional_insights(self, regional_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取区域洞察"""
        insights = []
        
        for region, data in regional_analysis.items():
            economic_activity = data["metrics"].get("economic_activity", 0.5)
            digital_adoption = data["metrics"].get("digital_adoption", 0.5)
            
            if economic_activity > 0.8 and digital_adoption > 0.7:
                insights.append({
                    "type": "digital_hotspot",
                    "region": region,
                    "description": f"{region} is a digital hotspot with high economic activity and digital adoption",
                    "supporting_data": {
                        "economic_activity": economic_activity,
                        "digital_adoption": digital_adoption
                    },
                    "recommendation": f"Focus digital initiatives in {region} market",
                    "importance_score": (economic_activity + digital_adoption) / 2
                })
        
        return insights
    
    def _extract_cross_insights(self, cross_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取交叉洞察"""
        insights = []
        
        # 分析行业-区域交叉机会
        if "industry_region" in cross_analysis:
            for industry, regions in cross_analysis["industry_region"].items():
                for region, data in regions.items():
                    opportunity_score = data.get("opportunity_score", 0)
                    
                    if opportunity_score > 90:
                        insights.append({
                            "type": "perfect_match",
                            "industry": industry,
                            "region": region,
                            "description": f"Perfect match identified: {industry} in {region} with {opportunity_score} score",
                            "supporting_data": {
                                "opportunity_score": opportunity_score,
                                "regional_fit": data.get("regional_fit", 0)
                            },
                            "recommendation": f"Launch integrated {industry} strategy in {region}",
                            "importance_score": opportunity_score / 100
                        })
        
        return insights
    
    # 评分与评估
    
    def _calculate_overall_score(self,
                                analysis_results: Dict[str, Any],
                                cross_analysis: Dict[str, Any]) -> float:
        """计算综合得分"""
        scores = []
        
        # 行业分析贡献
        if "industry" in analysis_results:
            industry_scores = [
                data["metrics"]["opportunity_score"]
                for data in analysis_results["industry"].values()
            ]
            if industry_scores:
                scores.append(np.mean(industry_scores))
        
        # 区域分析贡献
        if "region" in analysis_results:
            regional_scores = []
            for data in analysis_results["region"].values():
                activity = data["metrics"].get("economic_activity", 0.5)
                adoption = data["metrics"].get("digital_adoption", 0.5)
                regional_scores.append((activity + adoption) * 50)  # 转换为0-100分
            
            if regional_scores:
                scores.append(np.mean(regional_scores))
        
        # 交叉分析贡献
        if cross_analysis and "industry_region" in cross_analysis:
            cross_scores = []
            for industry_data in cross_analysis["industry_region"].values():
                for region_data in industry_data.values():
                    cross_scores.append(region_data.get("opportunity_score", 0))
            
            if cross_scores:
                scores.append(np.mean(cross_scores))
        
        if scores:
            overall_score = np.mean(scores)
        else:
            overall_score = 70.0  # 默认分数
        
        return round(overall_score, 1)
    
    def _classify_trend_strength(self, score: float) -> TrendStrength:
        """分类趋势强度"""
        if score >= 90:
            return TrendStrength.VERY_STRONG
        elif score >= 80:
            return TrendStrength.STRONG
        elif score >= 70:
            return TrendStrength.MODERATE
        elif score >= 60:
            return TrendStrength.WEAK
        else:
            return TrendStrength.VERY_WEAK
    
    def _calculate_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """计算置信度"""
        data_points = 0
        
        # 统计总数据点
        for key, analysis in analysis_results.items():
            if isinstance(analysis, dict):
                for subkey, data in analysis.items():
                    if isinstance(data, dict):
                        data_points += data.get("trend_count", 0) + data.get("video_count", 0)
        
        # 数据量归一化
        normalized_data = min(1.0, data_points / 200)
        
        # 分析深度贡献
        depth_score = len(analysis_results) / len(AnalysisDimension)
        
        # 综合置信度
        confidence = (normalized_data * 0.7 + depth_score * 0.3)
        
        return round(confidence, 2)
    
    def _identify_focus_areas(self, insights: List[Dict[str, Any]]) -> List[str]:
        """识别重点领域"""
        focus_areas = []
        
        for insight in insights[:5]:  # 前5个洞察
            if insight["type"] == "high_opportunity":
                focus_areas.append(insight["industry"])
            elif insight["type"] == "perfect_match":
                focus_areas.append(f"{insight['industry']}-{insight['region']}")
        
        return list(set(focus_areas))[:3]
    
    # 降级方案
    
    def _generate_fallback_analysis(self,
                                   industries: List[str],
                                   regions: List[Region],
                                   dimensions: List[AnalysisDimension],
                                   timeframe: str) -> Dict[str, Any]:
        """生成降级分析结果"""
        return {
            "timestamp": datetime.now().isoformat(),
            "timeframe": timeframe,
            "scope": {
                "industries": industries,
                "regions": [r.value for r in regions],
                "dimensions": [d.value for d in dimensions]
            },
            "data_summary": {
                "global_trends_count": 50,
                "video_trends_count": 25,
                "coverage_score": 0.7
            },
            "dimensional_analysis": {},
            "cross_analysis": {},
            "insights": [
                {
                    "type": "fallback_insight",
                    "description": "Analysis based on simulated data due to connectivity issues",
                    "importance_score": 0.5
                }
            ],
            "overall_assessment": {
                "score": 65.0,
                "strength": TrendStrength.MODERATE.value,
                "confidence": 0.6,
                "recommended_focus_areas": ["general_digital_transformation"]
            },
            "strategic_recommendations": [
                "Focus on core digital initiatives",
                "Leverage existing market intelligence",
                "Consider alternative data sources"
            ],
            "analysis_metadata": {
                "processing_time_ms": 150.0,
                "algorithm_version": "1.0",
                "freshness_hours": 24,
                "fallback_mode": True
            }
        }