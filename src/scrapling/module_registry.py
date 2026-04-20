#!/usr/bin/env python3
"""
Scrapling模块注册系统
将Scrapling注册为SellAI核心一级模块，设置最高执行优先级
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
    HIGHEST = 5  # Scrapling模块使用最高优先级

class ModuleStatus(Enum):
    """模块状态枚举"""
    REGISTERED = "registered"
    ACTIVE = "active"
    DISABLED = "disabled"
    FAILED = "failed"

class ModuleCapability(Enum):
    """模块能力枚举"""
    GLOBAL_CRAWLING = "global_crawling"  # 全球爬取
    ADAPTIVE_PARSING = "adaptive_parsing"  # 自适应解析
    ANTI_ANTI_CRAWL = "anti_anti_crawl"  # 抗反爬
    PROXY_ROTATION = "proxy_rotation"  # 代理轮换
    SESSION_MANAGEMENT = "session_management"  # 会话管理
    DATA_PROCESSING = "data_processing"  # 数据处理
    MEMORY_INTEGRATION = "memory_integration"  # 记忆集成
    AI_AGENT_ACCESS = "ai_agent_access"  # AI分身访问

class ScraplingModule:
    """
    Scrapling核心模块类
    负责模块注册、初始化、任务管理
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化Scrapling模块
        
        参数：
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.module_id = "scrapling_global_business_intel"
        self.module_name = "Scrapling全球商业情报爬虫"
        self.module_version = "1.0.0"
        self.priority = ModulePriority.HIGHEST
        self.status = ModuleStatus.REGISTERED
        self.capabilities = [
            ModuleCapability.GLOBAL_CRAWLING.value,
            ModuleCapability.ADAPTIVE_PARSING.value,
            ModuleCapability.ANTI_ANTI_CRAWL.value,
            ModuleCapability.PROXY_ROTATION.value,
            ModuleCapability.SESSION_MANAGEMENT.value,
            ModuleCapability.DATA_PROCESSING.value,
            ModuleCapability.MEMORY_INTEGRATION.value,
            ModuleCapability.AI_AGENT_ACCESS.value
        ]
        
        # 强制VPN策略配置
        self.vpn_config = {
            "verify_ssl": False,  # 强制忽略SSL证书错误
            "proxy_servers": [
                "http://proxy-global-1.sellai.com:8080",
                "http://proxy-global-2.sellai.com:8080",
                "http://proxy-global-3.sellai.com:8080"
            ],
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            ],
            "retry_attempts": 3,
            "retry_delay_seconds": 2,
            "timeout_seconds": 30
        }
        
        logger.info(f"初始化Scrapling模块: {self.module_name} v{self.module_version}")
    
    def register(self) -> bool:
        """
        注册Scrapling模块到SellAI核心系统
        
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
                    json.dumps(self.vpn_config),
                    self.module_id
                ))
                logger.info(f"更新Scrapling模块注册信息: {self.module_id}")
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
                    json.dumps(self.vpn_config)
                ))
                logger.info(f"注册Scrapling模块到核心系统: {self.module_id}")
            
            conn.commit()
            conn.close()
            
            # 更新模块状态
            self.status = ModuleStatus.ACTIVE
            logger.info(f"Scrapling模块注册成功，优先级: {self.priority.value}")
            return True
            
        except Exception as e:
            logger.error(f"Scrapling模块注册失败: {e}")
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
            
            # 1. 创建Scrapling任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrapling_tasks (
                    task_id TEXT PRIMARY KEY,
                    target_category TEXT NOT NULL,  -- 目标品类
                    target_regions TEXT NOT NULL,   -- JSON数组格式
                    crawl_config TEXT NOT NULL,     -- JSON格式爬取配置
                    status TEXT NOT NULL CHECK(status IN (
                        'pending', 'running', 'completed', 'failed', 'paused'
                    )),
                    priority INTEGER NOT NULL DEFAULT 3,
                    scheduled_time TIMESTAMP,
                    start_time TIMESTAMP,
                    completion_time TIMESTAMP,
                    result_data TEXT,  -- JSON格式结果数据
                    error_message TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. 创建全球情报数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS global_business_intelligence (
                    intel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_platform TEXT NOT NULL,
                    category TEXT NOT NULL,
                    region TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    keywords TEXT,  -- JSON数组格式
                    estimated_value REAL,
                    confidence_score REAL DEFAULT 0.0,
                    crawl_timestamp TIMESTAMP NOT NULL,
                    processed_at TIMESTAMP,
                    stored_in_memory BOOLEAN DEFAULT FALSE,
                    memory_reference_id TEXT,
                    metadata TEXT,  -- JSON格式
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 3. 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scrapling_tasks_status 
                ON scrapling_tasks(status, priority)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_global_intel_category 
                ON global_business_intelligence(category, region, crawl_timestamp)
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("Scrapling模块数据库表初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"Scrapling模块初始化失败: {e}")
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
            "vpn_config": self.vpn_config,
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
            self.vpn_config.update(config)
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE system_modules 
                SET config = ?, updated_at = CURRENT_TIMESTAMP
                WHERE module_id = ?
            """, (
                json.dumps(self.vpn_config),
                self.module_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info("Scrapling模块配置更新成功")
            return True
            
        except Exception as e:
            logger.error(f"Scrapling模块配置更新失败: {e}")
            return False
    
    def submit_crawl_task(self, target_category: str, target_regions: List[str], 
                         config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        提交爬取任务
        
        参数：
            target_category: 目标品类
            target_regions: 目标地区列表
            config: 爬取配置（可选）
        
        返回：
            任务ID，提交失败返回None
        """
        try:
            import uuid
            import time
            
            task_id = f"scrapling_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # 默认配置
            default_config = {
                "crawl_depth": 3,
                "max_pages": 100,
                "timeout_minutes": 60,
                "data_format": "structured",
                "enable_proxy": True,
                "enable_retry": True
            }
            
            # 合并配置
            crawl_config = default_config.copy()
            if config:
                crawl_config.update(config)
            
            # 保存任务到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO scrapling_tasks 
                (task_id, target_category, target_regions, crawl_config, 
                 status, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                task_id,
                target_category,
                json.dumps(target_regions),
                json.dumps(crawl_config),
                "pending",
                self.priority.value  # 使用模块的最高优先级
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"提交Scrapling爬取任务: {task_id} - {target_category} - {target_regions}")
            return task_id
            
        except Exception as e:
            logger.error(f"提交爬取任务失败: {e}")
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
            
            logger.info("Scrapling模块已关闭")
            return True
            
        except Exception as e:
            logger.error(f"关闭Scrapling模块失败: {e}")
            return False