#!/usr/bin/env python3
"""
优化任务分配器模块

提供与现有系统兼容但功能增强的任务分配接口。
集成智能分配算法、批处理优化和性能监控。

主要功能：
1. 兼容现有find_best_avatar_for_task接口
2. 增强的多维度评分算法
3. 任务批处理支持
4. 性能数据记录
5. 自适应策略调整
"""

import json
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import hashlib
from enum import Enum

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class OptimizedTaskAllocator:
    """优化任务分配器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self.profile_cache = {}
        self.cache_expiry = 60
        self.last_cache_update = 0
        
        # 初始化性能监控表
        self._init_performance_tables()
        
        logger.info("优化任务分配器初始化完成")
    
    def _init_performance_tables(self):
        """初始化性能监控表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 分配决策表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignment_decisions (
                    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    avatar_id TEXT NOT NULL,
                    task_type TEXT,
                    required_capabilities TEXT,  -- JSON数组
                    priority INTEGER,
                    complexity REAL,
                    target_regions TEXT,  -- JSON数组
                    capability_match REAL,
                    specialization_match REAL,
                    region_match REAL,
                    success_rate REAL,
                    load_factor REAL,
                    response_speed REAL,
                    total_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 通信开销表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS communication_metrics (
                    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT,
                    source_node TEXT,
                    target_node TEXT,
                    message_size_bytes INTEGER,
                    processing_time_ms INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"初始化性能表失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def find_best_avatar_for_task(self, required_capabilities: List[str] = None,
                                min_score_threshold: float = 0.6,
                                task_type: str = None,
                                priority: int = 2,
                                complexity: float = 1.0,
                                target_regions: List[str] = None) -> Optional[str]:
        """
        增强版任务分配接口
        
        Args:
            required_capabilities: 所需能力列表
            min_score_threshold: 最低能力分数阈值
            task_type: 任务类型标识
            priority: 任务优先级
            complexity: 任务复杂度
            target_regions: 目标地域列表
        
        Returns:
            最适合的分身ID，如无合适则返回None
        """
        start_time = time.time()
        
        # 默认值处理
        if required_capabilities is None:
            required_capabilities = ['data_crawling', 'financial_analysis']
        
        if target_regions is None:
            target_regions = []
        
        # 加载分身画像
        profiles = self._load_avatar_profiles()
        if not profiles:
            logger.warning("没有可用的分身画像")
            return None
        
        best_avatar_id = None
        best_score = -1
        score_details = {}
        
        for profile in profiles:
            avatar_id = profile['avatar_id']
            # 检查成功率阈值
            if profile['success_rate'] < min_score_threshold:
                continue
            
            # 计算匹配分数
            scores = self._calculate_enhanced_match_score(
                profile, required_capabilities, task_type, priority, 
                complexity, target_regions
            )
            
            total_score = scores['total']
            
            if total_score > best_score:
                best_score = total_score
                best_avatar_id = avatar_id
                score_details = scores
        
        # 记录分配决策
        if best_avatar_id:
            self._record_decision(
                avatar_id=best_avatar_id,
                required_capabilities=required_capabilities,
                task_type=task_type,
                priority=priority,
                complexity=complexity,
                target_regions=target_regions,
                score_details=score_details
            )
            
            logger.info(f"分配结果: {best_avatar_id} (分数: {best_score:.3f})")
        
        # 记录通信开销
        processing_time = int((time.time() - start_time) * 1000)
        self._record_communication_metric(
            operation_type='task_allocation',
            source_node='opportunity_deduplicator',
            target_node='intelligence_officer',
            processing_time_ms=processing_time,
            message_size_bytes=len(json.dumps(required_capabilities))
        )
        
        return best_avatar_id
    
    def _load_avatar_profiles(self) -> List[Dict[str, Any]]:
        """加载分身画像"""
        current_time = time.time()
        
        if current_time - self.last_cache_update < self.cache_expiry and self.profile_cache:
            return self.profile_cache
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        profiles = []
        try:
            cursor.execute("""
                SELECT avatar_id, avatar_name, template_id, capability_scores, 
                       specialization_tags, success_rate, total_tasks_completed,
                       avg_completion_time_seconds, current_load, last_active
                FROM avatar_capability_profiles
            """)
            
            for row in cursor.fetchall():
                profile = {
                    'avatar_id': row[0],
                    'avatar_name': row[1],
                    'template_id': row[2],
                    'capability_scores': json.loads(row[3]) if row[3] else {},
                    'specialization_tags': json.loads(row[4]) if row[4] else [],
                    'success_rate': row[5] or 0.0,
                    'total_tasks_completed': row[6] or 0,
                    'avg_completion_time_seconds': row[7] or 0.0,
                    'current_load': row[8] or 0,
                    'last_active': row[9]
                }
                profiles.append(profile)
            
            self.profile_cache = profiles
            self.last_cache_update = current_time
            
            logger.debug(f"加载了 {len(profiles)} 个分身画像")
            
        except Exception as e:
            logger.error(f"加载分身画像失败: {e}")
        finally:
            conn.close()
        
        return profiles
    
    def _calculate_enhanced_match_score(self, profile: Dict[str, Any],
                                      required_capabilities: List[str],
                                      task_type: Optional[str],
                                      priority: int,
                                      complexity: float,
                                      target_regions: List[str]) -> Dict[str, float]:
        """
        计算增强的匹配分数
        
        考虑因素：
        1. 能力匹配度（权重0.25）
        2. 专长标签匹配度（权重0.20）
        3. 地域匹配度（权重0.15）
        4. 成功率（权重0.15）
        5. 负载因子（权重0.10）
        6. 响应速度（权重0.10）
        7. 任务复杂度匹配（权重0.05）
        """
        scores = {}
        
        # 1. 能力匹配度
        capability_score = 0.0
        if required_capabilities:
            relevant_scores = []
            for capability in required_capabilities:
                if capability in profile['capability_scores']:
                    score = profile['capability_scores'][capability]
                    relevant_scores.append(score)
                else:
                    relevant_scores.append(0.0)
            
            if relevant_scores:
                capability_score = sum(relevant_scores) / len(relevant_scores)
        
        scores['capability_match'] = capability_score
        
        # 2. 专长标签匹配度
        specialization_score = 0.0
        if task_type and profile['specialization_tags']:
            task_lower = task_type.lower()
            tag_match = False
            
            for tag in profile['specialization_tags']:
                tag_lower = tag.lower()
                if task_lower in tag_lower or tag_lower in task_lower:
                    tag_match = True
                    break
            
            if tag_match:
                specialization_score = 1.0
            elif profile['specialization_tags']:
                specialization_score = 0.3
        
        scores['specialization_match'] = specialization_score
        
        # 3. 地域匹配度
        region_score = 0.0
        if target_regions and profile['specialization_tags']:
            matched_regions = 0
            for region in target_regions:
                region_lower = region.lower()
                for tag in profile['specialization_tags']:
                    if region_lower in tag.lower():
                        matched_regions += 1
                        break
            
            if matched_regions > 0:
                region_score = matched_regions / len(target_regions)
        
        scores['region_match'] = region_score
        
        # 4. 成功率
        success_score = profile['success_rate']
        scores['success_rate'] = success_score
        
        # 5. 负载因子（负载越低越好）
        load_factor = 1.0 / (1.0 + profile['current_load'])
        scores['load_factor'] = load_factor
        
        # 6. 响应速度（完成时间越短越好）
        response_score = 1.0
        if profile['avg_completion_time_seconds'] and profile['avg_completion_time_seconds'] > 0:
            # 归一化：假设合理完成时间在300秒内
            normalized_time = min(1.0, profile['avg_completion_time_seconds'] / 300)
            response_score = 1.0 - normalized_time
        
        scores['response_speed'] = response_score
        
        # 7. 任务复杂度匹配（复杂任务分配给经验丰富的分身）
        complexity_score = 1.0
        if complexity > 5.0 and profile['total_tasks_completed'] < 10:
            # 复杂任务但分身经验不足，适当扣分
            complexity_score = 0.7
        elif complexity <= 3.0 and profile['total_tasks_completed'] > 50:
            # 简单任务分配给经验丰富的分身，适当加分
            complexity_score = 1.1
        
        scores['complexity_match'] = min(complexity_score, 1.0)
        
        # 计算总分（加权平均）
        weights = {
            'capability_match': 0.25,
            'specialization_match': 0.20,
            'region_match': 0.15,
            'success_rate': 0.15,
            'load_factor': 0.10,
            'response_speed': 0.10,
            'complexity_match': 0.05
        }
        
        total_score = 0.0
        for key, weight in weights.items():
            if key in scores:
                total_score += scores[key] * weight
        
        scores['total'] = total_score
        
        return scores
    
    def _record_decision(self, avatar_id: str, required_capabilities: List[str],
                       task_type: Optional[str], priority: int, complexity: float,
                       target_regions: List[str], score_details: Dict[str, float]):
        """记录分配决策"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO assignment_decisions 
                (avatar_id, task_type, required_capabilities, priority, complexity,
                 target_regions, capability_match, specialization_match, region_match,
                 success_rate, load_factor, response_speed, total_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                avatar_id,
                task_type,
                json.dumps(required_capabilities),
                priority,
                complexity,
                json.dumps(target_regions),
                score_details.get('capability_match', 0),
                score_details.get('specialization_match', 0),
                score_details.get('region_match', 0),
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
    
    def _record_communication_metric(self, operation_type: str, source_node: str,
                                   target_node: str, processing_time_ms: int,
                                   message_size_bytes: int = 0):
        """记录通信开销指标"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO communication_metrics 
                (operation_type, source_node, target_node, message_size_bytes,
                 processing_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (
                operation_type,
                source_node,
                target_node,
                message_size_bytes,
                processing_time_ms
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"记录通信指标失败: {e}")
        finally:
            conn.close()
    
    def allocate_batch_tasks(self, tasks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量分配任务，优化通信开销
        
        Args:
            tasks_data: 任务数据列表，每个元素包含：
                - opportunity_data: 商机数据
                - task_type: 任务类型
                - required_capabilities: 所需能力
                - priority: 优先级
                - complexity: 复杂度
                - target_regions: 目标地域
        
        Returns:
            分配结果列表
        """
        if not tasks_data:
            return []
        
        logger.info(f"开始批量分配 {len(tasks_data)} 个任务")
        
        # 按任务类型分组
        task_groups = {}
        for task_data in tasks_data:
            task_type = task_data.get('task_type', 'general')
            if task_type not in task_groups:
                task_groups[task_type] = []
            task_groups[task_type].append(task_data)
        
        assignments = []
        
        for task_type, group_tasks in task_groups.items():
            logger.info(f"处理任务类型: {task_type} ({len(group_tasks)} 个任务)")
            
            # 为每组任务寻找最佳分身
            if group_tasks:
                sample_task = group_tasks[0]
                best_avatar = self.find_best_avatar_for_task(
                    required_capabilities=sample_task.get('required_capabilities'),
                    task_type=sample_task.get('task_type'),
                    priority=sample_task.get('priority', 2),
                    complexity=sample_task.get('complexity', 1.0),
                    target_regions=sample_task.get('target_regions', [])
                )
                
                if not best_avatar:
                    logger.warning(f"未找到适合{task_type}任务的分身")
                    continue
                
                # 为每个任务创建分配记录
                for task_data in group_tasks:
                    assignment = {
                        'task_id': f"batch_{int(time.time())}_{hashlib.md5(json.dumps(task_data).encode()).hexdigest()[:8]}",
                        'assigned_avatar': best_avatar,
                        'opportunity_data': task_data.get('opportunity_data', {}),
                        'task_type': task_type,
                        'priority': task_data.get('priority', 2),
                        'assigned_at': datetime.now().isoformat(),
                        'status': 'pending',
                        'batch_size': len(group_tasks)
                    }
                    
                    assignments.append(assignment)
                    
                    # 记录到数据库
                    self._save_batch_assignment(assignment)
        
        logger.info(f"批量分配完成: {len(assignments)} 个任务已分配")
        return assignments
    
    def _save_batch_assignment(self, assignment: Dict[str, Any]):
        """保存批量分配记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO task_assignments 
                (opportunity_hash, assigned_avatar, assignment_time, 
                 priority, completion_status, result_summary)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                assignment.get('opportunity_data', {}).get('_metadata', {}).get('opportunity_hash'),
                assignment['assigned_avatar'],
                assignment['assigned_at'],
                assignment['priority'],
                assignment['status'],
                json.dumps({
                    'task_id': assignment['task_id'],
                    'task_type': assignment['task_type'],
                    'batch_size': assignment.get('batch_size', 1)
                })
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"保存批量分配失败: {e}")
        finally:
            conn.close()
    
    def get_allocation_performance(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取分配性能报告
        
        Args:
            hours: 统计小时数
        
        Returns:
            性能报告
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='assignment_decisions'
            """)
            
            if not cursor.fetchone():
                return {'status': 'no_data', 'message': '性能数据未收集'}
            
            # 获取分配决策统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_decisions,
                    AVG(total_score) as avg_score,
                    AVG(capability_match) as avg_capability,
                    AVG(specialization_match) as avg_specialization,
                    AVG(region_match) as avg_region,
                    AVG(success_rate) as avg_success,
                    AVG(load_factor) as avg_load,
                    AVG(response_speed) as avg_response
                FROM assignment_decisions 
                WHERE timestamp >= datetime('now', ?)
            """, (f'-{hours} hours',))
            
            row = cursor.fetchone()
            
            # 获取通信开销统计
            cursor.execute("""
                SELECT 
                    AVG(processing_time_ms) as avg_processing_time,
                    AVG(message_size_bytes) as avg_message_size,
                    COUNT(*) as total_operations
                FROM communication_metrics 
                WHERE timestamp >= datetime('now', ?)
            """, (f'-{hours} hours',))
            
            comm_row = cursor.fetchone()
            
            report = {
                'period_hours': hours,
                'total_decisions': row[0] or 0,
                'avg_total_score': round(row[1] or 0, 3),
                'avg_capability_match': round(row[2] or 0, 3),
                'avg_specialization_match': round(row[3] or 0, 3),
                'avg_region_match': round(row[4] or 0, 3),
                'avg_success_rate': round(row[5] or 0, 3),
                'avg_load_factor': round(row[6] or 0, 3),
                'avg_response_speed': round(row[7] or 0, 3),
                'avg_processing_time_ms': round(comm_row[0] or 0, 1) if comm_row else 0,
                'avg_message_size_bytes': round(comm_row[1] or 0, 0) if comm_row else 0,
                'total_operations': comm_row[2] or 0 if comm_row else 0,
                'generated_at': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"获取性能报告失败: {e}")
            return {}
        finally:
            conn.close()


# 兼容旧版接口
def find_best_avatar_for_task_compat(required_capabilities: List[str] = None,
                                   min_score_threshold: float = 0.6) -> Optional[str]:
    """
    完全兼容旧版接口
    
    Args:
        required_capabilities: 所需能力列表
        min_score_threshold: 最低能力分数阈值
    
    Returns:
        最适合的分身ID，如无合适则返回None
    """
    allocator = OptimizedTaskAllocator()
    return allocator.find_best_avatar_for_task(
        required_capabilities=required_capabilities,
        min_score_threshold=min_score_threshold
    )


def test_optimized_allocator():
    """测试优化分配器"""
    allocator = OptimizedTaskAllocator()
    
    # 测试单任务分配
    avatar_id = allocator.find_best_avatar_for_task(
        required_capabilities=['data_crawling', 'financial_analysis'],
        task_type='financial_analysis',
        priority=2,
        complexity=5.0,
        target_regions=['US', 'CA']
    )
    
    if avatar_id:
        print(f"✅ 单任务分配成功: {avatar_id}")
    else:
        print("❌ 单任务分配失败")
    
    # 测试批量分配
    batch_tasks = []
    for i in range(3):
        task_data = {
            'opportunity_data': {
                'id': f'test_batch_{i}',
                'title': f'批量测试商机 {i}',
                'estimated_margin': 40 + i,
                '_metadata': {
                    'opportunity_hash': f'batch_hash_{i}'
                }
            },
            'task_type': 'financial_analysis',
            'required_capabilities': ['data_crawling', 'financial_analysis'],
            'priority': 2,
            'complexity': 3.0 + i,
            'target_regions': ['US', 'CA']
        }
        batch_tasks.append(task_data)
    
    assignments = allocator.allocate_batch_tasks(batch_tasks)
    
    if assignments:
        print(f"✅ 批量分配成功: {len(assignments)} 个任务")
    else:
        print("❌ 批量分配失败")
    
    # 获取性能报告
    report = allocator.get_allocation_performance(hours=1)
    
    if report and report.get('status') != 'no_data':
        print(f"📊 性能报告:")
        for key, value in report.items():
            print(f"  {key}: {value}")
    else:
        print("📊 无性能数据")


if __name__ == "__main__":
    test_optimized_allocator()