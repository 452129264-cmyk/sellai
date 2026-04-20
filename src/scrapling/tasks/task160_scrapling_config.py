#!/usr/bin/env python3
"""
Scrapling全球全品类配置文件生成任务
执行任务160：生成全球全品类爬虫配置，创建Memory V2记忆池，运行本地测试
"""

import os
import sys
import logging
import json
import yaml
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

# 添加src目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.scrapling.config_manager import GlobalConfigManager
except ImportError:
    # 备用导入路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scrapling.config_manager import GlobalConfigManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScraplingConfigTask:
    """Scrapling配置任务执行器"""
    
    def __init__(self, mode: str = "local"):
        """
        初始化任务
        
        参数：
            mode: 执行模式，"local"表示本地模式，不触发外部HTTP请求
        """
        self.mode = mode
        self.db_path = "data/shared_state/state.db"
        self.output_dir = "outputs/scrapling/config"
        self.test_report_path = "outputs/scrapling/test/config_test_report.md"
        
        # 确保目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.test_report_path), exist_ok=True)
        
        logger.info(f"Scrapling配置任务初始化完成，模式：{mode}")
    
    def initialize_config_tables(self) -> bool:
        """
        初始化配置数据库表
        
        返回：
            成功返回True，失败返回False
        """
        try:
            logger.info("开始初始化Scrapling配置表...")
            
            config_manager = GlobalConfigManager(self.db_path)
            result = config_manager.initialize_config_tables()
            
            if result:
                logger.info("Scrapling配置表初始化成功")
                return True
            else:
                logger.error("Scrapling配置表初始化失败")
                return False
                
        except Exception as e:
            logger.error(f"初始化配置表时发生异常: {e}")
            return False
    
    def export_config_files(self) -> Dict[str, bool]:
        """
        导出配置文件
        
        返回：
            各文件导出状态字典
        """
        results = {}
        
        try:
            config_manager = GlobalConfigManager(self.db_path)
            
            # 1. 导出YAML配置文件
            yaml_path = os.path.join(self.output_dir, "global_config.yaml")
            results["yaml_config"] = config_manager.export_config_yaml(yaml_path)
            
            # 2. 导出JSON配置文件（备用格式）
            json_path = os.path.join(self.output_dir, "global_config.json")
            try:
                config_summary = config_manager.get_config_summary()
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(config_summary, f, indent=2, ensure_ascii=False)
                results["json_config"] = True
                logger.info(f"JSON配置文件导出成功: {json_path}")
            except Exception as e:
                logger.error(f"JSON配置文件导出失败: {e}")
                results["json_config"] = False
            
            # 3. 生成配置摘要文档
            summary_path = os.path.join(self.output_dir, "config_summary.md")
            try:
                categories = config_manager.get_all_categories()
                
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write("# Scrapling全球全品类配置摘要\n\n")
                    f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
                    f.write(f"总品类数: {len(categories)}\n\n")
                    
                    f.write("## 已启用品类\n\n")
                    enabled_categories = [c for c in categories if c["enabled"]]
                    for cat in enabled_categories:
                        f.write(f"### {cat['category_name']} ({cat['category_id']})\n")
                        f.write(f"优先级: {cat['priority']}/5 | 爬取深度: {cat['crawl_depth']} | 最大页数: {cat['max_pages']}\n")
                        f.write(f"目标地区: {', '.join(cat['target_regions'])}\n")
                        f.write(f"关键词: {', '.join(cat['keywords'][:5])}...\n")
                        f.write(f"数据字段: {', '.join(cat['data_fields'][:5])}...\n")
                        f.write(f"目标平台: {', '.join(cat['platforms'][:5])}...\n\n")
                    
                    f.write("## 配置详情\n\n")
                    f.write(f"- YAML配置文件: `{yaml_path}`\n")
                    f.write(f"- JSON配置文件: `{json_path}`\n")
                    f.write(f"- 数据库路径: `{self.db_path}`\n")
                
                results["summary_doc"] = True
                logger.info(f"配置摘要文档导出成功: {summary_path}")
                
            except Exception as e:
                logger.error(f"配置摘要文档导出失败: {e}")
                results["summary_doc"] = False
            
            return results
            
        except Exception as e:
            logger.error(f"导出配置文件时发生异常: {e}")
            return {
                "yaml_config": False,
                "json_config": False,
                "summary_doc": False
            }
    
    def create_memory_v2_pool(self) -> bool:
        """
        创建Memory V2全球商业情报记忆池
        
        返回：
            成功返回True，失败返回False
        """
        try:
            logger.info("开始创建Memory V2全球商业情报记忆池...")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否已存在同名记忆池
            cursor.execute(
                "SELECT memory_space_id FROM memory_space WHERE space_name = ?",
                ("global_business_intel",)
            )
            
            existing = cursor.fetchone()
            
            if existing:
                logger.info("Memory V2全球商业情报记忆池已存在，跳过创建")
                conn.close()
                return True
            
            # 生成唯一ID
            memory_space_id = f"memory_space_{int(datetime.now().timestamp())}_{os.urandom(4).hex()}"
            
            # 插入memory_space记录
            cursor.execute("""
                INSERT INTO memory_space 
                (memory_space_id, space_name, owner_user_id, space_type, description,
                 default_permission, encryption_enabled, retention_days, max_size_mb,
                 current_size_mb, is_active, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_space_id,
                "global_business_intel",
                "system",
                "business_intelligence",
                "全球商业情报记忆池，存储Scrapling爬取的全球全品类赚钱情报，支持多国多行业数据沉淀与AI进化",
                "read_write",
                True,
                3650,  # 10年保留期
                10240,  # 10GB最大容量
                0.0,
                True,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                json.dumps({
                    "module": "scrapling",
                    "data_type": "business_intelligence",
                    "global_coverage": True,
                    "multi_category": True,
                    "update_frequency": "30min",
                    "created_by": "task160"
                })
            ))
            
            # 创建关联的数据表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrapling_global_business_data (
                    data_id TEXT PRIMARY KEY,
                    memory_space_id TEXT NOT NULL,
                    category_id TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_platform TEXT NOT NULL,
                    region TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    extracted_data TEXT NOT NULL,  -- JSON格式
                    confidence_score REAL NOT NULL,
                    discovered_at TIMESTAMP NOT NULL,
                    processed_at TIMESTAMP,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    verification_status TEXT NOT NULL DEFAULT 'pending',
                    tags TEXT,  -- JSON数组格式
                    metadata TEXT,  -- JSON格式
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (memory_space_id) REFERENCES memory_space(memory_space_id),
                    FOREIGN KEY (category_id) REFERENCES scrapling_global_categories(category_id)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scrapling_data_memory_space 
                ON scrapling_global_business_data(memory_space_id, category_id, region)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scrapling_data_discovered 
                ON scrapling_global_business_data(discovered_at DESC, confidence_score DESC)
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("Memory V2全球商业情报记忆池创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建Memory V2记忆池时发生异常: {e}")
            return False
    
    def run_local_tests(self) -> Dict[str, Any]:
        """
        运行本地配置有效性测试
        
        返回：
            测试结果字典
        """
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "details": []
        }
        
        try:
            logger.info("开始运行本地配置有效性测试...")
            
            # 测试1：数据库连接测试
            test_results["total_tests"] += 1
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0] == 1:
                    test_results["passed_tests"] += 1
                    test_results["details"].append({
                        "test_name": "数据库连接测试",
                        "status": "passed",
                        "message": "数据库连接成功"
                    })
                else:
                    test_results["failed_tests"] += 1
                    test_results["details"].append({
                        "test_name": "数据库连接测试",
                        "status": "failed",
                        "message": "数据库查询返回异常结果"
                    })
            except Exception as e:
                test_results["failed_tests"] += 1
                test_results["details"].append({
                    "test_name": "数据库连接测试",
                    "status": "failed",
                    "message": f"数据库连接失败: {e}"
                })
            
            # 测试2：配置表存在性测试
            test_results["total_tests"] += 1
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                required_tables = [
                    "scrapling_global_categories",
                    "scrapling_anti_anti_crawl_config",
                    "scrapling_vpn_strategy_config",
                    "scrapling_data_processing_config"
                ]
                
                missing_tables = []
                for table in required_tables:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if not cursor.fetchone():
                        missing_tables.append(table)
                
                conn.close()
                
                if not missing_tables:
                    test_results["passed_tests"] += 1
                    test_results["details"].append({
                        "test_name": "配置表存在性测试",
                        "status": "passed",
                        "message": f"所有配置表存在: {', '.join(required_tables)}"
                    })
                else:
                    test_results["failed_tests"] += 1
                    test_results["details"].append({
                        "test_name": "配置表存在性测试",
                        "status": "failed",
                        "message": f"缺失配置表: {', '.join(missing_tables)}"
                    })
                    
            except Exception as e:
                test_results["failed_tests"] += 1
                test_results["details"].append({
                    "test_name": "配置表存在性测试",
                    "status": "failed",
                    "message": f"配置表检查失败: {e}"
                })
            
            # 测试3：默认配置数据测试
            test_results["total_tests"] += 1
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM scrapling_global_categories WHERE enabled = TRUE")
                category_count = cursor.fetchone()[0]
                
                conn.close()
                
                if category_count >= 5:  # 默认至少有5个品类
                    test_results["passed_tests"] += 1
                    test_results["details"].append({
                        "test_name": "默认配置数据测试",
                        "status": "passed",
                        "message": f"默认品类配置正常，已启用品类数: {category_count}"
                    })
                else:
                    test_results["failed_tests"] += 1
                    test_results["details"].append({
                        "test_name": "默认配置数据测试",
                        "status": "failed",
                        "message": f"默认品类配置不足，已启用品类数: {category_count} (期望≥5)"
                    })
                    
            except Exception as e:
                test_results["failed_tests"] += 1
                test_results["details"].append({
                    "test_name": "默认配置数据测试",
                    "status": "failed",
                    "message": f"默认配置检查失败: {e}"
                })
            
            # 测试4：Memory V2记忆池测试
            test_results["total_tests"] += 1
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT memory_space_id, space_name, description, is_active 
                    FROM memory_space 
                    WHERE space_name = 'global_business_intel'
                """)
                
                memory_pool = cursor.fetchone()
                conn.close()
                
                if memory_pool and memory_pool[3] == 1:  # is_active = TRUE
                    test_results["passed_tests"] += 1
                    test_results["details"].append({
                        "test_name": "Memory V2记忆池测试",
                        "status": "passed",
                        "message": f"全球商业情报记忆池已创建并激活: {memory_pool[1]}"
                    })
                else:
                    test_results["failed_tools"] += 1
                    test_results["details"].append({
                        "test_name": "Memory V2记忆池测试",
                        "status": "failed",
                        "message": "全球商业情报记忆池未创建或未激活"
                    })
                    
            except Exception as e:
                test_results["failed_tests"] += 1
                test_results["details"].append({
                    "test_name": "Memory V2记忆池测试",
                    "status": "failed",
                    "message": f"Memory V2记忆池检查失败: {e}"
                })
            
            # 测试5：配置文件存在性测试
            test_results["total_tests"] += 1
            try:
                yaml_path = os.path.join(self.output_dir, "global_config.yaml")
                json_path = os.path.join(self.output_dir, "global_config.json")
                summary_path = os.path.join(self.output_dir, "config_summary.md")
                
                files_exist = all([
                    os.path.exists(yaml_path),
                    os.path.exists(json_path),
                    os.path.exists(summary_path)
                ])
                
                if files_exist:
                    test_results["passed_tests"] += 1
                    test_results["details"].append({
                        "test_name": "配置文件存在性测试",
                        "status": "passed",
                        "message": "所有配置文件已成功生成"
                    })
                else:
                    test_results["failed_tests"] += 1
                    test_results["details"].append({
                        "test_name": "配置文件存在性测试",
                        "status": "failed",
                        "message": f"部分配置文件缺失，YAML: {os.path.exists(yaml_path)}, JSON: {os.path.exists(json_path)}, 摘要: {os.path.exists(summary_path)}"
                    })
                    
            except Exception as e:
                test_results["failed_tests"] += 1
                test_results["details"].append({
                    "test_name": "配置文件存在性测试",
                    "status": "failed",
                    "message": f"配置文件检查失败: {e}"
                })
            
            logger.info(f"本地测试完成: {test_results['passed_tests']}/{test_results['total_tests']} 通过")
            return test_results
            
        except Exception as e:
            logger.error(f"运行本地测试时发生异常: {e}")
            test_results["details"].append({
                "test_name": "测试框架异常",
                "status": "failed",
                "message": f"测试框架异常: {e}"
            })
            return test_results
    
    def generate_test_report(self, test_results: Dict[str, Any]) -> bool:
        """
        生成测试报告
        
        参数：
            test_results: 测试结果字典
            
        返回：
            成功返回True，失败返回False
        """
        try:
            logger.info("开始生成测试报告...")
            
            with open(self.test_report_path, 'w', encoding='utf-8') as f:
                f.write("# Scrapling配置有效性测试报告\n\n")
                f.write(f"生成时间: {test_results['timestamp']}\n\n")
                
                # 测试摘要
                f.write("## 测试摘要\n\n")
                f.write(f"- 总测试数: {test_results['total_tests']}\n")
                f.write(f"- 通过测试: {test_results['passed_tests']}\n")
                f.write(f"- 失败测试: {test_results['failed_tests']}\n")
                
                pass_rate = (test_results['passed_tests'] / test_results['total_tests']) * 100 if test_results['total_tests'] > 0 else 0
                f.write(f"- 通过率: {pass_rate:.1f}%\n\n")
                
                # 测试详情
                f.write("## 测试详情\n\n")
                for detail in test_results['details']:
                    status_icon = "✅" if detail['status'] == 'passed' else "❌"
                    f.write(f"### {status_icon} {detail['test_name']}\n")
                    f.write(f"- 状态: {detail['status']}\n")
                    f.write(f"- 消息: {detail['message']}\n\n")
                
                # 结论
                f.write("## 测试结论\n\n")
                if test_results['failed_tests'] == 0:
                    f.write("✅ **所有测试通过** - Scrapling配置有效性验证成功，配置文件、数据库表和记忆池均创建完成。\n")
                    f.write("配置系统已准备好支持全球全品类商业情报爬取任务。\n")
                else:
                    f.write(f"⚠️ **部分测试失败** - {test_results['failed_tests']}/{test_results['total_tests']} 测试失败。\n")
                    f.write("需要检查配置生成流程，确保所有组件正确初始化。\n")
                
                # 文件清单
                f.write("\n## 生成文件清单\n\n")
                f.write(f"- YAML配置文件: `{self.output_dir}/global_config.yaml`\n")
                f.write(f"- JSON配置文件: `{self.output_dir}/global_config.json`\n")
                f.write(f"- 配置摘要文档: `{self.output_dir}/config_summary.md`\n")
                f.write(f"- 测试报告: `{self.test_report_path}`\n")
                f.write(f"- 数据库: `{self.db_path}`\n")
            
            logger.info(f"测试报告生成成功: {self.test_report_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成测试报告时发生异常: {e}")
            return False
    
    def execute(self) -> bool:
        """
        执行主流程
        
        返回：
            整体执行成功返回True，失败返回False
        """
        logger.info("开始执行Scrapling全球全品类配置文件生成任务...")
        
        # 步骤1：初始化配置表
        logger.info("--- 步骤1: 初始化配置表 ---")
        if not self.initialize_config_tables():
            logger.error("配置表初始化失败，任务终止")
            return False
        
        # 步骤2：导出配置文件
        logger.info("--- 步骤2: 导出配置文件 ---")
        export_results = self.export_config_files()
        
        if not all(export_results.values()):
            logger.warning("部分配置文件导出失败，继续执行...")
        
        # 步骤3：创建Memory V2记忆池
        logger.info("--- 步骤3: 创建Memory V2记忆池 ---")
        if not self.create_memory_v2_pool():
            logger.error("Memory V2记忆池创建失败，任务终止")
            return False
        
        # 步骤4：运行本地测试
        logger.info("--- 步骤4: 运行本地测试 ---")
        test_results = self.run_local_tests()
        
        # 步骤5：生成测试报告
        logger.info("--- 步骤5: 生成测试报告 ---")
        self.generate_test_report(test_results)
        
        # 最终检查
        success = test_results['failed_tests'] == 0
        
        if success:
            logger.info("✅ Scrapling配置生成任务执行成功，所有测试通过")
        else:
            logger.warning(f"⚠️ Scrapling配置生成任务执行完成，但有{test_results['failed_tests']}个测试失败")
        
        return success


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrapling全球全品类配置文件生成任务')
    parser.add_argument('--mode', default='local', choices=['local', 'remote'],
                       help='执行模式: local(本地，无网络请求) 或 remote(远程)')
    
    args = parser.parse_args()
    
    # 创建任务实例并执行
    task = ScraplingConfigTask(mode=args.mode)
    success = task.execute()
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()