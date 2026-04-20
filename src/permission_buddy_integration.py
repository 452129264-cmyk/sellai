#!/usr/bin/env python3
"""
权限与Buddy系统集成模块
将权限管控与Buddy交互系统深度集成

主要功能：
1. 根据用户隐私设置调整Buddy交互行为
2. 在Buddy交互中考虑消息接收时段限制
3. 集成权限变更到Buddy建议系统
4. 记录权限相关的Buddy交互事件
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# 导入现有系统
try:
    from src.permission_manager import PermissionManager, get_permission_manager
    from src.buddy_system import BuddySystem, UserMood, InteractionType
    HAS_BOTH_SYSTEMS = True
except ImportError:
    HAS_BOTH_SYSTEMS = False
    print("警告: 未找到permission_manager或buddy_system，集成功能将不可用")

logger = logging.getLogger(__name__)

class PermissionBuddyIntegration:
    """权限与Buddy系统集成管理器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化集成管理器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        
        # 初始化权限管理器
        self.permission_manager = None
        if HAS_BOTH_SYSTEMS:
            try:
                self.permission_manager = get_permission_manager(db_path)
                logger.info("权限管理器集成成功")
            except Exception as e:
                logger.error(f"权限管理器集成失败: {e}")
        
        # 初始化Buddy系统
        self.buddy_system = None
        if HAS_BOTH_SYSTEMS:
            try:
                # 注意：BuddySystem可能需要特殊处理
                self.buddy_system = BuddySystem(db_path)
                logger.info("Buddy系统集成成功")
            except Exception as e:
                logger.error(f"Buddy系统集成失败: {e}")
        
        # 集成状态
        self.integration_active = False
        
        # 集成配置
        self.integration_config = {
            "respect_privacy_settings": True,
            "adjust_interaction_timing": True,
            "log_permission_events": True,
            "provide_privacy_suggestions": True
        }
        
        logger.info("权限与Buddy系统集成管理器初始化完成")
    
    def start_integration(self):
        """启动集成服务"""
        if self.integration_active:
            logger.warning("集成服务已在运行中")
            return
        
        if not HAS_BOTH_SYSTEMS:
            logger.error("缺少必要的系统组件，无法启动集成服务")
            return
        
        self.integration_active = True
        
        # 注册Buddy交互过滤器
        self._register_buddy_filters()
        
        # 启动集成监控
        self._start_integration_monitoring()
        
        logger.info("权限与Buddy系统集成服务已启动")
    
    def stop_integration(self):
        """停止集成服务"""
        self.integration_active = False
        
        # 注销Buddy交互过滤器
        self._unregister_buddy_filters()
        
        logger.info("权限与Buddy系统集成服务已停止")
    
    def _register_buddy_filters(self):
        """注册Buddy交互过滤器"""
        if not self.buddy_system:
            return
        
        # 这里需要根据BuddySystem的实际接口进行调整
        # 假设BuddySystem有注册过滤器的方法
        try:
            # 注册消息接收时段过滤器
            if hasattr(self.buddy_system, 'register_interaction_filter'):
                self.buddy_system.register_interaction_filter(
                    "permission_time_slot",
                    self._filter_by_time_slot
                )
            
            # 注册AI聊天权限过滤器
            if hasattr(self.buddy_system, 'register_interaction_filter'):
                self.buddy_system.register_interaction_filter(
                    "permission_ai_chat",
                    self._filter_by_ai_chat_permission
                )
            
            logger.info("Buddy交互过滤器注册成功")
            
        except Exception as e:
            logger.error(f"注册Buddy交互过滤器失败: {e}")
    
    def _unregister_buddy_filters(self):
        """注销Buddy交互过滤器"""
        if not self.buddy_system:
            return
        
        try:
            if hasattr(self.buddy_system, 'unregister_interaction_filter'):
                self.buddy_system.unregister_interaction_filter("permission_time_slot")
                self.buddy_system.unregister_interaction_filter("permission_ai_chat")
            
            logger.info("Buddy交互过滤器注销成功")
            
        except Exception as e:
            logger.error(f"注销Buddy交互过滤器失败: {e}")
    
    def _start_integration_monitoring(self):
        """启动集成监控"""
        # 这里可以启动一个后台线程来监控权限变更
        # 并调整Buddy系统的行为
        pass
    
    def _filter_by_time_slot(self, user_id: str, interaction_type: str, **kwargs) -> Tuple[bool, str]:
        """
        根据消息接收时段过滤Buddy交互
        
        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            **kwargs: 其他参数
        
        Returns:
            Tuple[bool, str]: (是否允许交互, 拒绝原因)
        """
        if not self.permission_manager:
            return True, ""
        
        # 检查当前时间是否可以接收消息
        can_receive = self.permission_manager.can_receive_message(user_id)
        
        if not can_receive:
            # 检查交互类型，某些重要交互可能可以忽略时段限制
            if interaction_type in [InteractionType.ALERT.value, InteractionType.REMINDER.value]:
                # 警报和提醒可能更重要，可以发送
                return True, ""
            else:
                current_time = datetime.now().strftime("%H:%M")
                return False, f"当前时间 {current_time} 不在允许的消息接收时段内"
        
        return True, ""
    
    def _filter_by_ai_chat_permission(self, user_id: str, interaction_type: str, **kwargs) -> Tuple[bool, str]:
        """
        根据AI聊天权限过滤Buddy交互
        
        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            **kwargs: 其他参数
        
        Returns:
            Tuple[bool, str]: (是否允许交互, 拒绝原因)
        """
        if not self.permission_manager:
            return True, ""
        
        # 如果交互是AI主动发起的聊天，检查权限
        if interaction_type == InteractionType.GREETING.value and "ai_initiated" in kwargs:
            can_ai_chat = self.permission_manager.can_ai_initiate_chat(user_id)
            
            if not can_ai_chat:
                return False, "用户禁止AI主动发起聊天"
        
        return True, ""
    
    def check_buddy_interaction_allowed(self, user_id: str, interaction_type: str, **kwargs) -> Tuple[bool, str]:
        """
        综合检查Buddy交互是否允许
        
        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            **kwargs: 其他参数
        
        Returns:
            Tuple[bool, str]: (是否允许交互, 拒绝原因)
        """
        if not self.permission_manager:
            return True, ""
        
        # 1. 检查消息接收时段
        can_by_time, time_reason = self._filter_by_time_slot(user_id, interaction_type, **kwargs)
        if not can_by_time:
            return False, time_reason
        
        # 2. 检查AI聊天权限
        can_by_ai, ai_reason = self._filter_by_ai_chat_permission(user_id, interaction_type, **kwargs)
        if not can_by_ai:
            return False, ai_reason
        
        # 3. 检查其他权限（根据交互类型）
        if interaction_type == InteractionType.SUGGESTION.value:
            # 建议类交互可能需要特定权限
            pass
        
        return True, ""
    
    def get_privacy_aware_suggestions(self, user_id: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        获取考虑隐私设置的个性化建议
        
        Args:
            user_id: 用户ID
            context: 上下文信息
        
        Returns:
            List[Dict]: 建议列表
        """
        suggestions = []
        
        if not self.permission_manager or not self.buddy_system:
            return suggestions
        
        # 获取用户隐私设置
        privacy_settings = self.permission_manager.get_user_privacy_settings(user_id)
        
        # 基于隐私设置生成建议
        if not privacy_settings.get('allow_ai_initiated_chat', True):
            suggestions.append({
                'type': 'privacy_reminder',
                'title': 'AI主动聊天已禁用',
                'content': '您已禁用AI主动发起聊天功能。AI分身将不会主动联系您。',
                'relevance_score': 0.8,
                'suggestion': '如需重新启用，请前往隐私设置进行调整。'
            })
        
        if not privacy_settings.get('show_opportunity_push', True):
            suggestions.append({
                'type': 'privacy_reminder',
                'title': '商机推送已隐藏',
                'content': '您已隐藏商机推送功能。AI发现的商机将不会主动推送给您。',
                'relevance_score': 0.7,
                'suggestion': '如需查看商机，请前往商机中心手动查看。'
            })
        
        # 检查消息接收时段设置是否过于严格
        start_hour = privacy_settings.get('receive_message_start_hour', 8)
        end_hour = privacy_settings.get('receive_message_end_hour', 22)
        
        if (end_hour - start_hour) < 8:  # 接收时段小于8小时
            suggestions.append({
                'type': 'privacy_suggestion',
                'title': '消息接收时段建议',
                'content': f'您当前的消息接收时段为 {start_hour}:00-{end_hour}:00，可能错过重要消息。',
                'relevance_score': 0.6,
                'suggestion': '建议适当延长消息接收时段，以确保及时接收重要通知。'
            })
        
        # 检查阅后即焚设置
        if privacy_settings.get('self_destruct_enabled', False):
            destruct_seconds = privacy_settings.get('self_destruct_seconds', 60)
            
            if destruct_seconds < 30:  # 销毁时间过短
                suggestions.append({
                    'type': 'privacy_warning',
                    'title': '阅后即焚时间过短',
                    'content': f'您设置的阅后即焚时间为 {destruct_seconds} 秒，可能影响消息阅读体验。',
                    'relevance_score': 0.9,
                    'suggestion': '建议将销毁时间调整为至少60秒，以确保有足够时间阅读消息。'
                })
        
        return suggestions
    
    def log_permission_aware_interaction(self, user_id: str, interaction_type: str, 
                                       details: Dict[str, Any], allowed: bool = True, 
                                       reason: str = ""):
        """
        记录考虑权限的交互事件
        
        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            details: 交互详情
            allowed: 是否允许
            reason: 允许/拒绝原因
        """
        if not self.permission_manager:
            return
        
        # 记录到权限管理器的审计日志
        operation_type = f"buddy_interaction_{interaction_type}"
        description = f"Buddy交互: {interaction_type} - {'允许' if allowed else '拒绝'}"
        
        if reason:
            description += f"，原因: {reason}"
        
        self.permission_manager._log_permission_operation(
            user_id,
            operation_type,
            description,
            details
        )
        
        logger.info(f"权限感知交互记录: 用户 {user_id}, 交互类型 {interaction_type}, 允许: {allowed}")
    
    def provide_privacy_settings_education(self, user_id: str) -> Dict[str, Any]:
        """
        提供隐私设置教育与指导
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 隐私教育内容
        """
        education_content = {
            'title': '隐私设置指南',
            'sections': [
                {
                    'title': 'AI主动聊天',
                    'content': '控制AI分身是否可以主动联系您。启用后，AI会在发现重要商机或有更新时主动通知您。',
                    'recommendation': '建议保持启用，以充分利用AI助手的能力。'
                },
                {
                    'title': '商机推送',
                    'content': '控制是否显示AI发现的商机推送。禁用后，您需要手动查看商机中心。',
                    'recommendation': '建议保持启用，及时获取赚钱机会。'
                },
                {
                    'title': '消息接收时段',
                    'content': '设置允许接收消息的时间段。在非接收时段，您将不会收到任何消息通知。',
                    'recommendation': '建议根据您的工作和生活习惯设置合适的时段。'
                },
                {
                    'title': '阅后即焚',
                    'content': '设置消息在阅读后自动销毁的时间。增强隐私保护，防止消息被他人查看。',
                    'recommendation': '对于敏感对话，建议启用此功能。'
                },
                {
                    'title': '自动清理',
                    'content': '设置聊天记录的自动清理周期。超过期限的消息将被自动清理。',
                    'recommendation': '建议根据存储空间和合规要求设置合适的保留期限。'
                }
            ],
            'tips': [
                '定期检查隐私设置，确保符合当前需求',
                '不同场景可以使用不同的隐私设置',
                '重要商机建议保持推送通知',
                '敏感对话建议使用阅后即焚功能'
            ]
        }
        
        return education_content
    
    def adjust_buddy_behavior_based_on_permissions(self, user_id: str):
        """
        根据用户权限调整Buddy系统行为
        
        Args:
            user_id: 用户ID
        """
        if not self.permission_manager or not self.buddy_system:
            return
        
        # 获取用户权限和隐私设置
        user_role = self.permission_manager.get_user_role(user_id)
        privacy_settings = self.permission_manager.get_user_privacy_settings(user_id)
        
        # 根据角色调整交互频率
        if user_role == 'guest':
            # 访客：减少交互频率
            self._adjust_interaction_frequency(user_id, multiplier=0.5)
        elif user_role == 'admin':
            # 管理员：增加重要通知频率
            self._adjust_interaction_frequency(user_id, multiplier=1.2)
        
        # 根据隐私设置调整交互时间
        if not privacy_settings.get('allow_ai_initiated_chat', True):
            # 禁止AI主动聊天：调整交互类型
            self._adjust_interaction_types(user_id, exclude_types=['greeting', 'suggestion'])
        
        # 根据消息接收时段调整交互计划
        if privacy_settings.get('receive_message_start_hour', 8) > 8:
            # 较晚开始接收消息：调整早晨的交互计划
            pass


# 单例实例
_permission_buddy_integration_instance = None

def get_permission_buddy_integration(db_path: str = "data/shared_state/state.db") -> PermissionBuddyIntegration:
    """获取权限与Buddy系统集成管理器单例实例"""
    global _permission_buddy_integration_instance
    if _permission_buddy_integration_instance is None:
        _permission_buddy_integration_instance = PermissionBuddyIntegration(db_path)
    return _permission_buddy_integration_instance