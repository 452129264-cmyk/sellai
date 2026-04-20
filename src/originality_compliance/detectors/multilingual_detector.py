"""
多语种原创检测模块
支持跨语言文本相似度计算与原创性评估
"""

import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np

from ..models.data_models import SimilarityItem, RiskLevel, ContentType, CountryCode
from ..utils.similarity_metrics import SimilarityCalculator
from ..utils.text_processor import TextProcessor

logger = logging.getLogger(__name__)


@dataclass
class MultilingualDetectionConfig:
    """多语种检测配置"""
    supported_languages: List[str] = None  # 支持的语言列表
    translation_enabled: bool = True  # 启用翻译
    min_translation_confidence: float = 0.8  # 最小翻译置信度
    cross_language_similarity_threshold: float = 0.75  # 跨语言相似度阈值
    language_specific_rules: Dict[str, Dict[str, Any]] = None  # 语言特定规则
    
    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = ["en", "zh", "fr", "de", "es", "it", "pt", "ru", "ja", "ko"]
        
        if self.language_specific_rules is None:
            self.language_specific_rules = {
                "en": {"stopwords_count": 100, "character_set": "latin"},
                "zh": {"stopwords_count": 200, "character_set": "cjk"},
                "ja": {"stopwords_count": 150, "character_set": "cjk"},
                "ko": {"stopwords_count": 120, "character_set": "hangul"}
            }


class MultilingualDetector:
    """多语种检测器"""
    
    def __init__(self, config: Optional[MultilingualDetectionConfig] = None,
                 translator: Optional[Any] = None):
        """
        初始化多语种检测器
        
        Args:
            config: 检测配置
            translator: 翻译器实例（可选，用于跨语言翻译）
        """
        self.config = config or MultilingualDetectionConfig()
        self.similarity_calculator = SimilarityCalculator()
        self.text_processor = TextProcessor()
        self.translator = translator  # 外部翻译器（如DeepL集成）
        
        # 语言检测器（简化实现）
        self._language_detector = self.text_processor
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        检测文本语言及置信度
        
        Args:
            text: 输入文本
            
        Returns:
            (语言代码, 置信度)
        """
        try:
            # 使用文本处理器检测语言
            language = self._language_detector.detect_language(text)
            
            # 简化置信度计算（基于字符分布）
            confidence = self._calculate_language_confidence(text, language)
            
            return language, confidence
            
        except Exception as e:
            logger.error(f"语言检测失败: {str(e)}")
            return "en", 0.5  # 默认返回英语
    
    def _calculate_language_confidence(self, text: str, detected_language: str) -> float:
        """
        计算语言检测置信度
        
        Args:
            text: 输入文本
            detected_language: 检测到的语言
            
        Returns:
            置信度分数（0.0-1.0）
        """
        if not text:
            return 0.0
        
        # 基于字符分布计算置信度（简化实现）
        if detected_language == "zh":
            # 中文字符比例
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            ratio = chinese_chars / len(text) if len(text) > 0 else 0.0
            return min(1.0, ratio * 1.5)  # 调整权重
        
        elif detected_language == "en":
            # 英文字符比例
            latin_chars = len([c for c in text if 'a' <= c.lower() <= 'z'])
            ratio = latin_chars / len(text) if len(text) > 0 else 0.0
            return min(1.0, ratio * 1.3)
        
        elif detected_language == "ja":
            # 日文字符比例
            japanese_chars = len([c for c in text if 
                                 ('\u3040' <= c <= '\u309f') or  # 平假名
                                 ('\u30a0' <= c <= '\u30ff')])  # 片假名
            ratio = japanese_chars / len(text) if len(text) > 0 else 0.0
            return min(1.0, ratio * 1.4)
        
        else:
            # 其他语言使用通用逻辑
            return 0.7
    
    def translate_text(self, text: str, source_lang: str, target_lang: str = "en") -> Tuple[str, float]:
        """
        翻译文本（简化实现或调用外部翻译器）
        
        Args:
            text: 待翻译文本
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            (翻译文本, 置信度)
        """
        if not self.config.translation_enabled or source_lang == target_lang:
            return text, 1.0
        
        # 如果有外部翻译器，优先使用
        if self.translator:
            try:
                # 假设翻译器有translate方法
                translated_text = self.translator.translate(text, source_lang, target_lang)
                return translated_text, 0.9  # 假设外部翻译器置信度较高
            except Exception as e:
                logger.error(f"外部翻译器调用失败: {str(e)}")
        
        # 简化实现：返回原始文本（实际应集成真实翻译服务）
        # 这里仅做演示
        logger.warning(f"翻译功能未完全实现，返回原始文本: {source_lang} -> {target_lang}")
        return text, 0.5  # 低置信度
    
    def detect_multilingual_similarity(self, 
                                      text: str, 
                                      reference_corpus: List[Tuple[str, str, str]]) -> List[SimilarityItem]:
        """
        多语种相似度检测
        
        Args:
            text: 待检测文本
            reference_corpus: 参考语料库，每个元素为(来源ID, 文本内容, 语言代码)
            
        Returns:
            相似项列表
        """
        # 检测输入文本语言
        text_language, lang_confidence = self.detect_language(text)
        
        logger.info(f"检测到文本语言: {text_language}, 置信度: {lang_confidence}")
        
        similarity_items = []
        
        for source_id, reference_text, ref_language in reference_corpus:
            try:
                # 处理跨语言情况
                if text_language != ref_language and self.config.translation_enabled:
                    # 将参考文本翻译到输入文本语言
                    translated_ref, translation_confidence = self.translate_text(
                        reference_text, ref_language, text_language
                    )
                    
                    if translation_confidence >= self.config.min_translation_confidence:
                        # 计算相似度
                        similarity_result = self.similarity_calculator.calculate_similarity_comprehensive(
                            text, translated_ref
                        )
                        
                        # 调整跨语言相似度阈值
                        adjusted_similarity = similarity_result.combined * 0.9  # 跨语言相似度打折扣
                        
                        matched_text = self._extract_multilingual_match(text, translated_ref)
                        
                        # 风险等级（考虑跨语言因素）
                        risk_level = self._determine_multilingual_risk(
                            adjusted_similarity, 
                            text_language, 
                            ref_language
                        )
                        
                        # 生成建议
                        recommendations = self._generate_multilingual_recommendations(
                            adjusted_similarity, risk_level, text_language, ref_language
                        )
                        
                        similarity_item = SimilarityItem(
                            source_id=source_id,
                            source_type="multilingual_reference",
                            similarity_score=adjusted_similarity,
                            matched_text=matched_text,
                            risk_level=risk_level,
                            recommendations=recommendations,
                            metadata={
                                "original_language": ref_language,
                                "translated_language": text_language,
                                "translation_confidence": translation_confidence
                            }
                        )
                        
                        similarity_items.append(similarity_item)
                
                else:
                    # 同语言直接比较
                    similarity_result = self.similarity_calculator.calculate_similarity_comprehensive(
                        text, reference_text
                    )
                    
                    matched_text = self._extract_multilingual_match(text, reference_text)
                    
                    risk_level = self._determine_multilingual_risk(
                        similarity_result.combined, text_language, text_language
                    )
                    
                    recommendations = self._generate_multilingual_recommendations(
                        similarity_result.combined, risk_level, text_language, text_language
                    )
                    
                    similarity_item = SimilarityItem(
                        source_id=source_id,
                        source_type="monolingual_reference",
                        similarity_score=similarity_result.combined,
                        matched_text=matched_text,
                        risk_level=risk_level,
                        recommendations=recommendations,
                        metadata={
                            "language": text_language
                        }
                    )
                    
                    similarity_items.append(similarity_item)
                    
            except Exception as e:
                logger.error(f"多语种相似度检测失败: {str(e)}")
                continue
        
        # 按相似度排序
        similarity_items.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return similarity_items
    
    def _extract_multilingual_match(self, text1: str, text2: str) -> str:
        """
        提取多语种匹配片段
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            匹配片段
        """
        # 简化实现：找出最长的公共连续词汇（考虑语言差异）
        words1 = text1.split()
        words2 = text2.split()
        
        max_match_length = 0
        best_match = ""
        
        # 查找连续匹配的词汇序列
        for i in range(len(words1)):
            for j in range(len(words2)):
                match_length = 0
                
                while (i + match_length < len(words1) and 
                       j + match_length < len(words2) and
                       words1[i + match_length].lower() == words2[j + match_length].lower()):
                    match_length += 1
                
                if match_length > max_match_length and match_length >= 2:
                    max_match_length = match_length
                    best_match = ' '.join(words1[i:i+match_length])
        
        if best_match:
            return f"匹配片段: {best_match}"
        else:
            return "未找到显著匹配片段"
    
    def _determine_multilingual_risk(self, 
                                    similarity_score: float, 
                                    text_lang: str, 
                                    ref_lang: str) -> RiskLevel:
        """
        确定多语种风险等级
        
        Args:
            similarity_score: 相似度分数
            text_lang: 文本语言
            ref_lang: 参考文本语言
            
        Returns:
            风险等级
        """
        # 跨语言检测时，降低阈值要求
        if text_lang != ref_lang:
            adjusted_threshold = self.config.cross_language_similarity_threshold
            
            if similarity_score >= adjusted_threshold:
                return RiskLevel.HIGH
            elif similarity_score >= adjusted_threshold * 0.8:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
        
        else:
            # 同语言检测，使用标准阈值
            if similarity_score >= 0.85:
                return RiskLevel.HIGH
            elif similarity_score >= 0.65:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
    
    def _generate_multilingual_recommendations(self, 
                                              similarity_score: float,
                                              risk_level: RiskLevel,
                                              text_lang: str,
                                              ref_lang: str) -> List[str]:
        """
        生成多语种建议
        
        Args:
            similarity_score: 相似度分数
            risk_level: 风险等级
            text_lang: 文本语言
            ref_lang: 参考文本语言
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if text_lang != ref_lang:
            # 跨语言情况
            if risk_level == RiskLevel.HIGH:
                recommendations.extend([
                    f"文本与{ref_language_name(ref_lang)}参考内容高度相似，存在跨语言抄袭风险",
                    "建议重新构思核心观点，避免直接翻译现有内容",
                    "考虑添加更多文化适配的原创内容"
                ])
            elif risk_level == RiskLevel.MEDIUM:
                recommendations.extend([
                    f"文本与{ref_language_name(ref_lang)}参考内容部分相似",
                    "建议修改相似部分的表达方式，增加独特性",
                    "确保翻译准确性的同时保持原创性"
                ])
            else:
                recommendations.extend([
                    "文本在多语种环境下原创性良好",
                    "建议继续保持当前创作风格",
                    "定期检查避免无意跨语言相似"
                ])
        
        else:
            # 同语言情况
            if risk_level == RiskLevel.HIGH:
                recommendations.extend([
                    "文本与同语言参考内容高度相似，抄袭风险高",
                    "建议完全重写或大幅修改相似部分",
                    "增加独特分析和创新观点"
                ])
            elif risk_level == RiskLevel.MEDIUM:
                recommendations.extend([
                    "文本与同语言参考内容中度相似",
                    "建议优化表达方式，降低相似度",
                    "加强原创性内容的比例"
                ])
            else:
                recommendations.extend([
                    "文本原创性良好，在同语言环境中表现优秀",
                    "可以继续使用当前文本",
                    "建议多样化表达以增强独特性"
                ])
        
        return recommendations
    
    def analyze_multilingual_patterns(self, 
                                     texts: List[str],
                                     languages: List[str]) -> Dict[str, Any]:
        """
        分析多语种文本模式
        
        Args:
            texts: 文本列表
            languages: 对应的语言列表
            
        Returns:
            模式分析结果
        """
        if len(texts) != len(languages):
            raise ValueError("文本数量与语言数量不匹配")
        
        results = {
            "language_distribution": {},
            "cross_language_similarity": {},
            "text_complexity_by_language": {}
        }
        
        # 语言分布统计
        for lang in languages:
            if lang in results["language_distribution"]:
                results["language_distribution"][lang] += 1
            else:
                results["language_distribution"][lang] = 1
        
        # 同语言文本相似度分析
        language_groups = {}
        for text, lang in zip(texts, languages):
            if lang not in language_groups:
                language_groups[lang] = []
            language_groups[lang].append(text)
        
        for lang, lang_texts in language_groups.items():
            if len(lang_texts) > 1:
                # 计算同语言文本间的平均相似度
                similarities = []
                for i in range(len(lang_texts)):
                    for j in range(i+1, len(lang_texts)):
                        sim_result = self.similarity_calculator.calculate_similarity_comprehensive(
                            lang_texts[i], lang_texts[j]
                        )
                        similarities.append(sim_result.combined)
                
                results["cross_language_similarity"][lang] = {
                    "avg_similarity": np.mean(similarities) if similarities else 0.0,
                    "max_similarity": max(similarities) if similarities else 0.0,
                    "text_count": len(lang_texts)
                }
        
        # 各语言文本复杂度分析
        for lang in set(languages):
            lang_texts = [text for text, text_lang in zip(texts, languages) if text_lang == lang]
            
            if lang_texts:
                complexities = []
                for text in lang_texts:
                    processor = TextProcessor(language=lang)
                    complexity = processor.calculate_text_complexity(text)
                    complexities.append(complexity["complexity_score"])
                
                results["text_complexity_by_language"][lang] = {
                    "avg_complexity": np.mean(complexities) if complexities else 0.0,
                    "text_count": len(lang_texts)
                }
        
        return results


def ref_language_name(lang_code: str) -> str:
    """获取语言名称"""
    language_names = {
        "en": "英语",
        "zh": "中文",
        "fr": "法语",
        "de": "德语",
        "es": "西班牙语",
        "it": "意大利语",
        "pt": "葡萄牙语",
        "ru": "俄语",
        "ja": "日语",
        "ko": "韩语"
    }
    
    return language_names.get(lang_code, f"未知语言({lang_code})")