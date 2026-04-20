#!/usr/bin/env python3
"""
达人洽谈军团 - 批量私信与智能跟进系统
支持TikTok、YouTube、Instagram、小红书等多平台API对接
实现批量私信发送、智能间隔跟进、档案永久归档到Memory V2认证记忆系统
"""

import sqlite3
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import threading
import queue
import hashlib
import os
import sys

# 导入话术引擎
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from influencer_outreach_engine import InfluencerOutreachEngine
except ImportError:
    # 如果导入失败，定义简化版本
    class InfluencerOutreachEngine:
        def __init__(self, db_path="data/shared_state/state.db"):
            self.db_path = db_path

class PlatformAPI:
    """平台API基类，定义统一接口"""
    
    def __init__(self, platform_name: str, api_config: Dict):
        self.platform_name = platform_name
        self.api_config = api_config
        self.rate_limit_remaining = 100
        self.rate_limit_reset_time = datetime.now() + timedelta(hours=1)
    
    def send_message(self, recipient: str, message: str, subject: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        发送私信
        
        Returns:
            (成功标志, 平台消息ID, 错误信息)
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def get_message_status(self, message_id: str) -> Tuple[str, Optional[str]]:
        """
        获取消息状态
        
        Returns:
            (状态, 回复内容)
            状态: sent, delivered, read, replied, failed
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def check_rate_limit(self) -> bool:
        """检查速率限制"""
        if datetime.now() > self.rate_limit_reset_time:
            self.rate_limit_remaining = 100
            self.rate_limit_reset_time = datetime.now() + timedelta(hours=1)
        
        return self.rate_limit_remaining > 0
    
    def use_rate_limit(self):
        """使用一次速率限制配额"""
        self.rate_limit_remaining -= 1

class TikTokAPI(PlatformAPI):
    """TikTok API实现（模拟）"""
    
    def __init__(self, api_config: Dict):
        super().__init__("tiktok", api_config)
        self.session_token = api_config.get("session_token", "")
        self.user_id = api_config.get("user_id", "")
    
    def send_message(self, recipient: str, message: str, subject: Optional[str] = None) -> Tuple[bool, str, str]:
        if not self.check_rate_limit():
            return False, "", "速率限制，请稍后重试"
        
        # 模拟API调用
        self.use_rate_limit()
        
        # 生成模拟消息ID
        msg_hash = hashlib.md5(f"{recipient}{message}{datetime.now().timestamp()}".encode()).hexdigest()[:16]
        message_id = f"tt_{msg_hash}"
        
        # 模拟成功率（85%）
        if random.random() > 0.15:
            # 记录发送日志
            print(f"[TikTok] 消息已发送给 {recipient}: {message[:50]}...")
            return True, message_id, ""
        else:
            print(f"[TikTok] 消息发送失败给 {recipient}")
            return False, "", "模拟失败：API返回错误"
    
    def get_message_status(self, message_id: str) -> Tuple[str, Optional[str]]:
        # 模拟消息状态
        statuses = ["sent", "delivered", "read", "replied", "failed"]
        weights = [0.2, 0.3, 0.2, 0.2, 0.1]
        
        status = random.choices(statuses, weights=weights, k=1)[0]
        
        # 如果状态是replied，生成模拟回复
        reply = None
        if status == "replied":
            replies = [
                "Hi! Thanks for reaching out. I'd love to learn more about your product.",
                "Interesting opportunity! Can you send me more details?",
                "Thanks for the offer! What's the commission rate?",
                "I'm interested! How do I get started?",
                "Sounds great! Do you have a media kit I can review?"
            ]
            reply = random.choice(replies)
        
        return status, reply

class YouTubeAPI(PlatformAPI):
    """YouTube API实现（模拟）"""
    
    def __init__(self, api_config: Dict):
        super().__init__("youtube", api_config)
        self.api_key = api_config.get("api_key", "")
        self.oauth_token = api_config.get("oauth_token", "")
    
    def send_message(self, recipient: str, message: str, subject: Optional[str] = None) -> Tuple[bool, str, str]:
        if not self.check_rate_limit():
            return False, "", "速率限制，请稍后重试"
        
        self.use_rate_limit()
        
        msg_hash = hashlib.md5(f"{recipient}{message}{datetime.now().timestamp()}".encode()).hexdigest()[:16]
        message_id = f"yt_{msg_hash}"
        
        # YouTube模拟成功率较高（90%）
        if random.random() > 0.1:
            print(f"[YouTube] 消息已发送给 {recipient}: {message[:50]}...")
            return True, message_id, ""
        else:
            print(f"[YouTube] 消息发送失败给 {recipient}")
            return False, "", "模拟失败：频道消息功能限制"
    
    def get_message_status(self, message_id: str) -> Tuple[str, Optional[str]]:
        statuses = ["sent", "delivered", "read", "replied"]
        weights = [0.3, 0.3, 0.2, 0.2]
        
        status = random.choices(statuses, weights=weights, k=1)[0]
        
        reply = None
        if status == "replied":
            replies = [
                "Thanks for the partnership offer! Can you share more about your brand?",
                "I specialize in fashion content. This seems like a good fit.",
                "What's the expected timeline for this collaboration?",
                "Do you have examples of previous successful campaigns?",
                "I'm interested but currently booked for the next month."
            ]
            reply = random.choice(replies)
        
        return status, reply

class InstagramAPI(PlatformAPI):
    """Instagram API实现（模拟）"""
    
    def __init__(self, api_config: Dict):
        super().__init__("instagram", api_config)
        self.access_token = api_config.get("access_token", "")
        self.business_account_id = api_config.get("business_account_id", "")
    
    def send_message(self, recipient: str, message: str, subject: Optional[str] = None) -> Tuple[bool, str, str]:
        if not self.check_rate_limit():
            return False, "", "速率限制，请稍后重试"
        
        self.use_rate_limit()
        
        msg_hash = hashlib.md5(f"{recipient}{message}{datetime.now().timestamp()}".encode()).hexdigest()[:16]
        message_id = f"ig_{msg_hash}"
        
        # Instagram模拟成功率（80%）
        if random.random() > 0.2:
            print(f"[Instagram] 消息已发送给 {recipient}: {message[:50]}...")
            return True, message_id, ""
        else:
            print(f"[Instagram] 消息发送失败给 {recipient}")
            return False, "", "模拟失败：用户不接受陌生人消息"
    
    def get_message_status(self, message_id: str) -> Tuple[str, Optional[str]]:
        statuses = ["sent", "delivered", "read", "replied"]
        weights = [0.4, 0.3, 0.1, 0.2]
        
        status = random.choices(statuses, weights=weights, k=1)[0]
        
        reply = None
        if status == "replied":
            replies = [
                "Love your aesthetic! Would love to collaborate.",
                "Thanks for reaching out! What are the terms?",
                "Can you send me the product details?",
                "Do you offer affiliate links?",
                "I only work with sustainable brands. What's your policy?"
            ]
            reply = random.choice(replies)
        
        return status, reply

class XiaohongshuAPI(PlatformAPI):
    """小红书API实现（模拟）"""
    
    def __init__(self, api_config: Dict):
        super().__init__("xiaohongshu", api_config)
        self.auth_token = api_config.get("auth_token", "")
        self.device_id = api_config.get("device_id", "")
    
    def send_message(self, recipient: str, message: str, subject: Optional[str] = None) -> Tuple[bool, str, str]:
        if not self.check_rate_limit():
            return False, "", "速率限制，请稍后重试"
        
        self.use_rate_limit()
        
        msg_hash = hashlib.md5(f"{recipient}{message}{datetime.now().timestamp()}".encode()).hexdigest()[:16]
        message_id = f"xhs_{msg_hash}"
        
        # 小红书模拟成功率（75%）
        if random.random() > 0.25:
            print(f"[小红书] 消息已发送给 {recipient}: {message[:50]}...")
            return True, message_id, ""
        else:
            print(f"[小红书] 消息发送失败给 {recipient}")
            return False, "", "模拟失败：账号未开启私信功能"
    
    def get_message_status(self, message_id: str) -> Tuple[str, Optional[str]]:
        statuses = ["sent", "delivered", "read", "replied"]
        weights = [0.5, 0.2, 0.1, 0.2]
        
        status = random.choices(statuses, weights=weights, k=1)[0]
        
        reply = None
        if status == "replied":
            replies = [
                "这款牛仔外套看起来不错，适合我的风格！",
                "合作方式是什么样的？寄样还是佣金？",
                "请问品牌方是哪里的？",
                "有详细的尺码表吗？",
                "粉丝专属折扣是多少？"
            ]
            reply = random.choice(replies)
        
        return status, reply

class APIManager:
    """平台API管理器"""
    
    def __init__(self, api_configs: Dict[str, Dict]):
        self.apis = {}
        self.api_configs = api_configs
        
        # 初始化各平台API
        for platform, config in api_configs.items():
            if platform.lower() == "tiktok":
                self.apis[platform] = TikTokAPI(config)
            elif platform.lower() == "youtube":
                self.apis[platform] = YouTubeAPI(config)
            elif platform.lower() == "instagram":
                self.apis[platform] = InstagramAPI(config)
            elif platform.lower() in ["xiaohongshu", "redbook"]:
                self.apis[platform] = XiaohongshuAPI(config)
            else:
                print(f"警告: 不支持的平台: {platform}")
    
    def get_api(self, platform: str) -> Optional[PlatformAPI]:
        """获取平台API实例"""
        platform_lower = platform.lower()
        
        # 尝试多种可能的关键词
        if platform_lower in self.apis:
            return self.apis[platform_lower]
        elif platform_lower == "tiktok":
            return self.apis.get("tiktok")
        elif platform_lower == "youtube":
            return self.apis.get("youtube")
        elif platform_lower in ["instagram", "ig"]:
            return self.apis.get("instagram")
        elif platform_lower in ["xiaohongshu", "redbook", "xhs"]:
            return self.apis.get("xiaohongshu")
        
        return None
    
    def send_message(
        self,
        platform: str,
        recipient: str,
        message: str,
        subject: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """发送消息"""
        api = self.get_api(platform)
        if not api:
            return False, "", f"不支持的平台: {platform}"
        
        return api.send_message(recipient, message, subject)
    
    def get_message_status(self, platform: str, message_id: str) -> Tuple[str, Optional[str]]:
        """获取消息状态"""
        api = self.get_api(platform)
        if not api:
            return "failed", f"不支持的平台: {platform}"
        
        return api.get_message_status(message_id)

class MassMessenger:
    """批量私信发送与智能跟进系统"""
    
    def __init__(
        self,
        db_path: str = "data/shared_state/state.db",
        api_configs: Optional[Dict] = None
    ):
        self.db_path = db_path
        self.api_configs = api_configs or self._load_default_configs()
        self.api_manager = APIManager(self.api_configs)
        self.outreach_engine = InfluencerOutreachEngine(db_path)
        
        # 任务队列
        self.task_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None
        
        # 发送统计
        self.stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
            "responses_received": 0
        }
    
    def _load_default_configs(self) -> Dict:
        """加载默认API配置（模拟）"""
        return {
            "tiktok": {
                "session_token": "simulated_tiktok_token",
                "user_id": "simulated_user_123"
            },
            "youtube": {
                "api_key": "simulated_youtube_api_key",
                "oauth_token": "simulated_oauth_token"
            },
            "instagram": {
                "access_token": "simulated_instagram_token",
                "business_account_id": "simulated_business_id"
            },
            "xiaohongshu": {
                "auth_token": "simulated_xhs_token",
                "device_id": "simulated_device_id"
            }
        }
    
    def schedule_campaign(
        self,
        project_name: str,
        batch_size: int = 50,
        delay_seconds: int = 30
    ) -> Tuple[bool, str]:
        """
        调度一个合作项目的批量发送
        
        Args:
            project_name: 项目名称
            batch_size: 每批次发送数量
            delay_seconds: 批次间延迟秒数
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取待处理的合作名单
            cursor.execute("""
                SELECT cl.id, cl.profile_id, ip.platform, ip.contact_info, 
                       ip.display_name, cl.collaboration_type
                FROM influencer_collaboration_list cl
                JOIN influencer_profiles ip ON cl.profile_id = ip.id
                WHERE cl.project_name = ? AND cl.status = 'pending'
                ORDER BY cl.priority_score DESC, cl.created_at ASC
                LIMIT ?
            """, (project_name, batch_size))
            
            pending_tasks = cursor.fetchall()
            
            if not pending_tasks:
                return False, "没有待处理的合作任务"
            
            # 将任务加入队列
            task_count = 0
            for task in pending_tasks:
                collab_id, profile_id, platform, contact_info, display_name, collab_type = task
                
                task_data = {
                    "collaboration_id": collab_id,
                    "profile_id": profile_id,
                    "platform": platform,
                    "contact_info": contact_info,
                    "display_name": display_name,
                    "collaboration_type": collab_type,
                    "project_name": project_name,
                    "scheduled_time": datetime.now()
                }
                
                self.task_queue.put(task_data)
                task_count += 1
            
            print(f"已调度 {task_count} 个任务到队列，项目: {project_name}")
            
            # 启动工作线程（如果未运行）
            if not self.is_running:
                self.start_worker()
            
            return True, f"已调度 {task_count} 个任务"
            
        except Exception as e:
            return False, f"调度失败: {e}"
        finally:
            conn.close()
    
    def start_worker(self):
        """启动工作线程处理队列"""
        if self.is_running:
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        print("批量私信工作线程已启动")
    
    def stop_worker(self):
        """停止工作线程"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        print("批量私信工作线程已停止")
    
    def _process_queue(self):
        """处理任务队列"""
        while self.is_running or not self.task_queue.empty():
            try:
                # 获取任务，最多等待5秒
                task_data = self.task_queue.get(timeout=5)
                
                # 处理任务
                self._process_single_task(task_data)
                
                # 标记任务完成
                self.task_queue.task_done()
                
                # 随机延迟，模拟真实发送间隔
                delay = random.uniform(2.0, 5.0)
                time.sleep(delay)
                
            except queue.Empty:
                # 队列为空，继续等待
                time.sleep(1)
            except Exception as e:
                print(f"处理任务时出错: {e}")
                time.sleep(1)
    
    def _process_single_task(self, task_data: Dict):
        """处理单个发送任务"""
        collab_id = task_data["collaboration_id"]
        platform = task_data["platform"]
        contact_info = task_data["contact_info"]
        display_name = task_data["display_name"]
        collab_type = task_data["collaboration_type"]
        project_name = task_data["project_name"]
        
        print(f"处理任务: 合作ID={collab_id}, 平台={platform}, 达人={display_name}")
        
        # 准备产品信息（示例）
        product_info = {
            "name": "750g美式复古牛仔外套",
            "description": "heavyweight denim jacket with vintage wash",
            "brand": "DenimCraft",
            "price": 129.99,
            "commission_rate": 15,
            "discount_percentage": 15,
            "valid_days": 7
        }
        
        # 准备达人信息
        influencer_info = {
            "display_name": display_name,
            "recent_topic": "fall fashion trends",
            "niche": "fashion"
        }
        
        # 生成个性化消息
        success, message, placeholders = self.outreach_engine.generate_personalized_message(
            collab_type, influencer_info, product_info, platform, "en"
        )
        
        if not success:
            print(f"  生成消息失败")
            
            # 更新状态为失败
            self.outreach_engine.update_collaboration_status(
                collab_id, "failed", "生成个性化消息失败"
            )
            
            self.stats["failed"] += 1
            return
        
        # 发送消息
        send_success, message_id, error_msg = self.api_manager.send_message(
            platform, contact_info, message
        )
        
        self.stats["total_sent"] += 1
        
        if send_success:
            print(f"  发送成功，消息ID: {message_id}")
            
            # 记录发送日志
            self.outreach_engine.send_initial_contact(
                collab_id, influencer_info, product_info, platform
            )
            
            self.stats["successful"] += 1
            
            # 启动状态检查（模拟）
            self._schedule_status_check(collab_id, message_id, platform)
            
        else:
            print(f"  发送失败: {error_msg}")
            
            # 更新状态为失败
            self.outreach_engine.update_collaboration_status(
                collab_id, "failed", f"发送失败: {error_msg}"
            )
            
            self.stats["failed"] += 1
    
    def _schedule_status_check(self, collaboration_id: int, message_id: str, platform: str):
        """调度消息状态检查（模拟）"""
        # 在实际实现中，这里可以启动一个定时任务
        # 现在只记录到数据库
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE influencer_followup_logs 
                SET platform_message_id = ?
                WHERE collaboration_id = ? 
                AND followup_type = 'initial_contact'
                ORDER BY sent_at DESC LIMIT 1
            """, (message_id, collaboration_id))
            
            conn.commit()
        except Exception as e:
            print(f"记录消息ID失败: {e}")
        finally:
            conn.close()
    
    def check_responses(self, hours_back: int = 24) -> List[Dict]:
        """检查过去一段时间内的回复"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查找有平台消息ID但未收到回复的记录
            cursor.execute("""
                SELECT fl.id, fl.collaboration_id, fl.platform_message_id, 
                       cl.profile_id, ip.platform, ip.display_name
                FROM influencer_followup_logs fl
                JOIN influencer_collaboration_list cl ON fl.collaboration_id = cl.id
                JOIN influencer_profiles ip ON cl.profile_id = ip.id
                WHERE fl.response_received = 0 
                AND fl.platform_message_id IS NOT NULL
                AND fl.sent_at >= datetime('now', ?)
                ORDER BY fl.sent_at DESC
            """, (f"-{hours_back} hours",))
            
            pending_checks = cursor.fetchall()
            
            responses = []
            
            for check in pending_checks:
                log_id, collab_id, message_id, profile_id, platform, display_name = check
                
                # 模拟检查消息状态
                status, reply_content = self.api_manager.get_message_status(platform, message_id)
                
                if status == "replied" and reply_content:
                    # 记录回复
                    success = self.outreach_engine.log_response(log_id, reply_content)
                    
                    if success:
                        responses.append({
                            "collaboration_id": collab_id,
                            "influencer": display_name,
                            "platform": platform,
                            "response": reply_content[:100],
                            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                        
                        self.stats["responses_received"] += 1
            
            return responses
            
        except Exception as e:
            print(f"检查回复失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_followup_tasks(self) -> List[Dict]:
        """获取需要跟进的任务"""
        return self.outreach_engine.get_due_followups()
    
    def run_smart_followup(self, limit: int = 20):
        """执行智能跟进"""
        followup_tasks = self.get_followup_tasks()[:limit]
        
        for task in followup_tasks:
            collab_id = task['id']
            
            # 根据状态确定跟进策略
            current_status = task['status']
            
            if current_status == 'contacted':
                # 发送跟进消息
                # 这里简化处理，实际应生成跟进消息
                print(f"  发送跟进消息给合作ID: {collab_id}")
                
                # 更新下次跟进时间
                self.outreach_engine._calculate_next_followup(collab_id, 'followup')
                
            elif current_status == 'replied':
                # 发送谈判跟进
                print(f"  发送谈判跟进给合作ID: {collab_id}")
    
    def get_stats(self) -> Dict:
        """获取发送统计"""
        # 获取数据库中的项目统计
        campaign_stats = self.outreach_engine.get_campaign_stats("750g美式复古牛仔外套推广")
        
        combined_stats = {
            "queue_size": self.task_queue.qsize(),
            "worker_running": self.is_running,
            "sending_stats": self.stats.copy(),
            "campaign_stats": campaign_stats
        }
        
        return combined_stats

# ==================== 主程序 ====================

def test_mass_messenger():
    """测试批量私信系统"""
    print("=== 测试批量私信与智能跟进系统 ===")
    
    # 创建实例
    messenger = MassMessenger()
    
    print("\n1. 调度测试活动:")
    success, msg = messenger.schedule_campaign(
        project_name="750g美式复古牛仔外套推广",
        batch_size=10
    )
    print(f"   {msg}")
    
    print("\n2. 启动工作线程:")
    messenger.start_worker()
    
    # 等待任务处理
    print("\n3. 等待5秒处理任务...")
    time.sleep(5)
    
    print("\n4. 检查回复:")
    responses = messenger.check_responses(hours_back=24)
    print(f"   收到 {len(responses)} 个回复")
    
    if responses:
        for i, resp in enumerate(responses[:3], 1):
            print(f"   回复{i}: {resp['influencer']} - {resp['response']}")
    
    print("\n5. 获取统计:")
    stats = messenger.get_stats()
    print(f"   队列大小: {stats['queue_size']}")
    print(f"   发送总数: {stats['sending_stats']['total_sent']}")
    print(f"   成功数: {stats['sending_stats']['successful']}")
    print(f"   失败数: {stats['sending_stats']['failed']}")
    
    print("\n6. 检查跟进任务:")
    followups = messenger.get_followup_tasks()
    print(f"   有 {len(followups)} 个需要跟进的任务")
    
    print("\n7. 停止工作线程:")
    messenger.stop_worker()
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    # 直接运行此文件时执行测试
    test_mass_messenger()