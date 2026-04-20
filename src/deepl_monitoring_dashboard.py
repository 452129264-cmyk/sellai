"""
DeepL翻译服务前端监控仪表盘
实时显示服务健康状态、使用统计、成本分析等
版本：v1.0
创建时间：2026-04-05
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import sqlite3
from dataclasses import asdict
import threading
import hashlib
from collections import deque
import statistics

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/deepl_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================================
# 实时监控数据收集器
# ==============================================

class RealTimeMetricsCollector:
    """实时指标收集器"""
    
    def __init__(self, window_size_minutes: int = 60):
        """
        初始化收集器
        
        参数:
            window_size_minutes: 滑动窗口大小（分钟）
        """
        self.window_size = window_size_minutes
        self.metrics_buffer = deque(maxlen=window_size * 60)  # 每秒一个数据点
        
        # 统计信息
        self.current_stats = {
            "request_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "total_characters": 0,
            "total_cost": 0.0,
            "response_times": [],
            "error_messages": [],
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # 时间窗口统计
        self.window_stats = {
            "last_minute": {},
            "last_5_minutes": {},
            "last_hour": {}
        }
        
        # 监控线程
        self.monitoring_thread = None
        self.is_monitoring = False
        
        logger.info(f"实时指标收集器初始化完成，窗口大小: {window_size_minutes}分钟")
    
    def record_transaction(self, request_id: str, success: bool, 
                          char_count: int = 0, cost: float = 0.0,
                          response_time_ms: float = 0.0,
                          cache_hit: bool = False,
                          error_message: Optional[str] = None):
        """
        记录单次翻译事务
        
        参数:
            request_id: 请求ID
            success: 是否成功
            char_count: 字符数
            cost: 成本
            response_time_ms: 响应时间（毫秒）
            cache_hit: 是否缓存命中
            error_message: 错误信息
        """
        timestamp = datetime.now()
        
        # 更新统计信息
        self.current_stats["request_count"] += 1
        
        if success:
            self.current_stats["success_count"] += 1
            self.current_stats["total_characters"] += char_count
            self.current_stats["total_cost"] += cost
            self.current_stats["response_times"].append(response_time_ms)
        else:
            self.current_stats["failed_count"] += 1
            if error_message:
                self.current_stats["error_messages"].append(error_message)
        
        if cache_hit:
            self.current_stats["cache_hits"] += 1
        else:
            self.current_stats["cache_misses"] += 1
        
        # 记录到滑动窗口
        metric_point = {
            "timestamp": timestamp.isoformat(),
            "request_id": request_id,
            "success": success,
            "char_count": char_count,
            "cost": cost,
            "response_time_ms": response_time_ms,
            "cache_hit": cache_hit,
            "error_message": error_message
        }
        
        self.metrics_buffer.append(metric_point)
        
        # 更新时间窗口统计
        self._update_window_stats()
    
    def _update_window_stats(self):
        """更新时间窗口统计"""
        now = datetime.now()
        
        # 最近1分钟
        one_min_ago = now - timedelta(minutes=1)
        recent_minute = [
            m for m in self.metrics_buffer
            if datetime.fromisoformat(m["timestamp"]) > one_min_ago
        ]
        
        self.window_stats["last_minute"] = {
            "request_count": len(recent_minute),
            "success_count": len([m for m in recent_minute if m["success"]]),
            "avg_response_time": statistics.mean([m["response_time_ms"] for m in recent_minute]) if recent_minute else 0
        }
        
        # 最近5分钟
        five_min_ago = now - timedelta(minutes=5)
        recent_5_minutes = [
            m for m in self.metrics_buffer
            if datetime.fromisoformat(m["timestamp"]) > five_min_ago
        ]
        
        self.window_stats["last_5_minutes"] = {
            "request_count": len(recent_5_minutes),
            "success_count": len([m for m in recent_5_minutes if m["success"]]),
            "total_characters": sum(m["char_count"] for m in recent_5_minutes),
            "total_cost": sum(m["cost"] for m in recent_5_minutes)
        }
        
        # 最近1小时
        one_hour_ago = now - timedelta(hours=1)
        recent_hour = [
            m for m in self.metrics_buffer
            if datetime.fromisoformat(m["timestamp"]) > one_hour_ago
        ]
        
        self.window_stats["last_hour"] = {
            "request_count": len(recent_hour),
            "success_count": len([m for m in recent_hour if m["success"]]),
            "total_characters": sum(m["char_count"] for m in recent_hour),
            "total_cost": sum(m["cost"] for m in recent_hour),
            "error_rate": len([m for m in recent_hour if not m["success"]]) / len(recent_hour) if recent_hour else 0
        }
    
    def get_realtime_metrics(self) -> Dict[str, Any]:
        """
        获取实时监控指标
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "current_stats": self.current_stats,
            "window_stats": self.window_stats,
            "buffer_size": len(self.metrics_buffer),
            "success_rate": self.current_stats["success_count"] / self.current_stats["request_count"] if self.current_stats["request_count"] > 0 else 0,
            "avg_response_time_ms": statistics.mean(self.current_stats["response_times"]) if self.current_stats["response_times"] else 0,
            "cache_hit_rate": self.current_stats["cache_hits"] / (self.current_stats["cache_hits"] + self.current_stats["cache_misses"]) if (self.current_stats["cache_hits"] + self.current_stats["cache_misses"]) > 0 else 0
        }
    
    def start_monitoring(self, interval_seconds: int = 5):
        """
        启动监控线程
        
        参数:
            interval_seconds: 监控间隔（秒）
        """
        if self.is_monitoring:
            logger.warning("监控已启动")
            return
        
        self.is_monitoring = True
        
        def monitoring_loop():
            while self.is_monitoring:
                try:
                    # 收集指标
                    metrics = self.get_realtime_metrics()
                    
                    # 记录到日志
                    logger.debug(f"监控指标: {json.dumps(metrics, indent=2)}")
                    
                    # 检查告警条件
                    self._check_alerts(metrics)
                    
                    # 间隔等待
                    time.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error(f"监控循环异常: {str(e)}")
                    time.sleep(interval_seconds)
        
        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info(f"实时监控已启动，间隔: {interval_seconds}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("实时监控已停止")
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """
        检查告警条件
        
        参数:
            metrics: 监控指标
        """
        alerts = []
        
        # 错误率告警
        current_error_rate = 1 - metrics["success_rate"]
        if current_error_rate > 0.1:  # 超过10%
            alerts.append({
                "level": "critical",
                "type": "high_error_rate",
                "message": f"错误率过高: {current_error_rate:.1%}",
                "timestamp": metrics["timestamp"],
                "metric": current_error_rate,
                "threshold": 0.1
            })
        
        # 响应时间告警
        avg_response_time = metrics["avg_response_time_ms"]
        if avg_response_time > 1000:  # 超过1秒
            alerts.append({
                "level": "warning",
                "type": "slow_response",
                "message": f"平均响应时间过慢: {avg_response_time:.0f}ms",
                "timestamp": metrics["timestamp"],
                "metric": avg_response_time,
                "threshold": 1000
            })
        
        # 缓存命中率告警
        cache_hit_rate = metrics["cache_hit_rate"]
        if cache_hit_rate < 0.3:  # 低于30%
            alerts.append({
                "level": "info",
                "type": "low_cache_hit_rate",
                "message": f"缓存命中率较低: {cache_hit_rate:.1%}",
                "timestamp": metrics["timestamp"],
                "metric": cache_hit_rate,
                "threshold": 0.3
            })
        
        # 触发告警（记录到日志）
        for alert in alerts:
            alert_level = alert["level"].upper()
            logger.warning(f"[{alert_level}] {alert['message']}")
            
            # 记录到数据库
            self._record_alert(alert)
    
    def _record_alert(self, alert: Dict[str, Any]):
        """
        记录告警到数据库
        """
        try:
            conn = sqlite3.connect("data/shared_state/state.db")
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_level TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metric_value REAL,
                    threshold_value REAL,
                    timestamp TEXT NOT NULL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    acknowledged_at TIMESTAMP,
                    acknowledged_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO monitoring_alerts 
                (alert_level, alert_type, message, metric_value, threshold_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert["level"],
                alert["type"],
                alert["message"],
                alert["metric"],
                alert["threshold"],
                alert["timestamp"]
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录告警失败: {str(e)}")

# ==============================================
# 前端仪表盘HTML生成器
# ==============================================

class DashboardHTMLGenerator:
    """仪表盘HTML生成器"""
    
    def __init__(self, service_name: str = "DeepL翻译服务"):
        """
        初始化生成器
        
        参数:
            service_name: 服务名称
        """
        self.service_name = service_name
        self.base_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{service_name}监控仪表盘</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}
        
        .dashboard-container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .dashboard-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        .dashboard-title {{
            font-size: 28px;
            font-weight: 600;
            color: #2c3e50;
        }}
        
        .dashboard-status {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .status-indicator {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        
        .status-healthy {{
            background-color: #27ae60;
            box-shadow: 0 0 10px rgba(39, 174, 96, 0.5);
        }}
        
        .status-degraded {{
            background-color: #f39c12;
            box-shadow: 0 0 10px rgba(243, 156, 18, 0.5);
        }}
        
        .status-unhealthy {{
            background-color: #e74c3c;
            box-shadow: 0 0 10px rgba(231, 76, 60, 0.5);
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
        }}
        
        .metric-card.critical {{
            border-left: 5px solid #e74c3c;
        }}
        
        .metric-card.warning {{
            border-left: 5px solid #f39c12;
        }}
        
        .metric-card.info {{
            border-left: 5px solid #3498db;
        }}
        
        .metric-title {{
            font-size: 16px;
            color: #7f8c8d;
            margin-bottom: 10px;
            font-weight: 500;
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        
        .metric-trend {{
            font-size: 14px;
            color: #95a5a6;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .trend-up {{
            color: #27ae60;
        }}
        
        .trend-down {{
            color: #e74c3c;
        }}
        
        .trend-neutral {{
            color: #95a5a6;
        }}
        
        .charts-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .charts-title {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #2c3e50;
        }}
        
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }}
        
        .chart-item {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            min-height: 300px;
        }}
        
        .alerts-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .alerts-title {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #2c3e50;
        }}
        
        .alert-list {{
            list-style: none;
        }}
        
        .alert-item {{
            padding: 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .alert-item:last-child {{
            border-bottom: none;
        }}
        
        .alert-content {{
            flex-grow: 1;
        }}
        
        .alert-time {{
            font-size: 14px;
            color: #95a5a6;
            margin-bottom: 5px;
        }}
        
        .alert-message {{
            font-size: 16px;
            margin-bottom: 5px;
        }}
        
        .alert-level {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .level-critical {{
            background-color: #ffeaea;
            color: #e74c3c;
        }}
        
        .level-warning {{
            background-color: #fff4e6;
            color: #f39c12;
        }}
        
        .level-info {{
            background-color: #e8f4fc;
            color: #3498db;
        }}
        
        .refresh-info {{
            text-align: center;
            margin-top: 20px;
            color: #95a5a6;
            font-size: 14px;
        }}
        
        .last-updated {{
            color: #3498db;
            font-weight: 500;
        }}
        
        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            
            .chart-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h1 class="dashboard-title">{service_name}监控仪表盘</h1>
            <div class="dashboard-status">
                <div id="statusIndicator" class="status-indicator status-healthy"></div>
                <span id="statusText">健康</span>
            </div>
        </div>
        
        <div class="metrics-grid">
            <!-- 动态指标卡片将由JavaScript填充 -->
        </div>
        
        <div class="charts-container">
            <h2 class="charts-title">性能图表</h2>
            <div class="chart-grid">
                <div class="chart-item">
                    <canvas id="responseTimeChart"></canvas>
                </div>
                <div class="chart-item">
                    <canvas id="errorRateChart"></canvas>
                </div>
                <div class="chart-item">
                    <canvas id="costChart"></canvas>
                </div>
                <div class="chart-item">
                    <canvas id="cacheHitChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="alerts-container">
            <h2 class="alerts-title">实时告警</h2>
            <ul id="alertList" class="alert-list">
                <!-- 动态告警列表将由JavaScript填充 -->
            </ul>
        </div>
        
        <div class="refresh-info">
            最后更新: <span id="lastUpdated" class="last-updated">正在加载...</span>
            数据每10秒自动刷新
        </div>
    </div>
    
    <!-- Chart.js库 -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- 自定义JavaScript -->
    <script>
        // 全局变量
        let metricsData = {{}};
        let charts = {{}};
        
        // 初始化
        document.addEventListener('DOMContentLoaded', function() {{
            loadMetrics();
            setInterval(loadMetrics, 10000); // 每10秒刷新一次
        }});
        
        // 加载监控指标
        async function loadMetrics() {{
            try {{
                const response = await fetch('/api/deepl/monitoring/metrics');
                const data = await response.json();
                
                metricsData = data;
                updateDashboard(data);
                updateCharts(data);
                updateAlerts(data);
                
                document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString('zh-CN');
            }} catch (error) {{
                console.error('加载监控数据失败:', error);
                document.getElementById('statusText').textContent = '连接失败';
                document.getElementById('statusIndicator').className = 'status-indicator status-unhealthy';
            }}
        }}
        
        // 更新仪表盘
        function updateDashboard(data) {{
            const metricsGrid = document.querySelector('.metrics-grid');
            
            // 清理旧的指标卡片
            metricsGrid.innerHTML = '';
            
            // 创建指标卡片
            const metricCards = [
                {{
                    title: '成功率',
                    value: (data.success_rate * 100).toFixed(2) + '%',
                    trend: data.trends.success_rate,
                    level: data.success_rate > 0.95 ? 'healthy' : data.success_rate > 0.9 ? 'warning' : 'critical'
                }},
                {{
                    title: '平均响应时间',
                    value: data.avg_response_time_ms.toFixed(2) + 'ms',
                    trend: data.trends.response_time,
                    level: data.avg_response_time_ms < 500 ? 'healthy' : data.avg_response_time_ms < 1000 ? 'warning' : 'critical'
                }},
                {{
                    title: '今日成本',
                    value: '$' + data.total_cost_today.toFixed(2),
                    trend: data.trends.cost,
                    level: data.total_cost_today < 10 ? 'healthy' : data.total_cost_today < 50 ? 'warning' : 'critical'
                }},
                {{
                    title: '缓存命中率',
                    value: (data.cache_hit_rate * 100).toFixed(2) + '%',
                    trend: data.trends.cache_hit_rate,
                    level: data.cache_hit_rate > 0.6 ? 'healthy' : data.cache_hit_rate > 0.3 ? 'warning' : 'critical'
                }},
                {{
                    title: '总请求数',
                    value: data.total_requests.toLocaleString(),
                    trend: 'neutral',
                    level: 'info'
                }},
                {{
                    title: '总字符数',
                    value: data.total_characters.toLocaleString(),
                    trend: data.trends.characters,
                    level: 'info'
                }}
            ];
            
            // 添加指标卡片到网格
            metricCards.forEach(metric => {{
                const card = document.createElement('div');
                card.className = `metric-card ${{metric.level}}`;
                
                // 生成趋势图标
                let trendIcon = '→';
                let trendClass = 'trend-neutral';
                
                if (metric.trend === 'up') {{
                    trendIcon = '↗';
                    trendClass = 'trend-up';
                }} else if (metric.trend === 'down') {{
                    trendIcon = '↘';
                    trendClass = 'trend-down';
                }}
                
                card.innerHTML = `
                    <div class="metric-title">${{metric.title}}</div>
                    <div class="metric-value">${{metric.value}}</div>
                    <div class="metric-trend ${{trendClass}}">
                        <span>${{trendIcon}}</span>
                        <span>与前一小时相比</span>
                    </div>
                `;
                
                metricsGrid.appendChild(card);
            }});
            
            // 更新状态指示器
            const statusIndicator = document.getElementById('statusIndicator');
            const statusText = document.getElementById('statusText');
            
            // 基于整体健康状态确定颜色
            const criticalCards = metricCards.filter(card => card.level === 'critical').length;
            const warningCards = metricCards.filter(card => card.level === 'warning').length;
            
            if (criticalCards > 0) {{
                statusIndicator.className = 'status-indicator status-unhealthy';
                statusText.textContent = '不健康';
            }} else if (warningCards > 0) {{
                statusIndicator.className = 'status-indicator status-degraded';
                statusText.textContent = '降级';
            }} else {{
                statusIndicator.className = 'status-indicator status-healthy';
                statusText.textContent = '健康';
            }}
        }}
        
        // 更新图表
        function updateCharts(data) {{
            // 响应时间图表
            if (!charts.responseTimeChart) {{
                const ctx = document.getElementById('responseTimeChart').getContext('2d');
                charts.responseTimeChart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: data.charts.response_time.labels,
                        datasets: [{{
                            label: '响应时间 (ms)',
                            data: data.charts.response_time.data,
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            borderWidth: 2,
                            tension: 0.4,
                            fill: true
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            title: {{
                                display: true,
                                text: '响应时间趋势 (最近60分钟)'
                            }}
                        }}
                    }}
                }});
            }} else {{
                charts.responseTimeChart.data.labels = data.charts.response_time.labels;
                charts.responseTimeChart.data.datasets[0].data = data.charts.response_time.data;
                charts.responseTimeChart.update('none');
            }}
            
            // 错误率图表
            if (!charts.errorRateChart) {{
                const ctx = document.getElementById('errorRateChart').getContext('2d');
                charts.errorRateChart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: data.charts.error_rate.labels,
                        datasets: [{{
                            label: '错误率 (%)',
                            data: data.charts.error_rate.data,
                            backgroundColor: '#e74c3c',
                            borderColor: '#c0392b',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            title: {{
                                display: true,
                                text: '错误率统计 (最近60分钟)'
                            }}
                        }}
                    }}
                }});
            }} else {{
                charts.errorRateChart.data.labels = data.charts.error_rate.labels;
                charts.errorRateChart.data.datasets[0].data = data.charts.error_rate.data;
                charts.errorRateChart.update('none');
            }}
            
            // 成本图表
            if (!charts.costChart) {{
                const ctx = document.getElementById('costChart').getContext('2d');
                charts.costChart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: data.charts.cost.labels,
                        datasets: [{{
                            label: '成本 ($)',
                            data: data.charts.cost.data,
                            borderColor: '#27ae60',
                            backgroundColor: 'rgba(39, 174, 96, 0.1)',
                            borderWidth: 2,
                            fill: true
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            title: {{
                                display: true,
                                text: '成本趋势 (最近24小时)'
                            }}
                        }}
                    }}
                }});
            }} else {{
                charts.costChart.data.labels = data.charts.cost.labels;
                charts.costChart.data.datasets[0].data = data.charts.cost.data;
                charts.costChart.update('none');
            }}
            
            // 缓存命中率图表
            if (!charts.cacheHitChart) {{
                const ctx = document.getElementById('cacheHitChart').getContext('2d');
                charts.cacheHitChart = new Chart(ctx, {{
                    type: 'pie',
                    data: {{
                        labels: ['命中', '未命中'],
                        datasets: [{{
                            data: [
                                data.cache_hit_rate * 100,
                                (1 - data.cache_hit_rate) * 100
                            ],
                            backgroundColor: [
                                '#2ecc71',
                                '#e74c3c'
                            ]
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            title: {{
                                display: true,
                                text: '缓存命中率分布'
                            }}
                        }}
                    }}
                }});
            }} else {{
                charts.cacheHitChart.data.datasets[0].data = [
                    data.cache_hit_rate * 100,
                    (1 - data.cache_hit_rate) * 100
                ];
                charts.cacheHitChart.update('none');
            }}
        }}
        
        // 更新告警列表
        function updateAlerts(data) {{
            const alertList = document.getElementById('alertList');
            
            if (data.alerts.length === 0) {{
                alertList.innerHTML = '<li class="alert-item">暂无告警</li>';
                return;
            }}
            
            // 清理旧的告警列表
            alertList.innerHTML = '';
            
            // 添加告警项
            data.alerts.forEach(alert => {{
                const alertItem = document.createElement('li');
                alertItem.className = 'alert-item';
                
                // 确定告警级别样式
                let levelClass = 'level-info';
                if (alert.level === 'critical') {{
                    levelClass = 'level-critical';
                }} else if (alert.level === 'warning') {{
                    levelClass = 'level-warning';
                }}
                
                alertItem.innerHTML = `
                    <div class="alert-content">
                        <div class="alert-time">${{formatTime(alert.timestamp)}}</div>
                        <div class="alert-message">${{alert.message}}</div>
                    </div>
                    <div>
                        <span class="alert-level ${{levelClass}}">${{alert.level.toUpperCase()}}</span>
                    </div>
                `;
                
                alertList.appendChild(alertItem);
            }});
        }}
        
        // 格式化时间
        function formatTime(timestamp) {{
            const date = new Date(timestamp);
            return date.toLocaleTimeString('zh-CN', {{
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            }}) + '.' + date.getMilliseconds().toString().padStart(3, '0');
        }}
    </script>
</body>
</html>
        """
    
    def generate_dashboard(self, metrics_data: Dict[str, Any]) -> str:
        """
        生成完整的监控仪表盘HTML
        
        参数:
            metrics_data: 监控指标数据
            
        返回:
            完整的HTML字符串
        """
        # 填充基础模板
        html_content = self.base_html.format(service_name=self.service_name)
        
        return html_content
    
    def generate_metrics_endpoint_response(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成监控API端点响应数据
        
        参数:
            metrics: 监控指标
            
        返回:
            标准化的API响应
        """
        # 计算趋势（简化实现）
        trends = {
            "success_rate": "up",  # 默认向上
            "response_time": "down",  # 默认向下
            "cost": "up",
            "cache_hit_rate": "up",
            "characters": "up"
        }
        
        # 生成图表数据（简化实现）
        now = datetime.now()
        
        # 最近60分钟的响应时间数据
        response_time_labels = []
        response_time_data = []
        
        for i in range(60):
            minute = now - timedelta(minutes=59-i)
            response_time_labels.append(minute.strftime("%H:%M"))
            # 模拟数据，实际应从数据库获取
            base_value = 200 + (i % 20) * 10
            response_time_data.append(base_value + (i % 10) * 5)
        
        # 最近60分钟的错误率数据
        error_rate_labels = response_time_labels
        error_rate_data = [max(0, min(10, (i % 15) / 10)) for i in range(60)]
        
        # 最近24小时的成本数据
        cost_labels = []
        cost_data = []
        
        for i in range(24):
            hour = now - timedelta(hours=23-i)
            cost_labels.append(hour.strftime("%H:00"))
            # 模拟数据
            base_cost = 0.5 + (i % 8) * 0.2
            cost_data.append(base_cost)
        
        charts = {
            "response_time": {
                "labels": response_time_labels,
                "data": response_time_data
            },
            "error_rate": {
                "labels": error_rate_labels,
                "data": error_rate_data
            },
            "cost": {
                "labels": cost_labels,
                "data": cost_data
            }
        }
        
        # 模拟告警数据
        alerts = [
            {
                "level": "warning",
                "type": "high_error_rate",
                "message": "过去5分钟错误率超过5%",
                "timestamp": (now - timedelta(minutes=2)).isoformat()
            }
        ]
        
        # 如果错误率过高，添加严重告警
        if metrics.get("error_rate", 0) > 0.1:
            alerts.append({
                "level": "critical",
                "type": "critical_error_rate",
                "message": f"当前错误率过高: {metrics.get('error_rate', 0):.1%}",
                "timestamp": now.isoformat()
            })
        
        # 构建完整的响应数据
        return {
            "timestamp": now.isoformat(),
            "success_rate": metrics.get("success_rate", 0.95),
            "avg_response_time_ms": metrics.get("avg_response_time_ms", 300),
            "total_cost_today": metrics.get("total_cost_today", 15.75),
            "cache_hit_rate": metrics.get("cache_hit_rate", 0.65),
            "total_requests": metrics.get("total_requests", 1250),
            "total_characters": metrics.get("total_characters", 125000),
            "error_rate": metrics.get("error_rate", 0.05),
            "plan_type": metrics.get("plan_type", "free"),
            "trends": trends,
            "charts": charts,
            "alerts": alerts,
            "updated_at": now.isoformat()
        }

# ==============================================
# 集成监控管理器
# ==============================================

class IntegratedMonitoringManager:
    """集成监控管理器"""
    
    def __init__(self, deepl_service):
        """
        初始化监控管理器
        
        参数:
            deepl_service: DeepL翻译服务实例
        """
        self.deepl_service = deepl_service
        
        # 初始化组件
        self.metrics_collector = RealTimeMetricsCollector(window_size_minutes=60)
        self.html_generator = DashboardHTMLGenerator(service_name="DeepL全域多语种润色服务")
        
        # 监控状态
        self.is_running = False
        self.monitoring_thread = None
        
        # API端点数据
        self.last_metrics = {}
        
        logger.info("集成监控管理器初始化完成")
    
    def start_monitoring(self):
        """
        启动集成监控
        """
        if self.is_running:
            logger.warning("监控已启动")
            return
        
        self.is_running = True
        
        # 启动指标收集器
        self.metrics_collector.start_monitoring(interval_seconds=5)
        
        # 启动监控线程
        def monitoring_loop():
            while self.is_running:
                try:
                    # 收集服务指标
                    service_stats = self.deepl_service.get_service_stats()
                    health_status = self.deepl_service.check_service_health()
                    
                    # 记录到指标收集器
                    self.metrics_collector.record_transaction(
                        request_id=f"monitoring_{int(time.time())}",
                        success=health_status.status == "healthy",
                        char_count=service_stats.get("total_characters", 0),
                        cost=service_stats.get("total_cost", 0.0),
                        response_time_ms=service_stats.get("response_time_p95", 0),
                        cache_hit=service_stats.get("cache_hit_rate", 0) > 0.5,
                        error_message=None if health_status.status == "healthy" else "服务降级"
                    )
                    
                    # 更新API端点数据
                    self.last_metrics = {
                        "success_rate": service_stats.get("successful_requests", 0) / service_stats.get("total_requests", 1),
                        "avg_response_time_ms": service_stats.get("response_time_p95", 0),
                        "total_cost_today": service_stats.get("total_cost", 0.0),
                        "cache_hit_rate": service_stats.get("cache_hit_rate", 0.0),
                        "total_requests": service_stats.get("total_requests", 0),
                        "total_characters": service_stats.get("total_characters", 0),
                        "error_rate": service_stats.get("failed_requests", 0) / service_stats.get("total_requests", 1),
                        "plan_type": self.deepl_service.plan_type
                    }
                    
                    # 等待下一次收集
                    time.sleep(10)
                    
                except Exception as e:
                    logger.error(f"监控循环异常: {str(e)}")
                    time.sleep(10)
        
        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("集成监控已启动")
    
    def stop_monitoring(self):
        """
        停止集成监控
        """
        self.is_running = False
        
        # 停止指标收集器
        self.metrics_collector.stop_monitoring()
        
        # 等待监控线程结束
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("集成监控已停止")
    
    def get_dashboard_html(self) -> str:
        """
        获取监控仪表盘HTML
        
        返回:
            完整的HTML内容
        """
        metrics_data = self.html_generator.generate_metrics_endpoint_response(self.last_metrics)
        return self.html_generator.generate_dashboard(metrics_data)
    
    def get_metrics_api_response(self) -> Dict[str, Any]:
        """
        获取监控API响应数据
        
        返回:
            标准化的API响应
        """
        return self.html_generator.generate_metrics_endpoint_response(self.last_metrics)
    
    def get_realtime_metrics(self) -> Dict[str, Any]:
        """
        获取实时监控指标
        
        返回:
            实时监控指标
        """
        return self.metrics_collector.get_realtime_metrics()
    
    def generate_health_report(self) -> Dict[str, Any]:
        """
        生成健康报告
        
        返回:
            健康状态报告
        """
        try:
            health_status = self.deepl_service.check_service_health()
            
            # 计算实时指标
            realtime_metrics = self.metrics_collector.get_realtime_metrics()
            
            # 评估健康状态
            recommendations = []
            
            if health_status.error_rate_last_hour > 0.05:
                recommendations.append("错误率过高，建议检查API密钥和网络连接")
            
            if health_status.response_time_p95 > 1000:
                recommendations.append("响应时间过长，建议优化代码或增加超时设置")
            
            if realtime_metrics.get("cache_hit_rate", 0) < 0.3:
                recommendations.append("缓存命中率较低，建议检查缓存策略")
            
            return {
                "status": health_status.status,
                "error_rate": health_status.error_rate_last_hour,
                "response_time_p95_ms": health_status.response_time_p95,
                "cache_hit_rate": realtime_metrics.get("cache_hit_rate", 0),
                "total_requests_last_hour": realtime_metrics.get("window_stats", {}).get("last_hour", {}).get("request_count", 0),
                "success_rate": realtime_metrics.get("success_rate", 0),
                "total_characters_hour": realtime_metrics.get("window_stats", {}).get("last_hour", {}).get("total_characters", 0),
                "estimated_cost_hour": realtime_metrics.get("window_stats", {}).get("last_hour", {}).get("total_cost", 0.0),
                "plan_type": self.deepl_service.plan_type,
                "last_update": datetime.now().isoformat(),
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"生成健康报告失败: {str(e)}")
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# ==============================================
# 快速使用示例
# ==============================================

def monitoring_example():
    """
    监控系统使用示例
    """
    print("=== DeepL监控系统使用示例 ===")
    
    try:
        # 注意：这里需要实际的DeepL翻译服务实例
        # 在真实环境中，应该传入已经初始化的服务实例
        print("注意：此示例需要实际的DeepL翻译服务实例")
        print("在真实环境中，监控管理器会与翻译服务深度集成")
        
        # 模拟数据
        from dataclasses import dataclass
        
        @dataclass
        class MockService:
            plan_type = "free"
            
            def get_service_stats(self):
                return {
                    "total_requests": 1250,
                    "successful_requests": 1180,
                    "failed_requests": 70,
                    "total_characters": 125000,
                    "total_cost": 15.75,
                    "response_time_p95": 320,
                    "cache_hit_rate": 0.65
                }
            
            def check_service_health(self):
                from dataclasses import dataclass
                
                @dataclass
                class HealthStatus:
                    status = "healthy"
                    error_rate_last_hour = 0.05
                    response_time_p95 = 320
                
                return HealthStatus()
        
        # 创建模拟服务
        mock_service = MockService()
        
        # 初始化监控管理器
        monitor = IntegratedMonitoringManager(mock_service)
        
        # 启动监控
        monitor.start_monitoring()
        
        print("监控已启动，等待数据收集...")
        time.sleep(10)  # 等待数据收集
        
        # 获取监控数据
        realtime_metrics = monitor.get_realtime_metrics()
        print(f"实时指标: {json.dumps(realtime_metrics, indent=2, default=str)}")
        
        # 获取健康报告
        health_report = monitor.generate_health_report()
        print(f"健康报告: {json.dumps(health_report, indent=2)}")
        
        # 生成仪表盘HTML（示例）
        print("生成监控仪表盘HTML...")
        
        # 停止监控
        monitor.stop_monitoring()
        
        print("监控示例完成")
        
    except Exception as e:
        print(f"监控示例执行失败: {str(e)}")

# ==============================================
# 主程序入口
# ==============================================

if __name__ == "__main__":
    # 创建必要的目录
    import os
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data/shared_state", exist_ok=True)
    
    # 运行示例
    monitoring_example()