#!/usr/bin/env python3
"""
SellAI v3.4.0 全自动闭环版
=======================
SellAI AI-SaaS平台 - 全功能商业系统

整合模块清单:
- v2.3.0: AI谈判引擎, AIGC服务中心, 电商集成, 人脸一致性
- v2.4.0: Notebook LM绑定, 原创性检测, 风控合规
- v2.5.0: 独立分身系统, 语音系统
- v2.6.0: 自我进化大脑, Memory V2, 全局调度器, HyperHorse视频
- v3.0.0: 全域商业大脑, AI分身市场, 达人外联, 社交系统, 
          安全系统, 健康监控, 邀请裂变, 任务调度, 
          短视频分发, 聊天系统, 佣金计算, 数据管道, 行业资源
- v3.1.0: 视频生成, 视觉生成, DeepL翻译, 流量爬虫
- v3.2.0: 权限管理, 任务分发, 共享状态, 语音服务, 
          知识驱动分身等95个核心模块
- v3.3.0: 全自动守护进程, 真实爬虫连接, 自动执行链,
          实现无需外部触发的全自动化闭环能力
- v3.4.0: WebSocket实时推送, 后端主动推送商机和分身更新

Author: SellAI Team
Version: 3.4.0
Date: 2026-04-18
"""

import os
import sys
import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict

# FastAPI 相关
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# 配置日志
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sellai_v3.0.0.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# 版本信息
# ============================================================
__version__ = "3.4.3"
VERSION_INFO = {
    "version": "3.4.3",
    "release_date": "2026-04-21",
    "release_name": "静态前端功能补全版（Code漂亮界面+真实API调用）",
    "features": [
        "v3.4.0新增：WebSocket实时推送（商机/分身/任务更新主动推送）",
        "v3.4.0新增：指数退避重连机制",
        "v3.4.0新增：心跳保持连接",
        "v3.3.0新增：全自动守护进程（每30分钟商机扫描，每6小时代码同步）",
        "v3.3.0新增：真实爬虫连接（7大平台真实数据）",
        "v3.3.0新增：自动执行链（商机自动触发分身创建和任务分配）",
        "v3.2.3新增：API配置模块（DeepSeek+百炼）",
        "v3.2.3新增：/api/config/api-status 端点",
        "v3.2.3新增：/api/config/test-deepseek 端点",
        "v3.2.3新增：/api/config/test-bailian 端点",
        "v3.2.0新增功能（从长期任务整合95个核心模块）",
        "权限管理系统",
        "任务分发系统",
        "共享状态管理器",
        "Memory V2索引器/验证器",
        "知识驱动分身"
    ]
}

# ============================================================
# v2.6.0 核心模块导入
# ============================================================
# 自我进化大脑
try:
    from src.self_evolution_brain import SelfEvolutionBrainController
    SELF_EVOLUTION_AVAILABLE = True
except ImportError as e:
    SELF_EVOLUTION_AVAILABLE = False
    logger.warning(f"自我进化大脑模块未加载: {e}")

# v3.3.0 全自动守护进程（使用原有的scrapling模块）
try:
    from src.scrapling.daemon_service import ScraplingDaemon
    from src.scrapling.crawler_engine import ScraplingCrawlerEngine
    DAEMON_SERVICE_AVAILABLE = True
except ImportError as e:
    DAEMON_SERVICE_AVAILABLE = False
    logger.warning(f"Scrapling守护进程模块未加载: {e}")

# Memory V2
try:
    from src.memory_v2_integration import MemoryV2IntegrationManager
    MEMORY_V2_AVAILABLE = True
except ImportError as e:
    MEMORY_V2_AVAILABLE = False
    logger.warning(f"Memory V2模块未加载: {e}")

# 全局调度器
try:
    from src.global_orchestrator import CoreScheduler
    GLOBAL_ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    GLOBAL_ORCHESTRATOR_AVAILABLE = False
    logger.warning(f"全局调度器模块未加载: {e}")

# HyperHorse视频引擎
try:
    from src.hyperhorse import HyperHorseEngine
    HYPERHORSE_AVAILABLE = True
except ImportError as e:
    HYPERHORSE_AVAILABLE = False
    logger.warning(f"HyperHorse视频引擎未加载: {e}")

# ============================================================
# v2.3.0-2.5.0 模块导入
# ============================================================
try:
    from src.ai_negotiation_engine import AINegotiationEngine
    AI_NEGOTIATION_AVAILABLE = True
except ImportError:
    AI_NEGOTIATION_AVAILABLE = False

try:
    from src.aigc_service_center import AIGCServiceCenter
    AIGC_CENTER_AVAILABLE = True
except ImportError:
    AIGC_CENTER_AVAILABLE = False

try:
    from src.banana_ecommerce_integration import EcommerceIntegrationManager
    ECOMMERCE_AVAILABLE = True
except ImportError:
    ECOMMERCE_AVAILABLE = False

try:
    from src.banana_face_consistency import BananaImageGenerationEngine
    FACE_CONSISTENCY_AVAILABLE = True
except ImportError:
    FACE_CONSISTENCY_AVAILABLE = False

try:
    from src.notebook_lm_binding import NotebookLMBindingController
    NOTEBOOK_LM_AVAILABLE = True
except ImportError:
    NOTEBOOK_LM_AVAILABLE = False

try:
    from src.originality_compliance import OriginalityDetectionService
    ORIGINALITY_AVAILABLE = True
except ImportError:
    ORIGINALITY_AVAILABLE = False

try:
    from src.risk_compliance import ComplianceCheckService
    RISK_COMPLIANCE_AVAILABLE = True
except ImportError:
    RISK_COMPLIANCE_AVAILABLE = False

# ============================================================
# v3.0.0 新增模块导入
# ============================================================
# 全域商业大脑
try:
    from src.global_business_brain import GlobalBusinessBrain, InsightType
    GLOBAL_BUSINESS_BRAIN_AVAILABLE = True
except ImportError as e:
    GLOBAL_BUSINESS_BRAIN_AVAILABLE = False
    logger.warning(f"全域商业大脑模块未加载: {e}")

# AI分身市场
try:
    from src.avatar_market import AvatarMarket, ListingType, PricingModel
    from src.avatar_market.marketplace_service import AvatarMarketplaceService, AvatarCategory, AvatarSkillLevel
    AVATAR_MARKET_AVAILABLE = True
except ImportError as e:
    AVATAR_MARKET_AVAILABLE = False
    logger.warning(f"AI分身市场模块未加载: {e}")

# 达人外联引擎
try:
    from src.influencer_outreach_engine import InfluencerOutreachEngine, InfluencerTier, CampaignType
    INFLUENCER_OUTREACH_AVAILABLE = True
except ImportError as e:
    INFLUENCER_OUTREACH_AVAILABLE = False
    logger.warning(f"达人外联引擎模块未加载: {e}")

# 社交关系管理
try:
    from src.social_relationship_manager import SocialRelationshipManager, RelationshipType, UserRole
    SOCIAL_AVAILABLE = True
except ImportError as e:
    SOCIAL_AVAILABLE = False
    logger.warning(f"社交关系管理模块未加载: {e}")

# 安全系统
try:
    from src.multi_layer_security import MultiLayerSecurity, KairosGuardian, UndercoverAuditor, ThreatLevel
    SECURITY_AVAILABLE = True
except ImportError as e:
    SECURITY_AVAILABLE = False
    logger.warning(f"安全系统模块未加载: {e}")

# 健康监控
try:
    from src.health_monitor import HealthMonitor, HealthStatus
    HEALTH_MONITOR_AVAILABLE = True
except ImportError as e:
    HEALTH_MONITOR_AVAILABLE = False
    logger.warning(f"健康监控系统未加载: {e}")

# 邀请裂变
try:
    from src.invitation_fission_manager import InvitationFissionManager, RewardType
    INVITATION_AVAILABLE = True
except ImportError as e:
    INVITATION_AVAILABLE = False
    logger.warning(f"邀请裂变系统未加载: {e}")

# 任务调度
try:
    from src.task_scheduler import TaskScheduler, TaskDispatcher, TaskPriority
    TASK_SCHEDULER_AVAILABLE = True
except ImportError as e:
    TASK_SCHEDULER_AVAILABLE = False
    logger.warning(f"任务调度系统未加载: {e}")

# 短视频分发
try:
    from src.short_video_distributor import ShortVideoDistributor, Platform, PublishStatus
    VIDEO_DISTRIBUTOR_AVAILABLE = True
except ImportError as e:
    VIDEO_DISTRIBUTOR_AVAILABLE = False
    logger.warning(f"短视频分发系统未加载: {e}")

# 聊天系统
try:
    from src.chat_system import ChatManager, MessageType
    CHAT_AVAILABLE = True
except ImportError as e:
    CHAT_AVAILABLE = False
    logger.warning(f"聊天系统未加载: {e}")

# 佣金计算
try:
    from src.commission_calculator import CommissionCalculator, CommissionType
    COMMISSION_AVAILABLE = True
except ImportError as e:
    COMMISSION_AVAILABLE = False
    logger.warning(f"佣金计算系统未加载: {e}")

# 数据同步
try:
    from src.network_data_sync import NetworkDataSync, SharedStateManager
    DATA_SYNC_AVAILABLE = True
except ImportError as e:
    DATA_SYNC_AVAILABLE = False
    logger.warning(f"数据同步系统未加载: {e}")

# 行业资源
try:
    from src.industry_resource_importer import IndustryResourceImporter, Industry, ResourceType
    INDUSTRY_RESOURCE_AVAILABLE = True
except ImportError as e:
    INDUSTRY_RESOURCE_AVAILABLE = False
    logger.warning(f"行业资源导入未加载: {e}")

# ============================================================
# v3.1.0 新增模块导入（从迁移文件同步）
# ============================================================

# Scrapling爬虫框架
try:
    from src.scrapling import CrawlerEngine, ScraperConfig
    SCRAPLING_AVAILABLE = True
except ImportError as e:
    SCRAPLING_AVAILABLE = False
    logger.warning(f"Scrapling爬虫框架未加载: {e}")

# 电商网关（淘宝/拼多多/抖音）
try:
    from src.ecommerce_gateway import EcommerceGateway, get_ecommerce_gateway
    ECOMMERCE_GATEWAY_AVAILABLE = True
except ImportError as e:
    ECOMMERCE_GATEWAY_AVAILABLE = False
    logger.warning(f"电商网关模块未加载: {e}")

# 支付服务
try:
    from src.payment_service import PaymentProcessor, PaymentMethod, PaymentStatus
    PAYMENT_AVAILABLE = True
except ImportError as e:
    PAYMENT_AVAILABLE = False
    logger.warning(f"支付服务未加载: {e}")

# 智能调度器
try:
    from src.scheduler import IntelligentScheduler, MemoryIsolationCore
    SCHEDULER_AVAILABLE = True
except ImportError as e:
    SCHEDULER_AVAILABLE = False
    logger.warning(f"智能调度器未加载: {e}")

# Sora2视频生成
try:
    from src.sora2_integration import Sora2Client, Sora2Workflow
    SORA2_AVAILABLE = True
except ImportError as e:
    SORA2_AVAILABLE = False
    logger.warning(f"Sora2视频生成未加载: {e}")

# Claude Notebook融合
try:
    from src.claude_notebook_fusion import ClaudeNotebookFusion
    CLAUDE_NOTEBOOK_AVAILABLE = True
except ImportError as e:
    CLAUDE_NOTEBOOK_AVAILABLE = False
    logger.warning(f"Claude Notebook融合未加载: {e}")

# 商业匹配引擎
try:
    from src.business_matching import BusinessMatcher
    BUSINESS_MATCHING_AVAILABLE = True
except ImportError as e:
    BUSINESS_MATCHING_AVAILABLE = False
    logger.warning(f"商业匹配引擎未加载: {e}")

# ============================================================
# v3.1.0 新增模块
# ============================================================
# 视频生成服务
try:
    from src.video_generation_service import VideoGenerationService
    VIDEO_GENERATION_AVAILABLE = True
except ImportError as e:
    VIDEO_GENERATION_AVAILABLE = False
    logger.warning(f"视频生成服务未加载: {e}")

# 视觉生成服务
try:
    from src.visual_generation_service import VisualGenerationService
    VISUAL_GENERATION_AVAILABLE = True
except ImportError as e:
    VISUAL_GENERATION_AVAILABLE = False
    logger.warning(f"视觉生成服务未加载: {e}")

# DeepL翻译服务
try:
    from src.deepl_translation_service import DeeplTranslationService
    DEEPL_TRANSLATION_AVAILABLE = True
except ImportError as e:
    DEEPL_TRANSLATION_AVAILABLE = False
    logger.warning(f"DeepL翻译服务未加载: {e}")

# 流量爆破爬虫
try:
    from src.traffic_burst_crawlers import TrafficBurstCrawler
    TRAFFIC_BURST_AVAILABLE = True
except ImportError as e:
    TRAFFIC_BURST_AVAILABLE = False
    logger.warning(f"流量爆破爬虫未加载: {e}")

# ============================================================
# v3.2.0 新增模块导入（从长期任务整合）
# ============================================================
# 权限管理
try:
    from src.permission_manager import PermissionManager
    PERMISSION_MANAGER_AVAILABLE = True
except ImportError as e:
    PERMISSION_MANAGER_AVAILABLE = False
    logger.warning(f"权限管理模块未加载: {e}")

# 任务分发器
try:
    from src.task_dispatcher import TaskDispatcher
    TASK_DISPATCHER_AVAILABLE = True
except ImportError as e:
    TASK_DISPATCHER_AVAILABLE = False
    logger.warning(f"任务分发器未加载: {e}")

# 社交关系API
try:
    from src.social_relationship_api import SocialRelationshipAPI
    SOCIAL_API_AVAILABLE = True
except ImportError as e:
    SOCIAL_API_AVAILABLE = False
    logger.warning(f"社交关系API未加载: {e}")

# 共享状态管理器
try:
    from src.shared_state_manager import SharedStateManager
    SHARED_STATE_MANAGER_AVAILABLE = True
except ImportError as e:
    SHARED_STATE_MANAGER_AVAILABLE = False
    logger.warning(f"共享状态管理器未加载: {e}")

# ============================================================
# v3.2.2 预测性记忆系统（解决502问题关键：延迟加载）
# ============================================================
PREDICTIVE_MEMORY_AVAILABLE = False
_predictive_memory_system = None

def get_predictive_memory_system():
    """延迟加载预测性记忆系统，避免启动时阻塞"""
    global _predictive_memory_system
    if _predictive_memory_system is None:
        try:
            from src.predictive_memory import PredictiveMemorySystem
            _predictive_memory_system = PredictiveMemorySystem()
            logger.info("预测性记忆系统延迟加载完成")
        except ImportError as e:
            logger.warning(f"预测性记忆系统未加载: {e}")
            return None
    return _predictive_memory_system

try:
    from src.bailian_image import (
        bailian_adapter, bailian_adapterSync,
        BailianImageRequest, BailianImageResult, BailianTaskStatus,
        BailianImageStyle, BailianModel
    )
    BAILIAN_AVAILABLE = True
except ImportError as e:
    BAILIAN_AVAILABLE = False
    logger.warning(f"百炼图片生成模块未加载: {e}")

# 百炼图片生成请求模型
class BailianText2ImageRequest(BaseModel):
    prompt: str
    style: str = "photography"
    model: str = "wanx-v1"
    width: int = 1024
    height: int = 1024
    n: int = 1

class BailianImage2ImageRequest(BaseModel):
    prompt: str
    image_url: str
    style: str = "photography"
    strength: float = 0.7

class BailianVirtualModelRequest(BaseModel):
    product_image_url: str
    model_type: str = "standard"

class BailianBackgroundRequest(BaseModel):
    product_image_url: str
    background_prompt: str = "studio white background"

# 全局百炼图片适配器
_bailian_adapter_instance: Optional[Any] = None

def get_bailian_adapter() -> Optional[Any]:
    global _bailian_adapter_instance
    if _bailian_adapter_instance is None and BAILIAN_AVAILABLE:
        try:
            _bailian_adapter_instance = bailian_adapter()
        except Exception as e:
            logger.error(f"初始化百炼图片适配器失败: {e}")
    return _bailian_adapter_instance

# 聊天记忆桥接
try:
    from src.chat_memory_bridge import ChatMemoryBridge
    CHAT_MEMORY_BRIDGE_AVAILABLE = True
except ImportError as e:
    CHAT_MEMORY_BRIDGE_AVAILABLE = False
    logger.warning(f"聊天记忆桥接未加载: {e}")

# 达人面板管理
try:
    from src.add_influencer_panel import InfluencerPanelManager
    INFLUENCER_PANEL_AVAILABLE = True
except ImportError as e:
    INFLUENCER_PANEL_AVAILABLE = False
    logger.warning(f"达人面板管理未加载: {e}")

# 邀请面板管理
try:
    from src.add_invitation_panel import InvitationPanelManager
    INVITATION_PANEL_AVAILABLE = True
except ImportError as e:
    INVITATION_PANEL_AVAILABLE = False
    logger.warning(f"邀请面板管理未加载: {e}")

# 智能路由
try:
    from src.smart_router import SmartRouter
    SMART_ROUTER_AVAILABLE = True
except ImportError as e:
    SMART_ROUTER_AVAILABLE = False
    logger.warning(f"智能路由未加载: {e}")

# 性能基准测试
try:
    from src.performance_benchmark import PerformanceBenchmark
    PERFORMANCE_BENCHMARK_AVAILABLE = True
except ImportError as e:
    PERFORMANCE_BENCHMARK_AVAILABLE = False
    logger.warning(f"性能基准测试未加载: {e}")

# 负载均衡分配器
try:
    from src.load_balanced_allocator import LoadBalancedAllocator
    LOAD_BALANCED_ALLOCATOR_AVAILABLE = True
except ImportError as e:
    LOAD_BALANCED_ALLOCATOR_AVAILABLE = False
    logger.warning(f"负载均衡分配器未加载: {e}")

# 优化任务分配器
try:
    from src.optimized_task_allocator import OptimizedTaskAllocator
    OPTIMIZED_ALLOCATOR_AVAILABLE = True
except ImportError as e:
    OPTIMIZED_ALLOCATOR_AVAILABLE = False
    logger.warning(f"优化任务分配器未加载: {e}")

# 达人群发
try:
    from src.influencer_mass_messenger import InfluencerMassMessenger
    INFLUENCER_MASS_AVAILABLE = True
except ImportError as e:
    INFLUENCER_MASS_AVAILABLE = False
    logger.warning(f"达人群发未加载: {e}")

# 网络服务器
try:
    from src.sellai_network_server import SellaiNetworkServer
    NETWORK_SERVER_AVAILABLE = True
except ImportError as e:
    NETWORK_SERVER_AVAILABLE = False
    logger.warning(f"网络服务器未加载: {e}")

# 网络客户端
try:
    from src.sellai_network_client import SellaiNetworkClient
    NETWORK_CLIENT_AVAILABLE = True
except ImportError as e:
    NETWORK_CLIENT_AVAILABLE = False
    logger.warning(f"网络客户端未加载: {e}")

# 语音合成服务
try:
    from src.voice_synthesis_service import VoiceSynthesisService
    VOICE_SYNTHESIS_AVAILABLE = True
except ImportError as e:
    VOICE_SYNTHESIS_AVAILABLE = False
    logger.warning(f"语音合成服务未加载: {e}")

# 语音识别服务
try:
    from src.voice_recognition_service import VoiceRecognitionService
    VOICE_RECOGNITION_AVAILABLE = True
except ImportError as e:
    VOICE_RECOGNITION_AVAILABLE = False
    logger.warning(f"语音识别服务未加载: {e}")

# 语音对话引擎
try:
    from src.voice_conversation_engine import VoiceConversationEngine
    VOICE_CONVERSATION_AVAILABLE = True
except ImportError as e:
    VOICE_CONVERSATION_AVAILABLE = False
    logger.warning(f"语音对话引擎未加载: {e}")

# 实时音频流
try:
    from src.real_time_audio_stream import RealTimeAudioStream
    AUDIO_STREAM_AVAILABLE = True
except ImportError as e:
    AUDIO_STREAM_AVAILABLE = False
    logger.warning(f"实时音频流未加载: {e}")

# Memory V2索引器
try:
    from src.memory_v2_indexer import MemoryV2Indexer
    MEMORY_V2_INDEXER_AVAILABLE = True
except ImportError as e:
    MEMORY_V2_INDEXER_AVAILABLE = False
    logger.warning(f"Memory V2索引器未加载: {e}")

# Memory V2验证器
try:
    from src.memory_v2_validator import MemoryV2Validator
    MEMORY_V2_VALIDATOR_AVAILABLE = True
except ImportError as e:
    MEMORY_V2_VALIDATOR_AVAILABLE = False
    logger.warning(f"Memory V2验证器未加载: {e}")

# 知识驱动分身
try:
    from src.knowledge_driven_avatar import KnowledgeDrivenAvatar
    KNOWLEDGE_AVATAR_AVAILABLE = True
except ImportError as e:
    KNOWLEDGE_AVATAR_AVAILABLE = False
    logger.warning(f"知识驱动分身未加载: {e}")

# ============================================================
# 创建 FastAPI 应用
# ============================================================
app = FastAPI(
    title="SellAI API",
    description="SellAI v3.0.0 终极完整版 - 全功能AI-SaaS商业平台",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 静态文件服务（前端页面）
# ============================================================
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# 挂载静态文件目录
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    logger.info(f"静态文件目录已挂载: {STATIC_DIR}")

# 前端首页路由
@app.get("/", response_class=FileResponse)
async def read_root():
    """返回前端首页"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SellAI API is running", "docs": "/docs"}

# ============================================================
# v3.4.0 WebSocket实时推送
# ============================================================
import threading
from typing import List

# 全局WebSocket连接管理器
active_websocket_connections: List[WebSocket] = []
ws_lock = threading.Lock()


class WebSocketConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.lock = threading.Lock()
    
    async def connect(self, websocket: WebSocket):
        """接受并注册WebSocket连接"""
        await websocket.accept()
        with self.lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket客户端连接，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """移除WebSocket连接"""
        with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket客户端断开，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送WebSocket消息失败: {e}")
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接的客户端"""
        disconnected = []
        with self.lock:
            connections = self.active_connections.copy()
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"广播消息到客户端失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


# 全局连接管理器实例
ws_manager = WebSocketConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket实时推送端点
    
    客户端连接后，可接收以下类型的消息：
    - opportunities_update: 商机数据更新
    - avatars_update: 分身数据更新
    - tasks_update: 任务数据更新
    - daemon_status: 守护进程状态更新
    - notification: 系统通知
    
    客户端可发送心跳ping消息，服务端会回复pong
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            # 处理心跳
            if data == "ping":
                await websocket.send_text("pong")
                continue
            
            # 尝试解析JSON
            try:
                import json
                msg = json.loads(data)
                msg_type = msg.get("type", "")
                
                # 处理客户端请求
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                elif msg_type == "subscribe":
                    # 客户端订阅特定频道
                    channel = msg.get("channel", "all")
                    logger.info(f"客户端订阅频道: {channel}")
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel,
                        "timestamp": datetime.now().isoformat()
                    })
                elif msg_type == "get_status":
                    # 返回守护进程状态
                    status = {}
                    if app_state.daemon_service:
                        status = app_state.daemon_service.get_daemon_status()
                    await websocket.send_json({
                        "type": "daemon_status",
                        "data": status,
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except json.JSONDecodeError:
                # 非JSON格式，忽略
                pass
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket客户端断开连接")
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        ws_manager.disconnect(websocket)


async def broadcast_to_websockets(message: dict):
    """
    广播消息给所有WebSocket客户端
    
    消息格式:
    {
        "type": "opportunities_update",  # 消息类型
        "data": {...},                   # 消息数据
        "timestamp": "2026-04-18T12:00:00"
    }
    
    用法:
    - 商机更新: broadcast_to_websockets({"type": "opportunities_update", "data": {"count": 10}})
    - 分身更新: broadcast_to_websockets({"type": "avatars_update", "data": {"count": 5}})
    - 任务更新: broadcast_to_websockets({"type": "tasks_update", "data": {...}})
    - 通知: broadcast_to_websockets({"type": "notification", "data": {"title": "新商机", "message": "发现5个新商机"}})
    """
    message["timestamp"] = datetime.now().isoformat()
    await ws_manager.broadcast(message)
    logger.info(f"WebSocket广播消息: {message.get('type', 'unknown')}")


# ============================================================
# 全局状态管理
# ============================================================
class AppState:
    """应用全局状态"""
    def __init__(self):
        # v2.6.0 模块
        self.evolution_controller = None
        self.memory_integration = None
        self.global_orchestrator = None
        self.hyperhorse_engine = None
        
        # v3.0.0 新增模块
        self.business_brain = None
        self.avatar_market = None
        self.avatar_marketplace = None  # AI分身定制市场服务
        self.influencer_engine = None
        self.social_manager = None
        self.security_system = None
        self.kairos_guardian = None
        self.undercover_auditor = None
        self.health_monitor = None
        self.invitation_manager = None
        self.task_scheduler = None
        self.task_dispatcher = None
        self.video_distributor = None
        self.chat_manager = None
        self.commission_calculator = None
        self.network_sync = None
        self.shared_state = None
        self.industry_resource = None
        
        # v3.2.0 新增模块
        self.permission_manager = None
        self.task_dispatcher = None
        self.social_relationship_api = None
        self.shared_state_manager = None
        self.chat_memory_bridge = None
        self.influencer_panel_manager = None
        self.invitation_panel_manager = None
        self.smart_router = None
        self.performance_benchmark = None
        self.load_balanced_allocator = None
        self.optimized_task_allocator = None
        self.influencer_mass_messenger = None
        self.network_server = None
        self.network_client = None
        self.voice_synthesis = None
        self.voice_recognition = None
        self.voice_conversation = None
        self.audio_stream = None
        self.memory_v2_indexer = None
        self.memory_v2_validator = None
        self.knowledge_avatar = None
        
        # v3.3.0 全自动闭环模块
        self.daemon_service = None
        self.real_crawler = None
        self.auto_execution_chain = None
        
        # 电商网关
        self.ecommerce_gateway = None
        
        self.startup_time = datetime.now()
        self._init_all_modules()
    
    def _init_all_modules(self):
        """初始化所有模块"""
        db_path = "data/shared_state/state.db"
        os.makedirs("data/shared_state", exist_ok=True)
        
        # v2.6.0 模块初始化
        if SELF_EVOLUTION_AVAILABLE:
            try:
                self.evolution_controller = SelfEvolutionBrainController(db_path=db_path)
                logger.info("✓ 自我进化大脑启动成功")
            except Exception as e:
                logger.error(f"✗ 自我进化大脑启动失败: {e}")
        
        if MEMORY_V2_AVAILABLE:
            try:
                self.memory_integration = MemoryV2IntegrationManager(db_path=db_path)
                logger.info("✓ Memory V2启动成功")
            except Exception as e:
                logger.error(f"✗ Memory V2启动失败: {e}")
        
        if GLOBAL_ORCHESTRATOR_AVAILABLE:
            try:
                self.global_orchestrator = CoreScheduler(db_path=db_path)
                logger.info("✓ 全局调度器启动成功")
            except Exception as e:
                logger.error(f"✗ 全局调度器启动失败: {e}")
        
        if HYPERHORSE_AVAILABLE:
            try:
                self.hyperhorse_engine = HyperHorseEngine(db_path=db_path)
                logger.info("✓ HyperHorse视频引擎启动成功")
            except Exception as e:
                logger.error(f"✗ HyperHorse视频引擎启动失败: {e}")
        
        # v3.0.0 模块初始化
        if GLOBAL_BUSINESS_BRAIN_AVAILABLE:
            try:
                self.business_brain = GlobalBusinessBrain(db_path=db_path)
                logger.info("✓ 全域商业大脑启动成功")
            except Exception as e:
                logger.error(f"✗ 全域商业大脑启动失败: {e}")
        
        if AVATAR_MARKET_AVAILABLE:
            try:
                self.avatar_market = AvatarMarket(db_path=db_path)
                self.avatar_marketplace = AvatarMarketplaceService()
                logger.info("✓ AI分身市场启动成功")
            except Exception as e:
                logger.error(f"✗ AI分身市场启动失败: {e}")
        
        if INFLUENCER_OUTREACH_AVAILABLE:
            try:
                self.influencer_engine = InfluencerOutreachEngine(db_path=db_path)
                logger.info("✓ 达人外联引擎启动成功")
            except Exception as e:
                logger.error(f"✗ 达人外联引擎启动失败: {e}")
        
        if SOCIAL_AVAILABLE:
            try:
                self.social_manager = SocialRelationshipManager(db_path=db_path)
                logger.info("✓ 社交关系管理启动成功")
            except Exception as e:
                logger.error(f"✗ 社交关系管理启动失败: {e}")
        
        if SECURITY_AVAILABLE:
            try:
                self.security_system = MultiLayerSecurity(db_path=db_path)
                self.kairos_guardian = KairosGuardian()
                self.undercover_auditor = UndercoverAuditor()
                logger.info("✓ 安全系统启动成功")
            except Exception as e:
                logger.error(f"✗ 安全系统启动失败: {e}")
        
        if HEALTH_MONITOR_AVAILABLE:
            try:
                self.health_monitor = HealthMonitor(db_path=db_path)
                logger.info("✓ 健康监控系统启动成功")
            except Exception as e:
                logger.error(f"✗ 健康监控系统启动失败: {e}")
        
        if INVITATION_AVAILABLE:
            try:
                self.invitation_manager = InvitationFissionManager(db_path=db_path)
                logger.info("✓ 邀请裂变系统启动成功")
            except Exception as e:
                logger.error(f"✗ 邀请裂变系统启动失败: {e}")
        
        if TASK_SCHEDULER_AVAILABLE:
            try:
                self.task_scheduler = TaskScheduler(db_path=db_path)
                self.task_dispatcher = TaskDispatcher()
                logger.info("✓ 任务调度系统启动成功")
            except Exception as e:
                logger.error(f"✗ 任务调度系统启动失败: {e}")
        
        if VIDEO_DISTRIBUTOR_AVAILABLE:
            try:
                self.video_distributor = ShortVideoDistributor(db_path=db_path)
                logger.info("✓ 短视频分发系统启动成功")
            except Exception as e:
                logger.error(f"✗ 短视频分发系统启动失败: {e}")
        
        if CHAT_AVAILABLE:
            try:
                self.chat_manager = ChatManager()
                logger.info("✓ 聊天系统启动成功")
            except Exception as e:
                logger.error(f"✗ 聊天系统启动失败: {e}")
        
        if COMMISSION_AVAILABLE:
            try:
                self.commission_calculator = CommissionCalculator(db_path=db_path)
                logger.info("✓ 佣金计算系统启动成功")
            except Exception as e:
                logger.error(f"✗ 佣金计算系统启动失败: {e}")
        
        if DATA_SYNC_AVAILABLE:
            try:
                self.network_sync = NetworkDataSync(db_path=db_path)
                self.shared_state = SharedStateManager(db_path=db_path)
                logger.info("✓ 数据同步系统启动成功")
            except Exception as e:
                logger.error(f"✗ 数据同步系统启动失败: {e}")
        
        if INDUSTRY_RESOURCE_AVAILABLE:
            try:
                self.industry_resource = IndustryResourceImporter(db_path=db_path)
                logger.info("✓ 行业资源导入启动成功")
            except Exception as e:
                logger.error(f"✗ 行业资源导入启动失败: {e}")
        
        # ========== v3.2.0 模块初始化 ==========
        
        if PERMISSION_MANAGER_AVAILABLE:
            try:
                self.permission_manager = PermissionManager(db_path=db_path)
                logger.info("✓ 权限管理模块启动成功")
            except Exception as e:
                logger.error(f"✗ 权限管理模块启动失败: {e}")
        
        if TASK_DISPATCHER_AVAILABLE:
            try:
                self.task_dispatcher = TaskDispatcher(db_path=db_path)
                logger.info("✓ 任务分发器启动成功")
            except Exception as e:
                logger.error(f"✗ 任务分发器启动失败: {e}")
        
        if SOCIAL_API_AVAILABLE:
            try:
                self.social_relationship_api = SocialRelationshipAPI(db_path=db_path)
                logger.info("✓ 社交关系API启动成功")
            except Exception as e:
                logger.error(f"✗ 社交关系API启动失败: {e}")
        
        if SHARED_STATE_MANAGER_AVAILABLE:
            try:
                self.shared_state_manager = SharedStateManager(db_path=db_path)
                logger.info("✓ 共享状态管理器启动成功")
            except Exception as e:
                logger.error(f"✗ 共享状态管理器启动失败: {e}")
        
        if CHAT_MEMORY_BRIDGE_AVAILABLE:
            try:
                self.chat_memory_bridge = ChatMemoryBridge()
                logger.info("✓ 聊天记忆桥接启动成功")
            except Exception as e:
                logger.error(f"✗ 聊天记忆桥接启动失败: {e}")
        
        if INFLUENCER_PANEL_AVAILABLE:
            try:
                self.influencer_panel_manager = InfluencerPanelManager(db_path=db_path)
                logger.info("✓ 达人面板管理启动成功")
            except Exception as e:
                logger.error(f"✗ 达人面板管理启动失败: {e}")
        
        if INVITATION_PANEL_AVAILABLE:
            try:
                self.invitation_panel_manager = InvitationPanelManager(db_path=db_path)
                logger.info("✓ 邀请面板管理启动成功")
            except Exception as e:
                logger.error(f"✗ 邀请面板管理启动失败: {e}")
        
        if SMART_ROUTER_AVAILABLE:
            try:
                self.smart_router = SmartRouter()
                logger.info("✓ 智能路由启动成功")
            except Exception as e:
                logger.error(f"✗ 智能路由启动失败: {e}")
        
        if PERFORMANCE_BENCHMARK_AVAILABLE:
            try:
                self.performance_benchmark = PerformanceBenchmark()
                logger.info("✓ 性能基准测试启动成功")
            except Exception as e:
                logger.error(f"✗ 性能基准测试启动失败: {e}")
        
        if LOAD_BALANCED_ALLOCATOR_AVAILABLE:
            try:
                self.load_balanced_allocator = LoadBalancedAllocator()
                logger.info("✓ 负载均衡分配器启动成功")
            except Exception as e:
                logger.error(f"✗ 负载均衡分配器启动失败: {e}")
        
        if OPTIMIZED_ALLOCATOR_AVAILABLE:
            try:
                self.optimized_task_allocator = OptimizedTaskAllocator()
                logger.info("✓ 优化任务分配器启动成功")
            except Exception as e:
                logger.error(f"✗ 优化任务分配器启动失败: {e}")
        
        if INFLUENCER_MASS_AVAILABLE:
            try:
                self.influencer_mass_messenger = InfluencerMassMessenger(db_path=db_path)
                logger.info("✓ 达人群发启动成功")
            except Exception as e:
                logger.error(f"✗ 达人群发启动失败: {e}")
        
        if NETWORK_SERVER_AVAILABLE:
            try:
                self.network_server = SellaiNetworkServer()
                logger.info("✓ 网络服务器启动成功")
            except Exception as e:
                logger.error(f"✗ 网络服务器启动失败: {e}")
        
        if NETWORK_CLIENT_AVAILABLE:
            try:
                self.network_client = SellaiNetworkClient()
                logger.info("✓ 网络客户端启动成功")
            except Exception as e:
                logger.error(f"✗ 网络客户端启动失败: {e}")
        
        if VOICE_SYNTHESIS_AVAILABLE:
            try:
                self.voice_synthesis = VoiceSynthesisService()
                logger.info("✓ 语音合成服务启动成功")
            except Exception as e:
                logger.error(f"✗ 语音合成服务启动失败: {e}")
        
        if VOICE_RECOGNITION_AVAILABLE:
            try:
                self.voice_recognition = VoiceRecognitionService()
                logger.info("✓ 语音识别服务启动成功")
            except Exception as e:
                logger.error(f"✗ 语音识别服务启动失败: {e}")
        
        if VOICE_CONVERSATION_AVAILABLE:
            try:
                self.voice_conversation = VoiceConversationEngine()
                logger.info("✓ 语音对话引擎启动成功")
            except Exception as e:
                logger.error(f"✗ 语音对话引擎启动失败: {e}")
        
        if AUDIO_STREAM_AVAILABLE:
            try:
                self.audio_stream = RealTimeAudioStream()
                logger.info("✓ 实时音频流启动成功")
            except Exception as e:
                logger.error(f"✗ 实时音频流启动失败: {e}")
        
        if MEMORY_V2_INDEXER_AVAILABLE:
            try:
                self.memory_v2_indexer = MemoryV2Indexer(db_path=db_path)
                logger.info("✓ Memory V2索引器启动成功")
            except Exception as e:
                logger.error(f"✗ Memory V2索引器启动失败: {e}")
        
        if MEMORY_V2_VALIDATOR_AVAILABLE:
            try:
                self.memory_v2_validator = MemoryV2Validator(db_path=db_path)
                logger.info("✓ Memory V2验证器启动成功")
            except Exception as e:
                logger.error(f"✗ Memory V2验证器启动失败: {e}")
        
        if KNOWLEDGE_AVATAR_AVAILABLE:
            try:
                # KnowledgeDrivenAvatar 是抽象类，跳过直接实例化
                logger.info("✓ 知识驱动分身模块已加载（按需初始化）")
            except Exception as e:
                logger.error(f"✗ 知识驱动分身启动失败: {e}")
        
        # ========== v3.3.0 全自动守护进程初始化 ==========
        
        if DAEMON_SERVICE_AVAILABLE:
            try:
                self.scrapling_daemon = ScraplingDaemon(db_path=db_path)
                self.scrapling_daemon.start()
                logger.info("✓ Scrapling全自动守护进程启动成功 - 每30分钟自动爬取商机")
            except Exception as e:
                logger.error(f"✗ Scrapling守护进程启动失败: {e}")
        
        # 电商网关初始化
        if ECOMMERCE_GATEWAY_AVAILABLE:
            try:
                self.ecommerce_gateway = get_ecommerce_gateway()
                logger.info("✓ 电商网关启动成功")
            except Exception as e:
                logger.error(f"✗ 电商网关启动失败: {e}")

# 创建全局状态实例
app_state = AppState()

# ============================================================
# Pydantic模型定义
# ============================================================

# v3.0.0 商业大脑相关
class BusinessInsightRequest(BaseModel):
    insight_type: str = "market_trend"
    context: Dict[str, Any] = {}
    data_sources: Optional[List[str]] = None

class MarketAnalysisRequest(BaseModel):
    market_name: str
    data_sources: Optional[List[str]] = None

class CompetitorAnalysisRequest(BaseModel):
    competitor_name: str
    data_sources: Optional[List[str]] = None

class DemandPredictionRequest(BaseModel):
    product_id: str
    forecast_days: int = 30

# v3.0.0 AI分身市场相关
class CreateListingRequest(BaseModel):
    title: str
    description: str
    listing_type: str = "avatar_template"
    category: str
    tags: List[str] = []
    pricing_model: str = "subscription"
    price: float
    capabilities: Optional[List[str]] = None

class SearchListingRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    listing_type: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    limit: int = 20

class CreateReviewRequest(BaseModel):
    listing_id: str
    buyer_id: str
    rating: float
    title: str
    content: str
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None

# v3.0.0 达人外联相关
class AddInfluencerRequest(BaseModel):
    name: str
    platform: str
    handle: str
    profile_url: str
    follower_count: int
    categories: List[str]
    engagement_rate: float = 0.0

class SearchInfluencerRequest(BaseModel):
    platform: Optional[str] = None
    categories: Optional[List[str]] = None
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    min_engagement: Optional[float] = None
    limit: int = 20

class CreateCampaignRequest(BaseModel):
    name: str
    description: str
    campaign_type: str = "product_review"
    target_platforms: List[str]
    target_categories: List[str]
    target_tiers: List[str]
    budget: float
    deadline: str
    deliverables: List[str]
    compensation: str

class InitiateOutreachRequest(BaseModel):
    influencer_id: str
    campaign_id: str
    contact_method: str = "email"
    message_template: str = "initial_contact"

# v3.0.0 社交相关
class CreateUserRequest(BaseModel):
    username: str
    display_name: str
    email: str

class CreateRelationshipRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    relationship_type: str = "follower"

class CreateCommunityRequest(BaseModel):
    name: str
    description: str
    owner_id: str

class RecordInteractionRequest(BaseModel):
    user_id: str
    target_type: str
    target_id: str
    interaction_type: str
    content: Optional[str] = None

# v3.0.0 安全相关
class GenerateApiKeyRequest(BaseModel):
    name: str
    permissions: List[str]
    expires_days: int = 90

class BlockIpRequest(BaseModel):
    ip_address: str
    reason: str
    duration_hours: int = 24

# v3.0.0 健康监控相关
class RecordMetricRequest(BaseModel):
    name: str
    value: float
    unit: str = ""
    tags: Optional[Dict[str, str]] = None

class CreateAlertRequest(BaseModel):
    level: str
    title: str
    message: str
    component: str

# v3.0.0 邀请裂变相关
class CreateInvitationRequest(BaseModel):
    inviter_id: str

class CreateRewardRuleRequest(BaseModel):
    name: str
    description: str
    reward_type: str
    reward_amount: float
    condition_type: str
    condition_value: float

class CreateFissionCampaignRequest(BaseModel):
    name: str
    description: str
    reward_rule_ids: List[str]
    start_date: str
    end_date: str
    referral_limit: int = 100

# v3.0.0 任务调度相关
class CreateTaskRequest(BaseModel):
    name: str
    handler: str
    payload: Dict[str, Any] = {}
    priority: int = 2
    task_type: str = "sync"
    timeout: int = 300

class CreateScheduledTaskRequest(BaseModel):
    name: str
    handler: str
    cron_expression: str

# v3.0.0 短视频分发相关
class ConnectAccountRequest(BaseModel):
    platform: str
    username: str
    access_token: str
    display_name: Optional[str] = None

class CreateContentRequest(BaseModel):
    title: str
    description: str
    hashtags: List[str] = []
    mentions: List[str] = []
    language: str = "en"

class CreatePublishTaskRequest(BaseModel):
    content_id: str
    platform: str
    account_id: str
    scheduled_time: Optional[str] = None

# v3.0.0 聊天相关
class CreateChatRequest(BaseModel):
    name: str
    chat_type: str
    created_by: str
    members: Optional[List[str]] = None

class SendMessageRequest(BaseModel):
    chat_id: str
    sender_id: str
    message_type: str = "text"
    content: str
    metadata: Optional[Dict[str, Any]] = None

# v3.0.0 佣金相关
class CalculateCommissionRequest(BaseModel):
    user_id: str
    source_user_id: str
    order_id: str
    amount: float
    level: int = 0

# v3.0.0 数据同步相关
class PutDataRequest(BaseModel):
    key: str
    value: Any
    metadata: Optional[Dict[str, Any]] = None

class SetStateRequest(BaseModel):
    key: str
    value: Any
    locker_id: Optional[str] = None

# v3.0.0 行业资源相关
class ImportResourceRequest(BaseModel):
    name: str
    description: str
    industry: str
    resource_type: str
    source: str
    tags: Optional[List[str]] = None

# 保留的v2.6.0模型
class EvolutionReviewRequest(BaseModel):
    time_range: Optional[str] = "24h"
    avatar_id: Optional[str] = None
    include_recommendations: bool = True

class MemoryManageRequest(BaseModel):
    action: str
    memory_data: Optional[Dict[str, Any]] = None
    memory_id: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None

class OrchestrateTaskRequest(BaseModel):
    task_type: str
    priority: int = 2
    payload: Dict[str, Any]

class HyperHorseVideoRequest(BaseModel):
    video_type: str
    product_info: Dict[str, Any]
    target_platform: str
    target_language: str = "en"
    quality_level: str = "premium"

# v2.3.0模型
class NegotiationRequest(BaseModel):
    negotiation_id: str
    action: str
    context: Optional[Dict[str, Any]] = None

class AIGCGenerateRequest(BaseModel):
    content_type: str
    prompt: str
    style: Optional[str] = "professional"

# ============================================================
# 电商API模型（v3.3.0 淘宝/拼多多/抖音）
# ============================================================

class TaobaoItemRequest(BaseModel):
    """淘宝商品详情请求"""
    item_id: str
    fields: Optional[List[str]] = None

class TaobaoSearchRequest(BaseModel):
    """淘宝商品搜索请求"""
    keyword: str
    page: int = 1
    page_size: int = 20
    sort: str = "tk_total_sales_desc"
    is_tmall: bool = False
    is_overseas: bool = False
    start_price: int = 0
    end_price: int = 0

class PddSearchRequest(BaseModel):
    """拼多多商品搜索请求"""
    keyword: str = ""
    cat_id: int = 0
    page: int = 1
    page_size: int = 20
    sort_type: int = 0
    with_coupon: bool = False

class DouyinProductRequest(BaseModel):
    """抖音商品列表请求"""
    page: int = 1
    size: int = 20
    status: Optional[int] = None
    product_ids: Optional[List[str]] = None

class OrderRequest(BaseModel):
    """统一订单查询请求"""
    platform: str = "all"  # taobao/pdd/douyin/all
    status: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    page: int = 1
    page_size: int = 50

class UnifiedSearchRequest(BaseModel):
    """统一商品搜索请求"""
    platform: str = "all"  # taobao/pdd/douyin/all
    keyword: str
    page: int = 1
    page_size: int = 20

class EcommerceConfigRequest(BaseModel):
    """电商配置更新请求"""
    platform: str  # taobao/pdd/douyin
    config: Dict[str, Any]

class PromotionUrlRequest(BaseModel):
    """推广链接生成请求"""
    platform: str
    item_id: str
    with_coupon: bool = True

# ============================================================
# 基础端点
# ============================================================

@app.get("/")
@app.get("/office")
async def root():
    from fastapi.responses import FileResponse
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SellAI API", "version": __version__, "docs": "/docs"}

@app.get("/health")
async def health_check():
    uptime = (datetime.now() - app_state.startup_time).total_seconds()
    
    modules = {
        # v2.6.0
        "self_evolution": app_state.evolution_controller is not None,
        "memory_v2": app_state.memory_integration is not None,
        "global_orchestrator": app_state.global_orchestrator is not None,
        "hyperhorse": app_state.hyperhorse_engine is not None,
        # v2.3.0
        "ai_negotiation": AI_NEGOTIATION_AVAILABLE,
        "aigc_center": AIGC_CENTER_AVAILABLE,
        "ecommerce": ECOMMERCE_AVAILABLE,
        "face_consistency": FACE_CONSISTENCY_AVAILABLE,
        "notebook_lm": NOTEBOOK_LM_AVAILABLE,
        "originality": ORIGINALITY_AVAILABLE,
        "risk_compliance": RISK_COMPLIANCE_AVAILABLE,
        # v3.0.0
        "business_brain": app_state.business_brain is not None,
        "avatar_market": app_state.avatar_market is not None,
        "avatar_marketplace": app_state.avatar_marketplace is not None,  # AI分身定制市场
        "influencer_outreach": app_state.influencer_engine is not None,
        "social": app_state.social_manager is not None,
        "security": app_state.security_system is not None,
        "health_monitor": app_state.health_monitor is not None,
        "invitation": app_state.invitation_manager is not None,
        "task_scheduler": app_state.task_scheduler is not None,
        "video_distributor": app_state.video_distributor is not None,
        "chat": app_state.chat_manager is not None,
        "commission": app_state.commission_calculator is not None,
        "data_sync": app_state.network_sync is not None,
        "industry_resource": app_state.industry_resource is not None,
        # v3.3.0
        "ecommerce_gateway": app_state.ecommerce_gateway is not None,
        # v3.2.2
        "predictive_memory": _predictive_memory_system is not None,
    }
    
    active = sum(1 for v in modules.values() if v)
    
    return {
        "status": "healthy",
        "version": __version__,
        "uptime_seconds": uptime,
        "modules": {k: "active" if v else "disabled" for k, v in modules.items()},
        "modules_active": f"{active}/{len(modules)}"
    }

@app.get("/api/v3/version")
async def version_info():
    return VERSION_INFO

@app.get("/api/v3/modules")
async def modules_status():
    """获取所有模块状态"""
    all_modules = {
        "v2.3.0_legacy": {
            "AI谈判引擎": AI_NEGOTIATION_AVAILABLE,
            "AIGC服务中心": AIGC_CENTER_AVAILABLE,
            "电商集成": ECOMMERCE_AVAILABLE,
            "人脸一致性": FACE_CONSISTENCY_AVAILABLE,
            "Notebook LM": NOTEBOOK_LM_AVAILABLE,
            "原创性检测": ORIGINALITY_AVAILABLE,
            "风控合规": RISK_COMPLIANCE_AVAILABLE,
        },
        "v2.6.0_core": {
            "自我进化大脑": app_state.evolution_controller is not None,
            "Memory V2": app_state.memory_integration is not None,
            "全局调度器": app_state.global_orchestrator is not None,
            "HyperHorse视频": app_state.hyperhorse_engine is not None,
        },
        "v3.0.0_business": {
            "全域商业大脑": app_state.business_brain is not None,
            "AI分身市场": app_state.avatar_market is not None,
            "AI分身定制市场": app_state.avatar_marketplace is not None,
            "达人外联引擎": app_state.influencer_engine is not None,
            "佣金计算": app_state.commission_calculator is not None,
            "行业资源导入": app_state.industry_resource is not None,
        },
        "v3.0.0_social": {
            "社交关系管理": app_state.social_manager is not None,
            "聊天系统": app_state.chat_manager is not None,
            "邀请裂变": app_state.invitation_manager is not None,
        },
        "v3.0.0_infra": {
            "安全系统": app_state.security_system is not None,
            "Kairos守护者": app_state.kairos_guardian is not None,
            "卧底审计员": app_state.undercover_auditor is not None,
            "健康监控": app_state.health_monitor is not None,
            "任务调度": app_state.task_scheduler is not None,
            "数据同步": app_state.network_sync is not None,
            "共享状态": app_state.shared_state is not None,
        },
        "v3.0.0_content": {
            "短视频分发": app_state.video_distributor is not None,
        }
    }
    
    total = sum(
        sum(1 for v in cat.values() if v)
        for cat in all_modules.values()
    )
    
    return {
        "modules": all_modules,
        "total_active": total,
        "version": __version__
    }

# ============================================================
# v3.2.2 预测性记忆系统API端点（解决502问题后集成）
# ============================================================

# 请求模型
class MemoryRememberRequest(BaseModel):
    """记忆经验请求"""
    event: str = Field(..., description="事件描述")
    outcome: str = Field(..., description="结果")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文")
    emotion: Dict[str, Any] = Field(default_factory=dict, description="情感")
    importance: float = Field(0.5, description="重要性(0-1)")
    tags: List[str] = Field(default_factory=list, description="标签")

class MemoryPredictRequest(BaseModel):
    """预测请求"""
    context: Dict[str, Any] = Field(..., description="预测上下文")
    prediction_type: str = Field("comprehensive", description="预测类型: comprehensive/causal/decision/emotional/social")
    horizon: int = Field(30, description="预测时间范围(天)")

@app.post("/api/memory/remember")
async def memory_remember(request: MemoryRememberRequest):
    """
    记忆经验
    
    主动决定是否值得记忆，并存储到相应的模式库
    """
    pams = get_predictive_memory_system()
    if not pams:
        raise HTTPException(status_code=503, detail="预测性记忆系统未可用")
    
    try:
        # 构造经验对象
        from datetime import datetime
        exp = {
            'event': request.event,
            'outcome': request.outcome,
            'context': request.context,
            'emotion': request.emotion,
            'importance': request.importance,
            'timestamp': datetime.now().isoformat(),
            'tags': request.tags
        }
        
        # 记忆经验
        success = pams.remember(exp)
        
        return {
            "success": success,
            "message": "经验已记忆" if success else "经验重要性不足，未记忆",
            "event": request.event[:100],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"记忆经验失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/predict")
async def memory_predict(request: MemoryPredictRequest):
    """
    预测
    
    基于记忆模式库进行综合预测
    """
    pams = get_predictive_memory_system()
    if not pams:
        raise HTTPException(status_code=503, detail="预测性记忆系统未可用")
    
    try:
        prediction = pams.predict(
            context=request.context,
            prediction_type=request.prediction_type,
            horizon=request.horizon
        )
        
        return {
            "success": True,
            "prediction_type": request.prediction_type,
            "prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/stats")
async def memory_stats():
    """
    获取预测性记忆系统统计信息
    """
    pams = get_predictive_memory_system()
    if not pams:
        raise HTTPException(status_code=503, detail="预测性记忆系统未可用")
    
    try:
        stats = pams.get_stats()
        return {
            "success": True,
            "stats": stats,
            "version": "3.2.2",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/health")
async def memory_health():
    """
    预测性记忆系统健康检查
    """
    pams = get_predictive_memory_system()
    return {
        "status": "healthy" if pams else "unavailable",
        "available": pams is not None,
        "system": "predictive_memory",
        "version": "3.2.2"
    }

# ============================================================
# v3.3.0 电商API端点 - 淘宝/拼多多/抖音
# ============================================================

@app.get("/api/ecommerce/status")
async def ecommerce_status():
    """获取电商平台配置状态"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    return {
        "success": True,
        "platforms": app_state.ecommerce_gateway.get_status()
    }

@app.post("/api/ecommerce/config")
async def update_ecommerce_config(request: EcommerceConfigRequest):
    """更新电商平台配置"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    success = app_state.ecommerce_gateway.update_config(
        platform=request.platform,
        config=request.config
    )
    
    if success:
        return {
            "success": True,
            "message": f"{request.platform} 配置已更新"
        }
    else:
        raise HTTPException(status_code=400, detail="配置更新失败")

@app.post("/api/ecommerce/search")
async def unified_search(request: UnifiedSearchRequest):
    """统一商品搜索（支持多平台）"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.search_products(
        platform=request.platform,
        keyword=request.keyword,
        page=request.page,
        page_size=request.page_size
    )
    
    return result

@app.get("/api/ecommerce/taobao/item")
async def taobao_item_detail(item_id: str):
    """获取淘宝商品详情"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.get_product_detail(
        platform="taobao",
        item_id=item_id
    )
    
    return result

@app.post("/api/ecommerce/taobao/search")
async def taobao_search(request: TaobaoSearchRequest):
    """淘宝商品搜索"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.taobao.search_items(
        keyword=request.keyword,
        page=request.page,
        page_size=request.page_size,
        sort=request.sort,
        is_tmall=request.is_tmall,
        is_overseas=request.is_overseas,
        start_price=request.start_price,
        end_price=request.end_price
    )
    
    return result

@app.post("/api/ecommerce/pdd/search")
async def pdd_search(request: PddSearchRequest):
    """拼多多商品搜索"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.pdd.pdd_ddk_goods_search(
        keyword=request.keyword,
        cat_id=request.cat_id,
        page=request.page,
        page_size=request.page_size,
        sort_type=request.sort_type,
        with_coupon=request.with_coupon
    )
    
    return result

@app.get("/api/ecommerce/douyin/products")
async def douyin_products(
    page: int = 1,
    size: int = 20,
    status: Optional[int] = None
):
    """抖音商品列表"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.douyin.product_list(
        page=page,
        size=size,
        status=status
    )
    
    return result

@app.get("/api/ecommerce/douyin/product/{product_id}")
async def douyin_product_detail(product_id: str):
    """抖音商品详情"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.get_product_detail(
        platform="douyin",
        item_id=product_id
    )
    
    return result

@app.post("/api/ecommerce/orders")
async def get_orders(request: OrderRequest):
    """统一订单查询（支持多平台）"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    from datetime import datetime as dt
    start_time = None
    end_time = None
    
    if request.start_time:
        start_time = dt.fromisoformat(request.start_time)
    if request.end_time:
        end_time = dt.fromisoformat(request.end_time)
    
    result = app_state.ecommerce_gateway.get_orders(
        platform=request.platform,
        start_time=start_time,
        end_time=end_time,
        status=request.status,
        page=request.page,
        page_size=request.page_size
    )
    
    return result

@app.get("/api/ecommerce/order/{platform}/{order_id}")
async def get_order_detail(platform: str, order_id: str):
    """获取订单详情"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.get_order_detail(
        platform=platform,
        order_id=order_id
    )
    
    return result

@app.post("/api/ecommerce/promotion-url")
async def generate_promotion_url(request: PromotionUrlRequest):
    """生成推广链接"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.generate_promotion_url(
        platform=request.platform,
        item_id=request.item_id,
        with_coupon=request.with_coupon
    )
    
    return result

@app.get("/api/ecommerce/oauth-url/{platform}")
async def get_oauth_url(platform: str, state: str = ""):
    """获取OAuth授权URL"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.get_oauth_url(
        platform=platform,
        state=state
    )
    
    return result

@app.get("/api/ecommerce/oauth/callback/{platform}")
async def handle_oauth_callback(platform: str, code: str):
    """处理OAuth回调"""
    if not ECOMMERCE_GATEWAY_AVAILABLE or not app_state.ecommerce_gateway:
        raise HTTPException(status_code=503, detail="电商网关未可用")
    
    result = app_state.ecommerce_gateway.handle_oauth_callback(
        platform=platform,
        code=code
    )
    
    return result

# ============================================================
# v3.0.0 API端点 - 全域商业大脑
# ============================================================

@app.post("/api/v3/business/insight")
async def generate_business_insight(request: BusinessInsightRequest):
    """生成商业洞察"""
    if not app_state.business_brain:
        raise HTTPException(status_code=503, detail="全域商业大脑未可用")
    
    insight = app_state.business_brain.generate_insight(
        insight_type=request.insight_type,
        context=request.context,
        data_sources=request.data_sources
    )
    
    return {
        "success": True,
        "insight": asdict(insight),
        "generated_at": datetime.now().isoformat()
    }

@app.post("/api/v3/business/market")
async def analyze_market(request: MarketAnalysisRequest):
    """市场分析"""
    if not app_state.business_brain:
        raise HTTPException(status_code=503, detail="全域商业大脑未可用")
    
    analysis = app_state.business_brain.analyze_market(
        market_name=request.market_name,
        data_sources=request.data_sources
    )
    
    return {
        "success": True,
        "analysis": asdict(analysis)
    }

@app.post("/api/v3/business/competitor")
async def analyze_competitor(request: CompetitorAnalysisRequest):
    """竞品分析"""
    if not app_state.business_brain:
        raise HTTPException(status_code=503, detail="全域商业大脑未可用")
    
    analysis = app_state.business_brain.analyze_competitor(
        competitor_name=request.competitor_name,
        data_sources=request.data_sources
    )
    
    return {
        "success": True,
        "analysis": asdict(analysis)
    }

@app.post("/api/v3/business/demand")
async def predict_demand(request: DemandPredictionRequest):
    """需求预测"""
    if not app_state.business_brain:
        raise HTTPException(status_code=503, detail="全域商业大脑未可用")
    
    prediction = app_state.business_brain.predict_demand(
        product_id=request.product_id,
        forecast_days=request.forecast_days
    )
    
    return {
        "success": True,
        "prediction": prediction
    }

# ============================================================
# v3.0.0 API端点 - AI分身市场
# ============================================================

@app.post("/api/v3/marketplace/listing")
async def create_listing(request: CreateListingRequest):
    """创建商品"""
    if not app_state.avatar_market:
        raise HTTPException(status_code=503, detail="AI分身市场未可用")
    
    listing = app_state.avatar_market.create_listing(
        seller_id="system",
        title=request.title,
        description=request.description,
        listing_type=request.listing_type,
        category=request.category,
        tags=request.tags,
        pricing_model=request.pricing_model,
        price=request.price,
        capabilities=request.capabilities
    )
    
    return {
        "success": True,
        "listing_id": listing.listing_id,
        "created_at": listing.created_at
    }

@app.post("/api/v3/marketplace/search")
async def search_listings(request: SearchListingRequest):
    """搜索商品"""
    if not app_state.avatar_market:
        raise HTTPException(status_code=503, detail="AI分身市场未可用")
    
    listings = app_state.avatar_market.search_listings(
        query=request.query,
        category=request.category,
        listing_type=request.listing_type,
        min_price=request.min_price,
        max_price=request.max_price,
        min_rating=request.min_rating,
        limit=request.limit
    )
    
    return {
        "success": True,
        "count": len(listings),
        "listings": [asdict(l) for l in listings]
    }

@app.get("/api/v3/marketplace/featured")
async def get_featured():
    """获取精选商品"""
    if not app_state.avatar_market:
        raise HTTPException(status_code=503, detail="AI分身市场未可用")
    
    listings = app_state.avatar_market.get_featured_listings()
    return {
        "success": True,
        "listings": [asdict(l) for l in listings]
    }

@app.post("/api/v3/marketplace/review")
async def create_review(request: CreateReviewRequest):
    """创建评价"""
    if not app_state.avatar_market:
        raise HTTPException(status_code=503, detail="AI分身市场未可用")
    
    review = app_state.avatar_market.create_review(
        listing_id=request.listing_id,
        buyer_id=request.buyer_id,
        rating=request.rating,
        title=request.title,
        content=request.content,
        pros=request.pros,
        cons=request.cons
    )
    
    return {
        "success": True,
        "review_id": review.review_id
    }

@app.get("/api/v3/marketplace/stats")
async def get_market_stats():
    """获取市场统计"""
    if not app_state.avatar_market:
        raise HTTPException(status_code=503, detail="AI分身市场未可用")
    
    return {
        "success": True,
        "stats": app_state.avatar_market.get_market_stats()
    }

# ============================================================
# v3.2.0 API端点 - AI分身定制市场服务
# ============================================================

@app.post("/api/v3/marketplace/custom/avatar")
async def create_custom_avatar(request: dict):
    """创建自定义AI分身"""
    if not app_state.avatar_marketplace:
        raise HTTPException(status_code=503, detail="AI分身定制市场未可用")
    
    try:
        avatar = app_state.avatar_marketplace.create_custom_avatar(
            user_id=request.get("user_id", "system"),
            name=request.get("name", "My Avatar"),
            category=request.get("category", "ecommerce"),
            skill_levels=request.get("skill_levels", {}),
            personality=request.get("personality", {}),
            use_cases=request.get("use_cases", [])
        )
        return {
            "success": True,
            "avatar_id": avatar.avatar_id,
            "status": avatar.status
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/v3/marketplace/templates")
async def get_templates(category: str = None, skill_level: str = None):
    """获取分身模板列表"""
    if not app_state.avatar_marketplace:
        raise HTTPException(status_code=503, detail="AI分身定制市场未可用")
    
    templates = app_state.avatar_marketplace.get_templates(
        category=category,
        skill_level=skill_level
    )
    return {
        "success": True,
        "count": len(templates),
        "templates": [t.to_dict() for t in templates]
    }

@app.get("/api/v3/marketplace/skills")
async def get_skills(category: str = None, level: str = None):
    """获取技能列表"""
    if not app_state.avatar_marketplace:
        raise HTTPException(status_code=503, detail="AI分身定制市场未可用")
    
    skills = app_state.avatar_marketplace.get_available_skills(
        category=category,
        level=level
    )
    return {
        "success": True,
        "count": len(skills),
        "skills": [s.to_dict() for s in skills]
    }

@app.get("/api/v3/marketplace/categories")
async def get_categories():
    """获取分身类别列表"""
    if not app_state.avatar_marketplace:
        raise HTTPException(status_code=503, detail="AI分身定制市场未可用")
    
    return {
        "success": True,
        "categories": [c.value for c in AvatarCategory]
    }

# ============================================================
# v3.0.0 API端点 - 达人外联引擎
# ============================================================

@app.post("/api/v3/influencer/add")
async def add_influencer(request: AddInfluencerRequest):
    """添加达人"""
    if not app_state.influencer_engine:
        raise HTTPException(status_code=503, detail="达人外联引擎未可用")
    
    influencer = app_state.influencer_engine.add_influencer(
        name=request.name,
        platform=request.platform,
        handle=request.handle,
        profile_url=request.profile_url,
        follower_count=request.follower_count,
        categories=request.categories,
        engagement_rate=request.engagement_rate
    )
    
    return {
        "success": True,
        "influencer_id": influencer.influencer_id
    }

@app.post("/api/v3/influencer/search")
async def search_influencers(request: SearchInfluencerRequest):
    """搜索达人"""
    if not app_state.influencer_engine:
        raise HTTPException(status_code=503, detail="达人外联引擎未可用")
    
    influencers = app_state.influencer_engine.search_influencers(
        platform=request.platform,
        categories=request.categories,
        min_followers=request.min_followers,
        max_followers=request.max_followers,
        min_engagement=request.min_engagement,
        limit=request.limit
    )
    
    return {
        "success": True,
        "count": len(influencers),
        "influencers": [asdict(i) for i in influencers]
    }

@app.post("/api/v3/influencer/campaign")
async def create_campaign(request: CreateCampaignRequest):
    """创建推广活动"""
    if not app_state.influencer_engine:
        raise HTTPException(status_code=503, detail="达人外联引擎未可用")
    
    campaign = app_state.influencer_engine.create_campaign(
        name=request.name,
        description=request.description,
        campaign_type=request.campaign_type,
        target_platforms=request.target_platforms,
        target_categories=request.target_categories,
        target_tiers=request.target_tiers,
        budget=request.budget,
        deadline=request.deadline,
        deliverables=request.deliverables,
        compensation=request.compensation
    )
    
    return {
        "success": True,
        "campaign_id": campaign.campaign_id
    }

@app.post("/api/v3/influencer/outreach")
async def initiate_outreach(request: InitiateOutreachRequest):
    """发起外联"""
    if not app_state.influencer_engine:
        raise HTTPException(status_code=503, detail="达人外联引擎未可用")
    
    outreach = app_state.influencer_engine.initiate_outreach(
        influencer_id=request.influencer_id,
        campaign_id=request.campaign_id,
        contact_method=request.contact_method,
        message_template=request.message_template
    )
    
    return {
        "success": True,
        "outreach_id": outreach.outreach_id,
        "status": outreach.status.value
    }

@app.get("/api/v3/influencer/stats")
async def get_outreach_stats():
    """获取外联统计"""
    if not app_state.influencer_engine:
        raise HTTPException(status_code=503, detail="达人外联引擎未可用")
    
    return {
        "success": True,
        "stats": app_state.influencer_engine.get_outreach_stats()
    }

# ============================================================
# v3.0.0 API端点 - 社交关系管理
# ============================================================

@app.post("/api/v3/social/user")
async def create_user(request: CreateUserRequest):
    """创建用户"""
    if not app_state.social_manager:
        raise HTTPException(status_code=503, detail="社交系统未可用")
    
    user = app_state.social_manager.create_user(
        username=request.username,
        display_name=request.display_name,
        email=request.email
    )
    
    return {
        "success": True,
        "user_id": user.user_id
    }

@app.post("/api/v3/social/relationship")
async def create_relationship(request: CreateRelationshipRequest):
    """创建关系"""
    if not app_state.social_manager:
        raise HTTPException(status_code=503, detail="社交系统未可用")
    
    rel = app_state.social_manager.create_relationship(
        from_user_id=request.from_user_id,
        to_user_id=request.to_user_id,
        relationship_type=request.relationship_type
    )
    
    return {
        "success": True,
        "relationship_id": rel.relationship_id
    }

@app.post("/api/v3/social/community")
async def create_community(request: CreateCommunityRequest):
    """创建社群"""
    if not app_state.social_manager:
        raise HTTPException(status_code=503, detail="社交系统未可用")
    
    community = app_state.social_manager.create_community(
        name=request.name,
        description=request.description,
        owner_id=request.owner_id
    )
    
    return {
        "success": True,
        "community_id": community.community_id
    }

@app.post("/api/v3/social/interaction")
async def record_interaction(request: RecordInteractionRequest):
    """记录互动"""
    if not app_state.social_manager:
        raise HTTPException(status_code=503, detail="社交系统未可用")
    
    interaction = app_state.social_manager.record_interaction(
        user_id=request.user_id,
        target_type=request.target_type,
        target_id=request.target_id,
        interaction_type=request.interaction_type,
        content=request.content
    )
    
    return {
        "success": True,
        "interaction_id": interaction.interaction_id
    }

@app.get("/api/v3/social/stats")
async def get_social_stats():
    """获取社交统计"""
    if not app_state.social_manager:
        raise HTTPException(status_code=503, detail="社交系统未可用")
    
    return {
        "success": True,
        "stats": app_state.social_manager.get_stats()
    }

# ============================================================
# v3.0.0 API端点 - 安全系统
# ============================================================

@app.post("/api/v3/security/apikey")
async def generate_api_key(request: GenerateApiKeyRequest):
    """生成API密钥"""
    if not app_state.security_system:
        raise HTTPException(status_code=503, detail="安全系统未可用")
    
    result = app_state.security_system.generate_api_key(
        name=request.name,
        permissions=request.permissions,
        expires_days=request.expires_days
    )
    
    return {
        "success": True,
        **result
    }

@app.post("/api/v3/security/block")
async def block_ip(request: BlockIpRequest):
    """封禁IP"""
    if not app_state.security_system:
        raise HTTPException(status_code=503, detail="安全系统未可用")
    
    app_state.security_system.block_ip(
        ip_address=request.ip_address,
        reason=request.reason,
        duration_hours=request.duration_hours
    )
    
    return {
        "success": True,
        "message": f"IP {request.ip_address} 已封禁"
    }

@app.get("/api/v3/security/events")
async def get_security_events(level: str = None):
    """获取安全事件"""
    if not app_state.security_system:
        raise HTTPException(status_code=503, detail="安全系统未可用")
    
    events = app_state.security_system.get_security_events(
        level=level if level else None
    )
    
    return {
        "success": True,
        "events": events
    }

@app.get("/api/v3/security/audit")
async def get_audit_logs(
    user_id: str = None,
    action: str = None,
    limit: int = 100
):
    """获取审计日志"""
    if not app_state.security_system:
        raise HTTPException(status_code=503, detail="安全系统未可用")
    
    logs = app_state.security_system.get_audit_logs(
        user_id=user_id,
        action=action,
        limit=limit
    )
    
    return {
        "success": True,
        "logs": logs
    }

# ============================================================
# v3.0.0 API端点 - 健康监控
# ============================================================

@app.post("/api/v3/health/check")
async def check_health(component: str = "all"):
    """健康检查"""
    if not app_state.health_monitor:
        raise HTTPException(status_code=503, detail="健康监控系统未可用")
    
    if component == "all":
        results = app_state.health_monitor.check_all()
        return {
            "success": True,
            "checks": {k: asdict(v) for k, v in results.items()}
        }
    else:
        check = app_state.health_monitor.check_component(component)
        return {
            "success": True,
            "check": asdict(check)
        }

@app.post("/api/v3/health/metric")
async def record_metric(request: RecordMetricRequest):
    """记录指标"""
    if not app_state.health_monitor:
        raise HTTPException(status_code=503, detail="健康监控系统未可用")
    
    metric = app_state.health_monitor.record_metric(
        name=request.name,
        value=request.value,
        unit=request.unit,
        tags=request.tags
    )
    
    return {
        "success": True,
        "metric_id": metric.metric_id
    }

@app.post("/api/v3/health/alert")
async def create_alert(request: CreateAlertRequest):
    """创建告警"""
    if not app_state.health_monitor:
        raise HTTPException(status_code=503, detail="健康监控系统未可用")
    
    alert = app_state.health_monitor.create_alert(
        level=request.level,
        title=request.title,
        message=request.message,
        component=request.component
    )
    
    return {
        "success": True,
        "alert_id": alert.alert_id
    }

@app.get("/api/v3/health/report")
async def get_health_report(period: str = "24h"):
    """获取健康报告"""
    if not app_state.health_monitor:
        raise HTTPException(status_code=503, detail="健康监控系统未可用")
    
    report = app_state.health_monitor.generate_report(period=period)
    return {
        "success": True,
        "report": report
    }

# ============================================================
# v3.0.0 API端点 - 邀请裂变
# ============================================================

@app.post("/api/v3/invitation/create")
async def create_invitation(request: CreateInvitationRequest):
    """创建邀请"""
    if not app_state.invitation_manager:
        raise HTTPException(status_code=503, detail="邀请裂变系统未可用")
    
    invitation = app_state.invitation_manager.create_invitation(
        inviter_id=request.inviter_id
    )
    
    return {
        "success": True,
        "invitation_id": invitation.invitation_id,
        "code": invitation.invitation_code
    }

@app.get("/api/v3/invitation/stats")
async def get_invitation_stats(inviter_id: str):
    """获取邀请统计"""
    if not app_state.invitation_manager:
        raise HTTPException(status_code=503, detail="邀请裂变系统未可用")
    
    stats = app_state.invitation_manager.get_inviter_stats(inviter_id)
    return {
        "success": True,
        "stats": stats
    }

@app.get("/api/v3/invitation/balance")
async def get_user_balance(user_id: str):
    """获取用户余额"""
    if not app_state.invitation_manager:
        raise HTTPException(status_code=503, detail="邀请裂变系统未可用")
    
    balance = app_state.invitation_manager.get_user_balance(user_id)
    return {
        "success": True,
        "balance": balance
    }

@app.post("/api/v3/invitation/campaign")
async def create_fission_campaign(request: CreateFissionCampaignRequest):
    """创建裂变活动"""
    if not app_state.invitation_manager:
        raise HTTPException(status_code=503, detail="邀请裂变系统未可用")
    
    campaign = app_state.invitation_manager.create_campaign(
        name=request.name,
        description=request.description,
        reward_rule_ids=request.reward_rule_ids,
        start_date=request.start_date,
        end_date=request.end_date,
        referral_limit=request.referral_limit
    )
    
    return {
        "success": True,
        "campaign_id": campaign.campaign_id
    }

# ============================================================
# v3.0.0 API端点 - 任务调度
# ============================================================

@app.post("/api/v3/task/create")
async def create_task(request: CreateTaskRequest):
    """创建任务"""
    if not app_state.task_scheduler:
        raise HTTPException(status_code=503, detail="任务调度系统未可用")
    
    task = app_state.task_scheduler.create_task(
        name=request.name,
        handler=request.handler,
        payload=request.payload,
        priority=request.priority,
        task_type=request.task_type,
        timeout=request.timeout
    )
    
    return {
        "success": True,
        "task_id": task.task_id,
        "status": task.status.value
    }

@app.get("/api/v3/task/{task_id}")
async def get_task(task_id: str):
    """获取任务"""
    if not app_state.task_scheduler:
        raise HTTPException(status_code=503, detail="任务调度系统未可用")
    
    task = app_state.task_scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "success": True,
        "task": asdict(task)
    }

@app.post("/api/v3/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    if not app_state.task_scheduler:
        raise HTTPException(status_code=503, detail="任务调度系统未可用")
    
    success = app_state.task_scheduler.cancel_task(task_id)
    return {
        "success": success,
        "message": "任务已取消" if success else "取消失败"
    }

@app.get("/api/v3/task/stats")
async def get_task_stats():
    """获取任务统计"""
    if not app_state.task_scheduler:
        raise HTTPException(status_code=503, detail="任务调度系统未可用")
    
    return {
        "success": True,
        "stats": app_state.task_scheduler.get_stats()
    }

# ============================================================
# v3.0.0 API端点 - 短视频分发
# ============================================================

@app.post("/api/v3/video/account")
async def connect_account(request: ConnectAccountRequest):
    """连接平台账号"""
    if not app_state.video_distributor:
        raise HTTPException(status_code=503, detail="短视频分发系统未可用")
    
    account = app_state.video_distributor.connect_account(
        platform=request.platform,
        username=request.username,
        access_token=request.access_token,
        display_name=request.display_name
    )
    
    return {
        "success": True,
        "account_id": account.account_id
    }

@app.post("/api/v3/video/content")
async def create_video_content(request: CreateContentRequest):
    """创建视频内容"""
    if not app_state.video_distributor:
        raise HTTPException(status_code=503, detail="短视频分发系统未可用")
    
    content = app_state.video_distributor.create_content(
        title=request.title,
        description=request.description,
        hashtags=request.hashtags,
        mentions=request.mentions,
        language=request.language
    )
    
    return {
        "success": True,
        "content_id": content.content_id
    }

@app.post("/api/v3/video/publish")
async def create_publish_task(request: CreatePublishTaskRequest):
    """创建发布任务"""
    if not app_state.video_distributor:
        raise HTTPException(status_code=503, detail="短视频分发系统未可用")
    
    task = app_state.video_distributor.create_publish_task(
        content_id=request.content_id,
        platform=request.platform,
        account_id=request.account_id,
        scheduled_time=request.scheduled_time
    )
    
    return {
        "success": True,
        "task_id": task.task_id,
        "status": task.status.value
    }

@app.get("/api/v3/video/stats")
async def get_video_stats():
    """获取分发统计"""
    if not app_state.video_distributor:
        raise HTTPException(status_code=503, detail="短视频分发系统未可用")
    
    return {
        "success": True,
        "stats": app_state.video_distributor.get_publish_stats()
    }

# ============================================================
# v3.0.0 API端点 - 聊天系统
# ============================================================

@app.post("/api/v3/chat/create")
async def create_chat(request: CreateChatRequest):
    """创建聊天"""
    if not app_state.chat_manager:
        raise HTTPException(status_code=503, detail="聊天系统未可用")
    
    chat = app_state.chat_manager.server.create_chat(
        name=request.name,
        chat_type=request.chat_type,
        created_by=request.created_by,
        members=request.members
    )
    
    return {
        "success": True,
        "chat_id": chat.chat_id
    }

@app.post("/api/v3/chat/message")
async def send_message(request: SendMessageRequest):
    """发送消息"""
    if not app_state.chat_manager:
        raise HTTPException(status_code=503, detail="聊天系统未可用")
    
    msg = app_state.chat_manager.server.send_message(
        chat_id=request.chat_id,
        sender_id=request.sender_id,
        message_type=request.message_type,
        content=request.content,
        metadata=request.metadata
    )
    
    # 存储到持久化记忆
    app_state.chat_manager.memory.store_message(
        chat_id=request.chat_id,
        sender_id=request.sender_id,
        content=request.content,
        metadata=request.metadata
    )
    
    return {
        "success": True,
        "message_id": msg.message_id
    }

@app.get("/api/v3/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: str, limit: int = 50):
    """获取聊天消息"""
    if not app_state.chat_manager:
        raise HTTPException(status_code=503, detail="聊天系统未可用")
    
    messages = app_state.chat_manager.server.get_chat_messages(
        chat_id=chat_id,
        limit=limit
    )
    
    return {
        "success": True,
        "messages": [asdict(m) for m in messages]
    }

@app.get("/api/v3/chat/{chat_id}/context")
async def get_conversation_context(chat_id: str, limit: int = 10):
    """获取对话上下文"""
    if not app_state.chat_manager:
        raise HTTPException(status_code=503, detail="聊天系统未可用")
    
    context = app_state.chat_manager.memory.get_conversation_context(
        chat_id=chat_id,
        limit=limit
    )
    
    return {
        "success": True,
        "context": context
    }

# ============================================================
# v3.0.0 API端点 - 佣金计算
# ============================================================

@app.post("/api/v3/commission/calculate")
async def calculate_commission(request: CalculateCommissionRequest):
    """计算佣金"""
    if not app_state.commission_calculator:
        raise HTTPException(status_code=503, detail="佣金计算系统未可用")
    
    record = app_state.commission_calculator.calculate_commission(
        user_id=request.user_id,
        source_user_id=request.source_user_id,
        order_id=request.order_id,
        amount=request.amount,
        level=request.level
    )
    
    if not record:
        return {
            "success": False,
            "message": "未找到适用的佣金规则"
        }
    
    return {
        "success": True,
        "record_id": record.record_id,
        "commission": record.commission,
        "rate": record.rate
    }

@app.get("/api/v3/commission/balance")
async def get_commission_balance(user_id: str):
    """获取佣金余额"""
    if not app_state.commission_calculator:
        raise HTTPException(status_code=503, detail="佣金计算系统未可用")
    
    balance = app_state.commission_calculator.get_user_balance(user_id)
    return {
        "success": True,
        "balance": balance
    }

@app.get("/api/v3/commission/history")
async def get_commission_history(user_id: str, status: str = None):
    """获取佣金历史"""
    if not app_state.commission_calculator:
        raise HTTPException(status_code=503, detail="佣金计算系统未可用")
    
    records = app_state.commission_calculator.get_user_commissions(
        user_id=user_id,
        status=status
    )
    
    return {
        "success": True,
        "records": [asdict(r) for r in records]
    }

# ============================================================
# v3.0.0 API端点 - 数据同步
# ============================================================

@app.post("/api/v3/sync/put")
async def put_sync_data(request: PutDataRequest):
    """写入同步数据"""
    if not app_state.network_sync:
        raise HTTPException(status_code=503, detail="数据同步系统未可用")
    
    record = app_state.network_sync.put(
        key=request.key,
        value=request.value,
        metadata=request.metadata
    )
    
    return {
        "success": True,
        "record_id": record.record_id
    }

@app.get("/api/v3/sync/get/{key}")
async def get_sync_data(key: str):
    """获取同步数据"""
    if not app_state.network_sync:
        raise HTTPException(status_code=503, detail="数据同步系统未可用")
    
    value = app_state.network_sync.get(key)
    return {
        "success": True,
        "key": key,
        "value": value
    }

@app.get("/api/v3/sync/state/{key}")
async def get_shared_state(key: str):
    """获取共享状态"""
    if not app_state.shared_state:
        raise HTTPException(status_code=503, detail="共享状态系统未可用")
    
    value = app_state.shared_state.get(key)
    return {
        "success": True,
        "key": key,
        "value": value
    }

@app.post("/api/v3/sync/state")
async def set_shared_state(request: SetStateRequest):
    """设置共享状态"""
    if not app_state.shared_state:
        raise HTTPException(status_code=503, detail="共享状态系统未可用")
    
    success = app_state.shared_state.set(
        key=request.key,
        value=request.value,
        locker_id=request.locker_id
    )
    
    return {
        "success": success
    }

# ============================================================
# v3.0.0 API端点 - 行业资源
# ============================================================

@app.post("/api/v3/resource/import")
async def import_resource(request: ImportResourceRequest):
    """导入资源"""
    if not app_state.industry_resource:
        raise HTTPException(status_code=503, detail="行业资源系统未可用")
    
    resource = app_state.industry_resource.import_resource(
        name=request.name,
        description=request.description,
        industry=request.industry,
        resource_type=request.resource_type,
        source=request.source,
        tags=request.tags
    )
    
    return {
        "success": True,
        "resource_id": resource.resource_id
    }

@app.get("/api/v3/resource/search")
async def search_resources(
    industry: str = None,
    resource_type: str = None,
    query: str = None
):
    """搜索资源"""
    if not app_state.industry_resource:
        raise HTTPException(status_code=503, detail="行业资源系统未可用")
    
    resources = app_state.industry_resource.search_resources(
        industry=industry,
        resource_type=resource_type,
        query=query
    )
    
    return {
        "success": True,
        "count": len(resources),
        "resources": [asdict(r) for r in resources]
    }

# ============================================================
# v2.6.0 保留API端点
# ============================================================

@app.post("/api/v2/evolution/review")
async def evolution_daily_review(request: EvolutionReviewRequest):
    """每日复盘"""
    if not app_state.evolution_controller:
        return {"success": False, "message": "自我进化大脑未可用"}
    
    result = app_state.evolution_controller.execute_daily_review(
        time_range=request.time_range,
        avatar_id=request.avatar_id,
        include_recommendations=request.include_recommendations
    )
    
    return {"success": True, "result": result}

@app.post("/api/v2/memory/manage")
async def memory_manage(request: MemoryManageRequest):
    """记忆管理"""
    if not app_state.memory_integration:
        return {"success": True, "message": "Memory V2未启用，使用基础功能"}
    
    result = app_state.memory_integration.manage_memory(
        action=request.action,
        memory_data=request.memory_data,
        memory_id=request.memory_id,
        query_params=request.query_params
    )
    
    return {"success": True, "result": result}

@app.post("/api/v2/orchestrator/task")
async def orchestrator_submit_task(request: OrchestrateTaskRequest):
    """全局编排任务"""
    if not app_state.global_orchestrator:
        raise HTTPException(status_code=503, detail="全局调度器未可用")
    
    task_id = app_state.global_orchestrator.submit_task(
        task_type=request.task_type,
        priority=request.priority,
        payload=request.payload
    )
    
    return {"success": True, "task_id": task_id}

@app.post("/api/v2/hyperhorse/video")
async def hyperhorse_video(request: HyperHorseVideoRequest):
    """HyperHorse视频生成"""
    if not app_state.hyperhorse_engine:
        raise HTTPException(status_code=503, detail="HyperHorse视频引擎未可用")
    
    result = app_state.hyperhorse_engine.generate_video_script(
        product_info=request.product_info,
        target_platform=request.target_platform,
        target_language=request.target_language,
        quality_level=request.quality_level
    )
    
    return {"success": True, "result": asdict(result)}

# ============================================================
# v2.3.0 保留API端点
# ============================================================

@app.post("/api/v2/negotiation/ai-engine")
async def ai_negotiation_engine(request: NegotiationRequest):
    """AI谈判引擎"""
    if not AI_NEGOTIATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI谈判引擎未可用")
    
    return {
        "success": True,
        "negotiation_id": request.negotiation_id,
        "action": request.action,
        "result": {"message": "AI谈判功能可用"}
    }

@app.post("/api/v2/aigc/generate")
async def aigc_service_center(request: AIGCGenerateRequest):
    """AIGC服务中心"""
    if not AIGC_CENTER_AVAILABLE:
        raise HTTPException(status_code=503, detail="AIGC服务中心未可用")
    
    return {
        "success": True,
        "content_id": f"aigc_{uuid.uuid4().hex[:8]}",
        "content_type": request.content_type,
        "status": "completed"
    }

# ============================================================
# v3.2.1 百炼图片生成API端点
# ============================================================

@app.get("/api/v2/bailian/status")
async def bailian_status():
    """百炼图片服务状态"""
    return {
        "available": BAILIAN_AVAILABLE,
        "service": "bailian_image",
        "version": "1.0.0",
        "features": [
            "text2image",
            "image2image", 
            "virtual_model",
            "ai_tryon",
            "poster",
            "background"
        ] if BAILIAN_AVAILABLE else []
    }

@app.post("/api/v2/bailian/text2image")
async def bailian_text2image(request: BailianText2ImageRequest):
    """百炼文生图"""
    if not BAILIAN_AVAILABLE:
        raise HTTPException(status_code=503, detail="百炼图片生成服务未可用")
    
    adapter = get_bailian_adapter()
    if not adapter:
        raise HTTPException(status_code=503, detail="百炼适配器初始化失败")
    
    try:
        result = await adapter.generate_text2image(
            prompt=request.prompt,
            style=request.style,
            model=request.model,
            width=request.width,
            height=request.height,
            n=request.n
        )
        return {
            "success": True,
            "task_id": result.task_id,
            "status": result.status.value,
            "images": result.images if result.status.value == "SUCCEEDED" else [],
            "message": result.message
        }
    except Exception as e:
        logger.error(f"百炼文生图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/bailian/image2image")
async def bailian_image2image(request: BailianImage2ImageRequest):
    """百炼图生图"""
    if not BAILIAN_AVAILABLE:
        raise HTTPException(status_code=503, detail="百炼图片生成服务未可用")
    
    adapter = get_bailian_adapter()
    if not adapter:
        raise HTTPException(status_code=503, detail="百炼适配器初始化失败")
    
    try:
        result = await adapter.generate_image2image(
            prompt=request.prompt,
            input_image_url=request.image_url,
            style=request.style,
            strength=request.strength
        )
        return {
            "success": True,
            "task_id": result.task_id,
            "status": result.status.value,
            "images": result.images if result.status.value == "SUCCEEDED" else [],
            "message": result.message
        }
    except Exception as e:
        logger.error(f"百炼图生图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/bailian/virtual-model")
async def bailian_virtual_model(request: BailianVirtualModelRequest):
    """百炼虚拟模特（人台图转真人）"""
    if not BAILIAN_AVAILABLE:
        raise HTTPException(status_code=503, detail="百炼图片生成服务未可用")
    
    adapter = get_bailian_adapter()
    if not adapter:
        raise HTTPException(status_code=503, detail="百炼适配器初始化失败")
    
    try:
        result = await adapter.generate_virtual_model(
            product_image_url=request.product_image_url,
            model_type=request.model_type
        )
        return {
            "success": True,
            "task_id": result.task_id,
            "status": result.status.value,
            "images": result.images if result.status.value == "SUCCEEDED" else [],
            "message": result.message
        }
    except Exception as e:
        logger.error(f"百炼虚拟模特失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/bailian/background")
async def bailian_background(request: BailianBackgroundRequest):
    """百炼背景生成"""
    if not BAILIAN_AVAILABLE:
        raise HTTPException(status_code=503, detail="百炼图片生成服务未可用")
    
    adapter = get_bailian_adapter()
    if not adapter:
        raise HTTPException(status_code=503, detail="百炼适配器初始化失败")
    
    try:
        result = await adapter.generate_background(
            product_image_url=request.product_image_url,
            background_prompt=request.background_prompt
        )
        return {
            "success": True,
            "task_id": result.task_id,
            "status": result.status.value,
            "images": result.images if result.status.value == "SUCCEEDED" else [],
            "message": result.message
        }
    except Exception as e:
        logger.error(f"百炼背景生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# v3.4.0 WebSocket测试与状态端点
# ============================================================

@app.get("/api/ws/status")
async def get_websocket_status():
    """获取WebSocket连接状态"""
    return {
        "success": True,
        "active_connections": len(ws_manager.active_connections),
        "websocket_enabled": True
    }


@app.post("/api/ws/test")
async def test_websocket_broadcast():
    """测试WebSocket广播（用于调试）"""
    await broadcast_to_websockets({
        "type": "notification",
        "data": {
            "title": "WebSocket测试",
            "message": "这是一条测试消息，用于验证WebSocket功能是否正常",
            "level": "info"
        }
    })
    return {
        "success": True,
        "message": "测试消息已广播"
    }


@app.post("/api/ws/broadcast")
async def broadcast_message(message_type: str, content: str):
    """
    手动广播消息
    
    参数:
        message_type: 消息类型 (opportunities_update, avatars_update, tasks_update, notification)
        content: 消息内容
    """
    await broadcast_to_websockets({
        "type": message_type,
        "data": {"message": content}
    })
    return {
        "success": True,
        "message": f"已广播 {message_type} 类型消息"
    }

@app.get("/")
@app.get("/office")
async def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    print("启动 Uvicorn...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
