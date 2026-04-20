#!/usr/bin/env python3
"""
AI内容创作工坊模块

此模块提供基于Notebook LM知识库的内容创作能力，
支持营销文案、分析报告、商业计划等各类内容自动生成，
与现有AIGC模块深度打通，确保内容符合品牌标准并基于事实。
"""

import os
import json
import re
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import time

# 尝试导入必要的库
try:
    import jinja2
    JINJA_SUPPORT = True
except ImportError:
    JINJA_SUPPORT = False

# 导入Notebook LM集成
try:
    from src.notebook_lm_integration import NotebookLMIntegration
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.notebook_lm_integration import NotebookLMIntegration

# 配置日志
logger = logging.getLogger(__name__)


class ContentCreationWorkshop:
    """
    内容创作工坊
    
    基于Notebook LM知识库生成各类商业内容，
    确保内容准确、专业且符合品牌标准。
    """
    
    def __init__(self, notebook_lm_integration: Optional[NotebookLMIntegration] = None,
                 language: str = "zh-CN"):
        """
        初始化内容创作工坊
        
        Args:
            notebook_lm_integration: Notebook LM集成实例
            language: 目标语言
        """
        self.language = language
        self.nli = notebook_lm_integration
        
        # 内容模板库
        self.templates = self._initialize_templates()
        
        # 风格指南
        self.style_guides = self._initialize_style_guides()
        
        # 内容质量评估器
        self.quality_assessor = ContentQualityAssessor(language)
        
        logger.info(f"内容创作工坊初始化完成，语言: {language}")
    
    def create_content(self, content_type: str,
                      parameters: Dict[str, Any],
                      tone: str = "professional",
                      length: str = "medium") -> Dict[str, Any]:
        """
        创建内容
        
        Args:
            content_type: 内容类型
            parameters: 内容参数
            tone: 语气风格
            length: 长度级别
            
        Returns:
            生成的内容和元数据
        """
        start_time = time.time()
        
        try:
            # 1. 验证输入
            validated_params = self._validate_parameters(content_type, parameters)
            
            # 2. 从知识库检索相关信息
            knowledge_context = self._retrieve_knowledge_context(
                content_type, validated_params
            )
            
            # 3. 选择或生成模板
            template = self._select_template(content_type, tone, length)
            
            # 4. 生成内容
            content_text = self._generate_content_text(
                template, validated_params, knowledge_context, tone
            )
            
            # 5. 内容质量评估
            quality_metrics = self.quality_assessor.assess_quality(
                content_text, content_type, parameters
            )
            
            # 6. 优化建议
            optimization_suggestions = self._generate_optimization_suggestions(
                content_text, quality_metrics
            )
            
            # 7. 构建结果
            result = {
                "content_type": content_type,
                "content_text": content_text,
                "parameters": validated_params,
                "tone": tone,
                "length": length,
                "knowledge_context": knowledge_context,
                "quality_metrics": quality_metrics,
                "optimization_suggestions": optimization_suggestions,
                "generation_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "language": self.language,
                "content_id": self._generate_content_id(content_text, parameters)
            }
            
            logger.info(f"内容创建完成: 类型={content_type}, 质量={quality_metrics.get('overall_quality', 0):.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"内容创建失败: {content_type}, 错误: {str(e)}")
            
            return {
                "content_type": content_type,
                "error": str(e),
                "error_type": type(e).__name__,
                "generation_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
    
    def create_marketing_copy(self, product_info: Dict[str, Any],
                             target_audience: str,
                             platform: str = "general",
                             style: str = "persuasive") -> Dict[str, Any]:
        """
        创建营销文案
        
        Args:
            product_info: 产品信息
            target_audience: 目标受众
            platform: 平台类型
            style: 文案风格
            
        Returns:
            营销文案和元数据
        """
        parameters = {
            "product_info": product_info,
            "target_audience": target_audience,
            "platform": platform,
            "style": style,
            "purpose": "marketing"
        }
        
        return self.create_content("marketing_copy", parameters)
    
    def create_analysis_report(self, topic: str,
                              scope: Dict[str, Any],
                              audience: str = "business_executives",
                              format: str = "executive_summary") -> Dict[str, Any]:
        """
        创建分析报告
        
        Args:
            topic: 报告主题
            scope: 报告范围
            audience: 受众类型
            format: 报告格式
            
        Returns:
            分析报告和元数据
        """
        parameters = {
            "topic": topic,
            "scope": scope,
            "audience": audience,
            "format": format,
            "purpose": "analysis"
        }
        
        return self.create_content("analysis_report", parameters)
    
    def create_business_plan(self, business_concept: str,
                            market_analysis: Dict[str, Any],
                            financial_projections: Dict[str, Any],
                            template_type: str = "startup") -> Dict[str, Any]:
        """
        创建商业计划
        
        Args:
            business_concept: 商业概念
            market_analysis: 市场分析
            financial_projections: 财务预测
            template_type: 模板类型
            
        Returns:
            商业计划和元数据
        """
        parameters = {
            "business_concept": business_concept,
            "market_analysis": market_analysis,
            "financial_projections": financial_projections,
            "template_type": template_type,
            "purpose": "business_planning"
        }
        
        return self.create_content("business_plan", parameters)
    
    def create_social_media_post(self, content_theme: str,
                                platform: str,
                                target_hashtags: List[str],
                                call_to_action: str = "learn_more") -> Dict[str, Any]:
        """
        创建社交媒体帖子
        
        Args:
            content_theme: 内容主题
            platform: 平台名称
            target_hashtags: 目标标签
            call_to_action: 行动号召
            
        Returns:
            社交媒体帖子和元数据
        """
        parameters = {
            "content_theme": content_theme,
            "platform": platform,
            "target_hashtags": target_hashtags,
            "call_to_action": call_to_action,
            "purpose": "social_media"
        }
        
        return self.create_content("social_media_post", parameters)
    
    def _initialize_templates(self) -> Dict[str, Any]:
        """初始化内容模板"""
        templates = {
            "marketing_copy": {
                "product_intro": {
                    "template": "{{product_name}} - {{tagline}}\n\n{{product_description}}\n\n主要特点:\n{% for feature in features %}- {{feature}}\n{% endfor %}\n\n{{call_to_action}}",
                    "description": "产品介绍文案模板",
                    "variables": ["product_name", "tagline", "product_description", "features", "call_to_action"]
                },
                "social_ad": {
                    "template": "🔥 {{headline}} 🔥\n\n{{main_message}}\n\n{{benefits}}\n\n👉 {{action_button}}\n\n{{hashtags}}",
                    "description": "社交媒体广告模板",
                    "variables": ["headline", "main_message", "benefits", "action_button", "hashtags"]
                }
            },
            "analysis_report": {
                "executive_summary": {
                    "template": "# {{report_title}}\n\n## 执行摘要\n\n{{summary_content}}\n\n## 关键发现\n\n{% for finding in key_findings %}- {{finding}}\n{% endfor %}\n\n## 建议措施\n\n{% for recommendation in recommendations %}- {{recommendation}}\n{% endfor %}",
                    "description": "执行摘要模板",
                    "variables": ["report_title", "summary_content", "key_findings", "recommendations"]
                },
                "market_analysis": {
                    "template": "# {{market_name}}市场分析\n\n## 市场概况\n{{market_overview}}\n\n## 趋势分析\n{{trend_analysis}}\n\n## 竞争格局\n{{competitive_landscape}}\n\n## 机会评估\n{{opportunity_assessment}}",
                    "description": "市场分析报告模板",
                    "variables": ["market_name", "market_overview", "trend_analysis", "competitive_landscape", "opportunity_assessment"]
                }
            },
            "business_plan": {
                "startup": {
                    "template": "# {{business_name}}商业计划书\n\n## 1. 执行摘要\n{{executive_summary}}\n\n## 2. 公司描述\n{{company_description}}\n\n## 3. 市场分析\n{{market_analysis}}\n\n## 4. 产品与服务\n{{products_services}}\n\n## 5. 营销策略\n{{marketing_strategy}}\n\n## 6. 管理团队\n{{management_team}}\n\n## 7. 财务预测\n{{financial_projections}}",
                    "description": "创业公司商业计划模板",
                    "variables": ["business_name", "executive_summary", "company_description", "market_analysis", "products_services", "marketing_strategy", "management_team", "financial_projections"]
                }
            },
            "social_media_post": {
                "linkedin": {
                    "template": "{{headline}}\n\n{{content_body}}\n\n{{insight}}\n\n#{{industry}} #{{topic}} {{hashtags}}",
                    "description": "LinkedIn专业帖子模板",
                    "variables": ["headline", "content_body", "insight", "industry", "topic", "hashtags"]
                },
                "twitter": {
                    "template": "{{headline}}\n\n{{key_message}}\n\n{{link}}\n\n{{hashtags}}",
                    "description": "Twitter推文模板",
                    "variables": ["headline", "key_message", "link", "hashtags"]
                },
                "instagram": {
                    "template": "{{caption}}\n\n{{hashtags}}",
                    "description": "Instagram帖子模板",
                    "variables": ["caption", "hashtags"]
                }
            }
        }
        
        return templates
    
    def _initialize_style_guides(self) -> Dict[str, Any]:
        """初始化风格指南"""
        style_guides = {
            "tone_options": {
                "professional": {
                    "description": "专业正式",
                    "characteristics": ["清晰", "准确", "权威", "客观"],
                    "avoid": ["俚语", "夸张", "情绪化", "模糊"]
                },
                "persuasive": {
                    "description": "说服性营销",
                    "characteristics": ["引人入胜", "价值导向", "行动号召", "客户利益"],
                    "avoid": ["技术术语", "复杂表述", "被动语态"]
                },
                "friendly": {
                    "description": "友好亲切",
                    "characteristics": ["对话式", "温暖", "易理解", "积极"],
                    "avoid": ["正式", "生硬", "技术性", "冷漠"]
                },
                "educational": {
                    "description": "教育性",
                    "characteristics": ["结构清晰", "解释充分", "实例丰富", "实用性强"],
                    "avoid": ["推销性", "主观", "不完整"]
                }
            },
            "length_options": {
                "short": {
                    "description": "简短精炼",
                    "word_range": [50, 200],
                    "focus": "核心信息"
                },
                "medium": {
                    "description": "适中详细",
                    "word_range": [200, 800],
                    "focus": "全面阐述"
                },
                "long": {
                    "description": "详细深入",
                    "word_range": [800, 2000],
                    "focus": "深度分析"
                }
            },
            "brand_standards": {
                "sellai": {
                    "voice": "专业、创新、前瞻",
                    "personality": "可靠的技术专家，贴心的商业伙伴",
                    "key_messages": ["全球视野", "AI驱动", "商业价值", "持续进化"],
                    "preferred_terms": ["AI商业合伙人", "全球智能", "数字化转型", "智能决策"],
                    "avoided_terms": ["自动化工具", "简单机器人", "预设程序", "固定模板"]
                }
            }
        }
        
        return style_guides
    
    def _validate_parameters(self, content_type: str, 
                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数"""
        validated = parameters.copy()
        
        # 检查必需参数
        required_params = {
            "marketing_copy": ["product_info", "target_audience"],
            "analysis_report": ["topic", "scope"],
            "business_plan": ["business_concept", "market_analysis"],
            "social_media_post": ["content_theme", "platform"]
        }
        
        if content_type in required_params:
            for param in required_params[content_type]:
                if param not in parameters:
                    raise ValueError(f"必需参数缺失: {param}")
        
        # 添加默认值
        validated.setdefault("language", self.language)
        validated.setdefault("purpose", content_type)
        
        return validated
    
    def _retrieve_knowledge_context(self, content_type: str,
                                   parameters: Dict[str, Any]) -> Dict[str, Any]:
        """检索知识上下文"""
        if not self.nli:
            return {"status": "no_integration", "content": []}
        
        try:
            # 构建查询问题
            query_questions = self._build_knowledge_queries(content_type, parameters)
            
            knowledge_results = []
            
            for question in query_questions:
                try:
                    result = self.nli.query_knowledge_base(
                        question=question,
                        max_results=3
                    )
                    
                    if result.get("answers"):
                        knowledge_results.append({
                            "question": question,
                            "answers": result["answers"],
                            "sources": result.get("sources", [])
                        })
                
                except Exception as query_error:
                    logger.warning(f"知识查询失败: {question}, 错误: {str(query_error)}")
            
            return {
                "status": "success",
                "content": knowledge_results,
                "query_count": len(query_questions),
                "result_count": len(knowledge_results)
            }
            
        except Exception as e:
            logger.error(f"知识上下文检索失败: {str(e)}")
            
            return {
                "status": "error",
                "error": str(e),
                "content": []
            }
    
    def _build_knowledge_queries(self, content_type: str,
                                parameters: Dict[str, Any]) -> List[str]:
        """构建知识查询"""
        queries = []
        
        if content_type == "marketing_copy":
            product_info = parameters.get("product_info", {})
            product_name = product_info.get("name", "")
            product_category = product_info.get("category", "")
            target_audience = parameters.get("target_audience", "")
            
            queries.append(f"{product_name} {product_category} 产品特点优势")
            queries.append(f"{target_audience} 目标受众偏好和需求")
            queries.append(f"{product_category} 行业市场趋势和竞争格局")
        
        elif content_type == "analysis_report":
            topic = parameters.get("topic", "")
            scope = parameters.get("scope", {})
            
            queries.append(f"{topic} 最新发展动态和趋势")
            queries.append(f"{topic} 市场规模和增长率数据")
            queries.append(f"{topic} 主要竞争对手和市场份额")
            queries.append(f"{topic} 未来预测和发展机会")
        
        elif content_type == "business_plan":
            business_concept = parameters.get("business_concept", "")
            market_analysis = parameters.get("market_analysis", {})
            
            queries.append(f"{business_concept} 商业模式和盈利方式")
            queries.append(f"{business_concept} 所在市场增长潜力")
            queries.append(f"初创企业融资策略和估值方法")
        
        elif content_type == "social_media_post":
            content_theme = parameters.get("content_theme", "")
            platform = parameters.get("platform", "")
            
            queries.append(f"{content_theme} 在{platform}平台的传播策略")
            queries.append(f"{platform} 平台最新算法和热门话题")
            queries.append(f"{content_theme} 相关成功案例和最佳实践")
        
        # 添加语言信息
        if self.language != "zh-CN":
            queries = [f"{q} ({self.language})" for q in queries]
        
        return queries[:5]  # 限制最多5个查询
    
    def _select_template(self, content_type: str,
                        tone: str, length: str) -> Dict[str, Any]:
        """选择模板"""
        if content_type not in self.templates:
            # 默认使用通用模板
            return {
                "template": "{{content}}",
                "description": "通用内容模板",
                "variables": ["content"]
            }
        
        templates_for_type = self.templates[content_type]
        
        # 根据语气和长度选择合适的模板
        # 这里简化处理，实际应用中应该有更复杂的匹配逻辑
        if len(templates_for_type) > 0:
            return next(iter(templates_for_type.values()))
        else:
            return {
                "template": "{{content}}",
                "description": "默认内容模板",
                "variables": ["content"]
            }
    
    def _generate_content_text(self, template: Dict[str, Any],
                              parameters: Dict[str, Any],
                              knowledge_context: Dict[str, Any],
                              tone: str) -> str:
        """生成内容文本"""
        template_str = template["template"]
        template_vars = template.get("variables", [])
        
        # 准备模板数据
        template_data = self._prepare_template_data(
            parameters, knowledge_context, tone
        )
        
        # 应用模板
        if JINJA_SUPPORT and "jinja" in template_str:
            # 使用Jinja2模板引擎
            try:
                env = jinja2.Environment()
                jinja_template = env.from_string(template_str)
                content_text = jinja_template.render(**template_data)
            except Exception as e:
                logger.warning(f"Jinja模板渲染失败，使用字符串替换: {str(e)}")
                content_text = self._simple_template_replace(template_str, template_data)
        else:
            # 简单字符串替换
            content_text = self._simple_template_replace(template_str, template_data)
        
        # 应用风格指南
        content_text = self._apply_style_guide(content_text, tone)
        
        return content_text
    
    def _prepare_template_data(self, parameters: Dict[str, Any],
                              knowledge_context: Dict[str, Any],
                              tone: str) -> Dict[str, Any]:
        """准备模板数据"""
        data = parameters.copy()
        
        # 添加知识上下文中的关键信息
        if knowledge_context.get("status") == "success":
            knowledge_content = knowledge_context.get("content", [])
            
            # 提取关键事实和数据
            key_facts = []
            key_data = []
            
            for item in knowledge_content:
                if "answers" in item:
                    for answer in item["answers"]:
                        if isinstance(answer, dict) and "content" in answer:
                            content = answer["content"]
                            # 提取数字和关键术语
                            numbers = re.findall(r'\d+\.?\d*%?', content)
                            if numbers:
                                key_data.extend(numbers)
                            
                            # 添加内容
                            if len(content) < 200:
                                key_facts.append(content)
            
            data["key_facts"] = key_facts[:5]  # 限制最多5个关键事实
            data["key_data"] = key_data[:5]    # 限制最多5个关键数据
        
        # 添加语气相关变量
        tone_guide = self.style_guides["tone_options"].get(tone, {})
        data["tone_characteristics"] = tone_guide.get("characteristics", [])
        
        # 添加品牌标准
        data["brand_voice"] = self.style_guides["brand_standards"]["sellai"]["voice"]
        
        return data
    
    def _simple_template_replace(self, template_str: str,
                                data: Dict[str, Any]) -> str:
        """简单模板替换"""
        content = template_str
        
        # 替换变量
        for key, value in data.items():
            placeholder = "{{" + key + "}}"
            
            if placeholder in content:
                if isinstance(value, list):
                    # 列表处理：转换为字符串
                    if value and isinstance(value[0], dict):
                        # 字典列表：提取文本
                        text_values = []
                        for item in value:
                            if isinstance(item, dict) and "text" in item:
                                text_values.append(item["text"])
                            elif isinstance(item, str):
                                text_values.append(item)
                        value_str = "\n".join(f"- {v}" for v in text_values[:5])
                    else:
                        value_str = "\n".join(f"- {v}" for v in value[:10])
                elif isinstance(value, dict):
                    # 字典处理：转换为可读文本
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    value_str = str(value)
                
                content = content.replace(placeholder, value_str)
        
        # 清理未替换的变量
        content = re.sub(r'\{\{.*?\}\}', '', content)
        
        return content.strip()
    
    def _apply_style_guide(self, content_text: str, tone: str) -> str:
        """应用风格指南"""
        # 获取语气指南
        tone_guide = self.style_guides["tone_options"].get(tone, {})
        avoid_words = tone_guide.get("avoid", [])
        
        # 获取品牌标准
        brand_guide = self.style_guides["brand_standards"]["sellai"]
        preferred_terms = brand_guide.get("preferred_terms", [])
        avoided_terms = brand_guide.get("avoided_terms", [])
        
        # 1. 避免使用负面词汇
        for word in avoid_words:
            # 简化实现：实际应用需要更复杂的语言处理
            pass
        
        # 2. 优先使用品牌偏好术语
        content_words = content_text.split()
        
        # 3. 确保内容符合品牌声音
        # （这里主要是概念性实现，实际应用需要更复杂的NLP处理）
        
        return content_text
    
    def _generate_optimization_suggestions(self, content_text: str,
                                          quality_metrics: Dict[str, float]) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        # 基于质量指标生成建议
        overall_quality = quality_metrics.get("overall_quality", 0.5)
        
        if overall_quality < 0.7:
            suggestions.append("内容质量有待提升，建议增加事实依据和具体数据")
        
        readability = quality_metrics.get("readability_score", 0.5)
        if readability < 0.6:
            suggestions.append("可读性较低，建议简化句子结构，使用更清晰的语言")
        
        brand_alignment = quality_metrics.get("brand_alignment_score", 0.5)
        if brand_alignment < 0.7:
            suggestions.append("品牌一致性需要加强，请确保内容符合SellAI专业创新的品牌形象")
        
        # 基于内容特性生成建议
        word_count = len(content_text.split())
        if word_count < 100:
            suggestions.append("内容较为简短，可补充更多细节和背景信息")
        elif word_count > 800:
            suggestions.append("内容较长，建议考虑分段或添加摘要")
        
        # 检查是否有具体数据
        has_numbers = bool(re.search(r'\d+', content_text))
        if not has_numbers and overall_quality < 0.8:
            suggestions.append("缺乏具体数据支持，建议添加相关统计数字或研究成果")
        
        return suggestions[:5]  # 限制最多5条建议
    
    def _generate_content_id(self, content_text: str, parameters: Dict[str, Any]) -> str:
        """生成内容ID"""
        # 基于内容、参数和时间生成唯一ID
        input_str = f"{content_text[:100]}{json.dumps(parameters, sort_keys=True)}{datetime.now().isoformat()}"
        
        return hashlib.md5(input_str.encode()).hexdigest()[:16]


class ContentQualityAssessor:
    """内容质量评估器"""
    
    def __init__(self, language: str = "zh-CN"):
        self.language = language
        
        # 质量指标权重
        self.weights = {
            "readability_score": 0.25,
            "factual_accuracy": 0.25,
            "brand_alignment_score": 0.20,
            "engagement_potential": 0.15,
            "structure_quality": 0.15
        }
    
    def assess_quality(self, content_text: str,
                      content_type: str,
                      parameters: Dict[str, Any]) -> Dict[str, float]:
        """
        评估内容质量
        
        Args:
            content_text: 内容文本
            content_type: 内容类型
            parameters: 生成参数
            
        Returns:
            质量指标
        """
        metrics = {}
        
        try:
            # 1. 可读性评分
            metrics["readability_score"] = self._assess_readability(content_text)
            
            # 2. 事实准确性（基于知识上下文）
            metrics["factual_accuracy"] = self._assess_factual_accuracy(
                content_text, parameters
            )
            
            # 3. 品牌一致性
            metrics["brand_alignment_score"] = self._assess_brand_alignment(content_text)
            
            # 4. 参与度潜力
            metrics["engagement_potential"] = self._assess_engagement_potential(
                content_text, content_type
            )
            
            # 5. 结构质量
            metrics["structure_quality"] = self._assess_structure_quality(content_text)
            
            # 计算总体质量
            metrics["overall_quality"] = self._calculate_overall_quality(metrics)
            
            # 添加解释
            metrics["quality_interpretation"] = self._interpret_quality(metrics["overall_quality"])
            
        except Exception as e:
            logger.error(f"内容质量评估失败: {str(e)}")
            
            # 设置默认值
            metrics = {
                "readability_score": 0.5,
                "factual_accuracy": 0.5,
                "brand_alignment_score": 0.5,
                "engagement_potential": 0.5,
                "structure_quality": 0.5,
                "overall_quality": 0.5,
                "quality_interpretation": "评估失败",
                "error": str(e)
            }
        
        return metrics
    
    def _assess_readability(self, text: str) -> float:
        """评估可读性"""
        try:
            # 简单可读性指标
            sentences = re.split(r'[.!?。！？]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return 0.5
            
            words = text.split()
            
            # 句子平均长度
            if len(sentences) > 0:
                avg_sentence_length = len(words) / len(sentences)
            else:
                avg_sentence_length = 15  # 默认值
            
            # 单词平均长度
            if len(words) > 0:
                avg_word_length = sum(len(w) for w in words) / len(words)
            else:
                avg_word_length = 5  # 默认值
            
            # 根据语言调整评分
            if self.language.startswith("zh"):
                # 中文可读性：句子长度适中为好
                if avg_sentence_length < 10:
                    sentence_score = 0.8
                elif avg_sentence_length < 20:
                    sentence_score = 0.9
                elif avg_sentence_length < 30:
                    sentence_score = 0.7
                else:
                    sentence_score = 0.5
                
                # 段落结构
                paragraphs = text.split('\n\n')
                if len(paragraphs) >= 2:
                    structure_score = 0.8
                else:
                    structure_score = 0.5
                
                readability = 0.6 * sentence_score + 0.4 * structure_score
            
            else:
                # 英文可读性：使用简单指标
                if avg_sentence_length < 15 and avg_word_length < 5:
                    readability = 0.9
                elif avg_sentence_length < 25 and avg_word_length < 6:
                    readability = 0.7
                else:
                    readability = 0.5
            
            return max(0.0, min(1.0, readability))
            
        except Exception as e:
            logger.warning(f"可读性评估异常: {str(e)}")
            return 0.5
    
    def _assess_factual_accuracy(self, text: str, 
                                parameters: Dict[str, Any]) -> float:
        """评估事实准确性"""
        # 简化实现：检查文本中的数字和事实陈述
        # 实际应用中需要连接知识库进行验证
        
        words = text.split()
        
        # 统计数字引用
        number_pattern = r'\b\d+\.?\d*%?\b'
        numbers = re.findall(number_pattern, text)
        
        # 统计专业术语
        professional_terms = [
            "AI", "人工智能", "机器学习", "数据分析", "商业智能",
            "市场", "策略", "优化", "效率", "增长", "价值"
        ]
        
        term_count = sum(1 for term in professional_terms if term in text)
        
        # 综合评分
        if numbers:
            # 有数据支持，得分较高
            if term_count >= 3:
                return 0.85
            else:
                return 0.7
        else:
            # 无数据支持，得分较低
            if term_count >= 2:
                return 0.6
            else:
                return 0.4
    
    def _assess_brand_alignment(self, text: str) -> float:
        """评估品牌一致性"""
        # SellAI品牌关键词
        brand_keywords = [
            "AI商业合伙人", "全球智能", "数字化转型", "智能决策",
            "创新", "专业", "前瞻", "可靠", "贴心", "进化"
        ]
        
        positive_terms = [
            "领先", "卓越", "优秀", "高效", "精准", "可靠"
        ]
        
        negative_terms = [
            "缺陷", "问题", "不足", "失败", "错误"
        ]
        
        # 检查品牌关键词
        brand_match = sum(1 for keyword in brand_keywords if keyword in text)
        brand_score = min(1.0, brand_match / 3.0)  # 出现3个关键词得满分
        
        # 检查正面词汇
        positive_match = sum(1 for term in positive_terms if term in text)
        positive_score = min(1.0, positive_match / 2.0)
        
        # 检查负面词汇（应避免）
        negative_match = sum(1 for term in negative_terms if term in text)
        if negative_match > 0:
            negative_penalty = 0.2 * negative_match
        else:
            negative_penalty = 0.0
        
        # 综合品牌一致性评分
        alignment = 0.6 * brand_score + 0.4 * positive_score - negative_penalty
        
        return max(0.0, min(1.0, alignment))
    
    def _assess_engagement_potential(self, text: str,
                                    content_type: str) -> float:
        """评估参与度潜力"""
        engagement_factors = {
            "question_count": len(re.findall(r'[？?]', text)),
            "exclamation_count": len(re.findall(r'[！!]', text)),
            "cta_phrases": len(re.findall(r'(?:请|建议|欢迎|点击|了解更多|立即|现在)', text)),
            "hashtag_count": len(re.findall(r'#\w+', text)),
            "link_count": len(re.findall(r'https?://\S+', text))
        }
        
        # 根据内容类型调整权重
        type_weights = {
            "marketing_copy": {"question": 0.3, "exclamation": 0.3, "cta": 0.4},
            "social_media_post": {"question": 0.2, "exclamation": 0.2, "cta": 0.3, "hashtag": 0.3},
            "analysis_report": {"question": 0.4, "cta": 0.6}
        }
        
        if content_type in type_weights:
            weights = type_weights[content_type]
            
            # 计算参与度得分
            engagement_score = 0.0
            
            if "question" in weights:
                question_score = min(1.0, engagement_factors["question_count"] / 3.0)
                engagement_score += weights["question"] * question_score
            
            if "exclamation" in weights:
                exclamation_score = min(1.0, engagement_factors["exclamation_count"] / 3.0)
                engagement_score += weights["exclamation"] * exclamation_score
            
            if "cta" in weights:
                cta_score = min(1.0, engagement_factors["cta_phrases"] / 2.0)
                engagement_score += weights["cta"] * cta_score
            
            if "hashtag" in weights:
                hashtag_score = min(1.0, engagement_factors["hashtag_count"] / 5.0)
                engagement_score += weights["hashtag"] * hashtag_score
            
            return max(0.0, min(1.0, engagement_score))
        else:
            # 默认评分
            total_engagement = sum(engagement_factors.values())
            return min(1.0, total_engagement / 10.0)
    
    def _assess_structure_quality(self, text: str) -> float:
        """评估结构质量"""
        # 检查结构元素
        structure_elements = {
            "has_headings": bool(re.search(r'^#+\s+.+$', text, re.MULTILINE)),
            "has_lists": bool(re.search(r'^[*-]\s+.+$', text, re.MULTILINE)),
            "has_paragraphs": len(text.split('\n\n')) >= 2,
            "has_length": len(text.split()) >= 100
        }
        
        # 计算结构得分
        element_count = sum(1 for value in structure_elements.values() if value)
        total_elements = len(structure_elements)
        
        structure_score = element_count / total_elements
        
        # 添加连贯性检查
        sentences = re.split(r'[.!?。！？]+', text)
        if len(sentences) >= 3:
            # 检查句子多样性
            avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 8 <= avg_length <= 25:
                coherence_bonus = 0.2
            else:
                coherence_bonus = 0.0
        else:
            coherence_bonus = 0.0
        
        final_score = min(1.0, structure_score + coherence_bonus)
        
        return max(0.0, min(1.0, final_score))
    
    def _calculate_overall_quality(self, metrics: Dict[str, float]) -> float:
        """计算总体质量"""
        weighted_sum = 0.0
        total_weight = 0.0
        
        for dimension, weight in self.weights.items():
            if dimension in metrics:
                weighted_sum += metrics[dimension] * weight
                total_weight += weight
        
        if total_weight == 0:
            return sum(metrics.values()) / max(len(metrics), 1)
        
        return weighted_sum / total_weight
    
    def _interpret_quality(self, quality_score: float) -> str:
        """解释质量分数"""
        if quality_score >= 0.9:
            return "质量卓越，可直接使用"
        elif quality_score >= 0.8:
            return "质量优秀，建议轻微优化"
        elif quality_score >= 0.7:
            return "质量良好，需要部分优化"
        elif quality_score >= 0.6:
            return "质量一般，建议全面优化"
        else:
            return "质量较差，需要重写"


# 便捷函数
def create_content_workshop(api_key: Optional[str] = None,
                           language: str = "zh-CN") -> ContentCreationWorkshop:
    """
    创建内容创作工坊的便捷函数
    
    Args:
        api_key: Notebook LM API密钥
        language: 目标语言
        
    Returns:
        内容创作工坊实例
    """
    from src.notebook_lm_integration import NotebookLMIntegration
    
    nli = None
    if api_key:
        nli = NotebookLMIntegration(api_key=api_key)
    
    workshop = ContentCreationWorkshop(nli, language)
    
    return workshop


if __name__ == "__main__":
    # 模块测试
    print("内容创作工坊模块测试")
    
    # 创建工坊实例
    workshop = ContentCreationWorkshop()
    
    # 测试营销文案生成
    product_info = {
        "name": "SellAI Pro",
        "category": "AI商业平台",
        "description": "下一代全球AI商业合伙人系统",
        "features": ["24小时自动运营", "无限AI分身", "全球商机洞察", "智能决策支持"]
    }
    
    result = workshop.create_marketing_copy(
        product_info=product_info,
        target_audience="中小企业主",
        style="persuasive"
    )
    
    print(f"内容类型: {result['content_type']}")
    print(f"内容长度: {len(result['content_text'])} 字符")
    print(f"生成时间: {result['generation_time']:.2f} 秒")
    print(f"质量评分: {result['quality_metrics']['overall_quality']:.2f}")
    print(f"优化建议: {result['optimization_suggestions'][:2]}")
    print("\n生成内容预览:")
    print(result['content_text'][:200] + "...")