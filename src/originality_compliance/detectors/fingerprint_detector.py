"""
文本指纹检测模块
"""

import hashlib
from typing import List, Dict, Tuple, Set, Optional, Any
from dataclasses import dataclass
import logging
import numpy as np

from ..models.data_models import SimilarityItem, RiskLevel
from ..utils.similarity_metrics import SimilarityCalculator
from ..utils.text_processor import TextProcessor

logger = logging.getLogger(__name__)


@dataclass
class FingerprintDetectionConfig:
    """指纹检测配置"""
    simhash_bits: int = 64  # SimHash位数
    ngram_size: int = 3  # n-gram大小
    similarity_threshold: float = 0.85  # 相似度阈值
    min_ngram_count: int = 5  # 最小n-gram数量
    enable_fingerprint_cache: bool = True  # 启用指纹缓存
    cache_ttl_seconds: int = 7200  # 缓存生存时间


class FingerprintDetector:
    """文本指纹检测器"""
    
    def __init__(self, config: Optional[FingerprintDetectionConfig] = None):
        """
        初始化指纹检测器
        
        Args:
            config: 检测配置
        """
        self.config = config or FingerprintDetectionConfig()
        self.similarity_calculator = SimilarityCalculator()
        self.text_processor = TextProcessor()
        
        # 指纹数据库（简化实现）
        self._fingerprint_db: Dict[str, Dict[str, Any]] = {}
        
    def generate_fingerprint(self, text: str) -> Dict[str, Any]:
        """
        生成文本指纹
        
        Args:
            text: 输入文本
            
        Returns:
            指纹特征字典
        """
        # 归一化文本
        normalized_text = self.text_processor.normalize_text(text)
        
        # 生成SimHash
        simhash = self.similarity_calculator.generate_simhash(
            normalized_text, 
            ngram_size=self.config.ngram_size,
            hash_bits=self.config.simhash_bits
        )
        
        # 提取n-gram
        ngrams = self.text_processor.extract_ngrams(normalized_text, self.config.ngram_size)
        
        # 计算n-gram哈希值
        ngram_hashes = []
        for ngram in ngrams:
            ngram_hash = hashlib.md5(ngram.encode()).hexdigest()[:16]
            ngram_hashes.append(ngram_hash)
        
        # 生成唯一标识符
        fingerprint_id = hashlib.md5(normalized_text.encode()).hexdigest()
        
        return {
            "fingerprint_id": fingerprint_id,
            "simhash": simhash,
            "ngram_hashes": ngram_hashes,
            "ngram_count": len(ngrams),
            "text_length": len(normalized_text),
            "normalized_text": normalized_text
        }
    
    def register_fingerprint(self, source_id: str, text: str) -> str:
        """
        注册文本指纹到数据库
        
        Args:
            source_id: 来源ID
            text: 文本内容
            
        Returns:
            指纹ID
        """
        fingerprint = self.generate_fingerprint(text)
        fingerprint_id = fingerprint["fingerprint_id"]
        
        # 存储到数据库
        self._fingerprint_db[fingerprint_id] = {
            "source_id": source_id,
            "fingerprint": fingerprint,
            "registration_time": np.datetime64('now')
        }
        
        return fingerprint_id
    
    def detect_similar_fingerprints(self, text: str, min_similarity: float = 0.7) -> List[SimilarityItem]:
        """
        检测文本的相似指纹
        
        Args:
            text: 待检测文本
            min_similarity: 最小相似度阈值
            
        Returns:
            相似指纹列表
        """
        # 生成待检测文本的指纹
        query_fingerprint = self.generate_fingerprint(text)
        query_simhash = query_fingerprint["simhash"]
        
        similarity_items = []
        
        for fp_id, record in self._fingerprint_db.items():
            try:
                # 计算SimHash相似度
                ref_simhash = record["fingerprint"]["simhash"]
                simhash_similarity = self.similarity_calculator.calculate_simhash_similarity(
                    query_simhash, ref_simhash
                )
                
                if simhash_similarity >= min_similarity:
                    # 提取匹配的文本片段
                    matched_text = self._extract_common_ngrams(
                        text, 
                        record["fingerprint"]["normalized_text"]
                    )
                    
                    # 确定风险等级
                    risk_level = self._determine_fingerprint_risk(simhash_similarity)
                    
                    # 生成建议
                    recommendations = self._generate_fingerprint_recommendations(
                        simhash_similarity, risk_level
                    )
                    
                    # 创建相似项
                    similarity_item = SimilarityItem(
                        source_id=record["source_id"],
                        source_type="fingerprint_db",
                        similarity_score=simhash_similarity,
                        matched_text=matched_text,
                        risk_level=risk_level,
                        recommendations=recommendations
                    )
                    
                    similarity_items.append(similarity_item)
                    
            except Exception as e:
                logger.error(f"计算指纹相似度时出错: {str(e)}")
                continue
        
        # 按相似度排序
        similarity_items.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return similarity_items
    
    def _extract_common_ngrams(self, text1: str, text2: str, max_fragments: int = 3) -> str:
        """
        提取公共n-gram片段
        
        Args:
            text1: 文本1
            text2: 文本2
            max_fragments: 最大片段数量
            
        Returns:
            公共n-gram片段
        """
        # 提取n-gram
        ngrams1 = set(self.text_processor.extract_ngrams(text1, self.config.ngram_size))
        ngrams2 = set(self.text_processor.extract_ngrams(text2, self.config.ngram_size))
        
        # 找出公共n-gram
        common_ngrams = ngrams1.intersection(ngrams2)
        
        if not common_ngrams:
            return "未找到显著相似片段"
        
        # 选择最长的几个n-gram组合
        sorted_ngrams = sorted(list(common_ngrams), key=len, reverse=True)
        
        # 组合片段（简化实现）
        fragments = []
        for ngram in sorted_ngrams[:max_fragments]:
            # 在原始文本中找到n-gram位置
            pos1 = text1.find(ngram)
            pos2 = text2.find(ngram)
            
            if pos1 >= 0:
                # 提取上下文
                start = max(0, pos1 - 20)
                end = min(len(text1), pos1 + len(ngram) + 20)
                fragment = text1[start:end]
                
                if len(fragment) > 10:  # 确保有足够内容
                    fragments.append(fragment)
        
        if fragments:
            return "... " + " ... ".join(fragments[:2]) + " ..."
        else:
            return " ".join(sorted_ngrams[:3]) if sorted_ngrams else "未找到显著相似片段"
    
    def _determine_fingerprint_risk(self, similarity_score: float) -> RiskLevel:
        """
        根据指纹相似度确定风险等级
        
        Args:
            similarity_score: 相似度分数
            
        Returns:
            风险等级
        """
        if similarity_score >= self.config.similarity_threshold:
            return RiskLevel.HIGH
        elif similarity_score >= 0.6:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_fingerprint_recommendations(self, similarity_score: float, risk_level: RiskLevel) -> List[str]:
        """
        生成指纹检测建议
        
        Args:
            similarity_score: 相似度分数
            risk_level: 风险等级
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "文本指纹与现有内容高度相似，存在抄袭风险",
                "建议重新组织文本结构和表达方式",
                "考虑添加更多原创性内容和独特观点"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend([
                "文本指纹部分相似，可能存在借鉴",
                "建议修改相似部分的表达方式",
                "增加个性化内容以降低相似度"
            ])
        elif risk_level == RiskLevel.LOW:
            recommendations.extend([
                "文本指纹相似度较低，原创性良好",
                "可以继续使用当前文本",
                "建议定期检查以避免无意相似"
            ])
        
        return recommendations
    
    def batch_generate_fingerprints(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        批量生成文本指纹
        
        Args:
            texts: 文本列表
            
        Returns:
            指纹列表
        """
        fingerprints = []
        
        for text in texts:
            fingerprint = self.generate_fingerprint(text)
            fingerprints.append(fingerprint)
        
        return fingerprints
    
    def compare_fingerprints(self, fp1: Dict[str, Any], fp2: Dict[str, Any]) -> Dict[str, float]:
        """
        比较两个指纹的相似度
        
        Args:
            fp1: 指纹1
            fp2: 指纹2
            
        Returns:
            相似度指标字典
        """
        # SimHash相似度
        simhash_similarity = self.similarity_calculator.calculate_simhash_similarity(
            fp1["simhash"], fp2["simhash"]
        )
        
        # n-gram重叠度
        ngrams1 = set(fp1.get("ngram_hashes", []))
        ngrams2 = set(fp2.get("ngram_hashes", []))
        
        if ngrams1 and ngrams2:
            ngram_overlap = len(ngrams1.intersection(ngrams2)) / max(len(ngrams1), len(ngrams2))
        else:
            ngram_overlap = 0.0
        
        # 长度相似度
        len1 = fp1.get("text_length", 0)
        len2 = fp2.get("text_length", 0)
        
        if len1 > 0 and len2 > 0:
            length_similarity = 1.0 - abs(len1 - len2) / max(len1, len2)
        else:
            length_similarity = 0.0
        
        # 综合相似度
        combined_similarity = (
            simhash_similarity * 0.5 +
            ngram_overlap * 0.3 +
            length_similarity * 0.2
        )
        
        return {
            "simhash_similarity": simhash_similarity,
            "ngram_overlap": ngram_overlap,
            "length_similarity": length_similarity,
            "combined_similarity": combined_similarity
        }
    
    def find_near_duplicates(self, text: str, similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        查找近似重复内容
        
        Args:
            text: 待检测文本
            similarity_threshold: 相似度阈值
            
        Returns:
            近似重复项列表
        """
        query_fingerprint = self.generate_fingerprint(text)
        
        near_duplicates = []
        
        for fp_id, record in self._fingerprint_db.items():
            similarity = self.compare_fingerprints(query_fingerprint, record["fingerprint"])
            
            if similarity["combined_similarity"] >= similarity_threshold:
                near_duplicates.append({
                    "source_id": record["source_id"],
                    "similarity": similarity,
                    "fingerprint_id": fp_id,
                    "registered_time": record["registration_time"]
                })
        
        # 按相似度排序
        near_duplicates.sort(key=lambda x: x["similarity"]["combined_similarity"], reverse=True)
        
        return near_duplicates
    
    def analyze_fingerprint_clusters(self, min_cluster_size: int = 2) -> List[List[str]]:
        """
        分析指纹聚类
        
        Args:
            min_cluster_size: 最小聚类大小
            
        Returns:
            聚类列表，每个聚类包含指纹ID
        """
        # 简化实现：基于SimHash相似度聚类
        all_fingerprints = list(self._fingerprint_db.items())
        
        if len(all_fingerprints) < min_cluster_size:
            return []
        
        clusters = []
        visited = set()
        
        for i, (fp_id1, record1) in enumerate(all_fingerprints):
            if fp_id1 in visited:
                continue
            
            cluster = [fp_id1]
            
            for j, (fp_id2, record2) in enumerate(all_fingerprints):
                if i == j or fp_id2 in visited:
                    continue
                
                # 计算相似度
                similarity = self.compare_fingerprints(
                    record1["fingerprint"], record2["fingerprint"]
                )
                
                if similarity["combined_similarity"] >= 0.7:  # 聚类阈值
                    cluster.append(fp_id2)
                    visited.add(fp_id2)
            
            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)
            
            visited.add(fp_id1)
        
        return clusters