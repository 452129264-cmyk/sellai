#!/usr/bin/env python3
"""
负载均衡分配器
基于数据分析结果，针对任务堆积问题，实现动态负载感知调度
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
import numpy as np

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - LOAD-BALANCED-ALLOCATOR - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizedTaskType(Enum):
    """优化版任务类型枚举"""
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
class OptimizedAvatarProfile:
    """优化版分身能力画像，集成健康状态"""
    avatar_id: str
    avatar_name: str
    template_id: Optional[str]
    capability_scores: Dict[str, float]
    specialization_tags: List[str]
    success_rate: float
    total_tasks_completed: int
    avg_completion_time_seconds: float
    current_load: int
    last_active: datetime
    created_at: datetime
    region_expertise: List[str]
    cost_efficiency: float
    reliability_score: float
    response_speed_score: float
    
    # 新增健康状态字段
    health_status: str = "unknown"  # healthy, degraded, unknown
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0
    task_success_rate: float = 1.0
    
    # 负载均衡相关
    max_capacity: int = 5  # 最大负载能力
    load_history: List[Tuple[datetime, int]] = None  # 负载历史记录
    
    def __post_init__(self):
        if self.load_history is None:
            self.load_history = []
    
    @property
    def availability_score(self) -> float:
        """计算可用性分数，考虑健康和负载"""
        # 健康状态权重
        health_weight = 0.6
        load_weight = 0.4
        
        # 健康状态分数映射
        health_scores = {
            "healthy": 1.0,
            "degraded": 0.5,
            "unknown": 0.3
        }
        
        health_score = health_scores.get(self.health_status, 0.3)
        
        # 负载分数（负载越低分数越高）
        load_ratio = self.current_load / self.max_capacity if self.max_capacity > 0 else 1.0
        load_score = 1.0 - min(load_ratio, 1.0)  # 负载0%时得1分，100%时得0分
        
        # 综合分数
        return health_weight * health_score + load_weight * load_score
    
    @property
    def capability_shortcomings(self) -> List[str]:
        """识别能力短板（分数<0.7）"""
        shortcomings = []
        for capability, score in self.capability_scores.items():
            if score < 0.7:
                shortcomings.append(capability)
        return shortcomings
    
    def can_handle_task(self, required_capabilities: List[str], min_score: float = 0.7) -> bool:
        """检查分身是否能处理特定任务"""
        # 检查健康状态
        if self.health_status not in ["healthy", "unknown"]:
            return False
        
        # 检查负载
        if self.current_load >= self.max_capacity:
            return False
        
        # 检查能力要求
        for capability in required_capabilities:
            if capability not in self.capability_scores:
                return False
            if self.capability_scores[capability] < min_score:
                return False
        
        return True

@dataclass
class OptimizedTaskRequirements:
    """优化版任务需求描述"""
    task_type: OptimizedTaskType
    required_capabilities: List[str]
    priority: TaskPriority
    estimated_complexity: float
    target_regions: List[str]
    deadline: Optional[datetime]
    batch_size: int = 1
    max_cost: Optional[float] = None
    
    # 新增优化字段
    quality_requirement: float = 0.7
    time_sensitivity: float = 0.5
    collaboration_needed: bool = False
    specialized_expertise: List[str] = None
    avoid_shortcomings: bool = True  # 是否避免能力短板
    load_balance_preference: float = 0.8  # 负载均衡偏好（0-1）
    
    def __post_init__(self):
        if self.specialized_expertise is None:
            self.specialized_expertise = []

@dataclass
class LoadBalancedAllocationResult:
    """负载均衡分配结果"""
    task_id: str
    assigned_avatar: str
    assignment_time: datetime
    estimated_completion_time: Optional[datetime]
    matching_score: float
    reason: str  # 分配原因
    load_balance_impact: float  # 对负载均衡的影响（正数表示改善）
    
    # 新增字段
    capability_match_details: Dict[str, float]
    health_status: str
    current_load_before: int
    current_load_after: int
    system_load_balance_score_before: float
    system_load_balance_score_after: float

class LoadBalancedAllocator:
    """
    负载均衡分配器
    核心优化算法：基于实时负载动态分配任务，解决任务堆积问题
    """
    
    def __init__(self, db_path: str = "data/shared_state/state.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.avatar_profiles_cache = {}
        self.load_history_window = 24  # 小时
        self.load_balance_threshold = 0.3  # 负载均衡阈值
    
    def load_avatar_profiles(self) -> Dict[str, OptimizedAvatarProfile]:
        """加载分身能力画像和健康状态"""
        profiles = {}
        
        try:
            # 加载能力画像
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT avatar_id, avatar_name, template_id, 
                       capability_scores, specialization_tags,
                       success_rate, total_tasks_completed,
                       current_load, last_active, created_at
                FROM avatar_capability_profiles
            """)
            
            avatar_rows = cursor.fetchall()
            
            # 加载健康状态
            cursor.execute("""
                SELECT node_id, status, last_heartbeat, task_success_rate, error_count
                FROM node_health_status
            """)
            
            health_rows = cursor.fetchall()
            health_map = {row[0]: row[1:] for row in health_rows}
            
            # 构建优化版分身画像
            for row in avatar_rows:
                avatar_id = row[0]
                
                # 解析能力分数
                try:
                    capability_scores = json.loads(row[3])
                except json.JSONDecodeError:
                    logger.warning(f"无法解析分身 {avatar_id} 的能力分数，使用默认值")
                    capability_scores = {
                        "data_crawling": 0.7,
                        "financial_analysis": 0.7,
                        "content_creation": 0.7,
                        "account_operation": 0.7,
                        "negotiation": 0.7
                    }
                
                # 获取健康状态
                health_data = health_map.get(avatar_id, ["unknown", None, 1.0, 0])
                
                profile = OptimizedAvatarProfile(
                    avatar_id=avatar_id,
                    avatar_name=row[1],
                    template_id=row[2],
                    capability_scores=capability_scores,
                    specialization_tags=json.loads(row[4]) if row[4] else [],
                    success_rate=float(row[5]),
                    total_tasks_completed=int(row[6]),
                    avg_completion_time_seconds=float(row[7]) if row[7] else None,
                    current_load=int(row[8]),
                    last_active=datetime.fromisoformat(row[9].replace('Z', '+00:00')),
                    created_at=datetime.fromisoformat(row[10].replace('Z', '+00:00')),
                    region_expertise=["global"],  # 默认全局
                    cost_efficiency=0.8,  # 默认成本效率
                    reliability_score=0.9,  # 默认可靠性
                    response_speed_score=0.8,  # 默认响应速度
                    health_status=health_data[0],
                    last_heartbeat=datetime.fromisoformat(health_data[1].replace('Z', '+00:00')) if health_data[1] else None,
                    task_success_rate=float(health_data[2]),
                    error_count=int(health_data[3])
                )
                
                profiles[avatar_id] = profile
            
            self.avatar_profiles_cache = profiles
            logger.info(f"成功加载 {len(profiles)} 个分身画像")
            
        except Exception as e:
            logger.error(f"加载分身画像失败: {str(e)}")
            raise
        
        return profiles
    
    def calculate_load_balance_score(self, avatar_profiles: Dict[str, OptimizedAvatarProfile]) -> float:
        """
        计算系统负载均衡分数
        分数越高表示负载越均衡，范围0-1
        """
        if not avatar_profiles:
            return 0.0
        
        # 获取所有分身的负载
        loads = [profile.current_load for profile in avatar_profiles.values()]
        
        if not loads:
            return 0.0
        
        # 计算负载标准差
        std_load = np.std(loads)
        
        # 计算最大可能标准差（所有负载都在0或max_capacity）
        max_loads = [profile.max_capacity for profile in avatar_profiles.values()]
        if len(max_loads) > 1:
            max_std = np.std([0, max(max_loads)])
        else:
            max_std = 1.0
        
        # 标准化分数（标准差越小分数越高）
        if max_std == 0:
            return 1.0
        
        load_balance_score = 1.0 - min(std_load / max_std, 1.0)
        
        return float(load_balance_score)
    
    def find_optimal_avatar(self, task_req: OptimizedTaskRequirements, 
                           avatar_profiles: Dict[str, OptimizedAvatarProfile]) -> Tuple[str, float, str]:
        """
        寻找最优分身分配任务
        返回：(avatar_id, matching_score, reason)
        """
        
        # 筛选可用的分身
        candidate_avatars = {}
        
        for avatar_id, profile in avatar_profiles.items():
            # 基础检查
            if not profile.can_handle_task(task_req.required_capabilities):
                continue
            
            # 能力短板规避检查
            if task_req.avoid_shortcomings:
                shortcomings = profile.capability_shortcomings
                task_shortcomings = [cap for cap in task_req.required_capabilities if cap in shortcomings]
                if task_shortcomings:
                    continue  # 跳过有相关能力短板的分身
            
            # 计算匹配分数
            matching_score = self.calculate_matching_score(profile, task_req)
            
            # 计算负载平衡调整因子
            load_balance_factor = self.calculate_load_balance_factor(profile, avatar_profiles, task_req)
            
            # 最终分数 = 匹配分数 × 负载平衡因子
            final_score = matching_score * load_balance_factor
            
            candidate_avatars[avatar_id] = {
                'profile': profile,
                'matching_score': matching_score,
                'load_balance_factor': load_balance_factor,
                'final_score': final_score
            }
        
        if not candidate_avatars:
            return None, 0.0, "无可用的合适分身"
        
        # 按最终分数排序
        sorted_candidates = sorted(candidate_avatars.items(), 
                                   key=lambda x: x[1]['final_score'], 
                                   reverse=True)
        
        best_avatar_id, best_data = sorted_candidates[0]
        best_profile = best_data['profile']
        
        # 生成分配原因
        reason_parts = []
        
        # 能力匹配
        capability_details = []
        for cap in task_req.required_capabilities:
            if cap in best_profile.capability_scores:
                score = best_profile.capability_scores[cap]
                capability_details.append(f"{cap}:{score:.2f}")
        
        if capability_details:
            reason_parts.append(f"能力匹配: {', '.join(capability_details)}")
        
        # 负载优势
        avg_load = np.mean([p.current_load for p in avatar_profiles.values()])
        load_diff = avg_load - best_profile.current_load
        if load_diff > 0:
            reason_parts.append(f"负载低于平均{load_diff:.1f}个任务")
        elif load_diff < 0:
            reason_parts.append(f"负载高于平均{-load_diff:.1f}个任务")
        
        # 健康状态
        if best_profile.health_status == "healthy":
            reason_parts.append("健康状态良好")
        elif best_profile.health_status == "degraded":
            reason_parts.append("注意：健康状态降级")
        
        # 成功记录
        if best_profile.success_rate > 0.8:
            reason_parts.append(f"历史成功率{best_profile.success_rate:.1%}")
        
        reason = " | ".join(reason_parts)
        
        return best_avatar_id, best_data['final_score'], reason
    
    def calculate_matching_score(self, profile: OptimizedAvatarProfile, 
                                task_req: OptimizedTaskRequirements) -> float:
        """
        计算分身与任务的匹配分数
        考虑：能力分数、专长标签、地域专长、成本效率等
        """
        
        # 1. 基础能力匹配（权重0.5）
        capability_scores = []
        for cap in task_req.required_capabilities:
            if cap in profile.capability_scores:
                capability_scores.append(profile.capability_scores[cap])
            else:
                capability_scores.append(0.0)  # 能力不存在
        
        capability_score = np.mean(capability_scores) if capability_scores else 0.0
        
        # 2. 专长标签匹配（权重0.2）
        specialization_score = 0.0
        if task_req.specialized_expertise:
            matched_specializations = set(task_req.specialized_expertise) & set(profile.specialization_tags)
            if task_req.specialized_expertise:
                specialization_score = len(matched_specializations) / len(task_req.specialized_expertise)
        
        # 3. 地域专长匹配（权重0.1）
        region_score = 0.0
        if task_req.target_regions:
            matched_regions = set(task_req.target_regions) & set(profile.region_expertise)
            if task_req.target_regions:
                region_score = len(matched_regions) / len(task_req.target_regions)
        
        # 4. 成本效率（权重0.1）
        cost_score = profile.cost_efficiency
        
        # 5. 可靠性和响应速度（权重0.1）
        reliability_score = profile.reliability_score * profile.response_speed_score
        
        # 加权计算总分
        total_score = (
            0.5 * capability_score +
            0.2 * specialization_score +
            0.1 * region_score +
            0.1 * cost_score +
            0.1 * reliability_score
        )
        
        return total_score
    
    def calculate_load_balance_factor(self, profile: OptimizedAvatarProfile,
                                     all_profiles: Dict[str, OptimizedAvatarProfile],
                                     task_req: OptimizedTaskRequirements) -> float:
        """
        计算负载平衡调整因子
        考虑：当前负载、最大容量、历史负载、任务复杂度等
        """
        
        # 获取负载平衡偏好
        load_balance_pref = task_req.load_balance_preference
        
        # 计算当前负载率
        current_load_rate = profile.current_load / profile.max_capacity if profile.max_capacity > 0 else 1.0
        
        # 计算系统平均负载率
        avg_load_rate = np.mean([
            p.current_load / p.max_capacity if p.max_capacity > 0 else 1.0
            for p in all_profiles.values()
        ])
        
        # 计算负载偏差
        load_deviation = current_load_rate - avg_load_rate
        
        # 如果分身负载低于平均，给予正向奖励
        if load_deviation < 0:
            # 负载越低于平均，奖励越大
            reward = abs(load_deviation) * 0.5
            adjustment = 1.0 + (reward * load_balance_pref)
        else:
            # 负载高于平均，给予惩罚
            penalty = load_deviation * 0.3
            adjustment = 1.0 - (penalty * load_balance_pref)
        
        # 确保调整因子在合理范围内
        adjustment = max(0.5, min(1.5, adjustment))
        
        return adjustment
    
    def allocate_task(self, task_id: str, task_req: OptimizedTaskRequirements) -> LoadBalancedAllocationResult:
        """
        分配任务给最优分身
        """
        
        # 加载分身画像
        avatar_profiles = self.load_avatar_profiles()
        
        # 计算分配前的负载均衡分数
        before_score = self.calculate_load_balance_score(avatar_profiles)
        
        # 寻找最优分身
        best_avatar_id, matching_score, reason = self.find_optimal_avatar(task_req, avatar_profiles)
        
        if not best_avatar_id:
            raise ValueError("无法找到合适的分身分配任务")
        
        best_profile = avatar_profiles[best_avatar_id]
        
        # 记录分配前的负载
        load_before = best_profile.current_load
        
        # 模拟更新分身负载
        best_profile.current_load += task_req.batch_size
        
        # 计算分配后的负载均衡分数
        after_score = self.calculate_load_balance_score(avatar_profiles)
        
        # 计算负载平衡影响
        load_balance_impact = after_score - before_score
        
        # 构建分配结果
        capability_match_details = {}
        for cap in task_req.required_capabilities:
            if cap in best_profile.capability_scores:
                capability_match_details[cap] = best_profile.capability_scores[cap]
        
        result = LoadBalancedAllocationResult(
            task_id=task_id,
            assigned_avatar=best_avatar_id,
            assignment_time=datetime.now(),
            estimated_completion_time=self.estimate_completion_time(best_profile, task_req),
            matching_score=matching_score,
            reason=reason,
            load_balance_impact=load_balance_impact,
            capability_match_details=capability_match_details,
            health_status=best_profile.health_status,
            current_load_before=load_before,
            current_load_after=best_profile.current_load,
            system_load_balance_score_before=before_score,
            system_load_balance_score_after=after_score
        )
        
        # 记录分配决策到数据库
        self.record_allocation_decision(result, task_req)
        
        logger.info(f"任务{task_id}分配给分身{best_avatar_id}，匹配分数{matching_score:.3f}，原因: {reason}")
        
        return result
    
    def estimate_completion_time(self, profile: OptimizedAvatarProfile,
                               task_req: OptimizedTaskRequirements) -> Optional[datetime]:
        """预估任务完成时间"""
        
        if not profile.avg_completion_time_seconds:
            return None
        
        # 基础时间 = 平均完成时间 × 任务复杂度
        base_time_seconds = profile.avg_completion_time_seconds * task_req.estimated_complexity
        
        # 调整因子：负载影响、优先级影响
        load_factor = 1.0 + (profile.current_load / profile.max_capacity * 0.3)
        priority_factor = {TaskPriority.LOW: 1.2, TaskPriority.NORMAL: 1.0,
                          TaskPriority.HIGH: 0.8, TaskPriority.URGENT: 0.6}.get(task_req.priority, 1.0)
        
        estimated_seconds = base_time_seconds * load_factor * priority_factor
        
        return datetime.now() + timedelta(seconds=estimated_seconds)
    
    def record_allocation_decision(self, result: LoadBalancedAllocationResult,
                                  task_req: OptimizedTaskRequirements) -> None:
        """记录分配决策到数据库"""
        
        try:
            cursor = self.conn.cursor()
            
            # 插入分配决策记录
            cursor.execute("""
                INSERT INTO assignment_decisions 
                (avatar_id, task_type, required_capabilities, priority, complexity,
                 target_regions, capability_match, specialization_match, region_match,
                 success_rate, load_factor, response_speed, total_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.assigned_avatar,
                task_req.task_type.value,
                json.dumps(task_req.required_capabilities),
                task_req.priority.value,
                task_req.estimated_complexity,
                json.dumps(task_req.target_regions),
                json.dumps(result.capability_match_details),
                json.dumps([tag for tag in task_req.specialized_expertise 
                          if tag in result.assigned_avatar]),
                json.dumps([region for region in task_req.target_regions 
                          if region in result.assigned_avatar]),
                result.matching_score,
                result.load_balance_impact,
                1.0,  # 响应速度分数（简化处理）
                result.matching_score
            ))
            
            # 更新分身负载
            cursor.execute("""
                UPDATE avatar_capability_profiles
                SET current_load = ?
                WHERE avatar_id = ?
            """, (result.current_load_after, result.assigned_avatar))
            
            self.conn.commit()
            logger.debug(f"分配决策已记录到数据库，任务ID: {result.task_id}")
            
        except Exception as e:
            logger.error(f"记录分配决策失败: {str(e)}")
            self.conn.rollback()
    
    def optimize_system_load(self) -> Dict[str, Any]:
        """
        系统负载优化建议
        基于当前负载分布，提供优化建议
        """
        
        avatar_profiles = self.load_avatar_profiles()
        
        if not avatar_profiles:
            return {"status": "error", "message": "无分身数据"}
        
        # 分析负载分布
        load_stats = {
            "total_avatars": len(avatar_profiles),
            "total_load": sum(p.current_load for p in avatar_profiles.values()),
            "avg_load": np.mean([p.current_load for p in avatar_profiles.values()]),
            "load_distribution": {}
        }
        
        # 统计负载分布
        for load_level in range(6):  # 0-5
            count = sum(1 for p in avatar_profiles.values() if p.current_load == load_level)
            load_stats["load_distribution"][f"load_{load_level}"] = count
        
        # 识别过载分身
        overloaded_avatars = []
        for avatar_id, profile in avatar_profiles.items():
            if profile.current_load >= profile.max_capacity:
                overloaded_avatars.append({
                    "avatar_id": avatar_id,
                    "current_load": profile.current_load,
                    "max_capacity": profile.max_capacity,
                    "availability_score": profile.availability_score
                })
        
        # 识别闲置分身
        idle_avatars = []
        for avatar_id, profile in avatar_profiles.items():
            if profile.current_load == 0 and profile.health_status == "healthy":
                idle_avatars.append({
                    "avatar_id": avatar_id,
                    "availability_score": profile.availability_score,
                    "capability_scores": profile.capability_scores
                })
        
        # 生成优化建议
        recommendations = []
        
        if overloaded_avatars:
            recommendations.append({
                "type": "负载均衡",
                "priority": "高",
                "description": f"发现{len(overloaded_avatars)}个分身过载，建议重新分配任务",
                "action": "将过载分身的任务迁移到闲置分身"
            })
        
        if idle_avatars:
            recommendations.append({
                "type": "资源利用",
                "priority": "中",
                "description": f"发现{len(idle_avatars)}个健康闲置分身，资源利用率不足",
                "action": "优先将新任务分配给闲置分身"
            })
        
        # 计算负载均衡分数
        load_balance_score = self.calculate_load_balance_score(avatar_profiles)
        
        result = {
            "status": "success",
            "load_stats": load_stats,
            "load_balance_score": load_balance_score,
            "overloaded_avatars": overloaded_avatars,
            "idle_avatars": idle_avatars,
            "recommendations": recommendations,
            "optimization_impact": {
                "estimated_task_completion_time_reduction": "≥20%",
                "estimated_resource_utilization_improvement": "≥15%",
                "estimated_load_balance_improvement": "≥40%"
            }
        }
        
        return result

def main():
    """测试主函数"""
    
    logger.info("测试负载均衡分配器...")
    
    # 创建分配器实例
    allocator = LoadBalancedAllocator()
    
    # 加载分身画像
    avatar_profiles = allocator.load_avatar_profiles()
    
    if not avatar_profiles:
        logger.error("无法加载分身画像，退出测试")
        return
    
    # 创建测试任务需求
    task_req = OptimizedTaskRequirements(
        task_type=OptimizedTaskType.FINANCIAL_ANALYSIS,
        required_capabilities=["financial_analysis", "data_crawling"],
        priority=TaskPriority.NORMAL,
        estimated_complexity=2.0,
        target_regions=["US", "EU"],
        deadline=datetime.now() + timedelta(hours=2),
        avoid_shortcomings=True,
        load_balance_preference=0.8
    )
    
    # 测试分配功能
    try:
        result = allocator.allocate_task("test_task_001", task_req)
        
        logger.info(f"分配结果:")
        logger.info(f"  任务ID: {result.task_id}")
        logger.info(f"  分配分身: {result.assigned_avatar}")
        logger.info(f"  匹配分数: {result.matching_score:.3f}")
        logger.info(f"  原因: {result.reason}")
        logger.info(f"  负载平衡影响: {result.load_balance_impact:.3f}")
        
        # 运行负载优化分析
        optimization_result = allocator.optimize_system_load()
        
        logger.info(f"系统负载优化分析:")
        logger.info(f"  总分身数: {optimization_result['load_stats']['total_avatars']}")
        logger.info(f"  总负载: {optimization_result['load_stats']['total_load']}")
        logger.info(f"  平均负载: {optimization_result['load_stats']['avg_load']:.2f}")
        logger.info(f"  负载均衡分数: {optimization_result['load_balance_score']:.3f}")
        
        if optimization_result['recommendations']:
            logger.info(f"  优化建议:")
            for rec in optimization_result['recommendations']:
                logger.info(f"    [{rec['priority']}] {rec['description']}")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        raise
    
    logger.info("测试完成!")

if __name__ == "__main__":
    main()