#!/usr/bin/env python3
"""
长期记忆配置测试脚本
验证工作流文件中记忆功能配置是否正确
"""

import json
import os
import sys

def load_workflow(file_path):
    """加载工作流JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        return None

def check_memory_config(workflow):
    """检查记忆功能配置"""
    print("🔍 检查长期记忆配置...")
    
    # 检查工作流全局设置
    settings = workflow.get('settings', {})
    memory_enabled = settings.get('memory_enabled', False)
    
    print(f"  工作流全局记忆启用: {'✅' if memory_enabled else '❌'}")
    
    # 检查关键分身节点
    key_avatars = [
        ('intelligence_officer', '情报官'),
        ('strategy_30margin', '30%毛利策略师'),
        ('copy_channel_officer', '文案渠道官'),
        ('todo_executor', '待办执行官'),
        ('avatar_processor', '分身处理器')
    ]
    
    nodes = workflow.get('nodes', [])
    node_map = {node['id']: node for node in nodes}
    
    print("\n🔍 检查关键分身节点记忆配置:")
    
    all_enabled = True
    for node_id, node_name in key_avatars:
        if node_id in node_map:
            node_data = node_map[node_id]
            # 对于Agent节点，检查memory字段
            if node_data.get('type') == 'agent':
                memory_config = node_data.get('data', {}).get('memory', False)
                status = '✅' if memory_config else '❌'
                print(f"  {node_name} ({node_id}): {status}")
                if not memory_config:
                    all_enabled = False
            else:
                print(f"  {node_name} ({node_id}): ⚠️ 不是Agent节点")
        else:
            print(f"  {node_name} ({node_id}): ❌ 未找到节点")
            all_enabled = False
    
    return memory_enabled and all_enabled

def check_shared_state_db():
    """检查共享状态库"""
    print("\n🔍 检查共享状态库...")
    
    db_path = 'data/shared_state/state.db'
    if os.path.exists(db_path):
        print(f"  ✅ 共享状态库存在: {db_path}")
        
        # 检查数据库是否可访问
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取表列表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print(f"  发现 {len(tables)} 个表:")
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table[0]})")
                columns = cursor.fetchall()
                print(f"    - {table[0]}: {len(columns)} 列")
            
            conn.close()
            return True
        except Exception as e:
            print(f"  ❌ 数据库访问错误: {e}")
            return False
    else:
        print(f"  ⚠️ 共享状态库不存在: {db_path}")
        print("    请确保已完成无限分身架构升级")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("SellAI封神版A - 长期记忆配置测试")
    print("=" * 60)
    
    # 测试工作流文件
    workflow_file = 'outputs/工作流/SellAI_OpenClow_记忆增强版.json'
    
    if not os.path.exists(workflow_file):
        print(f"⚠️ 增强版工作流不存在，检查完整版...")
        workflow_file = 'outputs/工作流/SellAI_OpenClow_完整版.json'
    
    workflow = load_workflow(workflow_file)
    if not workflow:
        sys.exit(1)
    
    print(f"📁 工作流文件: {workflow_file}")
    print(f"📊 节点数量: {len(workflow.get('nodes', []))}")
    print(f"🔗 连接数量: {len(workflow.get('edges', []))}")
    
    # 检查记忆配置
    memory_config_ok = check_memory_config(workflow)
    
    # 检查共享状态库
    db_ok = check_shared_state_db()
    
    # 综合结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    if memory_config_ok:
        print("✅ 长期记忆配置: 通过")
        print("   - 工作流全局记忆已启用")
        print("   - 所有关键分身节点记忆功能已配置")
    else:
        print("❌ 长期记忆配置: 未通过")
        print("   - 请检查工作流设置和节点配置")
    
    if db_ok:
        print("✅ 共享状态库: 通过")
        print("   - 数据库文件存在且可访问")
    else:
        print("⚠️ 共享状态库: 警告")
        print("   - 数据库可能未创建或无法访问")
    
    print("\n📋 后续步骤:")
    print("  1. 在Coze平台导入增强版工作流")
    print("  2. 启动系统并创建测试分身")
    print("  3. 执行简单任务（如商机发现、成本分析）")
    print("  4. 在Coze平台的记忆功能中查看决策历史")
    
    return memory_config_ok

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)