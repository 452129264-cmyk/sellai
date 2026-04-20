#!/usr/bin/env python3
"""
Banana电商集成命令行界面
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Optional

# 添加父目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from banana_ecommerce_integration import (
    EcommerceIntegrationManager,
    EcommerceProduct,
    ProductStatus,
    ShopifyAdapter,
    DianfuAdapter
)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EcommerceCLI:
    """电商集成命令行界面"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化CLI
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or "config/shopify_api.yaml"
        self.manager: Optional[EcommerceIntegrationManager] = None
    
    def init_manager(self) -> bool:
        """初始化集成管理器"""
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"配置文件不存在: {self.config_path}")
                logger.info("请先创建配置文件，或使用 'init-config' 命令生成模板")
                return False
            
            self.manager = EcommerceIntegrationManager(self.config_path)
            
            # 显示初始化状态
            stats = self.manager.get_statistics()
            logger.info(f"集成管理器初始化成功")
            logger.info(f"可用平台: {stats['platforms_available']}")
            logger.info(f"活动平台: {stats['active_platform']}")
            
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {str(e)}")
            return False
    
    def command_create(self, args) -> bool:
        """创建产品命令"""
        if not self.init_manager():
            return False
        
        try:
            # 解析参数
            title = args.title
            description = args.description
            prompt = args.prompt
            product_type = args.type
            vendor = args.vendor
            tags = args.tags.split(",") if args.tags else []
            collections = args.collections.split(",") if args.collections else []
            auto_publish = args.publish
            
            logger.info(f"创建产品: {title}")
            
            # 创建产品
            success, error, product = self.manager.generate_and_publish_product(
                title=title,
                description=description,
                generation_prompt=prompt,
                product_type=product_type,
                vendor=vendor,
                tags=tags,
                collections=collections,
                auto_publish=auto_publish
            )
            
            if success:
                logger.info(f"✅ 产品创建成功!")
                logger.info(f"   产品ID: {product.product_id}")
                logger.info(f"   产品标题: {product.title}")
                logger.info(f"   产品状态: {product.status.value}")
                logger.info(f"   图片数量: {len(product.images)}")
                
                # 保存产品信息到文件
                output_file = f"product_{product.product_id}.json"
                with open(output_file, 'w') as f:
                    json.dump(product.to_dict(), f, indent=2)
                
                logger.info(f"   产品数据已保存到: {output_file}")
                
                return True
            else:
                logger.error(f"❌ 产品创建失败: {error}")
                return False
                
        except Exception as e:
            logger.error(f"命令执行异常: {str(e)}")
            return False
    
    def command_batch(self, args) -> bool:
        """批量创建命令"""
        if not self.init_manager():
            return False
        
        try:
            # 读取产品列表文件
            input_file = args.input_file
            
            if not os.path.exists(input_file):
                logger.error(f"输入文件不存在: {input_file}")
                return False
            
            with open(input_file, 'r') as f:
                if input_file.endswith('.json'):
                    product_list = json.load(f)
                else:
                    # 尝试其他格式
                    import yaml
                    product_list = yaml.safe_load(f)
            
            if not isinstance(product_list, list):
                logger.error(f"输入文件应为列表格式")
                return False
            
            logger.info(f"批量处理 {len(product_list)} 个产品...")
            
            # 批量处理
            success_count, failed_count, details = self.manager.batch_generate_products(
                product_list=product_list,
                platform_name=args.platform,
                concurrent=args.concurrent
            )
            
            # 输出结果
            logger.info(f"批量处理完成:")
            logger.info(f"  成功: {success_count}")
            logger.info(f"  失败: {failed_count}")
            
            # 保存详细结果
            if details:
                result_file = f"batch_result_{int(time.time())}.json"
                with open(result_file, 'w') as f:
                    json.dump({
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "details": details
                    }, f, indent=2)
                
                logger.info(f"  详细结果已保存到: {result_file}")
            
            # 输出失败详情
            for detail in details:
                if not detail["success"]:
                    logger.warning(f"  ❌ {detail['title']}: {detail['error']}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"命令执行异常: {str(e)}")
            return False
    
    def command_sync(self, args) -> bool:
        """同步产品命令"""
        if not self.init_manager():
            return False
        
        try:
            limit = args.limit
            platform = args.platform
            
            logger.info(f"同步 {platform} 平台产品，限制: {limit} 个...")
            
            synced_count, products = self.manager.sync_existing_products(
                limit=limit,
                platform_name=platform
            )
            
            logger.info(f"同步完成: {synced_count} 个产品")
            
            if products:
                # 保存同步结果
                sync_file = f"sync_{platform}_{int(time.time())}.json"
                
                products_data = [p.to_dict() for p in products]
                with open(sync_file, 'w') as f:
                    json.dump({
                        "count": synced_count,
                        "products": products_data
                    }, f, indent=2)
                
                logger.info(f"同步数据已保存到: {sync_file}")
                
                # 显示部分产品
                logger.info("同步的产品列表（前5个）:")
                for idx, product in enumerate(products[:5]):
                    logger.info(f"  {idx+1}. {product.title} (ID: {product.product_id})")
            
            return synced_count > 0
            
        except Exception as e:
            logger.error(f"命令执行异常: {str(e)}")
            return False
    
    def command_stats(self, args) -> bool:
        """统计信息命令"""
        if not self.init_manager():
            return False
        
        try:
            stats = self.manager.get_statistics()
            
            logger.info("集成管理器统计信息:")
            logger.info(f"  已创建产品: {stats['products_created']}")
            logger.info(f"  已生成图片: {stats['images_generated']}")
            logger.info(f"  错误数量: {stats['errors']}")
            logger.info(f"  最后操作时间: {stats['last_operation_time']}")
            logger.info(f"  可用平台: {stats['platforms_available']}")
            logger.info(f"  活动平台: {stats['active_platform']}")
            logger.info(f"  Banana可用: {stats['banana_available']}")
            logger.info(f"  素材管道可用: {stats['asset_pipeline_available']}")
            
            return True
            
        except Exception as e:
            logger.error(f"命令执行异常: {str(e)}")
            return False
    
    def command_init_config(self, args) -> bool:
        """初始化配置文件命令"""
        try:
            output_path = args.output_file or self.config_path
            
            # 创建目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 导出配置模板
            from banana_ecommerce_integration.utils.config_loader import create_default_config, save_config
            
            config = create_default_config()
            success = save_config(config, output_path)
            
            if success:
                logger.info(f"✅ 配置文件模板已生成: {output_path}")
                logger.info("请修改配置文件中的Shopify店铺信息和API密钥")
                return True
            else:
                logger.error(f"❌ 配置文件生成失败")
                return False
                
        except Exception as e:
            logger.error(f"命令执行异常: {str(e)}")
            return False
    
    def command_test(self, args) -> bool:
        """测试连接命令"""
        if not self.init_manager():
            return False
        
        try:
            platform = args.platform
            
            if platform not in self.manager.platforms:
                logger.error(f"平台不存在: {platform}")
                return False
            
            adapter = self.manager.platforms[platform]
            success, error = adapter.test_connection()
            
            if success:
                logger.info(f"✅ {platform} 连接测试成功")
                return True
            else:
                logger.error(f"❌ {platform} 连接测试失败: {error}")
                return False
                
        except Exception as e:
            logger.error(f"命令执行异常: {str(e)}")
            return False


def main():
    """主函数"""
    import time
    
    parser = argparse.ArgumentParser(
        description="Banana生图内核与电商平台集成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s create --title "AI设计产品" --description "产品描述..."
  %(prog)s batch --input-file products.json
  %(prog)s sync --platform shopify --limit 50
  %(prog)s init-config --output-file config/shopify_api.yaml
        """
    )
    
    # 全局参数
    parser.add_argument(
        "--config",
        default="config/shopify_api.yaml",
        help="配置文件路径 (默认: config/shopify_api.yaml)"
    )
    
    # 子命令
    subparsers = parser.add_subparsers(
        title="可用命令",
        dest="command",
        help="要执行的操作"
    )
    
    # create 命令
    create_parser = subparsers.add_parser(
        "create",
        help="创建单个产品"
    )
    create_parser.add_argument(
        "--title",
        required=True,
        help="产品标题"
    )
    create_parser.add_argument(
        "--description",
        required=True,
        help="产品描述"
    )
    create_parser.add_argument(
        "--prompt",
        help="图片生成提示词 (可选)"
    )
    create_parser.add_argument(
        "--type",
        help="产品类型 (可选)"
    )
    create_parser.add_argument(
        "--vendor",
        help="供应商 (可选)"
    )
    create_parser.add_argument(
        "--tags",
        help="标签，逗号分隔 (可选)"
    )
    create_parser.add_argument(
        "--collections",
        help="集合，逗号分隔 (可选)"
    )
    create_parser.add_argument(
        "--publish",
        action="store_true",
        help="自动发布产品"
    )
    
    # batch 命令
    batch_parser = subparsers.add_parser(
        "batch",
        help="批量创建产品"
    )
    batch_parser.add_argument(
        "--input-file",
        required=True,
        help="产品列表文件 (JSON或YAML格式)"
    )
    batch_parser.add_argument(
        "--platform",
        default="shopify",
        choices=["shopify", "dianfu"],
        help="目标平台 (默认: shopify)"
    )
    batch_parser.add_argument(
        "--concurrent",
        type=int,
        default=3,
        help="并发处理数量 (默认: 3)"
    )
    
    # sync 命令
    sync_parser = subparsers.add_parser(
        "sync",
        help="同步现有产品"
    )
    sync_parser.add_argument(
        "--platform",
        default="shopify",
        choices=["shopify", "dianfu"],
        help="目标平台 (默认: shopify)"
    )
    sync_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="同步数量限制 (默认: 100)"
    )
    
    # stats 命令
    stats_parser = subparsers.add_parser(
        "stats",
        help="查看统计信息"
    )
    
    # init-config 命令
    init_parser = subparsers.add_parser(
        "init-config",
        help="初始化配置文件"
    )
    init_parser.add_argument(
        "--output-file",
        help="输出文件路径 (可选)"
    )
    
    # test 命令
    test_parser = subparsers.add_parser(
        "test",
        help="测试平台连接"
    )
    test_parser.add_argument(
        "--platform",
        default="shopify",
        choices=["shopify", "dianfu"],
        help="目标平台 (默认: shopify)"
    )
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 创建CLI实例
    cli = EcommerceCLI(args.config)
    
    # 执行命令
    command_handlers = {
        "create": cli.command_create,
        "batch": cli.command_batch,
        "sync": cli.command_sync,
        "stats": cli.command_stats,
        "init-config": cli.command_init_config,
        "test": cli.command_test
    }
    
    handler = command_handlers.get(args.command)
    if not handler:
        logger.error(f"未知命令: {args.command}")
        return 1
    
    success = handler(args)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())