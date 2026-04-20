# Railway 环境变量配置指南

## 方法1：Railway Dashboard（推荐）

1. 登录 Railway: https://railway.app/
2. 进入你的项目
3. 点击项目 → Settings → Variables
4. 添加以下变量：

```
DEEPSEEK_API_KEY = sk-e4be4293bd3542c593df4c02ec0074e1
DEEPSEEK_BASE_URL = https://api.deepseek.com/v1
DEEPSEEK_MODEL = deepseek-chat
BAILIAN_API_KEY = sk-1632361458d0485183fb21cdaeda3bce
BAILIAN_IMAGE_MODEL = wanx-v1
```

5. 点击 Save
6. Railway 会自动重新部署

## 方法2：Railway CLI

```bash
# 安装 Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 链接项目
railway link

# 设置环境变量
railway variables set DEEPSEEK_API_KEY=sk-e4be4293bd3542c593df4c02ec0074e1
railway variables set DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
railway variables set DEEPSEEK_MODEL=deepseek-chat
railway variables set BAILIAN_API_KEY=sk-1632361458d0485183fb21cdaeda3bce
railway variables set BAILIAN_IMAGE_MODEL=wanx-v1
```

## 验证配置

部署完成后访问：
```
GET https://你的域名/api/config/api-status
```

预期返回：
```json
{
  "success": true,
  "config": {
    "deepseek": {
      "available": true,
      "model": "deepseek-chat"
    },
    "bailian": {
      "available": true,
      "image_model": "wanx-v1"
    }
  }
}
```
