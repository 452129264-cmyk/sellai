#!/usr/bin/env python3
"""
任务状态检查脚本
检查当前所有任务状态，识别异常任务
"""

import os
import sys
from datetime import datetime, timedelta
import sqlite3

def check_task_status():
    """检查任务状态"""
    print("=== SellAI任务状态检查 ===")
    print(f"检查时间: {datetime.now()}")
    
    # 数据库路径
    db_path = "data/shared_state/state.db"
    
    if not os.path.exists(db_path):
        print("⚠️  共享状态数据库不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查各表状态
        print("\n1. 数据库表状态:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print(f"   表数量: {len(tables)}")
        
        # 检查task_assignments表
        print("\n2. 任务分配表:")
        cursor.execute("SELECT * FROM task_assignments ORDER BY id")
        tasks = cursor.fetchall()
        
        if not tasks:
            print("   无任务记录")
        else:
            print(f"   总任务数: {len(tasks)}")
            
            for task in tasks:
                task_id, hash_val, avatar_id, created_at, started_at, priority, status, completed_at, result = task
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if created_at else None
                
                # 判断是否异常（创建时间超过30分钟且未完成）
                is_abnormal = False
                if created_dt and status not in ['completed', 'failed']:
                    age = datetime.now(created_dt.tzinfo) - created_dt if created_dt.tzinfo else datetime.now() - created_dt
                    if age > timedelta(minutes=30):
                        is_abnormal = True
                
                status_symbol = "✅" if status == 'completed' else "⚠️ " if is_abnormal else "🔄"
                print(f"   {status_symbol} 任务{task_id}: {status} (优先级: {priority})")
                if is_abnormal:
                    print(f"       ⚠️  异常: 创建时间超过30分钟未完成")
        
        # 检查sync_status表
        print("\n3. 同步状态表:")
        cursor.execute("SELECT COUNT(*) FROM sync_status")
        sync_count = cursor.fetchone()[0]
        print(f"   同步记录数: {sync_count}")
        
        # 检查health_check_records表
        print("\n4. 健康检查记录:")
        cursor.execute("SELECT COUNT(*) FROM health_check_records")
        health_count = cursor.fetchone()[0]
        print(f"   健康检查记录数: {health_count}")
        
        if health_count > 0:
            cursor.execute("SELECT check_time, component, status FROM health_check_records ORDER BY check_time DESC LIMIT 5")
            recent_checks = cursor.fetchall()
            print("   最近5条记录:")
            for check in recent_checks:
                check_time, component, status = check
                status_icon = "✅" if status == 'healthy' else "❌" if status == 'unhealthy' else "⚠️ "
                print(f"     {status_icon} {check_time}: {component} - {status}")
        
        conn.close()
        
        print("\n=== 检查完成 ===")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_task_status()