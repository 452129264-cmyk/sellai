#!/usr/bin/env python3
"""
初始化调度系统数据库表
在现有共享状态库基础上添加调度相关表结构
"""

import sqlite3
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def init_scheduler_tables(db_path: str = "data/shared_state/state.db"):
    """
    初始化调度系统数据库表
    
    参数：
        db_path: 数据库文件路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("开始初始化调度系统数据库表...")
        
        # 1. 调度任务队列表
        print("创建调度任务队列表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_task_queue (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 2,
                estimated_duration_seconds REAL NOT NULL,
                resource_requirements TEXT NOT NULL,  -- JSON格式
                dependencies TEXT NOT NULL,           -- JSON数组
                deadline TIMESTAMP,
                status TEXT NOT NULL CHECK(status IN (
                    'pending', 'scheduled', 'running', 'completed', 'failed', 'blocked', 'timeout'
                )),
                assigned_avatar TEXT,
                created_at TIMESTAMP NOT NULL,
                scheduled_time TIMESTAMP,
                start_time TIMESTAMP,
                completion_time TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assigned_avatar) REFERENCES avatar_capability_profiles(avatar_id)
            )
        """)
        
        # 2. 资源分配表
        print("创建资源分配表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_resource_allocations (
                allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id TEXT NOT NULL,
                resource_type TEXT NOT NULL CHECK(resource_type IN (
                    'cpu', 'memory', 'network', 'storage', 'api_quota', 'db_conn'
                )),
                allocated_amount REAL NOT NULL,
                task_id TEXT NOT NULL,
                avatar_id TEXT NOT NULL,
                allocation_time TIMESTAMP NOT NULL,
                expected_release_time TIMESTAMP,
                actual_release_time TIMESTAMP,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'released', 'failed')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES scheduler_task_queue(task_id),
                FOREIGN KEY (avatar_id) REFERENCES avatar_capability_profiles(avatar_id)
            )
        """)
        
        # 3. 负载指标表
        print("创建负载指标表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_load_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                avatar_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                cpu_usage_percent REAL DEFAULT 0.0,
                memory_usage_mb REAL DEFAULT 0.0,
                active_tasks INTEGER DEFAULT 0,
                queued_tasks INTEGER DEFAULT 0,
                avg_response_time_ms REAL DEFAULT 0.0,
                task_success_rate REAL DEFAULT 0.0,
                network_latency_ms REAL DEFAULT 0.0,
                storage_usage_gb REAL DEFAULT 0.0,
                api_call_rate INTEGER DEFAULT 0,
                health_status TEXT DEFAULT 'unknown' CHECK(health_status IN (
                    'healthy', 'degraded', 'unknown', 'failed'
                )),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (avatar_id) REFERENCES avatar_capability_profiles(avatar_id)
            )
        """)
        
        # 4. 调度决策历史表
        print("创建调度决策历史表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_decision_history (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                avatar_id TEXT NOT NULL,
                decision_time TIMESTAMP NOT NULL,
                decision_type TEXT NOT NULL,  -- 'initial_assignment', 'reassignment', 'load_balance'
                match_score REAL NOT NULL,
                capability_match REAL DEFAULT 0.0,
                specialization_match REAL DEFAULT 0.0,
                region_match REAL DEFAULT 0.0,
                success_rate REAL DEFAULT 0.0,
                load_factor REAL DEFAULT 0.0,
                response_speed REAL DEFAULT 0.0,
                details TEXT,  -- JSON格式，记录详细决策数据
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES scheduler_task_queue(task_id),
                FOREIGN KEY (avatar_id) REFERENCES avatar_capability_profiles(avatar_id)
            )
        """)
        
        # 5. 资源池配置表
        print("创建资源池配置表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_resource_pool (
                pool_id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_type TEXT NOT NULL CHECK(resource_type IN (
                    'cpu', 'memory', 'network', 'storage', 'api_quota', 'db_conn'
                )),
                resource_name TEXT NOT NULL,
                total_amount REAL NOT NULL,
                available_amount REAL NOT NULL,
                unit TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(resource_type, resource_name)
            )
        """)
        
        # 6. 分身虚拟资源池表
        print("创建分身虚拟资源池表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS avatar_virtual_pools (
                pool_id INTEGER PRIMARY KEY AUTOINCREMENT,
                avatar_id TEXT NOT NULL,
                resource_type TEXT NOT NULL CHECK(resource_type IN (
                    'cpu', 'memory', 'network', 'storage', 'api_quota', 'db_conn'
                )),
                allocated_amount REAL NOT NULL,
                used_amount REAL DEFAULT 0.0,
                max_amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (avatar_id) REFERENCES avatar_capability_profiles(avatar_id),
                UNIQUE(avatar_id, resource_type)
            )
        """)
        
        # 创建索引
        print("创建索引...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_queue_status ON scheduler_task_queue(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_queue_priority ON scheduler_task_queue(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_queue_avatar ON scheduler_task_queue(assigned_avatar)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_alloc_task ON scheduler_resource_allocations(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_alloc_avatar ON scheduler_resource_allocations(avatar_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_load_metrics_avatar ON scheduler_load_metrics(avatar_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_load_metrics_time ON scheduler_load_metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decision_history_task ON scheduler_decision_history(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decision_history_time ON scheduler_decision_history(decision_time)")
        
        # 初始化资源池配置
        print("初始化默认资源池配置...")
        resource_configs = [
            # (resource_type, resource_name, total_amount, unit)
            ('cpu', 'cpu_cores', 64.0, 'cores'),
            ('memory', 'memory_gb', 256.0, 'GB'),
            ('network', 'bandwidth_mbps', 10000.0, 'Mbps'),
            ('storage', 'storage_gb', 10240.0, 'GB'),
            ('api_quota', 'requests_per_minute', 10000.0, 'requests/min'),
            ('db_conn', 'database_connections', 200.0, 'connections')
        ]
        
        for config in resource_configs:
            cursor.execute("""
                INSERT OR REPLACE INTO scheduler_resource_pool 
                (resource_type, resource_name, total_amount, available_amount, unit)
                VALUES (?, ?, ?, ?, ?)
            """, (config[0], config[1], config[2], config[2], config[3]))
        
        conn.commit()
        print("调度系统数据库表初始化完成！")
        
        # 显示创建的表
        print("\n已创建的表：")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'scheduler_%'")
        for table in cursor.fetchall():
            print(f"  - {table[0]}")
            
        print("\n索引：")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        for idx in cursor.fetchall():
            print(f"  - {idx[0]}")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """主函数"""
    try:
        # 检查数据库文件是否存在
        if not os.path.exists("data/shared_state/state.db"):
            print("警告：共享状态库不存在，将创建新数据库...")
            # 确保目录存在
            os.makedirs("data/shared_state", exist_ok=True)
        
        init_scheduler_tables()
        
        print("\n初始化成功！")
        print("数据库路径: data/shared_state/state.db")
        
    except Exception as e:
        print(f"初始化过程出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()