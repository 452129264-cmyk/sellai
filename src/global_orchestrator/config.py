"""
全局调度器配置管理模块
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class CapabilityType(Enum):
    """八大能力类型枚举"""
    FIRECRAWL = "firecrawl"
    DEEPL = "deepl"
    MULTILINGUAL = "multilingual"
    RISK_COMPLIANCE = "risk_compliance"
    BUSINESS_ANALYSIS = "business_analysis"
    VISUAL_GENERATION = "visual_generation"
    VIDEO_GENERATION = "video_generation"
    SELF_EVOLUTION = "self_evolution"


@dataclass
class CapabilityConfig:
    """单能力配置"""
    capability_type: CapabilityType
    enabled: bool = True
    priority: int = 5  # 1-10，越高优先级越高
    timeout_seconds: int = 300
    retry_count: int = 3
    adapter_class: Optional[str] = None
    module_path: Optional[str] = None
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataFlowConfig:
    """数据流配置"""
    enable_auto_routing: bool = True
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    validation_enabled: bool = True
    logging_level: str = "INFO"
    max_data_size_mb: int = 10


@dataclass
class WorkflowConfig:
    """工作流配置"""
    max_concurrent_workflows: int = 10
    default_timeout_seconds: int = 1800
    enable_checkpoints: bool = True
    checkpoint_dir: str = "data/checkpoints"
    recovery_enabled: bool = True
    max_retry_count: int = 3


@dataclass
class OrchestratorConfig:
    """全局调度器配置"""
    # 基础配置
    node_id: str = "default_orchestrator"
    log_level: str = "INFO"
    db_path: str = "data/shared_state/state.db"
    
    # 能力配置
    capabilities: Dict[CapabilityType, CapabilityConfig] = field(default_factory=dict)
    
    # 子系统配置
    data_flow: DataFlowConfig = field(default_factory=DataFlowConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    
    # 集成配置
    enable_avatar_system: bool = True
    enable_notebook_lm: bool = True
    enable_memory_v2: bool = True
    enable_claude_code: bool = True
    
    def __post_init__(self):
        """初始化默认能力配置"""
        if not self.capabilities:
            for cap_type in CapabilityType:
                self.capabilities[cap_type] = CapabilityConfig(
                    capability_type=cap_type,
                    enabled=True,
                    priority=5,
                    timeout_seconds=300,
                    retry_count=3
                )
    
    @classmethod
    def from_file(cls, config_path: str) -> "OrchestratorConfig":
        """从配置文件加载配置"""
        if not os.path.exists(config_path):
            return cls()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        return cls._from_dict(config_data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "OrchestratorConfig":
        """从字典创建配置对象"""
        # 创建基础配置
        config = cls(
            node_id=data.get("node_id", "default_orchestrator"),
            log_level=data.get("log_level", "INFO"),
            db_path=data.get("db_path", "data/shared_state/state.db"),
            enable_avatar_system=data.get("enable_avatar_system", True),
            enable_notebook_lm=data.get("enable_notebook_lm", True),
            enable_memory_v2=data.get("enable_memory_v2", True),
            enable_claude_code=data.get("enable_claude_code", True)
        )
        
        # 处理能力配置
        if "capabilities" in data:
            for cap_str, cap_data in data["capabilities"].items():
                try:
                    cap_type = CapabilityType(cap_str)
                    cap_config = CapabilityConfig(
                        capability_type=cap_type,
                        enabled=cap_data.get("enabled", True),
                        priority=cap_data.get("priority", 5),
                        timeout_seconds=cap_data.get("timeout_seconds", 300),
                        retry_count=cap_data.get("retry_count", 3),
                        adapter_class=cap_data.get("adapter_class"),
                        module_path=cap_data.get("module_path"),
                        api_key=cap_data.get("api_key"),
                        endpoint=cap_data.get("endpoint"),
                        custom_params=cap_data.get("custom_params", {})
                    )
                    config.capabilities[cap_type] = cap_config
                except ValueError:
                    continue
        
        # 处理数据流配置
        if "data_flow" in data:
            flow_data = data["data_flow"]
            config.data_flow = DataFlowConfig(
                enable_auto_routing=flow_data.get("enable_auto_routing", True),
                cache_enabled=flow_data.get("cache_enabled", True),
                cache_ttl_seconds=flow_data.get("cache_ttl_seconds", 3600),
                validation_enabled=flow_data.get("validation_enabled", True),
                logging_level=flow_data.get("logging_level", "INFO"),
                max_data_size_mb=flow_data.get("max_data_size_mb", 10)
            )
        
        # 处理工作流配置
        if "workflow" in data:
            wf_data = data["workflow"]
            config.workflow = WorkflowConfig(
                max_concurrent_workflows=wf_data.get("max_concurrent_workflows", 10),
                default_timeout_seconds=wf_data.get("default_timeout_seconds", 1800),
                enable_checkpoints=wf_data.get("enable_checkpoints", True),
                checkpoint_dir=wf_data.get("checkpoint_dir", "data/checkpoints"),
                recovery_enabled=wf_data.get("recovery_enabled", True),
                max_retry_count=wf_data.get("max_retry_count", 3)
            )
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "log_level": self.log_level,
            "db_path": self.db_path,
            "enable_avatar_system": self.enable_avatar_system,
            "enable_notebook_lm": self.enable_notebook_lm,
            "enable_memory_v2": self.enable_memory_v2,
            "enable_claude_code": self.enable_claude_code,
            "capabilities": {
                cap_type.value: {
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "timeout_seconds": config.timeout_seconds,
                    "retry_count": config.retry_count,
                    "adapter_class": config.adapter_class,
                    "module_path": config.module_path,
                    "api_key": config.api_key,
                    "endpoint": config.endpoint,
                    "custom_params": config.custom_params
                }
                for cap_type, config in self.capabilities.items()
            },
            "data_flow": {
                "enable_auto_routing": self.data_flow.enable_auto_routing,
                "cache_enabled": self.data_flow.cache_enabled,
                "cache_ttl_seconds": self.data_flow.cache_ttl_seconds,
                "validation_enabled": self.data_flow.validation_enabled,
                "logging_level": self.data_flow.logging_level,
                "max_data_size_mb": self.data_flow.max_data_size_mb
            },
            "workflow": {
                "max_concurrent_workflows": self.workflow.max_concurrent_workflows,
                "default_timeout_seconds": self.workflow.default_timeout_seconds,
                "enable_checkpoints": self.workflow.enable_checkpoints,
                "checkpoint_dir": self.workflow.checkpoint_dir,
                "recovery_enabled": self.workflow.recovery_enabled,
                "max_retry_count": self.workflow.max_retry_count
            }
        }
    
    def save_to_file(self, config_path: str):
        """保存配置到文件"""
        config_dir = os.path.dirname(config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# 默认配置实例
DEFAULT_CONFIG = OrchestratorConfig()