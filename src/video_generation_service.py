#!/usr/bin/env python3
"""
全域短视频创作引擎 - 视频生成服务层

基于现有AIGC多模态能力和FFmpeg工具链，实现全行业全球短视频一键生成。
支持异步批量生成、进度跟踪、结果回调，深度集成无限分身体系。

核心功能：
1. 视频脚本生成与结构化拆解
2. 图像序列并行生成（调用现有AIGC图像引擎）
3. 语音合成与音频生成（调用现有语音合成服务）
4. FFmpeg视频合成与编码（1080p分辨率，≥30fps）
5. 多平台分发适配（TikTok美区、YouTube Shorts、Instagram Reels、小红书）
6. 全球本土化自动适配（集成DeepL多语种润色能力）
7. 与Shopify产品数据深度集成
"""

import os
import json
import time
import logging
import hashlib
import subprocess
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入现有系统模块
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
    from src.voice_synthesis_service import (
        VoiceSynthesisService,
        SynthesisResult,
        create_voice_synthesis_service
    )
    HAS_VOICE_SERVICE = True
except ImportError:
    HAS_VOICE_SERVICE = False
    logging.warning("语音合成服务模块未找到，相关功能将受限")

try:
    from src.deepl_translation_service import (
        DeepLTranslationService,
        TranslationResult,
        create_deepl_service
    )
    HAS_DEEPL_SERVICE = True
except ImportError:
    HAS_DEEPL_SERVICE = False
    logging.warning("DeepL翻译服务模块未找到，相关功能将受限")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoCategory(Enum):
    """视频品类枚举"""
    FASHION_CLOTHING = "fashion_clothing"      # 时尚服装
    ELECTRONICS_3C = "electronics_3c"          # 3C电子产品
    HOME_FURNISHINGS = "home_furnishings"      # 家居用品
    BEAUTY_COSMETICS = "beauty_cosmetics"      # 美妆护肤
    FOOD_BEVERAGE = "food_beverage"            # 食品饮料
    SPORTS_OUTDOOR = "sports_outdoor"          # 运动户外
    BOOKS_STATIONERY = "books_stationery"      # 图书文具
    TOYS_HOBBIES = "toys_hobbies"              # 玩具爱好
    AUTOMOTIVE = "automotive"                  # 汽车用品
    JEWELRY_ACCESSORIES = "jewelry_accessories" # 珠宝配饰


class VideoStyle(Enum):
    """视频风格枚举"""
    PRODUCT_SHOWCASE = "product_showcase"      # 产品展示
    TUTORIAL = "tutorial"                      # 教程解说
    PROMOTIONAL = "promotional"                # 促销推广
    LIFESTYLE = "lifestyle"                    # 生活方式
    TESTIMONIAL = "testimonial"                # 用户见证
    COMPARISON = "comparison"                  # 对比评测
    BEHIND_SCENES = "behind_scenes"            # 幕后制作
    EVENT_COVERAGE = "event_coverage"          # 活动报道


class PlatformType(Enum):
    """平台类型枚举"""
    TIKTOK_US = "tiktok_us"            # TikTok美区
    YOUTUBE_SHORTS = "youtube_shorts"   # YouTube Shorts
    INSTAGRAM_REELS = "instagram_reels" # Instagram Reels
    XIAOHONGSHU = "xiaohongshu"         # 小红书


@dataclass
class VideoGenerationRequest:
    """视频生成请求"""
    request_id: str
    category: VideoCategory
    title: str
    description: str
    style: VideoStyle
    target_platform: PlatformType
    target_country: str = "US"
    target_language: str = "en"
    duration_seconds: int = 30
    resolution: Tuple[int, int] = (1920, 1080)
    framerate: int = 30
    brand_id: Optional[str] = None
    product_data: Optional[Dict[str, Any]] = None
    additional_requirements: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['category'] = self.category.value
        data['style'] = self.style.value
        data['target_platform'] = self.target_platform.value
        data['resolution'] = f"{self.resolution[0]}x{self.resolution[1]}"
        return data


@dataclass
class VideoGenerationResult:
    """视频生成结果"""
    request_id: str
    success: bool
    video_id: str
    video_path: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    audio_path: Optional[str] = None
    metadata: Dict[str, Any] = None
    generation_time_seconds: float = 0.0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'request_id': self.request_id,
            'success': self.success,
            'video_id': self.video_id,
            'generation_time_seconds': self.generation_time_seconds,
            'metadata': self.metadata
        }
        
        if self.video_path:
            result['video_path'] = self.video_path
            
        if self.video_url:
            result['video_url'] = self.video_url
            
        if self.thumbnail_path:
            result['thumbnail_path'] = self.thumbnail_path
            
        if self.audio_path:
            result['audio_path'] = self.audio_path
            
        if self.error_message:
            result['error_message'] = self.error_message
            
        return result


class VideoScriptGenerator:
    """视频脚本生成器"""
    
    def __init__(self, template_manager):
        self.template_manager = template_manager
        self.deepl_service = None
        if HAS_DEEPL_SERVICE:
            try:
                self.deepl_service = create_deepl_service()
            except Exception as e:
                logger.warning(f"DeepL服务初始化失败: {str(e)}")
    
    def generate_script(self, request: VideoGenerationRequest) -> Dict[str, Any]:
        """生成视频脚本"""
        # 获取品类模板
        template = self.template_manager.get_template(request.category)
        if not template:
            raise ValueError(f"品类 {request.category.value} 的模板未找到")
        
        # 提取模板结构
        scene_structure = template.get("scene_structure", [])
        default_transitions = template.get("default_transitions", [])
        pacing_guidelines = template.get("pacing_guidelines", {})
        
        # 构建脚本
        script = {
            "request_id": request.request_id,
            "title": request.title,
            "description": request.description,
            "category": request.category.value,
            "style": request.style.value,
            "target_platform": request.target_platform.value,
            "target_language": request.target_language,
            "scenes": [],
            "total_duration_seconds": request.duration_seconds,
            "estimated_frame_count": request.duration_seconds * request.framerate,
            "generated_at": datetime.now().isoformat()
        }
        
        # 根据视频风格调整场景结构
        style_adjustments = self._get_style_adjustments(request.style)
        
        # 分配场景时长
        scene_durations = self._allocate_scene_durations(
            scene_structure, 
            request.duration_seconds,
            style_adjustments
        )
        
        # 生成每个场景的详细描述
        for i, (scene_type, duration) in enumerate(zip(scene_structure, scene_durations)):
            scene = {
                "scene_id": f"scene_{i+1}",
                "scene_type": scene_type,
                "duration_seconds": duration,
                "frame_count": duration * request.framerate,
                "description": self._generate_scene_description(
                    scene_type, request, i, len(scene_structure)
                ),
                "visual_elements": self._generate_visual_elements(
                    scene_type, request, i
                ),
                "audio_cues": self._generate_audio_cues(
                    scene_type, request, i
                ),
                "transitions": self._select_transitions(
                    scene_type, default_transitions, i, len(scene_structure)
                )
            }
            
            # 应用风格调整
            scene.update(style_adjustments.get("scene_adjustments", {}))
            
            script["scenes"].append(scene)
        
        # 添加品牌和产品信息（如果有）
        if request.brand_id:
            script["brand_info"] = {
                "brand_id": request.brand_id,
                "integration_level": "full"
            }
        
        if request.product_data:
            script["product_info"] = request.product_data
        
        # 本地化翻译（如果需要）
        if request.target_language != "en" and self.deepl_service:
            script = self._localize_script(script, request.target_language)
        
        return script
    
    def _get_style_adjustments(self, style: VideoStyle) -> Dict[str, Any]:
        """获取风格调整参数"""
        adjustments = {
            VideoStyle.PRODUCT_SHOWCASE: {
                "scene_adjustments": {"focus": "product_details", "pacing": "slow"},
                "shot_types": ["close_up", "medium_shot", "slow_pan"]
            },
            VideoStyle.TUTORIAL: {
                "scene_adjustments": {"focus": "step_by_step", "pacing": "moderate"},
                "shot_types": ["medium_shot", "over_the_shoulder", "screen_recording"]
            },
            VideoStyle.PROMOTIONAL: {
                "scene_adjustments": {"focus": "emotional_appeal", "pacing": "fast"},
                "shot_types": ["dynamic_shot", "quick_cuts", "special_effects"]
            },
            VideoStyle.LIFESTYLE: {
                "scene_adjustments": {"focus": "authentic_moments", "pacing": "natural"},
                "shot_types": ["candid_shot", "natural_lighting", "real_time"]
            },
            VideoStyle.TESTIMONIAL: {
                "scene_adjustments": {"focus": "personal_stories", "pacing": "deliberate"},
                "shot_types": ["interview_style", "close_up", "soft_lighting"]
            }
        }
        
        return adjustments.get(style, {})
    
    def _allocate_scene_durations(self, scene_structure: List[str], 
                                 total_duration: int,
                                 style_adjustments: Dict) -> List[int]:
        """分配场景时长"""
        num_scenes = len(scene_structure)
        if num_scenes == 0:
            return []
        
        # 基础分配：平均分配
        base_duration = total_duration // num_scenes
        durations = [base_duration] * num_scenes
        
        # 调整余数
        remainder = total_duration - base_duration * num_scenes
        for i in range(remainder):
            durations[i] += 1
        
        # 根据风格调整
        pacing = style_adjustments.get("scene_adjustments", {}).get("pacing", "moderate")
        if pacing == "fast":
            # 前短后长，强调结尾
            for i in range(num_scenes):
                if i < num_scenes // 2:
                    durations[i] = max(1, durations[i] - 1)
                else:
                    durations[i] = durations[i] + 1
        elif pacing == "slow":
            # 前长后短，强调开头
            for i in range(num_scenes):
                if i < num_scenes // 2:
                    durations[i] = durations[i] + 1
                else:
                    durations[i] = max(1, durations[i] - 1)
        
        # 确保总时长不变
        total = sum(durations)
        if total != total_duration:
            durations[-1] += total_duration - total
        
        return durations
    
    def _generate_scene_description(self, scene_type: str, 
                                   request: VideoGenerationRequest,
                                   scene_index: int,
                                   total_scenes: int) -> str:
        """生成场景描述"""
        # 根据场景类型生成描述
        descriptions = {
            "intro": f"引人入胜的开场，展示{request.title}的核心卖点",
            "product_features": f"详细展示{request.title}的关键功能和特点",
            "usage_scenario": f"演示{request.title}在实际生活中的应用场景",
            "benefits": f"突出{request.title}为用户带来的核心价值和好处",
            "social_proof": f"展示其他用户对{request.title}的积极评价和体验",
            "call_to_action": f"明确的行动号召，告诉观众如何获取{request.title}",
            "outro": f"简洁有力的结尾，强化品牌印象和产品认知"
        }
        
        description = descriptions.get(scene_type, f"展示{request.title}的相关内容")
        
        # 根据视频风格调整
        if request.style == VideoStyle.PROMOTIONAL:
            description += "，采用快节奏剪辑和动感音乐"
        elif request.style == VideoStyle.TUTORIAL:
            description += "，步骤清晰，讲解详细"
        elif request.style == VideoStyle.LIFESTYLE:
            description += "，自然真实，贴近生活"
        
        return description
    
    def _generate_visual_elements(self, scene_type: str,
                                 request: VideoGenerationRequest,
                                 scene_index: int) -> List[Dict[str, Any]]:
        """生成视觉元素列表"""
        elements = []
        
        # 根据场景类型添加视觉元素
        if scene_type == "intro":
            elements.append({
                "element_type": "logo_reveal",
                "description": "品牌logo动画展示",
                "duration_seconds": 3,
                "priority": "high"
            })
            elements.append({
                "element_type": "product_hero_shot",
                "description": "产品全景展示",
                "duration_seconds": 4,
                "priority": "high"
            })
        
        elif scene_type == "product_features":
            elements.append({
                "element_type": "feature_highlight",
                "description": "关键功能特写展示",
                "duration_seconds": 3,
                "priority": "medium"
            })
            elements.append({
                "element_type": "comparison_visual",
                "description": "与竞品对比展示",
                "duration_seconds": 4,
                "priority": "medium"
            })
        
        # 添加通用元素
        elements.append({
            "element_type": "text_overlay",
            "description": "关键信息文字叠加",
            "duration_seconds": 2,
            "priority": "low"
        })
        
        # 根据平台调整
        if request.target_platform == PlatformType.TIKTOK_US:
            elements.append({
                "element_type": "trending_sticker",
                "description": "流行贴纸元素",
                "duration_seconds": 1,
                "priority": "low"
            })
        
        return elements
    
    def _generate_audio_cues(self, scene_type: str,
                            request: VideoGenerationRequest,
                            scene_index: int) -> List[Dict[str, Any]]:
        """生成音频提示点"""
        cues = []
        
        # 根据场景类型添加音频提示
        cue_types = {
            "intro": ["background_music_start", "voiceover_intro"],
            "product_features": ["voiceover_features", "sound_effects_highlight"],
            "call_to_action": ["voiceover_cta", "music_swell"],
            "outro": ["music_fade_out", "brand_jingle"]
        }
        
        for cue_type in cue_types.get(scene_type, ["background_music"]):
            cues.append({
                "cue_type": cue_type,
                "description": f"{cue_type.replace('_', ' ').title()}",
                "timing": "scene_start",
                "duration_seconds": 5
            })
        
        return cues
    
    def _select_transitions(self, scene_type: str,
                           default_transitions: List[str],
                           scene_index: int,
                           total_scenes: int) -> List[str]:
        """选择转场效果"""
        transitions = default_transitions.copy()
        
        # 根据场景位置调整转场
        if scene_index == 0:
            # 开场转场
            transitions = ["fade_in"] + transitions
        elif scene_index == total_scenes - 1:
            # 结尾转场
            transitions = transitions + ["fade_out"]
        
        # 根据场景类型调整
        if scene_type in ["intro", "outro"]:
            transitions.append("smooth_crossfade")
        elif scene_type in ["product_features", "usage_scenario"]:
            transitions.append("zoom_transition")
        
        return transitions
    
    def _localize_script(self, script: Dict[str, Any], target_language: str) -> Dict[str, Any]:
        """本地化脚本翻译"""
        if not self.deepl_service:
            return script
        
        try:
            # 翻译标题和描述
            title_result = self.deepl_service.translate(
                text=script["title"],
                target_lang=target_language,
                preserve_formatting=True
            )
            
            if title_result.success:
                script["title"] = title_result.translated_text
            
            # 翻译场景描述
            for scene in script["scenes"]:
                desc_result = self.deepl_service.translate(
                    text=scene["description"],
                    target_lang=target_language,
                    preserve_formatting=True
                )
                
                if desc_result.success:
                    scene["description"] = desc_result.translated_text
            
            # 记录翻译信息
            script["localization_info"] = {
                "target_language": target_language,
                "translated_at": datetime.now().isoformat(),
                "translation_service": "DeepL"
            }
            
        except Exception as e:
            logger.warning(f"脚本本地化翻译失败: {str(e)}")
        
        return script


class VideoTemplateManager:
    """视频模板管理器"""
    
    def __init__(self, templates_dir: str = "src/video_templates"):
        self.templates_dir = templates_dir
        self.templates: Dict[str, Dict] = {}
        os.makedirs(templates_dir, exist_ok=True)
        self._load_templates()
    
    def _load_templates(self):
        """加载所有模板"""
        if not os.path.exists(self.templates_dir):
            logger.warning(f"模板目录不存在: {self.templates_dir}")
            return
        
        template_files = [f for f in os.listdir(self.templates_dir) 
                         if f.endswith('.json')]
        
        for template_file in template_files:
            try:
                with open(os.path.join(self.templates_dir, template_file), 
                         'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                category = template_data.get('category')
                if category:
                    self.templates[category] = template_data
                    logger.info(f"加载视频模板: {category}")
                    
            except Exception as e:
                logger.error(f"加载视频模板文件失败 {template_file}: {str(e)}")
    
    def get_template(self, category: Union[str, VideoCategory]) -> Optional[Dict]:
        """获取指定品类模板"""
        if isinstance(category, VideoCategory):
            category = category.value
        
        return self.templates.get(category)
    
    def create_template(self, category: str, template_data: Dict) -> bool:
        """创建新模板"""
        try:
            template_path = os.path.join(self.templates_dir, f"{category}.json")
            
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            
            # 重新加载
            self.templates[category] = template_data
            logger.info(f"创建视频模板: {category}")
            return True
            
        except Exception as e:
            logger.error(f"创建视频模板失败 {category}: {str(e)}")
            return False
    
    def list_categories(self) -> List[str]:
        """列出所有可用的品类"""
        return list(self.templates.keys())


class PlatformAdapterManager:
    """平台适配器管理器"""
    
    def __init__(self, adapters_dir: str = "src/platform_adapters"):
        self.adapters_dir = adapters_dir
        self.adapters: Dict[str, Dict] = {}
        os.makedirs(adapters_dir, exist_ok=True)
        self._load_adapters()
    
    def _load_adapters(self):
        """加载所有平台适配器"""
        if not os.path.exists(self.adapters_dir):
            logger.warning(f"适配器目录不存在: {self.adapters_dir}")
            return
        
        adapter_files = [f for f in os.listdir(self.adapters_dir) 
                        if f.endswith('.json')]
        
        for adapter_file in adapter_files:
            try:
                with open(os.path.join(self.adapters_dir, adapter_file), 
                         'r', encoding='utf-8') as f:
                    adapter_data = json.load(f)
                
                platform = adapter_data.get('platform')
                if platform:
                    self.adapters[platform] = adapter_data
                    logger.info(f"加载平台适配器: {platform}")
                    
            except Exception as e:
                logger.error(f"加载平台适配器文件失败 {adapter_file}: {str(e)}")
    
    def get_adapter(self, platform: Union[str, PlatformType]) -> Optional[Dict]:
        """获取指定平台适配器"""
        if isinstance(platform, PlatformType):
            platform = platform.value
        
        return self.adapters.get(platform)
    
    def optimize_for_platform(self, script: Dict[str, Any],
                             platform: PlatformType) -> Dict[str, Any]:
        """针对平台优化脚本"""
        adapter = self.get_adapter(platform)
        if not adapter:
            return script
        
        optimized = script.copy()
        
        # 应用平台格式要求
        format_guidelines = adapter.get('format_guidelines', {})
        
        # 调整时长
        max_duration = format_guidelines.get('max_duration_seconds', 60)
        if optimized['total_duration_seconds'] > max_duration:
            optimized['total_duration_seconds'] = max_duration
            logger.info(f"调整视频时长为平台上限: {max_duration}秒")
        
        # 调整分辨率
        aspect_ratio = format_guidelines.get('aspect_ratio', '9:16')
        if aspect_ratio == "9:16":
            optimized['metadata']['target_resolution'] = (1080, 1920)
        elif aspect_ratio == "1:1":
            optimized['metadata']['target_resolution'] = (1080, 1080)
        elif aspect_ratio == "16:9":
            optimized['metadata']['target_resolution'] = (1920, 1080)
        
        # 添加平台特定元素
        platform_elements = adapter.get('recommended_elements', [])
        if platform_elements:
            # 在脚本中添加平台特定元素标记
            optimized['platform_optimizations'] = platform_elements
        
        # 记录平台适配信息
        optimized['platform_optimization_info'] = {
            'platform': platform.value,
            'optimized_at': datetime.now().isoformat(),
            'guidelines_applied': list(format_guidelines.keys())
        }
        
        return optimized


class VideoGenerationService:
    """视频生成服务主类"""
    
    def __init__(self, config_path: Optional[str] = None):
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化现有服务
        self.aigc_service = None
        if HAS_AIGC_SERVICE:
            try:
                self.aigc_service = create_aigc_service_center()
                self.aigc_service.start()
            except Exception as e:
                logger.error(f"AIGC服务启动失败: {str(e)}")
        
        self.voice_service = None
        if HAS_VOICE_SERVICE:
            try:
                self.voice_service = create_voice_synthesis_service()
            except Exception as e:
                logger.warning(f"语音合成服务初始化失败: {str(e)}")
        
        # 初始化各管理器
        self.template_manager = VideoTemplateManager()
        self.script_generator = VideoScriptGenerator(self.template_manager)
        self.platform_adapter = PlatformAdapterManager()
        
        # 生成队列和状态跟踪
        self.generation_queue = queue.Queue()
        self.active_generations: Dict[str, Dict] = {}
        self.generation_history: List[VideoGenerationResult] = []
        
        # 工作线程池
        self.executor = ThreadPoolExecutor(max_workers=self.config['max_concurrent_generations'])
        self.is_running = False
        
        # 启动工作线程
        self.worker_thread = threading.Thread(target=self._process_generation_queue, daemon=True)
        
        logger.info("视频生成服务初始化完成")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            'video_generation_enabled': True,
            'platform_optimization_enabled': True,
            'localization_enabled': True,
            'quality_check_enabled': True,
            'default_resolution': (1920, 1080),
            'default_framerate': 30,
            'max_duration_seconds': 60,
            'min_duration_seconds': 15,
            'max_concurrent_generations': 3,
            'ffmpeg_path': '/usr/bin/ffmpeg',
            'temp_dir': 'temp/video_generation',
            'output_dir': 'outputs/videos',
            'thumbnail_enabled': True,
            'audio_synthesis_enabled': True,
            'cache_enabled': True,
            'cache_ttl': 3600
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
            logger.warning("视频生成服务已在运行中")
            return False
        
        # 创建输出目录
        os.makedirs(self.config['temp_dir'], exist_ok=True)
        os.makedirs(self.config['output_dir'], exist_ok=True)
        
        self.is_running = True
        self.worker_thread.start()
        logger.info("视频生成服务启动成功")
        return True
    
    def stop(self):
        """停止服务"""
        if not self.is_running:
            logger.warning("视频生成服务未在运行")
            return False
        
        self.is_running = False
        self.executor.shutdown(wait=True)
        logger.info("视频生成服务停止")
        return True
    
    def generate_video(self, request: VideoGenerationRequest) -> str:
        """
        提交视频生成请求
        
        Args:
            request: 视频生成请求
            
        Returns:
            生成任务ID
        """
        # 验证请求
        validation_error = self._validate_request(request)
        if validation_error:
            raise ValueError(validation_error)
        
        # 创建任务ID
        task_id = f"video_{int(time.time())}_{hashlib.md5(request.request_id.encode()).hexdigest()[:8]}"
        
        # 将任务加入队列
        task_data = {
            'task_id': task_id,
            'request': request,
            'status': 'pending',
            'submitted_at': time.time(),
            'progress': 0.0
        }
        
        self.generation_queue.put(task_data)
        self.active_generations[task_id] = task_data
        
        logger.info(f"视频生成任务提交成功: {task_id}, 品类: {request.category.value}")
        return task_id
    
    def _validate_request(self, request: VideoGenerationRequest) -> Optional[str]:
        """验证生成请求"""
        if not request.title or not request.title.strip():
            return "视频标题不能为空"
        
        if not request.description or not request.description.strip():
            return "视频描述不能为空"
        
        if request.duration_seconds < self.config['min_duration_seconds']:
            return f"视频时长过短，最小为{self.config['min_duration_seconds']}秒"
        
        if request.duration_seconds > self.config['max_duration_seconds']:
            return f"视频时长过长，最大为{self.config['max_duration_seconds']}秒"
        
        if request.resolution[0] < 640 or request.resolution[1] < 480:
            return "视频分辨率过低，最小为640×480"
        
        if request.resolution[0] > 3840 or request.resolution[1] > 2160:
            return "视频分辨率过高，最大为4K(3840×2160)"
        
        return None
    
    def _process_generation_queue(self):
        """处理生成队列"""
        while self.is_running:
            try:
                # 从队列获取任务
                task_data = self.generation_queue.get(timeout=1.0)
                task_id = task_data['task_id']
                
                # 更新状态为处理中
                task_data['status'] = 'processing'
                task_data['started_at'] = time.time()
                
                logger.info(f"开始处理视频生成任务: {task_id}")
                
                # 提交到线程池执行
                future = self.executor.submit(self._execute_generation_task, task_data)
                future.add_done_callback(lambda f: self._task_completion_callback(f, task_id))
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"处理生成队列时出错: {str(e)}")
    
    def _execute_generation_task(self, task_data: Dict[str, Any]) -> VideoGenerationResult:
        """执行视频生成任务"""
        task_id = task_data['task_id']
        request = task_data['request']
        
        try:
            start_time = time.time()
            
            # 1. 生成视频脚本
            task_data['progress'] = 0.1
            script = self.script_generator.generate_script(request)
            
            # 2. 平台优化
            task_data['progress'] = 0.2
            optimized_script = self.platform_adapter.optimize_for_platform(
                script, request.target_platform
            )
            
            # 3. 创建临时工作目录
            work_dir = os.path.join(self.config['temp_dir'], task_id)
            os.makedirs(work_dir, exist_ok=True)
            
            # 4. 生成图像序列
            task_data['progress'] = 0.3
            image_paths = self._generate_image_sequence(
                optimized_script, work_dir, task_data
            )
            
            if not image_paths:
                raise ValueError("图像序列生成失败")
            
            # 5. 生成音频
            task_data['progress'] = 0.6
            audio_path = self._generate_audio(
                optimized_script, work_dir, task_data
            )
            
            # 6. 合成视频
            task_data['progress'] = 0.8
            video_path, thumbnail_path = self._compose_video(
                image_paths, audio_path, work_dir, optimized_script
            )
            
            # 7. 计算生成时间和质量指标
            generation_time = time.time() - start_time
            
            # 构建结果
            result = VideoGenerationResult(
                request_id=request.request_id,
                success=True,
                video_id=task_id,
                video_path=video_path,
                video_url=f"/generated/videos/{task_id}.mp4",
                thumbnail_path=thumbnail_path,
                audio_path=audio_path,
                metadata={
                    'script': optimized_script,
                    'image_count': len(image_paths),
                    'platform': request.target_platform.value,
                    'language': request.target_language,
                    'duration_seconds': request.duration_seconds,
                    'resolution': request.resolution,
                    'framerate': request.framerate,
                    'generation_time_seconds': generation_time,
                    'task_duration_seconds': time.time() - task_data['submitted_at']
                },
                generation_time_seconds=generation_time
            )
            
            logger.info(f"视频生成任务完成: {task_id}, 耗时: {generation_time:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"视频生成任务失败 {task_id}: {str(e)}", exc_info=True)
            
            return VideoGenerationResult(
                request_id=request.request_id,
                success=False,
                video_id=task_id,
                error_message=f"视频生成失败: {str(e)}",
                generation_time_seconds=time.time() - start_time if 'start_time' in locals() else 0.0
            )
    
    def _generate_image_sequence(self, script: Dict[str, Any],
                                work_dir: str,
                                task_data: Dict[str, Any]) -> List[str]:
        """生成图像序列"""
        if not self.aigc_service:
            raise ValueError("AIGC服务不可用")
        
        image_paths = []
        
        # 为每个场景生成图像
        for i, scene in enumerate(script['scenes']):
            # 更新进度
            base_progress = 0.3
            scene_progress = (i / len(script['scenes'])) * 0.3
            task_data['progress'] = base_progress + scene_progress
            
            # 构建图像生成规格
            image_spec = ContentSpecification(
                content_type=ContentType.IMAGE,
                subject=scene['description'],
                style=GenerationStyle.PHOTOREALISTIC,
                dimensions=script['metadata'].get('target_resolution', (1920, 1080)),
                target_platform=script['target_platform'],
                quality_preset="high"
            )
            
            # 调用AIGC服务生成图像
            result = self.aigc_service.generate_content(image_spec)
            
            if not result.success:
                raise ValueError(f"场景 {i+1} 图像生成失败: {result.error_message}")
            
            # 保存图像到文件
            image_filename = f"scene_{i+1}.png"
            image_path = os.path.join(work_dir, image_filename)
            
            if result.content_data:
                with open(image_path, 'wb') as f:
                    f.write(result.content_data)
            else:
                # 如果没有图像数据，创建占位符
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new('RGB', (1920, 1080), color='blue')
                draw = ImageDraw.Draw(img)
                draw.text((100, 100), f"场景 {i+1}: {scene['description']}", fill='white')
                img.save(image_path)
            
            image_paths.append(image_path)
            
            logger.debug(f"生成图像: {image_filename}")
        
        return image_paths
    
    def _generate_audio(self, script: Dict[str, Any],
                       work_dir: str,
                       task_data: Dict[str, Any]) -> str:
        """生成音频"""
        if not self.config['audio_synthesis_enabled'] or not self.voice_service:
            # 如果不支持音频生成，返回静音音频或占位符
            audio_path = os.path.join(work_dir, "audio_silent.wav")
            # 创建静音WAV文件
            self._create_silent_audio(audio_path, script['total_duration_seconds'])
            return audio_path
        
        try:
            # 构建音频文本（组合所有场景描述）
            audio_text = "。".join([scene['description'] for scene in script['scenes']])
            
            # 调用语音合成服务
            synthesis_result = self.voice_service.synthesize(
                text=audio_text,
                voice_name="zh-CN-XiaoxiaoNeural",  # 示例音色
                language="zh-CN"
            )
            
            if synthesis_result:
                # 保存音频文件
                audio_path = os.path.join(work_dir, "audio_generated.wav")
                synthesis_result.save_to_file(audio_path)
                return audio_path
            else:
                raise ValueError("语音合成失败")
                
        except Exception as e:
            logger.warning(f"音频生成失败，使用静音替代: {str(e)}")
            audio_path = os.path.join(work_dir, "audio_silent.wav")
            self._create_silent_audio(audio_path, script['total_duration_seconds'])
            return audio_path
    
    def _create_silent_audio(self, audio_path: str, duration_seconds: float):
        """创建静音音频文件"""
        try:
            # 使用FFmpeg生成静音音频
            cmd = [
                self.config['ffmpeg_path'],
                '-f', 'lavfi',
                '-i', f'anullsrc=r=48000:cl=stereo',
                '-t', str(duration_seconds),
                '-c:a', 'pcm_s16le',
                audio_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
        except Exception as e:
            logger.error(f"创建静音音频失败: {str(e)}")
            # 创建空文件作为占位符
            with open(audio_path, 'wb') as f:
                f.write(b'SILENT_AUDIO_PLACEHOLDER')
    
    def _compose_video(self, image_paths: List[str],
                      audio_path: str,
                      work_dir: str,
                      script: Dict[str, Any]) -> Tuple[str, str]:
        """合成视频"""
        # 创建图像序列文件列表
        list_file = os.path.join(work_dir, "image_list.txt")
        with open(list_file, 'w') as f:
            for image_path in image_paths:
                # 每张图像持续时长根据场景时长分配
                f.write(f"file '{image_path}'\\n")
        
        # 输出视频路径
        video_filename = f"video_{int(time.time())}.mp4"
        video_path = os.path.join(self.config['output_dir'], video_filename)
        
        # 缩略图路径
        thumbnail_filename = f"thumbnail_{int(time.time())}.jpg"
        thumbnail_path = os.path.join(self.config['output_dir'], thumbnail_filename)
        
        try:
            # 使用FFmpeg合成视频
            cmd = [
                self.config['ffmpeg_path'],
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-i', audio_path,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                '-pix_fmt', 'yuv420p',
                video_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # 生成缩略图（从视频第一帧提取）
            thumbnail_cmd = [
                self.config['ffmpeg_path'],
                '-i', video_path,
                '-ss', '00:00:01',
                '-vframes', '1',
                '-q:v', '2',
                thumbnail_path
            ]
            
            subprocess.run(thumbnail_cmd, check=True, capture_output=True)
            
            logger.info(f"视频合成成功: {video_path}, 缩略图: {thumbnail_path}")
            
            return video_path, thumbnail_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg合成失败: {e.stderr.decode() if e.stderr else str(e)}")
            raise ValueError(f"视频合成失败: {str(e)}")
        except Exception as e:
            logger.error(f"视频合成过程出错: {str(e)}")
            raise
    
    def _task_completion_callback(self, future, task_id: str):
        """任务完成回调"""
        try:
            result = future.result()
            
            # 更新任务状态
            if task_id in self.active_generations:
                task_data = self.active_generations[task_id]
                task_data['status'] = 'completed' if result.success else 'failed'
                task_data['completed_at'] = time.time()
                task_data['result'] = result
                task_data['progress'] = 1.0
            
            # 记录历史
            self.generation_history.append(result)
            
            # 清理临时文件（可配置）
            if self.config.get('cleanup_temp_files', True):
                self._cleanup_temp_files(task_id)
            
            logger.info(f"任务回调处理完成: {task_id}, 成功: {result.success}")
            
        except Exception as e:
            logger.error(f"任务完成回调出错 {task_id}: {str(e)}")
    
    def _cleanup_temp_files(self, task_id: str):
        """清理临时文件"""
        try:
            temp_dir = os.path.join(self.config['temp_dir'], task_id)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"清理临时目录: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时文件失败 {task_id}: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.active_generations.get(task_id)
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'is_running': self.is_running,
            'queue_size': self.generation_queue.qsize(),
            'active_tasks': len(self.active_generations),
            'total_completed': len(self.generation_history),
            'config': {
                'video_generation_enabled': self.config.get('video_generation_enabled'),
                'platform_optimization_enabled': self.config.get('platform_optimization_enabled'),
                'localization_enabled': self.config.get('localization_enabled'),
                'max_concurrent_generations': self.config.get('max_concurrent_generations')
            }
        }


# 工厂函数
def create_video_generation_service(config_path: Optional[str] = None) -> VideoGenerationService:
    """创建视频生成服务实例"""
    return VideoGenerationService(config_path)


# 简化接口
def generate_video_simple(
    category: str,
    title: str,
    description: str,
    target_platform: str,
    duration_seconds: int = 30,
    resolution: Tuple[int, int] = (1920, 1080)
) -> Optional[str]:
    """
    简化视频生成接口
    
    Args:
        category: 视频品类
        title: 视频标题
        description: 视频描述
        target_platform: 目标平台
        duration_seconds: 视频时长（秒）
        resolution: 视频分辨率
        
    Returns:
        视频文件路径或None
    """
    try:
        # 创建服务
        service = create_video_generation_service()
        service.start()
        
        # 构建请求
        request = VideoGenerationRequest(
            request_id=f"simple_{int(time.time())}_{hashlib.md5(title.encode()).hexdigest()[:8]}",
            category=VideoCategory(category),
            title=title,
            description=description,
            style=VideoStyle.PRODUCT_SHOWCASE,
            target_platform=PlatformType(target_platform),
            duration_seconds=duration_seconds,
            resolution=resolution
        )
        
        # 提交生成
        task_id = service.generate_video(request)
        
        # 等待完成（简化的阻塞方式）
        max_wait = duration_seconds * 2  # 最长等待时间为视频时长的2倍
        wait_start = time.time()
        
        while time.time() - wait_start < max_wait:
            status = service.get_task_status(task_id)
            if status and status['status'] in ['completed', 'failed']:
                if status['status'] == 'completed':
                    return status['result'].video_path
                else:
                    logger.error(f"视频生成失败: {status.get('result', {}).get('error_message', '未知错误')}")
                    return None
            
            time.sleep(1.0)
        
        logger.error(f"视频生成超时，等待超过{max_wait}秒")
        return None
        
    except Exception as e:
        logger.error(f"简化视频生成失败: {str(e)}")
        return None
    finally:
        if 'service' in locals():
            service.stop()


if __name__ == "__main__":
    """测试视频生成服务"""
    
    print("全域短视频创作引擎 - 视频生成服务测试")
    print("=" * 60)
    
    # 创建服务实例
    service = create_video_generation_service()
    
    # 启动服务
    if service.start():
        print("✅ 视频生成服务启动成功")
        
        # 测试服务状态
        status = service.get_service_status()
        print(f"服务状态: 运行中={status['is_running']}, 队列大小={status['queue_size']}")
        
        # 创建测试请求
        test_request = VideoGenerationRequest(
            request_id=f"test_{int(time.time())}",
            category=VideoCategory.FASHION_CLOTHING,
            title="美式复古牛仔外套展示",
            description="高品质牛仔面料，复古设计，适合日常穿搭",
            style=VideoStyle.PRODUCT_SHOWCASE,
            target_platform=PlatformType.TIKTOK_US,
            target_country="US",
            target_language="en",
            duration_seconds=15,
            resolution=(1920, 1080),
            framerate=30
        )
        
        # 提交生成任务
        try:
            task_id = service.generate_video(test_request)
            print(f"\\n视频生成任务已提交: {task_id}")
            
            # 等待一段时间
            print("等待视频生成...")
            time.sleep(5.0)
            
            # 检查状态
            task_status = service.get_task_status(task_id)
            if task_status:
                print(f"任务状态: {task_status['status']}, 进度: {task_status['progress']:.1%}")
                
                if task_status['status'] == 'completed':
                    result = task_status['result']
                    print(f"生成成功: 视频路径={result.video_path}")
                    print(f"生成耗时: {result.generation_time_seconds:.2f}秒")
                elif task_status['status'] == 'failed':
                    result = task_status['result']
                    print(f"生成失败: {result.error_message}")
        
        except Exception as e:
            print(f"❌ 视频生成请求失败: {str(e)}")
        
        # 停止服务
        service.stop()
        print("\\n🛑 视频生成服务已停止")
        
    else:
        print("❌ 视频生成服务启动失败")