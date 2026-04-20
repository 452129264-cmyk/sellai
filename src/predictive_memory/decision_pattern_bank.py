#!/usr/bin/env python3
"""
决策模式库
Decision Pattern Bank

功能：记录决策模式，推荐最优行动
核心：情境→行动→结果，找到成功率最高的决策路径
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DecisionPattern:
    """决策模式"""
    pattern_id: str
    situation_key: str                   # 情境编码
    situation_features: Dict[str, Any]   # 情境特征
    action: str                          # 采取的行动
    outcome: str                         # 结果
    success_score: float                 # 成功评分 0-1
    context: Dict[str, Any]              # 上下文
    timestamp: datetime
    
    def to_dict(self):
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass 
class ActionRecommendation:
    """行动推荐"""
    action: str
    success_rate: float
    confidence: float
    evidence_count: int
    expected_outcome: str
    similar_cases: List[Dict]
    warnings: List[str]


class DecisionPatternBank:
    """
    决策模式库
    
    功能：
    1. 记录决策历史：情境→行动→结果
    2. 推荐最优行动：基于历史成功率
    3. 预测行动结果：给定行动预测可能结果
    4. 风险评估：识别可能的失败因素
    """
    
    def __init__(self, db_path: str = "data/predictive_memory/decision.db"):
        self.db_path = db_path
        
        # 决策树：情境→行动→结果统计
        self.decision_tree: Dict[str, Dict[str, Dict]] = defaultdict(
            lambda: defaultdict(lambda: {
                'success_count': 0,
                'fail_count': 0,
                'total_score': 0.0,
                'outcomes': [],
                'contexts': []
            })
        )
        
        # 模式索引
        self.patterns: Dict[str, DecisionPattern] = {}
        
        # 初始化
        self._init_db()
        self._load_patterns()
        
        logger.info(f"决策模式库初始化完成，已加载{len(self.patterns)}个模式")
    
    def _init_db(self):
        """初始化数据库"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_patterns (
                pattern_id TEXT PRIMARY KEY,
                situation_key TEXT NOT NULL,
                situation_features TEXT,
                action TEXT NOT NULL,
                outcome TEXT,
                success_score REAL,
                context TEXT,
                timestamp TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_situation ON decision_patterns(situation_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_action ON decision_patterns(action)')
        
        conn.commit()
        conn.close()
    
    def _load_patterns(self):
        """加载已有模式"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM decision_patterns ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            pattern = DecisionPattern(
                pattern_id=row[0],
                situation_key=row[1],
                situation_features=json.loads(row[2]) if row[2] else {},
                action=row[3],
                outcome=row[4],
                success_score=row[5],
                context=json.loads(row[6]) if row[6] else {},
                timestamp=datetime.fromisoformat(row[7])
            )
            
            self.patterns[pattern.pattern_id] = pattern
            
            # 构建决策树
            self._update_decision_tree(pattern)
    
    def record(self, situation: Dict, action: str, outcome: str, 
               success_score: float, context: Dict = None):
        """
        记录决策模式
        
        Args:
            situation: 情境特征
            action: 采取的行动
            outcome: 结果描述
            success_score: 成功评分 0-1
            context: 额外上下文
        """
        # 编码情境
        situation_key = self._encode_situation(situation)
        
        # 生成模式ID
        pattern_id = self._generate_pattern_id(situation_key, action, outcome)
        
        # 创建模式
        pattern = DecisionPattern(
            pattern_id=pattern_id,
            situation_key=situation_key,
            situation_features=situation,
            action=action,
            outcome=outcome,
            success_score=success_score,
            context=context or {},
            timestamp=datetime.now()
        )
        
        self.patterns[pattern_id] = pattern
        
        # 更新决策树
        self._update_decision_tree(pattern)
        
        # 保存到数据库
        self._save_pattern(pattern)
        
        logger.debug(f"记录决策: {situation_key} → {action}, 成功率: {success_score:.2f}")
        
        return pattern
    
    def recommend(self, situation: Dict, top_k: int = 3) -> List[ActionRecommendation]:
        """
        推荐最优行动
        
        Args:
            situation: 当前情境
            top_k: 返回前k个推荐
            
        Returns:
            推荐行动列表
        """
        situation_key = self._encode_situation(situation)
        
        if situation_key not in self.decision_tree:
            # 尝试找相似情境
            similar_key = self._find_similar_situation(situation_key)
            if similar_key:
                situation_key = similar_key
            else:
                return []  # 无经验
        
        actions = self.decision_tree[situation_key]
        recommendations = []
        
        for action, stats in actions.items():
            total = stats['success_count'] + stats['fail_count']
            if total == 0:
                continue
            
            # 成功率
            success_rate = stats['success_count'] / total
            
            # 置信度（基于样本量）
            confidence = min(1.0, total / 10) * 0.5 + 0.5 * (success_rate if success_rate > 0.5 else 1 - success_rate)
            
            # 预期结果
            expected_outcome = self._predict_outcome(stats['outcomes'])
            
            # 相似案例
            similar_cases = [
                {'outcome': o, 'context': c} 
                for o, c in zip(stats['outcomes'][-5:], stats['contexts'][-5:])
            ]
            
            # 警告
            warnings = []
            if stats['fail_count'] > stats['success_count']:
                warnings.append(f"该行动历史失败率较高 ({stats['fail_count']}/{total})")
            if total < 3:
                warnings.append("样本量较少，建议谨慎参考")
            
            recommendations.append(ActionRecommendation(
                action=action,
                success_rate=success_rate,
                confidence=confidence,
                evidence_count=total,
                expected_outcome=expected_outcome,
                similar_cases=similar_cases,
                warnings=warnings
            ))
        
        # 按成功率和置信度排序
        recommendations.sort(key=lambda x: x.success_rate * x.confidence, reverse=True)
        
        return recommendations[:top_k]
    
    def predict_outcome(self, situation: Dict, action: str) -> Optional[Dict]:
        """
        预测行动结果
        
        Args:
            situation: 当前情境
            action: 计划采取的行动
            
        Returns:
            预测结果
        """
        situation_key = self._encode_situation(situation)
        
        if situation_key not in self.decision_tree:
            return None
        
        if action not in self.decision_tree[situation_key]:
            return None
        
        stats = self.decision_tree[situation_key][action]
        total = stats['success_count'] + stats['fail_count']
        
        if total == 0:
            return None
        
        return {
            'success_probability': stats['success_count'] / total,
            'expected_outcome': self._predict_outcome(stats['outcomes']),
            'confidence': min(1.0, total / 10),
            'evidence_count': total,
            'historical_outcomes': stats['outcomes'][-5:]
        }
    
    def find_similar_cases(self, situation: Dict, action: str = None, limit: int = 10) -> List[DecisionPattern]:
        """
        查找相似案例
        """
        situation_key = self._encode_situation(situation)
        
        similar = []
        for pattern in self.patterns.values():
            if action and pattern.action != action:
                continue
            
            # 计算情境相似度
            similarity = self._situation_similarity(situation_key, pattern.situation_key)
            if similarity > 0.3:
                similar.append((pattern, similarity))
        
        similar.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in similar[:limit]]
    
    def _encode_situation(self, situation: Dict) -> str:
        """
        编码情境为字符串
        用于快速匹配相似情境
        """
        if not situation:
            return "default"
        
        # 提取关键特征
        features = []
        for key, value in sorted(situation.items()):
            if isinstance(value, (str, int, float, bool)):
                features.append(f"{key}={value}")
            elif isinstance(value, list):
                features.append(f"{key}=[{len(value)}]")
            elif isinstance(value, dict):
                features.append(f"{key}={{{len(value)}}}")
        
        return "|".join(features)
    
    def _generate_pattern_id(self, situation_key: str, action: str, outcome: str) -> str:
        """生成模式ID"""
        key = f"{situation_key}|{action}|{outcome}|{datetime.now().isoformat()}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _update_decision_tree(self, pattern: DecisionPattern):
        """更新决策树"""
        stats = self.decision_tree[pattern.situation_key][pattern.action]
        
        if pattern.success_score >= 0.5:
            stats['success_count'] += 1
        else:
            stats['fail_count'] += 1
        
        stats['total_score'] += pattern.success_score
        stats['outcomes'].append(pattern.outcome)
        stats['contexts'].append(pattern.context)
        
        # 限制历史长度
        if len(stats['outcomes']) > 100:
            stats['outcomes'] = stats['outcomes'][-100:]
            stats['contexts'] = stats['contexts'][-100:]
    
    def _predict_outcome(self, outcomes: List[str]) -> str:
        """预测最可能的结果"""
        if not outcomes:
            return "未知结果"
        
        # 统计结果频率
        outcome_counts = defaultdict(int)
        for outcome in outcomes[-20:]:  # 最近20个
            outcome_counts[outcome] += 1
        
        # 返回最频繁的结果
        return max(outcome_counts.items(), key=lambda x: x[1])[0]
    
    def _find_similar_situation(self, situation_key: str) -> Optional[str]:
        """查找相似情境"""
        best_match = None
        best_similarity = 0.3  # 最低相似度阈值
        
        for existing_key in self.decision_tree.keys():
            similarity = self._situation_similarity(situation_key, existing_key)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = existing_key
        
        return best_match
    
    def _situation_similarity(self, key1: str, key2: str) -> float:
        """计算情境相似度"""
        if key1 == key2:
            return 1.0
        
        # 分解特征
        features1 = set(key1.split('|'))
        features2 = set(key2.split('|'))
        
        if not features1 or not features2:
            return 0.0
        
        # Jaccard相似度
        intersection = len(features1 & features2)
        union = len(features1 | features2)
        
        return intersection / union if union > 0 else 0.0
    
    def _save_pattern(self, pattern: DecisionPattern):
        """保存到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO decision_patterns 
            (pattern_id, situation_key, situation_features, action, outcome, 
             success_score, context, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern.pattern_id,
            pattern.situation_key,
            json.dumps(pattern.situation_features),
            pattern.action,
            pattern.outcome,
            pattern.success_score,
            json.dumps(pattern.context),
            pattern.timestamp.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_decisions = len(self.patterns)
        
        success_count = sum(1 for p in self.patterns.values() if p.success_score >= 0.5)
        
        return {
            'total_decisions': total_decisions,
            'success_rate': success_count / total_decisions if total_decisions > 0 else 0,
            'unique_situations': len(self.decision_tree),
            'unique_actions': len(set(p.action for p in self.patterns.values())),
            'avg_confidence': sum(
                min(1.0, (s['success_count'] + s['fail_count']) / 10)
                for actions in self.decision_tree.values()
                for s in actions.values()
            ) / sum(len(actions) for actions in self.decision_tree.values()) if self.decision_tree else 0
        }
