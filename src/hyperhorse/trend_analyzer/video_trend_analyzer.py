#!/usr/bin/env python3
"""
视频内容趋势分析器
基于Firecrawl全球商业情报数据，实时分析全球各行业视频内容趋势
包括热门内容识别、风格偏好分析、转化效果预测等功能
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from enum import Enum

from ..data_sources.firecrawl_adapter import FirecrawlAdapter, Region, Language

logger = logging.getLogger(__name__)


class ContentStyle(str, Enum):
    """内容风格"""
    FAST_PACED = "fast_paced"  # 快节奏
    EDUCATIONAL = "educational"  # 教育性
    ENTERTAINING = "entertaining"  # 娱乐性
    INSPIRATIONAL = "inspirational"  # 励志性
    MINIMALIST = "minimalist"  # 极简主义
    VISUAL_STORYTELLING = "visual_storytelling"  # 视觉叙事


class EngagementMetric(str, Enum):
    """互动指标"""
    VIEW_COUNT = "view_count"
    LIKE_RATIO = "like_ratio"
    COMMENT_COUNT = "comment_count"
    SHARE_COUNT = "share_count"
    COMPLETION_RATE = "completion_rate"
    CLICK_THROUGH_RATE = "click_through_rate"


class VideoTrendAnalyzer:
    """视频趋势分析器"""
    
    def __init__(self, firecrawl_adapter: Optional[FirecrawlAdapter] = None):
        """
        初始化视频趋势分析器
        
        Args:
            firecrawl_adapter: Firecrawl适配器实例，可选
        """
        self.firecrawl_adapter = firecrawl_adapter or FirecrawlAdapter()
        
        # 平台权重配置（基于商业转化潜力）
        self.platform_weights = {
            "tiktok": {"discovery": 0.9, "conversion": 0.7, "retention": 0.6},
            "youtube": {"discovery": 0.7, "conversion": 0.8, "retention": 0.9},
            "instagram": {"discovery": 0.8, "conversion": 0.6, "retention": 0.7},
            "facebook": {"discovery": 0.6, "conversion": 0.5, "retention": 0.8},
            "twitter": {"discovery": 0.5, "conversion": 0.4, "retention": 0.5}
        }
        
        # 行业视频趋势模式
        self.industry_patterns = self._load_industry_patterns()
        
        # 风格偏好模型
        self.style_preferences = self._load_style_preferences()
        
        logger.info("视频趋势分析器初始化完成")
    
    def _load_industry_patterns(self) -> Dict[str, Dict[str, Any]]:
        """加载行业视频趋势模式"""
        return {
            "ecommerce": {
                "preferred_length": [15, 30, 60],  # 秒
                "optimal_style": [ContentStyle.FAST_PACED, ContentStyle.VISUAL_STORYTELLING],
                "key_elements": ["product_showcase", "demonstration", "testimonial"],
                "conversion_factors": ["clear_cta", "limited_time_offer", "social_proof"]
            },
            "ai_technology": {
                "preferred_length": [60, 180, 300],
                "optimal_style": [ContentStyle.EDUCATIONAL, ContentStyle.INSPIRATIONAL],
                "key_elements": ["demo", "explanation", "use_cases"],
                "conversion_factors": ["technical_depth", "expert_endorsement", "case_studies"]
            },
            "digital_health": {
                "preferred_length": [30, 90, 180],
                "optimal_style": [ContentStyle.EDUCATIONAL, ContentStyle.INSPIRATIONAL],
                "key_elements": ["testimonial", "expert_interview", "educational_content"],
                "conversion_factors": ["trust_signals", "clinical_evidence", "patient_stories"]
            },
            "sustainable_energy": {
                "preferred_length": [60, 180, 300],
                "optimal_style": [ContentStyle.INSPIRATIONAL, ContentStyle.EDUCATIONAL],
                "key_elements": ["visual_impact", "data_visualization", "future_scenarios"],
                "conversion_factors": ["environmental_impact", "cost_savings", "government_incentives"]
            },
            "creators_economy": {
                "preferred_length": [15, 30, 60],
                "optimal_style": [ContentStyle.ENTERTAINING, ContentStyle.INSPIRATIONAL],
                "key_elements": ["behind_the_scenes", "tutorial", "community_interaction"],
                "conversion_factors": ["authenticity", "community_engagement", "monetization_tips"]
            }
        }
    
    def _load_style_preferences(self) -> Dict[str, Dict[str, Any]]:
        """加载风格偏好模型"""
        return {
            Region.NORTH_AMERICA.value: {
                "preferred_styles": [ContentStyle.FAST_PACED, ContentStyle.ENTERTAINING],
                "optimal_length": [15, 30, 60],
                "cultural_markers": ["direct_communication", "individual_achievement", "innovation"],
                "avoid_elements": ["excessive_formality", "indirect_messaging"]
            },
            Region.EUROPE.value: {
                "preferred_styles": [ContentStyle.MINIMALIST, ContentStyle.EDUCATIONAL],
                "optimal_length": [30, 60, 180],
                "cultural_markers": ["sophistication", "sustainability", "multiculturalism"],
                "avoid_elements": ["exaggerated_claims", "low_quality_production"]
            },
            Region.ASIA_PACIFIC.value: {
                "preferred_styles": [ContentStyle.VISUAL_STORYTELLING, ContentStyle.INSPIRATIONAL],
                "optimal_length": [15, 30, 60],
                "cultural_markers": ["harmony", "respect_for_tradition", "technological_innovation"],
                "avoid_elements": ["confrontational_content", "individualistic_focus"]
            },
            Region.LATIN_AMERICA.value: {
                "preferred_styles": [ContentStyle.ENTERTAINING, ContentStyle.INSPIRATIONAL],
                "optimal_length": [30, 60, 90],
                "cultural_markers": ["passion", "community", "music_and_dance"],
                "avoid_elements": ["sterile_presentation", "lack_of_emotional_connection"]
            }
        }
    
    def analyze_global_video_trends(self,
                                   industries: List[str] = None,
                                   regions: List[Region] = None,
                                   timeframe: str = "7d") -> Dict[str, Any]:
        """
        分析全球视频趋势
        
        Args:
            industries: 行业列表，默认分析所有行业
            regions: 区域列表，默认全球
            timeframe: 时间范围
            
        Returns:
            全球视频趋势分析结果
        """
        start_time = time.time()
        
        if industries is None:
            industries = list(self.industry_patterns.keys())
        if regions is None:
            regions = [Region.GLOBAL]
        
        logger.info(f"开始分析全球视频趋势: 行业={industries}, 区域={regions}")
        
        try:
            # 获取全球商业趋势数据
            global_trends = self.firecrawl_adapter.fetch_global_trends(limit=50)
            
            # 获取视频内容趋势数据
            video_trends = self.firecrawl_adapter.fetch_video_content_trends(
                platform="all",
                content_type="commercial",
                timeframe=timeframe,
                limit=30
            )
            
            # 分析行业趋势
            industry_analysis = self._analyze_industries(industries, global_trends, video_trends)
            
            # 分析区域偏好
            regional_analysis = self._analyze_regions(regions, video_trends)
            
            # 识别热门内容模式
            content_patterns = self._identify_content_patterns(video_trends)
            
            # 预测转化效果
            conversion_predictions = self._predict_conversion_effectiveness(
                industry_analysis, regional_analysis, content_patterns
            )
            
            # 生成推荐策略
            recommendations = self._generate_recommendations(
                industry_analysis, regional_analysis, content_patterns, conversion_predictions
            )
            
            # 组装结果
            result = {
                "timestamp": datetime.now().isoformat(),
                "timeframe": timeframe,
                "industries_analyzed": industries,
                "regions_analyzed": [r.value for r in regions],
                "industry_analysis": industry_analysis,
                "regional_analysis": regional_analysis,
                "content_patterns": content_patterns,
                "conversion_predictions": conversion_predictions,
                "recommendations": recommendations,
                "analysis_metadata": {
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    "trends_processed": len(global_trends) + len(video_trends),
                    "confidence_score": self._calculate_confidence_score(
                        industry_analysis, regional_analysis
                    )
                }
            }
            
            logger.info(f"全球视频趋势分析完成: {len(industries)}个行业, {len(regions)}个区域")
            
            return result
            
        except Exception as e:
            logger.error(f"全球视频趋势分析失败: {e}")
            return self._generate_fallback_analysis(industries, regions, timeframe)
    
    def analyze_video_content_potential(self,
                                       content_description: str,
                                       target_industry: str,
                                       target_region: Region) -> Dict[str, Any]:
        """
        分析视频内容潜力
        
        Args:
            content_description: 内容描述
            target_industry: 目标行业
            target_region: 目标区域
            
        Returns:
            内容潜力分析结果
        """
        try:
            # 获取市场偏好数据
            market_preferences = self.firecrawl_adapter.fetch_market_preferences(
                target_region, target_industry
            )
            
            # 分析内容匹配度
            content_match_score = self._calculate_content_match(
                content_description, target_industry, target_region, market_preferences
            )
            
            # 预测互动效果
            engagement_prediction = self._predict_engagement(
                content_description, target_industry, target_region
            )
            
            # 预测商业转化
            conversion_prediction = self._predict_conversion(
                content_match_score, engagement_prediction, target_industry
            )
            
            result = {
                "content_description": content_description,
                "target_industry": target_industry,
                "target_region": target_region.value,
                "content_match_score": content_match_score,
                "engagement_prediction": engagement_prediction,
                "conversion_prediction": conversion_prediction,
                "optimization_suggestions": self._generate_optimization_suggestions(
                    content_description, content_match_score, market_preferences
                ),
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"视频内容潜力分析失败: {e}")
            return self._generate_fallback_content_analysis(
                content_description, target_industry, target_region
            )
    
    def get_platform_recommendations(self,
                                   industry: str,
                                   content_style: ContentStyle,
                                   business_goal: str = "awareness") -> List[Dict[str, Any]]:
        """
        获取平台推荐
        
        Args:
            industry: 行业
            content_style: 内容风格
            business_goal: 商业目标 (awareness, engagement, conversion, retention)
            
        Returns:
            平台推荐列表
        """
        platform_scores = []
        
        for platform, weights in self.platform_weights.items():
            # 计算平台得分
            score = self._calculate_platform_score(
                platform, industry, content_style, business_goal, weights
            )
            
            platform_scores.append({
                "platform": platform,
                "score": score,
                "weights": weights,
                "recommendation_reason": self._get_platform_recommendation_reason(
                    platform, industry, content_style, business_goal, score
                )
            })
        
        # 按得分排序
        platform_scores.sort(key=lambda x: x["score"], reverse=True)
        
        return platform_scores[:3]  # 返回前三名
    
    # 内部分析方法
    
    def _analyze_industries(self,
                           industries: List[str],
                           global_trends: List[Dict[str, Any]],
                           video_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析行业趋势"""
        analysis = {}
        
        for industry in industries:
            # 过滤相关趋势
            industry_trends = [
                t for t in global_trends 
                if t.get("industry") == industry or industry in t.get("keywords", [])
            ]
            
            industry_videos = [
                v for v in video_trends
                if industry in v.get("description", "").lower() or 
                   industry in str(v.get("content_elements", {}))
            ]
            
            # 计算行业热度
            heat_score = self._calculate_industry_heat(industry_trends, industry_videos)
            
            # 识别关键趋势
            key_trends = self._identify_key_trends(industry_trends)
            
            # 分析视频表现
            video_performance = self._analyze_video_performance(industry_videos)
            
            analysis[industry] = {
                "heat_score": heat_score,
                "trend_count": len(industry_trends),
                "video_count": len(industry_videos),
                "key_trends": key_trends,
                "video_performance": video_performance,
                "growth_potential": self._estimate_growth_potential(industry, heat_score)
            }
        
        return analysis
    
    def _analyze_regions(self,
                        regions: List[Region],
                        video_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析区域偏好"""
        analysis = {}
        
        for region in regions:
            region_preferences = self.style_preferences.get(region.value, {})
            
            # 分析区域内容偏好
            content_preferences = self._analyze_regional_content_preferences(
                region, video_trends
            )
            
            analysis[region.value] = {
                "style_preferences": region_preferences,
                "content_preferences": content_preferences,
                "localization_requirements": self._get_localization_requirements(region),
                "cultural_sensitivities": self._get_cultural_sensitivities(region)
            }
        
        return analysis
    
    def _identify_content_patterns(self, video_trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别内容模式"""
        patterns = []
        
        if not video_trends:
            return patterns
        
        # 按平台分组
        platform_groups = {}
        for trend in video_trends:
            platform = trend.get("platform", "unknown")
            if platform not in platform_groups:
                platform_groups[platform] = []
            platform_groups[platform].append(trend)
        
        # 分析每个平台的热门模式
        for platform, trends in platform_groups.items():
            # 分析内容类型分布
            content_types = {}
            for trend in trends:
                content_type = trend.get("content_type", "unknown")
                content_types[content_type] = content_types.get(content_type, 0) + 1
            
            # 分析成功因素
            success_factors = self._extract_success_factors(trends)
            
            # 分析最佳实践
            best_practices = self._extract_best_practices(trends)
            
            patterns.append({
                "platform": platform,
                "trend_count": len(trends),
                "content_type_distribution": content_types,
                "success_factors": success_factors,
                "best_practices": best_practices,
                "recommended_approach": self._generate_platform_recommendation(platform, trends)
            })
        
        return patterns
    
    def _predict_conversion_effectiveness(self,
                                         industry_analysis: Dict[str, Any],
                                         regional_analysis: Dict[str, Any],
                                         content_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """预测转化效果"""
        predictions = {}
        
        for industry, analysis in industry_analysis.items():
            heat_score = analysis.get("heat_score", 50)
            growth_potential = analysis.get("growth_potential", "medium")
            
            # 计算基础转化潜力
            base_potential = self._calculate_base_conversion_potential(heat_score, growth_potential)
            
            # 考虑区域因素
            regional_adjustment = self._calculate_regional_adjustment(regional_analysis, industry)
            
            # 考虑内容模式因素
            content_adjustment = self._calculate_content_adjustment(content_patterns, industry)
            
            # 综合预测
            final_prediction = base_potential * regional_adjustment * content_adjustment
            
            predictions[industry] = {
                "base_potential": base_potential,
                "regional_adjustment": regional_adjustment,
                "content_adjustment": content_adjustment,
                "final_prediction": final_prediction,
                "confidence_level": self._calculate_prediction_confidence(
                    analysis, regional_analysis, content_patterns
                )
            }
        
        return predictions
    
    # 计算辅助方法
    
    def _calculate_industry_heat(self,
                                trends: List[Dict[str, Any]],
                                videos: List[Dict[str, Any]]) -> float:
        """计算行业热度"""
        if not trends and not videos:
            return 50.0  # 中性
        
        # 趋势权重
        trend_score = 0.0
        if trends:
            avg_growth = np.mean([t.get("metrics", {}).get("growth_rate", 0) for t in trends])
            trend_score = min(100.0, avg_growth * 4)  # 转换为0-100分
        
        # 视频表现权重
        video_score = 0.0
        if videos:
            avg_engagement = np.mean([v.get("metrics", {}).get("engagement_rate", 0) * 100 for v in videos])
            video_score = min(100.0, avg_engagement * 2)
        
        # 综合得分
        if trend_score > 0 and video_score > 0:
            return (trend_score * 0.6 + video_score * 0.4)
        elif trend_score > 0:
            return trend_score
        else:
            return video_score
    
    def _identify_key_trends(self, trends: List[Dict[str, Any]]) -> List[str]:
        """识别关键趋势"""
        if not trends:
            return []
        
        # 按置信度排序
        sorted_trends = sorted(trends, key=lambda x: x.get("confidence_score", 0), reverse=True)
        
        # 提取关键趋势主题
        key_themes = set()
        for trend in sorted_trends[:5]:  # 前5个
            title = trend.get("title", {}).get("en", "")
            if title:
                # 提取关键词
                words = title.lower().split()
                for word in words:
                    if len(word) > 5 and word not in ["trend", "emerging", "business", "sector"]:
                        key_themes.add(word)
        
        return list(key_themes)[:3] if key_themes else []
    
    def _analyze_video_performance(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析视频表现"""
        if not videos:
            return {"average_engagement": 0, "optimal_length": 30, "preferred_style": "unknown"}
        
        # 计算平均互动率
        engagements = [v.get("metrics", {}).get("engagement_rate", 0) for v in videos]
        avg_engagement = np.mean(engagements) if engagements else 0
        
        # 分析最佳时长
        lengths = []
        for v in videos:
            length = v.get("content_elements", {}).get("preferred_length_seconds", 30)
            lengths.append(length)
        
        optimal_length = int(np.median(lengths)) if lengths else 30
        
        # 分析风格偏好
        styles = []
        for v in videos:
            style_prefs = v.get("content_elements", {}).get("style_preferences", [])
            if style_prefs:
                styles.extend(style_prefs)
        
        preferred_style = max(set(styles), key=styles.count) if styles else "unknown"
        
        return {
            "average_engagement": round(avg_engagement, 3),
            "optimal_length": optimal_length,
            "preferred_style": preferred_style,
            "sample_size": len(videos)
        }
    
    def _estimate_growth_potential(self, industry: str, heat_score: float) -> str:
        """估计增长潜力"""
        if heat_score > 80:
            return "very_high"
        elif heat_score > 65:
            return "high"
        elif heat_score > 50:
            return "medium"
        elif heat_score > 35:
            return "low"
        else:
            return "very_low"
    
    def _analyze_regional_content_preferences(self,
                                             region: Region,
                                             video_trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析区域内容偏好"""
        # 简化实现：基于预定义模型
        # 实际应用中应从数据中分析
        return self.style_preferences.get(region.value, {})
    
    def _get_localization_requirements(self, region: Region) -> List[str]:
        """获取本地化要求"""
        requirements = {
            Region.NORTH_AMERICA: ["language_localization", "currency_conversion", "measurement_conversion"],
            Region.EUROPE: ["multilingual_support", "gdpr_compliance", "currency_localization"],
            Region.ASIA_PACIFIC: ["language_localization", "cultural_adaptation", "payment_methods"],
            Region.LATIN_AMERICA: ["language_localization", "cultural_references", "local_payment_gateways"]
        }
        return requirements.get(region, ["basic_localization"])
    
    def _get_cultural_sensitivities(self, region: Region) -> List[str]:
        """获取文化敏感性"""
        sensitivities = {
            Region.NORTH_AMERICA: ["diversity_inclusion", "political_correctness", "regional_differences"],
            Region.EUROPE: ["environmental_sustainability", "social_responsibility", "historical_context"],
            Region.ASIA_PACIFIC: ["hierarchical_respect", "face_culture", "group_harmony"],
            Region.LATIN_AMERICA: ["family_values", "religious_sensitivities", "social_hierarchy"]
        }
        return sensitivities.get(region, ["general_cultural_sensitivity"])
    
    def _extract_success_factors(self, trends: List[Dict[str, Any]]) -> List[str]:
        """提取成功因素"""
        if not trends:
            return ["engaging_content", "clear_messaging", "visual_appeal"]
        
        factors = []
        for trend in trends:
            if "recommended_strategies" in trend:
                factors.extend(trend["recommended_strategies"])
        
        # 去重并排序
        unique_factors = list(set(factors))
        return unique_factors[:5] if unique_factors else ["engaging_content", "clear_messaging"]
    
    def _extract_best_practices(self, trends: List[Dict[str, Any]]) -> List[str]:
        """提取最佳实践"""
        if not trends:
            return ["use_high_quality_visuals", "keep_content_concise", "include_clear_cta"]
        
        practices = []
        for trend in trends:
            if "top_performing_examples" in trend:
                examples = trend["top_performing_examples"]
                for example in examples:
                    if "key_insights" in example:
                        practices.append(example["key_insights"])
        
        return list(set(practices))[:5] if practices else ["use_high_quality_visuals"]
    
    def _generate_platform_recommendation(self,
                                         platform: str,
                                         trends: List[Dict[str, Any]]) -> str:
        """生成平台推荐"""
        recommendations = {
            "tiktok": "Focus on short, engaging content with trending music and visual effects",
            "youtube": "Create longer, educational content with high production value",
            "instagram": "Use high-quality visuals and stories for brand building",
            "facebook": "Leverage community engagement and group interactions",
            "twitter": "Focus on timely, conversation-driving content"
        }
        
        return recommendations.get(platform, "Create platform-appropriate content")
    
    def _calculate_base_conversion_potential(self, heat_score: float, growth_potential: str) -> float:
        """计算基础转化潜力"""
        # 热度得分转换为0-1范围
        heat_normalized = heat_score / 100
        
        # 增长潜力权重
        growth_weights = {
            "very_high": 1.3,
            "high": 1.2,
            "medium": 1.0,
            "low": 0.8,
            "very_low": 0.6
        }
        
        growth_weight = growth_weights.get(growth_potential, 1.0)
        
        return heat_normalized * growth_weight
    
    def _calculate_regional_adjustment(self,
                                      regional_analysis: Dict[str, Any],
                                      industry: str) -> float:
        """计算区域调整因子"""
        # 简化实现：基于区域偏好匹配度
        # 实际应用中应更复杂
        return 1.0  # 中性调整
    
    def _calculate_content_adjustment(self,
                                     content_patterns: List[Dict[str, Any]],
                                     industry: str) -> float:
        """计算内容调整因子"""
        if not content_patterns:
            return 1.0
        
        # 计算行业相关内容模式的平均表现
        relevant_patterns = [
            p for p in content_patterns 
            if industry.lower() in str(p).lower()
        ]
        
        if not relevant_patterns:
            return 0.9  # 保守调整
        
        # 基于成功因素数量和质量调整
        success_factors_count = sum(len(p.get("success_factors", [])) for p in relevant_patterns)
        avg_factors = success_factors_count / len(relevant_patterns)
        
        # 转换为调整因子 (0.8-1.2)
        adjustment = 0.8 + (avg_factors * 0.2)
        
        return min(1.2, max(0.8, adjustment))
    
    def _calculate_prediction_confidence(self,
                                        industry_analysis: Dict[str, Any],
                                        regional_analysis: Dict[str, Any],
                                        content_patterns: List[Dict[str, Any]]) -> float:
        """计算预测置信度"""
        # 基于数据量和一致性计算置信度
        trend_count = industry_analysis.get("trend_count", 0)
        video_count = industry_analysis.get("video_count", 0)
        
        # 数据量贡献
        data_contribution = min(1.0, (trend_count + video_count) / 50)
        
        # 一致性贡献（简化）
        consistency_score = 0.7  # 假设中等一致性
        
        # 综合置信度
        confidence = (data_contribution * 0.6 + consistency_score * 0.4)
        
        return round(confidence, 2)
    
    def _calculate_content_match(self,
                                content_description: str,
                                industry: str,
                                region: Region,
                                market_preferences: Dict[str, Any]) -> float:
        """计算内容匹配度"""
        # 简化实现：基于关键词匹配
        # 实际应用中应使用NLP模型
        
        industry_keywords = self._get_industry_keywords(industry)
        region_keywords = self._get_region_keywords(region)
        
        content_lower = content_description.lower()
        
        # 计算关键词匹配度
        industry_match = self._calculate_keyword_match(content_lower, industry_keywords)
        region_match = self._calculate_keyword_match(content_lower, region_keywords)
        
        # 综合匹配度
        match_score = (industry_match * 0.7 + region_match * 0.3)
        
        return round(match_score, 2)
    
    def _predict_engagement(self,
                           content_description: str,
                           industry: str,
                           region: Region) -> Dict[str, Any]:
        """预测互动效果"""
        # 简化实现：基于行业和区域基准
        # 实际应用中应使用预测模型
        
        base_engagement = 0.05  # 5%基准互动率
        
        # 行业调整
        industry_boost = self._get_industry_engagement_boost(industry)
        
        # 区域调整
        region_boost = self._get_region_engagement_boost(region)
        
        predicted_engagement = base_engagement * (1 + industry_boost) * (1 + region_boost)
        
        return {
            "predicted_engagement_rate": round(predicted_engagement, 3),
            "confidence_interval": [round(predicted_engagement * 0.8, 3), round(predicted_engagement * 1.2, 3)],
            "key_drivers": [f"{industry}_relevance", f"{region.value}_cultural_fit"]
        }
    
    def _predict_conversion(self,
                           content_match_score: float,
                           engagement_prediction: Dict[str, Any],
                           industry: str) -> Dict[str, Any]:
        """预测商业转化"""
        base_conversion_rate = 0.02  # 2%基准转化率
        
        # 内容匹配度调整
        match_adjustment = content_match_score
        
        # 互动预测调整
        engagement_rate = engagement_prediction.get("predicted_engagement_rate", 0.05)
        engagement_adjustment = engagement_rate / 0.05  # 相对于基准
        
        # 行业特定调整
        industry_adjustment = self._get_industry_conversion_adjustment(industry)
        
        predicted_conversion = base_conversion_rate * match_adjustment * engagement_adjustment * industry_adjustment
        
        return {
            "predicted_conversion_rate": round(predicted_conversion, 4),
            "key_factors": ["content_relevance", "engagement_potential", "industry_fit"],
            "optimization_priority": self._get_conversion_optimization_priority(
                match_adjustment, engagement_adjustment, industry_adjustment
            )
        }
    
    # 辅助计算方法
    
    def _get_industry_keywords(self, industry: str) -> List[str]:
        """获取行业关键词"""
        keyword_map = {
            "ecommerce": ["product", "shopping", "online", "store", "buy", "sale"],
            "ai_technology": ["ai", "artificial intelligence", "machine learning", "technology", "innovation"],
            "digital_health": ["health", "wellness", "medical", "fitness", "care", "doctor"]
        }
        return keyword_map.get(industry, ["business", "innovation", "growth"])
    
    def _get_region_keywords(self, region: Region) -> List[str]:
        """获取区域关键词"""
        keyword_map = {
            Region.NORTH_AMERICA: ["usa", "canada", "american", "north america"],
            Region.EUROPE: ["europe", "eu", "france", "germany", "uk", "italy"],
            Region.ASIA_PACIFIC: ["asia", "china", "japan", "korea", "india", "singapore"]
        }
        return keyword_map.get(region, ["global", "international"])
    
    def _calculate_keyword_match(self, text: str, keywords: List[str]) -> float:
        """计算关键词匹配度"""
        if not keywords:
            return 0.5
        
        matches = 0
        for keyword in keywords:
            if keyword in text:
                matches += 1
        
        return matches / len(keywords)
    
    def _get_industry_engagement_boost(self, industry: str) -> float:
        """获取行业互动提升率"""
        boost_map = {
            "ecommerce": 0.2,  # +20%
            "ai_technology": 0.3,
            "digital_health": 0.1,
            "sustainable_energy": 0.15,
            "creators_economy": 0.25
        }
        return boost_map.get(industry, 0.0)
    
    def _get_region_engagement_boost(self, region: Region) -> float:
        """获取区域互动提升率"""
        boost_map = {
            Region.NORTH_AMERICA: 0.1,
            Region.EUROPE: 0.05,
            Region.ASIA_PACIFIC: 0.15,
            Region.LATIN_AMERICA: 0.2
        }
        return boost_map.get(region, 0.0)
    
    def _get_industry_conversion_adjustment(self, industry: str) -> float:
        """获取行业转化调整因子"""
        adjustment_map = {
            "ecommerce": 1.5,  # 电商转化率较高
            "ai_technology": 1.2,
            "digital_health": 1.1,
            "sustainable_energy": 1.0,
            "creators_economy": 1.3
        }
        return adjustment_map.get(industry, 1.0)
    
    def _get_conversion_optimization_priority(self,
                                             match_adjustment: float,
                                             engagement_adjustment: float,
                                             industry_adjustment: float) -> str:
        """获取转化优化优先级"""
        scores = {
            "content_match": match_adjustment,
            "engagement": engagement_adjustment,
            "industry_fit": industry_adjustment
        }
        
        # 找出最低分项作为优化优先级
        min_category = min(scores, key=scores.get)
        
        priority_map = {
            "content_match": "improve_content_relevance",
            "engagement": "enhance_engagement_elements",
            "industry_fit": "better_align_with_industry_trends"
        }
        
        return priority_map.get(min_category, "general_optimization")
    
    def _calculate_platform_score(self,
                                 platform: str,
                                 industry: str,
                                 content_style: ContentStyle,
                                 business_goal: str,
                                 weights: Dict[str, float]) -> float:
        """计算平台得分"""
        # 基础平台权重
        base_score = sum(weights.values()) / len(weights)
        
        # 行业适配调整
        industry_fit = self._get_platform_industry_fit(platform, industry)
        
        # 风格适配调整
        style_fit = self._get_platform_style_fit(platform, content_style)
        
        # 目标适配调整
        goal_fit = self._get_platform_goal_fit(platform, business_goal)
        
        # 综合得分
        final_score = base_score * (1 + industry_fit) * (1 + style_fit) * (1 + goal_fit)
        
        return round(final_score, 2)
    
    def _get_platform_industry_fit(self, platform: str, industry: str) -> float:
        """获取平台行业适配度"""
        fit_matrix = {
            "tiktok": {"ecommerce": 0.3, "creators_economy": 0.4},
            "youtube": {"ai_technology": 0.3, "digital_health": 0.2, "educational": 0.4},
            "instagram": {"ecommerce": 0.2, "lifestyle": 0.3}
        }
        
        platform_fits = fit_matrix.get(platform, {})
        return platform_fits.get(industry, 0.0)
    
    def _get_platform_style_fit(self, platform: str, content_style: ContentStyle) -> float:
        """获取平台风格适配度"""
        fit_matrix = {
            "tiktok": {ContentStyle.FAST_PACED: 0.4, ContentStyle.ENTERTAINING: 0.3},
            "youtube": {ContentStyle.EDUCATIONAL: 0.4, ContentStyle.INSPIRATIONAL: 0.3},
            "instagram": {ContentStyle.VISUAL_STORYTELLING: 0.3, ContentStyle.MINIMALIST: 0.2}
        }
        
        platform_fits = fit_matrix.get(platform, {})
        return platform_fits.get(content_style, 0.0)
    
    def _get_platform_goal_fit(self, platform: str, business_goal: str) -> float:
        """获取平台目标适配度"""
        goal_weights = {
            "awareness": 0.4,  # TikTok, Instagram
            "engagement": 0.3,  # YouTube, Twitter
            "conversion": 0.2,  # Facebook, YouTube
            "retention": 0.1   # Email, Community
        }
        
        # 简化实现
        if business_goal in ["awareness", "engagement"] and platform in ["tiktok", "instagram"]:
            return 0.3
        elif business_goal == "conversion" and platform in ["youtube", "facebook"]:
            return 0.2
        else:
            return 0.0
    
    def _get_platform_recommendation_reason(self,
                                           platform: str,
                                           industry: str,
                                           content_style: ContentStyle,
                                           business_goal: str,
                                           score: float) -> str:
        """获取平台推荐理由"""
        reasons = {
            "tiktok": f"High discovery potential for {industry} content with {content_style.value} style",
            "youtube": f"Strong conversion and retention capabilities for {industry} educational content",
            "instagram": f"Excellent visual storytelling platform for {industry} brand building"
        }
        
        return reasons.get(platform, f"Platform score: {score} for {business_goal} goal")
    
    # 降级方案
    
    def _generate_fallback_analysis(self,
                                   industries: List[str],
                                   regions: List[Region],
                                   timeframe: str) -> Dict[str, Any]:
        """生成降级分析结果"""
        return {
            "timestamp": datetime.now().isoformat(),
            "timeframe": timeframe,
            "industries_analyzed": industries,
            "regions_analyzed": [r.value for r in regions],
            "industry_analysis": {
                industry: {
                    "heat_score": 60 + i * 5,
                    "trend_count": 10 + i,
                    "video_count": 5 + i,
                    "key_trends": ["digital_transformation", "consumer_engagement"],
                    "growth_potential": "medium"
                }
                for i, industry in enumerate(industries)
            },
            "regional_analysis": {
                region.value: {
                    "style_preferences": {"preferred_styles": ["fast_paced", "visual_storytelling"]},
                    "content_preferences": {"optimal_length": 30}
                }
                for region in regions
            },
            "content_patterns": [],
            "conversion_predictions": {},
            "recommendations": ["Use simulated data for analysis"],
            "analysis_metadata": {
                "processing_time_ms": 100.0,
                "trends_processed": 50,
                "confidence_score": 0.6,
                "fallback_mode": True
            }
        }
    
    def _generate_fallback_content_analysis(self,
                                           content_description: str,
                                           target_industry: str,
                                           target_region: Region) -> Dict[str, Any]:
        """生成降级内容分析结果"""
        return {
            "content_description": content_description,
            "target_industry": target_industry,
            "target_region": target_region.value,
            "content_match_score": 0.7,
            "engagement_prediction": {
                "predicted_engagement_rate": 0.08,
                "confidence_interval": [0.06, 0.10],
                "key_drivers": ["industry_relevance", "cultural_fit"]
            },
            "conversion_prediction": {
                "predicted_conversion_rate": 0.025,
                "key_factors": ["content_relevance", "engagement_potential"],
                "optimization_priority": "general_optimization"
            },
            "optimization_suggestions": [
                "Improve content relevance to target audience",
                "Enhance visual appeal and storytelling",
                "Include clear call-to-action"
            ],
            "timestamp": datetime.now().isoformat(),
            "fallback_mode": True
        }
    
    def _calculate_confidence_score(self,
                                   industry_analysis: Dict[str, Any],
                                   regional_analysis: Dict[str, Any]) -> float:
        """计算置信度得分"""
        # 基于数据量和分析深度计算
        data_points = sum(analysis.get("trend_count", 0) + analysis.get("video_count", 0) 
                         for analysis in industry_analysis.values())
        
        # 归一化到0-1
        normalized_data = min(1.0, data_points / 100)
        
        # 区域分析完整性
        regional_completeness = len(regional_analysis) / max(1, len(self.style_preferences))
        
        # 综合置信度
        confidence = (normalized_data * 0.6 + regional_completeness * 0.4)
        
        return round(confidence, 2)
    
    def _generate_optimization_suggestions(self,
                                          content_description: str,
                                          content_match_score: float,
                                          market_preferences: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        if content_match_score < 0.7:
            suggestions.append("Increase relevance to target industry through specific keywords and examples")
        
        # 基于市场偏好添加建议
        if "regional_preferences" in market_preferences:
            preferences = market_preferences["regional_preferences"]
            if "preferred_styles" in preferences:
                styles = preferences["preferred_styles"]
                suggestions.append(f"Incorporate {styles[0]} style elements for better regional acceptance")
        
        if len(suggestions) < 3:
            suggestions.extend([
                "Use data-driven insights to optimize content structure",
                "Test different formats and analyze performance metrics",
                "Continuously refine based on audience feedback"
            ])
        
        return suggestions[:5]