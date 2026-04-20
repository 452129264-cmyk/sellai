"""
DeepL翻译服务集成模块
实现与DeepL API的多语言翻译集成
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# 尝试导入DeepL SDK，如果不可用则使用模拟
try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False
    logging.warning("DeepL SDK not available, using simulation mode")

logger = logging.getLogger(__name__)

@dataclass
class TranslationRequest:
    """翻译请求"""
    text: str
    target_lang: str = "EN-US"
    source_lang: Optional[str] = None
    formality: str = "default"  # default, less, more
    glossary_id: Optional[str] = None
    split_sentences: bool = True
    context: Optional[str] = None

@dataclass
class TranslationResponse:
    """翻译响应"""
    translated_text: str
    detected_source_lang: str = "unknown"
    character_count: int = 0
    cost: float = 0.0  # 美元
    response_time_ms: float = 0.0
    processing_time_ms: float = 0.0

class DeepLIntegrator:
    """DeepL集成器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "api_key": "your_deepl_api_key_here",
            "api_endpoint": "https://api.deepl.com/v2",
            "plan_type": "free",  # free, pro
            "cache_enabled": True,
            "cache_ttl_seconds": 3600,
            "rate_limit_requests_per_second": 1 if config.get("plan_type") == "free" else 10,
            "max_retries": 3,
            "retry_delay_seconds": 2
        }
        
        # 初始化DeepL客户端（如果可用）
        self.client = None
        if DEEPL_AVAILABLE and self.config.get("api_key"):
            try:
                self.client = deepl.Translator(self.config["api_key"])
                logger.info("DeepL client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize DeepL client: {str(e)}")
                self.client = None
        
        # 翻译缓存
        self.translation_cache = {}
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_characters": 0,
            "total_cost_usd": 0.0,
            "avg_response_time_ms": 0.0
        }
        
        # 支持的语种映射
        self.supported_languages = {
            "EN-US": "American English",
            "EN-GB": "British English",
            "ZH": "Chinese",
            "FR": "French",
            "DE": "German",
            "ES": "Spanish",
            "IT": "Italian",
            "PT": "Portuguese",
            "RU": "Russian",
            "JA": "Japanese",
            "KO": "Korean",
            "AR": "Arabic",
            "NL": "Dutch",
            "PL": "Polish",
            "SV": "Swedish",
            "DA": "Danish",
            "FI": "Finnish",
            "NO": "Norwegian",
            "HI": "Hindi",
            "TR": "Turkish",
            "ID": "Indonesian",
            "VI": "Vietnamese",
            "TH": "Thai"
        }
        
        logger.info("DeepLIntegrator initialized")
    
    async def translate_text(self, request: TranslationRequest) -> TranslationResponse:
        """
        翻译文本
        Args:
            request: 翻译请求
        Returns:
            翻译响应
        """
        start_time = time.time()
        
        try:
            # 检查缓存
            cache_key = self._generate_cache_key(request)
            if self.config.get("cache_enabled", True) and cache_key in self.translation_cache:
                cached_result = self.translation_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.debug(f"使用缓存翻译结果: {cache_key}")
                    
                    # 更新缓存命中时间
                    cached_result["last_accessed"] = time.time()
                    
                    return TranslationResponse(**cached_result["data"])
            
            # 实际翻译
            translation_result = await self._perform_translation(request)
            
            # 计算处理时间
            processing_time = (time.time() - start_time) * 1000
            translation_result.processing_time_ms = processing_time
            
            # 更新统计
            self._update_stats(translation_result, success=True)
            
            # 缓存结果
            if self.config.get("cache_enabled", True):
                self.translation_cache[cache_key] = {
                    "data": {
                        "translated_text": translation_result.translated_text,
                        "detected_source_lang": translation_result.detected_source_lang,
                        "character_count": translation_result.character_count,
                        "cost": translation_result.cost,
                        "response_time_ms": translation_result.response_time_ms
                    },
                    "timestamp": time.time(),
                    "last_accessed": time.time(),
                    "ttl": self.config.get("cache_ttl_seconds", 3600)
                }
            
            logger.info(f"翻译完成: characters={translation_result.character_count}, "
                       f"source_lang={translation_result.detected_source_lang}, "
                       f"target_lang={request.target_lang}, "
                       f"time={processing_time:.2f}ms")
            
            return translation_result
            
        except Exception as e:
            # 更新统计
            self._update_stats(None, success=False)
            
            logger.error(f"翻译失败: error={str(e)}, text_length={len(request.text)}")
            
            # 返回失败响应
            return TranslationResponse(
                translated_text=request.text,  # 返回原文作为降级处理
                detected_source_lang="unknown",
                character_count=len(request.text),
                cost=0.0,
                response_time_ms=0.0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    async def batch_translate(self, requests: List[TranslationRequest]) -> List[TranslationResponse]:
        """
        批量翻译
        Args:
            requests: 翻译请求列表
        Returns:
            翻译响应列表
        """
        results = []
        
        # 限制并发请求（根据DeepL限制）
        max_concurrent = min(5, self.config.get("rate_limit_requests_per_second", 1))
        
        # 分批处理
        for i in range(0, len(requests), max_concurrent):
            batch = requests[i:i+max_concurrent]
            
            # 并行处理批内请求
            batch_tasks = [self.translate_text(req) for req in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"批量翻译失败: {str(result)}")
                    results.append(TranslationResponse(
                        translated_text="",
                        detected_source_lang="unknown",
                        character_count=0,
                        cost=0.0,
                        response_time_ms=0.0,
                        processing_time_ms=0.0
                    ))
                else:
                    results.append(result)
            
            # 限速延迟（避免超过API限制）
            if i + max_concurrent < len(requests):
                await asyncio.sleep(1.0 / self.config.get("rate_limit_requests_per_second", 1))
        
        return results
    
    async def detect_language(self, text: str) -> Tuple[str, float]:
        """
        检测文本语言
        Args:
            text: 待检测文本
        Returns:
            (语言代码, 置信度)
        """
        try:
            if self.client and DEEPL_AVAILABLE:
                # 使用DeepL API检测语言
                result = self.client.translate_text(
                    text=text[:100],  # 只检测前100个字符
                    target_lang="EN-US",
                    source_lang=None
                )
                return result.detected_source_lang, 0.95
            
            else:
                # 模拟语言检测
                return self._simulate_language_detection(text)
                
        except Exception as e:
            logger.error(f"语言检测失败: {str(e)}")
            return "unknown", 0.0
    
    async def get_usage(self) -> Dict[str, Any]:
        """
        获取API使用情况
        Returns:
            使用情况统计
        """
        try:
            if self.client and DEEPL_AVAILABLE:
                usage = self.client.get_usage()
                
                return {
                    "character_limit": usage.character_limit,
                    "character_count": usage.character_count,
                    "character_remaining": usage.character_limit - usage.character_count,
                    "limit_reached": usage.character_limit_reached,
                    "plan_type": self.config.get("plan_type", "free")
                }
            
            else:
                # 模拟使用情况
                return {
                    "character_limit": 500000 if self.config.get("plan_type") == "free" else 1000000,
                    "character_count": 125000,
                    "character_remaining": 375000 if self.config.get("plan_type") == "free" else 875000,
                    "limit_reached": False,
                    "plan_type": self.config.get("plan_type", "free")
                }
                
        except Exception as e:
            logger.error(f"获取使用情况失败: {str(e)}")
            return {
                "error": str(e),
                "plan_type": self.config.get("plan_type", "free")
            }
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """获取支持的语言列表"""
        languages = []
        
        for code, name in self.supported_languages.items():
            languages.append({
                "code": code,
                "name": name,
                "type": "target" if code.startswith("EN-") or code == "ZH" else "both"
            })
        
        return languages
    
    def clear_cache(self):
        """清空翻译缓存"""
        self.translation_cache.clear()
        logger.info("DeepL翻译缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_characters": 0,
            "total_cost_usd": 0.0,
            "avg_response_time_ms": 0.0
        }
        logger.info("DeepL统计信息已重置")
    
    async def _perform_translation(self, request: TranslationRequest) -> TranslationResponse:
        """执行翻译"""
        start_time = time.time()
        
        # 根据可用性选择翻译方式
        if self.client and DEEPL_AVAILABLE:
            return await self._translate_with_deepl_api(request, start_time)
        else:
            return await self._simulate_translation(request, start_time)
    
    async def _translate_with_deepl_api(self, request: TranslationRequest, 
                                       start_time: float) -> TranslationResponse:
        """使用DeepL API翻译"""
        try:
            # 调用DeepL API
            result = self.client.translate_text(
                text=request.text,
                target_lang=request.target_lang,
                source_lang=request.source_lang,
                formality=request.formality,
                glossary_id=request.glossary_id,
                split_sentences=request.split_sentences,
                context=request.context
            )
            
            # 计算响应时间
            response_time = (time.time() - start_time) * 1000
            
            # 计算成本（DeepL按字符计费，约$20/百万字符）
            character_count = len(request.text)
            cost = character_count / 1_000_000 * 20
            
            return TranslationResponse(
                translated_text=result.text,
                detected_source_lang=result.detected_source_lang,
                character_count=character_count,
                cost=round(cost, 4),
                response_time_ms=round(response_time, 2)
            )
            
        except Exception as e:
            logger.error(f"DeepL API调用失败: {str(e)}")
            raise
    
    async def _simulate_translation(self, request: TranslationRequest, 
                                   start_time: float) -> TranslationResponse:
        """模拟翻译（简化实现）"""
        # 在实际系统中，这里会调用真实的DeepL API
        # 简化实现：模拟翻译过程
        
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        # 简单模拟翻译结果
        if request.target_lang == "ZH":
            translated_text = f"[模拟翻译到中文] {request.text}"
            detected_source_lang = "EN-US"
        elif request.target_lang.startswith("EN-"):
            translated_text = f"[Simulated translation to English] {request.text}"
            detected_source_lang = "ZH"
        else:
            translated_text = f"[Simulated translation to {request.target_lang}] {request.text}"
            detected_source_lang = "EN-US"
        
        # 计算响应时间
        response_time = (time.time() - start_time) * 1000
        
        # 计算成本
        character_count = len(request.text)
        cost = character_count / 1_000_000 * 20
        
        return TranslationResponse(
            translated_text=translated_text,
            detected_source_lang=detected_source_lang,
            character_count=character_count,
            cost=round(cost, 4),
            response_time_ms=round(response_time, 2)
        )
    
    def _simulate_language_detection(self, text: str) -> Tuple[str, float]:
        """模拟语言检测"""
        # 简单规则：检查常见语言特征
        
        # 检查中文特征
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        if chinese_chars > len(text) * 0.3:
            return "ZH", 0.9
        
        # 检查英文特征
        english_patterns = ["the", "and", "you", "for", "that", "this"]
        english_matches = sum(1 for word in english_patterns if word in text.lower())
        if english_matches >= 2:
            return "EN-US", 0.85
        
        # 默认
        return "unknown", 0.5
    
    def _generate_cache_key(self, request: TranslationRequest) -> str:
        """生成缓存键"""
        key_parts = [
            request.text,
            request.target_lang,
            request.source_lang or "auto",
            request.formality,
            request.glossary_id or "none"
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()[:16]
    
    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if not cached_data:
            return False
        
        timestamp = cached_data.get("timestamp", 0)
        ttl = cached_data.get("ttl", 3600)
        current_time = time.time()
        
        return (current_time - timestamp) <= ttl
    
    def _update_stats(self, result: Optional[TranslationResponse], success: bool):
        """更新统计"""
        self.stats["total_requests"] += 1
        
        if success and result:
            self.stats["successful_requests"] += 1
            self.stats["total_characters"] += result.character_count
            self.stats["total_cost_usd"] += result.cost
            
            # 更新平均响应时间（移动平均）
            current_avg = self.stats["avg_response_time_ms"]
            n = self.stats["successful_requests"]
            self.stats["avg_response_time_ms"] = (
                current_avg * (n - 1) + result.response_time_ms
            ) / n
        
        else:
            self.stats["failed_requests"] += 1
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        total_entries = len(self.translation_cache)
        
        # 计算缓存大小（估算）
        cache_size = 0
        for cached in self.translation_cache.values():
            # 估算每个缓存条目的大小
            data_size = len(str(cached.get("data", {})))
            cache_size += data_size
        
        # 计算缓存命中率（需要记录历史）
        # 简化实现：返回基本信息
        
        return {
            "total_entries": total_entries,
            "estimated_size_bytes": cache_size,
            "cache_enabled": self.config.get("cache_enabled", True),
            "cache_ttl_seconds": self.config.get("cache_ttl_seconds", 3600)
        }
    
    def cleanup_cache(self, max_age_hours: int = 24):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for key, cached in self.translation_cache.items():
            timestamp = cached.get("timestamp", 0)
            age_hours = (current_time - timestamp) / 3600
            
            if age_hours > max_age_hours:
                expired_keys.append(key)
        
        # 删除过期缓存
        for key in expired_keys:
            del self.translation_cache[key]
        
        logger.info(f"缓存清理完成: 删除了{len(expired_keys)}个过期条目")
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """验证配置"""
        errors = []
        
        # 检查API密钥
        api_key = self.config.get("api_key", "")
        if not api_key or api_key.startswith("your_"):
            errors.append("DeepL API密钥未配置或无效")
        
        # 检查计划类型
        plan_type = self.config.get("plan_type", "").lower()
        if plan_type not in ["free", "pro"]:
            errors.append(f"无效的DeepL计划类型: {plan_type}")
        
        # 检查缓存配置
        if self.config.get("cache_enabled", True):
            ttl = self.config.get("cache_ttl_seconds", 3600)
            if ttl <= 0:
                errors.append(f"无效的缓存TTL: {ttl}秒")
        
        return len(errors) == 0, errors