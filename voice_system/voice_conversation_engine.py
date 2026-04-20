#!/usr/bin/env python3
"""
实时语音对话引擎

此模块提供完整的语音对话功能，集成语音唤醒、语音识别、AI处理和语音合成，
与无限分身系统深度绑定，实现全链路语音交互。

核心功能：
1. 语音唤醒集成
2. 实时语音识别（ASR）
3. AI分身对话处理
4. 语音合成输出（TTS）
5. 多分身语音兼容
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
import base64

# 导入现有服务
try:
    from src.voice_wakeup_system import VoiceWakeupSystem, WakeupResult, WakeupState
    HAS_WAKEUP_SYSTEM = True
except ImportError:
    HAS_WAKEUP_SYSTEM = False

try:
    from src.voice_recognition_service import WhisperRecognitionService, create_whisper_service
    HAS_WHISPER_SERVICE = True
except ImportError:
    HAS_WHISPER_SERVICE = False

try:
    from src.voice_synthesis_service import AzureTTSService, create_azure_tts_service, VoiceStyle
    HAS_AZURE_TTS_SERVICE = True
except ImportError:
    HAS_AZURE_TTS_SERVICE = False

# 导入分身系统接口（假设存在）
try:
    from src.social_relationship_manager import SocialRelationshipManager
    from src.chat_manager import ChatManager
    HAS_AVATAR_SYSTEM = True
except ImportError:
    HAS_AVATAR_SYSTEM = False
    # 创建模拟接口用于测试
    class SocialRelationshipManager:
        def get_active_avatars(self):
            return ["情报官", "内容官", "运营官", "增长官"]
    
    class ChatManager:
        def send_message(self, avatar_name, message):
            print(f"[模拟] {avatar_name} 收到消息: {message}")
            return {"response": f"这是 {avatar_name} 的模拟回复", "timestamp": time.time()}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """对话状态"""
    IDLE = "idle"              # 空闲状态，等待唤醒
    LISTENING = "listening"    # 正在监听用户语音
    PROCESSING = "processing"  # 正在处理用户请求
    SPEAKING = "speaking"      # 正在播放AI回复
    ERROR = "error"            # 错误状态


class VoiceConversationEngine:
    """实时语音对话引擎主类"""
    
    def __init__(
        self,
        default_avatar: str = "情报官",
        wakeup_phrase: str = "sell sell 在吗",
        whisper_model_size: str = "base",
        azure_tts_key: Optional[str] = None,
        azure_tts_region: Optional[str] = None,
        sample_rate: int = 16000
    ):
        """
        初始化语音对话引擎
        
        Args:
            default_avatar: 默认对话分身
            wakeup_phrase: 唤醒词短语
            whisper_model_size: Whisper模型大小
            azure_tts_key: Azure TTS密钥
            azure_tts_region: Azure TTS区域
            sample_rate: 音频采样率
        """
        self.default_avatar = default_avatar
        self.sample_rate = sample_rate
        
        # 状态管理
        self.state = ConversationState.IDLE
        self.state_lock = threading.Lock()
        self.current_avatar = default_avatar
        self.conversation_context = {}
        
        # 初始化语音唤醒系统
        self.wakeup_system = None
        if HAS_WAKEUP_SYSTEM:
            try:
                self.wakeup_system = VoiceWakeupSystem(
                    wakeup_phrase=wakeup_phrase,
                    whisper_model_size="tiny",  # 唤醒用更小的模型
                    sample_rate=sample_rate
                )
                # 注册唤醒回调
                self.wakeup_system.register_wakeup_callback(self._on_wakeup_detected)
                self.wakeup_system.register_state_change_callback(self._on_wakeup_state_change)
                logger.info("语音唤醒系统初始化完成")
            except Exception as e:
                logger.warning(f"语音唤醒系统初始化失败: {e}")
        
        # 初始化语音识别服务（用于对话）
        self.whisper_service = None
        if HAS_WHISPER_SERVICE:
            try:
                self.whisper_service = create_whisper_service(model_size=whisper_model_size)
                logger.info(f"语音识别服务初始化完成 (模型: {whisper_model_size})")
            except Exception as e:
                logger.warning(f"语音识别服务初始化失败: {e}")
        
        # 初始化语音合成服务
        self.tts_service = None
        if HAS_AZURE_TTS_SERVICE and azure_tts_key:
            try:
                self.tts_service = create_azure_tts_service(
                    subscription_key=azure_tts_key,
                    region=azure_tts_region or "eastus"
                )
                logger.info("语音合成服务初始化完成")
            except Exception as e:
                logger.warning(f"语音合成服务初始化失败: {e}")
        
        # 初始化分身系统
        self.avatar_manager = None
        self.chat_manager = None
        if HAS_AVATAR_SYSTEM:
            try:
                self.avatar_manager = SocialRelationshipManager()
                self.chat_manager = ChatManager()
                logger.info("分身系统接口初始化完成")
            except Exception as e:
                logger.warning(f"分身系统接口初始化失败: {e}")
        else:
            # 使用模拟接口
            self.avatar_manager = SocialRelationshipManager()
            self.chat_manager = ChatManager()
            logger.info("使用模拟分身系统接口")
        
        # 对话队列和线程
        self.conversation_queue = queue.Queue(maxsize=10)
        self.processing_thread = None
        self.running = False
        
        # 音频输出队列（用于播放合成语音）
        self.audio_output_queue = queue.Queue(maxsize=5)
        
        # 统计信息
        self.stats = {
            "total_conversations": 0,
            "total_wakeups": 0,
            "total_user_speech_seconds": 0.0,
            "total_processing_time_ms": 0.0,
            "avg_response_time_ms": 0.0,
            "success_rate": 1.0,
            "start_time": time.time()
        }
        
        # 回调函数
        self.state_change_callbacks = []
        self.speech_start_callbacks = []
        self.speech_end_callbacks = []
        self.response_ready_callbacks = []
        
        logger.info("实时语音对话引擎初始化完成")
    
    def start(self):
        """启动对话引擎"""
        if self.running:
            logger.warning("对话引擎已经在运行中")
            return
        
        self.running = True
        
        # 启动语音唤醒系统
        if self.wakeup_system:
            self.wakeup_system.start()
        
        # 启动处理线程
        self.processing_thread = threading.Thread(
            target=self._conversation_processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        
        logger.info("实时语音对话引擎启动成功")
        self._set_state(ConversationState.IDLE)
    
    def stop(self):
        """停止对话引擎"""
        if not self.running:
            return
        
        self.running = False
        
        # 停止语音唤醒系统
        if self.wakeup_system:
            self.wakeup_system.stop()
        
        # 停止处理线程
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        logger.info("实时语音对话引擎已停止")
        self._set_state(ConversationState.IDLE)
    
    def _on_wakeup_detected(self, result: WakeupResult):
        """处理唤醒事件"""
        if result.is_wakeup:
            logger.info(f"唤醒词检测成功: {result.detected_text}, 置信度: {result.confidence:.2f}")
            self.stats["total_wakeups"] += 1
            
            # 切换到监听状态
            self._set_state(ConversationState.LISTENING)
            
            # 播放唤醒提示音（可选）
            self._play_wakeup_sound()
            
            # 开始监听用户语音
            self._start_listening()
    
    def _on_wakeup_state_change(self, state: WakeupState):
        """处理唤醒系统状态变更"""
        logger.debug(f"唤醒系统状态变更: {state.value}")
        
        if state == WakeupState.SLEEPING and self.state == ConversationState.IDLE:
            # 如果唤醒系统进入睡眠状态，且当前是空闲状态，保持同步
            pass
    
    def _play_wakeup_sound(self):
        """播放唤醒提示音"""
        logger.info("播放唤醒提示音")
        # 实际实现中，这里可以播放一个简短的提示音
        # 例如：一个简短的"叮"声或语音提示"我在听"
        
        # 使用语音合成播放提示
        if self.tts_service:
            try:
                # 异步播放提示音
                threading.Thread(
                    target=self._synthesize_and_play,
                    args=("请说", "zh-CN-XiaoxiaoNeural", "zh-CN"),
                    daemon=True
                ).start()
            except Exception as e:
                logger.warning(f"播放唤醒提示音失败: {e}")
    
    def _start_listening(self):
        """开始监听用户语音"""
        logger.info("开始监听用户语音")
        
        # 在实际实现中，这里会启动录音或设置音频流监听
        # 由于系统架构已有音频流处理，这里主要设置状态
        
        # 在实际部署中，这里会启动一个录音会话
        # 简化：设置一个定时器模拟语音输入结束
        self._schedule_listening_timeout()
    
    def _schedule_listening_timeout(self):
        """设置监听超时（用户不说话时自动结束）"""
        # 在实际实现中，这里会启动一个计时器
        # 简化：使用线程延迟
        def listening_timeout():
            time.sleep(5.0)  # 5秒无语音则结束监听
            if self.state == ConversationState.LISTENING:
                logger.info("监听超时，返回空闲状态")
                self._set_state(ConversationState.IDLE)
        
        threading.Thread(target=listening_timeout, daemon=True).start()
    
    def process_user_speech(self, audio_data: bytes, sample_rate: int = 16000):
        """
        处理用户语音输入
        
        Args:
            audio_data: 音频数据字节
            sample_rate: 采样率
        """
        if self.state != ConversationState.LISTENING:
            logger.warning(f"当前状态 {self.state.value} 不能处理用户语音")
            return
        
        logger.info(f"收到用户语音数据，大小: {len(audio_data)} 字节")
        
        # 切换到处理状态
        self._set_state(ConversationState.PROCESSING)
        
        # 放入处理队列
        try:
            self.conversation_queue.put((audio_data, sample_rate), timeout=1.0)
            logger.debug("用户语音已加入处理队列")
        except queue.Full:
            logger.error("处理队列已满，丢弃用户语音")
            self._set_state(ConversationState.LISTENING)  # 返回监听状态
    
    def _conversation_processing_loop(self):
        """对话处理循环"""
        logger.info("对话处理线程启动")
        
        while self.running:
            try:
                # 从队列获取用户语音
                audio_data, sample_rate = self.conversation_queue.get(timeout=1.0)
                
                # 处理语音
                self._process_conversation(audio_data, sample_rate)
                
                # 标记任务完成
                self.conversation_queue.task_done()
                
            except queue.Empty:
                continue  # 队列为空，继续等待
            except Exception as e:
                logger.error(f"对话处理循环发生错误: {e}")
                self._set_state(ConversationState.ERROR)
                time.sleep(0.1)
    
    def _process_conversation(self, audio_data: bytes, sample_rate: int):
        """处理单次对话"""
        start_time = time.time()
        
        try:
            # 步骤1：语音转文字
            user_text = self._speech_to_text(audio_data, sample_rate)
            if not user_text or not user_text.strip():
                logger.warning("语音转文字结果为空")
                self._set_state(ConversationState.IDLE)
                return
            
            # 更新统计
            audio_seconds = len(audio_data) / (sample_rate * 2)  # 近似计算
            self.stats["total_user_speech_seconds"] += audio_seconds
            
            logger.info(f"用户语音转文字: '{user_text}'")
            
            # 步骤2：发送给AI分身处理
            ai_response = self._send_to_avatar(user_text)
            if not ai_response:
                logger.warning("AI分身未返回有效响应")
                ai_response = "抱歉，我没有理解你的意思。请再说一遍。"
            
            # 步骤3：文字转语音
            self._text_to_speech(ai_response)
            
            # 计算处理时间
            processing_time = (time.time() - start_time) * 1000
            self.stats["total_processing_time_ms"] += processing_time
            
            # 更新平均响应时间
            self.stats["avg_response_time_ms"] = (
                self.stats["avg_response_time_ms"] * self.stats["total_conversations"] + processing_time
            ) / (self.stats["total_conversations"] + 1)
            
            self.stats["total_conversations"] += 1
            
            logger.info(f"对话处理完成，响应时间: {processing_time:.0f}ms")
            
            # 返回到空闲状态
            self._set_state(ConversationState.IDLE)
            
        except Exception as e:
            logger.error(f"处理对话失败: {e}")
            self._set_state(ConversationState.ERROR)
            
            # 尝试恢复
            time.sleep(1)
            self._set_state(ConversationState.IDLE)
    
    def _speech_to_text(self, audio_data: bytes, sample_rate: int) -> Optional[str]:
        """语音转文字"""
        if not self.whisper_service:
            logger.warning("语音识别服务不可用")
            return None
        
        try:
            result = self.whisper_service.transcribe_audio_bytes(
                audio_bytes=audio_data,
                sample_rate=sample_rate
            )
            return result.text.strip()
        except Exception as e:
            logger.error(f"语音转文字失败: {e}")
            return None
    
    def _send_to_avatar(self, user_text: str) -> Optional[str]:
        """发送给AI分身处理"""
        try:
            # 使用当前激活的分身
            avatar_name = self.current_avatar
            
            # 在实际系统中，这里会调用分身系统的API
            # 简化：直接调用模拟接口
            response = self.chat_manager.send_message(avatar_name, user_text)
            
            if isinstance(response, dict) and "response" in response:
                return response["response"]
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"发送给分身处理失败: {e}")
            return None
    
    def _text_to_speech(self, text: str):
        """文字转语音"""
        if not self.tts_service:
            logger.warning("语音合成服务不可用")
            return
        
        try:
            # 异步合成和播放
            threading.Thread(
                target=self._synthesize_and_play,
                args=(text, "zh-CN-XiaoxiaoNeural", "zh-CN"),
                daemon=True
            ).start()
            
            # 切换到说话状态
            self._set_state(ConversationState.SPEAKING)
            
        except Exception as e:
            logger.error(f"文字转语音失败: {e}")
    
    def _synthesize_and_play(self, text: str, voice: str, language: str):
        """合成语音并播放"""
        try:
            result = self.tts_service.synthesize_text(
                text=text,
                voice_name=voice,
                language=language
            )
            
            logger.info(f"语音合成完成，音频大小: {len(result.audio_data)} 字节")
            
            # 在实际系统中，这里会播放音频
            # 简化：保存到文件
            timestamp = int(time.time())
            audio_file = f"temp/voice_output_{timestamp}.mp3"
            os.makedirs(os.path.dirname(audio_file), exist_ok=True)
            
            with open(audio_file, "wb") as f:
                f.write(result.audio_data)
            
            logger.info(f"语音已保存到: {audio_file}")
            
            # 通知语音合成完成
            self._notify_response_ready(text, audio_file)
            
        except Exception as e:
            logger.error(f"合成和播放语音失败: {e}")
    
    def _set_state(self, state: ConversationState):
        """设置引擎状态"""
        with self.state_lock:
            old_state = self.state
            self.state = state
            
            if old_state != state:
                logger.info(f"对话引擎状态变更: {old_state.value} -> {state.value}")
                self._notify_state_change(state)
    
    def switch_avatar(self, avatar_name: str):
        """切换当前对话分身"""
        # 获取可用的分身列表
        available_avatars = self.avatar_manager.get_active_avatars()
        
        if avatar_name in available_avatars:
            self.current_avatar = avatar_name
            logger.info(f"已切换到分身: {avatar_name}")
            
            # 播放切换提示
            if self.tts_service:
                self._synthesize_and_play(f"已切换到{avatar_name}", "zh-CN-XiaoxiaoNeural", "zh-CN")
            
            return True
        else:
            logger.warning(f"分身 {avatar_name} 不可用，可用分身: {available_avatars}")
            return False
    
    def register_state_change_callback(self, callback: Callable[[ConversationState], None]):
        """注册状态变更回调函数"""
        self.state_change_callbacks.append(callback)
    
    def register_speech_start_callback(self, callback: Callable[[], None]):
        """注册语音开始回调函数"""
        self.speech_start_callbacks.append(callback)
    
    def register_speech_end_callback(self, callback: Callable[[], None]):
        """注册语音结束回调函数"""
        self.speech_end_callbacks.append(callback)
    
    def register_response_ready_callback(self, callback: Callable[[str, Optional[str]], None]):
        """注册响应就绪回调函数"""
        self.response_ready_callbacks.append(callback)
    
    def _notify_state_change(self, state: ConversationState):
        """通知状态变更"""
        for callback in self.state_change_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"状态变更回调函数执行失败: {e}")
    
    def _notify_response_ready(self, text: str, audio_file: Optional[str] = None):
        """通知响应就绪"""
        for callback in self.response_ready_callbacks:
            try:
                callback(text, audio_file)
            except Exception as e:
                logger.error(f"响应就绪回调函数执行失败: {e}")
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态信息"""
        return {
            "engine": "实时语音对话引擎",
            "state": self.state.value,
            "current_avatar": self.current_avatar,
            "default_avatar": self.default_avatar,
            "running": self.running,
            "conversation_queue_size": self.conversation_queue.qsize(),
            "services": {
                "wakeup_system": self.wakeup_system is not None,
                "whisper_service": self.whisper_service is not None,
                "tts_service": self.tts_service is not None,
                "avatar_system": self.avatar_manager is not None
            },
            "statistics": self.stats,
            "uptime_seconds": time.time() - self.stats["start_time"],
            "timestamp": datetime.now().isoformat()
        }


# 与无限分身系统的集成适配器
class AvatarVoiceAdapter:
    """分身语音适配器，将语音功能集成到每个分身"""
    
    def __init__(self, conversation_engine: VoiceConversationEngine):
        self.engine = conversation_engine
        self.avatar_voice_settings = {}  # 每个分身的语音设置
        
        logger.info("分身语音适配器初始化完成")
    
    def bind_avatar(self, avatar_name: str, voice_settings: Optional[Dict] = None):
        """绑定分身到语音系统"""
        default_settings = {
            "wakeup_enabled": True,
            "default_voice": "zh-CN-XiaoxiaoNeural",
            "speaking_rate": 1.0,
            "pitch": 0.0,
            "style": VoiceStyle.NEUTRAL
        }
        
        if voice_settings:
            default_settings.update(voice_settings)
        
        self.avatar_voice_settings[avatar_name] = default_settings
        logger.info(f"分身 {avatar_name} 已绑定到语音系统")
    
    def enable_avatar_wakeup(self, avatar_name: str, enabled: bool = True):
        """启用/禁用分身的语音唤醒"""
        if avatar_name in self.avatar_voice_settings:
            self.avatar_voice_settings[avatar_name]["wakeup_enabled"] = enabled
            logger.info(f"分身 {avatar_name} 语音唤醒已{'启用' if enabled else '禁用'}")
            return True
        return False
    
    def process_avatar_voice_command(self, avatar_name: str, audio_data: bytes) -> Optional[str]:
        """处理分身的语音命令"""
        # 在实际系统中，这里会调用对应分身的处理逻辑
        # 简化：使用引擎的通用处理
        self.engine.process_user_speech(audio_data)
        
        # 在实际实现中，这里需要等待响应
        return "语音命令已接收，正在处理..."
    
    def speak_as_avatar(self, avatar_name: str, text: str):
        """以分身身份说话"""
        if avatar_name in self.avatar_voice_settings:
            settings = self.avatar_voice_settings[avatar_name]
            
            # 使用分身的语音设置
            voice = settings.get("default_voice", "zh-CN-XiaoxiaoNeural")
            language = voice[:5] if '-' in voice else "zh-CN"
            
            # 异步合成语音
            threading.Thread(
                target=self._avatar_synthesize,
                args=(avatar_name, text, voice, language),
                daemon=True
            ).start()
    
    def _avatar_synthesize(self, avatar_name: str, text: str, voice: str, language: str):
        """分身语音合成"""
        if self.engine.tts_service:
            try:
                result = self.engine.tts_service.synthesize_text(
                    text=text,
                    voice_name=voice,
                    language=language
                )
                
                # 保存或播放音频
                timestamp = int(time.time())
                audio_file = f"temp/avatar_voice_{avatar_name}_{timestamp}.mp3"
                os.makedirs(os.path.dirname(audio_file), exist_ok=True)
                
                with open(audio_file, "wb") as f:
                    f.write(result.audio_data)
                
                logger.info(f"分身 {avatar_name} 语音已合成: '{text[:50]}...'")
                return audio_file
                
            except Exception as e:
                logger.error(f"分身 {avatar_name} 语音合成失败: {e}")
                return None


# 便利函数
def create_voice_conversation_engine(
    default_avatar: str = "情报官",
    wakeup_phrase: str = "sell sell 在吗",
    whisper_model_size: str = "base",
    azure_tts_key: Optional[str] = None,
    azure_tts_region: Optional[str] = None
) -> VoiceConversationEngine:
    """
    创建语音对话引擎实例
    
    Args:
        default_avatar: 默认对话分身
        wakeup_phrase: 唤醒词短语
        whisper_model_size: Whisper模型大小
        azure_tts_key: Azure TTS密钥
        azure_tts_region: Azure TTS区域
        
    Returns:
        VoiceConversationEngine: 语音对话引擎实例
    """
    return VoiceConversationEngine(
        default_avatar=default_avatar,
        wakeup_phrase=wakeup_phrase,
        whisper_model_size=whisper_model_size,
        azure_tts_key=azure_tts_key,
        azure_tts_region=azure_tts_region
    )


# 测试代码
if __name__ == "__main__":
    print("实时语音对话引擎测试")
    print("=" * 50)
    
    # 创建引擎实例（使用模拟服务）
    try:
        engine = create_voice_conversation_engine()
        
        # 打印状态
        status = engine.get_engine_status()
        print("引擎状态:")
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # 定义回调函数
        def on_state_change(state: ConversationState):
            print(f"引擎状态变更: {state.value}")
        
        def on_response_ready(text: str, audio_file: Optional[str]):
            print(f"AI响应就绪: '{text[:50]}...', 音频文件: {audio_file}")
        
        engine.register_state_change_callback(on_state_change)
        engine.register_response_ready_callback(on_response_ready)
        
        print("\n启动引擎... (按Ctrl+C停止)")
        engine.start()
        
        # 模拟测试
        time.sleep(2)
        
        print("\n模拟用户语音输入...")
        # 创建模拟音频数据（静音）
        sample_rate = 16000
        duration = 1.0  # 1秒
        audio_data = np.zeros(int(sample_rate * duration), dtype=np.int16).tobytes()
        
        engine.process_user_speech(audio_data, sample_rate)
        
        # 等待处理
        time.sleep(3)
        
        print("\n切换分身测试...")
        engine.switch_avatar("内容官")
        
        time.sleep(2)
        
        print("\n停止引擎...")
        engine.stop()
        
        print("\n测试完成")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()