#!/usr/bin/env python3
"""
情感模式库
Emotional Pattern Bank

功能：学习情感规律，预测情感反应
核心：事件→情感，知道什么情况下用户会有什么感受
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmotionalPattern:
    """情感模式"""
    pattern_id: str
    event_type: str                       # 事件类型
    event_features: Dict[str, Any]        # 事件特征
    primary_emotion: str                  # 主要情感
    emotion_intensity: float              # 情感强度 0-1
    emotion_duration: float               # 持续时间（小时）
    context: Dict[str, Any]               # 上下文
    evidence_count: int
    first_observed: datetime
    last_observed: datetime


class EmotionalPatternBank:
    """
    情感模式库
    
    功能：
    1. 学习情感规律：什么事件触发什么情感
    2. 预测情感反应：给定事件预测可能的情感
    3. 情感记忆权重：情感越强烈，记忆越深刻
    """
    
    # 情感权重（基于进化心理学）
    EMOTION_WEIGHTS = {
        'fear': 2.0,       # 恐惧（生存关键）
        'anger': 1.8,      # 愤怒（边界保护）
        'surprise': 1.7,   # 惊讶（注意力）
        'sadness': 1.6,    # 悲伤（损失感知）
        'joy': 1.5,        # 快乐
        'disgust': 1.4,    # 厌恶
        'anticipation': 1.3,  # 期待
        'trust': 1.2,      # 信任
        'neutral': 1.0     # 中性
    }
    
    def __init__(self, db_path: str = "data/predictive_memory/emotional.db"):
        self.db_path = db_path
        
        # 情感模式索引
        self.patterns: Dict[str, EmotionalPattern] = {}
        
        # 事件→情感映射
        self.event_emotion_map: Dict[str, Dict] = defaultdict(lambda: defaultdict(float))
        
        # 初始化
        self._init_db()
        self._load_patterns()
        
        logger.info(f"情感模式库初始化完成，已加载{len(self.patterns)}个模式")
    
    def _init_db(self):
        """初始化数据库"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emotional_patterns (
                pattern_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                event_features TEXT,
                primary_emotion TEXT NOT NULL,
                emotion_intensity REAL,
                emotion_duration REAL,
                context TEXT,
                evidence_count INTEGER DEFAULT 1,
                first_observed TIMESTAMP,
                last_observed TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_patterns(self):
        """加载已有模式"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM emotional_patterns')
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            pattern = EmotionalPattern(
                pattern_id=row[0],
                event_type=row[1],
                event_features=json.loads(row[2]) if row[2] else {},
                primary_emotion=row[3],
                emotion_intensity=row[4],
                emotion_duration=row[5],
                context=json.loads(row[6]) if row[6] else {},
                evidence_count=row[7],
                first_observed=datetime.fromisoformat(row[8]),
                last_observed=datetime.fromisoformat(row[9])
            )
            
            self.patterns[pattern.pattern_id] = pattern
            
            # 构建映射
            self.event_emotion_map[pattern.event_type][pattern.primary_emotion] += pattern.emotion_intensity
    
    def learn(self, event_type: str, event_features: Dict, emotion: str, 
              intensity: float, duration: float = 1.0, context: Dict = None):
        """
        学习情感模式
        
        Args:
            event_type: 事件类型
            event_features: 事件特征
            emotion: 主要情感
            intensity: 情感强度 0-1
            duration: 持续时间（小时）
            context: 上下文
        """
        pattern_id = self._generate_pattern_id(event_type, emotion, event_features)
        
        if pattern_id in self.patterns:
            # 更新已有模式
            pattern = self.patterns[pattern_id]
            pattern.evidence_count += 1
            pattern.last_observed = datetime.now()
            
            # 更新强度（平均）
            pattern.emotion_intensity = (
                pattern.emotion_intensity * (pattern.evidence_count - 1) + intensity
            ) / pattern.evidence_count
            
        else:
            # 创建新模式
            pattern = EmotionalPattern(
                pattern_id=pattern_id,
                event_type=event_type,
                event_features=event_features,
                primary_emotion=emotion,
                emotion_intensity=intensity,
                emotion_duration=duration,
                context=context or {},
                evidence_count=1,
                first_observed=datetime.now(),
                last_observed=datetime.now()
            )
            
            self.patterns[pattern_id] = pattern
        
        # 更新映射
        self.event_emotion_map[event_type][emotion] += intensity
        
        # 保存
        self._save_pattern(pattern)
        
        logger.debug(f"学习情感模式: {event_type} → {emotion}, 强度: {intensity:.2f}")
        
        return pattern
    
    def predict_emotion(self, event_type: str, event_features: Dict = None) -> List[Dict]:
        """
        预测情感反应
        
        Args:
            event_type: 事件类型
            event_features: 事件特征（可选）
            
        Returns:
            预测的情感列表
        """
        predictions = []
        
        if event_type in self.event_emotion_map:
            # 归一化
            total = sum(self.event_emotion_map[event_type].values())
            
            for emotion, weight in self.event_emotion_map[event_type].items():
                probability = weight / total if total > 0 else 0
                
                # 找到对应模式获取更多细节
                matching_patterns = [
                    p for p in self.patterns.values()
                    if p.event_type == event_type and p.primary_emotion == emotion
                ]
                
                avg_intensity = (
                    sum(p.emotion_intensity for p in matching_patterns) / len(matching_patterns)
                    if matching_patterns else 0.5
                )
                
                predictions.append({
                    'emotion': emotion,
                    'probability': probability,
                    'expected_intensity': avg_intensity,
                    'emotion_weight': self.EMOTION_WEIGHTS.get(emotion, 1.0),
                    'evidence_count': len(matching_patterns)
                })
        
        # 按概率排序
        predictions.sort(key=lambda x: x['probability'], reverse=True)
        
        return predictions
    
    def calculate_memory_importance(self, event_type: str, emotion: str, intensity: float) -> float:
        """
        计算记忆重要性
        情感越强烈，记忆越深刻
        
        Args:
            event_type: 事件类型
            emotion: 情感
            intensity: 情感强度
            
        Returns:
            记忆重要性评分
        """
        emotion_weight = self.EMOTION_WEIGHTS.get(emotion, 1.0)
        
        return emotion_weight * intensity
    
    def _generate_pattern_id(self, event_type: str, emotion: str, features: Dict) -> str:
        """生成模式ID"""
        key = f"{event_type}|{emotion}|{json.dumps(features, sort_keys=True)}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _save_pattern(self, pattern: EmotionalPattern):
        """保存到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO emotional_patterns 
            (pattern_id, event_type, event_features, primary_emotion, emotion_intensity,
             emotion_duration, context, evidence_count, first_observed, last_observed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern.pattern_id,
            pattern.event_type,
            json.dumps(pattern.event_features),
            pattern.primary_emotion,
            pattern.emotion_intensity,
            pattern.emotion_duration,
            json.dumps(pattern.context),
            pattern.evidence_count,
            pattern.first_observed.isoformat(),
            pattern.last_observed.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_patterns': len(self.patterns),
            'unique_events': len(self.event_emotion_map),
            'emotion_distribution': dict(
                sum((dict(self.event_emotion_map[e]) for e in self.event_emotion_map), defaultdict(float))
            )
        }
