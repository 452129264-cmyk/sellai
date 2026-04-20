#!/usr/bin/env python3
"""
分身通信协议 v2.5.0
定义分身之间的标准通信格式和协议
"""

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid


class MessageType(str, Enum):
    """消息类型枚举"""
    # 基础消息类型
    GREET = "greet"                      # 打招呼
    TASK = "task"                        # 分配任务
    RESULT = "result"                    # 返回结果
    HELP = "help"                        # 请求帮助
    LEARN = "learn"                      # 分享经验
    STATUS = "status"                    # 状态同步
    RESPONSE = "response"                # 响应消息
    ERROR = "error"                      # 错误消息
    
    # 协作消息类型
    COLLABORATE = "collaborate"          # 协作请求
    DELEGATE = "delegate"                # 委托任务
    REPORT = "report"                    # 进度报告
    CONSULT = "consult"                  # 咨询意见
    SHARE_KNOWLEDGE = "share_knowledge"  # 分享知识
    
    # 高级消息类型
    NEGOTIATION = "negotiation"          # 商务谈判
    ANALYSIS = "analysis"                # 商业分析
    CREATION = "creation"               # 内容创作
    REVIEW = "review"                    # 审查反馈


class Priority(int, Enum):
    """消息优先级"""
    LOW = 0      # 低优先级
    NORMAL = 1   # 普通优先级
    HIGH = 2     # 高优先级
    URGENT = 3   # 紧急优先级
    CRITICAL = 4 # 关键优先级


@dataclass
class AvatarMessage:
    """标准分身消息格式"""
    from_id: str                         # 发送者ID
    to_id: str | List[str]               # 接收者ID（单个或多个）
    msg_type: MessageType                # 消息类型
    content: Dict[str, Any]              # 消息内容
    timestamp: float = field(default_factory=time.time)  # 时间戳
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 消息ID
    priority: Priority = Priority.NORMAL  # 优先级
    correlation_id: Optional[str] = None # 关联ID（用于追踪相关消息）
    ttl: int = 3600                      # 生存时间（秒）
    retry_count: int = 0                 # 重试次数
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "from": self.from_id,
            "to": self.to_id,
            "type": self.msg_type.value if isinstance(self.msg_type, MessageType) else self.msg_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "priority": int(self.priority) if isinstance(self.priority, Priority) else self.priority,
            "correlation_id": self.correlation_id,
            "ttl": self.ttl,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AvatarMessage':
        """从字典创建"""
        return cls(
            from_id=data.get("from", ""),
            to_id=data.get("to", ""),
            msg_type=MessageType(data.get("type", "response")),
            content=data.get("content", {}),
            timestamp=data.get("timestamp", time.time()),
            message_id=data.get("message_id", str(uuid.uuid4())),
            priority=Priority(data.get("priority", 1)),
            correlation_id=data.get("correlation_id"),
            ttl=data.get("ttl", 3600),
            retry_count=data.get("retry_count", 0),
            metadata=data.get("metadata", {})
        )
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return (time.time() - self.timestamp) > self.ttl
    
    def increment_retry(self) -> bool:
        """增加重试次数"""
        self.retry_count += 1
        return self.retry_count < 3  # 最多重试3次


class AvatarProtocol:
    """分身通信协议"""
    
    # 协议版本
    PROTOCOL_VERSION = "2.5.0"
    
    @staticmethod
    def create_message(from_id: str, to_id: str | List[str], 
                      msg_type: MessageType, content: Dict[str, Any],
                      priority: Priority = Priority.NORMAL,
                      correlation_id: Optional[str] = None) -> AvatarMessage:
        """创建标准消息"""
        return AvatarMessage(
            from_id=from_id,
            to_id=to_id,
            msg_type=msg_type,
            content=content,
            priority=priority,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_greet_message(from_id: str, to_id: str) -> AvatarMessage:
        """创建打招呼消息"""
        return AvatarProtocol.create_message(
            from_id=from_id,
            to_id=to_id,
            msg_type=MessageType.GREET,
            content={
                "greeting": "你好！",
                "capabilities": [],
                "ready": True
            }
        )
    
    @staticmethod
    def create_task_message(from_id: str, to_id: str, 
                           task_type: str, task_data: Dict[str, Any],
                           priority: Priority = Priority.NORMAL,
                           correlation_id: Optional[str] = None) -> AvatarMessage:
        """创建任务消息"""
        return AvatarProtocol.create_message(
            from_id=from_id,
            to_id=to_id,
            msg_type=MessageType.TASK,
            content={
                "task_type": task_type,
                "data": task_data,
                "instructions": task_data.get("instructions", "")
            },
            priority=priority,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_help_message(from_id: str, to_id: str, 
                            topic: str, context: Dict[str, Any] = None) -> AvatarMessage:
        """创建帮助请求消息"""
        return AvatarProtocol.create_message(
            from_id=from_id,
            to_id=to_id,
            msg_type=MessageType.HELP,
            content={
                "topic": topic,
                "context": context or {},
                "urgency": "normal"
            },
            priority=Priority.HIGH
        )
    
    @staticmethod
    def create_learn_message(from_id: str, to_id: str | List[str],
                            experience: Dict[str, Any], 
                            lesson: str = "") -> AvatarMessage:
        """创建学习分享消息"""
        return AvatarProtocol.create_message(
            from_id=from_id,
            to_id=to_id,
            msg_type=MessageType.LEARN,
            content={
                "experience": experience,
                "lesson": lesson,
                "share_with_all": isinstance(to_id, list)
            },
            priority=Priority.NORMAL
        )
    
    @staticmethod
    def create_collaboration_message(from_id: str, to_id: str | List[str],
                                    collaboration_type: str,
                                    task_data: Dict[str, Any]) -> AvatarMessage:
        """创建协作请求消息"""
        return AvatarProtocol.create_message(
            from_id=from_id,
            to_id=to_id,
            msg_type=MessageType.COLLABORATE,
            content={
                "collaboration_type": collaboration_type,
                "task": task_data,
                "roles": task_data.get("roles", {})
            },
            priority=Priority.HIGH
        )
    
    @staticmethod
    def create_status_message(from_id: str, to_id: str) -> AvatarMessage:
        """创建状态查询消息"""
        return AvatarProtocol.create_message(
            from_id=from_id,
            to_id=to_id,
            msg_type=MessageType.STATUS,
            content={
                "request": "status_report",
                "include_details": True
            }
        )
    
    @staticmethod
    def create_negotiation_message(from_id: str, to_id: str,
                                  scenario: str, strategy: str,
                                  context: Dict[str, Any]) -> AvatarMessage:
        """创建商务谈判消息"""
        return AvatarProtocol.create_message(
            from_id=from_id,
            to_id=to_id,
            msg_type=MessageType.NEGOTIATION,
            content={
                "scenario": scenario,
                "strategy": strategy,
                "context": context,
                "counterparty": to_id
            },
            priority=Priority.HIGH
        )
    
    @staticmethod
    def create_analysis_message(from_id: str, to_id: str,
                                analysis_type: str,
                                data: Dict[str, Any]) -> AvatarMessage:
        """创建分析请求消息"""
        return AvatarProtocol.create_message(
            from_id=from_id,
            to_id=to_id,
            msg_type=MessageType.ANALYSIS,
            content={
                "analysis_type": analysis_type,
                "data": data,
                "format": data.get("format", "detailed")
            },
            priority=Priority.NORMAL
        )
    
    @staticmethod
    def parse_message(raw_message: Dict[str, Any]) -> AvatarMessage:
        """解析原始消息"""
        try:
            return AvatarMessage.from_dict(raw_message)
        except Exception as e:
            # 返回错误消息
            return AvatarMessage(
                from_id="system",
                to_id="unknown",
                msg_type=MessageType.ERROR,
                content={
                    "error": str(e),
                    "original": raw_message
                }
            )
    
    @staticmethod
    def validate_message(message: AvatarMessage) -> tuple[bool, str]:
        """验证消息格式"""
        if not message.from_id:
            return False, "缺少发送者ID"
        if not message.to_id:
            return False, "缺少接收者ID"
        if not message.msg_type:
            return False, "缺少消息类型"
        if not message.content:
            return False, "消息内容为空"
        return True, "消息格式正确"


class MessageTemplate:
    """消息模板"""
    
    @staticmethod
    def task_template() -> Dict[str, Any]:
        """标准任务模板"""
        return {
            "task_type": "",
            "data": {},
            "instructions": "",
            "deadline": None,
            "priority": "normal",
            "requirements": []
        }
    
    @staticmethod
    def result_template() -> Dict[str, Any]:
        """标准结果模板"""
        return {
            "status": "completed",
            "result": {},
            "summary": "",
            "errors": [],
            "suggestions": []
        }
    
    @staticmethod
    def help_request_template() -> Dict[str, Any]:
        """帮助请求模板"""
        return {
            "topic": "",
            "context": {},
            "urgency": "normal",
            "preferred_helper": None
        }
    
    @staticmethod
    def status_report_template() -> Dict[str, Any]:
        """状态报告模板"""
        return {
            "avatar_id": "",
            "state": "",
            "current_task": None,
            "progress": 0,
            "metrics": {},
            "availability": True
        }


class CollaborationPattern:
    """协作模式"""
    
    @staticmethod
    def master_worker(master_id: str, worker_ids: List[str]) -> Dict[str, Any]:
        """主从模式 - 主分身负责任务分配，从分身执行"""
        return {
            "pattern": "master_worker",
            "master": master_id,
            "workers": worker_ids,
            "task_distribution": "round_robin",
            "result_aggregation": "sequential"
        }
    
    @staticmethod
    def peer_to_peer(peer_ids: List[str]) -> Dict[str, Any]:
        """点对点模式 - 所有分身地位平等，互帮互助"""
        return {
            "pattern": "peer_to_peer",
            "peers": peer_ids,
            "discovery": "broadcast",
            "consensus": "majority"
        }
    
    @staticmethod
    def pipeline(stages: List[str], avatar_mapping: Dict[str, str]) -> Dict[str, Any]:
        """流水线模式 - 任务按阶段流转"""
        return {
            "pattern": "pipeline",
            "stages": stages,
            "avatar_mapping": avatar_mapping,
            "handoff": "sequential"
        }
    
    @staticmethod
    def hub_spoke(hub_id: str, spoke_ids: List[str]) -> Dict[str, Any]:
        """中心辐射模式 - 中央分身协调边缘分身"""
        return {
            "pattern": "hub_spoke",
            "hub": hub_id,
            "spokes": spoke_ids,
            "routing": "through_hub"
        }


class ProtocolHandler:
    """协议处理器"""
    
    def __init__(self):
        self.handlers = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        self.handlers[MessageType.GREET] = self._handle_greet
        self.handlers[MessageType.TASK] = self._handle_task
        self.handlers[MessageType.HELP] = self._handle_help
        self.handlers[MessageType.LEARN] = self._handle_learn
        self.handlers[MessageType.STATUS] = self._handle_status
        self.handlers[MessageType.COLLABORATE] = self._handle_collaborate
        self.handlers[MessageType.NEGOTIATION] = self._handle_negotiation
        self.handlers[MessageType.ANALYSIS] = self._handle_analysis
    
    def register_handler(self, msg_type: MessageType, handler):
        """注册自定义处理器"""
        self.handlers[msg_type] = handler
    
    def process(self, message: AvatarMessage) -> Optional[AvatarMessage]:
        """处理消息"""
        handler = self.handlers.get(message.msg_type)
        if handler:
            return handler(message)
        return None
    
    def _handle_greet(self, message: AvatarMessage) -> AvatarMessage:
        """处理打招呼"""
        return AvatarProtocol.create_message(
            from_id=message.to_id,
            to_id=message.from_id,
            msg_type=MessageType.RESPONSE,
            content={
                "acknowledged": True,
                "message": f"你好！收到你的问候。"
            }
        )
    
    def _handle_task(self, message: AvatarMessage) -> AvatarMessage:
        """处理任务"""
        return AvatarProtocol.create_message(
            from_id=message.to_id,
            to_id=message.from_id,
            msg_type=MessageType.RESULT,
            content={
                "status": "received",
                "task_type": message.content.get("task_type"),
                "estimated_time": 60
            },
            correlation_id=message.message_id
        )
    
    def _handle_help(self, message: AvatarMessage) -> AvatarMessage:
        """处理帮助请求"""
        return AvatarProtocol.create_message(
            from_id=message.to_id,
            to_id=message.from_id,
            msg_type=MessageType.RESPONSE,
            content={
                "topic": message.content.get("topic"),
                "advice": "正在处理你的帮助请求...",
                "suggestions": []
            }
        )
    
    def _handle_learn(self, message: AvatarMessage) -> AvatarMessage:
        """处理学习请求"""
        return AvatarProtocol.create_message(
            from_id=message.to_id if isinstance(message.to_id, str) else message.to_id[0],
            to_id=message.from_id,
            msg_type=MessageType.RESPONSE,
            content={
                "learned": True,
                "lesson": message.content.get("lesson", "")
            }
        )
    
    def _handle_status(self, message: AvatarMessage) -> AvatarMessage:
        """处理状态查询"""
        return AvatarProtocol.create_message(
            from_id=message.to_id,
            to_id=message.from_id,
            msg_type=MessageType.RESPONSE,
            content={
                "status": "available",
                "state": "idle",
                "capabilities": []
            }
        )
    
    def _handle_collaborate(self, message: AvatarMessage) -> AvatarMessage:
        """处理协作请求"""
        return AvatarProtocol.create_message(
            from_id=message.to_id,
            to_id=message.from_id,
            msg_type=MessageType.RESPONSE,
            content={
                "accepted": True,
                "collaboration_type": message.content.get("collaboration_type")
            }
        )
    
    def _handle_negotiation(self, message: AvatarMessage) -> AvatarMessage:
        """处理谈判请求"""
        return AvatarProtocol.create_message(
            from_id=message.to_id,
            to_id=message.from_id,
            msg_type=MessageType.RESPONSE,
            content={
                "ready": True,
                "strategy": message.content.get("strategy"),
                "counter_offers": []
            }
        )
    
    def _handle_analysis(self, message: AvatarMessage) -> AvatarMessage:
        """处理分析请求"""
        return AvatarProtocol.create_message(
            from_id=message.to_id,
            to_id=message.from_id,
            msg_type=MessageType.RESPONSE,
            content={
                "analysis_type": message.content.get("analysis_type"),
                "results": {},
                "confidence": 0.8
            }
        )


# 创建默认协议处理器实例
default_protocol_handler = ProtocolHandler()
