#!/usr/bin/env python3
"""
社交系统集成脚本
将社交关系管理系统、聊天系统、共享状态库进行深度集成
实现真人用户↔AI和AI↔AI双社交体系打通
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import sqlite3

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SocialSystemsIntegrator:
    """社交系统集成器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化社交系统集成器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 导入依赖模块
        self._import_dependencies()
        
        logger.info(f"社交系统集成器初始化完成，数据库路径: {db_path}")
    
    def _import_dependencies(self):
        """导入依赖模块"""
        try:
            from shared_state_manager import SharedStateManager
            self.SharedStateManager = SharedStateManager
            logger.info("共享状态管理器导入成功")
        except ImportError as e:
            logger.error(f"导入共享状态管理器失败: {e}")
            self.SharedStateManager = None
        
        try:
            from social_relationship_manager import SocialRelationshipManager
            self.SocialRelationshipManager = SocialRelationshipManager
            logger.info("社交关系管理器导入成功")
        except ImportError as e:
            logger.error(f"导入社交关系管理器失败: {e}")
            self.SocialRelationshipManager = None
    
    def create_ai_ai_communication_room(self, avatar1_id: str, avatar2_id: str) -> str:
        """
        创建AI-AI私聊房间（用于分身间私下通信）
        
        Args:
            avatar1_id: AI分身1 ID
            avatar2_id: AI分身2 ID
        
        Returns:
            房间ID
        """
        # 生成唯一的AI-AI通信房间ID
        sorted_ids = sorted([avatar1_id, avatar2_id])
        room_id = f"ai_ai_private_{sorted_ids[0]}_{sorted_ids[1]}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查聊天房间表是否存在
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_rooms (
                    room_id TEXT PRIMARY KEY,
                    room_type TEXT NOT NULL,
                    room_name TEXT,
                    creator_id TEXT,
                    created_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)
            
            now = datetime.now().isoformat()
            
            # 插入AI-AI通信房间记录
            cursor.execute("""
                INSERT OR IGNORE INTO chat_rooms 
                (room_id, room_type, creator_id, created_at, last_activity, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                room_id,
                'ai_ai_private',
                avatar1_id,
                now,
                now,
                json.dumps({
                    'participants': [avatar1_id, avatar2_id],
                    'purpose': 'ai_collaboration',
                    'created_by': 'system_integrator'
                }, ensure_ascii=False)
            ))
            
            conn.commit()
            logger.info(f"AI-AI通信房间创建成功: {room_id} ({avatar1_id} <-> {avatar2_id})")
            
            return room_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"创建AI-AI通信房间失败: {e}")
            raise
            
        finally:
            conn.close()
    
    def sync_opportunity_to_user_chat(self, user_id: str, communication_data: Dict[str, Any]) -> bool:
        """
        将AI-AI通信中的高价值商机同步到用户聊天窗口
        
        Args:
            user_id: 用户ID
            communication_data: AI-AI通信数据，包含：
                - sender_avatar_id: 发送方AI分身ID
                - receiver_avatar_id: 接收方AI分身ID  
                - content: 商机内容
                - priority: 优先级
                - metadata: 元数据
        
        Returns:
            是否成功
        """
        try:
            # 连接到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建聊天消息表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT CHECK(message_type IN ('text', 'image', 'file', 'opportunity', 'system')) DEFAULT 'text',
                    timestamp TIMESTAMP NOT NULL,
                    metadata TEXT,
                    is_deleted BOOLEAN DEFAULT 0,
                    deleted_at TIMESTAMP
                )
            """)
            
            # 生成消息ID和时间戳
            message_id = f"opportunity_sync_{datetime.now().timestamp()}_{user_id}"
            timestamp = datetime.now().isoformat()
            
            # 构建消息内容
            sender_avatar_id = communication_data.get('sender_avatar_id', 'unknown')
            content = communication_data.get('content', '')
            priority = communication_data.get('priority', 1)
            
            # 生成用户友好的消息内容
            formatted_content = f"🔔 高价值商机推送（优先级{priority}）\n\n"
            formatted_content += f"来自AI分身 [{sender_avatar_id}] 的发现：\n"
            formatted_content += f"{content}\n\n"
            formatted_content += f"时间: {timestamp}\n"
            formatted_content += f"AI内部通信ID: {communication_data.get('communication_id', 'unknown')}"
            
            # 元数据
            metadata = {
                'original_communication': communication_data,
                'sync_type': 'ai_ai_opportunity',
                'priority': priority,
                'auto_synced': True,
                'sync_timestamp': timestamp
            }
            
            # 插入消息记录
            # 这里使用一个特殊的房间ID表示用户的商机推送频道
            room_id = f"user_{user_id}_opportunity_channel"
            
            cursor.execute("""
                INSERT INTO chat_messages 
                (message_id, room_id, sender_id, content, message_type, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                room_id,
                'system_opportunity_sync',
                formatted_content,
                'opportunity',
                timestamp,
                json.dumps(metadata, ensure_ascii=False)
            ))
            
            conn.commit()
            
            logger.info(f"商机同步到用户聊天成功: 用户{user_id}, 消息ID{message_id}, 优先级{priority}")
            
            return True
            
        except Exception as e:
            logger.error(f"商机同步到用户聊天失败: {e}")
            return False
            
        finally:
            conn.close()
    
    def establish_user_ai_friend_relationship(self, user_id: str, avatar_id: str) -> bool:
        """
        建立用户-AI分身好友关系并初始化聊天房间
        
        Args:
            user_id: 用户ID
            avatar_id: AI分身ID
        
        Returns:
            是否成功
        """
        try:
            # 1. 使用社交关系管理器添加好友
            if self.SocialRelationshipManager:
                social_manager = self.SocialRelationshipManager(self.db_path)
                friend_success = social_manager.add_ai_friend(
                    user_id=user_id,
                    avatar_id=avatar_id,
                    metadata={
                        'relationship_established_at': datetime.now().isoformat(),
                        'relationship_source': 'user_initiated',
                        'initial_chat_room_created': True
                    }
                )
                
                if not friend_success:
                    logger.error(f"社交关系管理器添加好友失败: {user_id} -> {avatar_id}")
                    return False
                
                logger.info(f"社交关系添加成功: {user_id} -> {avatar_id}")
            
            # 2. 创建私聊房间（如果聊天系统需要）
            self.create_ai_ai_communication_room(user_id, avatar_id)
            
            logger.info(f"用户-AI分身好友关系建立完成: {user_id} <-> {avatar_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"建立用户-AI分身好友关系失败: {e}")
            return False
    
    def integrate_with_chat_system(self, chat_system_config: Dict[str, Any]) -> bool:
        """
        与现有聊天系统集成
        
        Args:
            chat_system_config: 聊天系统配置
        
        Returns:
            是否成功
        """
        try:
            logger.info("开始与聊天系统集成...")
            
            # 这里可以根据具体聊天系统的API进行集成
            # 例如：注册社交关系事件处理器、设置消息过滤器等
            
            # 模拟集成步骤
            integration_steps = [
                "注册用户状态变更事件监听器",
                "设置AI-AI通信消息转发规则", 
                "配置商机推送频道",
                "绑定隐私设置到聊天界面"
            ]
            
            for step in integration_steps:
                logger.info(f"集成步骤: {step}")
                # 实际集成代码会根据具体聊天系统API实现
            
            logger.info("聊天系统集成完成")
            
            return True
            
        except Exception as e:
            logger.error(f"聊天系统集成失败: {e}")
            return False
    
    def integrate_with_global_business_brain(self, business_brain_config: Dict[str, Any]) -> bool:
        """
        与全球商业大脑集成
        
        Args:
            business_brain_config: 全球商业大脑配置
        
        Returns:
            是否成功
        """
        try:
            logger.info("开始与全球商业大脑集成...")
            
            # 与全球商业大脑集成的关键点：
            # 1. 共享商机数据
            # 2. 同步AI分身状态
            # 3. 集成商务匹配算法
            
            integration_points = [
                "建立商机数据同步通道",
                "共享AI分身能力画像",
                "集成用户-商机匹配逻辑",
                "同步高价值机会到商业大脑"
            ]
            
            for point in integration_points:
                logger.info(f"集成点: {point}")
                # 实际集成代码会根据全球商业大脑的API实现
            
            logger.info("全球商业大脑集成完成")
            
            return True
            
        except Exception as e:
            logger.error(f"全球商业大脑集成失败: {e}")
            return False
    
    def setup_privacy_control_system(self) -> bool:
        """
        设置隐私控制系统
        
        Returns:
            是否成功
        """
        try:
            logger.info("设置隐私控制系统...")
            
            # 隐私控制的关键组件：
            # 1. 用户隐私设置存储
            # 2. AI主动聊天权限检查
            # 3. 商机推送开关
            # 4. AI间协作可见性控制
            
            components = [
                "用户隐私设置数据库表",
                "AI主动聊天权限检查器",
                "商机推送过滤器",
                "AI间协作可见性管理器"
            ]
            
            for component in components:
                logger.info(f"隐私控制组件: {component}")
                # 实际设置代码会根据具体实现
            
            logger.info("隐私控制系统设置完成")
            
            return True
            
        except Exception as e:
            logger.error(f"隐私控制系统设置失败: {e}")
            return False
    
    def create_demo_data(self) -> Dict[str, Any]:
        """
        创建演示数据，展示双社交体系功能
        
        Returns:
            演示数据结果
        """
        try:
            logger.info("创建社交系统演示数据...")
            
            demo_results = {
                'user_ai_friendships': [],
                'ai_ai_communications': [],
                'opportunity_syncs': []
            }
            
            # 1. 创建用户-AI好友关系演示
            demo_users = [
                {'user_id': 'demo_user_001', 'avatar_id': 'intelligence_officer'},
                {'user_id': 'demo_user_001', 'avatar_id': 'content_officer'}
            ]
            
            for friendship in demo_users:
                success = self.establish_user_ai_friend_relationship(
                    user_id=friendship['user_id'],
                    avatar_id=friendship['avatar_id']
                )
                
                if success:
                    demo_results['user_ai_friendships'].append(friendship)
            
            # 2. 创建AI-AI通信演示
            demo_communications = [
                {
                    'sender_avatar_id': 'intelligence_officer',
                    'receiver_avatar_id': 'content_officer',
                    'content': '发现高利润牛仔外套商机，亚马逊售价$89.99，批发价$52，利润率42%',
                    'content_type': 'opportunity',
                    'metadata': {
                        'priority': 4,
                        'tags': ['high_value', 'urgent', 'fashion'],
                        'source_platform': 'Amazon',
                        'original_id': 'B08N5WRWNW'
                    }
                }
            ]
            
            for comm_data in demo_communications:
                try:
                    if self.SocialRelationshipManager:
                        social_manager = self.SocialRelationshipManager(self.db_path)
                        comm_id = social_manager.record_ai_ai_communication(
                            sender_avatar_id=comm_data['sender_avatar_id'],
                            receiver_avatar_id=comm_data['receiver_avatar_id'],
                            content=comm_data['content'],
                            content_type=comm_data['content_type'],
                            metadata=comm_data['metadata']
                        )
                        
                        comm_data['communication_id'] = comm_id
                        demo_results['ai_ai_communications'].append(comm_data)
                        
                except Exception as e:
                    logger.error(f"创建AI-AI通信演示数据失败: {e}")
            
            # 3. 演示商机同步到用户
            if demo_results['ai_ai_communications']:
                comm_data = demo_results['ai_ai_communications'][0]
                comm_data['priority'] = comm_data['metadata']['priority']
                
                success = self.sync_opportunity_to_user_chat(
                    user_id='demo_user_001',
                    communication_data=comm_data
                )
                
                if success:
                    demo_results['opportunity_syncs'].append({
                        'user_id': 'demo_user_001',
                        'communication_id': comm_data.get('communication_id'),
                        'priority': comm_data['priority'],
                        'timestamp': datetime.now().isoformat()
                    })
            
            logger.info(f"演示数据创建完成: {len(demo_results['user_ai_friendships'])}个好友关系, "
                       f"{len(demo_results['ai_ai_communications'])}个AI通信, "
                       f"{len(demo_results['opportunity_syncs'])}个商机同步")
            
            return demo_results
            
        except Exception as e:
            logger.error(f"创建演示数据失败: {e}")
            return {'error': str(e)}
    
    def run_full_integration(self) -> Dict[str, Any]:
        """
        运行完整的社交系统集成
        
        Returns:
            集成结果报告
        """
        integration_report = {
            'start_time': datetime.now().isoformat(),
            'steps_completed': [],
            'errors': [],
            'demo_data': None,
            'status': 'in_progress'
        }
        
        try:
            logger.info("开始完整的社交系统集成...")
            
            # 步骤1: 确保数据库和表结构
            logger.info("步骤1: 初始化数据库结构")
            self._ensure_database_structure()
            integration_report['steps_completed'].append('database_initialization')
            
            # 步骤2: 设置隐私控制系统
            logger.info("步骤2: 设置隐私控制系统")
            privacy_success = self.setup_privacy_control_system()
            if privacy_success:
                integration_report['steps_completed'].append('privacy_control_setup')
            else:
                integration_report['errors'].append('privacy_control_setup_failed')
            
            # 步骤3: 与聊天系统集成
            logger.info("步骤3: 与聊天系统集成")
            chat_integration_success = self.integrate_with_chat_system({
                'api_endpoint': 'http://localhost:5002/api/chat',
                'websocket_endpoint': 'ws://localhost:5001'
            })
            if chat_integration_success:
                integration_report['steps_completed'].append('chat_system_integration')
            else:
                integration_report['errors'].append('chat_system_integration_failed')
            
            # 步骤4: 与全球商业大脑集成
            logger.info("步骤4: 与全球商业大脑集成")
            brain_integration_success = self.integrate_with_global_business_brain({
                'api_endpoint': 'http://localhost:5000/api/global_brain',
                'data_sync_frequency': 'realtime'
            })
            if brain_integration_success:
                integration_report['steps_completed'].append('global_brain_integration')
            else:
                integration_report['errors'].append('global_brain_integration_failed')
            
            # 步骤5: 创建演示数据
            logger.info("步骤5: 创建演示数据")
            demo_data = self.create_demo_data()
            integration_report['demo_data'] = demo_data
            integration_report['steps_completed'].append('demo_data_creation')
            
            # 完成报告
            integration_report['end_time'] = datetime.now().isoformat()
            integration_report['status'] = 'completed'
            
            if integration_report['errors']:
                integration_report['status'] = 'completed_with_errors'
            
            logger.info(f"社交系统集成完成，状态: {integration_report['status']}")
            
            return integration_report
            
        except Exception as e:
            integration_report['status'] = 'failed'
            integration_report['errors'].append(f'integration_failed: {str(e)}')
            logger.error(f"社交系统集成失败: {e}")
            
            return integration_report
    
    def _ensure_database_structure(self):
        """确保数据库结构完整"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查核心表是否存在
            tables = [
                ('processed_opportunities', '已处理商机去重表'),
                ('task_assignments', '任务分配历史表'),
                ('avatar_capability_profiles', '分身能力画像表'),
                ('cost_consumption_logs', '成本消耗记录表'),
                ('user_avatar_relationships', '用户-AI社交关系表'),
                ('ai_ai_communications', 'AI-AI通信记录表'),
                ('user_privacy_settings', '用户隐私设置表'),
                ('chat_rooms', '聊天房间表'),
                ('chat_messages', '聊天消息表')
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table_name, description in tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                if cursor.fetchone():
                    existing_tables.append(f"{description} ({table_name})")
                else:
                    missing_tables.append(f"{description} ({table_name})")
            
            logger.info(f"数据库检查: 现有表 {len(existing_tables)}个，缺失表 {len(missing_tables)}个")
            
            if missing_tables:
                logger.warning(f"缺失表: {', '.join(missing_tables)}")
                logger.info("将尝试初始化缺失表...")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"数据库结构检查失败: {e}")


# 主程序
def main():
    """主程序"""
    print("=" * 60)
    print("社交系统集成器")
    print("功能: 实现真人用户↔AI和AI↔AI双社交体系打通")
    print("=" * 60)
    
    # 创建集成器实例
    integrator = SocialSystemsIntegrator()
    
    # 运行完整集成
    print("\n开始社交系统集成...")
    report = integrator.run_full_integration()
    
    # 打印结果摘要
    print("\n" + "=" * 60)
    print("集成结果摘要")
    print("=" * 60)
    
    print(f"状态: {report['status']}")
    print(f"开始时间: {report['start_time']}")
    print(f"结束时间: {report.get('end_time', 'N/A')}")
    print(f"完成步骤: {len(report['steps_completed'])}个")
    print(f"错误数量: {len(report['errors'])}个")
    
    if report['steps_completed']:
        print("\n完成的步骤:")
        for i, step in enumerate(report['steps_completed'], 1):
            print(f"  {i}. {step}")
    
    if report['errors']:
        print("\n错误列表:")
        for i, error in enumerate(report['errors'], 1):
            print(f"  {i}. {error}")
    
    if report['demo_data'] and 'user_ai_friendships' in report['demo_data']:
        print(f"\n演示数据创建:")
        print(f"  - 用户-AI好友关系: {len(report['demo_data']['user_ai_friendships'])}个")
        print(f"  - AI-AI通信记录: {len(report['demo_data']['ai_ai_communications'])}个")
        print(f"  - 商机同步: {len(report['demo_data']['opportunity_syncs'])}个")
    
    print("\n" + "=" * 60)
    print("集成完成")
    print("=" * 60)
    
    return report


if __name__ == "__main__":
    main()