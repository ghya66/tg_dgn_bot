"""
Premium 会员直充处理器：Telegram Bot 对话流程
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from ..models import OrderType
from ..payments.order import OrderManager
from ..payments.suffix_manager import SuffixManager
from ..payments.amount_calculator import AmountCalculator
from .recipient_parser import RecipientParser
from .delivery import PremiumDeliveryService

logger = logging.getLogger(__name__)

# 对话状态
SELECTING_PACKAGE, ENTERING_RECIPIENTS, CONFIRMING_PAYMENT = range(3)


class PremiumHandler:
    """Premium 购买对话处理器"""
    
    # 套餐配置 {months: price_usdt}
    PACKAGES = {
        3: 10.0,
        6: 18.0,
        12: 30.0
    }
    
    def __init__(
        self, 
        order_manager: OrderManager,
        suffix_manager: SuffixManager,
        delivery_service: PremiumDeliveryService,
        receive_address: str
    ):
        """
        初始化处理器
        
        Args:
            order_manager: 订单管理器
            suffix_manager: 后缀管理器
            delivery_service: 交付服务
            receive_address: USDT 收款地址
        """
        self.order_manager = order_manager
        self.suffix_manager = suffix_manager
        self.delivery_service = delivery_service
        self.receive_address = receive_address
    
    def get_conversation_handler(self) -> ConversationHandler:
        """
        获取对话处理器
        
        Returns:
            ConversationHandler 实例
        """
        return ConversationHandler(
            entry_points=[CommandHandler('premium', self.start_premium)],
            states={
                SELECTING_PACKAGE: [
                    CallbackQueryHandler(self.package_selected, pattern=r'^premium_\d+$')
                ],
                ENTERING_RECIPIENTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.recipients_entered)
                ],
                CONFIRMING_PAYMENT: [
                    CallbackQueryHandler(self.confirm_payment, pattern=r'^confirm_payment$'),
                    CallbackQueryHandler(self.cancel_order, pattern=r'^cancel_order$')
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            allow_reentry=True
        )
    
    async def start_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        开始 Premium 购买流程
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            下一个对话状态
        """
        keyboard = [
            [
                InlineKeyboardButton(f"3个月 - ${self.PACKAGES[3]}", callback_data="premium_3"),
                InlineKeyboardButton(f"6个月 - ${self.PACKAGES[6]}", callback_data="premium_6")
            ],
            [
                InlineKeyboardButton(f"12个月 - ${self.PACKAGES[12]}", callback_data="premium_12")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎁 *Premium 会员直充*\n\n"
            "选择套餐后，请提供收件人用户名（支持 @username 或 t.me/username 格式）\n\n"
            "套餐价格：",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return SELECTING_PACKAGE
    
    async def package_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        用户选择套餐
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            下一个对话状态
        """
        query = update.callback_query
        await query.answer()
        
        # 解析月数
        months = int(query.data.split('_')[1])
        context.user_data['premium_months'] = months
        context.user_data['base_amount'] = self.PACKAGES[months]
        
        await query.edit_message_text(
            f"✅ 已选择：{months} 个月 Premium\n\n"
            f"💰 价格：${self.PACKAGES[months]} USDT\n\n"
            f"📝 请发送收件人用户名（每行一个）：\n"
            f"支持格式：\n"
            f"  • @username\n"
            f"  • t.me/username\n"
            f"  • username\n\n"
            f"示例：\n"
            f"@alice\n"
            f"@bob\n"
            f"t.me/charlie"
        )
        
        return ENTERING_RECIPIENTS
    
    async def recipients_entered(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        用户输入收件人
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            下一个对话状态
        """
        text = update.message.text
        recipients = RecipientParser.parse(text)
        
        if not recipients:
            await update.message.reply_text(
                "❌ 未识别到有效用户名，请重新输入。\n\n"
                "支持格式：@username, t.me/username, username"
            )
            return ENTERING_RECIPIENTS
        
        # 验证用户名格式
        invalid = [r for r in recipients if not RecipientParser.validate_username(r)]
        if invalid:
            await update.message.reply_text(
                f"❌ 以下用户名格式无效：\n{', '.join(invalid)}\n\n"
                f"请重新输入（用户名需 5-32 字符，仅字母、数字、下划线）"
            )
            return ENTERING_RECIPIENTS
        
        context.user_data['recipients'] = recipients
        
        # 创建订单
        try:
            suffix = await self.suffix_manager.allocate_suffix()
            base_amount = context.user_data['base_amount']
            total_amount = AmountCalculator.generate_payment_amount(base_amount, suffix)
            
            order = await self.order_manager.create_order(
                base_amount=base_amount,
                unique_suffix=suffix,
                user_id=update.effective_user.id,
                order_type=OrderType.PREMIUM,
                premium_months=context.user_data['premium_months'],
                recipients=recipients
            )
            
            context.user_data['order_id'] = order.order_id
            context.user_data['total_amount'] = total_amount
            context.user_data['unique_suffix'] = suffix
            
        except Exception as e:
            logger.error(f"Failed to create premium order: {e}")
            await update.message.reply_text(
                "❌ 创建订单失败，请稍后重试或联系客服。"
            )
            return ConversationHandler.END
        
        # 确认订单
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认支付", callback_data="confirm_payment"),
                InlineKeyboardButton("❌ 取消", callback_data="cancel_order")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📦 *订单确认*\n\n"
            f"套餐：{context.user_data['premium_months']} 个月 Premium\n"
            f"收件人数量：{len(recipients)}\n"
            f"收件人：{', '.join('@' + r for r in recipients[:5])}"
            f"{'...' if len(recipients) > 5 else ''}\n\n"
            f"💰 应付金额：`{total_amount:.3f}` USDT (TRC20)\n"
            f"📍 收款地址：`{self.receive_address}`\n\n"
            f"⏰ 订单有效期：30分钟\n"
            f"🔖 订单号：`{order.order_id}`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return CONFIRMING_PAYMENT
    
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        用户确认支付
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            对话结束
        """
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            f"✅ *订单已创建*\n\n"
            f"💰 应付金额：`{context.user_data['total_amount']:.3f}` USDT\n"
            f"📍 收款地址：`{self.receive_address}`\n\n"
            f"⚠️ 请精确转账 `{context.user_data['total_amount']:.3f}` USDT（包含小数部分）\n"
            f"⏰ 支付后 2-5 分钟内自动到账\n\n"
            f"🔖 订单号：`{context.user_data['order_id']}`\n"
            f"查询订单状态：/order_status {context.user_data['order_id']}",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    async def cancel_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        取消订单
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            对话结束
        """
        query = update.callback_query
        await query.answer()
        
        # 释放后缀
        if 'unique_suffix' in context.user_data:
            await self.suffix_manager.release_suffix(context.user_data['unique_suffix'])
        
        # 取消订单
        if 'order_id' in context.user_data:
            await self.order_manager.cancel_order(context.user_data['order_id'])
        
        await query.edit_message_text("❌ 订单已取消")
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        取消对话
        
        Args:
            update: Telegram 更新
            context: 上下文
            
        Returns:
            对话结束
        """
        await update.message.reply_text("操作已取消")
        
        # 清理资源
        if 'unique_suffix' in context.user_data:
            await self.suffix_manager.release_suffix(context.user_data['unique_suffix'])
        
        return ConversationHandler.END
