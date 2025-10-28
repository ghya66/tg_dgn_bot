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
        
        user = update.effective_user
        
        # 使用配置的欢迎语
        text = settings.welcome_message.replace("{first_name}", user.first_name)
        
        # 构建引流按钮
        keyboard = MainMenuHandler._build_promotion_buttons()
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
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
