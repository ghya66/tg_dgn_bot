"""
能量兑换 Bot 处理器（TRX/USDT 直转模式）
用户直接转账到代理地址，后台自动处理订单
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from loguru import logger

from .models import EnergyPackage, EnergyOrderType
from ..address_query.validator import AddressValidator
from ..config import settings


# 对话状态
STATE_SELECT_TYPE = 1
STATE_SELECT_PACKAGE = 2
STATE_INPUT_ADDRESS = 3
STATE_INPUT_COUNT = 4
STATE_SHOW_PAYMENT = 5
STATE_INPUT_USDT = 6


class EnergyDirectHandler:
    """能量兑换处理器（直转模式）"""
    
    async def start_energy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始能量兑换流程"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("⚡ 时长能量（闪租）", callback_data="energy_type_hourly")],
            [InlineKeyboardButton("📦 笔数套餐", callback_data="energy_type_package")],
            [InlineKeyboardButton("🔄 闪兑", callback_data="energy_type_flash")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "⚡ <b>能量兑换服务</b>\n\n"
            "选择兑换类型：\n\n"
            "⚡ <b>时长能量（闪租）</b>\n"
            "  • 6.5万能量 = 3 TRX\n"
            "  • 13.1万能量 = 6 TRX\n"
            "  • 有效期：1小时\n"
            "  • 支付方式：TRX 转账\n"
            "  • 6秒到账\n\n"
            "📦 <b>笔数套餐</b>\n"
            "  • 弹性笔数：有U扣1笔，无U扣2笔\n"
            "  • 起售金额：5 USDT\n"
            "  • 支付方式：USDT 转账\n"
            "  • 每天至少使用一次\n\n"
            "🔄 <b>闪兑</b>\n"
            "  • USDT 直接兑换能量\n"
            "  • 支付方式：USDT 转账\n"
            "  • 即时到账"
        )
        
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        return STATE_SELECT_TYPE
    
    async def select_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择能量类型"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "energy_type_hourly":
            # 时长能量（闪租） -> 选择套餐
            context.user_data["energy_type"] = EnergyOrderType.HOURLY
            return await self.select_package(update, context)
            
        elif data == "energy_type_package":
            # 笔数套餐 -> 输入地址
            context.user_data["energy_type"] = EnergyOrderType.PACKAGE
            
            text = (
                "📦 <b>笔数套餐购买</b>\n\n"
                "请输入接收能量的波场地址：\n\n"
                "⚠️ 注意：\n"
                "• 必须是有效的波场地址（T开头）\n"
                "• 最低充值：5 USDT\n"
                "• 每笔约0.5 USDT\n\n"
                "示例: <code>TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH</code>"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="energy_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            return STATE_INPUT_ADDRESS
            
        elif data == "energy_type_flash":
            # 闪兑 -> 输入地址
            context.user_data["energy_type"] = EnergyOrderType.FLASH
            
            text = (
                "🔄 <b>闪兑购买</b>\n\n"
                "请输入接收能量的波场地址：\n\n"
                "⚠️ 注意：\n"
                "• 必须是有效的波场地址（T开头）\n"
                "• USDT 直接兑换能量\n"
                "• 即时到账\n\n"
                "示例: <code>TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH</code>"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="energy_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            return STATE_INPUT_ADDRESS
        
        return STATE_SELECT_TYPE
    
    async def select_package(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """选择能量套餐"""
        query = update.callback_query
        
        keyboard = [
            [InlineKeyboardButton("⚡ 6.5万能量 (3 TRX)", callback_data="package_65000")],
            [InlineKeyboardButton("⚡ 13.1万能量 (6 TRX)", callback_data="package_131000")],
            [InlineKeyboardButton("🔙 返回", callback_data="energy_start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "⚡ <b>选择能量套餐</b>\n\n"
            "请选择购买的能量数量：\n\n"
            "💡 说明：\n"
            "• 有效期：1小时\n"
            "• 6秒到账\n"
            "• TRX 转账支付\n"
            "• 下一步将输入购买笔数（1-20）"
        )
        
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        return STATE_SELECT_PACKAGE
    
    async def input_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """输入购买笔数"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "package_65000":
            context.user_data["energy_package"] = EnergyPackage.SMALL
            unit_price = 3
        elif data == "package_131000":
            context.user_data["energy_package"] = EnergyPackage.LARGE
            unit_price = 6
        else:
            return STATE_SELECT_PACKAGE
        
        text = (
            f"⚡ <b>购买笔数</b>\n\n"
            f"已选套餐：{context.user_data['energy_package'].value} 能量\n"
            f"单价：{unit_price} TRX/笔\n\n"
            f"请输入购买笔数（1-20）：\n\n"
            f"💡 示例：\n"
            f"• 输入 5 = {unit_price * 5} TRX\n"
            f"• 输入 10 = {unit_price * 10} TRX\n"
            f"• 输入 20 = {unit_price * 20} TRX"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="energy_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        return STATE_INPUT_COUNT
    
    async def input_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """输入接收地址"""
        message = update.message
        energy_type = context.user_data.get("energy_type")
        
        # 如果是时长能量，先验证笔数
        if energy_type == EnergyOrderType.HOURLY:
            try:
                count = int(message.text.strip())
                if count < 1 or count > 20:
                    await message.reply_text(
                        "❌ 购买笔数必须在 1-20 之间，请重新输入："
                    )
                    return STATE_INPUT_COUNT
                
                context.user_data["purchase_count"] = count
                
            except ValueError:
                await message.reply_text(
                    "❌ 请输入有效的数字（1-20）："
                )
                return STATE_INPUT_COUNT
            
            # 计算价格
            package = context.user_data["energy_package"]
            unit_price = 3 if package == EnergyPackage.SMALL else 6
            total_price = unit_price * count
            
            text = (
                f"📍 <b>接收地址</b>\n\n"
                f"套餐：{package.value} 能量\n"
                f"笔数：{count} 笔\n"
                f"总价：{total_price} TRX (约{total_price / 7:.2f} USDT)\n\n"
                f"请输入接收能量的波场地址：\n\n"
                f"⚠️ 注意：\n"
                f"• 必须是有效的波场地址（T开头）\n"
                f"• 能量将发送到此地址\n"
                f"• 1小时内有效\n\n"
                f"示例: <code>TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH</code>"
            )
            
            await message.reply_text(text, parse_mode="HTML")
            return STATE_INPUT_ADDRESS
        
        # 笔数套餐和闪兑：直接等待地址输入
        else:
            # 这里是等待地址输入的状态，不需要额外处理
            return STATE_INPUT_ADDRESS
    
    async def show_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """显示支付信息"""
        message = update.message
        address = message.text.strip()
        
        # 验证地址
        is_valid, error_msg = AddressValidator.validate(address)
        if not is_valid:
            await message.reply_text(
                f"❌ {error_msg}\n\n"
                "请重新输入正确的波场地址"
            )
            return STATE_INPUT_ADDRESS
        
        context.user_data["receive_address"] = address
        
        # 获取订单信息
        energy_type = context.user_data["energy_type"]
        
        if energy_type == EnergyOrderType.HOURLY:
            # 时长能量（闪租）- TRX 支付
            package = context.user_data["energy_package"]
            count = context.user_data["purchase_count"]
            unit_price = 3 if package == EnergyPackage.SMALL else 6
            total_price = unit_price * count
            
            # 检查代理地址配置
            proxy_address = settings.energy_rent_address
            if not proxy_address:
                await message.reply_text(
                    "❌ <b>系统错误</b>\n\n"
                    "能量闪租地址未配置，请联系管理员",
                    parse_mode="HTML"
                )
                return ConversationHandler.END
            
            text = (
                f"💳 <b>支付信息</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 套餐：{package.value} 能量\n"
                f"🔢 笔数：{count} 笔\n"
                f"📍 接收地址：\n<code>{address}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>支付金额：{total_price} TRX</b>\n\n"
                f"🔗 <b>收款地址：</b>\n"
                f"<code>{proxy_address}</code>\n\n"
                f"⚠️ <b>重要提示：</b>\n"
                f"• 请转账 <b>整数金额</b>（{total_price} TRX）\n"
                f"• 转账后 <b>6秒自动到账</b>\n"
                f"• 能量有效期：<b>1小时</b>\n"
                f"• 请勿重复转账\n\n"
                f"💡 如有问题请联系客服"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ 我已转账", callback_data="payment_done")],
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")],
            ]
            
        elif energy_type == EnergyOrderType.PACKAGE:
            # 笔数套餐 - USDT 支付
            proxy_address = settings.energy_package_address
            if not proxy_address:
                await message.reply_text(
                    "❌ <b>系统错误</b>\n\n"
                    "笔数套餐地址未配置，请联系管理员",
                    parse_mode="HTML"
                )
                return ConversationHandler.END
            
            text = (
                f"💳 <b>支付信息</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 笔数套餐\n"
                f"📍 接收地址：\n<code>{address}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>支付金额：自定义（最低 5 USDT）</b>\n\n"
                f"🔗 <b>收款地址（USDT TRC20）：</b>\n"
                f"<code>{proxy_address}</code>\n\n"
                f"⚠️ <b>重要提示：</b>\n"
                f"• 请转账 <b>整数金额</b>（如：5、10、20 USDT）\n"
                f"• 最低充值：<b>5 USDT</b>\n"
                f"• 每笔约 0.5 USDT\n"
                f"• 弹性扣费：有U扣1笔，无U扣2笔\n"
                f"• 每天至少使用一次\n\n"
                f"💡 如有问题请联系客服"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ 我已转账", callback_data="payment_done")],
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")],
            ]
            
        elif energy_type == EnergyOrderType.FLASH:
            # 闪兑 - USDT 支付
            proxy_address = settings.energy_flash_address
            if not proxy_address:
                await message.reply_text(
                    "❌ <b>系统错误</b>\n\n"
                    "闪兑地址未配置，请联系管理员",
                    parse_mode="HTML"
                )
                return ConversationHandler.END
            
            text = (
                f"💳 <b>支付信息</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔄 闪兑\n"
                f"📍 接收地址：\n<code>{address}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>支付金额：自定义</b>\n\n"
                f"🔗 <b>收款地址（USDT TRC20）：</b>\n"
                f"<code>{proxy_address}</code>\n\n"
                f"⚠️ <b>重要提示：</b>\n"
                f"• 请转账 <b>整数金额</b>（如：10、20、50 USDT）\n"
                f"• USDT 直接兑换能量\n"
                f"• 即时到账\n\n"
                f"💡 如有问题请联系客服"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ 我已转账", callback_data="payment_done")],
                [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")],
            ]
        
        else:
            return ConversationHandler.END
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        return STATE_SHOW_PAYMENT
    
    async def payment_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """用户确认已转账"""
        query = update.callback_query
        await query.answer()
        
        energy_type = context.user_data.get("energy_type")
        
        if energy_type == EnergyOrderType.HOURLY:
            wait_time = "6秒"
            note = "能量将在6秒内自动到账"
        else:
            wait_time = "几分钟"
            note = "转账成功后将自动处理"
        
        text = (
            f"✅ <b>已记录</b>\n\n"
            f"我们已收到您的转账确认。\n\n"
            f"⏰ 预计到账时间：{wait_time}\n\n"
            f"💡 {note}\n\n"
            f"如有疑问，请联系客服"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        # 清理用户数据
        context.user_data.clear()
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消操作"""
        query = update.callback_query
        if query:
            await query.answer()
            await query.edit_message_text(
                text="❌ 已取消操作"
            )
        else:
            await update.message.reply_text("❌ 已取消操作")
        
        context.user_data.clear()
        return ConversationHandler.END


def create_energy_direct_handler() -> ConversationHandler:
    """创建能量兑换对话处理器（直转模式）"""
    handler_instance = EnergyDirectHandler()
    
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handler_instance.start_energy, pattern="^menu_energy$"),
        ],
        states={
            STATE_SELECT_TYPE: [
                CallbackQueryHandler(handler_instance.select_type, pattern="^energy_type_"),
            ],
            STATE_SELECT_PACKAGE: [
                CallbackQueryHandler(handler_instance.input_count, pattern="^package_"),
            ],
            STATE_INPUT_COUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler_instance.input_address),
            ],
            STATE_INPUT_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler_instance.show_payment),
            ],
            STATE_SHOW_PAYMENT: [
                CallbackQueryHandler(handler_instance.payment_done, pattern="^payment_done$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(handler_instance.start_energy, pattern="^energy_start$"),
            CallbackQueryHandler(handler_instance.cancel, pattern="^back_to_main$"),
        ],
        name="energy_direct_handler",
        persistent=False,
    )
