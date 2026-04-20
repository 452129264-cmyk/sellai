"""
Notebook LM知识底座集成模块
实现与Notebook LM知识库的查询和更新
"""

import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import asdict
import hashlib

from ..database.models import CaseReference

logger = logging.getLogger(__name__)

class NotebookLMIntegrator:
    """Notebook LM集成器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "api_endpoint": "https://notebooklm.googleapis.com/v1",
            "api_key": "your_notebooklm_api_key",
            "default_collection": "compliance_knowledge",
            "cache_enabled": True,
            "cache_ttl_seconds": 3600,
            "max_retries": 3,
            "retry_delay_seconds": 1
        }
        
        # 知识库集合映射
        self.collections = {
            "regulations": "法规库",
            "cases": "案例库", 
            "rules": "规则库",
            "risk_patterns": "风险模式库"
        }
        
        # 查询缓存（简化实现）
        self.query_cache = {}
        
        logger.info("NotebookLMIntegrator initialized")
    
    async def query_similar_cases(self, query: str, country_code: str, 
                                 max_results: int = 5) -> List[CaseReference]:
        """
        查询相似合规案例
        Args:
            query: 查询文本
            country_code: 国家代码
            max_results: 最大返回结果数
        Returns:
            相似案例列表
        """
        try:
            # 构建缓存键
            cache_key = self._generate_cache_key(query, country_code)
            
            # 检查缓存
            if self.config.get("cache_enabled", True) and cache_key in self.query_cache:
                cached_result = self.query_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.debug(f"使用缓存查询结果: {cache_key}")
                    return cached_result["data"]
            
            # 构建查询参数
            query_params = {
                "query": query,
                "country": country_code,
                "collection": self.collections.get("cases", "案例库"),
                "max_results": max_results,
                "similarity_threshold": 0.6
            }
            
            # 在实际系统中，这里会调用Notebook LM API
            # 简化实现：返回模拟数据
            similar_cases = await self._simulate_notebooklm_query(query_params)
            
            # 缓存结果
            if self.config.get("cache_enabled", True):
                self.query_cache[cache_key] = {
                    "data": similar_cases,
                    "timestamp": self._get_current_timestamp(),
                    "ttl": self.config.get("cache_ttl_seconds", 3600)
                }
            
            logger.info(f"查询相似案例完成: query='{query[:50]}...', "
                       f"country={country_code}, results={len(similar_cases)}")
            
            return similar_cases
            
        except Exception as e:
            logger.error(f"查询相似案例失败: {str(e)}")
            return []
    
    async def query_regulations(self, country_code: str, keyword: Optional[str] = None,
                               category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查询法规条款
        Args:
            country_code: 国家代码
            keyword: 关键词（可选）
            category: 法规分类（可选）
        Returns:
            法规条款列表
        """
        try:
            # 构建查询
            query_parts = [f"国家: {country_code}"]
            
            if keyword:
                query_parts.append(f"关键词: {keyword}")
            
            if category:
                query_parts.append(f"分类: {category}")
            
            query_text = " | ".join(query_parts)
            
            # 构建查询参数
            query_params = {
                "query": query_text,
                "country": country_code,
                "collection": self.collections.get("regulations", "法规库"),
                "max_results": 20
            }
            
            # 在实际系统中，这里会调用Notebook LM API
            # 简化实现：返回模拟数据
            regulations = await self._simulate_regulations_query(query_params)
            
            logger.info(f"查询法规条款完成: country={country_code}, "
                       f"keyword={keyword}, results={len(regulations)}")
            
            return regulations
            
        except Exception as e:
            logger.error(f"查询法规条款失败: {str(e)}")
            return []
    
    async def add_compliance_case(self, case_data: Dict[str, Any]) -> bool:
        """
        添加合规案例到知识库
        Args:
            case_data: 案例数据
        Returns:
            是否成功
        """
        try:
            # 构建案例文档
            case_document = self._build_case_document(case_data)
            
            # 在实际系统中，这里会调用Notebook LM API添加文档
            # 简化实现：记录到日志
            
            logger.info(f"添加合规案例到知识库: case_id={case_data.get('id', 'unknown')}, "
                       f"country={case_data.get('country_code', 'unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"添加合规案例失败: {str(e)}")
            return False
    
    async def update_regulation(self, regulation_data: Dict[str, Any]) -> bool:
        """
        更新法规条款
        Args:
            regulation_data: 法规数据
        Returns:
            是否成功
        """
        try:
            # 构建法规文档
            regulation_document = self._build_regulation_document(regulation_data)
            
            # 在实际系统中，这里会调用Notebook LM API更新文档
            # 简化实现：记录到日志
            
            logger.info(f"更新法规条款: clause_code={regulation_data.get('clause_code', 'unknown')}, "
                       f"country={regulation_data.get('country_code', 'unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"更新法规条款失败: {str(e)}")
            return False
    
    async def search_risk_patterns(self, risk_pattern: str, country_code: str) -> List[Dict[str, Any]]:
        """
        搜索风险模式
        Args:
            risk_pattern: 风险模式描述
            country_code: 国家代码
        Returns:
            风险模式列表
        """
        try:
            # 构建查询
            query = f"风险模式: {risk_pattern} | 国家: {country_code}"
            
            # 构建查询参数
            query_params = {
                "query": query,
                "country": country_code,
                "collection": self.collections.get("risk_patterns", "风险模式库"),
                "max_results": 10
            }
            
            # 在实际系统中，这里会调用Notebook LM API
            # 简化实现：返回模拟数据
            patterns = await self._simulate_risk_patterns_query(query_params)
            
            logger.info(f"搜索风险模式完成: pattern='{risk_pattern[:50]}...', "
                       f"country={country_code}, results={len(patterns)}")
            
            return patterns
            
        except Exception as e:
            logger.error(f"搜索风险模式失败: {str(e)}")
            return []
    
    def clear_cache(self):
        """清空查询缓存"""
        self.query_cache.clear()
        logger.info("Notebook LM查询缓存已清空")
    
    async def _simulate_notebooklm_query(self, query_params: Dict[str, Any]) -> List[CaseReference]:
        """模拟Notebook LM查询（简化实现）"""
        # 在实际系统中，这里会调用Notebook LM API
        # 简化实现：返回模拟案例
        
        query_text = query_params.get("query", "")
        country_code = query_params.get("country", "US")
        max_results = query_params.get("max_results", 5)
        
        # 根据查询内容生成模拟案例
        cases = []
        
        # 示例案例1：夸大宣传
        if "夸大" in query_text or "绝对化" in query_text or "exaggerat" in query_text.lower():
            cases.append(CaseReference(
                case_id="case_us_001",
                title="美国FTC查处夸大宣传案例",
                similarity_score=0.85,
                violation_type="夸大宣传",
                key_points=[
                    "使用'最有效'等绝对化用语",
                    "缺乏充分科学证据支持",
                    "罚款金额: $50,000"
                ]
            ))
        
        # 示例案例2：数据隐私违规
        if "数据" in query_text or "privacy" in query_text.lower() or "GDPR" in query_text:
            cases.append(CaseReference(
                case_id="case_eu_001", 
                title="欧盟GDPR数据保护违规案例",
                similarity_score=0.78,
                violation_type="数据隐私违规",
                key_points=[
                    "未经用户同意收集个人数据",
                    "未提供明确的数据使用说明",
                    "罚款金额: €100,000"
                ]
            ))
        
        # 示例案例3：虚假广告
        if "虚假" in query_text or "false" in query_text.lower() or "mislead" in query_text.lower():
            cases.append(CaseReference(
                case_id="case_cn_001",
                title="中国广告法虚假宣传案例", 
                similarity_score=0.72,
                violation_type="虚假广告",
                key_points=[
                    "使用未经验证的统计数据",
                    "虚构产品功效和效果",
                    "处罚: 下架广告并罚款¥200,000"
                ]
            ))
        
        # 通用案例（如果查询不匹配特定类型）
        if not cases:
            cases.append(CaseReference(
                case_id="case_generic_001",
                title=f"{country_code}合规审查通用指南",
                similarity_score=0.65,
                violation_type="通用风险",
                key_points=[
                    "确保所有声明有据可查",
                    "避免使用绝对化用语",
                    "明确披露重要限制条件",
                    "遵守当地广告法规要求"
                ]
            ))
        
        # 限制返回数量
        return cases[:max_results]
    
    async def _simulate_regulations_query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """模拟法规查询（简化实现）"""
        country_code = query_params.get("country", "US")
        
        regulations = []
        
        if country_code == "US":
            regulations.extend([
                {
                    "id": "reg_us_001",
                    "clause_code": "FTC_001",
                    "title": "广告真实性要求",
                    "description": "所有广告声明必须真实、不误导消费者",
                    "risk_level": "high",
                    "keywords": ["虚假", "误导", "夸大", "不实"],
                    "penalty": "最高罚款$50,000，可能需要撤回广告"
                },
                {
                    "id": "reg_us_002",
                    "clause_code": "FTC_002",
                    "title": "功效声明证据要求",
                    "description": "产品功效声明必须有充分科学证据支持",
                    "risk_level": "medium",
                    "keywords": ["证据", "研究", "临床试验", "证明"],
                    "penalty": "缺乏证据的声明可能面临罚款和纠正措施"
                }
            ])
        
        elif country_code == "EU":
            regulations.extend([
                {
                    "id": "reg_eu_001",
                    "clause_code": "GDPR_001",
                    "title": "数据收集同意要求",
                    "description": "收集个人数据前必须获得用户明确同意",
                    "risk_level": "critical",
                    "keywords": ["同意", "授权", "许可", "opt-in"],
                    "penalty": "最高罚款€20,000,000或年营业额的4%"
                }
            ])
        
        elif country_code == "CN":
            regulations.extend([
                {
                    "id": "reg_cn_001",
                    "clause_code": "CN_AD_001",
                    "title": "禁止使用绝对化用语",
                    "description": "广告中禁止使用'最'、'第一'、'顶级'等绝对化用语",
                    "risk_level": "high",
                    "keywords": ["最", "第一", "顶级", "极致", "100%"],
                    "penalty": "罚款¥200,000-¥1,000,000"
                }
            ])
        
        # 默认返回通用法规
        if not regulations:
            regulations.append({
                "id": "reg_generic_001",
                "clause_code": "GENERIC_001",
                "title": "广告合规基本原则",
                "description": "广告必须真实、不误导、有证据支持",
                "risk_level": "medium",
                "keywords": ["真实", "准确", "客观", "透明"],
                "penalty": "根据当地法规处罚"
            })
        
        return regulations
    
    async def _simulate_risk_patterns_query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """模拟风险模式查询（简化实现）"""
        risk_pattern = query_params.get("query", "")
        
        patterns = []
        
        # 夸大宣传模式
        if "夸大" in risk_pattern or "exaggerat" in risk_pattern.lower():
            patterns.append({
                "id": "pattern_exaggeration_001",
                "name": "夸大宣传模式",
                "description": "使用绝对化用语、缺乏证据支持的功效声明",
                "risk_level": "high",
                "examples": [
                    "'最有效的减肥产品'",
                    "'100%治愈率保证'",
                    "'顶级品质，无人能及'"
                ],
                "detection_rules": [
                    "关键词: 最, 第一, 顶级, 100%, 彻底",
                    "模式: 最+形容词+的+名词",
                    "语义: 缺乏限定条件的绝对化声明"
                ]
            })
        
        # 数据隐私违规模式
        if "数据" in risk_pattern or "privacy" in risk_pattern.lower():
            patterns.append({
                "id": "pattern_privacy_001",
                "name": "数据隐私违规模式",
                "description": "未经同意收集、使用或分享个人数据",
                "risk_level": "critical",
                "examples": [
                    "'默认收集用户位置信息'",
                    "'自动获取联系人权限'",
                    "'数据可能分享给第三方合作伙伴'"
                ],
                "detection_rules": [
                    "关键词: 默认, 自动, 必须, 强制, 分享, 第三方",
                    "模式: 动词+个人数据+无同意表述",
                    "语义: 强制或默认的数据收集行为"
                ]
            })
        
        # 虚假广告模式
        if "虚假" in risk_pattern or "false" in risk_pattern.lower():
            patterns.append({
                "id": "pattern_false_ad_001",
                "name": "虚假广告模式",
                "description": "虚构事实、伪造数据、不实承诺",
                "risk_level": "high",
                "examples": [
                    "'经过1000人临床试验证明'（实际无试验）",
                    "'权威机构认证'（实际无认证）",
                    "'限时免费'（实际一直免费）"
                ],
                "detection_rules": [
                    "关键词: 证明, 认证, 权威, 限时, 独家",
                    "模式: 声称+证据+但缺乏具体信息",
                    "语义: 虚构或夸大的事实描述"
                ]
            })
        
        return patterns
    
    def _build_case_document(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建案例文档"""
        document = {
            "id": case_data.get("id", ""),
            "title": case_data.get("title", ""),
            "description": case_data.get("description", ""),
            "country_code": case_data.get("country_code", ""),
            "violation_type": case_data.get("violation_type", ""),
            "original_content": case_data.get("original_content", ""),
            "corrected_content": case_data.get("corrected_content", ""),
            "penalty_amount": case_data.get("penalty_amount", 0),
            "case_date": case_data.get("case_date", ""),
            "source_url": case_data.get("source_url", ""),
            "tags": case_data.get("tags", []),
            "metadata": {
                "document_type": "compliance_case",
                "created_at": self._get_current_timestamp(),
                "version": "1.0"
            }
        }
        
        # 生成文档哈希
        content_str = json.dumps(document, sort_keys=True, ensure_ascii=False)
        document["metadata"]["document_hash"] = hashlib.md5(content_str.encode()).hexdigest()[:16]
        
        return document
    
    def _build_regulation_document(self, regulation_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建法规文档"""
        document = {
            "id": regulation_data.get("id", ""),
            "clause_code": regulation_data.get("clause_code", ""),
            "title": regulation_data.get("title", ""),
            "description": regulation_data.get("description", ""),
            "country_code": regulation_data.get("country_code", ""),
            "category": regulation_data.get("category", ""),
            "legal_text": regulation_data.get("legal_text", ""),
            "simplified_text": regulation_data.get("simplified_text", ""),
            "risk_level": regulation_data.get("risk_level", "medium"),
            "keywords": regulation_data.get("keywords", []),
            "penalty_info": regulation_data.get("penalty_info", ""),
            "effective_date": regulation_data.get("effective_date", ""),
            "metadata": {
                "document_type": "regulation",
                "updated_at": self._get_current_timestamp(),
                "version": "1.0"
            }
        }
        
        # 生成文档哈希
        content_str = json.dumps(document, sort_keys=True, ensure_ascii=False)
        document["metadata"]["document_hash"] = hashlib.md5(content_str.encode()).hexdigest()[:16]
        
        return document
    
    def _generate_cache_key(self, query: str, country_code: str) -> str:
        """生成缓存键"""
        key_str = f"{query}_{country_code}".encode('utf-8')
        return hashlib.md5(key_str).hexdigest()[:16]
    
    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if not cached_data:
            return False
        
        timestamp = cached_data.get("timestamp", 0)
        ttl = cached_data.get("ttl", 3600)
        current_time = self._get_current_timestamp()
        
        return (current_time - timestamp) <= ttl
    
    def _get_current_timestamp(self) -> int:
        """获取当前时间戳（秒）"""
        import time
        return int(time.time())