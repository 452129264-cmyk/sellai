#!/usr/bin/env python3
"""
Shopify集成示例
展示如何使用Banana生图内核与Shopify平台集成
"""

import os
import sys
import json
import logging
from pathlib import Path

# 添加父目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from banana_ecommerce_integration import (
    EcommerceIntegrationManager,
    EcommerceProduct,
    ProductStatus,
    ProductImage,
    ProductVariant
)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_single_product_creation():
    """示例：创建单个产品"""
    print("=== 示例1: 创建单个产品 ===\n")
    
    # 1. 初始化集成管理器
    config_path = "config/shopify_api.yaml"
    manager = EcommerceIntegrationManager(config_path)
    
    # 2. 检查连接
    stats = manager.get_statistics()
    print(f"初始化状态: {stats}\n")
    
    # 3. 创建产品
    title = "AI生成美式复古牛仔外套"
    description = """
高端美式复古风格牛仔外套，采用AI生成设计，融合经典与现代元素。
特点：
- 100%纯棉牛仔面料
- 复古水洗工艺
- 经典纽扣设计
- 多个实用口袋
- 舒适合身剪裁

适合日常穿搭、休闲出游等多种场合，展现独特个人风格。
"""
    
    print(f"生成产品: {title}")
    
    success, error, product = manager.generate_and_publish_product(
        title=title,
        description=description,
        generation_prompt="Vintage American denim jacket, distressed wash, classic button front, professional fashion photography, studio lighting, detailed texture, 4K resolution",
        product_type="牛仔外套",
        vendor="Banana生图AI",
        tags=["AI生成", "美式复古", "牛仔外套", "时尚设计"],
        collections=["AI生成设计", "牛仔系列"],
        auto_publish=True
    )
    
    if success:
        print(f"✅ 产品创建成功!")
        print(f"   产品ID: {product.product_id}")
        print(f"   产品标题: {product.title}")
        print(f"   产品状态: {product.status.value}")
        print(f"   图片数量: {len(product.images)}")
        
        if product.images:
            main_image = product.get_main_image()
            if main_image:
                print(f"   主图URL: {main_image.url}")
    else:
        print(f"❌ 产品创建失败: {error}")
    
    return success, product


def example_batch_product_creation():
    """示例：批量创建产品"""
    print("\n=== 示例2: 批量创建产品 ===\n")
    
    # 1. 初始化集成管理器
    config_path = "config/shopify_api.yaml"
    manager = EcommerceIntegrationManager(config_path)
    
    # 2. 准备产品列表
    product_list = [
        {
            "title": "AI设计复古水洗牛仔裤",
            "description": "经典复古水洗牛仔裤，AI优化剪裁设计，舒适耐穿，展现复古潮流风格。",
            "product_type": "牛仔裤",
            "tags": ["AI设计", "复古风", "水洗牛仔", "舒适"],
            "generation_prompt": "Vintage washed denim jeans, distressed details, classic fit, professional fashion photography, studio lighting, detailed texture"
        },
        {
            "title": "AI生成潮流连帽卫衣",
            "description": "时尚潮流连帽卫衣，AI生成印花设计，柔软舒适面料，适合日常休闲穿搭。",
            "product_type": "卫衣",
            "tags": ["潮流", "连帽", "AI印花", "舒适"],
            "generation_prompt": "Trendy hoodie with AI-generated pattern, modern streetwear style, professional photography, studio lighting, detailed fabric texture"
        },
        {
            "title": "AI设计简约T恤",
            "description": "简约设计纯棉T恤，AI优化版型与印花，透气舒适，百搭基础款。",
            "product_type": "T恤",
            "tags": ["简约", "纯棉", "基础款", "百搭"],
            "generation_prompt": "Minimalist cotton t-shirt with AI-designed print, basic wardrobe essential, professional product photography, studio lighting"
        }
    ]
    
    print(f"批量处理 {len(product_list)} 个产品...\n")
    
    # 3. 批量处理
    success_count, failed_count, details = manager.batch_generate_products(
        product_list=product_list,
        platform_name="shopify",
        concurrent=2
    )
    
    # 4. 输出结果
    print(f"批量处理完成:")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    
    for detail in details:
        status = "✅" if detail["success"] else "❌"
        print(f"  {status} {detail['title']}: {detail['error'] or '成功'}")
    
    return success_count > 0


def example_sync_existing_products():
    """示例：同步现有产品"""
    print("\n=== 示例3: 同步现有产品 ===\n")
    
    # 1. 初始化集成管理器
    config_path = "config/shopify_api.yaml"
    manager = EcommerceIntegrationManager(config_path)
    
    # 2. 同步产品
    print("同步Shopify店铺现有产品...")
    synced_count, products = manager.sync_existing_products(
        limit=10,
        platform_name="shopify"
    )
    
    print(f"同步完成: {synced_count} 个产品")
    
    if products:
        print("\n同步的产品列表:")
        for idx, product in enumerate(products[:5]):  # 只显示前5个
            print(f"  {idx+1}. {product.title} (ID: {product.product_id})")
    
    return synced_count > 0


def example_custom_product_creation():
    """示例：自定义产品创建"""
    print("\n=== 示例4: 自定义产品创建 ===\n")
    
    # 1. 初始化集成管理器
    config_path = "config/shopify_api.yaml"
    manager = EcommerceIntegrationManager(config_path)
    
    # 2. 手动创建产品对象
    product = EcommerceProduct(
        product_id="custom_prod_001",
        title="自定义AI设计产品",
        description="这是一个完全自定义的产品示例，展示如何手动构建产品对象。",
        product_type="自定义类型",
        vendor="自定义供应商",
        tags=["自定义", "示例", "测试"],
        status=ProductStatus.DRAFT
    )
    
    # 3. 添加图片（模拟）
    image = ProductImage(
        image_id="img_custom_001",
        url="https://example.com/image.jpg",
        alt_text="自定义产品图片",
        position=0
    )
    product.add_image(image)
    
    # 4. 添加变体
    variant = ProductVariant(
        variant_id="var_custom_001",
        sku="CUSTOM-001",
        price=49.99,
        inventory_quantity=50,
        option1="蓝色"
    )
    product.add_variant(variant)
    
    print(f"自定义产品创建完成:")
    print(f"  标题: {product.title}")
    print(f"  描述: {product.description[:50]}...")
    print(f"  图片数量: {len(product.images)}")
    print(f"  变体数量: {len(product.variants)}")
    
    return True


def example_generate_from_existing_image():
    """示例：从已有图片创建产品"""
    print("\n=== 示例5: 从已有图片创建产品 ===\n")
    
    # 1. 初始化集成管理器
    config_path = "config/shopify_api.yaml"
    manager = EcommerceIntegrationManager(config_path)
    
    # 2. 模拟已有图片和元数据
    image_path = "/tmp/banana_generated_image.png"
    image_metadata = {
        "prompt": "Vintage denim jacket with artistic design, professional photography",
        "generation_time": "2024-01-15T10:30:00",
        "resolution": "2048x2048",
        "model_id": "banana_standard",
        "face_consistency_score": 0.98,
        "texture_accuracy_score": 0.96,
        "product_type": "牛仔外套",
        "vendor": "Banana生图AI",
        "tags": ["艺术设计", "牛仔", "复古"]
    }
    
    print(f"从已有图片创建产品...")
    print(f"  图片路径: {image_path}")
    print(f"  生成提示: {image_metadata['prompt']}")
    
    # 3. 创建产品
    success, error, product = manager.generate_product_from_banana_image(
        image_path=image_path,
        image_metadata=image_metadata,
        title="艺术设计复古牛仔外套",
        description="独特艺术设计的复古风格牛仔外套，展现个性与品味。"
    )
    
    if success:
        print(f"✅ 产品创建成功!")
        print(f"  产品ID: {product.product_id}")
    else:
        print(f"❌ 产品创建失败: {error}")
    
    return success


def main():
    """主函数：运行所有示例"""
    print("Banana生图内核与Shopify电商平台集成示例")
    print("=" * 60 + "\n")
    
    # 检查配置文件
    config_path = "config/shopify_api.yaml"
    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        print("请先创建配置文件或使用模板")
        return False
    
    results = []
    
    try:
        # 运行示例1：单个产品创建
        success, product = example_single_product_creation()
        results.append(("单个产品创建", success))
        
        # 运行示例2：批量产品创建
        success = example_batch_product_creation()
        results.append(("批量产品创建", success))
        
        # 运行示例3：同步现有产品
        success = example_sync_existing_products()
        results.append(("同步现有产品", success))
        
        # 运行示例4：自定义产品创建
        success = example_custom_product_creation()
        results.append(("自定义产品创建", success))
        
        # 运行示例5：从已有图片创建产品
        success = example_generate_from_existing_image()
        results.append(("从已有图片创建产品", success))
        
    except Exception as e:
        logger.error(f"示例运行异常: {str(e)}")
        results.append(("总体运行", False))
    
    # 输出总结
    print("\n" + "=" * 60)
    print("示例运行总结:")
    
    all_success = True
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}: {'成功' if success else '失败'}")
        if not success:
            all_success = False
    
    print(f"\n总体结果: {'所有示例均成功' if all_success else '部分示例失败'}")
    
    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)