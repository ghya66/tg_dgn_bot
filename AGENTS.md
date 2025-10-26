# AGENTS.md
## Goal
实现：Premium直充（USDT→giftPremiumSubscription）、能量兑换/闪租/限时(占位)、
地址查询(30min/人限频)、个人中心(USDT余额充值 3位小数)、免费克隆、联系客服。
## Tech
Python 3.11, python-telegram-bot v21, httpx, Pydantic Settings。
使用 order_id 幂等、三位小数唯一码、TRC20 监听回调。
## Done
CI 通过；最小测试；README 更新。
