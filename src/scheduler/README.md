# SellAI智能调度系统

## 概述
智能调度系统是SellAI无限分身架构的核心组件，负责实现无上限并行处理、动态资源分配、负载均衡、容错处理四大核心能力。

## 功能特性

### 1. 无上限并行处理
- 支持无限数量的分身同时执行任务
- 动态任务队列管理
- 任务优先级调度

### 2. 动态资源分配
- 基于分身能力画像的智能分配
- 多维度评分算法
- 实时资源监控与调整

### 3. 负载均衡
- 实时分身负载监控
- 智能任务迁移机制
- 多种均衡策略支持（轮询、加权、最少连接）

### 4. 容错处理
- 任务失败自动重试
- 资源自动回收
- 系统自愈能力

## 系统架构

### 核心模块
1. **IntelligentScheduler** - 调度器主类
2. **TaskRequirements** - 任务需求定义
3. **AvatarProfile** - 分身能力画像
4. **ScheduledTask** - 调度任务定义

### 数据库表
1. **scheduler_task_queue** - 任务队列表
2. **scheduler_resource_allocations** - 资源分配表
3. **scheduler_load_metrics** - 负载指标表
4. **scheduler_decision_history** - 调度决策历史表
5. **scheduler_resource_pool** - 资源池配置表
6. **avatar_virtual_pools** - 分身虚拟资源池表

## 快速开始

### 1. 初始化数据库
```bash
python src/scheduler/init_scheduler_tables.py
```

### 2. 使用智能调度器
```python
from src.scheduler.intelligent_scheduler import (
    IntelligentScheduler, TaskRequirements, TaskType, 
    TaskPriority, ResourceType, TaskStatus
)

# 创建调度器实例
scheduler = IntelligentScheduler()

# 创建任务需求
task_req = TaskRequirements(
    task_type=TaskType.FINANCIAL_ANALYSIS,
    required_capabilities=['data_crawling', 'financial_analysis'],
    priority=TaskPriority.NORMAL,
    estimated_complexity=5.0,
    target_regions=['US', 'CA'],
    deadline=datetime.now() + timedelta(hours=1)
)

# 商机数据
opportunity_data = {
    'source_platform': 'Amazon',
    'original_id': 'B08N5WRWNW',
    'title': '男士牛仔裤 - 高品质牛仔布料',
    'estimated_margin': 35,
    '_metadata': {
        'opportunity_hash': 'unique_hash_12345'
    }
}

# 提交任务
task_id = scheduler.submit_task(task_req, opportunity_data)
```

### 3. 运行测试
```bash
python src/scheduler/test_intelligent_scheduler.py
```

## API参考

### IntelligentScheduler类

#### 构造函数
```python
def __init__(self, db_path: str = "data/shared_state/state.db"):
```

#### 主要方法
1. **submit_task** - 提交新任务
   ```python
   def submit_task(task_req: TaskRequirements, opportunity_data: Dict[str, Any]) -> Optional[str]:
   ```

2. **get_system_status** - 获取系统状态
   ```python
   def get_system_status() -> Dict[str, Any]:
   ```

3. **shutdown** - 关闭调度器
   ```python
   def shutdown():
   ```

### 数据类定义

#### TaskRequirements
```python
@dataclass
class TaskRequirements:
    task_type: TaskType
    required_capabilities: List[str]
    priority: TaskPriority
    estimated_complexity: float
    target_regions: List[str]
    deadline: Optional[datetime] = None
    batch_size: int = 1
    max_cost: Optional[float] = None
    min_success_rate: float = 0.0
```

#### AvatarProfile
```python
@dataclass
class AvatarProfile:
    avatar_id: str
    avatar_name: str
    template_id: Optional[str] = None
    capability_scores: Dict[str, float] = field(default_factory=dict)
    specialization_tags: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    total_tasks_completed: int = 0
    avg_completion_time_seconds: float = 0.0
    current_load: int = 0
    last_active: datetime = field(default_factory=datetime.now)
```

#### ScheduledTask
```python
@dataclass
class ScheduledTask:
    task_id: str
    avatar_id: str
    priority: int
    estimated_duration_seconds: float
    resource_requirements: List[TaskResourceRequirement]
    dependencies: List[str]
    deadline: Optional[datetime]
    status: TaskStatus
```

## 部署指南

### 环境要求
- Python ≥ 3.13
- SQLite 3.35+
- 内存 ≥ 1GB
- 存储空间 ≥ 10GB

### 部署步骤
1. 确保Python环境正确配置
2. 运行初始化脚本创建数据库表
3. 在应用程序中导入和使用调度器
4. 定期监控系统性能指标

### 监控指标
1. **任务状态** - 待处理、运行中、完成、失败任务数
2. **系统负载** - 各分身负载情况
3. **资源使用** - CPU、内存、网络资源利用率
4. **性能指标** - 调度延迟、任务成功率、吞吐量

## 故障排除

### 常见问题
1. **任务无法提交**
   - 检查数据库连接
   - 验证分身能力画像是否完整
   - 确认资源池配置是否正确

2. **调度延迟过高**
   - 优化分身能力画像缓存策略
   - 调整任务队列处理算法
   - 增加系统资源分配

3. **任务失败率高**
   - 检查分身健康状态
   - 验证任务依赖关系
   - 调整自动重试策略

### 日志查看
调度器使用标准Python logging模块，日志级别为INFO，格式为：
```
2026-04-08 06:30:00 - INTELLIGENT-SCHEDULER - INFO - 任务提交成功: task_1744115400_a1b2c3d4
```

## 性能优化

### 推荐配置
1. **缓存策略** - 分身画像缓存60秒
2. **并发控制** - 适当的分身最大容量限制
3. **资源预留** - 根据历史负载预留部分资源

### 最佳实践
1. 定期清理过期任务
2. 监控资源使用趋势
3. 根据负载动态调整调度策略
4. 定期备份调度状态数据

## 相关文档
- [智能调度系统设计文档](../docs/无限分身核心能力/智能调度系统设计文档.md)
- [资源自治管理指南](../docs/无限分身核心能力/资源自治管理指南.md)
- [调度算法测试报告](../docs/无限分身核心能力/调度算法测试报告.md)

---

**版本**: 1.0  
**更新日期**: 2026-04-08  
**维护者**: 扣子 Worker Agent