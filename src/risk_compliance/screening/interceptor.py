"""
内容拦截器模块
实现高风险内容的自动拦截与处理
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib

from ..database.models import RiskLevel, ComplianceResult, Violation

logger = logging.getLogger(__name__)

@dataclass
class InterceptionRecord:
    """拦截记录"""
    content_id: str
    timestamp: datetime
    risk_level: RiskLevel
    risk_score: float
    reason: str
    violations: List[Violation]
    action: str  # blocked, flagged, warned
    decision_source: str  # rule_engine, ai_model, manual
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content_id": self.content_id,
            "timestamp": self.timestamp.isoformat(),
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "reason": self.reason,
            "violations": [asdict(v) for v in self.violations],
            "action": self.action,
            "decision_source": self.decision_source,
            "metadata": self.metadata
        }

class ContentInterceptor:
    """内容拦截器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "risk_thresholds": {
                "critical": {"score": 0.9, "action": "block"},
                "high": {"score": 0.75, "action": "flag"},
                "medium": {"score": 0.5, "action": "warn"},
                "low": {"score": 0.3, "action": "pass"}
            },
            "auto_interception_enabled": True,
            "notification_channels": ["log", "database"],
            "interception_history_size": 1000
        }
        
        # 拦截历史记录
        self.interception_history: List[InterceptionRecord] = []
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "blocked_count": 0,
            "flagged_count": 0,
            "warned_count": 0,
            "passed_count": 0,
            "avg_processing_time_ms": 0.0
        }
        
        logger.info("ContentInterceptor initialized")
    
    def should_intercept(self, compliance_result: ComplianceResult) -> Tuple[bool, str, str]:
        """
        判断是否需要拦截
        Args:
            compliance_result: 合规检查结果
        Returns:
            (是否拦截, 拦截原因, 执行动作)
        """
        start_time = time.time()
        
        try:
            risk_level = compliance_result.risk_level
            risk_score = compliance_result.risk_score
            
            # 获取风险阈值配置
            thresholds = self.config.get("risk_thresholds", {})
            
            # 根据风险等级确定动作
            if risk_level == RiskLevel.CRITICAL:
                action = thresholds.get("critical", {}).get("action", "block")
                reason = "检测到紧急风险违规"
                should_intercept = True
            
            elif risk_level == RiskLevel.HIGH:
                high_threshold = thresholds.get("high", {}).get("score", 0.75)
                if risk_score >= high_threshold:
                    action = thresholds.get("high", {}).get("action", "flag")
                    reason = f"高风险分数超过阈值: {risk_score:.2f} >= {high_threshold}"
                    should_intercept = True
                else:
                    action = "warn"
                    reason = "高风险但分数未达拦截阈值"
                    should_intercept = False
            
            elif risk_level == RiskLevel.MEDIUM:
                medium_threshold = thresholds.get("medium", {}).get("score", 0.5)
                if risk_score >= medium_threshold:
                    action = thresholds.get("medium", {}).get("action", "warn")
                    reason = f"中风险分数超过阈值: {risk_score:.2f} >= {medium_threshold}"
                    should_intercept = False  # 中等风险只警告不拦截
                else:
                    action = "pass"
                    reason = "风险分数较低"
                    should_intercept = False
            
            else:  # LOW风险
                action = "pass"
                reason = "低风险内容"
                should_intercept = False
            
            # 特殊规则：特定违规类型直接拦截
            if self._has_critical_violation_types(compliance_result.violations):
                should_intercept = True
                action = "block"
                reason = "检测到关键违规类型"
            
            # 更新统计
            processing_time = (time.time() - start_time) * 1000
            self._update_stats(should_intercept, action, processing_time)
            
            logger.debug(f"拦截判断完成: content_id={compliance_result.content_id}, "
                        f"intercept={should_intercept}, action={action}, reason={reason}")
            
            return should_intercept, reason, action
            
        except Exception as e:
            logger.error(f"拦截判断失败: {str(e)}")
            # 出错时保守处理：高风险内容拦截
            return True, "拦截判断过程中发生错误", "block"
    
    def intercept_content(self, content_id: str, risk_level: RiskLevel, 
                         risk_score: float, reason: str, 
                         violations: List[Violation], action: str,
                         metadata: Optional[Dict[str, Any]] = None) -> InterceptionRecord:
        """
        执行内容拦截
        Args:
            content_id: 内容ID
            risk_level: 风险等级
            risk_score: 风险分数
            reason: 拦截原因
            violations: 违规列表
            action: 执行动作（block/flag/warn/pass）
            metadata: 附加元数据
        Returns:
            拦截记录
        """
        record = InterceptionRecord(
            content_id=content_id,
            timestamp=datetime.now(),
            risk_level=risk_level,
            risk_score=risk_score,
            reason=reason,
            violations=violations,
            action=action,
            decision_source="rule_engine",
            metadata=metadata or {}
        )
        
        # 添加时间戳和哈希
        record.metadata["processing_timestamp"] = datetime.now().isoformat()
        record.metadata["record_hash"] = self._generate_record_hash(record)
        
        # 添加到历史记录
        self.interception_history.append(record)
        
        # 限制历史记录大小
        if len(self.interception_history) > self.config.get("interception_history_size", 1000):
            self.interception_history = self.interception_history[-1000:]
        
        # 根据动作执行不同处理
        if action == "block":
            self._handle_blocked_content(record)
        elif action == "flag":
            self._handle_flagged_content(record)
        elif action == "warn":
            self._handle_warned_content(record)
        
        logger.info(f"内容拦截执行: content_id={content_id}, action={action}, "
                   f"risk_level={risk_level.value}, risk_score={risk_score:.2f}")
        
        return record
    
    def process_compliance_result(self, compliance_result: ComplianceResult) -> Dict[str, Any]:
        """
        处理合规检查结果，决定是否拦截
        Args:
            compliance_result: 合规检查结果
        Returns:
            处理结果
        """
        # 判断是否需要拦截
        should_intercept, reason, action = self.should_intercept(compliance_result)
        
        # 执行拦截
        interception_record = None
        if should_intercept or action != "pass":
            interception_record = self.intercept_content(
                content_id=compliance_result.content_id,
                risk_level=compliance_result.risk_level,
                risk_score=compliance_result.risk_score,
                reason=reason,
                violations=compliance_result.violations,
                action=action
            )
        
        # 生成响应
        result = {
            "content_id": compliance_result.content_id,
            "intercepted": should_intercept,
            "action": action,
            "reason": reason,
            "risk_level": compliance_result.risk_level.value,
            "risk_score": compliance_result.risk_score,
            "processing_time_ms": compliance_result.processing_time_ms,
            "violation_count": len(compliance_result.violations),
            "timestamp": datetime.now().isoformat()
        }
        
        if interception_record:
            result["interception_record"] = interception_record.to_dict()
        
        return result
    
    def batch_process(self, compliance_results: List[ComplianceResult]) -> List[Dict[str, Any]]:
        """批量处理合规检查结果"""
        results = []
        
        for compliance_result in compliance_results:
            result = self.process_compliance_result(compliance_result)
            results.append(result)
        
        return results
    
    def get_interception_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取拦截历史记录"""
        history = self.interception_history[-limit:]
        return [record.to_dict() for record in history]
    
    def clear_interception_history(self):
        """清空拦截历史记录"""
        self.interception_history.clear()
        logger.info("拦截历史记录已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_processed": 0,
            "blocked_count": 0,
            "flagged_count": 0,
            "warned_count": 0,
            "passed_count": 0,
            "avg_processing_time_ms": 0.0
        }
        logger.info("拦截统计信息已重置")
    
    def _has_critical_violation_types(self, violations: List[Violation]) -> bool:
        """检查是否有关键违规类型"""
        critical_clause_codes = self.config.get("critical_clause_codes", [
            "FTC_CRITICAL_001",
            "GDPR_CRITICAL_001", 
            "CN_AD_CRITICAL_001"
        ])
        
        for violation in violations:
            if violation.clause_code in critical_clause_codes:
                return True
        
        return False
    
    def _handle_blocked_content(self, record: InterceptionRecord):
        """处理被拦截的内容"""
        # 记录拦截日志
        logger.warning(f"内容被拦截: content_id={record.content_id}, "
                      f"reason={record.reason}, risk_score={record.risk_score:.2f}")
        
        # 发送通知（如果配置了通知通道）
        notification_channels = self.config.get("notification_channels", ["log"])
        
        for channel in notification_channels:
            if channel == "log":
                # 已在上面记录
                pass
            elif channel == "database":
                # 保存到数据库（简化实现）
                self._save_to_database(record)
            elif channel == "email":
                # 发送邮件通知（简化实现）
                self._send_email_notification(record)
            elif channel == "webhook":
                # 发送Webhook通知（简化实现）
                self._send_webhook_notification(record)
    
    def _handle_flagged_content(self, record: InterceptionRecord):
        """处理被标记的内容"""
        logger.info(f"内容被标记: content_id={record.content_id}, "
                   f"reason={record.reason}, risk_score={record.risk_score:.2f}")
        
        # 记录到待审核队列
        self._add_to_review_queue(record)
    
    def _handle_warned_content(self, record: InterceptionRecord):
        """处理被警告的内容"""
        logger.info(f"内容被警告: content_id={record.content_id}, "
                   f"reason={record.reason}, risk_score={record.risk_score:.2f}")
        
        # 生成警告通知
        self._generate_warning_notification(record)
    
    def _update_stats(self, intercepted: bool, action: str, processing_time: float):
        """更新统计信息"""
        self.stats["total_processed"] += 1
        
        if intercepted:
            if action == "block":
                self.stats["blocked_count"] += 1
            elif action == "flag":
                self.stats["flagged_count"] += 1
        else:
            if action == "warn":
                self.stats["warned_count"] += 1
            else:
                self.stats["passed_count"] += 1
        
        # 更新平均处理时间（移动平均）
        current_avg = self.stats["avg_processing_time_ms"]
        n = self.stats["total_processed"]
        self.stats["avg_processing_time_ms"] = (current_avg * (n - 1) + processing_time) / n
    
    def _generate_record_hash(self, record: InterceptionRecord) -> str:
        """生成记录哈希"""
        content_str = f"{record.content_id}_{record.timestamp.isoformat()}_{record.risk_score}"
        return hashlib.md5(content_str.encode()).hexdigest()[:16]
    
    def _save_to_database(self, record: InterceptionRecord):
        """保存到数据库（简化实现）"""
        # 在实际系统中，这里会将记录保存到数据库
        # 简化实现：记录到日志
        logger.debug(f"保存拦截记录到数据库: content_id={record.content_id}")
    
    def _send_email_notification(self, record: InterceptionRecord):
        """发送邮件通知（简化实现）"""
        # 在实际系统中，这里会发送邮件通知
        # 简化实现：记录到日志
        logger.debug(f"发送邮件通知: content_id={record.content_id}")
    
    def _send_webhook_notification(self, record: InterceptionRecord):
        """发送Webhook通知（简化实现）"""
        # 在实际系统中，这里会发送Webhook通知
        # 简化实现：记录到日志
        logger.debug(f"发送Webhook通知: content_id={record.content_id}")
    
    def _add_to_review_queue(self, record: InterceptionRecord):
        """添加到待审核队列（简化实现）"""
        # 在实际系统中，这里会将内容添加到待审核队列
        # 简化实现：记录到日志
        logger.debug(f"添加到待审核队列: content_id={record.content_id}")
    
    def _generate_warning_notification(self, record: InterceptionRecord):
        """生成警告通知（简化实现）"""
        # 在实际系统中，这里会生成警告通知
        # 简化实现：记录到日志
        logger.debug(f"生成警告通知: content_id={record.content_id}")
    
    def export_interception_data(self, file_path: str):
        """导出拦截数据到文件"""
        try:
            data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "total_records": len(self.interception_history),
                    "system_version": "1.0.0"
                },
                "records": [record.to_dict() for record in self.interception_history]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"拦截数据已导出到文件: {file_path}")
            
        except Exception as e:
            logger.error(f"导出拦截数据失败: {str(e)}")
            raise
    
    def import_interception_data(self, file_path: str):
        """从文件导入拦截数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            records = data.get("records", [])
            
            for record_data in records:
                # 转换时间戳
                timestamp_str = record_data.get("timestamp")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = datetime.now()
                
                # 创建拦截记录
                record = InterceptionRecord(
                    content_id=record_data.get("content_id", "unknown"),
                    timestamp=timestamp,
                    risk_level=RiskLevel(record_data.get("risk_level", "medium")),
                    risk_score=record_data.get("risk_score", 0.5),
                    reason=record_data.get("reason", "unknown"),
                    violations=[Violation(**v) for v in record_data.get("violations", [])],
                    action=record_data.get("action", "pass"),
                    decision_source=record_data.get("decision_source", "unknown"),
                    metadata=record_data.get("metadata", {})
                )
                
                self.interception_history.append(record)
            
            logger.info(f"拦截数据已从文件导入: {file_path}, 共{len(records)}条记录")
            
        except Exception as e:
            logger.error(f"导入拦截数据失败: {str(e)}")
            raise