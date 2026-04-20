#!/usr/bin/env python3
# Memory V2 功能测试脚本

import sys
sys.path.append('/app/data/files')

from src.memory_v2_validator import MemoryV2Validator
from src.memory_v2_indexer import MemoryV2Indexer

print("=== Memory V2 功能测试 ===")

# 测试验证器
print("\n1. 测试验证器...")
validator = MemoryV2Validator()

test_data = {
    "avatar_id": "test_avatar_001",
    "memory_type": "intelligence_officer",
    "data": {
        "data_source": "TikTok",
        "raw_items_count": 100,
        "high_margin_items_count": 35
    }
}

valid, error = validator.pre_write_validation(test_data)
print(f"写入前校验: {'通过' if valid else '失败'} - {error}")

memory_id = validator.generate_memory_id(test_data['avatar_id'], test_data['memory_type'])
print(f"生成的记忆ID: {memory_id}")

# 测试索引器
print("\n2. 测试索引器...")
indexer = MemoryV2Indexer()

stats = indexer.get_index_stats()
print(f"索引统计: {stats}")

print("\n测试完成！")
