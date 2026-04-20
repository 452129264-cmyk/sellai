#!/usr/bin/env python
"""
验证共享状态库实现的所有交付物
"""

import os
import sys
import sqlite3
import json

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (文件不存在)")
        return False

def check_db_structure(db_path):
    """检查数据库表结构"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查必需的表
        required_tables = [
            'processed_opportunities',
            'task_assignments',
            'avatar_capability_profiles',
            'cost_consumption_logs'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        all_tables_present = True
        for table in required_tables:
            if table in existing_tables:
                print(f"✅ 数据库表: {table}")
            else:
                print(f"❌ 数据库表: {table} (缺失)")
                all_tables_present = False
        
        # 检查数据行数
        cursor.execute("SELECT COUNT(*) FROM processed_opportunities")
        opp_count = cursor.fetchone()[0]
        print(f"  已处理商机数: {opp_count}")
        
        cursor.execute("SELECT COUNT(*) FROM avatar_capability_profiles")
        avatar_count = cursor.fetchone()[0]
        print(f"  分身画像数: {avatar_count}")
        
        conn.close()
        return all_tables_present
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False

def check_workflow_integration(workflow_path):
    """检查工作流集成"""
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        # 检查opportunity_deduplicator节点
        nodes = workflow.get('nodes', [])
        deduplicator_exists = any(node.get('id') == 'opportunity_deduplicator' for node in nodes)
        
        if deduplicator_exists:
            print("✅ 工作流集成: opportunity_deduplicator节点存在")
        else:
            print("❌ 工作流集成: opportunity_deduplicator节点缺失")
        
        # 检查shared_state_config变量
        variables = workflow.get('variables', {})
        shared_state_config = variables.get('shared_state_config')
        
        if shared_state_config:
            print("✅ 工作流集成: shared_state_config变量存在")
        else:
            print("❌ 工作流集成: shared_state_config变量缺失")
        
        return deduplicator_exists and shared_state_config is not None
        
    except Exception as e:
        print(f"❌ 工作流检查失败: {e}")
        return False

def check_office_interface(html_path):
    """检查办公室界面集成"""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('共享状态库监控', '监控标题'),
            ('metric-total-opp', '总商机数指标'),
            ('metric-completed-opp', '已完成指标'),
            ('metric-total-avatars', '总分身数指标'),
            ('metric-active-avatars', '活跃分身指标'),
            ('metric-total-cost', '累计成本指标'),
            ('metric-last-updated', '最后更新时间')
        ]
        
        all_checks_passed = True
        for term, description in checks:
            if term in content:
                print(f"✅ 办公室界面: {description}存在")
            else:
                print(f"❌ 办公室界面: {description}缺失")
                all_checks_passed = False
        
        return all_checks_passed
        
    except Exception as e:
        print(f"❌ 办公室界面检查失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("共享状态库实现交付物验证")
    print("=" * 60)
    
    # 检查文件
    required_files = [
        ('data/shared_state/state.db', '数据库文件'),
        ('src/shared_state_manager.py', '共享状态管理脚本'),
        ('src/test_shared_state.py', '测试脚本'),
        ('src/init_shared_state_db.py', '数据库初始化脚本'),
        ('src/integrate_shared_state.py', '工作流集成脚本'),
        ('outputs/工作流/SellAI_无限分身_升级版_with_shared_state.json', '集成后的工作流'),
        ('outputs/共享状态库验证报告.md', '验证报告'),
        ('outputs/仪表盘/SellAI_办公室.html', '办公室界面')
    ]
    
    all_files_exist = True
    for file_path, description in required_files:
        if not check_file_exists(file_path, description):
            all_files_exist = False
    
    print("\n" + "=" * 60)
    print("数据库结构验证")
    print("=" * 60)
    
    db_valid = check_db_structure('data/shared_state/state.db')
    
    print("\n" + "=" * 60)
    print("工作流集成验证")
    print("=" * 60)
    
    workflow_valid = check_workflow_integration('outputs/工作流/SellAI_无限分身_升级版_with_shared_state.json')
    
    print("\n" + "=" * 60)
    print("办公室界面验证")
    print("=" * 60)
    
    office_valid = check_office_interface('outputs/仪表盘/SellAI_办公室.html')
    
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    summary = {
        "文件完整性": all_files_exist,
        "数据库结构": db_valid,
        "工作流集成": workflow_valid,
        "办公室界面": office_valid
    }
    
    for item, status in summary.items():
        status_symbol = "✅" if status else "❌"
        print(f"{status_symbol} {item}: {'通过' if status else '失败'}")
    
    all_checks_passed = all(all_files_exist, db_valid, workflow_valid, office_valid)
    
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("✅ 所有交付物验证通过！")
        print("共享状态库实现完整，可以集成到无限AI分身架构中。")
    else:
        print("❌ 部分交付物验证失败，请检查上述问题。")
    
    print("=" * 60)
    
    # 保存验证结果
    verification_result = {
        "timestamp": "2026-04-03T15:34:00Z",
        "system": "SellAI无限AI分身架构",
        "component": "共享状态库",
        "checks": summary,
        "overall_status": "passed" if all_checks_passed else "failed"
    }
    
    result_file = "outputs/共享状态库交付物验证报告.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(verification_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n验证报告已保存: {result_file}")
    
    return 0 if all_checks_passed else 1

if __name__ == "__main__":
    sys.exit(main())