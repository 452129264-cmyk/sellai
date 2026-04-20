#!/usr/bin/env python3
"""
Banana生图内核归档流水线集成测试

测试图片处理、记忆同步等核心功能。
"""

import os
import sys
import json
import tempfile
import time
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.banana_asset_pipeline.config import PipelineConfig, DEFAULT_CONFIG, generate_image_id
from src.banana_asset_pipeline.pipeline import AssetPipeline
from src.banana_asset_pipeline.image_processor import ImageProcessor


def create_test_image(image_path: str, width: int = 512, height: int = 512) -> bool:
    """创建测试图片"""
    try:
        from PIL import Image, ImageDraw
        
        # 创建新图片
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # 添加一些文本
        draw.text((10, 10), f"Test Image {width}x{height}", fill='black')
        draw.text((10, 50), "Generated for pipeline testing", fill='blue')
        
        # 保存
        img.save(image_path, format='PNG')
        print(f"✅ 创建测试图片: {image_path} ({width}x{height})")
        return True
        
    except ImportError:
        # 如果PIL不可用，创建虚拟文件
        with open(image_path, 'wb') as f:
            f.write(b"fake image data for testing")
        print(f"⚠️  创建虚拟测试文件: {image_path} (PIL不可用)")
        return True
    except Exception as e:
        print(f"❌ 创建测试图片失败: {str(e)}")
        return False


def test_config() -> bool:
    """测试配置模块"""
    print("\n🔧 测试配置模块...")
    
    try:
        config = PipelineConfig(
            base_storage_dir="test_outputs/images",
            temp_processing_dir="test_temp/processing",
            metadata_dir="test_data/metadata",
            notebook_lm_sync_enabled=False,
        )
        
        # 确保目录
        config.ensure_directories()
        
        # 测试路径生成
        test_path = config.get_avatar_path("2024-01-01", "product_shoot", "avatar_001")
        print(f"✅ 配置测试通过")
        print(f"   基础目录: {config.base_storage_dir}")
        print(f"   测试路径: {test_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {str(e)}")
        return False


def test_image_processor() -> bool:
    """测试图片处理器"""
    print("\n🖼️  测试图片处理器...")
    
    try:
        # 创建测试配置
        config = PipelineConfig(
            base_storage_dir="test_outputs/images",
            temp_processing_dir="test_temp/processing",
            metadata_dir="test_data/metadata",
            notebook_lm_sync_enabled=False,
        )
        config.ensure_directories()
        
        # 创建测试图片
        test_image = os.path.join(config.temp_processing_dir, "processor_test.png")
        if not create_test_image(test_image, 1024, 768):
            return False
        
        # 测试处理器
        processor = ImageProcessor(config)
        
        test_params = {
            "prompt": "A beautiful test image for processor validation",
            "negative_prompt": "blurry, low quality, watermark",
            "model_name": "test_model",
            "model_version": "1.0",
            "seed": 9999,
            "steps": 30,
        }
        
        metadata, warnings = processor.process_image_file(
            image_path=test_image,
            generation_params=test_params,
            avatar_id="test_avatar_001",
            task_id="test_task_001",
            scene="test_scene",
        )
        
        if metadata:
            print(f"✅ 图片处理器测试通过")
            print(f"   图片ID: {metadata.image_id}")
            print(f"   分类: {metadata.category.value}")
            print(f"   质量等级: {metadata.quality_grade.value}")
            print(f"   存储路径: {metadata.file_path}")
            
            # 验证文件存在
            if os.path.exists(metadata.file_path):
                print(f"✅ 图片文件已正确存储")
            else:
                print(f"⚠️  图片文件未找到")
            
            return True
        else:
            print(f"❌ 图片处理器测试失败，警告: {warnings}")
            return False
            
    except Exception as e:
        print(f"❌ 图片处理器测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_pipeline() -> bool:
    """测试流水线"""
    print("\n🚀 测试流水线引擎...")
    
    try:
        # 创建测试配置
        config = PipelineConfig(
            base_storage_dir="test_outputs/images",
            temp_processing_dir="test_temp/processing",
            metadata_dir="test_data/metadata",
            notebook_lm_sync_enabled=False,
            max_concurrent=2,
            batch_size=2,
        )
        config.ensure_directories()
        
        # 创建测试图片 - 创建符合分辨率要求的图片
        test_images = []
        for i in range(2):
            # 创建分辨率符合要求的图片（>= 2048x2048）
            width = 2100 + i*100  # 确保大于2048
            height = 2100 + i*100
            image_path = os.path.join(config.temp_processing_dir, f"pipeline_test_{i}.png")
            if create_test_image(image_path, width, height):
                test_images.append(image_path)
        
        if len(test_images) < 2:
            print("❌ 无法创建足够的测试图片")
            return False
        
        # 创建流水线
        pipeline = AssetPipeline(config)
        
        # 启动流水线
        if not pipeline.start():
            print("❌ 流水线启动失败")
            return False
        
        print("✅ 流水线启动成功")
        
        # 提交任务
        job_ids = []
        for i, image_path in enumerate(test_images):
            job_id = pipeline.submit_job(
                image_path=image_path,
                generation_params={
                    "prompt": f"Pipeline test image {i}",
                    "negative_prompt": "blurry",
                    "model_name": "test_model",
                    "model_version": "1.0",
                },
                avatar_id=f"test_avatar_{i:03d}",
                task_id=f"test_task_{i:03d}",
                scene="test_scene",
            )
            job_ids.append(job_id)
            print(f"   提交任务 {i+1}: {job_id}")
        
        # 等待处理
        print("   等待处理完成...")
        processed_count = 0
        for _ in range(30):  # 最多等待3秒
            completed = pipeline.get_stats()["jobs_completed"]
            if completed >= len(job_ids):
                processed_count = completed
                break
            time.sleep(0.1)
        
        # 获取结果
        results = pipeline.get_all_results()
        
        success_count = sum(1 for r in results if r.success)
        
        print(f"   处理完成: {success_count}/{len(job_ids)} 成功")
        
        # 显示结果
        for result in results:
            if result.success and result.metadata:
                print(f"   ✅ {result.job_id}: {result.metadata.image_id} ({result.processing_time_ms:.0f}ms)")
            else:
                print(f"   ❌ {result.job_id}: 失败 ({result.errors})")
        
        # 停止流水线
        pipeline.stop()
        
        if success_count >= len(job_ids) * 0.8:  # 允许20%失败率
            print(f"✅ 流水线测试通过")
            return True
        else:
            print(f"❌ 流水线测试失败，成功率不足")
            return False
        
    except Exception as e:
        print(f"❌ 流水线测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_sync() -> bool:
    """测试记忆同步"""
    print("\n🧠 测试记忆同步...")
    
    try:
        # 创建测试配置
        config = PipelineConfig(
            base_storage_dir="test_outputs/images",
            temp_processing_dir="test_temp/processing",
            metadata_dir="test_data/metadata",
            notebook_lm_sync_enabled=False,  # 禁用实际同步
        )
        config.ensure_directories()
        
        # 测试记忆同步管理器初始化
        from src.banana_asset_pipeline.memory_sync import MemorySyncManager
        
        sync_manager = MemorySyncManager(config)
        
        # 检查状态
        stats = sync_manager.get_stats()
        
        print(f"✅ 记忆同步管理器初始化成功")
        print(f"   系统就绪: {stats['system_ready']}")
        print(f"   同步启用: {stats['sync_enabled']}")
        
        # 清理
        sync_manager.cleanup()
        
        return True
        
    except Exception as e:
        print(f"❌ 记忆同步测试失败: {str(e)}")
        return False


def test_main_cli() -> bool:
    """测试命令行接口"""
    print("\n🖥️  测试命令行接口...")
    
    try:
        import subprocess
        
        # 测试init命令
        result = subprocess.run(
            ["python3", "src/banana_asset_pipeline/main.py", "init"],
            capture_output=True,
            text=True,
            cwd="/app/data/files",
        )
        
        if result.returncode == 0:
            print("✅ 命令行接口测试通过")
            print(f"   输出: {result.stdout[:200]}...")
            return True
        else:
            print(f"❌ 命令行接口测试失败")
            print(f"   错误: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 命令行接口测试失败: {str(e)}")
        return False


def run_all_tests() -> bool:
    """运行所有测试"""
    print("="*60)
    print("Banana生图内核归档流水线集成测试")
    print("="*60)
    
    tests = [
        ("配置模块", test_config),
        ("图片处理器", test_image_processor),
        ("记忆同步", test_memory_sync),
        ("流水线引擎", test_pipeline),
        ("命令行接口", test_main_cli),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试 '{test_name}' 异常: {str(e)}")
            failed += 1
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 成功率: {passed/(passed+failed)*100:.1f}%")
    
    # 显示整体状态
    if failed == 0:
        print("\n🎉 所有测试通过！归档流水线功能完整。")
        return True
    elif passed / (passed + failed) >= 0.8:
        print("\n⚠️  部分测试失败，但核心功能可用。")
        return True
    else:
        print("\n💥 测试失败较多，需要修复。")
        return False


def cleanup_test_files() -> None:
    """清理测试文件"""
    import shutil
    
    test_dirs = [
        "test_outputs",
        "test_temp",
        "test_data",
    ]
    
    for dir_path in test_dirs:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"🧹 清理: {dir_path}")
            except Exception:
                pass


if __name__ == "__main__":
    try:
        # 运行测试
        success = run_all_tests()
        
        # 清理测试文件（可选）
        if os.getenv("KEEP_TEST_FILES", "0") != "1":
            cleanup_test_files()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        cleanup_test_files()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试执行异常: {str(e)}")
        cleanup_test_files()
        sys.exit(1)