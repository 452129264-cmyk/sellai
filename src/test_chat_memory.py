#!/usr/bin/env python3
"""
测试聊天记录永久记忆集成
"""

import os
import sys
import sqlite3
import json
from datetime import datetime

# 添加src目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_database_connection():
    """测试数据库连接和表结构"""
    db_path = "data/shared_state/state.db"
    
    print(f"测试数据库连接: {db_path}")
    
    if not os.path.exists(db_path):
        print("错误: 数据库文件不存在")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查聊天相关表
        tables_to_check = [
            'chat_rooms',
            'room_members', 
            'chat_messages',
            'message_status',
            'user_avatar_relationships',
            'ai_ai_communications'
        ]
        
        print("\n检查表结构:")
        for table in tables_to_check:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            exists = cursor.fetchone()
            if exists:
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"  {table}: 存在 ({len(columns)} 列)")
                # for col in columns:
                #     print(f"    - {col[1]} ({col[2]})")
            else:
                print(f"  {table}: 不存在")
        
        # 检查现有聊天记录
        cursor.execute("SELECT COUNT(*) FROM chat_messages")
        message_count = cursor.fetchone()[0]
        print(f"\n聊天消息总数: {message_count}")
        
        # 检查最近的消息
        if message_count > 0:
            cursor.execute("SELECT * FROM chat_messages ORDER BY timestamp DESC LIMIT 3")
            recent_messages = cursor.fetchall()
            print(f"最近3条消息:")
            for msg in recent_messages:
                print(f"  ID: {msg[0]}, 发送者: {msg[2]}, 时间: {msg[5]}, 类型: {msg[4]}")
        
        # 检查社交关系
        cursor.execute("SELECT COUNT(*) FROM user_avatar_relationships")
        relationship_count = cursor.fetchone()[0]
        print(f"\n用户-AI社交关系总数: {relationship_count}")
        
        cursor.execute("SELECT COUNT(*) FROM ai_ai_communications")
        communication_count = cursor.fetchone()[0]
        print(f"AI-AI通信记录总数: {communication_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"数据库连接测试失败: {e}")
        return False

def test_security_module():
    """测试安全模块"""
    print("\n测试安全模块...")
    
    try:
        from src.multi_layer_security import MultiLayerSecurity
        
        security = MultiLayerSecurity("data/shared_state/state.db")
        print("  多层次安全防护系统初始化成功")
        
        # 测试加密功能
        test_data = "这是一条测试聊天消息"
        
        if hasattr(security, 'data_layer') and hasattr(security.data_layer, 'encrypt_sensitive_data'):
            encrypted = security.data_layer.encrypt_sensitive_data(test_data)
            print(f"  加密测试: '{test_data}' -> '{encrypted[:50]}...'")
            return True
        else:
            print("  警告: 数据层加密功能不可用")
            return False
            
    except ImportError as e:
        print(f"  错误: 无法导入安全模块 - {e}")
        return False
    except Exception as e:
        print(f"  错误: 安全模块测试失败 - {e}")
        return False

def test_notebook_lm_integration():
    """测试Notebook LM集成模块"""
    print("\n测试Notebook LM集成模块...")
    
    try:
        from src.notebook_lm_integration import NotebookLMIntegration, KnowledgeDocument, ContentType, SourceType
        
        print("  Notebook LM集成模块导入成功")
        
        # 测试创建知识文档
        doc = KnowledgeDocument(
            title="测试聊天记录",
            content="测试内容",
            content_type=ContentType.MARKDOWN,
            source_type=SourceType.TASK_RESULT,
            tags=["test", "chat"]
        )
        
        print(f"  测试知识文档创建: {doc.title}")
        print(f"  内容类型: {doc.content_type.value}")
        print(f"  标签: {doc.tags}")
        
        return True
        
    except ImportError as e:
        print(f"  错误: 无法导入Notebook LM模块 - {e}")
        return False
    except Exception as e:
        print(f"  错误: Notebook LM模块测试失败 - {e}")
        return False

def main():
    print("聊天记录永久记忆集成测试")
    print("=" * 60)
    
    # 测试数据库连接
    db_ok = test_database_connection()
    
    # 测试安全模块
    security_ok = test_security_module()
    
    # 测试Notebook LM集成
    notebook_ok = test_notebook_lm_integration()
    
    print("\n" + "=" * 60)
    print("测试总结:")
    print(f"  数据库连接: {'✓ 成功' if db_ok else '✗ 失败'}")
    print(f"  安全模块: {'✓ 成功' if security_ok else '✗ 失败'}")
    print(f"  Notebook LM集成: {'✓ 成功' if notebook_ok else '✗ 失败'}")
    
    if db_ok and security_ok and notebook_ok:
        print("\n所有测试通过，可以继续集成开发")
        return True
    else:
        print("\n部分测试失败，需要先解决问题")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)