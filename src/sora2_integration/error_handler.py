"""
Sora2视频生成错误处理模块
实现API调用重试、网络异常处理、质量检查回退方案
"""

import time
import logging
from typing import Optional, Dict, Any, Callable, TypeVar, Generic
from dataclasses import dataclass
import random

from .config import Sora2RetryConfig


T = TypeVar('T')


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    retry_delay: float = 30.0  # 秒
    exponential_backoff: bool = True
    backoff_factor: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1


class Sora2Error(Exception):
    """Sora2错误基类"""
    def __init__(self, message: str, 
                 original_exception: Optional[Exception] = None,
                 context: Optional[Dict] = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.context = context or {}


class APIError(Sora2Error):
    """API调用错误"""
    pass


class NetworkError(Sora2Error):
    """网络错误"""
    pass


class AuthenticationError(Sora2Error):
    """认证错误"""
    pass


class RateLimitError(Sora2Error):
    """速率限制错误"""
    pass


class VideoGenerationError(Sora2Error):
    """视频生成错误"""
    pass


class QualityCheckError(Sora2Error):
    """质量检查错误"""
    pass


class RetryManager:
    """重试管理器"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)
    
    def execute_with_retry(self, func: Callable[[], T], 
                          error_handler: Optional[Callable[[Exception], Any]] = None) -> T:
        """
        执行带重试的函数
        
        Args:
            func: 要执行的函数
            error_handler: 错误处理函数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次尝试的异常
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    self._log_retry_attempt(attempt, last_exception)
                    self._wait_before_retry(attempt)
                
                return func()
                
            except Exception as e:
                last_exception = e
                
                # 调用错误处理函数
                if error_handler:
                    try:
                        error_handler(e)
                    except Exception as handler_error:
                        self.logger.warning(f"错误处理函数异常: {handler_error}")
                
                # 判断是否应该继续重试
                if not self._should_retry(e, attempt):
                    break
        
        # 所有重试都失败
        self._log_final_failure(self.config.max_retries, last_exception)
        raise last_exception
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        # 已达到最大重试次数
        if attempt >= self.config.max_retries:
            return False
        
        # 根据异常类型判断
        if isinstance(exception, (AuthenticationError, RateLimitError)):
            # 认证错误和速率限制错误通常不需要重试
            return False
        
        # 网络错误、API暂时不可用等可以重试
        if isinstance(exception, (NetworkError, APIError, VideoGenerationError)):
            return True
        
        # 其他未知错误，根据重试次数判断
        return attempt < min(self.config.max_retries, 3)
    
    def _wait_before_retry(self, attempt: int):
        """重试前等待"""
        delay = self.config.retry_delay
        
        if self.config.exponential_backoff:
            delay *= (self.config.backoff_factor ** (attempt - 1))
        
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay)  # 确保最小延迟
        
        self.logger.debug(f"重试前等待 {delay:.2f} 秒")
        time.sleep(delay)
    
    def _log_retry_attempt(self, attempt: int, exception: Exception):
        """记录重试尝试"""
        self.logger.warning(
            f"第 {attempt} 次重试 (异常: {type(exception).__name__}: {str(exception)[:100]}...)"
        )
    
    def _log_final_failure(self, max_retries: int, exception: Exception):
        """记录最终失败"""
        self.logger.error(
            f"经过 {max_retries} 次重试后仍然失败: "
            f"{type(exception).__name__}: {str(exception)}"
        )


class ErrorClassifier:
    """错误分类器"""
    
    @staticmethod
    def classify(exception: Exception) -> Sora2Error:
        """
        分类异常
        
        Args:
            exception: 异常对象
            
        Returns:
            分类后的Sora2Error
        """
        error_str = str(exception).lower()
        
        # API错误
        if "api" in error_str or "endpoint" in error_str:
            return APIError(str(exception), exception)
        
        # 网络错误
        if any(keyword in error_str for keyword in [
            "connection", "network", "timeout", "ssl", "proxy"
        ]):
            return NetworkError(str(exception), exception)
        
        # 认证错误
        if any(keyword in error_str for keyword in [
            "authentication", "unauthorized", "invalid key", "token"
        ]):
            return AuthenticationError(str(exception), exception)
        
        # 速率限制
        if any(keyword in error_str for keyword in [
            "rate limit", "too many requests", "quota", "429"
        ]):
            return RateLimitError(str(exception), exception)
        
        # 视频生成错误
        if any(keyword in error_str for keyword in [
            "video", "generation", "model", "render"
        ]):
            return VideoGenerationError(str(exception), exception)
        
        # 默认
        return Sora2Error(str(exception), exception)


class FallbackManager:
    """降级管理器"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)
    
    def quality_fallback(self, original_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        质量降级方案
        
        Args:
            original_params: 原始参数
            
        Returns:
            降级后的参数
        """
        fallback_params = original_params.copy()
        
        # 降低分辨率
        if "size" in fallback_params:
            # 从1080x1920降级到720x1280
            fallback_params["size"] = "720x1280"
        
        # 缩短时长
        if "seconds" in fallback_params:
            original_seconds = int(fallback_params["seconds"])
            fallback_params["seconds"] = str(max(5, original_seconds - 3))
        
        # 降低画质
        if "quality" in fallback_params:
            if fallback_params["quality"] == "Cinematic Ultra HD":
                fallback_params["quality"] = "HD"
        
        self.logger.info(f"应用质量降级: {fallback_params}")
        return fallback_params
    
    def model_fallback(self, original_model: str) -> str:
        """
        模型降级方案
        
        Args:
            original_model: 原始模型
            
        Returns:
            降级后的模型
        """
        fallback_hierarchy = [
            "sora-2-pro",
            "sora-2",
            "sora-2-landscape-15s",
            "sora-2-portrait-15s",
            "sora-1.5"  # 更旧但更稳定的模型
        ]
        
        try:
            current_index = fallback_hierarchy.index(original_model)
            if current_index < len(fallback_hierarchy) - 1:
                fallback_model = fallback_hierarchy[current_index + 1]
                self.logger.info(f"模型降级: {original_model} -> {fallback_model}")
                return fallback_model
        except ValueError:
            pass
        
        # 无法找到降级模型，返回默认
        return "sora-2-portrait-15s"
    
    def provider_fallback(self, current_provider: str) -> str:
        """
        服务提供商降级方案
        
        Args:
            current_provider: 当前提供商
            
        Returns:
            降级后的提供商
        """
        provider_hierarchy = [
            "openai_official",
            "sora2api", 
            "mountsea_ai"
        ]
        
        try:
            current_index = provider_hierarchy.index(current_provider)
            if current_index < len(provider_hierarchy) - 1:
                fallback_provider = provider_hierarchy[current_index + 1]
                self.logger.info(f"提供商降级: {current_provider} -> {fallback_provider}")
                return fallback_provider
        except ValueError:
            pass
        
        # 默认回退到第三方
        return "sora2api"


class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.retry_manager = RetryManager(retry_config)
        self.error_classifier = ErrorClassifier()
        self.fallback_manager = FallbackManager()
        self.logger = logging.getLogger(__name__)
    
    def handle_api_call(self, api_call_func: Callable[[], T], 
                       context: Optional[Dict] = None) -> T:
        """
        处理API调用，包括错误分类、重试和降级
        
        Args:
            api_call_func: API调用函数
            context: 调用上下文
            
        Returns:
            API调用结果
            
        Raises:
            最终的错误
        """
        context = context or {}
        
        def error_handler(exception: Exception) -> None:
            """错误处理函数"""
            classified_error = self.error_classifier.classify(exception)
            self.logger.warning(f"API调用错误: {type(classified_error).__name__}")
            
            # 记录上下文信息
            if context:
                self.logger.debug(f"错误上下文: {context}")
        
        try:
            return self.retry_manager.execute_with_retry(api_call_func, error_handler)
            
        except Sora2Error as e:
            # 已经分类的错误
            self._log_recovery_attempt(e)
            raise
            
        except Exception as e:
            # 未分类的错误
            classified_error = self.error_classifier.classify(e)
            self._log_recovery_attempt(classified_error)
            raise classified_error
    
    def _log_recovery_attempt(self, error: Sora2Error):
        """记录恢复尝试"""
        self.logger.error(
            f"错误恢复失败: {type(error).__name__} - "
            f"{str(error)[:200]}..."
        )
    
    def create_error_report(self, error: Exception, 
                           operation: str,
                           params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建错误报告
        
        Args:
            error: 错误对象
            operation: 操作名称
            params: 操作参数
            
        Returns:
            错误报告
        """
        classified_error = self.error_classifier.classify(error)
        
        report = {
            "timestamp": time.time(),
            "operation": operation,
            "error_type": type(classified_error).__name__,
            "error_message": str(error),
            "original_exception": str(classified_error.original_exception) 
                if classified_error.original_exception else None,
            "parameters": params,
            "recovery_suggestions": self._generate_recovery_suggestions(classified_error),
            "diagnostic_info": {
                "python_version": self._get_python_version(),
                "platform": self._get_platform_info(),
                "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }
        
        return report
    
    def _generate_recovery_suggestions(self, error: Sora2Error) -> List[str]:
        """生成恢复建议"""
        suggestions = []
        
        if isinstance(error, NetworkError):
            suggestions.extend([
                "检查网络连接是否正常",
                "验证代理服务器配置",
                "尝试禁用SSL证书验证（仅限测试环境）",
                "增加请求超时时间"
            ])
        
        elif isinstance(error, AuthenticationError):
            suggestions.extend([
                "验证API密钥是否正确",
                "检查API密钥权限",
                "确认服务订阅状态"
            ])
        
        elif isinstance(error, RateLimitError):
            suggestions.extend([
                "降低请求频率",
                "实施请求队列",
                "考虑升级API套餐"
            ])
        
        elif isinstance(error, VideoGenerationError):
            suggestions.extend([
                "简化提示词内容",
                "降低视频分辨率",
                "缩短视频时长",
                "尝试不同的模型"
            ])
        
        else:
            suggestions.append("检查API文档或联系技术支持")
        
        return suggestions
    
    def _get_python_version(self) -> str:
        """获取Python版本信息"""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    def _get_platform_info(self) -> str:
        """获取平台信息"""
        import platform
        return f"{platform.system()} {platform.release()}"


class CircuitBreaker:
    """熔断器模式实现"""
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger(__name__)
    
    def execute(self, func: Callable[[], T]) -> T:
        """
        执行函数，应用熔断器逻辑
        
        Args:
            func: 要执行的函数
            
        Returns:
            函数执行结果
        """
        if self.state == "OPEN":
            # 检查是否应该尝试恢复
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.logger.info("熔断器进入半开状态")
            else:
                raise CircuitBreakerOpenError("熔断器开启，拒绝请求")
        
        try:
            result = func()
            
            # 成功执行
            if self.state == "HALF_OPEN":
                # 半开状态下成功，关闭熔断器
                self._reset()
            
            return result
            
        except Exception as e:
            self._record_failure(e)
            raise
    
    def _record_failure(self, exception: Exception):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold and self.state != "OPEN":
            self.state = "OPEN"
            self.logger.warning(f"熔断器开启，失败次数: {self.failure_count}")
    
    def _reset(self):
        """重置熔断器"""
        self.failure_count = 0
        self.state = "CLOSED"
        self.logger.info("熔断器重置为关闭状态")


class CircuitBreakerOpenError(Sora2Error):
    """熔断器开启错误"""
    pass


# 便捷函数
def create_error_handling_pipeline() -> ErrorRecoveryManager:
    """创建错误处理管道"""
    retry_config = RetryConfig(
        max_retries=3,
        retry_delay=30.0,
        exponential_backoff=True,
        jitter=True
    )
    
    return ErrorRecoveryManager(retry_config)

def test_error_handling() -> Dict[str, Any]:
    """测试错误处理"""
    import random
    
    recovery_manager = create_error_handling_pipeline()
    
    test_results = []
    
    # 模拟各种错误
    test_cases = [
        ("模拟网络错误", lambda: (_ for _ in ()).throw(
            Exception("Connection failed: SSL certificate verify failed")
        )),
        ("模拟认证错误", lambda: (_ for _ in ()).throw(
            Exception("Invalid API key: authentication failed")
        )),
        ("模拟速率限制", lambda: (_ for _ in ()).throw(
            Exception("Rate limit exceeded: too many requests (429)")
        )),
        ("模拟成功调用", lambda: "API Call Successful")
    ]
    
    for name, test_func in test_cases:
        try:
            result = recovery_manager.handle_api_call(test_func, {"test_case": name})
            test_results.append({
                "name": name,
                "success": True,
                "result": result,
                "error": None
            })
        except Exception as e:
            test_results.append({
                "name": name,
                "success": False,
                "result": None,
                "error": str(e)
            })
    
    summary = {
        "total_tests": len(test_cases),
        "successful": sum(1 for r in test_results if r["success"]),
        "failed": sum(1 for r in test_results if not r["success"]),
        "results": test_results
    }
    
    return summary