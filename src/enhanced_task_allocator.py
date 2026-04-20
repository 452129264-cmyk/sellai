#!/usr/bin/env python3
"""
增强任务分配器
基于分身能力画像实现动态任务匹配，提升分配精度和协同效率
"""

import json
import time
import logging
import sqlite3
import hashlib
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict
import random

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - ENHANCED-ALLOCATOR - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskType(Enum):
    """任务类型枚举"""
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

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class AvatarProfile:
    """增强版分身能力画像"""
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
    response_speed_score: float  # 响应速度分数（基于历史数据）
    
    # 新增字段
    task_type_preference: Dict[str, float] = None  # 任务类型偏好分数
    collaboration_history: Dict[str, int] = None  # 协作历史（合作过的分身ID -> 合作次数）
    quality_score: float = 0.8  # 任务完成质量评分
    availability_score: float = 1.0  # 可用性评分
    
    def __post_init__(self):
        if self.task_type_preference is None:
            self.task_type_preference = {}
        if self.collaboration_history is None:
            self.collaboration_history = {}

@dataclass
class TaskRequirements:
    """增强版任务需求描述"""
    task_type: TaskType
    required_capabilities: List[str]  # 必需能力列表
    priority: TaskPriority
    estimated_complexity: float  # 预估复杂度（1-10）
    target_regions: List[str]  # 目标地域
    deadline: Optional[datetime]  # 截止时间
    batch_size: int = 1  # 批处理大小
    max_cost: Optional[float] = None  # 最大成本限制
    
    # 新增字段
    quality_requirement: float = 0.7  # 质量要求阈值
    time_sensitivity: float = 0.5  # 时间敏感性（0-1）
    collaboration_needed: bool = False  # 是否需要协作
    specialized_expertise: List[str] = None  # 特殊专长要求
    
    def __post_init__(self):
        if self.specialized_expertise is None:
            self.specialized_expertise = []

@dataclass
class AllocationResult:
    """分配结果"""
    task_id: str
    assigned_avatar: str
    assignment_time: datetime
    deadline: Optional[datetime]
    priority: int
    estimated_completion_time: Optional[datetime]
    confidence_score: float  # 分配置信度（0-1）
    reasoning: str  # 分配理由
    alternative_avatars: List[str]  # 备选分身
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class EnhancedTaskAllocator:
    """增强任务分配器"""
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        """
        初始化增强任务分配器
        
        Args:
            db_path: 共享状态数据库路径
        """
        self.db_path = db_path
        self.profile_cache: Dict[str, AvatarProfile] = {}
        self.cache_expiry = 300  # 缓存过期时间（秒）
        self.last_cache_update = 0
        
        # 分配算法参数
        self.algorithm_params = {
            'capability_weight': 0.25,
            'specialization_weight': 0.15,
            'region_weight': 0.15,
            'reliability_weight': 0.20,
            'load_weight': 0.15,
            'cost_weight': 0.10,
            'min_confidence_threshold': 0.6,
            'cold_start_boost': 0.3  # 冷启动分身的额外分数
        }
        
        # 统计信息
        self.allocation_stats = {
            'total_allocations': 0,
            'successful_allocations': 0,
            'avg_confidence': 0.0,
            'cold_start_allocations': 0
        }
        
        logger.info("增强任务分配器初始化完成")
    
    def _load_enhanced_avatar_profiles(self, force_refresh: bool = False) -> Dict[str, AvatarProfile]:
        """
        加载增强版分身能力画像
        
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
                SELECT 
                    avatar_id, avatar_name, template_id, capability_scores, 
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
                
                # 计算增强字段
                region_expertise = self._calculate_region_expertise(avatar_id)
                cost_efficiency = self._calculate_cost_efficiency(avatar_id)
                reliability_score = self._calculate_reliability_score(
                    row[5],  # success_rate
                    row[7],  # avg_completion_time_seconds
                    row[8]   # current_load
                )
                response_speed_score = self._calculate_response_speed_score(row[7])
                
                # 计算任务类型偏好
                task_type_preference = self._calculate_task_type_preference(avatar_id)
                
                # 计算协作历史
                collaboration_history = self._load_collaboration_history(avatar_id)
                
                # 计算质量评分
                quality_score = self._calculate_quality_score(avatar_id)
                
                # 计算可用性评分
                availability_score = self._calculate_availability_score(avatar_id)
                
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
                    reliability_score=reliability_score,
                    response_speed_score=response_speed_score,
                    task_type_preference=task_type_preference,
                    collaboration_history=collaboration_history,
                    quality_score=quality_score,
                    availability_score=availability_score
                )
                
                profiles[avatar_id] = profile
            
            self.profile_cache = profiles
            self.last_cache_update = current_time
            
            logger.info(f"加载了 {len(profiles)} 个增强版分身画像")
            return profiles
            
        except Exception as e:
            logger.error(f"加载增强版分身画像失败: {e}")
            return {}
        finally:
            conn.close()
    
    def allocate_task(self, task_req: TaskRequirements, opportunity_data: Optional[Dict[str, Any]] = None) -> Optional[AllocationResult]:
        """
        分配任务给最适合的分身
        
        Args:
            task_req: 任务需求描述
            opportunity_data: 商机数据（可选）
            
        Returns:
            分配结果，如无合适分身则返回None
        """
        # 加载分身画像
        profiles = self._load_enhanced_avatar_profiles()
        if not profiles:
            logger.warning("没有可用的分身画像")
            return None
        
        # 评估所有分身
        scored_avatars = []
        for avatar_id, profile in profiles.items():
            score, details, reasoning = self._evaluate_avatar_for_task(profile, task_req)
            
            if score >= self.algorithm_params['min_confidence_threshold']:
                scored_avatars.append((score, avatar_id, details, reasoning))
        
        if not scored_avatars:
            logger.warning("未找到满足最低置信度阈值的分身")
            return None
        
        # 按分数排序
        scored_avatars.sort(key=lambda x: x[0], reverse=True)
        
        # 选择最佳分身
        best_score, best_avatar_id, best_details, best_reasoning = scored_avatars[0]
        
        # 备选分身（分数相近的）
        alternative_avatars = []
        for score, avatar_id, _, _ in scored_avatars[1:4]:  # 取2-4名
            if score >= best_score * 0.8:  # 分数不低于最佳分数的80%
                alternative_avatars.append(avatar_id)
        
        # 生成任务ID
        task_id = self._generate_task_id(task_req, opportunity_data)
        
        # 计算预估完成时间
        estimated_completion = self._estimate_completion_time(
            profiles[best_avatar_id], task_req
        )
        
        # 创建分配结果
        result = AllocationResult(
            task_id=task_id,
            assigned_avatar=best_avatar_id,
            assignment_time=datetime.now(),
            deadline=task_req.deadline,
            priority=task_req.priority.value,
            estimated_completion_time=estimated_completion,
            confidence_score=best_score,
            reasoning=best_reasoning,
            alternative_avatars=alternative_avatars
        )
        
        # 更新统计信息
        self._update_allocation_stats(best_score, profiles[best_avatar_id])
        
        # 记录分配决策
        self._record_allocation_decision(result, best_details)
        
        logger.info(f"任务分配完成: {task_id} -> {best_avatar_id} (置信度: {best_score:.3f})")
        logger.debug(f"分配理由: {best_reasoning}")
        
        return result
    
    def _evaluate_avatar_for_task(self, profile: AvatarProfile, task_req: TaskRequirements) -> Tuple[float, Dict[str, float], str]:
        """
        评估分身对任务的适合度
        
        Returns:
            (综合分数, 各维度分数详情, 分配理由)
        """
        scores = {}
        reasoning_factors = []
        
        # 1. 能力匹配度（核心维度）
        capability_score = self._calculate_capability_match(profile, task_req)
        scores['capability_match'] = capability_score
        
        if capability_score < 0.5:
            reasoning_factors.append(f"能力匹配度较低({capability_score:.2f})")
        
        # 2. 专长标签匹配度
        specialization_score = self._calculate_specialization_match(profile, task_req)
        scores['specialization_match'] = specialization_score
        
        if specialization_score > 0.8:
            reasoning_factors.append(f"专长高度匹配")
        
        # 3. 地域匹配度
        region_score = self._calculate_region_match(profile, task_req)
        scores['region_match'] = region_score
        
        if region_score > 0:
            reasoning_factors.append(f"地域匹配({region_score:.2f})")
        
        # 4. 可靠性分数
        scores['reliability'] = profile.reliability_score
        
        if profile.reliability_score < 0.7:
            reasoning_factors.append(f"可靠性需提升")
        
        # 5. 负载因子
        load_factor = 1.0 / (1.0 + profile.current_load)
        scores['load_factor'] = load_factor
        
        if profile.current_load > 5:
            reasoning_factors.append(f"负载较高({profile.current_load})")
        
        # 6. 成本效率
        scores['cost_efficiency'] = profile.cost_efficiency
        
        if profile.cost_efficiency < 0.5:
            reasoning_factors.append(f"成本效率较低")
        
        # 7. 响应速度
        scores['response_speed'] = profile.response_speed_score
        
        # 8. 任务类型偏好
        preference_score = self._calculate_task_type_preference_score(profile, task_req)
        scores['task_type_preference'] = preference_score
        
        # 9. 质量评分
        scores['quality_score'] = profile.quality_score
        
        if profile.quality_score < task_req.quality_requirement:
            reasoning_factors.append(f"质量评分未达要求")
        
        # 10. 可用性评分
        scores['availability_score'] = profile.availability_score
        
        # 应用冷启动优化：为新分身（完成任务数<5）提供额外分数
        cold_start_boost = 0.0
        if profile.total_tasks_completed < 5:
            cold_start_boost = self.algorithm_params['cold_start_boost'] * (5 - profile.total_tasks_completed) / 5
            reasoning_factors.append(f"冷启动优化(+{cold_start_boost:.2f})")
        
        # 计算加权分数
        weights = {
            'capability_match': self.algorithm_params['capability_weight'],
            'specialization_match': self.algorithm_params['specialization_weight'],
            'region_match': self.algorithm_params['region_weight'],
            'reliability': self.algorithm_params['reliability_weight'],
            'load_factor': self.algorithm_params['load_weight'],
            'cost_efficiency': self.algorithm_params['cost_weight'],
            'response_speed': 0.05,
            'task_type_preference': 0.05,
            'quality_score': 0.05,
            'availability_score': 0.05
        }
        
        total_score = 0.0
        weight_sum = 0.0
        
        for key, weight in weights.items():
            if key in scores:
                total_score += scores[key] * weight
                weight_sum += weight
        
        if weight_sum > 0:
            weighted_score = total_score / weight_sum
        else:
            weighted_score = 0.0
        
        # 应用冷启动优化
        final_score = min(1.0, weighted_score + cold_start_boost)
        
        # 生成分配理由
        reasoning = self._generate_allocation_reasoning(
            profile, task_req, scores, reasoning_factors, final_score
        )
        
        return final_score, scores, reasoning
    
    def _calculate_capability_match(self, profile: AvatarProfile, task_req: TaskRequirements) -> float:
        """计算能力匹配度"""
        if not task_req.required_capabilities:
            return 1.0  # 没有特定要求，默认可匹配
        
        relevant_scores = []
        for capability in task_req.required_capabilities:
            if capability in profile.capability_scores:
                score = profile.capability_scores[capability]
                relevant_scores.append(score)
            else:
                relevant_scores.append(0.0)
        
        if not relevant_scores:
            return 0.0
        
        # 加权平均：核心能力权重更高
        weights = [1.2 if i < 2 else 1.0 for i in range(len(relevant_scores))]  # 前两项权重1.2
        weighted_sum = sum(s * w for s, w in zip(relevant_scores, weights))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_specialization_match(self, profile: AvatarProfile, task_req: TaskRequirements) -> float:
        """计算专长标签匹配度"""
        if not profile.specialization_tags:
            return 0.5  # 没有专长标签，中等匹配
        
        task_type_str = task_req.task_type.value
        
        # 精确匹配
        if task_type_str in profile.specialization_tags:
            return 1.0
        
        # 部分匹配（标签包含任务类型关键词）
        for tag in profile.specialization_tags:
            if task_type_str in tag.lower() or tag.lower() in task_type_str:
                return 0.8
        
        # 领域匹配（检查是否有相关领域专长）
        related_domains = {
            'data_crawling': ['web_scraping', 'data_collection', 'research'],
            'financial_analysis': ['finance', 'investment', 'accounting'],
            'content_creation': ['writing', 'copywriting', 'creative'],
            'account_operation': ['management', 'administration', 'operations']
        }
        
        if task_type_str in related_domains:
            for tag in profile.specialization_tags:
                for related in related_domains[task_type_str]:
                    if related in tag.lower():
                        return 0.6
        
        return 0.3  # 低匹配度
    
    def _calculate_region_match(self, profile: AvatarProfile, task_req: TaskRequirements) -> float:
        """计算地域匹配度"""
        if not task_req.target_regions or not profile.region_expertise:
            return 0.5  # 没有地域要求或专长，中等匹配
        
        # 计算交集比例
        intersection = set(task_req.target_regions) & set(profile.region_expertise)
        if intersection:
            return len(intersection) / len(task_req.target_regions)
        
        return 0.2  # 无交集，低匹配度
    
    def _calculate_reliability_score(self, success_rate: float, avg_completion_time: float, current_load: int) -> float:
        """计算可靠性分数"""
        # 成功率权重0.4
        success_component = success_rate * 0.4
        
        # 响应时间权重0.3（时间越短越好）
        if avg_completion_time and avg_completion_time > 0:
            time_score = max(0, 1.0 - (avg_completion_time / 600))  # 600秒内归一化
            time_component = time_score * 0.3
        else:
            time_component = 0.15  # 默认值
        
        # 负载权重0.3（负载越低越好）
        load_factor = 1.0 / (1.0 + current_load)
        load_component = load_factor * 0.3
        
        return success_component + time_component + load_component
    
    def _calculate_response_speed_score(self, avg_completion_time: float) -> float:
        """计算响应速度分数"""
        if avg_completion_time and avg_completion_time > 0:
            # 归一化：假设合理完成时间在300秒内
            return max(0, 1.0 - (avg_completion_time / 300))
        return 0.7  # 默认值
    
    def _calculate_task_type_preference(self, avatar_id: str) -> Dict[str, float]:
        """计算分身对任务类型的偏好"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查询历史任务记录
            cursor.execute("""
                SELECT task_type, COUNT(*) as count, AVG(completion_status = 'completed') as success_rate
                FROM task_assignments 
                WHERE assigned_avatar = ?
                GROUP BY task_type
            """, (avatar_id,))
            
            preferences = {}
            total_tasks = 0
            
            for row in cursor.fetchall():
                task_type, count, success_rate = row
                total_tasks += count
                
                # 偏好分数 = 任务占比 × 成功率
                if success_rate:
                    preferences[task_type] = (count / max(1, total_tasks)) * success_rate
                else:
                    preferences[task_type] = (count / max(1, total_tasks)) * 0.5
            
            # 如果没有历史记录，使用默认偏好
            if not preferences:
                for task_type in TaskType:
                    preferences[task_type.value] = 0.5
            
            return preferences
            
        except Exception as e:
            logger.debug(f"计算任务类型偏好失败: {e}")
            return {}
        finally:
            conn.close()
    
    def _calculate_task_type_preference_score(self, profile: AvatarProfile, task_req: TaskRequirements) -> float:
        """计算任务类型偏好匹配分数"""
        task_type = task_req.task_type.value
        
        if task_type in profile.task_type_preference:
            return profile.task_type_preference[task_type]
        
        return 0.5  # 默认值
    
    def _load_collaboration_history(self, avatar_id: str) -> Dict[str, int]:
        """加载协作历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查询与其他分身的协作次数
            cursor.execute("""
                SELECT assigned_avatar, COUNT(*) as collaboration_count
                FROM task_assignments ta1
                WHERE EXISTS (
                    SELECT 1 FROM task_assignments ta2
                    WHERE ta1.opportunity_hash = ta2.opportunity_hash
                    AND ta2.assigned_avatar = ?
                    AND ta1.assigned_avatar != ?
                )
                GROUP BY assigned_avatar
            """, (avatar_id, avatar_id))
            
            history = {}
            for row in cursor.fetchall():
                other_avatar, count = row
                history[other_avatar] = count
            
            return history
            
        except Exception as e:
            logger.debug(f"加载协作历史失败: {e}")
            return {}
        finally:
            conn.close()
    
    def _calculate_quality_score(self, avatar_id: str) -> float:
        """计算质量评分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 基于任务结果质量评估
            cursor.execute("""
                SELECT 
                    AVG(CASE WHEN completion_status = 'completed' THEN 1.0 ELSE 0.0 END) as completion_rate,
                    AVG(LENGTH(result_summary)) as result_detail
                FROM task_assignments 
                WHERE assigned_avatar = ?
            """, (avatar_id,))
            
            row = cursor.fetchone()
            if row:
                completion_rate = row[0] or 0.0
                result_detail = row[1] or 0.0
                
                # 综合评分：完成率权重0.7，结果详细程度权重0.3
                detail_score = min(1.0, result_detail / 500)  # 500字符为满分
                quality_score = (completion_rate * 0.7) + (detail_score * 0.3)
                return quality_score
            
            return 0.7  # 默认值
            
        except Exception as e:
            logger.debug(f"计算质量评分失败: {e}")
            return 0.7
        finally:
            conn.close()
    
    def _calculate_availability_score(self, avatar_id: str) -> float:
        """计算可用性评分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 基于最近活动和负载计算可用性
            cursor.execute("""
                SELECT current_load, last_active
                FROM avatar_capability_profiles
                WHERE avatar_id = ?
            """, (avatar_id,))
            
            row = cursor.fetchone()
            if row:
                current_load = row[0] or 0
                last_active_str = row[1]
                
                if last_active_str:
                    last_active = datetime.fromisoformat(last_active_str.replace('Z', '+00:00'))
                    hours_inactive = (datetime.now() - last_active).total_seconds() / 3600
                    
                    # 负载因子：负载越低越好
                    load_factor = 1.0 / (1.0 + current_load)
                    
                    # 活动性因子：最近活跃越好
                    activity_factor = max(0, 1.0 - (hours_inactive / 24))  # 24小时内活跃
                    
                    # 综合可用性评分
                    availability = (load_factor * 0.6) + (activity_factor * 0.4)
                    return availability
            
            return 0.8  # 默认值
            
        except Exception as e:
            logger.debug(f"计算可用性评分失败: {e}")
            return 0.8
        finally:
            conn.close()
    
    def _calculate_region_expertise(self, avatar_id: str) -> List[str]:
        """计算分身的地域专长"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 从任务结果中提取地域信息
            cursor.execute("""
                SELECT result_summary 
                FROM task_assignments
                WHERE assigned_avatar = ? 
                  AND completion_status = 'completed'
                  AND result_summary IS NOT NULL
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
                
                # 成本效率 = 完成任务数 / (成本 + 1)
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
    
    def _generate_allocation_reasoning(self, profile: AvatarProfile, task_req: TaskRequirements, 
                                     scores: Dict[str, float], reasoning_factors: List[str], 
                                     final_score: float) -> str:
        """生成分配理由"""
        # 主要优势
        strengths = []
        
        if scores['capability_match'] > 0.8:
            strengths.append("能力高度匹配")
        elif scores['capability_match'] > 0.6:
            strengths.append("能力匹配良好")
        
        if scores['specialization_match'] > 0.8:
            strengths.append("专长领域对口")
        
        if scores['region_match'] > 0.7:
            strengths.append("地域经验丰富")
        
        if profile.reliability_score > 0.8:
            strengths.append("可靠性高")
        
        if profile.current_load == 0:
            strengths.append("当前空闲")
        
        # 构建理由
        reason_parts = []
        
        if strengths:
            reason_parts.append(f"{profile.avatar_name}具有以下优势：{', '.join(strengths)}")
        
        if profile.total_tasks_completed < 5:
            reason_parts.append("该分身为新创建分身，提供冷启动机会以收集性能数据")
        
        if task_req.priority == TaskPriority.URGENT:
            reason_parts.append("任务优先级为紧急，选择响应速度最快且可靠性高的分身")
        
        # 综合理由
        if not reason_parts:
            reason_parts.append(f"基于能力匹配度({scores['capability_match']:.2f})和可靠性({profile.reliability_score:.2f})的综合评估")
        
        return "。".join(reason_parts) + f"（综合评分：{final_score:.3f}）"
    
    def _generate_task_id(self, task_req: TaskRequirements, opportunity_data: Optional[Dict[str, Any]]) -> str:
        """生成任务ID"""
        base_str = f"{task_req.task_type.value}_{int(time.time())}"
        
        if opportunity_data:
            # 使用商机数据的哈希部分
            data_hash = hashlib.md5(json.dumps(opportunity_data).encode()).hexdigest()[:8]
            return f"task_{base_str}_{data_hash}"
        else:
            # 随机生成
            random_str = ''.join(random.choices('0123456789abcdef', k=6))
            return f"task_{base_str}_{random_str}"
    
    def _estimate_completion_time(self, profile: AvatarProfile, task_req: TaskRequirements) -> Optional[datetime]:
        """估算任务完成时间"""
        if not profile.avg_completion_time_seconds or profile.avg_completion_time_seconds <= 0:
            return None
        
        # 基于历史平均时间和任务复杂度估算
        estimated_seconds = profile.avg_completion_time_seconds * task_req.estimated_complexity
        
        # 考虑当前负载
        load_factor = 1.0 + (profile.current_load * 0.2)  # 每增加一个负载，时间增加20%
        adjusted_seconds = estimated_seconds * load_factor
        
        return datetime.now() + timedelta(seconds=adjusted_seconds)
    
    def _update_allocation_stats(self, confidence_score: float, profile: AvatarProfile):
        """更新分配统计"""
        self.allocation_stats['total_allocations'] += 1
        self.allocation_stats['successful_allocations'] += 1
        
        # 更新平均置信度
        total_confidence = self.allocation_stats['avg_confidence'] * (self.allocation_stats['total_allocations'] - 1)
        self.allocation_stats['avg_confidence'] = (total_confidence + confidence_score) / self.allocation_stats['total_allocations']
        
        # 冷启动统计
        if profile.total_tasks_completed < 5:
            self.allocation_stats['cold_start_allocations'] += 1
    
    def _record_allocation_decision(self, result: AllocationResult, score_details: Dict[str, float]):
        """记录分配决策到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 确保表存在
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS enhanced_allocation_decisions (
                    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    assigned_avatar TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    score_details TEXT NOT NULL,  -- JSON格式
                    reasoning TEXT,
                    assignment_time TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 插入记录
            cursor.execute("""
                INSERT INTO enhanced_allocation_decisions 
                (task_id, assigned_avatar, confidence_score, score_details, reasoning, assignment_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                result.task_id,
                result.assigned_avatar,
                result.confidence_score,
                json.dumps(score_details),
                result.reasoning,
                result.assignment_time.isoformat()
            ))
            
            conn.commit()
            logger.debug(f"分配决策已记录: {result.task_id}")
            
        except Exception as e:
            logger.error(f"记录分配决策失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_allocation_report(self) -> Dict[str, Any]:
        """获取分配报告"""
        return {
            "total_allocations": self.allocation_stats['total_allocations'],
            "successful_allocations": self.allocation_stats['successful_allocations'],
            "success_rate": self.allocation_stats['successful_allocations'] / max(1, self.allocation_stats['total_allocations']),
            "avg_confidence": self.allocation_stats['avg_confidence'],
            "cold_start_allocations": self.allocation_stats['cold_start_allocations'],
            "algorithm_params": self.algorithm_params,
            "timestamp": datetime.now().isoformat()
        }


# 全局分配器实例
_global_allocator = None

def get_global_allocator() -> EnhancedTaskAllocator:
    """获取全局分配器实例"""
    global _global_allocator
    if _global_allocator is None:
        _global_allocator = EnhancedTaskAllocator()
    return _global_allocator


def create_sample_task() -> TaskRequirements:
    """创建示例任务"""
    return TaskRequirements(
        task_type=TaskType.FINANCIAL_ANALYSIS,
        required_capabilities=['data_crawling', 'financial_analysis', 'business_matching'],
        priority=TaskPriority.HIGH,
        estimated_complexity=6.0,
        target_regions=['US', 'CA', 'UK'],
        deadline=datetime.now() + timedelta(hours=12),
        quality_requirement=0.8,
        time_sensitivity=0.7,
        collaboration_needed=True,
        specialized_expertise=['investment_analysis', 'market_research']
    )


def main():
    """测试增强任务分配器"""
    allocator = EnhancedTaskAllocator()
    
    # 创建测试任务
    task_req = create_sample_task()
    
    print(f"分配任务: {task_req.task_type.value}")
    print(f"任务需求: {task_req.required_capabilities}")
    print(f"优先级: {task_req.priority.value}")
    
    # 分配任务
    result = allocator.allocate_task(task_req)
    
    if result:
        print(f"\n分配结果:")
        print(f"  任务ID: {result.task_id}")
        print(f"  分配分身: {result.assigned_avatar}")
        print(f"  置信度: {result.confidence_score:.3f}")
        print(f"  预估完成: {result.estimated_completion_time}")
        print(f"  分配理由: {result.reasoning}")
        print(f"  备选分身: {', '.join(result.alternative_avatars) if result.alternative_avatars else '无'}")
    else:
        print("任务分配失败")
    
    # 获取分配报告
    report = allocator.get_allocation_report()
    print(f"\n分配报告:")
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")
    
    print("\n增强任务分配器测试完成")


if __name__ == "__main__":
    main()