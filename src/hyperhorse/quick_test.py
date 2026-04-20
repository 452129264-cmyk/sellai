#!/usr/bin/env python3
"""
HyperHorse模块快速测试脚本
验证基本功能正常
"""

import sys
import os
import json
import logging
import sqlite3
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """测试数据库连接"""
    logger.info("测试数据库连接...")
    
    db_path = "data/shared_state/state.db"
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        logger.info(f"数据库连接成功，现有表数量: {len(tables)}")
        
        # 显示现有表
        for table in tables:
            logger.info(f"  表名: {table[0]}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return False

def test_module_registration():
    """测试模块注册"""
    logger.info("测试HyperHorse模块注册...")
    
    try:
        # 导入模块
        from module_registry import HyperHorseModule
        
        # 创建模块实例
        module = HyperHorseModule()
        
        # 注册模块
        success = module.register()
        
        if success:
            logger.info("模块注册成功")
            
            # 获取状态信息
            status = module.get_status()
            logger.info(f"模块状态: {json.dumps(status, ensure_ascii=False, indent=2)[:500]}...")
            
            return True
        else:
            logger.error("模块注册失败")
            return False
            
    except Exception as e:
        logger.error(f"模块注册测试失败: {e}")
        return False

def test_engine_initialization():
    """测试引擎初始化"""
    logger.info("测试HyperHorse引擎初始化...")
    
    try:
        # 导入引擎
        from core import HyperHorseEngine
        
        # 创建引擎实例
        engine = HyperHorseEngine()
        
        # 获取引擎信息
        engine_info = engine.get_engine_info()
        
        logger.info(f"引擎初始化成功")
        logger.info(f"引擎ID: {engine_info['engine_id']}")
        logger.info(f"模型版本: {engine_info['model_version']}")
        logger.info(f"质量等级: {engine_info['quality_level']}")
        logger.info(f"能力数量: {len(engine_info['capabilities'])}")
        logger.info(f"成功模式数量: {engine_info['success_patterns_count']}")
        
        return True
        
    except Exception as e:
        logger.error(f"引擎初始化测试失败: {e}")
        return False

def test_api_adapter():
    """测试API适配器"""
    logger.info("测试API适配器...")
    
    try:
        # 导入适配器
        from api_adapter import HyperHorseAPIAdapter
        
        # 创建适配器实例
        adapter = HyperHorseAPIAdapter()
        
        # 获取服务信息
        service_info = adapter.get_service_info()
        
        logger.info(f"API适配器初始化成功")
        logger.info(f"服务类型: {service_info['service_type']}")
        logger.info(f"引擎ID: {service_info['engine_info']['engine_id']}")
        
        # 检查兼容性
        compatibility = service_info['compatibility']
        logger.info(f"兼容性检查:")
        logger.info(f"  现有视频服务: {compatibility['existing_video_service']}")
        logger.info(f"  无限分身系统: {compatibility['infinite_agents_system']}")
        logger.info(f"  记忆V2系统: {compatibility['memory_v2_system']}")
        logger.info(f"  全球商业大脑: {compatibility['global_business_brain']}")
        
        return True
        
    except Exception as e:
        logger.error(f"API适配器测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始HyperHorse模块快速测试")
    
    test_results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "tests": [],
        "timestamp": datetime.now().isoformat()
    }
    
    tests = [
        ("数据库连接", test_database_connection),
        ("模块注册", test_module_registration),
        ("引擎初始化", test_engine_initialization),
        ("API适配器", test_api_adapter)
    ]
    
    all_passed = True
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"测试: {test_name}")
        logger.info(f"{'='*50}")
        
        test_results["total_tests"] += 1
        
        try:
            success = test_func()
            
            if success:
                logger.info(f"✅ {test_name} 测试通过")
                test_results["passed_tests"] += 1
                test_results["tests"].append({
                    "name": test_name,
                    "status": "PASSED",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                logger.error(f"❌ {test_name} 测试失败")
                test_results["failed_tests"] += 1
                test_results["tests"].append({
                    "name": test_name,
                    "status": "FAILED",
                    "timestamp": datetime.now().isoformat()
                })
                all_passed = False
                
        except Exception as e:
            logger.error(f"❌ {test_name} 测试异常: {e}")
            test_results["failed_tests"] += 1
            test_results["tests"].append({
                "name": test_name,
                "status": "ERROR",
                "error": str(e)[:200],
                "timestamp": datetime.now().isoformat()
            })
            all_passed = False
    
    # 计算通过率
    pass_rate = (test_results["passed_tests"] / max(1, test_results["total_tests"])) * 100
    
    print(f"\n{'='*80}")
    print("📊 测试结果汇总")
    print(f"{'='*80}")
    print(f"总测试数: {test_results['total_tests']}")
    print(f"通过数: {test_results['passed_tests']}")
    print(f"失败数: {test_results['failed_tests']}")
    print(f"通过率: {pass_rate:.2f}%")
    
    if all_passed:
        print(f"\n🎉 所有测试通过！HyperHorse模块功能正常。")
        return 0
    else:
        print(f"\n⚠️  部分测试失败，请检查相关功能。")
        return 1

if __name__ == "__main__":
    sys.exit(main())