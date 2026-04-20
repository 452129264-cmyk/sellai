#!/usr/bin/env python3
"""
预测性主动记忆系统 - 主控制器
Predictive Active Memory System (PAMS) - Main Controller

核心理念：记忆不是为了回忆过去，而是为了预测未来

功能：
1. 统一入口：所有记忆操作的主入口
2. 模式协调：协调各类模式库
3. 主动记忆：主动决定记什么、忘什么
4. 预测决策：基于记忆生成预测和建议
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict

from .causal_pattern_bank import CausalPatternBank
from .decision_pattern_bank import DecisionPatternBank
from .emotional_pattern_bank import EmotionalPatternBank
from .social_pattern_bank import SocialPatternBank
from .prediction_engine import PredictionEngine
from .meta_cognition import MetaCognition

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - PAMS - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """经验对象"""
    event: str                        # 事件描述
    outcome: str                      # 结果
    context: Dict[str, Any]           # 上下文
    emotion: Dict[str, Any]           # 情感
    importance: float                 # 重要性
    timestamp: datetime


class PredictiveMemorySystem:
    """
    预测性主动记忆系统
    
    这是系统的核心控制器，统一管理所有记忆和预测功能
    """
    
    def __init__(self, db_base_path: str = "data/predictive_memory"):
        """
        初始化预测性主动记忆系统
        
        Args:
            db_base_path: 数据库存储基础路径
        """
        self.db_base_path = db_base_path
        os.makedirs(db_base_path, exist_ok=True)
        
        # 初始化各模式库
        logger.info("初始化预测性主动记忆系统...")
        
        self.causal_bank = CausalPatternBank(f"{db_base_path}/causal.db")
        self.decision_bank = DecisionPatternBank(f"{db_base_path}/decision.db")
        self.emotional_bank = EmotionalPatternBank(f"{db_base_path}/emotional.db")
        self.social_bank = SocialPatternBank(f"{db_base_path}/social.db")
        
        # 元认知系统
        self.meta_cognition = MetaCognition(f"{db_base_path}/meta_cognition.db")
        
        # 预测引擎
        self.prediction_engine = PredictionEngine(
            causal_bank=self.causal_bank,
            decision_bank=self.decision_bank,
            emotional_bank=self.emotional_bank,
            social_bank=self.social_bank,
            meta_cognition=self.meta_cognition
        )
        
        # 记忆阈值（决定是否记住的标准）
        self.memory_threshold = 0.3
        
        logger.info("预测性主动记忆系统初始化完成")
    
    # ==================== 核心功能：记忆 ====================
    
    def remember(self, experience: Union[Experience, Dict]) -> bool:
        """
        记忆经验
        
        主动决定：
        1. 是否值得记忆
        2. 记忆到哪个模式库
        3. 提取什么模式
        
        Args:
            experience: 经验对象或字典
            
        Returns:
            是否成功记忆
        """
        # 标准化输入
        if isinstance(experience, dict):
            exp = Experience(
                event=experience.get('event', ''),
                outcome=experience.get('outcome', ''),
                context=experience.get('context', {}),
                emotion=experience.get('emotion', {}),
                importance=experience.get('importance', 0.5),
                timestamp=datetime.now()
            )
        else:
            exp = experience
        
        # 1. 计算是否值得记忆
        should_remember = self._should_remember(exp)
        
        if not should_remember['remember']:
            logger.debug(f"经验不值得记忆: {exp.event[:50]}...")
            return False
        
        # 2. 提取模式并存储到各模式库
        
        # 因果模式
        if exp.outcome and '→' in f"{exp.event}→{exp.outcome}":
            self.causal_bank.learn(
                cause=exp.event,
                effect=exp.outcome,
                context=exp.context,
                example={'event': exp.event, 'outcome': exp.outcome}
            )
        
        # 决策模式
        action = exp.context.get('action')
        if action:
            success_score = exp.importance  # 简化：用重要性代表成功度
            self.decision_bank.record(
                situation=exp.context,
                action=action,
                outcome=exp.outcome,
                success_score=success_score,
                context=exp.context
            )
        
        # 情感模式
        if exp.emotion:
            primary_emotion = exp.emotion.get('primary', 'neutral')
            intensity = exp.emotion.get('intensity', 0.5)
            
            self.emotional_bank.learn(
                event_type=exp.event,
                event_features=exp.context,
                emotion=primary_emotion,
                intensity=intensity
            )
        
        # 社交模式
        person_id = exp.context.get('person_id')
        if person_id:
            self.social_bank.record_interaction(
                person_id=person_id,
                person_name=exp.context.get('person_name', ''),
                situation=exp.event,
                behavior=exp.context.get('behavior', ''),
                outcome=exp.outcome,
                context=exp.context
            )
        
        # 3. 更新记忆重要性
        actual_importance = should_remember['importance']
        
        logger.info(f"已记忆经验: {exp.event[:50]}... (重要性: {actual_importance:.2f})")
        
        return True
    
    def _should_remember(self, experience: Experience) -> Dict:
        """
        判断是否应该记忆
        
        标准：
        1. 信息增益：能否提高预测准确率
        2. 情感重要性：情感越强烈越重要
        3. 新颖性：是否是新类型的经验
        4. 实用性：是否对决策有帮助
        """
        scores = {}
        
        # 1. 情感重要性
        emotion_importance = 0.5
        if experience.emotion:
            primary = experience.emotion.get('primary', 'neutral')
            intensity = experience.emotion.get('intensity', 0.5)
            emotion_importance = self.emotional_bank.calculate_memory_importance(
                experience.event, primary, intensity
            )
        scores['emotion'] = emotion_importance
        
        # 2. 新颖性（检查是否已有类似经验）
        novelty = 0.5
        similar = self.decision_bank.find_similar_cases(
            experience.context, 
            limit=5
        )
        if len(similar) < 3:
            novelty = 0.8  # 相似经验少，新颖性高
        scores['novelty'] = novelty
        
        # 3. 实用性（基于上下文判断）
        utility = experience.importance  # 使用传入的重要性
        scores['utility'] = utility
        
        # 综合判断
        weights = {'emotion': 0.3, 'novelty': 0.3, 'utility': 0.4}
        total_importance = sum(scores[k] * weights[k] for k in scores)
        
        should = total_importance >= self.memory_threshold
        
        return {
            'remember': should,
            'importance': total_importance,
            'scores': scores
        }
    
    # ==================== 核心功能：预测 ====================
    
    def predict(self, context: Dict, prediction_type: str = 'comprehensive') -> Dict:
        """
        预测未来
        
        基于记忆中的模式预测可能的结果
        
        Args:
            context: 预测上下文
            prediction_type: 预测类型
            
        Returns:
            预测结果
        """
        logger.info(f"开始预测: {prediction_type}")
        
        prediction = self.prediction_engine.predict(context, prediction_type)
        
        # 转换为字典返回
        return {
            'prediction_type': prediction.prediction_type,
            'content': prediction.content,
            'confidence': prediction.confidence,
            'evidence': prediction.evidence,
            'recommendations': prediction.recommendations,
            'warnings': prediction.warnings,
            'timestamp': prediction.timestamp.isoformat()
        }
    
    def recommend(self, situation: Dict, top_k: int = 3) -> List[Dict]:
        """
        推荐行动
        
        基于历史决策模式推荐成功率最高的行动
        
        Args:
            situation: 当前情境
            top_k: 返回前k个推荐
            
        Returns:
            推荐列表
        """
        recommendations = self.decision_bank.recommend(situation, top_k)
        
        return [
            {
                'action': rec.action,
                'success_rate': rec.success_rate,
                'confidence': rec.confidence,
                'evidence_count': rec.evidence_count,
                'expected_outcome': rec.expected_outcome,
                'warnings': rec.warnings
            }
            for rec in recommendations
        ]
    
    # ==================== 核心功能：遗忘 ====================
    
    def forget(self, criteria: Dict = None):
        """
        主动遗忘
        
        遗忘不是为了省空间，而是为了提高预测质量
        遗忘过时、错误、无用的模式
        
        Args:
            criteria: 遗忘标准（可选）
        """
        logger.info("执行主动遗忘...")
        
        # 1. 遗忘低置信度模式
        # 2. 遗忘长期未激活模式
        # 3. 遗忘与新模式冲突的模式
        
        # 简化实现：清理预测准确率持续低的模式
        # TODO: 实现更精细的遗忘机制
        
        logger.info("主动遗忘完成")
    
    # ==================== SellAI专用接口 ====================
    
    def record_business_opportunity(self, opportunity: Dict, outcome: str, success: bool):
        """
        记录商机经验（SellAI专用）
        
        Args:
            opportunity: 商机信息
            outcome: 结果
            success: 是否成功
        """
        experience = Experience(
            event=f"商机: {opportunity.get('product', {}).get('name', 'unknown')}",
            outcome=outcome,
            context={
                'action': 'evaluate_opportunity',
                'market': opportunity.get('market', {}),
                'competition': opportunity.get('competition', {}),
                'margin': opportunity.get('margin', 0)
            },
            emotion={'primary': 'joy' if success else 'sadness', 'intensity': 0.7 if success else 0.5},
            importance=0.8 if success else 0.6,
            timestamp=datetime.now()
        )
        
        return self.remember(experience)
    
    def predict_opportunity(self, opportunity: Dict) -> Dict:
        """
        预测商机（SellAI专用）
        
        Args:
            opportunity: 商机信息
            
        Returns:
            预测结果
        """
        return self.prediction_engine.predict_business_opportunity(opportunity)
    
    def record_user_interaction(self, user_id: str, action: str, context: Dict):
        """
        记录用户互动（SellAI专用）
        
        Args:
            user_id: 用户ID
            action: 用户行为
            context: 上下文
        """
        self.social_bank.record_interaction(
            person_id=user_id,
            person_name=context.get('user_name', ''),
            situation=context.get('situation', ''),
            behavior=action,
            outcome=context.get('outcome', ''),
            context=context
        )
    
    # ==================== 元认知接口 ====================
    
    def self_evaluate(self) -> Dict:
        """
        自我评估
        
        了解自己的知识状况、盲区、学习需求
        
        Returns:
            自我评估报告
        """
        return {
            'knowledge_domains': self.meta_cognition.get_stats(),
            'blind_spots': self.meta_cognition.identify_blind_spots(),
            'learning_suggestions': self.meta_cognition.suggest_learning(),
            'pattern_banks_status': {
                'causal': self.causal_bank.get_stats(),
                'decision': self.decision_bank.get_stats(),
                'emotional': self.emotional_bank.get_stats(),
                'social': self.social_bank.get_stats()
            },
            'prediction_engine_status': self.prediction_engine.get_stats()
        }
    
    def get_confidence(self, prediction_type: str, context: Dict = None) -> float:
        """
        获取置信度
        
        在做出预测前，先评估自己对这个预测有多大把握
        
        Args:
            prediction_type: 预测类型
            context: 上下文
            
        Returns:
            置信度 0-1
        """
        eval_result = self.meta_cognition.admit_uncertainty({
            'domain': prediction_type,
            'context': context or {}
        })
        
        return eval_result.get('confidence', 0.5)
    
    # ==================== 工具方法 ====================
    
    def export_knowledge(self, output_path: str = None):
        """
        导出知识
        
        将所有模式库导出为JSON文件，便于迁移和备份
        
        Args:
            output_path: 输出路径
        """
        if output_path is None:
            output_path = f"{self.db_base_path}/knowledge_export.json"
        
        knowledge = {
            'export_time': datetime.now().isoformat(),
            'causal_patterns': {k: v.to_dict() for k, v in self.causal_bank.patterns.items()},
            'decision_patterns': {k: v.to_dict() for k, v in self.decision_bank.patterns.items()},
            'stats': self.self_evaluate()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"知识已导出到: {output_path}")
        
        return output_path
    
    def get_stats(self) -> Dict:
        """获取系统统计信息"""
        return {
            'system': 'Predictive Active Memory System (PAMS)',
            'version': '1.0.0',
            'pattern_counts': {
                'causal': len(self.causal_bank.patterns),
                'decision': len(self.decision_bank.patterns),
                'emotional': len(self.emotional_bank.patterns),
                'social': len(self.social_bank.person_profiles)
            },
            'memory_threshold': self.memory_threshold,
            'meta_cognition': self.meta_cognition.get_stats()
        }


# ==================== 便捷函数 ====================

def create_predictive_memory(db_path: str = "data/predictive_memory") -> PredictiveMemorySystem:
    """
    创建预测性主动记忆系统实例
    
    Args:
        db_path: 数据库路径
        
    Returns:
        PredictiveMemorySystem实例
    """
    return PredictiveMemorySystem(db_path)


# ==================== 示例用法 ====================

if __name__ == "__main__":
    # 创建系统实例
    memory = create_predictive_memory()
    
    # 记忆一条经验
    memory.remember({
        'event': '用户购买了高价商品',
        'outcome': '订单完成',
        'context': {'action': 'recommend_premium', 'product': 'iPhone 15'},
        'emotion': {'primary': 'joy', 'intensity': 0.8},
        'importance': 0.9
    })
    
    # 预测
    prediction = memory.predict({
        'event': '用户浏览高端手机',
        'context': {'price_range': 'high'}
    })
    
    print(f"预测置信度: {prediction['confidence']}")
    print(f"建议: {prediction['recommendations']}")
    
    # 自我评估
    eval_result = memory.self_evaluate()
    print(f"知识盲区: {eval_result['blind_spots']}")
