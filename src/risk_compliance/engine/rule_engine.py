"""
智能规则引擎核心模块
实现多级规则匹配和风险评估
"""

import re
import json
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict
from datetime import datetime
from functools import lru_cache

from ..database.models import (
    RiskLevel,
    RuleType,
    MatchLogic,
    Violation,
    RiskRule,
    RegulationClause
)

# ==============================================
# 规则匹配器基类
# ==============================================

class BaseRuleMatcher:
    """规则匹配器基类"""
    
    def __init__(self, rule_type: RuleType):
        self.rule_type = rule_type
        self.cache = {}
    
    def match(self, text: str, rules: List[RiskRule], country_code: str) -> List[Violation]:
        """匹配文本中的规则违规"""
        violations = []
        for rule in rules:
            if rule.rule_type != self.rule_type or not rule.is_active:
                continue
            
            # 检查规则是否适用于目标国家
            # 这里需要查询法规条款的国家信息
            # 简化处理：假设规则已按国家过滤
            
            rule_violations = self._match_rule(text, rule, country_code)
            violations.extend(rule_violations)
        
        return violations
    
    def _match_rule(self, text: str, rule: RiskRule, country_code: str) -> List[Violation]:
        """匹配单个规则（子类实现）"""
        raise NotImplementedError
    
    def _generate_violation_id(self, rule_id: str, text_hash: str) -> str:
        """生成违规ID"""
        hash_input = f"{rule_id}_{text_hash}_{datetime.now().timestamp()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]

# ==============================================
# 关键词匹配器
# ==============================================

class KeywordMatcher(BaseRuleMatcher):
    """关键词匹配器"""
    
    def __init__(self):
        super().__init__(RuleType.KEYWORD)
        self.keyword_cache = {}
    
    def _match_rule(self, text: str, rule: RiskRule, country_code: str) -> List[Violation]:
        """匹配关键词规则"""
        violations = []
        rule_content = rule.rule_content
        
        # 提取关键词列表
        keywords = rule_content.get("keywords", [])
        match_logic = rule_content.get("match_logic", "exact")
        threshold = rule_content.get("threshold", 0.8)
        
        if not keywords:
            return violations
        
        text_lower = text.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            if match_logic == "exact":
                # 精确匹配
                matches = self._find_exact_matches(text_lower, keyword_lower)
            elif match_logic == "partial":
                # 部分匹配
                matches = self._find_partial_matches(text_lower, keyword_lower)
            elif match_logic == "fuzzy":
                # 模糊匹配
                matches = self._find_fuzzy_matches(text_lower, keyword_lower, threshold)
            else:
                continue
            
            for match_text, start_pos, end_pos, confidence in matches:
                violation = Violation(
                    id=self._generate_violation_id(rule.id, match_text),
                    clause_code=rule_content.get("clause_code", "UNKNOWN"),
                    description=rule_content.get("description", "关键词违规"),
                    risk_level=RiskLevel(rule_content.get("risk_level", "medium")),
                    matched_text=match_text,
                    position_start=start_pos,
                    position_end=end_pos,
                    confidence=confidence,
                    rule_id=rule.id
                )
                violations.append(violation)
        
        return violations
    
    def _find_exact_matches(self, text: str, keyword: str) -> List[Tuple[str, int, int, float]]:
        """查找精确匹配"""
        matches = []
        start = 0
        while True:
            start = text.find(keyword, start)
            if start == -1:
                break
            end = start + len(keyword)
            matches.append((keyword, start, end, 1.0))
            start = end
        return matches
    
    def _find_partial_matches(self, text: str, keyword: str) -> List[Tuple[str, int, int, float]]:
        """查找部分匹配（包含关系）"""
        matches = []
        if keyword in text:
            start = text.find(keyword)
            end = start + len(keyword)
            matches.append((keyword, start, end, 0.9))
        return matches
    
    def _find_fuzzy_matches(self, text: str, keyword: str, threshold: float) -> List[Tuple[str, int, int, float]]:
        """查找模糊匹配（简化实现）"""
        # 简化为检查关键词是否以子串形式出现
        matches = []
        if len(keyword) < 3:
            return matches
        
        # 检查滑动窗口
        window_size = len(keyword)
        for i in range(len(text) - window_size + 1):
            substring = text[i:i+window_size]
            # 简单相似度计算（字符重叠比例）
            overlap = sum(1 for a, b in zip(substring, keyword) if a == b)
            similarity = overlap / window_size
            
            if similarity >= threshold:
                matches.append((substring, i, i+window_size, similarity))
        
        return matches

# ==============================================
# 模式匹配器
# ==============================================

class PatternMatcher(BaseRuleMatcher):
    """模式匹配器（正则表达式）"""
    
    def __init__(self):
        super().__init__(RuleType.PATTERN)
        self.pattern_cache = {}
    
    def _match_rule(self, text: str, rule: RiskRule, country_code: str) -> List[Violation]:
        """匹配模式规则"""
        violations = []
        rule_content = rule.rule_content
        
        patterns = rule_content.get("patterns", [])
        if not patterns:
            return violations
        
        for pattern_str in patterns:
            # 编译正则表达式（缓存）
            if pattern_str not in self.pattern_cache:
                try:
                    self.pattern_cache[pattern_str] = re.compile(pattern_str, re.IGNORECASE)
                except re.error:
                    continue
            
            regex = self.pattern_cache[pattern_str]
            
            for match in regex.finditer(text):
                match_text = match.group()
                start_pos = match.start()
                end_pos = match.end()
                
                # 计算置信度（基于匹配长度和规则权重）
                confidence = min(0.95, 0.7 + (len(match_text) / 100) * 0.3)
                
                violation = Violation(
                    id=self._generate_violation_id(rule.id, match_text),
                    clause_code=rule_content.get("clause_code", "UNKNOWN"),
                    description=rule_content.get("description", "模式违规"),
                    risk_level=RiskLevel(rule_content.get("risk_level", "medium")),
                    matched_text=match_text,
                    position_start=start_pos,
                    position_end=end_pos,
                    confidence=confidence,
                    rule_id=rule.id
                )
                violations.append(violation)
        
        return violations

# ==============================================
# 语义分析器（简化实现）
# ==============================================

class SemanticAnalyzer(BaseRuleMatcher):
    """语义分析器（简化实现）"""
    
    def __init__(self):
        super().__init__(RuleType.SEMANTIC)
        # 在实际实现中，这里会加载预训练模型
        # 简化实现：基于关键词扩展和上下文分析
    
    def _match_rule(self, text: str, rule: RiskRule, country_code: str) -> List[Violation]:
        """匹配语义规则（简化实现）"""
        # 在实际系统中，这里会使用BERT等模型进行语义理解
        # 简化实现：返回空列表，表示需要真实模型才能实现
        
        # 占位实现：检查文本长度是否异常
        rule_content = rule.rule_content
        min_length = rule_content.get("min_length", 0)
        max_length = rule_content.get("max_length", float('inf'))
        
        violations = []
        text_length = len(text)
        
        if text_length < min_length or text_length > max_length:
            # 生成违规记录
            violation = Violation(
                id=self._generate_violation_id(rule.id, f"length_{text_length}"),
                clause_code=rule_content.get("clause_code", "SEMANTIC_001"),
                description=rule_content.get("description", "文本长度不符合要求"),
                risk_level=RiskLevel(rule_content.get("risk_level", "low")),
                matched_text=text[:50] + "..." if len(text) > 50 else text,
                position_start=0,
                position_end=min(50, len(text)),
                confidence=0.6,
                suggested_correction=rule_content.get("suggestion", None),
                rule_id=rule.id
            )
            violations.append(violation)
        
        return violations

# ==============================================
# 智能规则引擎主类
# ==============================================

class SmartRuleEngine:
    """智能规则引擎主类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 初始化匹配器
        self.matchers = {
            RuleType.KEYWORD: KeywordMatcher(),
            RuleType.PATTERN: PatternMatcher(),
            RuleType.SEMANTIC: SemanticAnalyzer()
        }
        
        # 规则缓存
        self.rule_cache = {}
        self.country_rules_cache = {}
        
        # 性能统计
        self.stats = {
            "total_checks": 0,
            "total_violations": 0,
            "avg_processing_time": 0.0
        }
    
    def check(self, text: str, country_code: str, content_type: str = "advertisement") -> List[Violation]:
        """
        执行规则检查
        Args:
            text: 待检查文本
            country_code: 目标国家代码
            content_type: 内容类型
        Returns:
            违规列表
        """
        start_time = time.time()
        
        # 获取适用于该国家和内容类型的规则
        rules = self._get_rules_for_country(country_code, content_type)
        
        # 逐级匹配
        all_violations = []
        
        # 1. 关键词匹配（快速筛查）
        if self.config.get("enable_keyword_matching", True):
            keyword_violations = self.matchers[RuleType.KEYWORD].match(text, rules, country_code)
            all_violations.extend(keyword_violations)
        
        # 2. 模式匹配
        if self.config.get("enable_pattern_matching", True):
            pattern_violations = self.matchers[RuleType.PATTERN].match(text, rules, country_code)
            all_violations.extend(pattern_violations)
        
        # 3. 语义分析
        if self.config.get("enable_semantic_analysis", True):
            semantic_violations = self.matchers[RuleType.SEMANTIC].match(text, rules, country_code)
            all_violations.extend(semantic_violations)
        
        # 去重处理
        violations = self._deduplicate_violations(all_violations)
        
        # 更新统计
        processing_time = (time.time() - start_time) * 1000
        self._update_stats(len(violations), processing_time)
        
        return violations
    
    def _get_rules_for_country(self, country_code: str, content_type: str) -> List[RiskRule]:
        """获取适用于特定国家和内容类型的规则"""
        cache_key = f"{country_code}_{content_type}"
        
        if cache_key in self.country_rules_cache:
            return self.country_rules_cache[cache_key]
        
        # 在实际系统中，这里会从数据库查询
        # 简化实现：返回示例规则
        rules = self._get_sample_rules(country_code, content_type)
        
        self.country_rules_cache[cache_key] = rules
        return rules
    
    def _get_sample_rules(self, country_code: str, content_type: str) -> List[RiskRule]:
        """获取示例规则（简化实现）"""
        rules = []
        
        # 美国广告法规示例规则
        if country_code == "US":
            rules.append(RiskRule(
                id="ftc_absolute_001",
                clause_id="clause_001",
                rule_type=RuleType.KEYWORD,
                rule_content={
                    "clause_code": "FTC_001",
                    "description": "使用绝对化用语",
                    "risk_level": "high",
                    "keywords": ["最好", "第一", "顶级", "之王", "最有效", "100%", "彻底"],
                    "match_logic": "partial",
                    "threshold": 0.7,
                    "suggestions": ["避免使用绝对化用语，改为比较性描述"]
                },
                match_logic=MatchLogic.PARTIAL,
                threshold=0.7,
                weight=1.0,
                is_active=True
            ))
            
            rules.append(RiskRule(
                id="ftc_pattern_001",
                clause_id="clause_002",
                rule_type=RuleType.PATTERN,
                rule_content={
                    "clause_code": "FTC_002",
                    "description": "夸大宣传模式",
                    "risk_level": "medium",
                    "patterns": [
                        r"最\w+的\w+",
                        r"第一\w+",
                        r"顶级\w+",
                        r"\w+之王"
                    ],
                    "suggestions": ["使用更客观的描述语言"]
                },
                match_logic=MatchLogic.FUZZY,
                threshold=0.6,
                weight=0.8,
                is_active=True
            ))
        
        # 欧盟GDPR示例规则
        elif country_code == "EU":
            rules.append(RiskRule(
                id="gdpr_consent_001",
                clause_id="clause_101",
                rule_type=RuleType.KEYWORD,
                rule_content={
                    "clause_code": "GDPR_001",
                    "description": "未经同意收集个人数据",
                    "risk_level": "critical",
                    "keywords": ["默认收集", "自动获取", "无需同意", "强制收集", "必须提供"],
                    "match_logic": "partial",
                    "threshold": 0.8,
                    "suggestions": ["明确获取用户同意，提供拒绝选项"]
                },
                match_logic=MatchLogic.PARTIAL,
                threshold=0.8,
                weight=1.0,
                is_active=True
            ))
        
        # 中国广告法示例规则
        elif country_code == "CN":
            rules.append(RiskRule(
                id="cn_ad_law_001",
                clause_id="clause_201",
                rule_type=RuleType.KEYWORD,
                rule_content={
                    "clause_code": "CN_AD_001",
                    "description": "使用违禁绝对化用语",
                    "risk_level": "high",
                    "keywords": ["最", "第一", "顶级", "极致", "完美", "100%", "绝对"],
                    "match_logic": "exact",
                    "threshold": 0.9,
                    "suggestions": ["使用相对性描述，如'优质'、'领先'"]
                },
                match_logic=MatchLogic.EXACT,
                threshold=0.9,
                weight=1.0,
                is_active=True
            ))
        
        return rules
    
    def _deduplicate_violations(self, violations: List[Violation]) -> List[Violation]:
        """去重违规记录（基于位置重叠）"""
        if not violations:
            return []
        
        # 按起始位置排序
        violations.sort(key=lambda v: v.position_start)
        
        deduplicated = []
        current = violations[0]
        
        for i in range(1, len(violations)):
            next_violation = violations[i]
            
            # 检查位置重叠
            if (next_violation.position_start <= current.position_end and 
                next_violation.position_end <= current.position_end):
                # 完全重叠，保留置信度高的
                if next_violation.confidence > current.confidence:
                    current = next_violation
            elif next_violation.position_start <= current.position_end:
                # 部分重叠，合并或保留两者
                # 简化：保留两者
                deduplicated.append(current)
                current = next_violation
            else:
                # 不重叠
                deduplicated.append(current)
                current = next_violation
        
        deduplicated.append(current)
        return deduplicated
    
    def _update_stats(self, violation_count: int, processing_time: float):
        """更新性能统计"""
        self.stats["total_checks"] += 1
        self.stats["total_violations"] += violation_count
        
        # 计算平均处理时间（移动平均）
        current_avg = self.stats["avg_processing_time"]
        n = self.stats["total_checks"]
        self.stats["avg_processing_time"] = (current_avg * (n - 1) + processing_time) / n
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.stats.copy()
    
    def clear_cache(self):
        """清空缓存"""
        self.rule_cache.clear()
        self.country_rules_cache.clear()
        for matcher in self.matchers.values():
            if hasattr(matcher, "cache"):
                matcher.cache.clear()
            if hasattr(matcher, "pattern_cache"):
                matcher.pattern_cache.clear()
            if hasattr(matcher, "keyword_cache"):
                matcher.keyword_cache.clear()