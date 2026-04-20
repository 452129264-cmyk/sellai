#!/usr/bin/env python3
"""
实时音频流处理框架

此模块提供实时音频流处理的核心功能，支持录音、编码、传输、解码全流程，
与Whisper语音识别服务和Azure TTS语音合成服务深度集成。

核心功能：
1. WebSocket音频流服务器
2. 音频数据缓冲与分块处理
3. 多客户端连接管理
4. 低延迟音频处理优化
5. 与现有SellAI系统架构兼容
"""

import os
import sys
import json
import time
import logging
import threading
import queue
import asyncio
import websockets
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, Callable, BinaryIO
from enum import Enum
import base64
import numpy as np

# 尝试导入音频处理库
try:
    import pydub
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False

# 导入语音识别和合成服务
try:
    from src.voice_recognition_service import WhisperRecognitionService, create_whisper_service
    HAS_WHISPER_SERVICE = True
except ImportError:
    HAS_WHISPER_SERVICE = False

try:
    from src.voice_synthesis_service import AzureTTSService, create_azure_tts_service
    HAS_AZURE_TTS_SERVICE = True
except ImportError:
    HAS_AZURE_TTS_SERVICE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioStreamFormat(Enum):
    """音频流格式"""
    PCM_16KHZ_16BIT_MONO = "pcm_16khz_16bit_mono"
    PCM_16KHZ_16BIT_STEREO = "pcm_16khz_16bit_stereo"
    PCM_48KHZ_16BIT_MONO = "pcm_48khz_16bit_mono"
    MP3_16KHZ_32KBPS_MONO = "mp3_16khz_32kbps_mono"
    OPUS_16KHZ_16KBPS_MONO = "opus_16khz_16kbps_mono"


class AudioChunk:
    """音频数据块"""
    
    def __init__(
        self,
        audio_data: bytes,
        chunk_id: str,
        timestamp: float,
        duration_ms: float,
        sample_rate: int = 16000,
        channels: int = 1,
        format: AudioStreamFormat = AudioStreamFormat.PCM_16KHZ_16BIT_MONO
    ):
        self.audio_data = audio_data
        self.chunk_id = chunk_id
        self.timestamp = timestamp
        self.duration_ms = duration_ms
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = format
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chunk_id": self.chunk_id,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "format": self.format.value,
            "audio_data_length": len(self.audio_data)
        }
    
    def __str__(self) -> str:
        return f"AudioChunk(id={self.chunk_id}, duration={self.duration_ms}ms, size={len(self.audio_data)} bytes)"


class ClientConnection:
    """客户端连接信息"""
    
    def __init__(
        self,
        client_id: str,
        websocket: Any,
        connected_at: float,
        client_info: Optional[Dict] = None
    ):
        self.client_id = client_id
        self.websocket = websocket
        self.connected_at = connected_at
        self.client_info = client_info or {}
        self.last_activity = connected_at
        self.total_audio_received = 0
        self.total_messages_sent = 0
        
    def update_activity(self):
        """更新活动时间"""
        self.last_activity = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "client_id": self.client_id,
            "connected_at": self.connected_at,
            "last_activity": self.last_activity,
            "total_audio_received": self.total_audio_received,
            "total_messages_sent": self.total_messages_sent,
            "client_info": self.client_info
        }


class RealTimeAudioStreamServer:
    """实时音频流处理服务器"""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        whisper_model_size: str = "base",
        azure_tts_key: Optional[str] = None,
        azure_tts_region: Optional[str] = None,
        max_clients: int = 100,
        chunk_duration_ms: int = 3000
    ):
        """
        初始化音频流服务器
        
        Args:
            host: 服务器主机地址
            port: 服务器端口
            whisper_model_size: Whisper模型大小
            azure_tts_key: Azure TTS密钥
            azure_tts_region: Azure TTS区域
            max_clients: 最大客户端数
            chunk_duration_ms: 音频分块时长（毫秒）
        """
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.chunk_duration_ms = chunk_duration_ms
        
        # 客户端连接管理
        self.clients: Dict[str, ClientConnection] = {}
        self.client_lock = threading.Lock()
        
        # 音频处理队列
        self.audio_queue = queue.Queue(maxsize=100)
        
        # 初始化语音服务
        self.whisper_service = None
        self.azure_tts_service = None
        
        if HAS_WHISPER_SERVICE:
            try:
                self.whisper_service = create_whisper_service(model_size=whisper_model_size)
                logger.info(f"Whisper服务初始化完成 (模型: {whisper_model_size})")
            except Exception as e:
                logger.warning(f"Whisper服务初始化失败: {e}")
        
        if HAS_AZURE_TTS_SERVICE and azure_tts_key:
            try:
                self.azure_tts_service = create_azure_tts_service(
                    subscription_key=azure_tts_key,
                    region=azure_tts_region or "eastus"
                )
                logger.info(f"Azure TTS服务初始化完成 (区域: {azure_tts_region or 'eastus'})")
            except Exception as e:
                logger.warning(f"Azure TTS服务初始化失败: {e}")
        
        # 处理线程
        self.processing_thread = None
        self.running = False
        
        # 统计信息
        self.stats = {
            "total_clients_connected": 0,
            "current_clients": 0,
            "total_audio_chunks_received": 0,
            "total_transcriptions": 0,
            "total_syntheses": 0,
            "total_bytes_received": 0,
            "start_time": time.time()
        }
        
        logger.info(f"实时音频流服务器初始化完成 (地址: {host}:{port})")
    
    async def start_server(self):
        """启动WebSocket服务器"""
        try:
            server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port
            )
            
            logger.info(f"WebSocket服务器启动成功，监听 {self.host}:{self.port}")
            logger.info("等待客户端连接...")
            
            # 启动音频处理线程
            self.running = True
            self.processing_thread = threading.Thread(
                target=self._audio_processing_loop,
                daemon=True
            )
            self.processing_thread.start()
            
            # 保持服务器运行
            await server.wait_closed()
            
        except Exception as e:
            logger.error(f"启动WebSocket服务器失败: {e}")
            raise
    
    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        client_id = f"client_{int(time.time() * 1000)}_{len(self.clients)}"
        
        # 注册客户端
        with self.client_lock:
            if len(self.clients) >= self.max_clients:
                await websocket.close(1001, "服务器达到最大客户端限制")
                return
            
            client = ClientConnection(
                client_id=client_id,
                websocket=websocket,
                connected_at=time.time()
            )
            self.clients[client_id] = client
            self.stats["total_clients_connected"] += 1
            self.stats["current_clients"] = len(self.clients)
        
        logger.info(f"客户端连接: {client_id}, 当前客户端数: {len(self.clients)}")
        
        try:
            # 发送欢迎消息
            welcome_msg = {
                "type": "welcome",
                "client_id": client_id,
                "timestamp": time.time(),
                "server_info": {
                    "version": "1.0.0",
                    "services": {
                        "whisper": HAS_WHISPER_SERVICE,
                        "azure_tts": HAS_AZURE_TTS_SERVICE and self.azure_tts_service is not None
                    }
                }
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # 处理客户端消息
            async for message in websocket:
                client.update_activity()
                await self._process_client_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端断开连接: {client_id}")
        except Exception as e:
            logger.error(f"处理客户端 {client_id} 时发生错误: {e}")
        finally:
            # 注销客户端
            with self.client_lock:
                if client_id in self.clients:
                    del self.clients[client_id]
                    self.stats["current_clients"] = len(self.clients)
                    logger.info(f"客户端注销: {client_id}, 剩余客户端数: {len(self.clients)}")
    
    async def _process_client_message(self, client_id: str, message: Union[str, bytes]):
        """处理客户端消息"""
        try:
            if isinstance(message, str):
                # JSON消息
                data = json.loads(message)
                msg_type = data.get("type", "unknown")
                
                if msg_type == "audio":
                    # 音频数据
                    audio_data = base64.b64decode(data.get("audio", ""))
                    format_str = data.get("format", "pcm_16khz_16bit_mono")
                    sample_rate = data.get("sample_rate", 16000)
                    
                    # 创建音频块
                    chunk_id = f"chunk_{int(time.time() * 1000)}"
                    chunk = AudioChunk(
                        audio_data=audio_data,
                        chunk_id=chunk_id,
                        timestamp=time.time(),
                        duration_ms=data.get("duration_ms", 3000),
                        sample_rate=sample_rate,
                        channels=data.get("channels", 1),
                        format=AudioStreamFormat(format_str)
                    )
                    
                    # 放入处理队列
                    if self.audio_queue.full():
                        logger.warning("音频队列已满，丢弃最旧数据")
                        try:
                            self.audio_queue.get_nowait()
                        except queue.Empty:
                            pass
                    
                    self.audio_queue.put((client_id, chunk))
                    self.stats["total_audio_chunks_received"] += 1
                    self.stats["total_bytes_received"] += len(audio_data)
                    
                    # 更新客户端统计
                    with self.client_lock:
                        if client_id in self.clients:
                            self.clients[client_id].total_audio_received += len(audio_data)
                    
                    logger.debug(f"收到音频块: {chunk_id}, 大小: {len(audio_data)} bytes, 客户端: {client_id}")
                    
                elif msg_type == "text_to_speech":
                    # 文本转语音请求
                    text = data.get("text", "")
                    voice_name = data.get("voice", None)
                    language = data.get("language", None)
                    
                    if text and self.azure_tts_service:
                        # 异步合成语音
                        threading.Thread(
                            target=self._handle_text_to_speech,
                            args=(client_id, text, voice_name, language),
                            daemon=True
                        ).start()
                    
                    # 确认收到
                    response = {
                        "type": "tts_received",
                        "timestamp": time.time(),
                        "text_length": len(text)
                    }
                    with self.client_lock:
                        if client_id in self.clients:
                            client = self.clients[client_id]
                            asyncio.create_task(client.websocket.send(json.dumps(response)))
                
                elif msg_type == "status_request":
                    # 状态查询
                    response = {
                        "type": "status_response",
                        "timestamp": time.time(),
                        "server_status": "running",
                        "client_count": len(self.clients),
                        "queue_size": self.audio_queue.qsize(),
                        "services": {
                            "whisper": self.whisper_service is not None,
                            "azure_tts": self.azure_tts_service is not None
                        }
                    }
                    with self.client_lock:
                        if client_id in self.clients:
                            client = self.clients[client_id]
                            asyncio.create_task(client.websocket.send(json.dumps(response)))
            
            elif isinstance(message, bytes):
                # 二进制音频数据（原始PCM）
                chunk_id = f"chunk_{int(time.time() * 1000)}"
                chunk = AudioChunk(
                    audio_data=message,
                    chunk_id=chunk_id,
                    timestamp=time.time(),
                    duration_ms=self.chunk_duration_ms,
                    sample_rate=16000,
                    channels=1,
                    format=AudioStreamFormat.PCM_16KHZ_16BIT_MONO
                )
                
                if self.audio_queue.full():
                    logger.warning("音频队列已满，丢弃最旧数据")
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        pass
                
                self.audio_queue.put((client_id, chunk))
                self.stats["total_audio_chunks_received"] += 1
                self.stats["total_bytes_received"] += len(message)
                
                logger.debug(f"收到二进制音频块: {chunk_id}, 大小: {len(message)} bytes")
                
        except Exception as e:
            logger.error(f"处理客户端消息失败: {e}")
    
    def _audio_processing_loop(self):
        """音频处理循环（在后台线程运行）"""
        logger.info("音频处理线程启动")
        
        while self.running:
            try:
                # 从队列获取音频块（带超时）
                try:
                    client_id, chunk = self.audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 处理音频块
                self._process_audio_chunk(client_id, chunk)
                
                # 标记任务完成
                self.audio_queue.task_done()
                
            except Exception as e:
                logger.error(f"音频处理循环发生错误: {e}")
                time.sleep(0.1)
    
    def _process_audio_chunk(self, client_id: str, chunk: AudioChunk):
        """处理音频块（语音识别）"""
        if not self.whisper_service:
            logger.warning("Whisper服务不可用，跳过音频处理")
            return
        
        try:
            logger.info(f"开始处理音频块: {chunk.chunk_id}, 时长: {chunk.duration_ms}ms")
            start_time = time.time()
            
            # 转录音频
            transcription_result = self.whisper_service.transcribe_audio_bytes(
                audio_bytes=chunk.audio_data,
                sample_rate=chunk.sample_rate
            )
            
            processing_time = time.time() - start_time
            logger.info(f"音频块处理完成: {chunk.chunk_id}, 文本: {transcription_result.text[:50]}..., "
                       f"处理时间: {processing_time:.2f}s, 置信度: {transcription_result.confidence:.2f}")
            
            # 发送结果给客户端
            response = {
                "type": "transcription_result",
                "chunk_id": chunk.chunk_id,
                "timestamp": time.time(),
                "processing_time": processing_time,
                "result": transcription_result.to_dict()
            }
            
            # 异步发送
            with self.client_lock:
                if client_id in self.clients:
                    client = self.clients[client_id]
                    asyncio.run_coroutine_threadsafe(
                        client.websocket.send(json.dumps(response)),
                        asyncio.get_event_loop()
                    )
                    client.total_messages_sent += 1
            
            self.stats["total_transcriptions"] += 1
            
            # 可选：触发后续处理（如发送给分身系统）
            self._trigger_downstream_processing(client_id, transcription_result)
            
        except Exception as e:
            logger.error(f"处理音频块失败: {chunk.chunk_id}, 错误: {e}")
    
    def _handle_text_to_speech(self, client_id: str, text: str, voice_name: Optional[str], language: Optional[str]):
        """处理文本转语音请求"""
        if not self.azure_tts_service:
            logger.warning("Azure TTS服务不可用，跳过语音合成")
            return
        
        try:
            logger.info(f"开始语音合成，客户端: {client_id}, 文本长度: {len(text)}")
            
            # 合成语音
            synthesis_result = self.azure_tts_service.synthesize_text(
                text=text,
                voice_name=voice_name,
                language=language
            )
            
            # 发送音频给客户端
            audio_base64 = synthesis_result.get_base64()
            response = {
                "type": "synthesis_result",
                "timestamp": time.time(),
                "result": synthesis_result.to_dict(),
                "audio": audio_base64
            }
            
            with self.client_lock:
                if client_id in self.clients:
                    client = self.clients[client_id]
                    asyncio.run_coroutine_threadsafe(
                        client.websocket.send(json.dumps(response)),
                        asyncio.get_event_loop()
                    )
                    client.total_messages_sent += 1
            
            self.stats["total_syntheses"] += 1
            
            logger.info(f"语音合成完成，客户端: {client_id}, 音频大小: {len(synthesis_result.audio_data)} bytes")
            
        except Exception as e:
            logger.error(f"语音合成失败，客户端: {client_id}, 错误: {e}")
    
    def _trigger_downstream_processing(self, client_id: str, transcription_result):
        """触发下游处理（如发送给分身系统）"""
        # 这里可以集成到现有SellAI系统
        # 例如，将转录文本发送给对应的AI分身进行处理
        logger.debug(f"触发下游处理，客户端: {client_id}, 文本: {transcription_result.text[:50]}...")
        
        # 示例：记录到日志文件
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id,
            "text": transcription_result.text,
            "language": transcription_result.language,
            "confidence": transcription_result.confidence
        }
        
        log_file = "logs/voice_transcriptions.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"写入转录日志失败: {e}")
    
    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态信息"""
        return {
            "service": "实时音频流处理服务器",
            "status": "running" if self.running else "stopped",
            "host": self.host,
            "port": self.port,
            "current_clients": len(self.clients),
            "queue_size": self.audio_queue.qsize(),
            "audio_queue_capacity": self.audio_queue.maxsize,
            "processing_thread_alive": self.processing_thread and self.processing_thread.is_alive(),
            "services": {
                "whisper": self.whisper_service is not None,
                "azure_tts": self.azure_tts_service is not None
            },
            "statistics": self.stats,
            "uptime_seconds": time.time() - self.stats["start_time"],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_client_list(self) -> List[Dict[str, Any]]:
        """获取客户端列表"""
        with self.client_lock:
            return [client.to_dict() for client in self.clients.values()]
    
    def broadcast_message(self, message_type: str, data: Dict[str, Any]):
        """广播消息给所有客户端"""
        with self.client_lock:
            for client in self.clients.values():
                message = {
                    "type": message_type,
                    "timestamp": time.time(),
                    "data": data
                }
                asyncio.run_coroutine_threadsafe(
                    client.websocket.send(json.dumps(message)),
                    asyncio.get_event_loop()
                )
    
    def stop_server(self):
        """停止服务器"""
        logger.info("正在停止音频流服务器...")
        self.running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        logger.info("音频流服务器已停止")


# 客户端类（用于测试和集成）
class AudioStreamClient:
    """音频流客户端"""
    
    def __init__(
        self,
        server_url: str = "ws://localhost:8765",
        client_id: Optional[str] = None
    ):
        self.server_url = server_url
        self.client_id = client_id or f"client_{int(time.time() * 1000)}"
        self.websocket = None
        self.connected = False
        self.message_callbacks = {}
        
    async def connect(self):
        """连接到服务器"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            logger.info(f"客户端 {self.client_id} 连接到服务器 {self.server_url}")
            
            # 启动消息接收循环
            asyncio.create_task(self._receive_messages())
            
            return True
        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            return False
    
    async def send_audio(self, audio_data: bytes, format: str = "pcm_16khz_16bit_mono", duration_ms: float = 3000):
        """发送音频数据到服务器"""
        if not self.connected or not self.websocket:
            raise ConnectionError("客户端未连接")
        
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        message = {
            "type": "audio",
            "client_id": self.client_id,
            "timestamp": time.time(),
            "audio": audio_base64,
            "format": format,
            "duration_ms": duration_ms
        }
        
        await self.websocket.send(json.dumps(message))
        logger.debug(f"发送音频数据，大小: {len(audio_data)} bytes")
    
    async def send_text_to_speech(self, text: str, voice: Optional[str] = None, language: Optional[str] = None):
        """发送文本转语音请求"""
        if not self.connected or not self.websocket:
            raise ConnectionError("客户端未连接")
        
        message = {
            "type": "text_to_speech",
            "client_id": self.client_id,
            "timestamp": time.time(),
            "text": text,
            "voice": voice,
            "language": language
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info(f"发送文本转语音请求，文本长度: {len(text)}")
    
    async def _receive_messages(self):
        """接收服务器消息"""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"与服务器的连接已关闭")
            self.connected = False
    
    async def _handle_message(self, message: str):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            
            # 触发回调函数
            if msg_type in self.message_callbacks:
                for callback in self.message_callbacks[msg_type]:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"消息回调函数执行失败: {e}")
            
            # 特定消息处理
            if msg_type == "welcome":
                logger.info(f"收到欢迎消息: {data}")
            
            elif msg_type == "transcription_result":
                result = data.get("result", {})
                logger.info(f"收到转录结果: {result.get('text', '')[:50]}..., 置信度: {result.get('confidence', 0):.2f}")
            
            elif msg_type == "synthesis_result":
                logger.info(f"收到语音合成结果，音频大小: {data.get('result', {}).get('audio_data_length', 0)} bytes")
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    def register_callback(self, message_type: str, callback: Callable):
        """注册消息回调函数"""
        if message_type not in self.message_callbacks:
            self.message_callbacks[message_type] = []
        self.message_callbacks[message_type].append(callback)
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
        self.connected = False
        logger.info(f"客户端 {self.client_id} 已断开连接")


# 便利函数
def start_audio_stream_server(
    host: str = "0.0.0.0",
    port: int = 8765,
    whisper_model_size: str = "base",
    azure_tts_key: Optional[str] = None,
    azure_tts_region: Optional[str] = None
) -> RealTimeAudioStreamServer:
    """
    启动音频流服务器
    
    Args:
        host: 服务器主机
        port: 服务器端口
        whisper_model_size: Whisper模型大小
        azure_tts_key: Azure TTS密钥
        azure_tts_region: Azure TTS区域
        
    Returns:
        RealTimeAudioStreamServer: 服务器实例
    """
    server = RealTimeAudioStreamServer(
        host=host,
        port=port,
        whisper_model_size=whisper_model_size,
        azure_tts_key=azure_tts_key,
        azure_tts_region=azure_tts_region
    )
    
    # 在后台线程启动服务器
    def run_server():
        asyncio.run(server.start_server())
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 等待服务器启动
    time.sleep(1)
    
    logger.info(f"音频流服务器已启动: {host}:{port}")
    return server


# 测试代码
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="实时音频流处理服务器")
    parser.add_argument("--mode", choices=["server", "client"], default="server", help="运行模式")
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机")
    parser.add_argument("--port", type=int, default=8765, help="服务器端口")
    parser.add_argument("--whisper-model", default="base", help="Whisper模型大小")
    parser.add_argument("--test-audio", help="测试音频文件路径")
    
    args = parser.parse_args()
    
    if args.mode == "server":
        print(f"启动音频流服务器，监听 {args.host}:{args.port}")
        print(f"Whisper模型: {args.whisper_model}")
        
        # 启动服务器
        server = start_audio_stream_server(
            host=args.host,
            port=args.port,
            whisper_model_size=args.whisper_model
        )
        
        try:
            # 保持主线程运行
            while True:
                time.sleep(1)
                # 可选：打印服务器状态
                # print(json.dumps(server.get_server_status(), indent=2))
        except KeyboardInterrupt:
            print("收到停止信号，正在关闭服务器...")
            server.stop_server()
        
    else:
        print("客户端模式暂未实现完整测试")
        print("请使用 --mode server 启动服务器进行测试")