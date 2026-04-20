#!/usr/bin/env python3
"""
Whisper语音识别服务

此模块提供基于OpenAI Whisper的实时语音识别服务，支持多语言转录、
实时音频流处理，并与现有SellAI分身系统深度集成。

核心功能：
1. 音频文件转录（WAV、MP3、M4A等格式）
2. 实时音频流转录（WebSocket/HTTP流）
3. 多语言支持（英语、中文等，自动检测）
4. 识别准确率优化与延迟控制
"""

import os
import io
import json
import time
import logging
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, BinaryIO
from enum import Enum
import base64
import numpy as np

# 尝试导入Whisper相关库
try:
    import whisper
    import whisper.transcribe
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    logging.warning("Whisper库未安装，语音识别功能将受限")

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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    """支持的音频格式"""
    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    OGG = "ogg"
    PCM = "pcm"  # 原始PCM数据


class TranscriptionResult:
    """转录结果类"""
    
    def __init__(
        self,
        text: str,
        language: str,
        confidence: float,
        duration_seconds: float,
        processing_time_seconds: float,
        segments: Optional[List[Dict]] = None
    ):
        self.text = text
        self.language = language
        self.confidence = confidence
        self.duration_seconds = duration_seconds
        self.processing_time_seconds = processing_time_seconds
        self.segments = segments or []
        
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "text": self.text,
            "language": self.language,
            "confidence": self.confidence,
            "duration_seconds": self.duration_seconds,
            "processing_time_seconds": self.processing_time_seconds,
            "segments": self.segments
        }
    
    def __str__(self) -> str:
        return f"TranscriptionResult(text={self.text[:50]}..., language={self.language}, confidence={self.confidence:.2f})"


class WhisperRecognitionService:
    """Whisper语音识别服务主类"""
    
    def __init__(
        self,
        model_size: str = "base",
        device: Optional[str] = None,
        language: Optional[str] = None,
        temperature: float = 0.0,
        beam_size: int = 5,
        best_of: int = 5
    ):
        """
        初始化Whisper识别服务
        
        Args:
            model_size: Whisper模型大小 (tiny, base, small, medium, large)
            device: 运行设备 (cpu, cuda)
            language: 目标语言代码 (en, zh, ja等)，None为自动检测
            temperature: 采样温度，影响随机性
            beam_size: Beam搜索大小
            best_of: 候选数量
        """
        if not HAS_WHISPER:
            raise ImportError("Whisper库未安装，请运行: pip install openai-whisper")
        
        self.model_size = model_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.language = language
        self.temperature = temperature
        self.beam_size = beam_size
        self.best_of = best_of
        
        # 延迟加载模型
        self._model = None
        self._model_lock = threading.Lock()
        
        # 性能统计
        self.stats = {
            "total_transcriptions": 0,
            "total_audio_seconds": 0.0,
            "total_processing_seconds": 0.0,
            "avg_confidence": 0.0
        }
        
        logger.info(f"Whisper识别服务初始化完成 (模型: {model_size}, 设备: {self.device})")
    
    @property
    def model(self):
        """延迟加载模型（线程安全）"""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    logger.info(f"正在加载Whisper模型: {self.model_size}")
                    start_time = time.time()
                    
                    try:
                        import torch
                        # 设置Whisper选项
                        model = whisper.load_model(
                            self.model_size,
                            device=self.device
                        )
                        self._model = model
                        load_time = time.time() - start_time
                        logger.info(f"Whisper模型加载完成，耗时: {load_time:.2f}秒")
                    except Exception as e:
                        logger.error(f"加载Whisper模型失败: {e}")
                        raise
        return self._model
    
    def transcribe_audio_file(
        self,
        audio_file_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        转录音频文件
        
        Args:
            audio_file_path: 音频文件路径
            language: 目标语言，None使用实例默认或自动检测
            **kwargs: 传递给Whisper转录函数的额外参数
            
        Returns:
            TranscriptionResult: 转录结果
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_file_path}")
        
        logger.info(f"开始转录音频文件: {audio_file_path}")
        start_time = time.time()
        
        try:
            # 获取音频时长
            duration = self._get_audio_duration(audio_file_path)
            
            # 执行转录
            transcription_options = {
                "language": language or self.language,
                "temperature": kwargs.get("temperature", self.temperature),
                "beam_size": kwargs.get("beam_size", self.beam_size),
                "best_of": kwargs.get("best_of", self.best_of),
                "task": "transcribe"
            }
            
            # 清理None值
            transcription_options = {k: v for k, v in transcription_options.items() if v is not None}
            
            result = self.model.transcribe(audio_file_path, **transcription_options)
            
            processing_time = time.time() - start_time
            
            # 计算平均置信度
            segments = result.get("segments", [])
            avg_confidence = np.mean([seg.get("confidence", 0.9) for seg in segments]) if segments else 0.9
            
            transcription_result = TranscriptionResult(
                text=result["text"].strip(),
                language=result.get("language", "unknown"),
                confidence=float(avg_confidence),
                duration_seconds=duration,
                processing_time_seconds=processing_time,
                segments=segments
            )
            
            # 更新统计信息
            self._update_stats(duration, processing_time, avg_confidence)
            
            logger.info(f"音频文件转录完成: {audio_file_path}, 时长: {duration:.2f}s, "
                       f"处理时间: {processing_time:.2f}s, 置信度: {avg_confidence:.2f}")
            
            return transcription_result
            
        except Exception as e:
            logger.error(f"转录音频文件失败: {audio_file_path}, 错误: {e}")
            raise
    
    def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        audio_format: AudioFormat = AudioFormat.WAV,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        转录音频字节数据
        
        Args:
            audio_bytes: 音频字节数据
            audio_format: 音频格式
            sample_rate: 采样率（Hz）
            language: 目标语言
            **kwargs: 额外参数
            
        Returns:
            TranscriptionResult: 转录结果
        """
        logger.info(f"开始转录音频字节数据，长度: {len(audio_bytes)} 字节，格式: {audio_format.value}")
        start_time = time.time()
        
        try:
            # 将音频字节保存到临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=f".{audio_format.value}", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
            
            # 使用文件转录方法
            result = self.transcribe_audio_file(tmp_file_path, language, **kwargs)
            
            # 清理临时文件
            try:
                os.unlink(tmp_file_path)
            except:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"转录音频字节数据失败: {e}")
            raise
    
    def transcribe_realtime_stream(
        self,
        audio_stream: BinaryIO,
        chunk_duration_ms: int = 3000,
        language: Optional[str] = None,
        callback: Optional[callable] = None
    ) -> List[TranscriptionResult]:
        """
        实时音频流转录（分批处理）
        
        Args:
            audio_stream: 音频流对象
            chunk_duration_ms: 分块时长（毫秒）
            language: 目标语言
            callback: 每块转录完成后的回调函数
            
        Returns:
            List[TranscriptionResult]: 所有块的转录结果列表
        """
        logger.info(f"开始实时音频流转录，分块时长: {chunk_duration_ms}ms")
        
        if not HAS_PYDUB:
            raise ImportError("pydub库未安装，实时流处理需要: pip install pydub")
        
        results = []
        
        try:
            # 读取音频流并分块处理
            audio_segment = AudioSegment.from_file(audio_stream)
            duration_ms = len(audio_segment)
            
            for start_ms in range(0, duration_ms, chunk_duration_ms):
                end_ms = min(start_ms + chunk_duration_ms, duration_ms)
                chunk = audio_segment[start_ms:end_ms]
                
                # 将分块保存到临时文件
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    chunk.export(tmp_file.name, format="wav")
                    tmp_file_path = tmp_file.name
                
                # 转录分块
                chunk_result = self.transcribe_audio_file(tmp_file_path, language)
                results.append(chunk_result)
                
                # 调用回调函数
                if callback:
                    callback(chunk_result)
                
                # 清理临时文件
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                
                logger.debug(f"实时流分块转录完成: {start_ms/1000:.1f}s-{end_ms/1000:.1f}s, "
                           f"文本: {chunk_result.text[:50]}...")
            
            logger.info(f"实时音频流转录完成，总时长: {duration_ms/1000:.2f}s, 分块数: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"实时音频流转录失败: {e}")
            raise
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """获取支持的语言列表"""
        # Whisper支持的语言代码和名称映射
        language_map = {
            "en": "English",
            "zh": "Chinese",
            "de": "German",
            "es": "Spanish",
            "ru": "Russian",
            "ko": "Korean",
            "fr": "French",
            "ja": "Japanese",
            "pt": "Portuguese",
            "tr": "Turkish",
            "pl": "Polish",
            "ca": "Catalan",
            "nl": "Dutch",
            "ar": "Arabic",
            "sv": "Swedish",
            "it": "Italian",
            "id": "Indonesian",
            "hi": "Hindi",
            "fi": "Finnish",
            "vi": "Vietnamese",
            "he": "Hebrew",
            "uk": "Ukrainian",
            "el": "Greek",
            "ms": "Malay",
            "cs": "Czech",
            "ro": "Romanian",
            "da": "Danish",
            "hu": "Hungarian",
            "ta": "Tamil",
            "no": "Norwegian",
            "th": "Thai",
            "ur": "Urdu",
            "hr": "Croatian",
            "bg": "Bulgarian",
            "lt": "Lithuanian",
            "la": "Latin",
            "mi": "Maori",
            "ml": "Malayalam",
            "cy": "Welsh",
            "sk": "Slovak",
            "te": "Telugu",
            "fa": "Persian",
            "lv": "Latvian",
            "bn": "Bengali",
            "sr": "Serbian",
            "az": "Azerbaijani",
            "sl": "Slovenian",
            "kn": "Kannada",
            "et": "Estonian",
            "mk": "Macedonian",
            "br": "Breton",
            "eu": "Basque",
            "is": "Icelandic",
            "hy": "Armenian",
            "ne": "Nepali",
            "mn": "Mongolian",
            "bs": "Bosnian",
            "kk": "Kazakh",
            "sq": "Albanian",
            "sw": "Swahili",
            "gl": "Galician",
            "mr": "Marathi",
            "pa": "Punjabi",
            "si": "Sinhala",
            "km": "Khmer",
            "sn": "Shona",
            "yo": "Yoruba",
            "so": "Somali",
            "af": "Afrikaans",
            "oc": "Occitan",
            "ka": "Georgian",
            "be": "Belarusian",
            "tg": "Tajik",
            "sd": "Sindhi",
            "gu": "Gujarati",
            "am": "Amharic",
            "yi": "Yiddish",
            "lo": "Lao",
            "uz": "Uzbek",
            "fo": "Faroese",
            "ht": "Haitian Creole",
            "ps": "Pashto",
            "tk": "Turkmen",
            "nn": "Nynorsk",
            "mt": "Maltese",
            "sa": "Sanskrit",
            "lb": "Luxembourgish",
            "my": "Myanmar",
            "bo": "Tibetan",
            "tl": "Tagalog",
            "mg": "Malagasy",
            "as": "Assamese",
            "tt": "Tatar",
            "haw": "Hawaiian",
            "ln": "Lingala",
            "ha": "Hausa",
            "ba": "Bashkir",
            "jw": "Javanese",
            "su": "Sundanese",
        }
        
        return [{"code": code, "name": name} for code, name in language_map.items()]
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态信息"""
        return {
            "service": "Whisper语音识别服务",
            "status": "running" if HAS_WHISPER else "error",
            "model_size": self.model_size,
            "device": self.device,
            "language": self.language,
            "has_whisper": HAS_WHISPER,
            "has_pydub": HAS_PYDUB,
            "has_soundfile": HAS_SOUNDFILE,
            "statistics": self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_audio_duration(self, audio_file_path: str) -> float:
        """获取音频文件时长（秒）"""
        try:
            if HAS_PYDUB:
                audio = AudioSegment.from_file(audio_file_path)
                return len(audio) / 1000.0  # 转换为秒
            elif HAS_SOUNDFILE:
                info = sf.info(audio_file_path)
                return info.duration
            else:
                # 简单估计：对于WAV文件，使用文件大小估计
                if audio_file_path.lower().endswith('.wav'):
                    import wave
                    with wave.open(audio_file_path, 'rb') as wav_file:
                        frames = wav_file.getnframes()
                        rate = wav_file.getframerate()
                        return frames / float(rate)
                return 0.0
        except Exception as e:
            logger.warning(f"获取音频时长失败: {e}")
            return 0.0
    
    def _update_stats(
        self,
        duration: float,
        processing_time: float,
        confidence: float
    ):
        """更新统计信息"""
        self.stats["total_transcriptions"] += 1
        self.stats["total_audio_seconds"] += duration
        self.stats["total_processing_seconds"] += processing_time
        
        # 更新平均置信度（加权平均）
        total_transcriptions = self.stats["total_transcriptions"]
        old_avg = self.stats["avg_confidence"]
        if total_transcriptions == 1:
            self.stats["avg_confidence"] = confidence
        else:
            # 使用指数移动平均
            alpha = 0.1
            self.stats["avg_confidence"] = old_avg * (1 - alpha) + confidence * alpha


# 便利函数
def create_whisper_service(
    model_size: str = "base",
    device: Optional[str] = None,
    language: Optional[str] = None
) -> WhisperRecognitionService:
    """
    创建Whisper识别服务实例
    
    Args:
        model_size: 模型大小
        device: 运行设备
        language: 目标语言
        
    Returns:
        WhisperRecognitionService: 识别服务实例
    """
    return WhisperRecognitionService(
        model_size=model_size,
        device=device,
        language=language
    )


# 测试代码
if __name__ == "__main__":
    # 测试服务初始化
    try:
        service = create_whisper_service(model_size="base")
        print("服务状态:", json.dumps(service.get_service_status(), indent=2, ensure_ascii=False))
        
        # 测试支持的语言
        languages = service.get_supported_languages()
        print(f"支持 {len(languages)} 种语言")
        
        print("Whisper语音识别服务测试通过！")
        
    except Exception as e:
        print(f"服务测试失败: {e}")
        import traceback
        traceback.print_exc()