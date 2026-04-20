#!/usr/bin/env python3
"""
创建达人合作相关表的脚本
执行达人洽谈军团DDL语句
"""

import sqlite3
import sys
import os

def main():
    # 数据库路径
    db_path = "data/shared_state/state.db"
    ddl_file = "docs/达人洽谈军团_DDL.sql"
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    if not os.path.exists(ddl_file):
        print(f"错误: DDL文件不存在: {ddl_file}")
        sys.exit(1)
    
    # 读取DDL文件
    with open(ddl_file, 'r', encoding='utf-8') as f:
        ddl_content = f.read()
    
    # 连接到数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("开始创建达人合作相关表...")
    
    # 分割SQL语句并执行
    statements = ddl_content.split(';')
    executed_count = 0
    
    for stmt in statements:
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            try:
                cursor.execute(stmt)
                executed_count += 1
                print(f"✓ 执行: {stmt[:80]}...")
            except sqlite3.OperationalError as e:
                if "already exists" in str(e):
                    print(f"⚠ 表已存在: {stmt[:80]}...")
                else:
                    print(f"✗ 执行失败: {e}")
    
    conn.commit()
    
    # 验证表是否创建成功
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE 'influencer_%'
        ORDER BY name
    """)
    
    created_tables = cursor.fetchall()
    
    print(f"\n=== 创建完成 ===")
    print(f"执行的SQL语句数: {executed_count}")
    print(f"创建的达人合作相关表:")
    
    for table in created_tables:
        print(f"  - {table[0]}")
    
    # 显示表结构
    for table in created_tables:
        print(f"\n表结构: {table[0]}")
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            pk_marker = " (PK)" if pk else ""
            print(f"  {col_id}. {col_name:<20} {col_type:<15} {pk_marker}")
    
    conn.close()
    
    if len(created_tables) >= 3:
        print(f"\n✅ 达人合作表创建成功")
        return True
    else:
        print(f"\n❌ 达人合作表创建不完整")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)