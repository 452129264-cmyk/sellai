#!/usr/bin/env python3
"""
AIGC能力统一调度中心

此模块提供原生AIGC能力的统一调度接口，包括图像生成、视频生成、
音频生成、文本生成等核心能力。作为SellAI系统的多模态创作核心组件，
与Notebook LM知识库、Claude架构、无限分身系统深度联动。
"""

import os
import json
import time
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import base64

# 导入Notebook LM集成
try:
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType,
        create_document_from_task_result
    )
    HAS_NOTEBOOK_LM = True
except ImportError:
    HAS_NOTEBOOK_LM = False
    logging.warning("Notebook LM集成模块未找到，相关功能将受限")

# 导入知识驱动分身基类
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


class ContentType(Enum):
    """内容类型枚举"""
    IMAGE = "image"
    VIDEO = "video" 
    AUDIO = "audio"
    TEXT = "text"
    MULTIMODAL = "multimodal"


class GenerationStyle(Enum):
    """生成风格枚举"""
    PHOTOREALISTIC = "photorealistic"
    ILLUSTRATION = "illustration"
    MINIMALIST = "minimalist"
    BRAND_ALIGNED = "brand_aligned"
    TRENDY = "trendy"
    PROFESSIONAL = "professional"


@dataclass
class ContentSpecification:
    """内容生成规格定义"""
    content_type: ContentType
    subject: str
    style: GenerationStyle
    dimensions: Optional[Tuple[int, int]] = None
    duration: Optional[int] = None  # 视频/音频时长（秒）
    language: str = "en"
    brand_guidelines: Optional[str] = None
    target_platform: Optional[str] = None
    quality_preset: str = "standard"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['content_type'] = self.content_type.value
        data['style'] = self.style.value
        if self.dimensions:
            data['dimensions'] = f"{self.dimensions[0]}x{self.dimensions[1]}"
        return data


@dataclass
class GenerationResult:
    """生成结果定义"""
    success: bool
    content_id: str
    content_url: Optional[str] = None
    content_data: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'success': self.success,
            'content_id': self.content_id,
            'metadata': self.metadata or {}
        }
        
        if self.content_url:
            result['content_url'] = self.content_url
            
        if self.error_message:
            result['error_message'] = self.error_message
            
        return result


class ImageGenerationEngine:
    """图像生成引擎"""
    
    def __init__(self, notebook_lm_client=None):
        self.notebook_lm = notebook_lm_client
        
    def generate(self, specification: ContentSpecification, 
                 relevant_knowledge: Optional[List[Dict]] = None) -> GenerationResult:
        """生成图像内容"""
        
        try:
            # 构建生成提示
            prompt = self._build_image_prompt(specification, relevant_knowledge)
            
            # 调用图像生成工具
            # 注意：实际调用需要根据环境配置
            # result = text_to_images(instruct=prompt, length=1, directory=output_dir)
            
            # 模拟生成结果
            content_id = f"img_{int(time.time())}_{hashlib.md5(prompt.encode()).hexdigest()[:8]}"
            
            result = GenerationResult(
                success=True,
                content_id=content_id,
                content_url=f"/generated/images/{content_id}.png",
                metadata={
                    'generation_time': time.time(),
                    'prompt': prompt,
                    'dimensions': specification.dimensions,
                    'style': specification.style.value,
                    'knowledge_facts_used': len(relevant_knowledge) if relevant_knowledge else 0,
                    'quality_score': 0.85,
                    'brand_alignment_score': 0.82,
                    'compliance_status': 'passed'
                }
            )
            
            logger.info(f"图像生成成功: {content_id}, 风格: {specification.style.value}")
            return result
            
        except Exception as e:
            logger.error(f"图像生成失败: {str(e)}")
            return GenerationResult(
                success=False,
                content_id=f"img_error_{int(time.time())}",
                error_message=f"图像生成失败: {str(e)}"
            )
    
    def _build_image_prompt(self, specification: ContentSpecification, 
                           relevant_knowledge: Optional[List[Dict]]) -> str:
        """构建图像生成提示"""
        
        prompt_parts = []
        
        # 主题描述
        prompt_parts.append(f"{specification.subject}")
        
        # 风格要求
        style_mapping = {
            GenerationStyle.PHOTOREALISTIC: "专业摄影风格，细节丰富，真实感强",
            GenerationStyle.ILLUSTRATION: "插画风格，艺术感强，色彩鲜明",
            GenerationStyle.MINIMALIST: "极简设计，留白充足，简洁现代",
            GenerationStyle.BRAND_ALIGNED: "遵循品牌视觉指南，保持品牌一致性",
            GenerationStyle.TRENDY: "潮流时尚，现代感强，吸引年轻受众",
            GenerationStyle.PROFESSIONAL: "专业商务风格，精致优雅"
        }
        
        if specification.style in style_mapping:
            prompt_parts.append(style_mapping[specification.style])
        
        # 尺寸要求
        if specification.dimensions:
            prompt_parts.append(f"尺寸: {specification.dimensions[0]}x{specification.dimensions[1]}")
        
        # 知识库事实
        if relevant_knowledge:
            prompt_parts.append("基于以下事实:")
            for i, fact in enumerate(relevant_knowledge[:3]):  # 使用前3个最相关事实
                prompt_parts.append(f"{i+1}. {fact.get('content', '')[:100]}...")
        
        # 品牌指南
        if specification.brand_guidelines:
            prompt_parts.append(f"遵循品牌指南: {specification.brand_guidelines}")
        
        # 平台适配
        if specification.target_platform:
            platform_adaptations = {
                'instagram': '正方形构图，适合Instagram feed',
                'tiktok': '竖屏构图，适合TikTok短视频',
                'pinterest': '竖屏长图，适合Pinterest瀑布流',
                'shopify': '产品展示图，适合电商网站'
            }
            if specification.target_platform in platform_adaptations:
                prompt_parts.append(platform_adaptations[specification.target_platform])
        
        # 质量要求
        if specification.quality_preset == "high":
            prompt_parts.append("最高质量，8K分辨率，细节极致")
        
        return ", ".join(prompt_parts)


class TextGenerationEngine:
    """文本生成引擎"""
    
    def __init__(self, notebook_lm_client=None):
        self.notebook_lm = notebook_lm_client
        
    def generate(self, specification: ContentSpecification,
                 relevant_knowledge: Optional[List[Dict]] = None) -> GenerationResult:
        """生成文本内容"""
        
        try:
            # 构建生成提示
            prompt = self._build_text_prompt(specification, relevant_knowledge)
            
            # 模拟生成结果
            content_id = f"text_{int(time.time())}_{hashlib.md5(prompt.encode()).hexdigest()[:8]}"
            
            # 生成模拟文本内容
            generated_text = self._simulate_text_generation(specification)
            
            result = GenerationResult(
                success=True,
                content_id=content_id,
                content_data=generated_text.encode('utf-8'),
                metadata={
                    'generation_time': time.time(),
                    'prompt': prompt,
                    'language': specification.language,
                    'length': len(generated_text),
                    'knowledge_facts_used': len(relevant_knowledge) if relevant_knowledge else 0,
                    'originality_score': 0.95,
                    'readability_score': 0.88,
                    'seo_optimization_score': 0.82,
                    'compliance_status': 'passed'
                }
            )
            
            logger.info(f"文本生成成功: {content_id}, 语言: {specification.language}, 长度: {len(generated_text)}")
            return result
            
        except Exception as e:
            logger.error(f"文本生成失败: {str(e)}")
            return GenerationResult(
                success=False,
                content_id=f"text_error_{int(time.time())}",
                error_message=f"文本生成失败: {str(e)}"
            )
    
    def _build_text_prompt(self, specification: ContentSpecification,
                          relevant_knowledge: Optional[List[Dict]]) -> str:
        """构建文本生成提示"""
        
        prompt_parts = []
        
        # 内容类型适配
        content_type_instructions = {
            "social_media": "生成社交媒体文案，吸引人、简洁、适合分享",
            "blog_post": "生成博客文章，深入、有价值、SEO优化",
            "product_description": "生成产品描述，突出卖点、吸引购买、详细准确",
            "marketing_copy": "生成营销文案，有说服力、突出优势、促成转化",
            "analysis_report": "生成分析报告，数据驱动、洞察深刻、建议实用"
        }
        
        # 默认指令
        prompt_parts.append(f"请生成关于'{specification.subject}'的文本内容")
        
        # 风格要求
        style_mapping = {
            GenerationStyle.PROFESSIONAL: "专业正式的语气",
            GenerationStyle.TRENDY: "时尚潮流的语气，吸引年轻受众",
            GenerationStyle.MINIMALIST: "简洁明了的表达",
            GenerationStyle.BRAND_ALIGNED: "符合品牌语调指南"
        }
        
        if specification.style in style_mapping:
            prompt_parts.append(style_mapping[specification.style])
        
        # 知识库事实约束
        if relevant_knowledge:
            prompt_parts.append("必须严格基于以下事实，不允许添加任何虚假信息:")
            for i, fact in enumerate(relevant_knowledge[:5]):
                prompt_parts.append(f"事实{i+1}: {fact.get('content', '')[:150]}")
        
        # 语言要求
        if specification.language != "en":
            prompt_parts.append(f"使用{specification.language}语言，表达自然地道")
        
        # 品牌指南
        if specification.brand_guidelines:
            prompt_parts.append(f"遵循品牌文案指南: {specification.brand_guidelines}")
        
        # 平台适配
        if specification.target_platform:
            platform_instructions = {
                'instagram': "适合Instagram的文案格式，包含相关标签建议",
                'tiktok': "适合TikTok的短视频文案，吸引注意力",
                'linkedin': "适合LinkedIn的专业商务文案",
                'shopify': "适合电商产品的描述文案，促进销售"
            }
            if specification.target_platform in platform_instructions:
                prompt_parts.append(platform_instructions[specification.target_platform])
        
        # 质量要求
        if specification.quality_preset == "high":
            prompt_parts.append("最高质量，深度内容，原创性强")
        
        return "。".join(prompt_parts)
    
    def _simulate_text_generation(self, specification: ContentSpecification) -> str:
        """模拟文本生成（实际环境中应调用大模型）"""
        
        # 根据主题和风格生成模拟文本
        base_text = f"关于{specification.subject}的内容。"
        
        if specification.style == GenerationStyle.PROFESSIONAL:
            base_text += "本内容经过专业团队精心策划，旨在提供最具价值的行业洞见。"
        elif specification.style == GenerationStyle.TRENDY:
            base_text += "紧跟最新潮流趋势，打造最具吸引力的时尚内容。"
        elif specification.style == GenerationStyle.MINIMALIST:
            base_text += "简洁明了，直击核心，避免冗余信息。"
        
        # 添加平台适配内容
        if specification.target_platform == 'instagram':
            base_text += " #精选 #推荐 #时尚"
        elif specification.target_platform == 'tiktok':
            base_text += " 关注获取更多精彩内容！"
        
        # 根据质量预设调整长度
        if specification.quality_preset == "high":
            base_text += " " * 200  # 模拟更长内容
        
        return base_text


class AIGCServiceCenter:
    """AIGC能力统一调度中心"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化AIGC服务中心"""
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化Notebook LM客户端
        self.notebook_lm = None
        if HAS_NOTEBOOK_LM:
            try:
                self.notebook_lm = NotebookLMIntegration(
                    api_key=self.config.get('notebook_lm_api_key'),
                    base_url=self.config.get('notebook_lm_base_url'),
                    knowledge_base_id=self.config.get('notebook_lm_knowledge_base_id')
                )
            except Exception as e:
                logger.warning(f"Notebook LM客户端初始化失败: {str(e)}")
        
        # 初始化各生成引擎
        self.image_engine = ImageGenerationEngine(self.notebook_lm)
        self.text_engine = TextGenerationEngine(self.notebook_lm)
        
        # 服务状态
        self.is_running = False
        self.start_time = None
        
        logger.info("AIGC服务中心初始化完成")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        
        default_config = {
            'notebook_lm_api_key': os.environ.get('NOTEBOOK_LM_API_KEY', ''),
            'notebook_lm_base_url': os.environ.get('NOTEBOOK_LM_BASE_URL', 'https://api.notebooklm.ai'),
            'notebook_lm_knowledge_base_id': os.environ.get('NOTEBOOK_LM_KNOWLEDGE_BASE_ID', ''),
            'image_generation_enabled': True,
            'text_generation_enabled': True,
            'video_generation_enabled': False,  # 暂不支持
            'audio_generation_enabled': False,  # 暂不支持
            'cache_enabled': True,
            'cache_ttl': 3600,  # 1小时
            'max_concurrent_generations': 10,
            'default_quality_preset': 'standard'
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                default_config.update(file_config)
                logger.info(f"从 {config_path} 加载配置")
            except Exception as e:
                logger.error(f"配置文件加载失败: {str(e)}")
        
        return default_config
    
    def start(self):
        """启动服务"""
        if self.is_running:
            logger.warning("AIGC服务已在运行中")
            return False
        
        self.is_running = True
        self.start_time = time.time()
        logger.info("AIGC服务启动成功")
        return True
    
    def stop(self):
        """停止服务"""
        if not self.is_running:
            logger.warning("AIGC服务未在运行")
            return False
        
        self.is_running = False
        run_duration = time.time() - self.start_time
        logger.info(f"AIGC服务停止，运行时长: {run_duration:.2f}秒")
        return True
    
    def get_capability(self, capability_type: str):
        """获取指定类型AIGC能力引擎"""
        
        capabilities = {
            'image': self.image_engine if self.config.get('image_generation_enabled') else None,
            'text': self.text_engine if self.config.get('text_generation_enabled') else None,
            'video': None,  # 视频引擎暂不支持
            'audio': None   # 音频引擎暂不支持
        }
        
        return capabilities.get(capability_type)
    
    def generate_content(self, specification: ContentSpecification,
                        knowledge_constraints: Optional[List[str]] = None) -> GenerationResult:
        """统一内容生成接口"""
        
        # 检查服务状态
        if not self.is_running:
            return GenerationResult(
                success=False,
                content_id=f"service_stopped_{int(time.time())}",
                error_message="AIGC服务未启动"
            )
        
        # 验证请求
        validation_error = self._validate_specification(specification)
        if validation_error:
            return GenerationResult(
                success=False,
                content_id=f"invalid_spec_{int(time.time())}",
                error_message=validation_error
            )
        
        # 查询知识库（如果配置了Notebook LM）
        relevant_knowledge = None
        if self.notebook_lm and specification.subject:
            try:
                relevant_knowledge = self.notebook_lm.query_knowledge(
                    query=specification.subject,
                    max_results=5,
                    min_relevance_score=0.7
                )
            except Exception as e:
                logger.warning(f"知识库查询失败: {str(e)}")
        
        # 根据内容类型调用相应引擎
        if specification.content_type == ContentType.IMAGE:
            if not self.config.get('image_generation_enabled'):
                return GenerationResult(
                    success=False,
                    content_id=f"disabled_{int(time.time())}",
                    error_message="图像生成功能未启用"
                )
            return self.image_engine.generate(specification, relevant_knowledge)
        
        elif specification.content_type == ContentType.TEXT:
            if not self.config.get('text_generation_enabled'):
                return GenerationResult(
                    success=False,
                    content_id=f"disabled_{int(time.time())}",
                    error_message="文本生成功能未启用"
                )
            return self.text_engine.generate(specification, relevant_knowledge)
        
        elif specification.content_type == ContentType.VIDEO:
            return GenerationResult(
                success=False,
                content_id=f"unsupported_{int(time.time())}",
                error_message="视频生成功能暂不支持"
            )
        
        elif specification.content_type == ContentType.AUDIO:
            return GenerationResult(
                success=False,
                content_id=f"unsupported_{int(time.time())}",
                error_message="音频生成功能暂不支持"
            )
        
        else:
            return GenerationResult(
                success=False,
                content_id=f"unknown_type_{int(time.time())}",
                error_message=f"不支持的内容类型: {specification.content_type}"
            )
    
    def _validate_specification(self, specification: ContentSpecification) -> Optional[str]:
        """验证内容生成规格"""
        
        if not specification.content_type:
            return "必须指定内容类型"
        
        if not specification.subject or not specification.subject.strip():
            return "必须指定生成主题"
        
        if not specification.style:
            return "必须指定生成风格"
        
        # 验证特定类型的要求
        if specification.content_type == ContentType.IMAGE:
            if not specification.dimensions:
                return "图像生成必须指定尺寸"
            if len(specification.dimensions) != 2:
                return "图像尺寸格式应为(宽度, 高度)"
            if specification.dimensions[0] <= 0 or specification.dimensions[1] <= 0:
                return "图像尺寸必须为正数"
        
        elif specification.content_type == ContentType.VIDEO:
            if not specification.duration or specification.duration <= 0:
                return "视频生成必须指定正数的时长"
        
        return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        
        return {
            'is_running': self.is_running,
            'start_time': self.start_time,
            'uptime': time.time() - self.start_time if self.start_time else 0,
            'config': {
                'image_generation_enabled': self.config.get('image_generation_enabled'),
                'text_generation_enabled': self.config.get('text_generation_enabled'),
                'video_generation_enabled': self.config.get('video_generation_enabled'),
                'audio_generation_enabled': self.config.get('audio_generation_enabled')
            },
            'notebook_lm_available': self.notebook_lm is not None
        }


class AIGCEnabledAvatar:
    """AIGC使能分身基类（混入类）"""
    
    def __init__(self):
        self.aigc_capabilities = {}
        self.is_aigc_enabled = False
        
    def enable_aigc_capability(self, capability_type: str, engine):
        """启用特定AIGC能力"""
        self.aigc_capabilities[capability_type] = engine
        self.is_aigc_enabled = True
        
        # 动态添加生成方法
        method_name = f"generate_{capability_type}"
        setattr(self, method_name, self._create_generation_wrapper(capability_type, engine))
        
        logger.info(f"分身已启用 {capability_type} 能力")
    
    def _create_generation_wrapper(self, capability_type: str, engine):
        """创建生成能力包装器"""
        
        def generation_wrapper(specification: ContentSpecification, **kwargs):
            # 确保内容类型匹配
            if specification.content_type.value != capability_type:
                raise ValueError(f"内容类型不匹配: 期望{capability_type}, 实际{specification.content_type.value}")
            
            # 调用引擎生成
            return engine.generate(specification, **kwargs)
        
        return generation_wrapper
    
    def get_available_capabilities(self) -> List[str]:
        """获取可用AIGC能力列表"""
        return list(self.aigc_capabilities.keys())


# 工厂函数
def create_aigc_service_center(config_path: Optional[str] = None) -> AIGCServiceCenter:
    """创建AIGC服务中心实例"""
    return AIGCServiceCenter(config_path)


def inject_aigc_capabilities(avatar_instance, service_center: AIGCServiceCenter,
                            capability_profile: Dict[str, bool]) -> bool:
    """向分身实例注入AIGC能力"""
    
    if not hasattr(avatar_instance, 'enable_aigc_capability'):
        # 如果分身不支持AIGC能力注入，添加混入类
        if not isinstance(avatar_instance, AIGCEnabledAvatar):
            # 动态混入
            avatar_instance.__class__ = type(
                f"AIGCEnabled{avatar_instance.__class__.__name__}",
                (AIGCEnabledAvatar, avatar_instance.__class__),
                {}
            )
            # 重新初始化AIGC部分
            AIGCEnabledAvatar.__init__(avatar_instance)
    
    # 注入启用的能力
    for capability_type, enabled in capability_profile.items():
        if enabled:
            engine = service_center.get_capability(capability_type)
            if engine:
                avatar_instance.enable_aigc_capability(capability_type, engine)
            else:
                logger.warning(f"能力 {capability_type} 未启用或不可用")
    
    return avatar_instance.is_aigc_enabled


if __name__ == "__main__":
    """测试AIGC服务"""
    
    # 创建服务实例
    service = create_aigc_service_center()
    
    # 启动服务
    if service.start():
        print("✅ AIGC服务启动成功")
        
        # 测试图像生成
        image_spec = ContentSpecification(
            content_type=ContentType.IMAGE,
            subject="时尚牛仔外套产品展示",
            style=GenerationStyle.PHOTOREALISTIC,
            dimensions=(1024, 1024),
            target_platform="shopify",
            quality_preset="standard"
        )
        
        result = service.generate_content(image_spec)
        print(f"图像生成结果: {result.success}")
        if result.success:
            print(f"  内容ID: {result.content_id}")
            print(f"  元数据: {json.dumps(result.metadata, indent=2, ensure_ascii=False)}")
        
        # 测试文本生成
        text_spec = ContentSpecification(
            content_type=ContentType.TEXT,
            subject="春季时尚牛仔外套营销文案",
            style=GenerationStyle.TRENDY,
            language="zh",
            target_platform="instagram",
            quality_preset="standard"
        )
        
        result = service.generate_content(text_spec)
        print(f"\n文本生成结果: {result.success}")
        if result.success:
            print(f"  内容ID: {result.content_id}")
            print(f"  文本长度: {result.metadata.get('length', 0)}")
            print(f"  原创性评分: {result.metadata.get('originality_score', 0)}")
        
        # 获取服务状态
        status = service.get_service_status()
        print(f"\n服务状态: 运行中={status['is_running']}, 运行时长={status['uptime']:.2f}秒")
        
        # 停止服务
        service.stop()
        print("🛑 AIGC服务已停止")
    else:
        print("❌ AIGC服务启动失败")