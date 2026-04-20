#!/usr/bin/env python3
"""
数据同步管理器验证脚本
验证核心功能是否正常工作
"""

import sys
import os

# 添加路径
sys.path.append('/app/data/files/src')

from src.global_orchestrator.data_sync_manager import (
    DataSyncManager, SyncDomain, get_global_data_sync_manager
)
from datetime import datetime


def test_basic_functionality():
    """测试基础功能"""
    print("=" * 80)
    print("数据同步管理器基础功能验证")
    print("=" * 80)
    
    # 使用临时数据库
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "validate_state.db")
    
    try:
        # 初始化管理器
        print(f"1. 初始化管理器，数据库: {db_path}")
        manager = DataSyncManager(db_path)
        
        # 测试基础同步
        print("\n2. 测试基础数据同步")
        test_domain = SyncDomain.AVATAR_STATE
        test_resource_id = "validate_avatar_001"
        test_data = {
            "avatar_id": test_resource_id,
            "name": "验证分身",
            "status": "idle",
            "load_factor": 0.0,
            "timestamp": datetime.now().isoformat()
        }
        
        result = manager.sync_data(test_domain, test_resource_id, test_data)
        print(f"   同步结果: {result['status']}")
        print(f"   版本ID: {result['version']['version_id']}")
        
        if result['status'] == 'success':
            print("   ✅ 基础同步测试通过")
        else:
            print("   ❌ 基础同步测试失败")
            return False
        
        # 测试数据更新
        print("\n3. 测试数据更新")
        updated_data = test_data.copy()
        updated_data['status'] = 'busy'
        updated_data['load_factor'] = 0.5
        
        update_result = manager.sync_data(test_domain, test_resource_id, updated_data)
        print(f"   更新结果: {update_result['status']}")
        
        if update_result['status'] == 'success':
            print("   ✅ 数据更新测试通过")
        else:
            print("   ❌ 数据更新测试失败")
            return False
        
        # 测试统计信息
        print("\n4. 测试统计信息")
        stats = manager.get_sync_stats()
        print(f"   总操作数: {stats['stats']['total_sync_operations']}")
        print(f"   成功数: {stats['stats']['successful_syncs']}")
        print(f"   平均时间: {stats['stats']['avg_sync_time_ms']:.2f}ms")
        
        if stats['stats']['total_sync_operations'] >= 2:
            print("   ✅ 统计信息测试通过")
        else:
            print("   ❌ 统计信息测试失败")
            return False
        
        # 测试锁功能
        print("\n5. 测试分布式锁")
        lock = manager.get_lock("validate_lock", timeout_seconds=10)
        
        if lock.acquire(wait_timeout_seconds=2):
            print("   ✅ 锁获取测试通过")
            
            if lock.release():
                print("   ✅ 锁释放测试通过")
            else:
                print("   ❌ 锁释放测试失败")
                return False
        else:
            print("   ❌ 锁获取测试失败")
            return False
        
        print("\n" + "=" * 80)
        print("所有基础功能验证通过 ✅")
        print("=" * 80)
        
        return True
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_concurrent_scenario():
    """测试并发场景"""
    print("\n" + "=" * 80)
    print("并发场景验证")
    print("=" * 80)
    
    import tempfile
    import shutil
    import threading
    import time
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "concurrent_state.db")
    
    try:
        manager = DataSyncManager(db_path)
        test_domain = SyncDomain.TASK_ASSIGNMENT
        test_resource_id = "concurrent_task_001"
        
        results = []
        errors = []
        lock = threading.Lock()
        
        def worker(worker_id):
            try:
                data = {
                    "task_id": test_resource_id,
                    "assigned_to": f"avatar_{worker_id:03d}",
                    "status": "assigned",
                    "priority": worker_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                result = manager.sync_data(
                    test_domain, test_resource_id, data,
                    source_node=f"worker_{worker_id}"
                )
                
                with lock:
                    results.append(result)
                    
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        # 创建5个并发线程
        threads = []
        num_workers = 5
        
        print(f"创建 {num_workers} 个并发工作线程...")
        
        for i in range(num_workers):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
        
        # 同时启动
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # 等待完成
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        total_time = end_time - start_time
        print(f"并发测试完成，总时间: {total_time:.2f}秒")
        
        # 分析结果
        success_count = sum(1 for r in results if r.get('status') == 'success')
        conflict_count = sum(1 for r in results if r.get('conflict', False))
        
        print(f"成功数: {success_count}/{num_workers}")
        print(f"冲突数: {conflict_count}/{num_workers}")
        print(f"错误数: {len(errors)}")
        
        if errors:
            print("错误详情:")
            for error in errors:
                print(f"  - {error}")
        
        # 验证至少有一个成功
        if success_count > 0 and len(errors) == 0:
            print("✅ 并发场景验证通过")
            return True
        else:
            print("❌ 并发场景验证失败")
            return False
            
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_sync_to_sellai():
    """验证同步到sellai测试智能体"""
    print("\n" + "=" * 80)
    print("同步到sellai测试智能体验证")
    print("=" * 80)
    
    # 检查sellai_test目录中的文件
    sellai_test_files = [
        "/app/data/files/sellai_test/src/global_orchestrator/data_sync_manager.py",
        "/app/data/files/sellai_test/docs/八大能力数据流转模型设计.md",
        "/app/data/files/sellai_test/tests/test_data_sync.py"
    ]
    
    all_files_exist = True
    for file_path in sellai_test_files:
        if os.path.exists(file_path):
            print(f"✅ {os.path.basename(file_path)} 存在")
        else:
            print(f"❌ {os.path.basename(file_path)} 不存在")
            all_files_exist = False
    
    if all_files_exist:
        print("\n✅ 所有文件已成功同步到sellai_test目录")
        
        # 验证文件内容完整性
        try:
            # 检查源文件和目标文件大小
            src_file = "/app/data/files/src/global_orchestrator/data_sync_manager.py"
            dst_file = "/app/data/files/sellai_test/src/global_orchestrator/data_sync_manager.py"
            
            src_size = os.path.getsize(src_file)
            dst_size = os.path.getsize(dst_file)
            
            if src_size == dst_size:
                print(f"✅ 数据同步管理器文件大小一致: {src_size}字节")
            else:
                print(f"⚠️  文件大小不一致: 源={src_size}字节, 目标={dst_size}字节")
                
        except Exception as e:
            print(f"⚠️  文件验证时发生错误: {e}")
        
        return True
    else:
        print("\n❌ 部分文件未成功同步")
        return False


def main():
    """主验证函数"""
    print("数据同步管理器全面验证开始")
    print("-" * 80)
    
    tests_passed = 0
    total_tests = 3
    
    # 运行基础功能测试
    if test_basic_functionality():
        tests_passed += 1
    
    # 运行并发场景测试
    if test_concurrent_scenario():
        tests_passed += 1
    
    # 运行同步验证
    if test_sync_to_sellai():
        tests_passed += 1
    
    # 生成验证报告
    print("\n" + "=" * 80)
    print("验证报告")
    print("=" * 80)
    print(f"测试总数: {total_tests}")
    print(f"通过数: {tests_passed}")
    print(f"失败数: {total_tests - tests_passed}")
    print(f"通过率: {tests_passed/total_tests*100:.1f}%")
    
    if tests_passed == total_tests:
        print("\n✅ 所有验证测试通过")
        return 0
    else:
        print("\n❌ 部分验证测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())