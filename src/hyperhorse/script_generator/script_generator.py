#!/usr/bin/env python3
"""
HyperHorse智能脚本生成器
基于全品类商业数据分析模型，自动生成符合30%毛利门槛的高转化视频脚本
支持全行业覆盖、多语言生成与效果优化闭环
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import random
import re

from ..trend_analyzer.content_recommendation import (
    ContentRecommendationEngine, 
    RecommendationGoal,
    ContentFormat,
    AudienceSegment
)
from ..trend_analyzer.video_trend_analyzer import ContentStyle
from ..core import LanguageCode, VideoPlatform

logger = logging.getLogger(__name__)

class ScriptType(str, Enum):
    """脚本类型枚举"""
    PRODUCT_DEMO = "product_demo"          # 产品展示类
    BRAND_STORY = "brand_story"           # 品牌故事类
    MARKETING_CONVERSION = "marketing_conversion"  # 营销转化类
    KNOWLEDGE_EXPLANATION = "knowledge_explanation"  # 知识解说类
    SOCIAL_PROOF = "social_proof"         # 社交证明类
    UGC_STYLE = "ugc_style"               # 用户生成内容风格

@dataclass
class VideoScript:
    """视频脚本数据结构"""
    script_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    script_type: ScriptType = ScriptType.PRODUCT_DEMO
    language: LanguageCode = LanguageCode.ENGLISH
    target_platforms: List[VideoPlatform] = field(default_factory=lambda: [VideoPlatform.TIKTOK])
    duration_seconds: int = 60
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    call_to_action: str = ""
    estimated_cpm: float = 0.0  # 预估千次展示成本
    estimated_roi: float = 0.0  # 预估投资回报率
    profit_margin: float = 0.3  # 默认30%毛利率
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 处理枚举类型
        data['script_type'] = self.script_type.value
        data['language'] = self.language.value
        data['target_platforms'] = [p.value for p in self.target_platforms]
        data['generated_at'] = self.generated_at.isoformat()
        return data
    
    def validate_profit_margin(self) -> bool:
        """验证毛利率是否符合30%门槛"""
        return self.profit_margin >= 0.3
    
    def calculate_commercial_score(self) -> float:
        """计算脚本商业得分（0-100）"""
        # 基础分
        score = 50.0
        
        # 毛利率权重（40%）
        margin_score = min(100, self.profit_margin * 200)  # 50%毛利率得100分
        score += margin_score * 0.4
        
        # 时长适应性（20%）
        if 15 <= self.duration_seconds <= 60:
            score += 20
        elif 61 <= self.duration_seconds <= 180:
            score += 10
        
        # 平台适应性（20%）
        platform_score = len(self.target_platforms) * 10
        if platform_score > 20:
            platform_score = 20
        score += platform_score
        
        # 关键词丰富度（10%）
        keyword_score = min(10, len(self.keywords) * 2)
        score += keyword_score
        
        # 标签丰富度（10%）
        tag_score = min(10, len(self.tags) * 2)
        score += tag_score
        
        return min(100, score)


class ScriptGenerator:
    """智能脚本生成器"""
    
    def __init__(self, recommendation_engine: Optional[ContentRecommendationEngine] = None):
        """
        初始化脚本生成器
        
        Args:
            recommendation_engine: 内容推荐引擎实例，可选
        """
        self.recommendation_engine = recommendation_engine or ContentRecommendationEngine()
        self.template_manager = TemplateManager()
        self.language_adapter = LanguageAdapter()
        self.feedback_optimizer = FeedbackOptimizer()
        
        logger.info("智能脚本生成器初始化完成")
    
    def generate_script(self,
                       product_info: Dict[str, Any],
                       target_market: Dict[str, Any],
                       script_type: Optional[ScriptType] = None,
                       language: Optional[LanguageCode] = None) -> VideoScript:
        """
        生成视频脚本
        
        Args:
            product_info: 产品信息，包含名称、描述、价格、成本等
            target_market: 目标市场信息，包含地区、平台、受众等
            script_type: 脚本类型，可选（自动选择最优类型）
            language: 目标语言，可选（默认为英语）
            
        Returns:
            VideoScript: 生成的视频脚本
        """
        logger.info(f"开始生成视频脚本，产品：{product_info.get('name', '未知')}")
        
        # 验证毛利率
        if not self._validate_profit_margin(product_info):
            raise ValueError("产品毛利率低于30%门槛，无法生成商业可行脚本")
        
        # 自动选择脚本类型
        if script_type is None:
            script_type = self._select_script_type(product_info, target_market)
        
        # 设置目标语言
        if language is None:
            language = self._detect_language(target_market)
        
        # 获取趋势分析结果
        trend_analysis = self._analyze_trends(product_info, target_market)
        
        # 选择模板
        template = self.template_manager.select_template(
            script_type=script_type,
            product_category=product_info.get('category', 'general'),
            platform=target_market.get('primary_platform', 'tiktok'),
            audience=target_market.get('audience', 'general')
        )
        
        # 生成脚本内容
        script_content = self._generate_content(
            template=template,
            product_info=product_info,
            trend_analysis=trend_analysis,
            target_market=target_market
        )
        
        # 本地化适配
        localized_content = self.language_adapter.adapt_content(
            content=script_content,
            target_language=language,
            target_culture=target_market.get('culture', 'western')
        )
        
        # 创建脚本对象
        script = VideoScript(
            title=localized_content['title'],
            description=localized_content['description'],
            script_type=script_type,
            language=language,
            target_platforms=self._get_target_platforms(target_market),
            duration_seconds=self._calculate_optimal_duration(
                script_type=script_type,
                platform=target_market.get('primary_platform', 'tiktok')
            ),
            scenes=localized_content['scenes'],
            keywords=localized_content['keywords'],
            tags=localized_content['tags'],
            call_to_action=localized_content['call_to_action'],
            estimated_cpm=self._estimate_cpm(target_market),
            estimated_roi=self._estimate_roi(product_info, target_market),
            profit_margin=product_info.get('profit_margin', 0.3)
        )
        
        # 记录生成日志
        self.feedback_optimizer.record_generation(script)
        
        logger.info(f"视频脚本生成完成，ID：{script.script_id}，商业得分：{script.calculate_commercial_score():.1f}")
        return script
    
    def batch_generate_scripts(self,
                              product_list: List[Dict[str, Any]],
                              market_configs: List[Dict[str, Any]],
                              max_scripts_per_product: int = 3) -> List[VideoScript]:
        """
        批量生成视频脚本
        
        Args:
            product_list: 产品列表
            market_configs: 市场配置列表
            max_scripts_per_product: 每个产品最大生成脚本数
            
        Returns:
            List[VideoScript]: 生成的脚本列表
        """
        scripts = []
        
        for product in product_list:
            # 为每个产品选择最匹配的市场配置
            suitable_markets = self._match_product_to_markets(product, market_configs)
            
            # 限制每个产品的脚本数量
            markets_to_use = suitable_markets[:max_scripts_per_product]
            
            for market in markets_to_use:
                try:
                    script = self.generate_script(product, market)
                    scripts.append(script)
                except Exception as e:
                    logger.error(f"为产品{product.get('name')}生成脚本失败：{e}")
        
        # 按商业得分排序
        scripts.sort(key=lambda s: s.calculate_commercial_score(), reverse=True)
        
        logger.info(f"批量生成完成，共生成{len(scripts)}个脚本")
        return scripts
    
    def optimize_script(self, script: VideoScript, feedback_data: Dict[str, Any]) -> VideoScript:
        """
        基于反馈数据优化脚本
        
        Args:
            script: 原始脚本
            feedback_data: 反馈数据，包含播放、互动、转化等指标
            
        Returns:
            VideoScript: 优化后的脚本
        """
        logger.info(f"开始优化脚本：{script.script_id}")
        
        # 分析反馈数据
        optimization_suggestions = self.feedback_optimizer.analyze_feedback(
            script=script,
            feedback_data=feedback_data
        )
        
        # 应用优化建议
        optimized_content = self._apply_optimizations(
            script_content=script.to_dict(),
            suggestions=optimization_suggestions
        )
        
        # 创建优化后的脚本
        optimized_script = VideoScript(
            title=optimized_content['title'],
            description=optimized_content['description'],
            script_type=script.script_type,
            language=script.language,
            target_platforms=script.target_platforms,
            duration_seconds=optimized_content.get('duration_seconds', script.duration_seconds),
            scenes=optimized_content['scenes'],
            keywords=optimized_content['keywords'],
            tags=optimized_content['tags'],
            call_to_action=optimized_content['call_to_action'],
            estimated_cpm=optimized_content.get('estimated_cpm', script.estimated_cpm),
            estimated_roi=optimized_content.get('estimated_roi', script.estimated_roi),
            profit_margin=script.profit_margin
        )
        
        # 记录优化日志
        self.feedback_optimizer.record_optimization(script, optimized_script, feedback_data)
        
        logger.info(f"脚本优化完成，新商业得分：{optimized_script.calculate_commercial_score():.1f}")
        return optimized_script
    
    def _validate_profit_margin(self, product_info: Dict[str, Any]) -> bool:
        """验证产品毛利率"""
        cost = product_info.get('cost', 0)
        price = product_info.get('price', 0)
        
        if cost <= 0 or price <= 0:
            return False
        
        profit_margin = (price - cost) / price
        product_info['profit_margin'] = profit_margin
        
        return profit_margin >= 0.3
    
    def _select_script_type(self, product_info: Dict[str, Any], target_market: Dict[str, Any]) -> ScriptType:
        """自动选择脚本类型"""
        # 基于产品类型和市场分析选择最优脚本类型
        product_category = product_info.get('category', 'general')
        audience = target_market.get('audience', 'general')
        
        # 简单规则：根据产品特征选择
        if product_category in ['fashion', 'beauty', 'electronics']:
            return ScriptType.PRODUCT_DEMO
        elif product_category in ['luxury', 'craft', 'artisan']:
            return ScriptType.BRAND_STORY
        elif product_category in ['tools', 'utilities', 'software']:
            return ScriptType.KNOWLEDGE_EXPLANATION
        else:
            return ScriptType.MARKETING_CONVERSION
    
    def _detect_language(self, target_market: Dict[str, Any]) -> LanguageCode:
        """检测目标语言"""
        region = target_market.get('region', 'global')
        
        language_map = {
            'us': LanguageCode.ENGLISH,
            'uk': LanguageCode.ENGLISH,
            'ca': LanguageCode.ENGLISH,
            'au': LanguageCode.ENGLISH,
            'es': LanguageCode.SPANISH,
            'mx': LanguageCode.SPANISH,
            'ar': LanguageCode.SPANISH,
            'sa': LanguageCode.ARABIC,
            'ae': LanguageCode.ARABIC,
            'br': LanguageCode.PORTUGUESE,
            'pt': LanguageCode.PORTUGUESE,
            'fr': LanguageCode.FRENCH,
            'de': LanguageCode.GERMAN,
            'jp': LanguageCode.JAPANESE,
            'kr': LanguageCode.KOREAN
        }
        
        return language_map.get(region.lower(), LanguageCode.ENGLISH)
    
    def _analyze_trends(self, product_info: Dict[str, Any], target_market: Dict[str, Any]) -> Dict[str, Any]:
        """分析趋势数据"""
        # 调用内容推荐引擎获取趋势分析
        try:
            recommendation = self.recommendation_engine.recommend_content(
                category=product_info.get('category', 'general'),
                target_regions=[target_market.get('region', 'global')],
                goal=RecommendationGoal.CONVERSION,
                format_preference=ContentFormat.SHORT_FORM,
                audience_segment=target_market.get('audience', AudienceSegment.GENERAL)
            )
            return recommendation
        except Exception as e:
            logger.warning(f"趋势分析失败，使用默认数据：{e}")
            return self._get_default_trend_data()
    
    def _generate_content(self, template: Dict[str, Any], 
                         product_info: Dict[str, Any],
                         trend_analysis: Dict[str, Any],
                         target_market: Dict[str, Any]) -> Dict[str, Any]:
        """生成脚本内容"""
        # 这里应该实现具体的模板填充逻辑
        # 简化实现：返回模板结构的填充版本
        
        return {
            'title': f"{product_info.get('name', '产品')} - {template.get('title_template', '展示')}",
            'description': f"了解{product_info.get('name', '产品')}的独特优势",
            'scenes': template.get('scenes', []),
            'keywords': trend_analysis.get('keywords', []),
            'tags': trend_analysis.get('tags', []),
            'call_to_action': template.get('call_to_action', '立即购买')
        }
    
    def _get_target_platforms(self, target_market: Dict[str, Any]) -> List[VideoPlatform]:
        """获取目标平台列表"""
        platforms = target_market.get('platforms', ['tiktok'])
        
        platform_map = {
            'tiktok': VideoPlatform.TIKTOK,
            'instagram': VideoPlatform.INSTAGRAM,
            'youtube_shorts': VideoPlatform.YOUTUBE_SHORTS,
            'facebook_reels': VideoPlatform.FACEBOOK_REELS,
            'shopify': VideoPlatform.SHOPIFY,
            'amazon': VideoPlatform.AMAZON,
            'aliexpress': VideoPlatform.ALIEXPRESS,
            'independent_site': VideoPlatform.INDEPENDENT_SITE
        }
        
        return [platform_map.get(p.lower(), VideoPlatform.TIKTOK) for p in platforms]
    
    def _calculate_optimal_duration(self, script_type: ScriptType, platform: str) -> int:
        """计算最优时长"""
        # 基于脚本类型和平台的推荐时长
        duration_rules = {
            ScriptType.PRODUCT_DEMO: {'tiktok': 30, 'instagram': 60, 'youtube': 180},
            ScriptType.BRAND_STORY: {'tiktok': 45, 'instagram': 90, 'youtube': 240},
            ScriptType.MARKETING_CONVERSION: {'tiktok': 30, 'instagram': 60, 'youtube': 120},
            ScriptType.KNOWLEDGE_EXPLANATION: {'tiktok': 60, 'instagram': 90, 'youtube': 300}
        }
        
        return duration_rules.get(script_type, {}).get(platform, 60)
    
    def _estimate_cpm(self, target_market: Dict[str, Any]) -> float:
        """预估千次展示成本"""
        # 简化实现：基于地区和平台估算
        region = target_market.get('region', 'us')
        platform = target_market.get('primary_platform', 'tiktok')
        
        cpm_map = {
            'us': {'tiktok': 10.0, 'instagram': 12.0, 'youtube': 8.0},
            'uk': {'tiktok': 8.0, 'instagram': 10.0, 'youtube': 7.0},
            'global': {'tiktok': 6.0, 'instagram': 8.0, 'youtube': 5.0}
        }
        
        return cpm_map.get(region, cpm_map['global']).get(platform, 8.0)
    
    def _estimate_roi(self, product_info: Dict[str, Any], target_market: Dict[str, Any]) -> float:
        """预估投资回报率"""
        # 简化实现：基于毛利率和平台估算
        profit_margin = product_info.get('profit_margin', 0.3)
        platform = target_market.get('primary_platform', 'tiktok')
        
        # 不同平台的转化率基准
        conversion_rate_map = {
            'tiktok': 0.02,
            'instagram': 0.015,
            'youtube': 0.025
        }
        
        conversion_rate = conversion_rate_map.get(platform, 0.02)
        
        # ROI估算公式：(毛利率 * 转化率) / CPM * 1000
        cpm = self._estimate_cpm(target_market)
        if cpm > 0:
            roi = (profit_margin * conversion_rate * 1000) / cpm
            return min(roi, 10.0)  # 限制最大ROI
        
        return 2.0  # 默认ROI
    
    def _match_product_to_markets(self, product: Dict[str, Any], 
                                 market_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """匹配产品到最适合的市场"""
        # 简化实现：基于产品类别和价格匹配
        product_category = product.get('category', 'general')
        product_price = product.get('price', 0)
        
        matched_markets = []
        
        for market in market_configs:
            # 简单的匹配逻辑
            market_category = market.get('preferred_category', 'general')
            market_price_range = market.get('price_range', (0, 1000))
            
            if (product_category == market_category or market_category == 'general') and \
               (market_price_range[0] <= product_price <= market_price_range[1]):
                matched_markets.append(market)
        
        return matched_markets
    
    def _get_default_trend_data(self) -> Dict[str, Any]:
        """获取默认趋势数据"""
        return {
            'keywords': ['product', 'demo', 'review', 'unboxing'],
            'tags': ['#productreview', '#unboxing', '#demo'],
            'trend_score': 0.7,
            'recommended_style': 'fast_paced',
            'audience_preferences': ['visual', 'entertaining']
        }
    
    def _apply_optimizations(self, script_content: Dict[str, Any], 
                           suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """应用优化建议"""
        # 简化实现：根据建议调整内容
        optimized = script_content.copy()
        
        for suggestion in suggestions:
            suggestion_type = suggestion.get('type')
            suggestion_value = suggestion.get('value')
            
            if suggestion_type == 'title_improvement':
                optimized['title'] = suggestion_value
            elif suggestion_type == 'cta_improvement':
                optimized['call_to_action'] = suggestion_value
            elif suggestion_type == 'keyword_addition':
                optimized['keywords'].extend(suggestion_value)
        
        return optimized