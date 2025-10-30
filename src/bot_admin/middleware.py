"""
权限验证中间件

确保只有 Bot Owner 可以访问管理功能。
"""
import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from src.config import settings

logger = logging.getLogger(__name__)


def owner_only(func):
    """
    装饰器：仅允许 Bot Owner 访问
    
    使用方法:
        @owner_only
        async def admin_function(self, update, context):
            ...
    
    支持类方法和普通函数。
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 判断是类方法还是普通函数
        # 类方法: args = (self, update, context, ...)
        # 普通函数: args = (update, context, ...)
        if len(args) >= 2 and hasattr(args[0], '__class__') and hasattr(args[1], 'effective_user'):
            # 类方法：self, update, context
            update = args[1]
            context = args[2] if len(args) > 2 else kwargs.get('context')
        elif len(args) >= 1 and hasattr(args[0], 'effective_user'):
            # 普通函数：update, context
            update = args[0]
            context = args[1] if len(args) > 1 else kwargs.get('context')
        else:
            logger.error(f"owner_only decorator: unexpected arguments {args}")
            return
        
        user_id = update.effective_user.id
        owner_id = settings.bot_owner_id
        
        if owner_id == 0:
            logger.error("BOT_OWNER_ID not configured in .env")
            await update.message.reply_text(
                "⚠️ 系统配置错误：未设置 Bot Owner ID\n"
                "请联系技术人员配置 BOT_OWNER_ID 环境变量。"
            )
            return
        
        if user_id != owner_id:
            logger.warning(f"Unauthorized admin access attempt by user {user_id}")
            await update.message.reply_text(
                "⛔ <b>权限不足</b>\n\n"
                "此功能仅限 Bot 管理员使用。\n"
                "如有问题，请联系客服。",
                parse_mode="HTML"
            )
            return
        
        # 记录管理员操作
        logger.info(f"Admin {user_id} executing: {func.__name__}")
        
        return await func(*args, **kwargs)
    
    return wrapper


def get_owner_id() -> int:
    """获取 Bot Owner ID"""
    return settings.bot_owner_id


def is_owner(user_id: int) -> bool:
    """检查用户是否为 Owner"""
    return user_id == settings.bot_owner_id
