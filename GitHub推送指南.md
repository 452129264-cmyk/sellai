# GitHub 推送指南

**版本**: v2.4.1  
**时间**: 2026-04-16

---

## 一、当前状态

```
本地分支: main
领先远程: 1个提交 (d813d89)
状态: 待推送
```

### 待推送提交
```
d813d89 fix: threshold参数从Query改为Body，默认值改为45%
```

### 提交内容
- 修复 threshold 参数不生效的 Bug
- 将毛利门槛从 60% 调整为 45%
- 简化代码（v3.2.0 → v2.4.0）

---

## 二、推送步骤

### 2.1 验证远程仓库
```bash
cd sellai_repo
git remote -v
```

预期输出：
```
origin  https://github.com/452129264-cmyk/sellai.git (fetch)
origin  https://github.com/452129264-cmyk/sellai.git (push)
```

### 2.2 执行推送
```bash
cd sellai_repo
git push origin main
```

### 2.3 验证推送成功
```bash
git log --oneline origin/main -3
```

---

## 三、Railway 自动部署

推送成功后，Railway 会自动：
1. 检测 GitHub 推送
2. 拉取最新代码
3. 重新部署应用

预计部署时间：1-3分钟

---

## 四、验证部署

### 4.1 检查 Railway 状态
1. 登录 https://railway.app
2. 进入 sellai-production 项目
3. 查看 Deployments 状态

### 4.2 API 验证
```bash
# 健康检查
curl https://sellai-production-8397.up.railway.app/api/health

# 预期输出:
# {"status":"healthy","version":"2.4.1",...}

# 测试 threshold 参数
curl -s -X POST "https://sellai-production-8397.up.railway.app/api/monitor/active" \
  -H "Content-Type: application/json" \
  -d '{"threshold": 60, "max_results": 3}' | grep threshold

# 预期输出: "threshold":60.0
```

---

## 五、如果推送失败

### 5.1 检查网络
```bash
ping github.com
```

### 5.2 检查凭证
```bash
git remote -vv
```

如果需要重新认证：
```bash
git remote set-url origin https://452129264-cmyk@github.com/452129264-cmyk/sellai.git
```

### 5.3 强制推送（谨慎使用）
```bash
git push origin main --force
```

---

## 六、推送日志

### 6.1 最近推送记录
查看 `sellai_git_push_log.md` 获取历史推送记录

### 6.2 推送后更新日志
```bash
# 追加到推送日志
echo "2026-04-16: 推送 v2.4.1 threshold修复版本" >> sellai_git_push_log.md
```

---

## 七、注意事项

1. **不要推送敏感信息** - 确保 .env 和 credentials 不在代码中
2. **先推送再部署** - 等待 Railway 完成部署
3. **验证后再结束** - 确认 API 正常工作后再离开

---

## 八、完整命令

```bash
cd sellai_repo
git push origin main && echo "推送成功，等待 Railway 部署..." && sleep 60 && curl https://sellai-production-8397.up.railway.app/api/health
```
