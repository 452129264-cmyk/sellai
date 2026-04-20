#!/usr/bin/env python3
"""
HyperHorse模块注册系统
将HyperHorse注册为SellAI核心一级模块，设置最高执行优先级
确保系统默认优先调用HyperHorse引擎而非第三方模型
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class ModulePriority(Enum):
    """模块优先级枚举"""
    LOWEST = 1
    LOW = 2
    NORMAL = 3
    HIGH = 4
    HIGHEST = 5  # HyperHorse模块使用最高优先级

class ModuleStatus(Enum):
    """模块状态枚举"""
    REGISTERED = "registered"
    ACTIVE = "active"
    DISABLED = "disabled"
    FAILED = "failed"

class HyperHorseCapability(Enum):
    """HyperHorse模块能力枚举"""
    GLOBAL_COMMERCIAL_NATIVE = "global_commercial_native"  # 全球商业原生
    AUTONOMOUS_PLANNING = "autonomous_planning"           # 自主策划
    END_TO_END_GENERATION = "end_to_end_generation"       # 全链路生成
    EVOLUTIONARY_GENERATION = "evolutionary_generation"   # 进化式生成
    MULTILINGUAL_ADAPTATION = "multilingual_adaptation"   # 多语言适配
    ONE_CLICK_PUBLISHING = "one_click_publishing"         # 一键发布
    REAL_TIME_TREND_ANALYSIS = "real_time_trend_analysis" # 实时趋势分析
    HIGH_CONVERSION_SCRIPT = "high_conversion_script"     # 高转化脚本生成
    MULTI_PLATFORM_DISTRIBUTION = "multi_platform_distribution"  # 多平台分发
    PERFORMANCE_TRACKING = "performance_tracking"         # 效果追踪

class HyperHorseModule:
    """
    HyperHorse核心模块类
    负责模块注册、初始化、与无限分身架构集成
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化HyperHorse模块
        
        参数：
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.module_id = "hyperhorse_video_engine"
        self.module_name = "HyperHorse自研视频引擎"
        self.module_version = "1.0.0"
        self.priority = ModulePriority.HIGHEST
        self.status = ModuleStatus.REGISTERED
        self.capabilities = [
            HyperHorseCapability.GLOBAL_COMMERCIAL_NATIVE.value,
            HyperHorseCapability.AUTONOMOUS_PLANNING.value,
            HyperHorseCapability.END_TO_END_GENERATION.value,
            HyperHorseCapability.EVOLUTIONARY_GENERATION.value,
            HyperHorseCapability.MULTILINGUAL_ADAPTATION.value,
            HyperHorseCapability.ONE_CLICK_PUBLISHING.value,
            HyperHorseCapability.REAL_TIME_TREND_ANALYSIS.value,
            HyperHorseCapability.HIGH_CONVERSION_SCRIPT.value,
            HyperHorseCapability.MULTI_PLATFORM_DISTRIBUTION.value,
            HyperHorseCapability.PERFORMANCE_TRACKING.value
        ]
        
        # 引擎配置
        self.engine_config = {
            "model_version": "hyperhorse_v1.0",
            "performance_mode": "high_conversion",  # 高转化模式
            "default_languages": ["en", "es", "ar", "pt"],  # 英语、西语、阿语、葡语
            "supported_platforms": [
                "tiktok", "instagram", "youtube_shorts", "facebook_reels",
                "shopify", "amazon", "aliexpress", "independent_site"
            ],
            "generation_pipeline": [
                "trend_analysis",
                "script_generation",
                "visual_generation",
                "voice_synthesis",
                "video_composition",
                "platform_adaptation"
            ],
            "optimization_features": [
                "real_time_trend_adaptation",
                "audience_segmentation",
                "conversion_prediction",
                "content_evolution"
            ],
            "integration_hooks": [
                "global_business_brain",
                "memory_v2_system",
                "infinite_agents_architecture",
                "gen_video_skill_compatibility"
            ]
        }
        
        logger.info(f"初始化HyperHorse模块: {self.module_name} v{self.module_version}")
    
    def register(self) -> bool:
        """
        注册HyperHorse模块到SellAI核心系统
        
        返回：
            注册成功返回True，失败返回False
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建模块注册表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_modules (
                    module_id TEXT PRIMARY KEY,
                    module_name TEXT NOT NULL,
                    module_version TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 3,
                    status TEXT NOT NULL CHECK(status IN (
                        'registered', 'active', 'disabled', 'failed'
                    )),
                    capabilities TEXT NOT NULL,  -- JSON数组格式
                    config TEXT NOT NULL,  -- JSON格式
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP,
                    metadata TEXT  -- JSON格式
                )
            """)
            
            # 检查模块是否已注册
            cursor.execute(
                "SELECT COUNT(*) FROM system_modules WHERE module_id = ?",
                (self.module_id,)
            )
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                # 更新模块信息
                cursor.execute("""
                    UPDATE system_modules 
                    SET module_name = ?, module_version = ?, priority = ?,
                        status = ?, capabilities = ?, config = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE module_id = ?
                """, (
                    self.module_name,
                    self.module_version,
                    self.priority.value,
                    self.status.value,
                    json.dumps(self.capabilities),
                    json.dumps(self.engine_config),
                    self.module_id
                ))
                logger.info(f"更新HyperHorse模块注册信息: {self.module_id}")
            else:
                # 插入新模块
                cursor.execute("""
                    INSERT INTO system_modules 
                    (module_id, module_name, module_version, priority, status, 
                     capabilities, config, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    self.module_id,
                    self.module_name,
                    self.module_version,
                    self.priority.value,
                    self.status.value,
                    json.dumps(self.capabilities),
                    json.dumps(self.engine_config)
                ))
                logger.info(f"注册HyperHorse模块到核心系统: {self.module_id}")
            
            conn.commit()
            conn.close()
            
            # 更新模块状态
            self.status = ModuleStatus.ACTIVE
            logger.info(f"HyperHorse模块注册成功，优先级: {self.priority.value}")
            return True
            
        except Exception as e:
            logger.error(f"HyperHorse模块注册失败: {e}")
            self.status = ModuleStatus.FAILED
            return False
    
    def initialize(self) -> bool:
        """
        初始化模块，创建必要的数据库表和配置
        
        返回：
            初始化成功返回True，失败返回False
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. 创建HyperHorse任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hyperhorse_tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,  -- 任务类型: video_generation, script_writing等
                    target_category TEXT NOT NULL,  -- 目标品类
                    target_regions TEXT NOT NULL,   -- JSON数组格式
                    generation_config TEXT NOT NULL,  -- JSON格式生成配置
                    status TEXT NOT NULL CHECK(status IN (
                        'pending', 'running', 'completed', 'failed', 'paused'
                    )),
                    priority INTEGER NOT NULL DEFAULT 5,  # 最高优先级
                    scheduled_time TIMESTAMP,
                    start_time TIMESTAMP,
                    completion_time TIMESTAMP,
                    result_data TEXT,  -- JSON格式结果数据
                    error_message TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. 创建视频内容性能追踪表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hyperhorse_performance_metrics (
                    content_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    category TEXT NOT NULL,
                    region TEXT NOT NULL,
                    generation_timestamp TIMESTAMP NOT NULL,
                    views INTEGER DEFAULT 0,
                    engagements INTEGER DEFAULT 0,
                    conversions INTEGER DEFAULT 0,
                    conversion_rate REAL DEFAULT 0.0,
                    revenue_generated REAL DEFAULT 0.0,
                    performance_score REAL DEFAULT 0.0,
                    trend_alignment_score REAL DEFAULT 0.0,
                    audience_fit_score REAL DEFAULT 0.0,
                    optimization_actions TEXT,  -- JSON格式优化操作记录
                    metadata TEXT,  -- JSON格式
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES hyperhorse_tasks(task_id)
                )
            """)
            
            # 3. 创建爆款结构记忆表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hyperhorse_success_patterns (
                    pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    region TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,  -- script_structure, visual_style, music_choice等
                    pattern_data TEXT NOT NULL,  -- JSON格式模式数据
                    success_score REAL DEFAULT 0.0,
                    usage_count INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hyperhorse_tasks_status 
                ON hyperhorse_tasks(status, priority)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hyperhorse_performance_metrics 
                ON hyperhorse_performance_metrics(task_id, platform, performance_score)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hyperhorse_success_patterns 
                ON hyperhorse_success_patterns(category, region, success_score)
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("HyperHorse模块数据库表初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"HyperHorse模块初始化失败: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取模块状态信息
        
        返回：
            模块状态字典
        """
        return {
            "module_id": self.module_id,
            "module_name": self.module_name,
            "module_version": self.module_version,
            "priority": self.priority.value,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "engine_config": self.engine_config,
            "timestamp": datetime.now().isoformat()
        }
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        更新模块配置
        
        参数：
            config: 新的配置字典
        
        返回：
            更新成功返回True，失败返回False
        """
        try:
            # 合并配置
            self.engine_config.update(config)
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE system_modules 
                SET config = ?, updated_at = CURRENT_TIMESTAMP
                WHERE module_id = ?
            """, (
                json.dumps(self.engine_config),
                self.module_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info("HyperHorse模块配置更新成功")
            return True
            
        except Exception as e:
            logger.error(f"HyperHorse模块配置更新失败: {e}")
            return False
    
    def submit_video_generation_task(self, target_category: str, target_regions: List[str], 
                                   config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        提交视频生成任务
        
        参数：
            target_category: 目标品类
            target_regions: 目标地区列表
            config: 生成配置（可选）
        
        返回：
            任务ID，提交失败返回None
        """
        try:
            import uuid
            import time
            
            task_id = f"hyperhorse_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # 默认配置
            default_config = {
                "video_duration_seconds": 60,
                "aspect_ratio": "9:16",  # 短视频竖屏
                "resolution": "1080x1920",
                "frame_rate": 30,
                "language_adaptation": True,
                "trend_analysis": True,
                "conversion_optimization": True,
                "multi_platform_output": True,
                "performance_tracking": True
            }
            
            # 合并配置
            generation_config = default_config.copy()
            if config:
                generation_config.update(config)
            
            # 保存任务到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO hyperhorse_tasks 
                (task_id, task_type, target_category, target_regions, generation_config, 
                 status, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                task_id,
                "video_generation",
                target_category,
                json.dumps(target_regions),
                json.dumps(generation_config),
                "pending",
                self.priority.value  # 使用模块的最高优先级
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"提交HyperHorse视频生成任务: {task_id} - {target_category} - {target_regions}")
            return task_id
            
        except Exception as e:
            logger.error(f"提交视频生成任务失败: {e}")
            return None
    
    def shutdown(self) -> bool:
        """
        关闭模块
        
        返回：
            关闭成功返回True，失败返回False
        """
        try:
            # 更新状态为禁用
            self.status = ModuleStatus.DISABLED
            
            # 更新数据库状态
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE system_modules 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE module_id = ?
            """, (
                self.status.value,
                self.module_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info("HyperHorse模块已关闭")
            return True
            
        except Exception as e:
            logger.error(f"关闭HyperHorse模块失败: {e}")
            return False