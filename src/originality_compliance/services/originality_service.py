"""
原创检测核心服务模块
提供完整的原创性检测功能，集成多个检测器和外部服务
"""

import logging
import time
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime

from ..models.data_models import (
    OriginalityRequest, OriginalityResult, SimilarityItem, 
    RiskLevel, ContentType, CountryCode
)
from ..detectors.semantic_detector import SemanticSimilarityDetector, SemanticDetectionConfig
from ..detectors.fingerprint_detector import FingerprintDetector, FingerprintDetectionConfig
from ..detectors.multilingual_detector import MultilingualDetector, MultilingualDetectionConfig
from ..integrators.notebooklm_integrator import NotebookLMIntegrator, NotebookLMConfig
from ..integrators.deepl_integrator import DeepLIntegrator, DeepLConfig
from ..utils.text_processor import TextProcessor

logger = logging.getLogger(__name__)


@dataclass
class OriginalityServiceConfig:
    """原创检测服务配置"""
    semantic_config: SemanticDetectionConfig = None
    fingerprint_config: FingerprintDetectionConfig = None
    multilingual_config: MultilingualDetectionConfig = None
    notebooklm_config: NotebookLMConfig = None
    deepl_config: DeepLConfig = None
    
    # 综合检测权重
    detection_weights: Dict[str, float] = None
    
    # 阈值配置
    high_risk_threshold: float = 0.85
    medium_risk_threshold: float = 0.65
    min_text_length: int = 10
    
    # 服务配置
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    max_processing_time_ms: int = 5000
    
    def __post_init__(self):
        if self.semantic_config is None:
            self.semantic_config = SemanticDetectionConfig()
        
        if self.fingerprint_config is None:
            self.fingerprint_config = FingerprintDetectionConfig()
        
        if self.multilingual_config is None:
            self.multilingual_config = MultilingualDetectionConfig()
        
        if self.notebooklm_config is None:
            self.notebooklm_config = NotebookLMConfig()
        
        if self.deepl_config is None:
            self.deepl_config = DeepLConfig()
        
        if self.detection_weights is None:
            self.detection_weights = {
                "semantic": 0.4,
                "fingerprint": 0.3,
                "multilingual": 0.3
            }


class OriginalityDetectionService:
    """原创检测核心服务"""
    
    def __init__(self, config: Optional[OriginalityServiceConfig] = None):
        """
        初始化原创检测服务
        
        Args:
            config: 服务配置
        """
        self.config = config or OriginalityServiceConfig()
        
        # 初始化各个组件
        self.semantic_detector = SemanticSimilarityDetector(self.config.semantic_config)
        self.fingerprint_detector = FingerprintDetector(self.config.fingerprint_config)
        self.multilingual_detector = MultilingualDetector(self.config.multilingual_config)
        
        # 初始化外部服务集成
        self.notebooklm_integrator = NotebookLMIntegrator(self.config.notebooklm_config)
        self.deepl_integrator = DeepLIntegrator(self.config.deepl_config)
        
        # 文本处理器
        self.text_processor = TextProcessor()
        
        # 缓存（简化实现）
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # 服务状态
        self.service_status = {
            "initialized": True,
            "last_health_check": datetime.now(),
            "total_requests": 0,
            "successful_requests": 0
        }
        
        logger.info("原创检测服务初始化完成")
    
    def check_originality(self, request: OriginalityRequest) -> OriginalityResult:
        """
        执行原创性检测
        
        Args:
            request: 检测请求
            
        Returns:
            检测结果
        """
        start_time = time.time()
        
        try:
            # 验证请求
            self._validate_request(request)
            
            # 检查缓存
            cache_key = self._generate_cache_key(request)
            if self.config.enable_cache and cache_key in self._cache:
                cached_result = self._cache[cache_key]
                if time.time() - cached_result["timestamp"] < self.config.cache_ttl_seconds:
                    logger.debug(f"从缓存获取检测结果: {cache_key}")
                    
                    # 更新处理时间
                    cached_result["result"].processing_time_ms = (time.time() - start_time) * 1000
                    return cached_result["result"]
            
            # 检测流程开始
            logger.info(f"开始原创性检测，内容类型: {request.content_type.value}, 语言: {request.language}")
            
            # 1. 查询Notebook LM相似内容
            notebooklm_items = self._query_notebooklm_knowledge(request)
            
            # 2. 执行多种检测
            semantic_items = self._detect_semantic_similarity(request, notebooklm_items)
            fingerprint_items = self._detect_fingerprint_similarity(request)
            multilingual_items = self._detect_multilingual_similarity(request, notebooklm_items)
            
            # 3. 合并和去重检测结果
            all_similarity_items = self._merge_similarity_items(
                semantic_items, fingerprint_items, multilingual_items
            )
            
            # 4. 计算综合原创性分数
            originality_score = self._calculate_comprehensive_originality(
                all_similarity_items
            )
            
            # 5. 确定抄袭风险等级
            plagiarism_risk = self._determine_plagiarism_risk(originality_score)
            
            # 6. 生成改进建议
            recommendations = self._generate_comprehensive_recommendations(
                originality_score, plagiarism_risk, all_similarity_items
            )
            
            # 检测语言（如果未指定）
            detected_language = request.language
            if request.language == "auto":
                detected_language, _ = self.deepl_integrator.detect_language(request.text)
            
            # 创建结果对象
            result = OriginalityResult(
                originality_score=originality_score,
                plagiarism_risk=plagiarism_risk,
                similarity_items=all_similarity_items[:10],  # 返回前10个最相似项
                recommendations=recommendations,
                processing_time_ms=(time.time() - start_time) * 1000,
                language_detected=detected_language
            )
            
            # 更新服务状态
            self.service_status["successful_requests"] += 1
            
            # 缓存结果
            if self.config.enable_cache:
                self._cache[cache_key] = {
                    "timestamp": time.time(),
                    "result": result
                }
            
            logger.info(f"原创性检测完成，分数: {originality_score:.2f}, 风险: {plagiarism_risk.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"原创性检测失败: {str(e)}")
            
            # 返回降级结果
            return self._get_fallback_result(request, start_time, str(e))
    
    def batch_check_originality(self, requests: List[OriginalityRequest]) -> List[OriginalityResult]:
        """
        批量执行原创性检测
        
        Args:
            requests: 检测请求列表
            
        Returns:
            检测结果列表
        """
        results = []
        
        for request in requests:
            result = self.check_originality(request)
            results.append(result)
        
        return results
    
    def register_reference_content(self, 
                                  source_id: str, 
                                  content: str,
                                  content_type: ContentType,
                                  language: str = "auto") -> str:
        """
        注册参考内容到检测系统
        
        Args:
            source_id: 来源ID
            content: 内容文本
            content_type: 内容类型
            language: 内容语言
            
        Returns:
            注册ID
        """
        try:
            # 生成指纹并注册
            fingerprint_id = self.fingerprint_detector.register_fingerprint(source_id, content)
            
            # 添加到Notebook LM知识库（可选）
            if self.config.notebooklm_config.api_key:
                metadata = {
                    "source_id": source_id,
                    "content_type": content_type.value,
                    "language": language,
                    "registered_at": datetime.now().isoformat()
                }
                
                doc_id = self.notebooklm_integrator.add_to_knowledge_base(content, metadata)
                
                if doc_id:
                    logger.info(f"内容成功注册到Notebook LM知识库: {doc_id}")
            
            logger.info(f"参考内容注册成功: {source_id}, 指纹ID: {fingerprint_id}")
            
            return fingerprint_id
            
        except Exception as e:
            logger.error(f"注册参考内容失败: {str(e)}")
            return ""
    
    def get_service_health(self) -> Dict[str, Any]:
        """
        获取服务健康状态
        
        Returns:
            健康状态字典
        """
        # 基本健康检查
        health_status = {
            "service": "originality_detection",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total_requests": self.service_status["total_requests"],
                "successful_requests": self.service_status["successful_requests"],
                "success_rate": (
                    self.service_status["successful_requests"] / 
                    max(self.service_status["total_requests"], 1)
                ) if self.service_status["total_requests"] > 0 else 1.0
            },
            "components": {
                "semantic_detector": self.semantic_detector is not None,
                "fingerprint_detector": self.fingerprint_detector is not None,
                "multilingual_detector": self.multilingual_detector is not None,
                "notebooklm_integrator": self.notebooklm_integrator is not None,
                "deepl_integrator": self.deepl_integrator is not None
            }
        }
        
        # 检查外部服务连接
        try:
            # 检查DeepL API
            deepl_valid, deepl_error = self.deepl_integrator.validate_api_key()
            health_status["components"]["deepl_api_valid"] = deepl_valid
            
            if not deepl_valid:
                health_status["status"] = "degraded"
                health_status["deepl_error"] = deepl_error
            
        except Exception as e:
            logger.warning(f"外部服务健康检查失败: {str(e)}")
            health_status["components"]["external_services"] = False
            health_status["status"] = "degraded"
        
        return health_status
    
    def _validate_request(self, request: OriginalityRequest):
        """验证检测请求"""
        if not request.text or len(request.text.strip()) < self.config.min_text_length:
            raise ValueError(f"文本长度不足{self.config.min_text_length}字符")
        
        # 更新请求计数
        self.service_status["total_requests"] += 1
    
    def _query_notebooklm_knowledge(self, request: OriginalityRequest) -> List[Dict[str, Any]]:
        """查询Notebook LM知识库"""
        try:
            # 确定查询语言
            query_language = request.language
            if query_language == "auto":
                # 检测语言
                detected_lang, _ = self.deepl_integrator.detect_language(request.text)
                query_language = detected_lang
            
            # 查询相似内容
            items = self.notebooklm_integrator.query_similar_content(
                text=request.text,
                content_type=request.content_type,
                max_results=20
            )
            
            logger.debug(f"Notebook LM查询返回 {len(items)} 个结果")
            
            return items
            
        except Exception as e:
            logger.warning(f"Notebook LM查询失败: {str(e)}")
            return []
    
    def _detect_semantic_similarity(self, 
                                   request: OriginalityRequest,
                                   notebooklm_items: List[Dict[str, Any]]) -> List[SimilarityItem]:
        """检测语义相似度"""
        try:
            # 转换Notebook LM结果为检测格式
            reference_texts = []
            for item in notebooklm_items:
                source_id = item.get("id", "unknown")
                content = item.get("content", "")
                if content:
                    reference_texts.append((source_id, content))
            
            # 执行语义检测
            similarity_items = self.semantic_detector.detect_similarity(
                request.text, reference_texts
            )
            
            logger.debug(f"语义检测返回 {len(similarity_items)} 个结果")
            
            return similarity_items
            
        except Exception as e:
            logger.warning(f"语义检测失败: {str(e)}")
            return []
    
    def _detect_fingerprint_similarity(self, request: OriginalityRequest) -> List[SimilarityItem]:
        """检测指纹相似度"""
        try:
            # 执行指纹检测
            similarity_items = self.fingerprint_detector.detect_similar_fingerprints(
                request.text, min_similarity=0.6
            )
            
            logger.debug(f"指纹检测返回 {len(similarity_items)} 个结果")
            
            return similarity_items
            
        except Exception as e:
            logger.warning(f"指纹检测失败: {str(e)}")
            return []
    
    def _detect_multilingual_similarity(self, 
                                       request: OriginalityRequest,
                                       notebooklm_items: List[Dict[str, Any]]) -> List[SimilarityItem]:
        """检测多语种相似度"""
        try:
            # 转换Notebook LM结果为检测格式
            reference_corpus = []
            for item in notebooklm_items:
                source_id = item.get("id", "unknown")
                content = item.get("content", "")
                language = item.get("metadata", {}).get("language", "en")
                
                if content:
                    reference_corpus.append((source_id, content, language))
            
            # 执行多语种检测
            similarity_items = self.multilingual_detector.detect_multilingual_similarity(
                request.text, reference_corpus
            )
            
            logger.debug(f"多语种检测返回 {len(similarity_items)} 个结果")
            
            return similarity_items
            
        except Exception as e:
            logger.warning(f"多语种检测失败: {str(e)}")
            return []
    
    def _merge_similarity_items(self, *item_lists: List[SimilarityItem]) -> List[SimilarityItem]:
        """合并和去重相似性检测结果"""
        all_items = []
        seen_ids = set()
        
        for item_list in item_lists:
            for item in item_list:
                # 基于来源ID和相似度创建唯一标识
                item_id = f"{item.source_id}_{item.similarity_score:.2f}"
                
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    all_items.append(item)
        
        # 按相似度排序
        all_items.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return all_items
    
    def _calculate_comprehensive_originality(self, 
                                           similarity_items: List[SimilarityItem]) -> float:
        """计算综合原创性分数"""
        if not similarity_items:
            return 1.0  # 没有相似项，完全原创
        
        # 提取最高相似度分数
        max_similarity = max(item.similarity_score for item in similarity_items)
        
        # 考虑相似项数量
        item_count_factor = min(1.0, len(similarity_items) / 10.0)
        
        # 计算原创性分数
        # 原创性 = 1 - (最高相似度 * 权重 + 数量因子 * 权重)
        originality_score = 1.0 - (
            max_similarity * 0.6 +
            item_count_factor * 0.2
        )
        
        # 确保在合理范围内
        originality_score = max(0.0, min(1.0, originality_score))
        
        return originality_score
    
    def _determine_plagiarism_risk(self, originality_score: float) -> RiskLevel:
        """确定抄袭风险等级"""
        if originality_score <= 0.5:  # 低于0.5为高风险
            return RiskLevel.HIGH
        elif originality_score <= 0.7:  # 0.5-0.7为中风险
            return RiskLevel.MEDIUM
        else:  # 高于0.7为低风险
            return RiskLevel.LOW
    
    def _generate_comprehensive_recommendations(self, 
                                              originality_score: float,
                                              plagiarism_risk: RiskLevel,
                                              similarity_items: List[SimilarityItem]) -> List[str]:
        """生成综合改进建议"""
        recommendations = []
        
        # 基于风险等级的建议
        if plagiarism_risk == RiskLevel.HIGH:
            recommendations.extend([
                "文本原创性严重不足，建议完全重写",
                "重新构思核心观点和表达方式",
                "增加独特的分析和行业见解"
            ])
        elif plagiarism_risk == RiskLevel.MEDIUM:
            recommendations.extend([
                "部分内容相似度较高，建议重点修改相似段落",
                "优化语言结构和表达方式",
                "增加个性化内容和案例"
            ])
        else:
            recommendations.extend([
                "文本原创性良好，可以继续使用",
                "建议添加更多创新性观点以增强独特性",
                "保持当前创作风格和质量"
            ])
        
        # 基于相似项的具体建议
        if similarity_items:
            top_items = similarity_items[:3]
            
            for i, item in enumerate(top_items, 1):
                if item.similarity_score > 0.7:
                    recommendations.append(
                        f"与来源 {item.source_id[:8]}... 相似度达{item.similarity_score:.0%}，建议修改相应部分"
                    )
        
        # 确保建议数量合理
        return recommendations[:5]
    
    def _get_fallback_result(self, 
                            request: OriginalityRequest, 
                            start_time: float,
                            error_message: str) -> OriginalityResult:
        """获取降级结果（当检测失败时）"""
        processing_time = (time.time() - start_time) * 1000
        
        # 检测语言
        detected_language = request.language
        if request.language == "auto":
            try:
                detected_language, _ = self.deepl_integrator.detect_language(request.text)
            except:
                detected_language = "unknown"
        
        return OriginalityResult(
            originality_score=0.5,  # 保守的中间值
            plagiarism_risk=RiskLevel.MEDIUM,  # 中等风险
            similarity_items=[],
            recommendations=[
                "检测服务暂时不可用，建议人工审核",
                "检查文本原创性，避免直接复制",
                f"错误信息: {error_message[:100]}..."
            ],
            processing_time_ms=processing_time,
            language_detected=detected_language
        )
    
    def _generate_cache_key(self, request: OriginalityRequest) -> str:
        """生成缓存键"""
        import hashlib
        
        key_data = {
            "text": request.text,
            "content_type": request.content_type.value,
            "language": request.language,
            "target_countries": [c.value for c in request.target_countries],
            "check_type": request.check_type
        }
        
        key_string = str(key_data)
        return hashlib.md5(key_string.encode()).hexdigest()