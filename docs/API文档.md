# SellAI v3.0.0 API文档
## 终极完整版

---

## 基础信息

- **基础URL**: `http://localhost:8000`
- **API版本**: v3.0.0
- **文档地址**: `/docs` (Swagger UI)
- **Redoc地址**: `/redoc`

---

## 认证方式

部分API需要API密钥认证，请通过以下方式获取：

```bash
POST /api/v3/security/apikey
{
    "name": "my-app",
    "permissions": ["read", "write"],
    "expires_days": 90
}
```

---

## 通用响应格式

### 成功响应
```json
{
    "success": true,
    "data": { ... }
}
```

### 错误响应
```json
{
    "success": false,
    "error": "错误信息",
    "detail": "详细说明"
}
```

---

## 基础端点

### 健康检查
```http
GET /health
```

**响应示例:**
```json
{
    "status": "healthy",
    "version": "3.0.0",
    "uptime_seconds": 3600,
    "modules": {
        "self_evolution": "active",
        "memory_v2": "active",
        "business_brain": "active",
        "avatar_market": "active"
    },
    "modules_active": "24/24"
}
```

### 版本信息
```http
GET /api/v3/version
```

### 模块状态
```http
GET /api/v3/modules
```

---

## 全域商业大脑 `/api/v3/business`

### 生成商业洞察
```http
POST /api/v3/business/insight
Content-Type: application/json

{
    "insight_type": "market_trend",
    "context": {
        "market": "电商",
        "period": "Q1"
    },
    "data_sources": ["ecommerce", "social"]
}
```

### 市场分析
```http
POST /api/v3/business/market
Content-Type: application/json

{
    "market_name": "短视频电商",
    "data_sources": ["platform_data"]
}
```

### 竞品分析
```http
POST /api/v3/business/competitor
Content-Type: application/json

{
    "competitor_name": "竞品A",
    "data_sources": ["public_data"]
}
```

### 需求预测
```http
POST /api/v3/business/demand
Content-Type: application/json

{
    "product_id": "prod_001",
    "forecast_days": 30
}
```

---

## AI分身市场 `/api/v3/marketplace`

### 创建商品
```http
POST /api/v3/marketplace/listing
Content-Type: application/json

{
    "title": "电商运营助手",
    "description": "专业的电商运营AI助手",
    "listing_type": "avatar_template",
    "category": "电商运营",
    "tags": ["电商", "运营", "客服"],
    "pricing_model": "subscription",
    "price": 99.99,
    "capabilities": ["商品管理", "数据分析"]
}
```

### 搜索商品
```http
POST /api/v3/marketplace/search
Content-Type: application/json

{
    "query": "电商",
    "category": "电商运营",
    "min_price": 50,
    "max_price": 200,
    "min_rating": 4.0,
    "limit": 20
}
```

### 获取精选
```http
GET /api/v3/marketplace/featured
```

### 创建评价
```http
POST /api/v3/marketplace/review
Content-Type: application/json

{
    "listing_id": "listing_001",
    "buyer_id": "user_001",
    "rating": 5.0,
    "title": "非常好用！",
    "content": "这个AI助手帮我提升了30%的运营效率",
    "pros": ["功能强大", "响应快速"],
    "cons": ["价格略高"]
}
```

### 市场统计
```http
GET /api/v3/marketplace/stats
```

---

## 达人外联引擎 `/api/v3/influencer`

### 添加达人
```http
POST /api/v3/influencer/add
Content-Type: application/json

{
    "name": "科技评测达人",
    "platform": "tiktok",
    "handle": "@techreviewer",
    "profile_url": "https://tiktok.com/@techreviewer",
    "follower_count": 2500000,
    "categories": ["科技", "数码"],
    "engagement_rate": 5.8
}
```

### 搜索达人
```http
POST /api/v3/influencer/search
Content-Type: application/json

{
    "platform": "tiktok",
    "categories": ["科技", "数码"],
    "min_followers": 100000,
    "min_engagement": 3.0,
    "limit": 20
}
```

### 创建推广活动
```http
POST /api/v3/influencer/campaign
Content-Type: application/json

{
    "name": "新品发布推广",
    "description": "为新产品寻找测评达人",
    "campaign_type": "product_review",
    "target_platforms": ["tiktok", "instagram"],
    "target_categories": ["科技", "数码"],
    "target_tiers": ["macro", "micro"],
    "budget": 50000,
    "deadline": "2025-05-01",
    "deliverables": ["1分钟测评视频", "3张图片"],
    "compensation": "免费产品+5000元"
}
```

### 发起外联
```http
POST /api/v3/influencer/outreach
Content-Type: application/json

{
    "influencer_id": "inf_001",
    "campaign_id": "camp_001",
    "contact_method": "email",
    "message_template": "initial_contact"
}
```

### 外联统计
```http
GET /api/v3/influencer/stats
```

---

## 社交关系管理 `/api/v3/social`

### 创建用户
```http
POST /api/v3/social/user
Content-Type: application/json

{
    "username": "john_doe",
    "display_name": "John Doe",
    "email": "john@example.com"
}
```

### 创建关系
```http
POST /api/v3/social/relationship
Content-Type: application/json

{
    "from_user_id": "user_001",
    "to_user_id": "user_002",
    "relationship_type": "follower"
}
```

### 创建社群
```http
POST /api/v3/social/community
Content-Type: application/json

{
    "name": "电商交流群",
    "description": "电商从业者交流社区",
    "owner_id": "user_001"
}
```

### 记录互动
```http
POST /api/v3/social/interaction
Content-Type: application/json

{
    "user_id": "user_001",
    "target_type": "post",
    "target_id": "post_001",
    "interaction_type": "comment",
    "content": "写得真好！"
}
```

---

## 安全系统 `/api/v3/security`

### 生成API密钥
```http
POST /api/v3/security/apikey
Content-Type: application/json

{
    "name": "我的应用",
    "permissions": ["read", "write", "admin"],
    "expires_days": 90
}
```

### 封禁IP
```http
POST /api/v3/security/block
Content-Type: application/json

{
    "ip_address": "192.168.1.100",
    "reason": "恶意请求",
    "duration_hours": 24
}
```

### 获取安全事件
```http
GET /api/v3/security/events?level=high
```

### 获取审计日志
```http
GET /api/v3/security/audit?user_id=user_001&limit=100
```

---

## 健康监控 `/api/v3/health`

### 健康检查
```http
POST /api/v3/health/check?component=all
```

### 记录指标
```http
POST /api/v3/health/metric
Content-Type: application/json

{
    "name": "cpu_percent",
    "value": 45.5,
    "unit": "%",
    "tags": {"host": "server-1"}
}
```

### 创建告警
```http
POST /api/v3/health/alert
Content-Type: application/json

{
    "level": "warning",
    "title": "CPU使用率过高",
    "message": "CPU使用率达到85%",
    "component": "system"
}
```

### 获取健康报告
```http
GET /api/v3/health/report?period=24h
```

---

## 邀请裂变 `/api/v3/invitation`

### 创建邀请
```http
POST /api/v3/invitation/create
Content-Type: application/json

{
    "inviter_id": "user_001"
}
```

### 获取邀请统计
```http
GET /api/v3/invitation/stats?inviter_id=user_001
```

### 获取用户余额
```http
GET /api/v3/invitation/balance?user_id=user_001
```

### 创建裂变活动
```http
POST /api/v3/invitation/campaign
Content-Type: application/json

{
    "name": "邀请好友活动",
    "description": "邀请好友得优惠券",
    "reward_rule_ids": ["rule_001", "rule_002"],
    "start_date": "2025-04-01",
    "end_date": "2025-05-01",
    "referral_limit": 100
}
```

---

## 任务调度 `/api/v3/task`

### 创建任务
```http
POST /api/v3/task/create
Content-Type: application/json

{
    "name": "数据同步任务",
    "handler": "sync_data",
    "payload": {"source": "shopify", "target": "warehouse"},
    "priority": 2,
    "task_type": "async",
    "timeout": 300
}
```

### 获取任务
```http
GET /api/v3/task/{task_id}
```

### 取消任务
```http
POST /api/v3/task/{task_id}/cancel
```

### 任务统计
```http
GET /api/v3/task/stats
```

---

## 短视频分发 `/api/v3/video`

### 连接平台账号
```http
POST /api/v3/video/account
Content-Type: application/json

{
    "platform": "tiktok",
    "username": "my_account",
    "access_token": "xxx",
    "display_name": "My TikTok"
}
```

### 创建视频内容
```http
POST /api/v3/video/content
Content-Type: application/json

{
    "title": "新品测评",
    "description": "最新产品全面测评",
    "hashtags": ["#测评", "#科技", "#新品"],
    "mentions": ["@brand"],
    "language": "zh"
}
```

### 创建发布任务
```http
POST /api/v3/video/publish
Content-Type: application/json

{
    "content_id": "content_001",
    "platform": "tiktok",
    "account_id": "acc_001",
    "scheduled_time": "2025-04-15T10:00:00"
}
```

### 分发统计
```http
GET /api/v3/video/stats
```

---

## 聊天系统 `/api/v3/chat`

### 创建聊天
```http
POST /api/v3/chat/create
Content-Type: application/json

{
    "name": "技术支持群",
    "chat_type": "group",
    "created_by": "user_001",
    "members": ["user_001", "user_002", "user_003"]
}
```

### 发送消息
```http
POST /api/v3/chat/message
Content-Type: application/json

{
    "chat_id": "chat_001",
    "sender_id": "user_001",
    "message_type": "text",
    "content": "大家好！",
    "metadata": {}
}
```

### 获取消息
```http
GET /api/v3/chat/{chat_id}/messages?limit=50
```

### 获取上下文
```http
GET /api/v3/chat/{chat_id}/context?limit=10
```

---

## 佣金计算 `/api/v3/commission`

### 计算佣金
```http
POST /api/v3/commission/calculate
Content-Type: application/json

{
    "user_id": "user_001",
    "source_user_id": "user_002",
    "order_id": "order_001",
    "amount": 1000.00,
    "level": 0
}
```

### 获取余额
```http
GET /api/v3/commission/balance?user_id=user_001
```

### 获取历史
```http
GET /api/v3/commission/history?user_id=user_001&status=settled
```

---

## 数据同步 `/api/v3/sync`

### 写入数据
```http
POST /api/v3/sync/put
Content-Type: application/json

{
    "key": "product:001",
    "value": {"name": "产品A", "price": 99},
    "metadata": {"source": "shopify"}
}
```

### 获取数据
```http
GET /api/v3/sync/get/product:001
```

### 设置状态
```http
POST /api/v3/sync/state
Content-Type: application/json

{
    "key": "app_mode",
    "value": "production",
    "locker_id": "system"
}
```

### 获取状态
```http
GET /api/v3/sync/state/app_mode
```

---

## 行业资源 `/api/v3/resource`

### 导入资源
```http
POST /api/v3/resource/import
Content-Type: application/json

{
    "name": "电商产品分类表",
    "description": "标准化的电商产品分类数据",
    "industry": "ecommerce",
    "resource_type": "dataset",
    "source": "官方",
    "tags": ["分类", "标准化"]
}
```

### 搜索资源
```http
GET /api/v3/resource/search?industry=ecommerce&resource_type=dataset
```

---

## 保留API (v2.x)

以下API保持向后兼容：

- `POST /api/v2/negotiation/ai-engine` - AI谈判引擎
- `POST /api/v2/aigc/generate` - AIGC生成
- `POST /api/v2/evolution/review` - 每日复盘
- `POST /api/v2/memory/manage` - 记忆管理
- `POST /api/v2/orchestrator/task` - 任务编排
- `POST /api/v2/hyperhorse/video` - 视频生成

---

## 错误代码

| 代码 | 说明 |
|------|------|
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

---

## 限流说明

| 端点类型 | 限制 |
|----------|------|
| 普通API | 100次/分钟 |
| 写入API | 50次/分钟 |
| 大文件上传 | 10次/分钟 |

---

*文档更新时间: 2025-04-10*
