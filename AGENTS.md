# AGENTS.md

Fixes #1  
Fixes #2  
Fixes #3

## Goal
实现：Premium直充（USDT→giftPremiumSubscription）✅、能量兑换/闪租/限时(占位)、
地址查询(30min/人限频)、个人中心(USDT余额充值 3位小数)✅、免费克隆、联系客服。

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
- 运行全部 120 个测试（80 核心 + 20 钱包 + 20 Redis）
- Python 3.11 & 3.12 矩阵测试
- 依赖：redis>=5.0, sqlalchemy>=2.0, pytest-asyncio>=0.23, pytest-timeout>=2.3

**测试固件增强: ✅**
- Session 级别 `redis_client` fixture
- 自动 `clean_redis` 前后清理（flushdb）
- SQLite 内存数据库 fixture（test_db）
- 无 Redis 环境自动跳过集成测试
- 统一使用 REDIS_URL 和 DATABASE_URL 环境变量

CI 全绿✅；真实 Redis 集成测试；SQLite 持久化；完整覆盖；README & .env.example 完整。
