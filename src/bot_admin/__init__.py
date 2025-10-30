"""
Bot 管理员功能模块

提供 Telegram Bot 内置的管理面板，包括：
- 价格配置管理
- 统计数据查询
- 订单管理
- 文案配置
- 操作审计日志

仅限 Bot Owner 访问。
"""
from .handler import admin_handler
from .middleware import owner_only

__all__ = ['admin_handler', 'owner_only']
