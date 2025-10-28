#!/usr/bin/env python3
"""
Telegram Bot 主程序入口
"""
import asyncio
import logging
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
from src.energy.client import EnergyAPIClient
from src.energy.manager import EnergyOrderManager
from src.energy.handler import EnergyHandler
from src.payments.order import order_manager
from src.payments.suffix_manager import suffix_manager

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
        self.energy_handler = None
        self.wallet_manager = None
        self.energy_client = None
        self.energy_manager = None
        
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
        
        # 初始化能量API客户端
        if settings.energy_api_username and settings.energy_api_password:
            self.energy_client = EnergyAPIClient(
                username=settings.energy_api_username,
                password=settings.energy_api_password,
                base_url=settings.energy_api_base_url,
                backup_url=settings.energy_api_backup_url
            )
            
            # 初始化能量订单管理器
            self.energy_manager = EnergyOrderManager(
                api_client=self.energy_client,
                wallet_manager=self.wallet_manager
            )
            
            # 初始化能量处理器
            self.energy_handler = EnergyHandler(order_manager=self.energy_manager)
            
            logger.info("✅ 能量兑换模块初始化完成")
        else:
            logger.warning("⚠️  能量API配置未设置，能量兑换功能将不可用")
        
        # 初始化 Premium 处理器
        delivery_service = PremiumDeliveryService(
            bot_token=settings.bot_token,
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
        self.app.add_handler(CommandHandler("help", MainMenuHandler.help_command))
        
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
        
        # === 能量兑换 ===
        if self.energy_handler:
            # 能量兑换对话处理器
            self.app.add_handler(self.energy_handler.get_conversation_handler())
            logger.info("✅ 能量兑换处理器已注册")
        else:
            # 如果未配置，显示占位提示
            self.app.add_handler(CallbackQueryHandler(
                MainMenuHandler.handle_coming_soon,
                pattern=r'^energy_exchange$'
            ))
            logger.warning("⚠️  能量兑换功能未配置，使用占位提示")
        
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
    
    async def stop(self):
        """停止 Bot"""
        logger.info("🛑 停止 Bot...")
        
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        
        # 关闭能量API客户端
        if self.energy_client:
            await self.energy_client.close()
        
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
