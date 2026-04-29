# SellAI v3.4.0 变更日志

## 版本信息

- **版本号**: v3.4.0
- **发布日期**: 2026-04-18
- **版本名称**: WebSocket实时推送版

## 核心更新

### WebSocket 实时推送功能

#### 后端 (main.py)

1. **新增 WebSocket 端点**: `/ws`
   - 支持客户端连接和消息收发
   - 处理心跳 `ping/pong`
   - 支持订阅频道功能

2. **新增 WebSocket 连接管理器**: `WebSocketConnectionManager`
   - 线程安全的管理器
   - 支持广播消息给所有客户端
   - 自动清理断开的连接

3. **新增广播函数**: `broadcast_to_websockets(message)`
   - 异步广播消息给所有连接的客户端
   - 支持多种消息类型

4. **新增测试 API**:
   - `GET /api/ws/status` - 获取连接状态
   - `POST /api/ws/test` - 测试广播
   - `POST /api/ws/broadcast` - 手动广播

#### 守护进程 (src/scrapling/daemon_service.py)

1. **新增爬取完成通知**: `_notify_websocket_clients()`
   - 爬取完成后自动通知客户端
   - 支持导入调用和 HTTP 回调两种方式
   - 非阻塞执行，不影响爬取性能

#### 前端 (frontend/js/app.js)

1. **新增 WebSocket 客户端**
   - 自动连接和重连
   - 指数退避重连策略
   - 心跳保活机制

2. **新增消息处理函数**
   - `handleOpportunitiesUpdate()` - 商机更新
   - `handleAvatarsUpdate()` - 分身更新
   - `handleTasksUpdate()` - 任务更新
   - `handleNotification()` - 系统通知

3. **新增 UI 更新**
   - 导航栏显示连接状态
   - Toast 通知推送消息
   - 页面数据自动刷新

## 文件变更清单

| 文件路径 | 变更类型 | 说明 |
|---------|---------|------|
| `main.py` | 修改 | 添加 WebSocket 支持，更新版本号到 v3.4.0 |
| `src/scrapling/daemon_service.py` | 修改 | 添加爬取完成通知函数 |
| `frontend/js/app.js` | 修改 | 添加 WebSocket 客户端代码 |
| `WebSocket测试指南.md` | 新增 | WebSocket 测试说明文档 |

## 消息格式

### 推送消息示例

```json
{
    "type": "opportunities_update",
    "data": {
        "success": true,
        "total_items": 15,
        "success_categories": 7,
        "failed_categories": 0,
        "duration_seconds": 45.2
    },
    "summary": "商机扫描完成，发现15条新商机",
    "timestamp": "2026-04-18T12:00:00"
}
```

## 兼容性

- ✅ 向后兼容现有 API
- ✅ 不依赖 WebSocket，连接失败不影响正常功能
- ✅ 自动降级为手动刷新

## 使用建议

1. **生产环境**: 建议使用 Nginx/HAProxy 进行 WebSocket 负载均衡
2. **长连接管理**: 当前使用内存存储，适合小规模用户（<1000并发）
3. **监控**: 建议监控 `/api/ws/status` 端点的连接数

## 测试方法

详见 [WebSocket测试指南.md](./WebSocket测试指南.md)

```bash
# 启动服务
cd SellAI部署包
python main.py

# 测试 WebSocket
curl http://localhost:8000/api/ws/status

# 测试广播
curl -X POST http://localhost:8000/api/ws/test
```
