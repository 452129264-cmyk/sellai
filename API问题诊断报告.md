# SellAI API 问题诊断报告

**生成时间**: 2026-04-16  
**诊断范围**: 主API + 备用API

---

## 一、问题概述

| API | 地址 | 版本 | 状态 |
|-----|------|------|------|
| 主API | https://genuine-insight-production-15b4.up.railway.app | v3.2.0 | ❌ 502错误 |
| 备用API | https://sellai-production-8397.up.railway.app | v2.4.0 | ⚠️ 运行但threshold参数不生效 |

---

## 二、主API 502错误分析

### 2.1 问题现象
- 主API持续返回502 Bad Gateway
- 频繁出现连接超时

### 2.2 可能原因分析

#### 原因1: 代码过于复杂
- **v3.2.0版本代码量**: ~87KB (main.py)
- **v2.4.0版本代码量**: ~38KB (main.py)
- 大量模块导入可能超时

#### 原因2: 依赖导入问题
```python
# v3.2.0 尝试导入大量模块
from src.health_monitor import HealthMonitor, HealthStatus
from src.global_business_brain import GlobalBusinessBrain
from src.avatar_collaboration_optimizer import AvatarCollaborationOptimizer
# ... 更多导入
```

#### 原因3: 启动超时
- Railway 默认启动超时: 60秒
- v3.2.0完整导入可能超过限制

### 2.3 建议方案
1. **立即修复**: 使用v2.4.0简化版代码
2. **长期方案**: 优化v3.2.0的模块导入延迟加载

---

## 三、备用API threshold参数Bug分析

### 3.1 问题现象
```bash
# 请求
curl -X POST "https://sellai-production-8397.up.railway.app/api/monitor/active" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 60, "max_results": 3}'

# 响应 (threshold=30.0，无视请求的60)
{"threshold": 30.0, "high_margin_count": 0, ...}
```

### 3.2 根本原因
Railway上运行的代码是**旧版本**，使用Query参数：
```python
# ❌ 旧版本代码 (Railway当前运行)
@app.post("/api/monitor/active")
async def monitor_opportunities(
    threshold: float = Query(60.0, description="毛利门槛"),
    max_results: int = Query(3, description="最多处理数")
):
```

### 3.3 修复后代码
```python
# ✅ 新版本代码 (本地测试通过)
@app.post("/api/monitor/active")
async def monitor_opportunities(
    threshold: float = Body(45.0, description="毛利门槛，默认45%"),
    max_results: int = Body(3, description="最多处理商机数")
):
```

### 3.4 问题根因
- **Query参数**: 客户端需要使用URL查询参数传递
  - 例如: `/api/monitor/active?threshold=60&max_results=3`
- **Body参数**: 客户端需要使用JSON body传递
  - 例如: `{"threshold": 60, "max_results": 3}`

---

## 四、GitHub代码状态

```
sellai_repo (本地克隆):
├── 分支: main
├── 本地提交: d813d89 (fix: threshold参数从Query改为Body)
└── 状态: 领先远程1个提交
```

### 最新提交内容
```bash
commit d813d89
fix: threshold参数从Query改为Body，默认值改为45%

变更文件:
├── main.py (v3.2.0 → v2.4.0简化版)
├── src/deploy_store.sh
├── src/store_generator.py
├── templates/checkout.html
└── templates/store.html
```

---

## 五、诊断结论

| 问题 | 根本原因 | 解决方案 |
|------|----------|----------|
| 主API 502 | 代码过复杂+启动超时 | 部署v2.4.0简化版 |
| threshold不生效 | Railway运行旧版代码 | 推送并重新部署最新代码 |

---

## 六、修复优先级

1. **P0 (紧急)**: 推送GitHub最新代码到Railway备用API
2. **P1 (重要)**: 评估v3.2.0主API是否需要精简部署
3. **P2 (优化)**: 添加健康检查和自动重启机制
