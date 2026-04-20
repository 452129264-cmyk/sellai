"""
合规校验服务模块
提供全球商业法规、广告合规、知识产权等方面的合规性检查
"""

import logging
import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from ..models.data_models import (
    ComplianceRequest, ComplianceResult, ViolationItem, RiskItem, RiskLevel,
    ContentType, CountryCode
)

logger = logging.getLogger(__name__)


@dataclass
class ComplianceRule:
    """合规规则定义"""
    rule_code: str            # 规则代码
    rule_name: str           # 规则名称
    description: str         # 规则描述
    applicable_countries: List[str]  # 适用国家
    applicable_industries: List[str]  # 适用行业
    risk_level: RiskLevel    # 风险等级
    check_function: str      # 检查函数名称
    severity: str = "medium"  # 严重程度（low/medium/high）
    suggested_fix: str = ""   # 修复建议


@dataclass
class ComplianceServiceConfig:
    """合规校验服务配置"""
    # 规则数据库路径
    rules_database_path: str = "data/compliance_rules.json"
    
    # 外部API配置
    trademark_api_enabled: bool = True
    copyright_api_enabled: bool = True
    patent_api_enabled: bool = False
    
    # 阈值配置
    high_risk_threshold: float = 0.8
    medium_risk_threshold: float = 0.6
    min_check_text_length: int = 10
    
    # 缓存配置
    enable_cache: bool = True
    cache_ttl_seconds: int = 86400  # 24小时


class ComplianceValidationService:
    """合规校验服务"""
    
    def __init__(self, config: Optional[ComplianceServiceConfig] = None):
        """
        初始化合规校验服务
        
        Args:
            config: 服务配置
        """
        self.config = config or ComplianceServiceConfig()
        
        # 加载合规规则
        self.rules = self._load_compliance_rules()
        
        # 缓存（简化实现）
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"合规校验服务初始化完成，加载{len(self.rules)}条规则")
    
    def validate_compliance(self, request: ComplianceRequest) -> ComplianceResult:
        """
        执行合规性校验
        
        Args:
            request: 校验请求
            
        Returns:
            校验结果
        """
        import time
        start_time = time.time()
        
        try:
            # 验证请求
            self._validate_request(request)
            
            # 检查缓存
            cache_key = self._generate_cache_key(request)
            if self.config.enable_cache and cache_key in self._cache:
                cached_result = self._cache[cache_key]
                if time.time() - cached_result["timestamp"] < self.config.cache_ttl_seconds:
                    logger.debug(f"从缓存获取合规校验结果: {cache_key}")
                    
                    # 更新处理时间
                    cached_result["result"].processing_time_ms = (time.time() - start_time) * 1000
                    return cached_result["result"]
            
            # 执行合规检查
            violations = []
            risk_items = []
            
            # 1. 广告法规检查
            ad_violations = self._check_advertisement_compliance(request)
            violations.extend(ad_violations)
            
            # 2. 商标风险检查（如果启用）
            if request.check_trademark:
                trademark_risks = self._check_trademark_risks(request)
                risk_items.extend(trademark_risks)
            
            # 3. 版权风险检查（如果启用）
            if request.check_copyright:
                copyright_risks = self._check_copyright_risks(request)
                risk_items.extend(copyright_risks)
            
            # 4. 专利风险检查（如果启用）
            if request.check_patent:
                patent_risks = self._check_patent_risks(request)
                risk_items.extend(patent_risks)
            
            # 计算合规分数
            compliance_score = self._calculate_compliance_score(violations, risk_items)
            
            # 确定总体风险等级
            overall_risk = self._determine_overall_risk(violations, risk_items)
            
            # 生成综合建议
            recommendations = self._generate_compliance_recommendations(violations, risk_items)
            
            # 创建结果对象
            result = ComplianceResult(
                compliance_score=compliance_score,
                violations=violations,
                risk_items=risk_items,
                recommendations=recommendations,
                processing_time_ms=(time.time() - start_time) * 1000,
                overall_risk=overall_risk,
                passed=(compliance_score >= 0.8 and overall_risk != RiskLevel.HIGH)
            )
            
            # 缓存结果
            if self.config.enable_cache:
                self._cache[cache_key] = {
                    "timestamp": time.time(),
                    "result": result
                }
            
            logger.info(f"合规校验完成，分数: {compliance_score:.2f}, 风险: {overall_risk.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"合规校验失败: {str(e)}")
            
            # 返回降级结果
            return self._get_fallback_result(request, start_time, str(e))
    
    def _load_compliance_rules(self) -> List[ComplianceRule]:
        """加载合规规则"""
        default_rules = self._get_default_compliance_rules()
        
        try:
            # 尝试从文件加载规则
            import os
            if os.path.exists(self.config.rules_database_path):
                with open(self.config.rules_database_path, 'r', encoding='utf-8') as f:
                    file_rules = json.load(f)
                
                # 合并规则
                all_rules = default_rules.copy()
                
                for rule_data in file_rules:
                    rule = ComplianceRule(
                        rule_code=rule_data.get("rule_code", ""),
                        rule_name=rule_data.get("rule_name", ""),
                        description=rule_data.get("description", ""),
                        applicable_countries=rule_data.get("applicable_countries", []),
                        applicable_industries=rule_data.get("applicable_industries", []),
                        risk_level=RiskLevel(rule_data.get("risk_level", "low")),
                        check_function=rule_data.get("check_function", ""),
                        severity=rule_data.get("severity", "medium"),
                        suggested_fix=rule_data.get("suggested_fix", "")
                    )
                    all_rules.append(rule)
                
                return all_rules
            
        except Exception as e:
            logger.warning(f"加载合规规则文件失败，使用默认规则: {str(e)}")
        
        return default_rules
    
    def _get_default_compliance_rules(self) -> List[ComplianceRule]:
        """获取默认合规规则"""
        return [
            # 美国FTC广告法规
            ComplianceRule(
                rule_code="FTC_001",
                rule_name="FTC真实性要求",
                description="广告内容必须真实，不得误导消费者",
                applicable_countries=["US"],
                applicable_industries=["all"],
                risk_level=RiskLevel.HIGH,
                check_function="check_ftc_truthfulness",
                severity="high",
                suggested_fix="确保广告声明有充分证据支持，避免夸大宣传"
            ),
            ComplianceRule(
                rule_code="FTC_002",
                rule_name="FTC证据要求",
                description="产品功效声明必须有科学证据支持",
                applicable_countries=["US"],
                applicable_industries=["health", "beauty", "fitness"],
                risk_level=RiskLevel.MEDIUM,
                check_function="check_ftc_evidence",
                severity="medium",
                suggested_fix="添加临床试验数据引用，明确声明适用范围"
            ),
            
            # 欧盟GDPR数据保护
            ComplianceRule(
                rule_code="GDPR_001",
                rule_name="GDPR数据收集同意",
                description="收集用户数据前必须获得明确同意",
                applicable_countries=["EU"],
                applicable_industries=["all"],
                risk_level=RiskLevel.HIGH,
                check_function="check_gdpr_consent",
                severity="high",
                suggested_fix="添加数据收集同意声明和隐私政策链接"
            ),
            
            # 中国广告法
            ComplianceRule(
                rule_code="CN_AD_001",
                rule_name="广告法真实性",
                description="广告不得含有虚假内容，不得欺骗、误导消费者",
                applicable_countries=["CN"],
                applicable_industries=["all"],
                risk_level=RiskLevel.HIGH,
                check_function="check_cn_ad_law",
                severity="high",
                suggested_fix="核实产品功效声明，避免使用绝对化用语"
            ),
            ComplianceRule(
                rule_code="CN_AD_002",
                rule_name="广告法用语限制",
                description="禁止使用国家级、最高级、最佳等绝对化用语",
                applicable_countries=["CN"],
                applicable_industries=["all"],
                risk_level=RiskLevel.HIGH,
                check_function="check_cn_absolute_terms",
                severity="high",
                suggested_fix="修改或删除绝对化用语，使用相对性表述"
            ),
            
            # 日本商品表示法
            ComplianceRule(
                rule_code="JP_001",
                rule_name="商品表示法准确性",
                description="商品标识必须准确，不得夸大功效",
                applicable_countries=["JP"],
                applicable_industries=["all"],
                risk_level=RiskLevel.MEDIUM,
                check_function="check_jp_labeling",
                severity="medium",
                suggested_fix="确保商品描述准确，避免误导性表述"
            ),
            
            # 韩国电子商务法
            ComplianceRule(
                rule_code="KR_001",
                rule_name="电子商务法透明度",
                description="电子商务交易必须透明，明确标示商品信息",
                applicable_countries=["KR"],
                applicable_industriess=["ecommerce", "retail"],
                risk_level=RiskLevel.MEDIUM,
                check_function="check_kr_ecommerce",
                severity="medium",
                suggested_fix="添加详细的商品规格、价格和交易条款"
            ),
            
            # 通用知识产权规则
            ComplianceRule(
                rule_code="IP_001",
                rule_name="商标侵权风险",
                description="避免使用已注册商标的词汇和标识",
                applicable_countries=["all"],
                applicable_industries=["all"],
                risk_level=RiskLevel.HIGH,
                check_function="check_trademark_risks",
                severity="high",
                suggested_fix="检查文本中可能侵犯商标权的词汇，进行修改或获得授权"
            ),
            ComplianceRule(
                rule_code="IP_002",
                rule_name="版权侵权风险",
                description="避免复制受版权保护的内容",
                applicable_countries=["all"],
                applicable_industries=["all"],
                risk_level=RiskLevel.HIGH,
                check_function="check_copyright_risks",
                severity="high",
                suggested_fix="确保内容的原创性，引用他人作品需注明来源"
            )
        ]
    
    def _check_advertisement_compliance(self, request: ComplianceRequest) -> List[ViolationItem]:
        """检查广告合规性"""
        violations = []
        
        # 获取适用的规则
        applicable_rules = self._get_applicable_rules(request.target_country.value, request.industry)
        
        for rule in applicable_rules:
            try:
                # 根据规则类型调用相应的检查函数
                check_result = self._execute_rule_check(rule.check_function, request.text)
                
                if check_result.get("violated", False):
                    violation = ViolationItem(
                        rule_code=rule.rule_code,
                        rule_name=rule.rule_name,
                        description=rule.description,
                        risk_level=rule.risk_level,
                        suggested_fix=rule.suggested_fix or check_result.get("suggestion", "")
                    )
                    violations.append(violation)
                    
            except Exception as e:
                logger.warning(f"执行规则检查失败: {rule.rule_code}, 错误: {str(e)}")
                continue
        
        return violations
    
    def _get_applicable_rules(self, country: str, industry: str) -> List[ComplianceRule]:
        """获取适用的规则"""
        applicable_rules = []
        
        for rule in self.rules:
            # 检查国家适用性
            country_applicable = (
                "all" in rule.applicable_countries or
                country in rule.applicable_countries or
                (country == "global" and "all" in rule.applicable_countries)
            )
            
            # 检查行业适用性
            industry_applicable = (
                "all" in rule.applicable_industries or
                industry in rule.applicable_industries or
                industry == "general"
            )
            
            if country_applicable and industry_applicable:
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def _execute_rule_check(self, check_function: str, text: str) -> Dict[str, Any]:
        """执行规则检查"""
        # 根据函数名调用相应的检查逻辑
        check_functions = {
            "check_ftc_truthfulness": self._check_ftc_truthfulness,
            "check_ftc_evidence": self._check_ftc_evidence,
            "check_gdpr_consent": self._check_gdpr_consent,
            "check_cn_ad_law": self._check_cn_ad_law,
            "check_cn_absolute_terms": self._check_cn_absolute_terms,
            "check_jp_labeling": self._check_jp_labeling,
            "check_kr_ecommerce": self._check_kr_ecommerce,
            "check_trademark_risks": self._check_trademark_risks,
            "check_copyright_risks": self._check_copyright_risks,
        }
        
        if check_function in check_functions:
            return check_functions[check_function](text)
        else:
            # 默认检查（总是通过）
            return {"violated": False, "suggestion": ""}
    
    def _check_ftc_truthfulness(self, text: str) -> Dict[str, Any]:
        """检查FTC真实性要求"""
        # 检测夸大宣传词汇
        exaggeration_patterns = [
            r"\b(?:best|perfect|ultimate|supreme|unbeatable|guaranteed)\b",
            r"\b(?:cure|heal|eliminate|eradicate|destroy|annihilate)\b.*?\b(?:disease|illness|pain|symptom)\b",
            r"\b(?:100%|fully|completely|totally|absolutely)\b.*?\b(?:safe|effective|proven|tested)\b"
        ]
        
        violations = []
        for pattern in exaggeration_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"检测到夸大宣传用语")
        
        if violations:
            return {
                "violated": True,
                "suggestion": "避免使用绝对化、夸张的宣传用语，确保所有声明有科学证据支持"
            }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_ftc_evidence(self, text: str) -> Dict[str, Any]:
        """检查FTC证据要求"""
        # 检测功效声明但缺乏证据
        efficacy_patterns = [
            r"\b(?:improve|enhance|boost|increase|strengthen)\b.*?\b(?:performance|result|outcome|effectiveness)\b",
            r"\b(?:reduce|decrease|lower|minimize|alleviate)\b.*?\b(?:symptom|pain|risk|problem)\b",
            r"\b(?:clinical|scientific|medical)\b.*?\b(?:study|trial|research|evidence)\b.*?\b(?:prove|demonstrate|confirm|validate)\b"
        ]
        
        # 检查是否有功效声明但没有引用证据
        efficacy_claimed = False
        evidence_cited = False
        
        for pattern in efficacy_patterns[:2]:
            if re.search(pattern, text, re.IGNORECASE):
                efficacy_claimed = True
        
        for pattern in efficacy_patterns[2:]:
            if re.search(pattern, text, re.IGNORECASE):
                evidence_cited = True
        
        if efficacy_claimed and not evidence_cited:
            return {
                "violated": True,
                "suggestion": "功效声明需要引用临床或科学证据支持，建议添加相关研究数据引用"
            }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_gdpr_consent(self, text: str) -> Dict[str, Any]:
        """检查GDPR数据收集同意"""
        # 检测数据收集相关词汇
        data_collection_patterns = [
            r"\b(?:collect|gather|obtain|acquire)\b.*?\b(?:data|information|details)\b",
            r"\b(?:personal|private|sensitive)\b.*?\b(?:data|information)\b",
            r"\b(?:email|phone|address|location|name|age)\b.*?\b(?:collect|store|use)\b"
        ]
        
        # 检查是否提到数据收集但没有说明同意机制
        data_collection_mentioned = False
        consent_mentioned = False
        
        for pattern in data_collection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                data_collection_mentioned = True
        
        consent_patterns = [
            r"\b(?:consent|permission|agreement|authorization)\b",
            r"\b(?:opt[\s-]*in|opt[\s-]*out)\b",
            r"\b(?:privacy[\s-]*policy|terms[\s-]*of[\s-]*service)\b"
        ]
        
        for pattern in consent_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                consent_mentioned = True
        
        if data_collection_mentioned and not consent_mentioned:
            return {
                "violated": True,
                "suggestion": "收集个人数据需要明确说明并获得用户同意，建议添加隐私政策链接和同意声明"
            }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_cn_ad_law(self, text: str) -> Dict[str, Any]:
        """检查中国广告法"""
        # 检测虚假宣传和误导性内容
        deceptive_patterns = [
            r"\b(?:虚假|伪造|假冒|伪造)\b",
            r"\b(?:误导|欺骗|欺诈|蒙骗)\b",
            r"\b(?:夸大|过分|过度|不实)\b.*?\b(?:宣传|广告|推广)\b"
        ]
        
        for pattern in deceptive_patterns:
            if re.search(pattern, text):
                return {
                    "violated": True,
                    "suggestion": "广告内容必须真实准确，不得含有虚假或误导性信息"
                }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_cn_absolute_terms(self, text: str) -> Dict[str, Any]:
        """检查中国广告法绝对化用语"""
        # 中国广告法禁止的绝对化用语
        absolute_terms = [
            "最", "第一", "顶级", "极品", "终极", "完美", "最好",
            "最高", "最佳", "最大", "最强", "最先进", "最科学",
            "国家级", "世界级", "宇宙级"
        ]
        
        for term in absolute_terms:
            if term in text:
                return {
                    "violated": True,
                    "suggestion": f"避免使用绝对化用语'{term}'，使用相对性表述替代"
                }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_jp_labeling(self, text: str) -> Dict[str, Any]:
        """检查日本商品表示法"""
        # 检测误导性标识
        misleading_patterns = [
            r"\b(?:誤解|誤認|欺瞞)\b.*?\b(?:表示|標示|表示内容)\b",
            r"\b(?:不当|不正|不適切)\b.*?\b(?:表示|広告)\b"
        ]
        
        for pattern in misleading_patterns:
            if re.search(pattern, text):
                return {
                    "violated": True,
                    "suggestion": "商品表示必须准确，不得含有误导性内容"
                }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_kr_ecommerce(self, text: str) -> Dict[str, Any]:
        """检查韩国电子商务法"""
        # 检测透明度不足的问题
        transparency_patterns = [
            r"\b(?:商品|製品|物品)\b.*?\b(?:規格|仕様|詳細)\b.*?\b(?:未記載|不明確|不透明)\b",
            r"\b(?:価格|費用|料金)\b.*?\b(?:不明|曖昧|不透明)\b"
        ]
        
        for pattern in transparency_patterns:
            if re.search(pattern, text):
                return {
                    "violated": True,
                    "suggestion": "电子商务交易需要明确的商品信息和价格标示"
                }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_trademark_risks(self, text: str) -> Dict[str, Any]:
        """检查商标侵权风险"""
        # 检测常见的商标词汇（简化示例）
        common_trademarks = [
            "Google", "iPhone", "iPad", "MacBook", "Windows", "Microsoft",
            "Coca-Cola", "Pepsi", "Nike", "Adidas", "Amazon", "eBay"
        ]
        
        for trademark in common_trademarks:
            if trademark in text:
                return {
                    "violated": True,
                    "suggestion": f"文本中包含可能侵权的商标词汇'{trademark}'，建议修改或获得授权"
                }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_copyright_risks(self, text: str) -> Dict[str, Any]:
        """检查版权侵权风险"""
        # 检测可能受版权保护的内容（简化实现）
        # 实际应用中应该更复杂的检测逻辑
        
        # 检查是否有引用著名作品但没有注明
        famous_works = [
            "To be or not to be",
            "Call me Ishmael",
            "It was the best of times",
            "All happy families are alike"
        ]
        
        for work in famous_works:
            if work in text:
                return {
                    "violated": True,
                    "suggestion": f"文本中包含可能受版权保护的著名作品引用，建议注明出处或获得授权"
                }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_trademark_risks(self, text: str) -> Dict[str, Any]:
        """检查商标侵权风险（实际实现）"""
        # 这里可以集成外部商标数据库API
        # 简化实现：检查常见商标词汇
        trademark_keywords = [
            ("iPhone", "Apple Inc."),
            ("iPad", "Apple Inc."),
            ("MacBook", "Apple Inc."),
            ("Windows", "Microsoft Corporation"),
            ("Office", "Microsoft Corporation"),
            ("Google", "Google LLC"),
            ("YouTube", "Google LLC"),
            ("Amazon", "Amazon Technologies, Inc."),
            ("Kindle", "Amazon Technologies, Inc.")
        ]
        
        for keyword, owner in trademark_keywords:
            if keyword in text:
                return {
                    "violated": True,
                    "suggestion": f"文本中包含商标'{keyword}'（所有权: {owner}），建议修改或获得授权"
                }
        
        return {"violated": False, "suggestion": ""}
    
    def _check_copyright_risks(self, text: str) -> Dict[str, Any]:
        """检查版权侵权风险（实际实现）"""
        # 简化实现：基于文本相似度检测
        # 实际应用中应该集成版权数据库或使用更复杂的算法
        
        # 这里可以调用原创检测服务的语义检测功能
        # 作为示例，我们进行简单检查
        
        suspicious_patterns = [
            r"\b(?:Copyright ©|All rights reserved|Unauthorized reproduction)\b",
            r"\b(?:盗版|抄袭|剽窃|侵权)\b"
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "violated": True,
                    "suggestion": "检测到可能涉及版权侵权的表述，建议核实内容原创性"
                }
        
        return {"violated": False, "suggestion": ""}
    
    def _calculate_compliance_score(self, violations: List[ViolationItem], 
                                   risk_items: List[RiskItem]) -> float:
        """计算合规分数"""
        # 基础分数
        base_score = 1.0
        
        # 根据违规项扣分
        for violation in violations:
            if violation.risk_level == RiskLevel.HIGH:
                base_score -= 0.3
            elif violation.risk_level == RiskLevel.MEDIUM:
                base_score -= 0.15
            else:
                base_score -= 0.05
        
        # 根据风险项扣分
        for risk in risk_items:
            if risk.risk_level == RiskLevel.HIGH:
                base_score -= 0.2
            elif risk.risk_level == RiskLevel.MEDIUM:
                base_score -= 0.1
            else:
                base_score -= 0.05
        
        # 确保分数在合理范围内
        return max(0.0, min(1.0, base_score))
    
    def _determine_overall_risk(self, violations: List[ViolationItem], 
                               risk_items: List[RiskItem]) -> RiskLevel:
        """确定总体风险等级"""
        # 检查是否有高风险违规项
        high_risk_violations = [v for v in violations if v.risk_level == RiskLevel.HIGH]
        high_risk_items = [r for r in risk_items if r.risk_level == RiskLevel.HIGH]
        
        if high_risk_violations or high_risk_items:
            return RiskLevel.HIGH
        
        # 检查是否有中风险违规项
        medium_risk_violations = [v for v in violations if v.risk_level == RiskLevel.MEDIUM]
        medium_risk_items = [r for r in risk_items if r.risk_level == RiskLevel.MEDIUM]
        
        if medium_risk_violations or medium_risk_items:
            return RiskLevel.MEDIUM
        
        # 默认低风险
        return RiskLevel.LOW
    
    def _generate_compliance_recommendations(self, violations: List[ViolationItem],
                                           risk_items: List[RiskItem]) -> List[str]:
        """生成合规建议"""
        recommendations = []
        
        # 基于违规项的建议
        for violation in violations:
            if violation.suggested_fix:
                recommendations.append(violation.suggested_fix)
        
        # 基于风险项的建议
        for risk in risk_items:
            if risk.suggested_action:
                recommendations.append(risk.suggested_action)
        
        # 通用建议
        if not recommendations:
            recommendations.extend([
                "文本合规性良好，建议继续保持",
                "定期更新对目标国家法规的了解",
                "考虑使用专业合规咨询服务"
            ])
        
        # 确保建议数量合理
        return recommendations[:5]
    
    def _validate_request(self, request: ComplianceRequest):
        """验证校验请求"""
        if not request.text or len(request.text.strip()) < self.config.min_check_text_length:
            raise ValueError(f"文本长度不足{self.config.min_check_text_length}字符")
    
    def _generate_cache_key(self, request: ComplianceRequest) -> str:
        """生成缓存键"""
        import hashlib
        
        key_data = {
            "text": request.text,
            "target_country": request.target_country.value,
            "industry": request.industry,
            "check_trademark": request.check_trademark,
            "check_copyright": request.check_copyright,
            "check_patent": request.check_patent
        }
        
        key_string = str(key_data)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_fallback_result(self, request: ComplianceRequest, start_time: float,
                            error_message: str) -> ComplianceResult:
        """获取降级结果"""
        import time
        processing_time = (time.time() - start_time) * 1000
        
        return ComplianceResult(
            compliance_score=0.6,  # 保守分数
            violations=[],
            risk_items=[],
            recommendations=[
                "合规校验服务暂时不可用，建议人工审核",
                "检查广告法规和知识产权要求",
                f"错误信息: {error_message[:100]}..."
            ],
            processing_time_ms=processing_time,
            overall_risk=RiskLevel.MEDIUM,  # 中等风险
            passed=False
        )