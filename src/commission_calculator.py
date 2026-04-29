"""
永久统一佣金规则计算器
全行业全球通用佣金规则，固化三档费率：
1. 大额供应链/千万级项目：成交永久抽2%-3%
2. 常规中小生意/资源对接：成交永久抽5%
3. 稀缺高利润小众精准匹配项目：成交永久抽8%
所有AI互联撮合、海内外供需对接、跨区域成交，全部自动按对应档位扣点结算。

新增邀请裂变规则集成：
- 当下级用户通过邀请关系参与成交时，下级用户终身获得10%成交佣金分成
- 需要与邀请关系管理系统（任务45）对接
- 分层佣金计算：总佣金 = 系统佣金（按业务类型） + 下级用户分成（交易金额的10%）
"""

import json
from typing import Dict, Any, Optional, Tuple, List

# 邀请裂变系统集成
try:
    from src.invitation_fission_manager import InvitationFissionManager
    INVITATION_SYSTEM_AVAILABLE = True
except ImportError:
    INVITATION_SYSTEM_AVAILABLE = False
    print("警告: 邀请裂变系统未找到，使用模拟模式")


class CommissionCalculator:
    """佣金计算器"""
    
    def __init__(self):
        self.rules = self._load_commission_rules()
        self.invitation_split_rate = 0.10  # 下级用户终身10%分成
    
    def _load_commission_rules(self) -> Dict[str, Dict[str, Any]]:
        """加载永久统一佣金规则"""
        return {
            "large_supply_chain": {
                "range_min": 0.02,  # 2%
                "range_max": 0.03,  # 3%
                "threshold": 1000000,  # 100万美元门槛
                "description": "大额供应链/千万级项目",
                "applicable_scenarios": [
                    "制造业供应链",
                    "大宗商品交易",
                    "大型工程项目",
                    "跨国企业合作",
                    "千万级及以上规模交易"
                ]
            },
            "regular_business": {
                "rate": 0.05,  # 5%
                "threshold_min": 10000,   # 1万美元
                "threshold_max": 999999,  # 100万美元以下
                "description": "常规中小生意/资源对接",
                "applicable_scenarios": [
                    "中小企业合作",
                    "跨境电商",
                    "技术服务",
                    "一般贸易",
                    "资源匹配对接"
                ]
            },
            "premium_niche": {
                "rate": 0.08,  # 8%
                "threshold": None,  # 无金额门槛
                "description": "稀缺高利润小众精准匹配项目",
                "applicable_scenarios": [
                    "高科技专利授权",
                    "奢侈品品牌合作",
                    "独家代理权",
                    "稀缺资源对接",
                    "高利润小众市场"
                ]
            }
        }
    
    def check_invitation_relationship(self, 
                                    user_id: str, 
                                    transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        检查邀请关系（与任务45的邀请关系管理系统对接）
        
        Args:
            user_id: 用户ID
            transaction_id: 交易ID
            
        Returns:
            邀请关系信息，如果没有邀请关系则返回None
        """
        # 使用真正的邀请裂变系统
        if INVITATION_SYSTEM_AVAILABLE:
            try:
                manager = InvitationFissionManager()
                relationship = manager.check_invitation_relationship(user_id, transaction_id)
                
                if relationship:
                    # 确保返回格式与原有系统兼容
                    return {
                        "inviter_id": relationship["inviter_id"],
                        "invitee_id": relationship["invitee_id"],
                        "split_rate": self.invitation_split_rate,
                        "relationship_type": "direct_invitation",
                        "relationship_id": relationship.get("relationship_id")
                    }
                return None
                
            except Exception as e:
                print(f"邀请关系检查出错: {e}")
                # 失败时回退到模拟模式
                pass
        
        # 模拟模式（兼容性回退）
        invitation_relationships = {
            "user_001": {
                "invited_by": None,  # 无上级
                "invited_users": ["user_002", "user_003"]
            },
            "user_002": {
                "invited_by": "user_001",
                "invited_users": []
            },
            "user_003": {
                "invited_by": "user_001",
                "invited_users": ["user_004"]
            }
        }
        
        if user_id in invitation_relationships:
            invited_by = invitation_relationships[user_id].get("invited_by")
            if invited_by:
                return {
                    "inviter_id": invited_by,
                    "invitee_id": user_id,
                    "split_rate": self.invitation_split_rate,
                    "relationship_type": "direct_invitation"
                }
        
        return None
    
    def calculate_commission(self,
                           transaction_value: float,
                           business_type: str = "regular_business",
                           currency: str = "USD",
                           user_id: Optional[str] = None,
                           transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """
        计算佣金（支持邀请裂变规则）
        
        Args:
            transaction_value: 交易金额
            business_type: 业务类型（large_supply_chain/regular_business/premium_niche）
            currency: 货币代码
            user_id: 用户ID（用于检查邀请关系）
            transaction_id: 交易ID（用于检查邀请关系）
            
        Returns:
            佣金计算结果，包含系统佣金和邀请分成
        """
        # 验证业务类型
        if business_type not in self.rules:
            raise ValueError(f"无效的业务类型: {business_type}。可选值: {list(self.rules.keys())}")
        
        rule = self.rules[business_type]
        system_commission_rate = 0.0
        calculation_details = {}
        
        # 计算系统佣金费率
        if business_type == "large_supply_chain":
            if transaction_value >= rule["threshold"]:
                rate_range = rule["range_max"] - rule["range_min"]
                max_threshold = rule["threshold"] * 10
                
                if transaction_value >= max_threshold:
                    scale_factor = 1.0
                else:
                    scale_factor = (transaction_value - rule["threshold"]) / (max_threshold - rule["threshold"])
                
                system_commission_rate = rule["range_max"] - (rate_range * scale_factor)
                system_commission_rate = max(rule["range_min"], min(rule["range_max"], system_commission_rate))
                
                calculation_details = {
                    "rate_range": f"{rule['range_min']*100}%-{rule['range_max']*100}%",
                    "scale_factor": round(scale_factor, 4)
                }
            else:
                rule = self.rules["regular_business"]
                system_commission_rate = rule["rate"]
                calculation_details = {
                    "note": "交易金额低于大额供应链门槛，自动降级为常规业务费率"
                }
        
        elif business_type == "regular_business":
            system_commission_rate = rule["rate"]
            
            if rule.get("threshold_min") and transaction_value < rule["threshold_min"]:
                system_commission_rate = rule["rate"] * 0.8
                calculation_details = {
                    "original_rate": rule["rate"],
                    "discount_reason": "交易金额低于常规业务最小阈值",
                    "discount_factor": 0.8
                }
            elif rule.get("threshold_max") and transaction_value > rule["threshold_max"]:
                calculation_details = {
                    "suggestion": "交易金额超过常规业务最大阈值，建议使用large_supply_chain类型"
                }
        
        elif business_type == "premium_niche":
            system_commission_rate = rule["rate"]
            calculation_details = {
                "note": "固定费率，无金额门槛"
            }
        
        # 计算系统佣金金额
        system_commission_amount = transaction_value * system_commission_rate
        
        # 检查邀请关系
        invitation_info = None
        invitation_split_amount = 0.0
        total_commission_amount = system_commission_amount
        
        if user_id and transaction_id:
            invitation_info = self.check_invitation_relationship(user_id, transaction_id)
            
            if invitation_info:
                # 计算下级用户分成
                invitation_split_amount = transaction_value * self.invitation_split_rate
                total_commission_amount = system_commission_amount + invitation_split_amount
                
                calculation_details["invitation_split"] = {
                    "rate": self.invitation_split_rate,
                    "inviter_id": invitation_info["inviter_id"],
                    "invitee_id": invitation_info["invitee_id"],
                    "split_amount": round(invitation_split_amount, 2)
                }
        
        return {
            "transaction_summary": {
                "value": round(transaction_value, 2),
                "currency": currency,
                "business_type": business_type,
                "business_description": rule["description"]
            },
            "system_commission": {
                "rate": round(system_commission_rate, 4),
                "percentage": round(system_commission_rate * 100, 2),
                "amount": round(system_commission_amount, 2)
            },
            "invitation_split": {
                "has_invitation": invitation_info is not None,
                "rate": self.invitation_split_rate if invitation_info else 0.0,
                "amount": round(invitation_split_amount, 2),
                "details": invitation_info if invitation_info else None
            },
            "total_commission": {
                "amount": round(total_commission_amount, 2),
                "percentage_of_transaction": round(total_commission_amount / transaction_value * 100, 2)
            },
            "calculation_details": calculation_details,
            "applicable_scenarios": rule.get("applicable_scenarios", []),
            "rule_verification": "永久统一佣金规则 + 邀请裂变规则，全行业全球通用"
        }
    
    def calculate_multi_level_commission(self,
                                       transaction_value: float,
                                       business_type: str = "regular_business",
                                       currency: str = "USD",
                                       user_hierarchy: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        计算多级邀请关系佣金（支持无限级邀请）
        
        Args:
            transaction_value: 交易金额
            business_type: 业务类型
            currency: 货币代码
            user_hierarchy: 用户层级列表，格式：
                [
                    {"user_id": "user_001", "level": 1, "split_rate": 0.10},
                    {"user_id": "user_002", "level": 2, "split_rate": 0.05},
                    ...
                ]
                如果不提供，则使用默认的邀请关系检查
            
        Returns:
            多级佣金计算结果
        """
        # 计算系统佣金
        basic_result = self.calculate_commission(
            transaction_value, business_type, currency
        )
        
        system_commission_amount = basic_result["system_commission"]["amount"]
        
        # 处理多级分成
        level_splits = []
        total_split_amount = 0.0
        
        if user_hierarchy:
            for user_info in user_hierarchy:
                split_rate = user_info.get("split_rate", 0.0)
                split_amount = transaction_value * split_rate
                
                level_splits.append({
                    "user_id": user_info["user_id"],
                    "level": user_info["level"],
                    "split_rate": split_rate,
                    "split_percentage": split_rate * 100,
                    "split_amount": round(split_amount, 2)
                })
                
                total_split_amount += split_amount
        
        # 计算总佣金
        total_commission_amount = system_commission_amount + total_split_amount
        
        return {
            "transaction_summary": basic_result["transaction_summary"],
            "system_commission": basic_result["system_commission"],
            "multi_level_splits": {
                "has_multi_level": len(level_splits) > 0,
                "levels": level_splits,
                "total_split_amount": round(total_split_amount, 2),
                "split_level_count": len(level_splits)
            },
            "total_commission": {
                "amount": round(total_commission_amount, 2),
                "percentage_of_transaction": round(total_commission_amount / transaction_value * 100, 2),
                "breakdown": {
                    "system_commission": round(system_commission_amount, 2),
                    "invitation_splits": round(total_split_amount, 2)
                }
            },
            "calculation_details": basic_result["calculation_details"],
            "rule_verification": "永久统一佣金规则 + 多级邀请裂变规则"
        }
    
    def recommend_business_type(self,
                              transaction_value: float,
                              business_nature: str = "general",
                              industry: Optional[str] = None) -> str:
        """
        推荐业务类型
        
        Args:
            transaction_value: 交易金额
            business_nature: 业务性质（supply_chain/regular/niche/premium）
            industry: 行业（可选）
            
        Returns:
            推荐的业务类型
        """
        if business_nature == "supply_chain":
            if transaction_value >= 1000000:
                return "large_supply_chain"
            else:
                return "regular_business"
        
        elif business_nature == "niche" or business_nature == "premium":
            return "premium_niche"
        
        elif business_nature == "regular":
            return "regular_business"
        
        else:
            if transaction_value >= 1000000:
                return "large_supply_chain"
            elif transaction_value <= 10000:
                return "regular_business"
            else:
                high_profit_industries = ["luxury", "technology", "pharmaceutical", "exclusive"]
                if industry and any(ind in industry.lower() for ind in high_profit_industries):
                    return "premium_niche"
                else:
                    return "regular_business"
    
    def validate_commission_calculation(self,
                                      transaction_value: float,
                                      business_type: str,
                                      expected_rate: float,
                                      has_invitation: bool = False,
                                      tolerance: float = 0.001) -> Dict[str, Any]:
        """
        验证佣金计算准确性（支持邀请关系）
        
        Args:
            transaction_value: 交易金额
            business_type: 业务类型
            expected_rate: 预期系统佣金费率
            has_invitation: 是否有邀请关系
            tolerance: 容差
            
        Returns:
            验证结果
        """
        result = self.calculate_commission(
            transaction_value, 
            business_type,
            user_id="test_user" if has_invitation else None,
            transaction_id="test_tx"
        )
        
        calculated_rate = result["system_commission"]["rate"]
        rate_match = abs(calculated_rate - expected_rate) <= tolerance
        
        # 验证邀请分成
        invitation_match = True
        if has_invitation:
            expected_split = transaction_value * self.invitation_split_rate
            actual_split = result["invitation_split"]["amount"]
            invitation_match = abs(actual_split - expected_split) <= 0.01
        
        return {
            "test_case": {
                "transaction_value": transaction_value,
                "business_type": business_type,
                "expected_rate": expected_rate,
                "has_invitation": has_invitation
            },
            "calculated_result": result,
            "system_rate_match": rate_match,
            "invitation_split_match": invitation_match,
            "rate_difference": abs(calculated_rate - expected_rate),
            "within_tolerance": rate_match,
            "validation_passed": rate_match and invitation_match
        }


def run_invitation_commission_tests():
    """运行邀请裂变佣金计算测试"""
    print("运行邀请裂变佣金计算器测试套件...")
    calculator = CommissionCalculator()
    
    print("\n1. 常规业务 + 邀请关系测试:")
    test_cases = [
        (50000.00, "regular_business", 0.05, True),
        (5000.00, "regular_business", 0.04, True),
        (500000.00, "regular_business", 0.05, False)
    ]
    
    for value, biz_type, expected_rate, has_invitation in test_cases:
        result = calculator.validate_commission_calculation(
            value, biz_type, expected_rate, has_invitation
        )
        print(f"  交易金额: ${value:,.2f}, 邀请关系: {has_invitation}")
        print(f"  系统佣金: {result['calculated_result']['system_commission']['percentage']}%")
        print(f"  邀请分成: ${result['calculated_result']['invitation_split']['amount']:,.2f}")
        print(f"  总佣金: ${result['calculated_result']['total_commission']['amount']:,.2f}")
        print(f"  验证结果: {'通过' if result['validation_passed'] else '失败'}")
    
    print("\n2. 多级邀请关系测试:")
    
    user_hierarchy = [
        {"user_id": "user_001", "level": 1, "split_rate": 0.10},
        {"user_id": "user_002", "level": 2, "split_rate": 0.05},
        {"user_id": "user_003", "level": 3, "split_rate": 0.02}
    ]
    
    multi_result = calculator.calculate_multi_level_commission(
        transaction_value=100000.00,
        business_type="regular_business",
        user_hierarchy=user_hierarchy
    )
    
    print(f"  交易金额: $100,000.00")
    print(f"  系统佣金: ${multi_result['system_commission']['amount']:,.2f}")
    print(f"  多级分成总额: ${multi_result['multi_level_splits']['total_split_amount']:,.2f}")
    print(f"  总佣金: ${multi_result['total_commission']['amount']:,.2f}")
    
    for split in multi_result["multi_level_splits"]["levels"]:
        print(f"    层级{split['level']}: 用户{split['user_id']}, 费率{split['split_percentage']}%, 金额${split['split_amount']:,.2f}")
    
    print("\n3. 业务类型推荐测试（含邀请关系上下文）:")
    
    test_scenarios = [
        (50000.00, "regular", "retail", True),
        (1500000.00, "supply_chain", "manufacturing", False),
        (200000.00, "niche", "luxury", True)
    ]
    
    for value, nature, industry, has_invitation in test_scenarios:
        recommended = calculator.recommend_business_type(value, nature, industry)
        print(f"  金额: ${value:,.2f}, 性质: {nature}, 行业: {industry}, 邀请: {has_invitation}")
        print(f"  推荐类型: {recommended}")
        
        # 计算示例佣金
        example = calculator.calculate_commission(
            value, 
            recommended,
            user_id="test_user" if has_invitation else None,
            transaction_id="test_tx"
        )
        
        total_percent = example["total_commission"]["percentage_of_transaction"]
        print(f"  总佣金比例: {total_percent}%")
    
    print("\n测试套件运行完成!")


if __name__ == "__main__":
    run_invitation_commission_tests()