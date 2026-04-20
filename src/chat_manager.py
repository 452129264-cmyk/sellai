#!/usr/bin/env python3
"""
聊天消息管理器
负责聊天消息的存储、检索和持久化，与共享状态库集成
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import logging

logger = logging.getLogger(__name__)

class ChatManager:
    """聊天消息管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化聊天管理器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self._ensure_chat_tables()
    
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
    
    def _ensure_chat_tables(self):
        """确保聊天相关表存在"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # 1. 聊天房间表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_rooms (
                room_id TEXT PRIMARY KEY,
                room_type TEXT CHECK(room_type IN ('private', 'group')) NOT NULL,
                room_name TEXT,
                creator_id TEXT,
                created_at TIMESTAMP NOT NULL,
                last_activity TIMESTAMP NOT NULL,
                metadata TEXT  -- JSON格式额外信息
            )
        """)
        
        # 2. 房间成员表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS room_members (
                room_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                joined_at TIMESTAMP NOT NULL,
                last_read TIMESTAMP,
                PRIMARY KEY (room_id, user_id),
                FOREIGN KEY (room_id) REFERENCES chat_rooms(room_id) ON DELETE CASCADE
            )
        """)
        
        # 3. 聊天消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                content TEXT NOT NULL,
                message_type TEXT CHECK(message_type IN ('text', 'image', 'file', 'opportunity', 'system')) DEFAULT 'text',
                timestamp TIMESTAMP NOT NULL,
                metadata TEXT,  -- JSON格式额外信息
                is_deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES chat_rooms(room_id) ON DELETE CASCADE
            )
        """)
        
        # 4. 消息状态表（已读/送达状态）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_status (
                message_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT CHECK(status IN ('sent', 'delivered', 'read')) DEFAULT 'sent',
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (message_id, user_id),
                FOREIGN KEY (message_id) REFERENCES chat_messages(message_id) ON DELETE CASCADE
            )
        """)
        
        # 5. 用户在线状态表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_presence (
                user_id TEXT PRIMARY KEY,
                is_online BOOLEAN DEFAULT 0,
                last_seen TIMESTAMP NOT NULL,
                device_info TEXT,  -- JSON格式设备信息
                socket_id TEXT  -- SocketIO连接ID
            )
        """)
        
        conn.commit()
        logger.info("聊天表初始化完成")
    
    # 房间管理方法
    def create_private_room(self, user1_id: str, user2_id: str) -> str:
        """
        创建一对一私聊房间
        
        Args:
            user1_id: 用户1 ID
            user2_id: 用户2 ID
            
        Returns:
            房间ID
        """
        # 生成房间ID（按字母顺序排序确保唯一性）
        sorted_ids = sorted([user1_id, user2_id])
        room_id = f"private_{sorted_ids[0]}_{sorted_ids[1]}"
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 检查房间是否已存在
            cursor.execute("SELECT room_id FROM chat_rooms WHERE room_id = ?", (room_id,))
            existing = cursor.fetchone()
            
            if not existing:
                # 创建房间
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO chat_rooms (room_id, room_type, room_name, creator_id, created_at, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (room_id, 'private', None, user1_id, now, now))
                
                # 添加成员
                cursor.execute("""
                    INSERT INTO room_members (room_id, user_id, joined_at)
                    VALUES (?, ?, ?)
                """, (room_id, user1_id, now))
                
                cursor.execute("""
                    INSERT INTO room_members (room_id, user_id, joined_at)
                    VALUES (?, ?, ?)
                """, (room_id, user2_id, now))
                
                conn.commit()
                logger.info(f"创建私聊房间: {room_id} ({user1_id} <-> {user2_id})")
            
            return room_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"创建私聊房间失败: {e}")
            raise
    
    def create_group_room(self, creator_id: str, room_name: str, member_ids: List[str]) -> str:
        """
        创建群聊房间
        
        Args:
            creator_id: 创建者ID
            room_name: 房间名称
            member_ids: 成员ID列表
            
        Returns:
            房间ID
        """
        # 生成唯一房间ID
        room_id = f"group_{uuid.uuid4().hex[:8]}"
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 创建房间
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO chat_rooms (room_id, room_type, room_name, creator_id, created_at, last_activity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (room_id, 'group', room_name, creator_id, now, now))
            
            # 添加所有成员
            for user_id in member_ids:
                cursor.execute("""
                    INSERT INTO room_members (room_id, user_id, joined_at)
                    VALUES (?, ?, ?)
                """, (room_id, user_id, now))
            
            conn.commit()
            logger.info(f"创建群聊房间: {room_id} ({room_name}), 成员数: {len(member_ids)}")
            
            return room_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"创建群聊房间失败: {e}")
            raise
    
    def get_user_rooms(self, user_id: str) -> List[Dict]:
        """
        获取用户所在的房间列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            房间信息列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                cr.room_id, 
                cr.room_type, 
                cr.room_name, 
                cr.creator_id,
                cr.created_at,
                cr.last_activity,
                (SELECT COUNT(*) FROM room_members rm WHERE rm.room_id = cr.room_id) as member_count,
                (SELECT MAX(timestamp) FROM chat_messages cm WHERE cm.room_id = cr.room_id) as last_message_time
            FROM chat_rooms cr
            INNER JOIN room_members rm ON cr.room_id = rm.room_id
            WHERE rm.user_id = ?
            ORDER BY cr.last_activity DESC
        """, (user_id,))
        
        rooms = []
        for row in cursor.fetchall():
            rooms.append({
                'room_id': row['room_id'],
                'room_type': row['room_type'],
                'room_name': row['room_name'] or self._generate_room_name(row['room_id'], user_id),
                'creator_id': row['creator_id'],
                'created_at': row['created_at'],
                'last_activity': row['last_activity'],
                'member_count': row['member_count'],
                'last_message_time': row['last_message_time']
            })
        
        return rooms
    
    def _generate_room_name(self, room_id: str, current_user_id: str) -> str:
        """为私聊房间生成显示名称（显示对方用户名）"""
        if room_id.startswith('private_'):
            # 提取两个用户ID
            parts = room_id.split('_')
            if len(parts) == 3:
                user1_id, user2_id = parts[1], parts[2]
                other_user_id = user1_id if user2_id == current_user_id else user2_id
                return f"与 {other_user_id} 的私聊"
        
        return "未知房间"
    
    # 消息管理方法
    def add_message(self, room_id: str, sender_id: str, content: str, 
                   message_type: str = "text", metadata: Dict = None) -> Dict:
        """
        添加消息到聊天记录
        
        Args:
            room_id: 房间ID
            sender_id: 发送者ID
            content: 消息内容
            message_type: 消息类型（text, image, file, opportunity, system）
            metadata: 额外元数据
            
        Returns:
            消息信息字典
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 插入消息
            cursor.execute("""
                INSERT INTO chat_messages (message_id, room_id, sender_id, content, message_type, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                message_id, room_id, sender_id, content, message_type, timestamp,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            
            # 更新房间最后活动时间
            cursor.execute("""
                UPDATE chat_rooms 
                SET last_activity = ?
                WHERE room_id = ?
            """, (timestamp, room_id))
            
            # 为房间内的每个成员创建初始消息状态
            cursor.execute("SELECT user_id FROM room_members WHERE room_id = ?", (room_id,))
            members = cursor.fetchall()
            
            for member in members:
                member_id = member['user_id']
                # 发送者标记为已送达，其他成员标记为已发送
                status = 'delivered' if member_id == sender_id else 'sent'
                cursor.execute("""
                    INSERT INTO message_status (message_id, user_id, status, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (message_id, member_id, status, timestamp))
            
            conn.commit()
            
            # 构建返回的消息对象
            message = {
                'id': message_id,
                'room_id': room_id,
                'sender_id': sender_id,
                'content': content,
                'type': message_type,
                'timestamp': timestamp,
                'metadata': metadata or {}
            }
            
            logger.info(f"消息存储成功: {message_id}, 房间: {room_id}, 发送者: {sender_id}")
            
            return message
            
        except Exception as e:
            conn.rollback()
            logger.error(f"添加消息失败: {e}")
            raise
    
    def get_messages(self, room_id: str, limit: int = 100, 
                    before_timestamp: str = None) -> List[Dict]:
        """
        获取聊天记录
        
        Args:
            room_id: 房间ID
            limit: 消息数量限制
            before_timestamp: 获取此时间之前的消息
            
        Returns:
            消息列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                cm.message_id as id,
                cm.room_id,
                cm.sender_id,
                cm.content,
                cm.message_type as type,
                cm.timestamp,
                cm.metadata,
                ms.status
            FROM chat_messages cm
            LEFT JOIN message_status ms ON cm.message_id = ms.message_id AND ms.user_id = ?
            WHERE cm.room_id = ? AND cm.is_deleted = 0
        """
        
        params = ['system', room_id]  # 使用system作为占位符，实际需要指定用户
        
        if before_timestamp:
            query += " AND cm.timestamp < ?"
            params.append(before_timestamp)
        
        query += " ORDER BY cm.timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        messages = []
        for row in cursor.fetchall():
            try:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
            except:
                metadata = {}
            
            messages.append({
                'id': row['id'],
                'room_id': row['room_id'],
                'sender_id': row['sender_id'],
                'content': row['content'],
                'type': row['type'],
                'timestamp': row['timestamp'],
                'metadata': metadata,
                'status': row['status']
            })
        
        # 按时间正序返回（最早的在前）
        messages.sort(key=lambda x: x['timestamp'])
        
        return messages
    
    def get_messages_for_user(self, room_id: str, user_id: str, limit: int = 100,
                             before_timestamp: str = None) -> List[Dict]:
        """
        获取用户视角的聊天记录（包含用户特定的状态）
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            limit: 消息数量限制
            before_timestamp: 获取此时间之前的消息
            
        Returns:
            消息列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                cm.message_id as id,
                cm.room_id,
                cm.sender_id,
                cm.content,
                cm.message_type as type,
                cm.timestamp,
                cm.metadata,
                ms.status
            FROM chat_messages cm
            LEFT JOIN message_status ms ON cm.message_id = ms.message_id AND ms.user_id = ?
            WHERE cm.room_id = ? AND cm.is_deleted = 0
        """
        
        params = [user_id, room_id]
        
        if before_timestamp:
            query += " AND cm.timestamp < ?"
            params.append(before_timestamp)
        
        query += " ORDER BY cm.timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        messages = []
        for row in cursor.fetchall():
            try:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
            except:
                metadata = {}
            
            messages.append({
                'id': row['id'],
                'room_id': row['room_id'],
                'sender_id': row['sender_id'],
                'content': row['content'],
                'type': row['type'],
                'timestamp': row['timestamp'],
                'metadata': metadata,
                'status': row['status'] or 'sent'  # 默认状态
            })
        
        # 按时间正序返回（最早的在前）
        messages.sort(key=lambda x: x['timestamp'])
        
        return messages
    
    def update_message_status(self, message_id: str, user_id: str, status: str) -> bool:
        """
        更新消息状态（已送达/已读）
        
        Args:
            message_id: 消息ID
            user_id: 用户ID
            status: 状态（sent, delivered, read）
            
        Returns:
            是否成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            timestamp = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO message_status (message_id, user_id, status, updated_at)
                VALUES (?, ?, ?, ?)
            """, (message_id, user_id, status, timestamp))
            
            conn.commit()
            logger.debug(f"消息状态更新: {message_id} -> {status} (用户: {user_id})")
            
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"更新消息状态失败: {e}")
            return False
    
    # 用户状态管理
    def update_user_presence(self, user_id: str, is_online: bool, 
                            device_info: Dict = None, socket_id: str = None) -> bool:
        """
        更新用户在线状态
        
        Args:
            user_id: 用户ID
            is_online: 是否在线
            device_info: 设备信息
            socket_id: SocketIO连接ID
            
        Returns:
            是否成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            timestamp = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_presence 
                (user_id, is_online, last_seen, device_info, socket_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id, 
                1 if is_online else 0, 
                timestamp,
                json.dumps(device_info or {}, ensure_ascii=False) if device_info else None,
                socket_id
            ))
            
            conn.commit()
            
            status = "在线" if is_online else "离线"
            logger.info(f"用户状态更新: {user_id} -> {status}")
            
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"更新用户状态失败: {e}")
            return False
    
    def get_online_users(self) -> List[str]:
        """
        获取在线用户列表
        
        Returns:
            在线用户ID列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id FROM user_presence 
            WHERE is_online = 1 
            ORDER BY last_seen DESC
        """)
        
        return [row['user_id'] for row in cursor.fetchall()]
    
    # 房间成员管理
    def add_room_member(self, room_id: str, user_id: str) -> bool:
        """
        添加成员到房间
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            timestamp = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR IGNORE INTO room_members (room_id, user_id, joined_at)
                VALUES (?, ?, ?)
            """, (room_id, user_id, timestamp))
            
            conn.commit()
            logger.info(f"添加成员到房间: {user_id} -> {room_id}")
            
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"添加成员失败: {e}")
            return False
    
    def remove_room_member(self, room_id: str, user_id: str) -> bool:
        """
        从房间移除成员
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM room_members 
                WHERE room_id = ? AND user_id = ?
            """, (room_id, user_id))
            
            conn.commit()
            logger.info(f"从房间移除成员: {user_id} <- {room_id}")
            
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"移除成员失败: {e}")
            return False
    
    # 工具方法
    def get_room_members(self, room_id: str) -> List[str]:
        """
        获取房间成员列表
        
        Args:
            room_id: 房间ID
            
        Returns:
            成员ID列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id FROM room_members WHERE room_id = ?
        """, (room_id,))
        
        return [row['user_id'] for row in cursor.fetchall()]
    
    def get_room_info(self, room_id: str) -> Dict:
        """
        获取房间详细信息
        
        Args:
            room_id: 房间ID
            
        Returns:
            房间信息字典
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                room_id, room_type, room_name, creator_id, created_at, last_activity,
                (SELECT COUNT(*) FROM room_members rm WHERE rm.room_id = cr.room_id) as member_count
            FROM chat_rooms cr
            WHERE room_id = ?
        """, (room_id,))
        
        row = cursor.fetchone()
        
        if not row:
            return {}
        
        return {
            'room_id': row['room_id'],
            'room_type': row['room_type'],
            'room_name': row['room_name'],
            'creator_id': row['creator_id'],
            'created_at': row['created_at'],
            'last_activity': row['last_activity'],
            'member_count': row['member_count']
        }
    
    def cleanup_old_messages(self, days: int = 30) -> int:
        """
        清理旧消息（归档到历史表）
        
        Args:
            days: 保留天数
            
        Returns:
            清理的消息数量
        """
        # 这里可以实现消息归档逻辑
        # 暂时返回0，表示未实现
        return 0

# 测试函数
def test_chat_manager():
    """测试聊天管理器"""
    print("测试聊天管理器...")
    
    # 创建管理器实例
    manager = ChatManager()
    
    try:
        # 测试创建私聊房间
        room_id = manager.create_private_room("user001", "user002")
        print(f"✅ 创建私聊房间: {room_id}")
        
        # 测试添加消息
        message = manager.add_message(
            room_id=room_id,
            sender_id="user001",
            content="你好，这是测试消息",
            message_type="text",
            metadata={"test": True}
        )
        print(f"✅ 添加消息: {message['id']}")
        
        # 测试获取消息
        messages = manager.get_messages_for_user(
            room_id=room_id,
            user_id="user002",
            limit=10
        )
        print(f"✅ 获取消息: {len(messages)}条")
        
        # 测试更新消息状态
        success = manager.update_message_status(
            message_id=message['id'],
            user_id="user002",
            status="read"
        )
        print(f"✅ 更新消息状态: {success}")
        
        # 测试创建群聊房间
        group_room_id = manager.create_group_room(
            creator_id="user001",
            room_name="测试群聊",
            member_ids=["user001", "user002", "user003"]
        )
        print(f"✅ 创建群聊房间: {group_room_id}")
        
        # 测试获取用户房间列表
        rooms = manager.get_user_rooms("user001")
        print(f"✅ 获取用户房间: {len(rooms)}个房间")
        
        print("🎉 聊天管理器测试通过!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    finally:
        manager.close()

if __name__ == "__main__":
    test_chat_manager()