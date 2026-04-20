#!/usr/bin/env python3
"""
聊天记录永久记忆集成模块

此模块负责：
1. 将聊天记录（一对一私聊、群聊消息）加密存入Notebook LM永久记忆系统
2. 将好友关系、社群成员关系同步到永久记忆
3. 提供多维度聊天记录检索功能
4. 确保与Memory V2分层记忆系统、办公室界面、无限分身系统完全兼容

数据流：SQLite数据库 → 加密 → 转换为知识文档 → 导入Notebook LM知识库
"""

import os
import json
import sqlite3
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum
import threading
import time

# 导入Notebook LM集成
try:
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType,
        create_document_from_task_result,
        create_document_from_market_data
    )
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.notebook_lm_integration import (
        NotebookLMIntegration,
        KnowledgeDocument,
        ContentType,
        SourceType,
        create_document_from_task_result,
        create_document_from_market_data
    )

# 导入安全加密模块
try:
    from src.multi_layer_security import MultiLayerSecurity
except ImportError:
    # 简化实现，如果模块不存在则使用基础加密
    MultiLayerSecurity = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CHAT_PERMANENT_MEMORY - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatDocumentType(Enum):
    """聊天文档类型枚举"""
    PRIVATE_MESSAGE = "private_message"
    GROUP_MESSAGE = "group_message"
    USER_RELATIONSHIP = "user_relationship"
    AI_RELATIONSHIP = "ai_relationship"
    GROUP_MEMBERSHIP = "group_membership"


class ChatPermanentMemory:
    """
    聊天记录永久记忆管理类
    
    功能：
    1. 聊天记录加密存储到Notebook LM
    2. 社交关系同步
    3. 多维度检索
    4. 增量同步与去重
    """
    
    def __init__(self, 
                 db_path: str = "data/shared_state/state.db",
                 notebook_lm_api_key: Optional[str] = None,
                 knowledge_base_id: Optional[str] = None,
                 encryption_key: Optional[str] = None):
        """
        初始化聊天永久记忆管理器
        
        Args:
            db_path: 共享状态数据库路径
            notebook_lm_api_key: Notebook LM API密钥
            knowledge_base_id: 目标知识库ID，如果为None则使用默认
            encryption_key: 加密密钥，如果为None则生成或从环境变量读取
        """
        self.db_path = db_path
        
        # 初始化Notebook LM集成
        self.api_key = notebook_lm_api_key or os.getenv("NOTEBOOKLM_API_KEY")
        if not self.api_key:
            logger.warning("未提供Notebook LM API密钥，永久记忆功能受限")
        
        self.nli = None
        if self.api_key:
            try:
                self.nli = NotebookLMIntegration(api_key=self.api_key)
                logger.info("Notebook LM集成初始化成功")
            except Exception as e:
                logger.error(f"Notebook LM集成初始化失败: {str(e)}")
        
        # 初始化安全加密
        if MultiLayerSecurity:
            try:
                self.security = MultiLayerSecurity(db_path)
                logger.info("多层次安全防护系统初始化成功")
            except Exception as e:
                logger.error(f"安全系统初始化失败: {str(e)}")
                self.security = None
        else:
            self.security = None
        
        # 知识库配置
        self.knowledge_base_id = knowledge_base_id
        self.chat_kb_id = None  # 聊天记录知识库ID
        self.relationship_kb_id = None  # 社交关系知识库ID
        
        # 同步状态跟踪
        self.sync_status = {}  # 跟踪已同步的消息ID
        self.last_sync_time = None
        
        # 加载同步状态
        self._load_sync_status()
        
        logger.info(f"聊天记录永久记忆管理器初始化完成，数据库: {db_path}")
    
    def _load_sync_status(self):
        """加载同步状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建同步状态表（如果不存在）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_memory_sync_status (
                    source_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    document_id TEXT,
                    sync_status TEXT CHECK(sync_status IN ('pending', 'synced', 'failed', 'encrypted')),
                    encrypted_content TEXT,
                    sync_timestamp TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    metadata TEXT  -- JSON格式
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sync_source_type 
                ON chat_memory_sync_status(source_type, sync_status)
            ''')
            
            # 读取已同步状态
            cursor.execute('''
                SELECT source_id, sync_status, document_id 
                FROM chat_memory_sync_status 
                WHERE sync_status = 'synced'
            ''')
            
            for row in cursor.fetchall():
                source_id = row[0]
                self.sync_status[source_id] = {
                    'status': row[1],
                    'document_id': row[2]
                }
            
            conn.commit()
            conn.close()
            
            logger.info(f"加载了 {len(self.sync_status)} 条同步状态记录")
            
        except Exception as e:
            logger.error(f"加载同步状态失败: {e}")
    
    def _save_sync_status(self, source_id: str, source_type: str, 
                         sync_status: str, document_id: Optional[str] = None,
                         encrypted_content: Optional[str] = None,
                         metadata: Optional[Dict] = None):
        """保存同步状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO chat_memory_sync_status 
                (source_id, source_type, document_id, sync_status, 
                 encrypted_content, sync_timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                source_id, source_type, document_id, sync_status,
                encrypted_content, timestamp,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()
            
            # 更新内存状态
            self.sync_status[source_id] = {
                'status': sync_status,
                'document_id': document_id
            }
            
            logger.debug(f"同步状态保存: {source_id} -> {sync_status}")
            
        except Exception as e:
            logger.error(f"保存同步状态失败: {e}")
    
    def encrypt_chat_content(self, content: str, metadata: Dict) -> Tuple[str, Dict]:
        """
        加密聊天内容
        
        Args:
            content: 原始聊天内容
            metadata: 元数据
            
        Returns:
            (加密内容, 更新后的元数据)
        """
        try:
            if self.security and self.security.data_layer:
                # 使用多层次安全系统的数据层加密
                encrypted = self.security.data_layer.encrypt_sensitive_data(content)
                
                # 更新元数据，标记为已加密
                metadata['encrypted'] = True
                metadata['encryption_method'] = 'multi_layer_security'
                metadata['encryption_timestamp'] = datetime.now().isoformat()
                
                return encrypted, metadata
            else:
                # 如果安全系统不可用，使用简单的base64编码（仅用于演示）
                import base64
                encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                
                metadata['encrypted'] = True
                metadata['encryption_method'] = 'base64'
                metadata['encryption_timestamp'] = datetime.now().isoformat()
                metadata['warning'] = '使用base64编码，建议配置完整的安全系统'
                
                return encoded, metadata
                
        except Exception as e:
            logger.error(f"加密聊天内容失败: {e}")
            # 返回原始内容但标记为未加密
            metadata['encrypted'] = False
            metadata['encryption_error'] = str(e)
            return content, metadata
    
    def ensure_knowledge_bases(self):
        """
        确保聊天记录和社交关系知识库存在
        
        Returns:
            (聊天记录知识库ID, 社交关系知识库ID)
        """
        if not self.nli:
            logger.error("Notebook LM集成未初始化，无法确保知识库")
            return None, None
        
        try:
            # 获取现有知识库列表
            knowledge_bases = self.nli.list_knowledge_bases()
            
            chat_kb_id = None
            relationship_kb_id = None
            
            for kb in knowledge_bases:
                name = kb.get('name', '')
                kb_id = kb.get('id', '')
                
                if '聊天记录库' in name or 'Chat History' in name:
                    chat_kb_id = kb_id
                elif '社交关系库' in name or 'Social Relationships' in name:
                    relationship_kb_id = kb_id
            
            # 创建缺失的知识库
            if not chat_kb_id:
                chat_kb_id = self.nli.create_knowledge_base(
                    name="SellAI聊天记录库",
                    description="存储所有一对一私聊、群聊消息的加密记录",
                    tags=["chat_history", "encrypted", "private_messages"]
                )
                logger.info(f"创建聊天记录知识库: {chat_kb_id}")
            
            if not relationship_kb_id:
                relationship_kb_id = self.nli.create_knowledge_base(
                    name="SellAI社交关系库",
                    description="存储用户-AI好友关系、AI-AI私下通信关系",
                    tags=["social_relationships", "friend_network", "avatar_connections"]
                )
                logger.info(f"创建社交关系知识库: {relationship_kb_id}")
            
            self.chat_kb_id = chat_kb_id
            self.relationship_kb_id = relationship_kb_id
            
            return chat_kb_id, relationship_kb_id
            
        except Exception as e:
            logger.error(f"确保知识库存在失败: {e}")
            return None, None
    
    def import_chat_messages(self, limit: Optional[int] = None, 
                           days_back: Optional[int] = None) -> Dict[str, Any]:
        """
        导入聊天记录到永久记忆
        
        Args:
            limit: 最大导入数量
            days_back: 仅导入最近N天的消息
            
        Returns:
            导入结果统计
        """
        if not self.nli:
            return {"error": "Notebook LM集成未初始化", "imported": 0}
        
        # 确保知识库存在
        chat_kb_id, _ = self.ensure_knowledge_bases()
        if not chat_kb_id:
            return {"error": "无法获取聊天记录知识库ID", "imported": 0}
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建查询条件
            query = '''
                SELECT cm.message_id, cm.room_id, cm.sender_id, cm.content,
                       cm.message_type, cm.timestamp, cm.metadata,
                       cr.room_type, cr.room_name
                FROM chat_messages cm
                JOIN chat_rooms cr ON cm.room_id = cr.room_id
                WHERE cm.is_deleted = 0
            '''
            
            params = []
            
            if days_back:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                query += " AND cm.timestamp >= ?"
                params.append(cutoff_date.isoformat())
            
            # 排除已同步的消息
            pending_sync = [sid for sid, status in self.sync_status.items() 
                          if status['status'] != 'synced']
            
            if pending_sync:
                # 只导入未同步的消息
                placeholders = ','.join(['?' for _ in pending_sync])
                query += f" AND cm.message_id NOT IN ({placeholders})"
                params.extend(pending_sync)
            
            query += " ORDER BY cm.timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            logger.info(f"找到 {len(rows)} 条待导入聊天记录")
            
            # 处理每条消息
            imported_count = 0
            failed_count = 0
            documents = []
            
            for row in rows:
                try:
                    message_id = row['message_id']
                    
                    # 解析元数据
                    metadata = {}
                    if row['metadata']:
                        try:
                            metadata = json.loads(row['metadata'])
                        except:
                            metadata = {}
                    
                    # 添加聊天特定元数据
                    metadata.update({
                        'room_id': row['room_id'],
                        'room_type': row['room_type'],
                        'room_name': row['room_name'],
                        'sender_id': row['sender_id'],
                        'message_type': row['message_type'],
                        'original_timestamp': row['timestamp']
                    })
                    
                    # 加密聊天内容
                    encrypted_content, metadata = self.encrypt_chat_content(
                        row['content'], metadata
                    )
                    
                    # 创建知识文档
                    document = KnowledgeDocument(
                        title=f"聊天记录_{message_id[:8]}",
                        content=encrypted_content,
                        content_type=ContentType.JSON,
                        source_type=SourceType.USER_INTERACTION,
                        source_id=message_id,
                        tags=["chat", row['room_type'], row['message_type']],
                        metadata=metadata
                    )
                    
                    documents.append(document)
                    
                    # 标记为已加密（但未同步）
                    self._save_sync_status(
                        source_id=message_id,
                        source_type="chat_message",
                        sync_status="encrypted",
                        encrypted_content=encrypted_content[:500] if encrypted_content else None,
                        metadata={"room_type": row['room_type'], "sender": row['sender_id']}
                    )
                    
                except Exception as e:
                    logger.error(f"处理消息 {row.get('message_id', 'unknown')} 失败: {e}")
                    failed_count += 1
            
            # 批量导入文档
            if documents:
                results = self.nli.batch_add_documents(
                    knowledge_base_id=chat_kb_id,
                    documents=documents,
                    batch_size=50
                )
                
                # 统计结果
                for i, result in enumerate(results):
                    source_doc = documents[i]
                    source_id = source_doc.source_id
                    
                    if result['status'] == 'success':
                        # 更新为同步成功
                        self._save_sync_status(
                            source_id=source_id,
                            source_type="chat_message",
                            sync_status="synced",
                            document_id=result['document_id']
                        )
                        imported_count += 1
                    else:
                        # 标记为失败
                        self._save_sync_status(
                            source_id=source_id,
                            source_type="chat_message", 
                            sync_status="failed",
                            error_message=result.get('error', 'Unknown error')
                        )
                        failed_count += 1
            
            conn.close()
            
            result_stats = {
                "total_found": len(rows),
                "imported": imported_count,
                "failed": failed_count,
                "knowledge_base_id": chat_kb_id
            }
            
            logger.info(f"聊天记录导入完成: {result_stats}")
            
            return result_stats
            
        except Exception as e:
            logger.error(f"导入聊天记录失败: {e}")
            return {"error": str(e), "imported": 0, "failed": 0}
    
    def import_social_relationships(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        导入社交关系到永久记忆
        
        Args:
            limit: 最大导入数量
            
        Returns:
            导入结果统计
        """
        if not self.nli:
            return {"error": "Notebook LM集成未初始化", "imported": 0}
        
        # 确保知识库存在
        _, relationship_kb_id = self.ensure_knowledge_bases()
        if not relationship_kb_id:
            return {"error": "无法获取社交关系知识库ID", "imported": 0}
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 导入用户-AI社交关系
            query_relationships = '''
                SELECT relationship_id, user_id, avatar_id, relationship_type,
                       created_at, last_interaction, metadata
                FROM user_avatar_relationships
                ORDER BY last_interaction DESC
            '''
            
            if limit:
                query_relationships += " LIMIT ?"
                cursor.execute(query_relationships, (limit,))
            else:
                cursor.execute(query_relationships)
            
            relationships = cursor.fetchall()
            
            # 导入AI-AI通信记录
            query_communications = '''
                SELECT communication_id, sender_avatar_id, receiver_avatar_id,
                       content, content_type, timestamp, metadata
                FROM ai_ai_communications
                ORDER BY timestamp DESC
            '''
            
            if limit:
                query_communications += " LIMIT ?"
                cursor.execute(query_communications, (limit,))
            else:
                cursor.execute(query_communications)
            
            communications = cursor.fetchall()
            
            logger.info(f"找到 {len(relationships)} 条社交关系，{len(communications)} 条AI通信记录")
            
            # 处理社交关系
            imported_count = 0
            failed_count = 0
            documents = []
            
            for row in relationships:
                try:
                    relationship_id = row['relationship_id']
                    
                    # 解析元数据
                    metadata = {}
                    if row['metadata']:
                        try:
                            metadata = json.loads(row['metadata'])
                        except:
                            metadata = {}
                    
                    # 构建关系描述
                    relationship_desc = f"""
用户 {row['user_id']} 与 AI分身 {row['avatar_id']} 的社交关系:
- 关系类型: {row['relationship_type']}
- 创建时间: {row['created_at']}
- 最后互动: {row['last_interaction']}
- 元数据: {json.dumps(metadata, ensure_ascii=False, indent=2)}
"""
                    
                    # 创建知识文档
                    document = KnowledgeDocument(
                        title=f"用户-AI关系_{relationship_id}",
                        content=relationship_desc,
                        content_type=ContentType.JSON,
                        source_type=SourceType.USER_INTERACTION,
                        source_id=f"relationship_{relationship_id}",
                        tags=["social_relationship", "user_avatar", row['relationship_type']],
                        metadata={
                            "user_id": row['user_id'],
                            "avatar_id": row['avatar_id'],
                            "relationship_type": row['relationship_type'],
                            "created_at": row['created_at'],
                            "last_interaction": row['last_interaction'],
                            "original_metadata": metadata
                        }
                    )
                    
                    documents.append(document)
                    
                except Exception as e:
                    logger.error(f"处理社交关系 {row.get('relationship_id', 'unknown')} 失败: {e}")
                    failed_count += 1
            
            # 处理AI-AI通信记录
            for row in communications:
                try:
                    communication_id = row['communication_id']
                    
                    # 解析元数据
                    metadata = {}
                    if row['metadata']:
                        try:
                            metadata = json.loads(row['metadata'])
                        except:
                            metadata = {}
                    
                    # 加密通信内容
                    encrypted_content, enc_metadata = self.encrypt_chat_content(
                        row['content'], metadata.copy()
                    )
                    
                    # 构建通信描述
                    communication_desc = f"""
AI分身 {row['sender_avatar_id']} 发送给 {row['receiver_avatar_id']} 的通信:
- 内容类型: {row['content_type']}
- 发送时间: {row['timestamp']}
- 元数据: {json.dumps(metadata, ensure_ascii=False, indent=2)}
"""
                    
                    # 创建知识文档
                    document = KnowledgeDocument(
                        title=f"AI-AI通信_{communication_id}",
                        content=communication_desc,
                        content_type=ContentType.JSON,
                        source_type=SourceType.USER_INTERACTION,
                        source_id=f"communication_{communication_id}",
                        tags=["ai_communication", row['content_type']],
                        metadata={
                            "sender_avatar_id": row['sender_avatar_id'],
                            "receiver_avatar_id": row['receiver_avatar_id'],
                            "content_type": row['content_type'],
                            "timestamp": row['timestamp'],
                            "original_metadata": metadata,
                            "encryption_info": enc_metadata
                        }
                    )
                    
                    documents.append(document)
                    
                except Exception as e:
                    logger.error(f"处理AI通信 {row.get('communication_id', 'unknown')} 失败: {e}")
                    failed_count += 1
            
            # 批量导入文档
            if documents:
                results = self.nli.batch_add_documents(
                    knowledge_base_id=relationship_kb_id,
                    documents=documents,
                    batch_size=50
                )
                
                # 统计结果
                for i, result in enumerate(results):
                    if result['status'] == 'success':
                        imported_count += 1
                    else:
                        failed_count += 1
            
            conn.close()
            
            result_stats = {
                "total_relationships": len(relationships),
                "total_communications": len(communications),
                "imported": imported_count,
                "failed": failed_count,
                "knowledge_base_id": relationship_kb_id
            }
            
            logger.info(f"社交关系导入完成: {result_stats}")
            
            return result_stats
            
        except Exception as e:
            logger.error(f"导入社交关系失败: {e}")
            return {"error": str(e), "imported": 0, "failed": 0}
    
    def search_chat_messages(self, query: str, 
                           filters: Optional[Dict] = None,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索聊天记录
        
        Args:
            query: 搜索关键词
            filters: 过滤条件，如 {"room_type": "private", "sender_id": "user123"}
            limit: 返回结果限制
            
        Returns:
            搜索结果列表
        """
        if not self.nli or not self.chat_kb_id:
            logger.error("Notebook LM集成或知识库未初始化")
            return []
        
        try:
            # 构建标签过滤器
            filter_tags = []
            if filters:
                if filters.get('room_type'):
                    filter_tags.append(filters['room_type'])
                if filters.get('message_type'):
                    filter_tags.append(filters['message_type'])
                if filters.get('sender_id'):
                    # 将sender_id作为标签的一部分
                    filter_tags.append(f"sender:{filters['sender_id']}")
            
            # 搜索文档
            documents = self.nli.search_documents(
                knowledge_base_id=self.chat_kb_id,
                query=query,
                filter_tags=filter_tags if filter_tags else None,
                limit=limit
            )
            
            # 解析结果
            results = []
            for doc in documents:
                try:
                    metadata = doc.get('metadata', {})
                    
                    # 提取聊天信息
                    result = {
                        'document_id': doc.get('id'),
                        'title': doc.get('title'),
                        'content_preview': doc.get('content', '')[:200] + '...',
                        'room_id': metadata.get('room_id'),
                        'room_type': metadata.get('room_type'),
                        'sender_id': metadata.get('sender_id'),
                        'message_type': metadata.get('message_type'),
                        'timestamp': metadata.get('original_timestamp'),
                        'encrypted': metadata.get('encrypted', False),
                        'score': doc.get('score', 0)
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"解析搜索结果失败: {e}")
            
            logger.info(f"聊天记录搜索完成: 查询='{query}', 结果数={len(results)}")
            
            return results
            
        except Exception as e:
            logger.error(f"搜索聊天记录失败: {e}")
            return []
    
    def get_user_chat_history(self, user_id: str, 
                            days_back: int = 30,
                            limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户的聊天历史
        
        Args:
            user_id: 用户ID
            days_back: 获取最近N天的记录
            limit: 最大返回数量
            
        Returns:
            聊天历史列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 计算时间范围
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # 查询用户参与的聊天房间
            cursor.execute('''
                SELECT DISTINCT cm.room_id
                FROM chat_messages cm
                JOIN room_members rm ON cm.room_id = rm.room_id
                WHERE rm.user_id = ? 
                  AND cm.timestamp >= ?
                ORDER BY cm.timestamp DESC
                LIMIT ?
            ''', (user_id, cutoff_date.isoformat(), limit))
            
            room_ids = [row['room_id'] for row in cursor.fetchall()]
            
            if not room_ids:
                conn.close()
                return []
            
            # 查询这些房间的消息
            placeholders = ','.join(['?' for _ in room_ids])
            query = f'''
                SELECT cm.message_id, cm.room_id, cm.sender_id, cm.content,
                       cm.message_type, cm.timestamp, cm.metadata,
                       cr.room_type, cr.room_name
                FROM chat_messages cm
                JOIN chat_rooms cr ON cm.room_id = cr.room_id
                WHERE cm.room_id IN ({placeholders})
                  AND cm.timestamp >= ?
                  AND cm.is_deleted = 0
                ORDER BY cm.timestamp DESC
            '''
            
            params = room_ids + [cutoff_date.isoformat()]
            cursor.execute(query, params)
            
            messages = []
            for row in cursor.fetchall():
                try:
                    metadata = {}
                    if row['metadata']:
                        try:
                            metadata = json.loads(row['metadata'])
                        except:
                            metadata = {}
                    
                    message = {
                        'id': row['message_id'],
                        'room_id': row['room_id'],
                        'room_type': row['room_type'],
                        'room_name': row['room_name'],
                        'sender_id': row['sender_id'],
                        'content': row['content'],
                        'type': row['message_type'],
                        'timestamp': row['timestamp'],
                        'metadata': metadata
                    }
                    
                    messages.append(message)
                    
                except Exception as e:
                    logger.error(f"解析消息失败: {e}")
            
            conn.close()
            
            logger.info(f"获取用户 {user_id} 聊天历史: 共 {len(messages)} 条消息")
            
            return messages
            
        except Exception as e:
            logger.error(f"获取用户聊天历史失败: {e}")
            return []
    
    def start_background_sync(self, interval_seconds: int = 300):
        """
        启动后台同步服务
        
        Args:
            interval_seconds: 同步间隔（秒）
        """
        def sync_worker():
            logger.info(f"后台同步服务启动，间隔: {interval_seconds}秒")
            
            while True:
                try:
                    # 导入新聊天记录
                    chat_result = self.import_chat_messages(limit=100, days_back=1)
                    
                    # 导入新社交关系
                    relationship_result = self.import_social_relationships(limit=50)
                    
                    logger.info(f"后台同步完成: 聊天={chat_result.get('imported', 0)}条, "
                              f"关系={relationship_result.get('imported', 0)}条")
                    
                except Exception as e:
                    logger.error(f"后台同步失败: {e}")
                
                # 等待下次同步
                time.sleep(interval_seconds)
        
        # 启动后台线程
        sync_thread = threading.Thread(target=sync_worker, daemon=True)
        sync_thread.start()
        
        logger.info("后台同步服务已启动")
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """
        获取同步统计信息
        
        Returns:
            同步统计数据
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 统计各种状态的记录数
            cursor.execute('''
                SELECT sync_status, COUNT(*) as count
                FROM chat_memory_sync_status
                GROUP BY sync_status
            ''')
            
            status_counts = {}
            for row in cursor.fetchall():
                status_counts[row[0]] = row[1]
            
            # 统计按类型的记录数
            cursor.execute('''
                SELECT source_type, COUNT(*) as count
                FROM chat_memory_sync_status
                GROUP BY source_type
            ''')
            
            type_counts = {}
            for row in cursor.fetchall():
                type_counts[row[0]] = row[1]
            
            conn.close()
            
            stats = {
                'total_synced': status_counts.get('synced', 0),
                'total_pending': status_counts.get('pending', 0) + status_counts.get('encrypted', 0),
                'total_failed': status_counts.get('failed', 0),
                'status_counts': status_counts,
                'type_counts': type_counts,
                'last_sync_time': self.last_sync_time
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取同步统计失败: {e}")
            return {"error": str(e)}


# 便捷工具函数
def create_chat_document_from_message(message_data: Dict) -> KnowledgeDocument:
    """
    从聊天消息数据创建知识文档
    
    Args:
        message_data: 聊天消息数据
        
    Returns:
        知识文档对象
    """
    metadata = message_data.get('metadata', {})
    
    # 添加聊天特定信息
    metadata.update({
        'room_id': message_data.get('room_id'),
        'sender_id': message_data.get('sender_id'),
        'message_type': message_data.get('type', 'text'),
        'original_timestamp': message_data.get('timestamp')
    })
    
    return KnowledgeDocument(
        title=f"聊天消息_{message_data.get('id', 'unknown')[:8]}",
        content=message_data.get('content', ''),
        content_type=ContentType.JSON,
        source_type=SourceType.USER_INTERACTION,
        source_id=message_data.get('id', ''),
        tags=["chat_message", message_data.get('room_type', 'unknown'), message_data.get('type', 'text')],
        metadata=metadata
    )


def initialize_chat_permanent_memory(config_file: Optional[str] = None) -> ChatPermanentMemory:
    """
    初始化聊天记录永久记忆系统
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        ChatPermanentMemory实例
    """
    # 加载配置（简化实现）
    db_path = "data/shared_state/state.db"
    api_key = os.getenv("NOTEBOOKLM_API_KEY")
    
    # 创建实例
    cpm = ChatPermanentMemory(
        db_path=db_path,
        notebook_lm_api_key=api_key
    )
    
    # 确保知识库存在
    cpm.ensure_knowledge_bases()
    
    logger.info("聊天记录永久记忆系统初始化完成")
    
    return cpm


if __name__ == "__main__":
    print("聊天记录永久记忆集成模块测试")
    print("=" * 50)
    
    # 创建测试实例
    cpm = ChatPermanentMemory(
        db_path="data/shared_state/state.db",
        notebook_lm_api_key="test_key"  # 实际使用时从环境变量读取
    )
    
    print("1. 确保知识库存在...")
    chat_kb, rel_kb = cpm.ensure_knowledge_bases()
    print(f"   聊天记录知识库: {chat_kb or '未创建'}")
    print(f"   社交关系知识库: {rel_kb or '未创建'}")
    
    print("\n2. 测试加密功能...")
    test_content = "这是一条测试聊天消息"
    test_metadata = {"test": True}
    encrypted, updated_metadata = cpm.encrypt_chat_content(test_content, test_metadata)
    print(f"   原始内容: {test_content}")
    print(f"   加密后: {encrypted[:50]}...")
    print(f"   元数据: {json.dumps(updated_metadata, ensure_ascii=False)}")
    
    print("\n3. 测试同步状态跟踪...")
    stats = cpm.get_sync_stats()
    print(f"   同步状态: {json.dumps(stats, ensure_ascii=False)}")
    
    print("\n模块测试完成")
    print("注意：完整功能需要配置有效的Notebook LM API密钥和数据库连接")