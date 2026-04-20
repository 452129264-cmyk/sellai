#!/usr/bin/env python3
"""
SellAI 语音系统模块

提供完整的语音交互功能，包括：
- 语音唤醒系统
- 语音识别服务  
- 语音合成服务
- 语音对话引擎
- 语音集成管理器
"""

# 尝试导入各个模块，如果依赖缺失则优雅降级
try:
    from .voice_wakeup_system import VoiceWakeupSystem, WakeupState, WakeupResult
    HAS_WAKEUP_SYSTEM = True
except ImportError as e:
    HAS_WAKEUP_SYSTEM = False
    print(f"语音唤醒系统导入失败: {e}")

try:
    from .voice_recognition_service import WhisperRecognitionService, create_whisper_service
    HAS_WHISPER_SERVICE = True
except ImportError as e:
    HAS_WHISPER_SERVICE = False
    print(f"语音识别服务导入失败: {e}")

try:
    from .voice_synthesis_service import AzureTTSService, create_azure_tts_service, VoiceStyle
    HAS_AZURE_TTS_SERVICE = True
except ImportError as e:
    HAS_AZURE_TTS_SERVICE = False
    print(f"语音合成服务导入失败: {e}")

try:
    from .voice_conversation_engine import VoiceConversationEngine, ConversationState
    HAS_CONVERSATION_ENGINE = True
except ImportError as e:
    HAS_CONVERSATION_ENGINE = False
    print(f"语音对话引擎导入失败: {e}")

try:
    from .voice_integration_manager import VoiceIntegrationManager
    HAS_VOICE_MANAGER = True
except ImportError as e:
    HAS_VOICE_MANAGER = False
    print(f"语音集成管理器导入失败: {e}")

# 模块信息
__version__ = "1.0.0"
__all__ = [
    "VoiceWakeupSystem",
    "WakeupState", 
    "WakeupResult",
    "WhisperRecognitionService",
    "create_whisper_service",
    "AzureTTSService",
    "create_azure_tts_service",
    "VoiceStyle",
    "VoiceConversationEngine",
    "ConversationState",
    "VoiceIntegrationManager",
    "HAS_WAKEUP_SYSTEM",
    "HAS_WHISPER_SERVICE",
    "HAS_AZURE_TTS_SERVICE",
    "HAS_CONVERSATION_ENGINE",
    "HAS_VOICE_MANAGER"
]
