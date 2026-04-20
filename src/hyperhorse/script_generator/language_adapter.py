#!/usr/bin/env python3
"""
多语言适配器
实现脚本内容的多语言翻译、本地化适配与文化敏感性检查
支持全球主流市场语言
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class LanguageCode(str, Enum):
    """语言代码枚举"""
    ENGLISH = "en"           # 英语
    SPANISH = "es"           # 西班牙语
    ARABIC = "ar"            # 阿拉伯语
    PORTUGUESE = "pt"        # 葡萄牙语
    FRENCH = "fr"            # 法语
    GERMAN = "de"            # 德语
    JAPANISH = "ja"          # 日语
    KOREAN = "ko"            # 韩语
    CHINESE_SIMPLIFIED = "zh-CN"  # 简体中文
    CHINESE_TRADITIONAL = "zh-TW"  # 繁体中文
    RUSSIAN = "ru"           # 俄语
    ITALIAN = "it"           # 意大利语

class CulturalRegion(str, Enum):
    """文化区域枚举"""
    WESTERN = "western"          # 西方文化
    MIDDLE_EASTERN = "middle_eastern"  # 中东文化
    EAST_ASIAN = "east_asian"    # 东亚文化
    SOUTH_ASIAN = "south_asian"  # 南亚文化
    LATIN_AMERICAN = "latin_american"  # 拉丁美洲
    AFRICAN = "african"          # 非洲文化
    GLOBAL = "global"           # 全球通用

@dataclass
class LocalizationRule:
    """本地化规则"""
    source_pattern: str
    target_pattern: str
    language: LanguageCode
    context: str  # 适用上下文

@dataclass
class CulturalSensitivityCheck:
    """文化敏感性检查结果"""
    has_issues: bool
    issues: List[str]
    severity: str  # low, medium, high
    suggestions: List[str]

class LanguageAdapter:
    """多语言适配器"""
    
    def __init__(self):
        """初始化多语言适配器"""
        # 加载本地化规则
        self.localization_rules = self._load_localization_rules()
        
        # 文化敏感性词汇库
        self.cultural_sensitive_terms = self._load_sensitive_terms()
        
        # 语言特定规则
        self.language_specific_rules = self._load_language_specific_rules()
        
        logger.info("多语言适配器初始化完成")
    
    def adapt_content(self,
                     content: Dict[str, Any],
                     target_language: LanguageCode,
                     target_culture: CulturalRegion = CulturalRegion.WESTERN) -> Dict[str, Any]:
        """
        适配内容到目标语言和文化
        
        Args:
            content: 原始内容
            target_language: 目标语言
            target_culture: 目标文化区域
            
        Returns:
            Dict[str, Any]: 适配后的内容
        """
        logger.info(f"适配内容到语言：{target_language.value}，文化：{target_culture.value}")
        
        # 深度复制内容
        adapted_content = content.copy()
        
        # 适配标题
        if 'title' in adapted_content:
            adapted_content['title'] = self._adapt_text(
                text=adapted_content['title'],
                target_language=target_language,
                target_culture=target_culture
            )
        
        # 适配描述
        if 'description' in adapted_content:
            adapted_content['description'] = self._adapt_text(
                text=adapted_content['description'],
                target_language=target_language,
                target_culture=target_culture
            )
        
        # 适配场景文本
        if 'scenes' in adapted_content and isinstance(adapted_content['scenes'], list):
            for scene in adapted_content['scenes']:
                if 'text' in scene:
                    scene['text'] = self._adapt_text(
                        text=scene['text'],
                        target_language=target_language,
                        target_culture=target_culture
                    )
        
        # 适配行动号召
        if 'call_to_action' in adapted_content:
            adapted_content['call_to_action'] = self._adapt_call_to_action(
                cta=adapted_content['call_to_action'],
                target_language=target_language,
                target_culture=target_culture
            )
        
        # 适配关键词和标签
        if 'keywords' in adapted_content:
            adapted_content['keywords'] = self._adapt_keywords(
                keywords=adapted_content['keywords'],
                target_language=target_language,
                target_culture=target_culture
            )
        
        if 'tags' in adapted_content:
            adapted_content['tags'] = self._adapt_hashtags(
                tags=adapted_content['tags'],
                target_language=target_language,
                target_culture=target_culture
            )
        
        # 文化敏感性检查
        sensitivity_check = self.check_cultural_sensitivity(
            content=adapted_content,
            target_culture=target_culture
        )
        
        if sensitivity_check.has_issues:
            logger.warning(f"文化敏感性检查发现问题：{sensitivity_check.issues}")
            # 应用修复建议
            adapted_content = self._apply_sensitivity_fixes(
                content=adapted_content,
                suggestions=sensitivity_check.suggestions,
                target_language=target_language
            )
        
        return adapted_content
    
    def translate_text(self,
                      text: str,
                      source_language: LanguageCode,
                      target_language: LanguageCode,
                      context: str = "general") -> str:
        """
        翻译文本
        
        Args:
            text: 源文本
            source_language: 源语言
            target_language: 目标语言
            context: 文本上下文
            
        Returns:
            str: 翻译后的文本
        """
        logger.info(f"翻译文本：{source_language.value} -> {target_language.value}")
        
        # 简化的翻译逻辑
        # 实际实现应该调用翻译API（如DeepL）
        
        # 如果目标语言是英语，返回原始文本（假设源文本是英语）
        if target_language == LanguageCode.ENGLISH:
            return text
        
        # 模拟翻译
        translation_map = {
            LanguageCode.SPANISH: {
                "product": "producto",
                "demo": "demostración",
                "buy now": "comprar ahora",
                "limited time offer": "oferta por tiempo limitado"
            },
            LanguageCode.FRENCH: {
                "product": "produit",
                "demo": "démonstration",
                "buy now": "acheter maintenant",
                "limited time offer": "offre à durée limitée"
            },
            LanguageCode.GERMAN: {
                "product": "Produkt",
                "demo": "Demonstration",
                "buy now": "Jetzt kaufen",
                "limited time offer": "Zeitlich begrenztes Angebot"
            },
            LanguageCode.JAPANESE: {
                "product": "製品",
                "demo": "デモ",
                "buy now": "今すぐ購入",
                "limited time offer": "期間限定オファー"
            }
        }
        
        # 简单的词对词翻译（实际应该使用完整的翻译模型）
        translated_text = text
        if target_language in translation_map:
            term_map = translation_map[target_language]
            for source_term, target_term in term_map.items():
                translated_text = translated_text.replace(source_term, target_term)
        
        return translated_text
    
    def check_cultural_sensitivity(self,
                                  content: Dict[str, Any],
                                  target_culture: CulturalRegion) -> CulturalSensitivityCheck:
        """
        检查文化敏感性
        
        Args:
            content: 内容
            target_culture: 目标文化区域
            
        Returns:
            CulturalSensitivityCheck: 检查结果
        """
        issues = []
        severity = "low"
        
        # 提取所有文本
        all_text = self._extract_all_text(content)
        
        # 检查敏感词汇
        sensitive_terms = self.cultural_sensitive_terms.get(target_culture, {})
        
        for text in all_text:
            text_lower = text.lower()
            
            for category, terms in sensitive_terms.items():
                for term in terms:
                    if term in text_lower:
                        issues.append(f"在文本中发现敏感词汇 '{term}'（类别：{category}）")
                        if category in ['religious', 'political']:
                            severity = "high"
                        elif category in ['cultural', 'historical']:
                            severity = "medium"
        
        # 检查文化不适当的表达
        cultural_inappropriateness = self._check_cultural_appropriateness(
            content=content,
            target_culture=target_culture
        )
        
        if cultural_inappropriateness:
            issues.extend(cultural_inappropriateness)
            severity = "medium" if severity == "low" else severity
        
        # 生成建议
        suggestions = self._generate_sensitivity_suggestions(issues, target_culture)
        
        return CulturalSensitivityCheck(
            has_issues=len(issues) > 0,
            issues=issues,
            severity=severity,
            suggestions=suggestions
        )
    
    def get_language_specific_guidelines(self, language: LanguageCode) -> Dict[str, Any]:
        """
        获取语言特定指南
        
        Args:
            language: 目标语言
            
        Returns:
            Dict[str, Any]: 语言指南
        """
        guidelines = {
            LanguageCode.ENGLISH: {
                "preferred_length": "中等长度句子",
                "formality_level": "中性到非正式",
                "common_phrases": ["Check this out", "You need this", "Don't miss out"],
                "avoid": ["过于正式的表达", "地域性俚语"]
            },
            LanguageCode.SPANISH: {
                "preferred_length": "稍长句子",
                "formality_level": "温暖而直接",
                "common_phrases": ["¡Mira esto!", "Esto es lo que necesitas", "No te lo pierdas"],
                "avoid": ["英式直译", "过于正式的表达"]
            },
            LanguageCode.JAPANESE: {
                "preferred_length": "短到中等句子",
                "formality_level": "礼貌但不过于正式",
                "common_phrases": ["見てください", "これが必要です", "お見逃しなく"],
                "avoid": ["直接翻译", "过于随意的表达"]
            },
            LanguageCode.ARABIC: {
                "preferred_length": "中等长度句子",
                "formality_level": "尊重而热情",
                "common_phrases": ["شاهد هذا", "أنت تحتاج هذا", "لا تفوت الفرصة"],
                "avoid": ["从右向左排版问题", "文化不敏感内容"]
            },
            LanguageCode.CHINESE_SIMPLIFIED: {
                "preferred_length": "短句",
                "formality_level": "直接而友好",
                "common_phrases": ["看看这个", "你需要这个", "不要错过"],
                "avoid": ["过于复杂的表达", "方言词汇"]
            }
        }
        
        return guidelines.get(language, guidelines[LanguageCode.ENGLISH])
    
    def _adapt_text(self,
                   text: str,
                   target_language: LanguageCode,
                   target_culture: CulturalRegion) -> str:
        """适配文本"""
        # 应用本地化规则
        adapted_text = text
        
        for rule in self.localization_rules:
            if rule.language == target_language:
                adapted_text = adapted_text.replace(
                    rule.source_pattern,
                    rule.target_pattern
                )
        
        # 语言特定调整
        language_rules = self.language_specific_rules.get(target_language, {})
        
        # 调整问候语和表达
        if 'greeting_patterns' in language_rules:
            for pattern, replacement in language_rules['greeting_patterns'].items():
                if re.search(pattern, adapted_text, re.IGNORECASE):
                    adapted_text = re.sub(pattern, replacement, adapted_text, flags=re.IGNORECASE)
        
        # 调整标点符号
        if 'punctuation_rules' in language_rules:
            punctuation_map = language_rules['punctuation_rules']
            for source, target in punctuation_map.items():
                adapted_text = adapted_text.replace(source, target)
        
        return adapted_text
    
    def _adapt_call_to_action(self,
                             cta: str,
                             target_language: LanguageCode,
                             target_culture: CulturalRegion) -> str:
        """适配行动号召"""
        # CTA翻译映射
        cta_translations = {
            LanguageCode.ENGLISH: {
                "buy now": "Buy Now",
                "learn more": "Learn More",
                "click here": "Click Here",
                "shop now": "Shop Now"
            },
            LanguageCode.SPANISH: {
                "buy now": "Comprar Ahora",
                "learn more": "Saber Más",
                "click here": "Haz Clic Aquí",
                "shop now": "Comprar Ahora"
            },
            LanguageCode.FRENCH: {
                "buy now": "Acheter Maintenant",
                "learn more": "En Savoir Plus",
                "click here": "Cliquez Ici",
                "shop now": "Acheter Maintenant"
            },
            LanguageCode.GERMAN: {
                "buy now": "Jetzt Kaufen",
                "learn more": "Mehr Erfahren",
                "click here": "Hier Klicken",
                "shop now": "Jetzt Einkaufen"
            },
            LanguageCode.JAPANESE: {
                "buy now": "今すぐ購入",
                "learn more": "詳細を見る",
                "click here": "こちらをクリック",
                "shop now": "今すぐ購入"
            },
            LanguageCode.CHINESE_SIMPLIFIED: {
                "buy now": "立即购买",
                "learn more": "了解更多",
                "click here": "点击这里",
                "shop now": "立即购买"
            }
        }
        
        # 查找匹配的CTA
        cta_lower = cta.lower()
        translations = cta_translations.get(target_language, cta_translations[LanguageCode.ENGLISH])
        
        for english_cta, translated_cta in translations.items():
            if english_cta in cta_lower:
                return translated_cta
        
        # 如果没有匹配，返回原始CTA
        return cta
    
    def _adapt_keywords(self,
                       keywords: List[str],
                       target_language: LanguageCode,
                       target_culture: CulturalRegion) -> List[str]:
        """适配关键词"""
        # 简单的关键词翻译
        keyword_translations = {
            LanguageCode.ENGLISH: {
                "product": "product",
                "review": "review",
                "unboxing": "unboxing",
                "tutorial": "tutorial"
            },
            LanguageCode.SPANISH: {
                "product": "producto",
                "review": "reseña",
                "unboxing": "unboxing",
                "tutorial": "tutorial"
            },
            LanguageCode.FRENCH: {
                "product": "produit",
                "review": "avis",
                "unboxing": "déballage",
                "tutorial": "tutoriel"
            }
        }
        
        translated_keywords = []
        translations = keyword_translations.get(target_language, keyword_translations[LanguageCode.ENGLISH])
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            translated = translations.get(keyword_lower, keyword)
            translated_keywords.append(translated)
        
        return translated_keywords
    
    def _adapt_hashtags(self,
                       tags: List[str],
                       target_language: LanguageCode,
                       target_culture: CulturalRegion) -> List[str]:
        """适配标签"""
        # 标签通常保持原样或添加本地化版本
        adapted_tags = []
        
        for tag in tags:
            # 如果标签是英文，可能添加本地化版本
            if target_language != LanguageCode.ENGLISH and tag.startswith('#'):
                base_tag = tag[1:]
                # 简单的标签翻译映射
                hashtag_translations = {
                    LanguageCode.SPANISH: {
                        "productreview": "resenadeproducto",
                        "unboxing": "unboxing",
                        "tutorial": "tutorial"
                    },
                    LanguageCode.FRENCH: {
                        "productreview": "avisproduit",
                        "unboxing": "deballage",
                        "tutorial": "tutoriel"
                    }
                }
                
                translations = hashtag_translations.get(target_language, {})
                translated = translations.get(base_tag.lower(), base_tag)
                adapted_tags.append(f"#{translated}")
            else:
                adapted_tags.append(tag)
        
        return adapted_tags
    
    def _load_localization_rules(self) -> List[LocalizationRule]:
        """加载本地化规则"""
        rules = [
            LocalizationRule(
                source_pattern="Check this out",
                target_pattern="¡Mira esto!",
                language=LanguageCode.SPANISH,
                context="title"
            ),
            LocalizationRule(
                source_pattern="You need this",
                target_pattern="Esto es lo que necesitas",
                language=LanguageCode.SPANISH,
                context="description"
            ),
            LocalizationRule(
                source_pattern="Don't miss out",
                target_pattern="No te lo pierdas",
                language=LanguageCode.SPANISH,
                context="cta"
            ),
            LocalizationRule(
                source_pattern="Check this out",
                target_pattern="Regardez ceci",
                language=LanguageCode.FRENCH,
                context="title"
            ),
            LocalizationRule(
                source_pattern="Buy Now",
                target_pattern="Acheter Maintenant",
                language=LanguageCode.FRENCH,
                context="cta"
            ),
            LocalizationRule(
                source_pattern="Limited Time Offer",
                target_pattern="Offre à Durée Limitée",
                language=LanguageCode.FRENCH,
                context="title"
            )
        ]
        
        return rules
    
    def _load_sensitive_terms(self) -> Dict[CulturalRegion, Dict[str, List[str]]]:
        """加载敏感词汇库"""
        sensitive_terms = {
            CulturalRegion.WESTERN: {
                "religious": ["jesus", "christ", "bible"],
                "political": ["trump", "biden", "brexit"],
                "cultural": ["native american", "first nations"]
            },
            CulturalRegion.MIDDLE_EASTERN: {
                "religious": ["allah", "mohammed", "quran", "islam"],
                "political": ["israel", "palestine", "iran"],
                "cultural": ["arab", "persian", "bedouin"]
            },
            CulturalRegion.EAST_ASIAN: {
                "religious": ["buddha", "confucius", "dao"],
                "political": ["taiwan", "north korea", "hong kong"],
                "cultural": ["samurai", "geisha", "mandarin"]
            },
            CulturalRegion.GLOBAL: {
                "general": ["war", "death", "poverty", "disease"]
            }
        }
        
        return sensitive_terms
    
    def _load_language_specific_rules(self) -> Dict[LanguageCode, Dict[str, Any]]:
        """加载语言特定规则"""
        rules = {
            LanguageCode.SPANISH: {
                "greeting_patterns": {
                    r"\bhello\b": "¡Hola!",
                    r"\bhi\b": "¡Hola!"
                },
                "punctuation_rules": {
                    "!": "¡",
                    "?": "¿"
                }
            },
            LanguageCode.ARABIC: {
                "greeting_patterns": {
                    r"\bhello\b": "مرحبًا",
                    r"\bhi\b": "مرحبًا"
                },
                "text_direction": "rtl"
            },
            LanguageCode.JAPANESE: {
                "greeting_patterns": {
                    r"\bhello\b": "こんにちは",
                    r"\bhi\b": "こんにちは"
                },
                "formality_indicators": ["です", "ます"]
            }
        }
        
        return rules
    
    def _extract_all_text(self, content: Dict[str, Any]) -> List[str]:
        """提取所有文本"""
        all_text = []
        
        # 标题
        if 'title' in content and content['title']:
            all_text.append(content['title'])
        
        # 描述
        if 'description' in content and content['description']:
            all_text.append(content['description'])
        
        # 场景文本
        if 'scenes' in content and isinstance(content['scenes'], list):
            for scene in content['scenes']:
                if 'text' in scene and scene['text']:
                    all_text.append(scene['text'])
        
        # 行动号召
        if 'call_to_action' in content and content['call_to_action']:
            all_text.append(content['call_to_action'])
        
        # 关键词和标签
        if 'keywords' in content:
            all_text.extend([str(k) for k in content['keywords']])
        
        if 'tags' in content:
            all_text.extend([str(t) for t in content['tags']])
        
        return all_text
    
    def _check_cultural_appropriateness(self,
                                       content: Dict[str, Any],
                                       target_culture: CulturalRegion) -> List[str]:
        """检查文化适当性"""
        issues = []
        
        # 检查颜色象征意义
        if 'visual_elements' in content:
            # 不同文化中颜色的含义不同
            color_issues = self._check_color_symbolism(content['visual_elements'], target_culture)
            if color_issues:
                issues.extend(color_issues)
        
        # 检查手势和肢体语言
        if 'scenes' in content:
            gesture_issues = self._check_gestures(content['scenes'], target_culture)
            if gesture_issues:
                issues.extend(gesture_issues)
        
        return issues
    
    def _check_color_symbolism(self,
                              visual_elements: List[Dict[str, Any]],
                              target_culture: CulturalRegion) -> List[str]:
        """检查颜色象征意义"""
        issues = []
        
        # 颜色象征意义映射
        color_symbolism = {
            CulturalRegion.WESTERN: {
                "white": ["纯洁", "婚礼"],
                "black": ["哀悼", "正式"],
                "red": ["危险", "爱情", "激情"]
            },
            CulturalRegion.EAST_ASIAN: {
                "white": ["哀悼", "死亡"],
                "red": ["好运", "庆祝", "繁荣"],
                "yellow": ["皇室", "神圣"]
            },
            CulturalRegion.MIDDLE_EASTERN: {
                "green": ["伊斯兰", "天堂", "繁荣"],
                "black": ["哀悼", "神秘"]
            }
        }
        
        # 简化检查
        return issues
    
    def _check_gestures(self,
                       scenes: List[Dict[str, Any]],
                       target_culture: CulturalRegion) -> List[str]:
        """检查手势和肢体语言"""
        issues = []
        
        # 手势文化差异
        gesture_differences = {
            CulturalRegion.WESTERN: {
                "ok_gesture": "积极",
                "thumbs_up": "积极"
            },
            CulturalRegion.MIDDLE_EASTERN: {
                "thumbs_up": "可能冒犯"
            },
            CulturalRegion.EAST_ASIAN: {
                "pointing": "可能不礼貌"
            }
        }
        
        # 简化检查
        return issues
    
    def _generate_sensitivity_suggestions(self,
                                        issues: List[str],
                                        target_culture: CulturalRegion) -> List[str]:
        """生成敏感性建议"""
        suggestions = []
        
        if issues:
            suggestions.append(f"建议进行{target_culture.value}文化的本地化审查")
            suggestions.append("考虑使用文化中性词汇替换敏感术语")
            suggestions.append("咨询目标市场的本地专家获取反馈")
        
        return suggestions
    
    def _apply_sensitivity_fixes(self,
                                content: Dict[str, Any],
                                suggestions: List[str],
                                target_language: LanguageCode) -> Dict[str, Any]:
        """应用敏感性修复"""
        # 简化实现
        logger.info(f"应用文化敏感性修复，建议：{suggestions}")
        return content