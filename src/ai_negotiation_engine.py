"""
AI自主商务洽谈引擎
支持AI-to-AI自动谈判，包括报价生成、还价分析、条款协商、风险评估等功能。
集成永久统一佣金规则（全行业全球通用）和邀请裂变规则。
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import sqlite3
from enum import Enum

# 导入独立的佣金计算器
from .commission_calculator import CommissionCalculator


class NegotiationStrategy(Enum):
    """谈判策略类型"""
    COMPETITIVE = "competitive"      # 竞争型：争取最大利益
    COOPERATIVE = "cooperative"      # 合作型：寻求双赢
    COMPROMISING = "compromising"    # 妥协型：各退一步
    ACCOMMODATING = "accommodating"  # 顺应型：优先满足对方
    AVOIDING = "avoiding"            # 回避型：暂时回避冲突


class NegotiationStage(Enum):
    """谈判阶段"""
    INITIAL_CONTACT = "initial_contact"      # 初次接触
    NEEDS_ANALYSIS = "needs_analysis"        # 需求分析
    PROPOSAL = "proposal"                    # 方案提议
    NEGOTIATION = "negotiation"              # 协商谈判
    AGREEMENT = "agreement"                  # 达成协议
    FINAL_REVIEW = "final_review"            # 终审确认


class NegotiationScenario(Enum):
    """谈判场景类型"""
    PRICE_NEGOTIATION = "price_negotiation"          # 价格协商
    TERMS_MODIFICATION = "terms_modification"        # 条款修改
    COOPERATION_MODE = "cooperation_mode"            # 合作方式
    DELIVERY_TIMING = "delivery_timing"              # 交付时间
    QUALITY_ASSURANCE = "quality_assurance"          # 质量保证
    PAYMENT_TERMS = "payment_terms"                  # 付款条件


class AINegotiationEngine:
    """AI商务谈判引擎"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化谈判引擎
        
        Args:
            db_path: 共享状态库路径
        """
        self.db_path = db_path
        self.strategy_library = self._load_strategy_library()
        self.scenario_templates = self._load_scenario_templates()
        self.commission_calculator = CommissionCalculator()
        
    def _load_strategy_library(self) -> Dict[str, Dict[str, Any]]:
        """加载谈判策略库"""
        return {
            "competitive": {
                "description": "竞争型策略，争取最大利益",
                "concession_rate": 0.1,  # 让步幅度小
                "risk_tolerance": "low",
                "communication_style": "assertive",
                "typical_phrases": [
                    "这是我们的底线价格",
                    "考虑到市场行情，这个报价已经很合理了",
                    "我们需要确保合理的利润率"
                ]
            },
            "cooperative": {
                "description": "合作型策略，寻求双赢",
                "concession_rate": 0.3,
                "risk_tolerance": "medium",
                "communication_style": "collaborative",
                "typical_phrases": [
                    "我们理解您的需求，一起找到解决方案",
                    "长期合作比单次交易更重要",
                    "我们可以调整方案来满足双方需求"
                ]
            },
            "compromising": {
                "description": "妥协型策略，各退一步",
                "concession_rate": 0.5,
                "risk_tolerance": "medium",
                "communication_style": "diplomatic",
                "typical_phrases": [
                    "我们双方都做出一些让步",
                    "折中方案可能对双方都公平",
                    "各让一步，达成协议"
                ]
            },
            "accommodating": {
                "description": "顺应型策略，优先满足对方",
                "concession_rate": 0.7,
                "risk_tolerance": "high",
                "communication_style": "accommodating",
                "typical_phrases": [
                    "我们愿意调整以满足您的需求",
                    "建立良好关系是我们的优先考虑",
                    "我们可以接受您的条款"
                ]
            },
            "avoiding": {
                "description": "回避型策略，暂时回避冲突",
                "concession_rate": 0.0,
                "risk_tolerance": "low",
                "communication_style": "evasive",
                "typical_phrases": [
                    "这个问题我们可以稍后再讨论",
                    "先聚焦在其他条款上",
                    "我们还需要更多时间考虑"
                ]
            }
        }
    
    def _load_scenario_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载谈判场景模板"""
        return {
            "price_negotiation": {
                "description": "价格协商场景",
                "key_parameters": ["base_price", "target_price", "quantity", "market_price"],
                "negotiation_points": ["unit_price", "bulk_discount", "payment_terms_discount"],
                "success_criteria": "价格差异在15%以内"
            },
            "terms_modification": {
                "description": "条款修改场景",
                "key_parameters": ["original_terms", "requested_changes", "legal_constraints"],
                "negotiation_points": ["payment_schedule", "delivery_penalties", "warranty_period"],
                "success_criteria": "核心条款达成一致"
            },
            "cooperation_mode": {
                "description": "合作方式场景",
                "key_parameters": ["business_type", "cooperation_duration", "exclusivity"],
                "negotiation_points": ["commission_rate", "territory_rights", "minimum_order_quantity"],
                "success_criteria": "合作模式清晰可行"
            },
            "delivery_timing": {
                "description": "交付时间场景",
                "key_parameters": ["requested_delivery", "production_capacity", "logistics_time"],
                "negotiation_points": ["phased_delivery", "expedited_fee", "penalty_for_delay"],
                "success_criteria": "交付时间可接受"
            },
            "quality_assurance": {
                "description": "质量保证场景",
                "key_parameters": ["quality_standards", "inspection_process", "rejection_criteria"],
                "negotiation_points": ["acceptance_criteria", "sampling_rate", "rework_process"],
                "success_criteria": "质量条款明确"
            },
            "payment_terms": {
                "description": "付款条件场景",
                "key_parameters": ["payment_method", "credit_period", "deposit_required"],
                "negotiation_points": ["advance_payment", "progress_payments", "retention_amount"],
                "success_criteria": "付款条件安全可行"
            }
        }
    
    def analyze_negotiation_context(self, 
                                  resource_a: Dict[str, Any], 
                                  resource_b: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析谈判上下文
        
        Args:
            resource_a: 资源A信息（供应方）
            resource_b: 资源B信息（需求方）
            
        Returns:
            谈判上下文分析结果
        """
        # 确定谈判场景
        scenario = self._identify_scenario(resource_a, resource_b)
        
        # 确定谈判策略
        strategy = self._determine_strategy(resource_a, resource_b, scenario)
        
        # 识别关键差异点
        differences = self._identify_differences(resource_a, resource_b)
        
        # 评估谈判难度
        difficulty = self._assess_difficulty(resource_a, resource_b, differences)
        
        return {
            "scenario": scenario.value,
            "strategy": strategy.value,
            "differences": differences,
            "difficulty_level": difficulty,
            "timestamp": datetime.now().isoformat(),
            "parties": {
                "party_a": {
                    "id": resource_a.get("id"),
                    "type": resource_a.get("resource_type"),
                    "industry": resource_a.get("industry")
                },
                "party_b": {
                    "id": resource_b.get("id"),
                    "type": resource_b.get("resource_type"),
                    "industry": resource_b.get("industry")
                }
            }
        }
    
    def _identify_scenario(self, resource_a: Dict[str, Any], resource_b: Dict[str, Any]) -> NegotiationScenario:
        """识别谈判场景"""
        resource_type_a = resource_a.get("resource_type", "").lower()
        resource_type_b = resource_b.get("resource_type", "").lower()
        
        # 根据资源类型判断场景
        if "supply" in resource_type_a and "demand" in resource_type_b:
            return NegotiationScenario.PRICE_NEGOTIATION
        elif "合作" in resource_type_a or "cooperation" in resource_type_a:
            return NegotiationScenario.COOPERATION_MODE
        elif "交付" in resource_type_a or "delivery" in resource_type_a:
            return NegotiationScenario.DELIVERY_TIMING
        elif "付款" in resource_type_a or "payment" in resource_type_a:
            return NegotiationScenario.PAYMENT_TERMS
        elif "质量" in resource_type_a or "quality" in resource_type_a:
            return NegotiationScenario.QUALITY_ASSURANCE
        else:
            return NegotiationScenario.TERMS_MODIFICATION
    
    def _determine_strategy(self, 
                          resource_a: Dict[str, Any], 
                          resource_b: Dict[str, Any],
                          scenario: NegotiationScenario) -> NegotiationStrategy:
        """确定谈判策略"""
        # 基于供需关系、历史合作等因素确定策略
        a_strength = self._calculate_bargaining_power(resource_a)
        b_strength = self._calculate_bargaining_power(resource_b)
        
        if a_strength > b_strength * 2:
            return NegotiationStrategy.COMPETITIVE
        elif b_strength > a_strength * 2:
            return NegotiationStrategy.ACCOMMODATING
        elif abs(a_strength - b_strength) < 0.2:
            return NegotiationStrategy.COOPERATIVE
        else:
            return NegotiationStrategy.COMPROMISING
    
    def _calculate_bargaining_power(self, resource: Dict[str, Any]) -> float:
        """计算议价能力（0-1之间）"""
        power = 0.5  # 基准
        
        # 考虑资源稀缺性
        if resource.get("scarcity_level") == "high":
            power += 0.3
        elif resource.get("scarcity_level") == "low":
            power -= 0.2
            
        # 考虑市场地位
        if resource.get("market_position") == "leader":
            power += 0.2
        elif resource.get("market_position") == "follower":
            power -= 0.1
            
        # 考虑紧急程度
        if resource.get("urgency") == "high":
            power -= 0.2
        elif resource.get("urgency") == "low":
            power += 0.1
            
        return max(0.1, min(1.0, power))
    
    def _identify_differences(self, 
                            resource_a: Dict[str, Any], 
                            resource_b: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别双方差异点"""
        differences = []
        
        # 价格差异
        price_a = resource_a.get("price_estimate")
        price_b = resource_b.get("price_expectation")
        if price_a and price_b:
            price_diff = abs(price_a - price_b) / max(price_a, price_b)
            differences.append({
                "aspect": "price",
                "party_a_value": price_a,
                "party_b_value": price_b,
                "difference_percentage": round(price_diff * 100, 2),
                "importance": "high"
            })
        
        # 交付时间差异
        delivery_a = resource_a.get("delivery_time")
        delivery_b = resource_b.get("delivery_expectation")
        if delivery_a and delivery_b:
            time_diff = abs(delivery_a - delivery_b) / max(delivery_a, delivery_b)
            differences.append({
                "aspect": "delivery_time",
                "party_a_value": delivery_a,
                "party_b_value": delivery_b,
                "difference_percentage": round(time_diff * 100, 2),
                "importance": "medium"
            })
        
        # 合作方式差异
        cooperation_a = resource_a.get("cooperation_mode")
        cooperation_b = resource_b.get("cooperation_preference")
        if cooperation_a and cooperation_b and cooperation_a != cooperation_b:
            differences.append({
                "aspect": "cooperation_mode",
                "party_a_value": cooperation_a,
                "party_b_value": cooperation_b,
                "difference_type": "categorical",
                "importance": "medium"
            })
        
        return differences
    
    def _assess_difficulty(self,
                          resource_a: Dict[str, Any],
                          resource_b: Dict[str, Any],
                          differences: List[Dict[str, Any]]) -> str:
        """评估谈判难度"""
        if not differences:
            return "easy"
        
        high_diff_count = sum(1 for d in differences if d.get("importance") == "high")
        medium_diff_count = sum(1 for d in differences if d.get("importance") == "medium")
        
        if high_diff_count >= 2:
            return "very_difficult"
        elif high_diff_count == 1 and medium_diff_count >= 2:
            return "difficult"
        elif high_diff_count == 1 or medium_diff_count >= 2:
            return "moderate"
        else:
            return "easy"
    
    def generate_initial_proposal(self,
                                context: Dict[str, Any],
                                party_role: str = "supplier") -> Dict[str, Any]:
        """
        生成初始提案
        
        Args:
            context: 谈判上下文
            party_role: 角色（supplier/demand）
            
        Returns:
            初始提案
        """
        scenario = context["scenario"]
        strategy = context["strategy"]
        
        # 根据场景和策略生成提案
        if scenario == "price_negotiation":
            proposal = self._generate_price_proposal(context, party_role)
        elif scenario == "cooperation_mode":
            proposal = self._generate_cooperation_proposal(context, party_role)
        else:
            proposal = self._generate_general_proposal(context, party_role)
        
        # 添加谈判话术
        proposal["opening_statement"] = self._generate_opening_statement(context, party_role)
        
        return {
            "proposal": proposal,
            "negotiation_stage": "initial_proposal",
            "generated_at": datetime.now().isoformat(),
            "valid_until": (datetime.now() + timedelta(days=7)).isoformat()  # 7天有效期
        }
    
    def _generate_price_proposal(self, 
                               context: Dict[str, Any], 
                               party_role: str) -> Dict[str, Any]:
        """生成价格提案"""
        # 获取买家和卖家的价格范围
        buyer_budget = context.get("buyer_budget", 100000)
        seller_ask = context.get("seller_ask", 120000)
        strategy = context.get("strategy", "balanced_win_win")
        
        # 根据策略确定价格点
        if strategy == "competitive":
            # 竞争型：接近卖家要价
            price = seller_ask * 0.95  # 降价5%
        elif strategy == "cooperative":
            # 合作型：中间偏下
            price = buyer_budget + (seller_ask - buyer_budget) * 0.3
        elif strategy == "compromising":
            # 妥协型：中间点
            price = (buyer_budget + seller_ask) / 2
        elif strategy == "accommodating":
            # 顺从型：接近买家预算
            price = buyer_budget * 1.05  # 加价5%
        else:  # balanced_win_win 或默认
            # 平衡型：中间偏上
            price = buyer_budget + (seller_ask - buyer_budget) * 0.7
        
        # 确保价格在合理范围内
        price = max(min(price, seller_ask), buyer_budget)
        
        return {
            "unit_price": round(price, 2),
            "currency": "USD",
            "payment_terms": "30 days net",
            "volume_discount": {
                "100+": "5%",
                "500+": "10%",
                "1000+": "15%"
            }
        }
    
    def _generate_cooperation_proposal(self,
                                     context: Dict[str, Any],
                                     party_role: str) -> Dict[str, Any]:
        """生成合作方式提案"""
        return {
            "cooperation_mode": "exclusive_distribution",
            "territory": "North America",
            "duration_months": 24,
            "minimum_order_value": 50000,
            "marketing_support": "co-op advertising up to 5%"
        }
    
    def _generate_general_proposal(self,
                                 context: Dict[str, Any],
                                 party_role: str) -> Dict[str, Any]:
        """生成通用提案"""
        return {
            "key_terms": {
                "delivery": "FOB origin",
                "quality_standards": "ISO 9001",
                "warranty": "12 months",
                "liability_limitation": "limited to contract value"
            }
        }
    
    def _generate_opening_statement(self,
                                  context: Dict[str, Any],
                                  party_role: str) -> str:
        """生成开场白"""
        scenario = context["scenario"]
        strategy = context["strategy"]
        # 安全地获取differences，如果不存在则使用空列表
        differences = context.get("differences", [])
        
        strategy_info = self.strategy_library.get(strategy, {})
        phrases = strategy_info.get("typical_phrases", [])
        
        if phrases:
            opening = random.choice(phrases)
        else:
            opening = "我们很高兴有机会与您探讨合作可能性。"
        
        # 根据场景调整
        if scenario == "price_negotiation":
            opening += " 关于价格，我们有以下初步建议..."
        elif scenario == "cooperation_mode":
            opening += " 关于合作方式，我们建议..."
        
        return opening
    
    def evaluate_counter_offer(self,
                             original_proposal: Dict[str, Any],
                             counter_offer: Dict[str, Any],
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估还价
        
        Args:
            original_proposal: 原始提案
            counter_offer: 还价内容
            context: 谈判上下文
            
        Returns:
            还价评估结果
        """
        # 计算还价与原始提案的差异
        differences = self._compare_proposals(original_proposal, counter_offer)
        
        # 评估还价的合理性
        reasonableness = self._assess_reasonableness(differences, context)
        
        # 生成还价建议
        recommendations = self._generate_counter_recommendations(differences, context)
        
        # 计算谈判进展
        progress = self._calculate_negotiation_progress(differences)
        
        return {
            "differences_analysis": differences,
            "reasonableness_score": reasonableness,
            "recommendations": recommendations,
            "negotiation_progress": progress,
            "suggested_response": self._generate_response_suggestion(differences, context),
            "evaluated_at": datetime.now().isoformat()
        }
    
    def _compare_proposals(self, 
                          proposal_a: Dict[str, Any], 
                          proposal_b: Dict[str, Any]) -> List[Dict[str, Any]]:
        """比较两个提案的差异"""
        differences = []
        
        # 比较价格
        if "unit_price" in proposal_a and "unit_price" in proposal_b:
            price_diff = (proposal_b["unit_price"] - proposal_a["unit_price"]) / proposal_a["unit_price"]
            differences.append({
                "aspect": "unit_price",
                "change_percentage": round(price_diff * 100, 2),
                "direction": "increase" if price_diff > 0 else "decrease"
            })
        
        # 比较其他关键条款
        for key in ["payment_terms", "delivery_time", "warranty"]:
            if key in proposal_a and key in proposal_b and proposal_a[key] != proposal_b[key]:
                differences.append({
                    "aspect": key,
                    "change_from": proposal_a[key],
                    "change_to": proposal_b[key]
                })
        
        return differences
    
    def _assess_reasonableness(self,
                             differences: List[Dict[str, Any]],
                             context: Dict[str, Any]) -> float:
        """评估还价合理性（0-1分）"""
        if not differences:
            return 1.0
        
        total_score = 0
        weights = 0
        
        for diff in differences:
            aspect = diff.get("aspect")
            if aspect == "unit_price":
                change = abs(diff.get("change_percentage", 0))
                # 价格变化在20%内视为合理
                score = max(0, 1 - change / 20)
                total_score += score * 0.5  # 价格权重较高
                weights += 0.5
            else:
                # 其他条款变化视为中等合理
                total_score += 0.7 * 0.3
                weights += 0.3
        
        return round(total_score / max(weights, 0.1), 2)
    
    def _generate_counter_recommendations(self,
                                        differences: List[Dict[str, Any]],
                                        context: Dict[str, Any]) -> List[str]:
        """生成还价建议"""
        recommendations = []
        strategy = context["strategy"]
        
        for diff in differences:
            aspect = diff.get("aspect")
            
            if aspect == "unit_price":
                if strategy == "competitive":
                    recommendations.append("坚持原报价，强调产品质量和市场地位")
                elif strategy == "cooperative":
                    recommendations.append("考虑小幅让步，提议3-5%的价格调整")
                else:
                    recommendations.append("评估对方还价的合理性，准备折中方案")
            else:
                recommendations.append(f"就{diff.get('aspect')}条款进行进一步沟通")
        
        return recommendations
    
    def _calculate_negotiation_progress(self,
                                      differences: List[Dict[str, Any]]) -> float:
        """计算谈判进展（0-1）"""
        if not differences:
            return 1.0
        
        # 简化：差异越少，进展越大
        diff_count = len(differences)
        progress = max(0, 1 - diff_count * 0.2)
        
        return round(progress, 2)
    
    def _generate_response_suggestion(self,
                                    differences: List[Dict[str, Any]],
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """生成回应建议"""
        strategy = context["strategy"]
        
        if strategy == "competitive":
            response_type = "counter_offer_minor"
        elif strategy == "cooperative":
            response_type = "compromise_proposal"
        elif strategy == "compromising":
            response_type = "middle_ground"
        else:
            response_type = "accept_with_conditions"
        
        return {
            "response_type": response_type,
            "suggested_phrasing": self._generate_response_phrasing(response_type, context),
            "concessions_to_consider": self._identify_possible_concessions(differences, context)
        }
    
    def _generate_response_phrasing(self,
                                  response_type: str,
                                  context: Dict[str, Any]) -> str:
        """生成回应话术"""
        phrases = {
            "counter_offer_minor": "感谢您的还价。基于我们的成本结构和市场定位，我们建议以下调整方案...",
            "compromise_proposal": "我们理解您的考虑。为了推进合作，我们提出以下折中方案...",
            "middle_ground": "双方都有合理的考量。我们建议在以下方面寻找中间点...",
            "accept_with_conditions": "我们可以接受您的提议，但需要明确以下实施细节..."
        }
        
        return phrases.get(response_type, "我们收到您的还价，正在认真考虑中。")
    
    def _identify_possible_concessions(self,
                                     differences: List[Dict[str, Any]],
                                     context: Dict[str, Any]) -> List[str]:
        """识别可能的让步点"""
        concessions = []
        strategy = context["strategy"]
        
        for diff in differences:
            aspect = diff.get("aspect")
            
            if aspect == "unit_price":
                if strategy in ["cooperative", "compromising"]:
                    concessions.append("价格可调整3-5%")
                elif strategy == "accommodating":
                    concessions.append("价格可调整8-10%")
            elif aspect == "payment_terms":
                concessions.append("付款期限可适当延长")
            elif aspect == "delivery_time":
                concessions.append("可安排分批交付")
        
        return concessions
    
    def generate_final_agreement(self,
                               negotiation_history: List[Dict[str, Any]],
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成最终协议草案（集成邀请裂变规则）
        
        Args:
            negotiation_history: 谈判历史记录
            context: 谈判上下文
            
        Returns:
            最终协议草案，包含佣金计算
        """
        # 提取谈判达成的共识点
        consensus_points = self._extract_consensus_points(negotiation_history)
        
        # 生成协议条款
        agreement_terms = self._generate_agreement_terms(consensus_points, context)
        
        # 计算佣金（考虑邀请关系）
        transaction_value = agreement_terms.get("financial_terms", {}).get("total_value", 0)
        business_type = agreement_terms.get("business_type", "regular_business")
        
        # 假设从上下文中获取用户ID和交易ID
        user_id = context.get("user_id")
        transaction_id = f"agreement_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        commission_result = self.commission_calculator.calculate_commission(
            transaction_value,
            business_type,
            currency="USD",
            user_id=user_id,
            transaction_id=transaction_id
        )
        
        # 风险评估
        risk_assessment = self._assess_agreement_risk(agreement_terms, context)
        
        return {
            "agreement_summary": {
                "parties": context["parties"],
                "business_type": business_type,
                "agreement_duration": agreement_terms.get("duration"),
                "transaction_value": transaction_value
            },
            "financial_terms": agreement_terms.get("financial_terms", {}),
            "operational_terms": agreement_terms.get("operational_terms", {}),
            "legal_terms": agreement_terms.get("legal_terms", {}),
            "commission_details": commission_result,
            "risk_assessment": risk_assessment,
            "submission_ready": True,
            "generated_at": datetime.now().isoformat(),
            "requires_final_approval": True
        }
    
    def _extract_consensus_points(self, 
                                 negotiation_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取谈判历史中的共识点"""
        consensus = []
        
        for record in negotiation_history[-5:]:  # 最近5轮
            if record.get("agreement_reached", False):
                consensus.append({
                    "aspect": record.get("negotiated_aspect"),
                    "agreed_value": record.get("agreed_value"),
                    "timestamp": record.get("timestamp")
                })
        
        return consensus
    
    def _generate_agreement_terms(self,
                                 consensus_points: List[Dict[str, Any]],
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """生成协议条款"""
        # 这里简化处理，实际应根据共识点生成详细条款
        return {
            "business_type": "regular_business",
            "duration": "24 months",
            "financial_terms": {
                "unit_price": 950.00,
                "currency": "USD",
                "payment_schedule": "30% advance, 70% upon delivery",
                "total_value": 95000.00  # 假设100件
            },
            "operational_terms": {
                "delivery_schedule": "within 60 days",
                "quality_standards": "meets industry specifications",
                "inspection_rights": "buyer has right to inspect before payment"
            },
            "legal_terms": {
                "governing_law": "laws of Singapore",
                "dispute_resolution": "arbitration in Hong Kong",
                "confidentiality": "both parties agree to keep terms confidential"
            }
        }
    
    def _assess_agreement_risk(self,
                              agreement_terms: Dict[str, Any],
                              context: Dict[str, Any]) -> Dict[str, Any]:
        """评估协议风险"""
        # 简化风险评估
        risk_factors = []
        
        # 价格风险
        unit_price = agreement_terms.get("financial_terms", {}).get("unit_price", 0)
        if unit_price < 500:
            risk_factors.append("low_price_may_indicate_quality_concerns")
        
        # 付款条件风险
        payment_terms = agreement_terms.get("financial_terms", {}).get("payment_schedule", "")
        if "advance" in payment_terms.lower() and "70%" in payment_terms:
            risk_factors.append("high_advance_payment_risk")
        
        return {
            "overall_risk_level": "medium" if risk_factors else "low",
            "risk_factors": risk_factors,
            "mitigation_suggestions": [
                "建议增加质量检验条款",
                "考虑第三方托管支付安排"
            ]
        }


def test_negotiation_engine_with_invitation():
    """测试谈判引擎（集成邀请裂变规则）"""
    print("测试AI自主商务洽谈引擎（集成邀请裂变规则）...")
    
    # 创建引擎实例
    engine = AINegotiationEngine()
    
    # 模拟两个资源
    resource_supplier = {
        "id": "resource_001",
        "resource_type": "supply_chain",
        "industry": "制造业",
        "price_estimate": 1200.00,
        "delivery_time": 45,
        "cooperation_mode": "exclusive_distribution",
        "scarcity_level": "medium",
        "market_position": "leader",
        "urgency": "low",
        "user_id": "user_002"  # 假设这是下级用户
    }
    
    resource_demand = {
        "id": "resource_002",
        "resource_type": "demand_market",
        "industry": "零售业",
        "price_expectation": 900.00,
        "delivery_expectation": 30,
        "cooperation_preference": "non_exclusive",
        "scarcity_level": "low",
        "market_position": "follower",
        "urgency": "medium",
        "user_id": "user_003"
    }
    
    # 分析谈判上下文
    context = engine.analyze_negotiation_context(resource_supplier, resource_demand)
    context["user_id"] = resource_supplier.get("user_id")  # 添加用户ID到上下文
    print(f"谈判上下文分析: {json.dumps(context, indent=2, ensure_ascii=False)}")
    
    # 生成初始提案
    proposal = engine.generate_initial_proposal(context, party_role="supplier")
    print(f"\n初始提案: {json.dumps(proposal, indent=2, ensure_ascii=False)}")
    
    # 模拟还价
    counter_offer = {
        "unit_price": 1000.00,
        "currency": "USD",
        "payment_terms": "50% advance, 50% upon delivery",
        "delivery_time": 35
    }
    
    # 评估还价
    evaluation = engine.evaluate_counter_offer(
        proposal["proposal"],
        counter_offer,
        context
    )
    print(f"\n还价评估: {json.dumps(evaluation, indent=2, ensure_ascii=False)}")
    
    # 测试佣金计算器（含邀请关系）
    print("\n佣金计算测试（含邀请关系）:")
    
    test_cases = [
        (50000.00, "regular_business", True),
        (1500000.00, "large_supply_chain", False),
        (200000.00, "premium_niche", True)
    ]
    
    for value, biz_type, has_invitation in test_cases:
        user_id = "user_002" if has_invitation else None
        result = engine.commission_calculator.calculate_commission(
            value, 
            biz_type,
            user_id=user_id,
            transaction_id=f"test_tx_{value}"
        )
        
        print(f"\n  交易金额: ${value:,.2f}, 业务类型: {biz_type}, 邀请关系: {has_invitation}")
        print(f"  系统佣金: {result['system_commission']['percentage']}% (${result['system_commission']['amount']:,.2f})")
        if has_invitation:
            print(f"  邀请分成: {result['invitation_split']['rate']*100}% (${result['invitation_split']['amount']:,.2f})")
        print(f"  总佣金: ${result['total_commission']['amount']:,.2f} ({result['total_commission']['percentage_of_transaction']}%)")
    
    # 测试生成最终协议
    print("\n\n生成最终协议测试:")
    
    mock_history = [
        {
            "agreement_reached": True,
            "negotiated_aspect": "unit_price",
            "agreed_value": 950.00,
            "timestamp": datetime.now().isoformat()
        },
        {
            "agreement_reached": True,
            "negotiated_aspect": "delivery_time",
            "agreed_value": 40,
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    final_agreement = engine.generate_final_agreement(mock_history, context)
    print(f"最终协议草案: {json.dumps(final_agreement, indent=2, ensure_ascii=False)}")
    
    print("\n测试完成!")


if __name__ == "__main__":
    test_negotiation_engine_with_invitation()