#!/usr/bin/env python3
"""
品牌元素识别与应用引擎

负责从Shopify独立站品牌配置中自动提取品牌视觉元素，
并在图像生成中正确应用，确保品牌一致性。
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


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


class BrandElementEngine:
    """品牌元素识别与应用引擎"""
    
    def __init__(self, brand_config_dir: str = "data/brand_config"):
        self.brand_config_dir = brand_config_dir
        os.makedirs(brand_config_dir, exist_ok=True)
        logger.info(f"品牌元素引擎初始化完成，配置目录: {brand_config_dir}")
    
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
        """
        从Shopify配置中提取品牌元素
        
        Args:
            shopify_config: Shopify店铺配置字典，包含：
                - shop_name: 店铺名称
                - theme_settings: 主题设置（颜色、字体等）
                - logo_url: logo URL
                
        Returns:
            BrandElements实例
        """
        # 解析Shopify主题配置
        theme_settings = shopify_config.get('theme_settings', {})
        
        # 提取主色调（默认为品牌蓝色）
        primary_color = theme_settings.get('primary_color', '#000000')
        if primary_color == '#000000':
            # Shopify默认主色调
            primary_color = '#008060'
        
        # 提取辅助色
        secondary_colors = theme_settings.get('secondary_colors', [])
        if not secondary_colors:
            secondary_colors = ['#FFFFFF', '#F7F7F7', '#333333']
        
        # 提取字体
        font_family = theme_settings.get('font_family', 'Arial')
        if 'font_families' in theme_settings:
            # Shopify主题可能提供字体家族列表
            font_families = theme_settings.get('font_families', {})
            if 'base' in font_families:
                font_family = font_families['base'].get('family', 'Arial')
        
        # 确定视觉语调
        visual_tone = self._detect_visual_tone(theme_settings)
        
        return BrandElements(
            brand_id=shopify_config.get('shop_name', 'unknown').lower().replace(' ', '_'),
            brand_name=shopify_config.get('shop_name', 'Unknown Brand'),
            primary_color=primary_color,
            secondary_colors=secondary_colors,
            logo_url=shopify_config.get('logo_url'),
            font_family=font_family,
            typography_style=theme_settings.get('typography_style', 'modern'),
            brand_guidelines=self._extract_guidelines(shopify_config),
            visual_tone=visual_tone
        )
    
    def apply_brand_to_prompt(self, prompt: str, brand_elements: BrandElements) -> str:
        """
        将品牌元素应用到生成提示中
        
        Args:
            prompt: 基础生成提示
            brand_elements: 品牌视觉元素
            
        Returns:
            增强后的生成提示
        """
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
                'natural': '自然环保风格',
                'minimalist': '极简主义风格',
                'tech': '科技感风格',
                'handmade': '手工艺风格'
            }
            chinese_tone = tone_mapping.get(brand_elements.visual_tone, 
                                           brand_elements.visual_tone)
            enhanced_prompt += f", 品牌调性: {chinese_tone}"
        
        # 添加品牌指南（如果有）
        if brand_elements.brand_guidelines:
            # 提取关键指导原则
            guidelines = brand_elements.brand_guidelines[:200]  # 限制长度
            enhanced_prompt += f", 遵循品牌指南: {guidelines}..."
        
        # 添加字体指导（如果特别指定）
        if brand_elements.font_family and brand_elements.font_family != "Arial":
            enhanced_prompt += f", 字体风格: {brand_elements.font_family}"
        
        return enhanced_prompt
    
    def _detect_visual_tone(self, theme_settings: Dict) -> str:
        """检测品牌视觉语调"""
        
        # 基于颜色分析
        primary_color = theme_settings.get('primary_color', '#000000')
        
        # 颜色到语调的映射
        color_tone_map = {
            '#008060': 'professional',    # Shopify绿
            '#000000': 'minimalist',      # 黑色
            '#FFFFFF': 'minimalist',      # 白色
            '#FF6B6B': 'youthful',       # 珊瑚红
            '#4ECDC4': 'natural',        # 薄荷绿
            '#FFD166': 'youthful',       # 明黄
            '#9B5DE5': 'modern',         # 紫色
            '#F15BB5': 'youthful',       # 粉色
            '#00BBF9': 'tech',           # 科技蓝
            '#F9844A': 'natural'         # 橙色
        }
        
        # 查找最接近的颜色
        for color, tone in color_tone_map.items():
            if primary_color.lower() == color.lower():
                return tone
        
        # 默认可专业
        return 'professional'
    
    def _extract_guidelines(self, shopify_config: Dict) -> Optional[str]:
        """从Shopify配置中提取品牌指南文本"""
        
        # 可能包含品牌指南的字段
        possible_fields = [
            'brand_description',
            'shop_description', 
            'about_us',
            'brand_story',
            'mission_statement'
        ]
        
        for field in possible_fields:
            if field in shopify_config and shopify_config[field]:
                return shopify_config[field]
        
        # 从主题设置中提取
        theme_settings = shopify_config.get('theme_settings', {})
        if 'brand' in theme_settings:
            brand_settings = theme_settings.get('brand', {})
            for field in possible_fields:
                if field in brand_settings and brand_settings[field]:
                    return brand_settings[field]
        
        return None
    
    def create_default_brand_config(self, brand_id: str, brand_name: str) -> BrandElements:
        """创建默认品牌配置"""
        
        return BrandElements(
            brand_id=brand_id,
            brand_name=brand_name,
            primary_color='#008060',  # Shopify品牌绿
            secondary_colors=['#FFFFFF', '#F7F7F7', '#333333'],
            logo_url=None,
            font_family='Arial',
            typography_style='modern',
            brand_guidelines=f"这是 {brand_name} 的品牌指南，请确保所有视觉内容符合品牌形象。",
            visual_tone='professional'
        )


# 测试函数
def test_brand_element_engine():
    """测试品牌元素引擎"""
    
    import tempfile
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化引擎
        engine = BrandElementEngine(brand_config_dir=tmpdir)
        
        # 创建测试品牌配置
        test_brand = engine.create_default_brand_config(
            brand_id="test_brand",
            brand_name="Test Brand"
        )
        
        # 保存配置
        save_success = engine.save_brand_config(test_brand)
        print(f"保存品牌配置: {'成功' if save_success else '失败'}")
        
        # 加载配置
        loaded_brand = engine.load_brand_config("test_brand")
        print(f"加载品牌配置: {'成功' if loaded_brand else '失败'}")
        
        if loaded_brand:
            print(f"品牌名称: {loaded_brand.brand_name}")
            print(f"主色调: {loaded_brand.primary_color}")
            print(f"辅助色: {loaded_brand.secondary_colors}")
        
        # 测试Shopify配置提取
        shopify_config = {
            'shop_name': 'My Shopify Store',
            'theme_settings': {
                'primary_color': '#FF6B6B',
                'secondary_colors': ['#FFFFFF', '#FFE66D', '#4ECDC4'],
                'font_family': 'Helvetica',
                'typography_style': 'modern'
            },
            'logo_url': 'https://example.com/logo.png',
            'brand_description': '我们是一个专注于可持续时尚的品牌。'
        }
        
        extracted_brand = engine.extract_brand_from_shopify(shopify_config)
        print(f"\\n从Shopify提取品牌:")
        print(f"  品牌ID: {extracted_brand.brand_id}")
        print(f"  品牌名称: {extracted_brand.brand_name}")
        print(f"  主色调: {extracted_brand.primary_color}")
        print(f"  视觉语调: {extracted_brand.visual_tone}")
        
        # 测试提示词增强
        base_prompt = "专业产品摄影，展示产品设计"
        enhanced_prompt = engine.apply_brand_to_prompt(base_prompt, extracted_brand)
        print(f"\\n提示词增强:")
        print(f"  基础提示: {base_prompt}")
        print(f"  增强提示: {enhanced_prompt}")
        
        print(f"\\n✅ 品牌元素引擎测试完成")


if __name__ == "__main__":
    test_brand_element_engine()