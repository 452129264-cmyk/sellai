"""
内容筛查核心模块
实现文本合规检查的主要流程
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict
from datetime import datetime

from ..database.models import (
    ComplianceRequest,
    ComplianceResult,
    Violation,
    CaseReference,
    RiskLevel,
    ContentType
)
from ..engine.rule_engine import SmartRuleEngine
from ..integrators.notebooklm_integrator import NotebookLMIntegrator
from ..integrators.deepl_integrator import DeepLIntegrator
from ..integrators.originality_integrator import OriginalityIntegrator

# 配置日志
logger = logging.getLogger(__name__)

class ContentScreener:
    """内容筛查器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 初始化组件
        self.rule_engine = SmartRuleEngine(
            config=self.config.get("rule_engine", {})
        )
        
        # 初始化集成器（实际系统中需要配置）
        self.notebooklm_integrator = None
        self.deepl_integrator = None
        self.originality_integrator = None
        
        # 性能统计
        self.stats = {
            "total_checks": 0,
            "total_violations": 0,
            "avg_processing_time": 0.0,
            "interception_count": 0
        }
    
    def initialize_integrators(self, 
                               notebooklm_config: Optional[Dict] = None,
                               deepl_config: Optional[Dict] = None,
                               originality_config: Optional[Dict] = None):
        """初始化集成器"""
        if notebooklm_config:
            self.notebooklm_integrator = NotebookLMIntegrator(notebooklm_config)
        
        if deepl_config:
            self.deepl_integrator = DeepLIntegrator(deepl_config)
        
        if originality_config:
            self.originality_integrator = OriginalityIntegrator(originality_config)
    
    async def screen_content(self, request: ComplianceRequest) -> ComplianceResult:
        """
        筛查内容合规性
        Args:
            request: 合规检查请求
        Returns:
            合规检查结果
        """
        start_time = time.time()
        
        try:
            # 1. 文本预处理
            processed_text = await self._preprocess_text(request)
            
            # 2. 规则引擎检查
            violations = self.rule_engine.check(
                processed_text, 
                request.target_country,
                request.content_type.value
            )
            
            # 3. AI风险评估（如果有AI集成）
            risk_score = await self._assess_risk(processed_text, request, violations)
            
            # 4. 查询相似案例（如果有Notebook LM集成）
            similar_cases = await self._get_similar_cases(processed_text, request, violations)
            
            # 5. 生成修改建议
            suggestions = self._generate_suggestions(violations, risk_score)
            
            # 6. 确定风险等级
            risk_level = self._determine_risk_level(risk_score, violations)
            
            # 7. 判断是否需要拦截
            intercepted, interception_reason = self._should_intercept(risk_level, risk_score, violations)
            
            # 8. 更新统计
            self._update_stats(len(violations), intercepted)
            
            # 9. 返回结果
            processing_time = (time.time() - start_time) * 1000
            
            result = ComplianceResult(
                content_id=request.content_id,
                risk_level=risk_level,
                risk_score=risk_score,
                violations=violations,
                suggestions=suggestions,
                similar_cases=similar_cases,
                processing_time_ms=processing_time,
                intercepted=intercepted,
                interception_reason=interception_reason
            )
            
            logger.info(f"内容筛查完成: content_id={request.content_id}, "
                       f"risk_level={risk_level}, violations={len(violations)}, "
                       f"intercepted={intercepted}, time={processing_time:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"内容筛查失败: content_id={request.content_id}, error={str(e)}")
            raise
    
    async def _preprocess_text(self, request: ComplianceRequest) -> str:
        """文本预处理（语言检测、翻译等）"""
        text = request.text
        
        # 检查文本长度限制
        max_length = self.config.get("max_text_length", 10000)
        if len(text) > max_length:
            logger.warning(f"文本过长: {len(text)}字符，将截断至{max_length}字符")
            text = text[:max_length]
        
        # 如果需要翻译且DeepL集成器可用
        if (self.deepl_integrator and 
            request.context and "translation_needed" in request.context.lower()):
            
            # 简化：假设需要翻译到目标国家语言
            target_lang = self._get_country_language(request.target_country)
            
            try:
                translated = await self.deepl_integrator.translate_text(
                    text=text,
                    target_lang=target_lang
                )
                return translated.translated_text
            except Exception as e:
                logger.warning(f"翻译失败，使用原文: {str(e)}")
        
        return text
    
    async def _assess_risk(self, text: str, request: ComplianceRequest, 
                          violations: List[Violation]) -> float:
        """AI风险评估"""
        # 基础风险评估：基于违规数量和严重程度
        
        if not violations:
            return 0.0
        
        # 计算加权风险分数
        total_weight = 0.0
        weighted_sum = 0.0
        
        risk_weights = {
            RiskLevel.LOW: 0.3,
            RiskLevel.MEDIUM: 0.6,
            RiskLevel.HIGH: 0.85,
            RiskLevel.CRITICAL: 1.0
        }
        
        for violation in violations:
            weight = risk_weights.get(violation.risk_level, 0.5)
            confidence = violation.confidence
            
            weighted_sum += weight * confidence
            total_weight += weight
        
        # 如果有AI模型集成，可以在这里添加更复杂的评估
        # 简化实现：返回加权平均
        
        if total_weight > 0:
            base_score = weighted_sum / total_weight
        else:
            base_score = 0.5
        
        # 根据行业和内容类型调整
        industry_factor = self._get_industry_factor(request.industry)
        content_type_factor = self._get_content_type_factor(request.content_type)
        
        adjusted_score = base_score * industry_factor * content_type_factor
        
        # 确保在0-1范围内
        return min(1.0, max(0.0, adjusted_score))
    
    async def _get_similar_cases(self, text: str, request: ComplianceRequest,
                                violations: List[Violation]) -> List[CaseReference]:
        """获取相似合规案例"""
        if not self.notebooklm_integrator or not violations:
            return []
        
        try:
            # 构建查询
            query = self._build_case_query(text, request, violations)
            
            # 查询Notebook LM
            cases = await self.notebooklm_integrator.query_similar_cases(
                query=query,
                country_code=request.target_country,
                max_results=5
            )
            
            return cases
            
        except Exception as e:
            logger.warning(f"获取相似案例失败: {str(e)}")
            return []
    
    def _generate_suggestions(self, violations: List[Violation], risk_score: float) -> List[str]:
        """生成修改建议"""
        suggestions = []
        
        # 基于违规生成具体建议
        for violation in violations:
            if violation.suggested_correction:
                suggestions.append(violation.suggested_correction)
        
        # 通用建议
        if risk_score >= 0.8:
            suggestions.append("内容风险极高，建议全面重写")
        elif risk_score >= 0.6:
            suggestions.append("内容存在明显风险，建议重点修改高风险部分")
        elif risk_score >= 0.4:
            suggestions.append("内容存在轻度风险，建议优化相关表述")
        
        # 去重
        return list(dict.fromkeys(suggestions))
    
    def _determine_risk_level(self, risk_score: float, violations: List[Violation]) -> RiskLevel:
        """确定风险等级"""
        if not violations:
            return RiskLevel.LOW
        
        # 如果有紧急违规，直接设为CRITICAL
        critical_violations = [v for v in violations if v.risk_level == RiskLevel.CRITICAL]
        if critical_violations:
            return RiskLevel.CRITICAL
        
        # 基于风险分数确定等级
        if risk_score >= 0.9:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.75:
            return RiskLevel.HIGH
        elif risk_score >= 0.5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _should_intercept(self, risk_level: RiskLevel, risk_score: float,
                         violations: List[Violation]) -> Tuple[bool, Optional[str]]:
        """判断是否需要拦截"""
        interception_config = self.config.get("interception", {})
        
        # 检查CRITICAL风险
        if risk_level == RiskLevel.CRITICAL:
            return True, "检测到紧急风险违规"
        
        # 检查HIGH风险且置信度高
        if (risk_level == RiskLevel.HIGH and 
            risk_score >= interception_config.get("high_risk_threshold", 0.85)):
            
            # 检查是否有高风险的特定违规类型
            high_risk_types = interception_config.get("high_risk_types", [])
            for violation in violations:
                if violation.clause_code in high_risk_types:
                    return True, f"高风险违规类型: {violation.clause_code}"
        
        # 配置拦截阈值
        intercept_threshold = interception_config.get("score_threshold", 0.95)
        if risk_score >= intercept_threshold:
            return True, f"风险分数超过阈值: {risk_score:.2f} >= {intercept_threshold}"
        
        return False, None
    
    def _build_case_query(self, text: str, request: ComplianceRequest,
                         violations: List[Violation]) -> str:
        """构建案例查询"""
        # 提取关键信息
        violation_types = [v.clause_code for v in violations]
        risk_levels = [v.risk_level.value for v in violations]
        
        query_parts = []
        
        # 添加违规类型
        if violation_types:
            query_parts.append(f"违规类型: {', '.join(set(violation_types))}")
        
        # 添加风险等级
        if risk_levels:
            query_parts.append(f"风险等级: {', '.join(set(risk_levels))}")
        
        # 添加上下文
        if request.context:
            query_parts.append(f"上下文: {request.context}")
        
        # 添加行业
        if request.industry:
            query_parts.append(f"行业: {request.industry}")
        
        # 添加内容类型
        query_parts.append(f"内容类型: {request.content_type.value}")
        
        # 添加文本摘要
        text_summary = text[:200] + "..." if len(text) > 200 else text
        query_parts.append(f"内容摘要: {text_summary}")
        
        return " | ".join(query_parts)
    
    def _get_country_language(self, country_code: str) -> str:
        """获取国家主要语言代码"""
        language_map = {
            "US": "EN-US",
            "GB": "EN-GB",
            "CN": "ZH",
            "JP": "JA",
            "KR": "KO",
            "DE": "DE",
            "FR": "FR",
            "ES": "ES",
            "IT": "IT",
            "RU": "RU"
        }
        return language_map.get(country_code, "EN-US")
    
    def _get_industry_factor(self, industry: Optional[str]) -> float:
        """获取行业风险因子"""
        if not industry:
            return 1.0
        
        high_risk_industries = ["healthcare", "finance", "pharmaceutical", "education"]
        medium_risk_industries = ["beauty", "fitness", "technology", "real_estate"]
        
        if industry.lower() in high_risk_industries:
            return 1.2
        elif industry.lower() in medium_risk_industries:
            return 1.1
        else:
            return 1.0
    
    def _get_content_type_factor(self, content_type: ContentType) -> float:
        """获取内容类型风险因子"""
        factors = {
            ContentType.ADVERTISEMENT: 1.3,
            ContentType.PRODUCT_DESCRIPTION: 1.1,
            ContentType.SOCIAL_MEDIA: 1.0,
            ContentType.EMAIL_MARKETING: 1.2,
            ContentType.WEB_CONTENT: 1.0,
            ContentType.DOCUMENT: 0.9
        }
        return factors.get(content_type, 1.0)
    
    def _update_stats(self, violation_count: int, intercepted: bool):
        """更新统计"""
        self.stats["total_checks"] += 1
        self.stats["total_violations"] += violation_count
        
        if intercepted:
            self.stats["interception_count"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计"""
        self.stats = {
            "total_checks": 0,
            "total_violations": 0,
            "avg_processing_time": 0.0,
            "interception_count": 0
        }