#!/usr/bin/env python3
"""
因果模式库
Causal Pattern Bank

功能：学习因果规律，预测因果关系
核心：A导致B，不是记住某次A导致B的事件，而是提取因果规律
"""

import json
import sqlite3
import hashlib
import networkx as nx
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CausalPattern:
    """因果模式"""
    pattern_id: str
    cause: str                          # 原因
    effect: str                         # 效果
    context: Dict[str, Any]             # 情境条件
    probability: float                  # 发生概率
    confidence: float                   # 置信度
    evidence_count: int                 # 证据数量
    first_observed: datetime
    last_observed: datetime
    examples: List[Dict]                # 典型案例
    
    def to_dict(self):
        return {
            **asdict(self),
            'first_observed': self.first_observed.isoformat(),
            'last_observed': self.last_observed.isoformat()
        }


class CausalPatternBank:
    """
    因果模式库
    
    功能：
    1. 学习因果关系：从经验中提取因果规律
    2. 预测效果：给定原因预测可能的效果
    3. 反向推理：给定效果推测可能的原因
    4. 置信度评估：根据证据强度评估因果关系的可信度
    """
    
    def __init__(self, db_path: str = "data/predictive_memory/causal.db"):
        self.db_path = db_path
        
        # 因果关系图（内存缓存）
        self.causal_graph = nx.DiGraph()
        
        # 因果模式索引
        self.pattern_index: Dict[str, CausalPattern] = {}
        
        # 初始化数据库
        self._init_db()
        
        # 加载已有模式
        self._load_patterns()
        
        logger.info(f"因果模式库初始化完成，已加载{len(self.pattern_index)}个模式")
    
    def _init_db(self):
        """初始化数据库表"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 因果模式表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS causal_patterns (
                pattern_id TEXT PRIMARY KEY,
                cause TEXT NOT NULL,
                effect TEXT NOT NULL,
                context TEXT,
                probability REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.5,
                evidence_count INTEGER DEFAULT 1,
                first_observed TIMESTAMP,
                last_observed TIMESTAMP,
                examples TEXT
            )
        ''')
        
        # 因果关系边表（用于快速查询）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS causal_edges (
                cause TEXT,
                effect TEXT,
                weight REAL,
                pattern_id TEXT,
                PRIMARY KEY (cause, effect, pattern_id)
            )
        ''')
        
        # 索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cause ON causal_patterns(cause)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_effect ON causal_patterns(effect)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_cause ON causal_edges(cause)')
        
        conn.commit()
        conn.close()
    
    def _load_patterns(self):
        """从数据库加载已有模式"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM causal_patterns')
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            pattern = CausalPattern(
                pattern_id=row[0],
                cause=row[1],
                effect=row[2],
                context=json.loads(row[3]) if row[3] else {},
                probability=row[4],
                confidence=row[5],
                evidence_count=row[6],
                first_observed=datetime.fromisoformat(row[7]),
                last_observed=datetime.fromisoformat(row[8]),
                examples=json.loads(row[9]) if row[9] else []
            )
            
            self.pattern_index[pattern.pattern_id] = pattern
            
            # 构建因果图
            self.causal_graph.add_edge(
                pattern.cause, 
                pattern.effect,
                weight=pattern.probability * pattern.confidence,
                pattern_id=pattern.pattern_id
            )
    
    def learn(self, cause: str, effect: str, context: Dict = None, example: Dict = None):
        """
        学习因果模式
        
        Args:
            cause: 原因
            effect: 效果
            context: 情境条件
            example: 具体案例
        """
        # 生成模式ID
        pattern_id = self._generate_pattern_id(cause, effect, context)
        
        if pattern_id in self.pattern_index:
            # 已存在，更新
            pattern = self.pattern_index[pattern_id]
            pattern.evidence_count += 1
            pattern.last_observed = datetime.now()
            
            # 更新概率（贝叶斯更新）
            pattern.probability = self._update_probability(pattern.probability, pattern.evidence_count)
            
            # 添加案例
            if example:
                pattern.examples.append(example)
                pattern.examples = pattern.examples[-10:]  # 保留最近10个案例
            
            # 更新置信度
            pattern.confidence = min(1.0, 0.5 + pattern.evidence_count * 0.05)
            
            # 更新因果图
            self.causal_graph[cause][effect]['weight'] = pattern.probability * pattern.confidence
            
        else:
            # 新模式
            pattern = CausalPattern(
                pattern_id=pattern_id,
                cause=cause,
                effect=effect,
                context=context or {},
                probability=0.5,
                confidence=0.5,
                evidence_count=1,
                first_observed=datetime.now(),
                last_observed=datetime.now(),
                examples=[example] if example else []
            )
            
            self.pattern_index[pattern_id] = pattern
            
            # 添加到因果图
            self.causal_graph.add_edge(
                cause, effect,
                weight=0.5 * 0.5,
                pattern_id=pattern_id
            )
        
        # 保存到数据库
        self._save_pattern(pattern)
        
        logger.debug(f"学习因果模式: {cause} → {effect}, 置信度: {pattern.confidence:.2f}")
        
        return pattern
    
    def predict_effects(self, cause: str, context: Dict = None, top_k: int = 5) -> List[Dict]:
        """
        预测效果：给定原因，预测可能的效果
        
        Args:
            cause: 原因
            context: 当前情境
            top_k: 返回前k个最可能的效果
            
        Returns:
            预测效果列表
        """
        predictions = []
        
        # 从因果图中查找所有出边
        if cause in self.causal_graph:
            for _, effect, data in self.causal_graph.out_edges(cause, data=True):
                pattern_id = data.get('pattern_id')
                if pattern_id:
                    pattern = self.pattern_index[pattern_id]
                    
                    # 情境匹配度
                    context_match = self._context_similarity(context, pattern.context)
                    
                    # 综合概率
                    probability = data['weight'] * context_match
                    
                    predictions.append({
                        'effect': effect,
                        'probability': probability,
                        'confidence': pattern.confidence,
                        'evidence_count': pattern.evidence_count,
                        'examples': pattern.examples[:3],
                        'pattern_id': pattern_id
                    })
        
        # 按概率排序
        predictions.sort(key=lambda x: x['probability'], reverse=True)
        
        return predictions[:top_k]
    
    def infer_causes(self, effect: str, context: Dict = None, top_k: int = 5) -> List[Dict]:
        """
        反向推理：给定效果，推测可能的原因
        """
        inferences = []
        
        # 从因果图中查找所有入边
        if effect in self.causal_graph:
            for cause, _, data in self.causal_graph.in_edges(effect, data=True):
                pattern_id = data.get('pattern_id')
                if pattern_id:
                    pattern = self.pattern_index[pattern_id]
                    
                    # 情境匹配度
                    context_match = self._context_similarity(context, pattern.context)
                    
                    # 反向概率（贝叶斯）
                    reverse_prob = pattern.probability * context_match
                    
                    inferences.append({
                        'cause': cause,
                        'probability': reverse_prob,
                        'confidence': pattern.confidence,
                        'evidence_count': pattern.evidence_count,
                        'pattern_id': pattern_id
                    })
        
        inferences.sort(key=lambda x: x['probability'], reverse=True)
        
        return inferences[:top_k]
    
    def find_causal_chain(self, start: str, end: str, max_depth: int = 5) -> List[List[str]]:
        """
        找到因果链：从start到end的所有可能路径
        
        例如：下雨 → 地湿 → 摔倒
        """
        try:
            paths = list(nx.all_simple_paths(
                self.causal_graph, 
                start, 
                end, 
                cutoff=max_depth
            ))
            
            # 计算每条路径的总概率
            path_probabilities = []
            for path in paths:
                prob = 1.0
                for i in range(len(path) - 1):
                    edge_data = self.causal_graph[path[i]][path[i+1]]
                    prob *= edge_data['weight']
                path_probabilities.append({
                    'path': path,
                    'probability': prob
                })
            
            path_probabilities.sort(key=lambda x: x['probability'], reverse=True)
            return path_probabilities
            
        except nx.NetworkXNoPath:
            return []
    
    def _generate_pattern_id(self, cause: str, effect: str, context: Dict) -> str:
        """生成模式ID"""
        key = f"{cause}→{effect}→{json.dumps(context, sort_keys=True)}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _update_probability(self, old_prob: float, evidence_count: int) -> float:
        """
        贝叶斯更新概率
        证据越多，概率越接近真实值
        """
        # 简化版贝叶斯更新
        alpha = 1.0  # 假设成功次数
        beta = 1.0   # 假设失败次数
        
        # 根据证据数量调整
        if evidence_count > 0:
            # 假设成功率为0.7（可以根据实际调整）
            success_rate = 0.7
            alpha = evidence_count * success_rate
            beta = evidence_count * (1 - success_rate)
        
        # 后验概率
        new_prob = alpha / (alpha + beta)
        
        # 平滑过渡
        return old_prob * 0.3 + new_prob * 0.7
    
    def _context_similarity(self, ctx1: Dict, ctx2: Dict) -> float:
        """计算情境相似度"""
        if not ctx1 or not ctx2:
            return 0.5  # 无情境信息时返回中等匹配度
        
        # 简单的键值匹配
        common_keys = set(ctx1.keys()) & set(ctx2.keys())
        if not common_keys:
            return 0.3
        
        matches = sum(1 for k in common_keys if ctx1.get(k) == ctx2.get(k))
        return matches / len(common_keys)
    
    def _save_pattern(self, pattern: CausalPattern):
        """保存模式到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO causal_patterns 
            (pattern_id, cause, effect, context, probability, confidence, 
             evidence_count, first_observed, last_observed, examples)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern.pattern_id,
            pattern.cause,
            pattern.effect,
            json.dumps(pattern.context),
            pattern.probability,
            pattern.confidence,
            pattern.evidence_count,
            pattern.first_observed.isoformat(),
            pattern.last_observed.isoformat(),
            json.dumps(pattern.examples)
        ))
        
        # 同时更新边表
        cursor.execute('''
            INSERT OR REPLACE INTO causal_edges (cause, effect, weight, pattern_id)
            VALUES (?, ?, ?, ?)
        ''', (pattern.cause, pattern.effect, pattern.probability * pattern.confidence, pattern.pattern_id))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_patterns': len(self.pattern_index),
            'unique_causes': len(set(p.cause for p in self.pattern_index.values())),
            'unique_effects': len(set(p.effect for p in self.pattern_index.values())),
            'avg_confidence': sum(p.confidence for p in self.pattern_index.values()) / len(self.pattern_index) if self.pattern_index else 0,
            'graph_nodes': self.causal_graph.number_of_nodes(),
            'graph_edges': self.causal_graph.number_of_edges()
        }
