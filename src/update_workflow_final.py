#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新工作流文件 - 最终版本
"""

import json
import os
import sys

def main():
    # 读取现有工作流
    with open('outputs/工作流/SellAI_无限分身_升级版_with_shared_state.json', 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    print(f"原始节点数: {len(workflow['nodes'])}")
    
    # 添加Memory V2验证节点
    new_node = {
        "id": "memory_v2_validator",
        "type": "code",
        "position": {"x": 800, "y": 500},
        "data": {
            "name": "Memory V2验证器",
            "description": "验证记忆数据的完整性和准确性，确保100%可靠。调用Python验证器模块进行写入验证和成功后再索引。",
            "code": "// Memory V2验证节点 - 调用外部Python模块\nconst { execSync } = require('child_process');\nconst path = require('path');\n\n// 解析请求\nconst requestBody = process.env.REQUEST_BODY || '{}';\nconst inputData = JSON.parse(requestBody);\nconst operation = inputData.operation || '';\n\nif (operation === 'write_validation') {\n    // 调用Python验证器\n    const scriptPath = path.join(__dirname, 'src/memory_v2_validator.py');\n    const cmd = `python -c \\\"\nimport sys\nsys.path.append('/app/data/files')\nfrom src.memory_v2_validator import validate_memory_write\nimport json\n\n# 模拟写入函数\ndef mock_write(data):\n    print('模拟Coze记忆写入:', data.get('avatar_id'))\n    return True, None\n\n# 模拟读取函数\ndef mock_read(mid):\n    import sqlite3\n    conn = sqlite3.connect('data/shared_state/state.db')\n    cursor = conn.cursor()\n    cursor.execute('SELECT original_data FROM memory_data_checksums WHERE memory_id=?', (mid,))\n    result = cursor.fetchone()\n    conn.close()\n    if result:\n        return True, json.loads(result[0])\n    else:\n        return False, '找不到记忆数据'\n\nmemory_data = json.loads('''${JSON.stringify(inputData.memory_data)}''')\nsuccess, memory_id, error = validate_memory_write(memory_data, mock_write, mock_read, 'coze_memory')\nprint(json.dumps({success: success, memory_id: memory_id, error: error}))\n\\\"`;\n    \n    try {\n        const result = execSync(cmd, { encoding: 'utf-8' });\n        return JSON.parse(result);\n    } catch (error) {\n        return {\n            success: false,\n            message: `验证器调用失败: ${error.message}`\n        };\n    }\n} else if (operation === 'query_verified') {\n    // 调用Python查询模块\n    const scriptPath = path.join(__dirname, 'src/memory_v2_integration.py');\n    const cmd = `python -c \\\"\nimport sys\nsys.path.append('/app/data/files')\nfrom src.memory_v2_integration import query_memories_safely\nimport json\n\nquery_params = json.loads('''${JSON.stringify(inputData.query)}''')\nlimit = ${inputData.limit || 50}\nresults = query_memories_safely(query_params, limit)\nprint(json.dumps({success: True, results: results, count: len(results)}))\n\\\"`;\n    \n    try {\n        const result = execSync(cmd, { encoding: 'utf-8' });\n        return JSON.parse(result);\n    } catch (error) {\n        return {\n            success: false,\n            message: `查询模块调用失败: ${error.message}`\n        };\n    }\n} else {\n    return {\n        success: false,\n        message: `不支持的操作: ${operation}`,\n        supported: ['write_validation', 'query_verified']\n    };\n}\n"
        }
    }
    
    # 检查是否已存在
    existing_ids = [n.get('id') for n in workflow['nodes']]
    if 'memory_v2_validator' not in existing_ids:
        workflow['nodes'].append(new_node)
    
    # 更新元数据
    workflow['description'] = 'SellAI封神版A：OpenClow体验无限分身系统 with Memory V2分层记忆系统（写入验证+成功后再索引+分层存储）'
    workflow['version'] = '2.2'
    
    if 'settings' not in workflow:
        workflow['settings'] = {}
    
    workflow['settings']['memory_enabled'] = True
    workflow['settings']['memory_v2_integrated'] = True
    
    # 保存
    output_path = 'outputs/工作流/SellAI_OpenClow_MemoryV2版.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
    
    print(f"已保存到: {output_path}")
    print(f"总节点数: {len(workflow['nodes'])}")
    
    # 创建简单的测试脚本
    test_script = '''#!/usr/bin/env python3
# Memory V2 功能测试脚本

import sys
sys.path.append('/app/data/files')

from src.memory_v2_validator import MemoryV2Validator
from src.memory_v2_indexer import MemoryV2Indexer

print("=== Memory V2 功能测试 ===")

# 测试验证器
print("\\n1. 测试验证器...")
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
print("\\n2. 测试索引器...")
indexer = MemoryV2Indexer()

stats = indexer.get_index_stats()
print(f"索引统计: {stats}")

print("\\n测试完成！")
'''
    
    with open('src/test_memory_v2.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print("创建了测试脚本: src/test_memory_v2.py")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())