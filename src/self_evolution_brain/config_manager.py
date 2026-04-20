#!/usr/bin/env python3
"""
自主迭代进化大脑配置管理器
管理复盘策略、优化目标、经验沉淀等配置参数
"""

import json
import os
import yaml
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReviewStrategy:
    """复盘策略配置"""
    # 复盘时间（每天几点执行）
    review_time: time = time(hour=0, minute=0)  # 默认凌晨0点
    
    # 复盘数据源
    data_sources: List[str] = field(default_factory=lambda: [
        "industry_resources",  # 行业资源库
        "market_analysis",     # 市场分析数据
        "business_performance", # 业务绩效数据
        "ai_negotiation",      # AI谈判记录
        "user_feedback"        # 用户反馈
    ])
    
    # 复盘周期（天）
    review_period_days: int = 7
    
    # 是否启用实时复盘
    enable_realtime_review: bool = True
    
    # 复盘深度级别：basic, standard, deep
    review_depth: str = "standard"


@dataclass
class OptimizationTarget:
    """优化目标配置"""
    # 核心优化目标
    targets: List[str] = field(default_factory=lambda: [
        "business_strategy_effectiveness",  # 商业策略有效性
        "ai_avatar_performance",            # AI分身性能
        "resource_allocation_efficiency",   # 资源分配效率
        "market_opportunity_identification", # 市场机会识别准确率
        "risk_management_capability",       # 风险管理能力
        "user_satisfaction_level"           # 用户满意度
    ])
    
    # 优化权重（0-1之间，总和为1）
    target_weights: Dict[str, float] = field(default_factory=lambda: {
        "business_strategy_effectiveness": 0.25,
        "ai_avatar_performance": 0.15,
        "resource_allocation_efficiency": 0.15,
        "market_opportunity_identification": 0.20,
        "risk_management_capability": 0.15,
        "user_satisfaction_level": 0.10
    })
    
    # 优化指标阈值
    improvement_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "min_improvement_rate": 0.05,  # 最小改进率
        "max_regression_rate": 0.03,   # 最大退步率
        "confidence_level": 0.8        # 置信水平
    })
    
    # 优化频率
    optimization_frequency_hours: int = 24


@dataclass
class ExperiencePersistenceConfig:
    """经验沉淀配置"""
    # Notebook LM集成配置
    notebook_lm_integration: Dict[str, Any] = field(default_factory=lambda: {
        "enable": True,
        "knowledge_base_id": "sellai_evolution_experiences",
        "sync_frequency_hours": 6,
        "max_experience_size_mb": 100,
        "compression_enabled": True
    })
    
    # 经验分类体系
    experience_categories: List[str] = field(default_factory=lambda: [
        "strategy_insights",      # 策略洞察
        "performance_patterns",   # 绩效模式
        "market_trends",          # 市场趋势
        "risk_lessons",           # 风险教训
        "user_preferences",       # 用户偏好
        "technology_adoption"     # 技术采纳
    ])
    
    # 经验保留策略
    retention_policy: Dict[str, Any] = field(default_factory=lambda: {
        "keep_all": False,
        "max_entries_per_category": 1000,
        "auto_prune_enabled": True,
        "prune_frequency_days": 30
    })
    
    # 经验质量评估
    quality_assessment: Dict[str, Any] = field(default_factory=lambda: {
        "min_confidence_score": 0.7,
        "min_impact_score": 0.5,
        "require_validation": True,
        "validation_period_days": 7
    })


@dataclass
class SelfEvolutionConfig:
    """自主迭代进化大脑总配置"""
    # 版本标识
    version: str = "1.0.0"
    
    # 节点标识
    node_id: str = "default_evolution_node"
    
    # 是否启用自主进化
    enabled: bool = True
    
    # 复盘策略
    review_strategy: ReviewStrategy = field(default_factory=ReviewStrategy)
    
    # 优化目标
    optimization_target: OptimizationTarget = field(default_factory=OptimizationTarget)
    
    # 经验沉淀
    experience_persistence: ExperiencePersistenceConfig = field(default_factory=ExperiencePersistenceConfig)
    
    # 数据库路径
    db_path: str = "data/shared_state/state.db"
    
    # 日志配置
    log_config: Dict[str, Any] = field(default_factory=lambda: {
        "level": "INFO",
        "file": "logs/self_evolution.log",
        "max_size_mb": 10,
        "backup_count": 5
    })
    
    # 性能监控
    performance_monitoring: Dict[str, Any] = field(default_factory=lambda: {
        "enable": True,
        "collection_interval_minutes": 60,
        "metrics_retention_days": 90,
        "alert_thresholds": {
            "error_rate": 0.05,
            "latency_ms": 1000,
            "memory_usage_percent": 80
        }
    })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), default=str, indent=2, ensure_ascii=False)
    
    def to_yaml(self) -> str:
        """转换为YAML字符串"""
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)
    
    def save_to_file(self, file_path: str, format: str = "json"):
        """
        保存配置到文件
        
        Args:
            file_path: 文件路径
            format: 文件格式 (json, yaml)
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            if format.lower() == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.to_json())
            elif format.lower() == "yaml":
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.to_yaml())
            else:
                raise ValueError(f"不支持的格式: {format}")
            
            logger.info(f"配置已保存到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str, format: str = "json"):
        """
        从文件加载配置
        
        Args:
            file_path: 文件路径
            format: 文件格式 (json, yaml)
            
        Returns:
            SelfEvolutionConfig实例
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"配置文件不存在: {file_path}，使用默认配置")
                return cls()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if format.lower() == "json":
                    data = json.load(f)
                elif format.lower() == "yaml":
                    data = yaml.safe_load(f)
                else:
                    raise ValueError(f"不支持的格式: {format}")
            
            # 递归重建配置对象
            def dict_to_obj(data_dict, obj_class):
                if not isinstance(data_dict, dict):
                    return data_dict
                
                # 获取字段类型注解
                import inspect
                type_hints = inspect.get_annotations(obj_class)
                
                kwargs = {}
                for field_name, field_type in type_hints.items():
                    if field_name in data_dict:
                        value = data_dict[field_name]
                        
                        # 处理复杂类型
                        if hasattr(field_type, '__origin__') and field_type.__origin__ == list:
                            # List类型
                            item_type = field_type.__args__[0]
                            if isinstance(value, list):
                                kwargs[field_name] = [dict_to_obj(item, item_type) if isinstance(item, dict) and hasattr(item_type, '__annotations__') else item for item in value]
                            else:
                                kwargs[field_name] = value
                        elif hasattr(field_type, '__annotations__'):
                            # 自定义数据类型
                            kwargs[field_name] = dict_to_obj(value, field_type)
                        elif field_type == time:
                            # 时间类型
                            if isinstance(value, str):
                                hour, minute, *second = value.split(':')
                                second = int(second[0]) if second else 0
                                kwargs[field_name] = time(int(hour), int(minute), second)
                            else:
                                kwargs[field_name] = value
                        else:
                            # 基本类型
                            kwargs[field_name] = value
                
                return obj_class(**kwargs)
            
            config = dict_to_obj(data, cls)
            logger.info(f"配置已从文件加载: {file_path}")
            return config
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}，使用默认配置")
            return cls()
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证配置有效性
        
        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []
        
        # 检查优化权重总和
        weights_sum = sum(self.optimization_target.target_weights.values())
        if abs(weights_sum - 1.0) > 0.001:
            errors.append(f"优化权重总和应为1.0，当前为{weights_sum:.3f}")
        
        # 检查数据库路径
        if not self.db_path.endswith('.db'):
            errors.append(f"数据库路径应以.db结尾: {self.db_path}")
        
        # 检查日志级别
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_config.get("level", "INFO").upper() not in valid_log_levels:
            errors.append(f"无效的日志级别: {self.log_config.get('level')}")
        
        return len(errors) == 0, errors


def load_default_config() -> SelfEvolutionConfig:
    """加载默认配置"""
    return SelfEvolutionConfig()


if __name__ == "__main__":
    # 测试配置
    config = load_default_config()
    print("默认配置:")
    print(config.to_json())
    
    # 验证配置
    is_valid, errors = config.validate()
    print(f"配置有效性: {is_valid}")
    if errors:
        print("错误列表:")
        for error in errors:
            print(f"  - {error}")