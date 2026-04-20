#!/usr/bin/env python3
"""
Banana生图内核全局素材库流水线主入口

提供命令行接口，支持启动、停止、状态查询、任务提交等功能。
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# 添加当前目录到路径，确保可以导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.banana_asset_pipeline.config import PipelineConfig, DEFAULT_CONFIG
from src.banana_asset_pipeline.pipeline import AssetPipeline, AsyncAssetPipeline, process_and_sync_image
from src.banana_asset_pipeline.api_server import start_asset_pipeline_api_server

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/banana_asset_pipeline.log")
    ]
)
logger = logging.getLogger(__name__)


class AssetPipelineCLI:
    """资产流水线命令行接口"""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.pipeline = None
        self.async_pipeline = None
    
    def run(self, args: argparse.Namespace) -> int:
        """执行命令"""
        command = args.command
        
        if command == "start":
            return self.start_pipeline(args)
        elif command == "stop":
            return self.stop_pipeline(args)
        elif command == "status":
            return self.show_status(args)
        elif command == "submit":
            return self.submit_job(args)
        elif command == "batch":
            return self.submit_batch(args)
        elif command == "search":
            return self.search_images(args)
        elif command == "server":
            return self.start_server(args)
        elif command == "init":
            return self.init_system(args)
        else:
            logger.error(f"未知命令: {command}")
            return 1
    
    def start_pipeline(self, args: argparse.Namespace) -> int:
        """启动流水线"""
        try:
            # 初始化流水线
            use_async = getattr(args, 'async', False)
            
            if use_async:
                self.async_pipeline = AsyncAssetPipeline(self.config)
                
                # 异步启动
                import asyncio
                asyncio.run(self.async_pipeline.start())
                
                logger.info("异步资产流水线已启动")
            else:
                self.pipeline = AssetPipeline(self.config)
                
                # 同步启动
                success = self.pipeline.start()
                
                if success:
                    logger.info("资产流水线已启动")
                    
                    # 如果要求保持运行
                    if args.daemon:
                        logger.info("进入守护进程模式，按Ctrl+C停止")
                        try:
                            while True:
                                time.sleep(1)
                        except KeyboardInterrupt:
                            self.pipeline.stop()
                            logger.info("流水线已停止")
                else:
                    logger.error("流水线启动失败")
                    return 1
            
            return 0
            
        except Exception as e:
            logger.error(f"启动流水线失败: {str(e)}", exc_info=True)
            return 1
    
    def stop_pipeline(self, args: argparse.Namespace) -> int:
        """停止流水线"""
        try:
            use_async = getattr(args, 'async', False)
            
            if use_async and self.async_pipeline:
                import asyncio
                asyncio.run(self.async_pipeline.stop())
                logger.info("异步流水线已停止")
            elif self.pipeline:
                self.pipeline.stop()
                logger.info("流水线已停止")
            else:
                logger.warning("流水线未运行")
            
            return 0
            
        except Exception as e:
            logger.error(f"停止流水线失败: {str(e)}")
            return 1
    
    def show_status(self, args: argparse.Namespace) -> int:
        """显示流水线状态"""
        try:
            # 获取配置信息
            config_info = {
                "base_storage_dir": self.config.base_storage_dir,
                "temp_processing_dir": self.config.temp_processing_dir,
                "metadata_dir": self.config.metadata_dir,
                "max_processing_delay_ms": self.config.max_processing_delay_ms,
                "max_concurrent": self.config.max_concurrent,
                "notebook_lm_sync_enabled": self.config.notebook_lm_sync_enabled,
            }
            
            # 获取流水线状态
            pipeline_status = {}
            if self.pipeline:
                pipeline_status = self.pipeline.get_stats()
            elif self.async_pipeline:
                pipeline_status = {"status": "async_running"}
            else:
                pipeline_status = {"status": "not_started"}
            
            # 格式化输出
            if args.json:
                output = {
                    "timestamp": datetime.now().isoformat(),
                    "config": config_info,
                    "pipeline": pipeline_status,
                }
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                print("\n" + "="*60)
                print("Banana生图内核全局素材库流水线状态")
                print("="*60)
                
                print("\n📦 配置信息:")
                for key, value in config_info.items():
                    print(f"  {key}: {value}")
                
                print("\n🚀 流水线状态:")
                for key, value in pipeline_status.items():
                    print(f"  {key}: {value}")
                
                print("\n📊 目录检查:")
                dirs_to_check = [
                    self.config.base_storage_dir,
                    self.config.temp_processing_dir,
                    self.config.metadata_dir,
                ]
                
                for dir_path in dirs_to_check:
                    exists = os.path.exists(dir_path)
                    writable = os.access(dir_path, os.W_OK) if exists else False
                    status = "✅ 存在且可写" if exists and writable else "⚠️  存在问题" if exists else "❌ 不存在"
                    print(f"  {dir_path}: {status}")
                
                print("\n" + "="*60)
            
            return 0
            
        except Exception as e:
            logger.error(f"获取状态失败: {str(e)}")
            return 1
    
    def submit_job(self, args: argparse.Namespace) -> int:
        """提交单个任务"""
        try:
            # 验证图片文件
            if not os.path.exists(args.image):
                logger.error(f"图片文件不存在: {args.image}")
                return 1
            
            # 构建生成参数
            generation_params = {
                "prompt": args.prompt,
                "negative_prompt": args.negative_prompt or "",
                "model_name": args.model_name,
                "model_version": args.model_version,
            }
            
            # 添加额外参数
            if args.extra_params:
                try:
                    extra = json.loads(args.extra_params)
                    generation_params.update(extra)
                except json.JSONDecodeError:
                    logger.error("额外参数不是有效的JSON格式")
                    return 1
            
            # 处理并同步
            start_time = time.time()
            
            success, result, metadata = process_and_sync_image(
                image_path=args.image,
                generation_params=generation_params,
                avatar_id=args.avatar,
                task_id=args.task,
                scene=args.scene,
                use_async=getattr(args, 'async', False),
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # 输出结果
            if args.json:
                output = {
                    "success": success,
                    "result": result,
                    "processing_time_ms": processing_time,
                    "metadata": metadata.to_dict() if metadata else None,
                }
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                print("\n" + "="*60)
                print("图片处理结果")
                print("="*60)
                
                print(f"📊 状态: {'✅ 成功' if success else '❌ 失败'}")
                print(f"⏱️  处理时间: {processing_time:.0f}ms")
                print(f"📝 结果信息: {result}")
                
                if metadata:
                    print(f"🆔 图片ID: {metadata.image_id}")
                    print(f"📏 尺寸: {metadata.dimensions[0]}x{metadata.dimensions[1]}")
                    print(f"🏷️  分类: {metadata.category.value}")
                    print(f"⭐ 质量等级: {metadata.quality_grade.value}")
                    
                    # 显示存储路径
                    if os.path.exists(metadata.file_path):
                        file_size_mb = metadata.file_size / (1024 * 1024)
                        print(f"💾 存储位置: {metadata.file_path} ({file_size_mb:.2f}MB)")
                
                print("="*60)
            
            return 0 if success else 1
            
        except Exception as e:
            logger.error(f"任务提交失败: {str(e)}", exc_info=True)
            return 1
    
    def submit_batch(self, args: argparse.Namespace) -> int:
        """提交批量任务"""
        try:
            # 读取批处理文件
            if not os.path.exists(args.batch_file):
                logger.error(f"批处理文件不存在: {args.batch_file}")
                return 1
            
            with open(args.batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            if not isinstance(batch_data, list):
                logger.error("批处理文件格式错误，应为任务列表")
                return 1
            
            # 验证每个任务
            valid_jobs = []
            for i, job in enumerate(batch_data):
                # 检查必需字段
                required_fields = ["image_path", "prompt", "avatar_id", "task_id", "scene"]
                missing_fields = [field for field in required_fields if field not in job]
                
                if missing_fields:
                    logger.warning(f"任务 {i} 缺少字段: {missing_fields}，已跳过")
                    continue
                
                # 检查文件存在性
                if not os.path.exists(job["image_path"]):
                    logger.warning(f"图片文件不存在: {job['image_path']}，已跳过")
                    continue
                
                valid_jobs.append(job)
            
            if not valid_jobs:
                logger.error("没有有效的任务")
                return 1
            
            logger.info(f"找到 {len(valid_jobs)} 个有效任务，开始处理...")
            
            # 使用批处理器
            from src.banana_asset_pipeline.image_processor import BatchImageProcessor
            batch_processor = BatchImageProcessor(self.config)
            
            # 处理批次
            results = batch_processor.process_batch(valid_jobs)
            
            # 输出结果
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                print("\n" + "="*60)
                print("批量处理结果汇总")
                print("="*60)
                
                print(f"📊 总体统计:")
                print(f"  总任务数: {results['total']}")
                print(f"  成功数: {results['success']}")
                print(f"  失败数: {results['failed']}")
                print(f"  总耗时: {results['processing_time_ms']:.0f}ms")
                
                if args.verbose:
                    print(f"\n📋 详细结果:")
                    for detail in results['details']:
                        status_icon = "✅" if detail.get('status') == 'success' else "❌"
                        print(f"  {status_icon} {detail.get('image_id', 'N/A')}: {detail.get('status')}")
                
                print("="*60)
            
            # 返回失败率
            failure_rate = results['failed'] / results['total'] if results['total'] > 0 else 0
            return 0 if failure_rate < 0.1 else 1  # 允许10%失败率
            
        except Exception as e:
            logger.error(f"批量处理失败: {str(e)}", exc_info=True)
            return 1
    
    def search_images(self, args: argparse.Namespace) -> int:
        """搜索图片"""
        try:
            # 需要记忆系统就绪
            from src.banana_asset_pipeline.memory_sync import MemorySyncManager
            sync_manager = MemorySyncManager(self.config)
            
            # 搜索
            filter_tags = None
            if args.tags:
                filter_tags = args.tags.split(',')
            
            results = sync_manager.search_similar_images(
                query=args.query,
                filter_tags=filter_tags,
                limit=args.limit,
            )
            
            sync_manager.cleanup()
            
            # 输出结果
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                print("\n" + "="*60)
                print(f"图片搜索结果: '{args.query}'")
                print("="*60)
                
                if not results:
                    print("🔍 未找到匹配结果")
                else:
                    print(f"找到 {len(results)} 个匹配结果:\n")
                    
                    for i, item in enumerate(results, 1):
                        print(f"{i}. [{item.get('quality_grade', 'N/A')}] {item.get('image_id')}")
                        print(f"   分身: {item.get('avatar_id')}, 场景: {item.get('scene')}")
                        print(f"   分类: {item.get('category')}, 相似度: {item.get('similarity_score', 0):.2%}")
                        
                        if args.verbose:
                            print(f"   路径: {item.get('file_path')}")
                            if item.get('tags'):
                                print(f"   标签: {', '.join(item.get('tags', [])[:5])}")
                        
                        print()
                
                print("="*60)
            
            return 0
            
        except Exception as e:
            logger.error(f"图片搜索失败: {str(e)}")
            return 1
    
    def start_server(self, args: argparse.Namespace) -> int:
        """启动API服务器"""
        try:
            logger.info(f"启动API服务器，监听 {args.host}:{args.port}")
            
            start_asset_pipeline_api_server(
                host=args.host,
                port=args.port,
                config=self.config,
            )
            
            return 0
            
        except KeyboardInterrupt:
            logger.info("API服务器已停止")
            return 0
        except Exception as e:
            logger.error(f"API服务器启动失败: {str(e)}", exc_info=True)
            return 1
    
    def init_system(self, args: argparse.Namespace) -> int:
        """初始化系统"""
        try:
            # 确保目录存在
            self.config.ensure_directories()
            
            # 创建配置目录
            config_dir = os.path.dirname(self.config.metadata_dir)
            os.makedirs(config_dir, exist_ok=True)
            
            # 创建日志目录
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            
            print("\n" + "="*60)
            print("系统初始化完成")
            print("="*60)
            
            print(f"✅ 创建目录:")
            print(f"  全局素材库: {self.config.base_storage_dir}")
            print(f"  临时处理目录: {self.config.temp_processing_dir}")
            print(f"  元数据目录: {self.config.metadata_dir}")
            print(f"  日志目录: {log_dir}")
            
            print(f"\n📋 配置信息:")
            print(f"  最大处理延迟: {self.config.max_processing_delay_ms}ms")
            print(f"  最大并发数: {self.config.max_concurrent}")
            print(f"  记忆同步启用: {self.config.notebook_lm_sync_enabled}")
            
            print(f"\n🚀 使用命令:")
            print(f"  启动流水线: python {__file__} start")
            print(f"  提交任务: python {__file__} submit --image <路径> --prompt <提示词>")
            print(f"  查看状态: python {__file__} status")
            
            print("="*60)
            
            return 0
            
        except Exception as e:
            logger.error(f"系统初始化失败: {str(e)}")
            return 1


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Banana生图内核全局素材库流水线管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s init                     # 初始化系统
  %(prog)s start --daemon           # 启动守护进程
  %(prog)s status                   # 查看状态
  %(prog)s submit --image test.png --prompt "测试" --avatar avatar_001
  %(prog)s search --query "产品图"  # 搜索图片
  %(prog)s server --port 8080       # 启动API服务器
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # init命令
    init_parser = subparsers.add_parser('init', help='初始化系统')
    
    # start命令
    start_parser = subparsers.add_parser('start', help='启动流水线')
    start_parser.add_argument('--daemon', action='store_true', help='守护进程模式')
    start_parser.add_argument('--async', action='store_true', dest='use_async', help='使用异步模式')
    
    # stop命令
    stop_parser = subparsers.add_parser('stop', help='停止流水线')
    stop_parser.add_argument('--async', action='store_true', dest='use_async', help='停止异步流水线')
    
    # status命令
    status_parser = subparsers.add_parser('status', help='查看流水线状态')
    status_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    # submit命令
    submit_parser = subparsers.add_parser('submit', help='提交单个图片处理任务')
    submit_parser.add_argument('--image', required=True, help='图片文件路径')
    submit_parser.add_argument('--prompt', required=True, help='生成提示词')
    submit_parser.add_argument('--negative-prompt', help='负向提示词')
    submit_parser.add_argument('--model-name', default='banana_model', help='模型名称')
    submit_parser.add_argument('--model-version', default='2.1', help='模型版本')
    submit_parser.add_argument('--extra-params', help='额外生成参数（JSON格式）')
    submit_parser.add_argument('--avatar', required=True, help='生成分身ID')
    submit_parser.add_argument('--task', required=True, help='关联任务ID')
    submit_parser.add_argument('--scene', required=True, help='使用场景')
    submit_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    submit_parser.add_argument('--async', action='store_true', dest='use_async', help='异步处理')
    
    # batch命令
    batch_parser = subparsers.add_parser('batch', help='批量提交图片处理任务')
    batch_parser.add_argument('--batch-file', required=True, help='批处理任务文件（JSON格式）')
    batch_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    batch_parser.add_argument('--verbose', action='store_true', help='详细输出')
    
    # search命令
    search_parser = subparsers.add_parser('search', help='搜索图片')
    search_parser.add_argument('--query', required=True, help='搜索查询')
    search_parser.add_argument('--tags', help='过滤标签（逗号分隔）')
    search_parser.add_argument('--limit', type=int, default=10, help='返回结果限制')
    search_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    search_parser.add_argument('--verbose', action='store_true', help='详细输出')
    
    # server命令
    server_parser = subparsers.add_parser('server', help='启动API服务器')
    server_parser.add_argument('--host', default='0.0.0.0', help='监听主机')
    server_parser.add_argument('--port', type=int, default=8080, help='监听端口')
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 创建CLI实例并执行
    cli = AssetPipelineCLI()
    return cli.run(args)


if __name__ == "__main__":
    sys.exit(main())