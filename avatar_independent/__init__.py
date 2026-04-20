#!/usr/bin/env python3
"""
独立分身系统初始化模块 v2.5.0
提供统一的导入和初始化接口
"""

import os
import sys
import logging
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 当前模块路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(CURRENT_DIR, "data")

# 导入所有模块
from avatar_process import (
    IndependentAvatar,
    AvatarMemory,
    MessageQueue,
    Personality,
    Skill,
    AvatarState,
    create_avatar_from_template
)

from avatar_protocol import (
    AvatarProtocol,
    AvatarMessage,
    MessageType,
    Priority,
    ProtocolHandler,
    CollaborationPattern,
    MessageTemplate
)

from avatar_manager import (
    AvatarManager,
    AvatarProfile,
    ManagerState,
    get_manager,
    reset_manager
)


# 可用模板列表
AVAILABLE_TEMPLATES = {
    "tiktok_expert": {
        "name": "TikTok运营专家",
        "description": "专注于短视频创作和TikTok运营",
        "expertise": ["短视频创作", "TikTok算法", "流量获取"]
    },
    "seo_master": {
        "name": "SEO优化大师",
        "description": "专业的SEO和搜索引擎优化专家",
        "expertise": ["SEO优化", "关键词研究", "网站排名"]
    },
    "ecommerce_expert": {
        "name": "跨境电商专家",
        "description": "跨境电商全链路运营专家",
        "expertise": ["跨境电商", "供应链", "店铺运营"]
    },
    "influencer_negotiator": {
        "name": "达人洽谈专家",
        "description": "达人合作和商务洽谈专家",
        "expertise": ["达人合作", "商务洽谈", "社交媒体"]
    },
    "general_assistant": {
        "name": "全能助手",
        "description": "综合性AI助手，处理各类任务",
        "expertise": ["多领域", "综合能力"]
    }
}


class IndependentAvatarSystem:
    """
    独立分身系统主类
    提供统一的系统初始化和管理接口
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or BASE_PATH
        self.manager: Optional[AvatarManager] = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """初始化独立分身系统"""
        try:
            # 确保目录存在
            os.makedirs(os.path.join(self.base_path, "avatars"), exist_ok=True)
            os.makedirs(os.path.join(self.base_path, "queues"), exist_ok=True)
            os.makedirs(os.path.join(self.base_path, "logs"), exist_ok=True)
            os.makedirs(os.path.join(self.base_path, "profiles"), exist_ok=True)
            
            # 创建管理器
            self.manager = get_manager(self.base_path)
            
            # 尝试加载已有分身
            self.manager.load_profiles()
            
            self.initialized = True
            logger.info("独立分身系统初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    def create_system_avatars(self, templates: list = None) -> dict:
        """创建系统预设分身"""
        if not self.initialized:
            self.initialize()
        
        templates = templates or ["general_assistant", "ecommerce_expert", "influencer_negotiator"]
        
        created = {}
        for template in templates:
            if template in AVAILABLE_TEMPLATES:
                info = AVAILABLE_TEMPLATES[template]
                avatar_id = self.manager.create_avatar(
                    name=info["name"],
                    template=template
                )
                created[template] = avatar_id
        
        return created
    
    def shutdown(self):
        """关闭系统"""
        if self.manager:
            self.manager._stop()
        self.initialized = False
        logger.info("独立分身系统已关闭")


# 创建全局实例
_system: Optional[IndependentAvatarSystem] = None


def get_avatar_system(base_path: str = None) -> IndependentAvatarSystem:
    """获取独立分身系统实例"""
    global _system
    if _system is None:
        _system = IndependentAvatarSystem(base_path)
        _system.initialize()
    return _system


def initialize_system(base_path: str = None) -> bool:
    """初始化系统"""
    system = get_avatar_system(base_path)
    return system.initialized


# 便捷函数
def list_templates():
    """列出所有可用模板"""
    return AVAILABLE_TEMPLATES


def create_avatar(name: str, template: str = "general_assistant",
                 personality: dict = None, skills: list = None) -> Optional[str]:
    """创建分身快捷函数"""
    system = get_avatar_system()
    if not system.manager:
        return None
    return system.manager.create_avatar(name, template, personality, skills)


def list_all_avatars() -> list:
    """列出所有分身"""
    system = get_avatar_system()
    if not system.manager:
        return []
    return system.manager.list_avatars()


def get_avatar(avatar_id: str):
    """获取分身"""
    system = get_avatar_system()
    if not system.manager:
        return None
    return system.manager.get_avatar(avatar_id)


def send_to_avatar(from_id: str, to_id: str, 
                  message_type: str, content: dict) -> bool:
    """发送消息给分身"""
    system = get_avatar_system()
    if not system.manager:
        return False
    return system.manager.send_message(from_id, to_id, message_type, content)


def get_avatar_status(avatar_id: str) -> dict:
    """获取分身状态"""
    system = get_avatar_system()
    if not system.manager:
        return {}
    return system.manager.get_avatar_status(avatar_id) or {}


def get_avatar_memory(avatar_id: str, query: str = None,
                     limit: int = 10) -> list:
    """获取分身记忆"""
    system = get_avatar_system()
    if not system.manager:
        return []
    return system.manager.get_avatar_memory(avatar_id, query, limit=limit)


def assign_task_auto(task_type: str, task_data: dict,
                    required_skills: list = None) -> Optional[str]:
    """自动分配任务"""
    system = get_avatar_system()
    if not system.manager:
        return None
    return system.manager.assign_task_auto(task_type, task_data, required_skills)


def get_system_status() -> dict:
    """获取系统状态"""
    system = get_avatar_system()
    if not system.manager:
        return {"initialized": False}
    return {
        "initialized": True,
        "status": system.manager.get_manager_status(),
        "templates": list(AVAILABLE_TEMPLATES.keys())
    }


# 导出所有公共接口
__all__ = [
    # 核心类
    'IndependentAvatar',
    'AvatarMemory',
    'MessageQueue',
    'AvatarManager',
    'AvatarProtocol',
    'Personality',
    'Skill',
    
    # 枚举
    'AvatarState',
    'MessageType',
    'Priority',
    'ManagerState',
    
    # 函数
    'get_avatar_system',
    'initialize_system',
    'list_templates',
    'create_avatar',
    'list_all_avatars',
    'get_avatar',
    'send_to_avatar',
    'get_avatar_status',
    'get_avatar_memory',
    'assign_task_auto',
    'get_system_status',
    
    # 常量
    'AVAILABLE_TEMPLATES',
    'BASE_PATH'
]
