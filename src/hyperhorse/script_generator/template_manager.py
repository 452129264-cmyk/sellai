#!/usr/bin/env python3
"""
脚本模板管理器
管理全行业视频脚本模板库，支持模板选择、匹配与个性化填充
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random

logger = logging.getLogger(__name__)

@dataclass
class TemplateMetadata:
    """模板元数据"""
    template_id: str
    name: str
    description: str
    script_type: str
    category: str
    audience: str
    platform: str
    difficulty: str  # beginner, intermediate, advanced
    conversion_rate: float  # 预估转化率
    engagement_score: float  # 预估互动得分
    cultural_adaptability: float  # 文化适应性
    tags: List[str]


class TemplateManager:
    """模板管理器"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        初始化模板管理器
        
        Args:
            templates_dir: 模板目录路径，可选
        """
        # 模板目录
        if templates_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.templates_dir = os.path.join(base_dir, 'templates')
        else:
            self.templates_dir = templates_dir
        
        # 确保模板目录存在
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # 加载模板库
        self.templates = self._load_templates()
        self.template_metadata = self._load_metadata()
        
        logger.info(f"模板管理器初始化完成，共加载{len(self.templates)}个模板")
    
    def select_template(self,
                       script_type: str,
                       product_category: str,
                       platform: str,
                       audience: str) -> Dict[str, Any]:
        """
        选择最适合的模板
        
        Args:
            script_type: 脚本类型
            product_category: 产品类别
            platform: 目标平台
            audience: 目标受众
            
        Returns:
            Dict[str, Any]: 选中的模板
        """
        logger.info(f"选择模板，脚本类型：{script_type}，产品类别：{product_category}，平台：{platform}")
        
        # 筛选候选模板
        candidates = []
        
        for template_id, template in self.templates.items():
            metadata = self.template_metadata.get(template_id)
            if metadata is None:
                continue
            
            # 计算匹配度
            match_score = self._calculate_match_score(
                metadata=metadata,
                script_type=script_type,
                product_category=product_category,
                platform=platform,
                audience=audience
            )
            
            if match_score > 0.5:  # 匹配度阈值
                candidates.append((match_score, template_id, template))
        
        if not candidates:
            logger.warning("未找到匹配模板，使用默认模板")
            return self._get_default_template(script_type)
        
        # 按匹配度排序
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        # 选择最佳模板
        best_score, best_id, best_template = candidates[0]
        
        logger.info(f"选择模板：{best_id}，匹配度：{best_score:.2f}")
        return best_template
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取模板"""
        return self.templates.get(template_id)
    
    def list_templates(self, 
                      script_type: Optional[str] = None,
                      category: Optional[str] = None,
                      platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出模板
        
        Args:
            script_type: 脚本类型过滤
            category: 产品类别过滤
            platform: 平台过滤
            
        Returns:
            List[Dict[str, Any]]: 模板列表
        """
        templates_list = []
        
        for template_id, template in self.templates.items():
            metadata = self.template_metadata.get(template_id)
            if metadata is None:
                continue
            
            # 应用过滤条件
            if script_type and metadata.script_type != script_type:
                continue
            if category and metadata.category != category:
                continue
            if platform and metadata.platform != platform:
                continue
            
            templates_list.append({
                'template_id': template_id,
                'name': metadata.name,
                'description': metadata.description,
                'script_type': metadata.script_type,
                'category': metadata.category,
                'platform': metadata.platform,
                'audience': metadata.audience,
                'conversion_rate': metadata.conversion_rate,
                'engagement_score': metadata.engagement_score
            })
        
        return templates_list
    
    def create_template(self,
                       template_data: Dict[str, Any],
                       metadata: Dict[str, Any]) -> str:
        """
        创建新模板
        
        Args:
            template_data: 模板内容
            metadata: 模板元数据
            
        Returns:
            str: 创建的模板ID
        """
        # 生成模板ID
        template_id = metadata.get('template_id')
        if not template_id:
            template_id = f"template_{len(self.templates) + 1:04d}"
        
        # 保存模板
        template_path = os.path.join(self.templates_dir, f"{template_id}.json")
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, ensure_ascii=False, indent=2)
        
        # 更新内存中的模板
        self.templates[template_id] = template_data
        
        # 创建元数据对象
        template_metadata = TemplateMetadata(
            template_id=template_id,
            name=metadata.get('name', '未命名模板'),
            description=metadata.get('description', ''),
            script_type=metadata.get('script_type', 'general'),
            category=metadata.get('category', 'general'),
            audience=metadata.get('audience', 'general'),
            platform=metadata.get('platform', 'tiktok'),
            difficulty=metadata.get('difficulty', 'intermediate'),
            conversion_rate=metadata.get('conversion_rate', 0.5),
            engagement_score=metadata.get('engagement_score', 0.6),
            cultural_adaptability=metadata.get('cultural_adaptability', 0.7),
            tags=metadata.get('tags', [])
        )
        
        # 保存元数据
        self.template_metadata[template_id] = template_metadata
        self._save_metadata()
        
        logger.info(f"创建模板成功：{template_id}")
        return template_id
    
    def update_template(self,
                       template_id: str,
                       template_data: Optional[Dict[str, Any]] = None,
                       metadata_update: Optional[Dict[str, Any]] = None) -> bool:
        """
        更新模板
        
        Args:
            template_id: 模板ID
            template_data: 更新的模板内容，可选
            metadata_update: 更新的元数据，可选
            
        Returns:
            bool: 更新是否成功
        """
        if template_id not in self.templates:
            logger.error(f"模板不存在：{template_id}")
            return False
        
        # 更新模板内容
        if template_data is not None:
            template_path = os.path.join(self.templates_dir, f"{template_id}.json")
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            self.templates[template_id] = template_data
        
        # 更新元数据
        if metadata_update is not None and template_id in self.template_metadata:
            metadata = self.template_metadata[template_id]
            
            # 更新字段
            for key, value in metadata_update.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
            
            # 保存更新
            self._save_metadata()
        
        logger.info(f"更新模板成功：{template_id}")
        return True
    
    def delete_template(self, template_id: str) -> bool:
        """
        删除模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            bool: 删除是否成功
        """
        if template_id not in self.templates:
            logger.error(f"模板不存在：{template_id}")
            return False
        
        # 删除模板文件
        template_path = os.path.join(self.templates_dir, f"{template_id}.json")
        if os.path.exists(template_path):
            os.remove(template_path)
        
        # 删除内存中的模板
        del self.templates[template_id]
        
        # 删除元数据
        if template_id in self.template_metadata:
            del self.template_metadata[template_id]
            self._save_metadata()
        
        logger.info(f"删除模板成功：{template_id}")
        return True
    
    def search_templates(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索模板
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        results = []
        query_lower = query.lower()
        
        for template_id, metadata in self.template_metadata.items():
            # 搜索名称和描述
            name_match = query_lower in metadata.name.lower()
            desc_match = query_lower in metadata.description.lower()
            tag_match = any(query_lower in tag.lower() for tag in metadata.tags)
            
            if name_match or desc_match or tag_match:
                results.append({
                    'template_id': template_id,
                    'name': metadata.name,
                    'description': metadata.description,
                    'script_type': metadata.script_type,
                    'category': metadata.category,
                    'platform': metadata.platform,
                    'match_type': 'name' if name_match else 'description' if desc_match else 'tag'
                })
        
        return results
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载所有模板"""
        templates = {}
        
        if not os.path.exists(self.templates_dir):
            logger.warning(f"模板目录不存在：{self.templates_dir}")
            return templates
        
        # 加载JSON模板文件
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.json'):
                template_id = filename[:-5]  # 移除.json后缀
                template_path = os.path.join(self.templates_dir, filename)
                
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    templates[template_id] = template_data
                except Exception as e:
                    logger.error(f"加载模板失败：{filename}，错误：{e}")
        
        # 如果没有模板文件，创建默认模板
        if not templates:
            logger.info("未找到模板文件，创建默认模板库")
            self._create_default_templates()
            templates = self._load_templates()  # 重新加载
        
        return templates
    
    def _load_metadata(self) -> Dict[str, TemplateMetadata]:
        """加载模板元数据"""
        metadata_path = os.path.join(self.templates_dir, 'metadata.json')
        
        if not os.path.exists(metadata_path):
            logger.warning("元数据文件不存在，从模板文件生成")
            return self._generate_metadata_from_templates()
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_dict = json.load(f)
            
            metadata_objects = {}
            for template_id, meta_dict in metadata_dict.items():
                metadata_objects[template_id] = TemplateMetadata(**meta_dict)
            
            return metadata_objects
        except Exception as e:
            logger.error(f"加载元数据失败：{e}")
            return self._generate_metadata_from_templates()
    
    def _save_metadata(self):
        """保存模板元数据"""
        metadata_path = os.path.join(self.templates_dir, 'metadata.json')
        
        metadata_dict = {}
        for template_id, metadata in self.template_metadata.items():
            metadata_dict[template_id] = asdict(metadata)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, ensure_ascii=False, indent=2)
    
    def _generate_metadata_from_templates(self) -> Dict[str, TemplateMetadata]:
        """从模板文件生成元数据"""
        metadata_objects = {}
        
        for template_id, template in self.templates.items():
            # 从模板数据中提取元数据
            name = template.get('name', '未命名模板')
            description = template.get('description', '')
            script_type = template.get('script_type', 'general')
            category = template.get('category', 'general')
            audience = template.get('audience', 'general')
            platform = template.get('platform', 'tiktok')
            
            metadata = TemplateMetadata(
                template_id=template_id,
                name=name,
                description=description,
                script_type=script_type,
                category=category,
                audience=audience,
                platform=platform,
                difficulty='intermediate',
                conversion_rate=0.5,
                engagement_score=0.6,
                cultural_adaptability=0.7,
                tags=[]
            )
            
            metadata_objects[template_id] = metadata
        
        # 保存生成的元数据
        self._save_metadata()
        
        return metadata_objects
    
    def _calculate_match_score(self,
                              metadata: TemplateMetadata,
                              script_type: str,
                              product_category: str,
                              platform: str,
                              audience: str) -> float:
        """计算模板匹配度得分"""
        score = 0.0
        max_score = 0.0
        
        # 脚本类型匹配 (权重30%)
        if metadata.script_type == script_type:
            score += 30
        max_score += 30
        
        # 产品类别匹配 (权重25%)
        if metadata.category == product_category or metadata.category == 'general':
            score += 25
        max_score += 25
        
        # 平台匹配 (权重20%)
        if metadata.platform == platform or metadata.platform == 'multi':
            score += 20
        max_score += 20
        
        # 受众匹配 (权重15%)
        if metadata.audience == audience or metadata.audience == 'general':
            score += 15
        max_score += 15
        
        # 转化率加成 (权重10%)
        conversion_bonus = metadata.conversion_rate * 10
        score += conversion_bonus
        max_score += 10
        
        # 归一化到0-1范围
        return score / max_score if max_score > 0 else 0
    
    def _create_default_templates(self):
        """创建默认模板库"""
        default_templates = [
            {
                'template_id': 'product_demo_001',
                'name': '快速产品展示模板',
                'description': '适用于电商产品的快速展示，突出产品卖点和使用场景',
                'script_type': 'product_demo',
                'category': 'general',
                'audience': 'general',
                'platform': 'tiktok',
                'difficulty': 'beginner',
                'conversion_rate': 0.6,
                'engagement_score': 0.7,
                'cultural_adaptability': 0.8,
                'tags': ['product', 'demo', 'ecommerce'],
                'content': {
                    'title_template': '你需要的{product_name}在这里！',
                    'description_template': '为什么每个人都爱这款{product_name}？看看就知道了',
                    'scenes': [
                        {
                            'scene_number': 1,
                            'duration_seconds': 5,
                            'visual': '产品特写镜头',
                            'text': '这是{product_name}',
                            'audio': '轻快背景音乐'
                        },
                        {
                            'scene_number': 2,
                            'duration_seconds': 10,
                            'visual': '产品使用场景',
                            'text': '解决{problem_description}',
                            'audio': '节奏加快'
                        },
                        {
                            'scene_number': 3,
                            'duration_seconds': 10,
                            'visual': '产品功能展示',
                            'text': '特点：{feature_1}, {feature_2}',
                            'audio': '高潮部分'
                        },
                        {
                            'scene_number': 4,
                            'duration_seconds': 5,
                            'visual': '行动号召',
                            'text': '立即购买{product_name}',
                            'audio': '逐渐结束'
                        }
                    ],
                    'call_to_action': '点击链接购买',
                    'hashtags': ['#{product_category}', '#productdemo', '#musthave']
                }
            },
            {
                'template_id': 'brand_story_001',
                'name': '品牌故事叙事模板',
                'description': '讲述品牌背后的故事，建立情感连接和品牌忠诚度',
                'script_type': 'brand_story',
                'category': 'luxury',
                'audience': 'professionals',
                'platform': 'instagram',
                'difficulty': 'advanced',
                'conversion_rate': 0.4,
                'engagement_score': 0.8,
                'cultural_adaptability': 0.6,
                'tags': ['brand', 'story', 'narrative'],
                'content': {
                    'title_template': '{brand_name}的故事',
                    'description_template': '从{origin_story}到今天的旅程',
                    'scenes': [
                        {
                            'scene_number': 1,
                            'duration_seconds': 15,
                            'visual': '品牌起源场景',
                            'text': '一切始于{year}',
                            'audio': '深情叙事音乐'
                        },
                        {
                            'scene_number': 2,
                            'duration_seconds': 20,
                            'visual': '发展历程展示',
                            'text': '多年来的坚持与创新',
                            'audio': '渐进式音乐'
                        },
                        {
                            'scene_number': 3,
                            'duration_seconds': 15,
                            'visual': '品牌价值体现',
                            'text': '我们相信{core_value}',
                            'audio': '高潮部分'
                        },
                        {
                            'scene_number': 4,
                            'duration_seconds': 10,
                            'visual': '未来展望',
                            'text': '加入我们的旅程',
                            'audio': '希望主题音乐'
                        }
                    ],
                    'call_to_action': '了解更多品牌故事',
                    'hashtags': ['#{brand_name}', '#brandstory', '#heritage']
                }
            },
            {
                'template_id': 'marketing_001',
                'name': '高转化营销模板',
                'description': '专门设计用于提高转化率的营销脚本，强调紧迫感和价值主张',
                'script_type': 'marketing_conversion',
                'category': 'general',
                'audience': 'general',
                'platform': 'tiktok',
                'difficulty': 'intermediate',
                'conversion_rate': 0.7,
                'engagement_score': 0.65,
                'cultural_adaptability': 0.75,
                'tags': ['marketing', 'conversion', 'sales'],
                'content': {
                    'title_template': '限时优惠：{product_name}',
                    'description_template': '不要错过这个难得的机会',
                    'scenes': [
                        {
                            'scene_number': 1,
                            'duration_seconds': 8,
                            'visual': '问题痛点展示',
                            'text': '你是否面临{problem}？',
                            'audio': '紧张氛围音乐'
                        },
                        {
                            'scene_number': 2,
                            'duration_seconds': 12,
                            'visual': '解决方案介绍',
                            'text': '{product_name}就是答案',
                            'audio': '解脱感音乐'
                        },
                        {
                            'scene_number': 3,
                            'duration_seconds': 15,
                            'visual': '价值证明',
                            'text': '原价${original_price}，现在只要${current_price}',
                            'audio': '兴奋音乐'
                        },
                        {
                            'scene_number': 4,
                            'duration_seconds': 10,
                            'visual': '紧迫感制造',
                            'text': '仅剩{time_left}小时',
                            'audio': '倒计时音效'
                        },
                        {
                            'scene_number': 5,
                            'duration_seconds': 5,
                            'visual': '明确行动号召',
                            'text': '立即点击购买',
                            'audio': '强烈鼓点'
                        }
                    ],
                    'call_to_action': '立即抢购，限时优惠',
                    'hashtags': ['#limitedtime', '#deal', '#sale']
                }
            },
            {
                'template_id': 'knowledge_001',
                'name': '知识解说模板',
                'description': '用于教育性内容，讲解复杂概念或提供实用教程',
                'script_type': 'knowledge_explanation',
                'category': 'software',
                'audience': 'professionals',
                'platform': 'youtube_shorts',
                'difficulty': 'intermediate',
                'conversion_rate': 0.35,
                'engagement_score': 0.75,
                'cultural_adaptability': 0.85,
                'tags': ['knowledge', 'tutorial', 'explainer'],
                'content': {
                    'title_template': '如何{topic_description}',
                    'description_template': '一步步教你掌握{skill_name}',
                    'scenes': [
                        {
                            'scene_number': 1,
                            'duration_seconds': 10,
                            'visual': '主题介绍',
                            'text': '今天学习{topic}',
                            'audio': '教育性背景音乐'
                        },
                        {
                            'scene_number': 2,
                            'duration_seconds': 25,
                            'visual': '步骤分解',
                            'text': '第一步：{step_1}\n第二步：{step_2}',
                            'audio': '清晰解说'
                        },
                        {
                            'scene_number': 3,
                            'duration_seconds': 15,
                            'visual': '示例演示',
                            'text': '看看实际效果',
                            'audio': '演示音效'
                        },
                        {
                            'scene_number': 4,
                            'duration_seconds': 10,
                            'visual': '总结回顾',
                            'text': '记住这些要点',
                            'audio': '总结性音乐'
                        }
                    ],
                    'call_to_action': '关注更多教程',
                    'hashtags': ['#{topic}', '#tutorial', '#howto']
                }
            }
        ]
        
        # 创建模板文件
        for template_info in default_templates:
            template_id = template_info['template_id']
            content = template_info['content']
            
            # 添加元数据到内容中
            content['template_id'] = template_id
            content['name'] = template_info['name']
            content['description'] = template_info['description']
            content['script_type'] = template_info['script_type']
            content['category'] = template_info['category']
            content['audience'] = template_info['audience']
            content['platform'] = template_info['platform']
            
            # 保存模板文件
            template_path = os.path.join(self.templates_dir, f"{template_id}.json")
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        
        logger.info(f"创建了{len(default_templates)}个默认模板")
    
    def _get_default_template(self, script_type: str) -> Dict[str, Any]:
        """获取指定类型的默认模板"""
        default_templates = {
            'product_demo': {
                'title_template': '产品展示',
                'description_template': '了解产品特点',
                'scenes': [
                    {
                        'scene_number': 1,
                        'duration_seconds': 10,
                        'visual': '产品介绍',
                        'text': '欢迎了解我们的产品',
                        'audio': '背景音乐'
                    }
                ],
                'call_to_action': '了解更多',
                'hashtags': ['#product', '#demo']
            },
            'brand_story': {
                'title_template': '品牌故事',
                'description_template': '了解品牌背后的故事',
                'scenes': [
                    {
                        'scene_number': 1,
                        'duration_seconds': 15,
                        'visual': '品牌介绍',
                        'text': '我们的品牌历程',
                        'audio': '叙事音乐'
                    }
                ],
                'call_to_action': '关注我们',
                'hashtags': ['#brand', '#story']
            },
            'marketing_conversion': {
                'title_template': '特别优惠',
                'description_template': '不要错过这个机会',
                'scenes': [
                    {
                        'scene_number': 1,
                        'duration_seconds': 10,
                        'visual': '优惠介绍',
                        'text': '限时优惠',
                        'audio': '兴奋音乐'
                    }
                ],
                'call_to_action': '立即购买',
                'hashtags': ['#sale', '#offer']
            },
            'knowledge_explanation': {
                'title_template': '知识讲解',
                'description_template': '学习新技能',
                'scenes': [
                    {
                        'scene_number': 1,
                        'duration_seconds': 15,
                        'visual': '主题介绍',
                        'text': '今天学习的内容',
                        'audio': '教育音乐'
                    }
                ],
                'call_to_action': '订阅更多',
                'hashtags': ['#knowledge', '#tutorial']
            }
        }
        
        return default_templates.get(script_type, default_templates['product_demo'])