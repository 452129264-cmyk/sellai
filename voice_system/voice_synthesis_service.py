#!/usr/bin/env python3
"""
Azure TTS语音合成服务

此模块提供基于Azure Cognitive Services Text-to-Speech (TTS)的
高质量语音合成服务，支持多种音色、语言和风格选项。

核心功能：
1. 文本转语音合成（支持SSML）
2. 多种音色选择（不同性别、年龄、风格）
3. 语音质量优化（自然度、流畅度）
4. 实时流式合成支持
5. 与现有SellAI系统深度集成
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

# 尝试导入Azure SDK
try:
    import azure.cognitiveservices.speech as speechsdk
    HAS_AZURE_SDK = True
except ImportError:
    HAS_AZURE_SDK = False
    logging.warning("Azure Cognitive Services SDK未安装，语音合成功能将受限")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VoiceGender(Enum):
    """语音性别"""
    MALE = "Male"
    FEMALE = "Female"
    NEUTRAL = "Neutral"


class VoiceStyle(Enum):
    """语音风格"""
    NEUTRAL = "neutral"
    CHEERFUL = "cheerful"
    SAD = "sad"
    ANGRY = "angry"
    FRIENDLY = "friendly"
    CALM = "calm"
    EXCITED = "excited"
    EMPATHETIC = "empathetic"


class SynthesisResult:
    """语音合成结果类"""
    
    def __init__(
        self,
        audio_data: bytes,
        text: str,
        voice_name: str,
        language: str,
        duration_seconds: float,
        processing_time_seconds: float,
        audio_format: str = "wav",
        sample_rate: int = 16000
    ):
        self.audio_data = audio_data
        self.text = text
        self.voice_name = voice_name
        self.language = language
        self.duration_seconds = duration_seconds
        self.processing_time_seconds = processing_time_seconds
        self.audio_format = audio_format
        self.sample_rate = sample_rate
        
    def save_to_file(self, file_path: str):
        """保存音频到文件"""
        with open(file_path, 'wb') as f:
            f.write(self.audio_data)
        logger.info(f"音频已保存到: {file_path}")
    
    def get_base64(self) -> str:
        """获取Base64编码的音频数据"""
        return base64.b64encode(self.audio_data).decode('utf-8')
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "text": self.text,
            "voice_name": self.voice_name,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "processing_time_seconds": self.processing_time_seconds,
            "audio_format": self.audio_format,
            "sample_rate": self.sample_rate,
            "audio_data_length": len(self.audio_data)
        }
    
    def __str__(self) -> str:
        return f"SynthesisResult(text={self.text[:50]}..., voice={self.voice_name}, duration={self.duration_seconds:.2f}s)"


class AzureTTSService:
    """Azure TTS语音合成服务主类"""
    
    def __init__(
        self,
        subscription_key: Optional[str] = None,
        region: Optional[str] = None,
        default_voice: str = "en-US-JennyNeural",
        default_language: str = "en-US",
        audio_format: str = "Audio16Khz32BitRateMonoMp3"
    ):
        """
        初始化Azure TTS服务
        
        Args:
            subscription_key: Azure订阅密钥（可以从环境变量读取）
            region: Azure区域（如 "eastus"）
            default_voice: 默认语音名称
            default_language: 默认语言代码
            audio_format: 音频输出格式
        """
        if not HAS_AZURE_SDK:
            raise ImportError("Azure Cognitive Services SDK未安装，请运行: pip install azure-cognitiveservices-speech")
        
        # 从参数或环境变量获取配置
        self.subscription_key = subscription_key or os.getenv("AZURE_SPEECH_KEY")
        self.region = region or os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.default_voice = default_voice
        self.default_language = default_language
        self.audio_format = audio_format
        
        if not self.subscription_key:
            raise ValueError("Azure订阅密钥未提供，请设置subscription_key参数或AZURE_SPEECH_KEY环境变量")
        
        if not self.region:
            raise ValueError("Azure区域未提供，请设置region参数或AZURE_SPEECH_REGION环境变量")
        
        # 创建语音配置
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.subscription_key,
            region=self.region
        )
        
        # 设置音频格式
        if audio_format == "Raw16Khz16BitMonoPcm":
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
            )
        elif audio_format == "Audio16Khz32BitRateMonoMp3":
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32BitRateMonoMp3
            )
        elif audio_format == "Audio16Khz64BitRateMonoMp3":
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio16Khz64BitRateMonoMp3
            )
        elif audio_format == "Audio16Khz128BitRateMonoMp3":
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128BitRateMonoMp3
            )
        else:
            # 默认为16kHz 32kbps MP3
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32BitRateMonoMp3
            )
        
        # 性能统计
        self.stats = {
            "total_syntheses": 0,
            "total_text_characters": 0,
            "total_audio_seconds": 0.0,
            "total_processing_seconds": 0.0,
            "avg_processing_time_per_character": 0.0
        }
        
        # 预定义语音列表
        self._predefined_voices = self._load_predefined_voices()
        
        logger.info(f"Azure TTS服务初始化完成 (区域: {self.region}, 默认语音: {default_voice})")
    
    def synthesize_text(
        self,
        text: str,
        voice_name: Optional[str] = None,
        language: Optional[str] = None,
        style: Optional[VoiceStyle] = None,
        speaking_rate: Optional[float] = None,
        pitch: Optional[float] = None
    ) -> SynthesisResult:
        """
        合成文本为语音
        
        Args:
            text: 要合成的文本
            voice_name: 语音名称（如 "en-US-JennyNeural"）
            language: 语言代码（如 "en-US"）
            style: 语音风格
            speaking_rate: 语速（-50%到+100%）
            pitch: 音高（-50%到+50%）
            
        Returns:
            SynthesisResult: 合成结果
        """
        if not text or not text.strip():
            raise ValueError("文本不能为空")
        
        logger.info(f"开始语音合成，文本长度: {len(text)} 字符，语音: {voice_name or self.default_voice}")
        start_time = time.time()
        
        try:
            # 设置语音
            voice = voice_name or self.default_voice
            lang = language or self.default_language
            
            # 创建SSML（支持更多控制）
            ssml = self._create_ssml(
                text=text,
                voice_name=voice,
                language=lang,
                style=style,
                speaking_rate=speaking_rate,
                pitch=pitch
            )
            
            # 创建合成器
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None  # 输出到内存
            )
            
            # 执行合成
            result = synthesizer.speak_ssml_async(ssml).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # 获取音频数据
                audio_data = result.audio_data
                
                # 计算处理时间
                processing_time = time.time() - start_time
                
                # 估计音频时长（MP3格式，32kbps）
                # 32kbps = 4000 bytes/s，近似计算
                duration = len(audio_data) / 4000.0 if self.audio_format.startswith("Audio16Khz") else 0.0
                
                synthesis_result = SynthesisResult(
                    audio_data=audio_data,
                    text=text,
                    voice_name=voice,
                    language=lang,
                    duration_seconds=duration,
                    processing_time_seconds=processing_time,
                    audio_format="mp3" if "Mp3" in self.audio_format else "wav",
                    sample_rate=16000
                )
                
                # 更新统计信息
                self._update_stats(len(text), processing_time, duration)
                
                logger.info(f"语音合成完成，文本: {text[:50]}..., "
                          f"处理时间: {processing_time:.2f}s, 估计时长: {duration:.2f}s")
                
                return synthesis_result
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                error_msg = f"合成取消: {cancellation_details.reason}"
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    error_msg += f", 错误详情: {cancellation_details.error_details}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            else:
                error_msg = f"合成失败，原因: {result.reason}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            raise
    
    def synthesize_to_file(
        self,
        text: str,
        output_file_path: str,
        voice_name: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> SynthesisResult:
        """
        合成文本为语音并保存到文件
        
        Args:
            text: 要合成的文本
            output_file_path: 输出文件路径
            voice_name: 语音名称
            language: 语言代码
            **kwargs: 其他参数（style, speaking_rate, pitch）
            
        Returns:
            SynthesisResult: 合成结果
        """
        logger.info(f"合成语音到文件: {output_file_path}")
        
        # 执行合成
        result = self.synthesize_text(
            text=text,
            voice_name=voice_name,
            language=language,
            **kwargs
        )
        
        # 保存到文件
        result.save_to_file(output_file_path)
        
        return result
    
    def synthesize_realtime_stream(
        self,
        text_stream: Union[str, List[str]],
        voice_name: Optional[str] = None,
        language: Optional[str] = None,
        callback: Optional[callable] = None
    ) -> List[SynthesisResult]:
        """
        实时流式语音合成（分批处理长文本）
        
        Args:
            text_stream: 文本流（字符串或字符串列表）
            voice_name: 语音名称
            language: 语言代码
            callback: 每块合成完成后的回调函数
            
        Returns:
            List[SynthesisResult]: 所有块的合成结果列表
        """
        logger.info(f"开始实时流式语音合成")
        
        # 如果是字符串，按句子分割
        if isinstance(text_stream, str):
            # 简单按标点分割（实际应用中可能需要更复杂的分割）
            import re
            sentences = re.split(r'(?<=[.!?])\s+', text_stream)
            if not sentences or sentences == ['']:
                sentences = [text_stream]
        else:
            sentences = text_stream
        
        results = []
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            logger.debug(f"合成分块 {i+1}/{len(sentences)}: {sentence[:50]}...")
            
            # 合成当前句子
            chunk_result = self.synthesize_text(
                text=sentence,
                voice_name=voice_name,
                language=language
            )
            results.append(chunk_result)
            
            # 调用回调函数
            if callback:
                callback(chunk_result)
            
            time.sleep(0.1)  # 避免过快请求
        
        logger.info(f"实时流式语音合成完成，分块数: {len(results)}")
        return results
    
    def get_available_voices(
        self,
        language_filter: Optional[str] = None,
        gender_filter: Optional[VoiceGender] = None
    ) -> List[Dict[str, Any]]:
        """
        获取可用的语音列表
        
        Args:
            language_filter: 语言代码过滤（如 "en-US"）
            gender_filter: 性别过滤
            
        Returns:
            List[Dict]: 语音信息列表
        """
        voices = self._predefined_voices
        
        # 应用过滤器
        if language_filter:
            voices = [v for v in voices if language_filter in v["locale"]]
        
        if gender_filter:
            voices = [v for v in voices if v["gender"] == gender_filter.value]
        
        return voices
    
    def get_recommended_voices(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取推荐语音（按场景分类）"""
        return {
            "conversational": [
                {"name": "en-US-JennyNeural", "description": "自然、友好的女性声音，适合一般对话"},
                {"name": "en-US-GuyNeural", "description": "温暖、亲切的男性声音，适合客服场景"},
                {"name": "zh-CN-XiaoxiaoNeural", "description": "清晰、甜美的中文女声，适合产品介绍"}
            ],
            "professional": [
                {"name": "en-US-AriaNeural", "description": "专业、自信的女性声音，适合商业演示"},
                {"name": "en-US-DavisNeural", "description": "权威、稳重的男性声音，适合新闻播报"},
                {"name": "zh-CN-YunxiNeural", "description": "正式、庄重的中文男声，适合官方公告"}
            ],
            "creative": [
                {"name": "en-US-AmberNeural", "description": "活泼、有表现力的女性声音，适合儿童内容"},
                {"name": "en-US-BrianNeural", "description": "幽默、风趣的男性声音，适合娱乐内容"},
                {"name": "zh-CN-XiaoyiNeural", "description": "温柔、亲切的中文女声，适合情感内容"}
            ]
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态信息"""
        return {
            "service": "Azure TTS语音合成服务",
            "status": "running" if HAS_AZURE_SDK else "error",
            "region": self.region,
            "default_voice": self.default_voice,
            "default_language": self.default_language,
            "audio_format": self.audio_format,
            "has_azure_sdk": HAS_AZURE_SDK,
            "statistics": self.stats,
            "available_voices_count": len(self._predefined_voices),
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_ssml(
        self,
        text: str,
        voice_name: str,
        language: str,
        style: Optional[VoiceStyle] = None,
        speaking_rate: Optional[float] = None,
        pitch: Optional[float] = None
    ) -> str:
        """创建SSML标记"""
        ssml_parts = []
        ssml_parts.append(f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}">')
        ssml_parts.append(f'<voice name="{voice_name}">')
        
        # 添加风格和音调控制
        prosody_parts = []
        if style:
            ssml_parts.append(f'<mstts:express-as style="{style.value}">')
        
        if speaking_rate is not None or pitch is not None:
            rate_attr = f' rate="{speaking_rate}%"' if speaking_rate is not None else ""
            pitch_attr = f' pitch="{pitch}%"' if pitch is not None else ""
            ssml_parts.append(f'<prosody{rate_attr}{pitch_attr}>')
            ssml_parts.append(text)
            ssml_parts.append('</prosody>')
        else:
            ssml_parts.append(text)
        
        if style:
            ssml_parts.append('</mstts:express-as>')
        
        ssml_parts.append('</voice>')
        ssml_parts.append('</speak>')
        
        return ''.join(ssml_parts)
    
    def _load_predefined_voices(self) -> List[Dict[str, Any]]:
        """加载预定义的语音列表"""
        # Azure TTS支持的部分常用语音
        voices = [
            # 英语（美国）
            {"name": "en-US-JennyNeural", "locale": "en-US", "gender": "Female", "description": "自然女性声音"},
            {"name": "en-US-GuyNeural", "locale": "en-US", "gender": "Male", "description": "温暖男性声音"},
            {"name": "en-US-AriaNeural", "locale": "en-US", "gender": "Female", "description": "专业女性声音"},
            {"name": "en-US-DavisNeural", "locale": "en-US", "gender": "Male", "description": "权威男性声音"},
            {"name": "en-US-AmberNeural", "locale": "en-US", "gender": "Female", "description": "活泼女性声音"},
            {"name": "en-US-BrianNeural", "locale": "en-US", "gender": "Male", "description": "幽默男性声音"},
            
            # 中文（普通话）
            {"name": "zh-CN-XiaoxiaoNeural", "locale": "zh-CN", "gender": "Female", "description": "甜美女性声音"},
            {"name": "zh-CN-YunxiNeural", "locale": "zh-CN", "gender": "Male", "description": "正式男性声音"},
            {"name": "zh-CN-YunxiaNeural", "locale": "zh-CN", "gender": "Male", "description": "温暖男性声音"},
            {"name": "zh-CN-YunyangNeural", "locale": "zh-CN", "gender": "Male", "description": "叙事男性声音"},
            {"name": "zh-CN-XiaoyiNeural", "locale": "zh-CN", "gender": "Female", "description": "温柔女性声音"},
            {"name": "zh-CN-XiaomoNeural", "locale": "zh-CN", "gender": "Female", "description": "活泼女性声音"},
            
            # 英语（英国）
            {"name": "en-GB-SoniaNeural", "locale": "en-GB", "gender": "Female", "description": "英式女性声音"},
            {"name": "en-GB-RyanNeural", "locale": "en-GB", "gender": "Male", "description": "英式男性声音"},
            
            # 日语
            {"name": "ja-JP-NanamiNeural", "locale": "ja-JP", "gender": "Female", "description": "日式女性声音"},
            {"name": "ja-JP-KeitaNeural", "locale": "ja-JP", "gender": "Male", "description": "日式男性声音"},
            
            # 韩语
            {"name": "ko-KR-SunHiNeural", "locale": "ko-KR", "gender": "Female", "description": "韩式女性声音"},
            {"name": "ko-KR-InJoonNeural", "locale": "ko-KR", "gender": "Male", "description": "韩式男性声音"},
            
            # 法语
            {"name": "fr-FR-DeniseNeural", "locale": "fr-FR", "gender": "Female", "description": "法式女性声音"},
            {"name": "fr-FR-HenriNeural", "locale": "fr-FR", "gender": "Male", "description": "法式男性声音"},
            
            # 德语
            {"name": "de-DE-KatjaNeural", "locale": "de-DE", "gender": "Female", "description": "德式女性声音"},
            {"name": "de-DE-ConradNeural", "locale": "de-DE", "gender": "Male", "description": "德式男性声音"},
            
            # 西班牙语
            {"name": "es-ES-ElviraNeural", "locale": "es-ES", "gender": "Female", "description": "西式女性声音"},
            {"name": "es-ES-AlvaroNeural", "locale": "es-ES", "gender": "Male", "description": "西式男性声音"},
        ]
        
        return voices
    
    def _update_stats(
        self,
        text_length: int,
        processing_time: float,
        audio_duration: float
    ):
        """更新统计信息"""
        self.stats["total_syntheses"] += 1
        self.stats["total_text_characters"] += text_length
        self.stats["total_audio_seconds"] += audio_duration
        self.stats["total_processing_seconds"] += processing_time
        
        # 更新平均每字符处理时间
        if text_length > 0:
            current_avg = self.stats["avg_processing_time_per_character"]
            new_value = processing_time / text_length
            
            if self.stats["total_syntheses"] == 1:
                self.stats["avg_processing_time_per_character"] = new_value
            else:
                # 使用指数移动平均
                alpha = 0.1
                self.stats["avg_processing_time_per_character"] = current_avg * (1 - alpha) + new_value * alpha


# 便利函数
def create_azure_tts_service(
    subscription_key: Optional[str] = None,
    region: Optional[str] = None,
    default_voice: str = "en-US-JennyNeural"
) -> AzureTTSService:
    """
    创建Azure TTS服务实例
    
    Args:
        subscription_key: Azure订阅密钥
        region: Azure区域
        default_voice: 默认语音名称
        
    Returns:
        AzureTTSService: TTS服务实例
    """
    return AzureTTSService(
        subscription_key=subscription_key,
        region=region,
        default_voice=default_voice
    )


# 测试代码
if __name__ == "__main__":
    # 测试服务初始化（需要环境变量）
    try:
        # 尝试从环境变量获取密钥
        subscription_key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        
        if subscription_key:
            service = create_azure_tts_service(
                subscription_key=subscription_key,
                region=region
            )
            print("服务状态:", json.dumps(service.get_service_status(), indent=2, ensure_ascii=False))
            
            # 测试可用语音
            voices = service.get_available_voices()
            print(f"可用语音数量: {len(voices)}")
            
            # 测试推荐语音
            recommended = service.get_recommended_voices()
            print(f"推荐语音分类: {list(recommended.keys())}")
            
            print("Azure TTS服务测试通过！")
        else:
            print("警告: 未设置AZURE_SPEECH_KEY环境变量，跳过实际合成测试")
            print("服务模块加载成功，功能代码正常")
            
    except Exception as e:
        print(f"服务测试失败: {e}")
        import traceback
        traceback.print_exc()