# 电商平台API接入指南

本文档详细说明如何为SellAI接入淘宝、拼多多、抖音三大电商平台的开放API。

## 目录

1. [淘宝开放平台](#1-淘宝开放平台)
2. [拼多多开放平台](#2-拼多多开放平台)
3. [抖音开放平台](#3-抖音开放平台)
4. [配置文件设置](#4-配置文件设置)
5. [常见问题](#5-常见问题)

---

## 1. 淘宝开放平台

### 1.1 开放平台入口
- **官网**: https://open.taobao.com/
- **淘宝联盟**: https://pub.alimama.com/
- **开发者文档**: https://open.taobao.com/doc.htm

### 1.2 注册认证流程

#### Step 1: 注册开发者账号
1. 访问淘宝开放平台官网
2. 使用淘宝账号登录（如无可使用支付宝账号注册）
3. 完成实名认证（个人/企业）

#### Step 2: 创建应用
1. 进入「开发者中心」→「应用管理」
2. 点击「创建应用」
3. 选择应用类型：
   - **自用型应用**：仅自己使用
   - **工具型应用**：可提供给其他商家使用
4. 填写应用基本信息

#### Step 3: 申请API权限
1. 在应用详情页点击「API权限」
2. 搜索并申请需要的API权限：
   - `taobao.tbk.item.info.get` - 淘宝客商品信息
   - `taobao.tbk.item.convert` - 淘宝客链接转换
   - `taobao.tbk.order.get` - 订单查询
   - `taobao.tbk.material.optimals` - 物料搜索

### 1.3 API Key申请步骤

1. 在应用详情页获取：
   - **AppKey**: 应用唯一标识
   - **AppSecret**: 应用密钥（请妥善保管）

2. 配置OAuth授权回调地址：
   - 进入「应用设置」→「授权回调地址」
   - 填写你的回调URL

### 1.4 签名算法说明

淘宝API使用HMAC-MD5签名：

```python
import hashlib
import hmac

def generate_sign(params, app_secret):
    # 1. 参数排序
    sorted_params = sorted(params.items())
    # 2. 拼接字符串
    sign_str = "".join(f"{k}{v}" for k, v in sorted_params)
    # 3. HMAC-MD5加密
    sign = hmac.new(
        app_secret.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.md5
    ).hexdigest().upper()
    return sign
```

### 1.5 调用示例

```python
from src.ecommerce_taobao import TaobaoAPI

# 初始化
api = TaobaoAPI(
    app_key="your_app_key",
    app_secret="your_app_secret",
    access_token="user_access_token"
)

# 商品搜索
result = api.search_items(
    keyword="无线蓝牙耳机",
    page=1,
    page_size=20,
    sort="tk_total_sales_desc"
)

# 商品详情
result = api.get_item_detail("123456789")

# 订单查询
result = api.get_order_list(status="settled")
```

---

## 2. 拼多多开放平台

### 2.1 开放平台入口
- **官网**: https://open.pinduoduo.com/
- **多多进宝**: https://ddxq.mobi/
- **开发者文档**: https://open.pinduoduo.com/document/

### 2.2 注册认证流程

#### Step 1: 注册多多客账号
1. 访问多多进宝官网
2. 使用手机号注册账号
3. 完成实名认证

#### Step 2: 申请成为推广者
1. 登录多多进宝
2. 进入「个人中心」→「我的API」
3. 申请API接口权限

#### Step 3: 创建应用
1. 访问拼多多开放平台
2. 创建应用获取Client ID和Client Secret

### 2.3 API Key申请步骤

1. 在开放平台获取：
   - **Client ID**: 应用标识
   - **Client Secret**: 应用密钥

2. 获取授权码：
   - 用户授权后获取authorization_code
   - 使用code换取access_token

### 2.4 签名算法说明

拼多多API使用MD5签名：

```python
import hashlib

def generate_sign(params, client_secret):
    # 1. 参数排序
    sorted_keys = sorted(params.keys())
    # 2. 拼接字符串
    sign_str = "".join(f"{k}{params[k]}" for k in sorted_keys if k != "sign")
    # 3. 头部尾部拼接client_secret
    sign_str = client_secret + sign_str + client_secret
    # 4. MD5加密
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
    return sign
```

### 2.5 调用示例

```python
from src.ecommerce_pdd import PddAPI

# 初始化
api = PddAPI(
    client_id="your_client_id",
    client_secret="your_client_secret",
    access_token="user_access_token"
)

# 商品搜索
result = api.pdd_ddk_goods_search(
    keyword="运动鞋",
    page=1,
    page_size=20,
    sort_type=4,  # 按销量降序
    with_coupon=True
)

# 商品详情
result = api.pdd_ddk_goods_detail(["123456789"])

# 订单查询
result = api.pdd_order_list_get(order_status=5)  # 已结算
```

---

## 3. 抖音开放平台

### 3.1 开放平台入口
- **官网**: https://open.douyin.com/
- **抖音电商**: https://creator.douyin.com/
- **开发者文档**: https://open.douyin.com/platform/

### 3.2 注册认证流程

#### Step 1: 注册开发者账号
1. 访问抖音开放平台
2. 使用抖音账号登录
3. 完成开发者认证（个人/企业）

#### Step 2: 创建应用
1. 进入「控制台」→「应用管理」
2. 点击「创建应用」
3. 选择应用类型：
   - **小程序**
   - **网站应用**
   - **移动应用**

#### Step 3: 申请电商权限
1. 在应用详情页点击「接口权限」
2. 申请电商相关接口：
   - `/product/*` - 商品接口
   - `/order/*` - 订单接口
   - `/shop/*` - 店铺接口

### 3.3 API Key申请步骤

1. 在应用详情页获取：
   - **Client Key**: 应用标识
   - **Client Secret**: 应用密钥

2. 配置授权回调地址：
   - 进入「应用设置」→「授权回调域」
   - 填写你的回调URL

### 3.4 签名算法说明

抖音API使用HMAC-SHA256+Base64签名：

```python
import hmac
import hashlib
import base64

def generate_sign(params, client_secret):
    # 1. 过滤空值并排序
    filtered = {k: v for k, v in params.items() if v}
    sorted_params = sorted(filtered.items())
    # 2. 拼接字符串
    sign_str = "&".join(f"{k}={v}" for k, v in sorted_params)
    # 3. HMAC-SHA256加密
    sign = hmac.new(
        client_secret.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha256
    ).digest()
    # 4. Base64编码
    return base64.b64encode(sign).decode('utf-8')
```

### 3.5 调用示例

```python
from src.ecommerce_douyin import DouyinAPI

# 初始化
api = DouyinAPI(
    app_id="your_app_id",
    app_secret="your_app_secret",
    access_token="user_access_token"
)

# 商品列表
result = api.product_list(
    page=1,
    size=20,
    status=1  # 上架状态
)

# 商品详情
result = api.product_detail("123456789")

# 订单列表
result = api.order_list(
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now(),
    order_status=5  # 已完成
)

# 订单发货
result = api.order_deliver(
    order_id="123456",
    express_company="SF",
    express_no="SF123456789"
)
```

---

## 4. 配置文件设置

将获取的API凭证填入 `ecommerce_config.json`：

```json
{
  "taobao": {
    "app_key": "your_taobao_app_key",
    "app_secret": "your_taobao_app_secret",
    "access_token": "",
    "redirect_uri": "https://your-domain.com/callback",
    "status": "pending"
  },
  "pdd": {
    "client_id": "your_pdd_client_id",
    "client_secret": "your_pdd_client_secret",
    "access_token": "",
    "status": "pending"
  },
  "douyin": {
    "app_id": "your_douyin_client_key",
    "app_secret": "your_douyin_client_secret",
    "access_token": "",
    "sandbox_mode": false,
    "redirect_uri": "https://your-domain.com/callback",
    "status": "pending"
  }
}
```

### 配置说明

| 字段 | 说明 |
|------|------|
| `app_key` / `client_id` / `app_id` | 平台分配的APP标识 |
| `app_secret` / `client_secret` / `app_secret` | APP密钥（请妥善保管） |
| `access_token` | OAuth授权后的访问令牌 |
| `redirect_uri` | OAuth回调地址 |
| `status` | 配置状态（pending/active/error） |

---

## 5. 常见问题

### Q1: 如何获取Access Token？
**淘宝/抖音**：通过OAuth2.0授权流程，用户授权后换取access_token
**拼多多**：同样通过OAuth授权获取

### Q2: Token过期怎么办？
每个平台都提供Token刷新接口，请定期刷新Token：
- 淘宝：`taobao.refresh.token`
- 拼多多：使用refresh_token换取新token
- 抖音：调用刷新接口

### Q3: API调用频率限制？
各平台都有不同的限流策略：
- 淘宝：不同API有不同配额
- 拼多多：按开发者等级限流
- 抖音：按接口类型限制

### Q4: 如何处理签名错误？
1. 检查app_secret是否正确
2. 确保参数拼接顺序正确
3. 确认签名方法（MD5/HMAC-SHA256）
4. 检查编码格式（UTF-8）

### Q5: 如何调试API调用？
1. 使用各平台的沙箱环境测试
2. 查看API返回的错误码和消息
3. 检查日志文件 `logs/ecommerce.log`

---

## API端点一览

### 淘宝API
| 方法 | 说明 |
|------|------|
| `GET /api/ecommerce/taobao/item` | 获取商品详情 |
| `POST /api/ecommerce/taobao/search` | 商品搜索 |
| `GET /api/ecommerce/taobao/orders` | 订单列表 |

### 拼多多API
| 方法 | 说明 |
|------|------|
| `POST /api/ecommerce/pdd/search` | 多多进宝商品搜索 |
| `GET /api/ecommerce/pdd/orders` | 订单列表 |

### 抖音API
| 方法 | 说明 |
|------|------|
| `GET /api/ecommerce/douyin/products` | 商品列表 |
| `POST /api/ecommerce/douyin/product` | 创建商品 |
| `GET /api/ecommerce/douyin/orders` | 订单列表 |

### 统一接口
| 方法 | 说明 |
|------|------|
| `POST /api/ecommerce/search` | 统一商品搜索（支持多平台） |
| `GET /api/ecommerce/orders` | 统一订单查询 |
| `GET /api/ecommerce/status` | 平台配置状态 |

---

如有问题，请查看日志文件或联系技术支持。
