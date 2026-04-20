"""
邀请裂变系统管理器
基于SellAI邀请裂变规则（永久生效），实现完整的用户增长裂变系统。

功能包括：
1. 邀请关系管理：多级邀请关系追踪、邀请状态管理、邀请奖励记录
2. 创作算力积分系统：积分发放、使用记录、余额查询
3. 佣金分成逻辑集成：与任务39的AI自主商务洽谈引擎佣金规则集成
4. 自动化推广内容生成：生成专属邀请码、推广海报、引流短视频
5. 办公室界面集成：邀请裂变面板数据支持
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import random
import string


class InvitationFissionManager:
    """邀请裂变管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化邀请裂变管理器
        
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
        """确保邀请裂变相关表存在"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # 1. 邀请关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invitation_relationships (
                relationship_id TEXT PRIMARY KEY,
                inviter_id TEXT NOT NULL,  -- 邀请人ID
                invitee_id TEXT NOT NULL UNIQUE,  -- 被邀请人ID
                invitation_code TEXT NOT NULL UNIQUE,  -- 邀请码
                invitation_time TIMESTAMP NOT NULL,  -- 邀请时间
                status TEXT CHECK(status IN ('pending', 'accepted', 'rejected', 'expired')) NOT NULL,
                credits_granted_inviter BOOLEAN DEFAULT 0,  -- 邀请人积分是否已发放
                credits_granted_invitee BOOLEAN DEFAULT 0,  -- 被邀请人积分是否已发放
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inviter_id) REFERENCES users(user_id) ON DELETE SET NULL,
                FOREIGN KEY (invitee_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)
        
        # 2. 积分记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_records (
                record_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,  -- 用户ID
                transaction_type TEXT CHECK(transaction_type IN ('grant', 'use', 'transfer')) NOT NULL,
                credit_amount INTEGER NOT NULL,  -- 积分数量（正数表示增加，负数表示减少）
                transaction_id TEXT,  -- 关联交易ID（如成交ID、邀请ID等）
                usage_scenario TEXT,  -- 使用场景（如"视频生成"、"图片生成"等）
                description TEXT,  -- 描述
                balance_after INTEGER NOT NULL,  -- 操作后余额
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)
        
        # 3. 用户表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                registration_time TIMESTAMP NOT NULL,
                credits_balance INTEGER DEFAULT 0,
                invitation_code TEXT UNIQUE,  -- 用户的专属邀请码
                invited_by TEXT,  -- 邀请人ID
                status TEXT CHECK(status IN ('active', 'inactive', 'suspended')) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invited_by) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)
        
        # 4. 推广内容表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promotion_contents (
                content_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,  -- 所属用户ID
                content_type TEXT CHECK(content_type IN ('invitation_code', 'poster', 'video', 'social_post')) NOT NULL,
                title TEXT,  -- 标题
                content_data TEXT,  -- 内容数据（JSON格式存储具体内容）
                platform TEXT,  -- 目标平台（如'tiktok', 'youtube', 'instagram', 'xiaohongshu'）
                status TEXT CHECK(status IN ('draft', 'generated', 'published', 'archived')) DEFAULT 'draft',
                generation_time TIMESTAMP,
                publication_time TIMESTAMP,
                views INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        self.close()
    
    def generate_invitation_code(self, length: int = 8) -> str:
        """生成邀请码"""
        # 使用大写字母和数字，避免混淆字符
        chars = string.ascii_uppercase + string.digits
        # 排除易混淆字符：0, O, 1, I, L
        exclude_chars = {'0', 'O', '1', 'I', 'L'}
        chars = ''.join([c for c in chars if c not in exclude_chars])
        
        while True:
            code = ''.join(random.choice(chars) for _ in range(length))
            # 检查是否已存在
            if not self._check_invitation_code_exists(code):
                return code
    
    def _check_invitation_code_exists(self, code: str) -> bool:
        """检查邀请码是否已存在"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM invitation_relationships WHERE invitation_code = ?", (code,))
        result = cursor.fetchone()
        
        self.close()
        return result is not None
    
    def create_user(self, username: str, email: str = None, invited_by: str = None) -> Dict[str, Any]:
        """
        创建新用户
        
        Args:
            username: 用户名
            email: 邮箱（可选）
            invited_by: 邀请人ID（可选）
            
        Returns:
            用户信息字典
        """
        user_id = f"user_{str(uuid.uuid4())[:8]}"
        invitation_code = self.generate_invitation_code()
        registration_time = datetime.now().isoformat()
        
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 插入用户记录
            cursor.execute("""
                INSERT INTO users (user_id, username, email, registration_time, invitation_code, invited_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, email, registration_time, invitation_code, invited_by))
            
            # 如果存在邀请人，创建邀请关系
            if invited_by:
                relationship_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO invitation_relationships 
                    (relationship_id, inviter_id, invitee_id, invitation_code, invitation_time, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (relationship_id, invited_by, user_id, invitation_code, registration_time, 'accepted'))
            
            conn.commit()
            
            user_info = {
                'user_id': user_id,
                'username': username,
                'email': email,
                'invitation_code': invitation_code,
                'registration_time': registration_time,
                'invited_by': invited_by
            }
            
            return user_info
            
        except sqlite3.Error as e:
            conn.rollback()
            raise e
        finally:
            self.close()
    
    def register_invitation(self, inviter_id: str, invitation_code: str) -> Dict[str, Any]:
        """
        注册邀请关系（被邀请人使用邀请码注册）
        
        Args:
            inviter_id: 邀请人ID
            invitation_code: 邀请码
            
        Returns:
            邀请关系信息
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 检查邀请码是否有效（属于邀请人）
            cursor.execute("""
                SELECT user_id, invitation_code FROM users 
                WHERE user_id = ? AND invitation_code = ?
            """, (inviter_id, invitation_code))
            
            inviter_info = cursor.fetchone()
            if not inviter_info:
                raise ValueError("无效的邀请码或邀请人ID")
            
            # 为被邀请人生成用户记录（这里简化处理，实际应由前端传入被邀请人信息）
            # 在实际系统中，应该由前端调用create_user并传入invited_by参数
            
            return {
                'success': True,
                'inviter_id': inviter_id,
                'invitation_code': invitation_code,
                'message': '邀请关系已建立'
            }
            
        finally:
            self.close()
    
    def grant_invitation_credits(self, inviter_id: str, invitee_id: str) -> Dict[str, Any]:
        """
        发放邀请奖励积分
        
        Args:
            inviter_id: 邀请人ID
            invitee_id: 被邀请人ID
            
        Returns:
            积分发放结果
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 查找邀请关系
            cursor.execute("""
                SELECT relationship_id, status, credits_granted_inviter, credits_granted_invitee
                FROM invitation_relationships 
                WHERE inviter_id = ? AND invitee_id = ? AND status = 'accepted'
            """, (inviter_id, invitee_id))
            
            relationship = cursor.fetchone()
            if not relationship:
                raise ValueError("未找到有效的邀请关系")
            
            relationship_id = relationship['relationship_id']
            results = []
            
            # 发放邀请人积分（6000分）如果尚未发放
            if not relationship['credits_granted_inviter']:
                inviter_result = self._grant_credits(
                    user_id=inviter_id,
                    transaction_type='grant',
                    credit_amount=6000,
                    transaction_id=relationship_id,
                    usage_scenario='invitation_reward',
                    description='邀请新用户奖励'
                )
                results.append({'user': 'inviter', 'result': inviter_result})
                
                # 更新邀请关系状态
                cursor.execute("""
                    UPDATE invitation_relationships 
                    SET credits_granted_inviter = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE relationship_id = ?
                """, (relationship_id,))
            
            # 发放被邀请人积分（5000分）如果尚未发放
            if not relationship['credits_granted_invitee']:
                invitee_result = self._grant_credits(
                    user_id=invitee_id,
                    transaction_type='grant',
                    credit_amount=5000,
                    transaction_id=relationship_id,
                    usage_scenario='registration_reward',
                    description='新用户注册奖励'
                )
                results.append({'user': 'invitee', 'result': invitee_result})
                
                # 更新邀请关系状态
                cursor.execute("""
                    UPDATE invitation_relationships 
                    SET credits_granted_invitee = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE relationship_id = ?
                """, (relationship_id,))
            
            conn.commit()
            
            return {
                'success': True,
                'results': results,
                'message': '邀请奖励积分已发放'
            }
            
        except sqlite3.Error as e:
            conn.rollback()
            raise e
        finally:
            self.close()
    
    def _grant_credits(self, user_id: str, transaction_type: str, credit_amount: int,
                      transaction_id: str = None, usage_scenario: str = None,
                      description: str = None) -> Dict[str, Any]:
        """
        发放或使用积分（内部方法）
        
        Args:
            user_id: 用户ID
            transaction_type: 交易类型（'grant', 'use', 'transfer'）
            credit_amount: 积分数量
            transaction_id: 关联交易ID
            usage_scenario: 使用场景
            description: 描述
            
        Returns:
            积分操作结果
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 获取当前余额
            cursor.execute("SELECT credits_balance FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise ValueError(f"用户不存在: {user_id}")
            
            current_balance = user['credits_balance']
            new_balance = current_balance + credit_amount
            
            # 检查积分使用限制
            if transaction_type == 'use' and credit_amount < 0:
                # 检查使用场景是否允许
                allowed_scenarios = ['video_generation', 'image_generation', 'ai_operation', 'content_creation']
                if usage_scenario not in allowed_scenarios:
                    raise ValueError(f"积分仅限创作场景使用，不支持: {usage_scenario}")
                
                # 检查余额是否充足
                if new_balance < 0:
                    raise ValueError(f"积分不足，当前余额: {current_balance}，需要: {-credit_amount}")
            
            # 更新用户余额
            cursor.execute("""
                UPDATE users 
                SET credits_balance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (new_balance, user_id))
            
            # 创建积分记录
            record_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO credit_records 
                (record_id, user_id, transaction_type, credit_amount, transaction_id, 
                 usage_scenario, description, balance_after)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (record_id, user_id, transaction_type, credit_amount, transaction_id,
                  usage_scenario, description, new_balance))
            
            return {
                'user_id': user_id,
                'transaction_type': transaction_type,
                'credit_amount': credit_amount,
                'previous_balance': current_balance,
                'new_balance': new_balance,
                'record_id': record_id
            }
            
        except sqlite3.Error as e:
            raise e
    
    def get_user_credits(self, user_id: str) -> Dict[str, Any]:
        """获取用户积分信息"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT user_id, username, credits_balance, invitation_code, invited_by
                FROM users WHERE user_id = ?
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                raise ValueError(f"用户不存在: {user_id}")
            
            # 获取积分记录
            cursor.execute("""
                SELECT record_id, transaction_type, credit_amount, usage_scenario, 
                       description, balance_after, created_at
                FROM credit_records 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,))
            
            records = [dict(row) for row in cursor.fetchall()]
            
            return {
                'user_id': user['user_id'],
                'username': user['username'],
                'credits_balance': user['credits_balance'],
                'invitation_code': user['invitation_code'],
                'invited_by': user['invited_by'],
                'recent_records': records
            }
            
        finally:
            self.close()
    
    def check_invitation_relationship(self, user_id: str, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        检查邀请关系（供commission_calculator调用）
        
        Args:
            user_id: 用户ID（交易参与方）
            transaction_id: 交易ID
            
        Returns:
            邀请关系信息或None
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 查找用户的邀请人
            cursor.execute("""
                SELECT u.user_id as inviter_id, ir.relationship_id
                FROM users u
                JOIN invitation_relationships ir ON u.user_id = ir.inviter_id
                WHERE ir.invitee_id = ? AND ir.status = 'accepted'
            """, (user_id,))
            
            relationship = cursor.fetchone()
            if not relationship:
                return None
            
            return {
                'inviter_id': relationship['inviter_id'],
                'invitee_id': user_id,
                'relationship_id': relationship['relationship_id']
            }
            
        finally:
            self.close()
    
    def generate_promotion_content(self, user_id: str, content_type: str, 
                                  platform: str = None) -> Dict[str, Any]:
        """
        生成推广内容
        
        Args:
            user_id: 用户ID
            content_type: 内容类型（'invitation_code', 'poster', 'video', 'social_post'）
            platform: 目标平台（可选）
            
        Returns:
            推广内容信息
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 获取用户信息
            cursor.execute("""
                SELECT user_id, username, invitation_code, credits_balance
                FROM users WHERE user_id = ?
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                raise ValueError(f"用户不存在: {user_id}")
            
            invitation_code = user['invitation_code']
            username = user['username']
            
            content_id = str(uuid.uuid4())
            generation_time = datetime.now().isoformat()
            
            # 根据内容类型生成不同内容
            content_data = {}
            title = ""
            
            if content_type == 'invitation_code':
                title = f"{username}的SellAI邀请码"
                content_data = {
                    'invitation_code': invitation_code,
                    'reward_info': {
                        'inviter_reward': '6000创作算力积分 + 下级用户终身10%成交佣金分成',
                        'invitee_reward': '5000创作算力积分 + 7天专业版会员免费体验'
                    },
                    'qr_code_url': f"https://sellai.com/invite/{invitation_code}",
                    'short_url': f"https://sellai.inv/{invitation_code[:6]}"
                }
                
            elif content_type == 'poster':
                title = f"加入SellAI全球赚钱AI合伙人 - {username}邀请您"
                content_data = {
                    'invitation_code': invitation_code,
                    'background_template': 'premium_blue_gradient',
                    'main_text': '24小时全自动全球赚钱AI合伙人',
                    'sub_text': f'邀请人：{username}',
                    'qr_code_position': 'bottom_right',
                    'branding_elements': ['SellAI Logo', 'Global Business Network']
                }
                
            elif content_type == 'video':
                title = f"SellAI邀请视频 - {username}"
                # 与短视频引流军团集成
                content_data = {
                    'invitation_code': invitation_code,
                    'video_template': 'black_model_denim_fashion',
                    'duration_seconds': 30,
                    'platform_specifications': {
                        'tiktok': {'aspect_ratio': '9:16', 'max_length': 60},
                        'youtube': {'aspect_ratio': '16:9', 'max_length': 180},
                        'instagram': {'aspect_ratio': '1:1', 'max_length': 60}
                    },
                    'call_to_action': f'使用邀请码 {invitation_code} 注册获得奖励'
                }
                
            elif content_type == 'social_post':
                title = f"SellAI社交推广 - {username}"
                platform = platform or 'general'
                
                platform_templates = {
                    'tiktok': {
                        'hashtags': ['#SellAI', '#AI赚钱', '#全球商机', '#跨境电商', '#创业'],
                        'format': '短视频+文字描述'
                    },
                    'instagram': {
                        'hashtags': ['#SellAI', '#BusinessAI', '#GlobalOpportunity', '#Entrepreneur'],
                        'format': '图片轮播+长描述'
                    },
                    'xiaohongshu': {
                        'hashtags': ['#SellAI', '#AI合伙人', '#赚钱项目', '#跨境电商攻略'],
                        'format': '图文笔记+详细教程'
                    }
                }
                
                template = platform_templates.get(platform, platform_templates['general'])
                
                content_data = {
                    'invitation_code': invitation_code,
                    'platform': platform,
                    'template': template,
                    'main_content': f'''🔥 发现一个超强的赚钱神器！SellAI全自动全球赚钱AI合伙人！

💡 核心优势：
✅ 24小时自动爬取全球高毛利商机（30%+毛利率）
✅ 无限AI分身，一键创建专属赚钱团队
✅ 全域全球无限制，覆盖所有国家/行业

🎁 限时福利：
使用我的邀请码「{invitation_code}」注册，立即获得：
👉 5000创作算力积分（生图/生视频/AI运营）
👉 7天专业版会员免费体验
👉 后续成交终身佣金分成

🚀 立即加入全球商业网络：
https://sellai.com/invite/{invitation_code}

#AI赚钱 #全球商机 #跨境电商 #创业 #SellAI'''
                }
            
            # 保存推广内容记录
            cursor.execute("""
                INSERT INTO promotion_contents 
                (content_id, user_id, content_type, title, content_data, platform, 
                 status, generation_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (content_id, user_id, content_type, title, 
                  json.dumps(content_data), platform, 'generated', generation_time))
            
            conn.commit()
            
            return {
                'content_id': content_id,
                'user_id': user_id,
                'content_type': content_type,
                'title': title,
                'content_data': content_data,
                'platform': platform,
                'generation_time': generation_time
            }
            
        except sqlite3.Error as e:
            conn.rollback()
            raise e
        finally:
            self.close()
    
    def get_user_invitation_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户邀请统计"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # 获取用户邀请总数
            cursor.execute("""
                SELECT COUNT(*) as total_invitations,
                       SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_invitations,
                       SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_invitations
                FROM invitation_relationships 
                WHERE inviter_id = ?
            """, (user_id,))
            
            stats = dict(cursor.fetchone())
            
            # 获取通过邀请获得的佣金总额
            cursor.execute("""
                SELECT SUM(credit_amount) as total_credits_earned
                FROM credit_records 
                WHERE user_id = ? AND transaction_type = 'grant' 
                AND usage_scenario = 'invitation_reward'
            """, (user_id,))
            
            credits_result = cursor.fetchone()
            stats['total_credits_earned'] = credits_result['total_credits_earned'] or 0
            
            # 获取邀请人列表
            cursor.execute("""
                SELECT ir.invitee_id, u.username, ir.invitation_time, ir.status,
                       (SELECT SUM(credit_amount) FROM credit_records cr 
                        WHERE cr.transaction_id = ir.relationship_id 
                        AND cr.user_id = ir.inviter_id) as credits_granted
                FROM invitation_relationships ir
                JOIN users u ON ir.invitee_id = u.user_id
                WHERE ir.inviter_id = ?
                ORDER BY ir.invitation_time DESC
                LIMIT 20
            """, (user_id,))
            
            invitations = [dict(row) for row in cursor.fetchall()]
            
            return {
                'user_id': user_id,
                'stats': stats,
                'recent_invitations': invitations
            }
            
        finally:
            self.close()


# 测试函数
def test_invitation_fission_system():
    """测试邀请裂变系统"""
    print("测试邀请裂变系统...")
    
    manager = InvitationFissionManager()
    
    try:
        # 测试1: 创建邀请人用户
        print("\n1. 创建邀请人用户...")
        inviter = manager.create_user(username="inviter_john", email="john@example.com")
        print(f"   邀请人创建成功: ID={inviter['user_id']}, 邀请码={inviter['invitation_code']}")
        
        # 测试2: 创建被邀请人用户（通过邀请）
        print("\n2. 创建被邀请人用户（通过邀请）...")
        invitee = manager.create_user(
            username="invitee_mary", 
            email="mary@example.com",
            invited_by=inviter['user_id']
        )
        print(f"   被邀请人创建成功: ID={invitee['user_id']}, 邀请人={invitee['invited_by']}")
        
        # 测试3: 发放邀请奖励积分
        print("\n3. 发放邀请奖励积分...")
        credit_result = manager.grant_invitation_credits(
            inviter_id=inviter['user_id'],
            invitee_id=invitee['user_id']
        )
        print(f"   积分发放结果: {credit_result['message']}")
        
        # 测试4: 查询用户积分信息
        print("\n4. 查询邀请人积分信息...")
        inviter_credits = manager.get_user_credits(inviter['user_id'])
        print(f"   邀请人积分余额: {inviter_credits['credits_balance']}")
        
        print("\n   查询被邀请人积分信息...")
        invitee_credits = manager.get_user_credits(invitee['user_id'])
        print(f"   被邀请人积分余额: {invitee_credits['credits_balance']}")
        
        # 测试5: 检查邀请关系（供佣金计算器调用）
        print("\n5. 检查邀请关系...")
        relationship = manager.check_invitation_relationship(
            user_id=invitee['user_id'],
            transaction_id="test_txn_001"
        )
        print(f"   邀请关系: {relationship}")
        
        # 测试6: 生成推广内容
        print("\n6. 生成推广内容...")
        promotion = manager.generate_promotion_content(
            user_id=inviter['user_id'],
            content_type='invitation_code'
        )
        print(f"   推广内容生成成功: {promotion['title']}")
        
        # 测试7: 获取邀请统计
        print("\n7. 获取邀请统计...")
        stats = manager.get_user_invitation_stats(inviter['user_id'])
        print(f"   邀请统计: 总数={stats['stats']['total_invitations']}, 已接受={stats['stats']['accepted_invitations']}")
        
        print("\n✅ 所有测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_invitation_fission_system()