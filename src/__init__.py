#!/usr/bin/env python3
"""
SellAI v3.0.0 - Source Package
整合所有核心模块
"""

# v2.3.0-2.5.0 核心模块
from .ai_negotiation_engine import AINegotiationEngine
from .aigc_service_center import AIGCServiceCenter

# v2.6.0 核心模块
from .self_evolution_brain import SelfEvolutionBrainController
from .global_orchestrator import CoreScheduler
from .hyperhorse import HyperHorseEngine

# Memory V2
from .memory_v2_validator import MemoryV2Validator
from .memory_v2_indexer import MemoryV2Indexer
from .memory_v2_integration import MemoryV2IntegrationManager

# v3.0.0 新增模块
from .global_business_brain import GlobalBusinessBrain
from .avatar_market import AvatarMarket
from .influencer_outreach_engine import InfluencerOutreachEngine
from .social_relationship_manager import SocialRelationshipManager
from .multi_layer_security import MultiLayerSecurity, KairosGuardian, UndercoverAuditor
from .health_monitor import HealthMonitor
from .invitation_fission_manager import InvitationFissionManager
from .task_scheduler import TaskScheduler, TaskDispatcher
from .short_video_distributor import ShortVideoDistributor
from .chat_system import ChatServer, ChatManager, ChatPermanentMemory
from .industry_resource_importer import IndustryResourceImporter
from .commission_calculator import CommissionCalculator
from .network_data_sync import NetworkDataSync, SharedStateManager

__version__ = "3.0.0"
__all__ = [
    # v2.3.0-2.5.0
    "AINegotiationEngine",
    "AIGCServiceCenter",
    # v2.6.0
    "SelfEvolutionBrainController",
    "CoreScheduler",
    "HyperHorseEngine",
    "MemoryV2Validator",
    "MemoryV2Indexer",
    "MemoryV2IntegrationManager",
    # v3.0.0
    "GlobalBusinessBrain",
    "AvatarMarket",
    "InfluencerOutreachEngine",
    "SocialRelationshipManager",
    "MultiLayerSecurity",
    "KairosGuardian",
    "UndercoverAuditor",
    "HealthMonitor",
    "InvitationFissionManager",
    "TaskScheduler",
    "TaskDispatcher",
    "ShortVideoDistributor",
    "ChatServer",
    "ChatManager",
    "ChatPermanentMemory",
    "IndustryResourceImporter",
    "CommissionCalculator",
    "NetworkDataSync",
    "SharedStateManager",
]
