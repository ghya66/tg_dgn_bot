"""
主菜单处理器
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class MainMenuHandler:
    """主菜单处理器"""
    
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        user = update.effective_user
        
        text = (
            f"👋 欢迎，{user.first_name}！\n\n"
            "🤖 <b>TG DGN Bot - 你的 Telegram 数字服务助手</b>\n\n"
            "📋 <b>功能菜单：</b>\n"
            "• 💎 Premium 直充 - 购买 Telegram Premium 会员\n"
            "• 🏠 个人中心 - 管理余额、充值 USDT\n"
            "• 🔍 地址查询 - 查询波场地址信息\n"
            "• ⚡ 能量兑换 - TRON 能量租用、笔数套餐\n"
            "• 🎁 免费克隆 - 即将上线\n"
            "• 👨‍💼 联系客服 - 获取帮助\n\n"
            "请点击下方按钮开始使用 👇"
        )
        
        keyboard = [
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
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """显示主菜单（回调）"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "🤖 <b>主菜单</b>\n\n"
            "📋 请选择功能："
        )
        
        keyboard = [
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
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def handle_coming_soon(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理即将上线的功能"""
        query = update.callback_query
        await query.answer()
        
        # 占位功能（仅克隆）
        feature_names = {
            "menu_clone": "🎁 免费克隆",
        }
        
        feature_name = feature_names.get(query.data, "该功能")
        
        text = (
            f"🚧 <b>{feature_name}</b>\n\n"
            "该功能正在开发中，敬请期待！\n\n"
            "如有任何问题，请联系客服。"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理联系客服"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "👨‍💼 <b>联系客服</b>\n\n"
            "如需帮助，请通过以下方式联系我们：\n\n"
            "📧 Telegram: @your_support_bot\n"
            "🌐 网站: https://your-website.com\n"
            "📮 邮箱: support@your-domain.com\n\n"
            "工作时间: 24/7 全天候服务"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
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
