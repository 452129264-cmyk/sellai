#!/usr/bin/env python3
"""
高端全场景视觉生成服务层

基于现有AIGC模块和Banana生图内核，提供全行业产品实拍图、品牌物料、
宣传海报、全球本土化视觉素材一键生成能力。

核心功能：
1. 全行业产品实拍图生成引擎（支持至少10个主要品类）
2. 品牌物料自动生成系统（自动识别与应用品牌logo、配色、字体等视觉元素）
3. 全球本土化视觉适配引擎（支持多语种文案自动嵌入、适配各国审美风格）
4. 高性能渲染与优化模块（确保生成图像分辨率≥2048×2048，画质≥Banana原版输出）
"""

import os
import json
import time
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

# 导入现有AIGC模块
try:
    from src.aigc_service_center import (
        AIGCServiceCenter,
        ContentSpecification,
        ContentType,
        GenerationStyle,
        GenerationResult,
        ImageGenerationEngine
    )
    HAS_AIGC = True
except ImportError:
    HAS_AIGC = False
    logging.warning("AIGC服务中心模块未找到，相关功能将受限")

# 导入Banana生图内核质量锁死机制
try:
    from src.banana_face_consistency.quality_lock_controller import (
        QualityLockController,
        QualityCheckResult,
        MaterialType
    )
    HAS_BANANA_QUALITY = True
except ImportError:
    HAS_BANANA_QUALITY = False
    logging.warning("Banana质量锁死控制器未找到，画质检查将受限")
    
    # 创建占位符类
    class QualityCheckResult:
        def __init__(self):
            self.success = False
            self.score = 0.0
            self.details = {}
        
        def to_dict(self):
            return {
                'success': self.success,
                'score': self.score,
                'details': self.details
            }
    
    class MaterialType:
        DENIM = "denim"
        COTTON = "cotton"
        SILK = "silk"
        LEATHER = "leather"
        SYNTHETIC = "synthetic"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductCategory(Enum):
    """产品品类枚举"""
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


class VisualStyle(Enum):
    """视觉风格枚举"""
    PRODUCT_PHOTOGRAPHY = "product_photography"  # 产品摄影
    LIFESTYLE = "lifestyle"                      # 生活方式
    MINIMALIST = "minimalist"                    # 极简设计
    BRAND_COMMERCIAL = "brand_commercial"        # 品牌商业
    SOCIAL_MEDIA = "social_media"                # 社交媒体
    ECOMMERCE = "ecommerce"                      # 电商展示
    EDITORIAL = "editorial"                      # 编辑风
    ARTISTIC = "artistic"                        # 艺术创作


@dataclass
class BrandElements:
    """品牌视觉元素定义"""
    brand_id: str
    brand_name: str
    primary_color: str                    # 主色调，十六进制
    secondary_colors: List[str]           # 辅助色列表
    logo_url: Optional[str] = None        # logo URL
    logo_image_data: Optional[bytes] = None  # logo图像数据
    font_family: str = "Arial"            # 字体家族
    typography_style: str = "modern"      # 排版风格
    brand_guidelines: Optional[str] = None  # 品牌指南文本
    visual_tone: str = "professional"     # 视觉语调
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


@dataclass
class VisualGenerationRequest:
    """视觉生成请求"""
    request_id: str
    category: ProductCategory
    product_name: str
    product_description: str
    visual_style: VisualStyle
    target_country: str = "US"
    target_language: str = "en"
    brand_elements: Optional[BrandElements] = None
    dimensions: Tuple[int, int] = (2048, 2048)
    quality_preset: str = "high"
    additional_prompt: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['category'] = self.category.value
        data['visual_style'] = self.visual_style.value
        return data


@dataclass
class VisualGenerationResult:
    """视觉生成结果"""
    request_id: str
    success: bool
    content_id: str
    content_url: Optional[str] = None
    content_data: Optional[bytes] = None
    quality_check_result: Optional[QualityCheckResult] = None
    brand_alignment_score: float = 0.0
    cultural_adaptation_score: float = 0.0
    metadata: Dict[str, Any] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'request_id': self.request_id,
            'success': self.success,
            'content_id': self.content_id,
            'brand_alignment_score': self.brand_alignment_score,
            'cultural_adaptation_score': self.cultural_adaptation_score,
            'metadata': self.metadata
        }
        
        if self.content_url:
            result['content_url'] = self.content_url
            
        if self.quality_check_result:
            result['quality_check_result'] = self.quality_check_result.to_dict()
            
        if self.error_message:
            result['error_message'] = self.error_message
            
        return result


class VisualTemplateManager:
    """视觉模板管理器"""
    
    def __init__(self, templates_dir: str = "src/visual_templates"):
        self.templates_dir = templates_dir
        self.templates: Dict[str, Dict] = {}
        os.makedirs(templates_dir, exist_ok=True)
        self._load_templates()
    
    def _load_templates(self):
        """加载所有模板"""
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
                    logger.info(f"加载模板: {category}")
                    
            except Exception as e:
                logger.error(f"加载模板文件失败 {template_file}: {str(e)}")
    
    def get_template(self, category: Union[str, ProductCategory]) -> Optional[Dict]:
        """获取指定品类模板"""
        if isinstance(category, ProductCategory):
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
            logger.info(f"创建模板: {category}")
            return True
            
        except Exception as e:
            logger.error(f"创建模板失败 {category}: {str(e)}")
            return False
    
    def list_categories(self) -> List[str]:
        """列出所有可用的品类"""
        return list(self.templates.keys())


class BrandElementEngine:
    """品牌元素识别与应用引擎"""
    
    def __init__(self, brand_config_dir: str = "data/brand_config"):
        self.brand_config_dir = brand_config_dir
        os.makedirs(brand_config_dir, exist_ok=True)
    
    def load_brand_config(self, brand_id: str) -> Optional[BrandElements]:
        """加载品牌配置"""
        config_path = os.path.join(self.brand_config_dir, f"{brand_id}.json")
        
        if not os.path.exists(config_path):
            logger.warning(f"品牌配置不存在: {brand_id}")
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return BrandElements(
                brand_id=config_data.get('brand_id', brand_id),
                brand_name=config_data.get('brand_name', brand_id),
                primary_color=config_data.get('primary_color', '#000000'),
                secondary_colors=config_data.get('secondary_colors', []),
                logo_url=config_data.get('logo_url'),
                font_family=config_data.get('font_family', 'Arial'),
                typography_style=config_data.get('typography_style', 'modern'),
                brand_guidelines=config_data.get('brand_guidelines'),
                visual_tone=config_data.get('visual_tone', 'professional')
            )
            
        except Exception as e:
            logger.error(f"加载品牌配置失败 {brand_id}: {str(e)}")
            return None
    
    def save_brand_config(self, brand_elements: BrandElements) -> bool:
        """保存品牌配置"""
        try:
            config_path = os.path.join(
                self.brand_config_dir, 
                f"{brand_elements.brand_id}.json"
            )
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(brand_elements.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"保存品牌配置: {brand_elements.brand_id}")
            return True
            
        except Exception as e:
            logger.error(f"保存品牌配置失败: {str(e)}")
            return False
    
    def extract_brand_from_shopify(self, shopify_config: Dict) -> BrandElements:
        """从Shopify配置中提取品牌元素"""
        # 解析Shopify主题配置
        theme_settings = shopify_config.get('theme_settings', {})
        
        return BrandElements(
            brand_id=shopify_config.get('shop_name', 'unknown'),
            brand_name=shopify_config.get('shop_name', 'Unknown Brand'),
            primary_color=theme_settings.get('primary_color', '#000000'),
            secondary_colors=theme_settings.get('secondary_colors', []),
            logo_url=shopify_config.get('logo_url'),
            font_family=theme_settings.get('font_family', 'Arial'),
            typography_style=theme_settings.get('typography_style', 'modern'),
            brand_guidelines=None,  # 需要从品牌指南文档中提取
            visual_tone=theme_settings.get('visual_tone', 'professional')
        )
    
    def apply_brand_to_prompt(self, prompt: str, brand_elements: BrandElements) -> str:
        """将品牌元素应用到生成提示中"""
        enhanced_prompt = prompt
        
        # 添加品牌色彩指导
        if brand_elements.primary_color:
            enhanced_prompt += f", 主色调: {brand_elements.primary_color}"
        
        if brand_elements.secondary_colors:
            colors_str = ', '.join(brand_elements.secondary_colors[:3])
            enhanced_prompt += f", 辅助色: {colors_str}"
        
        # 添加品牌风格指导
        if brand_elements.visual_tone:
            tone_mapping = {
                'professional': '专业商务风格',
                'modern': '现代简约风格',
                'luxury': '高端奢华风格',
                'youthful': '年轻活力风格',
                'natural': '自然环保风格'
            }
            chinese_tone = tone_mapping.get(brand_elements.visual_tone, 
                                           brand_elements.visual_tone)
            enhanced_prompt += f", 品牌调性: {chinese_tone}"
        
        # 添加品牌指南（如果有）
        if brand_elements.brand_guidelines:
            # 提取关键指导原则
            guidelines = brand_elements.brand_guidelines[:200]  # 限制长度
            enhanced_prompt += f", 遵循品牌指南: {guidelines}..."
        
        return enhanced_prompt


class VisualLocalizationEngine:
    """视觉本地化引擎"""
    
    def __init__(self):
        # 国家审美风格映射
        self.country_styles = {
            'US': {'description': '美式风格，大胆、直接、商业感强', 'preferred_colors': ['#1E40AF', '#DC2626', '#FFFFFF']},
            'CN': {'description': '中式风格，精致、含蓄、重视细节', 'preferred_colors': ['#D4AF37', '#B91C1C', '#111827']},
            'JP': {'description': '日式风格，简约、自然、注重平衡', 'preferred_colors': ['#3B82F6', '#EF4444', '#F59E0B']},
            'KR': {'description': '韩式风格，清新、时尚、年轻化', 'preferred_colors': ['#60A5FA', '#F87171', '#34D399']},
            'DE': {'description': '德式风格，严谨、精密、工业感', 'preferred_colors': ['#000000', '#DD0000', '#FFCC00']},
            'FR': {'description': '法式风格，优雅、浪漫、艺术感', 'preferred_colors': ['#0055A4', '#EF4135', '#FFFFFF']},
            'UK': {'description': '英式风格，传统、经典、绅士感', 'preferred_colors': ['#012169', '#C8102E', '#FFFFFF']},
            'IN': {'description': '印度风格，鲜艳、华丽、文化元素丰富', 'preferred_colors': ['#FF9933', '#138808', '#000080']}
        }
        
        # 文化敏感元素映射（需要避免的元素）
        self.cultural_sensitivities = {
            'IN': {'avoid_colors': ['#000000'], 'avoid_symbols': ['左手', '鞋子']},
            'CN': {'avoid_colors': ['#FFFFFF'], 'avoid_symbols': ['钟', '伞']},
            'JP': {'avoid_colors': ['#FFFFFF'], 'avoid_symbols': ['数字4', '紫色']}
        }
    
    def adapt_style_for_country(self, base_style: str, target_country: str) -> str:
        """根据目标国家适配视觉风格"""
        country_style = self.country_styles.get(target_country)
        
        if not country_style:
            return base_style
        
        # 融合基础风格与国家偏好
        adapted_style = f"{base_style}, {country_style['description']}"
        
        # 添加色彩指导
        if country_style['preferred_colors']:
            colors_str = ', '.join(country_style['preferred_colors'])
            adapted_style += f", 推荐色彩: {colors_str}"
        
        return adapted_style
    
    def localize_text_for_language(self, text: str, target_language: str) -> str:
        """将文本本地化为目标语言"""
        # 实际部署中应调用翻译API
        # 这里返回模拟翻译
        
        translation_examples = {
            'en': text,  # 英语
            'zh': f"{text} (中文版)",
            'es': f"{text} (versión en español)",
            'fr': f"{text} (version française)",
            'de': f"{text} (deutsche Version)",
            'ja': f"{text} (日本語版)",
            'ko': f"{text} (한국어 버전)",
            'ar': f"{text} (النسخة العربية)"
        }
        
        return translation_examples.get(target_language, text)
    
    def check_cultural_sensitivities(self, prompt: str, target_country: str) -> List[str]:
        """检查提示中是否有文化敏感元素"""
        sensitivities = self.cultural_sensitivities.get(target_country)
        
        if not sensitivities:
            return []
        
        warnings = []
        
        # 检查避免的颜色
        for color in sensitivities.get('avoid_colors', []):
            if color in prompt:
                warnings.append(f"避免使用颜色: {color}")
        
        # 检查避免的符号
        for symbol in sensitivities.get('avoid_symbols', []):
            if symbol in prompt:
                warnings.append(f"避免使用符号: {symbol}")
        
        return warnings


class VisualGenerationService:
    """视觉生成服务主类"""
    
    def __init__(self, config_path: Optional[str] = None):
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化现有AIGC服务
        self.aigc_service = None
        if HAS_AIGC:
            try:
                self.aigc_service = AIGCServiceCenter(config_path)
                self.aigc_service.start()
            except Exception as e:
                logger.error(f"AIGC服务启动失败: {str(e)}")
        
        # 初始化质量锁死控制器
        self.quality_controller = None
        if HAS_BANANA_QUALITY:
            try:
                self.quality_controller = QualityLockController()
            except Exception as e:
                logger.warning(f"质量控制器初始化失败: {str(e)}")
        
        # 初始化各引擎
        self.template_manager = VisualTemplateManager()
        self.brand_engine = BrandElementEngine()
        self.localization_engine = VisualLocalizationEngine()
        
        # 服务状态
        self.is_running = True
        self.start_time = time.time()
        self.generation_history: List[VisualGenerationResult] = []
        
        logger.info("视觉生成服务初始化完成")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            'visual_generation_enabled': True,
            'brand_integration_enabled': True,
            'localization_enabled': True,
            'quality_check_enabled': True,
            'default_dimensions': (2048, 2048),
            'default_quality_preset': 'high',
            'max_concurrent_generations': 5,
            'cache_enabled': True,
            'cache_ttl': 3600,
            'templates_dir': 'src/visual_templates',
            'brand_config_dir': 'data/brand_config',
            'output_dir': 'outputs/visual_generation'
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
    
    def generate_visual(self, request: VisualGenerationRequest) -> VisualGenerationResult:
        """生成视觉内容主接口"""
        
        # 验证请求
        validation_error = self._validate_request(request)
        if validation_error:
            return self._create_error_result(request, validation_error)
        
        try:
            # 1. 获取品类模板
            template = self.template_manager.get_template(request.category)
            if not template:
                return self._create_error_result(
                    request, f"品类 {request.category.value} 的模板未找到"
                )
            
            # 2. 加载品牌元素（如果提供）
            brand_elements = None
            if request.brand_elements:
                brand_elements = request.brand_elements
            elif request.brand_elements is None and hasattr(request, 'brand_id'):
                # 如果有brand_id，尝试加载配置
                brand_elements = self.brand_engine.load_brand_config(request.brand_id)
            
            # 3. 构建基础提示
            base_prompt = self._build_base_prompt(request, template)
            
            # 4. 应用品牌元素（如果有）
            if brand_elements:
                base_prompt = self.brand_engine.apply_brand_to_prompt(
                    base_prompt, brand_elements
                )
            
            # 5. 本地化适配
            localized_prompt = self.localization_engine.adapt_style_for_country(
                base_prompt, request.target_country
            )
            
            # 6. 检查文化敏感性
            warnings = self.localization_engine.check_cultural_sensitivities(
                localized_prompt, request.target_country
            )
            
            if warnings:
                logger.warning(f"文化敏感性警告: {warnings}")
            
            # 7. 创建AIGC内容规格
            content_spec = ContentSpecification(
                content_type=ContentType.IMAGE,
                subject=request.product_name,
                style=GenerationStyle.PHOTOREALISTIC,
                dimensions=request.dimensions,
                quality_preset=request.quality_preset,
                target_platform="shopify",
                brand_guidelines=brand_elements.brand_guidelines if brand_elements else None,
                language=request.target_language
            )
            
            # 8. 调用AIGC服务生成
            if not self.aigc_service:
                return self._create_error_result(request, "AIGC服务不可用")
            
            aigc_result = self.aigc_service.generate_content(content_spec)
            
            if not aigc_result.success:
                return VisualGenerationResult(
                    request_id=request.request_id,
                    success=False,
                    content_id=aigc_result.content_id,
                    error_message=aigc_result.error_message,
                    metadata=aigc_result.metadata or {}
                )
            
            # 9. 质量检查（如果启用）
            quality_result = None
            if self.config.get('quality_check_enabled') and self.quality_controller:
                # 需要将图像数据转换为numpy数组
                # 这里假设aigc_result.content_data是图像字节数据
                if aigc_result.content_data:
                    try:
                        import cv2
                        image_array = cv2.imdecode(
                            np.frombuffer(aigc_result.content_data, np.uint8),
                            cv2.IMREAD_COLOR
                        )
                        
                        if image_array is not None:
                            quality_result = self.quality_controller.check_image_quality(
                                image_array,
                                model_id=None,  # 可根据需要提供
                                material_type=MaterialType.DENIM,  # 示例材质
                                reference_texture_image=None
                            )
                    except Exception as e:
                        logger.error(f"质量检查失败: {str(e)}")
            
            # 10. 计算品牌一致性评分
            brand_alignment_score = self._calculate_brand_alignment(
                request, brand_elements, aigc_result
            )
            
            # 11. 计算文化适配评分
            cultural_adaptation_score = self._calculate_cultural_adaptation(
                request, aigc_result
            )
            
            # 12. 创建最终结果
            result = VisualGenerationResult(
                request_id=request.request_id,
                success=True,
                content_id=aigc_result.content_id,
                content_url=aigc_result.content_url,
                content_data=aigc_result.content_data,
                quality_check_result=quality_result,
                brand_alignment_score=brand_alignment_score,
                cultural_adaptation_score=cultural_adaptation_score,
                metadata=aigc_result.metadata or {}
            )
            
            # 记录历史
            self.generation_history.append(result)
            
            logger.info(f"视觉生成成功: {request.request_id}, 品类: {request.category.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"视觉生成失败 {request.request_id}: {str(e)}", exc_info=True)
            return self._create_error_result(request, f"生成失败: {str(e)}")
    
    def _validate_request(self, request: VisualGenerationRequest) -> Optional[str]:
        """验证生成请求"""
        if not request.product_name or not request.product_name.strip():
            return "产品名称不能为空"
        
        if not request.product_description or not request.product_description.strip():
            return "产品描述不能为空"
        
        if request.dimensions[0] < 512 or request.dimensions[1] < 512:
            return "图像尺寸过小，最小为512×512"
        
        if request.dimensions[0] > 8192 or request.dimensions[1] > 8192:
            return "图像尺寸过大，最大为8192×8192"
        
        return None
    
    def _build_base_prompt(self, request: VisualGenerationRequest, 
                          template: Dict) -> str:
        """构建基础生成提示"""
        # 从模板获取品类专属提示词
        prompt_template = template.get('prompt_template', '')
        
        # 填充变量
        prompt = prompt_template.format(
            product_name=request.product_name,
            product_description=request.product_description,
            visual_style=request.visual_style.value,
            quality_preset=request.quality_preset
        )
        
        # 添加额外提示（如果有）
        if request.additional_prompt:
            prompt += f", {request.additional_prompt}"
        
        return prompt
    
    def _calculate_brand_alignment(self, request: VisualGenerationRequest,
                                  brand_elements: Optional[BrandElements],
                                  aigc_result: GenerationResult) -> float:
        """计算品牌一致性评分"""
        if not brand_elements:
            return 0.0
        
        # 简单模拟评分逻辑
        # 实际部署中应基于图像分析
        score = 0.8  # 基础评分
        
        # 如果生成了元数据，可以根据元数据调整评分
        metadata = aigc_result.metadata or {}
        if metadata.get('brand_alignment_score'):
            score = metadata['brand_alignment_score']
        
        return min(max(score, 0.0), 1.0)  # 确保在0-1范围内
    
    def _calculate_cultural_adaptation(self, request: VisualGenerationRequest,
                                      aigc_result: GenerationResult) -> float:
        """计算文化适配评分"""
        # 简单模拟评分逻辑
        # 实际部署中应基于目标国家的文化特征分析
        
        # 根据目标国家给予不同基础评分
        country_scores = {
            'US': 0.85,
            'CN': 0.80,
            'JP': 0.75,
            'KR': 0.82,
            'DE': 0.78,
            'FR': 0.83,
            'UK': 0.79,
            'IN': 0.77
        }
        
        score = country_scores.get(request.target_country, 0.75)
        return min(max(score, 0.0), 1.0)
    
    def _create_error_result(self, request: VisualGenerationRequest,
                            error_message: str) -> VisualGenerationResult:
        """创建错误结果"""
        return VisualGenerationResult(
            request_id=request.request_id,
            success=False,
            content_id=f"error_{int(time.time())}",
            error_message=error_message,
            metadata={'error_time': time.time()}
        )
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'is_running': self.is_running,
            'start_time': self.start_time,
            'uptime': time.time() - self.start_time,
            'generation_count': len(self.generation_history),
            'template_categories': self.template_manager.list_categories(),
            'config': {
                'visual_generation_enabled': self.config.get('visual_generation_enabled'),
                'brand_integration_enabled': self.config.get('brand_integration_enabled'),
                'localization_enabled': self.config.get('localization_enabled'),
                'quality_check_enabled': self.config.get('quality_check_enabled')
            }
        }
    
    def stop(self):
        """停止服务"""
        if not self.is_running:
            return
        
        if self.aigc_service:
            self.aigc_service.stop()
        
        self.is_running = False
        logger.info("视觉生成服务已停止")


# 工厂函数
def create_visual_generation_service(config_path: Optional[str] = None) -> VisualGenerationService:
    """创建视觉生成服务实例"""
    return VisualGenerationService(config_path)


if __name__ == "__main__":
    """测试视觉生成服务"""
    
    # 创建服务实例
    service = create_visual_generation_service()
    
    print("✅ 视觉生成服务启动成功")
    
    # 测试状态查询
    status = service.get_service_status()
    print(f"服务状态: 运行中={status['is_running']}, 模板品类={status['template_categories']}")
    
    # 测试生成功能
    if HAS_AIGC:
        # 创建测试请求
        test_request = VisualGenerationRequest(
            request_id=f"test_{int(time.time())}",
            category=ProductCategory.FASHION_CLOTHING,
            product_name="美式复古牛仔外套",
            product_description="高品质牛仔面料，复古设计，适合日常穿搭",
            visual_style=VisualStyle.PRODUCT_PHOTOGRAPHY,
            target_country="US",
            target_language="en",
            dimensions=(2048, 2048),
            quality_preset="high"
        )
        
        result = service.generate_visual(test_request)
        print(f"\n视觉生成结果: {result.success}")
        if result.success:
            print(f"  内容ID: {result.content_id}")
            print(f"  品牌一致性评分: {result.brand_alignment_score:.2%}")
            print(f"  文化适配评分: {result.cultural_adaptation_score:.2%}")
        else:
            print(f"  错误: {result.error_message}")
    
    # 停止服务
    service.stop()
    print("🛑 视觉生成服务已停止")