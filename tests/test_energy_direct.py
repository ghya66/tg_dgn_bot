"""
能量直转模式处理器测试
测试 TRX/USDT 直转支付流程
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import ContextTypes

from src.energy.handler_direct import EnergyDirectHandler
from src.energy.models import EnergyOrderType, EnergyPackage


class TestEnergyDirectHandler:
    """测试能量直转模式处理器"""
    
    @pytest.fixture
    def handler(self):
        """创建处理器实例"""
        return EnergyDirectHandler()
    
    @pytest.fixture
    def mock_update_query(self):
        """模拟带有 callback_query 的 update"""
        update = Mock(spec=Update)
        query = Mock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update.callback_query = query
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        return update
    
    @pytest.fixture
    def mock_update_message(self):
        """模拟带有 message 的 update"""
        update = Mock(spec=Update)
        message = Mock(spec=Message)
        message.reply_text = AsyncMock()
        message.text = "5"  # 默认输入
        update.message = message
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123456
        return update
    
    @pytest.fixture
    def mock_context(self):
        """模拟 context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_start_energy(self, handler, mock_update_query, mock_context):
        """测试开始能量兑换"""
        result = await handler.start_energy(mock_update_query, mock_context)
        
        # 验证回调已应答
        mock_update_query.callback_query.answer.assert_called_once()
        
        # 验证消息已编辑
        mock_update_query.callback_query.edit_message_text.assert_called_once()
        args = mock_update_query.callback_query.edit_message_text.call_args
        
        # 验证消息内容
        text = args[1]["text"]
        assert "能量兑换服务" in text
        assert "时长能量" in text
        assert "笔数套餐" in text
        assert "闪兑" in text
        assert "TRX 转账" in text
        assert "USDT 转账" in text
        
        # 验证状态转换
        from src.energy.handler_direct import STATE_SELECT_TYPE
        assert result == STATE_SELECT_TYPE
    
    @pytest.mark.asyncio
    async def test_select_hourly_energy(self, handler, mock_update_query, mock_context):
        """测试选择时长能量（闪租）"""
        mock_update_query.callback_query.data = "energy_type_hourly"
        
        result = await handler.select_type(mock_update_query, mock_context)
        
        # 验证用户数据已设置
        assert mock_context.user_data["energy_type"] == EnergyOrderType.HOURLY
        
        # 验证显示了套餐选择
        args = mock_update_query.callback_query.edit_message_text.call_args
        text = args[1]["text"]
        assert "选择能量套餐" in text
        # 套餐按钮在 InlineKeyboard 中，不在文本中
        # assert "6.5万能量" in text
        # assert "13.1万能量" in text
    
    @pytest.mark.asyncio
    async def test_select_package(self, handler, mock_update_query, mock_context):
        """测试选择笔数套餐"""
        mock_update_query.callback_query.data = "energy_type_package"
        
        result = await handler.select_type(mock_update_query, mock_context)
        
        # 验证用户数据已设置
        assert mock_context.user_data["energy_type"] == EnergyOrderType.PACKAGE
        
        # 验证显示了地址输入提示
        args = mock_update_query.callback_query.edit_message_text.call_args
        text = args[1]["text"]
        assert "笔数套餐购买" in text
        assert "最低充值：5 USDT" in text
        assert "接收能量的波场地址" in text
    
    @pytest.mark.asyncio
    async def test_select_flash(self, handler, mock_update_query, mock_context):
        """测试选择闪兑"""
        mock_update_query.callback_query.data = "energy_type_flash"
        
        result = await handler.select_type(mock_update_query, mock_context)
        
        # 验证用户数据已设置
        assert mock_context.user_data["energy_type"] == EnergyOrderType.FLASH
        
        # 验证显示了地址输入提示
        args = mock_update_query.callback_query.edit_message_text.call_args
        text = args[1]["text"]
        assert "闪兑购买" in text
        assert "USDT 直接兑换能量" in text
    
    @pytest.mark.asyncio
    async def test_input_count_small_package(self, handler, mock_update_query, mock_context):
        """测试输入购买笔数（6.5万能量）"""
        mock_update_query.callback_query.data = "package_65000"
        
        result = await handler.input_count(mock_update_query, mock_context)
        
        # 验证用户数据已设置
        assert mock_context.user_data["energy_package"] == EnergyPackage.SMALL
        
        # 验证消息内容
        args = mock_update_query.callback_query.edit_message_text.call_args
        text = args[1]["text"]
        assert "65000 能量" in text
        assert "单价：3 TRX/笔" in text
        assert "输入购买笔数（1-20）" in text
    
    @pytest.mark.asyncio
    async def test_input_count_large_package(self, handler, mock_update_query, mock_context):
        """测试输入购买笔数（13.1万能量）"""
        mock_update_query.callback_query.data = "package_131000"
        
        result = await handler.input_count(mock_update_query, mock_context)
        
        # 验证用户数据已设置
        assert mock_context.user_data["energy_package"] == EnergyPackage.LARGE
        
        # 验证消息内容
        args = mock_update_query.callback_query.edit_message_text.call_args
        text = args[1]["text"]
        assert "131000 能量" in text
        assert "单价：6 TRX/笔" in text
    
    @pytest.mark.asyncio
    async def test_input_address_valid_count(self, handler, mock_update_message, mock_context):
        """测试输入有效笔数"""
        mock_context.user_data["energy_type"] = EnergyOrderType.HOURLY
        mock_context.user_data["energy_package"] = EnergyPackage.SMALL
        mock_update_message.message.text = "5"
        
        result = await handler.input_address(mock_update_message, mock_context)
        
        # 验证用户数据已保存
        assert mock_context.user_data["purchase_count"] == 5
        
        # 验证显示地址输入提示
        args = mock_update_message.message.reply_text.call_args
        text = args[0][0]
        assert "笔数：5 笔" in text
        assert "总价：15 TRX" in text
        assert "接收能量的波场地址" in text
    
    @pytest.mark.asyncio
    async def test_input_address_invalid_count(self, handler, mock_update_message, mock_context):
        """测试输入无效笔数"""
        mock_context.user_data["energy_type"] = EnergyOrderType.HOURLY
        mock_update_message.message.text = "abc"
        
        result = await handler.input_address(mock_update_message, mock_context)
        
        # 验证返回错误消息
        args = mock_update_message.message.reply_text.call_args
        text = args[0][0]
        assert "请输入有效的数字" in text
    
    @pytest.mark.asyncio
    async def test_input_address_out_of_range(self, handler, mock_update_message, mock_context):
        """测试输入超出范围笔数"""
        mock_context.user_data["energy_type"] = EnergyOrderType.HOURLY
        mock_update_message.message.text = "25"  # 超过20
        
        result = await handler.input_address(mock_update_message, mock_context)
        
        # 验证返回错误消息
        args = mock_update_message.message.reply_text.call_args
        text = args[0][0]
        assert "购买笔数必须在 1-20 之间" in text
    
    @pytest.mark.asyncio
    @patch("src.energy.handler_direct.settings")
    async def test_show_payment_hourly(self, mock_settings, handler, mock_update_message, mock_context):
        """测试显示时长能量支付信息"""
        mock_settings.energy_rent_address = "TTestRentAddress123"
        
        mock_context.user_data["energy_type"] = EnergyOrderType.HOURLY
        mock_context.user_data["energy_package"] = EnergyPackage.SMALL
        mock_context.user_data["purchase_count"] = 5
        mock_update_message.message.text = "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH"
        
        result = await handler.show_payment(mock_update_message, mock_context)
        
        # 验证用户数据已保存
        assert mock_context.user_data["receive_address"] == "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH"
        
        # 验证显示支付信息
        args = mock_update_message.message.reply_text.call_args
        # reply_text 参数: (text, parse_mode="HTML", reply_markup=...)
        text = args[0][0] if args[0] else args[1].get("text", "")
        assert "支付信息" in text
        assert "65000 能量" in text
        assert "笔数：5 笔" in text
        assert "支付金额：15 TRX" in text
        assert "TTestRentAddress123" in text
        assert "6秒自动到账" in text
        assert "整数金额" in text
    
    @pytest.mark.asyncio
    @patch("src.energy.handler_direct.settings")
    async def test_show_payment_package(self, mock_settings, handler, mock_update_message, mock_context):
        """测试显示笔数套餐支付信息"""
        mock_settings.energy_package_address = "TTestPackageAddress123"
        
        mock_context.user_data["energy_type"] = EnergyOrderType.PACKAGE
        mock_update_message.message.text = "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH"
        
        result = await handler.show_payment(mock_update_message, mock_context)
        
        # 验证显示支付信息
        args = mock_update_message.message.reply_text.call_args
        text = args[0][0] if args[0] else args[1].get("text", "")
        assert "笔数套餐" in text
        assert "TTestPackageAddress123" in text
        assert "最低 5 USDT" in text
        assert "弹性扣费" in text
    
    @pytest.mark.asyncio
    @patch("src.energy.handler_direct.settings")
    async def test_show_payment_flash(self, mock_settings, handler, mock_update_message, mock_context):
        """测试显示闪兑支付信息"""
        mock_settings.energy_flash_address = "TTestFlashAddress123"
        
        mock_context.user_data["energy_type"] = EnergyOrderType.FLASH
        mock_update_message.message.text = "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH"
        
        result = await handler.show_payment(mock_update_message, mock_context)
        
        # 验证显示支付信息
        args = mock_update_message.message.reply_text.call_args
        text = args[0][0] if args[0] else args[1].get("text", "")
        assert "闪兑" in text
        assert "TTestFlashAddress123" in text
        assert "USDT 直接兑换能量" in text
    
    @pytest.mark.asyncio
    async def test_show_payment_address_not_configured(self, handler, mock_update_message, mock_context):
        """测试未配置代理地址的错误处理"""
        with patch("src.energy.handler_direct.settings") as mock_settings:
            mock_settings.energy_rent_address = ""  # 未配置
            
            mock_context.user_data["energy_type"] = EnergyOrderType.HOURLY
            mock_context.user_data["energy_package"] = EnergyPackage.SMALL
            mock_context.user_data["purchase_count"] = 5
            mock_update_message.message.text = "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH"
            
            result = await handler.show_payment(mock_update_message, mock_context)
            
            # 验证显示错误消息
            args = mock_update_message.message.reply_text.call_args
            text = args[0][0]
            assert "系统错误" in text
            assert "能量闪租地址未配置" in text
    
    @pytest.mark.asyncio
    async def test_payment_done(self, handler, mock_update_query, mock_context):
        """测试用户确认已转账"""
        mock_context.user_data["energy_type"] = EnergyOrderType.HOURLY
        
        result = await handler.payment_done(mock_update_query, mock_context)
        
        # 验证显示确认消息
        args = mock_update_query.callback_query.edit_message_text.call_args
        text = args[1]["text"]
        assert "已记录" in text
        assert "预计到账时间：6秒" in text
        
        # 验证用户数据已清理
        assert len(mock_context.user_data) == 0
