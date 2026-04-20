"""
AI风险评估模型模块
实现基于机器学习的风险评估
"""

import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict
import logging

from ..database.models import RiskLevel

logger = logging.getLogger(__name__)

class RiskAssessor:
    """AI风险评估器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 风险特征权重配置
        self.feature_weights = self.config.get("feature_weights", {
            "violation_count": 0.3,
            "risk_level_sum": 0.4,
            "confidence_avg": 0.2,
            "text_length_factor": 0.1
        })
        
        # 风险等级阈值
        self.risk_thresholds = self.config.get("risk_thresholds", {
            "low": 0.3,
            "medium": 0.5,
            "high": 0.75,
            "critical": 0.9
        })
        
        # 行业风险因子
        self.industry_factors = self.config.get("industry_factors", {
            "healthcare": 1.3,
            "finance": 1.4,
            "pharmaceutical": 1.5,
            "education": 1.2,
            "beauty": 1.1,
            "fitness": 1.1,
            "technology": 1.0,
            "real_estate": 1.1,
            "fashion": 1.0,
            "food": 1.0,
            "default": 1.0
        })
        
        # 内容类型因子
        self.content_type_factors = self.config.get("content_type_factors", {
            "advertisement": 1.3,
            "product_description": 1.1,
            "social_media": 1.0,
            "email_marketing": 1.2,
            "web_content": 1.0,
            "document": 0.9,
            "default": 1.0
        })
        
        # 国家风险因子（不同国家法规严格程度）
        self.country_factors = self.config.get("country_factors", {
            "US": 1.2,    # 美国广告法规严格
            "EU": 1.4,    # 欧盟GDPR非常严格
            "CN": 1.3,    # 中国广告法严格
            "JP": 1.1,    # 日本商品表示法
            "KR": 1.1,    # 韩国电子商务法
            "GB": 1.2,    # 英国广告标准
            "DE": 1.2,    # 德国广告法
            "FR": 1.1,    # 法国消费者保护法
            "AU": 1.1,    # 澳大利亚消费者法
            "CA": 1.1,    # 加拿大广告标准
            "SG": 1.0,    # 新加坡
            "default": 1.0
        })
        
        logger.info("RiskAssessor initialized")
    
    def assess_risk(self, text: str, country_code: str, content_type: str,
                   industry: Optional[str] = None, 
                   violations: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        评估文本风险
        Args:
            text: 待评估文本
            country_code: 目标国家代码
            content_type: 内容类型
            industry: 行业分类（可选）
            violations: 已检测到的违规列表（可选）
        Returns:
            风险评估结果
        """
        try:
            # 提取风险特征
            features = self._extract_features(text, violations)
            
            # 计算基础风险分数
            base_score = self._calculate_base_score(features)
            
            # 应用调整因子
            adjusted_score = self._apply_adjustment_factors(
                base_score, country_code, content_type, industry, text
            )
            
            # 确定风险等级
            risk_level = self._determine_risk_level(adjusted_score)
            
            # 生成风险说明
            risk_explanation = self._generate_explanation(
                risk_level, adjusted_score, features, violations
            )
            
            result = {
                "risk_score": round(adjusted_score, 4),
                "risk_level": risk_level.value,
                "features": features,
                "explanation": risk_explanation,
                "recommendations": self._generate_recommendations(risk_level, features)
            }
            
            logger.debug(f"风险评估完成: score={adjusted_score:.4f}, level={risk_level.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"风险评估失败: {str(e)}")
            # 返回默认风险评估
            return {
                "risk_score": 0.5,
                "risk_level": RiskLevel.MEDIUM.value,
                "features": {},
                "explanation": "风险评估过程中发生错误",
                "recommendations": ["请人工审核内容"]
            }
    
    def _extract_features(self, text: str, violations: Optional[List[Dict]]) -> Dict[str, float]:
        """提取风险特征"""
        features = {}
        
        # 文本长度特征
        text_length = len(text)
        features["text_length"] = text_length
        features["text_length_factor"] = min(1.0, text_length / 10000)  # 归一化
        
        # 违规相关特征
        if violations:
            features["violation_count"] = len(violations)
            
            # 风险等级总和（数值化）
            risk_level_values = []
            for violation in violations:
                risk_level = violation.get("risk_level", "medium")
                risk_value = self._risk_level_to_value(risk_level)
                risk_level_values.append(risk_value)
            
            features["risk_level_sum"] = sum(risk_level_values)
            features["risk_level_avg"] = np.mean(risk_level_values) if risk_level_values else 0
            
            # 置信度特征
            confidences = [v.get("confidence", 0.5) for v in violations]
            features["confidence_avg"] = np.mean(confidences) if confidences else 0.5
            features["confidence_max"] = max(confidences) if confidences else 0.5
        
        else:
            features["violation_count"] = 0
            features["risk_level_sum"] = 0
            features["risk_level_avg"] = 0
            features["confidence_avg"] = 0.5
            features["confidence_max"] = 0.5
        
        # 文本复杂度特征（简化实现）
        features["word_count"] = len(text.split())
        features["avg_word_length"] = np.mean([len(word) for word in text.split()]) if text.split() else 0
        
        # 特殊字符比例
        special_chars = sum(1 for char in text if not char.isalnum() and char not in ' ,.')
        features["special_char_ratio"] = special_chars / text_length if text_length > 0 else 0
        
        return features
    
    def _calculate_base_score(self, features: Dict[str, float]) -> float:
        """计算基础风险分数"""
        score = 0.0
        total_weight = 0.0
        
        # 违规数量特征
        violation_count = features.get("violation_count", 0)
        if violation_count > 0:
            violation_score = min(1.0, violation_count / 10)  # 最多10个违规
            weight = self.feature_weights.get("violation_count", 0.3)
            score += violation_score * weight
            total_weight += weight
        
        # 风险等级特征
        risk_level_sum = features.get("risk_level_sum", 0)
        if risk_level_sum > 0:
            # 归一化处理
            max_risk_sum = 4.0 * violation_count if violation_count > 0 else 4.0
            risk_level_score = risk_level_sum / max_risk_sum
            weight = self.feature_weights.get("risk_level_sum", 0.4)
            score += risk_level_score * weight
            total_weight += weight
        
        # 置信度特征
        confidence_avg = features.get("confidence_avg", 0.5)
        weight = self.feature_weights.get("confidence_avg", 0.2)
        score += confidence_avg * weight
        total_weight += weight
        
        # 文本长度特征
        text_length_factor = features.get("text_length_factor", 0.0)
        weight = self.feature_weights.get("text_length_factor", 0.1)
        score += text_length_factor * weight
        total_weight += weight
        
        # 归一化分数
        if total_weight > 0:
            normalized_score = score / total_weight
        else:
            normalized_score = 0.5
        
        return min(1.0, max(0.0, normalized_score))
    
    def _apply_adjustment_factors(self, base_score: float, country_code: str,
                                 content_type: str, industry: Optional[str],
                                 text: str) -> float:
        """应用调整因子"""
        adjusted_score = base_score
        
        # 国家因子
        country_factor = self.country_factors.get(country_code, 
                                                 self.country_factors.get("default", 1.0))
        adjusted_score *= country_factor
        
        # 内容类型因子
        content_factor = self.content_type_factors.get(content_type,
                                                      self.content_type_factors.get("default", 1.0))
        adjusted_score *= content_factor
        
        # 行业因子
        if industry:
            industry_factor = self.industry_factors.get(industry.lower(),
                                                       self.industry_factors.get("default", 1.0))
            adjusted_score *= industry_factor
        
        # 文本内容特定因子
        text_specific_factor = self._calculate_text_specific_factor(text)
        adjusted_score *= text_specific_factor
        
        # 确保在0-1范围内
        return min(1.0, max(0.0, adjusted_score))
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """确定风险等级"""
        thresholds = self.risk_thresholds
        
        if risk_score >= thresholds.get("critical", 0.9):
            return RiskLevel.CRITICAL
        elif risk_score >= thresholds.get("high", 0.75):
            return RiskLevel.HIGH
        elif risk_score >= thresholds.get("medium", 0.5):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_explanation(self, risk_level: RiskLevel, risk_score: float,
                            features: Dict[str, float], 
                            violations: Optional[List[Dict]]) -> str:
        """生成风险说明"""
        explanation_parts = []
        
        # 风险等级说明
        level_explanations = {
            RiskLevel.CRITICAL: "内容存在严重合规风险，可能涉及违法行为",
            RiskLevel.HIGH: "内容存在高风险违规，需要重点审查",
            RiskLevel.MEDIUM: "内容存在中度风险，建议优化相关表述",
            RiskLevel.LOW: "内容风险较低，符合基本合规要求"
        }
        
        explanation_parts.append(level_explanations.get(risk_level, "风险评估完成"))
        
        # 违规数量说明
        violation_count = features.get("violation_count", 0)
        if violation_count > 0:
            explanation_parts.append(f"检测到{violation_count}处违规")
            
            # 高风险违规说明
            if violations:
                critical_violations = [v for v in violations 
                                      if v.get("risk_level") == "critical"]
                if critical_violations:
                    explanation_parts.append(f"包含{len(critical_violations)}处紧急风险")
        
        # 风险分数说明
        if risk_score >= 0.8:
            explanation_parts.append("风险分数较高，建议全面审查")
        elif risk_score >= 0.6:
            explanation_parts.append("风险分数适中，建议重点修改")
        
        return "。".join(explanation_parts)
    
    def _generate_recommendations(self, risk_level: RiskLevel, 
                                 features: Dict[str, float]) -> List[str]:
        """生成修改建议"""
        recommendations = []
        
        # 基于风险等级的建议
        if risk_level == RiskLevel.CRITICAL:
            recommendations.extend([
                "立即停止发布该内容",
                "咨询法律专家进行全面评估",
                "重新编写所有高风险部分"
            ])
        elif risk_level == RiskLevel.HIGH:
            recommendations.extend([
                "重点审查高风险违规部分",
                "修改或删除绝对化用语",
                "添加必要的免责声明"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend([
                "优化相关表述，避免误导",
                "检查数据引用是否准确",
                "确保所有声明有据可查"
            ])
        elif risk_level == RiskLevel.LOW:
            recommendations.extend([
                "保持当前合规水平",
                "定期检查法规更新",
                "建立合规审查流程"
            ])
        
        # 基于特征的建议
        violation_count = features.get("violation_count", 0)
        if violation_count >= 5:
            recommendations.append("违规数量较多，建议分阶段逐步优化")
        
        text_length = features.get("text_length", 0)
        if text_length > 5000:
            recommendations.append("文本较长，建议分段处理，重点关注关键声明部分")
        
        return recommendations
    
    def _risk_level_to_value(self, risk_level: str) -> float:
        """风险等级转换为数值"""
        mapping = {
            "low": 1.0,
            "medium": 2.0,
            "high": 3.0,
            "critical": 4.0
        }
        return mapping.get(risk_level.lower(), 2.0)
    
    def _calculate_text_specific_factor(self, text: str) -> float:
        """计算文本特定因子（简化实现）"""
        # 检查高风险关键词
        high_risk_keywords = [
            "免费", "保证", "治愈", "最佳", "第一",
            "免费", "guarantee", "cure", "best", "top"
        ]
        
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in high_risk_keywords 
                           if keyword.lower() in text_lower)
        
        # 计算因子：关键词越多，风险越高
        if keyword_count == 0:
            return 1.0
        elif keyword_count <= 3:
            return 1.1
        elif keyword_count <= 6:
            return 1.2
        else:
            return 1.3
    
    def batch_assess(self, texts: List[str], country_codes: List[str],
                    content_types: List[str], 
                    industries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """批量风险评估"""
        results = []
        
        for i, text in enumerate(texts):
            country_code = country_codes[i] if i < len(country_codes) else country_codes[-1]
            content_type = content_types[i] if i < len(content_types) else content_types[-1]
            industry = industries[i] if industries and i < len(industries) else None
            
            result = self.assess_risk(text, country_code, content_type, industry)
            results.append(result)
        
        return results
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.config.update(new_config)
        
        # 更新各因子配置
        if "feature_weights" in new_config:
            self.feature_weights.update(new_config["feature_weights"])
        
        if "risk_thresholds" in new_config:
            self.risk_thresholds.update(new_config["risk_thresholds"])
        
        if "industry_factors" in new_config:
            self.industry_factors.update(new_config["industry_factors"])
        
        if "content_type_factors" in new_config:
            self.content_type_factors.update(new_config["content_type_factors"])
        
        if "country_factors" in new_config:
            self.country_factors.update(new_config["country_factors"])
        
        logger.info("RiskAssessor配置已更新")