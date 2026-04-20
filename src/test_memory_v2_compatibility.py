#!/usr/bin/env python3
"""
Memory V2 系统兼容性测试
测试与现有系统的兼容性：
1. 无限分身架构
2. KAIROS守护系统
3. 共享状态库
4. 现有工作流节点
"""

import sys
import json
import time
import sqlite3
from datetime import datetime

sys.path.append('/app/data/files')

print("=== Memory V2 系统兼容性测试 ===\n")

def test_compatibility_with_shared_state():
    """测试与共享状态库的兼容性"""
    print("1. 测试与共享状态库兼容性...")
    
    try:
        # 检查共享状态库连接
        conn = sqlite3.connect('data/shared_state/state.db')
        cursor = conn.cursor()
        
        # 检查所有相关表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'memory_validation_status',
            'memory_data_checksums', 
            'memory_indexes',
            'memory_index_entries'
        ]
        
        missing_tables = []
        for table in required_tables:
            if table not in tables:
                missing_tables.append(table)
        
        if missing_tables:
            print(f"  ❌ 缺失表: {missing_tables}")
            return False
        else:
            print(f"  ✅ 所有必需表存在")
        
        # 测试表结构兼容性
        cursor.execute("PRAGMA table_info(memory_validation_status)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = ['memory_id', 'avatar_id', 'memory_type', 'data_hash', 
                          'write_status', 'verification_status']
        
        missing_columns = []
        for col in required_columns:
            if col not in columns:
                missing_columns.append(col)
        
        if missing_columns:
            print(f"  ❌ 缺失列: {missing_columns}")
            return False
        else:
            print(f"  ✅ 表结构兼容")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ 共享状态库测试失败: {e}")
        return False

def test_compatibility_with_avatar_system():
    """测试与分身系统的兼容性"""
    print("\n2. 测试与分身系统兼容性...")
    
    try:
        # 检查avatar相关表
        conn = sqlite3.connect('data/shared_state/state.db')
        cursor = conn.cursor()
        
        # 检查avatar_capability_profiles表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='avatar_capability_profiles'")
        if cursor.fetchone():
            print(f"  ✅ avatar能力配置表存在")
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(avatar_capability_profiles)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'avatar_id' in columns:
                print(f"  ✅ avatar_id列存在")
                
                # 测试数据插入兼容性
                test_avatar_id = f"test_compat_{int(time.time())}"
                cursor.execute('''
                    INSERT OR REPLACE INTO avatar_capability_profiles 
                    (avatar_id, avatar_name, capability_scores, specialization_tags, 
                     success_rate, total_tasks_completed, last_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    test_avatar_id,
                    '测试分身兼容性',
                    json.dumps({'data_crawling': 0.9, 'financial_analysis': 0.8}),
                    json.dumps(['测试', '兼容性']),
                    0.85,
                    10,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                print(f"  ✅ 数据插入成功")
                
                # 清理测试数据
                cursor.execute("DELETE FROM avatar_capability_profiles WHERE avatar_id = ?", (test_avatar_id,))
                conn.commit()
                
            else:
                print(f"  ❌ avatar_id列不存在")
                return False
        else:
            print(f"  ❌ avatar能力配置表不存在")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ 分身系统兼容性测试失败: {e}")
        return False

def test_compatibility_with_kairos():
    """测试与KAIROS守护系统的兼容性"""
    print("\n3. 测试与KAIROS守护系统兼容性...")
    
    try:
        # KAIROS通常会有健康检查表或监控表
        conn = sqlite3.connect('data/shared_state/state.db')
        cursor = conn.cursor()
        
        # 检查可能的KAIROS相关表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%health%' OR name LIKE '%monitor%'")
        kairos_tables = [row[0] for row in cursor.fetchall()]
        
        if kairos_tables:
            print(f"  ✅ 发现KAIROS相关表: {kairos_tables}")
        else:
            print(f"  ⚠️ 未发现明确的KAIROS表（可能使用其他机制）")
        
        # 测试Memory V2系统健康检查与KAIROS的兼容性
        # 从memory_v2_integration导入
        from src.memory_v2_integration import MemoryV2IntegrationManager
        
        manager = MemoryV2IntegrationManager()
        health_status = manager.get_system_health()
        
        print(f"  ✅ Memory V2健康检查正常: {health_status['health_status']}")
        
        # 检查必要的指标
        required_metrics = ['validation_failure_rate_percent', 'indexing_failure_rate_percent']
        metrics_present = all(metric in health_status.get('metrics', {}) for metric in required_metrics)
        
        if metrics_present:
            print(f"  ✅ 健康指标完整")
        else:
            print(f"  ⚠️ 部分健康指标缺失")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ KAIROS兼容性测试失败: {e}")
        return False

def test_compatibility_with_workflow():
    """测试与现有工作流的兼容性"""
    print("\n4. 测试与工作流兼容性...")
    
    try:
        # 检查工作流文件是否存在
        import os
        workflow_files = [
            'outputs/工作流/SellAI_OpenClow_MemoryV2版.json',
            'outputs/工作流/SellAI_无限分身_升级版_with_shared_state.json'
        ]
        
        existing_files = []
        for file in workflow_files:
            if os.path.exists(file):
                existing_files.append(file)
        
        if existing_files:
            print(f"  ✅ 发现工作流文件: {existing_files}")
            
            # 检查其中一个文件
            with open(existing_files[0], 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # 检查必要的节点
            nodes = workflow_data.get('nodes', [])
            node_names = [node.get('data', {}).get('name', '') for node in nodes]
            
            # 检查是否包含Memory V2相关节点
            memory_v2_indicators = ['memory', 'validation', 'validator', 'index']
            memory_nodes = []
            for name in node_names:
                if any(indicator in name.lower() for indicator in memory_v2_indicators):
                    memory_nodes.append(name)
            
            if memory_nodes:
                print(f"  ✅ 发现Memory V2相关节点: {memory_nodes}")
            else:
                print(f"  ⚠️ 未发现Memory V2相关节点（可能需要更新工作流）")
            
            return True
        else:
            print(f"  ❌ 未发现工作流文件")
            return False
            
    except Exception as e:
        print(f"  ❌ 工作流兼容性测试失败: {e}")
        return False

def test_performance_and_scalability():
    """测试性能和可扩展性"""
    print("\n5. 测试性能和可扩展性...")
    
    try:
        from src.memory_v2_validator import MemoryV2Validator
        from src.memory_v2_indexer import MemoryV2Indexer
        
        validator = MemoryV2Validator()
        indexer = MemoryV2Indexer()
        
        # 测试批量操作
        start_time = time.time()
        
        test_batch = []
        for i in range(10):
            test_data = {
                'avatar_id': f'perf_test_{i}',
                'memory_type': 'intelligence_officer',
                'data': {
                    'data_source': f'Source_{i}',
                    'raw_items_count': 100 + i * 10,
                    'high_margin_items_count': 30 + i * 5,
                    'filter_reasons': ['测试性能'],
                    'success_rate': 0.8 + i * 0.02
                }
            }
            
            # 执行验证流程
            memory_id = validator.generate_memory_id(
                test_data['avatar_id'], test_data['memory_type']
            )
            
            validator.record_memory_attempt(memory_id, test_data)
            indexer.queue_memory_for_indexing(memory_id)
            
            test_batch.append(memory_id)
        
        # 等待处理
        time.sleep(10)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"  ✅ 批量处理10个记忆耗时: {elapsed:.2f}秒")
        print(f"  ✅ 平均每个记忆: {elapsed/10:.2f}秒")
        
        # 检查索引统计
        stats = indexer.get_index_stats()
        print(f"  ✅ 索引统计: {json.dumps(stats, ensure_ascii=False)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 性能测试失败: {e}")
        return False

def main():
    """主兼容性测试函数"""
    
    results = []
    
    # 运行所有兼容性测试
    results.append(("共享状态库", test_compatibility_with_shared_state()))
    results.append(("分身系统", test_compatibility_with_avatar_system()))
    results.append(("KAIROS守护", test_compatibility_with_kairos()))
    results.append(("工作流", test_compatibility_with_workflow()))
    results.append(("性能可扩展性", test_performance_and_scalability()))
    
    # 总结结果
    print("\n" + "="*60)
    print("兼容性测试结果:")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("🎉 所有兼容性测试通过！Memory V2 系统与现有架构完全兼容")
        
        # 生成兼容性报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "system": "Memory V2 分层记忆系统",
            "compatibility_tests": [
                {"test": test_name, "passed": passed} for test_name, passed in results
            ],
            "overall_status": "fully_compatible",
            "recommendations": [
                "系统已准备好集成到生产环境",
                "建议在部署前进行端到端集成测试",
                "监控Memory V2系统健康指标以确保稳定性"
            ]
        }
        
        # 保存报告
        with open('temp/memory_v2_compatibility_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 兼容性报告已保存到: temp/memory_v2_compatibility_report.json")
        
    else:
        print("⚠️  部分兼容性测试失败，需要修复后重新测试")
        
        # 生成问题报告
        issues = [
            test_name for test_name, passed in results if not passed
        ]
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "system": "Memory V2 分层记忆系统",
            "failed_tests": issues,
            "overall_status": "needs_fixes",
            "action_items": [
                "检查缺失的表或列",
                "验证系统间的数据格式兼容性",
                "测试集成接口的正确性"
            ]
        }
        
        with open('temp/memory_v2_compatibility_issues.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 问题报告已保存到: temp/memory_v2_compatibility_issues.json")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 兼容性测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)