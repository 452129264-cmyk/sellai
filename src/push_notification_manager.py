#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SellAI封神版A推送通知管理器
提供微信和邮箱推送通道的配置管理、模板渲染、消息发送和记录查询功能。
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# 配置路径
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'push_config.json')
TEMPLATES_PATH = os.path.join(CONFIG_DIR, 'push_templates.json')
LOGS_DB_PATH = os.path.join(CONFIG_DIR, 'push_logs.db')

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PushNotificationManager:
    """推送通知管理器"""
    
    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = config_path
        self.config = self._load_config()
        self.templates = self._load_templates()
        self._init_logs_db()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载推送配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 默认配置
                default_config = {
                    "user_id": "default_user",
                    "wechat": {
                        "enabled": False,
                        "openid": "",
                        "serverchan_key": ""
                    },
                    "email": {
                        "enabled": False,
                        "address": "",
                        "smtp_server": "smtp.gmail.com",
                        "smtp_port": 587,
                        "smtp_username": "",
                        "smtp_password": ""
                    },
                    "scenes": {
                        "avatar_status": True,
                        "new_opportunity": True,
                        "match_recommendation": True,
                        "chat_message": True
                    },
                    "frequency_limit": {
                        "max_daily": 100,
                        "min_interval_seconds": 60
                    }
                }
                # 保存默认配置
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                return default_config
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return {}
    
    def _load_templates(self) -> Dict[str, Any]:
        """加载推送模板"""
        try:
            if os.path.exists(TEMPLATES_PATH):
                with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 默认模板
                default_templates = {
                    "avatar_status": {
                        "title": "【SellAI】分身状态更新",
                        "content": "分身\"{{avatar_name}}\"状态已变更：{{previous_status}} → {{new_status}}。时间：{{timestamp}}",
                        "link": "{{office_url}}/dashboard#avatars"
                    },
                    "new_opportunity": {
                        "title": "【SellAI】发现新商机",
                        "content": "发现{{platform}}平台{{category}}类目新商机！预估毛利：{{profit_margin}}%，投资额：{{investment_range}}。标题：{{title}}",
                        "link": "{{office_url}}/opportunities#{{opportunity_id}}"
                    },
                    "match_recommendation": {
                        "title": "【SellAI】商务匹配推荐",
                        "content": "{{avatar_name}}为您找到{{match_count}}条匹配商机！最佳匹配：{{best_match_title}}，匹配度：{{match_score}}%",
                        "link": "{{office_url}}/recommendations"
                    },
                    "chat_message": {
                        "title": "【SellAI】新聊天消息",
                        "content": "{{avatar_name}}向您发送了新消息：\"{{message_preview}}...\"",
                        "link": "{{office_url}}/chat/{{avatar_id}}"
                    }
                }
                # 保存默认模板
                os.makedirs(os.path.dirname(TEMPLATES_PATH), exist_ok=True)
                with open(TEMPLATES_PATH, 'w', encoding='utf-8') as f:
                    json.dump(default_templates, f, ensure_ascii=False, indent=2)
                return default_templates
        except Exception as e:
            logger.error(f"加载模板失败: {e}")
            return {}
    
    def _init_logs_db(self):
        """初始化推送记录数据库（SQLite）"""
        try:
            import sqlite3
            conn = sqlite3.connect(LOGS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS push_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    scene_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("推送记录数据库初始化完成")
        except Exception as e:
            logger.error(f"初始化推送记录数据库失败: {e}")
    
    def _render_template(self, template_str: str, data: Dict[str, Any]) -> str:
        """渲染模板字符串"""
        if not template_str:
            return ""
        
        result = template_str
        for key, value in data.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value))
        
        # 替换可能未提供的变量
        import re
        result = re.sub(r'\{\{.*?\}\}', '未知', result)
        return result
    
    def _check_frequency_limit(self) -> bool:
        """检查推送频率限制"""
        try:
            import sqlite3
            conn = sqlite3.connect(LOGS_DB_PATH)
            cursor = conn.cursor()
            
            # 检查24小时内的推送数量
            twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).isoformat()
            cursor.execute('''
                SELECT COUNT(*) FROM push_logs 
                WHERE timestamp > ? AND status = 'success'
            ''', (twenty_four_hours_ago,))
            
            count = cursor.fetchone()[0]
            max_daily = self.config.get('frequency_limit', {}).get('max_daily', 100)
            
            conn.close()
            
            if count >= max_daily:
                logger.warning(f"24小时内推送次数已达上限: {count}/{max_daily}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"检查频率限制失败: {e}")
            return True
    
    def _send_wechat_notification(self, title: str, content: str, link: str = "") -> bool:
        """发送微信推送（通过ServerChan）"""
        config = self.config.get('wechat', {})
        
        if not config.get('enabled', False):
            logger.warning("微信推送未启用")
            return False
        
        serverchan_key = config.get('serverchan_key', '').strip()
        if not serverchan_key:
            logger.warning("ServerChan Key未配置")
            return False
        
        try:
            # ServerChan API（新版）
            url = f"https://sctapi.ftqq.com/{serverchan_key}.send"
            
            payload = {
                "title": title,
                "desp": f"{content}\n\n[查看详情]({link})" if link else content
            }
            
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()
            
            if result.get('code') == 0:
                logger.info(f"微信推送发送成功: {title}")
                return True
            else:
                logger.error(f"微信推送发送失败: {result.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"微信推送发送异常: {e}")
            return False
    
    def _send_email_notification(self, title: str, content: str, link: str = "") -> bool:
        """发送邮箱推送"""
        config = self.config.get('email', {})
        
        if not config.get('enabled', False):
            logger.warning("邮箱推送未启用")
            return False
        
        address = config.get('address', '').strip()
        if not address:
            logger.warning("邮箱地址未配置")
            return False
        
        smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        smtp_port = config.get('smtp_port', 587)
        smtp_username = config.get('smtp_username', '').strip()
        smtp_password = config.get('smtp_password', '').strip()
        
        if not smtp_username or not smtp_password:
            logger.warning("SMTP用户名或密码未配置")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = smtp_username
            msg['To'] = address
            msg['Subject'] = title
            
            # HTML内容
            html_content = f"""
            <html>
            <body>
                <div style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>{title}</h2>
                    <p>{content}</p>
                    {f'<p><a href="{link}">查看详情</a></p>' if link else ''}
                    <hr>
                    <p style="color: #666; font-size: 12px;">
                        此邮件由SellAI封神版A系统自动发送，请勿直接回复。
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # 发送邮件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"邮箱推送发送成功: {title} -> {address}")
            return True
            
        except Exception as e:
            logger.error(f"邮箱推送发送异常: {e}")
            return False
    
    def _log_notification(self, scene_type: str, content: str, channel: str, 
                         recipient: str, status: str, error_message: str = ""):
        """记录推送日志"""
        try:
            import sqlite3
            conn = sqlite3.connect(LOGS_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO push_logs 
                (timestamp, scene_type, content, channel, recipient, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                scene_type,
                content,
                channel,
                recipient,
                status,
                error_message
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录推送日志失败: {e}")
    
    def send_notification(self, scene_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送推送通知
        
        Args:
            scene_type: 场景类型，可选值: avatar_status, new_opportunity, 
                       match_recommendation, chat_message
            data: 模板变量数据
            
        Returns:
            发送结果字典
        """
        # 检查场景是否启用
        scenes = self.config.get('scenes', {})
        if not scenes.get(scene_type, True):
            logger.info(f"场景 {scene_type} 未启用，跳过推送")
            return {
                "success": False,
                "message": f"场景 {scene_type} 未启用",
                "skipped": True
            }
        
        # 检查频率限制
        if not self._check_frequency_limit():
            return {
                "success": False,
                "message": "推送频率超过限制",
                "skipped": True
            }
        
        # 获取模板
        template = self.templates.get(scene_type, {})
        if not template:
            logger.error(f"未找到场景 {scene_type} 的模板")
            return {
                "success": False,
                "message": f"未找到场景 {scene_type} 的模板"
            }
        
        # 渲染模板
        title = self._render_template(template.get('title', ''), data)
        content = self._render_template(template.get('content', ''), data)
        link = self._render_template(template.get('link', ''), data)
        
        # 默认办公室URL
        if '{{office_url}}' in link:
            link = link.replace('{{office_url}}', 'https://sellai-office.example.com')
        
        results = []
        
        # 微信推送
        wechat_success = False
        if self.config.get('wechat', {}).get('enabled', False):
            wechat_success = self._send_wechat_notification(title, content, link)
            self._log_notification(
                scene_type=scene_type,
                content=content,
                channel='wechat',
                recipient=self.config.get('wechat', {}).get('openid', ''),
                status='success' if wechat_success else 'failed',
                error_message='' if wechat_success else '微信推送失败'
            )
            results.append({
                "channel": "wechat",
                "success": wechat_success
            })
        
        # 邮箱推送
        email_success = False
        if self.config.get('email', {}).get('enabled', False):
            email_success = self._send_email_notification(title, content, link)
            self._log_notification(
                scene_type=scene_type,
                content=content,
                channel='email',
                recipient=self.config.get('email', {}).get('address', ''),
                status='success' if email_success else 'failed',
                error_message='' if email_success else '邮箱推送失败'
            )
            results.append({
                "channel": "email",
                "success": email_success
            })
        
        # 如果没有启用任何通道，记录模拟发送
        if not (self.config.get('wechat', {}).get('enabled', False) or 
                self.config.get('email', {}).get('enabled', False)):
            logger.info(f"模拟推送发送: {title}")
            self._log_notification(
                scene_type=scene_type,
                content=content,
                channel='simulation',
                recipient='default_user',
                status='success',
                error_message=''
            )
            results.append({
                "channel": "simulation",
                "success": True
            })
        
        overall_success = any(r['success'] for r in results)
        
        return {
            "success": overall_success,
            "message": f"推送发送完成，结果: {results}",
            "results": results,
            "title": title,
            "content": content,
            "link": link
        }
    
    def update_config(self, wechat_openid: str = None, email: str = None,
                     enabled_scenes: Dict[str, bool] = None, **kwargs) -> bool:
        """更新推送配置"""
        try:
            # 加载当前配置
            current_config = self._load_config()
            
            # 更新微信配置
            if wechat_openid is not None:
                current_config['wechat']['openid'] = wechat_openid
            
            # 更新邮箱配置
            if email is not None:
                current_config['email']['address'] = email
            
            # 更新场景开关
            if enabled_scenes is not None:
                for scene, enabled in enabled_scenes.items():
                    if scene in current_config['scenes']:
                        current_config['scenes'][scene] = enabled
            
            # 更新其他参数
            for key, value in kwargs.items():
                if key in current_config:
                    current_config[key] = value
                elif key.startswith('wechat_'):
                    subkey = key[7:]  # 去掉'wechat_'前缀
                    if subkey in current_config['wechat']:
                        current_config['wechat'][subkey] = value
                elif key.startswith('email_'):
                    subkey = key[6:]  # 去掉'email_'前缀
                    if subkey in current_config['email']:
                        current_config['email'][subkey] = value
            
            # 保存配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, ensure_ascii=False, indent=2)
            
            # 重新加载配置
            self.config = current_config
            logger.info("推送配置更新成功")
            return True
            
        except Exception as e:
            logger.error(f"更新推送配置失败: {e}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """测试推送通道连接"""
        results = {}
        
        # 测试微信推送
        if self.config.get('wechat', {}).get('enabled', False):
            test_data = {
                "avatar_name": "测试分身",
                "previous_status": "离线",
                "new_status": "在线",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            wechat_result = self.send_notification('avatar_status', test_data)
            results['wechat'] = wechat_result
        else:
            results['wechat'] = {
                "success": False,
                "message": "微信推送未启用"
            }
        
        # 测试邮箱推送
        if self.config.get('email', {}).get('enabled', False):
            test_data = {
                "avatar_name": "测试分身",
                "previous_status": "离线",
                "new_status": "在线",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            email_result = self.send_notification('avatar_status', test_data)
            results['email'] = email_result
        else:
            results['email'] = {
                "success": False,
                "message": "邮箱推送未启用"
            }
        
        return results
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取推送统计信息"""
        try:
            import sqlite3
            conn = sqlite3.connect(LOGS_DB_PATH)
            cursor = conn.cursor()
            
            # 计算开始时间
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # 总推送数量
            cursor.execute('''
                SELECT COUNT(*) FROM push_logs WHERE timestamp > ?
            ''', (start_date,))
            total_count = cursor.fetchone()[0]
            
            # 成功推送数量
            cursor.execute('''
                SELECT COUNT(*) FROM push_logs 
                WHERE timestamp > ? AND status = 'success'
            ''', (start_date,))
            success_count = cursor.fetchone()[0]
            
            # 按场景统计
            cursor.execute('''
                SELECT scene_type, COUNT(*) 
                FROM push_logs 
                WHERE timestamp > ?
                GROUP BY scene_type
            ''', (start_date,))
            scenes_stats = dict(cursor.fetchall())
            
            # 按通道统计
            cursor.execute('''
                SELECT channel, COUNT(*) 
                FROM push_logs 
                WHERE timestamp > ?
                GROUP BY channel
            ''', (start_date,))
            channels_stats = dict(cursor.fetchall())
            
            conn.close()
            
            # 计算成功率
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            
            return {
                "total_count": total_count,
                "success_count": success_count,
                "success_rate": round(success_rate, 2),
                "scenes_stats": scenes_stats,
                "channels_stats": channels_stats,
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"获取推送统计失败: {e}")
            return {
                "total_count": 0,
                "success_count": 0,
                "success_rate": 0,
                "scenes_stats": {},
                "channels_stats": {},
                "period_days": days
            }
    
    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的推送记录"""
        try:
            import sqlite3
            conn = sqlite3.connect(LOGS_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM push_logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            logs = []
            for row in rows:
                logs.append({
                    "id": row['id'],
                    "timestamp": row['timestamp'],
                    "scene_type": row['scene_type'],
                    "content": row['content'],
                    "channel": row['channel'],
                    "recipient": row['recipient'],
                    "status": row['status'],
                    "error_message": row['error_message']
                })
            
            return logs
            
        except Exception as e:
            logger.error(f"获取推送记录失败: {e}")
            return []


def main():
    """命令行测试入口"""
    manager = PushNotificationManager()
    
    print("=== SellAI推送通知管理器测试 ===")
    print(f"配置路径: {manager.config_path}")
    print(f"当前配置: {json.dumps(manager.config, ensure_ascii=False, indent=2)}")
    
    # 测试发送通知
    test_data = {
        "avatar_name": "测试分身",
        "previous_status": "离线",
        "new_status": "在线",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "office_url": "https://sellai-office.example.com"
    }
    
    print("\n--- 测试发送分身状态通知 ---")
    result = manager.send_notification('avatar_status', test_data)
    print(f"发送结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 获取统计信息
    print("\n--- 获取推送统计 ---")
    stats = manager.get_statistics(days=7)
    print(f"统计信息: {json.dumps(stats, ensure_ascii=False, indent=2)}")
    
    # 获取最近记录
    print("\n--- 最近推送记录 ---")
    logs = manager.get_recent_logs(limit=5)
    for log in logs:
        print(f"[{log['timestamp']}] {log['scene_type']} - {log['status']}")

if __name__ == "__main__":
    main()