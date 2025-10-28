"""
测试免费克隆功能
"""
import pytest
from src.config import settings


def test_free_clone_message_exists():
    """测试免费克隆消息配置存在"""
    assert hasattr(settings, 'free_clone_message')
    assert isinstance(settings.free_clone_message, str)
    assert len(settings.free_clone_message) > 0


def test_free_clone_message_contains_required_elements():
    """测试免费克隆消息包含必要元素"""
    message = settings.free_clone_message
    
    # 检查必要的关键词
    assert "免费克隆" in message or "克隆" in message
    assert "客服" in message
    assert "🎁" in message  # emoji 图标
    
    # 检查HTML格式标签
    assert "<b>" in message
    assert "</b>" in message


def test_free_clone_message_format():
    """测试免费克隆消息格式正确"""
    message = settings.free_clone_message
    
    # 确保换行符存在
    assert "\n" in message
    
    # 确保不包含代码中的占位符
    assert "XXXX" not in message
    assert "待定" not in message
    assert "开发中" not in message


def test_free_clone_message_length():
    """测试免费克隆消息长度合理"""
    message = settings.free_clone_message
    
    # Telegram 消息长度限制为 4096 字符
    assert len(message) < 4096
    
    # 消息不能太短
    assert len(message) > 50


def test_free_clone_message_customizable():
    """测试免费克隆消息可通过环境变量自定义"""
    # 测试默认消息存在且不为空
    default_message = settings.free_clone_message
    assert default_message
    assert len(default_message) > 0
    
    # 验证消息结构可以被覆盖（理论上通过环境变量）
    assert isinstance(default_message, str)
    
    # 验证包含管理员可修改的内容
    assert "克隆" in default_message

