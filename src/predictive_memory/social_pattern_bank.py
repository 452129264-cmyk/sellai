#!/usr/bin/env python3
"""
社交模式库
Social Pattern Bank

功能：学习人际规律，预测社交行为
核心：知道不同人的行为倾向和互动模式
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
class PersonProfile:
    """人物画像"""
    person_id: str
    name: str
    traits: Dict[str, float]          # 特质评分
    behavior_patterns: List[str]       # 行为模式
    interaction_history: List[Dict]    # 互动历史
    preferences: Dict[str, Any]        # 偏好
    reliability_score: float           # 可靠性评分
    last_interaction: datetime


@dataclass
class SocialPattern:
    """社交模式"""
    pattern_id: str
    person_id: str                     # 人物ID
    situation_type: str                # 情境类型
    expected_behavior: str             # 预期行为
    behavior_probability: float        # 行为概率
    context: Dict[str, Any]
    evidence_count: int


class SocialPatternBank:
    """
    社交模式库
    
    功能：
    1. 人物画像：了解每个人的性格特质
    2. 行为预测：预测某人在某情境下的行为
    3. 关系管理：维护人际关系网络
    """
    
    def __init__(self, db_path: str = "data/predictive_memory/social.db"):
        self.db_path = db_path
        
        # 人物画像
        self.person_profiles: Dict[str, PersonProfile] = {}
        
        # 社交模式
        self.social_patterns: Dict[str, SocialPattern] = {}
        
        # 人物→行为映射
        self.person_behavior_map: Dict[str, Dict] = defaultdict(lambda: defaultdict(float))
        
        # 初始化
        self._init_db()
        self._load_state()
        
        logger.info(f"社交模式库初始化完成，已加载{len(self.person_profiles)}个人物画像")
    
    def _init_db(self):
        """初始化数据库"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS person_profiles (
                person_id TEXT PRIMARY KEY,
                name TEXT,
                traits TEXT,
                behavior_patterns TEXT,
                interaction_history TEXT,
                preferences TEXT,
                reliability_score REAL,
                last_interaction TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_patterns (
                pattern_id TEXT PRIMARY KEY,
                person_id TEXT,
                situation_type TEXT,
                expected_behavior TEXT,
                behavior_probability REAL,
                context TEXT,
                evidence_count INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_state(self):
        """加载状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM person_profiles')
        for row in cursor.fetchall():
            self.person_profiles[row[0]] = PersonProfile(
                person_id=row[0],
                name=row[1],
                traits=json.loads(row[2]) if row[2] else {},
                behavior_patterns=json.loads(row[3]) if row[3] else [],
                interaction_history=json.loads(row[4]) if row[4] else [],
                preferences=json.loads(row[5]) if row[5] else {},
                reliability_score=row[6],
                last_interaction=datetime.fromisoformat(row[7]) if row[7] else datetime.now()
            )
        
        conn.close()
    
    def record_interaction(self, person_id: str, person_name: str, 
                          situation: str, behavior: str, outcome: str,
                          context: Dict = None):
        """
        记录社交互动
        
        Args:
            person_id: 人物ID
            person_name: 人物名称
            situation: 情境
            behavior: 对方行为
            outcome: 互动结果
            context: 上下文
        """
        # 更新人物画像
        if person_id not in self.person_profiles:
            self.person_profiles[person_id] = PersonProfile(
                person_id=person_id,
                name=person_name,
                traits={},
                behavior_patterns=[],
                interaction_history=[],
                preferences={},
                reliability_score=0.5,
                last_interaction=datetime.now()
            )
        
        profile = self.person_profiles[person_id]
        
        # 记录互动历史
        profile.interaction_history.append({
            'situation': situation,
            'behavior': behavior,
            'outcome': outcome,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        })
        
        # 限制历史长度
        if len(profile.interaction_history) > 100:
            profile.interaction_history = profile.interaction_history[-100:]
        
        profile.last_interaction = datetime.now()
        
        # 更新行为模式
        self._update_behavior_pattern(person_id, situation, behavior)
        
        # 更新特质（基于行为推断）
        self._infer_traits(profile, behavior, outcome)
        
        # 保存
        self._save_person_profile(profile)
        
        logger.debug(f"记录社交互动: {person_name} 在 {situation} 情境下 {behavior}")
    
    def predict_behavior(self, person_id: str, situation: str, 
                        context: Dict = None) -> List[Dict]:
        """
        预测某人行为
        
        Args:
            person_id: 人物ID
            situation: 情境
            context: 上下文
            
        Returns:
            预测行为列表
        """
        predictions = []
        
        # 从人物行为映射中查找
        if person_id in self.person_behavior_map:
            behavior_probs = self.person_behavior_map[person_id]
            
            for behavior, prob in behavior_probs.items():
                predictions.append({
                    'behavior': behavior,
                    'probability': prob,
                    'confidence': self._calculate_confidence(person_id, behavior)
                })
        
        # 如果有人物画像，基于特质推断
        if person_id in self.person_profiles:
            profile = self.person_profiles[person_id]
            
            # 基于特质推断可能行为
            trait_based = self._infer_from_traits(profile, situation)
            for behavior, prob in trait_based.items():
                # 检查是否已在预测列表中
                existing = next((p for p in predictions if p['behavior'] == behavior), None)
                if existing:
                    # 融合预测
                    existing['probability'] = (existing['probability'] + prob) / 2
                else:
                    predictions.append({
                        'behavior': behavior,
                        'probability': prob,
                        'confidence': 0.3,  # 基于特质推断置信度较低
                        'source': 'trait_inference'
                    })
        
        # 排序
        predictions.sort(key=lambda x: x['probability'], reverse=True)
        
        return predictions[:5]
    
    def get_person_profile(self, person_id: str) -> Optional[Dict]:
        """获取人物画像"""
        if person_id not in self.person_profiles:
            return None
        
        profile = self.person_profiles[person_id]
        
        return {
            'person_id': profile.person_id,
            'name': profile.name,
            'traits': profile.traits,
            'behavior_patterns': profile.behavior_patterns,
            'interaction_count': len(profile.interaction_history),
            'reliability_score': profile.reliability_score,
            'last_interaction': profile.last_interaction.isoformat()
        }
    
    def _update_behavior_pattern(self, person_id: str, situation: str, behavior: str):
        """更新行为模式"""
        key = f"{situation}→{behavior}"
        self.person_behavior_map[person_id][key] += 1
        
        # 归一化
        total = sum(self.person_behavior_map[person_id].values())
        for k in self.person_behavior_map[person_id]:
            self.person_behavior_map[person_id][k] /= total
    
    def _infer_traits(self, profile: PersonProfile, behavior: str, outcome: str):
        """从行为推断特质"""
        # 简单的特质推断规则
        trait_indicators = {
            '及时回复': {'responsiveness': 0.1},
            '拖延': {'responsiveness': -0.1, 'reliability': -0.1},
            '守约': {'reliability': 0.1},
            '爽约': {'reliability': -0.2},
            '主动': {'proactivity': 0.1},
            '被动': {'proactivity': -0.1},
            '热情': {'warmth': 0.1},
            '冷淡': {'warmth': -0.1}
        }
        
        for indicator, trait_changes in trait_indicators.items():
            if indicator in behavior or indicator in outcome:
                for trait, change in trait_changes.items():
                    if trait not in profile.traits:
                        profile.traits[trait] = 0.5
                    profile.traits[trait] = max(0, min(1, profile.traits[trait] + change))
    
    def _infer_from_traits(self, profile: PersonProfile, situation: str) -> Dict[str, float]:
        """基于特质推断行为"""
        inferences = {}
        
        traits = profile.traits
        
        # 根据特质推断可能行为
        if traits.get('responsiveness', 0.5) > 0.6:
            inferences['及时回复'] = traits['responsiveness']
        else:
            inferences['可能延迟回复'] = 1 - traits['responsiveness']
        
        if traits.get('reliability', 0.5) > 0.6:
            inferences['守约'] = traits['reliability']
        else:
            inferences['可能变卦'] = 1 - traits['reliability']
        
        if traits.get('proactivity', 0.5) > 0.6:
            inferences['主动推进'] = traits['proactivity']
        else:
            inferences['等待对方'] = 1 - traits['proactivity']
        
        return inferences
    
    def _calculate_confidence(self, person_id: str, behavior: str) -> float:
        """计算预测置信度"""
        if person_id not in self.person_profiles:
            return 0.3
        
        profile = self.person_profiles[person_id]
        
        # 基于互动次数
        interaction_count = len(profile.interaction_history)
        confidence = min(1.0, interaction_count / 10)
        
        return confidence
    
    def _save_person_profile(self, profile: PersonProfile):
        """保存人物画像"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO person_profiles 
            (person_id, name, traits, behavior_patterns, interaction_history,
             preferences, reliability_score, last_interaction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile.person_id,
            profile.name,
            json.dumps(profile.traits),
            json.dumps(profile.behavior_patterns),
            json.dumps(profile.interaction_history),
            json.dumps(profile.preferences),
            profile.reliability_score,
            profile.last_interaction.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_persons': len(self.person_profiles),
            'total_patterns': len(self.social_patterns),
            'avg_reliability': sum(p.reliability_score for p in self.person_profiles.values()) / len(self.person_profiles) if self.person_profiles else 0
        }
