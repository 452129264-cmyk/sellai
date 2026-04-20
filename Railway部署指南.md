# SellAI Railway 部署指南

**适用版本**: v2.4.1  
**更新时间**: 2026-04-16

---

## 一、部署方式概述

| 方式 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| GitHub自动部署 | 简单、自动 | 需要GitHub仓库 | 生产环境 |
| Railway CLI | 可本地测试 | 需要安装CLI | 开发调试 |

---

## 二、GitHub 自动部署（推荐）

### 2.1 前置条件
- GitHub 账号
- Railway 账号（已连接 GitHub）

### 2.2 部署步骤

#### 步骤1: 推送代码到GitHub
```bash
# 进入代码目录
cd sellai_repo

# 添加远程仓库（如果尚未添加）
git remote -v
# 如果没有输出，执行：
git remote add origin https://github.com/452129264-cmyk/sellai.git

# 推送代码
git add .
git commit -m "deploy: v2.4.1 threshold修复版本"
git push -u origin main
```

#### 步骤2: Railway 自动检测
Railway 会自动检测 GitHub 推送，触发部署

#### 步骤3: 验证部署
```bash
# 健康检查
curl https://sellai-production-8397.up.railway.app/api/health

# 预期输出:
# {"status":"healthy","version":"2.4.1","stores_count":18,"timestamp":"..."}
```

### 2.3 触发重新部署
如果部署未自动触发：
1. 登录 https://railway.app
2. 进入项目 → Deployments
3. 点击右上角 "Deploy" 按钮

---

## 三、Railway CLI 部署

### 3.1 安装 Railway CLI
```bash
# macOS/Linux
curl -fsSL https://railway.app/install.sh | sh

# 或使用 npm
npm install -g @railway/cli
```

### 3.2 登录 Railway
```bash
railway login
```

### 3.3 部署步骤
```bash
# 进入项目目录
cd sellai_repo

# 初始化项目（如果尚未初始化）
railway init

# 部署
railway up

# 获取部署URL
railway domain
```

### 3.4 本地测试
```bash
# 运行本地服务器
railway run python main.py

# 或使用 uvicorn
railway run uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 四、Docker 部署

### 4.1 构建镜像
```bash
cd sellai_repo
docker build -t sellai-api .
```

### 4.2 运行容器
```bash
docker run -p 8000:8000 sellai-api
```

### 4.3 Railway Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 五、验证部署成功

### 5.1 健康检查
```bash
curl https://sellai-production-8397.up.railway.app/api/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "2.4.1",
  "stores_count": 18,
  "timestamp": "2026-04-16T13:00:00.000000"
}
```

### 5.2 测试 threshold 参数
```bash
# 测试60%毛利门槛
curl -s -X POST "https://sellai-production-8397.up.railway.app/api/monitor/active" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 60, "max_results": 3}' | jq '.threshold'

# 预期输出: 60.0
```

### 5.3 检查版本号
```bash
curl https://sellai-production-8397.up.railway.app/ | jq '.version'

# 预期输出: "2.4.1"
```

---

## 六、常见问题

### Q1: 部署失败怎么办？
1. 检查 Railway 部署日志
2. 确认 requirements.txt 依赖完整
3. 确认 Dockerfile 正确

### Q2: 如何回滚？
1. Railway 控制台 → Deployments
2. 选择之前的版本
3. 点击 "Redeploy"

### Q3: 如何查看日志？
```bash
railway logs
```

### Q4: 如何设置环境变量？
```bash
railway variables set FIRECRAWL_API_KEY=fc-xxx
```

---

## 七、环境变量配置

### 必需变量
| 变量名 | 说明 | 示例 |
|--------|------|------|
| FIRECRAWL_API_KEY | Firecrawl API密钥 | fc-xxx |

### 可选变量
| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| LOG_LEVEL | 日志级别 | INFO |
| PORT | 端口 | 8000 |

---

## 八、部署检查清单

- [ ] 代码已推送到 GitHub
- [ ] Railway 检测到推送
- [ ] 部署状态为 "Deployed"
- [ ] 健康检查通过
- [ ] threshold 参数正确生效
- [ ] 版本号显示为 2.4.1

---

## 九、快速部署命令

```bash
# 一键部署（假设 railway 已配置）
cd sellai_repo && git add . && git commit -m "deploy v2.4.1" && git push
```

---

## 十、技术支持

如有问题，请检查：
1. Railway 部署日志
2. GitHub Actions 状态
3. API 健康端点
