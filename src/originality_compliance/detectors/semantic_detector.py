"""
语义相似度检测模块
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import logging

from ..models.data_models import SimilarityItem, RiskLevel
from ..utils.similarity_metrics import SimilarityCalculator, SimilarityResult
from ..utils.text_processor import TextProcessor

logger = logging.getLogger(__name__)


@dataclass
class SemanticDetectionConfig:
    """语义检测配置"""
    similarity_threshold_high: float = 0.85  # 高于此值为高风险
    similarity_threshold_medium: float = 0.70  # 高于此值为中风险
    min_text_length: int = 10  # 最小检测文本长度
    enable_semantic_cache: bool = True  # 启用语义缓存
    cache_ttl_seconds: int = 3600  # 缓存生存时间


class SemanticSimilarityDetector:
    """语义相似度检测器"""
    
    def __init__(self, config: Optional[SemanticDetectionConfig] = None):
        """
        初始化语义检测器
        
        Args:
            config: 检测配置
        """
        self.config = config or SemanticDetectionConfig()
        self.similarity_calculator = SimilarityCalculator()
        self.text_processor = TextProcessor()
        
        # 缓存（简化实现）
        self._cache: Dict[str, Any] = {}
        
    def detect_similarity(self, text: str, reference_texts: List[Tuple[str, str]]) -> List[SimilarityItem]:
        """
        检测文本与参考文本的语义相似度
        
        Args:
            text: 待检测文本
            reference_texts: 参考文本列表，每个元素为(来源ID, 文本内容)
            
        Returns:
            相似内容项列表
        """
        if len(text.strip()) < self.config.min_text_length:
            logger.warning(f"文本长度不足{self.config.min_text_length}字符，跳过检测")
            return []
        
        similarity_items = []
        
        for source_id, reference_text in reference_texts:
            if len(reference_text.strip()) < self.config.min_text_length:
                continue
            
            try:
                # 计算综合相似度
                similarity_result = self.similarity_calculator.calculate_similarity_comprehensive(
                    text, reference_text
                )
                
                # 提取匹配的文本片段（简化实现）
                matched_text = self._extract_matched_fragment(text, reference_text)
                
                # 确定风险等级
                risk_level = self._determine_risk_level(similarity_result.combined)
                
                # 生成改进建议
                recommendations = self._generate_recommendations(
                    similarity_result.combined, risk_level
                )
                
                # 创建相似项
                similarity_item = SimilarityItem(
                    source_id=source_id,
                    source_type="reference",  # 默认类型
                    similarity_score=similarity_result.combined,
                    matched_text=matched_text,
                    risk_level=risk_level,
                    recommendations=recommendations
                )
                
                similarity_items.append(similarity_item)
                
            except Exception as e:
                logger.error(f"计算文本相似度时出错: {str(e)}")
                continue
        
        # 按相似度分数排序（从高到低）
        similarity_items.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return similarity_items
    
    def _extract_matched_fragment(self, text1: str, text2: str, fragment_length: int = 50) -> str:
        """
        提取匹配的文本片段（简化实现）
        
        Args:
            text1: 文本1
            text2: 文本2
            fragment_length: 片段长度
            
        Returns:
            匹配的文本片段
        """
        # 简单实现：找出最长的公共子字符串
        def longest_common_substring(s1: str, s2: str) -> str:
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            max_length = 0
            end_pos = 0
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i-1] == s2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                        if dp[i][j] > max_length:
                            max_length = dp[i][j]
                            end_pos = i
                    else:
                        dp[i][j] = 0
            
            if max_length > 0:
                return s1[end_pos - max_length:end_pos]
            return ""
        
        lcs = longest_common_substring(text1, text2)
        
        if len(lcs) > 0:
            # 截取适当长度的片段
            start_idx = max(0, len(lcs) - fragment_length // 2)
            return lcs[start_idx:start_idx + fragment_length]
        else:
            # 如果没有找到公共子串，返回第一个文本的前几个词
            words = text1.split()
            return ' '.join(words[:min(5, len(words))])
    
    def _determine_risk_level(self, similarity_score: float) -> RiskLevel:
        """
        根据相似度分数确定风险等级
        
        Args:
            similarity_score: 相似度分数（0.0-1.0）
            
        Returns:
            风险等级
        """
        if similarity_score >= self.config.similarity_threshold_high:
            return RiskLevel.HIGH
        elif similarity_score >= self.config.similarity_threshold_medium:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_recommendations(self, similarity_score: float, risk_level: RiskLevel) -> List[str]:
        """
        生成改进建议
        
        Args:
            similarity_score: 相似度分数
            risk_level: 风险等级
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "文本与现有内容高度相似，建议完全重写",
                "调整核心观点表述方式，避免直接复制",
                "增加独特的分析和见解"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend([
                "部分段落相似度较高，建议修改相似部分",
                "增加原创性内容，降低整体相似度",
                "重新组织语言结构，保持原意但改变表达"
            ])
        elif risk_level == RiskLevel.LOW:
            recommendations.extend([
                "文本原创性良好，可以继续使用",
                "建议添加更多个性化内容以增强独特性"
            ])
        
        return recommendations
    
    def calculate_overall_originality_score(self, similarity_items: List[SimilarityItem]) -> float:
        """
        计算整体原创性分数
        
        Args:
            similarity_items: 相似项列表
            
        Returns:
            原创性分数（0.0-1.0，越高表示越原创）
        """
        if not similarity_items:
            return 1.0  # 没有相似项，完全原创
        
        # 取最高相似度分数作为抄袭风险指标
        max_similarity = max(item.similarity_score for item in similarity_items)
        
        # 原创性分数 = 1 - 最大相似度（但保留一定容错）
        originality_score = 1.0 - (max_similarity * 0.8)
        
        # 确保在合理范围内
        return max(0.0, min(1.0, originality_score))
    
    def analyze_text_patterns(self, text: str, reference_texts: List[str]) -> Dict[str, Any]:
        """
        分析文本模式特征
        
        Args:
            text: 待分析文本
            reference_texts: 参考文本列表
            
        Returns:
            模式分析结果
        """
        # 文本复杂度分析
        complexity = self.text_processor.calculate_text_complexity(text)
        
        # 词频分布
        term_freq = self.similarity_calculator.calculate_term_frequency(text)
        
        # n-gram分布
        ngrams = self.text_processor.extract_ngrams(text, 3)
        
        # 相似度分布统计
        similarity_scores = []
        for ref_text in reference_texts:
            result = self.similarity_calculator.calculate_similarity_comprehensive(text, ref_text)
            similarity_scores.append(result.combined)
        
        return {
            "complexity": complexity,
            "vocabulary_size": len(term_freq),
            "ngram_variety": len(set(ngrams)),
            "avg_similarity": np.mean(similarity_scores) if similarity_scores else 0.0,
            "max_similarity": max(similarity_scores) if similarity_scores else 0.0,
            "similarity_distribution": {
                "high": len([s for s in similarity_scores if s >= 0.8]),
                "medium": len([s for s in similarity_scores if 0.5 <= s < 0.8]),
                "low": len([s for s in similarity_scores if s < 0.5])
            }
        }
    
    def batch_detect(self, texts: List[str], reference_corpus: List[Tuple[str, str]]) -> List[List[SimilarityItem]]:
        """
        批量检测文本相似度
        
        Args:
            texts: 待检测文本列表
            reference_corpus: 参考语料库，每个元素为(来源ID, 文本内容)
            
        Returns:
            每个文本的相似项列表
        """
        results = []
        
        for text in texts:
            similarity_items = self.detect_similarity(text, reference_corpus)
            results.append(similarity_items)
        
        return results