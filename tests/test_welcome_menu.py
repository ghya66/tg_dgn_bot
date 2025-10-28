"""
测试欢迎语和引流按钮功能
"""
import pytest
from src.config import settings
from src.menu.main_menu import MainMenuHandler


def test_welcome_message_exists():
    """测试欢迎语配置存在"""
    assert hasattr(settings, 'welcome_message')
    assert isinstance(settings.welcome_message, str)
    assert len(settings.welcome_message) > 0


def test_welcome_message_contains_welcome_text():
    """测试欢迎语包含欢迎内容"""
    message = settings.welcome_message
    
    # 检查必要元素
    assert "欢迎" in message or "Welcome" in message or "👋" in message
    assert "Bot" in message or "bot" in message or "🤖" in message


def test_promotion_buttons_config_exists():
    """测试引流按钮配置存在"""
    assert hasattr(settings, 'promotion_buttons')
    assert isinstance(settings.promotion_buttons, str)
    assert len(settings.promotion_buttons) > 0


def test_promotion_buttons_format():
    """测试引流按钮配置格式正确"""
    buttons_config = settings.promotion_buttons
    
    # 检查包含必要的JSON元素
    assert "text" in buttons_config
    assert "{" in buttons_config
    assert "}" in buttons_config
    assert "[" in buttons_config
    assert "]" in buttons_config


def test_build_promotion_buttons():
    """测试构建引流按钮"""
    keyboard = MainMenuHandler._build_promotion_buttons()
    
    # 验证返回的是列表
    assert isinstance(keyboard, list)
    assert len(keyboard) > 0
    
    # 验证每行包含按钮
    for row in keyboard:
        assert isinstance(row, list)
        assert len(row) > 0
        assert len(row) <= 2  # 每行最多2个按钮


def test_promotion_buttons_contain_callbacks():
    """测试引流按钮包含回调数据"""
    keyboard = MainMenuHandler._build_promotion_buttons()
    
    has_callback = False
    for row in keyboard:
        for button in row:
            if hasattr(button, 'callback_data') and button.callback_data:
                has_callback = True
                # 验证回调数据格式
                assert isinstance(button.callback_data, str)
                assert len(button.callback_data) > 0
    
    assert has_callback, "至少应该有一个带回调数据的按钮"


def test_promotion_buttons_text_not_empty():
    """测试引流按钮文字不为空"""
    keyboard = MainMenuHandler._build_promotion_buttons()
    
    for row in keyboard:
        for button in row:
            assert hasattr(button, 'text')
            assert button.text
            assert len(button.text) > 0


def test_welcome_message_length():
    """测试欢迎语长度合理"""
    message = settings.welcome_message
    
    # Telegram 消息长度限制
    assert len(message) < 4096
    
    # 不能太短
    assert len(message) > 20


def test_promotion_buttons_default_values():
    """测试引流按钮包含默认功能"""
    buttons_config = settings.promotion_buttons.lower()
    
    # 检查是否包含主要功能关键词
    has_premium = "premium" in buttons_config or "会员" in buttons_config
    has_profile = "profile" in buttons_config or "中心" in buttons_config or "余额" in buttons_config
    has_energy = "energy" in buttons_config or "能量" in buttons_config
    
    # 至少包含一个主要功能
    assert has_premium or has_profile or has_energy
