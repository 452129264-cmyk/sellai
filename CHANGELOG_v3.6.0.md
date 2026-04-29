# SellAI v3.6.0 更新说明

**版本**: 3.6.0  
**发布日期**: 2026-04-24  
**版本名称**: 核心功能激活版

---

## 📋 版本概述

v3.6.0 是 SellAI 的核心功能激活版本，正式激活了以下5大核心功能：

1. ✅ **分身自动执行** - 商机发现后自动创建分身团队
2. ✅ **AI-to-AI通信** - 分身间自主通信协作
3. ✅ **自我进化大脑激活** - 每日23:00自动复盘
4. ✅ **Memory V2决策集成** - 分层记忆优化推荐
5. ✅ **数据源优化** - 毛利门槛从60%降至45%

---

## 🆕 新增功能

### 1. 分身自动执行 (Auto Avatar Creation)

**功能描述**: 当发现高毛利商机时，系统自动创建分身团队并分配任务

**技术实现**:
- 修改 `src/monitor/monitor_routes.py` 中的 `MonitorService` 类
- 新增 `_create_avatars_for_opportunity()` 方法
- 自动创建3种专业分身：SEO专家、内容运营、运营经理

**API参数**:
```python
{
    "threshold": 45.0,      # 毛利门槛
    "auto_create": True      # 开启自动创建
}
```

**返回数据**:
```json
{
    "created_avatars": [
        {"avatar_id": "auto_seo_123", "name": "SEO专家-珠宝", "role": "seo"},
        {"avatar_id": "auto_content_123", "name": "内容运营-珠宝", "role": "content"},
        {"avatar_id": "auto_ops_123", "name": "运营经理-珠宝", "role": "operations"}
    ]
}
```

**新端点**:
- `GET /api/v2/avatar/auto/status` - 获取分身自动执行状态
- `POST /api/v2/avatar/auto/toggle` - 切换自动创建开关

---

### 2. AI-to-AI通信 (AI-to-AI Communication)

**功能描述**: 实现分身间的自主通信和任务分配

**新端点**:

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v2/collaboration/setup` | POST | 设置AI分身协作网络 |
| `/api/v2/collaboration/message` | POST | 分身间消息传递 |
| `/api/v2/collaboration/status/{id}` | GET | 获取协作状态 |

**协作模式**:
- `hierarchical` - 主分身→专业分身 (默认)
- `sequential` - 顺序执行
- `parallel` - 并行执行

**消息类型**:
- `task_assign` - 任务分配
- `status_update` - 状态更新
- `data_share` - 数据共享
- `request_help` - 请求协助

---

### 3. 自我进化大脑激活 (Self Evolution Brain Activation)

**功能描述**: 激活每日自动复盘功能，每天23:00自动执行

**技术实现**:
- 新增定时任务调度器 `_evolution_scheduler_worker()`
- 后台线程每分钟检查是否到达23:00
- 自动调用 `SelfEvolutionBrainController.execute_daily_review()`

**新端点**:
- `POST /api/v2/evolution/schedule` - 设置每日复盘定时任务
- `GET /api/v2/evolution/stats` - 获取进化统计数据

**返回示例**:
```json
{
    "evolution_metrics": {
        "total_reviews": 15,
        "last_review": "2026-04-23T23:00:00",
        "next_review": "2026-04-24T23:00:00",
        "strategy_improvements": 23,
        "performance_gain": "+12.5%"
    }
}
```

---

### 4. Memory V2决策集成 (Memory V2 Decision Integration)

**功能描述**: 在商机分析流程中集成分层记忆，优化推荐结果

**技术实现**:
- 新增 `_query_memory_for_context()` - 查询历史上下文
- 新增 `_record_decision_to_memory()` - 记录决策结果
- 商机返回数据包含 `memory_context` 字段

**记忆查询结果**:
```json
{
    "memory_context": {
        "has_history": true,
        "preferences": {
            "preferred_categories": ["珠宝饰品", "宠物用品"],
            "avoid_categories": ["低毛利商品"],
            "last_success_rate": 0.75
        },
        "recommendations": [
            "该类别历史表现良好，建议优先处理"
        ]
    }
}
```

---

### 5. 数据源优化 (Data Source Optimization)

**功能描述**: 调整毛利门槛和筛选逻辑，提高商机发现率

**配置变更**:

| 参数 | v3.5.x | v3.6.0 |
|------|--------|--------|
| 毛利门槛 | 60% | **45%** |
| 最低趋势分 | 0.7 | 0.7 |
| 刷新间隔 | 30分钟 | 30分钟 |

**新端点**:
- `GET /api/v2/datasource/config` - 获取数据源配置
- `POST /api/v2/datasource/config` - 更新数据源配置

---

## 🔧 修改内容

### main.py 修改

| 位置 | 修改类型 | 说明 |
|------|----------|------|
| 版本信息 | 更新 | 3.4.1 → 3.6.0 |
| MonitorRequest | 增强 | 新增 `auto_create` 参数 |
| `/api/v3/monitor/active` | 增强 | 支持分身自动创建 |
| 启动日志 | 增强 | 显示v3.6.0激活状态 |

### monitor_routes.py 修改

| 位置 | 修改类型 | 说明 |
|------|----------|------|
| MonitorService.__init__ | 新增 | 初始化分身自动执行配置 |
| MonitorService.scan_opportunities | 重写 | 集成分身创建和Memory V2 |
| MonitorService.get_status | 增强 | 显示v3.6.0功能状态 |

---

## 📝 API变更

### 兼容说明

- ✅ 所有现有API保持向后兼容
- ✅ 默认参数变更不影响现有调用
- ✅ 新增参数均为可选

### 请求示例

**商机监控 (v3.6.0)**:
```bash
curl -X POST http://localhost:8000/api/v3/monitor/active \
  -H "Content-Type: application/json" \
  -d '{
    "threshold": 45.0,
    "max_results": 5,
    "auto_create": true
  }'
```

**分身自动创建状态**:
```bash
curl http://localhost:8000/api/v2/avatar/auto/status
```

**版本检查**:
```bash
curl http://localhost:8000/api/v3/version/check
```

---

## 🚀 部署说明

### Railway 部署

1. 直接推送更新后的代码到GitHub
2. Railway会自动重新部署
3. 启动日志将显示:
   ```
   SellAI v3.6.0 核心功能激活版
   ✓ 分身自动执行：商机发现后自动创建分身团队
   ✓ AI-to-AI通信：分身间自主通信协作
   ✓ 自我进化大脑：每日23:00自动复盘
   ✓ Memory V2决策：分层记忆优化推荐
   ✓ 数据源优化：毛利门槛降至45%
   ```

### 环境变量

无需额外环境变量，现有的 `PORT` 和数据库配置保持不变。

---

## 📊 功能状态检查

部署后访问以下端点检查功能状态:

```bash
curl http://localhost:8000/api/v3/version/check
```

返回示例:
```json
{
    "version": "3.6.0",
    "all_features_active": true,
    "features": {
        "分身自动执行": true,
        "AI-to-AI通信": true,
        "自我进化大脑": true,
        "Memory V2集成": true,
        "数据源优化": true,
        "定时调度器": true
    },
    "summary": "6/6 个核心功能已激活"
}
```

---

## ⚠️ 注意事项

1. **分身管理器依赖**: 如果 `avatar_independent/avatar_manager.py` 不可用，分身自动创建将被静默跳过
2. **Memory V2依赖**: 如果Memory V2模块不可用，记忆功能将被静默跳过
3. **定时任务**: 自我进化复盘在应用启动后自动激活，无需手动调用
4. **毛利门槛**: 建议在30%-80%之间调整，过低可能增加噪音

---

## 📞 技术支持

如有问题，请检查:
1. 日志文件: `logs/sellai_v3.0.0.log`
2. 模块加载状态: 启动日志中的 ✓/✗ 标记
3. 功能检查: `/api/v3/version/check` 端点

---

**作者**: SellAI Team  
**版本**: 3.6.0  
**日期**: 2026-04-24
