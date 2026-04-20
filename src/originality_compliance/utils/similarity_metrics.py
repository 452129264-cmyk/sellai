"""
相似度度量工具模块
"""

import math
from typing import List, Tuple, Dict, Set, Any
import numpy as np
from dataclasses import dataclass
from collections import Counter
import hashlib


@dataclass
class SimilarityResult:
    """相似度计算结果"""
    jaccard: float = 0.0       # Jaccard相似度
    cosine: float = 0.0        # 余弦相似度
    edit_distance: float = 0.0  # 编辑距离（归一化）
    simhash: float = 0.0       # SimHash相似度
    semantic: float = 0.0      # 语义相似度（待实现）
    combined: float = 0.0      # 综合相似度分数


class SimilarityCalculator:
    """相似度计算器"""
    
    def __init__(self):
        pass
    
    def calculate_jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """
        计算Jaccard相似度
        
        Args:
            set1: 集合1
            set2: 集合2
            
        Returns:
            Jaccard相似度（0.0-1.0）
        """
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1（词频向量）
            vec2: 向量2（词频向量）
            
        Returns:
            余弦相似度（-1.0-1.0）
        """
        # 获取所有词汇
        all_words = set(vec1.keys()).union(set(vec2.keys()))
        
        if not all_words:
            return 0.0
        
        # 计算点积
        dot_product = sum(vec1.get(word, 0) * vec2.get(word, 0) for word in all_words)
        
        # 计算模长
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def calculate_normalized_edit_distance(self, text1: str, text2: str) -> float:
        """
        计算归一化编辑距离（Levenshtein距离）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            归一化编辑距离（0.0-1.0，0表示完全相同）
        """
        len1, len2 = len(text1), len(text2)
        
        # 特殊情况处理
        if len1 == 0 or len2 == 0:
            return 1.0 if len1 != len2 else 0.0
        
        # 创建DP表
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # 初始化
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j
        
        # 计算编辑距离
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if text1[i-1] == text2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # 删除
                    dp[i][j-1] + 1,      # 插入
                    dp[i-1][j-1] + cost  # 替换
                )
        
        edit_distance = dp[len1][len2]
        max_len = max(len1, len2)
        
        # 归一化到0-1范围
        return edit_distance / max_len if max_len > 0 else 0.0
    
    def calculate_simhash_similarity(self, hash1: str, hash2: str) -> float:
        """
        计算SimHash相似度（Hamming距离）
        
        Args:
            hash1: SimHash值1（64位二进制字符串）
            hash2: SimHash值2（64位二进制字符串）
            
        Returns:
            相似度分数（0.0-1.0，1表示完全相同）
        """
        if len(hash1) != len(hash2):
            raise ValueError("SimHash长度必须相同")
        
        # 计算Hamming距离
        hamming_distance = sum(1 for a, b in zip(hash1, hash2) if a != b)
        
        # 转换为相似度分数
        similarity = 1.0 - (hamming_distance / len(hash1))
        
        return max(0.0, min(1.0, similarity))
    
    def generate_simhash(self, text: str, ngram_size: int = 3, hash_bits: int = 64) -> str:
        """
        生成文本的SimHash
        
        Args:
            text: 输入文本
            ngram_size: n-gram大小
            hash_bits: 哈希位数
            
        Returns:
            SimHash字符串（二进制）
        """
        from .text_processor import TextProcessor
        
        processor = TextProcessor()
        
        # 归一化文本
        normalized_text = processor.normalize_text(text)
        
        # 提取n-gram
        ngrams = processor.extract_ngrams(normalized_text, ngram_size)
        
        if not ngrams:
            # 如果没有n-gram，使用整个文本
            ngrams = [normalized_text]
        
        # 计算每个n-gram的哈希值
        vectors = []
        for ngram in ngrams:
            # 使用MD5哈希，取其前hash_bits位
            hash_bytes = hashlib.md5(ngram.encode()).digest()
            hash_int = int.from_bytes(hash_bytes, byteorder='big')
            
            # 转换为二进制向量
            vector = []
            for i in range(hash_bits):
                bit = (hash_int >> i) & 1
                vector.append(1 if bit == 1 else -1)
            
            vectors.append(vector)
        
        if not vectors:
            # 返回全0哈希
            return '0' * hash_bits
        
        # 求和向量
        sum_vector = [0] * hash_bits
        for vector in vectors:
            for i in range(hash_bits):
                sum_vector[i] += vector[i]
        
        # 生成SimHash
        simhash = ''
        for i in range(hash_bits):
            simhash += '1' if sum_vector[i] > 0 else '0'
        
        return simhash
    
    def calculate_term_frequency(self, text: str) -> Dict[str, float]:
        """
        计算词频向量
        
        Args:
            text: 输入文本
            
        Returns:
            词频向量字典
        """
        from .text_processor import TextProcessor
        
        processor = TextProcessor()
        tokens = processor.tokenize_words(text)
        
        if not tokens:
            return {}
        
        total_tokens = len(tokens)
        term_freq = Counter(tokens)
        
        # 归一化词频
        return {word: count / total_tokens for word, count in term_freq.items()}
    
    def calculate_similarity_comprehensive(self, text1: str, text2: str) -> SimilarityResult:
        """
        综合相似度计算
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            综合相似度结果
        """
        from .text_processor import TextProcessor
        
        processor = TextProcessor()
        
        # 预处理文本
        tokens1 = set(processor.tokenize_words(text1))
        tokens2 = set(processor.tokenize_words(text2))
        
        # 计算各种相似度
        jaccard = self.calculate_jaccard_similarity(tokens1, tokens2)
        
        # 计算词频向量
        tf1 = self.calculate_term_frequency(text1)
        tf2 = self.calculate_term_frequency(text2)
        cosine = self.calculate_cosine_similarity(tf1, tf2)
        
        # 计算编辑距离
        edit_distance = self.calculate_normalized_edit_distance(text1, text2)
        
        # 计算SimHash
        simhash1 = self.generate_simhash(text1)
        simhash2 = self.generate_simhash(text2)
        simhash_similarity = self.calculate_simhash_similarity(simhash1, simhash2)
        
        # 综合相似度分数（加权平均）
        weights = {
            'jaccard': 0.25,
            'cosine': 0.30,
            'simhash': 0.30,
            'edit_distance': 0.15  # 编辑距离转换为相似度
        }
        
        # 将编辑距离转换为相似度（1 - 距离）
        edit_similarity = 1.0 - edit_distance
        
        combined = (jaccard * weights['jaccard'] +
                   cosine * weights['cosine'] +
                   simhash_similarity * weights['simhash'] +
                   edit_similarity * weights['edit_distance'])
        
        # 确保在0-1范围内
        combined = max(0.0, min(1.0, combined))
        
        return SimilarityResult(
            jaccard=jaccard,
            cosine=cosine,
            edit_distance=edit_distance,
            simhash=simhash_similarity,
            combined=combined
        )
    
    def calculate_text_fingerprint(self, text: str) -> Dict[str, Any]:
        """
        计算文本指纹（综合特征）
        
        Args:
            text: 输入文本
            
        Returns:
            指纹特征字典
        """
        from .text_processor import TextProcessor
        
        processor = TextProcessor()
        
        # 归一化文本
        normalized_text = processor.normalize_text(text)
        
        # 计算各种特征
        tokens = processor.tokenize_words(normalized_text)
        ngrams = processor.extract_ngrams(normalized_text, 3)
        
        # SimHash
        simhash = self.generate_simhash(normalized_text)
        
        # 关键词短语
        key_phrases = processor.extract_key_phrases(normalized_text, max_phrases=5)
        
        # 文本复杂度
        complexity = processor.calculate_text_complexity(normalized_text)
        
        # 生成唯一标识符
        fingerprint_id = hashlib.md5(normalized_text.encode()).hexdigest()
        
        return {
            'fingerprint_id': fingerprint_id,
            'simhash': simhash,
            'token_count': len(tokens),
            'unique_token_count': len(set(tokens)),
            'ngram_count': len(ngrams),
            'key_phrases': key_phrases,
            'complexity': complexity,
            'normalized_text': normalized_text
        }
    
    def detect_plagiarism_level(self, similarity_score: float) -> str:
        """
        根据相似度分数判断抄袭风险等级
        
        Args:
            similarity_score: 相似度分数（0.0-1.0）
            
        Returns:
            风险等级描述
        """
        if similarity_score >= 0.9:
            return "高风险 - 高度相似，可能抄袭"
        elif similarity_score >= 0.7:
            return "中风险 - 中度相似，需人工审核"
        elif similarity_score >= 0.4:
            return "低风险 - 轻度相似，可能为通用表述"
        else:
            return "极低风险 - 基本原创"