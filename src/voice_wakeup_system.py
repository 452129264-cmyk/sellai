#!/usr/bin/env python3
"""
语音唤醒系统

此模块提供语音唤醒功能，支持固定唤醒词【sell sell 在吗】检测，
实现秒级唤醒响应（<500ms）和待机静默模式。

核心功能：
1. 音频流实时监控与语音活动检测
2. 唤醒词识别与验证
3. 唤醒状态管理
4. 低功耗待机模式
5. 与现有无限分身系统深度集成
"""

import os
import sys
import json
import time
import logging
import threading
import queue
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from enum import Enum

# 尝试导入音频处理库
try:
    import pyaudio
    import wave
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    logging.warning("PyAudio库未安装，麦克风录音功能将受限")

# 导入现有的语音服务
try:
    from src.voice_recognition_service import WhisperRecognitionService, create_whisper_service
    HAS_WHISPER_SERVICE = True
except ImportError:
    HAS_WHISPER_SERVICE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WakeupState(Enum):
    """唤醒状态"""
    SLEEPING = "sleeping"      # 待机睡眠模式
    LISTENING = "listening"    # 监听唤醒词
    ACTIVE = "active"          # 唤醒激活状态
    PROCESSING = "processing"  # 正在处理用户语音


class WakeupResult:
    """唤醒结果类"""
    
    def __init__(
        self,
        is_wakeup: bool,
        confidence: float,
        detected_text: str,
        processing_time_ms: float,
        timestamp: float
    ):
        self.is_wakeup = is_wakeup
        self.confidence = confidence
        self.detected_text = detected_text
        self.processing_time_ms = processing_time_ms
        self.timestamp = timestamp
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_wakeup": self.is_wakeup,
            "confidence": self.confidence,
            "detected_text": self.detected_text,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp,
            "wakeup_time": datetime.fromtimestamp(self.timestamp).isoformat()
        }
    
    def __str__(self) -> str:
        return f"WakeupResult(wakeup={self.is_wakeup}, confidence={self.confidence:.2f}, text='{self.detected_text[:30]}...', time={self.processing_time_ms:.0f}ms)"


class VoiceActivityDetector:
    """语音活动检测器"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        energy_threshold: float = 500.0,
        silence_duration_ms: int = 500
    ):
        """
        初始化语音活动检测器
        
        Args:
            sample_rate: 采样率（Hz）
            frame_duration_ms: 帧时长（毫秒）
            energy_threshold: 能量阈值
            silence_duration_ms: 静默时长（毫秒），超过此时长认为语音结束
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.energy_threshold = energy_threshold
        self.silence_frames = int(silence_duration_ms / frame_duration_ms)
        
        # 状态跟踪
        self.is_speech = False
        self.silence_counter = 0
        self.audio_buffer = []
        self.buffer_max_duration_ms = 3000  # 最长缓存3秒音频
        
        logger.info(f"语音活动检测器初始化完成 (采样率: {sample_rate}Hz, 阈值: {energy_threshold})")
    
    def reset(self):
        """重置检测器状态"""
        self.is_speech = False
        self.silence_counter = 0
        self.audio_buffer = []
    
    def process_frame(self, audio_frame: np.ndarray) -> bool:
        """
        处理音频帧，返回是否检测到语音活动
        
        Args:
            audio_frame: 音频帧数据（numpy数组）
            
        Returns:
            bool: 是否处于语音活动状态
        """
        if len(audio_frame) != self.frame_size:
            logger.warning(f"音频帧大小不匹配: {len(audio_frame)} != {self.frame_size}")
            return self.is_speech
        
        # 计算帧能量
        energy = np.sum(audio_frame.astype(float) ** 2)
        
        # 语音活动检测逻辑
        if energy > self.energy_threshold:
            self.silence_counter = 0
            if not self.is_speech:
                self.is_speech = True
                logger.debug("检测到语音活动开始")
        else:
            if self.is_speech:
                self.silence_counter += 1
                if self.silence_counter >= self.silence_frames:
                    self.is_speech = False
                    logger.debug("检测到语音活动结束")
        
        # 缓存音频数据
        if self.is_speech:
            self.audio_buffer.append(audio_frame.copy())
            
            # 限制缓冲区大小
            max_frames = int(self.buffer_max_duration_ms / self.frame_duration_ms)
            if len(self.audio_buffer) > max_frames:
                self.audio_buffer = self.audio_buffer[-max_frames:]
        
        return self.is_speech
    
    def get_audio_data(self) -> Optional[np.ndarray]:
        """
        获取缓存的音频数据
        
        Returns:
            Optional[np.ndarray]: 拼接后的音频数据，如果没有数据则返回None
        """
        if not self.audio_buffer:
            return None
        
        return np.concatenate(self.audio_buffer)
    
    def clear_buffer(self):
        """清空音频缓冲区"""
        self.audio_buffer = []


class VoiceWakeupSystem:
    """语音唤醒系统主类"""
    
    def __init__(
        self,
        wakeup_phrase: str = "sell sell 在吗",
        whisper_model_size: str = "tiny",
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        vad_energy_threshold: float = 500.0
    ):
        """
        初始化语音唤醒系统
        
        Args:
            wakeup_phrase: 唤醒词短语
            whisper_model_size: Whisper模型大小 (tiny, base, small, medium, large)
            sample_rate: 音频采样率（Hz）
            channels: 音频通道数
            chunk_size: 音频块大小
            vad_energy_threshold: VAD能量阈值
        """
        self.wakeup_phrase = wakeup_phrase
        self.wakeup_keywords = self._parse_wakeup_phrase(wakeup_phrase)
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        
        # 状态管理
        self.state = WakeupState.SLEEPING
        self.state_lock = threading.Lock()
        self.last_wakeup_time = 0
        self.wakeup_count = 0
        
        # 语音活动检测器
        self.vad = VoiceActivityDetector(
            sample_rate=sample_rate,
            energy_threshold=vad_energy_threshold,
            silence_duration_ms=800
        )
        
        # 语音识别服务
        self.whisper_service = None
        if HAS_WHISPER_SERVICE:
            try:
                self.whisper_service = create_whisper_service(model_size=whisper_model_size)
                logger.info(f"Whisper服务初始化完成 (模型: {whisper_model_size})")
            except Exception as e:
                logger.warning(f"Whisper服务初始化失败: {e}")
        
        # 音频流处理
        self.audio_stream = None
        self.processing_thread = None
        self.running = False
        
        # 回调函数
        self.wakeup_callbacks = []
        self.state_change_callbacks = []
        
        # 统计信息
        self.stats = {
            "total_audio_frames_processed": 0,
            "total_speech_detections": 0,
            "total_wakeup_detections": 0,
            "total_false_positives": 0,
            "total_processing_time_ms": 0.0,
            "avg_wakeup_response_time_ms": 0.0,
            "start_time": time.time()
        }
        
        logger.info(f"语音唤醒系统初始化完成 (唤醒词: '{wakeup_phrase}')")
    
    def _parse_wakeup_phrase(self, phrase: str) -> List[str]:
        """解析唤醒词短语为关键词列表"""
        # 简单分割，实际应用中可能需要更复杂的处理
        keywords = phrase.lower().split()
        # 中文处理：如果没有空格，尝试按字符分割
        if len(keywords) == 1 and len(keywords[0]) > 2:
            # 可能是中文，按2-3个字符分割
            chinese_text = keywords[0]
            keywords = []
            for i in range(0, len(chinese_text), 2):
                if i + 2 <= len(chinese_text):
                    keywords.append(chinese_text[i:i+2])
        return keywords
    
    def start(self):
        """启动语音唤醒系统"""
        if self.running:
            logger.warning("语音唤醒系统已经在运行中")
            return
        
        if not HAS_PYAUDIO:
            logger.error("PyAudio不可用，无法启动语音唤醒系统")
            return False
        
        try:
            # 初始化音频流
            p = pyaudio.PyAudio()
            
            self.audio_stream = p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.running = True
            self.state = WakeupState.LISTENING
            
            # 启动处理线程
            self.processing_thread = threading.Thread(
                target=self._processing_loop,
                daemon=True
            )
            self.processing_thread.start()
            
            logger.info("语音唤醒系统启动成功")
            self._notify_state_change()
            return True
            
        except Exception as e:
            logger.error(f"启动语音唤醒系统失败: {e}")
            return False
    
    def stop(self):
        """停止语音唤醒系统"""
        if not self.running:
            return
        
        self.running = False
        
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        self.state = WakeupState.SLEEPING
        self._notify_state_change()
        logger.info("语音唤醒系统已停止")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频流回调函数"""
        self.stats["total_audio_frames_processed"] += 1
        
        # 转换为numpy数组
        audio_frame = np.frombuffer(in_data, dtype=np.int16)
        
        # 语音活动检测
        is_speech = self.vad.process_frame(audio_frame)
        
        if is_speech:
            self.stats["total_speech_detections"] += 1
        
        return (in_data, pyaudio.paContinue)
    
    def _processing_loop(self):
        """处理循环（检测语音活动并触发唤醒检测）"""
        logger.info("语音唤醒处理线程启动")
        
        while self.running:
            try:
                # 检查是否有完整的语音段
                time.sleep(0.01)  # 10ms间隔
                
                # 如果处于监听状态且检测到语音活动
                if self.state == WakeupState.LISTENING:
                    # 这里可以添加更复杂的逻辑，比如等待语音活动结束
                    # 简化：定期检查音频缓冲区
                    if self.vad.is_speech:
                        # 等待一小段时间让语音段更完整
                        time.sleep(0.2)
                        
                        # 获取音频数据
                        audio_data = self.vad.get_audio_data()
                        if audio_data is not None and len(audio_data) > self.sample_rate * 0.5:  # 至少0.5秒
                            # 异步处理唤醒检测
                            threading.Thread(
                                target=self._detect_wakeup,
                                args=(audio_data,),
                                daemon=True
                            ).start()
                            
                            # 清空缓冲区，避免重复处理
                            self.vad.clear_buffer()
                
            except Exception as e:
                logger.error(f"处理循环发生错误: {e}")
                time.sleep(0.1)
    
    def _detect_wakeup(self, audio_data: np.ndarray):
        """检测唤醒词"""
        if self.whisper_service is None:
            logger.warning("Whisper服务不可用，跳过唤醒检测")
            return
        
        start_time = time.time()
        
        try:
            # 将音频数据转换为字节
            audio_bytes = audio_data.tobytes()
            
            # 使用Whisper进行转录
            transcription_result = self.whisper_service.transcribe_audio_bytes(
                audio_bytes=audio_bytes,
                sample_rate=self.sample_rate
            )
            
            processing_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            # 检查是否包含唤醒词
            detected_text = transcription_result.text.lower()
            is_wakeup = False
            confidence = 0.0
            
            # 简单的关键词匹配
            for keyword in self.wakeup_keywords:
                if keyword in detected_text:
                    is_wakeup = True
                    confidence = transcription_result.confidence
                    break
            
            # 创建唤醒结果
            wakeup_result = WakeupResult(
                is_wakeup=is_wakeup,
                confidence=confidence,
                detected_text=detected_text,
                processing_time_ms=processing_time,
                timestamp=time.time()
            )
            
            logger.info(f"唤醒检测完成: {wakeup_result}")
            
            # 更新统计信息
            self.stats["total_processing_time_ms"] += processing_time
            
            if is_wakeup:
                self.stats["total_wakeup_detections"] += 1
                self.wakeup_count += 1
                self.last_wakeup_time = time.time()
                
                # 计算平均响应时间
                total_wakeups = self.stats["total_wakeup_detections"]
                current_avg = self.stats["avg_wakeup_response_time_ms"]
                self.stats["avg_wakeup_response_time_ms"] = (
                    current_avg * (total_wakeups - 1) + processing_time
                ) / total_wakeups if total_wakeups > 1 else processing_time
                
                # 切换到激活状态
                with self.state_lock:
                    self.state = WakeupState.ACTIVE
                    self._notify_state_change()
                
                # 触发唤醒回调
                self._notify_wakeup(wakeup_result)
                
            else:
                self.stats["total_false_positives"] += 1
                logger.debug(f"误报检测，文本: '{detected_text}'")
        
        except Exception as e:
            logger.error(f"唤醒检测失败: {e}")
    
    def register_wakeup_callback(self, callback: Callable[[WakeupResult], None]):
        """注册唤醒回调函数"""
        self.wakeup_callbacks.append(callback)
        logger.debug(f"注册唤醒回调函数，当前数量: {len(self.wakeup_callbacks)}")
    
    def register_state_change_callback(self, callback: Callable[[WakeupState], None]):
        """注册状态变更回调函数"""
        self.state_change_callbacks.append(callback)
        logger.debug(f"注册状态变更回调函数，当前数量: {len(self.state_change_callbacks)}")
    
    def _notify_wakeup(self, result: WakeupResult):
        """通知唤醒事件"""
        for callback in self.wakeup_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"唤醒回调函数执行失败: {e}")
    
    def _notify_state_change(self):
        """通知状态变更"""
        for callback in self.state_change_callbacks:
            try:
                callback(self.state)
            except Exception as e:
                logger.error(f"状态变更回调函数执行失败: {e}")
    
    def set_state(self, state: WakeupState):
        """设置系统状态"""
        with self.state_lock:
            self.state = state
            self._notify_state_change()
            logger.info(f"系统状态变更: {state.value}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态信息"""
        return {
            "system": "语音唤醒系统",
            "state": self.state.value,
            "wakeup_phrase": self.wakeup_phrase,
            "running": self.running,
            "wakeup_count": self.wakeup_count,
            "last_wakeup_time": self.last_wakeup_time,
            "time_since_last_wakeup": time.time() - self.last_wakeup_time if self.last_wakeup_time > 0 else None,
            "statistics": self.stats,
            "services": {
                "whisper": self.whisper_service is not None,
                "pyaudio": HAS_PYAUDIO
            },
            "uptime_seconds": time.time() - self.stats["start_time"],
            "timestamp": datetime.now().isoformat()
        }


# 便利函数
def create_voice_wakeup_system(
    wakeup_phrase: str = "sell sell 在吗",
    whisper_model_size: str = "tiny"
) -> VoiceWakeupSystem:
    """
    创建语音唤醒系统实例
    
    Args:
        wakeup_phrase: 唤醒词短语
        whisper_model_size: Whisper模型大小
        
    Returns:
        VoiceWakeupSystem: 语音唤醒系统实例
    """
    return VoiceWakeupSystem(
        wakeup_phrase=wakeup_phrase,
        whisper_model_size=whisper_model_size
    )


# 测试代码
if __name__ == "__main__":
    print("语音唤醒系统测试")
    print("=" * 50)
    
    # 创建系统实例
    try:
        system = create_voice_wakeup_system()
        
        # 打印系统状态
        status = system.get_system_status()
        print("系统状态:")
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # 定义回调函数
        def on_wakeup(result: WakeupResult):
            print(f"唤醒检测到: {result}")
        
        def on_state_change(state: WakeupState):
            print(f"状态变更: {state.value}")
        
        system.register_wakeup_callback(on_wakeup)
        system.register_state_change_callback(on_state_change)
        
        print("\n系统启动中... (按Ctrl+C停止)")
        
        # 启动系统
        if system.start():
            try:
                while True:
                    time.sleep(1)
                    # 定期打印状态
                    status = system.get_system_status()
                    print(f"运行中... 唤醒次数: {status['wakeup_count']}, 状态: {status['state']}")
            except KeyboardInterrupt:
                print("\n收到停止信号")
            finally:
                system.stop()
        else:
            print("系统启动失败")
        
        print("测试完成")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()