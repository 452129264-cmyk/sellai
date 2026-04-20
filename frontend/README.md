# SellAI 前端界面

> SellAI 智能电商AI助手 - 前端界面项目

## 📋 项目简介

SellAI 是一个主动AI电商助手系统的前端界面，用于连接电商平台、社交媒体，发现商机并实现自动化运营。

## 🎯 核心功能

### 1. 仪表盘
- 关键数据统计（今日商机、活跃分身、已绑定店铺、社媒账号）
- 热门商机展示
- 快捷操作入口
- 系统状态监控

### 2. 社媒绑定管理
- 支持7大平台：Facebook、TikTok、Instagram、小红书、微博、抖音、快手
- OAuth授权/API凭证绑定
- 账号状态管理
- Token刷新

### 3. 店铺绑定管理
- 支持6大电商平台：淘宝、拼多多、抖音小店、Shopify、Shopee、Amazon
- 多店铺统一管理
- 连接测试
- 商品同步状态

### 4. 商机分析
- 多条件筛选（分类、毛利区间、数据源）
- 商机详情展示
- 毛利分析
- 趋势追踪

### 5. AI图片生成
- 文生图模式
- 图生图模式
- 多种尺寸选择
- 生成历史记录

### 6. 分身管理
- 5种分身模板（TikTok专家、SEO大师、电商专家、达人谈判、通用助手）
- 分身状态控制（启动/停止）
- 任务管理

### 7. 系统设置
- 个人资料管理
- API配置
- 通知设置
- 监控参数配置

## 🛠 技术栈

- **HTML5** - 语义化标签
- **CSS3** - Tailwind CSS (CDN) + 自定义样式
- **JavaScript** - 原生ES6+
- **UI组件** - Font Awesome Icons
- **字体** - Google Fonts (Inter)

## 📁 项目结构

```
SellAI部署包/frontend/
├── index.html              # 主入口文件
├── css/
│   └── styles.css           # 自定义样式
├── js/
│   ├── config.js            # 配置文件
│   ├── api.js               # API封装
│   ├── mock-data.js         # 模拟数据
│   ├── components.js        # UI组件
│   └── app.js               # 主应用逻辑
└── README.md                # 项目说明
```

## 🚀 快速开始

### 方式一：直接打开
直接用浏览器打开 `index.html` 文件即可预览（默认使用Mock模式）。

### 方式二：本地服务器
```bash
# 使用Python
cd SellAI部署包/frontend
python -m http.server 8080

# 或使用Node.js
npx serve .
```

访问 `http://localhost:8080` 查看。

## ⚙️ 配置说明

### API配置
在设置页面可以配置：
- API服务器地址（默认使用备用API）
- API密钥
- Mock模式开关

### Mock模式
开启Mock模式后，所有数据使用本地模拟数据，无需连接后端API，便于离线预览和开发。

## 🔗 后端API对接

项目已对接以下API端点：

### 认证
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/profile` - 获取用户信息

### 社媒管理
- `GET /api/social/accounts` - 获取已绑定账号
- `POST /api/social/bind` - 绑定账号
- `DELETE /api/social/unbind/{platform}` - 解绑账号

### 店铺管理
- `GET /api/shops` - 获取已绑定店铺
- `POST /api/shops/bind` - 绑定店铺
- `DELETE /api/shops/unbind/{shop_id}` - 解绑店铺

### 商机监控
- `POST /api/monitor/active` - 启动主动监控
- `GET /api/monitor/notifications` - 获取通知

### 商机分析
- `POST /api/analysis/opportunity` - 分析商机

### 图片生成
- `POST /api/image/text2image` - 文生图
- `POST /api/image/image2image` - 图生图

### 分身系统
- `GET /api/v2/avatar/list` - 获取分身列表
- `POST /api/v2/avatar/create` - 创建分身
- `POST /api/v2/avatar/start` - 启动分身
- `POST /api/v2/avatar/stop` - 停止分身

## 📱 响应式设计

- 桌面端（>1024px）- 完整导航栏
- 平板端（768px-1024px）- 自适应布局
- 移动端（<768px）- 侧边导航菜单

## 🎨 设计特点

- **深色主题** - 科技感、专业感
- **玻璃态效果** - 现代UI风格
- **渐变配色** - 丰富的视觉层次
- **流畅动画** - 自然的交互反馈

## 🔧 扩展开发

### 添加新的社媒平台
在 `config.js` 的 `SOCIAL_PLATFORMS` 数组中添加：
```javascript
{
    id: 'new_platform',
    name: '新平台',
    icon: 'fa-icon',
    color: '#hex',
    bgGradient: 'from-color-500/20 to-color-600/10',
    description: '描述'
}
```

### 添加新的店铺平台
在 `config.js` 的 `SHOP_PLATFORMS` 数组中添加。

### 添加新的分身模板
在 `config.js` 的 `AVATAR_TEMPLATES` 数组中添加。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！
