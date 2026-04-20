#!/usr/bin/env python3
"""
反馈优化器
实现脚本效果的闭环优化，基于实际播放数据优化生成算法
建立效果数据库，支持进化式生成
"""

import json
import logging
import time
import uuid
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
from collections import defaultdict
import statistics

from .script_generator import VideoScript

logger = logging.getLogger(__name__)

class PerformanceMetric(str, Enum):
    """性能指标枚举"""
    VIEWS = "views"                 # 观看次数
    ENGAGEMENT_RATE = "engagement_rate"  # 互动率
    COMPLETION_RATE = "completion_rate"  # 完播率
    CTR = "ctr"                     # 点击率
    CONVERSION_RATE = "conversion_rate"  # 转化率
    RETENTION_SCORE = "retention_score"  # 留存得分

@dataclass
class PerformanceData:
    """性能数据"""
    script_id: str
    timestamp: datetime
    metric: PerformanceMetric
    value: float
    platform: str
    audience_segment: str
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OptimizationSuggestion:
    """优化建议"""
    suggestion_id: str
    script_id: str
    issue_type: str
    severity: str  # low, medium, high
    description: str
    suggested_changes: List[Dict[str, Any]]
    confidence_score: float  # 0-1
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class AlgorithmParameter:
    """算法参数"""
    parameter_name: str
    current_value: float
    optimal_range: Tuple[float, float]
    adjustment_step: float
    last_adjusted: datetime

class FeedbackOptimizer:
    """反馈优化器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化反馈优化器
        
        Args:
            db_path: 数据库路径，可选
        """
        if db_path is None:
            # 默认数据库路径
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, 'data', 'feedback')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'performance.db')
        
        self.db_path = db_path
        self._init_database()
        
        # 算法参数管理
        self.algorithm_parameters = self._load_algorithm_parameters()
        
        # 性能基准
        self.performance_baselines = self._load_performance_baselines()
        
        logger.info(f"反馈优化器初始化完成，数据库：{db_path}")
    
    def record_generation(self, script: VideoScript):
        """
        记录脚本生成
        
        Args:
            script: 生成的脚本
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 记录脚本基本信息
            cursor.execute('''
                INSERT OR REPLACE INTO script_generations 
                (script_id, title, script_type, language, profit_margin, commercial_score, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                script.script_id,
                script.title,
                script.script_type.value,
                script.language.value,
                script.profit_margin,
                script.calculate_commercial_score(),
                script.generated_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"记录脚本生成：{script.script_id}")
            
        except Exception as e:
            logger.error(f"记录脚本生成失败：{e}")
    
    def record_performance(self, 
                          script_id: str,
                          metric: PerformanceMetric,
                          value: float,
                          platform: str,
                          audience_segment: str,
                          context: Optional[Dict[str, Any]] = None):
        """
        记录性能数据
        
        Args:
            script_id: 脚本ID
            metric: 性能指标
            value: 指标值
            platform: 平台
            audience_segment: 受众细分
            context: 上下文信息，可选
        """
        try:
            performance_data = PerformanceData(
                script_id=script_id,
                timestamp=datetime.now(),
                metric=metric,
                value=value,
                platform=platform,
                audience_segment=audience_segment,
                context=context or {}
            )
            
            self._save_performance_data(performance_data)
            
            logger.info(f"记录性能数据：{script_id} - {metric.value}: {value}")
            
            # 检查是否需要触发优化
            self._check_for_optimization(performance_data)
            
        except Exception as e:
            logger.error(f"记录性能数据失败：{e}")
    
    def analyze_feedback(self,
                        script: VideoScript,
                        feedback_data: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """
        分析反馈数据，生成优化建议
        
        Args:
            script: 脚本
            feedback_data: 反馈数据
            
        Returns:
            List[OptimizationSuggestion]: 优化建议列表
        """
        logger.info(f"分析反馈数据，脚本：{script.script_id}")
        
        suggestions = []
        
        # 分析观看数据
        if 'views' in feedback_data:
            view_analysis = self._analyze_view_performance(script, feedback_data['views'])
            if view_analysis:
                suggestions.extend(view_analysis)
        
        # 分析互动数据
        if 'engagement' in feedback_data:
            engagement_analysis = self._analyze_engagement_performance(script, feedback_data['engagement'])
            if engagement_analysis:
                suggestions.extend(engagement_analysis)
        
        # 分析转化数据
        if 'conversions' in feedback_data:
            conversion_analysis = self._analyze_conversion_performance(script, feedback_data['conversions'])
            if conversion_analysis:
                suggestions.extend(conversion_analysis)
        
        # 分析留存数据
        if 'retention' in feedback_data:
            retention_analysis = self._analyze_retention_performance(script, feedback_data['retention'])
            if retention_analysis:
                suggestions.extend(retention_analysis)
        
        # 如果没有具体问题，提供一般优化建议
        if not suggestions:
            general_suggestions = self._generate_general_suggestions(script)
            suggestions.extend(general_suggestions)
        
        # 保存建议到数据库
        for suggestion in suggestions:
            self._save_optimization_suggestion(suggestion)
        
        return suggestions
    
    def record_optimization(self,
                           original_script: VideoScript,
                           optimized_script: VideoScript,
                           feedback_data: Dict[str, Any]):
        """
        记录优化过程
        
        Args:
            original_script: 原始脚本
            optimized_script: 优化后的脚本
            feedback_data: 反馈数据
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 记录优化历史
            cursor.execute('''
                INSERT INTO optimization_history 
                (optimization_id, original_script_id, optimized_script_id, 
                 feedback_summary, original_score, optimized_score, optimized_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                original_script.script_id,
                optimized_script.script_id,
                json.dumps(feedback_data),
                original_script.calculate_commercial_score(),
                optimized_script.calculate_commercial_score(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"记录优化过程：{original_script.script_id} -> {optimized_script.script_id}")
            
        except Exception as e:
            logger.error(f"记录优化过程失败：{e}")
    
    def get_performance_trends(self,
                              script_type: Optional[str] = None,
                              platform: Optional[str] = None,
                              days_back: int = 30) -> Dict[str, Any]:
        """
        获取性能趋势
        
        Args:
            script_type: 脚本类型过滤
            platform: 平台过滤
            days_back: 回溯天数
            
        Returns:
            Dict[str, Any]: 趋势数据
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            start_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            conditions.append("timestamp >= ?")
            params.append(start_date)
            
            if script_type:
                conditions.append("script_id IN (SELECT script_id FROM script_generations WHERE script_type = ?)")
                params.append(script_type)
            
            if platform:
                conditions.append("platform = ?")
                params.append(platform)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 查询性能数据
            cursor.execute(f'''
                SELECT metric, AVG(value), COUNT(*)
                FROM performance_data
                WHERE {where_clause}
                GROUP BY metric
            ''', params)
            
            trends = {}
            for metric, avg_value, count in cursor.fetchall():
                trends[metric] = {
                    'average': avg_value,
                    'sample_count': count,
                    'trend_direction': self._calculate_trend_direction(metric, avg_value)
                }
            
            conn.close()
            
            return trends
            
        except Exception as e:
            logger.error(f"获取性能趋势失败：{e}")
            return {}
    
    def adjust_algorithm_parameters(self,
                                   parameter_name: str,
                                   adjustment_direction: str,  # 'increase' or 'decrease'
                                   adjustment_factor: float = 1.0):
        """
        调整算法参数
        
        Args:
            parameter_name: 参数名称
            adjustment_direction: 调整方向
            adjustment_factor: 调整因子
            
        Returns:
            bool: 调整是否成功
        """
        if parameter_name not in self.algorithm_parameters:
            logger.error(f"参数不存在：{parameter_name}")
            return False
        
        parameter = self.algorithm_parameters[parameter_name]
        
        # 计算调整量
        adjustment = parameter.adjustment_step * adjustment_factor
        
        if adjustment_direction == 'increase':
            new_value = parameter.current_value + adjustment
        elif adjustment_direction == 'decrease':
            new_value = parameter.current_value - adjustment
        else:
            logger.error(f"无效的调整方向：{adjustment_direction}")
            return False
        
        # 确保在最优范围内
        optimal_min, optimal_max = parameter.optimal_range
        new_value = max(optimal_min, min(optimal_max, new_value))
        
        # 更新参数
        parameter.current_value = new_value
        parameter.last_adjusted = datetime.now()
        
        # 保存到数据库
        self._save_algorithm_parameter(parameter)
        
        logger.info(f"调整算法参数：{parameter_name} -> {new_value:.3f}")
        return True
    
    def get_optimization_history(self,
                                script_id: Optional[str] = None,
                                limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取优化历史
        
        Args:
            script_id: 脚本ID过滤
            limit: 返回记录限制
            
        Returns:
            List[Dict[str, Any]]: 优化历史记录
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if script_id:
                cursor.execute('''
                    SELECT * FROM optimization_history
                    WHERE original_script_id = ? OR optimized_script_id = ?
                    ORDER BY optimized_at DESC
                    LIMIT ?
                ''', (script_id, script_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM optimization_history
                    ORDER BY optimized_at DESC
                    LIMIT ?
                ''', (limit,))
            
            columns = [description[0] for description in cursor.description]
            records = []
            
            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                # 解析JSON字段
                if 'feedback_summary' in record and record['feedback_summary']:
                    try:
                        record['feedback_summary'] = json.loads(record['feedback_summary'])
                    except:
                        pass
                records.append(record)
            
            conn.close()
            return records
            
        except Exception as e:
            logger.error(f"获取优化历史失败：{e}")
            return []
    
    def _init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建脚本生成记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS script_generations (
                    script_id TEXT PRIMARY KEY,
                    title TEXT,
                    script_type TEXT,
                    language TEXT,
                    profit_margin REAL,
                    commercial_score REAL,
                    generated_at TEXT
                )
            ''')
            
            # 创建性能数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    script_id TEXT,
                    timestamp TEXT,
                    metric TEXT,
                    value REAL,
                    platform TEXT,
                    audience_segment TEXT,
                    context TEXT,
                    FOREIGN KEY (script_id) REFERENCES script_generations (script_id)
                )
            ''')
            
            # 创建优化建议表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_suggestions (
                    suggestion_id TEXT PRIMARY KEY,
                    script_id TEXT,
                    issue_type TEXT,
                    severity TEXT,
                    description TEXT,
                    suggested_changes TEXT,
                    confidence_score REAL,
                    generated_at TEXT,
                    FOREIGN KEY (script_id) REFERENCES script_generations (script_id)
                )
            ''')
            
            # 创建优化历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_history (
                    optimization_id TEXT PRIMARY KEY,
                    original_script_id TEXT,
                    optimized_script_id TEXT,
                    feedback_summary TEXT,
                    original_score REAL,
                    optimized_score REAL,
                    optimized_at TEXT,
                    FOREIGN KEY (original_script_id) REFERENCES script_generations (script_id),
                    FOREIGN KEY (optimized_script_id) REFERENCES script_generations (script_id)
                )
            ''')
            
            # 创建算法参数表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS algorithm_parameters (
                    parameter_name TEXT PRIMARY KEY,
                    current_value REAL,
                    optimal_min REAL,
                    optimal_max REAL,
                    adjustment_step REAL,
                    last_adjusted TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败：{e}")
    
    def _load_algorithm_parameters(self) -> Dict[str, AlgorithmParameter]:
        """加载算法参数"""
        parameters = {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM algorithm_parameters')
            
            for row in cursor.fetchall():
                param_name, current_value, optimal_min, optimal_max, adjustment_step, last_adj = row
                
                parameter = AlgorithmParameter(
                    parameter_name=param_name,
                    current_value=current_value,
                    optimal_range=(optimal_min, optimal_max),
                    adjustment_step=adjustment_step,
                    last_adjusted=datetime.fromisoformat(last_adj) if last_adj else datetime.now()
                )
                
                parameters[param_name] = parameter
            
            conn.close()
            
        except Exception as e:
            logger.error(f"加载算法参数失败：{e}")
        
        # 如果数据库为空，创建默认参数
        if not parameters:
            parameters = self._create_default_parameters()
        
        return parameters
    
    def _load_performance_baselines(self) -> Dict[str, Dict[str, float]]:
        """加载性能基准"""
        baselines = {
            'views': {
                'poor': 1000,
                'average': 5000,
                'good': 20000,
                'excellent': 100000
            },
            'engagement_rate': {
                'poor': 0.01,
                'average': 0.03,
                'good': 0.05,
                'excellent': 0.10
            },
            'completion_rate': {
                'poor': 0.20,
                'average': 0.40,
                'good': 0.60,
                'excellent': 0.80
            },
            'ctr': {
                'poor': 0.001,
                'average': 0.005,
                'good': 0.01,
                'excellent': 0.03
            },
            'conversion_rate': {
                'poor': 0.001,
                'average': 0.005,
                'good': 0.01,
                'excellent': 0.03
            }
        }
        
        return baselines
    
    def _create_default_parameters(self) -> Dict[str, AlgorithmParameter]:
        """创建默认算法参数"""
        parameters = {
            'creativity_weight': AlgorithmParameter(
                parameter_name='creativity_weight',
                current_value=0.7,
                optimal_range=(0.3, 0.9),
                adjustment_step=0.05,
                last_adjusted=datetime.now()
            ),
            'commercial_focus': AlgorithmParameter(
                parameter_name='commercial_focus',
                current_value=0.8,
                optimal_range=(0.5, 0.95),
                adjustment_step=0.05,
                last_adjusted=datetime.now()
            ),
            'cultural_adaptation': AlgorithmParameter(
                parameter_name='cultural_adaptation',
                current_value=0.6,
                optimal_range=(0.4, 0.8),
                adjustment_step=0.05,
                last_adjusted=datetime.now()
            ),
            'duration_preference': AlgorithmParameter(
                parameter_name='duration_preference',
                current_value=0.5,
                optimal_range=(0.3, 0.7),
                adjustment_step=0.05,
                last_adjusted=datetime.now()
            )
        }
        
        # 保存到数据库
        for param in parameters.values():
            self._save_algorithm_parameter(param)
        
        return parameters
    
    def _save_performance_data(self, data: PerformanceData):
        """保存性能数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_data 
                (script_id, timestamp, metric, value, platform, audience_segment, context)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.script_id,
                data.timestamp.isoformat(),
                data.metric.value,
                data.value,
                data.platform,
                data.audience_segment,
                json.dumps(data.context)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存性能数据失败：{e}")
    
    def _save_optimization_suggestion(self, suggestion: OptimizationSuggestion):
        """保存优化建议"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO optimization_suggestions 
                (suggestion_id, script_id, issue_type, severity, description, 
                 suggested_changes, confidence_score, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                suggestion.suggestion_id,
                suggestion.script_id,
                suggestion.issue_type,
                suggestion.severity,
                suggestion.description,
                json.dumps(suggestion.suggested_changes),
                suggestion.confidence_score,
                suggestion.generated_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存优化建议失败：{e}")
    
    def _save_algorithm_parameter(self, parameter: AlgorithmParameter):
        """保存算法参数"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO algorithm_parameters 
                (parameter_name, current_value, optimal_min, optimal_max, adjustment_step, last_adjusted)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                parameter.parameter_name,
                parameter.current_value,
                parameter.optimal_range[0],
                parameter.optimal_range[1],
                parameter.adjustment_step,
                parameter.last_adjusted.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存算法参数失败：{e}")
    
    def _check_for_optimization(self, performance_data: PerformanceData):
        """检查是否需要触发优化"""
        metric = performance_data.metric.value
        value = performance_data.value
        
        # 获取基准值
        baselines = self.performance_baselines.get(metric, {})
        
        if not baselines:
            return
        
        # 检查是否低于平均水平
        average_baseline = baselines.get('average', 0)
        
        if value < average_baseline * 0.7:  # 低于平均70%
            logger.info(f"检测到性能问题：{metric} = {value}，低于基准")
            
            # 记录优化需求
            suggestion = OptimizationSuggestion(
                suggestion_id=str(uuid.uuid4()),
                script_id=performance_data.script_id,
                issue_type=f"low_{metric}",
                severity="medium",
                description=f"性能指标{metric}低于预期，当前值：{value}，基准值：{average_baseline}",
                suggested_changes=[
                    {
                        "type": "parameter_adjustment",
                        "parameter": f"{metric}_weight",
                        "adjustment": "increase"
                    }
                ],
                confidence_score=0.7
            )
            
            self._save_optimization_suggestion(suggestion)
    
    def _analyze_view_performance(self,
                                 script: VideoScript,
                                 view_data: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """分析观看性能"""
        suggestions = []
        
        # 获取观看次数
        views = view_data.get('count', 0)
        
        # 判断表现
        baselines = self.performance_baselines.get('views', {})
        average_baseline = baselines.get('average', 5000)
        
        if views < average_baseline * 0.5:
            # 观看次数低于平均50%
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    script_id=script.script_id,
                    issue_type="low_views",
                    severity="high",
                    description=f"视频观看次数较低：{views}次，低于预期",
                    suggested_changes=[
                        {
                            "type": "title_improvement",
                            "description": "优化标题吸引力",
                            "examples": ["添加情感词汇", "突出核心卖点", "使用数字吸引注意力"]
                        },
                        {
                            "type": "thumbnail_suggestion",
                            "description": "改进缩略图设计",
                            "examples": ["使用高对比度颜色", "添加文字叠加", "突出产品主体"]
                        }
                    ],
                    confidence_score=0.8
                )
            )
        
        return suggestions
    
    def _analyze_engagement_performance(self,
                                       script: VideoScript,
                                       engagement_data: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """分析互动性能"""
        suggestions = []
        
        # 获取互动率
        engagement_rate = engagement_data.get('rate', 0)
        
        # 判断表现
        baselines = self.performance_baselines.get('engagement_rate', {})
        average_baseline = baselines.get('average', 0.03)
        
        if engagement_rate < average_baseline * 0.7:
            # 互动率低于平均70%
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    script_id=script.script_id,
                    issue_type="low_engagement",
                    severity="medium",
                    description=f"视频互动率较低：{engagement_rate:.2%}，建议优化",
                    suggested_changes=[
                        {
                            "type": "content_improvement",
                            "description": "增加互动元素",
                            "examples": ["添加提问环节", "使用投票功能", "鼓励用户评论"]
                        },
                        {
                            "type": "pacing_adjustment",
                            "description": "调整视频节奏",
                            "examples": ["加快前5秒节奏", "添加悬念元素", "优化信息密度"]
                        }
                    ],
                    confidence_score=0.75
                )
            )
        
        return suggestions
    
    def _analyze_conversion_performance(self,
                                       script: VideoScript,
                                       conversion_data: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """分析转化性能"""
        suggestions = []
        
        # 获取转化率
        conversion_rate = conversion_data.get('rate', 0)
        
        # 判断表现
        baselines = self.performance_baselines.get('conversion_rate', {})
        average_baseline = baselines.get('average', 0.005)
        
        if conversion_rate < average_baseline * 0.5:
            # 转化率低于平均50%
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    script_id=script.script_id,
                    issue_type="low_conversion",
                    severity="high",
                    description=f"视频转化率较低：{conversion_rate:.2%}，需重点优化",
                    suggested_changes=[
                        {
                            "type": "cta_improvement",
                            "description": "优化行动号召",
                            "examples": ["明确价值主张", "增加紧迫感", "简化转化路径"]
                        },
                        {
                            "type": "trust_elements",
                            "description": "增加信任元素",
                            "examples": ["添加用户评价", "展示使用场景", "提供质量保证"]
                        }
                    ],
                    confidence_score=0.85
                )
            )
        
        return suggestions
    
    def _analyze_retention_performance(self,
                                      script: VideoScript,
                                      retention_data: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """分析留存性能"""
        suggestions = []
        
        # 获取完播率
        completion_rate = retention_data.get('completion_rate', 0)
        
        # 判断表现
        baselines = self.performance_baselines.get('completion_rate', {})
        average_baseline = baselines.get('average', 0.4)
        
        if completion_rate < average_baseline * 0.6:
            # 完播率低于平均60%
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    script_id=script.script_id,
                    issue_type="low_retention",
                    severity="medium",
                    description=f"视频完播率较低：{completion_rate:.2%}，建议优化内容结构",
                    suggested_changes=[
                        {
                            "type": "duration_adjustment",
                            "description": "调整视频时长",
                            "examples": ["缩短至30秒以内", "优化信息节奏", "减少冗长内容"]
                        },
                        {
                            "type": "hook_improvement",
                            "description": "优化开场钩子",
                            "examples": ["前3秒展示核心价值", "使用强烈视觉冲击", "提出吸引人的问题"]
                        }
                    ],
                    confidence_score=0.7
                )
            )
        
        return suggestions
    
    def _generate_general_suggestions(self, script: VideoScript) -> List[OptimizationSuggestion]:
        """生成一般优化建议"""
        suggestions = []
        
        # 基于脚本特征的优化建议
        if len(script.keywords) < 5:
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    script_id=script.script_id,
                    issue_type="keyword_richness",
                    severity="low",
                    description="关键词数量较少，可能影响搜索曝光",
                    suggested_changes=[
                        {
                            "type": "keyword_expansion",
                            "description": "扩展相关关键词",
                            "examples": ["添加长尾关键词", "包含场景词汇", "加入情感词汇"]
                        }
                    ],
                    confidence_score=0.6
                )
            )
        
        if script.duration_seconds > 90:
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    script_id=script.script_id,
                    issue_type="duration_optimization",
                    severity="low",
                    description="视频时长较长，可能影响完播率",
                    suggested_changes=[
                        {
                            "type": "duration_reduction",
                            "description": "考虑缩短至60秒以内",
                            "examples": ["提炼核心信息", "加快节奏", "分段处理"]
                        }
                    ],
                    confidence_score=0.65
                )
            )
        
        return suggestions
    
    def _calculate_trend_direction(self, metric: str, current_avg: float) -> str:
        """计算趋势方向"""
        # 简化实现
        baselines = self.performance_baselines.get(metric, {})
        average_baseline = baselines.get('average', 0)
        
        if current_avg > average_baseline * 1.2:
            return "improving"
        elif current_avg > average_baseline * 0.8:
            return "stable"
        else:
            return "declining"