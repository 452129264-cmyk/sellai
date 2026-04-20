#!/usr/bin/env python3
"""
社交关系管理器
负责管理用户与AI分身之间的社交关系、AI之间的私下通信，
以及用户的隐私设置和社交边界管控。
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SocialRelationshipManager:
    """社交关系管理类"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化社交关系管理器
        
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
        """确保社交关系相关表存在"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # 1. 用户-分身社交关系表（支持双社交体系）
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
        
        # 2. AI-AI私下通信记录表
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
        
        # 3. 用户隐私设置表
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
        
        # 为社交关系表创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_avatar_relations ON user_avatar_relationships(user_id, avatar_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_communications ON ai_ai_communications(sender_avatar_id, receiver_avatar_id, timestamp)")
        
        conn.commit()
        self.close()
        logger.info("社交关系表初始化完成")
    
    # ===================== 用户-AI社交关系管理 =====================
    
    def add_ai_friend(self, user_id: str, avatar_id: str, metadata: Optional[Dict] = None) -> bool:
        """
        添加AI分身为好友
        
        Args:
            user_id: 用户ID
            avatar_id: AI分身ID
            metadata: 额外元数据
        
        Returns:
            是否成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_avatar_relationships 
                (user_id, avatar_id, relationship_type, created_at, last_interaction, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                avatar_id,
                'friend',
                now,
                now,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            
            conn.commit()
            logger.info(f"用户 {user_id} 添加AI分身 {avatar_id} 为好友")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"添加AI好友失败: {e}")
            return False
            
        finally:
            self.close()
    
    def remove_ai_friend(self, user_id: str, avatar_id: str) -> bool:
        """
        移除AI分身好友
        
        Args:
            user_id: 用户ID
            avatar_id: AI分身ID
        
        Returns:
            是否成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM user_avatar_relationships 
                WHERE user_id = ? AND avatar_id = ?
            """, (user_id, avatar_id))
            
            conn.commit()
            logger.info(f"用户 {user_id} 移除AI分身 {avatar_id} 好友")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"移除AI好友失败: {e}")
            return False
            
        finally:
            self.close()
    
    def block_ai(self, user_id: str, avatar_id: str) -> bool:
        """
        屏蔽AI分身（禁止其主动发起聊天）
        
        Args:
            user_id: 用户ID
            avatar_id: AI分身ID
        
        Returns:
            是否成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_avatar_relationships 
                (user_id, avatar_id, relationship_type, created_at, last_interaction, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                avatar_id,
                'blocked',
                now,
                now,
                json.dumps({"reason": "user_blocked"}, ensure_ascii=False)
            ))
            
            conn.commit()
            logger.info(f"用户 {user_id} 屏蔽AI分身 {avatar_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"屏蔽AI分身失败: {e}")
            return False
            
        finally:
            self.close()
    
    def get_user_ai_friends(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的AI分身好友列表
        
        Args:
            user_id: 用户ID
        
        Returns:
            AI好友列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    uar.relationship_id,
                    uar.user_id,
                    uar.avatar_id,
                    uar.relationship_type,
                    uar.created_at,
                    uar.last_interaction,
                    uar.metadata,
                    acp.avatar_name,
                    acp.capability_scores,
                    acp.specialization_tags
                FROM user_avatar_relationships uar
                LEFT JOIN avatar_capability_profiles acp ON uar.avatar_id = acp.avatar_id
                WHERE uar.user_id = ? AND uar.relationship_type = 'friend'
                ORDER BY uar.last_interaction DESC
            """, (user_id,))
            
            friends = []
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                except:
                    metadata = {}
                
                try:
                    capability_scores = json.loads(row['capability_scores']) if row['capability_scores'] else {}
                except:
                    capability_scores = {}
                
                try:
                    specialization_tags = json.loads(row['specialization_tags']) if row['specialization_tags'] else []
                except:
                    specialization_tags = []
                
                friends.append({
                    'relationship_id': row['relationship_id'],
                    'user_id': row['user_id'],
                    'avatar_id': row['avatar_id'],
                    'relationship_type': row['relationship_type'],
                    'created_at': row['created_at'],
                    'last_interaction': row['last_interaction'],
                    'metadata': metadata,
                    'avatar_name': row['avatar_name'],
                    'capability_scores': capability_scores,
                    'specialization_tags': specialization_tags
                })
            
            return friends
            
        finally:
            self.close()
    
    def can_ai_initiate_chat(self, avatar_id: str, target_user_id: str) -> bool:
        """
        检查AI分身是否可以主动向用户发起聊天
        
        Args:
            avatar_id: AI分身ID
            target_user_id: 目标用户ID
        
        Returns:
            是否允许
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 1. 检查用户隐私设置
            cursor.execute("""
                SELECT allow_ai_initiated_chat 
                FROM user_privacy_settings 
                WHERE user_id = ?
            """, (target_user_id,))
            
            privacy_row = cursor.fetchone()
            if privacy_row and privacy_row['allow_ai_initiated_chat'] == 0:
                logger.debug(f"用户 {target_user_id} 禁止所有AI主动聊天")
                return False
            
            # 2. 检查具体AI分身是否被屏蔽
            cursor.execute("""
                SELECT relationship_type 
                FROM user_avatar_relationships 
                WHERE user_id = ? AND avatar_id = ?
            """, (target_user_id, avatar_id))
            
            relation_row = cursor.fetchone()
            if relation_row and relation_row['relationship_type'] == 'blocked':
                logger.debug(f"用户 {target_user_id} 屏蔽了AI分身 {avatar_id}")
                return False
            
            return True
            
        finally:
            self.close()
    
    # ===================== AI-AI私下通信管理 =====================
    
    def record_ai_ai_communication(self, sender_avatar_id: str, receiver_avatar_id: str,
                                 content: str, content_type: str = "text",
                                 metadata: Optional[Dict] = None) -> int:
        """
        记录AI-AI私下通信
        
        Args:
            sender_avatar_id: 发送方AI分身ID
            receiver_avatar_id: 接收方AI分身ID
            content: 通信内容
            content_type: 内容类型
            metadata: 额外元数据
        
        Returns:
            通信记录ID
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO ai_ai_communications 
                (sender_avatar_id, receiver_avatar_id, content, content_type, 
                 timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sender_avatar_id,
                receiver_avatar_id,
                content,
                content_type,
                now,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            
            communication_id = cursor.lastrowid
            
            conn.commit()
            logger.info(f"AI-AI通信记录: {sender_avatar_id} -> {receiver_avatar_id}, 类型: {content_type}")
            
            return communication_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"记录AI-AI通信失败: {e}")
            raise
            
        finally:
            self.close()
    
    def get_ai_ai_communications(self, sender_avatar_id: Optional[str] = None,
                               receiver_avatar_id: Optional[str] = None,
                               content_type: Optional[str] = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取AI-AI通信记录
        
        Args:
            sender_avatar_id: 发送方AI分身ID
            receiver_avatar_id: 接收方AI分身ID
            content_type: 内容类型
            limit: 返回数量限制
        
        Returns:
            通信记录列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    communication_id,
                    sender_avatar_id,
                    receiver_avatar_id,
                    content,
                    content_type,
                    timestamp,
                    is_opportunity_synced,
                    synced_to_user_id,
                    synced_at,
                    metadata
                FROM ai_ai_communications 
                WHERE 1=1
            """
            params = []
            
            if sender_avatar_id:
                query += " AND sender_avatar_id = ?"
                params.append(sender_avatar_id)
            
            if receiver_avatar_id:
                query += " AND receiver_avatar_id = ?"
                params.append(receiver_avatar_id)
            
            if content_type:
                query += " AND content_type = ?"
                params.append(content_type)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            communications = []
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                except:
                    metadata = {}
                
                communications.append({
                    'communication_id': row['communication_id'],
                    'sender_avatar_id': row['sender_avatar_id'],
                    'receiver_avatar_id': row['receiver_avatar_id'],
                    'content': row['content'],
                    'content_type': row['content_type'],
                    'timestamp': row['timestamp'],
                    'is_opportunity_synced': bool(row['is_opportunity_synced']),
                    'synced_to_user_id': row['synced_to_user_id'],
                    'synced_at': row['synced_at'],
                    'metadata': metadata
                })
            
            return communications
            
        finally:
            self.close()
    
    def get_high_value_opportunities_from_ai(self, user_id: str, min_priority: int = 3) -> List[Dict[str, Any]]:
        """
        获取AI-AI通信中的高价值商机（一键同步给用户）
        
        Args:
            user_id: 用户ID
            min_priority: 最低优先级阈值（1-5，数字越大优先级越高）
        
        Returns:
            高价值商机列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    communication_id,
                    sender_avatar_id,
                    receiver_avatar_id,
                    content,
                    content_type,
                    timestamp,
                    metadata
                FROM ai_ai_communications 
                WHERE content_type = 'opportunity' 
                  AND is_opportunity_synced = 0
                  AND (metadata LIKE ? OR metadata LIKE ?)
                ORDER BY timestamp DESC
                LIMIT 50
            """, (
                f'%"priority"%: {min_priority}%',
                f'%"priority"%: {min_priority + 1}%'
            ))
            
            opportunities = []
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    priority = metadata.get('priority', 1)
                    
                    # 检查是否满足优先级要求
                    if priority >= min_priority:
                        opportunities.append({
                            'communication_id': row['communication_id'],
                            'sender_avatar_id': row['sender_avatar_id'],
                            'receiver_avatar_id': row['receiver_avatar_id'],
                            'content': row['content'],
                            'content_type': row['content_type'],
                            'timestamp': row['timestamp'],
                            'metadata': metadata,
                            'priority': priority
                        })
                        
                except Exception as e:
                    logger.warning(f"解析商机元数据失败: {e}")
                    continue
            
            return opportunities
            
        finally:
            self.close()
    
    def sync_opportunity_to_user(self, communication_id: int, user_id: str) -> bool:
        """
        将AI-AI通信中的高价值商机同步给用户
        
        Args:
            communication_id: 通信记录ID
            user_id: 用户ID
        
        Returns:
            是否成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            
            cursor.execute("""
                UPDATE ai_ai_communications 
                SET is_opportunity_synced = 1,
                    synced_to_user_id = ?,
                    synced_at = ?
                WHERE communication_id = ?
            """, (user_id, now, communication_id))
            
            conn.commit()
            logger.info(f"商机同步成功: 通信ID {communication_id} -> 用户 {user_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"同步商机失败: {e}")
            return False
            
        finally:
            self.close()
    
    # ===================== 用户隐私设置管理 =====================
    
    def set_user_privacy_settings(self, user_id: str, **settings) -> bool:
        """
        设置用户隐私选项
        
        Args:
            user_id: 用户ID
            **settings: 隐私设置键值对，支持：
                - allow_ai_initiated_chat: 允许AI主动发起聊天
                - show_opportunity_push: 显示商机推送
                - allow_ai_ai_collaboration_visibility: 允许查看AI间协作
                - auto_add_ai_friends: 自动添加AI分身为好友
        
        Returns:
            是否成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            
            # 检查是否存在设置
            cursor.execute("SELECT user_id FROM user_privacy_settings WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone() is not None
            
            # 构建设置字典
            default_settings = {
                'allow_ai_initiated_chat': 1,
                'show_opportunity_push': 1,
                'allow_ai_ai_collaboration_visibility': 1,
                'auto_add_ai_friends': 1
            }
            
            # 更新用户提供的设置
            for key, value in settings.items():
                if key in default_settings:
                    if isinstance(value, bool):
                        default_settings[key] = 1 if value else 0
                    else:
                        default_settings[key] = int(value)
            
            if exists:
                # 更新现有设置
                cursor.execute("""
                    UPDATE user_privacy_settings 
                    SET allow_ai_initiated_chat = ?,
                        show_opportunity_push = ?,
                        allow_ai_ai_collaboration_visibility = ?,
                        auto_add_ai_friends = ?,
                        updated_at = ?
                    WHERE user_id = ?
                """, (
                    default_settings['allow_ai_initiated_chat'],
                    default_settings['show_opportunity_push'],
                    default_settings['allow_ai_ai_collaboration_visibility'],
                    default_settings['auto_add_ai_friends'],
                    now,
                    user_id
                ))
            else:
                # 插入新设置
                cursor.execute("""
                    INSERT INTO user_privacy_settings 
                    (user_id, allow_ai_initiated_chat, show_opportunity_push, 
                     allow_ai_ai_collaboration_visibility, auto_add_ai_friends, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    default_settings['allow_ai_initiated_chat'],
                    default_settings['show_opportunity_push'],
                    default_settings['allow_ai_ai_collaboration_visibility'],
                    default_settings['auto_add_ai_friends'],
                    now
                ))
            
            conn.commit()
            logger.info(f"用户隐私设置更新: {user_id}, 设置: {settings}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"更新隐私设置失败: {e}")
            return False
            
        finally:
            self.close()
    
    def get_user_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户隐私设置
        
        Args:
            user_id: 用户ID
        
        Returns:
            隐私设置字典
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM user_privacy_settings WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row['user_id'],
                    'allow_ai_initiated_chat': bool(row['allow_ai_initiated_chat']),
                    'show_opportunity_push': bool(row['show_opportunity_push']),
                    'allow_ai_ai_collaboration_visibility': bool(row['allow_ai_ai_collaboration_visibility']),
                    'auto_add_ai_friends': bool(row['auto_add_ai_friends']),
                    'updated_at': row['updated_at']
                }
            
            # 返回默认设置
            return {
                'user_id': user_id,
                'allow_ai_initiated_chat': True,
                'show_opportunity_push': True,
                'allow_ai_ai_collaboration_visibility': True,
                'auto_add_ai_friends': True,
                'updated_at': datetime.now().isoformat()
            }
            
        finally:
            self.close()
    
    def should_show_opportunity_push(self, user_id: str) -> bool:
        """
        检查是否应向用户显示商机推送
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否显示
        """
        settings = self.get_user_privacy_settings(user_id)
        return settings.get('show_opportunity_push', True)
    
    # ===================== 工具方法 =====================
    
    def get_ai_friend_recommendations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        根据用户画像推荐AI分身好友
        
        Args:
            user_id: 用户ID
            limit: 推荐数量限制
        
        Returns:
            AI分身推荐列表
        """
        # TODO: 实现基于用户画像的推荐算法
        # 暂时返回一个空列表
        return []
    
    def get_social_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取社交关系统计信息
        
        Args:
            user_id: 指定用户ID，为空则获取系统整体统计
        
        Returns:
            统计信息字典
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            if user_id:
                # 用户特定统计
                cursor.execute("""
                    SELECT COUNT(*) as total_ai_friends 
                    FROM user_avatar_relationships 
                    WHERE user_id = ? AND relationship_type = 'friend'
                """, (user_id,))
                total_ai_friends = cursor.fetchone()['total_ai_friends']
                
                cursor.execute("""
                    SELECT COUNT(*) as blocked_ais 
                    FROM user_avatar_relationships 
                    WHERE user_id = ? AND relationship_type = 'blocked'
                """, (user_id,))
                blocked_ais = cursor.fetchone()['blocked_ais']
                
                return {
                    'user_id': user_id,
                    'total_ai_friends': total_ai_friends,
                    'blocked_ais': blocked_ais
                }
            else:
                # 系统整体统计
                cursor.execute("SELECT COUNT(DISTINCT user_id) as total_users FROM user_avatar_relationships")
                total_users = cursor.fetchone()['total_users']
                
                cursor.execute("SELECT COUNT(*) as total_relationships FROM user_avatar_relationships")
                total_relationships = cursor.fetchone()['total_relationships']
                
                cursor.execute("SELECT COUNT(*) as total_ai_communications FROM ai_ai_communications")
                total_ai_communications = cursor.fetchone()['total_ai_communications']
                
                return {
                    'total_users': total_users,
                    'total_relationships': total_relationships,
                    'total_ai_communications': total_ai_communications
                }
                
        finally:
            self.close()


# 单例模式，便于全局使用
_social_relationship_manager = None

def get_social_relationship_manager() -> SocialRelationshipManager:
    """获取社交关系管理器单例"""
    global _social_relationship_manager
    if _social_relationship_manager is None:
        _social_relationship_manager = SocialRelationshipManager()
    return _social_relationship_manager


# 提供简单的函数接口
def add_ai_friend(user_id: str, avatar_id: str, metadata: Optional[Dict] = None) -> bool:
    """添加AI分身为好友"""
    manager = get_social_relationship_manager()
    return manager.add_ai_friend(user_id, avatar_id, metadata)

def block_ai(user_id: str, avatar_id: str) -> bool:
    """屏蔽AI分身"""
    manager = get_social_relationship_manager()
    return manager.block_ai(user_id, avatar_id)

def get_user_ai_friends(user_id: str) -> List[Dict[str, Any]]:
    """获取用户的AI分身好友列表"""
    manager = get_social_relationship_manager()
    return manager.get_user_ai_friends(user_id)

def sync_high_value_opportunities(user_id: str, min_priority: int = 3) -> List[Dict[str, Any]]:
    """同步高价值商机给用户"""
    manager = get_social_relationship_manager()
    return manager.get_high_value_opportunities_from_ai(user_id, min_priority)

def set_privacy_settings(user_id: str, **settings) -> bool:
    """设置用户隐私选项"""
    manager = get_social_relationship_manager()
    return manager.set_user_privacy_settings(user_id, **settings)


# 测试代码
if __name__ == "__main__":
    # 初始化管理器
    manager = SocialRelationshipManager()
    
    print("社交关系管理器初始化完成")
    print(f"数据库路径: {manager.db_path}")
    
    # 测试添加AI好友
    success = manager.add_ai_friend("user001", "intelligence_officer", {"notes": "主要商务对接"})
    print(f"添加AI好友: {'成功' if success else '失败'}")
    
    # 测试获取用户AI好友列表
    friends = manager.get_user_ai_friends("user001")
    print(f"用户AI好友数: {len(friends)}")
    
    # 测试AI-AI通信记录
    comm_id = manager.record_ai_ai_communication(
        sender_avatar_id="intelligence_officer",
        receiver_avatar_id="content_officer",
        content="发现高利润牛仔外套商机，利润率42%",
        content_type="opportunity",
        metadata={"priority": 4, "tags": ["high_value", "urgent"]}
    )
    print(f"AI-AI通信记录ID: {comm_id}")
    
    # 测试获取高价值商机
    opportunities = manager.get_high_value_opportunities_from_ai("user001", min_priority=3)
    print(f"高价值商机数: {len(opportunities)}")
    
    # 测试隐私设置
    success = manager.set_user_privacy_settings(
        "user001",
        allow_ai_initiated_chat=True,
        show_opportunity_push=True
    )
    print(f"隐私设置更新: {'成功' if success else '失败'}")
    
    # 测试获取隐私设置
    privacy = manager.get_user_privacy_settings("user001")
    print(f"隐私设置: {privacy}")
    
    # 测试统计信息
    stats = manager.get_social_statistics("user001")
    print(f"用户社交统计: {stats}")
    
    print("\n社交关系管理器测试完成")