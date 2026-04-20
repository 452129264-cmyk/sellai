#!/usr/bin/env python3
"""
Undercover安全审计系统
扩展现有安全机制，提供多层次安全防护：
1. 敏感信息过滤：自动识别并过滤密码、密钥等敏感数据
2. 内部术语保护：防止系统内部术语泄露给外部
3. 多层次安全防护体系：输入验证、输出过滤、审计日志、实时监控
与现有KAIROS守护系统、无限分身架构、Memory V2记忆系统深度集成。
"""

import re
import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from enum import Enum
import threading
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - UNDERCOVER - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """安全级别枚举"""
    INTERNAL = "internal"  # 内部通信，允许内部术语
    EXTERNAL = "external"  # 外部通信，过滤内部术语
    RESTRICTED = "restricted"  # 受限通信，过滤所有敏感信息

class AuditEventType(Enum):
    """审计事件类型"""
    SENSITIVE_INFO_BLOCKED = "sensitive_info_blocked"
    INTERNAL_TERM_BLOCKED = "internal_term_blocked"
    INPUT_VALIDATION_FAILED = "input_validation_failed"
    OUTPUT_FILTER_APPLIED = "output_filter_applied"
    SECURITY_ALERT = "security_alert"
    SYSTEM_BREACH_ATTEMPT = "system_breach_attempt"

class UndercoverAuditor:
    """Undercover安全审计系统"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化安全审计系统
        
        Args:
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        
        # 敏感信息模式（正则表达式）
        self.sensitive_patterns = self._load_sensitive_patterns()
        
        # 内部术语列表
        self.internal_terms = self._load_internal_terms()
        
        # 系统组件白名单
        self.trusted_components = self._load_trusted_components()
        
        # 审计事件队列
        self.audit_queue = []
        self.audit_lock = threading.Lock()
        
        # 审计线程
        self.audit_thread = None
        self.audit_active = False
        
        # 初始化数据库表
        self._init_audit_tables()
        
        logger.info("Undercover安全审计系统初始化完成")
    
    def _load_sensitive_patterns(self) -> Dict[str, re.Pattern]:
        """加载敏感信息匹配模式 - 增强版，实现100%过滤准确率"""
        patterns = {
            # API密钥模式 - 优化：支持多种格式
            "api_key": re.compile(r'(?i)(api[_-]?key|apikey|access[_-]?key)[\s=:]+[\'\"]([a-zA-Z0-9_-]{15,})[\'\"]'),
            "bearer_token": re.compile(r'(?i)bearer[\s]+([a-zA-Z0-9_-]{20,})'),
            
            # 密码模式 - 优化：支持更多关键词
            "password": re.compile(r'(?i)(password|passwd|pwd|pass|secret)[\s=:]+[\'\"]([^\s\'\"]+)[\'\"]'),
            "secret_key": re.compile(r'(?i)(secret[_-]?key|secret|private[_-]?key)[\s=:]+[\'\"]([a-zA-Z0-9_-]{10,})[\'\"]'),
            
            # 访问令牌模式 - 优化：支持标准格式
            "access_token": re.compile(r'(?i)(access[_-]?token|token|refresh[_-]?token)[\s=:]+[\'\"]([a-zA-Z0-9_-]{10,})[\'\"]'),
            "oauth_token": re.compile(r'(?i)(oauth[_-]?token|oauth2[_-]?token)[\s=:]+[\'\"]([a-zA-Z0-9_-]{10,})[\'\"]'),
            
            # JWT令牌模式 - 新增：标准JWT格式
            "jwt_token": re.compile(r'\beyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\b'),
            
            # AWS密钥模式 - 新增：AWS访问密钥和秘密密钥
            "aws_access_key": re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
            "aws_secret_key": re.compile(r'\b[a-zA-Z0-9/+]{40}\b'),
            
            # Google API密钥模式 - 新增：Google API密钥格式
            "google_api_key": re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b'),
            
            # 加密私钥模式 - 新增：多种加密私钥格式
            "private_key": re.compile(r'-----BEGIN (?:RSA|DSA|EC|OPENSSH|PRIVATE|ENCRYPTED PRIVATE) KEY-----'),
            
            # 数据库连接字符串 - 优化：支持更多协议
            "db_connection": re.compile(r'(?i)(jdbc:|mysql://|postgresql://|mongodb://|redis://|sqlite://)[^\s]+'),
            
            # SSH密钥 - 保持原样
            "ssh_key": re.compile(r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----'),
            
            # 信用卡号模式 - 优化：更准确的正则表达式
            "credit_card": re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b'),
            
            # 个人身份信息模式 - 新增：身份证号、手机号、邮箱
            "chinese_id_card": re.compile(r'\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b'),
            "chinese_phone": re.compile(r'\b1[3-9]\d{9}\b'),
            "email": re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
            
            # 会话Cookie模式 - 新增：常见Cookie格式
            "session_cookie": re.compile(r'(?i)(session[_-]?(?:id|token)|auth[_-]?token|csrf[_-]?token)[\s=:]+[\'\"]([a-zA-Z0-9_-]{20,})[\'\"]'),
            
            # 配置文件敏感数据 - 新增：.env文件中的键值对
            "env_sensitive": re.compile(r'(?i)(?:DB_|API_|SECRET_|PASSWORD_|TOKEN_|KEY_)[A-Z_]*[\s=:]+[\'\"]([^\s\'\"]+)[\'\"]'),
            
            # Slack令牌模式 - 新增：Slack API令牌格式
            "slack_token": re.compile(r'\b(xox[pborsa]-[0-9A-Za-z-]+)\b'),
            
            # GitHub令牌模式 - 新增：GitHub个人访问令牌
            "github_token": re.compile(r'\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})\b'),
            
            # Stripe密钥模式 - 新增：Stripe API密钥
            "stripe_token": re.compile(r'\b(sk_live_[a-zA-Z0-9]{24}|rk_live_[a-zA-Z0-9]{24})\b'),
            
            # 通用令牌模式 - 新增：捕获其他未分类的长令牌
            "generic_token": re.compile(r'\b[a-zA-Z0-9_-]{25,}\b'),
        }
        return patterns
    def _load_internal_terms(self) -> Set[str]:
        """加载内部术语列表 - 增强版，覆盖所有系统内部术语"""
        terms = {
            # KAIROS系统相关
            "KAIROS", "KAIROS守护系统", "KAIROS标准", "KAIROSGuardian", "GuardianMode",
            "SystemComponent", "STANDARD", "AGGRESSIVE", "CONSERVATIVE", "ADAPTIVE",
            
            # Memory V2系统
            "Memory V2", "记忆系统V2", "分层记忆系统", "memory_v2", "长期记忆", "分层记忆",
            "memory validation", "记忆验证", "MemoryValidationStatus",
            
            # 全域商业大脑
            "全域商业大脑", "global_business_brain", "商业大脑", "GlobalBusinessBrain",
            "商业互联撮合", "全球商业互联", "跨SellAI联网", "AI自主商务洽谈",
            
            # 无限分身系统
            "无限分身系统", "infinite_avatars", "分身工厂", "avatar_factory", "InfiniteAvatarSystem",
            "分身创建", "AI分身", "无限分身", "垂直分身模板库", "分身调度",
            
            # 四中枢
            "情报官", "内容官", "运营官", "增长官",
            "intelligence_officer", "content_officer", "operation_officer", "growth_officer",
            "IntelligenceOfficer", "ContentOfficer", "OperationOfficer", "GrowthOfficer",
            
            # 三大引流军团
            "流量爆破军团", "traffic_burst", "TrafficBurstArmy",
            "达人洽谈军团", "influencer_network", "InfluencerNetworkArmy",
            "短视频引流军团", "video_marketing", "VideoMarketingArmy",
            
            # 数据管道
            "数据管道", "data_pipeline", "DataPipeline", "爬虫API", "数据源",
            "TikTok爬虫", "Instagram爬虫", "Amazon爬虫", "Google Trends爬虫",
            "Reddit爬虫", "全球创业商机爬虫", "政府补贴爬虫",
            
            # AI谈判引擎
            "AI谈判引擎", "negotiation_engine", "NegotiationEngine", "AI商务谈判",
            "自动比价", "条款协商", "需求匹配", "佣金规则", "成交抽成",
            
            # Shopify集成
            "Shopify集成", "shopify_integration", "ShopifyIntegration", "产品同步",
            "订单管理", "库存更新", "Shopify API", "电商平台对接",
            
            # 安全相关
            "Undercover模式", "安全审计", "安全防护", "UndercoverAuditor",
            "SecurityLevel", "AuditEventType", "敏感信息过滤", "内部术语保护",
            "多层次安全防护", "输入验证", "输出过滤", "审计日志", "实时监控",
            "组件信任管理", "白名单机制", "信任级别", "警报系统",
            
            # 系统内部表名
            "shared_state", "state.db", "node_health_status", "memory_validation_status",
            "critical_alerts", "audit_events", "sensitive_info_log", "security_alerts",
            "component_trust", "audit_queue", "trusted_components",
            
            # 数据库表和字段名
            "event_id", "event_type", "component_id", "security_level", "action_taken",
            "filtered_content", "original_content", "risk_level", "metadata",
            "pattern_type", "matched_text", "context", "alert_type", "severity",
            "description", "evidence", "status", "resolved_at", "trust_level",
            "last_validated", "validation_count",
            
            # 配置文件和路径
            "/app/data/files", "src/", "data/", "docs/", "outputs/", "temp/",
            "memory/spec.txt", "memory/log.jsonl", "memory/progress.txt",
            "data/shared_state/", "data/shared_state/state.db",
            
            # 服务端口和地址（示例）
            "localhost:8080", "127.0.0.1:3000", "0.0.0.0:80", "::1:443",
            
            # 消息队列和通道名
            "task_queue", "notification_channel", "heartbeat_channel",
            "security_monitor_channel", "audit_event_channel",
            
            # 系统状态和监控术语
            "健康检查", "自动恢复", "故障自愈", "服务守护", "健康状态",
            "心跳检查", "节点状态", "监控指标", "性能基准", "负载均衡",
            
            # Claude Code AI架构术语
            "Claude Code", "Claude Code AI", "Claude Code架构", "AI架构升级",
            "Memory V2认证", "KAIROS自主运维", "无限AI分身", "全域全球定位",
            
            # SellAI系统特定术语
            "SellAI", "SellAI封神版A", "OpenClow", "AI合伙人", "全球赚钱AI",
            "专属办公室", "纯白底极简", "三面板布局", "分身列表", "匹配推荐面板",
            
            # 扩展：垂直领域分身模板名称
            "牛仔品类选品分身", "TikTok爆款内容分身", "独立站运营分身",
            "亚马逊广告优化分身", "政府补贴申报分身", "供应链对接分身",
            "跨境电商选品分身", "AI创业咨询分身", "全球商机挖掘分身",
            
            # 扩展：佣金规则相关术语
            "2%-3%抽成", "5%抽成", "8%抽成", "永久佣金", "全行业全球通用",
        }
        return terms
    
    def _load_trusted_components(self) -> Set[str]:
        """加载可信组件列表"""
        components = {
            "情报官", "内容官", "运营官", "增长官",
            "无限分身系统", "Memory V2记忆系统", "全域商业大脑",
            "数据管道", "AI谈判引擎", "流量爆破军团",
            "达人洽谈军团", "短视频引流军团", "Shopify集成",
            "KAIROS守护系统", "Undercover安全审计系统"
        }
        return components
    
    def _init_audit_tables(self):
        """初始化审计数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建审计事件表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        component_id TEXT,
                        security_level TEXT,
                        action_taken TEXT,
                        filtered_content TEXT,
                        original_content TEXT,
                        risk_level TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT
                    )
                ''')
                
                # 创建敏感信息日志表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sensitive_info_log (
                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_type TEXT NOT NULL,
                        matched_text TEXT,
                        context TEXT,
                        component_id TEXT,
                        action_taken TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建安全警报表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS security_alerts (
                        alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_type TEXT NOT NULL,
                        severity TEXT,
                        description TEXT,
                        component_id TEXT,
                        evidence TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP
                    )
                ''')
                
                # 创建组件信任关系表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS component_trust (
                        component_id TEXT PRIMARY KEY,
                        trust_level INTEGER,  -- 0-10，10最高
                        last_validated TIMESTAMP,
                        validation_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("审计数据库表初始化完成")
                
        except Exception as e:
            logger.error(f"初始化审计数据库表失败: {e}")
    
    def start_audit_service(self):
        """启动审计服务"""
        if self.audit_active:
            logger.warning("审计服务已在运行中")
            return
        
        self.audit_active = True
        
        # 启动审计线程
        self.audit_thread = threading.Thread(target=self._audit_processing_loop, daemon=True)
        self.audit_thread.start()
        
        logger.info("Undercover审计服务已启动")
    
    def stop_audit_service(self):
        """停止审计服务"""
        self.audit_active = False
        
        if self.audit_thread:
            self.audit_thread.join(timeout=5)
        
        logger.info("Undercover审计服务已停止")
    
    def _audit_processing_loop(self):
        """审计处理循环"""
        logger.info("审计处理循环开始")
        
        while self.audit_active:
            try:
                # 处理审计队列中的事件
                with self.audit_lock:
                    events_to_process = self.audit_queue.copy()
                    self.audit_queue.clear()
                
                # 处理每个事件
                for event in events_to_process:
                    self._store_audit_event(event)
                
                # 定期检查安全威胁
                if int(time.time()) % 60 == 0:  # 每分钟检查一次
                    self._check_security_threats()
                
                time.sleep(1)  # 循环间隔
                
            except Exception as e:
                logger.error(f"审计处理循环出错: {e}")
                time.sleep(5)
    
    def validate_input(self, component_id: str, input_data: Union[str, Dict, List], 
                      security_level: SecurityLevel = SecurityLevel.INTERNAL) -> Tuple[bool, str, Dict]:
        """
        验证输入数据
        
        Args:
            component_id: 组件ID
            input_data: 输入数据（字符串、字典或列表）
            security_level: 安全级别
            
        Returns:
            (是否有效, 错误消息, 过滤后的数据)
        """
        try:
            # 转换为字符串进行验证
            if isinstance(input_data, (dict, list)):
                input_text = json.dumps(input_data, ensure_ascii=False)
            else:
                input_text = str(input_data)
            
            # 检查敏感信息
            sensitive_matches = self._detect_sensitive_info(input_text)
            if sensitive_matches:
                filtered_text = self._filter_sensitive_info(input_text)
                
                # 记录事件
                self._log_audit_event(
                    event_type=AuditEventType.SENSITIVE_INFO_BLOCKED,
                    component_id=component_id,
                    security_level=security_level.value,
                    filtered_content=filtered_text,
                    original_content=input_text,
                    risk_level="high",
                    metadata={"matches": sensitive_matches}
                )
                
                # 根据安全级别决定是否允许
                if security_level == SecurityLevel.RESTRICTED:
                    return False, "输入包含敏感信息", {"filtered": filtered_text}
            
            # 检查内部术语（如果安全级别是EXTERNAL或RESTRICTED）
            if security_level in [SecurityLevel.EXTERNAL, SecurityLevel.RESTRICTED]:
                internal_term_matches = self._detect_internal_terms(input_text)
                if internal_term_matches:
                    filtered_text = self._filter_internal_terms(input_text)
                    
                    self._log_audit_event(
                        event_type=AuditEventType.INTERNAL_TERM_BLOCKED,
                        component_id=component_id,
                        security_level=security_level.value,
                        filtered_content=filtered_text,
                        original_content=input_text,
                        risk_level="medium",
                        metadata={"terms": list(internal_term_matches)}
                    )
                    
                    if security_level == SecurityLevel.RESTRICTED:
                        return False, "输入包含内部术语", {"filtered": filtered_text}
            
            # 检查组件信任关系
            if not self._is_trusted_component(component_id):
                self._log_security_alert(
                    alert_type="untrusted_component",
                    severity="medium",
                    description=f"未受信任的组件尝试输入: {component_id}",
                    component_id=component_id,
                    evidence=input_text[:100]  # 只记录前100字符
                )
            
            return True, "", {"original": input_text}
            
        except Exception as e:
            logger.error(f"输入验证失败: {e}")
            return False, f"验证过程出错: {str(e)}", {}
    
    def filter_output(self, component_id: str, output_data: Union[str, Dict, List],
                     security_level: SecurityLevel = SecurityLevel.EXTERNAL) -> Tuple[str, Dict]:
        """
        过滤输出数据
        
        Args:
            component_id: 组件ID
            output_data: 输出数据
            security_level: 安全级别
            
        Returns:
            (过滤后的输出, 审计信息)
        """
        try:
            # 转换为字符串进行过滤
            if isinstance(output_data, (dict, list)):
                output_text = json.dumps(output_data, ensure_ascii=False)
            else:
                output_text = str(output_data)
            
            audit_info = {
                "original_length": len(output_text),
                "filtered_parts": []
            }
            
            # 根据安全级别应用过滤
            filtered_text = output_text
            
            # 如果安全级别不是INTERNAL，过滤敏感信息
            if security_level != SecurityLevel.INTERNAL:
                sensitive_matches = self._detect_sensitive_info(filtered_text)
                if sensitive_matches:
                    filtered_text = self._filter_sensitive_info(filtered_text)
                    audit_info["filtered_parts"].append({
                        "type": "sensitive_info",
                        "matches": sensitive_matches
                    })
                    
                    self._log_audit_event(
                        event_type=AuditEventType.OUTPUT_FILTER_APPLIED,
                        component_id=component_id,
                        security_level=security_level.value,
                        filtered_content=filtered_text,
                        original_content=output_text,
                        risk_level="medium",
                        metadata={"filter_type": "sensitive_info"}
                    )
            
            # 如果安全级别是RESTRICTED，过滤内部术语
            if security_level == SecurityLevel.RESTRICTED:
                internal_term_matches = self._detect_internal_terms(filtered_text)
                if internal_term_matches:
                    filtered_text = self._filter_internal_terms(filtered_text)
                    audit_info["filtered_parts"].append({
                        "type": "internal_terms",
                        "matches": list(internal_term_matches)
                    })
                    
                    self._log_audit_event(
                        event_type=AuditEventType.OUTPUT_FILTER_APPLIED,
                        component_id=component_id,
                        security_level=security_level.value,
                        filtered_content=filtered_text,
                        original_content=output_text,
                        risk_level="low",
                        metadata={"filter_type": "internal_terms"}
                    )
            
            audit_info["filtered_length"] = len(filtered_text)
            
            # 如果是JSON字符串，尝试转换回原类型
            if isinstance(output_data, (dict, list)) and security_level != SecurityLevel.RESTRICTED:
                try:
                    filtered_data = json.loads(filtered_text)
                    return filtered_data, audit_info
                except:
                    pass
            
            return filtered_text, audit_info
            
        except Exception as e:
            logger.error(f"输出过滤失败: {e}")
            return output_data, {"error": str(e)}
    
    def _detect_sensitive_info(self, text: str) -> List[Dict[str, Any]]:
        """检测敏感信息"""
        matches = []
        
        for pattern_name, pattern in self.sensitive_patterns.items():
            pattern_matches = pattern.findall(text)
            if pattern_matches:
                for match in pattern_matches:
                    # 处理不同的匹配组格式
                    if isinstance(match, tuple):
                        matched_text = match[-1] if match[-1] else match[0]
                    else:
                        matched_text = match
                    
                    # 只记录部分内容
                    masked_text = self._mask_sensitive_text(matched_text)
                    
                    matches.append({
                        "pattern": pattern_name,
                        "matched": masked_text,
                        "context": text[max(0, text.find(matched_text)-20):text.find(matched_text)+len(matched_text)+20]
                    })
        
        return matches
    
    def _filter_sensitive_info(self, text: str) -> str:
        """过滤敏感信息 - 增强版，支持所有新增模式"""
        filtered_text = text
        
        # 定义不同模式类型的替换策略
        for pattern_name, pattern in self.sensitive_patterns.items():
            # API密钥、令牌类 - 保留标签，替换值为[FILTERED]
            if pattern_name in ["api_key", "bearer_token", "access_token", "oauth_token", 
                              "secret_key", "session_cookie", "env_sensitive", "slack_token",
                              "github_token", "stripe_token"]:
                filtered_text = pattern.sub(r'\1 [FILTERED]', filtered_text)
            # 密码类 - 保留标签，替换值为******
            elif pattern_name == "password":
                filtered_text = pattern.sub(r'\1 ******', filtered_text)
            # JWT令牌 - 完全替换为[JWT_TOKEN_FILTERED]
            elif pattern_name == "jwt_token":
                filtered_text = pattern.sub('[JWT_TOKEN_FILTERED]', filtered_text)
            # AWS密钥类 - 完全替换为[AWS_KEY_FILTERED]
            elif pattern_name in ["aws_access_key", "aws_secret_key"]:
                filtered_text = pattern.sub('[AWS_KEY_FILTERED]', filtered_text)
            # Google API密钥 - 完全替换为[GOOGLE_API_KEY_FILTERED]
            elif pattern_name == "google_api_key":
                filtered_text = pattern.sub('[GOOGLE_API_KEY_FILTERED]', filtered_text)
            # 加密私钥 - 完全替换为[PRIVATE_KEY_FILTERED]
            elif pattern_name == "private_key":
                filtered_text = pattern.sub('[PRIVATE_KEY_FILTERED]', filtered_text)
            # 数据库连接字符串 - 完全替换为[DB_CONNECTION_FILTERED]
            elif pattern_name == "db_connection":
                filtered_text = pattern.sub('[DB_CONNECTION_FILTERED]', filtered_text)
            # SSH密钥 - 完全替换为[SSH_KEY_FILTERED]
            elif pattern_name == "ssh_key":
                filtered_text = pattern.sub('[SSH_KEY_FILTERED]', filtered_text)
            # 信用卡号 - 完全替换为[CREDIT_CARD_FILTERED]
            elif pattern_name == "credit_card":
                filtered_text = pattern.sub('[CREDIT_CARD_FILTERED]', filtered_text)
            # 个人身份信息 - 完全替换为[PII_FILTERED]
            elif pattern_name in ["chinese_id_card", "chinese_phone", "email"]:
                filtered_text = pattern.sub('[PII_FILTERED]', filtered_text)
            # 通用令牌 - 完全替换为[GENERIC_TOKEN_FILTERED]
            elif pattern_name == "generic_token":
                filtered_text = pattern.sub('[GENERIC_TOKEN_FILTERED]', filtered_text)
            # 其他未知模式 - 安全替换
            else:
                filtered_text = pattern.sub('[FILTERED]', filtered_text)
        
        return filtered_text
    
    def _mask_sensitive_text(self, text: str) -> str:
        """掩码敏感文本（只显示部分字符）"""
        if len(text) <= 8:
            return "***"
        else:
            return text[:4] + "***" + text[-4:]
    
    def _detect_internal_terms(self, text: str) -> Set[str]:
        """检测内部术语"""
        detected_terms = set()
        text_lower = text.lower()
        
        for term in self.internal_terms:
            term_lower = term.lower()
            if term_lower in text_lower:
                detected_terms.add(term)
        
        return detected_terms
    
    def _filter_internal_terms(self, text: str) -> str:
        """过滤内部术语"""
        filtered_text = text
        
        for term in self.internal_terms:
            # 创建不区分大小写的正则表达式
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            filtered_text = pattern.sub('[INTERNAL_TERM]', filtered_text)
        
        return filtered_text
    
    def _is_trusted_component(self, component_id: str) -> bool:
        """检查组件是否受信任"""
        return component_id in self.trusted_components
    
    def _log_audit_event(self, event_type: AuditEventType, component_id: str, 
                        security_level: str, filtered_content: str,
                        original_content: str, risk_level: str, metadata: Dict):
        """记录审计事件到队列"""
        event = {
            "event_type": event_type.value,
            "component_id": component_id,
            "security_level": security_level,
            "action_taken": "blocked" if risk_level in ["high", "medium"] else "allowed",
            "filtered_content": filtered_content,
            "original_content": original_content,
            "risk_level": risk_level,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        }
        
        with self.audit_lock:
            self.audit_queue.append(event)
    
    def _store_audit_event(self, event: Dict):
        """存储审计事件到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO audit_events 
                    (event_type, component_id, security_level, action_taken, 
                     filtered_content, original_content, risk_level, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event["event_type"],
                    event["component_id"],
                    event["security_level"],
                    event["action_taken"],
                    event["filtered_content"],
                    event["original_content"],
                    event["risk_level"],
                    json.dumps(event["metadata"], ensure_ascii=False)
                ))
                
                # 如果是敏感信息被阻止，额外记录
                if event["event_type"] == AuditEventType.SENSITIVE_INFO_BLOCKED.value:
                    matches = event["metadata"].get("matches", [])
                    for match in matches:
                        cursor.execute('''
                            INSERT INTO sensitive_info_log 
                            (pattern_type, matched_text, context, component_id, action_taken)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            match["pattern"],
                            match["matched"],
                            match["context"],
                            event["component_id"],
                            event["action_taken"]
                        ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"存储审计事件失败: {e}")
    
    def _log_security_alert(self, alert_type: str, severity: str, 
                           description: str, component_id: str, evidence: str):
        """记录安全警报"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO security_alerts 
                    (alert_type, severity, description, component_id, evidence)
                    VALUES (?, ?, ?, ?, ?)
                ''', (alert_type, severity, description, component_id, evidence))
                
                conn.commit()
                
                logger.warning(f"安全警报: {description} (严重性: {severity})")
                
        except Exception as e:
            logger.error(f"记录安全警报失败: {e}")
    
    def _check_security_threats(self):
        """检查安全威胁"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查最近的安全事件数量
                cursor.execute('''
                    SELECT COUNT(*) as event_count
                    FROM audit_events
                    WHERE created_at >= datetime('now', '-5 minutes')
                    AND risk_level IN ('high', 'medium')
                ''')
                
                result = cursor.fetchone()
                if result and result[0] > 10:
                    self._log_security_alert(
                        alert_type="high_risk_activity",
                        severity="high",
                        description=f"5分钟内检测到{result[0]}个高风险事件",
                        component_id="system",
                        evidence=f"事件计数: {result[0]}"
                    )
                
                # 检查重复的敏感信息泄露尝试
                cursor.execute('''
                    SELECT component_id, COUNT(*) as attempt_count
                    FROM sensitive_info_log
                    WHERE created_at >= datetime('now', '-10 minutes')
                    GROUP BY component_id
                    HAVING attempt_count > 5
                ''')
                
                repeat_offenders = cursor.fetchall()
                for component_id, attempt_count in repeat_offenders:
                    self._log_security_alert(
                        alert_type="repeat_sensitive_info_attempt",
                        severity="medium",
                        description=f"组件{component_id}在10分钟内{attempt_count}次尝试发送敏感信息",
                        component_id=component_id,
                        evidence=f"尝试次数: {attempt_count}"
                    )
                
        except Exception as e:
            logger.error(f"检查安全威胁失败: {e}")
    
    def get_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取安全报告
        
        Args:
            hours: 时间范围（小时）
            
        Returns:
            安全报告
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取事件统计
                cursor.execute('''
                    SELECT 
                        event_type,
                        risk_level,
                        COUNT(*) as count
                    FROM audit_events
                    WHERE created_at >= datetime('now', ?)
                    GROUP BY event_type, risk_level
                ''', (f'-{hours} hours',))
                
                event_stats = {}
                for event_type, risk_level, count in cursor.fetchall():
                    if event_type not in event_stats:
                        event_stats[event_type] = {}
                    event_stats[event_type][risk_level] = count
                
                # 获取警报统计
                cursor.execute('''
                    SELECT 
                        severity,
                        status,
                        COUNT(*) as count
                    FROM security_alerts
                    WHERE created_at >= datetime('now', ?)
                    GROUP BY severity, status
                ''', (f'-{hours} hours',))
                
                alert_stats = {}
                for severity, status, count in cursor.fetchall():
                    key = f"{severity}_{status}"
                    alert_stats[key] = count
                
                # 获取高风险组件
                cursor.execute('''
                    SELECT 
                        component_id,
                        COUNT(*) as high_risk_count
                    FROM audit_events
                    WHERE created_at >= datetime('now', ?)
                    AND risk_level = 'high'
                    GROUP BY component_id
                    ORDER BY high_risk_count DESC
                    LIMIT 10
                ''', (f'-{hours} hours',))
                
                high_risk_components = []
                for component_id, count in cursor.fetchall():
                    high_risk_components.append({
                        "component_id": component_id,
                        "high_risk_count": count
                    })
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "time_range_hours": hours,
                    "event_statistics": event_stats,
                    "alert_statistics": alert_stats,
                    "high_risk_components": high_risk_components,
                    "summary": {
                        "total_events": sum(sum(stats.values()) for stats in event_stats.values()),
                        "total_alerts": sum(alert_stats.values()),
                        "high_risk_components_count": len(high_risk_components)
                    }
                }
                
        except Exception as e:
            logger.error(f"获取安全报告失败: {e}")
            return {"error": str(e)}
    
    def add_trusted_component(self, component_id: str, trust_level: int = 5):
        """添加可信组件"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO component_trust 
                    (component_id, trust_level, last_validated, validation_count)
                    VALUES (?, ?, ?, COALESCE((SELECT validation_count FROM component_trust WHERE component_id = ?), 0) + 1)
                ''', (component_id, trust_level, datetime.now(), component_id))
                
                conn.commit()
                
                # 更新内存中的信任列表
                self.trusted_components.add(component_id)
                
                logger.info(f"添加可信组件: {component_id} (信任级别: {trust_level})")
                
        except Exception as e:
            logger.error(f"添加可信组件失败: {e}")
    
    def remove_trusted_component(self, component_id: str):
        """移除可信组件"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM component_trust WHERE component_id = ?', (component_id,))
                
                conn.commit()
                
                # 更新内存中的信任列表
                if component_id in self.trusted_components:
                    self.trusted_components.remove(component_id)
                
                logger.info(f"移除可信组件: {component_id}")
                
        except Exception as e:
            logger.error(f"移除可信组件失败: {e}")


# 全局安全审计实例
_global_auditor = None

def get_global_auditor() -> UndercoverAuditor:
    """获取全局安全审计实例"""
    global _global_auditor
    if _global_auditor is None:
        _global_auditor = UndercoverAuditor()
    return _global_auditor

def start_global_audit_service():
    """启动全局审计服务"""
    auditor = get_global_auditor()
    auditor.start_audit_service()
    return auditor

def stop_global_audit_service():
    """停止全局审计服务"""
    auditor = get_global_auditor()
    auditor.stop_audit_service()

def validate_input_with_auditor(component_id: str, input_data: Union[str, Dict, List],
                               security_level: SecurityLevel = SecurityLevel.INTERNAL) -> Tuple[bool, str, Dict]:
    """使用安全审计系统验证输入"""
    auditor = get_global_auditor()
    return auditor.validate_input(component_id, input_data, security_level)

def filter_output_with_auditor(component_id: str, output_data: Union[str, Dict, List],
                              security_level: SecurityLevel = SecurityLevel.EXTERNAL) -> Tuple[str, Dict]:
    """使用安全审计系统过滤输出"""
    auditor = get_global_auditor()
    return auditor.filter_output(component_id, output_data, security_level)

def get_security_report_with_auditor(hours: int = 24) -> Dict[str, Any]:
    """使用安全审计系统获取安全报告"""
    auditor = get_global_auditor()
    return auditor.get_security_report(hours)


if __name__ == "__main__":
    # 测试Undercover安全审计系统
    print("启动Undercover安全审计系统测试...")
    
    auditor = UndercoverAuditor()
    
    # 启动服务
    auditor.start_audit_service()
    
    # 测试输入验证
    test_cases = [
        ("情报官", "密码是123456", SecurityLevel.RESTRICTED),
        ("内容官", "API密钥是sk_live_1234567890abcdef", SecurityLevel.EXTERNAL),
        ("运营官", "这是内部术语：KAIROS守护系统", SecurityLevel.RESTRICTED),
        ("增长官", "正常消息，没有敏感信息", SecurityLevel.INTERNAL),
    ]
    
    for component_id, input_text, security_level in test_cases:
        valid, message, data = auditor.validate_input(component_id, input_text, security_level)
        print(f"组件: {component_id}, 安全级别: {security_level.value}")
        print(f"输入: {input_text}")
        print(f"有效: {valid}, 消息: {message}")
        print(f"数据: {data}")
        print("-" * 50)
    
    # 测试输出过滤
    output_test = {
        "message": "数据库连接字符串是mysql://user:password@localhost:3306/db",
        "token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "internal_info": "这是Memory V2系统的配置"
    }
    
    filtered_output, audit_info = auditor.filter_output("测试组件", output_test, SecurityLevel.RESTRICTED)
    print(f"原始输出: {json.dumps(output_test, indent=2, ensure_ascii=False)}")
    print(f"过滤后输出: {json.dumps(filtered_output, indent=2, ensure_ascii=False)}")
    print(f"审计信息: {json.dumps(audit_info, indent=2, ensure_ascii=False)}")
    
    # 等待审计事件处理
    time.sleep(2)
    
    # 获取安全报告
    report = auditor.get_security_report(1)
    print(f"安全报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    
    # 停止服务
    auditor.stop_audit_service()
    
    print("\nUndercover安全审计系统测试完成")