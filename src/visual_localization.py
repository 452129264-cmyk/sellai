#!/usr/bin/env python3
"""
视觉本地化引擎

负责视觉内容的全球化适配，包括：
1. 各国审美风格适配
2. 多语种文案自动翻译与嵌入
3. 文化敏感元素识别与处理
4. 本地化视觉策略生成
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class CountryCode(Enum):
    """国家代码枚举"""
    US = "US"  # 美国
    CN = "CN"  # 中国
    JP = "JP"  # 日本
    KR = "KR"  # 韩国
    DE = "DE"  # 德国
    FR = "FR"  # 法国
    UK = "UK"  # 英国
    IN = "IN"  # 印度
    AU = "AU"  # 澳大利亚
    CA = "CA"  # 加拿大
    BR = "BR"  # 巴西
    RU = "RU"  # 俄罗斯
    MX = "MX"  # 墨西哥
    SA = "SA"  # 沙特阿拉伯
    AE = "AE"  # 阿联酋
    SG = "SG"  # 新加坡
    TW = "TW"  # 台湾
    HK = "HK"  # 香港
    ES = "ES"  # 西班牙
    IT = "IT"  # 意大利


class LanguageCode(Enum):
    """语言代码枚举"""
    EN = "en"  # 英语
    ZH = "zh"  # 中文
    ES = "es"  # 西班牙语
    FR = "fr"  # 法语
    DE = "de"  # 德语
    JA = "ja"  # 日语
    KO = "ko"  # 韩语
    AR = "ar"  # 阿拉伯语
    PT = "pt"  # 葡萄牙语
    RU = "ru"  # 俄语
    IT = "it"  # 意大利语


class VisualStyle(Enum):
    """视觉风格枚举"""
    MODERN = "modern"          # 现代风格
    TRADITIONAL = "traditional" # 传统风格
    MINIMALIST = "minimalist"  # 极简风格
    LUXURY = "luxury"         # 奢华风格
    YOUTHFUL = "youthful"     # 年轻风格
    NATURAL = "natural"       # 自然风格
    TECH = "tech"             # 科技风格


class VisualLocalizationEngine:
    """视觉本地化引擎"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化本地化引擎"""
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化国家风格映射
        self.country_styles = self._init_country_styles()
        
        # 初始化文化敏感元素映射
        self.cultural_sensitivities = self._init_cultural_sensitivities()
        
        # 初始化翻译映射（模拟）
        self.translation_examples = self._init_translation_examples()
        
        logger.info("视觉本地化引擎初始化完成")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        
        default_config = {
            'enabled': True,
            'default_language': 'en',
            'default_country': 'US',
            'translation_service': 'simulated',  # simulated, deepl, google
            'cultural_check_enabled': True,
            'style_adaptation_enabled': True,
            'max_concurrent_localizations': 5,
            'cache_enabled': True,
            'cache_ttl': 3600,
            'localization_rules_dir': 'data/localization_rules'
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
    
    def _init_country_styles(self) -> Dict[str, Dict[str, Any]]:
        """初始化国家审美风格映射"""
        
        return {
            'US': {
                'description': '美式风格，大胆、直接、商业感强，注重实用和创新',
                'preferred_colors': ['#1E40AF', '#DC2626', '#FFFFFF', '#000000'],
                'composition_style': '动态，有冲击力，元素鲜明',
                'typography_preferences': '无衬线字体，简洁易读，字号较大',
                'cultural_context': '多元文化，个人主义，创业精神',
                'visual_priorities': ['清晰度', '实用性', '创新性', '品牌一致性']
            },
            'CN': {
                'description': '中式风格，精致、含蓄、重视细节，体现传统文化底蕴',
                'preferred_colors': ['#D4AF37', '#B91C1C', '#111827', '#FACC15'],
                'composition_style': '对称，平衡，有层次感',
                'typography_preferences': '宋体或黑体，优雅稳重，讲究布局',
                'cultural_context': '集体主义，尊重传统，重视家庭',
                'visual_priorities': ['精致度', '传统元素', '和谐感', '寓意深刻']
            },
            'JP': {
                'description': '日式风格，简约、自然、注重平衡和留白',
                'preferred_colors': ['#3B82F6', '#EF4444', '#F59E0B', '#FFFFFF'],
                'composition_style': '极简，有禅意，注重细节',
                'typography_preferences': '明朝体或ゴシック体，精致规范',
                'cultural_context': '集体主义，尊重传统，追求完美',
                'visual_priorities': ['简约美', '平衡感', '细节精致', '自然元素']
            },
            'KR': {
                'description': '韩式风格，清新、时尚、年轻化，注重潮流元素',
                'preferred_colors': ['#60A5FA', '#F87171', '#34D399', '#FFFFFF'],
                'composition_style': '活泼，有动感，色彩明亮',
                'typography_preferences': '圆润字体，可爱风格，排版自由',
                'cultural_context': '快速变化，重视外表，潮流敏感',
                'visual_priorities': ['时尚感', '年轻化', '色彩鲜艳', '视觉冲击']
            },
            'DE': {
                'description': '德式风格，严谨、精密、工业感强，注重品质和效率',
                'preferred_colors': ['#000000', '#DD0000', '#FFCC00', '#FFFFFF'],
                'composition_style': '严谨，有序，功能导向',
                'typography_preferences': '无衬线字体，精确规范，间距标准',
                'cultural_context': '注重规则，追求品质，工程思维',
                'visual_priorities': ['精确度', '功能性', '简约设计', '工业美学']
            },
            'FR': {
                'description': '法式风格，优雅、浪漫、艺术感强，注重美感和情感',
                'preferred_colors': ['#0055A4', '#EF4135', '#FFFFFF', '#000000'],
                'composition_style': '优雅，有艺术感，讲究氛围',
                'typography_preferences': '衬线字体，优雅华丽，讲究对比',
                'cultural_context': '重视艺术，追求生活品质，情感表达',
                'visual_priorities': ['艺术感', '优雅度', '情感表达', '品牌故事']
            },
            'UK': {
                'description': '英式风格，传统、经典、绅士感，注重品质和传承',
                'preferred_colors': ['#012169', '#C8102E', '#FFFFFF', '#000000'],
                'composition_style': '经典，稳重，有历史感',
                'typography_preferences': '衬线字体，传统规范，讲究细节',
                'cultural_context': '尊重传统，重视礼仪，追求品质',
                'visual_priorities': ['经典感', '品质感', '传统元素', '绅士风格']
            },
            'IN': {
                'description': '印度风格，鲜艳、华丽、文化元素丰富，注重宗教和传统',
                'preferred_colors': ['#FF9933', '#138808', '#000080', '#FFFFFF'],
                'composition_style': '丰富，华丽，色彩斑斓',
                'typography_preferences': '装饰性字体，复杂华丽，讲究对称',
                'cultural_context': '多元宗教，重视家庭，节日文化',
                'visual_priorities': ['色彩丰富', '文化元素',  '节日氛围', '传统图案']
            }
        }
    
    def _init_cultural_sensitivities(self) -> Dict[str, Dict[str, List[str]]]:
        """初始化文化敏感元素映射"""
        
        return {
            'CN': {
                'avoid_colors': ['白色', '黑色'],  # 特定场合
                'avoid_symbols': ['钟', '伞', '梨'],  # 谐音不吉利
                'sensitive_themes': ['政治', '历史争议'],
                'preferred_symbols': ['龙', '凤', '福', '寿']
            },
            'JP': {
                'avoid_colors': ['紫色'],  # 特定场合
                'avoid_symbols': ['数字4', '梳子'],
                'sensitive_themes': ['二战', '天皇'],
                'preferred_symbols': ['樱花', '富士山', '鹤', '龟']
            },
            'KR': {
                'avoid_colors': ['红色'],  # 特定场合
                'avoid_symbols': ['日本国旗'],
                'sensitive_themes': ['日本殖民', '朝鲜战争'],
                'preferred_symbols': ['太极', '无穷花']
            },
            'IN': {
                'avoid_colors': ['黑色'],  # 特定场合
                'avoid_symbols': ['左手', '鞋子', '皮革'],
                'sensitive_themes': ['宗教冲突', '种姓制度'],
                'preferred_symbols': ['象神', '莲花', '曼荼罗']
            },
            'SA': {
                'avoid_colors': ['黄色'],  # 特定场合
                'avoid_symbols': ['猪', '酒', '十字架'],
                'sensitive_themes': ['宗教', '政治体制'],
                'preferred_symbols': ['清真寺', '新月']
            }
        }
    
    def _init_translation_examples(self) -> Dict[str, Dict[str, str]]:
        """初始化翻译示例映射"""
        
        return {
            'product_name': {
                'en': 'Premium Denim Jacket',
                'zh': '高端牛仔外套',
                'es': 'Chaqueta de Denim Premium',
                'fr': 'Veste en Jean Premium',
                'de': 'Premium Denim Jacke',
                'ja': 'プレミアムデニムジャケット',
                'ko': '프리미엄 데님 자켓',
                'ar': 'سترة الدنيم المميزة'
            },
            'product_description': {
                'en': 'High-quality denim material with retro design, perfect for daily wear',
                'zh': '高品质牛仔面料，复古设计，适合日常穿搭',
                'es': 'Material de denim de alta calidad con diseño retro, perfecto para el uso diario',
                'fr': 'Tissu denim de haute qualité avec design rétro, parfait pour un usage quotidien',
                'de': 'Hochwertiges Denimmaterial mit Retro-Design, perfekt für den täglichen Gebrauch',
                'ja': 'レトロデザインの高品質デニム素材で、日常着に最適です',
                'ko': '레트로 디자인의 고급 데님 소재로 일상복에 완벽합니다',
                'ar': 'مادة الدنيم عالية الجودة بتصميم رجعي، مثالية للارتداء اليومي'
            }
        }
    
    def adapt_style_for_country(self, base_prompt: str, target_country: str, 
                              target_language: str = "en") -> str:
        """
        根据目标国家适配视觉风格
        
        Args:
            base_prompt: 基础生成提示
            target_country: 目标国家代码
            target_language: 目标语言代码
            
        Returns:
            适配后的生成提示
        """
        
        if not self.config.get('enabled', True) or not self.config.get('style_adaptation_enabled', True):
            return base_prompt
        
        country_style = self.country_styles.get(target_country.upper())
        if not country_style:
            logger.warning(f"未找到国家 {target_country} 的视觉风格配置，使用基础提示")
            return base_prompt
        
        # 构建本地化提示
        localization_parts = []
        
        # 添加国家风格描述
        localization_parts.append(f"风格适配: {country_style['description']}")
        
        # 添加色彩偏好
        if country_style.get('preferred_colors'):
            colors_str = ', '.join(country_style['preferred_colors'][:3])
            localization_parts.append(f"推荐色彩: {colors_str}")
        
        # 添加构图风格
        if country_style.get('composition_style'):
            localization_parts.append(f"构图风格: {country_style['composition_style']}")
        
        # 添加文化背景提示
        if country_style.get('cultural_context'):
            localization_parts.append(f"文化背景: {country_style['cultural_context']}")
        
        # 合并本地化提示
        if localization_parts:
            localized_prompt = f"{base_prompt}, {', '.join(localization_parts)}"
        else:
            localized_prompt = base_prompt
        
        # 语言本地化
        if target_language != 'en':
            localized_prompt = self._localize_text_for_language(
                localized_prompt, target_language
            )
        
        logger.info(f"国家 {target_country} 风格适配完成")
        return localized_prompt
    
    def check_cultural_sensitivities(self, prompt: str, target_country: str, 
                                   target_language: str = "en") -> Tuple[List[str], List[str]]:
        """
        检查提示中的文化敏感元素
        
        Args:
            prompt: 生成提示
            target_country: 目标国家代码
            target_language: 目标语言代码
            
        Returns:
            Tuple[警告信息列表, 建议修改列表]
        """
        
        if not self.config.get('enabled', True) or not self.config.get('cultural_check_enabled', True):
            return [], []
        
        sensitivities = self.cultural_sensitivities.get(target_country.upper())
        if not sensitivities:
            return [], []
        
        warnings = []
        suggestions = []
        
        # 检查避免的颜色
        avoid_colors = sensitivities.get('avoid_colors', [])
        for color in avoid_colors:
            if color in prompt:
                warnings.append(f"避免使用颜色: {color} (文化敏感)")
                suggestions.append(f"将颜色 {color} 替换为其他中性颜色")
        
        # 检查避免的符号
        avoid_symbols = sensitivities.get('avoid_symbols', [])
        for symbol in avoid_symbols:
            if symbol in prompt:
                warnings.append(f"避免使用符号: {symbol} (文化敏感)")
                suggestions.append(f"移除或替换符号 {symbol}")
        
        # 检查敏感主题
        sensitive_themes = sensitivities.get('sensitive_themes', [])
        for theme in sensitive_themes:
            if theme in prompt:
                warnings.append(f"避免提及主题: {theme} (文化敏感)")
                suggestions.append(f"移除或替换主题 {theme}")
        
        if warnings:
            logger.warning(f"发现 {len(warnings)} 个文化敏感性警告")
        
        return warnings, suggestions
    
    def localize_text_content(self, text: str, target_language: str, 
                            context: Optional[str] = None) -> str:
        """
        本地化文本内容
        
        Args:
            text: 原始文本
            target_language: 目标语言代码
            context: 上下文信息（可选）
            
        Returns:
            本地化后的文本
        """
        
        # 实际部署中应调用翻译API
        # 这里使用模拟翻译
        
        translation_method = self.config.get('translation_service', 'simulated')
        
        if translation_method == 'simulated':
            return self._simulate_translation(text, target_language, context)
        else:
            # 实际API调用占位
            logger.warning(f"翻译服务 {translation_method} 未实现，使用模拟翻译")
            return self._simulate_translation(text, target_language, context)
    
    def _localize_text_for_language(self, prompt: str, target_language: str) -> str:
        """为特定语言本地化文本"""
        
        # 简单的关键词替换
        translated_prompt = prompt
        
        # 产品名称本地化
        product_name_examples = self.translation_examples.get('product_name', {})
        if target_language in product_name_examples:
            # 替换常见的产品名称模式
            translated_prompt = translated_prompt.replace(
                'Premium Denim Jacket', product_name_examples[target_language]
            )
        
        # 添加语言提示
        language_prompt = f"，语言适配: {target_language}"
        if language_prompt not in translated_prompt:
            translated_prompt += language_prompt
        
        return translated_prompt
    
    def _simulate_translation(self, text: str, target_language: str, 
                            context: Optional[str] = None) -> str:
        """模拟翻译"""
        
        # 基于示例映射
        if text in self.translation_examples.get('product_name', {}).values():
            # 查找对应的翻译
            for source_lang, translation_map in self.translation_examples.items():
                for lang, translated_text in translation_map.items():
                    if translated_text == text and lang != target_language:
                        return translation_map.get(target_language, text)
        
        # 通用模拟翻译
        translation_prefix = {
            'zh': '[中文版] ',
            'es': '[Versión en español] ',
            'fr': '[Version française] ',
            'de': '[Deutsche Version] ',
            'ja': '[日本語版] ',
            'ko': '[한국어 버전] ',
            'ar': '[النسخة العربية] '
        }
        
        prefix = translation_prefix.get(target_language, '')
        return f"{prefix}{text} [{target_language.upper()}]"
    
    def get_localization_guidelines(self, target_country: str, 
                                  target_language: str = "en") -> Dict[str, Any]:
        """获取本地化指导原则"""
        
        country_style = self.country_styles.get(target_country.upper(), {})
        
        guidelines = {
            'target_country': target_country,
            'target_language': target_language,
            'style_guidelines': country_style,
            'cultural_sensitivities': self.cultural_sensitivities.get(target_country.upper(), {}),
            'recommended_practices': [
                f"尊重 {target_country} 的本地文化和传统",
                f"确保视觉风格符合 {target_country} 消费者的审美偏好",
                f"避免使用可能引起文化误解的元素",
                f"采用 {target_country} 当地流行的色彩和设计元素"
            ]
        }
        
        return guidelines


# 测试函数
def test_visual_localization_engine():
    """测试视觉本地化引擎"""
    
    # 初始化引擎
    engine = VisualLocalizationEngine()
    
    # 测试状态获取
    print("✅ 视觉本地化引擎初始化完成")
    
    # 测试风格适配
    base_prompt = "专业产品摄影，展示高质量产品设计"
    
    # 美国风格
    us_prompt = engine.adapt_style_for_country(base_prompt, "US")
    print(f"\\n美国风格适配:")
    print(f"  基础提示: {base_prompt}")
    print(f"  适配后: {us_prompt}")
    
    # 中国风格
    cn_prompt = engine.adapt_style_for_country(base_prompt, "CN")
    print(f"\\n中国风格适配:")
    print(f"  基础提示: {base_prompt}")
    print(f"  适配后: {cn_prompt}")
    
    # 日本风格
    jp_prompt = engine.adapt_style_for_country(base_prompt, "JP")
    print(f"\\n日本风格适配:")
    print(f"  基础提示: {base_prompt}")
    print(f"  适配后: {jp_prompt}")
    
    # 测试文化敏感性检查
    test_prompt = "使用白色背景和钟形图案，避免政治主题"
    
    for country in ["CN", "JP", "KR", "IN"]:
        warnings, suggestions = engine.check_cultural_sensitivities(test_prompt, country)
        if warnings:
            print(f"\\n{country} 文化敏感性检查:")
            for warning in warnings:
                print(f"  ⚠️ {warning}")
            for suggestion in suggestions[:2]:
                print(f"  💡 {suggestion}")
    
    # 测试文本本地化
    original_text = "High-quality denim material"
    
    for lang in ["zh", "es", "fr", "de", "ja", "ko", "ar"]:
        localized_text = engine.localize_text_content(original_text, lang)
        print(f"\\n语言 {lang} 本地化:")
        print(f"  原文: {original_text}")
        print(f"  本地化: {localized_text}")
    
    # 测试指导原则获取
    guidelines = engine.get_localization_guidelines("JP", "ja")
    print(f"\\n日本本地化指导原则:")
    print(f"  风格描述: {guidelines['style_guidelines']['description']}")
    print(f"  推荐色彩: {guidelines['style_guidelines']['preferred_colors']}")
    
    print(f"\\n✅ 视觉本地化引擎测试完成")


if __name__ == "__main__":
    test_visual_localization_engine()