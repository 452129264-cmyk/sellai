#!/usr/bin/env python3
"""
记忆隔离系统测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_isolation_core import (
    MemoryIsolationRecord, MemorySpace, SharingChannel, AccessLog,
    AccessPermission, IsolationLevel, OperationType, ResultStatus,
    SharingContentType, PermissionLevel,
    memory_isolation_manager, sharing_channel_manager, access_audit_logger
)

def test_basic_isolation():
    """测试基本隔离功能"""
    print("测试基本隔离功能...")
    
    # 创建测试记忆空间
    test_space = MemorySpace(
        memory_space_id="test_space_1",
        space_name="测试空间",
        owner_user_id="test_user_1",
        space_type="personal",
        description="测试用记忆空间"
    )
    
    # 创建隔离记录
    isolation_record = MemoryIsolationRecord(
        user_id="test_user_1",
        avatar_id="test_avatar_1",
        memory_space_id="test_space_1",
        access_permission=AccessPermission.READ_WRITE,
        isolation_level=IsolationLevel.STRICT
    )
    
    # 验证访问权限
    allowed, error = memory_isolation_manager.verify_access(
        avatar_id="test_avatar_1",
        memory_space_id="test_space_1",
        operation_type=OperationType.READ
    )
    
    print(f"  读取权限验证: allowed={allowed}, error={error}")
    
    allowed, error = memory_isolation_manager.verify_access(
        avatar_id="test_avatar_1",
        memory_space_id="test_space_1",
        operation_type=OperationType.WRITE
    )
    
    print(f"  写入权限验证: allowed={allowed}, error={error}")
    
    # 测试无权限访问
    allowed, error = memory_isolation_manager.verify_access(
        avatar_id="test_avatar_2",  # 未授权的分身
        memory_space_id="test_space_1",
        operation_type=OperationType.READ
    )
    
    print(f"  未授权分身访问: allowed={allowed}, error={error}")
    
    return True

def test_sharing_channel():
    """测试共享通道"""
    print("测试共享通道...")
    
    # 创建共享通道
    channel = SharingChannel(
        channel_id="test_channel_1",
        source_avatar_id="test_avatar_1",
        target_avatar_id="test_avatar_2",
        sharing_content_type=SharingContentType.MEMORY_FRAGMENT,
        permission_level=PermissionLevel.READ_ONLY,
        shared_data_hash="abc123",
        created_by="test_user_1"
    )
    
    # 访问共享内容
    content = sharing_channel_manager.access_shared_content(
        channel_id="test_channel_1",
        avatar_id="test_avatar_2"
    )
    
    print(f"  授权分身访问结果: {content is not None}")
    
    # 测试未授权访问
    content = sharing_channel_manager.access_shared_content(
        channel_id="test_channel_1",
        avatar_id="test_avatar_3"  # 未授权的分身
    )
    
    print(f"  未授权分身访问结果: {content is None}")
    
    return True

def test_access_logging():
    """测试访问日志"""
    print("测试访问日志...")
    
    # 创建访问日志
    log = AccessLog(
        avatar_id="test_avatar_1",
        user_id="test_user_1",
        operation_type=OperationType.READ,
        target_memory_space="test_space_1",
        result_status=ResultStatus.SUCCESS,
        request_id="test_request_1"
    )
    
    # 记录日志
    success = access_audit_logger.log_access(log)
    print(f"  日志记录结果: {success}")
    
    # 查询日志
    logs = access_audit_logger.get_access_logs(avatar_id="test_avatar_1", limit=5)
    print(f"  查询到的日志数量: {len(logs)}")
    
    return True

def test_integration_with_scheduler():
    """测试与调度器集成"""
    print("测试与调度器集成...")
    
    # 模拟调度器任务分配时的权限检查
    test_cases = [
        {
            "avatar_id": "test_avatar_1",
            "memory_space_id": "test_space_1",
            "operation": OperationType.READ,
            "expected": True
        },
        {
            "avatar_id": "test_avatar_2",
            "memory_space_id": "test_space_1",
            "operation": OperationType.READ,
            "expected": False
        },
        {
            "avatar_id": "test_avatar_1",
            "memory_space_id": "test_space_1",
            "operation": OperationType.DELETE,
            "expected": False  # READ_WRITE权限不允许删除
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        allowed, error = memory_isolation_manager.verify_access(
            avatar_id=test_case["avatar_id"],
            memory_space_id=test_case["memory_space_id"],
            operation_type=test_case["operation"]
        )
        
        passed = allowed == test_case["expected"]
        print(f"  测试用例 {i+1}: {'通过' if passed else '失败'} (expected={test_case['expected']}, actual={allowed}, error={error})")
    
    return True

def main():
    """主测试函数"""
    print("开始记忆隔离系统测试...\n")
    
    tests = [
        ("基本隔离功能", test_basic_isolation),
        ("共享通道", test_sharing_channel),
        ("访问日志", test_access_logging),
        ("调度器集成", test_integration_with_scheduler)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n▶ 测试: {test_name}")
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  测试异常: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*50)
    print("测试结果汇总:")
    print("="*50)
    
    all_passed = True
    for test_name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {test_name:20} {status}")
        if not success:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("所有测试通过！")
    else:
        print("部分测试失败！")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)