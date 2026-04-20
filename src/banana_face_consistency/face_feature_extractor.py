"""
人脸特征提取器
基于深度学习的人脸特征提取与绑定系统
"""

import os
import numpy as np
import cv2
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import pickle
import hashlib
from datetime import datetime

from .config import face_config

logger = logging.getLogger(__name__)


@dataclass
class FaceDetectionResult:
    """人脸检测结果"""
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    landmarks: np.ndarray  # 5个关键点 [x1, y1, x2, y2, ...]
    confidence: float
    quality_score: float = 0.0
    pose_angles: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # 俯仰, 偏航, 翻滚


@dataclass
class FaceEmbedding:
    """人脸特征向量"""
    embedding: np.ndarray  # 特征向量 [embedding_dim]
    face_id: str  # 人脸ID
    detection_result: FaceDetectionResult
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {
                "extraction_time": datetime.now().isoformat(),
                "model_version": "arcface_v1.0",
                "embedding_dim": len(self.embedding)
            }


class FaceFeatureExtractor:
    """人脸特征提取器"""
    
    def __init__(self, config: FaceConsistencyConfig = None):
        self.config = config or face_config
        self.detector = self._load_face_detector()
        self.recognizer = self._load_face_recognizer()
        self.embedding_dim = self.config.embedding_dim
        logger.info(f"人脸特征提取器初始化完成，设备: {self.config.device}")
    
    def _load_face_detector(self):
        """加载人脸检测器（模拟实现）"""
        # 实际部署时加载真实模型，如RetinaFace、MTCNN等
        logger.info(f"加载人脸检测器: {self.config.face_detector_model}")
        # 返回模拟检测器
        return MockFaceDetector(confidence_threshold=self.config.detection_confidence)
    
    def _load_face_recognizer(self):
        """加载人脸识别器（模拟实现）"""
        # 实际部署时加载真实模型，如ArcFace、FaceNet等
        logger.info(f"加载人脸识别器: {self.config.recognition_model}")
        # 返回模拟识别器
        return MockFaceRecognizer(embedding_dim=self.config.embedding_dim)
    
    def detect_faces(self, image: np.ndarray) -> List[FaceDetectionResult]:
        """
        检测图像中的人脸
        
        Args:
            image: RGB或BGR图像
            
        Returns:
            人脸检测结果列表
        """
        try:
            # 转换图像格式
            if len(image.shape) == 2:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            else:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 调用检测器
            detection_results = self.detector.detect(image_rgb)
            
            # 质量过滤
            filtered_results = []
            for result in detection_results:
                # 检查置信度
                if result.confidence < self.config.detection_confidence:
                    continue
                
                # 检查人脸尺寸
                bbox = result.bbox
                face_width = bbox[2] - bbox[0]
                face_height = bbox[3] - bbox[1]
                if face_width < self.config.min_face_size or face_height < self.config.min_face_size:
                    continue
                
                # 计算质量分数
                quality_score = self._calculate_face_quality(result, image_rgb)
                result.quality_score = quality_score
                
                # 检查质量分数
                if self.config.quality_check_enabled and quality_score < self.config.min_face_quality_score:
                    continue
                
                filtered_results.append(result)
            
            logger.info(f"检测到 {len(filtered_results)} 张人脸 (过滤前: {len(detection_results)})")
            return filtered_results
            
        except Exception as e:
            logger.error(f"人脸检测失败: {str(e)}")
            return []
    
    def extract_embedding(self, image: np.ndarray, 
                         detection_result: FaceDetectionResult) -> FaceEmbedding:
        """
        提取单张人脸的特征向量
        
        Args:
            image: 原始图像
            detection_result: 人脸检测结果
            
        Returns:
            人脸特征向量
        """
        try:
            # 提取人脸区域
            x1, y1, x2, y2 = detection_result.bbox
            face_region = image[y1:y2, x1:x2]
            
            if face_region.size == 0:
                raise ValueError("人脸区域为空")
            
            # 预处理人脸图像
            processed_face = self._preprocess_face(face_region)
            
            # 提取特征向量
            embedding = self.recognizer.extract(processed_face)
            
            # 生成人脸ID
            face_id = self._generate_face_id(embedding, detection_result)
            
            # 创建特征向量对象
            face_embedding = FaceEmbedding(
                embedding=embedding,
                face_id=face_id,
                detection_result=detection_result,
                metadata={
                    "extraction_time": datetime.now().isoformat(),
                    "model_version": self.config.recognition_model,
                    "image_shape": image.shape,
                    "bbox": detection_result.bbox,
                    "quality_score": detection_result.quality_score
                }
            )
            
            logger.info(f"特征提取完成: {face_id}, 维度: {len(embedding)}")
            return face_embedding
            
        except Exception as e:
            logger.error(f"特征提取失败: {str(e)}")
            # 返回空特征向量
            return FaceEmbedding(
                embedding=np.zeros(self.embedding_dim),
                face_id="error",
                detection_result=detection_result
            )
    
    def extract_from_image(self, image: np.ndarray) -> List[FaceEmbedding]:
        """
        从图像中提取所有人脸的特征向量
        
        Args:
            image: 原始图像
            
        Returns:
            人脸特征向量列表
        """
        # 检测人脸
        faces = self.detect_faces(image)
        
        # 提取特征
        embeddings = []
        for face in faces:
            embedding = self.extract_embedding(image, face)
            embeddings.append(embedding)
        
        return embeddings
    
    def _preprocess_face(self, face_image: np.ndarray) -> np.ndarray:
        """预处理人脸图像"""
        # 调整大小到模型输入尺寸
        target_size = (112, 112)  # ArcFace标准输入尺寸
        resized = cv2.resize(face_image, target_size)
        
        # 归一化
        normalized = resized.astype(np.float32) / 255.0
        
        # 标准化
        mean = [0.5, 0.5, 0.5]
        std = [0.5, 0.5, 0.5]
        normalized = (normalized - mean) / std
        
        # 转换为CHW格式
        if len(normalized.shape) == 3:
            normalized = np.transpose(normalized, (2, 0, 1))
        
        return normalized
    
    def _calculate_face_quality(self, detection_result: FaceDetectionResult, 
                               image: np.ndarray) -> float:
        """计算人脸质量分数"""
        quality = detection_result.confidence
        
        # 基于姿态的质量调整
        pose_angles = detection_result.pose_angles
        pitch, yaw, roll = abs(pose_angles[0]), abs(pose_angles[1]), abs(pose_angles[2])
        
        # 正面人脸分数更高
        pose_penalty = (pitch + yaw + roll) / 180.0
        quality *= (1.0 - pose_penalty * 0.3)
        
        # 基于清晰度的质量检查（模拟）
        bbox = detection_result.bbox
        x1, y1, x2, y2 = bbox
        face_region = image[y1:y2, x1:x2]
        
        if face_region.size > 0:
            # 计算模糊度（拉普拉斯方差）
            gray = cv2.cvtColor(face_region, cv2.COLOR_RGB2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 模糊度阈值
            if laplacian_var < 100:
                quality *= 0.7
            elif laplacian_var > 500:
                quality *= 1.1
        
        return min(max(quality, 0.0), 1.0)
    
    def _generate_face_id(self, embedding: np.ndarray, 
                         detection_result: FaceDetectionResult) -> str:
        """生成唯一人脸ID"""
        # 基于特征向量生成哈希ID
        embedding_bytes = embedding.tobytes()
        bbox_bytes = np.array(detection_result.bbox).tobytes()
        
        combined = embedding_bytes + bbox_bytes
        hash_obj = hashlib.md5(combined)
        
        return f"face_{hash_obj.hexdigest()[:12]}"
    
    def calculate_similarity(self, embedding1: np.ndarray, 
                            embedding2: np.ndarray) -> float:
        """计算两个人脸特征向量的相似度"""
        # 余弦相似度
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)


class MockFaceDetector:
    """模拟人脸检测器（用于演示）"""
    
    def __init__(self, confidence_threshold=0.95):
        self.confidence_threshold = confidence_threshold
    
    def detect(self, image: np.ndarray) -> List[FaceDetectionResult]:
        """模拟人脸检测"""
        height, width = image.shape[:2]
        
        # 模拟检测到1-3张人脸
        num_faces = np.random.randint(1, 4)
        results = []
        
        for i in range(num_faces):
            # 随机生成边界框
            face_width = np.random.randint(50, 200)
            face_height = np.random.randint(50, 200)
            x1 = np.random.randint(0, width - face_width - 1)
            y1 = np.random.randint(0, height - face_height - 1)
            x2 = x1 + face_width
            y2 = y1 + face_height
            
            # 随机生成关键点
            landmarks = np.random.rand(10) * 100
            landmarks = landmarks.reshape(5, 2)
            
            # 随机生成置信度（在阈值附近）
            confidence = self.confidence_threshold + np.random.uniform(-0.1, 0.1)
            
            # 随机生成姿态角度
            pitch = np.random.uniform(-10, 10)
            yaw = np.random.uniform(-15, 15)
            roll = np.random.uniform(-5, 5)
            
            result = FaceDetectionResult(
                bbox=(x1, y1, x2, y2),
                landmarks=landmarks,
                confidence=float(confidence),
                pose_angles=(pitch, yaw, roll)
            )
            results.append(result)
        
        return results


class MockFaceRecognizer:
    """模拟人脸识别器（用于演示）"""
    
    def __init__(self, embedding_dim=512):
        self.embedding_dim = embedding_dim
        # 模拟的参考特征向量
        self.reference_embeddings = self._generate_reference_embeddings()
    
    def _generate_reference_embeddings(self) -> Dict[str, np.ndarray]:
        """生成模拟的参考特征向量"""
        references = {}
        
        # 创建几个参考人脸的ID
        face_ids = ["face_model_001", "face_model_002", "face_model_003"]
        
        for face_id in face_ids:
            # 生成随机但稳定的特征向量
            np.random.seed(hash(face_id) % 1000)
            embedding = np.random.randn(self.embedding_dim)
            embedding = embedding / np.linalg.norm(embedding)
            references[face_id] = embedding
        
        return references
    
    def extract(self, face_image: np.ndarray) -> np.ndarray:
        """提取人脸特征向量"""
        # 模拟特征提取：随机选择一个参考人脸并添加噪声
        ref_id = np.random.choice(list(self.reference_embeddings.keys()))
        base_embedding = self.reference_embeddings[ref_id]
        
        # 添加少量噪声模拟个体差异
        noise = np.random.randn(self.embedding_dim) * 0.1
        embedding = base_embedding + noise
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding