"""
地址查询 Telegram Bot 处理器
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from typing import Optional
import logging
import httpx

from ..database import SessionLocal, AddressQueryLog
from ..config import settings
from .validator import AddressValidator
from .explorer import explorer_links

logger = logging.getLogger(__name__)


class AddressQueryHandler:
    """地址查询处理器"""
    
    @staticmethod
    async def query_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理地址查询按钮点击"""
        query = update.callback_query
        if query:
            await query.answer()
        
        user_id = update.effective_user.id
        
        # 检查限频
        can_query, remaining_minutes = AddressQueryHandler._check_rate_limit(user_id)
        
        if not can_query:
            text = (
                f"⏰ <b>查询限制</b>\n\n"
                f"您的查询过于频繁，请在 <b>{remaining_minutes}</b> 分钟后再试。\n\n"
                f"💡 限制：每用户 {settings.address_query_rate_limit_minutes} 分钟仅可查询 1 次"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if query:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            return
        
        # 提示输入地址
        text = (
            "🔍 <b>地址查询</b>\n\n"
            "请发送要查询的波场(TRON)地址：\n\n"
            "• 地址以 <code>T</code> 开头\n"
            "• 长度为 34 位字符\n"
            "• 支持 Base58 字符集\n\n"
            "示例: <code>TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH</code>"
        )
        
        keyboard = [[InlineKeyboardButton("❌ 取消", callback_data="cancel_query")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
        
        # 设置状态，等待用户输入地址
        context.user_data['awaiting_address'] = True
    
    @staticmethod
    async def handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理用户输入的地址"""
        # 检查是否在等待地址输入状态
        if not context.user_data.get('awaiting_address'):
            return
        
        context.user_data['awaiting_address'] = False
        address = update.message.text.strip()
        user_id = update.effective_user.id
        
        # 验证地址格式
        is_valid, error_msg = AddressValidator.validate(address)
        
        if not is_valid:
            text = f"❌ <b>地址格式错误</b>\n\n{error_msg}\n\n请重新发送正确的地址。"
            keyboard = [[InlineKeyboardButton("❌ 取消", callback_data="cancel_query")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
            context.user_data['awaiting_address'] = True  # 继续等待
            return
        
        # 再次检查限频（防止绕过）
        can_query, remaining_minutes = AddressQueryHandler._check_rate_limit(user_id)
        if not can_query:
            text = (
                f"⏰ <b>查询限制</b>\n\n"
                f"您的查询过于频繁，请在 <b>{remaining_minutes}</b> 分钟后再试。"
            )
            await update.message.reply_text(text, parse_mode="HTML")
            return
        
        # 记录查询
        AddressQueryHandler._record_query(user_id)
        
        # 获取地址信息
        await update.message.reply_text("🔄 正在查询地址信息...")
        
        address_info = await AddressQueryHandler._fetch_address_info(address)
        
        # 生成浏览器链接
        links = explorer_links(address)
        
        # 构建响应消息
        text = f"📍 <b>地址信息</b>\n\n"
        text += f"地址: <code>{address}</code>\n\n"
        
        if address_info:
            text += f"💰 TRX 余额: <b>{address_info.get('trx_balance', '0')} TRX</b>\n"
            text += f"🪙 USDT 余额: <b>{address_info.get('usdt_balance', '0')} USDT</b>\n\n"
            
            # 最近交易
            txs = address_info.get('recent_txs', [])
            if txs:
                text += "📊 <b>最近 5 笔交易:</b>\n\n"
                for idx, tx in enumerate(txs[:5], 1):
                    direction = tx.get('direction', '?')
                    amount = tx.get('amount', '0')
                    token = tx.get('token', 'TRX')
                    tx_hash = tx.get('hash', '')[:8]
                    timestamp = tx.get('time', '')
                    
                    text += f"{idx}. {direction} {amount} {token}\n"
                    text += f"   哈希: <code>{tx_hash}...</code>\n"
                    text += f"   时间: {timestamp}\n\n"
            else:
                text += "📊 <i>暂无最近交易记录</i>\n\n"
        else:
            text += "ℹ️ <i>API 暂时不可用，无法获取详细信息</i>\n\n"
        
        text += f"⏰ 下次可查询时间: {settings.address_query_rate_limit_minutes} 分钟后"
        
        # 添加深链接按钮
        keyboard = [
            [
                InlineKeyboardButton("🔗 链上查询详情", url=links["overview"]),
                InlineKeyboardButton("🔍 查询转账记录", url=links["txs"])
            ],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    
    @staticmethod
    def _check_rate_limit(user_id: int) -> tuple[bool, int]:
        """
        检查用户是否在限频期内
        
        Args:
            user_id: 用户 ID
            
        Returns:
            (是否可以查询, 剩余分钟数)
        """
        db = SessionLocal()
        try:
            log = db.query(AddressQueryLog).filter_by(user_id=user_id).first()
            
            if not log:
                return True, 0
            
            now = datetime.now()
            time_passed = now - log.last_query_at
            limit_delta = timedelta(minutes=settings.address_query_rate_limit_minutes)
            
            if time_passed < limit_delta:
                remaining = limit_delta - time_passed
                remaining_minutes = int(remaining.total_seconds() / 60) + 1
                return False, remaining_minutes
            
            return True, 0
        finally:
            db.close()
    
    @staticmethod
    def _record_query(user_id: int):
        """
        记录查询时间
        
        Args:
            user_id: 用户 ID
        """
        db = SessionLocal()
        try:
            log = db.query(AddressQueryLog).filter_by(user_id=user_id).first()
            
            if log:
                log.last_query_at = datetime.now()
                log.query_count += 1
            else:
                log = AddressQueryLog(
                    user_id=user_id,
                    last_query_at=datetime.now(),
                    query_count=1
                )
                db.add(log)
            
            db.commit()
        finally:
            db.close()
    
    @staticmethod
    async def _fetch_address_info(address: str) -> Optional[dict]:
        """
        获取地址信息（从 TRON API）
        
        Args:
            address: 波场地址
            
        Returns:
            地址信息字典，失败返回 None
        """
        # 检查 API 配置
        if not settings.tron_api_url or not settings.tron_api_key:
            logger.info("TRON API 未配置，跳过数据获取")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"Authorization": f"Bearer {settings.tron_api_key}"}
                response = await client.get(
                    f"{settings.tron_api_url}/address/{address}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data
                else:
                    logger.warning(f"TRON API 返回错误: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"获取地址信息失败: {e}")
            return None
    
    @staticmethod
    async def cancel_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """取消查询"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['awaiting_address'] = False
        
        text = "❌ 已取消地址查询"
        keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
