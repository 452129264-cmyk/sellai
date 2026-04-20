"""
短视频引流军团 - AI视频生成模板库
针对黑人模特牛仔穿搭场景，适配美区审美的视频生成提示词模板
支持至少5种不同场景变体，适用于AI视频生成工具
"""

# 基础配置
BASE_CONFIG = {
    "subject": "African American model wearing denim jacket",
    "style": "high fashion, professional photography, cinematic lighting",
    "aspect_ratio": "9:16",  # 竖屏视频适合短视频平台
    "duration": "15-30 seconds",
    "framerate": 30,
    "resolution": "1080x1920",
    "background_music": "upbeat urban hip-hop instrumental",
    "brand_elements": ["Brand logo watermark", "Shopify store URL overlay"]
}

# 5种不同场景的视频生成模板
SCENE_TEMPLATES = {
    # 1. 室内棚拍专业版
    "indoor_studio": {
        "name": "室内棚拍专业版",
        "description": "专业摄影棚环境，强调服装细节和质感",
        "prompt_template": """
Cinematic fashion video of an African American model wearing a 750g vintage denim jacket in a professional photography studio.
Model: Late 20s, confident pose, natural expression, professional runway model physique.
Lighting: Softbox lighting, rim light highlighting jacket texture, dramatic shadows.
Camera movement: Slow dolly zoom, focus on jacket details (buttons, stitching, fabric texture).
Scene: Minimalist white backdrop, studio lighting equipment visible in bokeh.
Styling: Jacket worn over plain white t-shirt, slim-fit black jeans, leather boots.
Action: Model slowly turns 360 degrees, shows front and back of jacket, touches fabric.
Atmosphere: High-end fashion campaign, premium brand aesthetic.
Technical: 4K resolution, cinematic color grading, shallow depth of field.
""",
        "variations": [
            "Close-up shots focusing on denim texture",
            "Slow-motion fabric movement",
            "Multiple model poses showcasing different angles"
        ]
    },
    
    # 2. 街头实拍潮流版
    "street_urban": {
        "name": "街头实拍潮流版",
        "description": "城市街头环境，展现日常穿搭场景和潮流感",
        "prompt_template": """
Urban street fashion video of an African American model wearing vintage denim jacket in downtown city environment.
Location: Brooklyn streets, graffiti walls, urban architecture, golden hour sunlight.
Model: Casual street style, confident walk, authentic urban vibe.
Action: Model walking down sidewalk, leaning against brick wall, interacting with environment.
Camera: Handheld documentary style, dynamic movement, natural transitions.
Styling: Denim jacket over hoodie, distressed jeans, high-top sneakers, baseball cap.
Atmosphere: Authentic street culture, urban lifestyle, relatable fashion.
Details: Wind blowing through jacket, natural city sounds in background.
Time: Sunset golden hour lighting, long shadows, warm tones.
""",
        "variations": [
            "Daytime bright lighting version",
            "Nighttime city lights version",
            "Rainy street reflective surface version"
        ]
    },
    
    # 3. 生活场景自然版
    "lifestyle_casual": {
        "name": "生活场景自然版",
        "description": "日常生活场景，展现服装舒适性和实用性",
        "prompt_template": """
Lifestyle video showing African American model wearing vintage denim jacket in everyday situations.
Scenes: Coffee shop, park bench, casual meetup with friends, relaxed atmosphere.
Model: Approachable, friendly smile, natural body language, relatable persona.
Activities: Drinking coffee, laughing with friends, checking phone, enjoying outdoors.
Camera: Natural documentary style, soft transitions, authentic moments.
Styling: Jacket worn open over plain t-shirt, comfortable jeans, casual sneakers.
Lighting: Natural daylight, soft shadows, warm inviting atmosphere.
Sound: Ambient sounds, light conversation, subtle background music.
Focus: Comfort and practicality of jacket for daily wear.
""",
        "variations": [
            "At-home cozy version",
            "Weekend brunch with friends",
            "Park picnic afternoon"
        ]
    },
    
    # 4. 运动动态活力版
    "active_dynamic": {
        "name": "运动动态活力版",
        "description": "运动场景展示服装灵活性和动态美感",
        "prompt_template": """
Dynamic action video of African American model in vintage denim jacket during active movement.
Actions: Jumping, spinning, dancing, showing jacket flexibility and freedom of movement.
Location: Outdoor basketball court, skatepark, urban sports facility.
Model: Athletic build, energetic movements, showing jacket doesn't restrict motion.
Camera: Dynamic tracking shots, slow-motion sequences, multi-angle coverage.
Styling: Jacket with athletic wear underneath, performance fabrics, sport shoes.
Lighting: Bright midday sun, high contrast, vibrant colors.
Atmosphere: Youthful energy, active lifestyle, modern athletic fashion.
Details: Jacket movement in slow motion, fabric flowing with body motion.
""",
        "variations": [
            "Dance choreography showcase",
            "Skateboarding action sequence",
            "Basketball court movement"
        ]
    },
    
    # 5. 艺术创意概念版
    "artistic_conceptual": {
        "name": "艺术创意概念版",
        "description": "艺术化表达，强调创意视觉和情感连接",
        "prompt_template": """
Artistic fashion film featuring African American model in vintage denim jacket with conceptual visual storytelling.
Concept: "Urban poetry" - jacket as symbol of personal identity and resilience.
Visual style: Cinematic symmetry, color theory (denim blue palette), symbolic framing.
Model: Expressive face, emotional depth, meaningful eye contact with camera.
Camera: Cinematic movements, creative angles, symbolic composition.
Lighting: Moody contrast, dramatic shadows, spotlight effects.
Scenes: Abstract urban environments, symbolic locations, metaphorical settings.
Styling: Jacket as central character, minimal other elements.
Atmosphere: Thought-provoking, emotionally resonant, brand philosophy expression.
Technical: Film grain texture, vintage color grading, poetic pacing.
""",
        "variations": [
            "Black and white minimalist version",
            "Surreal dream sequence",
            "Time-lapse urban transformation"
        ]
    }
}

# 产品特定模板（针对750g美式复古牛仔外套）
PRODUCT_SPECIFIC_TEMPLATES = {
    "750g_vintage_denim": {
        "product_name": "750g American Vintage Denim Jacket",
        "key_features": [
            "Heavyweight 750g premium denim",
            "Authentic vintage wash and distressing",
            "Reinforced stitching and durable construction",
            "Classic trucker jacket silhouette",
            "Brushed cotton lining for comfort"
        ],
        "selling_points": [
            "Perfect for layering in any season",
            "Ages beautifully with wear",
            "Unisex fit for versatile styling",
            "Statement piece for any wardrobe"
        ],
        "scene_integration": {
            "indoor_studio": "Showcase weight and texture details",
            "street_urban": "Demonstrate practical daily wear",
            "lifestyle_casual": "Highlight comfort and versatility",
            "active_dynamic": "Emphasize durability and flexibility",
            "artistic_conceptual": "Express brand heritage and quality"
        }
    }
}

# 平台优化模板
PLATFORM_OPTIMIZATIONS = {
    "tiktok": {
        "format_guidelines": {
            "duration": "15-30 seconds ideal",
            "hook": "First 3 seconds must grab attention",
            "text_overlay": "Large bold captions for silent viewing",
            "trends": "Incorporate trending sounds and hashtags",
            "cta": "Clear call-to-action in video and description"
        },
        "hashtag_suggestions": [
            "#denimjacket", "#vintagefashion", "#streetwear", "#ootd",
            "#fashionhaul", "#tryonhaul", "#fashiontiktok", "#styleinspo"
        ]
    },
    "youtube_shorts": {
        "format_guidelines": {
            "duration": "15-60 seconds",
            "hook": "Immediate value proposition",
            "branding": "Consistent intro/outro branding",
            "description": "Detailed product links and information",
            "seo": "Keyword-rich titles and descriptions"
        },
        "title_templates": [
            "This 750g Denim Jacket is PERFECT for Fall 🍂 | Try-On & Review",
            "Why This Vintage Denim Jacket Sold Out in 24 Hours",
            "The Ultimate Denim Jacket for Streetwear Lovers"
        ]
    },
    "instagram_reels": {
        "format_guidelines": {
            "duration": "15-30 seconds",
            "aesthetics": "Clean, curated visual style",
            "music": "Trending audio tracks",
            "engagement": "Interactive elements (polls, questions)",
            "shopping": "Direct product tagging integration"
        },
        "caption_templates": [
            "Meet your new favorite jacket 🤎 This 750g vintage denim piece is everything you need for effortless style. Link in bio!",
            "Denim that tells a story ✨ Each detail of this jacket speaks to quality craftsmanship and timeless design."
        ]
    },
    "xiaohongshu": {
        "format_guidelines": {
            "duration": "30-60 seconds",
            "format": "Detailed review with text overlays",
            "authenticity": "Genuine user experience sharing",
            "details": "Close-up shots of fabric, stitching, features",
            "community": "Engage with fashion community trends"
        },
        "content_angles": [
            "Detailed unboxing and first impressions",
            "Multiple outfit styling options",
            "Quality and durability demonstration",
            "Price-to-value analysis"
        ]
    }
}

# 批量生成配置
BATCH_GENERATION_CONFIGS = {
    "full_campaign": {
        "description": "完整营销战役视频集，覆盖所有场景和平台",
        "scene_distribution": {
            "indoor_studio": 2,  # 2个版本
            "street_urban": 3,   # 3个版本
            "lifestyle_casual": 2,
            "active_dynamic": 1,
            "artistic_conceptual": 1
        },
        "platform_optimizations": ["tiktok", "youtube_shorts", "instagram_reels", "xiaohongshu"],
        "total_videos": 9,
        "estimated_time": "3-4 hours for full batch generation"
    },
    "quick_launch": {
        "description": "快速启动精简版，核心场景覆盖",
        "scene_distribution": {
            "indoor_studio": 1,
            "street_urban": 2,
            "lifestyle_casual": 1
        },
        "platform_optimizations": ["tiktok", "instagram_reels"],
        "total_videos": 4,
        "estimated_time": "1-2 hours for batch generation"
    }
}

# 实用函数
def get_template(scene_key, product_name="750g_vintage_denim"):
    """
    获取指定场景和产品的视频生成模板
    
    Args:
        scene_key: 场景键名，如 "indoor_studio"
        product_name: 产品键名，默认为 "750g_vintage_denim"
    
    Returns:
        包含完整提示词和配置的字典
    """
    if scene_key not in SCENE_TEMPLATES:
        raise ValueError(f"未知场景: {scene_key}. 可用场景: {list(SCENE_TEMPLATES.keys())}")
    
    template = SCENE_TEMPLATES[scene_key].copy()
    product_info = PRODUCT_SPECIFIC_TEMPLATES.get(product_name, {})
    
    # 整合产品信息到提示词
    if product_info:
        features = " | ".join(product_info.get("key_features", []))
        prompt = template["prompt_template"]
        enhanced_prompt = f"{prompt}\n\nProduct Features: {features}"
        template["enhanced_prompt"] = enhanced_prompt
    
    return template

def get_platform_optimization(platform, scene_key):
    """
    获取指定平台和场景的优化配置
    
    Args:
        platform: 平台名称，如 "tiktok"
        scene_key: 场景键名
    
    Returns:
        平台优化配置字典
    """
    platform_config = PLATFORM_OPTIMIZATIONS.get(platform, {})
    template = get_template(scene_key)
    
    return {
        "platform": platform,
        "scene": template["name"],
        "guidelines": platform_config.get("format_guidelines", {}),
        "recommendations": {
            "duration": platform_config.get("format_guidelines", {}).get("duration", "15-30s"),
            "aspect_ratio": BASE_CONFIG["aspect_ratio"],
            "cta_suggestions": platform_config.get("cta_suggestions", [])
        }
    }

def generate_batch_config(campaign_type="quick_launch"):
    """
    生成批量视频生成配置
    
    Args:
        campaign_type: 战役类型，"full_campaign" 或 "quick_launch"
    
    Returns:
        批量生成配置
    """
    config = BATCH_GENERATION_CONFIGS.get(campaign_type, BATCH_GENERATION_CONFIGS["quick_launch"])
    
    # 生成具体视频列表
    video_list = []
    for scene_key, count in config["scene_distribution"].items():
        for i in range(count):
            video_id = f"{scene_key}_{i+1}"
            template = get_template(scene_key)
            
            video_list.append({
                "video_id": video_id,
                "scene": scene_key,
                "scene_name": template["name"],
                "platforms": config["platform_optimizations"],
                "estimated_duration": BASE_CONFIG["duration"],
                "priority": "high" if scene_key in ["street_urban", "indoor_studio"] else "medium"
            })
    
    config["video_list"] = video_list
    return config

def format_prompt_for_ai(template, platform="tiktok"):
    """
    为AI视频生成工具格式化提示词
    
    Args:
        template: 模板字典
        platform: 目标平台
    
    Returns:
        格式化后的提示词字符串
    """
    base_prompt = template.get("enhanced_prompt", template["prompt_template"])
    
    # 添加平台特定指导
    platform_config = PLATFORM_OPTIMIZATIONS.get(platform, {})
    guidelines = platform_config.get("format_guidelines", {})
    
    formatted = f"""{base_prompt}

Platform Optimization for {platform.upper()}:
- Duration: {guidelines.get('duration', '15-30 seconds')}
- Aspect Ratio: {BASE_CONFIG['aspect_ratio']}
- Style: {BASE_CONFIG['style']}
- Camera Movement: Dynamic and engaging
- Lighting: Professional cinematic quality
- Background Music: {BASE_CONFIG['background_music']}
- Brand Elements: {', '.join(BASE_CONFIG['brand_elements'])}
"""
    
    return formatted.strip()

# 示例使用
if __name__ == "__main__":
    print("短视频引流军团 - AI视频生成模板库")
    print("=" * 50)
    
    # 显示可用模板
    print(f"可用场景模板: {len(SCENE_TEMPLATES)} 种")
    for key, template in SCENE_TEMPLATES.items():
        print(f"  - {key}: {template['name']} - {template['description']}")
    
    print("\n产品特定模板:")
    for product_key, product_info in PRODUCT_SPECIFIC_TEMPLATES.items():
        print(f"  - {product_key}: {product_info['product_name']}")
    
    # 示例：获取街头场景模板
    print("\n示例 - 街头实拍潮流版模板:")
    street_template = get_template("street_urban")
    print(f"场景: {street_template['name']}")
    print(f"描述: {street_template['description']}")
    print(f"变体: {', '.join(street_template['variations'])}")
    
    # 示例：生成批量配置
    print("\n示例 - 快速启动批量配置:")
    batch_config = generate_batch_config("quick_launch")
    print(f"战役类型: {batch_config['description']}")
    print(f"视频总数: {batch_config['total_videos']}")
    print(f"场景分布: {batch_config['scene_distribution']}")
    
    # 示例：平台优化提示词
    print("\n示例 - TikTok优化提示词:")
    tiktok_prompt = format_prompt_for_ai(street_template, "tiktok")
    print(tiktok_prompt[:200] + "..." if len(tiktok_prompt) > 200 else tiktok_prompt)