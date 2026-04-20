"""
DeepL翻译服务集成模块
提供与DeepL API的集成接口，支持多语种翻译功能
"""

import logging
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import hashlib

# 尝试导入DeepL SDK，如果不可用则使用备用方案
try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("DeepL SDK未安装，使用备用翻译方案")

from ..models.data_models import RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class DeepLConfig:
    """DeepL配置"""
    api_key: str = ""                    # API密钥
    api_endpoint: str = "https://api.deepl.com/v2"  # API端点
    plan_type: str = "free"             # 套餐类型（free/pro）
    timeout_seconds: int = 30           # 请求超时时间
    max_retries: int = 3                # 最大重试次数
    cache_enabled: bool = True          # 启用缓存
    cache_ttl_seconds: int = 7200       # 缓存生存时间
    default_target_lang: str = "EN-US"  # 默认目标语言


class DeepLIntegrator:
    """DeepL集成器"""
    
    def __init__(self, config: Optional[DeepLConfig] = None):
        """
        初始化DeepL集成器
        
        Args:
            config: 配置对象
        """
        self.config = config or DeepLConfig()
        
        # 初始化DeepL客户端
        self.translator = None
        if DEEPL_AVAILABLE and self.config.api_key:
            try:
                self.translator = deepl.Translator(self.config.api_key)
                logger.info("DeepL客户端初始化成功")
            except Exception as e:
                logger.error(f"DeepL客户端初始化失败: {str(e)}")
                self.translator = None
        else:
            logger.warning("DeepL SDK不可用或API密钥未配置，使用备用翻译")
        
        # 缓存（简化实现）
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # 语言代码映射
        self._language_mapping = {
            "en": "EN-US", "en-us": "EN-US", "en-gb": "EN-GB",
            "zh": "ZH", "zh-cn": "ZH", "zh-tw": "ZH",
            "fr": "FR", "fr-fr": "FR", "fr-ca": "FR",
            "de": "DE", "de-de": "DE", "de-at": "DE", "de-ch": "DE",
            "es": "ES", "es-es": "ES", "es-mx": "ES",
            "it": "IT", "it-it": "IT",
            "pt": "PT", "pt-pt": "PT", "pt-br": "PT",
            "ru": "RU", "ru-ru": "RU",
            "ja": "JA", "ja-jp": "JA",
            "ko": "KO", "ko-kr": "KO"
        }
    
    def translate_text(self, 
                      text: str, 
                      source_lang: Optional[str] = None,
                      target_lang: Optional[str] = None,
                      formality: Optional[str] = None) -> Tuple[str, float]:
        """
        翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言代码（可选，自动检测）
            target_lang: 目标语言代码（可选，默认EN-US）
            formality: 正式度（less/default/more，可选）
            
        Returns:
            (翻译文本, 置信度)
        """
        if not text or not text.strip():
            return "", 0.0
        
        # 生成缓存键
        cache_key = self._generate_cache_key(text, source_lang, target_lang, formality)
        
        # 检查缓存
        if self.config.cache_enabled and cache_key in self._cache:
            cached_item = self._cache[cache_key]
            if time.time() - cached_item["timestamp"] < self.config.cache_ttl_seconds:
                logger.debug(f"从缓存获取翻译: {cache_key}")
                return cached_item["data"]["translated_text"], cached_item["data"]["confidence"]
        
        # 标准化语言代码
        target_lang = self._normalize_language_code(target_lang or self.config.default_target_lang)
        
        try:
            translated_text = ""
            confidence = 0.8  # 默认置信度
            
            if self.translator:
                # 使用DeepL官方SDK
                translation_result = self.translator.translate_text(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    formality=formality
                )
                
                translated_text = translation_result.text
                
                # 基于字符数和翻译质量估算置信度
                char_count = len(text)
                if char_count > 0:
                    # 简化的置信度计算（实际应用中需要更复杂的逻辑）
                    confidence = min(0.95, 0.7 + (char_count / 1000) * 0.1)
            
            else:
                # 备用翻译方案（简化实现）
                translated_text = self._fallback_translation(text, source_lang, target_lang)
                confidence = 0.5  # 备用翻译置信度较低
            
            # 缓存结果
            if self.config.cache_enabled and translated_text:
                self._cache[cache_key] = {
                    "timestamp": time.time(),
                    "data": {
                        "translated_text": translated_text,
                        "confidence": confidence,
                        "source_lang": source_lang,
                        "target_lang": target_lang
                    }
                }
            
            return translated_text, confidence
            
        except Exception as e:
            logger.error(f"翻译文本失败: {str(e)}")
            # 返回原始文本作为后备
            return text, 0.3
    
    def translate_batch(self, 
                       texts: List[str],
                       source_lang: Optional[str] = None,
                       target_lang: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        批量翻译文本
        
        Args:
            texts: 文本列表
            source_lang: 源语言代码（可选）
            target_lang: 目标语言代码（可选）
            
        Returns:
            翻译结果列表，每个元素为(翻译文本, 置信度)
        """
        results = []
        
        for text in texts:
            translated_text, confidence = self.translate_text(
                text, source_lang, target_lang
            )
            results.append((translated_text, confidence))
        
        return results
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        检测文本语言
        
        Args:
            text: 输入文本
            
        Returns:
            (语言代码, 置信度)
        """
        if not text or not text.strip():
            return "unknown", 0.0
        
        try:
            if self.translator:
                # 使用DeepL语言检测
                detection_result = self.translator.detect_language(text)
                language = detection_result.lang
                confidence = detection_result.confidence or 0.8
                
                # 标准化语言代码
                language = self._normalize_language_code(language)
                
                return language, confidence
                
            else:
                # 备用语言检测
                # 这里可以集成其他语言检测库，简化实现
                language = self._fallback_language_detection(text)
                return language, 0.6
                
        except Exception as e:
            logger.error(f"语言检测失败: {str(e)}")
            return "en", 0.5  # 默认返回英语
    
    def get_usage_info(self) -> Optional[Dict[str, Any]]:
        """
        获取DeepL API使用情况
        
        Returns:
            使用信息字典
        """
        if not self.translator:
            return None
        
        try:
            usage = self.translator.get_usage()
            
            return {
                "character_count": usage.character_count,
                "character_limit": usage.character_limit,
                "character_remaining": usage.character_limit - usage.character_count,
                "limit_reached": usage.character_limit_reached
            }
            
        except Exception as e:
            logger.error(f"获取使用信息失败: {str(e)}")
            return None
    
    def _fallback_translation(self, 
                            text: str, 
                            source_lang: Optional[str],
                            target_lang: str) -> str:
        """
        备用翻译方案（简化实现）
        
        注意：实际应用中应该集成其他翻译服务或使用离线翻译模型
        这里仅提供示例实现，实际效果有限
        """
        # 简化翻译表（仅示例）
        translation_dict = {
            # 简单词汇翻译
            "hello": {"ZH": "你好", "FR": "bonjour", "DE": "hallo", "ES": "hola"},
            "world": {"ZH": "世界", "FR": "monde", "DE": "welt", "ES": "mundo"},
            "thank you": {"ZH": "谢谢", "FR": "merci", "DE": "danke", "ES": "gracias"},
            "good morning": {"ZH": "早上好", "FR": "bonjour", "DE": "guten morgen", "ES": "buenos días"}
        }
        
        # 转换为小写用于匹配
        text_lower = text.lower().strip()
        
        # 检查是否有直接匹配
        for phrase, translations in translation_dict.items():
            if phrase in text_lower:
                if target_lang in translations:
                    # 替换短语（简化实现）
                    return text.replace(phrase, translations[target_lang])
        
        # 如果没有匹配，返回原始文本（实际应用中应使用真实翻译）
        return text
    
    def _fallback_language_detection(self, text: str) -> str:
        """
        备用语言检测（简化实现）
        
        基于字符分布进行简单检测
        """
        import re
        
        # 检测中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars / max(len(text), 1) > 0.3:
            return "zh"
        
        # 检测日文字符
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
        if japanese_chars / max(len(text), 1) > 0.3:
            return "ja"
        
        # 检测韩文字符
        korean_chars = len(re.findall(r'[\uac00-\ud7af]', text))
        if korean_chars / max(len(text), 1) > 0.3:
            return "ko"
        
        # 常见词汇检测（简化）
        language_indicators = {
            "en": ["the", "and", "that", "for", "with"],
            "fr": ["le", "la", "les", "et", "de"],
            "de": ["der", "die", "das", "und", "in"],
            "es": ["el", "la", "y", "en", "de"],
            "it": ["il", "la", "e", "di", "in"],
            "pt": ["o", "a", "e", "do", "da"],
            "ru": ["и", "в", "не", "на", "с"]  # 俄语常见词
        }
        
        text_lower = text.lower()
        
        best_lang = "en"
        best_score = 0
        
        for lang, indicators in language_indicators.items():
            score = sum(1 for word in indicators if f" {word} " in f" {text_lower} ")
            if score > best_score:
                best_score = score
                best_lang = lang
        
        return best_lang
    
    def _normalize_language_code(self, lang_code: str) -> str:
        """
        标准化语言代码
        
        Args:
            lang_code: 原始语言代码
            
        Returns:
            标准化后的语言代码
        """
        if not lang_code:
            return self.config.default_target_lang
        
        # 转换为小写
        lang_lower = lang_code.lower()
        
        # 查找映射
        for key, value in self._language_mapping.items():
            if lang_lower == key:
                return value
        
        # 如果没有找到映射，尝试直接匹配
        if lang_lower in ["en-us", "en"]:
            return "EN-US"
        elif lang_lower == "en-gb":
            return "EN-GB"
        elif lang_lower in ["zh-cn", "zh"]:
            return "ZH"
        
        # 默认返回输入值（大写）
        return lang_code.upper()
    
    def _generate_cache_key(self, *args) -> str:
        """生成缓存键"""
        key_string = ":".join(str(arg) for arg in args if arg is not None)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def validate_api_key(self) -> Tuple[bool, Optional[str]]:
        """
        验证API密钥有效性
        
        Returns:
            (是否有效, 错误信息)
        """
        if not self.config.api_key or self.config.api_key == "your_deepl_auth_key_here":
            return False, "API密钥未配置或使用默认值"
        
        if not DEEPL_AVAILABLE:
            return False, "DeepL SDK不可用"
        
        try:
            # 尝试调用简单的API验证
            test_text = "test"
            translation_result = self.translator.translate_text(
                text=test_text,
                target_lang="EN-US"
            )
            
            if translation_result and translation_result.text:
                return True, None
            else:
                return False, "API调用返回空结果"
                
        except deepl.exceptions.AuthorizationException:
            return False, "API密钥无效"
        except Exception as e:
            return False, f"API验证失败: {str(e)}"
    
    def get_supported_languages(self) -> Dict[str, List[str]]:
        """
        获取支持的语言列表
        
        Returns:
            支持的语言字典
        """
        if self.translator:
            try:
                # 获取DeepL支持的语言
                source_langs = self.translator.get_source_languages()
                target_langs = self.translator.get_target_languages()
                
                return {
                    "source_languages": [{"code": lang.code, "name": lang.name} for lang in source_langs],
                    "target_languages": [{"code": lang.code, "name": lang.name} for lang in target_langs]
                }
            except Exception:
                pass
        
        # 返回默认支持的语言
        return {
            "source_languages": [
                {"code": "EN", "name": "English"},
                {"code": "ZH", "name": "Chinese"},
                {"code": "FR", "name": "French"},
                {"code": "DE", "name": "German"},
                {"code": "ES", "name": "Spanish"},
                {"code": "IT", "name": "Italian"},
                {"code": "PT", "name": "Portuguese"},
                {"code": "RU", "name": "Russian"},
                {"code": "JA", "name": "Japanese"},
                {"code": "KO", "name": "Korean"}
            ],
            "target_languages": [
                {"code": "EN-US", "name": "English (American)"},
                {"code": "EN-GB", "name": "English (British)"},
                {"code": "ZH", "name": "Chinese"},
                {"code": "FR", "name": "French"},
                {"code": "DE", "name": "German"},
                {"code": "ES", "name": "Spanish"},
                {"code": "IT", "name": "Italian"},
                {"code": "PT", "name": "Portuguese"},
                {"code": "RU", "name": "Russian"},
                {"code": "JA", "name": "Japanese"},
                {"code": "KO", "name": "Korean"}
            ]
        }