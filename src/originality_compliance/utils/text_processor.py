"""
文本处理工具模块
"""

import re
import string
import hashlib
from typing import List, Tuple, Optional, Dict, Any
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import unicodedata


class TextProcessor:
    """文本处理器"""
    
    def __init__(self, language: str = "en"):
        """
        初始化文本处理器
        
        Args:
            language: 文本语言（en/zh/fr/de/es/ja/ko等）
        """
        self.language = language
        self._download_nltk_resources()
        
        # 语言特定的停用词
        self.stop_words = self._get_stopwords(language)
        
    def _download_nltk_resources(self):
        """下载NLTK必要资源"""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
    
    def _get_stopwords(self, language: str) -> set:
        """获取对应语言的停用词"""
        language_map = {
            "en": "english",
            "zh": "chinese",
            "fr": "french", 
            "de": "german",
            "es": "spanish",
            "it": "italian",
            "pt": "portuguese",
            "ru": "russian",
            "ja": "japanese",
            "ko": "korean"
        }
        
        try:
            nltk_lang = language_map.get(language, "english")
            return set(stopwords.words(nltk_lang))
        except:
            return set()
    
    def normalize_text(self, text: str) -> str:
        """
        文本归一化处理
        
        Args:
            text: 原始文本
            
        Returns:
            归一化后的文本
        """
        # 转换为小写（对英文）
        if self.language in ["en", "de", "fr", "es", "it", "pt"]:
            text = text.lower()
        
        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 移除特殊字符（保留基本标点）
        if self.language == "zh":
            # 中文保留中文标点
            text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？；："''、（）《》【】]', ' ', text)
        else:
            # 其他语言保留基本标点
            text = re.sub(r'[^\w\s.,!?;:"\'()-]', ' ', text)
        
        return text
    
    def tokenize_words(self, text: str) -> List[str]:
        """
        分词处理
        
        Args:
            text: 输入文本
            
        Returns:
            词汇列表
        """
        try:
            if self.language == "zh":
                # 中文简单分词（按字符）
                tokens = [char for char in text if char.strip()]
            else:
                # 其他语言使用NLTK分词
                tokens = word_tokenize(text, language=self.language)
            
            # 移除停用词
            tokens = [token for token in tokens if token not in self.stop_words]
            
            return tokens
        except:
            # 备用简单分词
            return [word for word in text.split() if word.strip()]
    
    def extract_ngrams(self, text: str, n: int = 3) -> List[str]:
        """
        提取n-gram特征
        
        Args:
            text: 输入文本
            n: n-gram大小
            
        Returns:
            n-gram列表
        """
        tokens = self.tokenize_words(text)
        ngrams = []
        
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i+n])
            ngrams.append(ngram)
        
        return ngrams
    
    def calculate_text_hash(self, text: str, method: str = "md5") -> str:
        """
        计算文本哈希值
        
        Args:
            text: 输入文本
            method: 哈希方法（md5/sha256/sha1）
            
        Returns:
            哈希字符串
        """
        normalized_text = self.normalize_text(text)
        
        if method == "md5":
            return hashlib.md5(normalized_text.encode()).hexdigest()
        elif method == "sha256":
            return hashlib.sha256(normalized_text.encode()).hexdigest()
        elif method == "sha1":
            return hashlib.sha1(normalized_text.encode()).hexdigest()
        else:
            raise ValueError(f"不支持的哈希方法: {method}")
    
    def detect_language(self, text: str) -> str:
        """
        检测文本语言（简化版）
        
        Args:
            text: 输入文本
            
        Returns:
            语言代码（en/zh/fr/de/es/ja/ko等）
        """
        # 简单启发式检测
        text_lower = text.lower()
        
        # 中文字符检测
        if re.search(r'[\u4e00-\u9fff]', text):
            return "zh"
        
        # 日文字符检测
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):  # 平假名/片假名
            return "ja"
        
        # 韩文字符检测
        if re.search(r'[\uac00-\ud7af]', text):
            return "ko"
        
        # 常见词汇检测（简化）
        common_words = {
            "en": ["the", "and", "that", "for", "with"],
            "fr": ["le", "la", "les", "et", "de"],
            "de": ["der", "die", "das", "und", "in"],
            "es": ["el", "la", "y", "en", "de"],
            "it": ["il", "la", "e", "di", "in"],
            "pt": ["o", "a", "e", "do", "da"]
        }
        
        scores = {}
        for lang, words in common_words.items():
            score = sum(1 for word in words if f" {word} " in f" {text_lower} ")
            scores[lang] = score
        
        if scores:
            best_lang = max(scores.items(), key=lambda x: x[1])
            if best_lang[1] > 0:
                return best_lang[0]
        
        # 默认返回英语
        return "en"
    
    def extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """
        提取关键词短语
        
        Args:
            text: 输入文本
            max_phrases: 最大短语数量
            
        Returns:
            关键词短语列表
        """
        tokens = self.tokenize_words(text)
        
        # 提取2-3个词的短语
        phrases = []
        for n in [2, 3]:
            ngrams = self.extract_ngrams(text, n)
            phrases.extend(ngrams)
        
        # 按频率排序
        from collections import Counter
        phrase_counter = Counter(phrases)
        
        # 返回最常见的短语
        return [phrase for phrase, _ in phrase_counter.most_common(max_phrases)]
    
    def calculate_text_complexity(self, text: str) -> Dict[str, float]:
        """
        计算文本复杂度指标
        
        Args:
            text: 输入文本
            
        Returns:
            复杂度指标字典
        """
        sentences = sent_tokenize(text, language=self.language)
        words = self.tokenize_words(text)
        
        if len(sentences) == 0 or len(words) == 0:
            return {
                "avg_sentence_length": 0,
                "avg_word_length": 0,
                "lexical_diversity": 0,
                "complexity_score": 0
            }
        
        # 平均句长
        avg_sentence_length = len(words) / len(sentences)
        
        # 平均词长
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # 词汇多样性（不同词汇比例）
        unique_words = set(words)
        lexical_diversity = len(unique_words) / len(words) if len(words) > 0 else 0
        
        # 综合复杂度分数
        complexity_score = (avg_sentence_length * 0.3 + 
                          avg_word_length * 0.2 + 
                          lexical_diversity * 0.5)
        
        return {
            "avg_sentence_length": avg_sentence_length,
            "avg_word_length": avg_word_length,
            "lexical_diversity": lexical_diversity,
            "complexity_score": complexity_score
        }
    
    def sanitize_text(self, text: str) -> str:
        """
        文本消毒处理（移除敏感信息）
        
        Args:
            text: 输入文本
            
        Returns:
            消毒后的文本
        """
        # 移除邮箱地址
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # 移除电话号码（简化模式）
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        
        # 移除URL
        text = re.sub(r'https?://\S+', '[URL]', text)
        
        return text