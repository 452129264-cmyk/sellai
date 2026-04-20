#!/usr/bin/env python3
"""
三大军团集成测试脚本
测试文件完整性、数据库连接、基本功能
"""

import os
import sys
import sqlite3
import importlib.util
from datetime import datetime

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path} (存在)")
        return True
    else:
        print(f"❌ {description}: {file_path} (不存在)")
        return False

def check_database_tables(db_path):
    """检查数据库表结构"""
    print(f"\n=== 检查共享状态库表结构 ===")
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查现有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print(f"数据库中的表 ({len(tables)}个):")
    for table in tables:
        print(f"  - {table[0]}")
    
    # 检查达人合作相关表
    required_tables = ['influencer_profiles', 'influencer_collaboration_list', 'influencer_followup_logs']
    missing_tables = []
    
    for req_table in required_tables:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (req_table,))
        if not cursor.fetchone():
            missing_tables.append(req_table)
    
    if missing_tables:
        print(f"❌ 缺失表: {missing_tables}")
        conn.close()
        return False
    else:
        print(f"✅ 所有达人合作表都存在")
        
        # 显示表结构
        for req_table in required_tables:
            print(f"\n表结构: {req_table}")
            cursor.execute(f"PRAGMA table_info({req_table})")
            columns = cursor.fetchall()
            
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                pk_marker = " (PK)" if pk else ""
                not_null_marker = " NOT NULL" if not_null else ""
                default_marker = f" DEFAULT {default_val}" if default_val else ""
                print(f"  {col_id}. {col_name:<25} {col_type:<15}{pk_marker}{not_null_marker}{default_marker}")
    
    conn.close()
    return True

def check_python_module(module_path, module_name):
    """检查Python模块是否可以导入"""
    print(f"\n=== 检查Python模块: {module_name} ===")
    
    if not os.path.exists(module_path):
        print(f"❌ 模块文件不存在: {module_path}")
        return False
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"✅ 模块导入成功: {module_name}")
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def check_office_interfaces():
    """检查办公室界面文件"""
    print(f"\n=== 检查办公室界面文件 ===")
    
    office_files = [
        ("outputs/仪表盘/SellAI_办公室_流量爆破版.html", "流量爆破军团办公室界面"),
        ("outputs/仪表盘/SellAI_办公室_达人洽谈版.html", "达人洽谈军团办公室界面"),
        ("outputs/仪表盘/SellAI_办公室_短视频引流版.html", "短视频引流军团办公室界面"),
    ]
    
    all_exist = True
    for file_path, description in office_files:
        if not check_file_exists(file_path, description):
            all_exist = False
    
    return all_exist

def check_avatar_templates():
    """检查分身模板文件"""
    print(f"\n=== 检查分身模板文件 ===")
    
    template_files = [
        ("outputs/分身模板库/SEO优化专家分身.json", "SEO优化专家分身模板"),
        ("outputs/分身模板库/达人筛选专家分身.json", "达人筛选专家分身模板"),
        ("outputs/分身模板库/视频创作专家分身.json", "视频创作专家分身模板"),
    ]
    
    all_exist = True
    for file_path, description in template_files:
        if not check_file_exists(file_path, description):
            all_exist = False
    
    return all_exist

def check_test_reports():
    """检查测试报告文件"""
    print(f"\n=== 检查测试报告文件 ===")
    
    report_files = [
        ("docs/流量爆破军团测试报告.md", "流量爆破军团测试报告"),
        ("docs/达人洽谈军团测试报告.md", "达人洽谈军团测试报告"),
        ("docs/短视频引流军团测试报告.md", "短视频引流军团测试报告"),
    ]
    
    all_exist = True
    for file_path, description in report_files:
        if not check_file_exists(file_path, description):
            all_exist = False
    
    return all_exist

def test_basic_functionality():
    """测试基本功能"""
    print(f"\n=== 测试基本功能 ===")
    
    # 测试流量爆破爬虫基本功能
    try:
        # 尝试导入模块
        sys.path.insert(0, 'src')
        from traffic_burst_crawlers import TrafficBurstCrawler
        
        crawler = TrafficBurstCrawler()
        print(f"✅ 流量爆破爬虫类初始化成功")
        
        # 测试请求方法结构
        result_structure = crawler.make_request("https://example.com", platform="test")
        required_keys = ['success', 'status_code', 'data', 'error', 'data_metrics']
        
        if all(key in result_structure for key in required_keys):
            print(f"✅ 请求返回结构完整")
        else:
            print(f"❌ 请求返回结构缺失")
            return False
            
    except Exception as e:
        print(f"❌ 流量爆破爬虫测试失败: {e}")
        return False
    
    # 测试达人洽谈引擎基本功能
    try:
        from influencer_outreach_engine import InfluencerOutreachEngine
        
        engine = InfluencerOutreachEngine()
        print(f"✅ 达人洽谈话术引擎初始化成功")
        
        # 测试数据库连接
        conn = engine.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM influencer_profiles")
        count = cursor.fetchone()[0]
        print(f"✅ 数据库连接正常，达人档案数: {count}")
        
        engine.close()
        
    except Exception as e:
        print(f"❌ 达人洽谈引擎测试失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("=== 三大军团集成完整性测试 ===\n")
    
    test_start = datetime.now()
    
    # 1. 检查核心代码文件
    core_modules = [
        ("src/traffic_burst_crawlers.py", "流量爆破爬虫模块"),
        ("src/shopify_seo_optimizer.py", "Shopify SEO优化引擎"),
        ("src/influencer_outreach_engine.py", "达人洽谈话术引擎"),
        ("src/influencer_mass_messenger.py", "批量私信系统"),
        ("src/video_generation_templates.py", "AI视频生成模板"),
        ("src/short_video_distributor.py", "短视频分发管道"),
        ("src/video_performance_tracker.py", "效果追踪系统"),
    ]
    
    all_core_exist = True
    for file_path, description in core_modules:
        if not check_file_exists(file_path, description):
            all_core_exist = False
    
    if not all_core_exist:
        print("\n❌ 核心代码文件缺失，测试中止")
        return False
    
    # 2. 检查产出文件
    if not check_office_interfaces():
        print("\n❌ 办公室界面文件缺失")
        return False
    
    if not check_avatar_templates():
        print("\n❌ 分身模板文件缺失")
        return False
    
    if not check_test_reports():
        print("\n❌ 测试报告文件缺失")
        return False
    
    # 3. 检查数据库
    if not check_database_tables("data/shared_state/state.db"):
        print("\n❌ 数据库表结构不完整")
        return False
    
    # 4. 测试基本功能
    if not test_basic_functionality():
        print("\n❌ 基本功能测试失败")
        return False
    
    # 5. 检查DDL文件
    if not check_file_exists("docs/达人洽谈军团_DDL.sql", "达人合作表DDL文件"):
        print("\n❌ DDL文件缺失")
        return False
    
    test_end = datetime.now()
    duration = (test_end - test_start).total_seconds()
    
    print(f"\n{'='*60}")
    print("✅ 所有集成完整性检查通过！")
    print(f"📊 测试耗时: {duration:.2f}秒")
    print(f"📅 测试时间: {test_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 生成测试摘要
    print(f"\n📋 测试摘要:")
    print(f"  • 核心代码文件: 7/7 存在")
    print(f"  • 办公室界面: 3/3 存在")  
    print(f"  • 分身模板: 3/3 存在")
    print(f"  • 测试报告: 3/3 存在")
    print(f"  • 数据库表: 3/3 达人合作表")
    print(f"  • 基本功能: ✅ 通过")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)