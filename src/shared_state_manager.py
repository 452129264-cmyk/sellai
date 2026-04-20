"""
共享状态库管理器
用于管理无限AI分身架构中的共享状态库，包括已处理商机去重、任务分配历史、
分身能力画像、成本消耗记录等功能。
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
import hashlib

class SharedStateManager:
    """共享状态库管理类"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化共享状态管理器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self._ensure_tables()
    
    def connect(self):
        """连接到数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _ensure_tables(self):
        """确保四张核心表存在"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # 1. 已处理商机去重表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_opportunities (
                opportunity_hash TEXT PRIMARY KEY,
                source_platform TEXT NOT NULL,
                original_id TEXT,
                title TEXT,
                first_discovered TIMESTAMP NOT NULL,
                last_checked TIMESTAMP NOT NULL,
                processed_by_avatars TEXT,  -- JSON数组记录处理过的分身ID
                status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'rejected'))
            )
        """)
        
        # 2. 任务分配历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_assignments (
                assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_hash TEXT NOT NULL,
                assigned_avatar TEXT NOT NULL,
                assignment_time TIMESTAMP NOT NULL,
                deadline TIMESTAMP,
                priority INTEGER DEFAULT 1,
                completion_status TEXT CHECK(completion_status IN ('pending', 'in_progress', 'completed', 'failed')),
                completion_time TIMESTAMP,
                result_summary TEXT,
                FOREIGN KEY (opportunity_hash) REFERENCES processed_opportunities(opportunity_hash)
            )
        """)
        
        # 3. 分身能力画像表 (根据架构文档，表名应为avatar_capability_profiles)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS avatar_capability_profiles (
                avatar_id TEXT PRIMARY KEY,
                avatar_name TEXT NOT NULL,
                template_id TEXT,
                capability_scores TEXT NOT NULL,  -- JSON格式：{"data_crawling": 0.85, "financial_analysis": 0.92, ...}
                specialization_tags TEXT,  -- JSON数组：["牛仔服装", "跨境电商", "美国市场"]
                success_rate REAL DEFAULT 0.0,
                total_tasks_completed INTEGER DEFAULT 0,
                avg_completion_time_seconds INTEGER,
                current_load INTEGER DEFAULT 0,  -- 当前同时处理的任务数
                last_active TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        """)
        
        # 4. 成本消耗记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_consumption_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                avatar_id TEXT NOT NULL,
                cost_type TEXT CHECK(cost_type IN ('tokens', 'workflow_executions', 'api_calls', 'memory_storage')),
                amount REAL NOT NULL,
                unit_price REAL,
                total_cost REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                country_code TEXT DEFAULT 'US',          -- ISO 3166-1 alpha-2国家代码
                logistics_cost REAL DEFAULT 0.0,         -- 物流成本（当地货币）
                tax_rate REAL DEFAULT 0.0,               -- 税率百分比
                local_operations_cost REAL DEFAULT 0.0,  -- 本地运营费用
                shipping_time_days INTEGER DEFAULT 7,    -- 运输天数
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                recorded_at TIMESTAMP NOT NULL,
                notes TEXT,
                FOREIGN KEY (avatar_id) REFERENCES avatar_capability_profiles(avatar_id)
            )
        """)
        
        # 5. 网络节点注册表（用于跨SellAI实例通信）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                capabilities TEXT NOT NULL,  -- JSON数组：["negotiation", "resource_matching"]
                last_seen TIMESTAMP NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('active', 'inactive', 'maintenance')),
                base_url TEXT,
                api_version TEXT,
                geographic_region TEXT,
                supported_industries TEXT,  -- JSON数组
                max_concurrent_negotiations INTEGER DEFAULT 10,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        # 6. 用户-分身社交关系表（支持双社交体系）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_avatar_relationships (
                relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                avatar_id TEXT NOT NULL,
                relationship_type TEXT CHECK(relationship_type IN ('friend', 'blocked', 'muted')) DEFAULT 'friend',
                created_at TIMESTAMP NOT NULL,
                last_interaction TIMESTAMP NOT NULL,
                metadata TEXT,  -- JSON格式：{"allow_ai_initiated_chat": true, "show_opportunity_push": true, ...}
                UNIQUE(user_id, avatar_id)
            )
        """)
        
        # 7. AI-AI私下通信记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_ai_communications (
                communication_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_avatar_id TEXT NOT NULL,
                receiver_avatar_id TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT CHECK(content_type IN ('text', 'opportunity', 'task_request', 'collaboration')) DEFAULT 'text',
                timestamp TIMESTAMP NOT NULL,
                is_opportunity_synced BOOLEAN DEFAULT 0,  -- 是否已同步给用户
                synced_to_user_id TEXT,  -- 同步给哪个用户
                synced_at TIMESTAMP,
                metadata TEXT,  -- JSON格式：{"priority": 1, "tags": ["high_value", "urgent"], ...}
                FOREIGN KEY (sender_avatar_id) REFERENCES avatar_capability_profiles(avatar_id),
                FOREIGN KEY (receiver_avatar_id) REFERENCES avatar_capability_profiles(avatar_id)
            )
        """)
        
        # 8. 用户隐私设置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_privacy_settings (
                user_id TEXT PRIMARY KEY,
                allow_ai_initiated_chat BOOLEAN DEFAULT 1,
                show_opportunity_push BOOLEAN DEFAULT 1,
                allow_ai_ai_collaboration_visibility BOOLEAN DEFAULT 1,
                auto_add_ai_friends BOOLEAN DEFAULT 1,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        
        # 为常用的查询字段创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_status ON processed_opportunities(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_avatar ON task_assignments(assigned_avatar)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_status ON task_assignments(completion_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_hash ON task_assignments(opportunity_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_avatar ON cost_consumption_logs(avatar_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_period ON cost_consumption_logs(period_start, period_end)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_status ON network_nodes(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON network_nodes(node_type)")
        # 新增社交关系索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_avatar_relations ON user_avatar_relationships(user_id, avatar_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_communications ON ai_ai_communications(sender_avatar_id, receiver_avatar_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_privacy_settings ON user_privacy_settings(user_id)")
        
        conn.commit()
        self.close()
    
    def calculate_opportunity_hash(self, source_platform: str, original_id: str, title: str) -> str:
        """
        计算商机的唯一哈希值
        
        Args:
            source_platform: 来源平台
            original_id: 原始ID
            title: 标题
        
        Returns:
            哈希字符串
        """
        # 使用平台、ID和标题的组合计算哈希
        content = f"{source_platform}:{original_id}:{title}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def check_and_record_opportunity(self, source_platform: str, original_id: str, 
                                   title: str, status: str = 'pending') -> Tuple[bool, str]:
        """
        检查商机是否已处理，如未处理则记录
        
        Args:
            source_platform: 来源平台
            original_id: 原始ID
            title: 标题
            status: 初始状态
        
        Returns:
            (是否为新商机, 哈希值)
        """
        opportunity_hash = self.calculate_opportunity_hash(source_platform, original_id, title)
        now = datetime.now().isoformat()
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute(
            "SELECT opportunity_hash FROM processed_opportunities WHERE opportunity_hash = ?",
            (opportunity_hash,)
        )
        exists = cursor.fetchone() is not None
        
        if not exists:
            # 插入新记录 (使用INSERT OR IGNORE保证幂等)
            cursor.execute("""
                INSERT OR IGNORE INTO processed_opportunities 
                (opportunity_hash, source_platform, original_id, title, 
                 first_discovered, last_checked, processed_by_avatars, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opportunity_hash,
                source_platform,
                original_id,
                title,
                now,
                now,
                json.dumps([]),  # 初始为空数组
                status
            ))
            conn.commit()
            self.close()
            return True, opportunity_hash
        else:
            # 更新最后检查时间
            cursor.execute(
                "UPDATE processed_opportunities SET last_checked = ? WHERE opportunity_hash = ?",
                (now, opportunity_hash)
            )
            conn.commit()
            self.close()
            return False, opportunity_hash
    
    def record_task_assignment(self, opportunity_hash: str, assigned_avatar: str, 
                             deadline: Optional[str] = None, priority: int = 1) -> int:
        """
        记录任务分配
        
        Args:
            opportunity_hash: 商机哈希
            assigned_avatar: 分配的分身ID
            deadline: 截止时间（ISO格式）
            priority: 优先级（1-5，数字越大优先级越高）
        
        Returns:
            分配ID
        """
        now = datetime.now().isoformat()
        
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO task_assignments 
            (opportunity_hash, assigned_avatar, assignment_time, deadline, 
             priority, completion_status, result_summary)
            VALUES (?, ?, ?, ?, ?, 'pending', NULL)
        """, (
            opportunity_hash,
            assigned_avatar,
            now,
            deadline,
            priority
        ))
        
        assignment_id = cursor.lastrowid
        
        # 更新商机状态为处理中
        cursor.execute(
            "UPDATE processed_opportunities SET status = 'processing' WHERE opportunity_hash = ?",
            (opportunity_hash,)
        )
        
        # 更新分身当前负载
        cursor.execute("""
            UPDATE avatar_capability_profiles 
            SET current_load = current_load + 1, last_active = ?
            WHERE avatar_id = ?
        """, (now, assigned_avatar))
        
        conn.commit()
        self.close()
        
        return assignment_id
    
    def update_task_completion(self, assignment_id: int, completion_status: str, 
                             result_summary: Optional[str] = None):
        """
        更新任务完成状态
        
        Args:
            assignment_id: 分配ID
            completion_status: 完成状态
            result_summary: 结果摘要
        """
        now = datetime.now().isoformat()
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # 获取分配信息以更新分身负载
        cursor.execute(
            "SELECT assigned_avatar, opportunity_hash FROM task_assignments WHERE assignment_id = ?",
            (assignment_id,)
        )
        row = cursor.fetchone()
        if not row:
            self.close()
            raise ValueError(f"分配ID {assignment_id} 不存在")
        
        assigned_avatar, opportunity_hash = row
        
        # 更新任务分配
        cursor.execute("""
            UPDATE task_assignments 
            SET completion_status = ?, completion_time = ?, result_summary = ?
            WHERE assignment_id = ?
        """, (
            completion_status,
            now if completion_status in ['completed', 'failed'] else None,
            result_summary,
            assignment_id
        ))
        
        # 更新商机状态
        if completion_status == 'completed':
            cursor.execute(
                "UPDATE processed_opportunities SET status = 'completed' WHERE opportunity_hash = ?",
                (opportunity_hash,)
            )
        elif completion_status == 'failed':
            cursor.execute(
                "UPDATE processed_opportunities SET status = 'rejected' WHERE opportunity_hash = ?",
                (opportunity_hash,)
            )
        
        # 更新分身当前负载和成功率
        if completion_status in ['completed', 'failed']:
            cursor.execute(
                "UPDATE avatar_capability_profiles SET current_load = current_load - 1 WHERE avatar_id = ?",
                (assigned_avatar,)
            )
            
            # 获取当前分身信息
            cursor.execute(
                "SELECT total_tasks_completed, success_rate FROM avatar_capability_profiles WHERE avatar_id = ?",
                (assigned_avatar,)
            )
            avatar_row = cursor.fetchone()
            if avatar_row:
                total_tasks = avatar_row['total_tasks_completed']
                success_rate = avatar_row['success_rate']
                
                # 更新统计
                new_total = total_tasks + 1
                if completion_status == 'completed':
                    new_success_rate = (success_rate * total_tasks + 1) / new_total
                else:
                    new_success_rate = (success_rate * total_tasks) / new_total
                
                cursor.execute("""
                    UPDATE avatar_capability_profiles 
                    SET total_tasks_completed = ?, success_rate = ?, last_active = ?
                    WHERE avatar_id = ?
                """, (new_total, new_success_rate, now, assigned_avatar))
        
        conn.commit()
        self.close()
    
    def register_or_update_avatar_profile(self, avatar_id: str, avatar_name: str, 
                                        template_id: Optional[str] = None,
                                        capability_scores: Optional[Dict[str, float]] = None,
                                        specialization_tags: Optional[List[str]] = None):
        """
        注册或更新分身能力画像
        
        Args:
            avatar_id: 分身ID
            avatar_name: 分身名称
            template_id: 模板ID
            capability_scores: 能力分数字典
            specialization_tags: 专业标签列表
        """
        now = datetime.now().isoformat()
        
        # 默认能力分数
        if capability_scores is None:
            capability_scores = {
                "data_crawling": 0.7,
                "business_matching": 0.7,
                "content_creation": 0.7,
                "account_operation": 0.7,
                "financial_analysis": 0.7,
                "supply_chain_analysis": 0.7,
                "trend_prediction": 0.7
            }
        
        if specialization_tags is None:
            specialization_tags = ["通用"]
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute(
            "SELECT avatar_id FROM avatar_capability_profiles WHERE avatar_id = ?",
            (avatar_id,)
        )
        exists = cursor.fetchone() is not None
        
        if exists:
            # 更新现有记录
            cursor.execute("""
                UPDATE avatar_capability_profiles 
                SET avatar_name = ?, template_id = ?, capability_scores = ?, 
                    specialization_tags = ?, last_active = ?
                WHERE avatar_id = ?
            """, (
                avatar_name,
                template_id,
                json.dumps(capability_scores),
                json.dumps(specialization_tags),
                now,
                avatar_id
            ))
        else:
            # 插入新记录
            cursor.execute("""
                INSERT INTO avatar_capability_profiles 
                (avatar_id, avatar_name, template_id, capability_scores, 
                 specialization_tags, success_rate, total_tasks_completed, 
                 avg_completion_time_seconds, current_load, last_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                avatar_id,
                avatar_name,
                template_id,
                json.dumps(capability_scores),
                json.dumps(specialization_tags),
                0.0,  # 初始成功率
                0,    # 初始完成任务数
                None, # 初始平均完成时间
                0,    # 初始负载
                now,
                now
            ))
        
        conn.commit()
        self.close()
    
    def register_network_node(self, node_info: Dict[str, Any]) -> bool:
        """
        注册网络节点信息到共享状态库
        
        Args:
            node_info: 节点信息字典，包含：
                - node_id: 节点ID
                - node_type: 节点类型
                - capabilities: 能力列表 (JSON数组或列表)
                - last_seen: 最后活跃时间
                - status: 状态 ('active', 'inactive', 'maintenance')
                - base_url: 基础URL (可选)
                - api_version: API版本 (可选)
                - geographic_region: 地理区域 (可选)
                - supported_industries: 支持行业列表 (可选)
        
        Returns:
            注册成功返回True，失败返回False
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            
            # 确保表存在
            self._ensure_tables()
            
            # 处理capabilities字段
            capabilities = node_info.get('capabilities', [])
            if isinstance(capabilities, list):
                capabilities_json = json.dumps(capabilities)
            else:
                capabilities_json = capabilities
            
            # 处理supported_industries字段
            supported_industries = node_info.get('supported_industries', [])
            if isinstance(supported_industries, list):
                supported_industries_json = json.dumps(supported_industries)
            else:
                supported_industries_json = supported_industries
            
            # 检查是否已存在
            cursor.execute(
                "SELECT node_id FROM network_nodes WHERE node_id = ?",
                (node_info['node_id'],)
            )
            exists = cursor.fetchone() is not None
            
            if exists:
                # 更新现有记录
                cursor.execute("""
                    UPDATE network_nodes 
                    SET node_type = ?, capabilities = ?, last_seen = ?, 
                        status = ?, base_url = ?, api_version = ?, 
                        geographic_region = ?, supported_industries = ?,
                        updated_at = ?
                    WHERE node_id = ?
                """, (
                    node_info.get('node_type', 'sellai_instance'),
                    capabilities_json,
                    node_info.get('last_seen', now),
                    node_info.get('status', 'active'),
                    node_info.get('base_url', ''),
                    node_info.get('api_version', '1.0'),
                    node_info.get('geographic_region', 'global'),
                    supported_industries_json,
                    now,
                    node_info['node_id']
                ))
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO network_nodes 
                    (node_id, node_type, capabilities, last_seen, status,
                     base_url, api_version, geographic_region, supported_industries,
                     max_concurrent_negotiations, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_info['node_id'],
                    node_info.get('node_type', 'sellai_instance'),
                    capabilities_json,
                    node_info.get('last_seen', now),
                    node_info.get('status', 'active'),
                    node_info.get('base_url', ''),
                    node_info.get('api_version', '1.0'),
                    node_info.get('geographic_region', 'global'),
                    supported_industries_json,
                    node_info.get('max_concurrent_negotiations', 10),
                    now,
                    now
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ 注册网络节点失败: {e}")
            conn.rollback()
            return False
            
        finally:
            self.close()
    
    def record_cost_consumption(self, avatar_id: str, cost_type: str, amount: float,
                              unit_price: Optional[float] = None, currency: str = "USD",
                              country_code: str = "US", logistics_cost: float = 0.0,
                              tax_rate: float = 0.0, local_operations_cost: float = 0.0,
                              shipping_time_days: int = 7,
                              period_start: Optional[str] = None,
                              period_end: Optional[str] = None,
                              notes: Optional[str] = None):
        """
        记录成本消耗（全球视角）
        
        Args:
            avatar_id: 分身ID
            cost_type: 成本类型
            amount: 消耗量
            unit_price: 单价（如未提供则使用默认值）
            currency: 货币
            country_code: ISO 3166-1 alpha-2国家代码，默认'US'
            logistics_cost: 物流成本（当地货币）
            tax_rate: 税率百分比
            local_operations_cost: 本地运营费用
            shipping_time_days: 运输天数
            period_start: 统计周期开始时间
            period_end: 统计周期结束时间
            notes: 备注
        """
        now = datetime.now().isoformat()
        
        # 设置默认时间
        if period_start is None:
            period_start = now
        if period_end is None:
            period_end = now
        
        # 设置默认单价
        if unit_price is None:
            default_prices = {
                "tokens": 0.000002,  # GPT-4o每token约0.002美元/千token
                "workflow_executions": 0.0001,  # 每次执行约0.0001美元
                "api_calls": 0.01,   # 外部API调用约0.01美元/次
                "memory_storage": 0.000023  # 存储约0.023美元/GB/月
            }
            unit_price = default_prices.get(cost_type, 0.0)
        
        total_cost = amount * unit_price
        
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO cost_consumption_logs 
            (avatar_id, cost_type, amount, unit_price, total_cost, currency,
             country_code, logistics_cost, tax_rate, local_operations_cost, shipping_time_days,
             period_start, period_end, recorded_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            avatar_id,
            cost_type,
            amount,
            unit_price,
            total_cost,
            currency,
            country_code,
            logistics_cost,
            tax_rate,
            local_operations_cost,
            shipping_time_days,
            period_start,
            period_end,
            now,
            notes
        ))
        
        conn.commit()
        self.close()
    
    def get_avatar_profiles(self, avatar_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        获取分身能力画像
        
        Args:
            avatar_ids: 指定的分身ID列表，为空则获取所有
        
        Returns:
            分身画像列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        if avatar_ids:
            placeholders = ','.join(['?'] * len(avatar_ids))
            query = f"SELECT * FROM avatar_capability_profiles WHERE avatar_id IN ({placeholders})"
            cursor.execute(query, avatar_ids)
        else:
            cursor.execute("SELECT * FROM avatar_capability_profiles")
        
        rows = cursor.fetchall()
        profiles = []
        
        for row in rows:
            profile = dict(row)
            # 解析JSON字段
            profile['capability_scores'] = json.loads(profile['capability_scores'])
            profile['specialization_tags'] = json.loads(profile['specialization_tags'])
            profiles.append(profile)
        
        self.close()
        return profiles
    
    def get_task_assignments(self, status: Optional[str] = None, 
                           avatar_id: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取任务分配记录
        
        Args:
            status: 过滤状态
            avatar_id: 过滤分身ID
            limit: 返回数量限制
        
        Returns:
            任务分配记录列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM task_assignments WHERE 1=1"
        params = []
        
        if status:
            query += " AND completion_status = ?"
            params.append(status)
        
        if avatar_id:
            query += " AND assigned_avatar = ?"
            params.append(avatar_id)
        
        query += " ORDER BY assignment_time DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        assignments = [dict(row) for row in rows]
        self.close()
        return assignments
    
    def get_cost_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        获取成本汇总
        
        Args:
            start_date: 开始时间（ISO格式）
            end_date: 结束时间（ISO格式）
        
        Returns:
            成本汇总信息
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        # 按类型汇总
        cursor.execute("""
            SELECT 
                cost_type,
                SUM(amount) as total_amount,
                SUM(total_cost) as total_cost,
                COUNT(*) as record_count
            FROM cost_consumption_logs
            WHERE period_start >= ? AND period_end <= ?
            GROUP BY cost_type
        """, (start_date, end_date))
        
        breakdown_rows = cursor.fetchall()
        breakdown = [dict(row) for row in breakdown_rows]
        
        # 总成本
        cursor.execute("""
            SELECT SUM(total_cost) as total_cost
            FROM cost_consumption_logs
            WHERE period_start >= ? AND period_end <= ?
        """, (start_date, end_date))
        
        total_row = cursor.fetchone()
        total_cost = total_row['total_cost'] if total_row['total_cost'] else 0.0
        
        # 分身成本排名
        cursor.execute("""
            SELECT 
                avatar_id,
                SUM(total_cost) as avatar_total_cost
            FROM cost_consumption_logs
            WHERE period_start >= ? AND period_end <= ?
            GROUP BY avatar_id
            ORDER BY avatar_total_cost DESC
            LIMIT 10
        """, (start_date, end_date))
        
        ranking_rows = cursor.fetchall()
        ranking = [dict(row) for row in ranking_rows]
        
        self.close()
        
        return {
            "period_start": start_date,
            "period_end": end_date,
            "total_cost": total_cost,
            "breakdown": breakdown,
            "avatar_ranking": ranking
        }
    
    def find_best_avatar_for_task(self, required_capabilities: List[str], 
                                min_score_threshold: float = 0.6) -> Optional[str]:
        """
        根据能力要求寻找最适合的分身（增强版）
        
        采用多维度评分算法，考虑能力匹配度、负载因子、成功率、
        响应速度等因素，提升任务分配精度。
        
        Args:
            required_capabilities: 所需能力列表
            min_score_threshold: 最低能力分数阈值
        
        Returns:
            最适合的分身ID，如无合适则返回None
        """
        profiles = self.get_avatar_profiles()
        
        best_avatar = None
        best_score = -1
        
        for profile in profiles:
            # 1. 检查成功率阈值
            if profile['success_rate'] < min_score_threshold:
                continue
            
            # 2. 计算能力匹配度
            capability_scores = profile['capability_scores']
            relevant_scores = []
            
            for capability in required_capabilities:
                if capability in capability_scores:
                    score = capability_scores[capability]
                    if score >= min_score_threshold:
                        relevant_scores.append(score)
                    else:
                        relevant_scores.append(0.0)
                else:
                    # 分身缺少此能力
                    relevant_scores.append(0.0)
            
            # 检查是否有所有所需能力
            if len(relevant_scores) != len(required_capabilities):
                continue
            
            # 能力匹配度（权重0.35）
            avg_capability_score = sum(relevant_scores) / len(relevant_scores)
            
            # 3. 负载因子：负载越低越好（权重0.25）
            load_factor = 1.0 / (1.0 + profile['current_load'])
            
            # 4. 成功率：越高越好（权重0.25）
            success_score = profile['success_rate']
            
            # 5. 响应速度：完成时间越短越好（权重0.15）
            response_score = 1.0
            if profile['avg_completion_time_seconds'] and profile['avg_completion_time_seconds'] > 0:
                # 归一化：假设合理完成时间在300秒内
                normalized_time = min(1.0, profile['avg_completion_time_seconds'] / 300)
                response_score = 1.0 - normalized_time
            
            # 计算综合分数（加权平均）
            total_score = (avg_capability_score * 0.35) + (load_factor * 0.25) + \
                         (success_score * 0.25) + (response_score * 0.15)
            
            # 记录分配决策（用于后续分析和优化）
            self._record_assignment_decision(
                profile['avatar_id'],
                required_capabilities,
                min_score_threshold,
                {
                    'capability_match': avg_capability_score,
                    'load_factor': load_factor,
                    'success_rate': success_score,
                    'response_speed': response_score,
                    'total_score': total_score
                }
            )
            
            if total_score > best_score:
                best_score = total_score
                best_avatar = profile['avatar_id']
        
        # 记录性能指标
        if best_avatar:
            self._record_performance_metric('allocation_success', 1)
        else:
            self._record_performance_metric('allocation_failure', 1)
        
        return best_avatar
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            统计信息字典
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        # 总商机数
        cursor.execute("SELECT COUNT(*) as count FROM processed_opportunities")
        total_opportunities = cursor.fetchone()['count']
        
        # 已完成商机数
        cursor.execute("SELECT COUNT(*) as count FROM processed_opportunities WHERE status = 'completed'")
        completed_opportunities = cursor.fetchone()['count']
        
        # 总任务数
        cursor.execute("SELECT COUNT(*) as count FROM task_assignments")
        total_tasks = cursor.fetchone()['count']
        
        # 进行中任务数
        cursor.execute("SELECT COUNT(*) as count FROM task_assignments WHERE completion_status = 'in_progress'")
        in_progress_tasks = cursor.fetchone()['count']
        
        # 总分身数
        cursor.execute("SELECT COUNT(*) as count FROM avatar_capability_profiles")
        total_avatars = cursor.fetchone()['count']
        
        # 活跃分身数（最近24小时有活动）
        one_day_ago = datetime.now().isoformat()  # 简化处理
        cursor.execute("""
            SELECT COUNT(*) as count FROM avatar_capability_profiles 
            WHERE last_active >= ? OR current_load > 0
        """, (one_day_ago,))
        active_avatars = cursor.fetchone()['count']
        
        # 总成本
        cursor.execute("SELECT SUM(total_cost) as total FROM cost_consumption_logs")
        total_cost_row = cursor.fetchone()
        total_cost = total_cost_row['total'] if total_cost_row['total'] else 0.0
        
        self.close()
        
        return {
            "total_opportunities": total_opportunities,
            "completed_opportunities": completed_opportunities,
            "total_tasks": total_tasks,
            "in_progress_tasks": in_progress_tasks,
            "total_avatars": total_avatars,
            "active_avatars": active_avatars,
            "total_cost_usd": total_cost
        }


# 单例模式，便于全局使用
_shared_state_manager = None

def get_shared_state_manager() -> SharedStateManager:
    """获取共享状态管理器单例"""
    global _shared_state_manager
    if _shared_state_manager is None:
        _shared_state_manager = SharedStateManager()
    return _shared_state_manager


# 提供简单的函数接口
def check_opportunity(source_platform: str, original_id: str, title: str) -> Tuple[bool, str]:
    """检查商机是否已处理"""
    manager = get_shared_state_manager()
    return manager.check_and_record_opportunity(source_platform, original_id, title)

def assign_task(opportunity_hash: str, avatar_id: str, priority: int = 1) -> int:
    """分配任务给分身"""
    manager = get_shared_state_manager()
    return manager.record_task_assignment(opportunity_hash, avatar_id, priority=priority)

def complete_task(assignment_id: int, result_summary: str):
    """标记任务完成"""
    manager = get_shared_state_manager()
    manager.update_task_completion(assignment_id, 'completed', result_summary)

def get_system_statistics() -> Dict[str, Any]:
    """获取系统统计"""
    manager = get_shared_state_manager()
    return manager.get_statistics()


if __name__ == "__main__":
    # 测试代码
    manager = SharedStateManager()
    
    print("共享状态管理器初始化完成")
    print(f"数据库路径: {manager.db_path}")
    
    # 注册几个测试分身
    manager.register_or_update_avatar_profile(
        avatar_id="intelligence_officer",
        avatar_name="情报官（调度中枢）",
        template_id="central_001",
        capability_scores={
            "data_crawling": 0.95,
            "business_matching": 0.85,
            "financial_analysis": 0.90,
            "trend_prediction": 0.88
        },
        specialization_tags=["数据爬取", "商机筛选", "调度协调"]
    )
    
    manager.register_or_update_avatar_profile(
        avatar_id="content_officer",
        avatar_name="内容官（创作中枢）",
        template_id="central_002",
        capability_scores={
            "content_creation": 0.95,
            "trend_prediction": 0.82,
            "account_operation": 0.75
        },
        specialization_tags=["内容创作", "多平台策略", "品牌一致性"]
    )
    
    # 测试商机检查
    is_new, hash_val = manager.check_and_record_opportunity(
        source_platform="Amazon",
        original_id="B08N5WRWNW",
        title="男士牛仔裤 - 高品质牛仔布料"
    )
    print(f"\n测试商机检查:")
    print(f"  是否新商机: {is_new}")
    print(f"  哈希值: {hash_val}")
    
    # 测试任务分配
    if is_new:
        assignment_id = manager.record_task_assignment(
            opportunity_hash=hash_val,
            assigned_avatar="intelligence_officer",
            priority=3
        )
        print(f"\n测试任务分配:")
        print(f"  分配ID: {assignment_id}")
        
        # 模拟任务完成
        manager.update_task_completion(
            assignment_id=assignment_id,
            completion_status="completed",
            result_summary="商机分析完成，利润率约35%，建议进一步对接"
        )
        print(f"  任务标记为完成")
    
    # 测试统计
    stats = manager.get_statistics()
    print(f"\n系统统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n共享状态库测试完成")