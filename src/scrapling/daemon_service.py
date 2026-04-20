#!/usr/bin/env python3
"""
Scrapling守护进程服务
实现24小时全自动、每30分钟全球全品类商业情报爬取
"""

import json
import logging
import time
import threading
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import schedule
import signal
import sys
import os

logger = logging.getLogger(__name__)

class ScraplingDaemon:
    """
    Scrapling守护进程
    实现定时爬取、状态监控、自动恢复等功能
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化守护进程
        
        参数：
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.running = False
        self.main_thread = None
        self.scheduler_thread = None
        
        # 配置
        self.config = {
            "crawl_interval_seconds": 1800,  # 30分钟
            "max_concurrent_tasks": 3,
            "auto_retry_failed": True,
            "max_retry_attempts": 3,
            "health_check_interval": 300,  # 5分钟
            "log_retention_days": 7
        }
        
        # 状态
        self.status = {
            "started_at": None,
            "last_crawl_time": None,
            "total_crawl_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "active_tasks": 0,
            "last_error": None,
            "health_status": "unknown"  # healthy, degraded, unknown
        }
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 导入爬虫引擎
        try:
            from .crawler_engine import ScraplingCrawlerEngine
            self.crawler_engine = ScraplingCrawlerEngine(db_path)
        except ImportError as e:
            logger.error(f"导入爬虫引擎失败: {e}")
            self.crawler_engine = None
        
        # 导入配置管理器
        try:
            from .config_manager import GlobalConfigManager
            self.config_manager = GlobalConfigManager(db_path)
        except ImportError as e:
            logger.error(f"导入配置管理器失败: {e}")
            self.config_manager = None
        
        logger.info("Scrapling守护进程初始化完成")
    
    def start(self) -> bool:
        """
        启动守护进程
        
        返回：
            启动成功返回True，失败返回False
        """
        with self.lock:
            if self.running:
                logger.warning("守护进程已在运行")
                return True
            
            try:
                # 初始化数据库表
                if not self._init_database_tables():
                    logger.error("数据库表初始化失败")
                    return False
                
                # 设置信号处理
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
                
                # 启动调度器线程
                self.running = True
                self.status["started_at"] = datetime.now().isoformat()
                
                # 启动主线程
                self.main_thread = threading.Thread(
                    target=self._main_loop,
                    name="ScraplingDaemon-Main",
                    daemon=True
                )
                self.main_thread.start()
                
                # 启动调度线程
                self.scheduler_thread = threading.Thread(
                    target=self._scheduler_loop,
                    name="ScraplingDaemon-Scheduler",
                    daemon=True
                )
                self.scheduler_thread.start()
                
                logger.info(f"Scrapling守护进程启动成功，爬取间隔: {self.config['crawl_interval_seconds']}秒")
                
                # 立即执行一次爬取
                self._trigger_crawl_cycle()
                
                return True
                
            except Exception as e:
                logger.error(f"守护进程启动失败: {e}")
                self.running = False
                return False
    
    def stop(self) -> bool:
        """
        停止守护进程
        
        返回：
            停止成功返回True，失败返回False
        """
        with self.lock:
            if not self.running:
                logger.warning("守护进程未在运行")
                return True
            
            try:
                self.running = False
                
                # 等待线程结束
                if self.main_thread and self.main_thread.is_alive():
                    self.main_thread.join(timeout=10)
                
                if self.scheduler_thread and self.scheduler_thread.is_alive():
                    self.scheduler_thread.join(timeout=10)
                
                logger.info("Scrapling守护进程已停止")
                return True
                
            except Exception as e:
                logger.error(f"守护进程停止失败: {e}")
                return False
    
    def _init_database_tables(self) -> bool:
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建守护进程状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrapling_daemon_status (
                    status_key TEXT PRIMARY KEY,
                    status_value TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建爬取历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrapling_crawl_history (
                    cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    total_categories INTEGER DEFAULT 0,
                    success_categories INTEGER DEFAULT 0,
                    failed_categories INTEGER DEFAULT 0,
                    total_intel_items INTEGER DEFAULT 0,
                    errors TEXT,  -- JSON数组格式
                    status TEXT NOT NULL CHECK(status IN (
                        'running', 'completed', 'failed', 'interrupted'
                    )),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建系统运行日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrapling_system_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_level TEXT NOT NULL CHECK(log_level IN (
                        'info', 'warning', 'error', 'critical'
                    )),
                    log_message TEXT NOT NULL,
                    component TEXT,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_crawl_history_time 
                ON scrapling_crawl_history(start_time, status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_system_logs_time 
                ON scrapling_system_logs(timestamp, log_level)
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("守护进程数据库表初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"数据库表初始化失败: {e}")
            return False
    
    def _main_loop(self) -> None:
        """主循环"""
        logger.info("守护进程主循环启动")
        
        while self.running:
            try:
                # 健康检查
                self._perform_health_check()
                
                # 清理旧日志
                self._cleanup_old_logs()
                
                # 更新状态
                self._update_daemon_status()
                
                # 休眠一段时间
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"主循环异常: {e}")
                time.sleep(30)
    
    def _scheduler_loop(self) -> None:
        """调度器循环"""
        logger.info("调度器循环启动")
        
        # 配置定时任务
        interval_seconds = self.config["crawl_interval_seconds"]
        
        # 使用schedule库设置定时任务
        schedule.every(interval_seconds).seconds.do(
            self._trigger_crawl_cycle
        )
        
        logger.info(f"定时任务配置完成，每{interval_seconds}秒执行一次爬取")
        
        while self.running:
            try:
                # 运行待执行的调度任务
                schedule.run_pending()
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"调度器异常: {e}")
                time.sleep(5)
    
    def _trigger_crawl_cycle(self) -> None:
        """触发爬取周期"""
        if not self.running:
            return
        
        with self.lock:
            try:
                # 检查并发任务数
                if self.status["active_tasks"] >= self.config["max_concurrent_tasks"]:
                    logger.warning(f"并发任务数已达上限: {self.status['active_tasks']}")
                    return
                
                # 记录开始时间
                cycle_start = datetime.now()
                cycle_id = self._start_crawl_cycle_record(cycle_start)
                
                logger.info(f"开始第{self.status['total_crawl_cycles'] + 1}次爬取周期")
                
                # 增加活动任务计数
                self.status["active_tasks"] += 1
                self.status["total_crawl_cycles"] += 1
                
                # 启动异步爬取
                crawl_thread = threading.Thread(
                    target=self._execute_crawl_cycle,
                    args=(cycle_id, cycle_start),
                    name=f"ScraplingCrawlCycle-{cycle_id}",
                    daemon=True
                )
                crawl_thread.start()
                
            except Exception as e:
                logger.error(f"触发爬取周期失败: {e}")
    
    def _start_crawl_cycle_record(self, start_time: datetime) -> int:
        """
        创建爬取周期记录
        
        参数：
            start_time: 开始时间
        
        返回：
            周期ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO scrapling_crawl_history 
                (start_time, status, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (
                start_time.isoformat(),
                "running"
            ))
            
            cycle_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            return cycle_id
            
        except Exception as e:
            logger.error(f"创建爬取周期记录失败: {e}")
            return -1
    
    def _execute_crawl_cycle(self, cycle_id: int, start_time: datetime) -> None:
        """
        执行爬取周期
        
        参数：
            cycle_id: 周期ID
            start_time: 开始时间
        """
        try:
            # 检查必要组件
            if not self.crawler_engine or not self.config_manager:
                logger.error("必要组件未初始化")
                self._complete_crawl_cycle_record(
                    cycle_id, start_time, datetime.now(),
                    status="failed",
                    errors=["必要组件未初始化"]
                )
                return
            
            # 获取所有启用的品类
            categories = self.config_manager.get_all_categories()
            if not categories:
                logger.warning("没有启用的品类配置")
                self._complete_crawl_cycle_record(
                    cycle_id, start_time, datetime.now(),
                    status="completed",
                    total_categories=0,
                    success_categories=0,
                    failed_categories=0,
                    total_intel_items=0,
                    errors=["没有启用的品类配置"]
                )
                return
            
            logger.info(f"开始爬取{len(categories)}个品类的情报")
            
            total_intel_items = 0
            success_categories = 0
            failed_categories = 0
            all_errors = []
            
            # 遍历所有品类
            for category in categories:
                try:
                    category_id = category["category_id"]
                    category_name = category["category_name"]
                    target_regions = category["target_regions"]
                    
                    logger.info(f"爬取品类: {category_name} ({category_id})")
                    
                    # 获取品类详细配置
                    category_config = self.config_manager.get_category_config(category_id)
                    if not category_config:
                        logger.warning(f"未找到品类配置: {category_id}")
                        failed_categories += 1
                        all_errors.append(f"未找到品类配置: {category_id}")
                        continue
                    
                    # 执行爬取
                    crawl_result = self.crawler_engine.crawl_global_business_intelligence(
                        target_category=category_id,
                        target_regions=target_regions,
                        task_config={
                            "crawl_depth": category_config.get("crawl_depth", 3),
                            "max_pages": category_config.get("max_pages", 100),
                            "priority": category_config.get("priority", 5)
                        }
                    )
                    
                    if crawl_result["success"]:
                        success_categories += 1
                        total_intel_items += crawl_result["total_intel_items"]
                        logger.info(f"品类{category_name}爬取成功，获取{crawl_result['total_intel_items']}条情报")
                    else:
                        failed_categories += 1
                        if "errors" in crawl_result:
                            all_errors.extend(crawl_result["errors"])
                        logger.error(f"品类{category_name}爬取失败")
                    
                    # 随机延迟，避免被屏蔽
                    time.sleep(random.uniform(1.0, 3.0))
                    
                except Exception as e:
                    failed_categories += 1
                    error_msg = f"品类{category.get('category_name', 'unknown')}爬取异常: {str(e)[:100]}"
                    all_errors.append(error_msg)
                    logger.error(error_msg)
            
            # 完成周期记录
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            status = "completed" if success_categories > 0 else "failed"
            
            self._complete_crawl_cycle_record(
                cycle_id, start_time, end_time,
                status=status,
                total_categories=len(categories),
                success_categories=success_categories,
                failed_categories=failed_categories,
                total_intel_items=total_intel_items,
                errors=all_errors
            )
            
            logger.info(f"爬取周期完成，耗时{duration:.2f}秒，成功{success_categories}个品类，获取{total_intel_items}条情报")
            
        except Exception as e:
            logger.error(f"执行爬取周期失败: {e}")
            
            # 更新周期记录为失败
            self._complete_crawl_cycle_record(
                cycle_id, start_time, datetime.now(),
                status="failed",
                errors=[f"执行爬取周期失败: {str(e)[:200]}"]
            )
            
        finally:
            # 减少活动任务计数
            with self.lock:
                if self.status["active_tasks"] > 0:
                    self.status["active_tasks"] -= 1
            
            # 更新最后爬取时间
            self.status["last_crawl_time"] = datetime.now().isoformat()
    
    def _complete_crawl_cycle_record(self, cycle_id: int, start_time: datetime,
                                    end_time: datetime, **kwargs) -> None:
        """
        完成爬取周期记录
        
        参数：
            cycle_id: 周期ID
            start_time: 开始时间
            end_time: 结束时间
            **kwargs: 其他字段
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建更新SQL
            set_clauses = ["end_time = ?"]
            params = [end_time.isoformat()]
            
            for key, value in kwargs.items():
                if key == "errors" and isinstance(value, list):
                    # 错误信息需要序列化为JSON
                    set_clauses.append(f"{key} = ?")
                    params.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            # 添加更新时间
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            sql = f"""
                UPDATE scrapling_crawl_history 
                SET {', '.join(set_clauses)}
                WHERE cycle_id = ?
            """
            
            params.append(cycle_id)
            
            cursor.execute(sql, params)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"完成爬取周期记录失败: {e}")
    
    def _perform_health_check(self) -> None:
        """执行健康检查"""
        try:
            health_checks = []
            
            # 检查数据库连接
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
                health_checks.append(("database_connection", True, ""))
            except Exception as e:
                health_checks.append(("database_connection", False, str(e)))
            
            # 检查必要组件
            if self.crawler_engine:
                health_checks.append(("crawler_engine", True, ""))
            else:
                health_checks.append(("crawler_engine", False, "未初始化"))
            
            if self.config_manager:
                health_checks.append(("config_manager", True, ""))
            else:
                health_checks.append(("config_manager", False, "未初始化"))
            
            # 检查最近爬取状态
            if self.status["last_crawl_time"]:
                last_time = datetime.fromisoformat(self.status["last_crawl_time"])
                now = datetime.now()
                time_diff = (now - last_time).total_seconds()
                
                if time_diff > self.config["crawl_interval_seconds"] * 2:
                    health_checks.append(("crawl_schedule", False, f"最近爬取已过去{time_diff:.0f}秒"))
                else:
                    health_checks.append(("crawl_schedule", True, ""))
            
            # 评估整体健康状态
            failed_checks = [check for check in health_checks if not check[1]]
            
            if not failed_checks:
                self.status["health_status"] = "healthy"
            elif len(failed_checks) <= 2:
                self.status["health_status"] = "degraded"
            else:
                self.status["health_status"] = "unknown"
            
            # 记录健康检查结果
            if failed_checks:
                failed_names = [name for name, _, _ in failed_checks]
                logger.warning(f"健康检查失败: {failed_names}")
            
            # 保存健康状态
            self._save_health_status(health_checks)
            
        except Exception as e:
            logger.error(f"健康检查异常: {e}")
            self.status["health_status"] = "unknown"
    
    def _save_health_status(self, health_checks: List[Tuple[str, bool, str]]) -> None:
        """保存健康状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 保存总体状态
            cursor.execute("""
                INSERT OR REPLACE INTO scrapling_daemon_status 
                (status_key, status_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (
                "health_status",
                json.dumps({
                    "status": self.status["health_status"],
                    "timestamp": datetime.now().isoformat(),
                    "checks": [
                        {"name": name, "healthy": healthy, "message": message}
                        for name, healthy, message in health_checks
                    ]
                })
            ))
            
            # 保存守护进程状态
            cursor.execute("""
                INSERT OR REPLACE INTO scrapling_daemon_status 
                (status_key, status_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (
                "daemon_status",
                json.dumps(self.status)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存健康状态失败: {e}")
    
    def _cleanup_old_logs(self) -> None:
        """清理旧日志"""
        try:
            retention_days = self.config["log_retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 删除旧日志
            cursor.execute("""
                DELETE FROM scrapling_system_logs 
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            
            # 清理旧爬取历史（保留30天）
            cursor.execute("""
                DELETE FROM scrapling_crawl_history 
                WHERE start_time < ?
            """, (cutoff_date.isoformat(),))
            
            deleted_history = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0 or deleted_history > 0:
                logger.info(f"清理日志完成，删除{deleted_count}条日志，{deleted_history}条历史记录")
                
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
    
    def _update_daemon_status(self) -> None:
        """更新守护进程状态"""
        try:
            # 更新最后活动时间
            self.status["last_active"] = datetime.now().isoformat()
            
            # 保存状态
            self._save_health_status([])
            
        except Exception as e:
            logger.error(f"更新守护进程状态失败: {e}")
    
    def _signal_handler(self, signum, frame) -> None:
        """信号处理"""
        logger.info(f"接收到信号 {signum}，准备关闭守护进程")
        self.stop()
        sys.exit(0)
    
    def get_daemon_status(self) -> Dict[str, Any]:
        """
        获取守护进程状态
        
        返回：
            状态字典
        """
        with self.lock:
            return self.status.copy()
    
    def get_crawl_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取爬取历史
        
        参数：
            limit: 返回记录数限制
        
        返回：
            爬取历史列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cycle_id, start_time, end_time, total_categories, 
                       success_categories, failed_categories, total_intel_items,
                       status, errors, created_at
                FROM scrapling_crawl_history 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = []
            for row in rows:
                history.append({
                    "cycle_id": row[0],
                    "start_time": row[1],
                    "end_time": row[2],
                    "total_categories": row[3],
                    "success_categories": row[4],
                    "failed_categories": row[5],
                    "total_intel_items": row[6],
                    "status": row[7],
                    "errors": json.loads(row[8]) if row[8] else [],
                    "created_at": row[9]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取爬取历史失败: {e}")
            return []
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        更新守护进程配置
        
        参数：
            new_config: 新配置字典
        
        返回：
            更新成功返回True，失败返回False
        """
        try:
            # 合并配置
            self.config.update(new_config)
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO scrapling_daemon_status 
                (status_key, status_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (
                "daemon_config",
                json.dumps(self.config)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info("守护进程配置更新成功")
            return True
            
        except Exception as e:
            logger.error(f"更新守护进程配置失败: {e}")
            return False
    
    def run_once(self) -> bool:
        """
        执行单次爬取（不通过调度器）
        
        返回：
            执行成功返回True，失败返回False
        """
        if self.running:
            logger.warning("守护进程在运行中，请使用调度器")
            return False
        
        try:
            # 初始化必要组件
            if not self.crawler_engine or not self.config_manager:
                logger.error("必要组件未初始化")
                return False
            
            # 执行单次爬取
            logger.info("开始单次爬取执行")
            
            categories = self.config_manager.get_all_categories()
            if not categories:
                logger.warning("没有启用的品类配置")
                return False
            
            total_intel_items = 0
            
            for category in categories:
                try:
                    category_id = category["category_id"]
                    target_regions = category["target_regions"]
                    
                    # 执行爬取
                    crawl_result = self.crawler_engine.crawl_global_business_intelligence(
                        target_category=category_id,
                        target_regions=target_regions,
                        task_config={
                            "crawl_depth": 3,
                            "max_pages": 50,
                            "priority": 5
                        }
                    )
                    
                    if crawl_result["success"]:
                        total_intel_items += crawl_result["total_intel_items"]
                        logger.info(f"品类{category_id}爬取成功，获取{crawl_result['total_intel_items']}条情报")
                    
                except Exception as e:
                    logger.error(f"品类{category.get('category_id', 'unknown')}爬取异常: {e}")
            
            logger.info(f"单次爬取完成，共获取{total_intel_items}条情报")
            return total_intel_items > 0
            
        except Exception as e:
            logger.error(f"单次爬取执行失败: {e}")
            return False