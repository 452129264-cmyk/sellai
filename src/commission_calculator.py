#!/usr/bin/env python3
"""
SellAI v3.0.0 - 佣金计算系统
Commission Calculator
多层分销佣金、团队奖励计算

功能：
- 多层佣金计算
- 分销奖励
- 团队激励
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class CommissionType(Enum):
    DIRECT = "direct"           # 直接推荐
    LEVEL_ONE = "level_one"    # 一级分销
    LEVEL_TWO = "level_two"    # 二级分销
    TEAM_BONUS = "team_bonus"  # 团队奖励
    PERFORMANCE = "performance" # 业绩奖励


@dataclass
class CommissionRule:
    rule_id: str
    name: str
    commission_type: CommissionType
    rate: float  # 百分比
    min_amount: float = 0
    max_amount: Optional[float] = None
    level: int = 0
    active: bool = True


@dataclass
class CommissionRecord:
    record_id: str
    user_id: str
    source_user_id: str  # 产生佣金的来源用户
    order_id: str
    commission_type: CommissionType
    amount: float  # 订单金额
    commission: float  # 佣金金额
    rate: float
    status: str = "pending"  # pending, settled, cancelled
    settled_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class CommissionCalculator:
    """佣金计算器"""
    
    def __init__(self, db_path: str = "data/shared_state/commission.db"):
        self.db_path = db_path
        self.rules: Dict[str, CommissionRule] = {}
        self.records: Dict[str, CommissionRecord] = {}
        self.user_balances: Dict[str, float] = {}
        self._ensure_data_dir()
        self._init_default_rules()
        logger.info("佣金计算器初始化完成")
    
    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_default_rules(self):
        defaults = [
            CommissionRule("rule_001", "直接推荐奖", CommissionType.DIRECT, 15.0),
            CommissionRule("rule_002", "一级分销奖", CommissionType.LEVEL_ONE, 8.0, level=1),
            CommissionRule("rule_003", "二级分销奖", CommissionType.LEVEL_TWO, 5.0, level=2),
            CommissionRule("rule_004", "团队激励奖", CommissionType.TEAM_BONUS, 3.0),
        ]
        for r in defaults:
            self.rules[r.rule_id] = r
    
    def calculate_commission(self, user_id: str, source_user_id: str,
                           order_id: str, amount: float,
                           level: int = 0) -> CommissionRecord:
        """计算佣金"""
        # 找到对应的规则
        if level == 0:
            commission_type = CommissionType.DIRECT
        elif level == 1:
            commission_type = CommissionType.LEVEL_ONE
        elif level == 2:
            commission_type = CommissionType.LEVEL_TWO
        else:
            commission_type = CommissionType.LEVEL_TWO
        
        rule = None
        for r in self.rules.values():
            if r.commission_type == commission_type and r.active:
                rule = r
                break
        
        if not rule:
            logger.warning(f"未找到佣金规则: {commission_type}")
            return None
        
        # 计算佣金
        commission = amount * (rule.rate / 100)
        
        record = CommissionRecord(
            record_id=f"comm_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            source_user_id=source_user_id,
            order_id=order_id,
            commission_type=commission_type,
            amount=amount,
            commission=commission,
            rate=rule.rate
        )
        
        self.records[record.record_id] = record
        
        # 更新用户余额
        self.user_balances[user_id] = self.user_balances.get(user_id, 0) + commission
        
        logger.info(f"计算佣金: {user_id} 获得 {commission}")
        return record
    
    def get_user_commissions(self, user_id: str,
                            status: Optional[str] = None) -> List[CommissionRecord]:
        records = [r for r in self.records.values() if r.user_id == user_id]
        if status:
            records = [r for r in records if r.status == status]
        records.sort(key=lambda x: x.created_at, reverse=True)
        return records
    
    def get_user_balance(self, user_id: str) -> Dict[str, float]:
        """获取用户佣金余额"""
        records = self.get_user_commissions(user_id, status="pending")
        pending = sum(r.commission for r in records)
        settled = sum(
            r.commission for r in self.get_user_commissions(user_id, status="settled")
        )
        total = self.user_balances.get(user_id, 0)
        
        return {
            "pending": pending,
            "settled": settled,
            "total": total
        }
    
    def settle_commission(self, record_id: str) -> bool:
        """结算佣金"""
        record = self.records.get(record_id)
        if not record or record.status != "pending":
            return False
        
        record.status = "settled"
        record.settled_at = datetime.now().isoformat()
        logger.info(f"结算佣金: {record_id}")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        total_commission = sum(r.commission for r in self.records.values())
        return {
            "module": "CommissionCalculator",
            "total_records": len(self.records),
            "total_commission": total_commission,
            "active_users": len(self.user_balances),
            "pending_settlement": len([r for r in self.records.values() if r.status == "pending"])
        }


__all__ = ["CommissionCalculator", "CommissionRule", "CommissionRecord", "CommissionType"]
