"""
原创合规校验系统集成模块
实现与原创检测系统的深度协同
"""

import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from ..database.models import RiskLevel, Violation, ComplianceResult

logger = logging.getLogger(__name__)

@dataclass
class OriginalityRequest:
    """原创检测请求"""
    content_id: str
    text: str
    content_type: str
    target_countries: List[str]
    language: str = "auto"

@dataclass
class OriginalityResult:
    """原创检测结果"""
    content_id: str
    originality_score: float  # 0.0-1.0
    plagiarism_risk: str  # low/medium/high
    similarity_items: List[Dict[str, Any]]
    recommendations: List[str]
    processing_time_ms: float

class OriginalityIntegrator:
    """原创检测集成器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "service_endpoint": "http://originality-service:8000",
            "api_key": "your_originality_api_key",
            "cache_enabled": True,
            "cache_ttl_seconds": 1800,
            "timeout_seconds": 10,
            "max_retries": 2,
            "retry_delay_seconds": 1
        }
        
        # 原创检测服务配置
        self.originality_service = None
        
        # 结果缓存
        self.result_cache = {}
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_processing_time_ms": 0.0
        }
        
        logger.info("OriginalityIntegrator initialized")
    
    async def initialize_service(self):
        """初始化原创检测服务连接"""
        # 在实际系统中，这里会建立与服务端的连接
        # 简化实现：模拟服务
        
        if self.config.get("simulation_mode", True):
            logger.info("使用模拟原创检测服务")
            return True
        
        try:
            # 这里应该建立实际的服务连接
            # 例如: self.originality_service = OriginalityServiceClient(...)
            pass
            
        except Exception as e:
            logger.error(f"原创检测服务初始化失败: {str(e)}")
            return False
        
        return True
    
    async def check_originality(self, request: OriginalityRequest) -> OriginalityResult:
        """
        检查内容原创性
        Args:
            request: 原创检测请求
        Returns:
            原创检测结果
        """
        start_time = datetime.now()
        
        try:
            # 检查缓存
            cache_key = self._generate_cache_key(request)
            if self.config.get("cache_enabled", True) and cache_key in self.result_cache:
                cached_result = self.result_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.debug(f"使用缓存原创检测结果: {cache_key}")
                    
                    # 更新缓存访问时间
                    cached_result["last_accessed"] = datetime.now()
                    
                    return OriginalityResult(**cached_result["data"])
            
            # 执行原创检测
            result = await self._perform_originality_check(request)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result.processing_time_ms = processing_time
            
            # 更新统计
            self._update_stats(success=True, processing_time=processing_time)
            
            # 缓存结果
            if self.config.get("cache_enabled", True):
                self.result_cache[cache_key] = {
                    "data": asdict(result),
                    "timestamp": datetime.now(),
                    "last_accessed": datetime.now(),
                    "ttl": self.config.get("cache_ttl_seconds", 1800)
                }
            
            logger.info(f"原创检测完成: content_id={request.content_id}, "
                       f"score={result.originality_score:.2f}, "
                       f"risk={result.plagiarism_risk}, "
                       f"time={processing_time:.2f}ms")
            
            return result
            
        except Exception as e:
            # 更新统计
            self._update_stats(success=False, processing_time=0)
            
            logger.error(f"原创检测失败: error={str(e)}, content_id={request.content_id}")
            
            # 返回默认结果
            return OriginalityResult(
                content_id=request.content_id,
                originality_score=0.5,
                plagiarism_risk="medium",
                similarity_items=[],
                recommendations=["原创检测服务暂时不可用，请人工审核"],
                processing_time_ms=0.0
            )
    
    async def integrate_results(self, compliance_result: ComplianceResult,
                               originality_result: OriginalityResult) -> Dict[str, Any]:
        """
        整合合规检测与原创检测结果
        Args:
            compliance_result: 合规检测结果
            originality_result: 原创检测结果
        Returns:
            整合结果
        """
        try:
            # 综合风险评估
            combined_risk = self._combine_risk_assessments(
                compliance_result, originality_result
            )
            
            # 生成整合建议
            combined_suggestions = self._generate_combined_suggestions(
                compliance_result, originality_result
            )
            
            # 确定优先级
            priority_items = self._determine_priority_items(
                compliance_result.violations,
                originality_result.similarity_items
            )
            
            # 构建整合结果
            integrated_result = {
                "content_id": compliance_result.content_id,
                "risk_assessment": combined_risk,
                "violations": {
                    "compliance": [asdict(v) for v in compliance_result.violations],
                    "originality": originality_result.similarity_items
                },
                "suggestions": combined_suggestions,
                "priority_items": priority_items,
                "overall_risk_level": self._determine_overall_risk_level(combined_risk),
                "processing_details": {
                    "compliance_time_ms": compliance_result.processing_time_ms,
                    "originality_time_ms": originality_result.processing_time_ms,
                    "total_time_ms": compliance_result.processing_time_ms + originality_result.processing_time_ms
                },
                "metadata": {
                    "integration_timestamp": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }
            
            logger.info(f"结果整合完成: content_id={compliance_result.content_id}, "
                       f"overall_risk={integrated_result['overall_risk_level']}")
            
            return integrated_result
            
        except Exception as e:
            logger.error(f"结果整合失败: {str(e)}")
            
            # 返回基本整合结果
            return {
                "content_id": compliance_result.content_id,
                "error": str(e),
                "compliance_result": asdict(compliance_result),
                "originality_result": asdict(originality_result)
            }
    
    async def get_originality_status(self, content_id: str) -> Dict[str, Any]:
        """
        获取内容原创性状态
        Args:
            content_id: 内容ID
        Returns:
            原创性状态
        """
        try:
            # 在实际系统中，这里会查询服务状态
            # 简化实现：返回模拟状态
            
            status = {
                "content_id": content_id,
                "last_check_time": (datetime.now() - timedelta(hours=1)).isoformat(),
                "originality_score": 0.85,
                "plagiarism_risk": "low",
                "status": "checked",
                "has_issues": False,
                "last_recommendations": ["内容原创性良好"]
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取原创性状态失败: {str(e)}")
            
            return {
                "content_id": content_id,
                "error": str(e),
                "status": "unknown"
            }
    
    async def get_statistics(self, time_range: str = "7d") -> Dict[str, Any]:
        """
        获取原创检测统计信息
        Args:
            time_range: 时间范围（1d, 7d, 30d）
        Returns:
            统计信息
        """
        # 简化实现：返回模拟统计数据
        
        stats = {
            "time_range": time_range,
            "total_checks": 1250,
            "avg_originality_score": 0.78,
            "plagiarism_distribution": {
                "low": 850,
                "medium": 350,
                "high": 50
            },
            "top_violation_types": [
                {"type": "text_reuse", "count": 120, "percentage": 9.6},
                {"type": "paraphrasing", "count": 85, "percentage": 6.8},
                {"type": "citation_missing", "count": 65, "percentage": 5.2}
            ],
            "risk_trends": {
                "past_week": [0.82, 0.79, 0.76, 0.81, 0.78, 0.75, 0.80],
                "labels": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]
            }
        }
        
        return stats
    
    async def _perform_originality_check(self, request: OriginalityRequest) -> OriginalityResult:
        """执行原创检测"""
        # 在实际系统中，这里会调用原创检测服务API
        # 简化实现：模拟检测过程
        
        await asyncio.sleep(0.05)  # 模拟处理延迟
        
        # 根据文本内容模拟检测结果
        text_lower = request.text.lower()
        
        # 检查常见违规模式
        plagiarism_risk = "low"
        originality_score = 0.9
        
        # 如果文本较短或包含常见短语，风险增加
        if len(request.text) < 50:
            originality_score = 0.6
            plagiarism_risk = "medium"
        
        # 检查常见营销用语
        common_phrases = [
            "best in class", "top quality", "number one",
            "unbeatable price", "limited time offer"
        ]
        
        common_count = sum(1 for phrase in common_phrases if phrase in text_lower)
        if common_count >= 3:
            originality_score = max(0.4, originality_score - 0.2)
            plagiarism_risk = "medium"
        
        # 生成相似项（模拟）
        similarity_items = []
        if originality_score < 0.8:
            similarity_items.append({
                "id": "similar_001",
                "source": "Industry Standard Marketing Copy",
                "similarity": round(1.0 - originality_score, 2),
                "matched_text": "best in class quality and service",
                "suggested_replacement": "excellent quality and reliable service"
            })
        
        # 生成建议
        recommendations = []
        if originality_score >= 0.8:
            recommendations.append("内容原创性良好，符合要求")
        elif originality_score >= 0.6:
            recommendations.append("内容原创性一般，建议优化部分常见表述")
        else:
            recommendations.append("内容原创性较低，建议重写或大幅修改")
        
        return OriginalityResult(
            content_id=request.content_id,
            originality_score=round(originality_score, 4),
            plagiarism_risk=plagiarism_risk,
            similarity_items=similarity_items,
            recommendations=recommendations,
            processing_time_ms=0.0  # 会在外部设置
        )
    
    def _combine_risk_assessments(self, compliance_result: ComplianceResult,
                                 originality_result: OriginalityResult) -> Dict[str, Any]:
        """综合风险评估"""
        # 合规风险分数
        compliance_risk = compliance_result.risk_score
        
        # 原创性风险分数（原创性越低风险越高）
        originality_risk = 1.0 - originality_result.originality_score
        
        # 加权综合
        weights = self.config.get("risk_weights", {
            "compliance": 0.7,
            "originality": 0.3
        })
        
        combined_score = (
            compliance_risk * weights["compliance"] +
            originality_risk * weights["originality"]
        )
        
        # 确定综合风险等级
        risk_level = self._determine_combined_risk_level(
            combined_score,
            compliance_result.risk_level,
            originality_result.plagiarism_risk
        )
        
        return {
            "combined_score": round(combined_score, 4),
            "compliance_score": round(compliance_risk, 4),
            "originality_score": round(originality_result.originality_score, 4),
            "risk_level": risk_level.value,
            "factors": {
                "compliance_violations": len(compliance_result.violations),
                "originality_issues": len(originality_result.similarity_items)
            }
        }
    
    def _generate_combined_suggestions(self, compliance_result: ComplianceResult,
                                      originality_result: OriginalityResult) -> List[str]:
        """生成整合建议"""
        suggestions = []
        
        # 添加合规建议
        suggestions.extend(compliance_result.suggestions)
        
        # 添加原创性建议
        suggestions.extend(originality_result.recommendations)
        
        # 去重
        unique_suggestions = []
        seen = set()
        
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        # 优先级排序
        high_priority_keywords = ["立即", "必须", "紧急", "严重", "高风险"]
        medium_priority_keywords = ["建议", "优化", "修改", "调整"]
        
        def get_priority(suggestion: str) -> int:
            suggestion_lower = suggestion.lower()
            for keyword in high_priority_keywords:
                if keyword in suggestion_lower:
                    return 1  # 高优先级
            for keyword in medium_priority_keywords:
                if keyword in suggestion_lower:
                    return 2  # 中优先级
            return 3  # 低优先级
        
        unique_suggestions.sort(key=get_priority)
        
        return unique_suggestions
    
    def _determine_priority_items(self, compliance_violations: List[Violation],
                                 similarity_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """确定优先级事项"""
        priority_items = []
        
        # 处理合规违规
        for violation in compliance_violations:
            if violation.risk_level == RiskLevel.CRITICAL:
                priority_items.append({
                    "id": violation.id,
                    "type": "compliance_critical",
                    "description": f"紧急合规风险: {violation.description}",
                    "risk_level": "critical",
                    "action": "block_immediately",
                    "matched_text": violation.matched_text[:100] + "..." if len(violation.matched_text) > 100 else violation.matched_text
                })
            elif violation.risk_level == RiskLevel.HIGH:
                priority_items.append({
                    "id": violation.id,
                    "type": "compliance_high",
                    "description": f"高风险合规违规: {violation.description}",
                    "risk_level": "high",
                    "action": "review_required",
                    "matched_text": violation.matched_text[:80] + "..." if len(violation.matched_text) > 80 else violation.matched_text
                })
        
        # 处理原创性问题
        for item in similarity_items:
            similarity = item.get("similarity", 0)
            if similarity >= 0.8:
                priority_items.append({
                    "id": item.get("id", "unknown"),
                    "type": "originality_critical",
                    "description": f"严重原创性问题: 相似度{similarity:.0%}",
                    "risk_level": "high",
                    "action": "major_rewrite_needed",
                    "matched_text": item.get("matched_text", "")[:80] + "..." if len(item.get("matched_text", "")) > 80 else item.get("matched_text", "")
                })
            elif similarity >= 0.6:
                priority_items.append({
                    "id": item.get("id", "unknown"),
                    "type": "originality_medium",
                    "description": f"中度原创性问题: 相似度{similarity:.0%}",
                    "risk_level": "medium",
                    "action": "optimization_needed",
                    "matched_text": item.get("matched_text", "")[:60] + "..." if len(item.get("matched_text", "")) > 60 else item.get("matched_text", "")
                })
        
        # 按风险等级排序
        priority_items.sort(key=lambda x: {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4
        }.get(x.get("risk_level", "low"), 5))
        
        return priority_items
    
    def _determine_combined_risk_level(self, combined_score: float,
                                     compliance_level: RiskLevel,
                                     originality_risk: str) -> RiskLevel:
        """确定综合风险等级"""
        # 如果有任意一个风险等级为CRITICAL，则综合为CRITICAL
        if compliance_level == RiskLevel.CRITICAL or originality_risk == "high":
            return RiskLevel.CRITICAL
        
        # 基于综合分数
        if combined_score >= 0.8:
            return RiskLevel.CRITICAL
        elif combined_score >= 0.65:
            return RiskLevel.HIGH
        elif combined_score >= 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _determine_overall_risk_level(self, risk_assessment: Dict[str, Any]) -> str:
        """确定总体风险等级"""
        risk_level = risk_assessment.get("risk_level", "medium")
        
        # 可以在这里添加更复杂的逻辑
        return risk_level
    
    def _generate_cache_key(self, request: OriginalityRequest) -> str:
        """生成缓存键"""
        import hashlib
        
        key_parts = [
            request.content_id,
            request.text[:500],  # 只取前500字符，避免太长
            request.content_type,
            ",".join(sorted(request.target_countries)),
            request.language
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()[:16]
    
    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if not cached_data:
            return False
        
        timestamp = cached_data.get("timestamp")
        if not timestamp:
            return False
        
        ttl = cached_data.get("ttl", 1800)
        age = (datetime.now() - timestamp).total_seconds()
        
        return age <= ttl
    
    def _update_stats(self, success: bool, processing_time: float):
        """更新统计"""
        self.stats["total_requests"] += 1
        
        if success:
            self.stats["successful_requests"] += 1
            
            # 更新平均处理时间（移动平均）
            current_avg = self.stats["avg_processing_time_ms"]
            n = self.stats["successful_requests"]
            self.stats["avg_processing_time_ms"] = (
                current_avg * (n - 1) + processing_time
            ) / n
        
        else:
            self.stats["failed_requests"] += 1
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        total_entries = len(self.result_cache)
        
        # 计算缓存大小（估算）
        cache_size = 0
        for cached in self.result_cache.values():
            # 估算每个缓存条目的大小
            data_size = len(json.dumps(cached.get("data", {}), ensure_ascii=False))
            cache_size += data_size
        
        # 计算缓存命中率（需要记录历史）
        # 简化实现：返回基本信息
        
        return {
            "total_entries": total_entries,
            "estimated_size_bytes": cache_size,
            "cache_enabled": self.config.get("cache_enabled", True),
            "cache_ttl_seconds": self.config.get("cache_ttl_seconds", 1800)
        }
    
    def cleanup_cache(self, max_age_hours: int = 12):
        """清理过期缓存"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, cached in self.result_cache.items():
            timestamp = cached.get("timestamp")
            if not timestamp:
                expired_keys.append(key)
                continue
            
            age_hours = (current_time - timestamp).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                expired_keys.append(key)
        
        # 删除过期缓存
        for key in expired_keys:
            del self.result_cache[key]
        
        logger.info(f"原创检测缓存清理完成: 删除了{len(expired_keys)}个过期条目")
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """验证配置"""
        errors = []
        
        # 检查服务端点
        endpoint = self.config.get("service_endpoint", "")
        if not endpoint:
            errors.append("原创检测服务端点未配置")
        elif endpoint.startswith("http://") and "localhost" in endpoint:
            logger.warning("使用本地开发端点，生产环境请配置正式服务")
        
        # 检查API密钥
        api_key = self.config.get("api_key", "")
        if not api_key or api_key.startswith("your_"):
            errors.append("原创检测API密钥未配置或无效")
        
        # 检查超时设置
        timeout = self.config.get("timeout_seconds", 10)
        if timeout <= 0:
            errors.append(f"无效的超时设置: {timeout}秒")
        
        return len(errors) == 0, errors