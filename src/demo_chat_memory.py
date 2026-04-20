#!/usr/bin/env python3
"""
聊天记录永久记忆功能演示
"""

import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def demo_basic_functionality():
    """演示基本功能"""
    print("聊天记录永久记忆功能演示")
    print("=" * 70)
    
    print("1. 创建永久记忆管理器...")
    try:
        from src.chat_permanent_memory import ChatPermanentMemory
        
        cpm = ChatPermanentMemory(
            db_path="data/shared_state/state.db",
            notebook_lm_api_key=os.getenv("NOTEBOOKLM_API_KEY", "demo_key")
        )
        
        print("   ✓ 永久记忆管理器创建成功")
        
    except Exception as e:
        print(f"   ✗ 创建失败: {e}")
        return False
    
    print("\n2. 测试加密功能...")
    try:
        test_content = "这是一条演示加密的聊天消息"
        test_metadata = {"demo": True, "timestamp": datetime.now().isoformat()}
        
        encrypted, updated_metadata = cpm.encrypt_chat_content(test_content, test_metadata)
        
        print(f"   原始内容: '{test_content}'")
        print(f"   加密内容: '{encrypted[:50]}...'")
        print(f"   元数据: {json.dumps(updated_metadata, ensure_ascii=False)}")
        print("   ✓ 加密功能正常")
        
    except Exception as e:
        print(f"   ✗ 加密测试失败: {e}")
    
    print("\n3. 检查知识库状态...")
    try:
        chat_kb_id, rel_kb_id = cpm.ensure_knowledge_bases()
        
        if chat_kb_id:
            print(f"   聊天记录知识库ID: {chat_kb_id[:20]}...")
        else:
            print("   ⚠ 聊天记录知识库未创建")
            
        if rel_kb_id:
            print(f"   社交关系知识库ID: {rel_kb_id[:20]}...")
        else:
            print("   ⚠ 社交关系知识库未创建")
        
        print("   ✓ 知识库检查完成")
        
    except Exception as e:
        print(f"   ✗ 知识库检查失败: {e}")
    
    print("\n4. 获取同步统计...")
    try:
        stats = cpm.get_sync_stats()
        
        print(f"   同步状态:")
        print(f"     已同步消息: {stats.get('total_synced', 0)}条")
        print(f"     待同步消息: {stats.get('total_pending', 0)}条")
        print(f"     失败消息: {stats.get('total_failed', 0)}条")
        
        # 检查数据库中实际有多少聊天消息
        import sqlite3
        conn = sqlite3.connect("data/shared_state/state.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chat_messages")
        db_message_count = cursor.fetchone()[0]
        conn.close()
        
        print(f"     数据库中消息总数: {db_message_count}条")
        print("   ✓ 同步统计获取成功")
        
    except Exception as e:
        print(f"   ✗ 同步统计失败: {e}")
    
    print("\n5. 测试桥接功能...")
    try:
        from src.chat_memory_bridge import ChatMemoryBridge
        
        bridge = ChatMemoryBridge()
        health = bridge.health_check()
        
        print(f"   桥接系统健康状态:")
        print(f"     基础管理器: {'可用' if health['base_manager_available'] else '不可用'}")
        print(f"     记忆系统: {'可用' if health['memory_system_available'] else '不可用'}")
        print(f"     后台同步: {'运行中' if health['sync_active'] else '未运行'}")
        print(f"     同步队列: {health['queue_size']}条")
        
        print("   ✓ 桥接功能正常")
        
    except Exception as e:
        print(f"   ⚠ 桥接测试警告: {e}")
    
    return True

def demo_api_endpoints():
    """演示API端点（如果服务器运行中）"""
    print("\n6. 演示API端点...")
    
    try:
        import requests
        
        # 尝试连接健康检查端点
        base_url = "http://localhost:5000"
        
        try:
            response = requests.get(f"{base_url}/api/chat-memory/health", timeout=2)
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✓ API服务器运行中")
                print(f"     状态: {health_data.get('status', 'unknown')}")
                print(f"     记忆桥接: {health_data.get('memory_bridge_available', False)}")
                
                # 演示搜索功能
                search_payload = {
                    "query": "测试",
                    "limit": 5
                }
                
                try:
                    search_response = requests.post(
                        f"{base_url}/api/chat-memory/messages/search",
                        json=search_payload,
                        timeout=3
                    )
                    
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        print(f"   ✓ 搜索功能正常")
                        print(f"     搜索结果: {search_data.get('count', 0)}条")
                    else:
                        print(f"   ⚠ 搜索端点返回 {search_response.status_code}")
                        
                except requests.exceptions.RequestException:
                    print(f"   ⚠ 搜索端点不可达")
                
            else:
                print(f"   ⚠ API服务器返回 {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ⚠ API服务器未运行，请使用以下命令启动:")
            print(f"      python src/chat_server_with_memory.py run")
        except requests.exceptions.Timeout:
            print(f"   ⚠ API服务器连接超时")
            
    except ImportError:
        print(f"   ⚠ requests模块未安装，API演示跳过")
    
    return True

def main():
    print("SellAI聊天记录永久记忆集成演示")
    print("=" * 70)
    
    # 演示基本功能
    basic_ok = demo_basic_functionality()
    
    # 演示API端点
    api_ok = demo_api_endpoints()
    
    print("\n" + "=" * 70)
    print("演示总结:")
    
    if basic_ok:
        print("✓ 基本功能演示成功")
    else:
        print("✗ 基本功能演示失败")
    
    print("\n文件清单:")
    files = [
        "src/chat_permanent_memory.py",
        "src/chat_memory_bridge.py", 
        "src/chat_memory_integrator.py",
        "src/chat_server_with_memory.py",
        "configs/chat_memory_config.json",
        "docs/聊天记录永久记忆集成说明.md",
        "scripts/install_chat_memory_integration.sh"
    ]
    
    for file_path in files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / 1024
            print(f"  ✓ {file_path} ({file_size:.1f} KB)")
        else:
            print(f"  ✗ {file_path} (缺失)")
    
    print("\n使用说明:")
    print("  1. 配置Notebook LM API密钥:")
    print("     export NOTEBOOKLM_API_KEY=your_api_key_here")
    print("     或编辑 configs/chat_memory_config.json")
    print("")
    print("  2. 安装依赖（可选，用于完整功能）:")
    print("     pip install flask flask-cors flask-socketio")
    print("")
    print("  3. 启动增强聊天服务器:")
    print("     python src/chat_server_with_memory.py run")
    print("")
    print("  4. 验证功能:")
    print("     curl http://localhost:5000/api/chat-memory/health")
    print("")
    print("注意: 完整功能需要有效的Notebook LM企业版API密钥")
    
    return basic_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)