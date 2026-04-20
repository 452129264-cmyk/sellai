# SellAI v3.2.2 GitHub 推送指南

**版本**: v3.2.2  
**时间**: 2026-04-17  
**修复内容**: 502错误修复 + 预测性记忆系统集成

---

## 一、修复内容

### 1. 502错误修复（核心问题）
- **Dockerfile健康检查等待时间**：从5秒增加到120秒
- **预测性记忆系统**：采用延迟加载，避免阻塞应用启动
- **健康检查超时**：从10秒增加到15秒

### 2. 预测性记忆系统集成
新增API端点：
- `POST /api/memory/remember` - 记忆经验
- `POST /api/memory/predict` - 预测
- `GET /api/memory/stats` - 统计信息
- `GET /api/memory/health` - 健康检查

### 3. 代码变更
- main.py: 3010行（原2874行，新增136行预测性记忆API）
- Dockerfile: 健康检查参数优化
- src/predictive_memory/: 8个核心模块文件

---

## 二、推送步骤

### 2.1 下载部署包
下载文件：`SellAI_v3.2.2_修复502问题_带预测性记忆.tar.gz`

### 2.2 解压并进入目录
```bash
tar -xzvf SellAI_v3.2.2_修复502问题_带预测性记忆.tar.gz
cd SellAI部署包
```

### 2.3 初始化Git仓库（如果是新目录）
```bash
git init
git remote add origin https://github.com/452129264-cmyk/sellai.git
```

### 2.4 添加并提交代码
```bash
git add -A
git commit -m "feat: v3.2.2 修复502问题 + 集成预测性记忆系统

修复内容：
1. Dockerfile健康检查等待时间从5s增加到120s
2. 预测性记忆系统采用延迟加载
3. 新增API端点：
   - POST /api/memory/remember
   - POST /api/memory/predict
   - GET /api/memory/stats
   - GET /api/memory/health
4. 健康检查端点添加predictive_memory模块状态
"
```

### 2.5 推送到GitHub
```bash
git push -u origin main
```

---

## 三、Railway 部署

推送成功后，Railway会自动检测并部署。

### 3.1 查看部署状态
1. 登录 https://railway.app
2. 进入 sellai 项目
3. 查看 Deployments

### 3.2 验证部署成功
```bash
# 健康检查（等待2分钟后再测试）
curl https://your-app.railway.app/health

# 预期输出：
# {"status":"healthy","version":"3.2.0",...,"predictive_memory":"active"}

# 预测性记忆系统健康检查
curl https://your-app.railway.app/api/memory/health

# 预期输出：
# {"status":"healthy","available":true,"system":"predictive_memory","version":"3.2.2"}

# 测试预测性记忆
curl -X POST https://your-app.railway.app/api/memory/predict \
  -H "Content-Type: application/json" \
  -d '{"context": {"product": "无线蓝牙耳机"}, "prediction_type": "causal"}'

# 测试记忆功能
curl -X POST https://your-app.railway.app/api/memory/remember \
  -H "Content-Type: application/json" \
  -d '{"event": "测试商机发现", "outcome": "毛利45%", "importance": 0.8}'
```

---

## 四、版本对比

| 版本 | main.py行数 | 健康检查等待 | 预测性记忆 |
|------|-------------|--------------|-----------|
| v3.2.0 | 2874行 | 5秒 | ❌ |
| v3.2.2 | 3010行 | 120秒 | ✅ |

---

## 五、回滚方案

如果部署失败，可回滚到上一版本：
1. Railway控制台 → Deployments → 选择上一版本 → Revert
