# 能量兑换功能文档

## 📖 功能概述

能量兑换模块提供 TRON 波场能量租用服务，支持三种兑换方式：

1. **⚡ 时长能量** - 6.5万/13.1万能量，1小时有效

2. **📦 笔数套餐** - 弹性笔数，按次扣费

3. **🔄 闪兑** - USDT直接兑换能量（即将上线）

## 🎯 功能特性

### 时长能量

- **6.5万能量**: 3 TRX/笔
- **13.1万能量**: 6 TRX/笔

- **有效期**: 1小时
- **购买范围**: 1-20笔

- **支付方式**: 余额扣费（TRX按1:7汇率折算USDT）

### 笔数套餐

- **扣费规则**: 对方地址有U扣1笔，无U扣2笔
- **每笔价格**: 3.6 TRX (约0.5 USDT)

- **起售金额**: 5 USDT
- **使用要求**: 每天至少使用一次，否则扣2笔

- **支付方式**: USDT余额扣费

## 🏗️ 技术架构

### 模块结构

```text
src/energy/
├── __init__.py           # 模块导出

├── models.py             # 数据模型（订单、套餐、状态）

├── client.py             # API客户端（对接trxno.com）

├── manager.py            # 订单管理器（创建、支付、查询）

└── handler.py            # Bot处理器（对话流程）

```text

### 数据流程

```text
用户请求 → Bot Handler → Order Manager → API Client → trxno.com
   ↓           ↓              ↓              ↓            ↓
 Telegram   创建订单      余额扣费      购买能量     交付能量

```text

### 数据库设计

**`energy_orders` 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | VARCHAR | 订单ID（主键）|
| user_id | INTEGER | 用户TG ID |
| order_type | VARCHAR | 订单类型（hourly/package/flash）|
| energy_amount | INTEGER | 能量数量（65000/131000）|
| purchase_count | INTEGER | 购买笔数（1-20）|
| package_count | INTEGER | 套餐笔数 |
| usdt_amount | FLOAT | USDT金额 |
| receive_address | VARCHAR | 接收地址 |
| total_price_trx | FLOAT | 总价(TRX) |
| total_price_usdt | FLOAT | 总价(USDT) |
| status | VARCHAR | 状态（PENDING/PROCESSING/COMPLETED/FAILED）|
| api_order_id | VARCHAR | API订单ID |
| error_message | VARCHAR | 错误信息 |
| created_at | DATETIME | 创建时间 |
| completed_at | DATETIME | 完成时间 |

**索引**:

- `idx_energy_user_status` (user_id, status)
- `idx_energy_order_type` (order_type)

## 🔌 API 对接

### 服务商信息

- **主URL**: <https://trxno.com>
- **备用URL**: <https://trxfast.com>

- **认证方式**: username + password

### 关键API端点

#### 1. 账号信息查询

```python
POST /api/account
Body: {
    "username": "your_username",
    "password": "your_password"
}
Response: {
    "code": 10000,
    "data": {
        "balance": 100.5,        # TRX余额

        "balance_usdt": 50.0,    # USDT余额

        "frozen_balance": 0.0     # 冻结余额

    }
}

```text

#### 2. 价格查询

```python
POST /api/price
Response: {
    "code": 10000,
    "data": {
        "energy_65k": 3.0,       # 6.5万能量价格

        "energy_131k": 6.0,      # 13.1万能量价格

        "package_price": 3.6     # 笔数套餐价格

    }
}

```text

#### 3. 购买时长能量

```python
POST /api/buyenergy
Body: {
    "username": "your_username",
    "password": "your_password",
    "re_type": "ENERGY",
    "re_address": "TXxx...xxx",  # 接收地址

    "re_value": 65000,           # 能量数量

    "rent_time": 1               # 租用时长（小时）

}
Response: {
    "code": 10000,
    "msg": "购买成功",
    "data": {
        "order_id": "ORDER_123456"
    }
}

```text

#### 4. 购买笔数套餐

```python
POST /api/buypackage
Body: {
    "username": "your_username",
    "password": "your_password",
    "re_address": "TXxx...xxx"
}
Response: {
    "code": 10000,
    "msg": "购买成功",
    "data": {
        "order_id": "ORDER_123456",
        "package_count": 140      # 获得笔数

    }
}

```text

### 状态码说明

| 状态码 | 说明 |
|--------|------|
| 10000 | 请求执行成功 |
| 10001 | 参数不正确 |
| 10002 | 余额不足 |
| 10003 | 用户名或密码不正确 |
| 10004 | 订单不存在 |
| 10005 | 激活地址失败 |
| 10009 | 地址未激活 |
| 10010 | 服务器错误 |
| 10011 | 已存在笔数订单 |

## 💻 使用流程

### Bot 使用步骤

### 1. 时长能量购买

```text
用户: 点击 "⚡ 能量兑换"
Bot:  显示兑换类型选择

用户: 选择 "⚡ 时长能量"
Bot:  显示套餐选择（6.5万/13.1万）

用户: 选择 "6.5万能量"
Bot:  提示输入购买笔数

用户: 输入 "5"
Bot:  提示输入接收地址

用户: 输入 "TXxx...xxx"
Bot:  显示订单确认
      - 套餐: 6.5万能量

      - 笔数: 5笔

      - 总价: 15 TRX (约2.14 USDT)

用户: 确认购买
Bot:  扣费 → 调用API → 能量发送
      ✅ 购买成功！能量已发送到您的地址

```text

### 2. 笔数套餐购买

```text
用户: 点击 "⚡ 能量兑换"
Bot:  显示兑换类型选择

用户: 选择 "📦 笔数套餐"
Bot:  提示输入充值金额（USDT）

用户: 输入 "10"
Bot:  提示输入接收地址
      充值金额: 10 USDT
      预计笔数: 约140笔

用户: 输入 "TXxx...xxx"
Bot:  显示订单确认
      - 笔数套餐

      - 金额: 10 USDT

      - 预计笔数: 约140笔

      - 弹性扣费: 有U扣1笔，无U扣2笔

用户: 确认购买
Bot:  扣费 → 调用API → 笔数激活
      ✅ 购买成功！笔数套餐已激活

```text

## ⚙️ 配置说明

### 环境变量

在 `.env` 文件中添加：

```bash

# 能量API配置

ENERGY_API_USERNAME=your_trxno_username
ENERGY_API_PASSWORD=your_trxno_password
ENERGY_API_BASE_URL=https://trxno.com
ENERGY_API_BACKUP_URL=https://trxfast.com

```text

### 后台设置

登录 [trxfast.com 后台](https://trxfast.com) 进行配置：

#### 1. 出租功能设置

```text
打开/关闭能量出租功能: 开启
出租地址: 填写你的TRX收款地址
每6.5万能量价格: 3 TRX
每13.1万能量价格: 6 TRX
一次最大可购买笔数: 20

```text

#### 2. 笔数套餐设置

```text
笔数套餐销售类型: 弹性笔数
套餐TRX起售价: 系统自动设置
套餐USDT起售价: 5
笔数折扣设置: （可选）

```text

#### 3. 地址设置

```text
⚠️ 重要提示:
填写的地址必须是专用的，不能用来收除能量租用外的任何款，
否则会自动购买成能量或笔数，造成损失平台不负责。

```text

## 🧪 测试流程

### 1. 配置测试

```bash

# 验证配置

python3 scripts/validate_config.py

# 应显示:

# ✅ 能量API配置已设置

```text

### 2. API连接测试

```python

# 测试账号查询

python3 -c "
import asyncio
from src.energy.client import EnergyAPIClient
from src.config import settings

async def test():
    client = EnergyAPIClient(
        username=settings.energy_api_username,
        password=settings.energy_api_password
    )
    info = await client.get_account_info()
    print(f'✅ 账号余额: {info.balance_trx} TRX')
    await client.close()

asyncio.run(test())
"

```text

### 3. 功能测试

```bash

# 启动Bot

./scripts/start_bot.sh

# Telegram测试

1. 发送 /start
2. 点击 "⚡ 能量兑换"
3. 选择 "⚡ 时长能量"
4. 选择 "6.5万能量"
5. 输入笔数: 1
6. 输入地址: TXxx...xxx
7. 确认购买
8. 验证能量到账

```text

## 📊 监控和日志

### 订单查询

```bash

# 查看能量订单

sqlite3 tg_bot.db "SELECT * FROM energy_orders ORDER BY created_at DESC LIMIT 10;"

# 统计订单状态

sqlite3 tg_bot.db "
SELECT 
    order_type,
    status,
    COUNT(*) as count,
    SUM(total_price_usdt) as total_usdt
FROM energy_orders
GROUP BY order_type, status;
"

# 查看用户订单

sqlite3 tg_bot.db "
SELECT order_id, order_type, status, total_price_usdt, created_at
FROM energy_orders
WHERE user_id = 123456789
ORDER BY created_at DESC;
"

```text

### 日志监控

```bash

# 查看能量相关日志

journalctl -u tg_bot -f | grep -i energy

# 查看API调用日志

tail -f /var/log/bot.log | grep "API请求\|API响应"

```text

## 🔒 安全注意事项

### 1. API密钥管理

- ❌ 不要在代码中硬编码API密钥
- ✅ 使用环境变量存储敏感信息

- ✅ 定期更换API密码

### 2. 地址验证

- ✅ 严格验证波场地址格式
- ✅ 防止SQL注入（使用ORM）

- ✅ 防止地址重复提交

### 3. 金额处理

- ✅ 整数化计算（避免浮点精度问题）
- ✅ 余额不足检查

- ✅ 并发扣费保护

### 4. API调用

- ✅ 超时保护（30秒）
- ✅ 自动重试（主URL失败切换备用URL）

- ✅ 错误日志记录

## 🐛 常见问题

### Q1: 能量兑换按钮不可用

**原因**: 未配置能量API
**解决**: 在 `.env` 中添加 `ENERGY_API_USERNAME` 和 `ENERGY_API_PASSWORD`

### Q2: API调用失败（code 10003）

**原因**: 用户名或密码错误
**解决**: 检查 `.env` 中的配置是否正确

### Q3: 余额不足（code 10002）

**原因**: trxno.com 后台余额不足
**解决**: 登录后台充值 TRX 或 USDT

### Q4: 地址未激活（code 10009）

**原因**: 目标地址未激活
**解决**: 使用 API 的激活接口激活地址

### Q5: 用户余额不足

**原因**: Bot用户USDT余额不足
**解决**: 用户先充值 USDT 到个人中心

## 📈 性能优化

### 1. 数据库索引

- `idx_energy_user_status` - 加速用户订单查询
- `idx_energy_order_type` - 加速订单类型统计

### 2. API调用优化

- 使用连接池（httpx.AsyncClient）
- 自动重试机制

- 备用URL切换

### 3. 并发控制

- 订单创建幂等性保证
- 余额扣费并发保护

- 数据库事务隔离

## 📝 开发计划

### 已完成 ✅

- [x] API客户端实现
- [x] 订单管理器实现

- [x] Bot对话流程
- [x] 时长能量购买

- [x] 笔数套餐购买
- [x] 余额扣费集成

- [x] 数据库持久化

### 待实现 🔲

- [ ] 闪兑功能
- [ ] 订单查询界面

- [ ] 能量使用记录
- [ ] 笔数余额查询

- [ ] 自动提前回收
- [ ] 价格实时同步

- [ ] 测试套件完善

---

**最后更新**: 2025-10-28  
**版本**: v1.0.0  
**作者**: TG DGN Bot Team
