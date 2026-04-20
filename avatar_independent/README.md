# SellAI v2.5.0 独立分身系统部署说明

## 版本信息
- **版本号**: v2.5.0
- **发布日期**: 2024年
- **核心特性**: 真正独立的分身系统

---

## 一、核心特性

### 1.1 独立运行架构
每个分身现在拥有：
- **独立进程**: 每个分身在独立线程中运行
- **独立内存**: 每个分身有独立的内存空间
- **独立记忆**: 每个分身有独立的SQLite数据库存储记忆
- **独立消息队列**: 每个分身有独立的收件箱/发件箱

### 1.2 独立人格系统
每个分身可以拥有不同的：
- **名字和语调**: professional, friendly, aggressive, casual
- **语言**: 中文、English、混合
- **专业领域**: 可指定多个专业领域
- **工作风格**: balanced, fast, thorough
- **沟通风格**: direct, diplomatic, detailed

### 1.3 分身协作协议
- **标准化通信**: 所有分身间通信使用统一协议
- **消息类型**: greet, task, help, learn, status, collaborate等
- **优先级机制**: LOW, NORMAL, HIGH, URGENT, CRITICAL
- **协作模式**: 主从、点对点、流水线、中心辐射

---

## 二、目录结构

```
SellAI部署包/
├── avatar_independent/           # 独立分身系统主目录
│   ├── __init__.py              # 系统初始化和便捷接口
│   ├── avatar_process.py         # 分身独立进程模块
│   ├── avatar_protocol.py        # 分身通信协议
│   ├── avatar_manager.py         # 分身管理器
│   ├── api_routes.py             # API路由（可选）
│   ├── data/                     # 分身数据目录
│   │   ├── avatars/              # 分身记忆数据库
│   │   │   └── avatar_xxx/
│   │   │       └── memory.db     # 独立记忆数据库
│   │   ├── queues/               # 消息队列目录
│   │   │   └── avatar_xxx_*.queue
│   │   ├── profiles/             # 分身档案目录
│   │   └── logs/                 # 日志目录
│   └── README.md                 # 本文档
├── main.py                       # 主程序（含独立分身API）
└── data/                         # 其他数据目录
```

---

## 三、快速开始

### 3.1 启动独立分身系统

独立分身系统在应用启动时自动初始化。确保 `avatar_independent/` 目录存在：

```bash
cd SellAI部署包
python main.py
```

### 3.2 创建第一个独立分身

通过API创建：

```bash
# 创建通用助手分身
curl -X POST "http://localhost:8000/api/v2/avatar/create" \
  -H "Content-Type: application/json" \
  -d '{"name": "小助手", "template": "general_assistant"}'

# 创建电商专家分身
curl -X POST "http://localhost:8000/api/v2/avatar/create" \
  -H "Content-Type: application/json" \
  -d '{"name": "电商专家", "template": "ecommerce_expert"}'
```

### 3.3 查看分身列表

```bash
curl "http://localhost:8000/api/v2/avatar/list"
```

### 3.4 查看分身状态

```bash
curl "http://localhost:8000/api/v2/avatar/{avatar_id}/status"
```

---

## 四、API 参考

### 4.1 系统管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v2/avatar/system/status` | 获取系统状态 |
| GET | `/api/v2/avatar/system/stats` | 获取系统统计 |
| GET | `/api/v2/avatar/templates` | 获取可用模板 |

### 4.2 分身管理

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v2/avatar/create` | 创建新分身 |
| POST | `/api/v2/avatar/create/batch` | 批量创建分身 |
| DELETE | `/api/v2/avatar/{avatar_id}` | 删除分身 |
| GET | `/api/v2/avatar/list` | 列出所有分身 |
| GET | `/api/v2/avatar/{avatar_id}/status` | 获取分身状态 |

### 4.3 消息通信

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v2/avatar/message` | 发送消息给分身 |
| POST | `/api/v2/avatar/message/broadcast` | 广播消息 |
| GET | `/api/v2/avatar/chat/history` | 获取对话历史 |

### 4.4 任务与协作

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v2/avatar/task/assign` | 分配任务 |
| POST | `/api/v2/avatar/collaborate` | 设置协作 |
| POST | `/api/v2/avatar/learn/share` | 分享经验 |

### 4.5 记忆管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v2/avatar/{avatar_id}/memory` | 获取分身记忆 |
| GET | `/api/v2/avatar/collective/knowledge` | 获取集体知识 |

---

## 五、可用分身模板

| 模板ID | 名称 | 专业领域 |
|--------|------|----------|
| `tiktok_expert` | TikTok运营专家 | 短视频创作、TikTok算法、流量获取 |
| `seo_master` | SEO优化大师 | SEO优化、关键词研究、网站排名 |
| `ecommerce_expert` | 跨境电商专家 | 跨境电商、供应链、店铺运营 |
| `influencer_negotiator` | 达人洽谈专家 | 达人合作、商务洽谈、社交媒体 |
| `general_assistant` | 全能助手 | 多领域、综合能力 |

---

## 六、代码示例

### 6.1 Python SDK 使用

```python
import sys
sys.path.append('SellAI部署包')

from avatar_independent import (
    get_avatar_system,
    create_avatar,
    list_all_avatars,
    get_avatar_status
)

# 初始化系统
system = get_avatar_system()

# 创建分身
avatar_id = system.manager.create_avatar(
    name="我的助手",
    template="general_assistant"
)

# 发送消息
system.manager.send_message(
    from_id="manager",
    to_id=avatar_id,
    message_type="greet",
    content={"message": "你好！"}
)

# 获取状态
status = system.manager.get_avatar_status(avatar_id)
print(status)
```

### 6.2 任务自动分配

```python
# 自动分配任务给最合适的分身
task_id = system.manager.assign_task_auto(
    task_type="product_research",
    task_data={"product_category": "electronics"},
    required_skills=["product_research", "market_analysis"]
)
```

### 6.3 设置协作

```python
# 设置点对点协作
system.manager.setup_collaboration(
    avatar_ids=["avatar_001", "avatar_002", "avatar_003"],
    pattern="peer_to_peer"
)

# 分享学习经验
system.manager.share_learning(
    from_id="avatar_001",
    experience={"type": "negotiation", "content": "谈判经验..."},
    lesson="在谈判中要善于倾听对方需求",
    share_with_all=True
)
```

---

## 七、数据存储

### 7.1 分身记忆数据库

每个分身有独立的SQLite数据库：
- **路径**: `avatar_independent/data/avatars/{avatar_id}/memory.db`
- **表结构**: memories (id, memory_type, content, metadata, created_at, access_count, importance)
- **特性**: 语义检索、重要性评分、访问统计

### 7.2 消息队列

基于文件的消息队列：
- **收件箱**: `avatar_independent/data/queues/avatar_{id}_inbox.queue`
- **发件箱**: `avatar_independent/data/queues/avatar_{id}_outbox.queue`
- **全局队列**: `avatar_independent/data/queues/global.queue`

---

## 八、协作模式

### 8.1 主从模式 (master_worker)
```
Manager
  ├── Worker-1
  ├── Worker-2
  └── Worker-3
```
- 主分身负责任务分配
- 从分身执行具体任务

### 8.2 点对点模式 (peer_to_peer)
```
Avatar-1 ←→ Avatar-2
    ↑           ↑
    └─────┬─────┘
          ↓
       Avatar-3
```
- 所有分身地位平等
- 互帮互助，共享知识

### 8.3 流水线模式 (pipeline)
```
Input → Stage-1 → Stage-2 → Stage-3 → Output
```
- 任务按阶段流转
- 每个分身负责特定阶段

### 8.4 中心辐射模式 (hub_spoke)
```
         Hub
        / | \
       /  |  \
   Spoke Spoke Spoke
```
- 中央分身协调边缘分身
- 所有通信经过中心

---

## 九、部署检查清单

### 9.1 环境要求
- Python 3.8+
- FastAPI
- Pydantic
- SQLite3 (内置)

### 9.2 目录权限
确保以下目录可写：
- `avatar_independent/data/`
- `avatar_independent/data/avatars/`
- `avatar_independent/data/queues/`
- `avatar_independent/data/profiles/`
- `avatar_independent/data/logs/`

### 9.3 启动验证
```bash
# 检查系统状态
curl "http://localhost:8000/api/v2/avatar/system/status"

# 预期输出
{
  "success": true,
  "initialized": true,
  "available_templates": ["tiktok_expert", "seo_master", ...]
}
```

---

## 十、故障排除

### 10.1 分身未启动
检查日志：`avatar_independent/data/logs/`

### 10.2 消息发送失败
- 检查队列目录权限
- 检查目标分身是否在线

### 10.3 记忆检索无结果
- 确认数据库文件存在
- 检查记忆是否已存储

---

## 十一、升级说明

### 从 v2.3.0 升级到 v2.5.0

1. 备份现有数据
2. 替换 `main.py`
3. 添加 `avatar_independent/` 目录
4. 重启服务

现有分身可以继续使用，新API需要通过 `/api/v2/avatar/*` 端点访问。

---

## 十二、联系支持

如有问题，请查看：
- API使用指南: `API使用指南.md`
- 整合完成报告: `整合完成报告.md`
