"""
个人中心 Telegram Bot 处理器
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from typing import Optional
import logging

from ..wallet.wallet_manager import WalletManager
from ..payments.suffix_manager import suffix_manager
from ..config import settings

logger = logging.getLogger(__name__)

# 对话状态
AWAITING_DEPOSIT_AMOUNT = 1


class ProfileHandler:
    """个人中心处理器"""
    
    @staticmethod
    async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /profile 命令"""
        user_id = update.effective_user.id
        
        # 获取余额
        with WalletManager() as wallet:
            balance = wallet.get_balance(user_id)
        
        # 构建键盘
        keyboard = [
            [InlineKeyboardButton("💰 余额查询", callback_data="profile_balance")],
            [InlineKeyboardButton("💳 充值 USDT", callback_data="profile_deposit")],
            [InlineKeyboardButton("📝 充值记录", callback_data="profile_history")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🏠 <b>个人中心</b>\n\n"
            f"💰 当前余额: <code>{balance:.3f}</code> USDT\n\n"
            "请选择操作："
        )
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def balance_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """查询余额"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        with WalletManager() as wallet:
            balance = wallet.get_balance(user_id)
            deposits = wallet.get_user_deposits(user_id, limit=5)
            debits = wallet.get_user_debits(user_id, limit=5)
        
        # 统计信息
        total_deposited = sum(d.total_amount for d in deposits if d.status == "PAID")
        total_spent = sum(d.get_amount() for d in debits)
        
        text = (
            "💰 <b>余额详情</b>\n\n"
            f"当前余额: <code>{balance:.3f}</code> USDT\n"
            f"累计充值: <code>{total_deposited:.3f}</code> USDT\n"
            f"累计消费: <code>{total_spent:.3f}</code> USDT\n"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="profile_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def start_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """开始充值流程"""
        query = update.callback_query
        await query.answer()
        
        text = (
            "💳 <b>充值 USDT</b>\n\n"
            "请输入充值金额（USDT）：\n"
            "• 支持整数或两位小数\n"
            "• 例如: 10 或 10.50\n"
            "• 最小充值: 1 USDT\n\n"
            "输入 /cancel 取消操作"
        )
        
        await query.edit_message_text(text, parse_mode="HTML")
        
        return AWAITING_DEPOSIT_AMOUNT
    
    @staticmethod
    async def receive_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """接收充值金额"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # 解析金额
        try:
            amount = float(text)
            if amount < 1:
                await update.message.reply_text(
                    "❌ 金额太小，最小充值 1 USDT\n\n请重新输入或 /cancel 取消："
                )
                return AWAITING_DEPOSIT_AMOUNT
            if amount > 10000:
                await update.message.reply_text(
                    "❌ 金额过大，最大充值 10000 USDT\n\n请重新输入或 /cancel 取消："
                )
                return AWAITING_DEPOSIT_AMOUNT
        except ValueError:
            await update.message.reply_text(
                "❌ 金额格式错误\n\n请输入有效数字或 /cancel 取消："
            )
            return AWAITING_DEPOSIT_AMOUNT
        
        # 分配唯一后缀
        await suffix_manager.connect()
        suffix = await suffix_manager.allocate_suffix()
        
        if suffix is None:
            await update.message.reply_text(
                "❌ 系统繁忙，请稍后再试"
            )
            return ConversationHandler.END
        
        # 创建充值订单
        with WalletManager() as wallet:
            order = wallet.create_deposit_order(
                user_id=user_id,
                base_amount=amount,
                unique_suffix=suffix,
                timeout_minutes=settings.ORDER_TIMEOUT_MINUTES
            )
        
        # 保存订单ID到后缀池
        await suffix_manager.set_order_id(suffix, order.order_id)
        
        # 计算倒计时
        remaining_minutes = int((order.expires_at - order.created_at).total_seconds() / 60)
        
        # 发送支付信息
        text = (
            "✅ <b>充值订单已创建</b>\n\n"
            f"订单号: <code>{order.order_id}</code>\n"
            f"应付金额: <code>{order.total_amount:.3f}</code> USDT\n"
            f"收款地址:\n<code>{settings.USDT_TRC20_RECEIVE_ADDR}</code>\n\n"
            f"⏰ 倒计时: {remaining_minutes} 分钟\n\n"
            "⚠️ <b>注意事项:</b>\n"
            f"• 请务必转账 <b>{order.total_amount:.3f}</b> USDT\n"
            "• 金额必须精确到 3 位小数\n"
            "• 使用 TRC20 网络转账\n"
            "• 转账后 2-5 分钟自动到账\n\n"
            "如有疑问请联系客服"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回个人中心", callback_data="profile_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
        
        return ConversationHandler.END
    
    @staticmethod
    async def deposit_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """查询充值记录"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        with WalletManager() as wallet:
            deposits = wallet.get_user_deposits(user_id, limit=10)
        
        if not deposits:
            text = "📝 <b>充值记录</b>\n\n暂无充值记录"
        else:
            text = "📝 <b>充值记录</b>\n\n"
            for i, deposit in enumerate(deposits, 1):
                status_emoji = {
                    "PAID": "✅",
                    "PENDING": "⏰",
                    "EXPIRED": "❌"
                }.get(deposit.status, "❓")
                
                text += (
                    f"{i}. {status_emoji} {deposit.total_amount:.3f} USDT\n"
                    f"   状态: {deposit.status}\n"
                    f"   时间: {deposit.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                )
        
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="profile_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def back_to_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """返回个人中心"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        with WalletManager() as wallet:
            balance = wallet.get_balance(user_id)
        
        keyboard = [
            [InlineKeyboardButton("💰 余额查询", callback_data="profile_balance")],
            [InlineKeyboardButton("💳 充值 USDT", callback_data="profile_deposit")],
            [InlineKeyboardButton("📝 充值记录", callback_data="profile_history")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🏠 <b>个人中心</b>\n\n"
            f"💰 当前余额: <code>{balance:.3f}</code> USDT\n\n"
            "请选择操作："
        )
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """取消操作"""
        await update.message.reply_text("操作已取消")
        return ConversationHandler.END


def get_profile_handlers():
    """获取个人中心处理器列表"""
    
    # 充值对话处理器
    deposit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ProfileHandler.start_deposit, pattern="^profile_deposit$")],
        states={
            AWAITING_DEPOSIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ProfileHandler.receive_deposit_amount)
            ],
        },
        fallbacks=[CommandHandler("cancel", ProfileHandler.cancel)],
    )
    
    return [
        CommandHandler("profile", ProfileHandler.profile_command),
        CallbackQueryHandler(ProfileHandler.balance_query, pattern="^profile_balance$"),
        deposit_conv,
        CallbackQueryHandler(ProfileHandler.deposit_history, pattern="^profile_history$"),
        CallbackQueryHandler(ProfileHandler.back_to_profile, pattern="^profile_back$"),
    ]
