"""
主菜单处理器
"""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class MainMenuHandler:
    """主菜单处理器"""
    
    @staticmethod
    def _build_promotion_buttons():
        """构建引流按钮（从配置读取）"""
        from ..config import settings
        
        try:
            # 解析配置的按钮
            buttons_config = settings.promotion_buttons
            # 移除换行和多余空格
            buttons_config = buttons_config.replace('\n', '').replace(' ', '')
            # 解析为列表
            button_rows = eval(f'[{buttons_config}]')
            
            keyboard = []
            for row in button_rows:
                button_row = []
                for btn in row:
                    text = btn.get('text', '')
                    url = btn.get('url')
                    callback = btn.get('callback')
                    
                    if url:
                        # 外部链接按钮
                        button_row.append(InlineKeyboardButton(text, url=url))
                    elif callback:
                        # 回调按钮
                        button_row.append(InlineKeyboardButton(text, callback_data=callback))
                
                if button_row:
                    keyboard.append(button_row)
            
            return keyboard
        except Exception as e:
            logger.error(f"解析引流按钮配置失败: {e}")
            # 返回默认按钮
            return [
                [
                    InlineKeyboardButton("💎 Premium直充", callback_data="menu_premium"),
                    InlineKeyboardButton("🏠 个人中心", callback_data="menu_profile")
                ],
                [
                    InlineKeyboardButton("🔍 地址查询", callback_data="menu_address_query"),
                    InlineKeyboardButton("⚡ 能量兑换", callback_data="menu_energy")
                ],
                [
                    InlineKeyboardButton("🎁 免费克隆", callback_data="menu_clone"),
                    InlineKeyboardButton("👨‍💼 联系客服", callback_data="menu_support")
                ]
            ]
    
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        from ..config import settings
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        
        user = update.effective_user
        
        # 使用配置的欢迎语
        text = settings.welcome_message.replace("{first_name}", user.first_name)
        
        # 构建引流按钮（InlineKeyboard）
        inline_keyboard = MainMenuHandler._build_promotion_buttons()
        inline_markup = InlineKeyboardMarkup(inline_keyboard)
        
        # 构建底部键盘（ReplyKeyboard）- 10个按钮
        reply_keyboard = [
            [KeyboardButton("💎 飞机会员"), KeyboardButton("⚡ 能量兑换")],
            [KeyboardButton("🔍 地址监听"), KeyboardButton("� 个人中心")],
            [KeyboardButton("� TRX 兑换"), KeyboardButton("� 限时能量")],
            [KeyboardButton("�‍💼 联系客服"), KeyboardButton("🌐 实时U价")],
            [KeyboardButton("⚡ 能量闪租"), KeyboardButton("📱 免费克隆")],
        ]
        reply_markup = ReplyKeyboardMarkup(
            reply_keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )
        
        # 先发送带 InlineKeyboard 的消息
        await update.message.reply_text(
            text, 
            parse_mode="HTML", 
            reply_markup=inline_markup
        )
        
        # 再设置底部键盘
        await update.message.reply_text(
            "📱 使用下方按钮快速访问功能：",
            reply_markup=reply_markup
        )
    
    @staticmethod
    async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示主菜单（回调）"""
        from ..config import settings
        
        query = update.callback_query
        await query.answer()
        
        # 使用配置的欢迎语（简化版）
        text = (
            "🤖 <b>主菜单</b>\n\n"
            "📋 请选择功能："
        )
        
        # 构建引流按钮
        keyboard = MainMenuHandler._build_promotion_buttons()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def handle_free_clone(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理免费克隆功能"""
        from ..config import settings
        
        query = update.callback_query
        await query.answer()
        
        # 从配置中读取管理员设置的文案
        text = settings.free_clone_message
        
        keyboard = [
            [InlineKeyboardButton("👨‍💼 联系客服", callback_data="menu_support")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理联系客服"""
        from ..config import settings
        
        query = update.callback_query
        if query:
            await query.answer()
        
        text = (
            "👨‍💼 <b>联系客服</b>\n\n"
            f"客服 Telegram: {settings.support_contact}\n\n"
            "工作时间: 24/7 全天候服务"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        text = (
            "📚 <b>帮助文档</b>\n\n"
            "<b>🎯 可用命令：</b>\n"
            "/start - 显示主菜单\n"
            "/help - 显示帮助信息\n"
            "/premium - 购买 Premium 会员\n"
            "/profile - 个人中心\n"
            "/cancel - 取消当前操作\n\n"
            "<b>💡 使用说明：</b>\n"
            "1. 点击主菜单按钮选择功能\n"
            "2. 按照提示完成操作\n"
            "3. 遇到问题可随时联系客服\n\n"
            "<b>💰 支付说明：</b>\n"
            "• 支持 TRC20 USDT 支付\n"
            "• 支付后 2-5 分钟自动到账\n"
            "• 请确保转账金额精确到小数点后3位\n\n"
            "如需更多帮助，请联系客服 👨‍💼"
        )
        
        keyboard = [[InlineKeyboardButton("🏠 返回主菜单", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def show_usdt_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示实时 USDT 汇率信息"""
        from datetime import datetime
        import httpx
        
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 尝试从公开 API 获取实时汇率（示例使用 CoinGecko API）
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={
                        "ids": "tether",
                        "vs_currencies": "cny,usd"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    cny_rate = data.get("tether", {}).get("cny", 0)
                    usd_rate = data.get("tether", {}).get("usd", 0)
                    
                    text = (
                        "📊 <b>实时 U 价</b>\n\n"
                        f"💵 <b>USDT 实时汇率</b>\n\n"
                        f"🇨🇳 CNY: <code>{cny_rate:.4f}</code> 元\n"
                        f"🇺🇸 USD: <code>{usd_rate:.4f}</code> 美元\n\n"
                        f"⏰ 更新时间: {current_time}\n\n"
                        "💡 数据来源: CoinGecko API"
                    )
                else:
                    raise Exception("API 请求失败")
        
        except Exception as e:
            logger.error(f"获取 USDT 汇率失败: {e}")
            # 使用模拟数据作为后备
            text = (
                "📊 <b>实时 U 价</b>\n\n"
                "💵 <b>USDT 参考汇率</b>\n\n"
                "🇨🇳 CNY: <code>7.13</code> 元\n"
                "🇺🇸 USD: <code>1.00</code> 美元\n\n"
                f"⏰ 当前时间: {current_time}\n\n"
                "⚠️ 汇率仅供参考，实际交易以平台实时价格为准"
            )
        
        keyboard = [[InlineKeyboardButton("🔄 刷新", callback_data="refresh_usdt_price")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def refresh_usdt_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """刷新 USDT 汇率（回调处理）"""
        from datetime import datetime
        import httpx
        
        query = update.callback_query
        await query.answer("正在刷新汇率...")
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={
                        "ids": "tether",
                        "vs_currencies": "cny,usd"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    cny_rate = data.get("tether", {}).get("cny", 0)
                    usd_rate = data.get("tether", {}).get("usd", 0)
                    
                    text = (
                        "📊 <b>实时 U 价</b>\n\n"
                        f"💵 <b>USDT 实时汇率</b>\n\n"
                        f"🇨🇳 CNY: <code>{cny_rate:.4f}</code> 元\n"
                        f"🇺🇸 USD: <code>{usd_rate:.4f}</code> 美元\n\n"
                        f"⏰ 更新时间: {current_time}\n\n"
                        "💡 数据来源: CoinGecko API"
                    )
                else:
                    raise Exception("API 请求失败")
        
        except Exception as e:
            logger.error(f"获取 USDT 汇率失败: {e}")
            text = (
                "📊 <b>实时 U 价</b>\n\n"
                "💵 <b>USDT 参考汇率</b>\n\n"
                "🇨🇳 CNY: <code>7.13</code> 元\n"
                "🇺🇸 USD: <code>1.00</code> 美元\n\n"
                f"⏰ 当前时间: {current_time}\n\n"
                "⚠️ 汇率仅供参考，实际交易以平台实时价格为准"
            )
        
        keyboard = [[InlineKeyboardButton("🔄 刷新", callback_data="refresh_usdt_price")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理底部键盘按钮"""
        text = update.message.text
        
        # 根据按钮文字路由到对应功能
        if text == "💎 飞机会员":
            # 导航到 Premium 购买
            from ..premium.handler import PremiumHandler
            await PremiumHandler.show_premium_menu(update, context)
        
        elif text == "⚡ 能量兑换":
            # 导航到能量兑换主菜单
            from ..energy.handler import EnergyHandler
            await EnergyHandler.show_main_menu(update, context)
        
        elif text == "🔍 地址监听":
            # 导航到地址查询
            from ..address_query.handler import AddressQueryHandler
            await AddressQueryHandler.start(update, context)
        
        elif text == "� 个人中心":
            # 导航到个人中心
            from ..wallet.profile_handler import ProfileHandler
            await ProfileHandler.profile_command(update, context)
        
        elif text == "🔄 TRX 兑换":
            # TRX兑换功能（占位）
            await update.message.reply_text(
                "🔄 <b>TRX 兑换</b>\n\n功能开发中，敬请期待",
                parse_mode="HTML"
            )
        
        elif text == "� 限时能量":
            # 限时能量功能（占位）
            await update.message.reply_text(
                "� <b>限时能量</b>\n\n功能开发中，敬请期待",
                parse_mode="HTML"
            )
        
        elif text == "👨‍💼 联系客服":
            # 显示客服联系方式
            from ..config import settings
            await update.message.reply_text(
                f"👨‍💼 <b>联系客服</b>\n\n{settings.support_contact}",
                parse_mode="HTML"
            )
        
        elif text == "🌐 实时U价":
            # 显示实时 USDT 汇率
            await MainMenuHandler.show_usdt_price(update, context)
        
        elif text == "⚡ 能量闪租":
            # 能量闪租功能（占位）
            await update.message.reply_text(
                "⚡ <b>能量闪租</b>\n\n功能开发中，敬请期待",
                parse_mode="HTML"
            )
        
        elif text == "� 免费克隆":
            # 免费克隆功能
            from ..config import settings
            keyboard = [[InlineKeyboardButton("👨‍💼 联系客服", callback_data="menu_support")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                settings.free_clone_message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
