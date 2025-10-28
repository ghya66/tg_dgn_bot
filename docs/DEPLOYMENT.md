# 部署和测试指南

## 📋 部署前检查清单

### 1. 环境准备

```bash

# 检查 Python 版本

python3 --version  # 需要 >= 3.11

# 检查 Redis 状态

redis-cli ping    # 应返回 PONG

# 检查依赖安装

pip list | grep -E "(telegram|httpx|sqlalchemy|redis|pydantic)"

```text

### 2. 配置文件

```bash

# 复制配置模板

cp .env.example .env

# 编辑配置（需要设置以下关键配置）

nano .env

```text

## 必需配置：

- `BOT_TOKEN` - 从 @BotFather 获取的真实 token
- `USDT_TRC20_RECEIVE_ADDR` - 波场 TRC20 USDT 收款地址（T开头，34位）

- `WEBHOOK_SECRET` - 自定义密钥（至少32字符，用于签名验证）

## 可选配置：

- `REDIS_URL` - 默认: `redis://localhost:6379/0`
- `DATABASE_URL` - 默认: `sqlite:///./bot_data.db`

- `TRON_EXPLORER` - 默认: `tronscan` (可选 `oklink`)
- `ADDRESS_QUERY_RATE_LIMIT_MINUTES` - 默认: `30`

### 3. 配置验证

```bash

# 运行配置验证工具

python3 scripts/validate_config.py

# 预期输出示例：

# ✅ .env 文件存在
# ✅ 所有必需配置已设置

# ✅ BOT_TOKEN 格式正确
# ✅ USDT_TRC20_RECEIVE_ADDR 格式正确

# ✅ Redis 连接成功
# ✅ 数据库连接成功

# ==================================================
# ✅ 配置验证通过！可以启动 Bot

```text

## 🚀 启动 Bot

### 方式 1: 使用启动脚本（推荐）

```bash

# 启动 Bot

./scripts/start_bot.sh

# 预期输出：

# ✅ 找到 .env 文件
# ✅ Python 版本: 3.11.x

# ✅ 依赖已安装
# ✅ Redis 连接正常

# ✅ 数据库已初始化
# 🚀 启动 Bot...

# Bot 正在运行 (PID: 12345)

```text

### 方式 2: 手动启动

```bash

# 设置 PYTHONPATH

export PYTHONPATH=/workspaces/tg_dgn_bot:$PYTHONPATH

# 启动 Bot

cd /workspaces/tg_dgn_bot
python3 -m src.bot

```text

## 🧪 功能测试

### 测试 1: 主菜单测试

1. 在 Telegram 中找到你的 Bot

2. 发送 `/start`
3. **预期结果**：看到欢迎消息 + 6个按钮：

   - ✅ Premium直充

   - ✅ 个人中心

   - ✅ 地址查询

   - 🔲 能量兑换（占位）

   - 🔲 免费克隆（占位）

   - 👨‍💼 联系客服（占位）

### 测试 2: Premium 直充流程

1. 点击 **"Premium直充"**

2. **预期**：看到 Premium 套餐选择

   - 🎁 3个月 ($10)

   - 🎁 6个月 ($18)

   - 🎁 12个月 ($30)

3. 选择套餐（例如：3个月）
4. **预期**：提示输入收件人（支持 @username / t.me/链接）

5. 输入收件人（例如：`@test_user`）
6. **预期**：生成支付地址和二维码

   ```

   💰 订单信息
   套餐: Premium 3个月
   收件人: @test_user
   金额: $10.234 USDT

   🔗 支付地址
   TXxx...xxx

   ⚠️ 注意：请准确转账 10.234 USDT（后三位必须是 .234）
   ```

7. 使用 USDT TRC20 转账到显示的地址（**金额精确到小数点后3位**）
8. **预期**：转账确认后，Bot 自动交付 Premium

## 测试要点：

- ✅ 收件人解析正确（@username / t.me/链接）
- ✅ 金额后缀唯一（0.001-0.999）

- ✅ 支付地址正确
- ✅ 订单状态更新及时

- ✅ Premium 自动交付

### 测试 3: 个人中心流程

1. 点击 **"个人中心"**

2. **预期**：看到余额和充值按钮

   ```

   💰 个人中心

   💳 余额: 0.000 USDT

   [💳 充值 USDT]  [📜 充值记录]
   ```

3. 点击 **"💳 充值 USDT"**
4. **预期**：提示输入充值金额

5. 输入金额（例如：`50`）
6. **预期**：生成支付地址

   ```

   💰 充值信息
   金额: $50.456 USDT

   🔗 支付地址
   TXxx...xxx

   ⚠️ 注意：请准确转账 50.456 USDT（后三位必须是 .456）
   ```

7. 转账后，**预期**：余额自动更新
8. 点击 **"📜 充值记录"**，**预期**：看到充值历史

## 测试要点：

- ✅ 余额查询正确
- ✅ 充值订单创建成功

- ✅ 支付后余额自动入账（幂等）
- ✅ 充值记录可查询

### 测试 4: 地址查询流程

1. 点击 **"地址查询"**

2. **预期**：提示输入波场地址

3. 输入有效地址（例如：`TXxx...xxx`）

4. **预期**：返回浏览器链接

   ```

   🔍 查询结果
   地址: TXxx...xxx

   🌐 浏览器查询:
   • Tronscan: <https://tronscan.org/#/address/TXxx...xxx>
   • OKLink: <https://www.oklink.com/cn/trx/address/TXxx...xxx>
   ```

5. 30分钟内再次查询，**预期**：拒绝查询

   ```

   ⏰ 查询过于频繁
   距离下次查询还需等待 29 分钟
   ```

## 测试要点：

- ✅ 有效地址验证（T开头，34位）
- ✅ 无效地址拒绝（长度、前缀、字符集）

- ✅ 限频保护（30分钟）
- ✅ 浏览器链接正确

### 测试 5: 帮助命令

1. 发送 `/help`

2. **预期**：看到完整使用文档

   - 功能列表

   - 使用流程

   - 支付说明

   - 限制说明

## 🛑 停止 Bot

```bash

# 使用停止脚本

./scripts/stop_bot.sh

# 预期输出：

# 🛑 正在停止 Bot (PID: 12345)...
# ⏳ 等待进程退出...

# ✅ Bot 已停止

```text

## 🔍 日志和调试

### 查看运行日志

```bash

# 查看 Bot 输出

tail -f /tmp/bot.log  # 如果配置了日志文件

# 或者直接运行查看实时输出

python3 -m src.bot

```text

### 常见问题排查

#### 1. Bot 无法启动

```bash

# 检查配置

python3 scripts/validate_config.py

# 检查 Redis

redis-cli ping

# 检查数据库

sqlite3 bot_data.db ".tables"

```text

#### 2. 支付回调不工作

```bash

# 检查 webhook 签名密钥

echo $WEBHOOK_SECRET  # 应为 32+ 字符

# 检查收款地址

echo $USDT_TRC20_RECEIVE_ADDR  # 应为 T开头 34位

# 测试签名验证

curl -X POST http://localhost:8000/webhook/trc20 \
  -H "Content-Type: application/json" \
  -H "X-Signature: test" \
  -d '{"test": "data"}'

```text

#### 3. Premium 交付失败

检查日志中的错误信息：

- `INVALID_USER` - 收件人不存在
- `PREMIUM_DISALLOWED` - 收件人禁用了礼物

- `USER_BLOCKED_BOT` - 收件人屏蔽了 Bot

## 📊 监控和维护

### 数据库查询

```bash

# 查看订单统计

sqlite3 bot_data.db "SELECT status, COUNT(*) FROM payment_orders GROUP BY status;"

# 查看用户余额

sqlite3 bot_data.db "SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10;"

# 查看充值记录

sqlite3 bot_data.db "SELECT * FROM deposit_orders ORDER BY created_at DESC LIMIT 20;"

```text

### Redis 监控

```bash

# 查看后缀池使用情况

redis-cli ZCARD suffix_pool

# 查看订单映射

redis-cli HGETALL suffix:order
redis-cli HGETALL suffix:user

# 查看 TTL

redis-cli TTL suffix:order:ORD_xxx

```text

## 🧪 自动化测试

```bash

# 运行全部测试（142个）

pytest tests/ -v

# 跳过 Redis 集成测试

pytest tests/ -m "not redis" -v

# 运行指定模块测试

pytest tests/test_payments/ -v
pytest tests/test_premium/ -v
pytest tests/test_wallet/ -v
pytest tests/test_address_query/ -v

# 查看测试覆盖率

pytest tests/ --cov=src --cov-report=html

```text

## 🔒 安全检查

### 配置安全

```bash

# 确保 .env 不被提交

git status .env  # 应显示 ignored

# 检查敏感信息

grep -r "BOT_TOKEN\|WEBHOOK_SECRET" --include="*.py" src/

# 应只出现在 config.py 中通过环境变量读取

```text

### 代码审计

```bash

# 检查硬编码密钥

grep -rE "([0-9]{10}:[A-Za-z0-9_-]{35})" src/

# 检查 SQL 注入风险（应使用 SQLAlchemy ORM）

grep -r "execute.*%" src/

# 检查命令注入风险

grep -r "os.system\|subprocess.call" src/

```text

## 📈 性能优化

### Redis 连接池

配置已使用 ConnectionPool，支持高并发：

```python

# src/config.py

REDIS_CLIENT = redis.Redis(
    connection_pool=redis.ConnectionPool.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=50
    )
)

```text

### 数据库优化

```bash

# 创建索引（已在模型中定义）

sqlite3 bot_data.db "CREATE INDEX IF NOT EXISTS idx_payment_orders_status ON payment_orders(status);"
sqlite3 bot_data.db "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);"

```text

## 🎯 下一步计划

### 待实现功能

1. **⚡ 能量兑换/闪租**

   - 能量包购买

   - 限时租赁

   - 自动交付

2. **🎁 免费克隆**

   - 账号克隆服务

   - 配额管理

3. **👨‍💼 联系客服**

   - 工单系统

   - 人工客服转接

### 架构改进

- [ ] Webhook 模式（生产环境推荐）

- [ ] 多语言支持（i18n）
- [ ] 管理后台（统计、配置）

- [ ] Docker 部署
- [ ] CI/CD 自动部署

---

**最后更新**: 2025-06-XX
**当前版本**: v1.0.0
**测试覆盖**: 142/142 ✅
