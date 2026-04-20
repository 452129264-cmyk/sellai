#!/usr/bin/env python3
"""
预测引擎
Prediction Engine

功能：综合各类模式，生成预测和建议
核心：整合因果、决策、情感、社交模式，做出智能预测
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """预测结果"""
    prediction_type: str              # 预测类型
    content: Dict[str, Any]           # 预测内容
    confidence: float                 # 置信度
    evidence: List[Dict]              # 证据
    recommendations: List[str]        # 建议
    warnings: List[str]               # 警告
    timestamp: datetime


class PredictionEngine:
    """
    预测引擎
    
    功能：
    1. 综合预测：整合多种模式库
    2. 多场景预测：支持不同预测场景
    3. 置信度评估：评估预测可信度
    4. 建议生成：生成行动建议
    5. LLM增强：使用DeepSeek API进行深度推理
    """
    
    def __init__(self, causal_bank=None, decision_bank=None, 
                 emotional_bank=None, social_bank=None, meta_cognition=None,
                 llm_client=None):
        """
        初始化预测引擎
        
        Args:
            causal_bank: 因果模式库
            decision_bank: 决策模式库
            emotional_bank: 情感模式库
            social_bank: 社交模式库
            meta_cognition: 元认知系统
            llm_client: LLM客户端（DeepSeek）
        """
        self.causal_bank = causal_bank
        self.decision_bank = decision_bank
        self.emotional_bank = emotional_bank
        self.social_bank = social_bank
        self.meta_cognition = meta_cognition
        self.llm_client = llm_client
        
        # 如果没有传入LLM客户端，尝试自动加载
        if self.llm_client is None:
            try:
                from src.api_config import get_deepseek_client
                self.llm_client = get_deepseek_client()
                logger.info("已自动加载DeepSeek客户端")
            except Exception as e:
                logger.warning(f"DeepSeek客户端加载失败: {e}，将使用规则引擎")
        
        # 预测类型权重
        self.type_weights = {
            'causal': 0.3,
            'decision': 0.3,
            'emotional': 0.2,
            'social': 0.2
        }
        
        logger.info("预测引擎初始化完成")
    
    def predict(self, context: Dict, prediction_type: str = 'comprehensive') -> Prediction:
        """
        综合预测
        
        Args:
            context: 预测上下文
            prediction_type: 预测类型
                - 'comprehensive': 综合预测（使用所有模式库）
                - 'causal': 因果预测
                - 'decision': 决策预测
                - 'emotional': 情感预测
                - 'social': 社交预测
            
        Returns:
            预测结果
        """
        predictions = {}
        evidence = []
        recommendations = []
        warnings = []
        
        # 1. 因果预测
        if prediction_type in ['comprehensive', 'causal'] and self.causal_bank:
            cause = context.get('cause') or context.get('event')
            if cause:
                causal_result = self.causal_bank.predict_effects(cause, context)
                if causal_result:
                    predictions['causal'] = causal_result
                    evidence.append({
                        'type': 'causal',
                        'source': '因果模式库',
                        'count': len(causal_result)
                    })
        
        # 2. 决策预测
        if prediction_type in ['comprehensive', 'decision'] and self.decision_bank:
            situation = context.get('situation', context)
            action = context.get('action')
            
            if action:
                # 预测特定行动的结果
                decision_result = self.decision_bank.predict_outcome(situation, action)
                if decision_result:
                    predictions['decision'] = decision_result
            else:
                # 推荐行动
                recommendations_result = self.decision_bank.recommend(situation)
                if recommendations_result:
                    predictions['decision'] = {
                        'recommendations': [r.__dict__ for r in recommendations_result]
                    }
            
            if 'decision' in predictions:
                evidence.append({
                    'type': 'decision',
                    'source': '决策模式库',
                    'count': len(predictions.get('decision', {}).get('recommendations', []))
                })
        
        # 3. 情感预测
        if prediction_type in ['comprehensive', 'emotional'] and self.emotional_bank:
            event_type = context.get('event_type') or context.get('event')
            if event_type:
                emotional_result = self.emotional_bank.predict_emotion(event_type)
                if emotional_result:
                    predictions['emotional'] = emotional_result
                    evidence.append({
                        'type': 'emotional',
                        'source': '情感模式库',
                        'count': len(emotional_result)
                    })
        
        # 4. 社交预测
        if prediction_type in ['comprehensive', 'social'] and self.social_bank:
            person_id = context.get('person_id')
            situation = context.get('social_situation') or context.get('situation')
            
            if person_id and situation:
                social_result = self.social_bank.predict_behavior(person_id, situation)
                if social_result:
                    predictions['social'] = social_result
                    evidence.append({
                        'type': 'social',
                        'source': '社交模式库',
                        'count': len(social_result)
                    })
        
        # 5. 综合置信度
        confidence = self._calculate_comprehensive_confidence(predictions)
        
        # 6. 元认知评估
        if self.meta_cognition:
            meta_eval = self.meta_cognition.evaluate({
                'prediction_type': prediction_type,
                'evidence_count': sum(e.get('count', 0) for e in evidence)
            })
            confidence = meta_eval.get('overall_confidence', confidence)
            
            # 添加元认知建议
            if meta_eval.get('uncertainty_level') in ['high', 'very_high']:
                warnings.append(f"预测不确定性{meta_eval['uncertainty_level']}，建议谨慎参考")
        
        # 7. 生成建议
        recommendations = self._generate_recommendations(predictions, context)
        
        # 7.5 LLM增强（如果可用）
        if self.llm_client and recommendations:
            try:
                llm_insight = self._enhance_with_llm(predictions, context)
                if llm_insight:
                    recommendations.insert(0, f"[AI洞察] {llm_insight}")
            except Exception as e:
                logger.warning(f"LLM增强失败: {e}")
        
        # 8. 生成警告
        warnings.extend(self._generate_warnings(predictions))
        
        return Prediction(
            prediction_type=prediction_type,
            content=predictions,
            confidence=confidence,
            evidence=evidence,
            recommendations=recommendations,
            warnings=warnings,
            timestamp=datetime.now()
        )
    
    def predict_business_opportunity(self, opportunity_data: Dict) -> Prediction:
        """
        商机预测（SellAI专用）
        
        Args:
            opportunity_data: 商机数据
                - product: 产品信息
                - market: 市场信息
                - competition: 竞争信息
                
        Returns:
            商机预测结果
        """
        context = {
            'event': opportunity_data.get('product', {}).get('category'),
            'situation': {
                'market': opportunity_data.get('market', {}),
                'competition': opportunity_data.get('competition', {})
            }
        }
        
        # 综合预测
        prediction = self.predict(context, 'comprehensive')
        
        # 商机专用分析
        business_analysis = self._analyze_business_opportunity(opportunity_data, prediction)
        
        # 合并结果
        prediction.content['business_analysis'] = business_analysis
        
        # 商机专用建议
        prediction.recommendations.extend(
            self._generate_business_recommendations(business_analysis)
        )
        
        return prediction
    
    def predict_user_behavior(self, user_id: str, action: str, context: Dict = None) -> Prediction:
        """
        用户行为预测（SellAI专用）
        
        Args:
            user_id: 用户ID
            action: 用户行为
            context: 上下文
            
        Returns:
            行为预测结果
        """
        prediction_context = {
            'person_id': user_id,
            'action': action,
            'situation': context or {}
        }
        
        return self.predict(prediction_context, 'social')
    
    def _calculate_comprehensive_confidence(self, predictions: Dict) -> float:
        """计算综合置信度"""
        if not predictions:
            return 0.0
        
        confidences = []
        
        for pred_type, pred_data in predictions.items():
            if pred_type == 'causal' and pred_data:
                # 因果预测置信度：基于证据数量
                avg_evidence = sum(p.get('evidence_count', 0) for p in pred_data) / len(pred_data)
                confidences.append(min(1.0, avg_evidence / 10) * self.type_weights.get(pred_type, 0.25))
            
            elif pred_type == 'decision' and pred_data:
                # 决策预测置信度：基于成功率
                if 'success_probability' in pred_data:
                    confidences.append(pred_data['success_probability'] * self.type_weights.get(pred_type, 0.25))
                elif 'recommendations' in pred_data:
                    avg_success = sum(r.get('success_rate', 0.5) for r in pred_data['recommendations']) / len(pred_data['recommendations'])
                    confidences.append(avg_success * self.type_weights.get(pred_type, 0.25))
            
            elif pred_type == 'emotional' and pred_data:
                # 情感预测置信度：基于情感权重
                avg_weight = sum(p.get('emotion_weight', 1.0) for p in pred_data) / len(pred_data)
                confidences.append(min(1.0, avg_weight / 2) * self.type_weights.get(pred_type, 0.25))
            
            elif pred_type == 'social' and pred_data:
                # 社交预测置信度：基于预测概率
                avg_prob = sum(p.get('probability', 0.5) for p in pred_data) / len(pred_data)
                confidences.append(avg_prob * self.type_weights.get(pred_type, 0.25))
        
        return sum(confidences) if confidences else 0.5
    
    def _generate_recommendations(self, predictions: Dict, context: Dict) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 因果建议
        if 'causal' in predictions and predictions['causal']:
            top_effect = predictions['causal'][0]
            recommendations.append(f"预期效果: {top_effect['effect']}（概率{top_effect['probability']:.0%}）")
        
        # 决策建议
        if 'decision' in predictions:
            decision_data = predictions['decision']
            if 'recommendations' in decision_data and decision_data['recommendations']:
                top_rec = decision_data['recommendations'][0]
                recommendations.append(f"建议行动: {top_rec['action']}（成功率{top_rec['success_rate']:.0%}）")
        
        # 情感建议
        if 'emotional' in predictions and predictions['emotional']:
            top_emotion = predictions['emotional'][0]
            if top_emotion['probability'] > 0.5:
                recommendations.append(f"预期情感: {top_emotion['emotion']}（强度{top_emotion['expected_intensity']:.0%}）")
        
        # 社交建议
        if 'social' in predictions and predictions['social']:
            top_behavior = predictions['social'][0]
            recommendations.append(f"预期行为: {top_behavior['behavior']}（概率{top_behavior['probability']:.0%}）")
        
        return recommendations
    
    def _generate_warnings(self, predictions: Dict) -> List[str]:
        """生成警告"""
        warnings = []
        
        # 检查低置信度预测
        for pred_type, pred_data in predictions.items():
            if pred_type == 'decision' and pred_data:
                if 'recommendations' in pred_data:
                    for rec in pred_data['recommendations']:
                        if rec.get('success_rate', 1) < 0.5:
                            warnings.append(f"行动 '{rec['action']}' 历史成功率较低")
        
        return warnings
    
    def _analyze_business_opportunity(self, data: Dict, prediction: Prediction) -> Dict:
        """分析商机"""
        analysis = {
            'overall_score': 0,
            'risk_level': 'medium',
            'key_factors': [],
            'competitive_advantage': None,
            'market_potential': None
        }
        
        # 基于预测内容分析
        if prediction.confidence > 0.7:
            analysis['overall_score'] = 80
            analysis['risk_level'] = 'low'
        elif prediction.confidence > 0.5:
            analysis['overall_score'] = 60
            analysis['risk_level'] = 'medium'
        else:
            analysis['overall_score'] = 40
            analysis['risk_level'] = 'high'
        
        # 提取关键因素
        if 'causal' in prediction.content:
            for effect in prediction.content['causal'][:3]:
                analysis['key_factors'].append(f"可能影响: {effect['effect']}")
        
        return analysis
    
    def _generate_business_recommendations(self, analysis: Dict) -> List[str]:
        """生成商机建议"""
        recommendations = []
        
        if analysis['overall_score'] >= 70:
            recommendations.append("商机质量较高，建议积极跟进")
        elif analysis['overall_score'] >= 50:
            recommendations.append("商机质量中等，建议谨慎评估")
        else:
            recommendations.append("商机风险较高，建议深入调研后再决定")
        
        if analysis['risk_level'] == 'high':
            recommendations.append("风险较高，建议制定风险应对预案")
        
        return recommendations
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'type_weights': self.type_weights,
            'banks_status': {
                'causal': self.causal_bank is not None,
                'decision': self.decision_bank is not None,
                'emotional': self.emotional_bank is not None,
                'social': self.social_bank is not None,
                'meta_cognition': self.meta_cognition is not None
            },
            'llm_enabled': self.llm_client is not None
        }
    
    def _enhance_with_llm(self, predictions: Dict, context: Dict) -> Optional[str]:
        """
        使用LLM增强预测建议
        
        Args:
            predictions: 预测结果
            context: 上下文
            
        Returns:
            LLM生成的洞察
        """
        if not self.llm_client:
            return None
        
        # 构建提示词
        prompt = f"""基于以下预测结果，生成一条简洁的洞察建议（不超过50字）：

预测结果: {json.dumps(predictions, ensure_ascii=False, indent=2)[:500]}

上下文: {json.dumps(context, ensure_ascii=False)[:200]}

要求：直接给出洞察，不要解释过程。"""
        
        try:
            response = self.llm_client.chat_simple(prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"LLM增强失败: {e}")
            return None
