#!/usr/bin/env python3
"""
多模态创作工作流模块

此模块提供完整的多模态内容创作工作流，实现「知识库→内容创意→多模态生成→分发优化」的
完整创作链条。与Notebook LM知识库、AIGC能力服务中心深度集成。
"""

import os
import json
import time
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 导入相关模块
try:
    from src.aigc_service_center import (
        AIGCServiceCenter,
        ContentSpecification,
        ContentType,
        GenerationStyle,
        GenerationResult,
        create_aigc_service_center
    )
    HAS_AIGC_SERVICE = True
except ImportError:
    HAS_AIGC_SERVICE = False
    logging.warning("AIGC服务中心模块未找到，相关功能将受限")

try:
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        query_relevant_documents
    )
    HAS_NOTEBOOK_LM = True
except ImportError:
    HAS_NOTEBOOK_LM = False

try:
    from src.knowledge_driven_avatar import KnowledgeDrivenAvatar
    HAS_KNOWLEDGE_AVATAR = True
except ImportError:
    HAS_KNOWLEDGE_AVATAR = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """工作流阶段枚举"""
    KNOWLEDGE_QUERY = "knowledge_query"
    IDEA_GENERATION = "idea_generation"
    CONTENT_CREATION = "content_creation"
    QUALITY_REVIEW = "quality_review"
    DISTRIBUTION_OPTIMIZATION = "distribution_optimization"


class ContentIdeaType(Enum):
    """内容创意类型枚举"""
    PRODUCT_SHOWCASE = "product_showcase"
    TUTORIAL = "tutorial"
    PROMOTIONAL = "promotional"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"


@dataclass
class ContentIdea:
    """内容创意定义"""
    idea_id: str
    idea_type: ContentIdeaType
    title: str
    description: str
    target_audience: str
    key_messages: List[str]
    content_types: List[ContentType]  # 需要生成的内容类型
    platforms: List[str]  # 目标分发平台
    style_guidance: GenerationStyle
    knowledge_facts: List[Dict[str, Any]]  # 相关知识事实
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['idea_type'] = self.idea_type.value
        data['content_types'] = [ct.value for ct in self.content_types]
        data['style_guidance'] = self.style_guidance.value
        return data


@dataclass
class CampaignPlan:
    """营销活动计划"""
    campaign_id: str
    product_id: Optional[str]
    target_markets: List[str]
    budget_range: Optional[Tuple[float, float]]
    timeline: Dict[str, datetime]
    content_ideas: List[ContentIdea]
    performance_metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 转换时间格式
        if 'timeline' in data:
            for key, value in data['timeline'].items():
                if isinstance(value, datetime):
                    data['timeline'][key] = value.isoformat()
        # 转换创意
        data['content_ideas'] = [idea.to_dict() for idea in self.content_ideas]
        return data


@dataclass
class MultimodalContentAsset:
    """多模态内容资产"""
    asset_id: str
    content_type: ContentType
    idea_id: str
    specification: ContentSpecification
    generation_result: GenerationResult
    review_status: str  # pending, approved, rejected
    review_feedback: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['content_type'] = self.content_type.value
        data['specification'] = self.specification.to_dict()
        data['generation_result'] = self.generation_result.to_dict()
        return data


class KnowledgeDrivenContentIdeation:
    """知识驱动的内容创意生成器"""
    
    def __init__(self, notebook_lm_client=None):
        self.notebook_lm = notebook_lm_client
        
    def generate_content_ideas(self, product_info: Dict[str, Any], 
                              target_markets: List[str],
                              num_ideas: int = 3) -> List[ContentIdea]:
        """基于产品信息和目标市场生成内容创意"""
        
        ideas = []
        
        try:
            # 查询相关知识库
            relevant_knowledge = self._query_relevant_knowledge(product_info, target_markets)
            
            # 生成不同类型的创意
            idea_types = [
                ContentIdeaType.PRODUCT_SHOWCASE,
                ContentIdeaType.TUTORIAL,
                ContentIdeaType.PROMOTIONAL
            ]
            
            for i, idea_type in enumerate(idea_types[:num_ideas]):
                # 生成创意
                idea = self._generate_specific_idea(
                    product_info=product_info,
                    idea_type=idea_type,
                    target_markets=target_markets,
                    relevant_knowledge=relevant_knowledge,
                    idea_index=i
                )
                
                if idea:
                    ideas.append(idea)
            
            logger.info(f"生成 {len(ideas)} 个内容创意，产品: {product_info.get('name', '未知')}")
            return ideas
            
        except Exception as e:
            logger.error(f"内容创意生成失败: {str(e)}")
            return []
    
    def _query_relevant_knowledge(self, product_info: Dict[str, Any],
                                 target_markets: List[str]) -> List[Dict[str, Any]]:
        """查询相关知识库"""
        
        if not self.notebook_lm:
            return []
        
        try:
            # 构建查询关键词
            queries = [
                product_info.get('name', ''),
                product_info.get('category', ''),
                product_info.get('target_audience', '')
            ]
            
            # 添加市场相关查询
            for market in target_markets[:2]:
                queries.append(f"{market} fashion trends")
            
            all_knowledge = []
            
            # 执行查询
            for query in queries:
                if query.strip():
                    results = self.notebook_lm.query_knowledge(
                        query=query,
                        max_results=3,
                        min_relevance_score=0.6
                    )
                    all_knowledge.extend(results)
            
            # 去重
            seen_content = set()
            unique_knowledge = []
            
            for item in all_knowledge:
                content_hash = hashlib.md5(str(item.get('content', '')).encode()).hexdigest()[:16]
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_knowledge.append(item)
            
            return unique_knowledge[:10]  # 限制数量
            
        except Exception as e:
            logger.warning(f"知识库查询失败: {str(e)}")
            return []
    
    def _generate_specific_idea(self, product_info: Dict[str, Any],
                               idea_type: ContentIdeaType,
                               target_markets: List[str],
                               relevant_knowledge: List[Dict[str, Any]],
                               idea_index: int) -> Optional[ContentIdea]:
        """生成特定类型的创意"""
        
        try:
            # 根据创意类型确定内容类型组合
            content_type_mapping = {
                ContentIdeaType.PRODUCT_SHOWCASE: [ContentType.IMAGE, ContentType.TEXT],
                ContentIdeaType.TUTORIAL: [ContentType.VIDEO, ContentType.TEXT],
                ContentIdeaType.PROMOTIONAL: [ContentType.IMAGE, ContentType.VIDEO, ContentType.TEXT],
                ContentIdeaType.EDUCATIONAL: [ContentType.TEXT, ContentType.IMAGE],
                ContentIdeaType.ENTERTAINMENT: [ContentType.VIDEO, ContentType.IMAGE]
            }
            
            # 根据市场确定风格
            style_mapping = {
                'US': GenerationStyle.TRENDY,
                'UK': GenerationStyle.PROFESSIONAL,
                'JP': GenerationStyle.MINIMALIST,
                'CN': GenerationStyle.BRAND_ALIGNED,
                'default': GenerationStyle.PHOTOREALISTIC
            }
            
            primary_market = target_markets[0] if target_markets else 'default'
            style = style_mapping.get(primary_market, style_mapping['default'])
            
            # 生成创意标题和描述
            title, description = self._generate_idea_title_description(
                product_info=product_info,
                idea_type=idea_type,
                target_market=primary_market
            )
            
            # 确定关键信息
            key_messages = self._extract_key_messages(product_info, relevant_knowledge)
            
            # 确定分发平台
            platforms = self._determine_platforms(idea_type, primary_market)
            
            # 生成创意ID
            idea_id = f"idea_{int(time.time())}_{idea_index}_{hashlib.md5(title.encode()).hexdigest()[:6]}"
            
            # 创建内容创意
            idea = ContentIdea(
                idea_id=idea_id,
                idea_type=idea_type,
                title=title,
                description=description,
                target_audience=product_info.get('target_audience', 'general'),
                key_messages=key_messages,
                content_types=content_type_mapping.get(idea_type, [ContentType.TEXT]),
                platforms=platforms,
                style_guidance=style,
                knowledge_facts=relevant_knowledge[:5]  # 使用前5个最相关事实
            )
            
            return idea
            
        except Exception as e:
            logger.error(f"特定创意生成失败: {str(e)}")
            return None
    
    def _generate_idea_title_description(self, product_info: Dict[str, Any],
                                        idea_type: ContentIdeaType,
                                        target_market: str) -> Tuple[str, str]:
        """生成创意标题和描述"""
        
        product_name = product_info.get('name', '产品')
        category = product_info.get('category', '时尚')
        
        # 基础标题模板
        title_templates = {
            ContentIdeaType.PRODUCT_SHOWCASE: [
                f"{product_name} - {target_market}时尚新选择",
                f"{product_name}精致展示，感受{category}魅力"
            ],
            ContentIdeaType.TUTORIAL: [
                f"如何使用{product_name}打造完美造型",
                f"{product_name}搭配教程，轻松掌握{category}技巧"
            ],
            ContentIdeaType.PROMOTIONAL: [
                f"{product_name}限时优惠，{target_market}专属福利",
                f"{product_name}春季上新，不可错过的{category}单品"
            ],
            ContentIdeaType.EDUCATIONAL: [
                f"了解{product_name}的设计理念与工艺",
                f"{category}知识科普：{product_name}的独特之处"
            ],
            ContentIdeaType.ENTERTAINMENT: [
                f"{product_name}趣味挑战，分享你的创意搭配",
                f"与{product_name}一起的精彩瞬间"
            ]
        }
        
        templates = title_templates.get(idea_type, [f"{product_name}相关内容"])
        title = templates[0]  # 使用第一个模板
        
        # 生成描述
        description_templates = {
            ContentIdeaType.PRODUCT_SHOWCASE: 
                f"展示{product_name}的精美细节与设计特点，突出在{target_market}市场的时尚定位。",
            ContentIdeaType.TUTORIAL:
                f"详细教程，教你如何充分利用{product_name}，打造专业级的{category}效果。",
            ContentIdeaType.PROMOTIONAL:
                f"特别促销活动，为{target_market}用户提供专属优惠，机会难得。",
            ContentIdeaType.EDUCATIONAL:
                f"深入了解{product_name}背后的设计与技术，提升你的{category}专业知识。",
            ContentIdeaType.ENTERTAINMENT:
                f"轻松有趣的内容，展示{product_name}在不同场景下的魅力与趣味性。"
        }
        
        description = description_templates.get(idea_type, 
                                               f"关于{product_name}的{idea_type.value}内容。")
        
        return title, description
    
    def _extract_key_messages(self, product_info: Dict[str, Any],
                             relevant_knowledge: List[Dict[str, Any]]) -> List[str]:
        """提取关键信息"""
        
        key_messages = []
        
        # 从产品信息提取
        if product_info.get('key_features'):
            if isinstance(product_info['key_features'], list):
                key_messages.extend(product_info['key_features'][:3])
            elif isinstance(product_info['key_features'], str):
                key_messages.append(product_info['key_features'])
        
        # 从知识库提取
        for knowledge in relevant_knowledge[:2]:
            content = knowledge.get('content', '')
            if content and len(content) > 20:
                # 提取前100个字符作为关键信息
                summary = content[:100].strip()
                if summary.endswith('...') or len(content) > 100:
                    summary = summary[:97] + '...'
                key_messages.append(summary)
        
        # 确保有至少一个关键信息
        if not key_messages:
            key_messages = [f"{product_info.get('name', '产品')}的独特价值与优势"]
        
        return key_messages[:5]  # 限制数量
    
    def _determine_platforms(self, idea_type: ContentIdeaType,
                            target_market: str) -> List[str]:
        """确定分发平台"""
        
        # 平台映射
        platform_mapping = {
            ContentIdeaType.PRODUCT_SHOWCASE: ['instagram', 'pinterest', 'shopify'],
            ContentIdeaType.TUTORIAL: ['youtube', 'tiktok', 'instagram'],
            ContentIdeaType.PROMOTIONAL: ['tiktok', 'instagram', 'facebook'],
            ContentIdeaType.EDUCATIONAL: ['linkedin', 'twitter', 'blog'],
            ContentIdeaType.ENTERTAINMENT: ['tiktok', 'instagram', 'youtube']
        }
        
        platforms = platform_mapping.get(idea_type, ['instagram', 'tiktok'])
        
        # 根据目标市场调整
        market_adjustments = {
            'CN': ['xiaohongshu', 'douyin', 'weibo'],
            'JP': ['twitter', 'instagram', 'line'],
            'KR': ['instagram', 'youtube', 'kakao']
        }
        
        if target_market in market_adjustments:
            # 结合通用平台和市场特定平台
            platforms = list(set(platforms + market_adjustments[target_market]))
        
        return platforms[:5]  # 限制数量


class MultimodalContentWorkflow:
    """多模态内容创作工作流管理器"""
    
    def __init__(self, aigc_service: AIGCServiceCenter,
                 notebook_lm_client = None):
        """初始化工作流管理器"""
        
        self.aigc_service = aigc_service
        self.notebook_lm = notebook_lm_client
        
        # 初始化子模块
        self.ideation = KnowledgeDrivenContentIdeation(notebook_lm_client)
        
        # 工作流状态
        self.current_stage = None
        self.workflow_id = None
        self.start_time = None
        self.assets = []  # 生成的内容资产
        self.status = 'idle'  # idle, running, completed, failed
        
        logger.info("多模态内容工作流管理器初始化完成")
    
    def start_workflow(self, product_info: Dict[str, Any],
                      target_markets: List[str]) -> str:
        """启动新的工作流"""
        
        # 生成工作流ID
        self.workflow_id = f"workflow_{int(time.time())}_{hashlib.md5(str(product_info).encode()).hexdigest()[:8]}"
        self.start_time = time.time()
        self.status = 'running'
        self.assets = []
        
        logger.info(f"启动工作流 {self.workflow_id}, 产品: {product_info.get('name', '未知')}")
        
        return self.workflow_id
    
    def execute_full_workflow(self, product_info: Dict[str, Any],
                             target_markets: List[str]) -> Dict[str, Any]:
        """执行完整工作流"""
        
        workflow_id = self.start_workflow(product_info, target_markets)
        
        try:
            # 阶段1：知识查询与创意生成
            self.current_stage = WorkflowStage.KNOWLEDGE_QUERY
            content_ideas = self.ideation.generate_content_ideas(
                product_info=product_info,
                target_markets=target_markets,
                num_ideas=3
            )
            
            if not content_ideas:
                raise ValueError("未能生成有效的内容创意")
            
            # 阶段2：多模态内容生成
            self.current_stage = WorkflowStage.CONTENT_CREATION
            generated_assets = []
            
            for idea in content_ideas:
                idea_assets = self._generate_content_for_idea(idea)
                generated_assets.extend(idea_assets)
            
            self.assets = generated_assets
            
            # 阶段3：质量审查
            self.current_stage = WorkflowStage.QUALITY_REVIEW
            review_results = self._review_content_assets(generated_assets)
            
            # 阶段4：分发优化建议
            self.current_stage = WorkflowStage.DISTRIBUTION_OPTIMIZATION
            distribution_plan = self._create_distribution_plan(
                generated_assets, target_markets
            )
            
            # 完成工作流
            self.status = 'completed'
            
            # 准备结果
            result = {
                'workflow_id': workflow_id,
                'success': True,
                'duration': time.time() - self.start_time,
                'content_ideas': [idea.to_dict() for idea in content_ideas],
                'assets_generated': len(generated_assets),
                'assets': [asset.to_dict() for asset in generated_assets],
                'review_summary': review_results,
                'distribution_plan': distribution_plan,
                'next_steps': self._determine_next_steps(review_results, distribution_plan)
            }
            
            logger.info(f"工作流 {workflow_id} 完成，生成 {len(generated_assets)} 个内容资产")
            return result
            
        except Exception as e:
            self.status = 'failed'
            logger.error(f"工作流 {workflow_id} 执行失败: {str(e)}")
            
            return {
                'workflow_id': workflow_id,
                'success': False,
                'error': str(e),
                'duration': time.time() - self.start_time,
                'current_stage': self.current_stage.value if self.current_stage else None,
                'assets_generated': len(self.assets)
            }
    
    def _generate_content_for_idea(self, idea: ContentIdea) -> List[MultimodalContentAsset]:
        """为创意生成多模态内容"""
        
        assets = []
        
        # 为每种内容类型生成内容
        for content_type in idea.content_types:
            try:
                # 创建内容规格
                specification = self._create_content_specification(idea, content_type)
                
                # 生成内容
                generation_result = self.aigc_service.generate_content(
                    specification=specification,
                    knowledge_constraints=[fact.get('id', '') for fact in idea.knowledge_facts[:3]]
                )
                
                # 创建内容资产
                asset = MultimodalContentAsset(
                    asset_id=f"asset_{int(time.time())}_{content_type.value}_{hashlib.md5(idea.idea_id.encode()).hexdigest()[:6]}",
                    content_type=content_type,
                    idea_id=idea.idea_id,
                    specification=specification,
                    generation_result=generation_result,
                    review_status='pending',
                    review_feedback=None
                )
                
                assets.append(asset)
                
                logger.info(f"为创意 {idea.idea_id} 生成 {content_type.value} 内容成功")
                
            except Exception as e:
                logger.error(f"为创意 {idea.idea_id} 生成 {content_type.value} 内容失败: {str(e)}")
                # 继续生成其他类型内容
        
        return assets
    
    def _create_content_specification(self, idea: ContentIdea,
                                     content_type: ContentType) -> ContentSpecification:
        """根据创意和内容类型创建内容规格"""
        
        # 基础规格
        specification = ContentSpecification(
            content_type=content_type,
            subject=idea.title,
            style=idea.style_guidance,
            language='en',  # 默认英语，实际可根据目标市场调整
            brand_guidelines=idea.key_messages[0] if idea.key_messages else None,
            target_platform=idea.platforms[0] if idea.platforms else None,
            quality_preset='standard'
        )
        
        # 根据内容类型设置特定参数
        if content_type == ContentType.IMAGE:
            # 根据平台设置推荐尺寸
            platform_dimensions = {
                'instagram': (1080, 1080),  # 正方形
                'tiktok': (1080, 1920),     # 竖屏
                'pinterest': (1000, 1500),  # 竖屏长图
                'shopify': (1200, 1200),    # 产品图
                'default': (1024, 1024)
            }
            
            platform = idea.platforms[0] if idea.platforms else 'default'
            dimensions = platform_dimensions.get(platform, platform_dimensions['default'])
            specification.dimensions = dimensions
        
        elif content_type == ContentType.VIDEO:
            specification.duration = 30  # 默认30秒
        
        # 根据目标市场调整语言
        if idea.target_audience and idea.target_audience.lower() in ['cn', 'china', 'chinese']:
            specification.language = 'zh'
        elif idea.target_audience and idea.target_audience.lower() in ['jp', 'japan', 'japanese']:
            specification.language = 'ja'
        elif idea.target_audience and idea.target_audience.lower() in ['kr', 'korea', 'korean']:
            specification.language = 'ko'
        
        return specification
    
    def _review_content_assets(self, assets: List[MultimodalContentAsset]) -> Dict[str, Any]:
        """审查内容资产质量"""
        
        review_summary = {
            'total_assets': len(assets),
            'successful_generations': 0,
            'failed_generations': 0,
            'quality_scores': [],
            'compliance_status': [],
            'brand_alignment_scores': []
        }
        
        for asset in assets:
            result = asset.generation_result
            
            if result.success:
                review_summary['successful_generations'] += 1
                
                # 收集质量指标
                metadata = result.metadata or {}
                
                if 'quality_score' in metadata:
                    review_summary['quality_scores'].append(metadata['quality_score'])
                
                if 'compliance_status' in metadata:
                    review_summary['compliance_status'].append(metadata['compliance_status'])
                
                if 'brand_alignment_score' in metadata:
                    review_summary['brand_alignment_scores'].append(metadata['brand_alignment_score'])
                
                # 设置审查状态
                if metadata.get('compliance_status') == 'passed' and metadata.get('brand_alignment_score', 0) >= 0.7:
                    asset.review_status = 'approved'
                    asset.review_feedback = "内容质量合格，符合品牌标准"
                else:
                    asset.review_status = 'rejected'
                    asset.review_feedback = f"内容需要优化：合规状态={metadata.get('compliance_status', 'unknown')}, 品牌一致性={metadata.get('brand_alignment_score', 0):.2f}"
            else:
                review_summary['failed_generations'] += 1
                asset.review_status = 'rejected'
                asset.review_feedback = f"生成失败: {result.error_message}"
        
        # 计算平均分
        if review_summary['quality_scores']:
            review_summary['average_quality_score'] = sum(review_summary['quality_scores']) / len(review_summary['quality_scores'])
        else:
            review_summary['average_quality_score'] = 0
        
        if review_summary['brand_alignment_scores']:
            review_summary['average_brand_alignment'] = sum(review_summary['brand_alignment_scores']) / len(review_summary['brand_alignment_scores'])
        else:
            review_summary['average_brand_alignment'] = 0
        
        # 统计合规通过率
        passed_count = sum(1 for status in review_summary['compliance_status'] if status == 'passed')
        total_compliance = len(review_summary['compliance_status'])
        review_summary['compliance_pass_rate'] = passed_count / total_compliance if total_compliance > 0 else 0
        
        logger.info(f"内容审查完成: {review_summary['successful_generations']}/{review_summary['total_assets']} 成功，平均质量分: {review_summary['average_quality_score']:.2f}")
        
        return review_summary
    
    def _create_distribution_plan(self, assets: List[MultimodalContentAsset],
                                 target_markets: List[str]) -> Dict[str, Any]:
        """创建内容分发计划"""
        
        # 按平台分组资产
        platform_assets = {}
        
        for asset in assets:
            platform = asset.specification.target_platform or 'default'
            
            if platform not in platform_assets:
                platform_assets[platform] = []
            
            if asset.review_status == 'approved':
                platform_assets[platform].append(asset)
        
        # 创建分发计划
        distribution_plan = {
            'target_markets': target_markets,
            'platform_distribution': {},
            'recommended_schedule': {},
            'performance_goals': {}
        }
        
        # 为每个平台制定计划
        for platform, platform_assets_list in platform_assets.items():
            if not platform_assets_list:
                continue
            
            # 平台特定策略
            platform_strategies = {
                'instagram': {
                    'optimal_times': ['10:00', '14:00', '19:00'],
                    'hashtag_recommendation': 10,
                    'stories_recommended': True
                },
                'tiktok': {
                    'optimal_times': ['12:00', '18:00', '21:00'],
                    'trending_sounds': True,
                    'duet_challenge': True
                },
                'youtube': {
                    'optimal_times': ['17:00', '20:00'],
                    'tags_recommendation': 15,
                    'end_screen_cta': True
                },
                'default': {
                    'optimal_times': ['12:00', '18:00'],
                    'general_guidelines': ['保持一致性', '互动回复', '分析数据']
                }
            }
            
            strategy = platform_strategies.get(platform, platform_strategies['default'])
            
            distribution_plan['platform_distribution'][platform] = {
                'asset_count': len(platform_assets_list),
                'content_types': list(set([asset.content_type.value for asset in platform_assets_list])),
                'strategy': strategy
            }
            
            # 推荐发布时间表
            today = datetime.now()
            distribution_plan['recommended_schedule'][platform] = {
                'next_post_time': f"{today.strftime('%Y-%m-%d')} {strategy['optimal_times'][0]}",
                'frequency': 'daily',
                'content_mix': self._determine_content_mix(platform_assets_list)
            }
            
            # 性能目标
            distribution_plan['performance_goals'][platform] = {
                'engagement_rate_goal': 0.05,  # 5%互动率
                'ctr_goal': 0.03,  # 3%点击率
                'conversion_goal': 0.01  # 1%转化率
            }
        
        return distribution_plan
    
    def _determine_content_mix(self, assets: List[MultimodalContentAsset]) -> Dict[str, int]:
        """确定内容组合比例"""
        
        content_type_counts = {}
        
        for asset in assets:
            content_type = asset.content_type.value
            content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
        
        total = len(assets)
        
        # 计算百分比
        content_mix = {}
        for content_type, count in content_type_counts.items():
            percentage = (count / total) * 100
            content_mix[content_type] = round(percentage, 1)
        
        return content_mix
    
    def _determine_next_steps(self, review_results: Dict[str, Any],
                             distribution_plan: Dict[str, Any]) -> List[str]:
        """确定后续步骤"""
        
        next_steps = []
        
        # 基于审查结果
        success_rate = review_results.get('successful_generations', 0) / review_results.get('total_assets', 1)
        
        if success_rate < 0.8:
            next_steps.append("优化内容生成参数，提高成功率")
        
        avg_quality = review_results.get('average_quality_score', 0)
        if avg_quality < 0.7:
            next_steps.append("加强质量审查，提升内容质量")
        
        # 基于分发计划
        total_assets = sum(data['asset_count'] for data in distribution_plan.get('platform_distribution', {}).values())
        if total_assets < 5:
            next_steps.append("生成更多内容资产以支持完整营销活动")
        
        # 通用下一步
        next_steps.extend([
            "根据分发计划安排内容发布",
            "监控内容表现并收集反馈数据",
            "基于表现数据优化后续内容策略"
        ])
        
        return next_steps
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        
        return {
            'workflow_id': self.workflow_id,
            'status': self.status,
            'current_stage': self.current_stage.value if self.current_stage else None,
            'start_time': self.start_time,
            'duration': time.time() - self.start_time if self.start_time else 0,
            'assets_generated': len(self.assets),
            'successful_assets': sum(1 for asset in self.assets if asset.generation_result.success),
            'failed_assets': sum(1 for asset in self.assets if not asset.generation_result.success)
        }


class GlobalMultilingualContentWorkflow(MultimodalContentWorkflow):
    """全球多语言内容工作流（扩展多语言支持）"""
    
    def __init__(self, aigc_service: AIGCServiceCenter,
                 notebook_lm_client=None):
        super().__init__(aigc_service, notebook_lm_client)
        
        # 语言支持配置
        self.supported_languages = {
            'en': {'name': 'English', 'region_variants': ['US', 'UK', 'AU']},
            'zh': {'name': '中文', 'region_variants': ['CN', 'TW', 'HK']},
            'es': {'name': 'Español', 'region_variants': ['ES', 'MX', 'AR']},
            'fr': {'name': 'Français', 'region_variants': ['FR', 'CA', 'BE']},
            'de': {'name': 'Deutsch', 'region_variants': ['DE', 'AT', 'CH']},
            'ja': {'name': '日本語', 'region_variants': ['JP']},
            'ko': {'name': '한국어', 'region_variants': ['KR']},
            'ar': {'name': 'العربية', 'region_variants': ['SA', 'AE', 'EG']}
        }
        
        # 文化适配规则
        self.cultural_adaptation_rules = self._load_cultural_adaptation_rules()
        
        logger.info("全球多语言内容工作流初始化完成，支持 {} 种语言".format(len(self.supported_languages)))
    
    def _load_cultural_adaptation_rules(self) -> Dict[str, Any]:
        """加载文化适配规则"""
        
        # 这里可以连接外部数据库或配置文件
        # 简化实现：硬编码基本规则
        
        rules = {
            'colors': {
                'CN': ['red', 'gold', 'black'],  # 中国喜欢红色、金色
                'JP': ['white', 'black', 'navy'],  # 日本喜欢白色、黑色、海军蓝
                'US': ['blue', 'red', 'white'],  # 美国喜欢蓝色、红色、白色
                'SA': ['green', 'white', 'black'],  # 沙特喜欢绿色、白色、黑色
            },
            'imagery': {
                'CN': ['dragon', 'phoenix', 'lotus'],  # 中国文化意象
                'JP': ['cherry_blossom', 'mount_fuji', 'torii_gate'],  # 日本文化意象
                'IN': ['lotus', 'elephant', 'peacock'],  # 印度文化意象
            },
            'tone': {
                'US': ['direct', 'enthusiastic', 'personal'],  # 美国喜欢直接、热情、个人化
                'JP': ['polite', 'humble', 'formal'],  # 日本喜欢礼貌、谦逊、正式
                'CN': ['respectful', 'harmonious', 'positive'],  # 中国喜欢尊重、和谐、积极
            },
            'taboos': {
                'CN': ['4', 'white_flowers'],  # 中国禁忌：数字4、白花
                'JP': ['4', '9'],  # 日本禁忌：数字4、9
                'SA': ['pork', 'alcohol', 'dogs'],  # 沙特禁忌：猪肉、酒精、狗
            }
        }
        
        return rules
    
    def execute_multilingual_campaign(self, product_info: Dict[str, Any],
                                     target_markets: List[Dict[str, str]]) -> Dict[str, Any]:
        """执行多语言营销活动工作流"""
        
        # 按市场组织工作流
        market_workflows = []
        
        for market_config in target_markets:
            market_code = market_config.get('market_code', 'US')
            language = market_config.get('language', 'en')
            region_variant = market_config.get('region_variant', 'US')
            
            # 验证语言支持
            if language not in self.supported_languages:
                logger.warning(f"不支持的语言: {language}，跳过市场 {market_code}")
                continue
            
            # 为每个市场执行独立工作流
            market_result = self._execute_market_specific_workflow(
                product_info=product_info,
                market_code=market_code,
                language=language,
                region_variant=region_variant
            )
            
            market_workflows.append(market_result)
        
        # 整合结果
        consolidated_result = {
            'total_markets': len(market_workflows),
            'successful_markets': sum(1 for wf in market_workflows if wf.get('success', False)),
            'failed_markets': sum(1 for wf in market_workflows if not wf.get('success', True)),
            'total_assets': sum(wf.get('assets_generated', 0) for wf in market_workflows),
            'market_details': market_workflows,
            'cross_market_recommendations': self._generate_cross_market_recommendations(market_workflows)
        }
        
        logger.info(f"多语言营销活动完成: {consolidated_result['successful_markets']}/{consolidated_result['total_markets']} 市场成功")
        
        return consolidated_result
    
    def _execute_market_specific_workflow(self, product_info: Dict[str, Any],
                                         market_code: str, language: str,
                                         region_variant: str) -> Dict[str, Any]:
        """执行特定市场的工作流"""
        
        # 调整产品信息以适应目标市场
        adapted_product_info = self._adapt_product_for_market(
            product_info=product_info,
            market_code=market_code,
            language=language,
            region_variant=region_variant
        )
        
        # 执行基础工作流
        workflow_result = self.execute_full_workflow(
            product_info=adapted_product_info,
            target_markets=[market_code]
        )
        
        # 添加市场特定信息
        workflow_result.update({
            'market_code': market_code,
            'language': language,
            'region_variant': region_variant,
            'cultural_adaptation_applied': True
        })
        
        return workflow_result
    
    def _adapt_product_for_market(self, product_info: Dict[str, Any],
                                 market_code: str, language: str,
                                 region_variant: str) -> Dict[str, Any]:
        """根据目标市场调整产品信息"""
        
        adapted_info = product_info.copy()
        
        # 文化适配
        cultural_rules = self.cultural_adaptation_rules
        
        # 调整颜色偏好
        if 'colors' in cultural_rules and market_code in cultural_rules['colors']:
            adapted_info['preferred_colors'] = cultural_rules['colors'][market_code]
        
        # 调整视觉意象
        if 'imagery' in cultural_rules and market_code in cultural_rules['imagery']:
            adapted_info['cultural_imagery'] = cultural_rules['imagery'][market_code]
        
        # 调整语调风格
        if 'tone' in cultural_rules and market_code in cultural_rules['tone']:
            adapted_info['communication_tone'] = cultural_rules['tone'][market_code]
        
        # 避免文化禁忌
        if 'taboos' in cultural_rules and market_code in cultural_rules['taboos']:
            adapted_info['cultural_taboos'] = cultural_rules['taboos'][market_code]
        
        # 本地化产品名称（如有）
        if 'localized_names' in product_info and language in product_info['localized_names']:
            adapted_info['name'] = product_info['localized_names'][language]
            adapted_info['local_name'] = True
        
        # 添加市场标签
        adapted_info['target_market'] = market_code
        adapted_info['target_language'] = language
        adapted_info['region_variant'] = region_variant
        
        return adapted_info
    
    def _generate_cross_market_recommendations(self, market_workflows: List[Dict[str, Any]]) -> List[str]:
        """生成跨市场推荐"""
        
        recommendations = []
        
        # 分析成功模式
        successful_markets = [wf for wf in market_workflows if wf.get('success', False)]
        
        if len(successful_markets) >= 2:
            # 识别共同成功因素
            common_factors = []
            
            # 检查创意类型分布
            idea_types = {}
            for wf in successful_markets:
                for idea in wf.get('content_ideas', []):
                    idea_type = idea.get('idea_type')
                    idea_types[idea_type] = idea_types.get(idea_type, 0) + 1
            
            # 推荐最受欢迎的创意类型
            popular_types = sorted(idea_types.items(), key=lambda x: x[1], reverse=True)[:2]
            if popular_types:
                recommendations.append(f"跨市场表现最佳的创意类型: {', '.join([t[0] for t in popular_types])}")
            
            # 推荐内容组合策略
            asset_distribution = {}
            for wf in successful_markets:
                for asset in wf.get('assets', []):
                    content_type = asset.get('specification', {}).get('content_type')
                    asset_distribution[content_type] = asset_distribution.get(content_type, 0) + 1
            
            optimal_mix = {}
            total_assets = sum(asset_distribution.values())
            for content_type, count in asset_distribution.items():
                percentage = (count / total_assets) * 100
                if percentage >= 15:  # 占比超过15%的内容类型值得推荐
                    optimal_mix[content_type] = round(percentage, 1)
            
            if optimal_mix:
                mix_desc = ', '.join([f"{ct}: {p}%" for ct, p in optimal_mix.items()])
                recommendations.append(f"建议的内容组合: {mix_desc}")
        
        # 通用跨市场推荐
        recommendations.extend([
            "考虑文化节日和季节性活动安排内容发布",
            "建立跨市场内容表现对比分析仪表板",
            "识别各地区热门话题和趋势进行内容本地化",
            "建立多语言内容质量评估标准体系"
        ])
        
        return recommendations


# 工厂函数
def create_multimodal_workflow(aigc_service: AIGCServiceCenter,
                              notebook_lm_client = None) -> MultimodalContentWorkflow:
    """创建多模态内容工作流实例"""
    return MultimodalContentWorkflow(aigc_service, notebook_lm_client)


def create_global_workflow(aigc_service: AIGCServiceCenter,
                          notebook_lm_client = None) -> GlobalMultilingualContentWorkflow:
    """创建全球多语言工作流实例"""
    return GlobalMultilingualContentWorkflow(aigc_service, notebook_lm_client)


if __name__ == "__main__":
    """测试多模态工作流"""
    
    print("🧪 测试多模态内容创作工作流")
    
    # 创建AIGC服务
    try:
        aigc_service = create_aigc_service_center()
        aigc_service.start()
        print("✅ AIGC服务启动成功")
    except Exception as e:
        print(f"❌ AIGC服务启动失败: {str(e)}")
        exit(1)
    
    # 创建多模态工作流
    workflow = create_multimodal_workflow(aigc_service)
    
    # 测试数据
    product_info = {
        'name': '时尚牛仔外套',
        'category': '服装',
        'key_features': ['经典设计', '舒适面料', '多口袋功能'],
        'target_audience': '年轻时尚人群',
        'price_range': '$80-$120',
        'brand': 'UrbanStyle'
    }
    
    target_markets = ['US', 'CN']
    
    print(f"📦 产品: {product_info['name']}")
    print(f"🌍 目标市场: {', '.join(target_markets)}")
    print("🚀 开始执行工作流...")
    
    # 执行工作流
    start_time = time.time()
    result = workflow.execute_full_workflow(product_info, target_markets)
    duration = time.time() - start_time
    
    print(f"⏱️  工作流执行时间: {duration:.2f}秒")
    print(f"📊 结果: {'成功' if result['success'] else '失败'}")
    
    if result['success']:
        print(f"💡 生成创意: {len(result['content_ideas'])} 个")
        print(f"🖼️  生成资产: {result['assets_generated']} 个")
        print(f"✅ 审查通过率: {result['review_summary'].get('successful_generations', 0)}/{result['review_summary'].get('total_assets', 1)}")
        print(f"📈 平均质量分: {result['review_summary'].get('average_quality_score', 0):.2f}")
        
        # 显示部分创意
        print("\n📝 创意示例:")
        for i, idea in enumerate(result['content_ideas'][:2]):
            print(f"  {i+1}. {idea['title']}")
            print(f"     类型: {idea['idea_type']}, 内容类型: {', '.join(idea['content_types'])}")
            print(f"     平台: {', '.join(idea['platforms'][:3])}")
    
    # 停止服务
    aigc_service.stop()
    print("\n🛑 AIGC服务已停止")
    
    print("\n✅ 多模态工作流测试完成")