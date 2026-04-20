#!/usr/bin/env python3
"""
达人洽谈军团 - 本土化英文话术引擎
支持寄样、佣金、专属码三种合作方案的话术模板与个性化填充
基于共享状态库 data/shared_state/state.db 实现合作名单管理和智能跟进系统
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import random
import hashlib
import os
import sys

class InfluencerOutreachEngine:
    """达人洽谈话术引擎主类"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化话术引擎
        
        Args:
            db_path: 共享状态库SQLite文件路径
        """
        self.db_path = db_path
        self.conn = None
        self._ensure_tables()
    
    def connect(self) -> sqlite3.Connection:
        """连接到数据库"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _ensure_tables(self):
        """确保达人合作相关表存在"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # 读取DDL文件并执行（如果表不存在）
        ddl_file = "docs/达人洽谈军团_DDL.sql"
        if os.path.exists(ddl_file):
            try:
                with open(ddl_file, 'r', encoding='utf-8') as f:
                    ddl_statements = f.read()
                # 分割SQL语句并执行
                statements = ddl_statements.split(';')
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt and not stmt.startswith('--'):
                        cursor.execute(stmt)
                conn.commit()
                print(f"达人合作表结构已确保，来自: {ddl_file}")
            except Exception as e:
                print(f"执行DDL时出错，可能表已存在: {e}")
                conn.rollback()
    
    # ==================== 达人基本信息管理 ====================
    
    def add_influencer_profile(
        self,
        influencer_id: str,
        platform: str,
        display_name: Optional[str] = None,
        follower_count: Optional[int] = None,
        engagement_rate: Optional[float] = None,
        niche: Optional[str] = None,
        contact_info: Optional[str] = None,
        profile_url: Optional[str] = None
    ) -> Tuple[bool, int, str]:
        """
        添加达人基本信息，实现去重
        
        Returns:
            (成功标志, 记录ID或现有记录ID, 消息)
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 检查是否已存在（去重）
            cursor.execute(
                "SELECT id FROM influencer_profiles WHERE influencer_id = ? AND platform = ?",
                (influencer_id, platform)
            )
            existing = cursor.fetchone()
            
            if existing:
                profile_id = existing['id']
                return False, profile_id, f"达人已存在，ID: {profile_id}"
            
            # 插入新记录
            cursor.execute("""
                INSERT INTO influencer_profiles 
                (influencer_id, platform, display_name, follower_count, engagement_rate, niche, contact_info, profile_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                influencer_id, platform, display_name, follower_count,
                engagement_rate, niche, contact_info, profile_url
            ))
            
            profile_id = cursor.lastrowid
            conn.commit()
            return True, profile_id, f"达人添加成功，ID: {profile_id}"
            
        except Exception as e:
            conn.rollback()
            return False, 0, f"添加达人失败: {e}"
    
    def get_influencer_profile(self, profile_id: int) -> Optional[Dict]:
        """获取达人详细信息"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM influencer_profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def search_influencers(
        self,
        platform: Optional[str] = None,
        niche: Optional[str] = None,
        min_followers: Optional[int] = None,
        max_followers: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """搜索符合条件的达人"""
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM influencer_profiles WHERE 1=1"
        params = []
        
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        
        if niche:
            query += " AND niche LIKE ?"
            params.append(f"%{niche}%")
        
        if min_followers is not None:
            query += " AND follower_count >= ?"
            params.append(min_followers)
        
        if max_followers is not None:
            query += " AND follower_count <= ?"
            params.append(max_followers)
        
        query += " ORDER BY follower_count DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== 合作名单管理 ====================
    
    def add_to_collaboration_list(
        self,
        profile_id: int,
        project_name: str,
        collaboration_type: str = "commission",
        priority_score: int = 50
    ) -> Tuple[bool, int, str]:
        """
        将达人添加到具体项目的合作名单
        
        Args:
            collaboration_type: sample, commission, exclusive_code
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 检查是否已在同一项目中
            cursor.execute("""
                SELECT id FROM influencer_collaboration_list 
                WHERE profile_id = ? AND project_name = ?
            """, (profile_id, project_name))
            
            if cursor.fetchone():
                return False, 0, "该达人已在此项目合作名单中"
            
            # 插入新记录
            cursor.execute("""
                INSERT INTO influencer_collaboration_list 
                (profile_id, project_name, collaboration_type, priority_score, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (profile_id, project_name, collaboration_type, priority_score))
            
            collab_id = cursor.lastrowid
            conn.commit()
            return True, collab_id, f"已添加到合作名单，ID: {collab_id}"
            
        except Exception as e:
            conn.rollback()
            return False, 0, f"添加到合作名单失败: {e}"
    
    def update_collaboration_status(
        self,
        collaboration_id: int,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """更新合作状态"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE influencer_collaboration_list 
                SET status = ?, notes = COALESCE(?, notes), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, notes, collaboration_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"更新状态失败: {e}")
            return False
    
    def get_pending_collaborations(
        self,
        project_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """获取待处理的合作名单"""
        conn = self.connect()
        cursor = conn.cursor()
        
        query = """
            SELECT cl.*, ip.display_name, ip.platform, ip.follower_count, ip.niche
            FROM influencer_collaboration_list cl
            JOIN influencer_profiles ip ON cl.profile_id = ip.id
            WHERE cl.status = 'pending'
        """
        params = []
        
        if project_name:
            query += " AND cl.project_name = ?"
            params.append(project_name)
        
        query += " ORDER BY cl.priority_score DESC, cl.created_at ASC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== 话术模板管理 ====================
    
    def get_template(
        self,
        template_type: str,
        platform: str = "generic",
        language: str = "en"
    ) -> Optional[Dict]:
        """获取指定类型、平台、语言的活跃模板"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM outreach_template_library 
            WHERE template_type = ? AND platform = ? AND language = ? AND is_active = 1
            ORDER BY expected_response_rate DESC LIMIT 1
        """, (template_type, platform, language))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_templates(
        self,
        template_type: Optional[str] = None,
        platform: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict]:
        """获取所有模板"""
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM outreach_template_library WHERE 1=1"
        params = []
        
        if template_type:
            query += " AND template_type = ?"
            params.append(template_type)
        
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY template_type, platform, language"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def add_template(
        self,
        template_name: str,
        template_type: str,
        platform: str,
        language: str,
        message_template: str,
        personalization_hints: str = "",
        expected_response_rate: float = 20.0,
        average_negotiation_days: int = 7
    ) -> Tuple[bool, int, str]:
        """添加新话术模板"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO outreach_template_library 
                (template_name, template_type, platform, language, message_template, 
                 personalization_hints, expected_response_rate, average_negotiation_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template_name, template_type, platform, language,
                message_template, personalization_hints,
                expected_response_rate, average_negotiation_days
            ))
            
            template_id = cursor.lastrowid
            conn.commit()
            return True, template_id, f"模板添加成功，ID: {template_id}"
            
        except Exception as e:
            conn.rollback()
            return False, 0, f"添加模板失败: {e}"
    
    # ==================== 个性化填充引擎 ====================
    
    def generate_personalized_message(
        self,
        template_type: str,
        influencer_info: Dict,
        product_info: Dict,
        platform: str = "generic",
        language: str = "en"
    ) -> Tuple[bool, str, Dict]:
        """
        生成个性化消息
        
        Args:
            template_type: sample, commission, exclusive_code
            influencer_info: 达人信息字典
            product_info: 产品信息字典
            platform: tiktok, youtube, instagram, xiaohongshu, generic
            language: en, zh
        
        Returns:
            (成功标志, 填充后消息, 占位符映射)
        """
        # 获取模板
        template = self.get_template(template_type, platform, language)
        if not template:
            # 降级到通用模板
            template = self.get_template(template_type, "generic", language)
            if not template:
                return False, "", {"error": f"未找到{template_type}类型的模板"}
        
        message_template = template['message_template']
        
        # 准备占位符数据
        placeholders = self._prepare_placeholders(influencer_info, product_info, template_type, platform)
        
        # 填充模板
        personalized_message = self._fill_template(message_template, placeholders)
        
        return True, personalized_message, placeholders
    
    def _prepare_placeholders(
        self,
        influencer_info: Dict,
        product_info: Dict,
        template_type: str,
        platform: str
    ) -> Dict:
        """准备占位符数据"""
        placeholders = {}
        
        # 基础占位符
        placeholders['[InfluencerName]'] = influencer_info.get('display_name', 'there')
        placeholders['[Platform]'] = platform.capitalize()
        
        # 产品信息
        placeholders['[ProductName]'] = product_info.get('name', 'our product')
        placeholders['[ProductDescription]'] = product_info.get('description', 'premium quality product')
        placeholders['[ProductCategory]'] = product_info.get('category', 'fashion item')
        placeholders['[BrandName]'] = product_info.get('brand', 'our brand')
        
        # 根据模板类型添加特定占位符
        if template_type == 'commission':
            commission_rate = product_info.get('commission_rate', 15)
            placeholders['[CommissionRate]'] = f"{commission_rate}%"
            
            # 估算收益
            price = product_info.get('price', 100)
            estimated_earnings = price * commission_rate / 100
            placeholders['[EstimatedEarnings]'] = f"${estimated_earnings:.2f}"
            
        elif template_type == 'exclusive_code':
            # 生成折扣码
            discount_code = self._generate_discount_code()
            placeholders['[DiscountCode]'] = discount_code
            
            discount_percentage = product_info.get('discount_percentage', 15)
            placeholders['[DiscountPercentage]'] = f"{discount_percentage}"
            
            valid_days = product_info.get('valid_days', 7)
            placeholders['[ValidDays]'] = f"{valid_days}"
            
            placeholders['[CommissionRate]'] = f"{product_info.get('exclusive_commission_rate', 10)}%"
        
        elif template_type == 'sample':
            # 寄样模板特定占位符
            placeholders['[RecentTopic]'] = influencer_info.get('recent_topic', 'fashion content')
            placeholders['[NicheFocus]'] = influencer_info.get('niche', 'fashion')
        
        # 添加当前日期
        placeholders['[CurrentDate]'] = datetime.now().strftime('%B %d, %Y')
        
        return placeholders
    
    def _generate_discount_code(self, length: int = 8) -> str:
        """生成折扣码"""
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _fill_template(self, template: str, placeholders: Dict) -> str:
        """填充模板"""
        result = template
        
        for placeholder, value in placeholders.items():
            result = result.replace(placeholder, str(value))
        
        return result
    
    # ==================== 批量私信与智能跟进 ====================
    
    def send_initial_contact(
        self,
        collaboration_id: int,
        influencer_info: Dict,
        product_info: Dict,
        platform: str = "generic"
    ) -> Tuple[bool, str, int]:
        """
        发送首次联系消息
        
        Returns:
            (成功标志, 消息内容, 跟进记录ID)
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 获取合作信息
            cursor.execute("""
                SELECT cl.*, ip.platform as influencer_platform, ip.language_preference
                FROM influencer_collaboration_list cl
                JOIN influencer_profiles ip ON cl.profile_id = ip.id
                WHERE cl.id = ?
            """, (collaboration_id,))
            
            collab_info = cursor.fetchone()
            if not collab_info:
                return False, "合作记录不存在", 0
            
            # 确定模板类型
            template_type = collab_info['collaboration_type']
            
            # 确定语言偏好
            language = collab_info.get('language_preference', 'en')
            if not language or language not in ['en', 'zh']:
                language = 'en'
            
            # 确定平台（优先使用达人平台）
            actual_platform = collab_info['influencer_platform'] or platform
            
            # 生成个性化消息
            success, message, placeholders = self.generate_personalized_message(
                template_type, influencer_info, product_info, actual_platform, language
            )
            
            if not success:
                return False, "生成消息失败", 0
            
            # 记录发送
            message_id = f"msg_{hashlib.md5(message.encode()).hexdigest()[:10]}"
            
            cursor.execute("""
                INSERT INTO influencer_followup_logs 
                (collaboration_id, followup_type, message_content, platform_message_id, sent_at)
                VALUES (?, 'initial_contact', ?, ?, CURRENT_TIMESTAMP)
            """, (collaboration_id, message, message_id))
            
            followup_id = cursor.lastrowid
            
            # 更新合作状态
            cursor.execute("""
                UPDATE influencer_collaboration_list 
                SET status = 'contacted', initial_contact_date = CURRENT_TIMESTAMP,
                    last_contact_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (collaboration_id,))
            
            # 计算下次跟进时间
            self._calculate_next_followup(collaboration_id, 'initial_contact')
            
            conn.commit()
            return True, message, followup_id
            
        except Exception as e:
            conn.rollback()
            return False, f"发送消息失败: {e}", 0
    
    def _calculate_next_followup(self, collaboration_id: int, last_action: str):
        """计算下次跟进时间"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 获取智能跟进配置
            cursor.execute("""
                SELECT * FROM followup_smart_config 
                WHERE current_status = (
                    SELECT status FROM influencer_collaboration_list WHERE id = ?
                )
                AND action_type LIKE 'send_followup%'
                ORDER BY days_delay ASC LIMIT 1
            """, (collaboration_id,))
            
            config = cursor.fetchone()
            
            if config:
                days_delay = config['days_delay']
                next_date = datetime.now() + timedelta(days=days_delay)
                
                cursor.execute("""
                    UPDATE influencer_collaboration_list 
                    SET next_followup_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (next_date.strftime('%Y-%m-%d %H:%M:%S'), collaboration_id))
            
        except Exception as e:
            print(f"计算下次跟进时间失败: {e}")
    
    def get_due_followups(self) -> List[Dict]:
        """获取到期的跟进任务"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cl.*, ip.display_name, ip.platform, ip.contact_info
            FROM influencer_collaboration_list cl
            JOIN influencer_profiles ip ON cl.profile_id = ip.id
            WHERE cl.next_followup_date IS NOT NULL 
            AND cl.next_followup_date <= CURRENT_TIMESTAMP
            AND cl.status IN ('contacted', 'replied', 'negotiating')
            ORDER BY cl.priority_score DESC, cl.next_followup_date ASC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def log_response(
        self,
        followup_id: int,
        response_content: str,
        sentiment_score: Optional[float] = None
    ) -> bool:
        """记录达人回复"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 获取关联的合作ID
            cursor.execute("""
                SELECT collaboration_id FROM influencer_followup_logs WHERE id = ?
            """, (followup_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            collaboration_id = row['collaboration_id']
            
            # 更新跟进记录
            cursor.execute("""
                UPDATE influencer_followup_logs 
                SET response_received = 1, response_content = ?, 
                    response_time = CURRENT_TIMESTAMP, sentiment_score = ?
                WHERE id = ?
            """, (response_content, sentiment_score, followup_id))
            
            # 更新合作状态
            # 简单判断：如果回复内容积极，标记为已回复积极
            is_positive = False
            if sentiment_score is not None:
                is_positive = sentiment_score > 0.3
            else:
                # 简单关键词判断
                positive_keywords = ['interested', 'yes', 'sure', 'love', 'great', 'awesome', 'good']
                lower_response = response_content.lower()
                is_positive = any(keyword in lower_response for keyword in positive_keywords)
            
            new_status = 'replied_positive' if is_positive else 'replied'
            cursor.execute("""
                UPDATE influencer_collaboration_list 
                SET status = ?, response_received = 1, response_positive = ?,
                    last_contact_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, 1 if is_positive else 0, collaboration_id))
            
            # 重新计算下次跟进时间
            self._calculate_next_followup(collaboration_id, 'response_received')
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"记录回复失败: {e}")
            return False
    
    # ==================== 统计分析 ====================
    
    def get_campaign_stats(self, project_name: str) -> Dict:
        """获取项目统计数据"""
        conn = self.connect()
        cursor = conn.cursor()
        
        stats = {}
        
        # 总体统计
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'contacted' THEN 1 ELSE 0 END) as contacted,
                SUM(CASE WHEN status = 'replied' THEN 1 ELSE 0 END) as replied,
                SUM(CASE WHEN status = 'replied_positive' THEN 1 ELSE 0 END) as replied_positive,
                SUM(CASE WHEN status = 'negotiating' THEN 1 ELSE 0 END) as negotiating,
                SUM(CASE WHEN status = 'contracted' THEN 1 ELSE 0 END) as contracted,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END) as archived
            FROM influencer_collaboration_list 
            WHERE project_name = ?
        """, (project_name,))
        
        row = cursor.fetchone()
        if row:
            stats.update(dict(row))
            
            # 计算通过率
            total_contacted = stats.get('contacted', 0) + stats.get('replied', 0) + stats.get('replied_positive', 0) + stats.get('negotiating', 0)
            if total_contacted > 0:
                stats['response_rate'] = (stats.get('replied', 0) + stats.get('replied_positive', 0)) / total_contacted * 100
            else:
                stats['response_rate'] = 0.0
        
        return stats
    
    def export_collaboration_list(self, project_name: str, format: str = "json") -> str:
        """导出合作名单"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                cl.*,
                ip.display_name, ip.platform, ip.follower_count, ip.engagement_rate, 
                ip.niche, ip.contact_info, ip.profile_url
            FROM influencer_collaboration_list cl
            JOIN influencer_profiles ip ON cl.profile_id = ip.id
            WHERE cl.project_name = ?
            ORDER BY cl.priority_score DESC, cl.created_at ASC
        """, (project_name,))
        
        rows = [dict(row) for row in cursor.fetchall()]
        
        if format == "json":
            return json.dumps(rows, indent=2, ensure_ascii=False)
        elif format == "csv":
            # 简单CSV转换
            import csv
            import io
            
            if not rows:
                return ""
            
            output = io.StringIO()
            fieldnames = rows[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            return output.getvalue()
        
        return ""

# ==================== 辅助函数 ====================

def test_influencer_engine():
    """测试话术引擎"""
    engine = InfluencerOutreachEngine()
    
    print("=== 测试达人洽谈话术引擎 ===")
    
    # 测试添加达人
    print("\n1. 添加达人测试:")
    success, profile_id, msg = engine.add_influencer_profile(
        influencer_id="fashionista_jane",
        platform="tiktok",
        display_name="Jane Doe",
        follower_count=150000,
        engagement_rate=4.2,
        niche="fashion",
        contact_info="jane@example.com",
        profile_url="https://tiktok.com/@fashionista_jane"
    )
    print(f"   {msg}")
    
    # 测试添加模板（如果不存在）
    print("\n2. 模板测试:")
    templates = engine.get_all_templates()
    print(f"   现有模板数量: {len(templates)}")
    
    # 测试生成消息
    print("\n3. 生成个性化消息测试:")
    influencer_info = {
        'display_name': 'Jane Doe',
        'recent_topic': 'fall fashion trends',
        'niche': 'fashion'
    }
    
    product_info = {
        'name': '750g美式复古牛仔外套',
        'description': 'heavyweight denim jacket with vintage wash',
        'brand': 'DenimCraft',
        'price': 129.99,
        'commission_rate': 15,
        'discount_percentage': 15,
        'valid_days': 7
    }
    
    for template_type in ['sample', 'commission', 'exclusive_code']:
        success, message, placeholders = engine.generate_personalized_message(
            template_type, influencer_info, product_info, 'tiktok', 'en'
        )
        
        if success:
            print(f"   {template_type}模板消息生成成功")
            print(f"   消息预览: {message[:100]}...")
        else:
            print(f"   {template_type}模板消息生成失败")
    
    # 测试添加到合作名单
    print("\n4. 合作名单测试:")
    if success and profile_id:
        success2, collab_id, msg2 = engine.add_to_collaboration_list(
            profile_id=profile_id,
            project_name="750g美式复古牛仔外套推广",
            collaboration_type="commission"
        )
        print(f"   {msg2}")
    
    # 测试统计数据
    print("\n5. 统计数据测试:")
    stats = engine.get_campaign_stats("750g美式复古牛仔外套推广")
    print(f"   项目统计: {stats}")
    
    engine.close()
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    # 直接运行此文件时执行测试
    test_influencer_engine()