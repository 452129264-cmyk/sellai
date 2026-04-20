"""
HyperHorse视频内容趋势分析模块
实时分析全球各行业视频内容趋势，集成Firecrawl全域爬虫数据
支持多语言、多文化背景的智能推荐
"""

from .video_trend_analyzer import VideoTrendAnalyzer
from .global_trend_analyzer import GlobalTrendAnalyzer
from .content_recommendation import ContentRecommendationEngine

__all__ = [
    "VideoTrendAnalyzer",
    "GlobalTrendAnalyzer",
    "ContentRecommendationEngine"
]