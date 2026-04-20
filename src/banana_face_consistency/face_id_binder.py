"""
人脸ID绑定系统
确保同一模特ID在100张内脸部特征差异<3%
"""

import os
import json
import numpy as np
import sqlite3
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import hashlib
import pickle

from .config import face_config
from .face_feature_extractor import FaceFeatureExtractor, FaceEmbedding

logger = logging.getLogger(__name__)


@dataclass
class FaceIdentity:
    """人脸身份定义"""
    face_id: str  # 人脸ID（基于特征向量生成）
    model_id: str  # 模特ID（用户指定）
    reference_embeddings: List[np.ndarray]  # 参考特征向量列表
    embedding_count: int  # 已收集的特征向量数量
    mean_embedding: np.ndarray  # 平均特征向量
    variance_score: float  # 特征方差分数
    last_update: datetime  # 最后更新时间
    quality_scores: List[float]  # 历史质量分数
    metadata: Dict[str, Any]  # 元数据
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {
                "created_at": datetime.now().isoformat(),
                "model_type": "human",
                "consistency_threshold": face_config.max_face_variance
            }


@dataclass
class BindingResult:
    """绑定结果"""
    success: bool
    model_id: str
    face_id: str
    similarity_score: float
    variance_score: float
    is_new_identity: bool
    message: str


class FaceIDBinder:
    """人脸ID绑定器"""
    
    def __init__(self, config: FaceConsistencyConfig = None):
        self.config = config or face_config
        self.extractor = FaceFeatureExtractor(config)
        self.database_path = self.config.face_id_database
        self._init_database()
        logger.info(f"人脸ID绑定器初始化完成，数据库: {self.database_path}")
    
    def _init_database(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # 创建人脸身份表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_identities (
                face_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                reference_embeddings BLOB,
                embedding_count INTEGER DEFAULT 0,
                mean_embedding BLOB,
                variance_score REAL DEFAULT 0.0,
                last_update TIMESTAMP,
                quality_scores BLOB,
                metadata BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建特征向量历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS embedding_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                extraction_time TIMESTAMP,
                image_hash TEXT,
                quality_score REAL,
                FOREIGN KEY (face_id) REFERENCES face_identities (face_id)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_model_id ON face_identities (model_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_embedding_history_face_id ON embedding_history (face_id)')
        
        conn.commit()
        conn.close()
    
    def bind_face(self, image: np.ndarray, model_id: str) -> BindingResult:
        """
        将图像中的人脸绑定到指定模特ID
        
        Args:
            image: 输入图像
            model_id: 目标模特ID
            
        Returns:
            绑定结果
        """
        try:
            # 检测并提取人脸特征
            faces = self.extractor.detect_faces(image)
            
            if not faces:
                return BindingResult(
                    success=False,
                    model_id=model_id,
                    face_id="",
                    similarity_score=0.0,
                    variance_score=0.0,
                    is_new_identity=False,
                    message="未检测到人脸"
                )
            
            # 使用最大人脸
            primary_face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
            
            # 提取特征向量
            embedding_obj = self.extractor.extract_embedding(image, primary_face)
            
            # 查找或创建人脸身份
            binding_result = self._find_or_create_identity(
                embedding_obj.embedding, 
                model_id,
                embedding_obj.face_id,
                primary_face.quality_score
            )
            
            # 计算特征差异
            variance_score = self._calculate_variance_score(
                binding_result.face_id, 
                embedding_obj.embedding
            )
            
            # 检查一致性
            consistency_check = self._check_consistency(variance_score)
            
            if not consistency_check:
                return BindingResult(
                    success=False,
                    model_id=model_id,
                    face_id=binding_result.face_id,
                    similarity_score=binding_result.similarity_score,
                    variance_score=float(variance_score),
                    is_new_identity=binding_result.is_new_identity,
                    message=f"特征差异超过阈值: {variance_score:.4f} > {self.config.max_face_variance}"
                )
            
            # 更新数据库
            self._update_identity(
                binding_result.face_id,
                embedding_obj.embedding,
                primary_face.quality_score
            )
            
            return BindingResult(
                success=True,
                model_id=model_id,
                face_id=binding_result.face_id,
                similarity_score=binding_result.similarity_score,
                variance_score=float(variance_score),
                is_new_identity=binding_result.is_new_identity,
                message=f"成功绑定到模特{model_id}, 特征差异: {variance_score:.4f}"
            )
            
        except Exception as e:
            logger.error(f"人脸绑定失败: {str(e)}")
            return BindingResult(
                success=False,
                model_id=model_id,
                face_id="",
                similarity_score=0.0,
                variance_score=0.0,
                is_new_identity=False,
                message=f"绑定失败: {str(e)}"
            )
    
    def _find_or_create_identity(self, embedding: np.ndarray, 
                                model_id: str, 
                                face_id: str,
                                quality_score: float) -> BindingResult:
        """查找或创建人脸身份"""
        # 查找该模特ID的现有身份
        existing_ids = self._find_identities_by_model_id(model_id)
        
        if existing_ids:
            # 计算与现有身份的相似度
            best_match = None
            best_similarity = 0.0
            
            for existing_id in existing_ids:
                identity = self._load_identity(existing_id)
                if identity is None:
                    continue
                    
                similarity = self.extractor.calculate_similarity(
                    embedding, identity.mean_embedding
                )
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = identity
            
            # 检查是否匹配现有身份
            if best_match and best_similarity >= self.config.recognition_threshold:
                return BindingResult(
                    success=True,
                    model_id=model_id,
                    face_id=best_match.face_id,
                    similarity_score=float(best_similarity),
                    variance_score=best_match.variance_score,
                    is_new_identity=False,
                    message=f"匹配到现有身份: {best_match.face_id}"
                )
        
        # 创建新身份
        new_face_id = self._create_new_identity(
            embedding, model_id, face_id, quality_score
        )
        
        return BindingResult(
            success=True,
            model_id=model_id,
            face_id=new_face_id,
            similarity_score=1.0,
            variance_score=0.0,
            is_new_identity=True,
            message=f"创建新身份: {new_face_id}"
        )
    
    def _find_identities_by_model_id(self, model_id: str) -> List[str]:
        """查找指定模特ID的所有人脸身份"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT face_id FROM face_identities WHERE model_id = ?",
            (model_id,)
        )
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def _load_identity(self, face_id: str) -> Optional[FaceIdentity]:
        """从数据库加载人脸身份"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM face_identities WHERE face_id = ?",
            (face_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # 解析二进制数据
        face_id, model_id, ref_emb_blob, embedding_count, mean_emb_blob, \
        variance_score, last_update, quality_scores_blob, metadata_blob, created_at = row
        
        # 反序列化
        reference_embeddings = pickle.loads(ref_emb_blob) if ref_emb_blob else []
        mean_embedding = pickle.loads(mean_emb_blob) if mean_emb_blob else None
        quality_scores = pickle.loads(quality_scores_blob) if quality_scores_blob else []
        metadata = pickle.loads(metadata_blob) if metadata_blob else {}
        
        # 转换为datetime
        if isinstance(last_update, str):
            last_update = datetime.fromisoformat(last_update)
        
        return FaceIdentity(
            face_id=face_id,
            model_id=model_id,
            reference_embeddings=reference_embeddings,
            embedding_count=embedding_count,
            mean_embedding=mean_embedding,
            variance_score=variance_score,
            last_update=last_update,
            quality_scores=quality_scores,
            metadata=metadata
        )
    
    def _create_new_identity(self, embedding: np.ndarray, 
                            model_id: str, 
                            face_id: str,
                            quality_score: float) -> str:
        """创建新的人脸身份"""
        # 生成唯一ID
        if not face_id or face_id == "error":
            face_id = self._generate_unique_face_id(embedding, model_id)
        
        # 创建初始数据
        reference_embeddings = [embedding.copy()]
        mean_embedding = embedding.copy()
        quality_scores = [quality_score]
        
        identity = FaceIdentity(
            face_id=face_id,
            model_id=model_id,
            reference_embeddings=reference_embeddings,
            embedding_count=1,
            mean_embedding=mean_embedding,
            variance_score=0.0,
            last_update=datetime.now(),
            quality_scores=quality_scores,
            metadata={
                "created_at": datetime.now().isoformat(),
                "initial_quality": quality_score,
                "model_type": "human"
            }
        )
        
        # 保存到数据库
        self._save_identity(identity)
        
        # 保存特征向量历史
        self._save_embedding_history(face_id, embedding, quality_score)
        
        logger.info(f"创建新人脸身份: {face_id} (模特: {model_id})")
        return face_id
    
    def _save_identity(self, identity: FaceIdentity):
        """保存人脸身份到数据库"""
        # 序列化二进制数据
        ref_emb_blob = pickle.dumps(identity.reference_embeddings)
        mean_emb_blob = pickle.dumps(identity.mean_embedding)
        quality_scores_blob = pickle.dumps(identity.quality_scores)
        metadata_blob = pickle.dumps(identity.metadata)
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO face_identities 
            (face_id, model_id, reference_embeddings, embedding_count, 
             mean_embedding, variance_score, last_update, quality_scores, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            identity.face_id,
            identity.model_id,
            ref_emb_blob,
            identity.embedding_count,
            mean_emb_blob,
            identity.variance_score,
            identity.last_update.isoformat(),
            quality_scores_blob,
            metadata_blob
        ))
        
        conn.commit()
        conn.close()
    
    def _save_embedding_history(self, face_id: str, embedding: np.ndarray, 
                               quality_score: float):
        """保存特征向量历史"""
        # 生成图像哈希（模拟）
        image_hash = hashlib.md5(embedding.tobytes()).hexdigest()[:8]
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO embedding_history 
            (face_id, embedding, extraction_time, image_hash, quality_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            face_id,
            pickle.dumps(embedding),
            datetime.now().isoformat(),
            image_hash,
            quality_score
        ))
        
        conn.commit()
        conn.close()
    
    def _update_identity(self, face_id: str, embedding: np.ndarray, 
                        quality_score: float):
        """更新人脸身份"""
        identity = self._load_identity(face_id)
        if identity is None:
            logger.error(f"无法找到身份: {face_id}")
            return
        
        # 添加新特征向量
        identity.reference_embeddings.append(embedding.copy())
        identity.quality_scores.append(quality_score)
        
        # 限制历史记录数量
        max_history = 100
        if len(identity.reference_embeddings) > max_history:
            identity.reference_embeddings = identity.reference_embeddings[-max_history:]
            identity.quality_scores = identity.quality_scores[-max_history:]
        
        # 更新计数
        identity.embedding_count = len(identity.reference_embeddings)
        
        # 重新计算平均特征向量
        identity.mean_embedding = np.mean(identity.reference_embeddings, axis=0)
        identity.mean_embedding = identity.mean_embedding / np.linalg.norm(identity.mean_embedding)
        
        # 计算方差分数
        identity.variance_score = self._calculate_variance_score(
            face_id, embedding
        )
        
        # 更新最后更新时间
        identity.last_update = datetime.now()
        
        # 保存更新
        self._save_identity(identity)
        
        # 保存特征向量历史
        self._save_embedding_history(face_id, embedding, quality_score)
        
        logger.info(f"更新人脸身份: {face_id}, 特征数量: {identity.embedding_count}")
    
    def _calculate_variance_score(self, face_id: str, 
                                 new_embedding: np.ndarray) -> float:
        """计算特征方差分数"""
        identity = self._load_identity(face_id)
        if identity is None or identity.embedding_count == 0:
            return 0.0
        
        # 计算与平均特征向量的差异
        similarity = self.extractor.calculate_similarity(
            new_embedding, identity.mean_embedding
        )
        
        # 差异分数 = 1 - 相似度
        variance = 1.0 - similarity
        
        return float(variance)
    
    def _check_consistency(self, variance_score: float) -> bool:
        """检查一致性是否满足要求"""
        return variance_score <= self.config.max_face_variance
    
    def _generate_unique_face_id(self, embedding: np.ndarray, 
                                model_id: str) -> str:
        """生成唯一人脸ID"""
        timestamp = int(datetime.now().timestamp())
        
        # 基于特征向量和模特ID生成哈希
        data = embedding.tobytes() + model_id.encode() + str(timestamp).encode()
        hash_obj = hashlib.md5(data)
        
        return f"face_{hash_obj.hexdigest()[:12]}_{timestamp % 10000:04d}"
    
    def get_consistency_report(self, model_id: str, 
                              limit: int = 100) -> Dict[str, Any]:
        """获取一致性报告"""
        identities = self._find_identities_by_model_id(model_id)
        
        if not identities:
            return {
                "model_id": model_id,
                "total_faces": 0,
                "average_variance": 0.0,
                "max_variance": 0.0,
                "consistency_status": "NO_DATA",
                "details": []
            }
        
        # 获取最近的limit个特征向量
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        all_embeddings = []
        all_variance_scores = []
        
        for face_id in identities:
            cursor.execute('''
                SELECT embedding, quality_score 
                FROM embedding_history 
                WHERE face_id = ? 
                ORDER BY extraction_time DESC 
                LIMIT ?
            ''', (face_id, limit))
            
            for emb_blob, q_score in cursor.fetchall():
                embedding = pickle.loads(emb_blob)
                all_embeddings.append(embedding)
        
        conn.close()
        
        if not all_embeddings:
            return {
                "model_id": model_id,
                "total_faces": 0,
                "average_variance": 0.0,
                "max_variance": 0.0,
                "consistency_status": "NO_DATA",
                "details": []
            }
        
        # 计算平均特征向量
        avg_embedding = np.mean(all_embeddings, axis=0)
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        
        # 计算每个特征向量与平均值的差异
        for emb in all_embeddings:
            similarity = self.extractor.calculate_similarity(emb, avg_embedding)
            variance = 1.0 - similarity
            all_variance_scores.append(variance)
        
        avg_variance = np.mean(all_variance_scores)
        max_variance = np.max(all_variance_scores) if all_variance_scores else 0.0
        
        # 评估一致性状态
        if avg_variance <= self.config.max_face_variance:
            consistency_status = "EXCELLENT"
        elif avg_variance <= self.config.max_face_variance * 1.5:
            consistency_status = "GOOD"
        else:
            consistency_status = "POOR"
        
        return {
            "model_id": model_id,
            "total_faces": len(all_embeddings),
            "average_variance": float(avg_variance),
            "max_variance": float(max_variance),
            "consistency_status": consistency_status,
            "threshold": self.config.max_face_variance,
            "details": [
                {
                    "embedding_index": i,
                    "variance_score": float(var)
                }
                for i, var in enumerate(all_variance_scores[:10])  # 只显示前10个
            ]
        }
    
    def enforce_consistency(self, model_id: str) -> bool:
        """强制执行一致性，清理不一致的特征向量"""
        report = self.get_consistency_report(model_id)
        
        if report["consistency_status"] == "EXCELLENT":
            logger.info(f"模特 {model_id} 一致性优秀，无需清理")
            return True
        
        logger.warning(f"模特 {model_id} 一致性较差，开始清理...")
        
        # 清理策略：移除方差超过阈值2倍的特征向量
        threshold = self.config.max_face_variance * 2.0
        
        # 获取所有身份
        identities = self._find_identities_by_model_id(model_id)
        
        for face_id in identities:
            # 获取该身份的历史记录
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, embedding 
                FROM embedding_history 
                WHERE face_id = ? 
                ORDER BY extraction_time DESC
            ''', (face_id,))
            
            rows = cursor.fetchall()
            
            # 计算每个特征向量的方差
            for row_id, emb_blob in rows:
                embedding = pickle.loads(emb_blob)
                
                # 计算方差
                identity = self._load_identity(face_id)
                if identity is None:
                    continue
                
                variance = self._calculate_variance_score(face_id, embedding)
                
                if variance > threshold:
                    # 删除不一致的特征向量
                    cursor.execute(
                        "DELETE FROM embedding_history WHERE id = ?",
                        (row_id,)
                    )
                    logger.info(f"删除不一致特征向量: 身份 {face_id}, 方差 {variance:.4f}")
            
            conn.commit()
            conn.close()
        
        logger.info(f"模特 {model_id} 一致性清理完成")
        return True