# SellAI API 配置指南

## 快速开始

### 1. 获取 API Key

#### DeepSeek（推理引擎）
1. 访问 https://platform.deepseek.com/
2. 注册账号并登录
3. 进入「API Keys」页面
4. 点击「创建 API Key」
5. 复制生成的 Key（格式：sk-xxxxxxxx）

**费用**: 
- 充值最低 ¥10 即可使用
- 价格约 ¥0.001/千token（约等于免费）
- 新用户有免费额度

#### 百炼（图片生成）
1. 访问 https://bailian.console.aliyun.com/
2. 使用阿里云账号登录
3. 开通「百炼」服务
4. 进入「API-KEY管理」
5. 创建并复制 API Key

**费用**:
- 图片生成约 ¥0.08/张
- 新用户有免费额度（约100张）

### 2. 配置环境变量

#### Railway 部署
在 Railway 项目设置中添加环境变量：
```
DEEPSEEK_API_KEY=sk-你的key
BAILIAN_API_KEY=你的百炼key
```

#### 本地开发
复制 `.env.example` 为 `.env` 并填入 Key：
```bash
cp .env.example .env
# 编辑 .env 文件
```

### 3. 验证配置

启动服务后访问：
```
GET /api/config/api-status
```

返回示例：
```json
{
  "deepseek": {
    "available": true,
    "model": "deepseek-chat"
  },
  "bailian": {
    "available": true,
    "image_model": "wanx-v1"
  }
}
```

## 功能说明

### DeepSeek 用于：
- 预测性记忆推理
- 商机分析
- SEO优化建议
- 文案生成
- 多语言翻译

### 百炼用于：
- 电商产品图生成
- 营销海报设计
- 商品主图优化

## 成本估算

| 使用场景 | 预估月成本 |
|---------|-----------|
| 轻度使用（每日100次推理+10张图） | ¥20-50 |
| 中度使用（每日500次推理+50张图） | ¥100-200 |
| 重度使用（每日2000次推理+200张图） | ¥500-800 |

**对比 OpenAI GPT-4**：同等使用量需 ¥2000-5000/月

## 常见问题

### Q: DeepSeek 和 GPT-4 差距大吗？
A: 对于电商场景的推理、分析任务，差距不大。复杂创意写作略弱。

### Q: 百炼图片质量如何？
A: 通义万相适合电商产品图、海报。创意艺术图可用 Midjourney。

### Q: 可以只用 DeepSeek 不用百炼吗？
A: 可以，但无法使用图片生成功能。推理功能完全正常。

### Q: API Key 泄露了怎么办？
A: 立即在对应平台删除旧 Key 并创建新 Key。
