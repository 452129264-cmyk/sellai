"""
DeepL全域多语种原生润色能力集成核心服务模块
版本：v1.0
创建时间：2026-04-05
基于SellAI封神版A架构的DeepL API完整集成实现
"""

import deepl
import time
import logging
import sqlite3
import json
import hashlib
import redis
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/deepl_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 环境配置
DEEPL_AUTH_KEY = os.getenv("DEEPL_AUTH_KEY", "your_deepl_auth_key_here")
DEEPL_API_ENDPOINT = os.getenv("DEEPL_API_ENDPOINT", "https://api.deepl.com/v2")
DEEPL_PLAN_TYPE = os.getenv("DEEPL_PLAN_TYPE", "free")  # free | pro

# Redis缓存配置（如果可用）
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# 数据库配置
DB_PATH = "data/shared_state/state.db"

# ==============================================
# 数据结构定义
# ==============================================

class SupportedLanguage(Enum):
    """支持的语种枚举"""
    ENGLISH_US = "EN-US"
    ENGLISH_GB = "EN-GB"
    CHINESE_SIMPLIFIED = "ZH"
    CHINESE_TRADITIONAL = "ZH"
    FRENCH = "FR"
    GERMAN = "DE"
    SPANISH = "ES"
    ITALIAN = "IT"
    PORTUGUESE = "PT"
    RUSSIAN = "RU"
    JAPANESE = "JA"
    KOREAN = "KO"
    ARABIC = "AR"
    DUTCH = "NL"
    POLISH = "PL"
    SWEDISH = "SV"
    DANISH = "DA"
    FINNISH = "FI"
    NORWEGIAN = "NO"
    HINDI = "HI"
    TURKISH = "TR"
    INDONESIAN = "ID"
    VIETNAMESE = "VI"
    THAI = "TH"

@dataclass
class TranslationRequest:
    """翻译请求数据结构"""
    text: str
    target_lang: str = "EN-US"
    source_lang: Optional[str] = None
    formality: str = "default"  # default | less | more
    glossary_id: Optional[str] = None
    split_sentences: bool = True
    context: Optional[str] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if self.request_id is None:
            self.request_id = hashlib.md5(
                f"{self.text}_{self.target_lang}_{datetime.now().timestamp()}".encode()
            ).hexdigest()[:16]

@dataclass
class TranslationResponse:
    """翻译响应数据结构"""
    translated_text: str
    detected_source_lang: str
    character_count: int
    cost: float
    response_time_ms: float
    request_id: str
    timestamp: str
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class ServiceHealthStatus:
    """服务健康状态"""
    status: str  # healthy | degraded | unhealthy
    deepl_usage: Dict[str, Any]
    last_success_time: Optional[str]
    error_rate_last_hour: float
    response_time_p95: float
    cache_hit_rate: float
    timestamp: str

# ==============================================
# 自定义异常类
# ==============================================

class TranslationError(Exception):
    """翻译服务基础异常"""
    pass

class AuthError(TranslationError):
    """认证失败异常"""
    pass

class APILimitError(TranslationError):
    """API调用超限异常"""
    pass

class NetworkError(TranslationError):
    """网络连接异常"""
    pass

class ContentError(TranslationError):
    """内容格式异常"""
    pass

# ==============================================
# 核心服务类
# ==============================================

class DeepLTranslationService:
    """DeepL翻译服务核心类"""
    
    def __init__(self):
        """初始化DeepL服务"""
        self.auth_key = DEEPL_AUTH_KEY
        self.plan_type = DEEPL_PLAN_TYPE
        
        # 初始化DeepL客户端
        try:
            self.translator = deepl.Translator(self.auth_key)
            logger.info(f"DeepL客户端初始化成功，计划类型: {self.plan_type}")
        except Exception as e:
            logger.error(f"DeepL客户端初始化失败: {str(e)}")
            raise AuthError(f"DeepL认证失败: {str(e)}")
        
        # 初始化缓存
        self._init_cache()
        
        # 初始化数据库
        self._init_database()
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_characters": 0,
            "total_cost": 0.0,
            "response_times": []
        }
        
        # 速率限制
        self.rate_limiter = RateLimiter(
            requests_per_second=1 if self.plan_type == "free" else 10
        )
        
        logger.info("DeepL翻译服务初始化完成")
    
    def _init_cache(self):
        """初始化缓存系统"""
        self.cache = {}
        if REDIS_ENABLED:
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                self.redis_client.ping()
                logger.info("Redis缓存连接成功")
            except Exception as e:
                logger.warning(f"Redis连接失败，使用内存缓存: {str(e)}")
                REDIS_ENABLED = False
                self.redis_client = None
        else:
            self.redis_client = None
    
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # 创建翻译记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS translation_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE NOT NULL,
                    source_text_hash TEXT NOT NULL,
                    source_text TEXT,
                    source_lang TEXT,
                    target_lang TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    formality TEXT DEFAULT 'default',
                    glossary_id TEXT,
                    character_count INTEGER NOT NULL,
                    cost REAL NOT NULL,
                    response_time_ms REAL NOT NULL,
                    status TEXT NOT NULL,  -- success | failed | fallback
                    fallback_used BOOLEAN DEFAULT FALSE,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建API使用统计表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deepl_usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    plan_type TEXT NOT NULL,
                    characters_used INTEGER DEFAULT 0,
                    request_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0.0,
                    peak_usage_period TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, plan_type)
                )
            """)
            
            # 创建术语表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS multilingual_glossary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term_source TEXT NOT NULL,
                    term_target TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    category TEXT,
                    priority INTEGER DEFAULT 1,
                    verified BOOLEAN DEFAULT FALSE,
                    usage_count INTEGER DEFAULT 0,
                    created_by_agent_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("数据库表结构初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise
    
    # ==============================================
    # 核心翻译接口
    # ==============================================
    
    def translate_text(self, request: TranslationRequest) -> TranslationResponse:
        """
        DeepL文本翻译核心接口
        支持多语种、正式度调整、术语表、上下文等高级功能
        """
        start_time = time.time()
        request_id = request.request_id
        
        logger.info(f"[{request_id}] 开始翻译，目标语言: {request.target_lang}, 字符数: {len(request.text)}")
        
        # 检查缓存
        cache_key = self._generate_cache_key(request)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"[{request_id}] 缓存命中，使用缓存结果")
            return cached_result
        
        # 应用速率限制
        self.rate_limiter.wait_if_needed()
        
        try:
            # 调用DeepL API
            result = self.translator.translate_text(
                text=request.text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                formality=request.formality,
                glossary_id=request.glossary_id,
                split_sentences=request.split_sentences,
                context=request.context
            )
            
            # 计算响应时间和成本
            response_time = round((time.time() - start_time) * 1000, 2)
            char_count = len(request.text)
            cost = self._calculate_cost(char_count)
            
            # 构建响应
            response = TranslationResponse(
                translated_text=result.text,
                detected_source_lang=result.detected_source_lang,
                character_count=char_count,
                cost=cost,
                response_time_ms=response_time,
                request_id=request_id,
                timestamp=datetime.now().isoformat()
            )
            
            # 更新统计信息
            self._update_stats(success=True, char_count=char_count, cost=cost, response_time=response_time)
            
            # 缓存结果
            self._set_to_cache(cache_key, response)
            
            # 记录到数据库
            self._record_translation(request, response, status="success")
            
            logger.info(f"[{request_id}] 翻译成功，字符数: {char_count}, 成本: {cost}, 耗时: {response_time}ms")
            
            return response
            
        except deepl.exceptions.AuthorizationException as e:
            error_msg = f"DeepL认证失败: {str(e)}"
            logger.error(f"[{request_id}] {error_msg}")
            self._update_stats(success=False)
            self._record_translation(request, None, status="failed", error_message=error_msg)
            raise AuthError(error_msg) from e
            
        except deepl.exceptions.TooManyRequestsException as e:
            error_msg = f"DeepL API请求超限: {str(e)}"
            logger.warning(f"[{request_id}] {error_msg}")
            self._update_stats(success=False)
            self._record_translation(request, None, status="failed", error_message=error_msg)
            raise APILimitError(error_msg) from e
            
        except deepl.exceptions.DeepLException as e:
            error_msg = f"DeepL API错误: {str(e)}"
            logger.error(f"[{request_id}] {error_msg}")
            self._update_stats(success=False)
            self._record_translation(request, None, status="failed", error_message=error_msg)
            raise TranslationError(error_msg) from e
            
        except Exception as e:
            error_msg = f"翻译未知错误: {str(e)}"
            logger.error(f"[{request_id}] {error_msg}")
            self._update_stats(success=False)
            self._record_translation(request, None, status="failed", error_message=error_msg)
            raise TranslationError(error_msg) from e
    
    def batch_translate(self, requests: List[TranslationRequest]) -> List[TranslationResponse]:
        """
        批量翻译多段文本
        用于社媒内容批量生成、产品描述批量优化等场景
        """
        logger.info(f"开始批量翻译，共 {len(requests)} 个请求")
        results = []
        
        # 使用线程池并行处理（注意DeepL API限制）
        with ThreadPoolExecutor(max_workers=min(5, len(requests))) as executor:
            future_to_request = {
                executor.submit(self.translate_text, req): req 
                for req in requests
            }
            
            for future in as_completed(future_to_request):
                request = future_to_request[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"请求 {request.request_id} 翻译失败: {str(e)}")
                    # 创建失败响应
                    error_response = TranslationResponse(
                        translated_text="",
                        detected_source_lang="",
                        character_count=len(request.text),
                        cost=0.0,
                        response_time_ms=0.0,
                        request_id=request.request_id,
                        timestamp=datetime.now().isoformat()
                    )
                    results.append(error_response)
        
        logger.info(f"批量翻译完成，成功: {len([r for r in results if r.translated_text])}, 失败: {len([r for r in results if not r.translated_text])}")
        return results
    
    # ==============================================
    # 辅助接口
    # ==============================================
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        自动检测文本语言
        返回检测结果和置信度
        """
        try:
            result = self.translator.detect_language(text)
            return {
                "detected_lang": result.lang,
                "confidence": result.confidence,
                "text_sample": text[:100],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"语种检测失败: {str(e)}")
            raise TranslationError(f"语种检测失败: {str(e)}") from e
    
    def get_usage(self) -> Dict[str, Any]:
        """
        查询DeepL API用量
        监控字符消耗和成本
        """
        try:
            usage = self.translator.get_usage()
            return {
                "character_limit": usage.character_limit,
                "character_count": usage.character_count,
                "remaining": usage.character_limit - usage.character_count,
                "limit_reached": usage.character_limit_reached,
                "plan_type": self.plan_type,
                "estimated_cost": self._calculate_cost(usage.character_count),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"用量查询失败: {str(e)}")
            raise TranslationError(f"用量查询失败: {str(e)}") from e
    
    # ==============================================
    # 安全翻译接口（带兜底逻辑）
    # ==============================================
    
    def safe_translate(self, request: TranslationRequest, 
                      fallback_text: Optional[str] = None,
                      retry_count: int = 3,
                      use_cache: bool = True) -> Dict[str, Any]:
        """
        带异常兜底+重试的安全翻译接口
        核心兜底逻辑，确保服务稳定性
        
        参数:
            request: 翻译请求
            fallback_text: 备用文本（API失败时返回）
            retry_count: 重试次数
            use_cache: 是否使用缓存
        
        返回:
            包含状态、数据、元信息的完整响应
        """
        request_id = request.request_id
        logger.info(f"[{request_id}] 安全翻译开始，重试次数: {retry_count}, 使用缓存: {use_cache}")
        
        # 检查缓存（如果启用）
        if use_cache:
            cache_key = self._generate_cache_key(request)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.info(f"[{request_id}] 缓存命中，返回缓存结果")
                return {
                    "status": "success",
                    "data": asdict(cached_result),
                    "source": "cache",
                    "fallback_used": False,
                    "retry_count": 0,
                    "cached": True,
                    "timestamp": datetime.now().isoformat()
                }
        
        # 重试逻辑
        last_exception = None
        for attempt in range(retry_count):
            try:
                # 每次重试前等待一段时间（指数退避）
                if attempt > 0:
                    wait_time = 2 ** (attempt - 1)
                    logger.info(f"[{request_id}] 第 {attempt + 1} 次重试，等待 {wait_time} 秒")
                    time.sleep(wait_time)
                
                # 执行翻译
                response = self.translate_text(request)
                
                logger.info(f"[{request_id}] 翻译成功，重试次数: {attempt}")
                
                return {
                    "status": "success",
                    "data": asdict(response),
                    "source": "deepl_api",
                    "fallback_used": False,
                    "retry_count": attempt,
                    "cached": False,
                    "timestamp": datetime.now().isoformat()
                }
                
            except (AuthError, ContentError) as e:
                # 认证或内容错误不重试
                logger.error(f"[{request_id}] 认证/内容错误，不重试: {str(e)}")
                last_exception = e
                break
                
            except APILimitError as e:
                logger.warning(f"[{request_id}] API限流，重试第 {attempt + 1} 次: {str(e)}")
                last_exception = e
                continue
                
            except Exception as e:
                logger.error(f"[{request_id}] 翻译未知错误，重试第 {attempt + 1} 次: {str(e)}")
                last_exception = e
                continue
        
        # 所有重试都失败，使用兜底方案
        logger.warning(f"[{request_id}] 所有重试失败，使用兜底方案")
        
        if fallback_text:
            logger.info(f"[{request_id}] 使用备用文本兜底")
            fallback_response = TranslationResponse(
                translated_text=fallback_text,
                detected_source_lang="unknown",
                character_count=len(request.text),
                cost=0.0,
                response_time_ms=0.0,
                request_id=request_id,
                timestamp=datetime.now().isoformat()
            )
            
            return {
                "status": "fallback",
                "data": asdict(fallback_response),
                "source": "fallback_text",
                "fallback_used": True,
                "error": str(last_exception) if last_exception else "unknown error",
                "retry_count": retry_count,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 无兜底文本，返回错误
            error_msg = f"翻译失败且无兜底文本: {str(last_exception)}"
            logger.error(f"[{request_id}] {error_msg}")
            
            return {
                "status": "failed",
                "data": None,
                "source": "none",
                "fallback_used": False,
                "error": error_msg,
                "retry_count": retry_count,
                "timestamp": datetime.now().isoformat()
            }
    
    # ==============================================
    # 健康检查接口
    # ==============================================
    
    def check_service_health(self) -> ServiceHealthStatus:
        """
        检查DeepL API服务状态+系统健康
        返回完整的健康状态报告
        """
        logger.info("开始服务健康检查")
        
        try:
            # 1. 测试API连通性
            usage = self.get_usage()
            
            # 2. 测试翻译功能
            test_request = TranslationRequest(
                text="健康检查测试",
                target_lang="EN-US",
                request_id="health_check_" + datetime.now().strftime("%Y%m%d%H%M%S")
            )
            
            test_response = self.translate_text(test_request)
            
            # 3. 计算统计指标
            error_rate = self._calculate_error_rate()
            response_time_p95 = self._calculate_response_time_p95()
            cache_hit_rate = self._calculate_cache_hit_rate()
            
            # 4. 确定健康状态
            if error_rate < 0.01 and response_time_p95 < 500:
                status = "healthy"
            elif error_rate < 0.05 and response_time_p95 < 1000:
                status = "degraded"
            else:
                status = "unhealthy"
            
            health_status = ServiceHealthStatus(
                status=status,
                deepl_usage=usage,
                last_success_time=datetime.now().isoformat(),
                error_rate_last_hour=error_rate,
                response_time_p95=response_time_p95,
                cache_hit_rate=cache_hit_rate,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"服务健康检查完成，状态: {status}, 错误率: {error_rate:.2%}, 响应时间P95: {response_time_p95}ms")
            
            return health_status
            
        except Exception as e:
            logger.error(f"服务健康检查失败: {str(e)}")
            
            return ServiceHealthStatus(
                status="unhealthy",
                deepl_usage={},
                last_success_time=None,
                error_rate_last_hour=1.0,
                response_time_p95=0.0,
                cache_hit_rate=0.0,
                timestamp=datetime.now().isoformat()
            )
    
    # ==============================================
    # 缓存管理
    # ==============================================
    
    def _generate_cache_key(self, request: TranslationRequest) -> str:
        """
        生成缓存键
        基于请求内容生成唯一标识
        """
        key_parts = [
            request.text,
            request.target_lang,
            request.source_lang or "auto",
            request.formality,
            request.glossary_id or "none"
        ]
        key_string = "|".join(str(p) for p in key_parts)
        return f"deepl:{hashlib.md5(key_string.encode()).hexdigest()[:32]}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[TranslationResponse]:
        """
        从缓存获取结果
        支持Redis和内存缓存
        """
        try:
            if REDIS_ENABLED and self.redis_client:
                # Redis缓存
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    data_dict = json.loads(cached_data)
                    # 检查缓存是否过期（默认24小时）
                    cache_time = datetime.fromisoformat(data_dict["timestamp"])
                    if datetime.now() - cache_time < timedelta(hours=24):
                        return TranslationResponse(**data_dict)
                    else:
                        self.redis_client.delete(cache_key)
            else:
                # 内存缓存
                if cache_key in self.cache:
                    cached_data = self.cache[cache_key]
                    cache_time = datetime.fromisoformat(cached_data["timestamp"])
                    if datetime.now() - cache_time < timedelta(hours=24):
                        return TranslationResponse(**cached_data)
                    else:
                        del self.cache[cache_key]
        except Exception as e:
            logger.warning(f"缓存获取失败 {cache_key}: {str(e)}")
        
        return None
    
    def _set_to_cache(self, cache_key: str, response: TranslationResponse):
        """
        将结果存入缓存
        支持Redis和内存缓存
        """
        try:
            response_dict = asdict(response)
            
            if REDIS_ENABLED and self.redis_client:
                # Redis缓存，24小时过期
                self.redis_client.setex(
                    cache_key,
                    timedelta(hours=24),
                    json.dumps(response_dict)
                )
            else:
                # 内存缓存，LRU策略，限制10000条
                if len(self.cache) >= 10000:
                    # 删除最早的10%
                    keys_to_remove = list(self.cache.keys())[:1000]
                    for key in keys_to_remove:
                        del self.cache[key]
                
                self.cache[cache_key] = response_dict
                
        except Exception as e:
            logger.warning(f"缓存设置失败 {cache_key}: {str(e)}")
    
    # ==============================================
    # 数据库操作
    # ==============================================
    
    def _record_translation(self, request: TranslationRequest, 
                          response: Optional[TranslationResponse],
                          status: str,
                          error_message: Optional[str] = None):
        """
        记录翻译操作到数据库
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO translation_records 
                (request_id, source_text_hash, source_text, source_lang, target_lang,
                 translated_text, formality, glossary_id, character_count, cost,
                 response_time_ms, status, fallback_used, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id,
                hashlib.md5(request.text.encode()).hexdigest(),
                request.text[:500],  # 只存储前500字符
                request.source_lang,
                request.target_lang,
                response.translated_text if response else "",
                request.formality,
                request.glossary_id,
                len(request.text),
                response.cost if response else 0.0,
                response.response_time_ms if response else 0.0,
                status,
                1 if status == "fallback" else 0,
                error_message
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录翻译失败 {request.request_id}: {str(e)}")
    
    # ==============================================
    # 统计与监控
    # ==============================================
    
    def _update_stats(self, success: bool, char_count: int = 0, 
                     cost: float = 0.0, response_time: float = 0.0):
        """
        更新服务统计信息
        """
        self.stats["total_requests"] += 1
        
        if success:
            self.stats["successful_requests"] += 1
            self.stats["total_characters"] += char_count
            self.stats["total_cost"] += cost
            self.stats["response_times"].append(response_time)
            
            # 保持最近1000个响应时间
            if len(self.stats["response_times"]) > 1000:
                self.stats["response_times"] = self.stats["response_times"][-1000:]
        else:
            self.stats["failed_requests"] += 1
    
    def _calculate_error_rate(self) -> float:
        """
        计算错误率
        """
        total = self.stats["total_requests"]
        if total == 0:
            return 0.0
        
        failed = self.stats["failed_requests"]
        return failed / total
    
    def _calculate_response_time_p95(self) -> float:
        """
        计算P95响应时间
        """
        times = self.stats["response_times"]
        if not times:
            return 0.0
        
        sorted_times = sorted(times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]
    
    def _calculate_cache_hit_rate(self) -> float:
        """
        计算缓存命中率
        """
        # 简化实现，实际应记录缓存查询次数
        return 0.0
    
    def _calculate_cost(self, char_count: int) -> float:
        """
        计算翻译成本
        基于DeepL定价模型
        """
        # DeepL专业版约 €20/百万字符 ≈ $22/百万字符
        cost_per_million_chars = 22.0
        
        if self.plan_type == "free":
            return 0.0
        else:
            return round(char_count / 1_000_000 * cost_per_million_chars, 4)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        获取服务统计信息
        """
        return {
            **self.stats,
            "error_rate": self._calculate_error_rate(),
            "response_time_p95": self._calculate_response_time_p95(),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "plan_type": self.plan_type,
            "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
            "timestamp": datetime.now().isoformat()
        }
    
    # ==============================================
    # 高级功能
    # ==============================================
    
    def create_glossary(self, source_terms: List[str], 
                       target_terms: List[str],
                       source_lang: str, target_lang: str,
                       category: Optional[str] = None) -> str:
        """
        创建术语表
        仅DeepL Pro版本支持
        """
        if self.plan_type != "pro":
            raise TranslationError("术语表功能仅DeepL Pro版本支持")
        
        if len(source_terms) != len(target_terms):
            raise TranslationError("源术语和目标术语数量必须相同")
        
        try:
            # 这里简化实现，实际应调用DeepL API创建术语表
            glossary_id = f"glossary_{int(time.time())}_{hashlib.md5(''.join(source_terms).encode()).hexdigest()[:8]}"
            
            # 记录到数据库
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            for source, target in zip(source_terms, target_terms):
                cursor.execute("""
                    INSERT INTO multilingual_glossary 
                    (term_source, term_target, source_lang, target_lang, category)
                    VALUES (?, ?, ?, ?, ?)
                """, (source, target, source_lang, target_lang, category))
            
            conn.commit()
            conn.close()
            
            logger.info(f"术语表创建成功，ID: {glossary_id}, 术语数量: {len(source_terms)}")
            
            return glossary_id
            
        except Exception as e:
            logger.error(f"术语表创建失败: {str(e)}")
            raise TranslationError(f"术语表创建失败: {str(e)}") from e
    
    # ==============================================
    # 服务管理
    # ==============================================
    
    def start(self):
        """
        启动服务
        """
        self.start_time = time.time()
        logger.info("DeepL翻译服务已启动")
    
    def stop(self):
        """
        停止服务
        """
        logger.info("DeepL翻译服务已停止")
    
    def restart(self):
        """
        重启服务
        """
        logger.info("重启DeepL翻译服务")
        self.stop()
        time.sleep(1)
        self.start()

# ==============================================
# 速率限制器
# ==============================================

class RateLimiter:
    """API速率限制器"""
    
    def __init__(self, requests_per_second: float = 1.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """
        如果需要，等待直到可以发送下一个请求
        """
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                time.sleep(wait_time)
            
            self.last_request_time = time.time()

# ==============================================
# 前端监控组件（示例代码）
# ==============================================

class DeepLMonitoringDashboard:
    """
    DeepL翻译服务前端监控仪表盘
    实时显示服务健康状态、使用统计、成本分析等
    """
    
    def __init__(self, service: DeepLTranslationService):
        self.service = service
        self.metrics_history = []
        self.last_update_time = datetime.now()
    
    def update_metrics(self):
        """
        更新监控指标
        """
        try:
            # 获取健康状态
            health_status = self.service.check_service_health()
            
            # 获取服务统计
            stats = self.service.get_service_stats()
            
            # 记录历史数据
            self.metrics_history.append({
                "timestamp": datetime.now().isoformat(),
                "health_status": health_status.status,
                "error_rate": health_status.error_rate_last_hour,
                "response_time_p95": health_status.response_time_p95,
                "cache_hit_rate": health_status.cache_hit_rate,
                "total_requests": stats["total_requests"],
                "success_rate": stats["successful_requests"] / stats["total_requests"] if stats["total_requests"] > 0 else 0,
                "total_characters": stats["total_characters"],
                "total_cost": stats["total_cost"],
                "plan_type": self.service.plan_type
            })
            
            # 保持最近24小时数据
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.metrics_history = [
                m for m in self.metrics_history 
                if datetime.fromisoformat(m["timestamp"]) > cutoff_time
            ]
            
            self.last_update_time = datetime.now()
            
            logger.info("监控指标更新完成")
            
        except Exception as e:
            logger.error(f"监控指标更新失败: {str(e)}")
    
    def generate_health_report(self) -> Dict[str, Any]:
        """
        生成健康报告
        """
        if not self.metrics_history:
            return {"status": "no_data", "message": "尚无监控数据"}
        
        latest_metrics = self.metrics_history[-1]
        
        # 评估健康状态
        status = latest_metrics["health_status"]
        error_rate = latest_metrics["error_rate"]
        response_time = latest_metrics["response_time_p95"]
        
        # 生成建议
        recommendations = []
        
        if error_rate > 0.05:
            recommendations.append("错误率过高，建议检查API密钥和网络连接")
        
        if response_time > 1000:
            recommendations.append("响应时间过长，建议优化代码或增加超时设置")
        
        if latest_metrics["success_rate"] < 0.9:
            recommendations.append("成功率偏低，建议查看详细错误日志")
        
        return {
            "status": status,
            "error_rate": error_rate,
            "response_time_p95_ms": response_time,
            "cache_hit_rate": latest_metrics["cache_hit_rate"],
            "total_requests_last_24h": len(self.metrics_history),
            "success_rate": latest_metrics["success_rate"],
            "total_characters_today": latest_metrics["total_characters"],
            "estimated_cost_today": latest_metrics["total_cost"],
            "plan_type": latest_metrics["plan_type"],
            "last_update": latest_metrics["timestamp"],
            "recommendations": recommendations,
            "alerts": self._generate_alerts()
        }
    
    def _generate_alerts(self) -> List[Dict[str, Any]]:
        """
        生成告警信息
        """
        alerts = []
        
        if not self.metrics_history:
            return alerts
        
        latest = self.metrics_history[-1]
        
        # 错误率告警
        if latest["error_rate"] > 0.1:
            alerts.append({
                "level": "critical",
                "type": "error_rate_high",
                "message": f"错误率过高: {latest['error_rate']:.1%}",
                "timestamp": latest["timestamp"]
            })
        
        # 响应时间告警
        if latest["response_time_p95"] > 2000:
            alerts.append({
                "level": "warning",
                "type": "response_time_slow",
                "message": f"响应时间过慢: {latest['response_time_p95']:.0f}ms",
                "timestamp": latest["timestamp"]
            })
        
        # 成本告警（如果启用了Pro版）
        if latest["plan_type"] == "pro" and latest["total_cost"] > 50:
            alerts.append({
                "level": "warning",
                "type": "cost_exceeded",
                "message": f"今日成本已超过 $50: ${latest['total_cost']:.2f}",
                "timestamp": latest["timestamp"]
            })
        
        return alerts
    
    def get_performance_summary(self, period_hours: int = 24) -> Dict[str, Any]:
        """
        获取性能摘要
        """
        if not self.metrics_history:
            return {"status": "no_data"}
        
        cutoff_time = datetime.now() - timedelta(hours=period_hours)
        relevant_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]
        
        if not relevant_metrics:
            return {"status": "no_data_in_period"}
        
        # 计算统计数据
        error_rates = [m["error_rate"] for m in relevant_metrics]
        response_times = [m["response_time_p95"] for m in relevant_metrics]
        success_rates = [m["success_rate"] for m in relevant_metrics]
        
        return {
            "period_hours": period_hours,
            "total_requests": sum(m["total_requests"] for m in relevant_metrics),
            "avg_error_rate": sum(error_rates) / len(error_rates) if error_rates else 0,
            "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
            "avg_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0,
            "total_characters": sum(m["total_characters"] for m in relevant_metrics),
            "total_cost": sum(m["total_cost"] for m in relevant_metrics),
            "data_points": len(relevant_metrics),
            "start_time": relevant_metrics[0]["timestamp"],
            "end_time": relevant_metrics[-1]["timestamp"]
        }

# ==============================================
# 快速使用示例
# ==============================================

def example_usage():
    """
    使用示例
    """
    print("=== DeepL翻译服务使用示例 ===")
    
    # 1. 初始化服务
    service = DeepLTranslationService()
    service.start()
    
    # 2. 创建翻译请求
    request = TranslationRequest(
        text="你好，世界！欢迎使用DeepL翻译服务。",
        target_lang="EN-US",
        source_lang="ZH",
        formality="more",  # 正式语气
        request_id="example_001"
    )
    
    print(f"翻译请求: {request.text}")
    print(f"目标语言: {request.target_lang}")
    
    # 3. 执行翻译（安全版本）
    result = service.safe_translate(
        request,
        fallback_text="Hello, world! Welcome to DeepL translation service.",
        retry_count=2,
        use_cache=True
    )
    
    print(f"翻译状态: {result['status']}")
    print(f"翻译结果: {result['data']['translated_text'] if result['data'] else '无结果'}")
    print(f"字符数: {result['data']['character_count'] if result['data'] else 0}")
    print(f"成本: ${result['data']['cost'] if result['data'] else 0:.4f}")
    print(f"响应时间: {result['data']['response_time_ms'] if result['data'] else 0:.2f}ms")
    
    # 4. 批量翻译示例
    batch_requests = [
        TranslationRequest(text="产品描述示例一", target_lang="EN-US", request_id="batch_001"),
        TranslationRequest(text="产品描述示例二", target_lang="JA", request_id="batch_002"),
        TranslationRequest(text="产品描述示例三", target_lang="FR", request_id="batch_003")
    ]
    
    batch_results = service.batch_translate(batch_requests)
    print(f"批量翻译完成，共 {len(batch_results)} 个结果")
    
    # 5. 监控示例
    dashboard = DeepLMonitoringDashboard(service)
    dashboard.update_metrics()
    
    health_report = dashboard.generate_health_report()
    print(f"服务健康状态: {health_report['status']}")
    
    # 6. 获取使用统计
    usage = service.get_usage()
    print(f"API用量: {usage['character_count']}/{usage['character_limit']} 字符")
    print(f"剩余额度: {usage['remaining']} 字符")
    
    # 7. 停止服务
    service.stop()
    
    print("=== 示例完成 ===")

# ==============================================
# 主程序入口
# ==============================================

if __name__ == "__main__":
    # 检查依赖
    try:
        import deepl
    except ImportError:
        print("错误: 请先安装 deepl-python 库")
        print("安装命令: pip install deepl-python")
        exit(1)
    
    try:
        import redis
    except ImportError:
        print("警告: redis 库未安装，缓存功能将受限")
        REDIS_ENABLED = False
    
    # 创建必要的目录
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data/shared_state", exist_ok=True)
    
    # 运行示例
    example_usage()