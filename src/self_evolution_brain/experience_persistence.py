#!/usr/bin/env python3
"""
经验沉淀模块
将复盘洞察和优化经验写入Notebook LM永久记忆系统
实现长期自主进化
"""

import json
import time
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum

# 尝试导入相关模块
try:
    from src.notebook_lm_integration import NotebookLMIntegration
    HAS_NOTEBOOK_LM = True
except ImportError:
    HAS_NOTEBOOK_LM = False
    logging.warning("notebook_lm_integration 模块未找到，部分功能将受限")

try:
    from src.shared_state_manager import SharedStateManager
    HAS_SHARED_STATE = True
except ImportError:
    HAS_SHARED_STATE = False
    logging.warning("shared_state_manager 模块未找到，部分功能将受限")

logger = logging.getLogger(__name__)


class ExperienceCategory(Enum):
    """经验分类"""
    STRATEGY_INSIGHT = "strategy_insight"       # 策略洞察
    PERFORMANCE_PATTERN = "performance_pattern"  # 绩效模式
    MARKET_TREND = "market_trend"               # 市场趋势
    RISK_LESSON = "risk_lesson"                 # 风险教训
    USER_PREFERENCE = "user_preference"         # 用户偏好
    TECHNOLOGY_ADOPTION = "technology_adoption"  # 技术采纳


@dataclass
class ExperienceEntry:
    """经验条目"""
    experience_id: str
    category: ExperienceCategory
    title: str
    description: str
    content: Dict[str, Any]  # 结构化经验内容
    source_data: Dict[str, Any]  # 原始数据来源
    impact_score: float
    confidence_score: float
    tags: List[str]
    related_experiences: List[str]  # 相关经验ID
    created_at: datetime
    updated_at: datetime
    applied_count: int = 0
    effectiveness_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


@dataclass
class ExperiencePackage:
    """经验包"""
    package_id: str
    package_type: str  # daily_review, strategy_optimization, capability_enhancement
    experiences: List[ExperienceEntry]
    summary: Dict[str, Any]
    generated_at: datetime
    applied_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExperiencePersistence:
    """经验沉淀管理器"""
    
    def __init__(self, config, db_path: str = "data/shared_state/state.db"):
        """
        初始化经验沉淀管理器
        
        Args:
            config: 配置对象
            db_path: 数据库路径
        """
        self.config = config
        self.db_path = db_path
        
        # 初始化组件
        self._init_components()
        
        # 经验库状态
        self.experience_library = {}  # experience_id -> ExperienceEntry
        self.experience_packages = []
        
        logger.info("经验沉淀管理器初始化完成")
    
    def _init_components(self):
        """初始化各功能组件"""
        # Notebook LM集成
        if HAS_NOTEBOOK_LM:
            notebook_config = self.config.experience_persistence.notebook_lm_integration
            self.notebook_lm = NotebookLMIntegration(notebook_config)
        else:
            self.notebook_lm = None
        
        # 共享状态管理器
        if HAS_SHARED_STATE:
            self.state_manager = SharedStateManager(self.db_path)
        else:
            self.state_manager = None
    
    def persist_daily_review_experiences(self, review_report, 
                                       optimization_results: List[Any] = None) -> ExperiencePackage:
        """
        沉淀每日复盘经验
        
        Args:
            review_report: 每日复盘报告
            optimization_results: 优化结果列表（可选）
            
        Returns:
            经验包
        """
        logger.info("开始沉淀每日复盘经验")
        
        experiences = []
        
        try:
            # 1. 从复盘报告中提取经验
            review_experiences = self._extract_experiences_from_review(review_report)
            experiences.extend(review_experiences)
            
            # 2. 从优化结果中提取经验
            if optimization_results:
                optimization_experiences = self._extract_experiences_from_optimizations(optimization_results)
                experiences.extend(optimization_experiences)
            
            # 3. 生成经验包
            package = self._create_experience_package(
                package_type="daily_review",
                experiences=experiences,
                summary=self._generate_experience_summary(experiences, review_report)
            )
            
            # 4. 写入Notebook LM（如果启用）
            if self.config.experience_persistence.notebook_lm_integration.get('enable', False) and self.notebook_lm:
                self._persist_to_notebook_lm(package)
            
            # 5. 保存到本地数据库
            self._save_experiences_to_db(experiences)
            
            # 6. 更新经验库
            for experience in experiences:
                self.experience_library[experience.experience_id] = experience
            
            self.experience_packages.append(package)
            
            logger.info(f"每日复盘经验沉淀完成，共{len(experiences)}条经验")
            
            return package
            
        except Exception as e:
            logger.error(f"沉淀每日复盘经验时出错: {e}")
            
            # 返回空的经验包
            return ExperiencePackage(
                package_id=f"exp_pkg_{int(time.time())}",
                package_type="daily_review",
                experiences=[],
                summary={'error': str(e)},
                generated_at=datetime.now()
            )
    
    def _extract_experiences_from_review(self, review_report) -> List[ExperienceEntry]:
        """从复盘报告中提取经验"""
        experiences = []
        
        try:
            # 1. 从关键洞察中提取经验
            key_insights = getattr(review_report, 'key_insights', [])
            for insight in key_insights:
                experience = self._create_experience_from_insight(insight, review_report)
                if experience:
                    experiences.append(experience)
            
            # 2. 从改进机会中提取经验
            improvement_opportunities = getattr(review_report, 'improvement_opportunities', [])
            for opportunity in improvement_opportunities:
                experience = self._create_experience_from_opportunity(opportunity, review_report)
                if experience:
                    experiences.append(experience)
            
            # 3. 从风险预警中提取经验
            risk_warnings = getattr(review_report, 'risk_warnings', [])
            for warning in risk_warnings:
                experience = self._create_experience_from_warning(warning, review_report)
                if experience:
                    experiences.append(experience)
            
            # 4. 从整体评估中提取经验
            overall_assessment = getattr(review_report, 'overall_assessment', {})
            if overall_assessment:
                experience = self._create_experience_from_assessment(overall_assessment, review_report)
                if experience:
                    experiences.append(experience)
        
        except Exception as e:
            logger.error(f"从复盘报告中提取经验时出错: {e}")
        
        return experiences
    
    def _create_experience_from_insight(self, insight, review_report) -> Optional[ExperienceEntry]:
        """从关键洞察中创建经验条目"""
        try:
            # 确定经验类别
            category = self._determine_category_from_insight(insight)
            
            # 生成经验ID
            experience_id = self._generate_experience_id(insight, review_report)
            
            # 构建经验内容
            experience_content = {
                'insight_type': insight.insight_type,
                'strength': getattr(insight, 'strength', 0),
                'impact': getattr(insight, 'impact_score', 0),
                'supporting_data': getattr(insight, 'supporting_data', []),
                'recommended_actions': getattr(insight, 'recommended_actions', [])
            }
            
            # 创建经验条目
            experience = ExperienceEntry(
                experience_id=experience_id,
                category=category,
                title=f"{insight.insight_type.capitalize()} Insight: {insight.title}",
                description=insight.description,
                content=experience_content,
                source_data={
                    'source_type': 'daily_review_insight',
                    'source_id': insight.insight_id,
                    'source_report': review_report.report_id,
                    'extracted_at': datetime.now().isoformat()
                },
                impact_score=insight.impact_score,
                confidence_score=insight.confidence_score,
                tags=self._generate_tags_from_insight(insight),
                related_experiences=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return experience
            
        except Exception as e:
            logger.error(f"从关键洞察创建经验条目时出错: {e}")
            return None
    
    def _determine_category_from_insight(self, insight) -> ExperienceCategory:
        """根据洞察确定经验类别"""
        dimension = getattr(insight, 'dimension', None)
        if not dimension:
            return ExperienceCategory.STRATEGY_INSIGHT
        
        dimension_value = dimension.value if hasattr(dimension, 'value') else str(dimension)
        
        category_map = {
            'market_trend': ExperienceCategory.MARKET_TREND,
            'business_performance': ExperienceCategory.PERFORMANCE_PATTERN,
            'ai_avatar_effectiveness': ExperienceCategory.TECHNOLOGY_ADOPTION,
            'user_satisfaction': ExperienceCategory.USER_PREFERENCE,
            'risk_exposure': ExperienceCategory.RISK_LESSON
        }
        
        return category_map.get(dimension_value, ExperienceCategory.STRATEGY_INSIGHT)
    
    def _generate_experience_id(self, source_data, review_report) -> str:
        """生成经验ID"""
        # 使用哈希值确保唯一性
        source_str = f"{review_report.report_id}_{time.time()}_{hash(str(source_data)) % 10000}"
        experience_hash = hashlib.md5(source_str.encode()).hexdigest()[:16]
        
        return f"exp_{experience_hash}"
    
    def _generate_tags_from_insight(self, insight) -> List[str]:
        """从洞察生成标签"""
        tags = []
        
        # 维度标签
        dimension = getattr(insight, 'dimension', None)
        if dimension:
            dimension_value = dimension.value if hasattr(dimension, 'value') else str(dimension)
            tags.append(f"dimension:{dimension_value}")
        
        # 洞察类型标签
        insight_type = getattr(insight, 'insight_type', '')
        if insight_type:
            tags.append(f"type:{insight_type}")
        
        # 影响级别标签
        impact_score = getattr(insight, 'impact_score', 0)
        if impact_score >= 0.8:
            tags.append("impact:high")
        elif impact_score >= 0.6:
            tags.append("impact:medium")
        else:
            tags.append("impact:low")
        
        return tags
    
    def _create_experience_from_opportunity(self, opportunity, review_report) -> Optional[ExperienceEntry]:
        """从改进机会中创建经验条目"""
        try:
            # 确定经验类别
            category = ExperienceCategory.STRATEGY_INSIGHT
            
            # 生成经验ID
            experience_id = self._generate_experience_id(opportunity, review_report)
            
            # 构建经验内容
            experience_content = {
                'dimension': opportunity.get('dimension', ''),
                'current_score': opportunity.get('current_score', 0),
                'target_score': opportunity.get('target_score', 0),
                'improvement_needed': opportunity.get('improvement_needed', 0),
                'priority': opportunity.get('priority', 'medium'),
                'expected_impact': opportunity.get('expected_impact', 0),
                'recommended_actions': opportunity.get('recommended_actions', [])
            }
            
            # 创建经验条目
            experience = ExperienceEntry(
                experience_id=experience_id,
                category=category,
                title=f"Improvement Opportunity: {opportunity.get('description', '')}",
                description=f"维度: {opportunity.get('dimension', '')}, "
                          f"当前得分: {opportunity.get('current_score', 0):.2f}, "
                          f"目标得分: {opportunity.get('target_score', 0):.2f}",
                content=experience_content,
                source_data={
                    'source_type': 'improvement_opportunity',
                    'source_id': opportunity.get('opportunity_id', ''),
                    'source_report': review_report.report_id,
                    'extracted_at': datetime.now().isoformat()
                },
                impact_score=opportunity.get('expected_impact', 0.5),
                confidence_score=0.7,
                tags=[
                    f"dimension:{opportunity.get('dimension', '')}",
                    f"priority:{opportunity.get('priority', 'medium')}",
                    "type:improvement_opportunity"
                ],
                related_experiences=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return experience
            
        except Exception as e:
            logger.error(f"从改进机会创建经验条目时出错: {e}")
            return None
    
    def _create_experience_from_warning(self, warning, review_report) -> Optional[ExperienceEntry]:
        """从风险预警中创建经验条目"""
        try:
            # 确定经验类别
            category = ExperienceCategory.RISK_LESSON
            
            # 生成经验ID
            experience_id = self._generate_experience_id(warning, review_report)
            
            # 构建经验内容
            experience_content = {
                'dimension': warning.get('dimension', ''),
                'risk_level': warning.get('risk_level', 'medium'),
                'description': warning.get('description', ''),
                'trigger_factors': warning.get('trigger_factors', []),
                'immediate_actions': warning.get('immediate_actions', []),
                'potential_impact': warning.get('potential_impact', '')
            }
            
            # 创建经验条目
            experience = ExperienceEntry(
                experience_id=experience_id,
                category=category,
                title=f"Risk Warning: {warning.get('description', '')}",
                description=f"风险等级: {warning.get('risk_level', 'medium')}, "
                          f"维度: {warning.get('dimension', '')}",
                content=experience_content,
                source_data={
                    'source_type': 'risk_warning',
                    'source_id': warning.get('warning_id', ''),
                    'source_report': review_report.report_id,
                    'extracted_at': datetime.now().isoformat()
                },
                impact_score=0.8 if warning.get('risk_level') == 'critical' else 0.6,
                confidence_score=0.75,
                tags=[
                    f"dimension:{warning.get('dimension', '')}",
                    f"risk_level:{warning.get('risk_level', 'medium')}",
                    "type:risk_warning"
                ],
                related_experiences=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return experience
            
        except Exception as e:
            logger.error(f"从风险预警创建经验条目时出错: {e}")
            return None
    
    def _create_experience_from_assessment(self, assessment, review_report) -> Optional[ExperienceEntry]:
        """从整体评估中创建经验条目"""
        try:
            # 确定经验类别
            category = ExperienceCategory.PERFORMANCE_PATTERN
            
            # 生成经验ID
            experience_id = self._generate_experience_id(assessment, review_report)
            
            # 构建经验内容
            experience_content = {
                'overall_score': assessment.get('overall_score', 0),
                'performance_level': assessment.get('performance_level', ''),
                'strengths': assessment.get('strengths', []),
                'weaknesses': assessment.get('weaknesses', [])
            }
            
            # 创建经验条目
            experience = ExperienceEntry(
                experience_id=experience_id,
                category=category,
                title=f"Overall Performance Assessment: {assessment.get('performance_level', '')}",
                description=f"综合得分: {assessment.get('overall_score', 0):.2f}, "
                          f"强项: {len(assessment.get('strengths', []))}个, "
                          f"弱项: {len(assessment.get('weaknesses', []))}个",
                content=experience_content,
                source_data={
                    'source_type': 'overall_assessment',
                    'source_report': review_report.report_id,
                    'extracted_at': datetime.now().isoformat()
                },
                impact_score=0.7,
                confidence_score=0.8,
                tags=[
                    "type:overall_assessment",
                    f"level:{assessment.get('performance_level', '').lower()}"
                ],
                related_experiences=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return experience
            
        except Exception as e:
            logger.error(f"从整体评估创建经验条目时出错: {e}")
            return None
    
    def _extract_experiences_from_optimizations(self, optimization_results: List[Any]) -> List[ExperienceEntry]:
        """从优化结果中提取经验"""
        experiences = []
        
        try:
            for optimization in optimization_results:
                experience = self._create_experience_from_optimization(optimization)
                if experience:
                    experiences.append(experience)
        
        except Exception as e:
            logger.error(f"从优化结果中提取经验时出错: {e}")
        
        return experiences
    
    def _create_experience_from_optimization(self, optimization_result) -> Optional[ExperienceEntry]:
        """从优化结果中创建经验条目"""
        try:
            # 确定经验类别
            category = self._determine_category_from_optimization(optimization_result)
            
            # 生成经验ID
            experience_id = f"opt_exp_{optimization_result.optimization_id}"
            
            # 构建经验内容
            experience_content = {
                'optimization_type': optimization_result.type.value,
                'target_dimension': optimization_result.target_dimension,
                'improvement_rate': optimization_result.improvement_rate,
                'applied_actions': optimization_result.applied_actions,
                'impact_assessment': optimization_result.impact_assessment,
                'effectiveness_score': getattr(optimization_result, 'effectiveness_score', 0)
            }
            
            # 创建经验条目
            experience = ExperienceEntry(
                experience_id=experience_id,
                category=category,
                title=f"Optimization Experience: {optimization_result.type.value}",
                description=f"目标维度: {optimization_result.target_dimension}, "
                          f"改进率: {optimization_result.improvement_rate:.1%}",
                content=experience_content,
                source_data={
                    'source_type': 'optimization_result',
                    'source_id': optimization_result.optimization_id,
                    'extracted_at': datetime.now().isoformat()
                },
                impact_score=optimization_result.impact_assessment.get('performance_impact', 0.5),
                confidence_score=0.8,
                tags=[
                    f"optimization_type:{optimization_result.type.value}",
                    f"dimension:{optimization_result.target_dimension}",
                    "type:optimization_experience"
                ],
                related_experiences=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return experience
            
        except Exception as e:
            logger.error(f"从优化结果创建经验条目时出错: {e}")
            return None
    
    def _determine_category_from_optimization(self, optimization_result) -> ExperienceCategory:
        """根据优化结果确定经验类别"""
        optimization_type = optimization_result.type.value
        
        category_map = {
            'strategy_refinement': ExperienceCategory.STRATEGY_INSIGHT,
            'capability_enhancement': ExperienceCategory.PERFORMANCE_PATTERN,
            'resource_reallocation': ExperienceCategory.PERFORMANCE_PATTERN,
            'risk_mitigation': ExperienceCategory.RISK_LESSON,
            'model_upgrade': ExperienceCategory.TECHNOLOGY_ADOPTION
        }
        
        return category_map.get(optimization_type, ExperienceCategory.STRATEGY_INSIGHT)
    
    def _create_experience_package(self, package_type: str, experiences: List[ExperienceEntry], 
                                 summary: Dict[str, Any]) -> ExperiencePackage:
        """创建经验包"""
        package_id = f"{package_type}_pkg_{int(time.time())}"
        
        package = ExperiencePackage(
            package_id=package_id,
            package_type=package_type,
            experiences=experiences,
            summary=summary,
            generated_at=datetime.now()
        )
        
        return package
    
    def _generate_experience_summary(self, experiences: List[ExperienceEntry], 
                                   review_report) -> Dict[str, Any]:
        """生成经验摘要"""
        summary = {
            'total_experiences': len(experiences),
            'experiences_by_category': {},
            'total_impact_score': 0.0,
            'average_confidence_score': 0.0,
            'key_learnings': []
        }
        
        if not experiences:
            return summary
        
        # 按类别统计
        category_counts = {}
        total_impact = 0
        total_confidence = 0
        
        for experience in experiences:
            category = experience.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
            
            total_impact += experience.impact_score
            total_confidence += experience.confidence_score
        
        summary['experiences_by_category'] = category_counts
        summary['total_impact_score'] = total_impact
        summary['average_confidence_score'] = total_confidence / len(experiences)
        
        # 提取关键学习
        high_impact_experiences = [exp for exp in experiences if exp.impact_score >= 0.7]
        for exp in high_impact_experiences[:3]:  # 最多3个
            summary['key_learnings'].append({
                'title': exp.title,
                'key_insight': exp.description,
                'impact_score': exp.impact_score
            })
        
        return summary
    
    def _persist_to_notebook_lm(self, experience_package: ExperiencePackage):
        """将经验包持久化到Notebook LM"""
        try:
            if not self.notebook_lm:
                logger.warning("Notebook LM集成未启用，无法持久化经验")
                return
            
            # 为每个经验条目创建Notebook文档
            for experience in experience_package.experiences:
                # 创建文档内容
                document_content = self._create_notebook_document(experience)
                
                # 保存到Notebook LM
                success = self.notebook_lm.save_experience(experience, document_content)
                
                if success:
                    logger.info(f"经验已保存到Notebook LM: {experience.experience_id}")
                else:
                    logger.warning(f"保存经验到Notebook LM失败: {experience.experience_id}")
            
            # 保存经验包摘要
            package_success = self.notebook_lm.save_experience_package(experience_package)
            
            if package_success:
                logger.info(f"经验包已保存到Notebook LM: {experience_package.package_id}")
            
        except Exception as e:
            logger.error(f"持久化到Notebook LM时出错: {e}")
    
    def _create_notebook_document(self, experience: ExperienceEntry) -> Dict[str, Any]:
        """创建Notebook文档内容"""
        document = {
            'id': experience.experience_id,
            'title': experience.title,
            'content': {
                'summary': experience.description,
                'detailed_analysis': experience.content,
                'impact_assessment': {
                    'score': experience.impact_score,
                    'confidence': experience.confidence_score
                },
                'source_references': experience.source_data,
                'related_learnings': experience.related_experiences,
                'tags': experience.tags,
                'metadata': {
                    'created_at': experience.created_at.isoformat(),
                    'updated_at': experience.updated_at.isoformat(),
                    'applied_count': experience.applied_count,
                    'effectiveness_score': experience.effectiveness_score
                }
            },
            'category': experience.category.value,
            'timestamp': experience.created_at.isoformat(),
            'version': '1.0'
        }
        
        return document
    
    def _save_experiences_to_db(self, experiences: List[ExperienceEntry]):
        """保存经验到本地数据库"""
        if not self.state_manager or not experiences:
            return
        
        try:
            conn = self.state_manager.connect()
            cursor = conn.cursor()
            
            # 创建经验表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experience_library (
                    experience_id TEXT PRIMARY KEY,
                    category TEXT,
                    title TEXT,
                    description TEXT,
                    content TEXT,
                    source_data TEXT,
                    impact_score REAL,
                    confidence_score REAL,
                    tags TEXT,
                    related_experiences TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    applied_count INTEGER DEFAULT 0,
                    effectiveness_score REAL DEFAULT 0.0,
                    created_at_db DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入经验条目
            for experience in experiences:
                cursor.execute("""
                    INSERT OR REPLACE INTO experience_library 
                    (experience_id, category, title, description, content, 
                     source_data, impact_score, confidence_score, tags, 
                     related_experiences, created_at, updated_at, 
                     applied_count, effectiveness_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    experience.experience_id,
                    experience.category.value,
                    experience.title,
                    experience.description,
                    json.dumps(experience.content, default=str, ensure_ascii=False),
                    json.dumps(experience.source_data, default=str, ensure_ascii=False),
                    experience.impact_score,
                    experience.confidence_score,
                    json.dumps(experience.tags, ensure_ascii=False),
                    json.dumps(experience.related_experiences, ensure_ascii=False),
                    experience.created_at.isoformat(),
                    experience.updated_at.isoformat(),
                    experience.applied_count,
                    experience.effectiveness_score
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"经验已保存到本地数据库，共{len(experiences)}条")
            
        except Exception as e:
            logger.error(f"保存经验到数据库时出错: {e}")
    
    def search_experiences(self, query: str, category: Optional[ExperienceCategory] = None, 
                         min_impact_score: float = 0.0, max_results: int = 50) -> List[ExperienceEntry]:
        """
        搜索经验
        
        Args:
            query: 搜索关键词
            category: 经验类别筛选（可选）
            min_impact_score: 最小影响得分筛选
            max_results: 最大返回结果数
            
        Returns:
            匹配的经验条目列表
        """
        results = []
        
        try:
            for experience in self.experience_library.values():
                # 类别筛选
                if category and experience.category != category:
                    continue
                
                # 影响得分筛选
                if experience.impact_score < min_impact_score:
                    continue
                
                # 关键词匹配
                if (query.lower() in experience.title.lower() or 
                    query.lower() in experience.description.lower() or
                    any(query.lower() in tag.lower() for tag in experience.tags)):
                    
                    results.append(experience)
            
            # 按影响得分排序
            results.sort(key=lambda x: x.impact_score, reverse=True)
            
            # 限制结果数量
            results = results[:max_results]
            
            logger.info(f"经验搜索完成，查询: '{query}'，返回{len(results)}条结果")
            
        except Exception as e:
            logger.error(f"搜索经验时出错: {e}")
        
        return results
    
    def get_related_experiences(self, experience_id: str, max_results: int = 10) -> List[ExperienceEntry]:
        """
        获取相关经验
        
        Args:
            experience_id: 经验ID
            max_results: 最大返回结果数
            
        Returns:
            相关经验条目列表
        """
        related_experiences = []
        
        try:
            if experience_id not in self.experience_library:
                logger.warning(f"未找到经验: {experience_id}")
                return []
            
            source_experience = self.experience_library[experience_id]
            
            # 基于类别和标签查找相关经验
            for experience in self.experience_library.values():
                if experience.experience_id == experience_id:
                    continue  # 跳过自身
                
                # 类别匹配
                if experience.category == source_experience.category:
                    related_experiences.append(experience)
                    continue
                
                # 标签匹配
                common_tags = set(experience.tags) & set(source_experience.tags)
                if common_tags:
                    related_experiences.append(experience)
            
            # 按相关性排序（基于标签匹配数量和类别相似度）
            def relevance_score(exp):
                tag_score = len(set(exp.tags) & set(source_experience.tags)) / len(set(source_experience.tags))
                category_score = 1.0 if exp.category == source_experience.category else 0.5
                return tag_score * 0.6 + category_score * 0.4
            
            related_experiences.sort(key=relevance_score, reverse=True)
            
            # 限制结果数量
            related_experiences = related_experiences[:max_results]
            
            logger.info(f"获取相关经验完成，源经验: {experience_id}，返回{len(related_experiences)}条结果")
            
        except Exception as e:
            logger.error(f"获取相关经验时出错: {e}")
        
        return related_experiences
    
    def update_experience_effectiveness(self, experience_id: str, applied_success: bool, 
                                      improvement_rate: float = 0.0) -> bool:
        """
        更新经验有效性
        
        Args:
            experience_id: 经验ID
            applied_success: 应用是否成功
            improvement_rate: 实际改进率（如果可用）
            
        Returns:
            更新是否成功
        """
        try:
            if experience_id not in self.experience_library:
                logger.warning(f"未找到经验: {experience_id}")
                return False
            
            experience = self.experience_library[experience_id]
            
            # 更新应用计数
            experience.applied_count += 1
            
            # 更新有效性得分
            if applied_success:
                # 成功的应用会提高有效性得分
                base_improvement = max(improvement_rate, 0.1)
                effectiveness_increase = base_improvement * 0.3
                experience.effectiveness_score = min(1.0, experience.effectiveness_score + effectiveness_increase)
            else:
                # 失败的应用会降低有效性得分
                experience.effectiveness_score = max(0.0, experience.effectiveness_score - 0.1)
            
            # 更新更新时间
            experience.updated_at = datetime.now()
            
            # 更新数据库
            if self.state_manager:
                conn = self.state_manager.connect()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE experience_library 
                    SET applied_count = ?, effectiveness_score = ?, updated_at = ?
                    WHERE experience_id = ?
                """, (
                    experience.applied_count,
                    experience.effectiveness_score,
                    experience.updated_at.isoformat(),
                    experience_id
                ))
                
                conn.commit()
                conn.close()
            
            logger.info(f"经验有效性更新完成: {experience_id}, "
                       f"应用次数: {experience.applied_count}, "
                       f"有效性得分: {experience.effectiveness_score:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"更新经验有效性时出错: {e}")
            return False
    
    def export_experience_library(self, format: str = 'json') -> str:
        """
        导出经验库
        
        Args:
            format: 导出格式 (json, markdown)
            
        Returns:
            导出内容
        """
        export_data = {
            'export_id': f"experience_export_{int(time.time())}",
            'exported_at': datetime.now().isoformat(),
            'total_experiences': len(self.experience_library),
            'experience_categories': {},
            'experiences': []
        }
        
        # 按类别统计
        category_counts = {}
        for experience in self.experience_library.values():
            category = experience.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        export_data['experience_categories'] = category_counts
        
        # 添加经验详情
        for experience in list(self.experience_library.values())[:100]:  # 最多导出100条
            export_data['experiences'].append({
                'id': experience.experience_id,
                'category': experience.category.value,
                'title': experience.title,
                'description': experience.description,
                'impact_score': experience.impact_score,
                'applied_count': experience.applied_count,
                'effectiveness_score': experience.effectiveness_score,
                'tags': experience.tags
            })
        
        if format == 'json':
            return json.dumps(export_data, default=str, indent=2, ensure_ascii=False)
        elif format == 'markdown':
            return self._convert_to_markdown(export_data)
        else:
            logger.warning(f"不支持的导出格式: {format}，默认使用JSON")
            return json.dumps(export_data, default=str, indent=2, ensure_ascii=False)
    
    def _convert_to_markdown(self, export_data: Dict[str, Any]) -> str:
        """转换为Markdown格式"""
        lines = []
        
        # 标题
        lines.append(f"# 经验库导出")
        lines.append(f"导出ID: {export_data['export_id']}")
        lines.append(f"导出时间: {export_data['exported_at']}")
        lines.append(f"总经验数: {export_data['total_experiences']}")
        lines.append("")
        
        # 类别统计
        lines.append("## 经验类别分布")
        for category, count in export_data['experience_categories'].items():
            lines.append(f"- **{category}**: {count} 条")
        lines.append("")
        
        # 经验列表
        lines.append("## 经验详情")
        for exp in export_data['experiences']:
            lines.append(f"### {exp['title']}")
            lines.append(f"- **类别**: {exp['category']}")
            lines.append(f"- **影响得分**: {exp['impact_score']:.2f}")
            lines.append(f"- **应用次数**: {exp['applied_count']}")
            lines.append(f"- **有效性得分**: {exp['effectiveness_score']:.2f}")
            lines.append(f"- **标签**: {', '.join(exp['tags'])}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_experience_statistics(self) -> Dict[str, Any]:
        """
        获取经验统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_experiences': len(self.experience_library),
            'categories': {},
            'average_impact_score': 0.0,
            'average_confidence_score': 0.0,
            'top_experiences': [],
            'recent_experiences': []
        }
        
        if not self.experience_library:
            return stats
        
        # 按类别统计
        category_data = {}
        total_impact = 0
        total_confidence = 0
        
        for experience in self.experience_library.values():
            category = experience.category.value
            
            if category not in category_data:
                category_data[category] = {
                    'count': 0,
                    'total_impact': 0,
                    'total_confidence': 0
                }
            
            category_data[category]['count'] += 1
            category_data[category]['total_impact'] += experience.impact_score
            category_data[category]['total_confidence'] += experience.confidence_score
            
            total_impact += experience.impact_score
            total_confidence += experience.confidence_score
        
        # 计算统计
        stats['categories'] = category_data
        stats['average_impact_score'] = total_impact / len(self.experience_library)
        stats['average_confidence_score'] = total_confidence / len(self.experience_library)
        
        # 获取顶级经验
        top_experiences = sorted(self.experience_library.values(), 
                                key=lambda x: x.impact_score, reverse=True)[:10]
        stats['top_experiences'] = [exp.experience_id for exp in top_experiences]
        
        # 获取最近经验
        recent_experiences = sorted(self.experience_library.values(), 
                                  key=lambda x: x.created_at, reverse=True)[:10]
        stats['recent_experiences'] = [exp.experience_id for exp in recent_experiences]
        
        return stats


if __name__ == "__main__":
    # 测试经验沉淀模块
    from .config_manager import SelfEvolutionConfig
    
    config = SelfEvolutionConfig()
    persistence = ExperiencePersistence(config)
    
    # 测试经验搜索
    experiences = persistence.search_experiences("策略", max_results=5)
    print(f"搜索到{len(experiences)}条相关经验")
    
    # 获取统计信息
    stats = persistence.get_experience_statistics()
    print(f"经验库统计: 总数{stats['total_experiences']}, "
          f"平均影响得分{stats['average_impact_score']:.2f}")
    
    # 导出经验库
    export_content = persistence.export_experience_library('markdown')
    print(f"经验库导出完成，长度: {len(export_content)} 字符")