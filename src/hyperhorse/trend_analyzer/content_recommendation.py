#!/usr/bin/env python3
"""
内容智能推荐引擎
基于全球趋势分析结果，生成个性化的视频内容推荐策略
支持多目标、多场景、多平台的智能推荐
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


class RecommendationGoal(str, Enum):
    """推荐目标"""
    AWARENESS = "awareness"  # 品牌认知
    ENGAGEMENT = "engagement"  # 用户互动
    CONVERSION = "conversion"  # 转化购买
    RETENTION = "retention"  # 用户留存
    VIRALITY = "virality"  # 病毒传播


class ContentFormat(str, Enum):
    """内容格式"""
    SHORT_FORM = "short_form"  # 短视频 (15-60秒)
    MEDIUM_FORM = "medium_form"  # 中视频 (1-5分钟)
    LONG_FORM = "long_form"  # 长视频 (5+分钟)
    LIVE = "live"  # 直播
    STORIES = "stories"  # 故事/快拍


class AudienceSegment(str, Enum):
    """受众细分"""
    GENERAL = "general"  # 大众
    YOUTH = "youth"  # 年轻人 (18-25)
    PROFESSIONALS = "professionals"  # 专业人士
    ENTREPRENEURS = "entrepreneurs"  # 创业者
    INVESTORS = "investors"  # 投资者


class ContentRecommendationEngine:
    """内容推荐引擎"""
    
    def __init__(self, firecrawl_adapter: Optional[FirecrawlAdapter] = None):
        """
        初始化内容推荐引擎
        
        Args:
            firecrawl_adapter: Firecrawl适配器实例，可选
        """
        self.firecrawl_adapter = firecrawl_adapter or FirecrawlAdapter()
        
        # 内容模板库
        self.content_templates = self._load_content_templates()
        
        # 平台适配规则
        self.platform_rules = self._load_platform_rules()
        
        # 成功模式库
        self.success_patterns = self._load_success_patterns()
        
        logger.info("内容推荐引擎初始化完成")
    
    def _load_content_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载内容模板"""
        return {
            "problem_solution": {
                "name": "问题-解决方案",
                "description": "展示常见问题并提供解决方案",
                "structure": [
                    "痛点引入",
                    "问题放大",
                    "解决方案展示",
                    "成果证明",
                    "行动号召"
                ],
                "optimal_length": [30, 60, 90],
                "suitable_goals": [RecommendationGoal.AWARENESS, RecommendationGoal.CONVERSION],
                "style_preferences": [ContentStyle.EDUCATIONAL, ContentStyle.INSPIRATIONAL]
            },
            "behind_the_scenes": {
                "name": "幕后故事",
                "description": "展示产品或服务的幕后制作过程",
                "structure": [
                    "场景设置",
                    "过程展示",
                    "细节聚焦",
                    "成果预览",
                    "情感连接"
                ],
                "optimal_length": [15, 30, 45],
                "suitable_goals": [RecommendationGoal.ENGAGEMENT, RecommendationGoal.RETENTION],
                "style_preferences": [ContentStyle.ENTERTAINING, ContentStyle.VISUAL_STORYTELLING]
            },
            "comparison_review": {
                "name": "对比评测",
                "description": "比较不同产品或解决方案",
                "structure": [
                    "对比介绍",
                    "标准设定",
                    "逐项比较",
                    "优胜者宣布",
                    "购买建议"
                ],
                "optimal_length": [60, 120, 180],
                "suitable_goals": [RecommendationGoal.CONVERSION],
                "style_preferences": [ContentStyle.EDUCATIONAL]
            },
            "tutorial_howto": {
                "name": "教程指南",
                "description": "逐步指导完成特定任务",
                "structure": [
                    "目标说明",
                    "工具准备",
                    "步骤演示",
                    "技巧分享",
                    "结果展示"
                ],
                "optimal_length": [90, 180, 300],
                "suitable_goals": [RecommendationGoal.ENGAGEMENT, RecommendationGoal.RETENTION],
                "style_preferences": [ContentStyle.EDUCATIONAL, ContentStyle.VISUAL_STORYTELLING]
            },
            "trend_spotlight": {
                "name": "趋势聚焦",
                "description": "分析当前热门趋势",
                "structure": [
                    "趋势引入",
                    "数据支撑",
                    "影响分析",
                    "机会识别",
                    "行动指南"
                ],
                "optimal_length": [45, 90, 150],
                "suitable_goals": [RecommendationGoal.AWARENESS, RecommendationGoal.VIRALITY],
                "style_preferences": [ContentStyle.FAST_PACED, ContentStyle.INSPIRATIONAL]
            }
        }
    
    def _load_platform_rules(self) -> Dict[str, Dict[str, Any]]:
        """加载平台规则"""
        return {
            "tiktok": {
                "optimal_length": [15, 30, 60],
                "preferred_formats": [ContentFormat.SHORT_FORM, ContentFormat.STORIES],
                "style_weights": {
                    ContentStyle.FAST_PACED: 0.4,
                    ContentStyle.ENTERTAINING: 0.3,
                    ContentStyle.VISUAL_STORYTELLING: 0.3
                },
                "audience_segments": [AudienceSegment.YOUTH, AudienceSegment.GENERAL]
            },
            "youtube": {
                "optimal_length": [180, 300, 600],
                "preferred_formats": [ContentFormat.MEDIUM_FORM, ContentFormat.LONG_FORM],
                "style_weights": {
                    ContentStyle.EDUCATIONAL: 0.4,
                    ContentStyle.INSPIRATIONAL: 0.3,
                    ContentStyle.VISUAL_STORYTELLING: 0.3
                },
                "audience_segments": [AudienceSegment.PROFESSIONALS, AudienceSegment.ENTREPRENEURS]
            },
            "instagram": {
                "optimal_length": [30, 60, 90],
                "preferred_formats": [ContentFormat.SHORT_FORM, ContentFormat.STORIES],
                "style_weights": {
                    ContentStyle.VISUAL_STORYTELLING: 0.4,
                    ContentStyle.ENTERTAINING: 0.3,
                    ContentStyle.MINIMALIST: 0.3
                },
                "audience_segments": [AudienceSegment.GENERAL, AudienceSegment.YOUTH]
            }
        }
    
    def _load_success_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载成功模式"""
        return {
            "high_conversion": [
                {
                    "pattern": "clear_problem_agitation",
                    "description": "清晰的问题放大引起共鸣",
                    "effectiveness": 0.85,
                    "key_elements": ["pain_points", "emotional_connection", "urgent_solution"]
                },
                {
                    "pattern": "social_proof_integration",
                    "description": "整合社会证明建立信任",
                    "effectiveness": 0.80,
                    "key_elements": ["testimonials", "usage_stats", "expert_endorsements"]
                }
            ],
            "high_engagement": [
                {
                    "pattern": "interactive_elements",
                    "description": "互动元素促进参与",
                    "effectiveness": 0.90,
                    "key_elements": ["questions", "polls", "challenges", "user_generated_content"]
                },
                {
                    "pattern": "emotional_storytelling",
                    "description": "情感叙事建立连接",
                    "effectiveness": 0.85,
                    "key_elements": ["character_development", "conflict_resolution", "transformation"]
                }
            ],
            "viral_potential": [
                {
                    "pattern": "surprise_and_delight",
                    "description": "惊喜元素引发分享",
                    "effectiveness": 0.88,
                    "key_elements": ["unexpected_twist", "visual_wow", "emotional_high"]
                },
                {
                    "pattern": "cultural_relevance",
                    "description": "文化相关性扩大传播",
                    "effectiveness": 0.82,
                    "key_elements": ["trend_references", "community_values", "shared_identity"]
                }
            ]
        }
    
    def generate_recommendations(self,
                               trend_analysis: Dict[str, Any],
                               business_goals: List[RecommendationGoal],
                               target_regions: List[Region],
                               audience_segments: List[AudienceSegment],
                               platforms: List[str] = None) -> Dict[str, Any]:
        """
        生成内容推荐
        
        Args:
            trend_analysis: 趋势分析结果
            business_goals: 商业目标列表
            target_regions: 目标区域列表
            audience_segments: 受众细分列表
            platforms: 目标平台列表，默认全部
            
        Returns:
            内容推荐结果
        """
        start_time = time.time()
        
        if platforms is None:
            platforms = list(self.platform_rules.keys())
        
        logger.info(f"开始生成内容推荐: 目标={business_goals}, 区域={target_regions}, 受众={audience_segments}")
        
        try:
            # 分析趋势机会
            opportunities = self._analyze_opportunities(trend_analysis, target_regions)
            
            # 生成内容策略
            content_strategies = self._generate_content_strategies(
                opportunities, business_goals, audience_segments
            )
            
            # 平台适配优化
            platform_recommendations = self._optimize_for_platforms(
                content_strategies, platforms, target_regions, audience_segments
            )
            
            # 个性化调整
            personalized_recommendations = self._personalize_recommendations(
                platform_recommendations, audience_segments, target_regions
            )
            
            # 优先级排序
            prioritized_recommendations = self._prioritize_recommendations(
                personalized_recommendations, business_goals
            )
            
            # 组装结果
            result = {
                "timestamp": datetime.now().isoformat(),
                "input_parameters": {
                    "business_goals": [goal.value for goal in business_goals],
                    "target_regions": [region.value for region in target_regions],
                    "audience_segments": [segment.value for segment in audience_segments],
                    "platforms": platforms
                },
                "opportunity_analysis": opportunities,
                "content_strategies": content_strategies,
                "platform_recommendations": platform_recommendations,
                "personalized_recommendations": personalized_recommendations,
                "prioritized_recommendations": prioritized_recommendations,
                "implementation_guidelines": self._generate_implementation_guidelines(
                    prioritized_recommendations, platforms
                ),
                "success_metrics": self._define_success_metrics(business_goals),
                "recommendation_metadata": {
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    "confidence_score": self._calculate_recommendation_confidence(
                        trend_analysis, opportunities
                    ),
                    "freshness_hours": self._get_analysis_freshness(trend_analysis)
                }
            }
            
            logger.info(f"内容推荐生成完成: {len(prioritized_recommendations)}条推荐")
            
            return result
            
        except Exception as e:
            logger.error(f"内容推荐生成失败: {e}")
            return self._generate_fallback_recommendations(
                business_goals, target_regions, audience_segments
            )
    
    def optimize_existing_content(self,
                                 content_data: Dict[str, Any],
                                 target_platforms: List[str],
                                 business_goals: List[RecommendationGoal]) -> Dict[str, Any]:
        """
        优化现有内容
        
        Args:
            content_data: 内容数据
            target_platforms: 目标平台列表
            business_goals: 商业目标列表
            
        Returns:
            内容优化建议
        """
        try:
            # 分析内容现状
            content_analysis = self._analyze_content_status(content_data, target_platforms)
            
            # 识别优化机会
            optimization_opportunities = self._identify_optimization_opportunities(
                content_analysis, business_goals
            )
            
            # 生成优化方案
            optimization_plans = self._generate_optimization_plans(
                content_analysis, optimization_opportunities, target_platforms
            )
            
            # 预期效果预测
            expected_impact = self._predict_optimization_impact(
                optimization_plans, content_analysis, business_goals
            )
            
            result = {
                "original_content": content_data,
                "content_analysis": content_analysis,
                "optimization_opportunities": optimization_opportunities,
                "optimization_plans": optimization_plans,
                "expected_impact": expected_impact,
                "implementation_priority": self._prioritize_optimization_tasks(
                    optimization_plans, expected_impact
                ),
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"内容优化分析失败: {e}")
            return self._generate_fallback_optimization(content_data, target_platforms, business_goals)
    
    def generate_content_brief(self,
                              recommendation: Dict[str, Any],
                              content_template: str,
                              specific_requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        生成内容简报
        
        Args:
            recommendation: 推荐数据
            content_template: 内容模板名称
            specific_requirements: 特定要求
            
        Returns:
            内容简报
        """
        try:
            template = self.content_templates.get(content_template)
            if not template:
                raise ValueError(f"内容模板不存在: {content_template}")
            
            # 生成简报结构
            brief = {
                "template_name": template["name"],
                "template_description": template["description"],
                "business_context": {
                    "goals": recommendation.get("business_goals", []),
                    "target_regions": recommendation.get("target_regions", []),
                    "audience_segments": recommendation.get("audience_segments", [])
                },
                "content_structure": template["structure"],
                "format_requirements": {
                    "optimal_length_seconds": template["optimal_length"],
                    "recommended_style": template["style_preferences"],
                    "platform_adaptations": self._get_platform_adaptations(
                        recommendation.get("platforms", []),
                        content_template
                    )
                },
                "key_messaging": self._generate_key_messaging(
                    recommendation, template, specific_requirements
                ),
                "success_criteria": self._define_success_criteria(
                    recommendation.get("business_goals", [])
                ),
                "production_guidelines": self._generate_production_guidelines(
                    template, recommendation.get("platforms", [])
                ),
                "timeline_recommendations": self._suggest_timeline(content_template),
                "timestamp": datetime.now().isoformat()
            }
            
            # 添加特定要求
            if specific_requirements:
                brief["specific_requirements"] = specific_requirements
                brief["custom_adaptations"] = self._adapt_for_requirements(
                    template, specific_requirements
                )
            
            return brief
            
        except Exception as e:
            logger.error(f"内容简报生成失败: {e}")
            return self._generate_fallback_brief(recommendation, content_template)
    
    # 核心分析方法
    
    def _analyze_opportunities(self,
                              trend_analysis: Dict[str, Any],
                              target_regions: List[Region]) -> Dict[str, Any]:
        """分析机会点"""
        opportunities = {}
        
        # 提取行业机会
        if "industry_analysis" in trend_analysis:
            for industry, analysis in trend_analysis["industry_analysis"].items():
                opportunity_score = analysis.get("heat_score", 50)
                growth_potential = analysis.get("growth_potential", "medium")
                
                # 评估区域适配度
                regional_fit = self._assess_regional_fit(industry, target_regions)
                
                opportunities[industry] = {
                    "opportunity_score": opportunity_score,
                    "growth_potential": growth_potential,
                    "regional_fit": regional_fit,
                    "combined_score": opportunity_score * regional_fit,
                    "key_themes": analysis.get("key_themes", []),
                    "video_performance": analysis.get("video_performance", {})
                }
        
        # 按综合得分排序
        sorted_opportunities = dict(sorted(
            opportunities.items(),
            key=lambda x: x[1]["combined_score"],
            reverse=True
        ))
        
        return sorted_opportunities
    
    def _generate_content_strategies(self,
                                   opportunities: Dict[str, Any],
                                   business_goals: List[RecommendationGoal],
                                   audience_segments: List[AudienceSegment]) -> List[Dict[str, Any]]:
        """生成内容策略"""
        strategies = []
        
        for industry, data in list(opportunities.items())[:5]:  # 前5个机会
            # 根据商业目标匹配策略
            for goal in business_goals:
                strategy = self._create_strategy_for_goal(
                    industry, data, goal, audience_segments
                )
                if strategy:
                    strategies.append(strategy)
        
        return strategies
    
    def _optimize_for_platforms(self,
                               content_strategies: List[Dict[str, Any]],
                               platforms: List[str],
                               target_regions: List[Region],
                               audience_segments: List[AudienceSegment]) -> Dict[str, List[Dict[str, Any]]]:
        """针对平台优化"""
        platform_recommendations = {}
        
        for platform in platforms:
            platform_rules = self.platform_rules.get(platform, {})
            
            # 筛选适合平台的策略
            suitable_strategies = []
            for strategy in content_strategies:
                # 检查策略与平台匹配度
                match_score = self._calculate_platform_match(
                    strategy, platform_rules, target_regions, audience_segments
                )
                
                if match_score > 0.6:  # 匹配度阈值
                    # 优化策略以适应平台
                    optimized_strategy = self._optimize_strategy_for_platform(
                        strategy, platform_rules, match_score
                    )
                    suitable_strategies.append(optimized_strategy)
            
            # 按匹配度排序
            suitable_strategies.sort(
                key=lambda x: x.get("platform_match_score", 0),
                reverse=True
            )
            
            platform_recommendations[platform] = suitable_strategies[:3]  # 每个平台最多3个策略
        
        return platform_recommendations
    
    def _personalize_recommendations(self,
                                   platform_recommendations: Dict[str, List[Dict[str, Any]]],
                                   audience_segments: List[AudienceSegment],
                                   target_regions: List[Region]) -> Dict[str, List[Dict[str, Any]]]:
        """个性化推荐"""
        personalized = {}
        
        for platform, strategies in platform_recommendations.items():
            platform_personalized = []
            
            for strategy in strategies:
                # 为每个受众细分创建个性化版本
                for segment in audience_segments:
                    personalized_strategy = self._personalize_for_segment(
                        strategy, segment, target_regions
                    )
                    if personalized_strategy:
                        platform_personalized.append(personalized_strategy)
            
            # 去重和排序
            unique_strategies = self._deduplicate_strategies(platform_personalized)
            personalized[platform] = unique_strategies[:5]  # 每个平台最多5个个性化推荐
        
        return personalized
    
    def _prioritize_recommendations(self,
                                  personalized_recommendations: Dict[str, List[Dict[str, Any]]],
                                  business_goals: List[RecommendationGoal]) -> List[Dict[str, Any]]:
        """优先级排序"""
        all_recommendations = []
        
        for platform, strategies in personalized_recommendations.items():
            for strategy in strategies:
                # 计算综合优先级分数
                priority_score = self._calculate_priority_score(
                    strategy, business_goals, platform
                )
                
                strategy["priority_score"] = priority_score
                strategy["platform"] = platform
                all_recommendations.append(strategy)
        
        # 按优先级分数排序
        all_recommendations.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        return all_recommendations[:10]  # 返回前10个优先级最高的推荐
    
    # 辅助计算方法
    
    def _assess_regional_fit(self, industry: str, target_regions: List[Region]) -> float:
        """评估区域适配度"""
        # 基于行业和区域特征的匹配度
        regional_factors = {
            "ecommerce": {
                Region.NORTH_AMERICA: 0.9,
                Region.EUROPE: 0.8,
                Region.ASIA_PACIFIC: 0.7
            },
            "ai_technology": {
                Region.NORTH_AMERICA: 0.9,
                Region.EUROPE: 0.8,
                Region.ASIA_PACIFIC: 0.8
            },
            "digital_health": {
                Region.NORTH_AMERICA: 0.8,
                Region.EUROPE: 0.9,
                Region.ASIA_PACIFIC: 0.7
            }
        }
        
        # 计算平均适配度
        fit_scores = []
        for region in target_regions:
            industry_factors = regional_factors.get(industry, {})
            fit_score = industry_factors.get(region, 0.7)  # 默认0.7
            fit_scores.append(fit_score)
        
        return round(np.mean(fit_scores), 2) if fit_scores else 0.7
    
    def _create_strategy_for_goal(self,
                                 industry: str,
                                 opportunity_data: Dict[str, Any],
                                 goal: RecommendationGoal,
                                 audience_segments: List[AudienceSegment]) -> Optional[Dict[str, Any]]:
        """为目标创建策略"""
        
        # 目标特定策略
        goal_strategies = {
            RecommendationGoal.AWARENESS: {
                "focus": "brand_storytelling",
                "key_elements": ["origin_story", "mission_values", "impact_stories"],
                "success_indicators": ["reach", "impressions", "brand_recall"]
            },
            RecommendationGoal.ENGAGEMENT: {
                "focus": "audience_interaction",
                "key_elements": ["questions", "challenges", "user_generated_content"],
                "success_indicators": ["likes", "comments", "shares", "saves"]
            },
            RecommendationGoal.CONVERSION: {
                "focus": "product_showcase",
                "key_elements": ["benefits_demonstration", "social_proof", "limited_offer"],
                "success_indicators": ["click_through_rate", "conversion_rate", "roas"]
            }
        }
        
        strategy_template = goal_strategies.get(goal)
        if not strategy_template:
            return None
        
        # 创建策略
        strategy = {
            "industry": industry,
            "goal": goal.value,
            "opportunity_score": opportunity_data.get("opportunity_score", 0),
            "combined_score": opportunity_data.get("combined_score", 0),
            "focus_area": strategy_template["focus"],
            "key_elements": strategy_template["key_elements"],
            "target_audience": [segment.value for segment in audience_segments],
            "success_metrics": strategy_template["success_indicators"],
            "content_templates": self._identify_suitable_templates(industry, goal),
            "expected_outcomes": self._predict_outcomes(opportunity_data, goal)
        }
        
        return strategy
    
    def _calculate_platform_match(self,
                                 strategy: Dict[str, Any],
                                 platform_rules: Dict[str, Any],
                                 target_regions: List[Region],
                                 audience_segments: List[AudienceSegment]) -> float:
        """计算平台匹配度"""
        base_score = 0.7
        
        # 目标匹配度
        goal = strategy.get("goal")
        if goal in ["awareness", "engagement"] and "tiktok" in str(platform_rules):
            base_score += 0.1
        
        # 受众匹配度
        for segment in audience_segments:
            if segment.value in platform_rules.get("audience_segments", []):
                base_score += 0.05
        
        # 风格匹配度
        strategy_styles = strategy.get("style_preferences", [])
        platform_styles = platform_rules.get("style_weights", {}).keys()
        
        style_match = any(style in platform_styles for style in strategy_styles)
        if style_match:
            base_score += 0.1
        
        return round(min(1.0, base_score), 2)
    
    def _optimize_strategy_for_platform(self,
                                       strategy: Dict[str, Any],
                                       platform_rules: Dict[str, Any],
                                       match_score: float) -> Dict[str, Any]:
        """为平台优化策略"""
        optimized = strategy.copy()
        
        # 添加平台特定优化
        optimized["platform_optimizations"] = {
            "format_recommendation": platform_rules.get("preferred_formats", [])[:2],
            "length_adjustment": platform_rules.get("optimal_length", [30])[0],
            "style_adaptations": self._get_style_adaptations(strategy, platform_rules)
        }
        
        # 更新匹配度分数
        optimized["platform_match_score"] = match_score
        
        # 添加平台特定的成功指标
        platform_metrics = self._get_platform_metrics(platform_rules)
        if platform_metrics:
            optimized["platform_specific_metrics"] = platform_metrics
        
        return optimized
    
    def _personalize_for_segment(self,
                                strategy: Dict[str, Any],
                                segment: AudienceSegment,
                                target_regions: List[Region]) -> Optional[Dict[str, Any]]:
        """为受众细分个性化"""
        
        # 检查策略是否适合该细分
        suitable = self._check_segment_suitability(strategy, segment, target_regions)
        if not suitable:
            return None
        
        # 创建个性化版本
        personalized = strategy.copy()
        
        # 添加细分特定调整
        segment_adaptations = self._get_segment_adaptations(segment, target_regions)
        personalized["audience_segment"] = segment.value
        personalized["segment_adaptations"] = segment_adaptations
        
        # 调整关键信息
        personalized["key_messaging"] = self._adapt_messaging_for_segment(
            strategy, segment, target_regions
        )
        
        # 更新预期效果
        personalized["segment_specific_outcomes"] = self._predict_segment_outcomes(
            strategy, segment
        )
        
        return personalized
    
    def _calculate_priority_score(self,
                                 strategy: Dict[str, Any],
                                 business_goals: List[RecommendationGoal],
                                 platform: str) -> float:
        """计算优先级分数"""
        base_score = 50.0
        
        # 目标权重
        goal = strategy.get("goal")
        goal_priority = business_goals[0].value if business_goals else "awareness"
        if goal == goal_priority:
            base_score += 20
        
        # 机会分数贡献
        opportunity_score = strategy.get("opportunity_score", 50)
        base_score += opportunity_score * 0.3
        
        # 平台适配度贡献
        platform_match = strategy.get("platform_match_score", 0.7)
        base_score += platform_match * 20
        
        # 受众覆盖面
        audience_coverage = len(strategy.get("target_audience", [])) / 5
        base_score += audience_coverage * 10
        
        return round(min(100.0, base_score), 1)
    
    # 更多辅助方法
    
    def _identify_suitable_templates(self, industry: str, goal: RecommendationGoal) -> List[str]:
        """识别合适的内容模板"""
        suitable_templates = []
        
        for template_name, template in self.content_templates.items():
            # 检查目标适配度
            if goal.value in [g.value for g in template.get("suitable_goals", [])]:
                # 检查行业相关性
                if self._check_industry_relevance(template, industry):
                    suitable_templates.append(template_name)
        
        return suitable_templates[:3]
    
    def _predict_outcomes(self, opportunity_data: Dict[str, Any], goal: RecommendationGoal) -> Dict[str, Any]:
        """预测结果"""
        base_score = opportunity_data.get("combined_score", 50)
        
        # 根据目标调整预期
        goal_adjustments = {
            RecommendationGoal.AWARENESS: 1.2,
            RecommendationGoal.ENGAGEMENT: 1.1,
            RecommendationGoal.CONVERSION: 1.0,
            RecommendationGoal.RETENTION: 1.15,
            RecommendationGoal.VIRALITY: 1.3
        }
        
        adjustment = goal_adjustments.get(goal, 1.0)
        predicted_score = base_score * adjustment
        
        return {
            "predicted_performance_score": round(predicted_score, 1),
            "confidence_interval": [round(predicted_score * 0.8, 1), round(predicted_score * 1.2, 1)],
            "key_drivers": ["opportunity_strength", "goal_alignment", "audience_match"]
        }
    
    def _get_style_adaptations(self, strategy: Dict[str, Any], platform_rules: Dict[str, Any]) -> List[str]:
        """获取风格适应建议"""
        adaptations = []
        
        # 基于平台偏好调整风格
        platform_styles = platform_rules.get("style_weights", {})
        if platform_styles:
            recommended_styles = sorted(
                platform_styles.items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            
            for style, weight in recommended_styles:
                adaptations.append(f"Emphasize {style} elements (weight: {weight})")
        
        return adaptations[:3]
    
    def _get_platform_metrics(self, platform_rules: Dict[str, Any]) -> List[str]:
        """获取平台特定指标"""
        platform_metrics = {
            "tiktok": ["watch_time", "completion_rate", "sound_usage"],
            "youtube": ["retention_graph", "click_through_rate", "subscriber_growth"],
            "instagram": ["reach_impressions_ratio", "save_rate", "story_completion"]
        }
        
        # 基于平台规则识别平台类型
        for platform, metrics in platform_metrics.items():
            if platform in str(platform_rules):
                return metrics
        
        return ["engagement_rate", "share_rate", "comment_rate"]
    
    def _check_segment_suitability(self,
                                  strategy: Dict[str, Any],
                                  segment: AudienceSegment,
                                  target_regions: List[Region]) -> bool:
        """检查细分适配度"""
        industry = strategy.get("industry", "")
        goal = strategy.get("goal", "")
        
        # 基本适配规则
        if segment == AudienceSegment.GENERAL:
            return True
        
        # 行业特定适配
        if industry in ["ai_technology", "fintech"] and segment in [AudienceSegment.PROFESSIONALS, AudienceSegment.INVESTORS]:
            return True
        
        if industry in ["creators_economy", "ecommerce"] and segment in [AudienceSegment.YOUTH, AudienceSegment.ENTREPRENEURS]:
            return True
        
        return False
    
    def _get_segment_adaptations(self, segment: AudienceSegment, target_regions: List[Region]) -> Dict[str, Any]:
        """获取细分适应建议"""
        adaptations = {
            "communication_style": "",
            "content_format": "",
            "key_messaging_focus": ""
        }
        
        if segment == AudienceSegment.YOUTH:
            adaptations.update({
                "communication_style": "casual_and_trendy",
                "content_format": "short_form_video",
                "key_messaging_focus": "authenticity_and_community"
            })
        elif segment == AudienceSegment.PROFESSIONALS:
            adaptations.update({
                "communication_style": "professional_and_data_driven",
                "content_format": "medium_form_educational",
                "key_messaging_focus": "expertise_and_efficiency"
            })
        
        # 添加区域特定调整
        if target_regions:
            regional_adaptations = self._get_regional_adaptations(target_regions[0])
            adaptations.update(regional_adaptations)
        
        return adaptations
    
    def _adapt_messaging_for_segment(self,
                                    strategy: Dict[str, Any],
                                    segment: AudienceSegment,
                                    target_regions: List[Region]) -> List[str]:
        """为细分调整信息"""
        messaging = strategy.get("key_elements", [])
        
        # 细分特定调整
        if segment == AudienceSegment.YOUTH:
            messaging.append("Use relatable language and current trends")
            messaging.append("Emphasize visual storytelling over text")
        
        elif segment == AudienceSegment.PROFESSIONALS:
            messaging.append("Focus on data, results, and ROI")
            messaging.append("Use industry-specific terminology appropriately")
        
        return messaging[:5]
    
    def _predict_segment_outcomes(self, strategy: Dict[str, Any], segment: AudienceSegment) -> Dict[str, Any]:
        """预测细分特定结果"""
        base_score = strategy.get("combined_score", 50)
        
        # 细分调整因子
        segment_adjustments = {
            AudienceSegment.GENERAL: 1.0,
            AudienceSegment.YOUTH: 1.1,
            AudienceSegment.PROFESSIONALS: 1.05,
            AudienceSegment.ENTREPRENEURS: 1.2,
            AudienceSegment.INVESTORS: 1.15
        }
        
        adjustment = segment_adjustments.get(segment, 1.0)
        predicted_score = base_score * adjustment
        
        return {
            "predicted_score": round(predicted_score, 1),
            "segment_specific_factors": [
                f"{segment.value} engagement patterns",
                "Platform usage habits",
                "Content consumption preferences"
            ]
        }
    
    def _generate_implementation_guidelines(self,
                                          prioritized_recommendations: List[Dict[str, Any]],
                                          platforms: List[str]) -> Dict[str, Any]:
        """生成实施指南"""
        guidelines = {
            "overall_approach": "Iterative implementation with continuous optimization",
            "phase_1": {
                "focus": "Quick wins and validation",
                "duration": "2-4 weeks",
                "key_activities": [
                    "Implement top 3 recommendations",
                    "Establish baseline metrics",
                    "Test and refine content formats"
                ]
            },
            "phase_2": {
                "focus": "Scale and optimize",
                "duration": "4-8 weeks",
                "key_activities": [
                    "Expand to remaining recommendations",
                    "Deep dive into performance analytics",
                    "Optimize for each platform"
                ]
            },
            "phase_3": {
                "focus": "Sustain and innovate",
                "duration": "Ongoing",
                "key_activities": [
                    "Continuous content optimization",
                    "Explore new content formats and platforms",
                    "Build audience feedback loops"
                ]
            },
            "platform_specific_guidelines": self._get_platform_guidelines(platforms),
            "success_measurement": {
                "short_term": ["engagement_rate", "content_velocity"],
                "medium_term": ["audience_growth", "content_quality"],
                "long_term": ["brand_impact", "business_outcomes"]
            }
        }
        
        return guidelines
    
    def _define_success_metrics(self, business_goals: List[RecommendationGoal]) -> Dict[str, List[str]]:
        """定义成功指标"""
        metrics = {
            "awareness": ["impressions", "reach", "brand_search_volume"],
            "engagement": ["likes", "comments", "shares", "saves"],
            "conversion": ["click_through_rate", "conversion_rate", "roas"],
            "retention": ["repeat_views", "follow_rate", "notification_open_rate"],
            "virality": ["share_rate", "virality_score", "cultural_relevance"]
        }
        
        return {
            "primary_metrics": [
                metrics[goal.value][0] 
                for goal in business_goals 
                if goal.value in metrics
            ],
            "supporting_metrics": [
                metric
                for goal in business_goals
                for metric in metrics.get(goal.value, [])[1:3]
            ]
        }
    
    # 降级方案
    
    def _generate_fallback_recommendations(self,
                                         business_goals: List[RecommendationGoal],
                                         target_regions: List[Region],
                                         audience_segments: List[AudienceSegment]) -> Dict[str, Any]:
        """生成降级推荐"""
        return {
            "timestamp": datetime.now().isoformat(),
            "fallback_mode": True,
            "general_recommendations": [
                "Focus on educational content that addresses audience pain points",
                "Use visual storytelling to explain complex concepts",
                "Adapt content to local cultural preferences",
                "Test different formats and optimize based on performance",
                "Build a consistent content publishing schedule"
            ],
            "platform_priorities": [
                "YouTube for long-form educational content",
                "TikTok for short-form engagement",
                "Instagram for visual storytelling"
            ],
            "key_focus_areas": [
                "Content quality over quantity",
                "Audience engagement metrics",
                "Continuous performance optimization"
            ]
        }
    
    def _get_regional_adaptations(self, region: Region) -> Dict[str, Any]:
        """获取区域适应建议"""
        adaptations = {
            "north_america": {
                "communication_style": "direct_and_results_focused",
                "cultural_references": ["innovation", "individual_achievement", "diversity"]
            },
            "europe": {
                "communication_style": "sophisticated_and_data_driven",
                "cultural_references": ["sustainability", "quality", "multiculturalism"]
            }
        }
        
        return adaptations.get(region.value, {
            "communication_style": "adaptable_and_respectful",
            "cultural_references": ["local_values", "community", "progress"]
        })
    
    def _get_platform_guidelines(self, platforms: List[str]) -> Dict[str, List[str]]:
        """获取平台特定指南"""
        guidelines = {
            "tiktok": [
                "Keep videos under 60 seconds for maximum engagement",
                "Use trending sounds and challenges",
                "Focus on the first 3 seconds to hook viewers"
            ],
            "youtube": [
                "Create chapters for longer videos",
                "Focus on retention metrics",
                "Use end screens and cards strategically"
            ],
            "instagram": [
                "Optimize for both feed and stories",
                "Use high-quality visuals",
                "Leverage reels for discoverability"
            ]
        }
        
        return {
            platform: guidelines.get(platform, [
                "Focus on platform-specific best practices",
                "Adapt content format to platform norms",
                "Monitor platform-specific metrics"
            ])
            for platform in platforms
        }