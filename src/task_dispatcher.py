#!/usr/bin/env python3
"""
智能任务分发器模块

优化多Agent协作逻辑，减少通信开销，提升任务分配精度。
对齐forked subagent思路，实现基于能力画像的动态任务匹配。

主要功能：
1. 智能任务分配算法（多维度评分）
2. 任务批处理与负载均衡
3. 性能监控与自适应调整
4. 与现有共享状态库兼容
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
    GENERAL = "general"


@dataclass
class TaskRequirements:
    """任务需求描述"""
    task_type: TaskType = TaskType.GENERAL
    required_capabilities: List[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_complexity: float = 1.0
    target_regions: List[str] = None
    deadline: Optional[datetime] = None
    batch_size: int = 1
    max_cost: Optional[float] = None
    min_success_rate: float = 0.0
    
    def __post_init__(self):
        if self.required_capabilities is None:
            self.required_capabilities = []
        if self.target_regions is None:
            self.target_regions = []


@dataclass
class AvatarCapabilityProfile:
    """分身能力画像（简化版，与数据库结构兼容）"""
    avatar_id: str
    avatar_name: str
    template_id: Optional[str] = None
    capability_scores: Dict[str, float] = None
    specialization_tags: List[str] = None
    success_rate: float = 0.0
    total_tasks_completed: int = 0
    avg_completion_time_seconds: float = 0.0
    current_load: int = 0
    last_active: datetime = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.capability_scores is None:
            self.capability_scores = {}
        if self.specialization_tags is None:
            self.specialization_tags = []
        if self.last_active is None:
            self.last_active = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()


class TaskDispatcher:
    """智能任务分发器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化任务分发器
        
        Args:
            db_path: 共享状态库路径
        """
        self.db_path = db_path
        self.profile_cache = {}
        self.cache_expiry = 60  # 缓存过期时间（秒）
        self.last_cache_update = 0
        
        logger.info("智能任务分发器初始化完成")
    
    def _load_avatar_profiles(self, force_refresh: bool = False) -> Dict[str, AvatarCapabilityProfile]:
        """
        加载分身能力画像，支持缓存
        
        Returns:
            分身画像字典
        """
        current_time = time.time()
        
        if not force_refresh and current_time - self.last_cache_update < self.cache_expiry:
            if self.profile_cache:
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
                capability_scores = {}
                if row[3]:
                    try:
                        capability_scores = json.loads(row[3])
                    except:
                        capability_scores = {}
                
                specialization_tags = []
                if row[4]:
                    try:
                        specialization_tags = json.loads(row[4])
                    except:
                        specialization_tags = []
                
                # 转换时间戳
                last_active = datetime.now()
                if row[9]:
                    try:
                        last_active = datetime.fromisoformat(row[9].replace('Z', '+00:00'))
                    except:
                        pass
                
                created_at = datetime.now()
                if row[10]:
                    try:
                        created_at = datetime.fromisoformat(row[10].replace('Z', '+00:00'))
                    except:
                        pass
                
                profile = AvatarCapabilityProfile(
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
                    created_at=created_at
                )
                
                profiles[avatar_id] = profile
            
            self.profile_cache = profiles
            self.last_cache_update = current_time
            
            logger.debug(f"加载了 {len(profiles)} 个分身画像")
            return profiles
            
        except Exception as e:
            logger.error(f"加载分身画像失败: {e}")
            return {}
        finally:
            conn.close()
    
    def find_best_avatar_for_task(self, task_req: TaskRequirements) -> Optional[str]:
        """
        智能任务分配：根据任务需求寻找最适合的分身
        
        这是现有系统接口的增强版本，保持向后兼容
        
        Args:
            task_req: 任务需求描述
        
        Returns:
            最适合的分身ID，如无合适则返回None
        """
        profiles = self._load_avatar_profiles()
        if not profiles:
            logger.warning("没有可用的分身画像")
            return None
        
        # 默认值（兼容旧版）
        if not task_req.required_capabilities:
            task_req.required_capabilities = ['data_crawling', 'financial_analysis']
        
        best_avatar_id = None
        best_score = -1
        score_details = {}
        
        for avatar_id, profile in profiles.items():
            # 检查最低要求
            if task_req.min_success_rate > 0 and profile.success_rate < task_req.min_success_rate:
                continue
            
            # 计算匹配分数
            scores = self._calculate_match_score(profile, task_req)
            total_score = scores['total']
            
            if total_score > best_score:
                best_score = total_score
                best_avatar_id = avatar_id
                score_details = scores
        
        if best_avatar_id:
            logger.info(f"任务分配: {best_avatar_id} (分数: {best_score:.3f})")
            logger.debug(f"分数详情: {score_details}")
            
            # 记录分配决策
            self._record_assignment_decision(
                avatar_id=best_avatar_id,
                task_req=task_req,
                score_details=score_details
            )
            
            return best_avatar_id
        else:
            logger.warning("未找到合适的分身")
            return None
    
    def _calculate_match_score(self, profile: AvatarCapabilityProfile, 
                             task_req: TaskRequirements) -> Dict[str, float]:
        """
        计算分身与任务的匹配分数
        
        考虑维度：
        1. 能力匹配度（权重0.3）
        2. 专长标签匹配度（权重0.2）
        3. 地域匹配度（权重0.15）
        4. 成功率（权重0.15）
        5. 负载因子（权重0.1）
        6. 响应速度（权重0.1）
        
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
        if task_req.task_type != TaskType.GENERAL and profile.specialization_tags:
            task_type_str = task_req.task_type.value.lower()
            tag_match = False
            
            for tag in profile.specialization_tags:
                tag_lower = tag.lower()
                if task_type_str in tag_lower or tag_lower in task_type_str:
                    tag_match = True
                    break
            
            if tag_match:
                specialization_score = 1.0
            elif profile.specialization_tags:
                specialization_score = 0.3
        
        scores['specialization_match'] = specialization_score
        
        # 3. 地域匹配度
        region_score = 0.0
        if task_req.target_regions and profile.specialization_tags:
            # 检查地域标签匹配
            region_tags = [tag.lower() for tag in profile.specialization_tags 
                          if any(region.lower() in tag for region in task_req.target_regions)]
            
            if region_tags:
                region_score = len(region_tags) / len(task_req.target_regions)
        
        scores['region_match'] = region_score
        
        # 4. 成功率（归一化到0-1）
        success_score = profile.success_rate or 0.0
        scores['success_rate'] = success_score
        
        # 5. 负载因子（负载越低越好）
        load_factor = 1.0 / (1.0 + profile.current_load)
        scores['load_factor'] = load_factor
        
        # 6. 响应速度（完成时间越短越好）
        response_score = 1.0
        if profile.avg_completion_time_seconds and profile.avg_completion_time_seconds > 0:
            # 假设合理完成时间在300秒内
            response_score = max(0, 1.0 - (profile.avg_completion_time_seconds / 300))
        
        scores['response_speed'] = response_score
        
        # 计算总分（加权平均）
        weights = {
            'capability_match': 0.30,
            'specialization_match': 0.20,
            'region_match': 0.15,
            'success_rate': 0.15,
            'load_factor': 0.10,
            'response_speed': 0.10
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
    
    def _record_assignment_decision(self, avatar_id: str, task_req: TaskRequirements, 
                                  score_details: Dict[str, float]):
        """
        记录任务分配决策，用于后续分析和优化
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建分配决策表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignment_decisions (
                    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    avatar_id TEXT NOT NULL,
                    task_type TEXT,
                    priority INTEGER,
                    complexity REAL,
                    region_match REAL,
                    capability_match REAL,
                    specialization_match REAL,
                    success_rate REAL,
                    load_factor REAL,
                    response_speed REAL,
                    total_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (avatar_id) REFERENCES avatar_capability_profiles(avatar_id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO assignment_decisions 
                (avatar_id, task_type, priority, complexity, region_match, 
                 capability_match, specialization_match, success_rate, 
                 load_factor, response_speed, total_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                avatar_id,
                task_req.task_type.value,
                task_req.priority.value,
                task_req.estimated_complexity,
                score_details.get('region_match', 0),
                score_details.get('capability_match', 0),
                score_details.get('specialization_match', 0),
                score_details.get('success_rate', 0),
                score_details.get('load_factor', 0),
                score_details.get('response_speed', 0),
                score_details.get('total', 0)
            ))
            
            conn.commit()
            logger.debug(f"分配决策已记录: {avatar_id}")
            
        except Exception as e:
            logger.error(f"记录分配决策失败: {e}")
        finally:
            conn.close()
    
    def assign_tasks_in_batch(self, tasks: List[Tuple[TaskRequirements, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        批量分配任务，优化通信开销
        
        Args:
            tasks: 任务列表，每个元素为(任务需求, 商机数据)
        
        Returns:
            分配结果列表
        """
        if not tasks:
            return []
        
        logger.info(f"开始批量分配 {len(tasks)} 个任务")
        
        # 按任务类型分组
        task_groups = {}
        for task_req, opportunity_data in tasks:
            task_type = task_req.task_type.value
            if task_type not in task_groups:
                task_groups[task_type] = []
            task_groups[task_type].append((task_req, opportunity_data))
        
        assignments = []
        
        for task_type, group_tasks in task_groups.items():
            logger.info(f"处理任务类型: {task_type} ({len(group_tasks)} 个任务)")
            
            # 寻找适合处理此类任务的分身
            sample_req = group_tasks[0][0]
            best_avatar_id = self.find_best_avatar_for_task(sample_req)
            
            if not best_avatar_id:
                logger.warning(f"未找到适合{task_type}任务的分身")
                continue
            
            # 为每个任务创建分配
            for task_req, opportunity_data in group_tasks:
                assignment = self._create_assignment_record(
                    task_req=task_req,
                    opportunity_data=opportunity_data,
                    assigned_avatar=best_avatar_id
                )
                
                if assignment:
                    assignments.append(assignment)
                    # 更新负载
                    self._increment_avatar_load(best_avatar_id)
        
        logger.info(f"批量分配完成: {len(assignments)} 个任务已分配")
        return assignments
    
    def _create_assignment_record(self, task_req: TaskRequirements, 
                                opportunity_data: Dict[str, Any], 
                                assigned_avatar: str) -> Optional[Dict[str, Any]]:
        """
        创建分配记录
        """
        try:
            # 生成唯一ID
            task_id = f"batch_{int(time.time())}_{hashlib.md5(json.dumps(opportunity_data).encode()).hexdigest()[:6]}"
            
            assignment = {
                'task_id': task_id,
                'assigned_avatar': assigned_avatar,
                'task_type': task_req.task_type.value,
                'priority': task_req.priority.value,
                'complexity': task_req.estimated_complexity,
                'target_regions': task_req.target_regions,
                'deadline': task_req.deadline.isoformat() if task_req.deadline else None,
                'opportunity_data': opportunity_data,
                'assigned_at': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            # 保存到数据库
            self._save_assignment(assignment)
            
            return assignment
            
        except Exception as e:
            logger.error(f"创建分配记录失败: {e}")
            return None
    
    def _save_assignment(self, assignment: Dict[str, Any]):
        """保存分配到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 使用现有的task_assignments表
            cursor.execute("""
                INSERT INTO task_assignments 
                (opportunity_hash, assigned_avatar, assignment_time, deadline, 
                 priority, completion_status, result_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment.get('opportunity_data', {}).get('_metadata', {}).get('opportunity_hash'),
                assignment['assigned_avatar'],
                assignment['assigned_at'],
                assignment['deadline'],
                assignment['priority'],
                assignment['status'],
                json.dumps({
                    'task_id': assignment['task_id'],
                    'task_type': assignment['task_type'],
                    'complexity': assignment['complexity'],
                    'target_regions': assignment['target_regions']
                })
            ))
            
            conn.commit()
            logger.debug(f"分配记录已保存: {assignment['task_id']}")
            
        except Exception as e:
            logger.error(f"保存分配记录失败: {e}")
        finally:
            conn.close()
    
    def _increment_avatar_load(self, avatar_id: str):
        """增加分身负载"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE avatar_capability_profiles 
                SET current_load = current_load + 1,
                    last_active = ?
                WHERE avatar_id = ?
            """, (datetime.now().isoformat(), avatar_id))
            
            conn.commit()
            
            # 更新缓存
            if avatar_id in self.profile_cache:
                self.profile_cache[avatar_id].current_load += 1
                self.profile_cache[avatar_id].last_active = datetime.now()
            
        except Exception as e:
            logger.error(f"更新分身负载失败: {e}")
        finally:
            conn.close()
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取分配性能指标
        
        Args:
            hours: 统计小时数
        
        Returns:
            性能指标字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查分配决策表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='assignment_decisions'
            """)
            
            if not cursor.fetchone():
                return {'status': 'no_data', 'message': '分配决策表未创建'}
            
            # 获取统计信息
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_decisions,
                    AVG(total_score) as avg_score,
                    AVG(capability_match) as avg_capability_match,
                    AVG(specialization_match) as avg_specialization_match,
                    AVG(region_match) as avg_region_match,
                    AVG(success_rate) as avg_success_rate,
                    AVG(load_factor) as avg_load_factor,
                    AVG(response_speed) as avg_response_speed
                FROM assignment_decisions 
                WHERE timestamp >= datetime('now', ?)
            """, (f'-{hours} hours',))
            
            row = cursor.fetchone()
            
            metrics = {
                'period_hours': hours,
                'total_decisions': row[0] or 0,
                'avg_total_score': round(row[1] or 0, 3),
                'avg_capability_match': round(row[2] or 0, 3),
                'avg_specialization_match': round(row[3] or 0, 3),
                'avg_region_match': round(row[4] or 0, 3),
                'avg_success_rate': round(row[5] or 0, 3),
                'avg_load_factor': round(row[6] or 0, 3),
                'avg_response_speed': round(row[7] or 0, 3),
                'timestamp': datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"获取性能指标失败: {e}")
            return {}
        finally:
            conn.close()
    
    def optimize_assignment_strategy(self):
        """
        基于历史数据优化分配策略
        可以定期调用此方法来调整权重参数
        """
        metrics = self.get_performance_metrics(hours=48)
        
        if not metrics or metrics.get('total_decisions', 0) < 50:
            logger.info("数据不足，无法进行策略优化")
            return
        
        logger.info("开始优化分配策略...")
        
        # 这里可以添加更复杂的优化逻辑
        # 例如：基于历史成功率调整权重，或者使用机器学习模型
        
        logger.info(f"当前性能指标: 平均分数={metrics['avg_total_score']:.3f}, "
                   f"能力匹配={metrics['avg_capability_match']:.3f}")
        
        # 简单示例：如果能力匹配度低，可能需要调整能力评分权重
        if metrics['avg_capability_match'] < 0.7:
            logger.info("建议：提高能力匹配度的权重系数")
        
        if metrics['avg_success_rate'] < 0.8:
            logger.info("建议：提高成功率的权重系数，或调整最低成功率阈值")
        
        logger.info("分配策略优化完成")


# 兼容旧版接口的包装函数
def find_best_avatar_for_task(required_capabilities: List[str] = None, 
                            min_score_threshold: float = 0.6) -> Optional[str]:
    """
    兼容旧版接口：根据能力要求寻找最适合的分身
    
    Args:
        required_capabilities: 所需能力列表
        min_score_threshold: 最低能力分数阈值
    
    Returns:
        最适合的分身ID，如无合适则返回None
    """
    if required_capabilities is None:
        required_capabilities = ['data_crawling', 'financial_analysis']
    
    dispatcher = TaskDispatcher()
    
    # 创建任务需求
    task_req = TaskRequirements(
        required_capabilities=required_capabilities,
        min_success_rate=min_score_threshold
    )
    
    return dispatcher.find_best_avatar_for_task(task_req)


def main():
    """测试任务分发器"""
    dispatcher = TaskDispatcher()
    
    # 测试单任务分配
    task_req = TaskRequirements(
        task_type=TaskType.FINANCIAL_ANALYSIS,
        required_capabilities=['data_crawling', 'financial_analysis'],
        priority=TaskPriority.NORMAL,
        estimated_complexity=5.0,
        target_regions=['US', 'CA']
    )
    
    best_avatar = dispatcher.find_best_avatar_for_task(task_req)
    
    if best_avatar:
        print(f"最佳分身ID: {best_avatar}")
    else:
        print("未找到合适分身")
    
    # 测试批量分配
    tasks = []
    for i in range(5):
        task_req = TaskRequirements(
            task_type=TaskType.FINANCIAL_ANALYSIS,
            required_capabilities=['data_crawling', 'financial_analysis'],
            priority=TaskPriority.NORMAL,
            estimated_complexity=3.0 + i,
            target_regions=['US', 'CA']
        )
        
        opportunity_data = {
            'id': f'test_opp_{i}',
            'title': f'测试商机 {i}',
            'estimated_margin': 35 + i,
            '_metadata': {
                'opportunity_hash': f'hash_{i}'
            }
        }
        
        tasks.append((task_req, opportunity_data))
    
    assignments = dispatcher.assign_tasks_in_batch(tasks)
    print(f"批量分配结果: {len(assignments)} 个任务")
    
    # 获取性能指标
    metrics = dispatcher.get_performance_metrics(hours=1)
    print(f"性能指标: {json.dumps(metrics, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()