#!/usr/bin/env python3
"""
知识驱动型分身基类

此模块提供知识驱动型分身的基类实现，确保所有AI分身在执行任务前优先检索Notebook LM知识库，
实现基于全局知识的智能决策和品牌标准对齐。
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Tuple
from abc import ABC, abstractmethod
import hashlib
from dataclasses import dataclass, asdict

# 导入Notebook LM集成
try:
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType,
        create_document_from_task_result
    )
except ImportError:
    # 如果直接运行，使用相对导入
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType,
        create_document_from_task_result
    )


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """任务上下文数据"""
    task_id: str
    task_description: str
    avatar_id: str
    user_id: Optional[str] = None
    priority: int = 1
    deadline: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class KnowledgeRetrievalResult:
    """知识检索结果"""
    query: str
    answers: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    retrieval_time: float
    relevance_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class KnowledgeDrivenAvatar(ABC):
    """
    知识驱动型分身基类
    
    所有SellAI分身应继承此基类，以获得知识驱动的任务执行能力。
    核心特性：
    1. 任务执行前自动检索相关知识
    2. 基于知识库的上下文增强
    3. 任务结果自动归档到知识库
    4. 品牌标准自动对齐检查
    """
    
    def __init__(self, avatar_id: str, avatar_name: str,
                 notebook_lm_integration: NotebookLMIntegration,
                 knowledge_base_id: str = "kb_global_sellai",
                 enable_knowledge_driven: bool = True):
        """
        初始化知识驱动型分身
        
        Args:
            avatar_id: 分身唯一标识
            avatar_name: 分身名称
            notebook_lm_integration: Notebook LM集成实例
            knowledge_base_id: 默认知识库ID
            enable_knowledge_driven: 是否启用知识驱动模式
        """
        self.avatar_id = avatar_id
        self.avatar_name = avatar_name
        self.nli = notebook_lm_integration
        self.knowledge_base_id = knowledge_base_id
        self.enable_knowledge_driven = enable_knowledge_driven
        
        # 知识检索缓存
        self.knowledge_cache = {}
        # 任务执行统计
        self.task_stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "avg_retrieval_time": 0.0,
            "knowledge_hit_rate": 0.0
        }
        
        # 品牌标准检查器（延迟初始化）
        self.brand_enforcer = None
        
        logger.info(f"知识驱动型分身初始化完成: {avatar_name} ({avatar_id})")
    
    def execute_task(self, task_description: str,
                    context: Optional[Dict[str, Any]] = None,
                    task_id: Optional[str] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        执行任务（知识驱动版）
        
        此方法重写原有分身执行逻辑，添加知识检索前置步骤。
        
        Args:
            task_description: 任务描述
            context: 任务上下文
            task_id: 任务ID，如果为None则自动生成
            **kwargs: 其他参数
            
        Returns:
            任务执行结果
        """
        start_time = time.time()
        
        # 生成任务ID
        task_id = task_id or self._generate_task_id(task_description)
        
        # 创建任务上下文
        task_context = TaskContext(
            task_id=task_id,
            task_description=task_description,
            avatar_id=self.avatar_id,
            additional_context=context or {}
        )
        
        logger.info(f"分身 {self.avatar_name} 开始执行任务: {task_id}")
        logger.debug(f"任务描述: {task_description[:200]}...")
        
        try:
            # 步骤1：知识检索（如果启用）
            knowledge_result = None
            if self.enable_knowledge_driven:
                knowledge_result = self._retrieve_relevant_knowledge(
                    task_description, context, task_context
                )
                
                # 更新知识命中率统计
                self._update_knowledge_stats(knowledge_result)
            
            # 步骤2：上下文增强
            enhanced_context = self._enhance_context_with_knowledge(
                context or {}, knowledge_result, task_context
            )
            
            # 步骤3：品牌标准检查（如果适用）
            brand_compliance = True
            compliance_suggestions = None
            if self.enable_knowledge_driven and self._should_check_brand_compliance(task_description):
                brand_compliance, compliance_suggestions = self._check_brand_compliance(
                    task_description, enhanced_context, task_context
                )
                
                if not brand_compliance:
                    logger.warning(f"任务 {task_id} 品牌标准检查未通过")
                    if compliance_suggestions:
                        logger.info(f"改进建议: {compliance_suggestions}")
            
            # 步骤4：执行核心任务逻辑
            task_result = self._execute_core_task(
                task_description=task_description,
                enhanced_context=enhanced_context,
                task_context=task_context,
                knowledge_result=knowledge_result,
                brand_compliance=brand_compliance,
                **kwargs
            )
            
            # 步骤5：结果归档
            if self.enable_knowledge_driven:
                archive_success = self._archive_task_result(
                    task_context=task_context,
                    task_result=task_result,
                    knowledge_result=knowledge_result,
                    brand_compliance=brand_compliance,
                    compliance_suggestions=compliance_suggestions
                )
                
                if archive_success:
                    logger.info(f"任务结果已归档到知识库: {task_id}")
            
            # 步骤6：更新统计
            execution_time = time.time() - start_time
            self._update_task_stats(success=True, execution_time=execution_time)
            
            # 步骤7：构建返回结果
            final_result = {
                "task_id": task_id,
                "avatar_id": self.avatar_id,
                "execution_time": execution_time,
                "success": True,
                "result": task_result,
                "metadata": {
                    "knowledge_retrieved": knowledge_result is not None,
                    "brand_compliance": brand_compliance,
                    "archived": self.enable_knowledge_driven,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            if knowledge_result:
                final_result["knowledge_summary"] = self._summarize_knowledge(knowledge_result)
            
            if compliance_suggestions:
                final_result["brand_suggestions"] = compliance_suggestions
            
            logger.info(f"任务执行成功: {task_id} (耗时: {execution_time:.2f}秒)")
            return final_result
            
        except Exception as e:
            # 异常处理
            execution_time = time.time() - start_time
            self._update_task_stats(success=False, execution_time=execution_time)
            
            error_result = {
                "task_id": task_id,
                "avatar_id": self.avatar_id,
                "execution_time": execution_time,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "knowledge_driven": self.enable_knowledge_driven
                }
            }
            
            logger.error(f"任务执行失败: {task_id}, 错误: {str(e)}")
            
            # 尝试归档错误信息
            if self.enable_knowledge_driven:
                try:
                    error_doc = self._create_error_document(task_context, str(e))
                    self.nli.add_document(
                        knowledge_base_id=self.knowledge_base_id,
                        document=error_doc
                    )
                except Exception as archive_error:
                    logger.error(f"错误信息归档失败: {str(archive_error)}")
            
            return error_result
    
    def _retrieve_relevant_knowledge(self, task_description: str,
                                    context: Optional[Dict[str, Any]],
                                    task_context: TaskContext) -> Optional[KnowledgeRetrievalResult]:
        """
        检索相关知识
        
        Args:
            task_description: 任务描述
            context: 任务上下文
            task_context: 任务上下文对象
            
        Returns:
            知识检索结果，如果失败则返回None
        """
        start_time = time.time()
        
        try:
            # 构建查询
            query = self._build_knowledge_query(task_description, context, task_context)
            
            # 检查缓存
            cache_key = self._get_knowledge_cache_key(query)
            if cache_key in self.knowledge_cache:
                cached_result = self.knowledge_cache[cache_key]
                # 检查缓存时效（默认5分钟）
                if time.time() - cached_result["timestamp"] < 300:
                    logger.debug(f"知识缓存命中: {query[:100]}...")
                    return KnowledgeRetrievalResult(
                        query=query,
                        answers=cached_result["answers"],
                        sources=cached_result["sources"],
                        retrieval_time=time.time() - start_time,
                        relevance_score=cached_result["relevance_score"]
                    )
            
            # 调用Notebook LM API
            api_result = self.nli.query_knowledge_base(
                knowledge_base_id=self.knowledge_base_id,
                question=query,
                context=context.get("knowledge_context") if context else None,
                max_results=5,
                include_sources=True
            )
            
            # 解析结果
            answers = api_result.get("answers", [])
            sources = api_result.get("sources", [])
            
            # 计算相关性评分
            relevance_score = self._calculate_relevance_score(
                answers, task_description, context
            )
            
            result = KnowledgeRetrievalResult(
                query=query,
                answers=answers,
                sources=sources,
                retrieval_time=time.time() - start_time,
                relevance_score=relevance_score
            )
            
            # 更新缓存
            self.knowledge_cache[cache_key] = {
                "answers": answers,
                "sources": sources,
                "relevance_score": relevance_score,
                "timestamp": time.time()
            }
            
            # 清理过期缓存（超过1小时）
            self._clean_expired_cache()
            
            logger.info(f"知识检索完成: 找到 {len(answers)} 个答案，相关性评分: {relevance_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"知识检索失败: {str(e)}")
            return None
    
    def _build_knowledge_query(self, task_description: str,
                              context: Optional[Dict[str, Any]],
                              task_context: TaskContext) -> str:
        """
        构建知识查询
        
        Args:
            task_description: 任务描述
            context: 任务上下文
            task_context: 任务上下文对象
            
        Returns:
            优化后的查询语句
        """
        # 基础查询
        query = f"""
        任务类型: AI分身执行任务
        任务描述: {task_description}
        
        请从知识库中检索以下信息：
        1. 类似历史任务的最佳实践和结果
        2. 相关市场情报和行业趋势
        3. 品牌标准和规范要求
        4. 技术约束和架构限制
        """
        
        # 添加上下文信息
        if context:
            if "industry" in context:
                query += f"\n行业领域: {context['industry']}"
            if "region" in context:
                query += f"\n目标地区: {context['region']}"
            if "product_type" in context:
                query += f"\n产品类型: {context['product_type']}"
        
        # 添加分身信息
        query += f"\n执行分身: {self.avatar_name} ({self.avatar_id})"
        
        return query.strip()
    
    def _enhance_context_with_knowledge(self, context: Dict[str, Any],
                                        knowledge_result: Optional[KnowledgeRetrievalResult],
                                        task_context: TaskContext) -> Dict[str, Any]:
        """
        用知识增强上下文
        
        Args:
            context: 原始上下文
            knowledge_result: 知识检索结果
            task_context: 任务上下文对象
            
        Returns:
            增强后的上下文
        """
        enhanced = context.copy()
        
        if knowledge_result and knowledge_result.answers:
            # 提取关键知识
            key_insights = []
            relevant_data = []
            
            for answer in knowledge_result.answers:
                if "content" in answer:
                    # 提取摘要
                    insight = self._extract_insight_from_answer(answer["content"])
                    if insight:
                        key_insights.append(insight)
                    
                    # 提取数据
                    data = self._extract_data_from_answer(answer["content"])
                    if data:
                        relevant_data.append(data)
            
            # 添加到上下文
            if key_insights:
                enhanced["knowledge_insights"] = key_insights
            
            if relevant_data:
                enhanced["knowledge_data"] = relevant_data
            
            # 添加来源信息
            enhanced["knowledge_sources"] = [
                {"title": source.get("title", "未知"), "relevance": source.get("relevance", 0.0)}
                for source in knowledge_result.sources
            ]
        
        return enhanced
    
    def _check_brand_compliance(self, task_description: str,
                               enhanced_context: Dict[str, Any],
                               task_context: TaskContext) -> Tuple[bool, Optional[str]]:
        """
        检查品牌标准合规性
        
        Args:
            task_description: 任务描述
            enhanced_context: 增强后的上下文
            task_context: 任务上下文对象
            
        Returns:
            (是否合规, 改进建议)
        """
        try:
            # 延迟初始化品牌标准执行器
            if self.brand_enforcer is None:
                self.brand_enforcer = BrandStandardEnforcer(self.nli)
            
            # 检查内容类型
            content_type = self._determine_content_type(task_description, enhanced_context)
            
            # 调用品牌标准检查
            compliance, suggestions = self.brand_enforcer.check_content_compliance(
                content=task_description,
                content_type=content_type,
                context=enhanced_context
            )
            
            if compliance:
                logger.debug(f"品牌标准检查通过: {task_context.task_id}")
            else:
                logger.warning(f"品牌标准检查未通过: {task_context.task_id}")
                if suggestions:
                    logger.info(f"改进建议: {suggestions}")
            
            return compliance, suggestions
            
        except Exception as e:
            logger.error(f"品牌标准检查失败: {str(e)}")
            # 检查失败时默认通过，避免阻塞任务执行
            return True, None
    
    def _archive_task_result(self, task_context: TaskContext,
                            task_result: Dict[str, Any],
                            knowledge_result: Optional[KnowledgeRetrievalResult],
                            brand_compliance: bool,
                            compliance_suggestions: Optional[str]) -> bool:
        """
        归档任务结果到知识库
        
        Args:
            task_context: 任务上下文
            task_result: 任务结果
            knowledge_result: 知识检索结果
            brand_compliance: 品牌合规性
            compliance_suggestions: 合规改进建议
            
        Returns:
            是否归档成功
        """
        try:
            # 创建知识文档
            document = create_document_from_task_result(
                task_id=task_context.task_id,
                task_description=task_context.task_description,
                task_result=json.dumps(task_result, ensure_ascii=False, indent=2),
                avatar_id=self.avatar_id,
                additional_tags=[
                    f"avatar_{self.avatar_id}",
                    f"priority_{task_context.priority}",
                    "knowledge_driven"
                ]
            )
            
            # 添加知识引用信息
            if knowledge_result:
                knowledge_refs = []
                for answer in knowledge_result.answers:
                    if "content" in answer:
                        ref = {
                            "summary": self._extract_insight_from_answer(answer["content"]),
                            "relevance": answer.get("confidence", 0.5)
                        }
                        knowledge_refs.append(ref)
                
                if knowledge_refs:
                    document.metadata["knowledge_references"] = knowledge_refs
            
            # 添加品牌合规信息
            document.metadata["brand_compliance"] = brand_compliance
            if compliance_suggestions:
                document.metadata["brand_suggestions"] = compliance_suggestions
            
            # 添加到知识库
            doc_id = self.nli.add_document(
                knowledge_base_id=self.knowledge_base_id,
                document=document
            )
            
            logger.info(f"任务结果归档成功: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"任务结果归档失败: {str(e)}")
            return False
    
    def _generate_task_id(self, task_description: str) -> str:
        """
        生成任务ID
        
        Args:
            task_description: 任务描述
            
        Returns:
            任务ID
        """
        # 使用哈希生成唯一ID
        hash_input = f"{self.avatar_id}_{task_description}_{time.time()}".encode('utf-8')
        return f"task_{hashlib.md5(hash_input).hexdigest()[:12]}"
    
    def _get_knowledge_cache_key(self, query: str) -> str:
        """
        获取知识缓存键
        
        Args:
            query: 查询语句
            
        Returns:
            缓存键
        """
        return hashlib.md5(query.encode('utf-8')).hexdigest()[:16]
    
    def _calculate_relevance_score(self, answers: List[Dict[str, Any]],
                                  task_description: str,
                                  context: Optional[Dict[str, Any]]) -> float:
        """
        计算知识相关性评分
        
        Args:
            answers: 答案列表
            task_description: 任务描述
            context: 上下文
            
        Returns:
            相关性评分 (0.0-1.0)
        """
        if not answers:
            return 0.0
        
        # 基于答案置信度计算平均相关性
        total_score = 0.0
        valid_answers = 0
        
        for answer in answers:
            confidence = answer.get("confidence", 0.5)
            # 调整置信度为0-1范围
            adjusted_confidence = max(0.0, min(1.0, confidence))
            
            total_score += adjusted_confidence
            valid_answers += 1
        
        if valid_answers > 0:
            return total_score / valid_answers
        
        return 0.0
    
    def _extract_insight_from_answer(self, answer_content: str) -> Optional[str]:
        """
        从答案内容提取关键洞察
        
        Args:
            answer_content: 答案内容
            
        Returns:
            关键洞察摘要
        """
        # 简化实现：提取前200个字符
        if len(answer_content) > 200:
            return answer_content[:197] + "..."
        return answer_content
    
    def _extract_data_from_answer(self, answer_content: str) -> Optional[Dict[str, Any]]:
        """
        从答案内容提取结构化数据
        
        Args:
            answer_content: 答案内容
            
        Returns:
            结构化数据
        """
        # 简化实现：返回基本元数据
        return {
            "content_length": len(answer_content),
            "has_data": any(keyword in answer_content.lower() 
                          for keyword in ["data", "figure", "statistic", "percentage"])
        }
    
    def _summarize_knowledge(self, knowledge_result: KnowledgeRetrievalResult) -> str:
        """
        总结知识检索结果
        
        Args:
            knowledge_result: 知识检索结果
            
        Returns:
            知识摘要
        """
        if not knowledge_result.answers:
            return "无相关知识"
        
        summary = f"检索到 {len(knowledge_result.answers)} 个相关知识点，"
        summary += f"平均相关性: {knowledge_result.relevance_score:.2f}"
        
        return summary
    
    def _create_error_document(self, task_context: TaskContext, error_message: str) -> KnowledgeDocument:
        """
        创建错误文档
        
        Args:
            task_context: 任务上下文
            error_message: 错误信息
            
        Returns:
            错误知识文档
        """
        content = f"""
# 任务执行错误记录

## 任务信息
- **任务ID**: {task_context.task_id}
- **执行分身**: {self.avatar_name} ({self.avatar_id})
- **失败时间**: {datetime.now().isoformat()}
- **任务描述**: {task_context.task_description}

## 错误详情
{error_message}

## 上下文信息
{json.dumps(task_context.additional_context or {}, ensure_ascii=False, indent=2)}

## 建议措施
1. 检查任务输入格式和内容
2. 验证相关依赖和服务状态
3. 查看系统日志获取更多信息
"""
        
        return KnowledgeDocument(
            title=f"任务错误记录_{task_context.task_id}",
            content=content,
            content_type=ContentType.MARKDOWN,
            source_type=SourceType.SYSTEM_LOG,
            source_id=task_context.task_id,
            tags=["error_record", "task_failure", "debug_info"],
            metadata={
                "avatar_id": self.avatar_id,
                "error_type": "execution_error",
                "recorded_at": datetime.now().isoformat()
            }
        )
    
    def _should_check_brand_compliance(self, task_description: str) -> bool:
        """
        判断是否需要检查品牌标准
        
        Args:
            task_description: 任务描述
            
        Returns:
            是否需要检查品牌标准
        """
        # 根据任务类型判断
        content_types_to_check = [
            "marketing_copy", "product_description", "social_media_post",
            "email_template", "advertisement", "brand_content"
        ]
        
        # 检查任务描述中是否包含相关内容
        description_lower = task_description.lower()
        content_keywords = [
            "文案", "广告", "宣传", "营销", "品牌", "内容",
            "copy", "ad", "promotion", "marketing", "brand", "content"
        ]
        
        return any(keyword in description_lower for keyword in content_keywords)
    
    def _determine_content_type(self, task_description: str, context: Dict[str, Any]) -> str:
        """
        确定内容类型
        
        Args:
            task_description: 任务描述
            context: 上下文
            
        Returns:
            内容类型标识
        """
        # 基于任务描述和上下文判断
        description_lower = task_description.lower()
        
        if any(keyword in description_lower for keyword in ["广告", "advertisement", "ad"]):
            return "advertisement"
        elif any(keyword in description_lower for keyword in ["社交", "social", "post"]):
            return "social_media_post"
        elif any(keyword in description_lower for keyword in ["邮件", "email"]):
            return "email_template"
        elif any(keyword in description_lower for keyword in ["产品描述", "product description"]):
            return "product_description"
        else:
            return "general_content"
    
    def _update_knowledge_stats(self, knowledge_result: Optional[KnowledgeRetrievalResult]) -> None:
        """
        更新知识检索统计
        
        Args:
            knowledge_result: 知识检索结果
        """
        if knowledge_result:
            # 更新平均检索时间
            total_time = self.task_stats["avg_retrieval_time"] * self.task_stats["total_tasks"]
            total_time += knowledge_result.retrieval_time
            self.task_stats["total_tasks"] += 1
            self.task_stats["avg_retrieval_time"] = total_time / self.task_stats["total_tasks"]
            
            # 更新知识命中率
            if knowledge_result.answers:
                self.task_stats["knowledge_hit_rate"] = (
                    self.task_stats["knowledge_hit_rate"] * (self.task_stats["total_tasks"] - 1) + 1
                ) / self.task_stats["total_tasks"]
            else:
                self.task_stats["knowledge_hit_rate"] = (
                    self.task_stats["knowledge_hit_rate"] * (self.task_stats["total_tasks"] - 1)
                ) / self.task_stats["total_tasks"]
    
    def _update_task_stats(self, success: bool, execution_time: float) -> None:
        """
        更新任务执行统计
        
        Args:
            success: 是否成功
            execution_time: 执行时间
        """
        if success:
            self.task_stats["successful_tasks"] += 1
    
    def _clean_expired_cache(self) -> None:
        """
        清理过期缓存
        """
        current_time = time.time()
        expired_keys = [
            key for key, data in self.knowledge_cache.items()
            if current_time - data["timestamp"] > 3600  # 1小时过期
        ]
        
        for key in expired_keys:
            del self.knowledge_cache[key]
        
        if expired_keys:
            logger.debug(f"清理 {len(expired_keys)} 个过期缓存")
    
    @abstractmethod
    def _execute_core_task(self, task_description: str,
                          enhanced_context: Dict[str, Any],
                          task_context: TaskContext,
                          knowledge_result: Optional[KnowledgeRetrievalResult],
                          brand_compliance: bool,
                          **kwargs) -> Dict[str, Any]:
        """
        执行核心任务逻辑（抽象方法）
        
        具体分身需要实现此方法，定义其核心业务逻辑。
        
        Args:
            task_description: 任务描述
            enhanced_context: 增强后的上下文
            task_context: 任务上下文对象
            knowledge_result: 知识检索结果
            brand_compliance: 品牌合规性
            **kwargs: 其他参数
            
        Returns:
            任务执行结果
        """
        pass
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """
        获取任务执行统计
        
        Returns:
            任务统计信息
        """
        return self.task_stats.copy()
    
    def clear_knowledge_cache(self) -> None:
        """
        清空知识缓存
        """
        self.knowledge_cache.clear()
        logger.info("知识缓存已清空")
    
    def set_knowledge_base(self, knowledge_base_id: str) -> None:
        """
        设置知识库ID
        
        Args:
            knowledge_base_id: 知识库ID
        """
        self.knowledge_base_id = knowledge_base_id
        logger.info(f"知识库已设置为: {knowledge_base_id}")


# 品牌标准执行器
class BrandStandardEnforcer:
    """
    品牌标准执行器
    
    负责检查内容是否符合SellAI品牌标准，确保所有分身输出内容保持品牌一致性。
    """
    
    def __init__(self, notebook_lm_integration: NotebookLMIntegration):
        """
        初始化品牌标准执行器
        
        Args:
            notebook_lm_integration: Notebook LM集成实例
        """
        self.nli = notebook_lm_integration
        self.brand_standards = None
        
        logger.info("品牌标准执行器初始化完成")
    
    def load_brand_standards(self) -> Dict[str, Any]:
        """
        加载品牌标准
        
        从Notebook LM知识库加载品牌标准配置。
        
        Returns:
            品牌标准配置
        """
        try:
            # 从知识库查询品牌标准
            result = self.nli.query_knowledge_base(
                knowledge_base_id="kb_brand_standards",
                question="查询SellAI品牌标准，包括VI规范、文案模板、视觉风格、多语种指南",
                max_results=10,
                include_sources=True
            )
            
            # 解析品牌标准
            standards = {}
            for answer in result.get("answers", []):
                content = answer.get("content", "")
                # 解析内容中的品牌标准（简化实现）
                if "VI规范" in content or "visual identity" in content.lower():
                    standards["vi_guidelines"] = self._extract_guidelines(content)
                elif "文案模板" in content or "copy template" in content.lower():
                    standards["copy_templates"] = self._extract_templates(content)
                elif "视觉风格" in content or "visual style" in content.lower():
                    standards["visual_styles"] = self._extract_styles(content)
                elif "多语种" in content or "multilingual" in content.lower():
                    standards["multilingual_guides"] = self._extract_guides(content)
            
            self.brand_standards = standards
            logger.info(f"加载品牌标准完成，包含 {len(standards)} 个类别")
            
            return standards
            
        except Exception as e:
            logger.error(f"加载品牌标准失败: {str(e)}")
            # 返回默认标准
            return self._get_default_standards()
    
    def check_content_compliance(self, content: str,
                                content_type: str,
                                context: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        检查内容合规性
        
        Args:
            content: 待检查内容
            content_type: 内容类型（marketing_copy, product_description等）
            context: 上下文信息
            
        Returns:
            (是否合规, 改进建议)
        """
        # 确保品牌标准已加载
        if self.brand_standards is None:
            self.load_brand_standards()
        
        violations = []
        
        # 1. 检查VI规范
        vi_compliant, vi_suggestions = self._check_vi_compliance(content, content_type)
        if not vi_compliant:
            violations.append("VI规范不符合")
            if vi_suggestions:
                violations[-1] += f": {vi_suggestions}"
        
        # 2. 检查品牌语调
        tone_compliant, tone_suggestions = self._check_brand_tone(content, content_type)
        if not tone_compliant:
            violations.append("品牌语调不一致")
            if tone_suggestions:
                violations[-1] += f": {tone_suggestions}"
        
        # 3. 检查多语种标准（如果适用）
        if context and context.get("target_language"):
            language_compliant, language_suggestions = self._check_language_compliance(
                content, content_type, context["target_language"]
            )
            if not language_compliant:
                violations.append(f"语言标准不符合 ({context['target_language']})")
                if language_suggestions:
                    violations[-1] += f": {language_suggestions}"
        
        if violations:
            suggestions = self._generate_compliance_suggestions(content, violations, content_type)
            return False, suggestions
        else:
            return True, None
    
    def _check_vi_compliance(self, content: str, content_type: str) -> Tuple[bool, Optional[str]]:
        """
        检查VI规范合规性
        
        Args:
            content: 内容
            content_type: 内容类型
            
        Returns:
            (是否合规, 改进建议)
        """
        # 简化实现：检查基本品牌元素
        brand_keywords = ["SellAI", "AI合伙人", "智能系统"]
        required_keywords = []
        
        # 根据内容类型确定必要关键词
        if content_type == "marketing_copy":
            required_keywords = ["智能", "高效", "专业"]
        elif content_type == "product_description":
            required_keywords = ["创新", "可靠", "领先"]
        
        # 检查必要关键词
        missing_keywords = []
        for keyword in required_keywords:
            if keyword not in content:
                missing_keywords.append(keyword)
        
        if missing_keywords:
            return False, f"建议添加以下关键词: {', '.join(missing_keywords)}"
        
        # 检查品牌关键词出现频率
        brand_count = sum(1 for keyword in brand_keywords if keyword in content)
        if brand_count == 0 and content_type in ["marketing_copy", "brand_content"]:
            return False, "建议至少包含一个品牌关键词（如SellAI、AI合伙人）"
        
        return True, None
    
    def _check_brand_tone(self, content: str, content_type: str) -> Tuple[bool, Optional[str]]:
        """
        检查品牌语调
        
        Args:
            content: 内容
            content_type: 内容类型
            
        Returns:
            (是否合规, 改进建议)
        """
        # 简化实现：检查语调特征
        professional_keywords = ["系统", "方案", "优化", "效率", "性能"]
        friendly_keywords = ["您", "我们", "一起", "体验", "支持"]
        
        # 分析内容语调
        professional_count = sum(1 for keyword in professional_keywords if keyword in content)
        friendly_count = sum(1 for keyword in friendly_keywords if keyword in content)
        
        # 根据内容类型确定语调要求
        if content_type in ["marketing_copy", "social_media_post"]:
            # 营销内容需要友好和专业平衡
            if friendly_count < 2:
                return False, "营销内容建议使用更友好的语调，增加'您'、'我们'等人称代词"
        elif content_type == "product_description":
            # 产品描述需要专业
            if professional_count < 3:
                return False, "产品描述建议使用更专业的语调，增加技术术语和性能描述"
        
        return True, None
    
    def _check_language_compliance(self, content: str, content_type: str, 
                                  target_language: str) -> Tuple[bool, Optional[str]]:
        """
        检查多语种标准
        
        Args:
            content: 内容
            content_type: 内容类型
            target_language: 目标语言
            
        Returns:
            (是否合规, 改进建议)
        """
        # 简化实现：根据目标语言检查基本合规性
        language_checks = {
            "en": {
                "required": ["AI", "system", "solution"],
                "avoid": ["Chinglish", "grammar error"]
            },
            "ja": {
                "required": ["AI", "システム", "ソリューション"],
                "avoid": ["誤訳", "不自然な表現"]
            },
            "ko": {
                "required": ["AI", "시스템", "솔루션"],
                "avoid": ["오역", "부자연스러운 표현"]
            }
        }
        
        if target_language in language_checks:
            checks = language_checks[target_language]
            
            # 检查必要词汇
            missing_required = []
            for word in checks["required"]:
                if word.lower() not in content.lower():
                    missing_required.append(word)
            
            if missing_required:
                return False, f"{target_language}内容建议包含以下词汇: {', '.join(missing_required)}"
            
            # 检查应避免的内容（简化）
            for avoid_term in checks["avoid"]:
                if avoid_term in content:
                    return False, f"建议避免使用'{avoid_term}'"
        
        return True, None
    
    def _generate_compliance_suggestions(self, content: str,
                                        violations: List[str],
                                        content_type: str) -> str:
        """
        生成合规性改进建议
        
        Args:
            content: 内容
            violations: 违规项列表
            content_type: 内容类型
            
        Returns:
            改进建议
        """
        suggestions = []
        
        for violation in violations:
            if "VI规范" in violation:
                suggestions.append("1. 添加品牌Logo标识或标准配色")
                suggestions.append("2. 使用品牌标准字体和排版")
            elif "品牌语调" in violation:
                if content_type == "marketing_copy":
                    suggestions.append("3. 增加客户导向的语言，如'为您'、'助力'等")
                elif content_type == "product_description":
                    suggestions.append("4. 使用专业术语和数据支撑描述")
            elif "语言标准" in violation:
                suggestions.append("5. 请使用专业翻译工具或母语审校内容")
        
        # 添加通用建议
        suggestions.append("6. 参考品牌手册中的案例和模板")
        suggestions.append("7. 确保内容准确传达品牌核心价值")
        
        return "\n".join(suggestions)
    
    def _extract_guidelines(self, content: str) -> Dict[str, Any]:
        """提取VI规范"""
        return {
            "summary": "SellAI品牌视觉识别规范",
            "has_details": "Logo" in content or "配色" in content or "字体" in content
        }
    
    def _extract_templates(self, content: str) -> Dict[str, Any]:
        """提取文案模板"""
        return {
            "summary": "标准文案模板库",
            "has_details": "模板" in content or "示例" in content or "框架" in content
        }
    
    def _extract_styles(self, content: str) -> Dict[str, Any]:
        """提取视觉风格"""
        return {
            "summary": "视觉设计风格指南",
            "has_details": "风格" in content or "设计" in content or "视觉" in content
        }
    
    def _extract_guides(self, content: str) -> Dict[str, Any]:
        """提取多语种指南"""
        return {
            "summary": "多语种内容创作指南",
            "has_details": "翻译" in content or "本地化" in content or "语种" in content
        }
    
    def _get_default_standards(self) -> Dict[str, Any]:
        """获取默认品牌标准"""
        return {
            "vi_guidelines": {
                "logo": "SellAI标准Logo",
                "colors": ["#007AFF", "#34C759", "#FF9500"],
                "fonts": ["PingFang SC", "Noto Sans CJK"]
            },
            "copy_templates": {
                "marketing_headline": "[产品/服务]助力[目标用户]实现[核心价值]",
                "product_description": "[产品名称]是[品类定位]，采用[核心技术]，具备[核心功能]，适用于[应用场景]"
            },
            "visual_styles": {
                "minimalist": "极简风格，大量留白，清晰排版",
                "professional": "专业风格，数据图表，结构化展示"
            },
            "multilingual_guides": {
                "en": "使用简洁专业的商务英语",
                "ja": "使用礼貌正式的商业日语",
                "ko": "使用正式专业的商务韩语"
            }
        }


# 使用示例
class ExampleKnowledgeDrivenAvatar(KnowledgeDrivenAvatar):
    """
    示例知识驱动型分身
    
    展示如何继承KnowledgeDrivenAvatar并实现核心任务逻辑。
    """
    
    def __init__(self, avatar_id: str, avatar_name: str,
                 notebook_lm_integration: NotebookLMIntegration):
        super().__init__(avatar_id, avatar_name, notebook_lm_integration)
    
    def _execute_core_task(self, task_description: str,
                          enhanced_context: Dict[str, Any],
                          task_context: TaskContext,
                          knowledge_result: Optional[KnowledgeRetrievalResult],
                          brand_compliance: bool,
                          **kwargs) -> Dict[str, Any]:
        """
        示例核心任务逻辑
        
        具体分身需要根据其专业领域实现此方法。
        """
        logger.info(f"示例分身执行核心任务: {task_description[:100]}...")
        
        # 演示如何利用知识检索结果
        if knowledge_result and knowledge_result.answers:
            logger.info(f"任务基于 {len(knowledge_result.answers)} 个相关知识执行")
        
        # 演示如何利用品牌合规性
        if not brand_compliance:
            logger.warning("任务执行中品牌合规性警告")
        
        # 示例任务结果
        result = {
            "status": "completed",
            "output": f"任务 '{task_description[:50]}...' 已成功执行",
            "metrics": {
                "accuracy": 0.95,
                "efficiency": 0.88,
                "satisfaction": 0.92
            },
            "details": {
                "processed_at": datetime.now().isoformat(),
                "execution_duration": "2.5秒",
                "resources_used": ["CPU", "Memory", "Network"]
            }
        }
        
        return result


if __name__ == "__main__":
    # 模块测试
    print("知识驱动型分身基类测试")
    
    # 创建Notebook LM集成实例（需要配置API密钥）
    api_key = os.getenv("NOTEBOOKLM_API_KEY", "test_key")
    
    # 由于是测试，使用模拟配置
    from unittest.mock import Mock
    
    # 创建模拟的Notebook LM集成
    mock_nli = Mock(spec=NotebookLMIntegration)
    mock_nli.query_knowledge_base.return_value = {
        "answers": [
            {
                "content": "历史数据显示类似任务的成功率为85%，建议采用A方案",
                "confidence": 0.8
            }
        ],
        "sources": [
            {
                "title": "任务历史分析报告_202604",
                "relevance": 0.9
            }
        ]
    }
    
    # 创建示例分身
    example_avatar = ExampleKnowledgeDrivenAvatar(
        avatar_id="avatar_example_001",
        avatar_name="示例知识驱动分身",
        notebook_lm_integration=mock_nli
    )
    
    # 执行示例任务
    print("\n执行示例任务...")
    task_result = example_avatar.execute_task(
        task_description="为新产品'智能AI助手'撰写营销文案",
        context={
            "industry": "科技",
            "region": "中国",
            "target_language": "中文"
        }
    )
    
    print(f"任务ID: {task_result['task_id']}")
    print(f"执行成功: {task_result['success']}")
    print(f"耗时: {task_result['execution_time']:.2f}秒")
    
    if "knowledge_summary" in task_result:
        print(f"知识检索: {task_result['knowledge_summary']}")
    
    # 获取统计信息
    stats = example_avatar.get_task_statistics()
    print(f"\n任务统计:")
    print(f"总任务数: {stats['total_tasks']}")
    print(f"成功率: {stats['successful_tasks']}/{stats['total_tasks']}")
    print(f"平均知识检索时间: {stats['avg_retrieval_time']:.3f}秒")
    print(f"知识命中率: {stats['knowledge_hit_rate']:.2%}")
    
    print("\n模块测试完成")
    print("注意：完整功能需要与真实的Notebook LM服务集成")