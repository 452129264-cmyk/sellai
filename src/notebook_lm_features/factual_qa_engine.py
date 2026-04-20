#!/usr/bin/env python3
"""
零幻觉精准问答引擎

此模块提供基于Notebook LM事实性知识库的精准问答功能，
确保所有回答基于知识库事实，实现零幻觉、高准确率，
覆盖全球市场情报、业务数据、架构文档等SellAI专用场景。
"""

import os
import json
import re
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
import time

# 导入Notebook LM集成
try:
    from src.notebook_lm_integration import NotebookLMIntegration, KnowledgeDocument
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.notebook_lm_integration import NotebookLMIntegration, KnowledgeDocument

# 配置日志
logger = logging.getLogger(__name__)


class FactualQAEngine:
    """
    事实性问答引擎
    
    基于Notebook LM知识库提供零幻觉精准问答，
    包含事实核查、置信度评估、多源验证等功能。
    """
    
    def __init__(self, notebook_lm_integration: NotebookLMIntegration,
                 knowledge_base_id: str = "kb_global_sellai",
                 min_confidence_threshold: float = 0.7):
        """
        初始化事实性问答引擎
        
        Args:
            notebook_lm_integration: Notebook LM集成实例
            knowledge_base_id: 知识库ID
            min_confidence_threshold: 最小置信度阈值
        """
        self.nli = notebook_lm_integration
        self.knowledge_base_id = knowledge_base_id
        self.min_confidence_threshold = min_confidence_threshold
        
        # 问答缓存
        self.qa_cache = {}
        # 事实核查器
        self.fact_checker = FactChecker()
        # 置信度评估器
        self.confidence_assessor = ConfidenceAssessor()
        
        logger.info(f"事实性问答引擎初始化完成，知识库: {knowledge_base_id}")
    
    def ask_question(self, question: str, 
                    context: Optional[Dict[str, Any]] = None,
                    language: str = "zh-CN",
                    require_fact_check: bool = True) -> Dict[str, Any]:
        """
        提问并获取基于事实的回答
        
        Args:
            question: 问题文本
            context: 上下文信息
            language: 目标语言
            require_fact_check: 是否进行事实核查
            
        Returns:
            问答结果，包含回答、置信度、来源等
        """
        start_time = time.time()
        
        # 检查缓存
        cache_key = self._get_cache_key(question, context, language)
        if cache_key in self.qa_cache:
            cached_result = self.qa_cache[cache_key]
            if time.time() - cached_result["timestamp"] < 300:  # 5分钟缓存
                logger.debug(f"问答缓存命中: {question[:50]}...")
                cached_result["cached"] = True
                return cached_result
        
        try:
            # 步骤1：构建增强查询
            enhanced_query = self._enhance_query_with_context(question, context, language)
            
            # 步骤2：查询知识库
            knowledge_result = self.nli.query_knowledge_base(
                knowledge_base_id=self.knowledge_base_id,
                question=enhanced_query,
                context=context.get("knowledge_context") if context else None,
                max_results=5,
                include_sources=True
            )
            
            # 步骤3：生成回答
            answer, answer_metadata = self._generate_answer_from_knowledge(
                question, knowledge_result, context, language
            )
            
            # 步骤4：事实核查（如果要求）
            fact_check_result = None
            if require_fact_check:
                fact_check_result = self.fact_checker.check_factuality(
                    answer=answer,
                    question=question,
                    sources=knowledge_result.get("sources", []),
                    context=context
                )
                
                # 如果事实核查不通过，调整回答
                if not fact_check_result.get("is_factual", True):
                    answer = self._adjust_answer_for_fact_check(
                        answer, fact_check_result, question, language
                    )
            
            # 步骤5：置信度评估
            confidence_result = self.confidence_assessor.assess_confidence(
                answer=answer,
                knowledge_result=knowledge_result,
                fact_check_result=fact_check_result,
                question=question,
                context=context
            )
            
            # 步骤6：构建最终结果
            final_result = {
                "question": question,
                "answer": answer,
                "confidence": confidence_result["overall_confidence"],
                "fact_check": fact_check_result,
                "confidence_details": confidence_result,
                "sources": self._format_sources(knowledge_result.get("sources", [])),
                "answer_metadata": answer_metadata,
                "retrieval_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "language": language,
                "knowledge_base_id": self.knowledge_base_id,
                "cached": False
            }
            
            # 更新缓存
            self.qa_cache[cache_key] = {
                **final_result,
                "timestamp": time.time()
            }
            
            # 清理过期缓存
            self._clean_expired_cache()
            
            logger.info(f"问答完成: 问题='{question[:50]}...', 置信度={confidence_result['overall_confidence']:.2f}")
            
            return final_result
            
        except Exception as e:
            logger.error(f"问答失败: {question[:50]}..., 错误: {str(e)}")
            
            error_result = {
                "question": question,
                "answer": f"抱歉，我无法回答这个问题。错误: {str(e)}",
                "confidence": 0.0,
                "fact_check": None,
                "confidence_details": {"error": str(e)},
                "sources": [],
                "answer_metadata": {"error": True, "error_type": type(e).__name__},
                "retrieval_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "language": language,
                "knowledge_base_id": self.knowledge_base_id,
                "cached": False
            }
            
            return error_result
    
    def _enhance_query_with_context(self, question: str,
                                   context: Optional[Dict[str, Any]],
                                   language: str) -> str:
        """
        用上下文增强查询
        
        Args:
            question: 原始问题
            context: 上下文信息
            language: 目标语言
            
        Returns:
            增强后的查询
        """
        enhanced = question
        
        # 添加语言信息
        if language != "zh-CN":
            enhanced += f" (请用{language}回答)"
        
        # 添加上下文相关关键词
        if context:
            # 行业上下文
            if "industry" in context:
                enhanced += f" 行业:{context['industry']}"
            
            # 地区上下文
            if "region" in context:
                enhanced += f" 地区:{context['region']}"
            
            # 时间上下文
            if "time_range" in context:
                enhanced += f" 时间范围:{context['time_range']}"
            
            # 产品上下文
            if "product" in context:
                enhanced += f" 产品:{context['product']}"
        
        # 添加SellAI特定查询策略
        enhanced += """
        请基于知识库事实回答，确保信息准确可靠。
        如果知识库中没有相关信息，请明确说明。
        优先使用最新数据，并注明数据来源和时间。
        """
        
        return enhanced
    
    def _generate_answer_from_knowledge(self, question: str,
                                       knowledge_result: Dict[str, Any],
                                       context: Optional[Dict[str, Any]],
                                       language: str) -> Tuple[str, Dict[str, Any]]:
        """
        从知识结果生成回答
        
        Args:
            question: 原始问题
            knowledge_result: 知识库查询结果
            context: 上下文信息
            language: 目标语言
            
        Returns:
            (回答文本, 元数据)
        """
        answers = knowledge_result.get("answers", [])
        sources = knowledge_result.get("sources", [])
        
        if not answers:
            # 没有找到相关知识
            answer = self._generate_no_knowledge_answer(question, language)
            
            metadata = {
                "has_knowledge": False,
                "sources_count": 0,
                "answer_type": "no_knowledge"
            }
            
            return answer, metadata
        
        # 提取主要答案
        primary_answer = self._extract_primary_answer(answers, question)
        
        # 构建完整回答
        answer_parts = []
        
        # 1. 直接回答
        answer_parts.append(primary_answer["content"])
        
        # 2. 补充信息（如果有）
        supplementary_info = self._extract_supplementary_info(answers, primary_answer)
        if supplementary_info:
            answer_parts.append("\n补充信息:")
            for info in supplementary_info[:3]:  # 限制前3条补充信息
                answer_parts.append(f"- {info}")
        
        # 3. 来源说明
        if sources:
            answer_parts.append("\n信息来源:")
            for i, source in enumerate(sources[:3]):  # 限制前3个来源
                title = source.get("title", "未知来源")
                relevance = source.get("relevance", 0.0)
                answer_parts.append(f"{i+1}. {title} (相关性: {relevance:.2f})")
        
        # 4. 置信度说明
        avg_confidence = sum(a.get("confidence", 0.5) for a in answers) / len(answers)
        if avg_confidence < self.min_confidence_threshold:
            answer_parts.append(f"\n注意: 此回答的置信度较低 ({avg_confidence:.2f})，建议进一步核实。")
        
        # 合并回答
        full_answer = "\n".join(answer_parts)
        
        # 生成元数据
        metadata = {
            "has_knowledge": True,
            "answers_count": len(answers),
            "sources_count": len(sources),
            "primary_answer_confidence": primary_answer.get("confidence", 0.5),
            "average_confidence": avg_confidence,
            "answer_type": "knowledge_based",
            "language": language,
            "extraction_method": "notebook_lm_query"
        }
        
        return full_answer, metadata
    
    def _generate_no_knowledge_answer(self, question: str, language: str) -> str:
        """
        生成无知识时的回答
        
        Args:
            question: 问题
            language: 目标语言
            
        Returns:
            无知识时的标准回答
        """
        if language == "zh-CN":
            return f"抱歉，我的知识库中没有关于'{question}'的准确信息。\n\n建议：\n1. 提供更多背景信息\n2. 检查问题表述是否准确\n3. 联系相关业务部门获取最新数据"
        elif language == "en":
            return f"I'm sorry, I don't have accurate information about '{question}' in my knowledge base.\n\nSuggestions:\n1. Provide more context\n2. Check if the question is accurately phrased\n3. Contact relevant business departments for the latest data"
        else:
            return f"Knowledge base does not contain information about '{question}'."
    
    def _extract_primary_answer(self, answers: List[Dict[str, Any]], 
                               question: str) -> Dict[str, Any]:
        """
        提取主要答案
        
        Args:
            answers: 答案列表
            question: 原始问题
            
        Returns:
            主要答案
        """
        if not answers:
            return {"content": "无相关信息", "confidence": 0.0}
        
        # 基于置信度排序
        sorted_answers = sorted(answers, key=lambda x: x.get("confidence", 0.5), reverse=True)
        
        # 返回置信度最高的答案
        primary = sorted_answers[0]
        
        # 确保答案格式
        if isinstance(primary, str):
            return {"content": primary, "confidence": 0.5}
        
        return primary
    
    def _extract_supplementary_info(self, answers: List[Dict[str, Any]],
                                   primary_answer: Dict[str, Any]) -> List[str]:
        """
        提取补充信息
        
        Args:
            answers: 答案列表
            primary_answer: 主要答案
            
        Returns:
            补充信息列表
        """
        supplementary = []
        
        for answer in answers[1:]:  # 跳过主要答案
            if isinstance(answer, dict) and "content" in answer:
                content = answer["content"]
                # 提取关键信息（简化实现）
                if len(content) > 50 and len(content) < 500:
                    supplementary.append(content[:200] + "...")
        
        return supplementary[:5]  # 限制5条补充信息
    
    def _adjust_answer_for_fact_check(self, original_answer: str,
                                     fact_check_result: Dict[str, Any],
                                     question: str,
                                     language: str) -> str:
        """
        根据事实核查调整回答
        
        Args:
            original_answer: 原始回答
            fact_check_result: 事实核查结果
            question: 原始问题
            language: 目标语言
            
        Returns:
            调整后的回答
        """
        issues = fact_check_result.get("issues", [])
        
        if language == "zh-CN":
            adjusted = f"关于'{question}'，基于当前核查发现以下问题:\n"
            for i, issue in enumerate(issues[:3]):  # 限制前3个问题
                adjusted += f"{i+1}. {issue}\n"
            
            adjusted += "\n原回答中存在不确定信息，建议:\n"
            adjusted += "1. 联系业务部门核实最新数据\n"
            adjusted += "2. 查看官方文档获取准确信息\n"
            adjusted += "3. 等待知识库更新后再查询"
            
            return adjusted
        else:
            return f"Fact check identified issues with the original answer. Please verify with reliable sources."
    
    def _format_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化来源信息
        
        Args:
            sources: 原始来源列表
            
        Returns:
            格式化后的来源列表
        """
        formatted = []
        
        for source in sources[:5]:  # 限制前5个来源
            formatted.append({
                "title": source.get("title", "未知来源"),
                "type": source.get("type", "document"),
                "relevance": source.get("relevance", 0.0),
                "date": source.get("date", ""),
                "url": source.get("url", "")
            })
        
        return formatted
    
    def _get_cache_key(self, question: str, 
                      context: Optional[Dict[str, Any]],
                      language: str) -> str:
        """
        获取缓存键
        
        Args:
            question: 问题
            context: 上下文
            language: 语言
            
        Returns:
            缓存键
        """
        # 基于问题、上下文和语言生成唯一键
        context_str = json.dumps(context, sort_keys=True) if context else ""
        input_str = f"{question}||{context_str}||{language}"
        
        return hashlib.md5(input_str.encode()).hexdigest()[:16]
    
    def _clean_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self.qa_cache.items()
            if current_time - data["timestamp"] > 3600  # 1小时过期
        ]
        
        for key in expired_keys:
            del self.qa_cache[key]
        
        if expired_keys:
            logger.debug(f"清理 {len(expired_keys)} 个过期问答缓存")


class FactChecker:
    """事实核查器"""
    
    def __init__(self):
        """初始化事实核查器"""
        self.supported_domains = [
            "business_intelligence",
            "market_data", 
            "technical_specifications",
            "brand_standards",
            "regulatory_compliance"
        ]
        
        logger.info("事实核查器初始化完成")
    
    def check_factuality(self, answer: str,
                        question: str,
                        sources: List[Dict[str, Any]],
                        context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        检查事实性
        
        Args:
            answer: 待核查回答
            question: 原始问题
            sources: 来源列表
            context: 上下文
            
        Returns:
            事实核查结果
        """
        try:
            issues = []
            warnings = []
            verification_sources = []
            
            # 1. 检查来源可信度
            source_issues = self._check_source_credibility(sources)
            if source_issues:
                issues.extend(source_issues)
            
            # 2. 检查内容一致性
            consistency_issues = self._check_content_consistency(answer, sources)
            if consistency_issues:
                issues.extend(consistency_issues)
            
            # 3. 检查时效性
            timeliness_issues = self._check_timeliness(answer, sources, context)
            if timeliness_issues:
                issues.extend(timeliness_issues)
            
            # 4. 提取验证来源
            verification_sources = self._extract_verification_sources(sources)
            
            # 5. 生成总体评估
            overall_assessment = self._generate_overall_assessment(
                issues, warnings, verification_sources
            )
            
            result = {
                "is_factual": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "verification_sources": verification_sources,
                "overall_assessment": overall_assessment,
                "source_count": len(sources),
                "check_time": datetime.now().isoformat()
            }
            
            logger.debug(f"事实核查完成: 问题='{question[:30]}...', 事实性={result['is_factual']}")
            
            return result
            
        except Exception as e:
            logger.error(f"事实核查失败: {str(e)}")
            
            return {
                "is_factual": False,
                "issues": [f"事实核查过程出错: {str(e)}"],
                "warnings": ["事实核查不可用"],
                "verification_sources": [],
                "overall_assessment": "核查失败",
                "source_count": len(sources),
                "check_time": datetime.now().isoformat()
            }
    
    def _check_source_credibility(self, sources: List[Dict[str, Any]]) -> List[str]:
        """检查来源可信度"""
        issues = []
        
        if not sources:
            issues.append("缺少信息来源，无法验证事实性")
            return issues
        
        # 检查来源类型
        credible_source_types = ["official_document", "research_paper", "verified_report"]
        questionable_types = ["social_media", "user_generated", "unverified"]
        
        for source in sources:
            source_type = source.get("type", "").lower()
            
            if source_type in questionable_types:
                issues.append(f"来源类型可信度较低: {source.get('title', '未知')}")
            
            # 检查来源日期
            source_date = source.get("date", "")
            if source_date:
                # 检查是否过时（假设超过2年为过时）
                try:
                    date_obj = datetime.strptime(source_date[:10], "%Y-%m-%d")
                    age_years = (datetime.now() - date_obj).days / 365
                    if age_years > 2:
                        issues.append(f"信息来源可能已过时: {source_date}")
                except:
                    pass
        
        return issues
    
    def _check_content_consistency(self, answer: str, 
                                  sources: List[Dict[str, Any]]) -> List[str]:
        """检查内容一致性"""
        issues = []
        
        if len(sources) < 2:
            # 只有一个来源，无法进行一致性检查
            return issues
        
        # 简化一致性检查：检查关键数据点
        # 实际应用中可以使用更复杂的逻辑
        data_patterns = [
            r"\d+\.?\d*%",  # 百分比
            r"\$\d+\.?\d*",  # 美元金额
            r"\d+\.?\d*\s*(million|billion|trillion)",  # 大数字
            r"\d{4}-\d{2}-\d{2}",  # 日期
        ]
        
        # 提取答案中的关键数据
        answer_data = []
        for pattern in data_patterns:
            matches = re.findall(pattern, answer, re.IGNORECASE)
            answer_data.extend(matches)
        
        if not answer_data:
            # 没有明确数据点，跳过一致性检查
            return issues
        
        # 检查来源中的数据一致性（简化）
        for data_point in answer_data[:3]:  # 检查前3个数据点
            source_with_data = []
            
            for source in sources:
                if "content" in source and data_point in source["content"]:
                    source_with_data.append(source.get("title", "未知"))
            
            if len(source_with_data) == 0:
                issues.append(f"数据点 '{data_point}' 在来源中未找到验证")
            elif len(source_with_data) == 1:
                issues.append(f"数据点 '{data_point}' 仅有一个来源验证")
        
        return issues
    
    def _check_timeliness(self, answer: str,
                         sources: List[Dict[str, Any]],
                         context: Optional[Dict[str, Any]]) -> List[str]:
        """检查时效性"""
        issues = []
        
        # 检查是否有时间敏感关键词
        time_sensitive_keywords = [
            "最近", "最新", "当前", "今年", "本月", "本周",
            "recent", "latest", "current", "this year"
        ]
        
        has_time_sensitive = any(
            keyword in answer.lower() for keyword in time_sensitive_keywords
        )
        
        if not has_time_sensitive:
            return issues
        
        # 检查来源时效性
        recent_sources = 0
        for source in sources:
            source_date = source.get("date", "")
            if source_date:
                try:
                    date_obj = datetime.strptime(source_date[:10], "%Y-%m-%d")
                    # 检查是否在6个月内
                    age_days = (datetime.now() - date_obj).days
                    if age_days <= 180:
                        recent_sources += 1
                except:
                    pass
        
        if recent_sources == 0:
            issues.append("回答包含时效性信息，但所有来源都超过6个月")
        elif recent_sources < 2:
            issues.append("回答包含时效性信息，但近期来源不足")
        
        return issues
    
    def _extract_verification_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取验证来源"""
        verification_sources = []
        
        for source in sources:
            if source.get("relevance", 0.0) > 0.5:  # 相关性阈值
                verification_sources.append({
                    "title": source.get("title", "未知"),
                    "type": source.get("type", "document"),
                    "relevance": source.get("relevance", 0.0),
                    "date": source.get("date", "")
                })
        
        return verification_sources[:5]  # 限制前5个验证来源
    
    def _generate_overall_assessment(self, issues: List[str],
                                    warnings: List[str],
                                    verification_sources: List[Dict[str, Any]]) -> str:
        """生成总体评估"""
        if not issues:
            if verification_sources:
                return "高可信度，有多个来源验证"
            else:
                return "可信度中等，来源验证有限"
        else:
            issue_count = len(issues)
            if issue_count <= 2:
                return f"存在 {issue_count} 个需要关注的问题"
            else:
                return f"存在多个问题，需要谨慎对待"


class ConfidenceAssessor:
    """置信度评估器"""
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        初始化置信度评估器
        
        Args:
            weights: 各评估维度权重
        """
        self.weights = weights or {
            "source_credibility": 0.3,
            "answer_specificity": 0.25,
            "consistency_score": 0.2,
            "timeliness": 0.15,
            "context_relevance": 0.1
        }
        
        logger.info("置信度评估器初始化完成")
    
    def assess_confidence(self, answer: str,
                         knowledge_result: Dict[str, Any],
                         fact_check_result: Optional[Dict[str, Any]],
                         question: str,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        评估回答置信度
        
        Args:
            answer: 回答文本
            knowledge_result: 知识库查询结果
            fact_check_result: 事实核查结果
            question: 原始问题
            context: 上下文
            
        Returns:
            置信度评估结果
        """
        try:
            # 各维度评分
            scores = {}
            
            # 1. 来源可信度
            scores["source_credibility"] = self._assess_source_credibility(
                knowledge_result.get("sources", [])
            )
            
            # 2. 回答具体性
            scores["answer_specificity"] = self._assess_answer_specificity(
                answer, question
            )
            
            # 3. 一致性评分
            scores["consistency_score"] = self._assess_consistency(
                answer, knowledge_result.get("answers", [])
            )
            
            # 4. 时效性
            scores["timeliness"] = self._assess_timeliness(
                knowledge_result.get("sources", []),
                context
            )
            
            # 5. 上下文相关性
            scores["context_relevance"] = self._assess_context_relevance(
                answer, question, context
            )
            
            # 6. 事实核查影响
            if fact_check_result:
                fact_check_impact = self._calculate_fact_check_impact(fact_check_result)
                # 调整来源可信度
                scores["source_credibility"] *= fact_check_impact
            
            # 计算总体置信度
            overall_confidence = self._calculate_overall_confidence(scores)
            
            result = {
                "overall_confidence": overall_confidence,
                "dimension_scores": scores,
                "weights": self.weights.copy(),
                "interpretation": self._interpret_confidence(overall_confidence),
                "assessment_time": datetime.now().isoformat()
            }
            
            logger.debug(f"置信度评估: 总体={overall_confidence:.2f}, 维度={scores}")
            
            return result
            
        except Exception as e:
            logger.error(f"置信度评估失败: {str(e)}")
            
            return {
                "overall_confidence": 0.0,
                "dimension_scores": {},
                "weights": self.weights.copy(),
                "interpretation": "评估失败",
                "assessment_time": datetime.now().isoformat()
            }
    
    def _assess_source_credibility(self, sources: List[Dict[str, Any]]) -> float:
        """评估来源可信度"""
        if not sources:
            return 0.2  # 无来源，极低可信度
        
        credible_types = ["official_document", "research_paper", "verified_report"]
        questionable_types = ["social_media", "user_generated", "unverified"]
        
        credible_count = 0
        total_weight = 0
        
        for source in sources:
            source_type = source.get("type", "").lower()
            relevance = source.get("relevance", 0.5)
            
            if source_type in credible_types:
                credible_count += 1 * relevance
            elif source_type in questionable_types:
                credible_count += 0.3 * relevance  # 可疑类型权重较低
            else:
                credible_count += 0.5 * relevance  # 未知类型中等权重
            
            total_weight += relevance
        
        if total_weight == 0:
            return 0.5
        
        score = credible_count / total_weight
        return max(0.0, min(1.0, score))
    
    def _assess_answer_specificity(self, answer: str, question: str) -> float:
        """评估回答具体性"""
        # 检查回答是否包含具体信息
        specific_indicators = [
            r"\d+",  # 数字
            r"[A-Z]{2,}",  # 大写缩写（如AI、SEO）
            r"\d{4}-\d{2}-\d{2}",  # 日期
            r"\$?\d+\.?\d*\s*(million|billion|trillion|千|万|亿)",  # 金额
        ]
        
        indicator_count = 0
        for pattern in specific_indicators:
            if re.search(pattern, answer):
                indicator_count += 1
        
        # 基于关键词数量评分
        if indicator_count >= 3:
            return 0.9
        elif indicator_count == 2:
            return 0.7
        elif indicator_count == 1:
            return 0.5
        else:
            # 没有具体信息，检查是否是通用回答
            generic_patterns = [
                r"抱歉", r"无法回答", r"没有信息", 
                r"sorry", r"cannot answer", r"no information"
            ]
            
            if any(pattern in answer.lower() for pattern in generic_patterns):
                return 0.3  # 明确表示无信息
            else:
                return 0.4  # 可能是模糊回答
    
    def _assess_consistency(self, answer: str, knowledge_answers: List[Dict[str, Any]]) -> float:
        """评估一致性"""
        if len(knowledge_answers) < 2:
            return 0.5  # 单个来源，无法评估一致性
        
        # 提取答案中的关键实体和数字
        answer_entities = self._extract_entities(answer)
        answer_numbers = self._extract_numbers(answer)
        
        if not answer_entities and not answer_numbers:
            return 0.5  # 没有可验证的信息
        
        # 检查知识库答案的一致性
        entity_consistency = 0.0
        number_consistency = 0.0
        
        for kb_answer in knowledge_answers:
            if "content" in kb_answer:
                content = kb_answer["content"]
                
                # 实体一致性
                kb_entities = self._extract_entities(content)
                if answer_entities:
                    common_entities = set(answer_entities) & set(kb_entities)
                    entity_consistency += len(common_entities) / max(len(answer_entities), 1)
                
                # 数字一致性
                kb_numbers = self._extract_numbers(content)
                if answer_numbers:
                    # 检查相近数字（允许10%误差）
                    matching_numbers = 0
                    for ans_num in answer_numbers:
                        for kb_num in kb_numbers:
                            if abs(ans_num - kb_num) / max(abs(ans_num), 1) < 0.1:
                                matching_numbers += 1
                                break
                    
                    number_consistency += matching_numbers / max(len(answer_numbers), 1)
        
        # 计算平均一致性
        if knowledge_answers:
            entity_consistency /= len(knowledge_answers)
            number_consistency /= len(knowledge_answers)
        
        overall_consistency = (entity_consistency + number_consistency) / 2
        
        return max(0.0, min(1.0, overall_consistency))
    
    def _assess_timeliness(self, sources: List[Dict[str, Any]],
                          context: Optional[Dict[str, Any]]) -> float:
        """评估时效性"""
        if not sources:
            return 0.3  # 无来源，时效性未知
        
        # 提取来源日期
        dates = []
        for source in sources:
            date_str = source.get("date", "")
            if date_str:
                try:
                    # 尝试解析日期
                    date_part = date_str[:10]
                    date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                    dates.append(date_obj)
                except:
                    pass
        
        if not dates:
            return 0.5  # 无日期信息
        
        # 计算最新日期
        latest_date = max(dates)
        current_date = datetime.now()
        
        # 计算时间差（年）
        time_diff_years = (current_date - latest_date).days / 365
        
        # 根据时间差评分
        if time_diff_years <= 0.5:  # 6个月内
            return 0.9
        elif time_diff_years <= 1:  # 1年内
            return 0.7
        elif time_diff_years <= 2:  # 2年内
            return 0.5
        elif time_diff_years <= 3:  # 3年内
            return 0.3
        else:  # 超过3年
            return 0.1
    
    def _assess_context_relevance(self, answer: str,
                                 question: str,
                                 context: Optional[Dict[str, Any]]) -> float:
        """评估上下文相关性"""
        if not context:
            return 0.5  # 无上下文，默认中等相关性
        
        # 检查答案中是否包含上下文关键词
        context_keywords = []
        
        # 行业关键词
        if "industry" in context:
            context_keywords.append(context["industry"].lower())
        
        # 地区关键词
        if "region" in context:
            context_keywords.append(context["region"].lower())
        
        # 产品关键词
        if "product" in context:
            context_keywords.append(context["product"].lower())
        
        if not context_keywords:
            return 0.5
        
        # 检查答案中关键词出现情况
        answer_lower = answer.lower()
        keyword_hits = sum(1 for keyword in context_keywords if keyword in answer_lower)
        
        score = keyword_hits / len(context_keywords)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_fact_check_impact(self, fact_check_result: Dict[str, Any]) -> float:
        """计算事实核查影响"""
        is_factual = fact_check_result.get("is_factual", True)
        issues = fact_check_result.get("issues", [])
        
        if is_factual and not issues:
            return 1.0  # 无负面影响
        
        if not is_factual:
            # 有严重问题
            return 0.3
        
        # 有一些问题但不太严重
        issue_count = len(issues)
        if issue_count == 1:
            return 0.8
        elif issue_count == 2:
            return 0.6
        else:
            return 0.4
    
    def _calculate_overall_confidence(self, scores: Dict[str, float]) -> float:
        """计算总体置信度"""
        if not scores:
            return 0.0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for dimension, score in scores.items():
            weight = self.weights.get(dimension, 0.0)
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return sum(scores.values()) / max(len(scores), 1)
        
        return weighted_sum / total_weight
    
    def _interpret_confidence(self, confidence: float) -> str:
        """解释置信度"""
        if confidence >= 0.9:
            return "极高置信度，基于多个可靠来源"
        elif confidence >= 0.8:
            return "高置信度，信息可靠"
        elif confidence >= 0.7:
            return "中等置信度，建议核实"
        elif confidence >= 0.6:
            return "较低置信度，需要谨慎对待"
        else:
            return "低置信度，不建议依赖"
    
    def _extract_entities(self, text: str) -> List[str]:
        """提取实体（简化实现）"""
        # 实际应用中可以使用NLP库
        # 这里提取连续的大写字母序列和特定关键词
        entities = []
        
        # 大写字母序列（缩写）
        uppercase_pattern = r'\b[A-Z]{2,}\b'
        entities.extend(re.findall(uppercase_pattern, text))
        
        # 特定关键词（示例）
        keywords = ["AI", "SellAI", "亚马逊", "TikTok", "Shopify", "SEO", "KPI"]
        for keyword in keywords:
            if keyword.lower() in text.lower():
                entities.append(keyword)
        
        return list(set(entities))  # 去重
    
    def _extract_numbers(self, text: str) -> List[float]:
        """提取数字"""
        numbers = []
        
        # 匹配整数和小数
        number_pattern = r'\b\d+\.?\d*\b'
        matches = re.findall(number_pattern, text)
        
        for match in matches:
            try:
                numbers.append(float(match))
            except:
                pass
        
        return numbers


# 便捷函数
def create_factual_qa_engine(api_key: Optional[str] = None,
                            knowledge_base_id: str = "kb_global_sellai") -> FactualQAEngine:
    """
    创建事实性问答引擎的便捷函数
    
    Args:
        api_key: Notebook LM API密钥
        knowledge_base_id: 知识库ID
        
    Returns:
        事实性问答引擎实例
    """
    from src.notebook_lm_integration import NotebookLMIntegration
    
    nli = NotebookLMIntegration(api_key=api_key)
    engine = FactualQAEngine(nli, knowledge_base_id)
    
    return engine


if __name__ == "__main__":
    # 模块测试
    print("事实性问答引擎模块测试")
    
    # 创建模拟引擎进行测试
    class MockNotebookLMIntegration:
        def query_knowledge_base(self, **kwargs):
            return {
                "answers": [
                    {
                        "content": "测试回答内容，包含具体数据如85%的成功率和2024年最新信息。",
                        "confidence": 0.85
                    }
                ],
                "sources": [
                    {
                        "title": "测试来源文档",
                        "type": "official_document",
                        "relevance": 0.9,
                        "date": "2024-03-15"
                    }
                ]
            }
    
    mock_nli = MockNotebookLMIntegration()
    engine = FactualQAEngine(mock_nli)
    
    # 测试提问
    test_question = "SellAI系统的成功率是多少？"
    result = engine.ask_question(test_question)
    
    print(f"问题: {test_question}")
    print(f"回答: {result['answer'][:100]}...")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"来源数: {len(result['sources'])}")