"""
短视频引流军团 - 效果追踪系统
实时监控视频引流效果：点击率、转化率、ROI等关键指标
集成智能优化模块，基于效果数据自动调整视频内容和分发策略
与Memory V2认证记忆系统深度集成，确保所有效果数据100%准确归档
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import statistics
from collections import defaultdict

# 导入现有系统模块
try:
    from src.shared_state_manager import SharedStateManager
    from src.memory_v2_indexer import MemoryV2Indexer
    SHARED_STATE_AVAILABLE = True
except ImportError:
    SHARED_STATE_AVAILABLE = False
    print("警告: 共享状态模块不可用，使用模拟模式")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceMetric:
    """性能指标基类"""
    
    def __init__(self, metric_name: str, metric_type: str):
        self.metric_name = metric_name
        self.metric_type = metric_type  # 'count', 'rate', 'value', 'percentage'
        self.data_points = []
        self.timestamps = []
        
    def add_data_point(self, value: float, timestamp: Optional[datetime] = None):
        """添加数据点"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.data_points.append(value)
        self.timestamps.append(timestamp)
        
        # 保持最近1000个数据点
        if len(self.data_points) > 1000:
            self.data_points = self.data_points[-1000:]
            self.timestamps = self.timestamps[-1000:]
    
    def get_current_value(self) -> Optional[float]:
        """获取当前值"""
        if not self.data_points:
            return None
        return self.data_points[-1]
    
    def get_average(self, window: Optional[int] = None) -> Optional[float]:
        """获取平均值"""
        if not self.data_points:
            return None
        
        if window is None or window >= len(self.data_points):
            return statistics.mean(self.data_points)
        else:
            return statistics.mean(self.data_points[-window:])
    
    def get_trend(self, window: int = 10) -> Optional[float]:
        """获取趋势（最近window个点的斜率）"""
        if len(self.data_points) < window:
            return None
        
        recent_points = self.data_points[-window:]
        
        # 简单线性回归计算斜率
        x = list(range(len(recent_points)))
        y = recent_points
        
        n = len(x)
        if n == 0:
            return None
            
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = n * sum_x2 - sum_x * sum_x
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope

class VideoPerformanceTracker:
    """视频性能追踪器"""
    
    def __init__(self):
        self.metrics = {}
        self.video_records = {}
        self.campaign_records = {}
        self.optimization_rules = {}
        
        # 初始化基础指标
        self._initialize_metrics()
        
        # 连接共享状态和记忆系统
        if SHARED_STATE_AVAILABLE:
            self.shared_state = SharedStateManager()
            self.memory_indexer = MemoryV2Indexer()
        else:
            self.shared_state = None
            self.memory_indexer = None
        
        # 加载优化规则
        self._load_optimization_rules()
        
        logger.info("视频性能追踪器初始化完成")
    
    def _initialize_metrics(self):
        """初始化基础性能指标"""
        base_metrics = {
            "views": PerformanceMetric("views", "count"),
            "likes": PerformanceMetric("likes", "count"),
            "comments": PerformanceMetric("comments", "count"),
            "shares": PerformanceMetric("shares", "count"),
            "clicks": PerformanceMetric("clicks", "count"),
            "conversions": PerformanceMetric("conversions", "count"),
            "revenue": PerformanceMetric("revenue", "value"),
            "cost": PerformanceMetric("cost", "value"),
        }
        
        derived_metrics = {
            "engagement_rate": PerformanceMetric("engagement_rate", "percentage"),
            "click_through_rate": PerformanceMetric("click_through_rate", "percentage"),
            "conversion_rate": PerformanceMetric("conversion_rate", "percentage"),
            "roi": PerformanceMetric("roi", "percentage"),
            "cac": PerformanceMetric("cac", "value"),  # Customer Acquisition Cost
            "lifetime_value": PerformanceMetric("lifetime_value", "value"),
        }
        
        self.metrics.update(base_metrics)
        self.metrics.update(derived_metrics)
    
    def _load_optimization_rules(self):
        """加载智能优化规则"""
        self.optimization_rules = {
            "engagement_optimization": {
                "low_engagement_threshold": 3.0,  # 低于3%的互动率为低
                "actions": [
                    "increase_call_to_action_frequency",
                    "add_interactive_elements",
                    "optimize_video_hook_first_3s",
                    "test_different_music_tracks"
                ],
                "priority": "high"
            },
            "ctr_optimization": {
                "low_ctr_threshold": 1.5,  # 低于1.5%的点击率为低
                "actions": [
                    "improve_thumbnail_design",
                    "optimize_video_title",
                    "add_urgency_to_call_to_action",
                    "test_different_video_intros"
                ],
                "priority": "high"
            },
            "conversion_optimization": {
                "low_conversion_threshold": 0.5,  # 低于0.5%的转化率为低
                "actions": [
                    "optimize_landing_page_load_time",
                    "simplify_checkout_process",
                    "add_trust_signals_to_product_page",
                    "test_different_pricing_strategies"
                ],
                "priority": "medium"
            },
            "roi_optimization": {
                "low_roi_threshold": 100.0,  # 低于100%的ROI为低
                "actions": [
                    "optimize_targeting_audience",
                    "reduce_production_costs",
                    "increase_average_order_value",
                    "test_different_product_bundles"
                ],
                "priority": "high"
            },
            "content_optimization": {
                "performance_variance_threshold": 30.0,  # 同一产品不同视频效果差异超过30%
                "actions": [
                    "analyze_top_performing_video_elements",
                    "replicate_successful_content_patterns",
                    "test_content_variations_methodically",
                    "optimize_based_on_platform_specific_insights"
                ],
                "priority": "medium"
            }
        }
    
    def record_video_performance(self, 
                                video_id: str,
                                platform: str,
                                metrics: Dict[str, float],
                                timestamp: Optional[datetime] = None):
        """
        记录视频性能数据
        
        Args:
            video_id: 视频ID
            platform: 平台名称
            metrics: 指标字典
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 创建或更新视频记录
        if video_id not in self.video_records:
            self.video_records[video_id] = {
                "video_id": video_id,
                "platform": platform,
                "created_at": timestamp.isoformat(),
                "performance_history": [],
                "current_metrics": {},
                "optimization_history": []
            }
        
        # 更新当前指标
        self.video_records[video_id]["current_metrics"] = metrics
        self.video_records[video_id]["performance_history"].append({
            "timestamp": timestamp.isoformat(),
            "metrics": metrics
        })
        
        # 更新全局指标
        for metric_name, value in metrics.items():
            if metric_name in self.metrics:
                self.metrics[metric_name].add_data_point(value, timestamp)
        
        # 计算派生指标
        self._calculate_derived_metrics(video_id, metrics, timestamp)
        
        # 保存到记忆系统
        self._save_performance_to_memory(video_id, platform, metrics, timestamp)
        
        logger.info(f"记录视频性能数据: {video_id}@{platform} - {metrics}")
    
    def _calculate_derived_metrics(self, 
                                  video_id: str,
                                  metrics: Dict[str, float],
                                  timestamp: datetime):
        """计算派生性能指标"""
        
        # 互动率 = (点赞+评论+分享) / 观看次数
        views = metrics.get("views", 0)
        if views > 0:
            engagement = (metrics.get("likes", 0) + 
                         metrics.get("comments", 0) + 
                         metrics.get("shares", 0))
            engagement_rate = (engagement / views) * 100
            self.metrics["engagement_rate"].add_data_point(engagement_rate, timestamp)
            
            # 更新视频记录
            if video_id in self.video_records:
                self.video_records[video_id]["current_metrics"]["engagement_rate"] = engagement_rate
        
        # 点击率 = 点击次数 / 观看次数
        clicks = metrics.get("clicks", 0)
        if views > 0:
            ctr = (clicks / views) * 100
            self.metrics["click_through_rate"].add_data_point(ctr, timestamp)
            
            if video_id in self.video_records:
                self.video_records[video_id]["current_metrics"]["click_through_rate"] = ctr
        
        # 转化率 = 转化次数 / 点击次数
        conversions = metrics.get("conversions", 0)
        if clicks > 0:
            conversion_rate = (conversions / clicks) * 100
            self.metrics["conversion_rate"].add_data_point(conversion_rate, timestamp)
            
            if video_id in self.video_records:
                self.video_records[video_id]["current_metrics"]["conversion_rate"] = conversion_rate
        
        # ROI = (收入 - 成本) / 成本 * 100
        revenue = metrics.get("revenue", 0)
        cost = metrics.get("cost", 0)
        if cost > 0:
            roi = ((revenue - cost) / cost) * 100
            self.metrics["roi"].add_data_point(roi, timestamp)
            
            if video_id in self.video_records:
                self.video_records[video_id]["current_metrics"]["roi"] = roi
        
        # 客户获取成本 = 成本 / 转化次数
        if conversions > 0:
            cac = cost / conversions
            self.metrics["cac"].add_data_point(cac, timestamp)
            
            if video_id in self.video_records:
                self.video_records[video_id]["current_metrics"]["cac"] = cac
    
    def _save_performance_to_memory(self,
                                   video_id: str,
                                   platform: str,
                                   metrics: Dict[str, float],
                                   timestamp: datetime):
        """保存性能数据到Memory V2认证记忆系统"""
        if not self.memory_indexer:
            return
        
        memory_data = {
            "video_id": video_id,
            "platform": platform,
            "metrics": metrics,
            "timestamp": timestamp.isoformat(),
            "derived_metrics": {
                "engagement_rate": self.metrics["engagement_rate"].get_current_value(),
                "click_through_rate": self.metrics["click_through_rate"].get_current_value(),
                "conversion_rate": self.metrics["conversion_rate"].get_current_value(),
                "roi": self.metrics["roi"].get_current_value(),
                "cac": self.metrics["cac"].get_current_value()
            }
        }
        
        try:
            success = self.memory_indexer.index_memory(
                memory_data,
                category="video_performance",
                tags=["performance_tracking", platform, video_id[:8]]
            )
            
            if success:
                logger.debug(f"性能数据已保存到Memory V2: {video_id}")
            else:
                logger.warning(f"性能数据保存到Memory V2失败: {video_id}")
                
        except Exception as e:
            logger.error(f"保存到Memory V2时出错: {e}")
    
    def analyze_performance(self, 
                           video_id: Optional[str] = None,
                           platform: Optional[str] = None,
                           time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        分析视频性能数据
        
        Args:
            video_id: 特定视频ID，None表示分析所有视频
            platform: 特定平台，None表示所有平台
            time_range: 时间范围，None表示所有时间
        
        Returns:
            性能分析报告
        """
        # 筛选视频记录
        filtered_records = []
        
        for record_id, record in self.video_records.items():
            # 视频ID筛选
            if video_id is not None and record_id != video_id:
                continue
            
            # 平台筛选
            if platform is not None and record["platform"] != platform:
                continue
            
            # 时间范围筛选
            if time_range is not None:
                record_time = datetime.fromisoformat(record["created_at"])
                start_time, end_time = time_range
                if not (start_time <= record_time <= end_time):
                    continue
            
            filtered_records.append(record)
        
        if not filtered_records:
            return {
                "status": "no_data",
                "message": "没有匹配的性能数据",
                "timestamp": datetime.now().isoformat()
            }
        
        # 计算总体统计
        total_videos = len(filtered_records)
        
        # 聚合指标
        aggregated_metrics = defaultdict(list)
        
        for record in filtered_records:
            for metric_name, value in record["current_metrics"].items():
                if isinstance(value, (int, float)):
                    aggregated_metrics[metric_name].append(value)
        
        # 计算统计量
        performance_stats = {}
        
        for metric_name, values in aggregated_metrics.items():
            if not values:
                continue
            
            performance_stats[metric_name] = {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0.0
            }
        
        # 识别表现最佳和最差的视频
        if "engagement_rate" in aggregated_metrics:
            engagement_values = aggregated_metrics["engagement_rate"]
            max_engagement = max(engagement_values)
            min_engagement = min(engagement_values)
            
            # 找到对应的视频
            top_video = None
            bottom_video = None
            
            for record in filtered_records:
                if record["current_metrics"].get("engagement_rate") == max_engagement:
                    top_video = record["video_id"]
                if record["current_metrics"].get("engagement_rate") == min_engagement:
                    bottom_video = record["video_id"]
            
            performance_stats["engagement_rate"]["top_video"] = top_video
            performance_stats["engagement_rate"]["bottom_video"] = bottom_video
        
        # 生成优化建议
        optimization_suggestions = self._generate_optimization_suggestions(filtered_records)
        
        # 编译报告
        report = {
            "status": "success",
            "analysis_summary": {
                "total_videos_analyzed": total_videos,
                "platform_breakdown": self._get_platform_breakdown(filtered_records),
                "time_range": {
                    "start": min(r["created_at"] for r in filtered_records),
                    "end": max(r["created_at"] for r in filtered_records)
                } if filtered_records else None
            },
            "performance_statistics": performance_stats,
            "optimization_suggestions": optimization_suggestions,
            "key_insights": self._extract_key_insights(filtered_records),
            "timestamp": datetime.now().isoformat()
        }
        
        return report
    
    def _get_platform_breakdown(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """获取平台细分统计"""
        breakdown = defaultdict(int)
        
        for record in records:
            platform = record.get("platform", "unknown")
            breakdown[platform] += 1
        
        return dict(breakdown)
    
    def _generate_optimization_suggestions(self, 
                                         records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成优化建议"""
        suggestions = []
        
        # 检查各项指标是否需要优化
        for record in records:
            video_id = record["video_id"]
            platform = record["platform"]
            metrics = record["current_metrics"]
            
            # 检查互动率
            engagement_rate = metrics.get("engagement_rate")
            if engagement_rate is not None:
                low_threshold = self.optimization_rules["engagement_optimization"]["low_engagement_threshold"]
                if engagement_rate < low_threshold:
                    suggestions.append({
                        "video_id": video_id,
                        "platform": platform,
                        "metric": "engagement_rate",
                        "current_value": engagement_rate,
                        "threshold": low_threshold,
                        "severity": "high",
                        "suggested_actions": self.optimization_rules["engagement_optimization"]["actions"],
                        "reason": f"互动率低于阈值 {low_threshold}%"
                    })
            
            # 检查点击率
            ctr = metrics.get("click_through_rate")
            if ctr is not None:
                low_threshold = self.optimization_rules["ctr_optimization"]["low_ctr_threshold"]
                if ctr < low_threshold:
                    suggestions.append({
                        "video_id": video_id,
                        "platform": platform,
                        "metric": "click_through_rate",
                        "current_value": ctr,
                        "threshold": low_threshold,
                        "severity": "high",
                        "suggested_actions": self.optimization_rules["ctr_optimization"]["actions"],
                        "reason": f"点击率低于阈值 {low_threshold}%"
                    })
            
            # 检查ROI
            roi = metrics.get("roi")
            if roi is not None:
                low_threshold = self.optimization_rules["roi_optimization"]["low_roi_threshold"]
                if roi < low_threshold:
                    suggestions.append({
                        "video_id": video_id,
                        "platform": platform,
                        "metric": "roi",
                        "current_value": roi,
                        "threshold": low_threshold,
                        "severity": "high",
                        "suggested_actions": self.optimization_rules["roi_optimization"]["actions"],
                        "reason": f"ROI低于阈值 {low_threshold}%"
                    })
        
        return suggestions
    
    def _extract_key_insights(self, records: List[Dict[str, Any]]) -> List[str]:
        """提取关键洞察"""
        insights = []
        
        if not records:
            return insights
        
        # 按平台分组
        platform_groups = defaultdict(list)
        for record in records:
            platform = record.get("platform", "unknown")
            platform_groups[platform].append(record)
        
        # 平台表现比较
        platform_performance = {}
        for platform, platform_records in platform_groups.items():
            if platform_records:
                engagement_rates = [r["current_metrics"].get("engagement_rate", 0) 
                                   for r in platform_records]
                avg_engagement = statistics.mean(engagement_rates) if engagement_rates else 0
                platform_performance[platform] = avg_engagement
        
        # 找出表现最佳的平台
        if platform_performance:
            best_platform = max(platform_performance, key=platform_performance.get)
            best_performance = platform_performance[best_platform]
            
            insights.append(f"最佳表现平台: {best_platform} (平均互动率: {best_performance:.1f}%)")
            
            # 检查是否有表现显著较差的平台
            for platform, performance in platform_performance.items():
                if performance < best_performance * 0.5:  # 表现不到最佳平台的一半
                    insights.append(f"需要优化平台: {platform} (表现仅为最佳平台的 {performance/best_performance*100:.0f}%)")
        
        # 时间趋势分析
        if len(records) >= 5:
            # 按创建时间排序
            sorted_records = sorted(records, key=lambda r: r["created_at"])
            
            # 检查近期表现趋势
            recent_records = sorted_records[-5:]
            recent_engagement = [r["current_metrics"].get("engagement_rate", 0) 
                               for r in recent_records]
            
            if len(recent_engagement) >= 3:
                trend = self._calculate_trend(recent_engagement)
                if trend > 0.1:
                    insights.append("近期表现: 互动率呈上升趋势 ✓")
                elif trend < -0.1:
                    insights.append("近期表现: 互动率呈下降趋势 ⚠️")
                else:
                    insights.append("近期表现: 互动率保持稳定")
        
        # 内容效果差异分析
        if len(records) >= 3:
            engagement_rates = [r["current_metrics"].get("engagement_rate", 0) 
                              for r in records]
            
            if engagement_rates:
                max_rate = max(engagement_rates)
                min_rate = min(engagement_rates)
                
                if max_rate > 0 and (max_rate - min_rate) / max_rate > 0.3:
                    insights.append("内容效果差异: 不同视频表现差异显著 (>30%)，建议分析最佳实践")
        
        return insights
    
    def _calculate_trend(self, values: List[float]) -> float:
        """计算数值趋势"""
        if len(values) < 2:
            return 0.0
        
        # 简单线性回归
        x = list(range(len(values)))
        y = values
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = n * sum_x2 - sum_x * sum_x
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def get_recommendations(self, 
                           video_id: Optional[str] = None,
                           priority: str = "all") -> Dict[str, Any]:
        """
        获取优化推荐
        
        Args:
            video_id: 特定视频ID，None表示所有视频
            priority: 优先级过滤，'high'、'medium'、'low'、'all'
        
        Returns:
            优化推荐报告
        """
        # 获取相关记录
        if video_id:
            records = [self.video_records.get(video_id)] if video_id in self.video_records else []
        else:
            records = list(self.video_records.values())
        
        records = [r for r in records if r is not None]
        
        if not records:
            return {
                "status": "no_data",
                "message": "没有可用的性能数据",
                "timestamp": datetime.now().isoformat()
            }
        
        # 生成建议
        suggestions = self._generate_optimization_suggestions(records)
        
        # 按优先级过滤
        if priority != "all":
            severity_map = {"high": "high", "medium": "medium", "low": "low"}
            suggestions = [s for s in suggestions if s["severity"] == severity_map.get(priority, "medium")]
        
        # 分组建议
        grouped_suggestions = defaultdict(list)
        for suggestion in suggestions:
            key = f"{suggestion['metric']}_{suggestion['severity']}"
            grouped_suggestions[key].append(suggestion)
        
        # 编译推荐报告
        report = {
            "status": "success",
            "summary": {
                "total_videos_analyzed": len(records),
                "total_suggestions": len(suggestions),
                "high_priority_suggestions": len([s for s in suggestions if s["severity"] == "high"]),
                "medium_priority_suggestions": len([s for s in suggestions if s["severity"] == "medium"]),
                "timestamp": datetime.now().isoformat()
            },
            "recommendations": suggestions,
            "action_plan": self._generate_action_plan(suggestions)
        }
        
        return report
    
    def _generate_action_plan(self, suggestions: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """生成行动方案"""
        action_plan = {
            "immediate_actions": [],  # 高优先级，今天执行
            "short_term_actions": [],  # 中等优先级，本周执行
            "long_term_actions": []   # 低优先级，本月执行
        }
        
        for suggestion in suggestions:
            # 根据严重程度分配时间框架
            if suggestion["severity"] == "high":
                target_list = action_plan["immediate_actions"]
            elif suggestion["severity"] == "medium":
                target_list = action_plan["short_term_actions"]
            else:
                target_list = action_plan["long_term_actions"]
            
            # 格式化行动项
            video_info = f"视频 {suggestion['video_id'][:8]}"
            action_item = f"{video_info} - {suggestion['reason']}"
            
            # 添加前3个建议行动
            actions_to_add = suggestion["suggested_actions"][:3]
            for action in actions_to_add:
                target_list.append(f"{action_item}: {action}")
        
        return action_plan
    
    def export_performance_report(self, 
                                 report_format: str = "json",
                                 filename: Optional[str] = None) -> Optional[str]:
        """
        导出性能报告
        
        Args:
            report_format: 报告格式，'json' 或 'markdown'
            filename: 输出文件名
        
        Returns:
            报告内容或文件路径
        """
        # 生成完整分析报告
        analysis = self.analyze_performance()
        
        if report_format == "json":
            content = json.dumps(analysis, indent=2, ensure_ascii=False)
            extension = ".json"
        elif report_format == "markdown":
            content = self._format_markdown_report(analysis)
            extension = ".md"
        else:
            logger.error(f"不支持的报告格式: {report_format}")
            return None
        
        # 确定文件名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"video_performance_report_{timestamp}{extension}"
        
        # 写入文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"性能报告已导出: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"导出性能报告失败: {e}")
            return None
    
    def _format_markdown_report(self, analysis: Dict[str, Any]) -> str:
        """格式化Markdown报告"""
        lines = []
        
        lines.append("# 视频性能分析报告")
        lines.append(f"生成时间: {analysis.get('timestamp', '未知')}")
        lines.append("")
        
        # 摘要部分
        lines.append("## 分析摘要")
        summary = analysis.get("analysis_summary", {})
        lines.append(f"- 分析视频总数: {summary.get('total_videos_analyzed', 0)}")
        
        platform_breakdown = summary.get("platform_breakdown", {})
        if platform_breakdown:
            lines.append("- 平台分布:")
            for platform, count in platform_breakdown.items():
                lines.append(f"  - {platform}: {count}个视频")
        
        lines.append("")
        
        # 性能统计
        lines.append("## 性能统计")
        stats = analysis.get("performance_statistics", {})
        
        for metric, data in stats.items():
            lines.append(f"### {metric}")
            lines.append(f"- 平均值: {data.get('mean', 0):.2f}")
            lines.append(f"- 中位数: {data.get('median', 0):.2f}")
            lines.append(f"- 范围: {data.get('min', 0):.2f} ~ {data.get('max', 0):.2f}")
            lines.append(f"- 标准差: {data.get('std', 0):.2f}")
            lines.append("")
        
        # 优化建议
        lines.append("## 优化建议")
        suggestions = analysis.get("optimization_suggestions", [])
        
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f"### 建议 {i}: {suggestion.get('metric', '未知指标')}")
                lines.append(f"- 视频ID: {suggestion.get('video_id', '未知')}")
                lines.append(f"- 平台: {suggestion.get('platform', '未知')}")
                lines.append(f"- 当前值: {suggestion.get('current_value', 0):.2f}")
                lines.append(f"- 阈值: {suggestion.get('threshold', 0):.2f}")
                lines.append(f"- 严重程度: {suggestion.get('severity', '中')}")
                lines.append(f"- 原因: {suggestion.get('reason', '未知')}")
                lines.append("- 建议行动:")
                for action in suggestion.get("suggested_actions", []):
                    lines.append(f"  - {action}")
                lines.append("")
        else:
            lines.append("暂无优化建议，当前表现良好。")
            lines.append("")
        
        # 关键洞察
        lines.append("## 关键洞察")
        insights = analysis.get("key_insights", [])
        
        if insights:
            for insight in insights:
                lines.append(f"- {insight}")
        else:
            lines.append("暂无关键洞察。")
        
        lines.append("")
        
        return "\n".join(lines)

# 实用函数
def create_tracker() -> VideoPerformanceTracker:
    """创建视频性能追踪器实例"""
    return VideoPerformanceTracker()

def simulate_performance_data(tracker: VideoPerformanceTracker, 
                             num_videos: int = 10):
    """模拟性能数据用于测试"""
    import random
    
    platforms = ["tiktok", "youtube_shorts", "instagram_reels", "xiaohongshu"]
    scenes = ["indoor_studio", "street_urban", "lifestyle_casual", "active_dynamic", "artistic_conceptual"]
    
    for i in range(num_videos):
        video_id = f"test_video_{i+1}_{int(time.time())}"
        platform = random.choice(platforms)
        scene = random.choice(scenes)
        
        # 生成模拟指标
        base_views = random.randint(1000, 10000)
        
        metrics = {
            "views": base_views,
            "likes": random.randint(int(base_views * 0.02), int(base_views * 0.08)),
            "comments": random.randint(int(base_views * 0.001), int(base_views * 0.005)),
            "shares": random.randint(int(base_views * 0.001), int(base_views * 0.003)),
            "clicks": random.randint(int(base_views * 0.01), int(base_views * 0.03)),
            "conversions": random.randint(int(base_views * 0.001), int(base_views * 0.005)),
            "revenue": random.uniform(100.0, 1000.0),
            "cost": random.uniform(50.0, 200.0)
        }
        
        # 添加时间偏移
        hours_offset = random.randint(0, 72)  # 0-72小时前
        timestamp = datetime.now() - timedelta(hours=hours_offset)
        
        tracker.record_video_performance(video_id, platform, metrics, timestamp)
        
        # 添加一些后续数据点
        for followup in range(random.randint(0, 3)):
            hours_later = random.randint(1, 12)
            followup_timestamp = timestamp + timedelta(hours=hours_later)
            
            # 增加指标
            followup_metrics = {k: v * random.uniform(1.1, 1.5) for k, v in metrics.items()}
            tracker.record_video_performance(video_id, platform, followup_metrics, followup_timestamp)

# 示例使用
if __name__ == "__main__":
    print("短视频引流军团 - 效果追踪系统")
    print("=" * 50)
    
    # 创建追踪器
    tracker = create_tracker()
    
    # 模拟性能数据
    print("正在模拟性能数据...")
    simulate_performance_data(tracker, num_videos=8)
    
    # 分析性能
    print("\n性能分析报告:")
    analysis = tracker.analyze_performance()
    
    if analysis["status"] == "success":
        summary = analysis["analysis_summary"]
        print(f"分析视频总数: {summary['total_videos_analyzed']}")
        
        platform_breakdown = summary.get('platform_breakdown', {})
        print(f"平台分布: {platform_breakdown}")
        
        # 关键洞察
        print("\n关键洞察:")
        for insight in analysis.get("key_insights", []):
            print(f"  • {insight}")
        
        # 优化建议
        suggestions = analysis.get("optimization_suggestions", [])
        if suggestions:
            print(f"\n优化建议 ({len(suggestions)} 条):")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"  {i}. {suggestion['video_id'][:8]}@{suggestion['platform']}: "
                      f"{suggestion['metric']} ({suggestion['current_value']:.1f} < {suggestion['threshold']})")
        else:
            print("\n暂无优化建议，表现良好。")
        
        # 导出报告
        print("\n导出报告...")
        report_file = tracker.export_performance_report("markdown", "temp/video_performance_demo.md")
        if report_file:
            print(f"报告已导出到: {report_file}")
    
    print("\n系统准备就绪，可实时追踪视频引流效果。")