# SellAI v3.4.0 WebSocket 测试指南

## 功能概述

v3.4.0 新增了 WebSocket 实时推送功能，实现以下能力：
- 商机数据更新实时推送
- 分身数据更新实时推送
- 守护进程状态推送
- 系统通知推送
- 指数退避重连机制
- 心跳保持连接

## WebSocket 端点

```
ws://localhost:8000/ws
```

## 消息格式

### 服务端推送消息

```json
{
    "type": "opportunities_update",
    "data": {
        "success": true,
        "total_items": 10,
        "success_categories": 5,
        "failed_categories": 0,
        "duration_seconds": 12.5,
        "crawl_time": "2026-04-18T12:00:00"
    },
    "summary": "商机扫描完成，发现10条新商机",
    "timestamp": "2026-04-18T12:00:00"
}
```

### 客户端发送消息

```json
// 心跳
"ping"

// 订阅频道
{"type": "subscribe", "channel": "all"}

// 获取守护进程状态
{"type": "get_status"}
```

## 测试方法

### 1. WebSocket 连接测试

使用浏览器控制台或 WebSocket 测试工具连接：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    console.log('连接成功');
    ws.send(JSON.stringify({type: 'subscribe', channel: 'all'}));
};

ws.onmessage = (event) => {
    console.log('收到消息:', event.data);
};
```

### 2. 使用 curl 测试（仅限创建连接）

```bash
# 注意：curl 的 websocket 支持需要特定版本
# 推荐使用 websocat 工具

# 安装 websocat (Linux/macOS)
curl -sL https://github.com/vi/websocat/releases/download/v1.8.4/websocat.x86_64-unknown-linux-musl.gz | zcat > websocat && chmod +x websocat

# 测试 WebSocket 连接
./websocat ws://localhost:8000/ws

# 发送订阅消息
echo '{"type":"subscribe","channel":"all"}' | ./websocat ws://localhost:8000/ws
```

### 3. 使用 Python 测试

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as websocket:
        # 发送订阅消息
        await websocket.send(json.dumps({
            "type": "subscribe",
            "channel": "all"
        }))
        print("已发送订阅消息")
        
        # 接收消息
        async for message in websocket:
            data = json.loads(message)
            print(f"收到消息: {data}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
```

### 4. 测试广播 API

```bash
# 测试 WebSocket 广播
curl -X POST http://localhost:8000/api/ws/test

# 获取 WebSocket 状态
curl http://localhost:8000/api/ws/status

# 手动广播消息
curl -X POST "http://localhost:8000/api/ws/broadcast?message_type=notification&content=测试消息"
```

## 消息类型

| 类型 | 说明 | 数据内容 |
|------|------|---------|
| `opportunities_update` | 商机更新 | success, total_items, success_categories, failed_categories |
| `avatars_update` | 分身更新 | avatars 数组 |
| `tasks_update` | 任务更新 | tasks 数组 |
| `daemon_status` | 守护进程状态 | 状态对象 |
| `notification` | 系统通知 | title, message, level |
| `pong` | 心跳回复 | timestamp |

## 注意事项

1. **跨域支持**: WebSocket 支持跨域访问，无需特殊配置
2. **重连机制**: 连接断开后自动重连，使用指数退避策略（最长30秒）
3. **心跳保活**: 每30秒发送一次心跳，保持连接活跃
4. **向后兼容**: 即使 WebSocket 不可用，页面仍可正常使用刷新按钮

## 故障排除

### 连接失败

1. 确认服务器已启动（`python main.py`）
2. 检查端口 8000 是否被占用
3. 查看服务器日志中的错误信息

### 消息接收不到

1. 确认连接状态为 OPEN
2. 检查是否正确发送了订阅消息
3. 查看浏览器控制台是否有错误

### 重连次数过多

1. 检查网络连接
2. 查看服务器是否正常响应
3. 确认没有防火墙阻止 WebSocket 连接
