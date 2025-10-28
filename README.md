# TG DGN Bot - Telegram 支付与会员系统

[![CI](https://github.com/Jack123-UU/tg_dgn_bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Jack123-UU/tg_dgn_bot/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 项目简介

完整的 Telegram Bot 数字服务平台，提供 Premium 会员直充、USDT 余额管理、地址查询等功能。

### ✨ 核心特性

- 🔐 **TRC20 USDT 支付系统** - 固定地址 + 0.001-0.999 唯一后缀
- 💎 **Premium 会员直充** - 自动交付 Telegram Premium
- 💰 **余额管理系统** - 充值、扣费、记录查询
- 🔍 **地址查询功能** - 波场地址验证 + 30分钟限频
- 🎯 **模块化架构** - 清晰的代码组织和扩展性

## ✅ 功能实现状态

| 功能 | 状态 | Issue |
|------|------|-------|
| TRC20 USDT 支付系统 | ✅ | [#1](https://github.com/Jack123-UU/tg_dgn_bot/issues/1) |
| Premium 会员直充 | ✅ | [#2](https://github.com/Jack123-UU/tg_dgn_bot/issues/2) |
| 个人中心余额充值 | ✅ | [#3](https://github.com/Jack123-UU/tg_dgn_bot/issues/3) |
| 地址查询 + 限频 | ✅ | [#4](https://github.com/Jack123-UU/tg_dgn_bot/issues/4) |
| 能量兑换/闪租 | 🔲 | - |
| 免费克隆 | 🔲 | - |
| 联系客服 | 🔲 | - |

## 📁 项目结构

```
tg_dgn_bot/
├── src/
│   ├── bot.py                      # 🤖 Bot 主程序入口
│   ├── menu/                       # 主菜单模块
│   │   └── main_menu.py            # /start 命令和主菜单
│   ├── payments/                   # 支付模块（Issue #1）
│   │   ├── suffix_manager.py       # 后缀管理器 (0.001-0.999池)
│   │   ├── amount_calculator.py    # 金额计算器 (整数化精度)
│   │   └── order.py                # 订单状态管理
│   ├── premium/                    # Premium 模块（Issue #2）
│   │   ├── handler.py              # 对话处理器
│   │   ├── recipient_parser.py     # 收件人解析器
│   │   └── delivery.py             # 交付服务
│   ├── wallet/                     # 钱包模块（Issue #3）
│   │   ├── wallet_manager.py       # 余额管理器
│   │   └── profile_handler.py      # 个人中心处理器
│   ├── address_query/              # 地址查询模块（Issue #4）
│   │   ├── validator.py            # 地址验证器
│   │   ├── explorer.py             # 浏览器链接生成
│   │   └── handler.py              # 查询处理器
│   ├── webhook/                    # Webhook 模块
│   │   └── trc20_handler.py        # TRC20 回调处理器
│   ├── config.py                   # 配置管理
│   ├── database.py                 # 数据库模型（SQLAlchemy）
│   ├── models.py                   # Pydantic 模型
│   └── signature.py                # HMAC 签名验证
├── scripts/                        # 🛠️ 管理脚本
│   ├── start_bot.sh                # 启动 Bot
│   ├── stop_bot.sh                 # 停止 Bot
│   └── validate_config.py          # 配置验证工具
├── tests/                          # 🧪 测试套件（142 测试）
│   ├── test_*.py                   # 单元测试
│   └── conftest.py                 # 测试配置
├── .env.example                    # 环境变量模板
├── requirements.txt                # 项目依赖
└── README.md                       # 本文档
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- Redis 7.0+
- SQLite 3 (或其他 SQLAlchemy 支持的数据库)

### 2. 配置环境

```bash
# 1. 克隆项目
git clone https://github.com/Jack123-UU/tg_dgn_bot.git
cd tg_dgn_bot

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
vim .env  # 编辑配置
```

### 3. 必需配置项

编辑 `.env` 文件：

```bash
# Telegram Bot
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# USDT TRC20 Payment
USDT_TRC20_RECEIVE_ADDR=TYourUSDTReceiveAddress  # 波场收款地址

# HMAC Signature
WEBHOOK_SECRET=your_webhook_secret_key            # 签名密钥

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 订单设置
ORDER_TIMEOUT_MINUTES=30
```

### 4. 验证配置

```bash
python3 scripts/validate_config.py
```

### 5. 启动 Bot

```bash
# 方式 1: 使用启动脚本（推荐）
./scripts/start_bot.sh

# 方式 2: 直接运行
python3 -m src.bot

# 停止 Bot
./scripts/stop_bot.sh
```

## 🎯 Bot 使用指南

### 用户命令

| 命令 | 说明 |
|------|------|
| `/start` | 显示主菜单 |
| `/help` | 显示帮助信息 |
| `/premium` | 购买 Premium 会员 |
| `/profile` | 个人中心（余额管理）|
| `/cancel` | 取消当前操作 |

### 功能流程

#### 💎 Premium 直充
1. 点击 "Premium直充" 或发送 `/premium`
2. 选择套餐（3/6/12 个月）
3. 输入收件人（支持 @username 或 t.me/ 链接）
4. 确认订单并支付 USDT
5. 自动交付到收件人账户

#### 💰 余额充值
1. 点击 "个人中心" 或发送 `/profile`
2. 选择 "充值 USDT"
3. 输入充值金额
4. 转账到指定地址（精确到 3 位小数）
5. 2-5 分钟自动到账

#### 🔍 地址查询
1. 点击 "地址查询"
2. 输入波场地址（T 开头 34 位）
3. 查看地址信息
4. 点击按钮访问区块链浏览器
## 🧪 测试

### 运行测试

```bash
# 运行完整测试套件
python -m pytest tests/ -v

# 跳过 Redis 集成测试（仅核心测试）
python -m pytest tests/ -m "not redis" -v

# 运行特定模块测试
python -m pytest tests/test_address_validator.py -v
python -m pytest tests/test_wallet.py -v
```

### 测试覆盖

- **总测试数**: 142 个
  - 80 个核心功能测试（无需 Redis/Database）
  - 20 个钱包模块测试（SQLite 内存数据库）
  - 22 个地址查询测试（SQLite 内存数据库）
  - 20 个 Redis 集成测试

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| Bot 框架 | python-telegram-bot v21 |
| 异步 HTTP | httpx |
| 配置管理 | Pydantic Settings |
| 数据库 | SQLAlchemy 2.0 + SQLite |
| 缓存 | Redis 7.0+ |
| 测试 | pytest + pytest-asyncio |
| CI/CD | GitHub Actions |

## 📊 数据库设计

### SQLite 表结构

```sql
-- 用户表
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance_micro_usdt INTEGER DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
);

-- 充值订单表
CREATE TABLE deposit_orders (
    order_id TEXT PRIMARY KEY,
    user_id INTEGER,
    base_amount REAL,
    unique_suffix INTEGER,
    total_amount REAL,
    amount_micro_usdt INTEGER,
    status TEXT,  -- PENDING, PAID, EXPIRED
    tx_hash TEXT,
    created_at DATETIME,
    paid_at DATETIME,
    expires_at DATETIME
);

-- 扣费记录表
CREATE TABLE debit_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount_micro_usdt INTEGER,
    order_type TEXT,
    related_order_id TEXT,
    created_at DATETIME
);

-- 地址查询限频表
CREATE TABLE address_query_logs (
    user_id INTEGER PRIMARY KEY,
    last_query_at DATETIME,
    query_count INTEGER DEFAULT 1
);
```

## 🔐 安全特性

- ✅ **HMAC-SHA256 签名验证** - 防止回调伪造
- ✅ **订单幂等性保证** - 防止重复支付
- ✅ **金额整数化计算** - 避免浮点误差
- ✅ **并发保护** - 余额扣费使用行级锁
- ✅ **限频机制** - 30 分钟/人查询限制
- ✅ **自动过期回收** - Redis TTL 管理订单生命周期

**CI/CD：**

- GitHub Actions 自动运行所有 101 个测试
- 使用真实 Redis 7 服务（docker service）
- Python 3.11 & 3.12 矩阵测试
- 自动健康检查和连接等待

## 🔧 API 接口

### 主要端点

- `POST /webhook/trc20` - 处理TRC20支付回调（支持Premium自动交付）
- `GET /health` - 健康检查
- `GET /stats` - 获取订单统计信息
- `POST /test/create-order` - 创建测试订单
- `POST /test/simulate-payment` - 模拟支付回调

### Telegram Bot 命令

- `/premium` - 开始 Premium 会员购买流程
- `/order_status <order_id>` - 查询订单状态
- `/cancel` - 取消当前操作

### 支付回调格式

```json
{
  "order_id": "订单ID",
  "amount": 10.123,
  "txid": "交易哈希",
  "timestamp": 1635724800,
  "signature": "HMAC签名",
  "order_type": "premium"  // 可选：指定订单类型
}
```

## 🚀 使用示例

### Issue #1: 创建支付订单

```python
from src.payments.order import order_manager

# 创建普通订单
order = await order_manager.create_order(
    user_id=123456,
    base_amount=10.0
)

print(f"订单ID: {order.order_id}")
print(f"应付金额: {order.total_amount:.3f} USDT")  # 例如: 10.123 USDT
```

### Issue #2: Premium 会员购买流程

**1. 用户发起购买**

```
用户: /premium
Bot: 显示套餐选择（3/6/12个月）
```

**2. 选择套餐**

```
用户: 点击 "3个月 - $10"
Bot: 请输入收件人用户名
```

**3. 输入收件人**

```
用户: @alice
      @bob
      t.me/charlie
Bot: 显示订单确认
     - 套餐：3个月 Premium
     - 收件人：3人
     - 应付：10.123 USDT
```

**4. 确认支付**

```
用户: 点击 "确认支付"
Bot: 订单已创建，请转账至指定地址
```

**5. 自动交付**

```
用户支付后 2-5 分钟：
- 系统检测到支付
- 自动调用 Premium 交付服务
- 向收件人发送 Premium 礼物
- 更新订单状态为 DELIVERED/PARTIAL
```

### Premium API 示例

```python
from src.premium.handler import PremiumHandler
from src.premium.recipient_parser import RecipientParser
from src.models import OrderType

# 解析收件人
text = "@alice @bob t.me/charlie"
recipients = RecipientParser.parse(text)
# 结果: ['alice', 'bob', 'charlie']

# 创建 Premium 订单
order = await order_manager.create_order(
    user_id=123456,
    base_amount=10.0,
    order_type=OrderType.PREMIUM,
    premium_months=3,
    recipients=['alice', 'bob', 'charlie']
)
```

## 💡 核心技术特性

### 1. 唯一后缀管理

- **后缀范围**: 0.001 - 0.999 (999个可用)
- **并发安全**: Redis 分布式锁确保唯一性
- **自动过期**: 30分钟TTL自动释放
- **原子操作**: Lua脚本确保一致性

### 2. 金额精度处理

```python
# 避免浮点误差的整数化计算
micro_usdt = int(amount * 1000000)  # 转为微USDT
```

### 3. 签名安全机制

```python
# HMAC-SHA256 签名生成
signature = hmac.new(
    secret.encode('utf-8'),
    message.encode('utf-8'),
    hashlib.sha256
).hexdigest()
```

### 4. 幂等更新保障

- 同一订单多次回调仅处理一次
- 状态转换验证（PENDING→PAID）
- 原子性状态更新

## 📊 性能指标

- **并发支持**: 300+ 订单同时创建无冲突
- **响应时间**: < 100ms 订单创建
- **精度保证**: 6位小数精度（微USDT级别）
- **可用性**: 999个唯一后缀支持高频交易

## 🧪 测试覆盖

### 单元测试

- 后缀分配/释放机制
- 金额匹配逻辑（浮点精度）
- HMAC签名验证
- 订单状态管理
- 过期清理机制

### 集成测试

- 端到端支付流程
- 并发后缀分配
- 回调处理验证
- 安全性测试

### 功能验证

```bash
# 运行完整功能验证
python verify_functionality.py
```

## 🔒 安全特性

- **HMAC签名**: 防止回调数据篡改
- **时间戳验证**: 防止重放攻击
- **地址格式验证**: 确保波场地址合法性
- **金额范围检查**: 防止异常金额
- **幂等性保护**: 防止重复处理

## 📈 扩展性设计

- **微服务架构**: 模块化设计便于扩展
- **Redis集群**: 支持水平扩展
- **异步处理**: 支持高并发请求
- **配置驱动**: 灵活的环境配置

## 🐛 故障排除

### 常见问题

1. **后缀分配失败**
   - 检查Redis连接状态
   - 确认是否达到999个并发上限

2. **签名验证失败**
   - 检查WEBHOOK_SECRET配置
   - 确认数据格式正确

3. **订单状态异常**
   - 检查订单是否过期
   - 确认状态转换逻辑

### 日志调试

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python -m src.webhook
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如有问题或建议，请通过以下方式联系：

- 创建 Issue
- 发送邮件至项目维护者
- 参与讨论
