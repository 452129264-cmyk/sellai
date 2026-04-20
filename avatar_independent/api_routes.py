#!/usr/bin/env python3
"""
独立分身系统 API 路由 v2.5.0
为FastAPI提供独立分身相关的API接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 导入独立分身系统
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from avatar_independent import (
    get_avatar_system,
    list_templates,
    AVAILABLE_TEMPLATES,
    AvatarMessage,
    MessageType,
    Priority
)


# ============================================================
# 请求模型
# ============================================================

class AvatarCreateRequest(BaseModel):
    """创建分身请求"""
    name: str = Field(..., description="分身名称")
    template: str = Field("general_assistant", description="分身模板")
    personality: Optional[Dict[str, Any]] = Field(None, description="自定义人格")
    skills: Optional[List[Dict[str, Any]]] = Field(None, description="自定义技能")


class AvatarMessageRequest(BaseModel):
    """分身消息请求"""
    from_id: str = Field(..., description="发送者ID")
    to_id: str = Field(..., description="接收者ID")
    message_type: str = Field(..., description="消息类型")
    content: Dict[str, Any] = Field(default_factory=dict, description="消息内容")


class TaskAssignRequest(BaseModel):
    """任务分配请求"""
    avatar_id: Optional[str] = Field(None, description="指定分身ID（不指定则自动分配）")
    task_type: str = Field(..., description="任务类型")
    task_data: Dict[str, Any] = Field(default_factory=dict, description="任务数据")
    required_skills: Optional[List[str]] = Field(None, description="所需技能")
    priority: int = Field(1, description="优先级 0-4")


class CollaborationRequest(BaseModel):
    """协作请求"""
    avatar_ids: List[str] = Field(..., description="参与协作的分身ID列表")
    pattern: str = Field("peer_to_peer", description="协作模式")
    task_data: Optional[Dict[str, Any]] = Field(None, description="协作任务数据")


class LearnShareRequest(BaseModel):
    """经验分享请求"""
    from_id: str = Field(..., description="分享者ID")
    experience: Dict[str, Any] = Field(..., description="经验内容")
    lesson: str = Field(..., description="经验总结")
    share_with_all: bool = Field(True, description="是否分享给所有分身")


class MemoryQueryRequest(BaseModel):
    """记忆查询请求"""
    avatar_id: str = Field(..., description="分身ID")
    query: Optional[str] = Field(None, description="查询关键词")
    memory_type: Optional[str] = Field(None, description="记忆类型")
    limit: int = Field(10, description="返回数量限制")


# ============================================================
# 响应模型
# ============================================================

class AvatarResponse(BaseModel):
    """分身响应"""
    success: bool
    avatar_id: Optional[str] = None
    message: str
    data: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """消息响应"""
    success: bool
    message_id: Optional[str] = None
    message: str


class StatusResponse(BaseModel):
    """状态响应"""
    success: bool
    data: Dict[str, Any]


# ============================================================
# API 路由
# ============================================================

# 创建路由
avatar_router = APIRouter(prefix="/api/v2/avatar", tags=["独立分身系统 v2.5.0"])


@avatar_router.get("/system/status")
async def get_system_status():
    """获取独立分身系统状态"""
    try:
        status = get_avatar_system().get_system_status()
        return StatusResponse(success=True, data=status)
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.get("/templates")
async def get_templates():
    """获取所有可用分身模板"""
    return {
        "success": True,
        "templates": AVAILABLE_TEMPLATES
    }


@avatar_router.post("/create")
async def create_avatar(request: AvatarCreateRequest):
    """创建独立运行的AI分身"""
    try:
        system = get_avatar_system()
        
        avatar_id = system.manager.create_avatar(
            name=request.name,
            template=request.template,
            personality=request.personality,
            skills=request.skills
        )
        
        return AvatarResponse(
            success=True,
            avatar_id=avatar_id,
            message=f"分身 '{request.name}' 创建成功",
            data={
                "avatar_id": avatar_id,
                "template": request.template,
                "status": "running"
            }
        )
    except Exception as e:
        logger.error(f"创建分身失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.post("/create/batch")
async def create_batch_avatars(templates: List[str] = None):
    """批量创建预设分身"""
    try:
        system = get_avatar_system()
        created = system.create_system_avatars(templates)
        
        return {
            "success": True,
            "message": f"成功创建 {len(created)} 个分身",
            "data": created
        }
    except Exception as e:
        logger.error(f"批量创建失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.delete("/{avatar_id}")
async def delete_avatar(avatar_id: str):
    """删除分身"""
    try:
        system = get_avatar_system()
        success = system.manager.remove_avatar(avatar_id)
        
        if success:
            return AvatarResponse(
                success=True,
                message=f"分身 {avatar_id} 已删除"
            )
        else:
            raise HTTPException(status_code=404, detail="分身不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除分身失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.get("/list")
async def list_avatars():
    """列出所有分身"""
    try:
        system = get_avatar_system()
        avatars = system.manager.list_avatars()
        
        return {
            "success": True,
            "count": len(avatars),
            "avatars": avatars
        }
    except Exception as e:
        logger.error(f"列出分身失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.get("/{avatar_id}/status")
async def get_avatar_status(avatar_id: str):
    """获取分身独立状态"""
    try:
        system = get_avatar_system()
        status = system.manager.get_avatar_status(avatar_id)
        
        if status:
            return StatusResponse(success=True, data=status)
        else:
            raise HTTPException(status_code=404, detail="分身不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.post("/message")
async def send_message(request: AvatarMessageRequest):
    """给分身发送消息"""
    try:
        system = get_avatar_system()
        success = system.manager.send_message(
            from_id=request.from_id,
            to_id=request.to_id,
            message_type=request.message_type,
            content=request.content
        )
        
        if success:
            return MessageResponse(
                success=True,
                message="消息发送成功"
            )
        else:
            raise HTTPException(status_code=400, detail="消息发送失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.post("/message/broadcast")
async def broadcast_message(message_type: str, content: Dict[str, Any],
                           exclude_ids: List[str] = None):
    """广播消息给所有分身"""
    try:
        system = get_avatar_system()
        results = system.manager.broadcast(message_type, content, exclude_ids)
        
        return {
            "success": True,
            "message": f"广播消息给 {len(results)} 个分身",
            "results": results
        }
    except Exception as e:
        logger.error(f"广播失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.get("/{avatar_id}/memory")
async def get_avatar_memory(avatar_id: str, query: str = None,
                           limit: int = 10):
    """获取分身独立记忆"""
    try:
        system = get_avatar_system()
        memories = system.manager.get_avatar_memory(
            avatar_id, query, limit=limit
        )
        
        return {
            "success": True,
            "avatar_id": avatar_id,
            "count": len(memories),
            "memories": memories
        }
    except Exception as e:
        logger.error(f"获取记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.get("/collective/knowledge")
async def get_collective_knowledge(topic: str, limit_per_avatar: int = 3):
    """获取所有分身的集体知识"""
    try:
        system = get_avatar_system()
        knowledge = system.manager.get_collective_knowledge(
            topic, limit_per_avatar
        )
        
        return {
            "success": True,
            "topic": topic,
            "sources": list(knowledge.keys()),
            "knowledge": knowledge
        }
    except Exception as e:
        logger.error(f"获取集体知识失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.get("/chat/history")
async def get_chat_history(avatar_id: str = None, limit: int = 50):
    """查看分身之间的对话记录"""
    try:
        system = get_avatar_system()
        history = system.manager.get_conversation_history(avatar_id, limit)
        
        return {
            "success": True,
            "count": len(history),
            "history": history
        }
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.post("/task/assign")
async def assign_task(request: TaskAssignRequest):
    """分配任务给分身"""
    try:
        system = get_avatar_system()
        
        if request.avatar_id:
            task_id = system.manager.assign_task(
                avatar_id=request.avatar_id,
                task_type=request.task_type,
                task_data=request.task_data,
                priority=request.priority
            )
        else:
            task_id = system.manager.assign_task_auto(
                task_type=request.task_type,
                task_data=request.task_data,
                required_skills=request.required_skills,
                priority=request.priority
            )
        
        if task_id:
            return MessageResponse(
                success=True,
                message_id=task_id,
                message="任务分配成功"
            )
        else:
            raise HTTPException(status_code=400, detail="任务分配失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分配任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.post("/collaborate")
async def setup_collaboration(request: CollaborationRequest):
    """设置分身协作"""
    try:
        system = get_avatar_system()
        success = system.manager.setup_collaboration(
            avatar_ids=request.avatar_ids,
            pattern=request.pattern
        )
        
        if success:
            return AvatarResponse(
                success=True,
                message=f"协作关系已建立: {request.pattern}"
            )
        else:
            raise HTTPException(status_code=400, detail="协作设置失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置协作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.post("/learn/share")
async def share_learning(request: LearnShareRequest):
    """分享学习经验"""
    try:
        system = get_avatar_system()
        results = system.manager.share_learning(
            from_id=request.from_id,
            experience=request.experience,
            lesson=request.lesson,
            share_with_all=request.share_with_all
        )
        
        return {
            "success": True,
            "message": f"经验已分享给 {len(results)} 个分身",
            "results": results
        }
    except Exception as e:
        logger.error(f"分享经验失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@avatar_router.get("/system/stats")
async def get_system_stats():
    """获取系统完整统计"""
    try:
        system = get_avatar_system()
        stats = system.manager.get_system_stats()
        
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
