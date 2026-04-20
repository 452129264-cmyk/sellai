#!/usr/bin/env python3
"""
语音集成管理器

此模块负责将语音唤醒与交互功能深度集成到SellAI全域系统中，
实现语音功能与无限分身架构、Claude Code架构、Notebook LM知识底座、
办公室界面的无缝对接。

核心功能：
1. 语音系统与分身系统的双向绑定
2. 办公室界面的语音交互集成
3. 全局状态同步与管理
4. 性能监控与故障恢复
5. 强制同步到测试环境
"""

import os
import sys
import json
import time
import logging
import threading
import queue
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from enum import Enum

# 导入语音系统模块
try:
    from src.voice_wakeup_system import VoiceWakeupSystem, WakeupResult, WakeupState
    HAS_WAKEUP_SYSTEM = True
except ImportError:
    HAS_WAKEUP_SYSTEM = False

try:
    from src.voice_conversation_engine import VoiceConversationEngine, ConversationState
    HAS_CONVERSATION_ENGINE = True
except ImportError:
    HAS_CONVERSATION_ENGINE = False

# 导入现有系统模块
try:
    from src.social_relationship_manager import SocialRelationshipManager
    from src.chat_manager import ChatManager
    from src.shared_state_manager import SharedStateManager
    HAS_AVATAR_SYSTEM = True
except ImportError:
    HAS_AVATAR_SYSTEM = False
    # 模拟接口
    class SocialRelationshipManager:
        def get_active_avatars(self):
            return ["情报官", "内容官", "运营官", "增长官"]
    
    class ChatManager:
        def send_message(self, avatar_name, message):
            print(f"[模拟] {avatar_name} 收到消息: {message}")
            return {"response": f"这是 {avatar_name} 的模拟回复", "timestamp": time.time()}
    
    class SharedStateManager:
        def __init__(self):
            self.state = {}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationState(Enum):
    """集成状态"""
    INITIALIZING = "initializing"    # 初始化中
    IDLE = "idle"                    # 空闲待机
    ACTIVE = "active"                # 激活运行
    ERROR = "error"                  # 错误状态
    STOPPED = "stopped"              # 已停止


class VoiceIntegrationManager:
    """语音集成管理器主类"""
    
    def __init__(
        self,
        db_path: str = "data/shared_state/state.db",
        wakeup_phrase: str = "sell sell 在吗",
        default_avatar: str = "情报官",
        office_interface_url: Optional[str] = None,
        sync_to_test: bool = True,
        test_target_dir: str = "/app/data/files/sellai_test"
    ):
        """
        初始化语音集成管理器
        
        Args:
            db_path: 共享状态数据库路径
            wakeup_phrase: 唤醒词短语
            default_avatar: 默认对话分身
            office_interface_url: 办公室界面URL（可选）
            sync_to_test: 是否同步到测试环境
            test_target_dir: 测试环境目标目录
        """
        self.db_path = db_path
        self.wakeup_phrase = wakeup_phrase
        self.default_avatar = default_avatar
        self.office_interface_url = office_interface_url
        self.sync_to_test = sync_to_test
        self.test_target_dir = test_target_dir
        
        # 状态管理
        self.state = IntegrationState.INITIALIZING
        self.state_lock = threading.Lock()
        self.last_activity_time = time.time()
        
        # 初始化现有系统组件
        self.avatar_manager = None
        self.chat_manager = None
        self.shared_state_manager = None
        
        self._initialize_existing_systems()
        
        # 初始化语音系统组件
        self.wakeup_system = None
        self.conversation_engine = None
        
        self._initialize_voice_systems()
        
        # 集成状态跟踪
        self.integrated_avatars = []
        self.voice_enabled_avatars = {}
        self.voice_activity_log = []
        
        # 配置管理
        self.config = {
            "wakeup_enabled": True,
            "auto_listen_after_wakeup": True,
            "max_conversation_duration_seconds": 300,
            "enable_voice_logging": True,
            "speech_recognition_timeout_seconds": 10,
            "tts_voice": "zh-CN-XiaoxiaoNeural",
            "sample_rate": 16000,
            "chunk_size": 1024
        }
        
        # 回调函数注册
        self.integration_callbacks = {
            "on_wakeup": [],
            "on_conversation_start": [],
            "on_conversation_end": [],
            "on_error": [],
            "on_state_change": []
        }
        
        # 统计信息
        self.stats = {
            "total_wakeups": 0,
            "total_conversations": 0,
            "total_voice_commands": 0,
            "avg_wakeup_response_ms": 0.0,
            "avg_conversation_duration_ms": 0.0,
            "success_rate": 1.0,
            "system_uptime_seconds": 0.0,
            "last_error": None,
            "start_time": time.time()
        }
        
        # 运行标志
        self.running = False
        self.processing_thread = None
        
        # 办公室界面集成
        self.office_connected = False
        self.voice_interface_ready = False
        
        logger.info("语音集成管理器初始化完成")
    
    def _initialize_existing_systems(self):
        """初始化现有系统组件"""
        try:
            if HAS_AVATAR_SYSTEM:
                self.avatar_manager = SocialRelationshipManager(self.db_path)
                self.chat_manager = ChatManager()
                self.shared_state_manager = SharedStateManager(self.db_path)
                logger.info("现有系统组件初始化成功")
            else:
                logger.warning("现有系统组件不可用，使用模拟接口")
                self.avatar_manager = SocialRelationshipManager()
                self.chat_manager = ChatManager()
                self.shared_state_manager = SharedStateManager()
        except Exception as e:
            logger.error(f"初始化现有系统组件失败: {e}")
            raise
    
    def _initialize_voice_systems(self):
        """初始化语音系统组件"""
        try:
            # 初始化语音唤醒系统
            if HAS_WAKEUP_SYSTEM:
                self.wakeup_system = VoiceWakeupSystem(
                    wakeup_phrase=self.wakeup_phrase,
                    whisper_model_size="tiny",
                    sample_rate=self.config["sample_rate"],
                    chunk_size=self.config["chunk_size"]
                )
                
                # 注册唤醒回调
                self.wakeup_system.register_wakeup_callback(self._handle_wakeup_event)
                self.wakeup_system.register_state_change_callback(self._handle_wakeup_state_change)
                
                logger.info("语音唤醒系统初始化成功")
            
            # 初始化语音对话引擎
            if HAS_CONVERSATION_ENGINE:
                self.conversation_engine = VoiceConversationEngine(
                    default_avatar=self.default_avatar,
                    wakeup_phrase=self.wakeup_phrase,
                    whisper_model_size="base",
                    azure_tts_key=None,  # 实际部署时需要配置
                    azure_tts_region=None,
                    sample_rate=self.config["sample_rate"]
                )
                
                # 注册引擎回调
                self.conversation_engine.register_state_change_callback(self._handle_engine_state_change)
                self.conversation_engine.register_response_ready_callback(self._handle_engine_response)
                
                logger.info("语音对话引擎初始化成功")
                
        except Exception as e:
            logger.error(f"初始化语音系统组件失败: {e}")
            raise
    
    def start(self):
        """启动集成管理器"""
        if self.running:
            logger.warning("集成管理器已经在运行中")
            return
        
        logger.info("启动语音集成管理器...")
        
        # 设置为激活状态
        self._set_state(IntegrationState.ACTIVE)
        self.running = True
        
        # 启动语音唤醒系统
        if self.wakeup_system:
            try:
                self.wakeup_system.start()
                logger.info("语音唤醒系统已启动")
            except Exception as e:
                logger.error(f"启动语音唤醒系统失败: {e}")
                self._set_state(IntegrationState.ERROR)
                return False
        
        # 启动语音对话引擎
        if self.conversation_engine:
            try:
                self.conversation_engine.start()
                logger.info("语音对话引擎已启动")
            except Exception as e:
                logger.error(f"启动语音对话引擎失败: {e}")
                self._set_state(IntegrationState.ERROR)
                return False
        
        # 绑定所有活跃分身
        self._bind_all_active_avatars()
        
        # 启动处理线程
        self.processing_thread = threading.Thread(
            target=self._integration_processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        
        # 同步到测试环境
        if self.sync_to_test:
            self._sync_to_test_environment()
        
        logger.info("语音集成管理器启动成功")
        return True
    
    def stop(self):
        """停止集成管理器"""
        if not self.running:
            return
        
        logger.info("停止语音集成管理器...")
        
        self.running = False
        
        # 停止语音系统
        if self.wakeup_system:
            self.wakeup_system.stop()
        
        if self.conversation_engine:
            self.conversation_engine.stop()
        
        # 等待处理线程结束
        if self.processing_thread:
            self.processing_thread.join(timeout=3.0)
        
        self._set_state(IntegrationState.STOPPED)
        logger.info("语音集成管理器已停止")
    
    def _bind_all_active_avatars(self):
        """绑定所有活跃分身到语音系统"""
        try:
            if not self.avatar_manager:
                return
            
            # 获取活跃分身列表
            active_avatars = self.avatar_manager.get_active_avatars()
            
            for avatar_name in active_avatars:
                self._bind_avatar(avatar_name)
            
            logger.info(f"已绑定 {len(active_avatars)} 个活跃分身到语音系统")
            
        except Exception as e:
            logger.error(f"绑定分身失败: {e}")
    
    def _bind_avatar(self, avatar_name: str):
        """绑定单个分身到语音系统"""
        try:
            # 记录绑定信息
            self.voice_enabled_avatars[avatar_name] = {
                "bound_at": time.time(),
                "last_voice_activity": None,
                "voice_command_count": 0,
                "status": "enabled"
            }
            
            self.integrated_avatars.append(avatar_name)
            
            logger.debug(f"分身 {avatar_name} 已绑定到语音系统")
            return True
            
        except Exception as e:
            logger.error(f"绑定分身 {avatar_name} 失败: {e}")
            return False
    
    def _integration_processing_loop(self):
        """集成处理循环"""
        logger.info("集成处理线程启动")
        
        while self.running:
            try:
                # 定期状态检查和维护
                self._periodic_maintenance()
                
                # 更新统计信息
                self._update_stats()
                
                # 记录活动日志
                if self.config["enable_voice_logging"]:
                    self._log_activity()
                
                # 睡眠以避免过高CPU使用
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"集成处理循环发生错误: {e}")
                self._notify_error(f"处理循环错误: {str(e)}")
                time.sleep(5.0)
    
    def _periodic_maintenance(self):
        """定期维护任务"""
        try:
            # 检查系统健康状态
            self._check_system_health()
            
            # 清理旧日志
            self._cleanup_old_logs()
            
            # 更新性能统计
            self._update_performance_stats()
            
        except Exception as e:
            logger.warning(f"定期维护任务失败: {e}")
    
    def _check_system_health(self):
        """检查系统健康状态"""
        # 检查语音唤醒系统
        if self.wakeup_system:
            try:
                wakeup_status = self.wakeup_system.get_system_status()
                if wakeup_status.get("state") == "error":
                    logger.warning("语音唤醒系统报告错误状态")
                    self._notify_error(f"语音唤醒系统错误: {wakeup_status}")
            except Exception as e:
                logger.warning(f"检查语音唤醒系统健康状态失败: {e}")
        
        # 检查语音对话引擎
        if self.conversation_engine:
            try:
                engine_status = self.conversation_engine.get_engine_status()
                if engine_status.get("state") == "error":
                    logger.warning("语音对话引擎报告错误状态")
                    self._notify_error(f"语音对话引擎错误: {engine_status}")
            except Exception as e:
                logger.warning(f"检查语音对话引擎健康状态失败: {e}")
    
    def _cleanup_old_logs(self):
        """清理旧的语音活动日志"""
        try:
            # 保留最近1000条日志
            max_logs = 1000
            if len(self.voice_activity_log) > max_logs:
                self.voice_activity_log = self.voice_activity_log[-max_logs:]
                
        except Exception as e:
            logger.warning(f"清理日志失败: {e}")
    
    def _update_performance_stats(self):
        """更新性能统计信息"""
        try:
            # 更新系统运行时间
            self.stats["system_uptime_seconds"] = time.time() - self.stats["start_time"]
            
        except Exception as e:
            logger.warning(f"更新性能统计失败: {e}")
    
    def _update_stats(self):
        """更新统计信息"""
        # 这里可以添加更多统计更新逻辑
        pass
    
    def _log_activity(self):
        """记录活动日志"""
        try:
            log_entry = {
                "timestamp": time.time(),
                "datetime": datetime.now().isoformat(),
                "state": self.state.value,
                "integrated_avatars_count": len(self.integrated_avatars),
                "stats": self.stats.copy()
            }
            
            self.voice_activity_log.append(log_entry)
            
            # 定期写入文件
            if len(self.voice_activity_log) % 10 == 0:
                self._save_activity_log()
                
        except Exception as e:
            logger.warning(f"记录活动日志失败: {e}")
    
    def _save_activity_log(self):
        """保存活动日志到文件"""
        try:
            log_dir = "logs/voice_integration"
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
            
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump({
                    "system": "语音集成管理器",
                    "timestamp": time.time(),
                    "log_entries": self.voice_activity_log[-100:]  # 保存最近100条
                }, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.warning(f"保存活动日志失败: {e}")
    
    def _handle_wakeup_event(self, result: WakeupResult):
        """处理唤醒事件"""
        logger.info(f"唤醒事件: {result}")
        
        # 更新统计
        self.stats["total_wakeups"] += 1
        
        # 计算平均响应时间
        total_wakeups = self.stats["total_wakeups"]
        current_avg = self.stats["avg_wakeup_response_ms"]
        response_time = result.processing_time_ms
        
        if total_wakeups == 1:
            self.stats["avg_wakeup_response_ms"] = response_time
        else:
            # 指数移动平均
            alpha = 0.1
            self.stats["avg_wakeup_response_ms"] = current_avg * (1 - alpha) + response_time * alpha
        
        # 通知回调
        self._notify_wakeup(result)
        
        # 如果是唤醒成功，激活对话引擎
        if result.is_wakeup and self.conversation_engine:
            # 切换到激活状态
            self.conversation_engine._set_state(ConversationState.LISTENING)
    
    def _handle_wakeup_state_change(self, state: WakeupState):
        """处理唤醒系统状态变更"""
        logger.debug(f"唤醒系统状态变更: {state.value}")
        
        # 更新最后活动时间
        self.last_activity_time = time.time()
    
    def _handle_engine_state_change(self, state: ConversationState):
        """处理对话引擎状态变更"""
        logger.debug(f"对话引擎状态变更: {state.value}")
        
        # 更新集成管理器状态
        if state == ConversationState.IDLE:
            self._set_state(IntegrationState.IDLE)
        elif state == ConversationState.LISTENING or state == ConversationState.PROCESSING:
            self._set_state(IntegrationState.ACTIVE)
        elif state == ConversationState.ERROR:
            self._set_state(IntegrationState.ERROR)
            self._notify_error(f"对话引擎进入错误状态: {state.value}")
    
    def _handle_engine_response(self, text: str, audio_file: Optional[str] = None):
        """处理对话引擎响应"""
        logger.info(f"对话引擎响应: '{text[:50]}...'")
        
        # 更新统计
        self.stats["total_conversations"] += 1
        
        # 记录活动
        activity_entry = {
            "type": "ai_response",
            "timestamp": time.time(),
            "text": text,
            "audio_file": audio_file,
            "current_avatar": self.conversation_engine.current_avatar if self.conversation_engine else None
        }
        
        self.voice_activity_log.append(activity_entry)
        
        # 通知回调
        for callback in self.integration_callbacks["on_conversation_end"]:
            try:
                callback(text, audio_file)
            except Exception as e:
                logger.error(f"对话结束回调函数执行失败: {e}")
    
    def _set_state(self, state: IntegrationState):
        """设置集成状态"""
        with self.state_lock:
            old_state = self.state
            self.state = state
            
            if old_state != state:
                logger.info(f"集成状态变更: {old_state.value} -> {state.value}")
                self._notify_state_change(state)
                
                # 记录状态变更
                activity_entry = {
                    "type": "state_change",
                    "timestamp": time.time(),
                    "old_state": old_state.value,
                    "new_state": state.value
                }
                
                self.voice_activity_log.append(activity_entry)
    
    def _sync_to_test_environment(self):
        """同步到测试环境"""
        if not self.sync_to_test:
            return
        
        logger.info(f"同步语音功能到测试环境: {self.test_target_dir}")
        
        try:
            # 确保目标目录存在
            os.makedirs(self.test_target_dir, exist_ok=True)
            
            # 语音系统核心文件列表
            voice_files = [
                "src/voice_wakeup_system.py",
                "src/voice_conversation_engine.py",
                "src/voice_integration_manager.py",
                "src/voice_recognition_service.py",
                "src/voice_synthesis_service.py",
                "src/real_time_audio_stream.py"
            ]
            
            # 同步每个文件
            synced_files = []
            for file_path in voice_files:
                src_path = os.path.join("/app/data/files", file_path)
                if os.path.exists(src_path):
                    # 创建目标目录结构
                    rel_path = os.path.relpath(file_path, "src")
                    dst_path = os.path.join(self.test_target_dir, rel_path)
                    dst_dir = os.path.dirname(dst_path)
                    os.makedirs(dst_dir, exist_ok=True)
                    
                    # 复制文件
                    with open(src_path, "r", encoding="utf-8") as src_file:
                        content = src_file.read()
                    
                    with open(dst_path, "w", encoding="utf-8") as dst_file:
                        dst_file.write(content)
                    
                    synced_files.append(rel_path)
                    logger.debug(f"已同步: {file_path} -> {dst_path}")
                else:
                    logger.warning(f"源文件不存在: {file_path}")
            
            # 生成同步报告
            sync_report = {
                "sync_time": time.time(),
                "sync_timestamp": datetime.now().isoformat(),
                "source_system": "SellAI全域语音系统",
                "target_directory": self.test_target_dir,
                "synced_files": synced_files,
                "total_files_synced": len(synced_files),
                "status": "completed" if synced_files else "failed",
                "voice_systems": {
                    "wakeup_system": self.wakeup_system is not None,
                    "conversation_engine": self.conversation_engine is not None,
                    "recognition_service": HAS_WAKEUP_SYSTEM,
                    "synthesis_service": HAS_CONVERSATION_ENGINE,
                    "integration_manager": True
                }
            }
            
            # 保存同步报告
            report_file = os.path.join(self.test_target_dir, "sync_report.json")
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(sync_report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"同步完成，报告已保存到: {report_file}")
            logger.info(f"同步了 {len(synced_files)} 个文件")
            
            # 通知回调
            for callback in self.integration_callbacks.get("on_sync_complete", []):
                try:
                    callback(sync_report)
                except Exception as e:
                    logger.error(f"同步完成回调函数执行失败: {e}")
        
        except Exception as e:
            logger.error(f"同步到测试环境失败: {e}")
            self._notify_error(f"同步失败: {str(e)}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """注册回调函数"""
        if event_type in self.integration_callbacks:
            self.integration_callbacks[event_type].append(callback)
            logger.debug(f"注册回调函数: {event_type}, 当前数量: {len(self.integration_callbacks[event_type])}")
        else:
            logger.warning(f"未知的事件类型: {event_type}")
    
    def _notify_wakeup(self, result: WakeupResult):
        """通知唤醒事件"""
        for callback in self.integration_callbacks["on_wakeup"]:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"唤醒回调函数执行失败: {e}")
    
    def _notify_state_change(self, state: IntegrationState):
        """通知状态变更"""
        for callback in self.integration_callbacks["on_state_change"]:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"状态变更回调函数执行失败: {e}")
    
    def _notify_error(self, error_msg: str):
        """通知错误事件"""
        self.stats["last_error"] = error_msg
        
        for callback in self.integration_callbacks["on_error"]:
            try:
                callback(error_msg)
            except Exception as e:
                logger.error(f"错误回调函数执行失败: {e}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """获取集成状态信息"""
        return {
            "system": "语音集成管理器",
            "state": self.state.value,
            "running": self.running,
            "last_activity_time": self.last_activity_time,
            "time_since_last_activity": time.time() - self.last_activity_time,
            "integrated_avatars_count": len(self.integrated_avatars),
            "integrated_avatars": self.integrated_avatars,
            "config": self.config,
            "services": {
                "wakeup_system": self.wakeup_system is not None,
                "conversation_engine": self.conversation_engine is not None,
                "avatar_manager": self.avatar_manager is not None,
                "chat_manager": self.chat_manager is not None,
                "shared_state_manager": self.shared_state_manager is not None
            },
            "statistics": self.stats,
            "voice_activity_log_count": len(self.voice_activity_log),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_avatar_voice_status(self, avatar_name: str) -> Optional[Dict[str, Any]]:
        """获取指定分身的语音状态"""
        if avatar_name in self.voice_enabled_avatars:
            status = self.voice_enabled_avatars[avatar_name].copy()
            status["avatar_name"] = avatar_name
            status["is_current"] = (self.conversation_engine and 
                                  self.conversation_engine.current_avatar == avatar_name)
            return status
        return None
    
    def list_all_voice_enabled_avatars(self) -> List[Dict[str, Any]]:
        """列出所有启用语音功能的分身"""
        result = []
        for avatar_name, status in self.voice_enabled_avatars.items():
            avatar_status = status.copy()
            avatar_status["avatar_name"] = avatar_name
            avatar_status["is_current"] = (self.conversation_engine and 
                                         self.conversation_engine.current_avatar == avatar_name)
            result.append(avatar_status)
        return result


# 全局集成管理器实例
_global_integration_manager = None

def get_global_integration_manager(**kwargs) -> VoiceIntegrationManager:
    """
    获取全局集成管理器实例（单例模式）
    
    Args:
        **kwargs: 初始化参数
        
    Returns:
        VoiceIntegrationManager: 全局集成管理器实例
    """
    global _global_integration_manager
    if _global_integration_manager is None:
        _global_integration_manager = VoiceIntegrationManager(**kwargs)
    return _global_integration_manager


# 测试代码
if __name__ == "__main__":
    print("语音集成管理器测试")
    print("=" * 50)
    
    try:
        # 创建集成管理器实例
        manager = VoiceIntegrationManager(
            wakeup_phrase="sell sell 在吗",
            default_avatar="情报官",
            sync_to_test=False  # 测试时不实际同步
        )
        
        # 打印初始状态
        status = manager.get_integration_status()
        print("初始状态:")
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # 定义回调函数
        def on_wakeup(result: WakeupResult):
            print(f"唤醒检测到: {result}")
        
        def on_state_change(state: IntegrationState):
            print(f"集成状态变更: {state.value}")
        
        def on_error(error_msg: str):
            print(f"集成错误: {error_msg}")
        
        manager.register_callback("on_wakeup", on_wakeup)
        manager.register_callback("on_state_change", on_state_change)
        manager.register_callback("on_error", on_error)
        
        print("\n启动集成管理器... (运行5秒后停止)")
        
        # 启动管理器
        if manager.start():
            print("集成管理器启动成功")
            
            # 运行5秒
            time.sleep(5)
            
            print("\n集成状态:")
            status = manager.get_integration_status()
            print(json.dumps(status, indent=2, ensure_ascii=False))
            
            print("\n停止集成管理器...")
            manager.stop()
            
            print("测试完成")
        else:
            print("集成管理器启动失败")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()