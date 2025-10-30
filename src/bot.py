#!/usr/bin/env python3
"""
Telegram Bot 主程序入口
"""
import asyncio
import logging
import re
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from src.config import settings
from src.database import init_db
from src.menu import MainMenuHandler
from src.premium.handler import PremiumHandler
from src.premium.delivery import PremiumDeliveryService
from src.wallet.profile_handler import ProfileHandler
from src.wallet.wallet_manager import WalletManager
from src.address_query.handler import AddressQueryHandler
from src.energy.handler_direct import create_energy_direct_handler
from src.trx_exchange.handler import TRXExchangeHandler
from src.payments.order import order_manager
from src.payments.suffix_manager import suffix_manager
from src.health import health_command
from src.bot_admin import admin_handler
from src.tasks.order_expiry import order_expiry_task
from src.orders import get_orders_handler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram Bot 主类"""
    
    def __init__(self):
        """初始化 Bot"""
        self.app = None
        self.premium_handler = None
        self.wallet_manager = None
        self.scheduler = None
        
    async def initialize(self):
        """初始化所有组件"""
        logger.info("🚀 初始化 Telegram Bot...")
        
        # 初始化数据库
        init_db()
        logger.info("✅ 数据库初始化完成")
        
        # 连接 Redis
        await order_manager.connect()
        await suffix_manager.connect()
        logger.info("✅ Redis 连接成功")
        
        # 创建 Application
        self.app = Application.builder().token(settings.bot_token).build()
        
        # 初始化钱包管理器
        self.wallet_manager = WalletManager()
        logger.info("✅ 钱包管理器初始化完成")
        
        # 初始化 Premium 处理器
        delivery_service = PremiumDeliveryService(
            bot=self.app.bot,
            order_manager=order_manager
        )
        
        self.premium_handler = PremiumHandler(
            order_manager=order_manager,
            suffix_manager=suffix_manager,
            delivery_service=delivery_service,
            receive_address=settings.usdt_trc20_receive_addr
        )
        
        logger.info("✅ 处理器初始化完成")
    
    def register_handlers(self):
        """注册所有命令和回调处理器"""
        logger.info("📝 注册处理器...")
        
        # === 基础命令 ===
        self.app.add_handler(CommandHandler("start", MainMenuHandler.start_command))
        self.app.add_handler(CommandHandler("health", health_command))
        
        # === 增强帮助系统 ===
        from src.help import get_help_handler
        self.app.add_handler(get_help_handler())
        logger.info("✅ 帮助系统处理器已注册（分类帮助 + FAQ）")
        
        # === 管理员面板 ===
        self.app.add_handler(admin_handler.get_conversation_handler())
        logger.info("✅ 管理员面板处理器已注册")
        
        # === 订单查询（管理员专用） ===
        self.app.add_handler(get_orders_handler())
        logger.info("✅ 订单查询处理器已注册（管理员专用）")
        
        # === 底部键盘按钮处理 ===
        # 使用 Regex 过滤器匹配特定按钮文字
        from telegram.ext import filters as tg_filters
        keyboard_buttons = [
            "💎 飞机会员",
            "⚡ 能量兑换",
            "🔍 地址查询",
            "👤 个人中心",
            "🔄 TRX 兑换",
            "👨‍💼 联系客服",
            "💵 实时U价",
            "🎁 免费克隆"
        ]
        self.app.add_handler(MessageHandler(
            tg_filters.Regex(f"^({'|'.join(map(re.escape, keyboard_buttons))})$"),
            MainMenuHandler.handle_keyboard_button
        ))
        
        # === Premium 会员直充 ===
        # 使用 ConversationHandler
        self.app.add_handler(self.premium_handler.get_conversation_handler())
        
        # 从主菜单进入 Premium
        self.app.add_handler(CallbackQueryHandler(
            self.premium_handler.start_premium,
            pattern=r'^menu_premium$'
        ))
        
        # === 个人中心 ===
        self.app.add_handler(CommandHandler("profile", ProfileHandler.profile_command))
        
        # 个人中心回调
        self.app.add_handler(CallbackQueryHandler(
            ProfileHandler.profile_command_callback,
            pattern=r'^menu_profile$'
        ))
        self.app.add_handler(CallbackQueryHandler(
            ProfileHandler.balance_query,
            pattern=r'^profile_balance$'
        ))
        self.app.add_handler(CallbackQueryHandler(
            ProfileHandler.start_deposit,
            pattern=r'^profile_deposit$'
        ))
        self.app.add_handler(CallbackQueryHandler(
            ProfileHandler.deposit_history,
            pattern=r'^profile_history$'
        ))
        self.app.add_handler(CallbackQueryHandler(
            ProfileHandler.back_to_profile,
            pattern=r'^profile_back$'
        ))
        
        # 个人中心消息处理（充值金额输入）
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            ProfileHandler.receive_deposit_amount
        ))
        
        # === 地址查询 ===
        self.app.add_handler(CallbackQueryHandler(
            AddressQueryHandler.query_address,
            pattern=r'^menu_address_query$'
        ))
        self.app.add_handler(CallbackQueryHandler(
            AddressQueryHandler.cancel_query,
            pattern=r'^cancel_query$'
        ))
        
        # 地址查询消息处理（地址输入）
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            AddressQueryHandler.handle_address_input
        ))
        
        # === 能量兑换（直转模式） ===
        # 使用新的直转模式 handler
        self.app.add_handler(create_energy_direct_handler())
        logger.info("✅ 能量兑换处理器已注册（TRX/USDT 直转模式）")
        
        # === TRX 兑换 ===
        trx_exchange_handler = TRXExchangeHandler()
        self.app.add_handler(trx_exchange_handler.get_handlers())
        logger.info("✅ TRX 兑换处理器已注册")
        
        # === 即将上线功能 ===
        self.app.add_handler(CallbackQueryHandler(
            MainMenuHandler.handle_free_clone,
            pattern=r'^menu_clone$'
        ))
        
        # === 联系客服 ===
        self.app.add_handler(CallbackQueryHandler(
            MainMenuHandler.handle_support,
            pattern=r'^menu_support$'
        ))
        
        # === 实时U价 ===
        self.app.add_handler(CallbackQueryHandler(
            MainMenuHandler.refresh_usdt_price,
            pattern=r'^refresh_usdt_price$'
        ))
        
        # === 通用回调：返回主菜单 ===
        self.app.add_handler(CallbackQueryHandler(
            MainMenuHandler.show_main_menu,
            pattern=r'^back_to_main$'
        ))
        
        logger.info("✅ 所有处理器注册完成")
    
    async def start_polling(self):
        """启动 Bot (Polling 模式)"""
        logger.info("🤖 启动 Bot (Polling 模式)...")
        
        await self.initialize()
        self.register_handlers()
        
        # 启动 Bot
        await self.app.initialize()
        await self.app.start()
        
        # 设置 Bot 菜单命令
        await self.setup_bot_commands()
        
        # 启动定时任务调度器
        self.start_scheduler()
        
        await self.app.updater.start_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
        
        logger.info("✅ Bot 启动成功！")
        logger.info(f"📱 Bot 用户名: @{(await self.app.bot.get_me()).username}")
        logger.info("🎯 等待用户消息...")
        
        # 保持运行
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("⏹️  收到停止信号...")
        finally:
            await self.stop()
    
    async def setup_bot_commands(self):
        """设置 Bot 菜单命令（左下角菜单按钮）"""
        from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
        
        # 1. 为所有用户设置通用命令（只显示 /start）
        common_commands = [
            BotCommand("start", "🏠 开始使用 / 主菜单"),
        ]
        await self.app.bot.set_my_commands(
            common_commands,
            scope=BotCommandScopeDefault()
        )
        logger.info("✅ 已设置通用用户命令")
        
        # 2. 为 Owner 设置管理员命令
        if settings.bot_owner_id and settings.bot_owner_id > 0:
            admin_commands = [
                BotCommand("start", "🏠 开始使用 / 主菜单"),
                BotCommand("health", "🏥 系统健康检查"),
                BotCommand("admin", "🔐 管理员面板"),
                BotCommand("orders", "📦 订单查询管理"),
            ]
            try:
                await self.app.bot.set_my_commands(
                    admin_commands,
                    scope=BotCommandScopeChat(chat_id=settings.bot_owner_id)
                )
                logger.info(f"✅ 已设置 Owner 管理员命令（User ID: {settings.bot_owner_id}）")
            except Exception as e:
                logger.warning(f"⚠️ 设置 Owner 命令失败: {e}")
        
        logger.info("✅ Bot 菜单命令已设置")
    
    def start_scheduler(self):
        """启动定时任务调度器"""
        try:
            self.scheduler = AsyncIOScheduler()
            
            # 添加订单超时检查任务（每5分钟执行一次）
            self.scheduler.add_job(
                order_expiry_task.run,
                trigger='interval',
                minutes=5,
                id='order_expiry_task',
                name='订单超时检查任务',
                replace_existing=True
            )
            
            # 启动调度器
            self.scheduler.start()
            logger.info("✅ 定时任务调度器已启动（每5分钟检查订单超时）")
            
        except Exception as e:
            logger.error(f"❌ 定时任务调度器启动失败: {e}", exc_info=True)
    
    async def stop(self):
        """停止 Bot"""
        logger.info("🛑 停止 Bot...")
        
        # 停止定时任务调度器
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            logger.info("✅ 定时任务调度器已停止")
        
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        
        # 断开 Redis
        await order_manager.disconnect()
        await suffix_manager.disconnect()
        
        logger.info("✅ Bot 已停止")


async def main():
    """主函数"""
    bot = TelegramBot()
    try:
        await bot.start_polling()
    except Exception as e:
        logger.error(f"❌ Bot 启动失败: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 再见！")
