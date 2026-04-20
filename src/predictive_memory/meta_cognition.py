#!/usr/bin/env python3
"""
元认知系统
Meta-Cognition System

功能：知道"自己知道什么"，评估预测可信度
核心：智慧不仅在于知道，更在于知道自己不知道
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDomain:
    """知识领域"""
    domain_name: str
    mastery_level: float          # 掌握程度 0-1
    experience_count: int         # 经验数量
    accuracy_history: List[float] # 准确率历史
    last_updated: datetime
    blind_spots: List[str]        # 盲区


class MetaCognition:
    """
    元认知系统
    
    功能：
    1. 自我评估：知道自己懂什么、不懂什么
    2. 置信度计算：基于证据强度评估预测可信度
    3. 盲区识别：发现知识盲区
    4. 学习规划：建议学习方向
    """
    
    def __init__(self, db_path: str = "data/predictive_memory/meta_cognition.db"):
        self.db_path = db_path
        
        # 知识领域掌握程度
        self.knowledge_domains: Dict[str, KnowledgeDomain] = {}
        
        # 自信度历史
        self.confidence_history: List[Dict] = []
        
        # 预测准确率追踪
        self.prediction_accuracy: Dict[str, List[bool]] = defaultdict(list)
        
        # 初始化
        self._init_db()
        self._load_state()
        
        logger.info("元认知系统初始化完成")
    
    def _init_db(self):
        """初始化数据库"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_domains (
                domain_name TEXT PRIMARY KEY,
                mastery_level REAL,
                experience_count INTEGER,
                accuracy_history TEXT,
                last_updated TIMESTAMP,
                blind_spots TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS confidence_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_type TEXT,
                confidence REAL,
                actual_result INTEGER,
                timestamp TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_state(self):
        """加载状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM knowledge_domains')
        for row in cursor.fetchall():
            self.knowledge_domains[row[0]] = KnowledgeDomain(
                domain_name=row[0],
                mastery_level=row[1],
                experience_count=row[2],
                accuracy_history=json.loads(row[3]) if row[3] else [],
                last_updated=datetime.fromisoformat(row[4]),
                blind_spots=json.loads(row[5]) if row[5] else []
            )
        
        conn.close()
    
    def evaluate(self, prediction: Dict, domain: str = None) -> Dict:
        """
        评估预测的可信度
        
        Args:
            prediction: 预测结果
            domain: 领域名称
            
        Returns:
            可信度评估
        """
        # 1. 领域掌握度
        domain_mastery = self._get_domain_mastery(domain or 'general')
        
        # 2. 证据强度
        evidence_strength = self._evaluate_evidence(prediction.get('evidence_count', 0))
        
        # 3. 历史准确率
        accuracy_score = self._get_accuracy_score(domain or 'general')
        
        # 4. 预测类型可信度
        prediction_type_confidence = self._get_prediction_type_confidence(
            prediction.get('prediction_type', 'unknown')
        )
        
        # 综合置信度
        overall_confidence = (
            domain_mastery * 0.25 +
            evidence_strength * 0.35 +
            accuracy_score * 0.25 +
            prediction_type_confidence * 0.15
        )
        
        return {
            'overall_confidence': overall_confidence,
            'domain_mastery': domain_mastery,
            'evidence_strength': evidence_strength,
            'accuracy_score': accuracy_score,
            'prediction_type_confidence': prediction_type_confidence,
            'uncertainty_level': self._classify_uncertainty(overall_confidence),
            'recommendation': self._generate_recommendation(overall_confidence)
        }
    
    def admit_uncertainty(self, situation: Dict) -> Dict:
        """
        承认不确定：智慧的体现
        
        Args:
            situation: 当前情境
            
        Returns:
            不确定性声明
        """
        domain = situation.get('domain', 'general')
        confidence = self._get_domain_mastery(domain)
        
        if confidence < 0.3:
            return {
                'status': 'I_dont_know',
                'message': '我对这个领域了解不足，建议寻求其他资源',
                'suggestion': f'可以尝试学习{domain}相关知识',
                'confidence': confidence,
                'should_proceed': False
            }
        
        elif confidence < 0.6:
            return {
                'status': 'uncertain',
                'message': '我有一定了解，但存在不确定性',
                'confidence': confidence,
                'should_proceed': True,
                'warning': '建议谨慎参考，实际情况可能有偏差'
            }
        
        else:
            return {
                'status': 'confident',
                'message': '我对这个预测有信心',
                'confidence': confidence,
                'should_proceed': True
            }
    
    def record_feedback(self, prediction_id: str, prediction_type: str, 
                       was_correct: bool, domain: str = None):
        """
        记录预测反馈，更新元认知
        
        Args:
            prediction_id: 预测ID
            prediction_type: 预测类型
            was_correct: 是否正确
            domain: 领域
        """
        # 更新预测准确率
        self.prediction_accuracy[prediction_type].append(was_correct)
        
        # 限制历史长度
        if len(self.prediction_accuracy[prediction_type]) > 100:
            self.prediction_accuracy[prediction_type] = self.prediction_accuracy[prediction_type][-100:]
        
        # 更新领域掌握度
        if domain:
            self._update_domain_mastery(domain, was_correct)
        
        # 记录到数据库
        self._record_confidence_history(prediction_type, was_correct)
        
        logger.debug(f"记录反馈: {prediction_type}, 正确: {was_correct}")
    
    def identify_blind_spots(self) -> List[Dict]:
        """
        识别知识盲区
        
        Returns:
            盲区列表
        """
        blind_spots = []
        
        for domain, knowledge in self.knowledge_domains.items():
            if knowledge.mastery_level < 0.3:
                blind_spots.append({
                    'domain': domain,
                    'mastery_level': knowledge.mastery_level,
                    'recommendation': f'需要学习{domain}相关知识',
                    'priority': 'high' if knowledge.mastery_level < 0.1 else 'medium'
                })
        
        # 找出准确率持续低的领域
        for prediction_type, accuracy_history in self.prediction_accuracy.items():
            if len(accuracy_history) >= 5:
                recent_accuracy = sum(accuracy_history[-5:]) / 5
                if recent_accuracy < 0.5:
                    blind_spots.append({
                        'domain': f'prediction_{prediction_type}',
                        'mastery_level': recent_accuracy,
                        'recommendation': f'预测类型{prediction_type}准确率较低，需要优化',
                        'priority': 'high'
                    })
        
        return blind_spots
    
    def suggest_learning(self) -> List[Dict]:
        """
        建议学习方向
        
        Returns:
            学习建议列表
        """
        suggestions = []
        
        # 基于盲区建议
        blind_spots = self.identify_blind_spots()
        for spot in blind_spots:
            suggestions.append({
                'area': spot['domain'],
                'reason': f'当前掌握度: {spot["mastery_level"]:.0%}',
                'priority': spot['priority']
            })
        
        # 基于使用频率建议（常用的需要精通）
        for domain, knowledge in self.knowledge_domains.items():
            if knowledge.experience_count > 10 and knowledge.mastery_level < 0.7:
                suggestions.append({
                    'area': domain,
                    'reason': f'使用频繁({knowledge.experience_count}次)但掌握度不高',
                    'priority': 'medium'
                })
        
        # 按优先级排序
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        suggestions.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return suggestions[:5]  # 返回前5个建议
    
    def _get_domain_mastery(self, domain: str) -> float:
        """获取领域掌握度"""
        if domain not in self.knowledge_domains:
            return 0.3  # 新领域默认低置信度
        
        return self.knowledge_domains[domain].mastery_level
    
    def _evaluate_evidence(self, evidence_count: int) -> float:
        """评估证据强度"""
        # 样本越多越可信，但有上限
        return min(1.0, evidence_count / 10)
    
    def _get_accuracy_score(self, domain: str) -> float:
        """获取历史准确率"""
        if domain not in self.prediction_accuracy:
            return 0.5  # 无历史数据，中性评分
        
        history = self.prediction_accuracy[domain]
        if not history:
            return 0.5
        
        # 最近10次的准确率
        recent = history[-10:]
        return sum(recent) / len(recent)
    
    def _get_prediction_type_confidence(self, prediction_type: str) -> float:
        """获取预测类型可信度"""
        type_weights = {
            'causal': 0.7,      # 因果预测较可靠
            'decision': 0.6,    # 决策预测中等
            'emotional': 0.5,   # 情感预测较难
            'social': 0.4,      # 社交预测最难
            'unknown': 0.3      # 未知类型
        }
        
        return type_weights.get(prediction_type, 0.3)
    
    def _classify_uncertainty(self, confidence: float) -> str:
        """分类不确定性等级"""
        if confidence >= 0.8:
            return 'very_low'
        elif confidence >= 0.6:
            return 'low'
        elif confidence >= 0.4:
            return 'medium'
        elif confidence >= 0.2:
            return 'high'
        else:
            return 'very_high'
    
    def _generate_recommendation(self, confidence: float) -> str:
        """生成建议"""
        if confidence >= 0.7:
            return "可以信任此预测，建议直接采纳"
        elif confidence >= 0.5:
            return "预测有一定参考价值，建议结合其他信息判断"
        elif confidence >= 0.3:
            return "预测不确定性较高，建议谨慎参考"
        else:
            return "预测可信度很低，建议不要作为决策依据"
    
    def _update_domain_mastery(self, domain: str, was_correct: bool):
        """更新领域掌握度"""
        if domain not in self.knowledge_domains:
            self.knowledge_domains[domain] = KnowledgeDomain(
                domain_name=domain,
                mastery_level=0.3,
                experience_count=0,
                accuracy_history=[],
                last_updated=datetime.now(),
                blind_spots=[]
            )
        
        knowledge = self.knowledge_domains[domain]
        knowledge.experience_count += 1
        knowledge.accuracy_history.append(1.0 if was_correct else 0.0)
        knowledge.last_updated = datetime.now()
        
        # 限制历史长度
        if len(knowledge.accuracy_history) > 50:
            knowledge.accuracy_history = knowledge.accuracy_history[-50:]
        
        # 更新掌握度（基于准确率）
        if knowledge.accuracy_history:
            knowledge.mastery_level = sum(knowledge.accuracy_history) / len(knowledge.accuracy_history)
        
        # 保存
        self._save_domain(domain)
    
    def _record_confidence_history(self, prediction_type: str, was_correct: bool):
        """记录置信度历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO confidence_history (prediction_type, confidence, actual_result, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (prediction_type, 0.5, 1 if was_correct else 0, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def _save_domain(self, domain: str):
        """保存领域状态"""
        knowledge = self.knowledge_domains[domain]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO knowledge_domains 
            (domain_name, mastery_level, experience_count, accuracy_history, last_updated, blind_spots)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            knowledge.domain_name,
            knowledge.mastery_level,
            knowledge.experience_count,
            json.dumps(knowledge.accuracy_history),
            knowledge.last_updated.isoformat(),
            json.dumps(knowledge.blind_spots)
        ))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_domains': len(self.knowledge_domains),
            'avg_mastery': sum(k.mastery_level for k in self.knowledge_domains.values()) / len(self.knowledge_domains) if self.knowledge_domains else 0,
            'blind_spots_count': len(self.identify_blind_spots()),
            'high_mastery_domains': [d for d, k in self.knowledge_domains.items() if k.mastery_level >= 0.7],
            'low_mastery_domains': [d for d, k in self.knowledge_domains.items() if k.mastery_level < 0.3]
        }
