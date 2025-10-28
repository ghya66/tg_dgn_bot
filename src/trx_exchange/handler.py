"""TRX Exchange Handler - TRX/USDT Exchange with QR Code Payment."""

import logging
from decimal import Decimal
from typing import Optional
import uuid

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..address_query.validator import AddressValidator
from .models import TRXExchangeOrder
from .rate_manager import RateManager
from .trx_sender import TRXSender

logger = logging.getLogger(__name__)

# Conversation states
INPUT_AMOUNT, INPUT_ADDRESS, SHOW_PAYMENT, CONFIRM_PAYMENT = range(4)


class TRXExchangeHandler:
    """Handle TRX Exchange (USDT → TRX)."""

    def __init__(self):
        """Initialize TRX exchange handler."""
        self.trx_sender = TRXSender()
        self.validator = AddressValidator()

    def generate_order_id(self) -> str:
        """Generate unique order ID."""
        return f"TRX{uuid.uuid4().hex[:16].upper()}"

    def generate_unique_amount(self, base_amount: Decimal) -> Decimal:
        """
        Generate unique amount with 3-decimal suffix.

        Args:
            base_amount: Base amount (e.g., Decimal('10'))

        Returns:
            Amount with unique suffix (e.g., Decimal('10.123'))
        """
        # Simple implementation: use random 3-digit suffix
        import random
        suffix = random.randint(1, 999)
        unique_amount = base_amount + Decimal(f"0.{suffix:03d}")
        return unique_amount


class TRXExchangeHandler:
    """Handle TRX Exchange (USDT → TRX)."""

    def __init__(self):
        """Initialize TRX exchange handler."""
        self.trx_sender = TRXSender()
        self.validator = AddressValidator()

    def generate_order_id(self) -> str:
        """Generate unique order ID."""
        return f"TRX{uuid.uuid4().hex[:16].upper()}"

    def generate_unique_amount(self, base_amount: Decimal) -> Decimal:
        """
        Generate unique amount with 3-decimal suffix.

        Args:
            base_amount: Base amount (e.g., Decimal('10'))

        Returns:
            Amount with unique suffix (e.g., Decimal('10.123'))
        """
        # Simple implementation: use random 3-digit suffix
        import random
        suffix = random.randint(1, 999)
        unique_amount = base_amount + Decimal(f"0.{suffix:03d}")
        return unique_amount

    async def start_exchange(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start TRX exchange flow."""
        await update.message.reply_text(
            "🔄 *TRX 闪兑*\n\n"
            "24小时自动兑换，安全快捷！\n\n"
            "💰 最低兑换：5 USDT\n"
            "💰 最高兑换：20,000 USDT\n"
            "⚡ 到账时间：5-10 分钟\n"
            "🔒 手续费：Bot 承担\n\n"
            "请输入您要兑换的 USDT 数量：",
            parse_mode="Markdown",
        )
        return INPUT_AMOUNT

    async def input_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle USDT amount input."""
        user_input = update.message.text.strip()

        # Validate amount
        try:
            amount = Decimal(user_input)
        except Exception:
            await update.message.reply_text(
                "❌ 金额格式错误，请输入数字（例如：10 或 10.5）"
            )
            return INPUT_AMOUNT

        # Check min/max limits
        if amount < Decimal("5"):
            await update.message.reply_text(
                f"❌ 最低兑换金额为 5 USDT\n请重新输入："
            )
            return INPUT_AMOUNT

        if amount > Decimal("20000"):
            await update.message.reply_text(
                f"❌ 最高兑换金额为 20,000 USDT\n请重新输入："
            )
            return INPUT_AMOUNT

        # Get current exchange rate
        db: Session = SessionLocal()
        try:
            rate = RateManager.get_rate(db)
            trx_amount = RateManager.calculate_trx_amount(amount, rate)
        finally:
            db.close()

        # Store in context
        context.user_data["exchange_usdt_amount"] = amount
        context.user_data["exchange_rate"] = rate
        context.user_data["exchange_trx_amount"] = trx_amount

        await update.message.reply_text(
            f"💱 *当前汇率*\n\n"
            f"1 USDT = {rate} TRX\n\n"
            f"📊 *兑换明细*\n"
            f"支付：{amount} USDT\n"
            f"获得：{trx_amount} TRX\n\n"
            f"请输入您的 TRX 接收地址：\n"
            f"（波场地址，T 开头，34 位）",
            parse_mode="Markdown",
        )
        return INPUT_ADDRESS

    async def input_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle TRX address input."""
        address = update.message.text.strip()

        # Validate address
        if not self.trx_sender.validate_address(address):
            await update.message.reply_text(
                "❌ 地址格式错误\n\n"
                "请输入有效的波场地址（T 开头，34 位）："
            )
            return INPUT_ADDRESS

        # Store address
        context.user_data["exchange_recipient_address"] = address

        # Show payment page
        return await self.show_payment(update, context)

    async def show_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Show payment QR code and address."""
        user_id = update.effective_user.id
        usdt_amount = context.user_data["exchange_usdt_amount"]
        rate = context.user_data["exchange_rate"]
        trx_amount = context.user_data["exchange_trx_amount"]
        recipient_address = context.user_data["exchange_recipient_address"]

        # Create order with 3-decimal suffix
        db: Session = SessionLocal()
        try:
            # Generate unique amount with suffix
            unique_amount = self.generate_unique_amount(usdt_amount)
            order_id = self.generate_order_id()

            # Create order in database
            order = TRXExchangeOrder(
                order_id=order_id,
                user_id=user_id,
                usdt_amount=unique_amount,
                trx_amount=trx_amount,
                exchange_rate=rate,
                recipient_address=recipient_address,
                payment_address=settings.trx_exchange_receive_address,
                status="PENDING",
            )
            db.add(order)
            db.commit()

            logger.info(
                f"Created TRX exchange order: {order_id} "
                f"(user: {user_id}, USDT: {unique_amount}, TRX: {trx_amount})"
            )

        finally:
            db.close()

        # Store order_id in context
        context.user_data["exchange_order_id"] = order_id

        # Payment instruction message
        payment_address = settings.trx_exchange_receive_address
        qrcode_file_id = settings.trx_exchange_qrcode_file_id

        message_text = (
            f"💳 *支付信息*\n\n"
            f"💰 支付金额：`{unique_amount}` USDT\n"
            f"📍 收款地址：\n<code>{payment_address}</code>\n\n"
            f"📊 *兑换信息*\n"
            f"🔄 兑换汇率：1 USDT = {rate} TRX\n"
            f"⚡ 获得数量：{trx_amount} TRX\n"
            f"📥 接收地址：<code>{recipient_address}</code>\n\n"
            f"⏰ *到账时间*\n"
            f"USDT 到账后 5-10 分钟内自动转账 TRX\n\n"
            f"⚠️ *温馨提示*\n"
            f"1. 请务必使用 TRC20-USDT 支付\n"
            f"2. 支付金额必须完全一致（包含 3 位小数）\n"
            f"3. 手续费由 Bot 承担，您无需额外支付\n"
            f"4. 订单有效期 30 分钟\n\n"
            f"💡 轻触地址即可复制到剪贴板"
        )

        # Send QR code image if available
        if qrcode_file_id and qrcode_file_id != "YOUR_QRCODE_FILE_ID_HERE":
            try:
                await update.effective_message.reply_photo(
                    photo=qrcode_file_id,
                    caption=message_text,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Failed to send QR code image: {e}")
                # Fallback to text only
                await update.effective_message.reply_text(
                    message_text,
                    parse_mode="HTML",
                )
        else:
            # No QR code configured, send text only
            await update.effective_message.reply_text(
                message_text,
                parse_mode="HTML",
            )

        await update.effective_message.reply_text(
            "✅ 支付完成后，请点击下方按钮确认：",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 我已支付", callback_data=f"trx_paid_{order_id}")],
                [InlineKeyboardButton("❌ 取消兑换", callback_data=f"trx_cancel_{order_id}")],
            ]),
        )

        return CONFIRM_PAYMENT

    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle payment confirmation button."""
        query = update.callback_query
        await query.answer()

        data = query.data
        order_id = context.user_data.get("exchange_order_id")

        if data.startswith("trx_cancel_"):
            await query.edit_message_text(
                "❌ 兑换已取消\n\n"
                "如需重新兑换，请使用 🔄 TRX 兑换 功能"
            )
            return ConversationHandler.END

        if data.startswith("trx_paid_"):
            await query.edit_message_text(
                "⏳ *处理中*\n\n"
                "我们正在确认您的支付...\n"
                "预计 5-10 分钟内完成 TRX 转账\n\n"
                "💡 您可以通过 👤 个人中心 查看兑换记录",
                parse_mode="Markdown",
            )
            return ConversationHandler.END

        return CONFIRM_PAYMENT

    async def handle_payment_callback(self, order_id: str) -> None:
        """
        Handle TRC20 payment callback for TRX exchange.

        Called by TRC20Handler when payment is confirmed.

        Args:
            order_id: TRX exchange order ID
        """
        db: Session = SessionLocal()
        try:
            # Get order
            order = db.query(TRXExchangeOrder).filter_by(order_id=order_id).first()

            if not order:
                logger.error(f"TRX exchange order not found: {order_id}")
                return

            if order.status != "PENDING":
                logger.warning(f"Order already processed: {order_id} (status: {order.status})")
                return

            # Update order status
            order.status = "PAID"
            from datetime import datetime, timezone
            order.paid_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"TRX exchange order paid: {order_id}")

            # Send TRX
            try:
                tx_hash = self.trx_sender.send_trx(
                    recipient_address=order.recipient_address,
                    amount=order.trx_amount,
                    order_id=order_id,
                )

                # Update order status
                order.status = "TRANSFERRED"
                order.tx_hash = tx_hash
                order.transferred_at = datetime.now(timezone.utc)
                db.commit()

                logger.info(
                    f"TRX transferred: {order.trx_amount} TRX → {order.recipient_address} "
                    f"(order: {order_id}, tx: {tx_hash})"
                )

                # TODO: Notify user about successful transfer
                # This requires bot instance in context

            except Exception as e:
                logger.error(f"TRX transfer failed (order: {order_id}): {e}", exc_info=True)
                order.status = "FAILED"
                db.commit()

                # TODO: Notify admin about failed transfer

        finally:
            db.close()

    def get_handlers(self):
        """Get conversation handlers for TRX exchange."""
        return ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^🔄 TRX 兑换$"), self.start_exchange)],
            states={
                INPUT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_amount)],
                INPUT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_address)],
                CONFIRM_PAYMENT: [CallbackQueryHandler(self.confirm_payment, pattern="^trx_(paid|cancel)_")],
            },
            fallbacks=[CommandHandler("cancel", self._cancel)],
            name="trx_exchange",
            persistent=False,
        )

    async def _cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel conversation."""
        await update.message.reply_text("❌ 操作已取消")
        return ConversationHandler.END
