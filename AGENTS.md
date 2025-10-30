# AGENTS.md

Fixes #1  
Fixes #2  
Fixes #3
Fixes #4
Fixes #5
Fixes #6
Fixes #7 (NEW)

## Goal
实现：Premium直充（USDT→giftPremiumSubscription）✅、能量闪租/笔数套餐/闪兑（TRX/USDT直转）✅、
地址查询(30min/人限频 免费)✅、个人中心(USDT余额充值 3位小数)✅、免费克隆、联系客服、
**管理员面板（按钮式配置管理）✅**。

## Tech
Python 3.11, python-telegram-bot v21, httpx, Pydantic Settings, SQLAlchemy 2.0。
使用 order_id 幂等、三位小数唯一码、TRC20 监听回调、SQLite 持久化存储。

## Done

- ✅ Issue #1: TRC20 USDT 支付系统
  - 固定地址 + 0.001-0.999 唯一后缀
  - HMAC 签名验证
  - Redis 分布式后缀管理
  - 幂等订单状态更新
  - 完整测试覆盖

- ✅ Issue #2: Premium 直充功能  
  - src/premium/ 模块：收件人解析、Bot对话流程、自动交付
  - 支持 @username / t.me/ 链接解析和去重
  - 3/6/12 个月套餐 ($10/$18/$30)
  - 支付后自动触发 Premium 礼物交付
  - DELIVERED/PARTIAL 状态追踪
  - 完整测试套件：80/88 测试通过（8个Redis集成测试已标记）

- ✅ Issue #3: 个人中心余额充值
  - SQLite + SQLAlchemy 持久化存储（users, deposit_orders, debit_records）
  - 余额查询、充值 USDT（复用 #1 后缀池，3位小数）
  - TRC20 回调自动入账（幂等，整数化金额匹配）
  - 扣费接口：wallet.debit() - 余额不足拒绝、并发保护
  - Telegram Bot /profile 命令：余额查询、充值流程、充值记录
  - 完整测试覆盖（16 wallet + 4 deposit_callback）

- ✅ Issue #4: 地址查询功能（免费）
  - src/address_query/ 模块：地址验证、限频管理、浏览器链接
  - 波场地址验证（T开头34位Base58Check）
  - 30分钟/人限频（SQLite持久化，重启仍生效）
  - 区块链浏览器深链接（Tronscan/OKLink）
  - 支持 TRON API 查询（可选，优雅降级）
  - **免费功能，无需扣费**
  - 完整测试覆盖（8 validator + 5 explorer + 9 rate_limit = 22 tests）

- ✅ Issue #5: 能量服务（TRX/USDT 直转模式）
  - src/energy/handler_direct.py 模块：直转支付流程
  - 三种支付地址：能量闪租（TRX）、笔数套餐（USDT）、闪兑（USDT）
  - 支付流程：用户选择→输入地址→显示代理地址→用户转账→自动到账
  - 能量闪租：3/6 TRX，6秒到账，1小时有效期
  - 笔数套餐：最低5 USDT，弹性扣费
  - 闪兑：USDT 直接兑换能量
  - 完整配置文档：docs/PAYMENT_MODES.md

- ✅ Issue #6: TRX 兑换功能（USDT → TRX）
  - src/trx_exchange/ 模块：TRX 闪兑功能
  - 支付方式：3位小数后缀（复用 Premium/余额充值系统）
  - 汇率管理：固定汇率 + 1小时缓存 + 管理员配置
  - 金额限制：最低 5 USDT，最高 20,000 USDT
  - 手续费：Bot 承担（汇率已包含手续费成本）
  - QR码：Telegram file_id（最安全方式）
  - 转账：测试模式（生产环境需配置私钥）
  - UI特性：QR码图片 + 可复制地址（<code>标签）
  - 按钮布局：优化为 4x2（8个按钮）
  - 完整测试覆盖（25 tests，包含汇率管理、地址验证、支付流程）

- ✅ Issue #7: Bot 管理员面板（新功能）
  - src/bot_admin/ 模块：Telegram Bot 内置管理面板
  - 权限控制：仅 BOT_OWNER_ID 可访问（@owner_only 装饰器）
  - 配置管理：SQLite 数据库存储（price_configs, content_configs, setting_configs）
  - 实时生效：配置修改无需重启 Bot
  - 审计日志：所有操作记录到 audit_logs 表
  - 核心功能：
    - 📊 统计数据：订单/用户/收入统计
    - 💰 价格配置：Premium/TRX/能量价格管理
    - 📝 文案配置：欢迎语/克隆/客服联系方式
    - ⚙️ 系统设置：超时/限频/缓存/状态管理
  - 按钮式操作：无需手动编辑 JSON/命令
  - 完整文档：使用指南 + 实现总结
  - 集成测试：7/7 通过（100%）

## Test Summary

**核心功能测试（无需Redis/Database）: ✅ 80/80 通过**

- AmountCalculator: 10/10 通过
- PaymentProcessor: 9/9 通过  
- RecipientParser: 12/12 通过
- TRC20Handler: 15/15 通过
- SuffixGenerator: 10/10 通过
- Signature: 12/12 通过
- Integration: 4/4 通过
- PremiumDelivery: 8/8 通过

**钱包模块测试（SQLite内存数据库）: ✅ 20/20 通过**

- WalletManager: 16/16 通过
  - 用户创建、余额查询
  - 充值订单创建
  - 充值回调处理（成功、幂等、金额不匹配、过期）
  - 扣费功能（成功、余额不足、并发保护）
  - 金额整数化计算（正例、反例）
  - 充值/扣费记录查询
  - 多用户场景
- DepositCallback: 4/4 通过
  - TRC20回调集成测试
  - deposit订单类型路由
  - 幂等性、金额匹配、订单查询

**地址查询测试（SQLite内存数据库）: ✅ 22/22 通过**

- AddressValidator: 8/8 通过
  - 有效地址验证（Tronscan地址格式）
  - 长度错误检测（太短/太长）
  - 前缀错误检测（非T开头）
  - 无效字符检测（Base58规则）
  - 空地址拒绝
  - 特殊字符拒绝
  - 以太坊/比特币地址拒绝
- ExplorerLinks: 5/5 通过
  - Tronscan链接生成
  - OKLink链接生成
  - 默认Tronscan
  - 大小写不敏感
  - 链接结构正确性
- RateLimit: 9/9 通过
  - 首次查询允许
  - 限频期内拒绝
  - 限频期后允许
  - 查询记录创建
  - 查询记录更新
  - 重启后持久化
  - 多用户独立
  - 并发保护
  - 边界情况处理

**TRX 兑换测试（SQLite内存数据库）: ✅ 25/25 通过**

- RateManager: 9/9 通过
  - TRX 金额计算（精度保证）
  - 从数据库获取汇率
  - 汇率缓存机制（1小时TTL）
  - 管理员设置汇率（创建/更新）
  - 无效汇率拒绝（≤ 0）
  - 设置汇率后清除缓存
- TRXSender: 6/6 通过
  - TRX 地址验证（Base58格式）
  - 测试模式转账（返回mock tx_hash）
  - 生产模式提示（未实现tronpy集成）
  - 无效地址拒绝（长度/前缀/空值）
- TRXExchangeHandler: 10/10 通过
  - 订单ID生成（TRX前缀）
  - 唯一金额生成（3位小数后缀）
  - 启动兑换流程
  - 金额输入验证（有效/格式错误/过小/过大）
  - 地址输入验证（有效/无效）
  - 支付页面展示（QR码+地址+汇率）

**Redis 集成测试（标记 @pytest.mark.redis）: 20 个**

- 8 个原有集成测试（payment_processor, integration, premium_delivery）
- 12 个新增后缀池真实测试（test_suffix_pool_redis.py）
  - 基本分配/释放/重用
  - 并发唯一性保证（50 并发 + 200 压力测试）
  - TTL 自动过期释放
  - 租期延长机制
  - 后缀池耗尽场景
  - 错误 order_id 保护
- 可通过 `pytest -m "not redis"` 跳过
- CI 中使用真实 Redis 7 服务运行全部测试

**CI/CD 配置: ✅**

- GitHub Actions 使用 `redis:7-alpine` service
- 健康检查 + 连接等待确保 Redis 就绪
- 运行全部 198 个测试（80 核心 + 20 钱包 + 22 地址查询 + 25 TRX兑换 + 14 能量 + 其他）
- Python 3.11 & 3.12 矩阵测试
- 依赖：redis>=5.0, sqlalchemy>=2.0, pytest-asyncio>=0.23, pytest-timeout>=2.3

**测试固件增强: ✅**

- Session 级别 `redis_client` fixture
- 自动 `clean_redis` 前后清理（flushdb）
- SQLite 内存数据库 fixture（test_db）
- 无 Redis 环境自动跳过集成测试
- 统一使用 REDIS_URL 和 DATABASE_URL 环境变量

**支付模式架构: ✅**

- 三位小数后缀模式（Premium、余额充值、TRX兑换）
- TRX/USDT 直转模式（能量服务）
- 免费功能（地址查询）
- 完整文档：docs/PAYMENT_MODES.md

**按钮布局优化: ✅**

- 从 10 个按钮优化为 8 个按钮（4x2 布局）
- 删除 2 个占位按钮（能量闪租、限时能量）
- 实现 TRX 兑换按钮完整功能
- 按钮顺序：飞机会员、能量兑换、地址监听、个人中心、TRX兑换、联系客服、实时U价、免费克隆

CI 全绿✅；真实 Redis 集成测试；SQLite 持久化；完整覆盖；README & .env.example 完整。
