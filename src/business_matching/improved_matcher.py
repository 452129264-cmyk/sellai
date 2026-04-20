#!/usr/bin/env python3
"""
改进的商务信息自动匹配算法
结合用户画像、毛利要求、投资范围等多维度进行精准匹配
目标：匹配准确率≥90%
"""

import json
from typing import Dict, List, Any, Tuple, Optional
import numpy as np

class ImprovedBusinessMatcher:
    """改进的商务匹配算法"""
    
    def __init__(self):
        # 匹配权重配置 - 优化版本，强调偏好和投资匹配
        self.weights = {
            'margin': 0.25,          # 毛利率权重（降低，因为已有硬性门槛）
            'preference': 0.40,      # 用户偏好权重（提高，减少不匹配推荐）
            'investment_fit': 0.25,  # 投资范围匹配权重（提高，减少超出范围推荐）
            'historical_fit': 0.10   # 历史成功匹配权重（降低）
        }
        
        # 类别映射表（用于偏好匹配）
        self.category_mapping = {
            '服装': ['服装', '服饰', '时尚', '鞋子', '配饰'],
            '电子产品': ['电子产品', '数码', '手机配件', '电脑周边', '智能设备'],
            '家居用品': ['家居用品', '家居装饰', '家具', '厨房用品', '生活用品'],
            '美妆': ['美妆', '化妆品', '护肤品', '个人护理'],
            '食品': ['食品', '零食', '饮料', '保健品']
        }
        
        # 投资范围解析函数
        self.investment_parser = self._parse_investment_range
    
    def _parse_investment_range(self, investment_range) -> Tuple[float, float]:
        """解析投资范围，返回(min, max)"""
        # 支持多种格式: ["$500", "$5000"], "$500-$5000", 或直接的元组
        import re
        
        if isinstance(investment_range, list):
            # 列表格式: ["$500", "$5000"]
            if len(investment_range) >= 2:
                min_str, max_str = investment_range[0], investment_range[1]
                min_num = float(re.findall(r'\d+', min_str)[0]) if re.findall(r'\d+', min_str) else 500.0
                max_num = float(re.findall(r'\d+', max_str)[0]) if re.findall(r'\d+', max_str) else 5000.0
                return min_num, max_num
        elif isinstance(investment_range, str):
            # 字符串格式: "$500-$5000"
            numbers = re.findall(r'\d+', investment_range)
            if len(numbers) >= 2:
                return float(numbers[0]), float(numbers[1])
            elif len(numbers) == 1:
                return float(numbers[0]), float(numbers[0]) * 10
        
        # 默认值
        return 500.0, 5000.0
    
    def _category_match_score(self, opportunity_category: str, user_preferences: List[str]) -> float:
        """计算类别匹配分数"""
        if not user_preferences:
            return 0.5  # 默认中等分数
        
        # 标准化类别名称
        opp_category_lower = opportunity_category.lower()
        
        # 检查直接匹配
        for pref in user_preferences:
            if pref.lower() in opp_category_lower or opp_category_lower in pref.lower():
                return 1.0
        
        # 检查映射匹配
        for main_category, subcategories in self.category_mapping.items():
            if any(sub.lower() in opp_category_lower for sub in subcategories):
                # 如果用户偏好包含这个主类别
                if any(pref.lower() in main_category.lower() or main_category.lower() in pref.lower() for pref in user_preferences):
                    return 0.8
        
        return 0.2  # 低匹配分数
    
    def _investment_fit_score(self, investment_required: float, user_investment_range: Tuple[float, float]) -> float:
        """计算投资范围匹配分数"""
        min_invest, max_invest = user_investment_range
        
        # 计算相对位置：0表示等于min，1表示等于max
        if investment_required <= min_invest:
            position = 0.0
        elif investment_required >= max_invest:
            position = 1.0
        else:
            position = (investment_required - min_invest) / (max_invest - min_invest)
        
        # 使用高斯函数，中心在0.5（中间位置），标准差0.3
        # 这样在范围内分数较高，超出范围分数迅速下降
        import math
        score = math.exp(-((position - 0.5) ** 2) / (2 * (0.3 ** 2)))
        
        # 对于严重超出或不足的情况，额外惩罚
        if investment_required < min_invest * 0.3:
            score *= 0.05  # 远低于最小范围
        elif investment_required < min_invest * 0.7:
            score *= 0.2   # 显著低于最小范围
        elif investment_required > max_invest * 1.5:
            score *= 0.05  # 远超出最大范围
        elif investment_required > max_invest * 1.2:
            score *= 0.2   # 显著超出最大范围
        
        return max(0.0, min(1.0, score))
    
    def _historical_fit_score(self, opportunity_margin: float, user_history_success_rate: float) -> float:
        """基于历史成功率的匹配分数"""
        # 如果用户历史成功率较高，可以接受稍低的毛利
        # 如果用户历史成功率较低，需要更高的毛利保证
        if user_history_success_rate >= 0.8:
            # 成功率高，可以接受25%+的毛利
            if opportunity_margin >= 25:
                return 1.0
            elif opportunity_margin >= 20:
                return 0.7
            else:
                return 0.3
        elif user_history_success_rate >= 0.5:
            # 中等成功率，需要30%+的毛利
            if opportunity_margin >= 30:
                return 1.0
            elif opportunity_margin >= 25:
                return 0.6
            else:
                return 0.2
        else:
            # 低成功率，需要35%+的毛利
            if opportunity_margin >= 35:
                return 1.0
            elif opportunity_margin >= 30:
                return 0.5
            else:
                return 0.1
    
    def calculate_match_score(self, 
                            opportunity: Dict[str, Any], 
                            user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """计算综合匹配分数"""
        
        # 提取机会数据
        opp_category = opportunity.get('category', '')
        opp_margin = opportunity.get('estimated_margin', 0.0)
        opp_investment = opportunity.get('investment_required', 0.0)
        
        # 提取用户画像
        user_preferences = user_profile.get('preferences', [])
        user_investment_range = self.investment_parser(user_profile.get('investment_range', ['$500', '$5000']))
        user_success_rate = user_profile.get('historical_success_rate', 0.5)
        
        # 硬性条件：必须满足30%毛利门槛（基于用户历史成功率可调整）
        min_margin_required = 30.0
        if user_success_rate < 0.5:
            min_margin_required = 35.0  # 低成功率用户需要更高毛利保证
        elif user_success_rate > 0.8:
            min_margin_required = 25.0  # 高成功率用户可接受稍低毛利
        
        meets_margin_requirement = opp_margin >= min_margin_required
        
        # 计算各项分数
        margin_score = min(opp_margin / 50.0, 1.0)  # 假设50%毛利为满分
        preference_score = self._category_match_score(opp_category, user_preferences)
        investment_score = self._investment_fit_score(opp_investment, user_investment_range)
        historical_score = self._historical_fit_score(opp_margin, user_success_rate)
        
        # 计算加权总分
        total_score = (
            margin_score * self.weights['margin'] +
            preference_score * self.weights['preference'] +
            investment_score * self.weights['investment_fit'] +
            historical_score * self.weights['historical_fit']
        )
        
        # 推荐逻辑：必须满足毛利门槛，且总分达到阈值
        # 同时要求投资匹配分数不能太低
        investment_threshold = 0.3  # 投资匹配最低要求
        
        # 基础推荐条件
        base_condition = meets_margin_requirement and investment_score >= investment_threshold
        
        # 根据不同偏好匹配度调整总分要求
        if preference_score >= 0.8:
            # 高度匹配偏好，标准阈值
            recommendation = base_condition and total_score >= 0.65
        elif preference_score >= 0.5:
            # 中等匹配偏好，较高阈值
            recommendation = base_condition and total_score >= 0.75
        else:
            # 不匹配偏好，很高阈值且需要超高毛利
            recommendation = (base_condition and 
                            opp_margin >= 50.0 and 
                            total_score >= 0.85)
        
        # 构建结果
        result = {
            'opportunity_id': opportunity.get('id', ''),
            'category': opp_category,
            'estimated_margin': opp_margin,
            'investment_required': opp_investment,
            'match_score': round(total_score, 4),
            'component_scores': {
                'margin_score': round(margin_score, 4),
                'preference_score': round(preference_score, 4),
                'investment_score': round(investment_score, 4),
                'historical_score': round(historical_score, 4)
            },
            'meets_margin_requirement': meets_margin_requirement,
            'min_margin_required': min_margin_required,
            'recommendation': recommendation
        }
        
        return result
    
    def filter_and_rank_opportunities(self,
                                    opportunities: List[Dict[str, Any]],
                                    user_profile: Dict[str, Any],
                                    min_margin: float = 30.0,
                                    min_match_score: float = 0.65) -> List[Dict[str, Any]]:
        """过滤并排序商机"""
        
        scored_opportunities = []
        
        for opp in opportunities:
            # 基本筛选：必须满足最低毛利要求
            if opp.get('estimated_margin', 0.0) < min_margin:
                continue
            
            # 计算匹配分数
            match_result = self.calculate_match_score(opp, user_profile)
            
            # 应用匹配分数阈值
            if match_result['match_score'] >= min_match_score:
                scored_opportunities.append(match_result)
        
        # 按匹配分数降序排序
        sorted_opportunities = sorted(scored_opportunities, 
                                    key=lambda x: x['match_score'], 
                                    reverse=True)
        
        return sorted_opportunities
    
    def evaluate_accuracy(self,
                         test_data: List[Dict[str, Any]],
                         user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """评估算法准确性"""
        
        if not test_data:
            return {'accuracy': 0.0, 'total': 0, 'correct': 0, 'details': []}
        
        total_cases = len(test_data)
        correct_cases = 0
        details = []
        
        for test_case in test_data:
            # 测试用例格式: {'opportunity': ..., 'should_recommend': True/False}
            opportunity = test_case['opportunity']
            should_recommend = test_case['should_recommend']
            
            # 计算匹配结果
            match_result = self.calculate_match_score(opportunity, user_profile)
            actual_recommendation = match_result['recommendation']
            
            is_correct = (actual_recommendation == should_recommend)
            if is_correct:
                correct_cases += 1
            
            details.append({
                'opportunity_id': opportunity.get('id', ''),
                'category': opportunity.get('category', ''),
                'estimated_margin': opportunity.get('estimated_margin', 0.0),
                'should_recommend': should_recommend,
                'actual_recommendation': actual_recommendation,
                'match_score': match_result['match_score'],
                'is_correct': is_correct
            })
        
        accuracy = correct_cases / total_cases if total_cases > 0 else 0
        
        return {
            'accuracy': round(accuracy, 4),
            'total': total_cases,
            'correct': correct_cases,
            'details': details
        }


# 示例用法
if __name__ == "__main__":
    # 初始化匹配器
    matcher = ImprovedBusinessMatcher()
    
    # 示例用户画像
    sample_user_profile = {
        "user_id": "user_001",
        "preferences": ["家居用品", "电子产品"],
        "investment_range": ["$500", "$5000"],
        "historical_success_rate": 0.75
    }
    
    # 示例商机数据（与测试一致）
    sample_opportunities = [
        {
            "id": "opp_001",
            "category": "电子产品",
            "estimated_margin": 45.2,
            "investment_required": 1200,
        },
        {
            "id": "opp_002",
            "category": "服装",
            "estimated_margin": 25.5,
            "investment_required": 800,
        },
        {
            "id": "opp_003",
            "category": "家居用品",
            "estimated_margin": 38.7,
            "investment_required": 2000,
        }
    ]
    
    # 过滤并排序
    filtered = matcher.filter_and_rank_opportunities(sample_opportunities, sample_user_profile)
    
    print("改进匹配算法结果:")
    print(f"过滤后机会数: {len(filtered)}")
    for opp in filtered:
        print(f"  ID: {opp['opportunity_id']}, 类别: {opp['category']}, "
              f"毛利: {opp['estimated_margin']}%, 匹配分数: {opp['match_score']:.4f}, "
              f"推荐: {opp['recommendation']}")
    
    # 评估准确性
    test_cases = [
        {'opportunity': sample_opportunities[0], 'should_recommend': True},
        {'opportunity': sample_opportunities[1], 'should_recommend': False},
        {'opportunity': sample_opportunities[2], 'should_recommend': True}
    ]
    
    eval_result = matcher.evaluate_accuracy(test_cases, sample_user_profile)
    print(f"\n算法准确性评估:")
    print(f"准确率: {eval_result['accuracy']:.2%} ({eval_result['correct']}/{eval_result['total']})")
    
    # 保存配置
    config = {
        'weights': matcher.weights,
        'min_margin': 30.0,
        'min_match_score': 0.65,
        'category_mapping': matcher.category_mapping
    }
    
    with open('src/business_matching/config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("\n配置已保存到 src/business_matching/config.json")