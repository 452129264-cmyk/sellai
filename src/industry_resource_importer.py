#!/usr/bin/env python3
"""
全行业商业资源库数据导入模块
功能：
1. 执行DDL创建全行业资源表结构
2. 将现有商机数据导入到新模型
3. 支持从外部数据源导入行业资源数据
4. 提供模拟数据生成功能用于测试
"""

import sqlite3
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import hashlib
import random

# 添加父目录到路径以便导入共享状态管理器
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class IndustryResourceImporter:
    """行业资源导入器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化导入器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        
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
    
    def execute_ddl(self, ddl_file: str = None):
        """
        执行DDL创建表结构
        
        Args:
            ddl_file: DDL文件路径，如为None则使用内置DDL
        """
        print("开始执行全行业商业资源库DDL...")
        
        if ddl_file:
            # 从文件读取DDL
            with open(ddl_file, 'r', encoding='utf-8') as f:
                ddl_sql = f.read()
        else:
            # 使用内置DDL（简略版，完整版在docs/全行业商业资源库_DDL.sql）
            ddl_sql = self._get_builtin_ddl()
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # 执行DDL语句
        try:
            cursor.executescript(ddl_sql)
            conn.commit()
            print("✅ DDL执行成功，表结构已创建")
        except sqlite3.Error as e:
            print(f"❌ DDL执行失败: {e}")
            conn.rollback()
            raise
        
        # 验证表是否创建成功
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%industry%'")
        tables = cursor.fetchall()
        print(f"已创建行业资源相关表: {[t[0] for t in tables]}")
        
        self.close()
        return True
    
    def _get_builtin_ddl(self) -> str:
        """获取内置DDL语句（简略版）"""
        return """
        -- 资源分类表
        CREATE TABLE IF NOT EXISTS resource_categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_type TEXT NOT NULL CHECK(category_type IN ('industry', 'resource_type', 'region_scope', 'cooperation_mode')),
            category_code TEXT NOT NULL,
            category_name TEXT NOT NULL,
            description TEXT,
            parent_category_id INTEGER,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category_type, category_code),
            FOREIGN KEY (parent_category_id) REFERENCES resource_categories(category_id) ON DELETE SET NULL
        );
        
        -- 行业资源主表
        CREATE TABLE IF NOT EXISTS industry_resources (
            resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_title TEXT NOT NULL,
            resource_description TEXT,
            resource_type INTEGER NOT NULL,
            industry_path TEXT NOT NULL,
            region_scope INTEGER NOT NULL,
            country_code TEXT,
            region_details TEXT,
            cooperation_mode INTEGER,
            budget_range TEXT,
            timeline TEXT,
            direction TEXT NOT NULL CHECK(direction IN ('supply', 'demand', 'both')),
            status TEXT NOT NULL CHECK(status IN ('active', 'pending', 'completed', 'expired', 'archived')) DEFAULT 'active',
            quality_score REAL DEFAULT 0.0,
            relevance_score REAL DEFAULT 0.0,
            source_platform TEXT,
            source_url TEXT,
            source_id TEXT,
            contact_name TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            contact_company TEXT,
            created_by_avatar TEXT,
            last_updated_by_avatar TEXT,
            viewed_count INTEGER DEFAULT 0,
            matched_count INTEGER DEFAULT 0,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resource_type) REFERENCES resource_categories(category_id),
            FOREIGN KEY (region_scope) REFERENCES resource_categories(category_id),
            FOREIGN KEY (cooperation_mode) REFERENCES resource_categories(category_id),
            UNIQUE(source_platform, source_id)
        );
        
        -- 匹配标准表
        CREATE TABLE IF NOT EXISTS matching_criteria (
            criteria_id INTEGER PRIMARY KEY AUTOINCREMENT,
            criteria_name TEXT NOT NULL,
            criteria_type TEXT NOT NULL CHECK(criteria_type IN ('industry', 'region', 'budget', 'timeline', 'capability', 'composite')),
            condition_schema TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 1.0,
            applicable_resource_types TEXT,
            applicable_industries TEXT,
            matching_algorithm TEXT DEFAULT 'exact',
            threshold REAL DEFAULT 0.7,
            is_active INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 0,
            description TEXT,
            created_by_avatar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 跨行业映射表
        CREATE TABLE IF NOT EXISTS cross_industry_mappings (
            mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_industry_id INTEGER NOT NULL,
            target_industry_id INTEGER NOT NULL,
            mapping_type TEXT NOT NULL CHECK(mapping_type IN ('similarity', 'complementary', 'supply_chain', 'technology_transfer', 'market_expansion')),
            strength REAL NOT NULL DEFAULT 0.5,
            confidence REAL DEFAULT 0.8,
            mapping_rules TEXT,
            applicable_scenarios TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_industry_id) REFERENCES resource_categories(category_id),
            FOREIGN KEY (target_industry_id) REFERENCES resource_categories(category_id),
            UNIQUE(source_industry_id, target_industry_id, mapping_type)
        );
        
        -- 资源匹配记录表
        CREATE TABLE IF NOT EXISTS resource_matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_a_id INTEGER NOT NULL,
            resource_b_id INTEGER NOT NULL,
            match_type TEXT NOT NULL CHECK(match_type IN ('auto', 'manual', 'recommended')),
            match_score REAL NOT NULL,
            match_reason TEXT,
            status TEXT NOT NULL CHECK(status IN ('pending', 'contacted', 'negotiating', 'successful', 'failed', 'expired')) DEFAULT 'pending',
            initiated_by_avatar TEXT,
            contact_date TIMESTAMP,
            last_contact_date TIMESTAMP,
            next_followup_date TIMESTAMP,
            outcome TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resource_a_id) REFERENCES industry_resources(resource_id) ON DELETE CASCADE,
            FOREIGN KEY (resource_b_id) REFERENCES industry_resources(resource_id) ON DELETE CASCADE,
            UNIQUE(resource_a_id, resource_b_id, match_type)
        );
        """
    
    def import_existing_opportunities(self, batch_size: int = 100):
        """
        将现有商机数据导入到行业资源模型
        
        Args:
            batch_size: 批量处理大小
        """
        print("开始导入现有商机数据到行业资源模型...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # 1. 确保分类数据已存在
        self._ensure_basic_categories(cursor)
        
        # 2. 获取现有商机数据
        cursor.execute("""
            SELECT opportunity_hash, source_platform, original_id, title, 
                   first_discovered, last_checked, status
            FROM processed_opportunities
            ORDER BY first_discovered
        """)
        
        opportunities = cursor.fetchall()
        print(f"找到 {len(opportunities)} 个现有商机")
        
        # 3. 导入每个商机
        imported_count = 0
        skipped_count = 0
        
        for opp in opportunities:
            opportunity_hash = opp['opportunity_hash']
            source_platform = opp['source_platform']
            original_id = opp['original_id']
            title = opp['title']
            created_at = opp['first_discovered']
            updated_at = opp['last_checked']
            status = opp['status']
            
            # 检查是否已导入（通过source_id唯一性）
            cursor.execute(
                "SELECT resource_id FROM industry_resources WHERE source_id = ?",
                (opportunity_hash,)
            )
            if cursor.fetchone():
                skipped_count += 1
                continue
            
            # 确定资源类型：默认为商品供应
            resource_type_id = self._get_resource_type_id(cursor, 'product_supply')
            
            # 确定行业分类：默认为零售/电商
            industry_id = self._get_industry_id(cursor, 'retail')
            industry_path = json.dumps([industry_id])
            
            # 确定地域范围：根据平台推断
            region_scope_id = self._get_region_scope_id(cursor, 
                'global' if source_platform in ['Amazon', 'TikTok'] else 'regional'
            )
            
            # 确定合作模式：默认为分销代理
            cooperation_mode_id = self._get_cooperation_mode_id(cursor, 'distribution')
            
            # 转换状态映射
            resource_status = self._map_opportunity_status(status)
            
            # 生成质量评分（基于平台可信度）
            quality_score = self._calculate_quality_score(source_platform, title)
            
            # 插入行业资源记录
            cursor.execute("""
                INSERT INTO industry_resources (
                    resource_title, resource_description, resource_type,
                    industry_path, region_scope, cooperation_mode,
                    direction, status, quality_score, relevance_score,
                    source_platform, source_url, source_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,  # resource_title
                f"来自 {source_platform} 的商机: {title}",  # resource_description
                resource_type_id,
                industry_path,
                region_scope_id,
                cooperation_mode_id,
                'supply',  # direction (现有商机都是供应方)
                resource_status,
                quality_score,
                0.5,  # 默认相关性评分
                source_platform,
                f"https://{source_platform.lower()}.com/item/{original_id}" if original_id else None,
                opportunity_hash,  # source_id
                created_at,
                updated_at
            ))
            
            imported_count += 1
            
            # 每处理一批提交一次
            if imported_count % batch_size == 0:
                conn.commit()
                print(f"  已导入 {imported_count} 个商机...")
        
        # 最终提交
        conn.commit()
        self.close()
        
        print(f"✅ 现有商机数据导入完成")
        print(f"  成功导入: {imported_count} 个")
        print(f"  跳过重复: {skipped_count} 个")
        
        return imported_count
    
    def _ensure_basic_categories(self, cursor):
        """确保基础分类数据存在"""
        # 行业分类
        industries = [
            ('manufacturing', '制造业', '各类制造行业'),
            ('service', '服务业', '各类服务行业'),
            ('technology', '科技', '高新技术产业'),
            ('agriculture', '农业', '农业相关产业'),
            ('retail', '零售/电商', '商品零售和电子商务'),
        ]
        
        for code, name, desc in industries:
            cursor.execute("""
                INSERT OR IGNORE INTO resource_categories 
                (category_type, category_code, category_name, description, sort_order)
                VALUES ('industry', ?, ?, ?, ?)
            """, (code, name, desc, len(industries)))
        
        # 资源类型
        resource_types = [
            ('supply_chain', '供应链', '原材料、零部件供应'),
            ('tech_cooperation', '技术合作', '技术研发合作'),
            ('product_supply', '商品供应', '成品商品供应'),
            ('capital', '资金对接', '投资融资需求'),
            ('talent', '人才匹配', '人才招聘合作'),
        ]
        
        for code, name, desc in resource_types:
            cursor.execute("""
                INSERT OR IGNORE INTO resource_categories 
                (category_type, category_code, category_name, description, sort_order)
                VALUES ('resource_type', ?, ?, ?, ?)
            """, (code, name, desc, len(resource_types)))
        
        # 地域范围
        region_scopes = [
            ('local', '本地', '同一城市或地区'),
            ('regional', '区域', '同一国家内跨区域'),
            ('national', '全国', '同一国家范围内'),
            ('global', '全球', '跨国或全球范围'),
        ]
        
        for code, name, desc in region_scopes:
            cursor.execute("""
                INSERT OR IGNORE INTO resource_categories 
                (category_type, category_code, category_name, description, sort_order)
                VALUES ('region_scope', ?, ?, ?, ?)
            """, (code, name, desc, len(region_scopes)))
        
        # 合作模式
        cooperation_modes = [
            ('equity', '股权合作', '股权投资、合资公司'),
            ('project', '项目分包', '项目整体或部分分包'),
            ('distribution', '代理分销', '代理销售、分销合作'),
            ('commission', '佣金合作', '按销售额提成合作'),
        ]
        
        for code, name, desc in cooperation_modes:
            cursor.execute("""
                INSERT OR IGNORE INTO resource_categories 
                (category_type, category_code, category_name, description, sort_order)
                VALUES ('cooperation_mode', ?, ?, ?, ?)
            """, (code, name, desc, len(cooperation_modes)))
    
    def _get_resource_type_id(self, cursor, category_code: str) -> int:
        """获取资源类型ID"""
        cursor.execute(
            "SELECT category_id FROM resource_categories WHERE category_type = 'resource_type' AND category_code = ?",
            (category_code,)
        )
        row = cursor.fetchone()
        return row['category_id'] if row else 1  # 默认为1
    
    def _get_industry_id(self, cursor, category_code: str) -> int:
        """获取行业分类ID"""
        cursor.execute(
            "SELECT category_id FROM resource_categories WHERE category_type = 'industry' AND category_code = ?",
            (category_code,)
        )
        row = cursor.fetchone()
        return row['category_id'] if row else 1  # 默认为1
    
    def _get_region_scope_id(self, cursor, category_code: str) -> int:
        """获取地域范围ID"""
        cursor.execute(
            "SELECT category_id FROM resource_categories WHERE category_type = 'region_scope' AND category_code = ?",
            (category_code,)
        )
        row = cursor.fetchone()
        return row['category_id'] if row else 1  # 默认为1
    
    def _get_cooperation_mode_id(self, cursor, category_code: str) -> int:
        """获取合作模式ID"""
        cursor.execute(
            "SELECT category_id FROM resource_categories WHERE category_type = 'cooperation_mode' AND category_code = ?",
            (category_code,)
        )
        row = cursor.fetchone()
        return row['category_id'] if row else 1  # 默认为1
    
    def _map_opportunity_status(self, opp_status: str) -> str:
        """映射商机状态到资源状态"""
        status_map = {
            'pending': 'active',
            'processing': 'active',
            'completed': 'completed',
            'rejected': 'archived',
        }
        return status_map.get(opp_status, 'active')
    
    def _calculate_quality_score(self, source_platform: str, title: str) -> float:
        """计算质量评分"""
        platform_scores = {
            'Amazon': 0.9,
            'Google Trends': 0.8,
            'TikTok': 0.7,
            'Instagram': 0.7,
            'Reddit': 0.6,
            '政府补贴网站': 0.8,
        }
        
        base_score = platform_scores.get(source_platform, 0.5)
        
        # 根据标题长度调整
        title_length = len(title)
        if title_length < 10:
            length_factor = 0.7
        elif title_length < 30:
            length_factor = 0.9
        else:
            length_factor = 0.8
        
        return round(base_score * length_factor, 2)
    
    def generate_sample_resources(self, count: int = 50):
        """
        生成样本行业资源数据用于测试
        
        Args:
            count: 生成的资源数量
        """
        print(f"开始生成 {count} 个样本行业资源数据...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # 确保基础分类数据存在
        self._ensure_basic_categories(cursor)
        
        # 获取所有分类ID
        industry_ids = self._get_all_category_ids(cursor, 'industry')
        resource_type_ids = self._get_all_category_ids(cursor, 'resource_type')
        region_scope_ids = self._get_all_category_ids(cursor, 'region_scope')
        cooperation_mode_ids = self._get_all_category_ids(cursor, 'cooperation_mode')
        
        if not all([industry_ids, resource_type_ids, region_scope_ids]):
            print("❌ 缺少必要的分类数据，请先执行DDL")
            return 0
        
        # 样本数据模板
        sample_templates = [
            {
                'title': '精密机械零部件供应',
                'description': '专业生产高精度机械零部件，适用于自动化设备、医疗器械等领域',
                'industry': 'manufacturing',
                'resource_type': 'supply_chain',
                'direction': 'supply',
                'keywords': ['机械', '零部件', '精密加工', '自动化'],
            },
            {
                'title': '人工智能算法合作开发',
                'description': '寻求AI算法研发合作伙伴，共同开发计算机视觉或自然语言处理解决方案',
                'industry': 'technology',
                'resource_type': 'tech_cooperation',
                'direction': 'demand',
                'keywords': ['人工智能', '算法', '计算机视觉', '合作开发'],
            },
            {
                'title': '农业物联网解决方案需求',
                'description': '农场需要智能灌溉、环境监测等物联网解决方案，提高农业生产效率',
                'industry': 'agriculture',
                'resource_type': 'tech_cooperation',
                'direction': 'demand',
                'keywords': ['农业', '物联网', '智能灌溉', '环境监测'],
            },
            {
                'title': '跨境电商物流服务',
                'description': '提供全球跨境电商物流解决方案，包括仓储、清关、最后一公里配送',
                'industry': 'logistics',
                'resource_type': 'supply_chain',
                'direction': 'supply',
                'keywords': ['跨境电商', '物流', '仓储', '清关'],
            },
            {
                'title': '医疗设备融资租赁',
                'description': '为医院提供高端医疗设备的融资租赁服务，降低采购门槛',
                'industry': 'healthcare',
                'resource_type': 'capital',
                'direction': 'supply',
                'keywords': ['医疗设备', '融资租赁', '医院', '医疗'],
            },
        ]
        
        generated_count = 0
        
        for i in range(count):
            # 随机选择一个模板
            template = random.choice(sample_templates)
            
            # 确定具体分类ID
            industry_id = self._get_industry_id(cursor, template['industry'])
            industry_path = json.dumps([industry_id])
            
            resource_type_id = self._get_resource_type_id(cursor, template['resource_type'])
            region_scope_id = random.choice(region_scope_ids)
            cooperation_mode_id = random.choice(cooperation_mode_ids) if cooperation_mode_ids else None
            
            # 生成预算范围
            budget_min = random.randint(10000, 500000)
            budget_max = budget_min + random.randint(50000, 200000)
            budget_range = json.dumps({
                'currency': 'USD',
                'min': budget_min,
                'max': budget_max,
            })
            
            # 生成时间线
            timeline_days = random.randint(30, 180)
            timeline = json.dumps({
                'unit': 'days',
                'value': timeline_days,
            })
            
            # 生成质量评分
            quality_score = random.uniform(0.6, 0.95)
            
            # 插入记录
            cursor.execute("""
                INSERT INTO industry_resources (
                    resource_title, resource_description, resource_type,
                    industry_path, region_scope, cooperation_mode,
                    budget_range, timeline, direction, status,
                    quality_score, relevance_score, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{template['title']} #{i+1}",
                template['description'],
                resource_type_id,
                industry_path,
                region_scope_id,
                cooperation_mode_id,
                budget_range,
                timeline,
                template['direction'],
                'active',
                round(quality_score, 2),
                round(random.uniform(0.3, 0.8), 2),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ))
            
            generated_count += 1
            
            # 每10个提交一次
            if generated_count % 10 == 0:
                conn.commit()
                print(f"  已生成 {generated_count} 个样本资源...")
        
        conn.commit()
        self.close()
        
        print(f"✅ 样本行业资源数据生成完成: {generated_count} 个")
        return generated_count
    
    def _get_all_category_ids(self, cursor, category_type: str) -> List[int]:
        """获取指定类型的所有分类ID"""
        cursor.execute(
            "SELECT category_id FROM resource_categories WHERE category_type = ? AND is_active = 1",
            (category_type,)
        )
        rows = cursor.fetchall()
        return [row['category_id'] for row in rows]
    
    def insert_industry_resource(self, resource_data: Dict[str, Any]) -> Optional[int]:
        """
        插入单个行业资源记录
        
        Args:
            resource_data: 资源数据字典，包含：
                - resource_type: 资源类型代码 (如 'supply_chain')
                - industry: 行业代码 (如 'manufacturing')
                - title: 资源标题
                - description: 资源描述
                - country: 国家代码 (如 'US')
                - value_range: 价值范围字符串 (如 '100000-500000')
                - contact_info: 联系人信息
                - created_at: 创建时间 (ISO格式)
                - status: 状态 ('active', 'pending', etc.)
                - direction: 方向 ('supply', 'demand', 'both')，默认为'supply'
                - region_scope: 地域范围代码，默认为'global'
                - cooperation_mode: 合作模式代码，默认为'distribution'
        
        Returns:
            插入的资源ID，失败返回None
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 确保基础分类数据存在
            self._ensure_basic_categories(cursor)
            
            # 获取分类ID
            resource_type_id = self._get_resource_type_id(cursor, resource_data.get('resource_type', 'product_supply'))
            industry_id = self._get_industry_id(cursor, resource_data.get('industry', 'retail'))
            industry_path = json.dumps([industry_id])
            
            region_scope = resource_data.get('region_scope', 'global')
            region_scope_id = self._get_region_scope_id(cursor, region_scope)
            
            cooperation_mode = resource_data.get('cooperation_mode', 'distribution')
            cooperation_mode_id = self._get_cooperation_mode_id(cursor, cooperation_mode) if cooperation_mode else None
            
            # 处理预算范围
            budget_range = json.dumps({
                'currency': 'USD',
                'min': 0,
                'max': 0
            })
            if 'value_range' in resource_data:
                try:
                    # 尝试解析 "100000-500000" 格式
                    range_str = resource_data['value_range']
                    if '-' in range_str:
                        min_val, max_val = range_str.split('-')
                        budget_range = json.dumps({
                            'currency': 'USD',
                            'min': int(min_val),
                            'max': int(max_val)
                        })
                except:
                    pass
            
            # 插入记录
            cursor.execute("""
                INSERT INTO industry_resources (
                    resource_title, resource_description, resource_type,
                    industry_path, region_scope, cooperation_mode,
                    country_code, budget_range, direction, status,
                    quality_score, relevance_score, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                resource_data.get('title', '未命名资源'),
                resource_data.get('description', ''),
                resource_type_id,
                industry_path,
                region_scope_id,
                cooperation_mode_id,
                resource_data.get('country', ''),
                budget_range,
                resource_data.get('direction', 'supply'),
                resource_data.get('status', 'active'),
                0.7,  # 默认质量评分
                0.5,  # 默认相关性评分
                resource_data.get('created_at', datetime.now().isoformat()),
                datetime.now().isoformat()
            ))
            
            resource_id = cursor.lastrowid
            conn.commit()
            
            return resource_id
            
        except Exception as e:
            print(f"❌ 插入行业资源失败: {e}")
            conn.rollback()
            return None
            
        finally:
            self.close()
    
    def validate_extension(self) -> Dict[str, Any]:
        """
        验证扩展的完整性
        
        Returns:
            验证结果字典
        """
        print("开始验证全行业商业资源库扩展完整性...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        validation_results = {
            'tables_created': [],
            'tables_missing': [],
            'data_counts': {},
            'compatibility_checks': [],
            'overall_status': 'pending',
        }
        
        # 1. 检查表是否创建
        expected_tables = [
            'resource_categories',
            'industry_resources',
            'matching_criteria',
            'cross_industry_mappings',
            'resource_matches',
        ]
        
        for table in expected_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name = '{table}'")
            if cursor.fetchone():
                validation_results['tables_created'].append(table)
                
                # 获取数据量
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count_row = cursor.fetchone()
                validation_results['data_counts'][table] = count_row['count']
            else:
                validation_results['tables_missing'].append(table)
        
        # 2. 检查与现有系统的兼容性
        # 检查processed_opportunities表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = 'processed_opportunities'")
        if cursor.fetchone():
            validation_results['compatibility_checks'].append({
                'check': 'processed_opportunities_exists',
                'status': 'passed',
                'message': '现有商机表存在',
            })
        else:
            validation_results['compatibility_checks'].append({
                'check': 'processed_opportunities_exists',
                'status': 'failed',
                'message': '现有商机表不存在',
            })
        
        # 3. 检查分类数据是否完整
        cursor.execute("SELECT COUNT(*) as count FROM resource_categories WHERE category_type = 'industry'")
        industry_count = cursor.fetchone()['count']
        validation_results['compatibility_checks'].append({
            'check': 'industry_categories_count',
            'status': 'passed' if industry_count >= 5 else 'warning',
            'message': f'行业分类数量: {industry_count} (要求≥5)',
        })
        
        # 4. 总体状态评估
        if len(validation_results['tables_missing']) == 0:
            validation_results['overall_status'] = 'passed'
            print("✅ 扩展完整性验证通过")
        else:
            validation_results['overall_status'] = 'failed'
            print(f"❌ 扩展完整性验证失败，缺失表: {validation_results['tables_missing']}")
        
        self.close()
        
        return validation_results
    
    def generate_matching_examples(self, count: int = 10):
        """
        生成匹配示例
        
        Args:
            count: 生成的匹配示例数量
        """
        print(f"开始生成 {count} 个匹配示例...")
        
        conn = self.connect()
        cursor = conn.cursor()
        
        # 获取资源ID
        cursor.execute("SELECT resource_id, direction FROM industry_resources WHERE status = 'active' LIMIT 100")
        resources = cursor.fetchall()
        
        if len(resources) < 2:
            print("❌ 资源数量不足，请先生成样本数据")
            return 0
        
        generated_count = 0
        
        for i in range(min(count, len(resources) // 2)):
            # 选择一对供需资源
            supply_resources = [r for r in resources if r['direction'] in ['supply', 'both']]
            demand_resources = [r for r in resources if r['direction'] in ['demand', 'both']]
            
            if not supply_resources or not demand_resources:
                break
            
            supply = random.choice(supply_resources)
            demand = random.choice(demand_resources)
            
            # 确保不是同一个资源
            if supply['resource_id'] == demand['resource_id']:
                continue
            
            # 计算匹配分数
            match_score = random.uniform(0.6, 0.95)
            
            # 插入匹配记录
            cursor.execute("""
                INSERT OR IGNORE INTO resource_matches (
                    resource_a_id, resource_b_id, match_type,
                    match_score, match_reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                demand['resource_id'],  # 需求方
                supply['resource_id'],   # 供应方
                'auto',
                round(match_score, 2),
                f"基于行业相关性自动匹配，匹配度{match_score:.0%}",
                'pending',
                datetime.now().isoformat(),
            ))
            
            generated_count += 1
        
        conn.commit()
        self.close()
        
        print(f"✅ 匹配示例生成完成: {generated_count} 个")
        return generated_count


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='全行业商业资源库数据导入工具')
    parser.add_argument('--init', action='store_true', help='初始化数据库表结构')
    parser.add_argument('--import-opportunities', action='store_true', help='导入现有商机数据')
    parser.add_argument('--generate-samples', type=int, default=0, help='生成样本数据数量')
    parser.add_argument('--validate', action='store_true', help='验证扩展完整性')
    parser.add_argument('--generate-matches', type=int, default=0, help='生成匹配示例数量')
    parser.add_argument('--all', action='store_true', help='执行完整流程')
    
    args = parser.parse_args()
    
    importer = IndustryResourceImporter()
    
    if args.init or args.all:
        importer.execute_ddl()
    
    if args.import_opportunities or args.all:
        importer.import_existing_opportunities()
    
    if args.generate_samples > 0:
        importer.generate_sample_resources(args.generate_samples)
    
    if args.generate_matches > 0:
        importer.generate_matching_examples(args.generate_matches)
    
    if args.validate or args.all:
        results = importer.validate_extension()
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    if not any([args.init, args.import_opportunities, args.generate_samples, 
                args.validate, args.generate_matches, args.all]):
        parser.print_help()


if __name__ == '__main__':
    main()