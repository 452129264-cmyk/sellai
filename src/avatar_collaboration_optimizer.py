#!/usr/bin/env python3
"""
分身协同优化模块

对齐forked subagent思路，优化多Agent协作逻辑：
1. 分析现有分身协同机制，识别通信开销和任务分配问题
2. 优化任务传递路径，减少通信延迟
3. 实现基于分身能力画像的动态任务匹配
4. 提升无限AI分身的协同效率与任务分配精度

主要优化点：
- 智能任务分配算法（考虑能力、负载、历史表现、地域匹配）
- 任务批处理减少通信开销
- 异步结果处理机制
- 性能监控与自适应调整
"""

import json
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum
import hashlib
from dataclasses import dataclass, asdict
import threading
from queue import Queue
import math

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskType(Enum):
    """任务类型"""
    DATA_CRAWLING = "data_crawling"
    FINANCIAL_ANALYSIS = "financial_analysis"
    CONTENT_CREATION = "content_creation"
    ACCOUNT_OPERATION = "account_operation"
    NEGOTIATION = "negotiation"
    SEO_OPTIMIZATION = "seo_optimization"
    VIDEO_PRODUCTION = "video_production"
    SOCIAL_MEDIA = "social_media"
    CUSTOMER_SERVICE = "customer_service"
    LOGISTICS = "logistics"


@dataclass
class AvatarProfile:
    """分身能力画像"""
    avatar_id: str
    avatar_name: str
    template_id: Optional[str]
    capability_scores: Dict[str, float]  # 能力分数字典
    specialization_tags: List[str]  # 专长标签
    success_rate: float  # 成功率
    total_tasks_completed: int  # 完成任务总数
    avg_completion_time_seconds: float  # 平均完成时间（秒）
    current_load: int  # 当前负载（同时处理的任务数）
    last_active: datetime  # 最后活跃时间
    created_at: datetime  # 创建时间
    region_expertise: List[str]  # 地域专长
    cost_efficiency: float  # 成本效率（0-1，越高越好）
    reliability_score: float  # 可靠性分数（0-1）


@dataclass
class TaskRequirements:
    """任务需求描述"""
    task_type: TaskType
    required_capabilities: List[str]  # 必需能力列表
    priority: TaskPriority
    estimated_complexity: float  # 预估复杂度（1-10）
    target_regions: List[str]  # 目标地域
    deadline: Optional[datetime]  # 截止时间
    batch_size: int = 1  # 批处理大小
    max_cost: Optional[float] = None  # 最大成本限制


@dataclass
class TaskAssignment:
    """任务分配结果"""
    task_id: str
    opportunity_hash: Optional[str]
    assigned_avatar: str
    assignment_time: datetime
    deadline: Optional[datetime]
    priority: int
    completion_status: str = "pending"
    completion_time: Optional[datetime] = None
    result_summary: Optional[str] = None
    estimated_completion_time: Optional[datetime] = None


class AvatarCollaborationOptimizer:
    """分身协同优化器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化协同优化器
        
        Args:
            db_path: 共享状态库路径
        """
        self.db_path = db_path
        self._init_tables()
        self.profile_cache = {}  # 分身画像缓存
        self.cache_expiry = 300  # 缓存过期时间（秒）
        self.last_cache_update = 0
        
        # 任务队列
        self.task_queue = Queue()
        self.result_queue = Queue()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_performance, daemon=True)
        self.monitor_thread.start()
        
        logger.info("分身协同优化器初始化完成")
    
    def _init_tables(self):
        """初始化优化相关表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. 任务分配优化表（扩展原有表）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimized_task_assignments (
                assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                opportunity_hash TEXT,
                assigned_avatar TEXT NOT NULL,
                assignment_time TIMESTAMP NOT NULL,
                deadline TIMESTAMP,
                priority INTEGER DEFAULT 2,
                estimated_completion_time TIMESTAMP,
                actual_completion_time TIMESTAMP,
                completion_status TEXT CHECK(completion_status IN 
                    ('pending', 'in_progress', 'completed', 'failed', 'timeout')),
                result_summary TEXT,
                communication_cost INTEGER DEFAULT 0,
                processing_time_ms INTEGER,
                score_metrics TEXT,  -- JSON格式：{"capability_match": 0.85, "load_factor": 0.9, ...}
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. 性能监控表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collaboration_performance (
                performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active_avatars INTEGER,
                avg_task_completion_time_seconds REAL,
                task_throughput_per_hour REAL,
                communication_overhead_percentage REAL,
                assignment_accuracy REAL,
                load_imbalance_score REAL,  -- 负载不均衡分数（越低越好）
                cache_hit_rate REAL
            )
        """)
        
        # 3. 通信开销记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communication_cost_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_avatar TEXT,
                target_avatar TEXT,
                message_type TEXT,
                message_size_bytes INTEGER,
                transmission_time_ms INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_opt_assignments_avatar ON optimized_task_assignments(assigned_avatar)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_opt_assignments_status ON optimized_task_assignments(completion_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_opt_assignments_task ON optimized_task_assignments(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_time ON collaboration_performance(timestamp)")
        
        conn.commit()
        conn.close()
    
    def _load_avatar_profiles(self, force_refresh: bool = False) -> Dict[str, AvatarProfile]:
        """
        加载分身能力画像，支持缓存
        
        Args:
            force_refresh: 是否强制刷新缓存
        
        Returns:
            分身画像字典
        """
        current_time = time.time()
        
        # 检查缓存是否过期
        if not force_refresh and current_time - self.last_cache_update < self.cache_expiry:
            if self.profile_cache:
                logger.debug("使用缓存的分身画像")
                return self.profile_cache
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT avatar_id, avatar_name, template_id, capability_scores, 
                       specialization_tags, success_rate, total_tasks_completed,
                       avg_completion_time_seconds, current_load, last_active, 
                       created_at
                FROM avatar_capability_profiles
            """)
            
            profiles = {}
            for row in cursor.fetchall():
                avatar_id = row[0]
                
                # 解析JSON字段
                capability_scores = json.loads(row[3]) if row[3] else {}
                specialization_tags = json.loads(row[4]) if row[4] else []
                
                # 转换时间戳
                last_active = datetime.fromisoformat(row[9].replace('Z', '+00:00')) if row[9] else datetime.now()
                created_at = datetime.fromisoformat(row[10].replace('Z', '+00:00')) if row[10] else datetime.now()
                
                # 计算地域专长（根据历史任务记录）
                region_expertise = self._calculate_region_expertise(avatar_id)
                
                # 计算成本效率（根据成本记录）
                cost_efficiency = self._calculate_cost_efficiency(avatar_id)
                
                # 计算可靠性分数
                reliability_score = self._calculate_reliability_score(
                    row[5],  # success_rate
                    row[7],  # avg_completion_time_seconds
                    row[8]   # current_load
                )
                
                profile = AvatarProfile(
                    avatar_id=avatar_id,
                    avatar_name=row[1],
                    template_id=row[2],
                    capability_scores=capability_scores,
                    specialization_tags=specialization_tags,
                    success_rate=row[5] or 0.0,
                    total_tasks_completed=row[6] or 0,
                    avg_completion_time_seconds=row[7] or 0.0,
                    current_load=row[8] or 0,
                    last_active=last_active,
                    created_at=created_at,
                    region_expertise=region_expertise,
                    cost_efficiency=cost_efficiency,
                    reliability_score=reliability_score
                )
                
                profiles[avatar_id] = profile
            
            self.profile_cache = profiles
            self.last_cache_update = current_time
            
            logger.info(f"加载了 {len(profiles)} 个分身画像")
            return profiles
            
        except Exception as e:
            logger.error(f"加载分身画像失败: {e}")
            return {}
        finally:
            conn.close()
    
    def _calculate_region_expertise(self, avatar_id: str) -> List[str]:
        """计算分身的地域专长"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 从任务分配历史中提取地域信息
            cursor.execute("""
                SELECT ta.result_summary 
                FROM task_assignments ta
                WHERE ta.assigned_avatar = ? 
                  AND ta.completion_status = 'completed'
                  AND ta.result_summary IS NOT NULL
                LIMIT 50
            """, (avatar_id,))
            
            regions = set()
            for row in cursor.fetchall():
                try:
                    result = json.loads(row[0])
                    if 'target_regions' in result:
                        for region in result['target_regions']:
                            regions.add(region)
                except:
                    continue
            
            return list(regions)[:5]  # 返回最多5个地域
            
        except Exception as e:
            logger.debug(f"计算地域专长失败: {e}")
            return []
        finally:
            conn.close()
    
    def _calculate_cost_efficiency(self, avatar_id: str) -> float:
        """计算分身的成本效率"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT SUM(total_cost), COUNT(*)
                FROM cost_consumption_logs
                WHERE avatar_id = ?
            """, (avatar_id,))
            
            row = cursor.fetchone()
            if row and row[1] > 0:
                total_cost = row[0] or 0
                task_count = row[1]
                
                # 简单的成本效率计算：完成任务数 / (成本 + 1)
                efficiency = task_count / (total_cost + 1)
                # 归一化到0-1范围
                normalized = min(1.0, efficiency / 10.0)
                return normalized
            
            return 0.5  # 默认值
            
        except Exception as e:
            logger.debug(f"计算成本效率失败: {e}")
            return 0.5
        finally:
            conn.close()
    
    def _calculate_reliability_score(self, success_rate: float, avg_completion_time: float, 
                                   current_load: int) -> float:
        """
        计算分身可靠性分数
        
        考虑因素：
        - 成功率（权重0.4）
        - 平均完成时间（权重0.3）
        - 当前负载（权重0.3）
        """
        if success_rate is None:
            success_rate = 0.5
        
        if avg_completion_time is None or avg_completion_time <= 0:
            time_score = 1.0
        else:
            # 完成时间越短越好，归一化处理（假设合理完成时间在600秒内）
            time_score = max(0, 1.0 - (avg_completion_time / 600))
        
        # 负载越低越好
        load_score = 1.0 / (1.0 + current_load)
        
        # 加权计算
        reliability = (success_rate * 0.4) + (time_score * 0.3) + (load_score * 0.3)
        return reliability
    
    def find_best_avatar_for_task(self, task_req: TaskRequirements) -> Optional[AvatarProfile]:
        """
        智能任务分配：根据任务需求寻找最适合的分身
        
        Args:
            task_req: 任务需求描述
        
        Returns:
            最适合的分身画像，如无合适则返回None
        """
        profiles = self._load_avatar_profiles()
        if not profiles:
            logger.warning("没有可用的分身画像")
            return None
        
        best_avatar = None
        best_score = -1
        score_details = {}
        
        for avatar_id, profile in profiles.items():
            # 计算匹配分数
            scores = self._calculate_avatar_match_score(profile, task_req)
            total_score = scores['total']
            
            if total_score > best_score:
                best_score = total_score
                best_avatar = profile
                score_details = scores
        
        if best_avatar:
            logger.info(f"找到最佳分身: {best_avatar.avatar_name} (分数: {best_score:.3f})")
            logger.debug(f"分数详情: {score_details}")
            return best_avatar
        else:
            logger.warning("未找到合适的分身")
            return None
    
    def _calculate_avatar_match_score(self, profile: AvatarProfile, 
                                    task_req: TaskRequirements) -> Dict[str, float]:
        """
        计算分身与任务的匹配分数
        
        考虑维度：
        1. 能力匹配度（权重0.3）
        2. 专长标签匹配度（权重0.2）
        3. 地域匹配度（权重0.15）
        4. 可靠性分数（权重0.2）
        5. 负载因子（权重0.15）
        
        Returns:
            各维度分数及总分的字典
        """
        scores = {}
        
        # 1. 能力匹配度
        capability_score = 0.0
        if task_req.required_capabilities:
            relevant_scores = []
            for capability in task_req.required_capabilities:
                if capability in profile.capability_scores:
                    score = profile.capability_scores[capability]
                    relevant_scores.append(score)
                else:
                    relevant_scores.append(0.0)
            
            if relevant_scores:
                capability_score = sum(relevant_scores) / len(relevant_scores)
        
        scores['capability_match'] = capability_score
        
        # 2. 专长标签匹配度
        specialization_score = 0.0
        if task_req.task_type and profile.specialization_tags:
            task_type_str = task_req.task_type.value
            # 简单匹配：如果任务类型出现在专长标签中
            if any(task_type_str in tag.lower() for tag in profile.specialization_tags):
                specialization_score = 1.0
            elif profile.specialization_tags:
                specialization_score = 0.3  # 有专长但非完全匹配
        
        scores['specialization_match'] = specialization_score
        
        # 3. 地域匹配度
        region_score = 0.0
        if task_req.target_regions and profile.region_expertise:
            # 计算地域交集比例
            intersection = set(task_req.target_regions) & set(profile.region_expertise)
            if intersection:
                region_score = len(intersection) / len(task_req.target_regions)
        
        scores['region_match'] = region_score
        
        # 4. 可靠性分数（已计算）
        scores['reliability'] = profile.reliability_score
        
        # 5. 负载因子（负载越低越好）
        load_factor = 1.0 / (1.0 + profile.current_load)
        scores['load_factor'] = load_factor
        
        # 6. 成本效率（成本效率越高越好）
        scores['cost_efficiency'] = profile.cost_efficiency
        
        # 计算总分（加权平均）
        weights = {
            'capability_match': 0.25,
            'specialization_match': 0.15,
            'region_match': 0.15,
            'reliability': 0.20,
            'load_factor': 0.15,
            'cost_efficiency': 0.10
        }
        
        total_score = 0.0
        weight_sum = 0.0
        
        for key, weight in weights.items():
            if key in scores:
                total_score += scores[key] * weight
                weight_sum += weight
        
        if weight_sum > 0:
            total_score /= weight_sum
        
        scores['total'] = total_score
        
        return scores
    
    def assign_task_batch(self, task_batch: List[Tuple[TaskRequirements, Dict[str, Any]]]) -> List[TaskAssignment]:
        """
        批量分配任务，优化通信开销
        
        Args:
            task_batch: 任务批次，每个元素为(任务需求, 商机数据)
        
        Returns:
            任务分配结果列表
        """
        assignments = []
        
        # 按任务类型分组
        task_groups = {}
        for task_req, opportunity_data in task_batch:
            task_type = task_req.task_type.value
            if task_type not in task_groups:
                task_groups[task_type] = []
            task_groups[task_type].append((task_req, opportunity_data))
        
        # 为每组任务寻找最佳分身
        for task_type, group_tasks in task_groups.items():
            if len(group_tasks) == 0:
                continue
            
            # 取第一个任务的需求作为代表（假设同组任务需求相似）
            sample_req, _ = group_tasks[0]
            
            # 寻找最佳分身
            best_avatar = self.find_best_avatar_for_task(sample_req)
            if not best_avatar:
                logger.warning(f"未找到适合{task_type}任务的分身")
                continue
            
            # 为每个任务创建分配
            for task_req, opportunity_data in group_tasks:
                assignment = self._create_task_assignment(
                    task_req=task_req,
                    opportunity_data=opportunity_data,
                    assigned_avatar=best_avatar.avatar_id
                )
                
                if assignment:
                    assignments.append(assignment)
                    # 更新分身负载
                    self._update_avatar_load(best_avatar.avatar_id, increment=1)
        
        logger.info(f"批量分配了 {len(assignments)} 个任务给 {len(set(a.assigned_avatar for a in assignments))} 个分身")
        return assignments
    
    def _create_task_assignment(self, task_req: TaskRequirements, 
                              opportunity_data: Dict[str, Any], 
                              assigned_avatar: str) -> Optional[TaskAssignment]:
        """
        创建任务分配记录
        
        Returns:
            任务分配对象
        """
        try:
            # 生成唯一任务ID
            task_id = f"task_{int(time.time())}_{hashlib.md5(json.dumps(opportunity_data).encode()).hexdigest()[:8]}"
            
            # 提取商机哈希（如果存在）
            opportunity_hash = opportunity_data.get('_metadata', {}).get('opportunity_hash')
            
            # 计算预估完成时间（基于历史数据）
            estimated_completion = None
            if task_req.deadline:
                estimated_completion = task_req.deadline
            else:
                # 基于平均完成时间预估
                profiles = self._load_avatar_profiles()
                if assigned_avatar in profiles:
                    avg_time = profiles[assigned_avatar].avg_completion_time_seconds
                    if avg_time > 0:
                        estimated_completion = datetime.now() + timedelta(seconds=avg_time * task_req.estimated_complexity)
            
            assignment = TaskAssignment(
                task_id=task_id,
                opportunity_hash=opportunity_hash,
                assigned_avatar=assigned_avatar,
                assignment_time=datetime.now(),
                deadline=task_req.deadline,
                priority=task_req.priority.value,
                estimated_completion_time=estimated_completion
            )
            
            # 保存到数据库
            self._save_assignment_to_db(assignment)
            
            return assignment
            
        except Exception as e:
            logger.error(f"创建任务分配失败: {e}")
            return None
    
    def _save_assignment_to_db(self, assignment: TaskAssignment):
        """保存任务分配到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO optimized_task_assignments 
                (task_id, opportunity_hash, assigned_avatar, assignment_time, 
                 deadline, priority, estimated_completion_time, completion_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment.task_id,
                assignment.opportunity_hash,
                assignment.assigned_avatar,
                assignment.assignment_time.isoformat(),
                assignment.deadline.isoformat() if assignment.deadline else None,
                assignment.priority,
                assignment.estimated_completion_time.isoformat() if assignment.estimated_completion_time else None,
                assignment.completion_status
            ))
            
            conn.commit()
            logger.debug(f"任务分配已保存: {assignment.task_id}")
            
        except Exception as e:
            logger.error(f"保存任务分配失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _update_avatar_load(self, avatar_id: str, increment: int = 1):
        """更新分身负载"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE avatar_capability_profiles 
                SET current_load = current_load + ?
                WHERE avatar_id = ?
            """, (increment, avatar_id))
            
            conn.commit()
            
            # 刷新缓存
            if avatar_id in self.profile_cache:
                self.profile_cache[avatar_id].current_load += increment
            
        except Exception as e:
            logger.error(f"更新分身负载失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _monitor_performance(self):
        """监控协同性能"""
        while True:
            try:
                self._record_performance_metrics()
                time.sleep(60)  # 每分钟记录一次
            except Exception as e:
                logger.error(f"性能监控失败: {e}")
                time.sleep(60)
    
    def _record_performance_metrics(self):
        """记录性能指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取活跃分身数量
            cursor.execute("SELECT COUNT(*) FROM avatar_capability_profiles WHERE current_load > 0")
            active_avatars = cursor.fetchone()[0] or 0
            
            # 获取平均任务完成时间
            cursor.execute("""
                SELECT AVG(avg_completion_time_seconds) 
                FROM avatar_capability_profiles 
                WHERE total_tasks_completed > 0
            """)
            avg_completion_time = cursor.fetchone()[0] or 0
            
            # 计算任务吞吐量（每小时）
            cursor.execute("""
                SELECT COUNT(*) 
                FROM optimized_task_assignments 
                WHERE assignment_time >= datetime('now', '-1 hour')
            """)
            tasks_last_hour = cursor.fetchone()[0] or 0
            
            # 计算分配准确率（基于任务完成状态）
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN completion_status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
                FROM optimized_task_assignments 
                WHERE completion_status IN ('completed', 'failed', 'timeout')
            """)
            row = cursor.fetchone()
            total_tasks = row[0] or 0
            completed_tasks = row[1] or 0
            
            assignment_accuracy = (completed_tasks / total_tasks) if total_tasks > 0 else 1.0
            
            # 计算负载不均衡分数
            cursor.execute("""
                SELECT STDDEV(current_load) / (AVG(current_load) + 0.001) as load_imbalance
                FROM avatar_capability_profiles
            """)
            load_imbalance = cursor.fetchone()[0] or 0
            
            # 记录性能数据
            cursor.execute("""
                INSERT INTO collaboration_performance 
                (active_avatars, avg_task_completion_time_seconds, task_throughput_per_hour,
                 assignment_accuracy, load_imbalance_score, cache_hit_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                active_avatars,
                avg_completion_time,
                tasks_last_hour,
                assignment_accuracy,
                load_imbalance,
                0.8  # 默认缓存命中率，实际应动态计算
            ))
            
            conn.commit()
            logger.debug(f"性能指标已记录: 活跃分身={active_avatars}, 准确率={assignment_accuracy:.2f}")
            
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取协同性能报告
        
        Args:
            hours: 统计小时数
        
        Returns:
            性能报告字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    AVG(active_avatars) as avg_active_avatars,
                    AVG(avg_task_completion_time_seconds) as avg_completion_time,
                    AVG(task_throughput_per_hour) as avg_throughput,
                    AVG(assignment_accuracy) as avg_accuracy,
                    AVG(load_imbalance_score) as avg_load_imbalance
                FROM collaboration_performance 
                WHERE timestamp >= datetime('now', ?)
            """, (f'-{hours} hours',))
            
            row = cursor.fetchone()
            
            report = {
                'period_hours': hours,
                'avg_active_avatars': row[0] or 0,
                'avg_completion_time_seconds': row[1] or 0,
                'avg_throughput_per_hour': row[2] or 0,
                'avg_assignment_accuracy': row[3] or 1.0,
                'avg_load_imbalance': row[4] or 0,
                'timestamp': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"获取性能报告失败: {e}")
            return {}
        finally:
            conn.close()


def create_sample_task_requirements() -> TaskRequirements:
    """创建示例任务需求"""
    return TaskRequirements(
        task_type=TaskType.FINANCIAL_ANALYSIS,
        required_capabilities=['data_crawling', 'financial_analysis'],
        priority=TaskPriority.NORMAL,
        estimated_complexity=5.0,
        target_regions=['US', 'CA'],
        deadline=datetime.now() + timedelta(hours=24),
        batch_size=1
    )


def main():
    """测试协同优化器"""
    optimizer = AvatarCollaborationOptimizer()
    
    # 测试单任务分配
    task_req = create_sample_task_requirements()
    best_avatar = optimizer.find_best_avatar_for_task(task_req)
    
    if best_avatar:
        print(f"最佳分身: {best_avatar.avatar_name} (ID: {best_avatar.avatar_id})")
        print(f"能力分数: {best_avatar.capability_scores}")
        print(f"可靠性分数: {best_avatar.reliability_score:.3f}")
    else:
        print("未找到合适分身")
    
    # 获取性能报告
    report = optimizer.get_performance_report(hours=1)
    print(f"性能报告: {json.dumps(report, indent=2, default=str)}")


if __name__ == "__main__":
    main()