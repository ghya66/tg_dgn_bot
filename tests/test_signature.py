"""
HMAC签名验证测试
"""
import pytest
import json
import hmac
import hashlib

from src.signature import SignatureValidator


def test_generate_signature():
    """测试生成HMAC签名"""
    data = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "tx_hash": "test_tx_hash",
        "block_number": 12345678,
        "timestamp": 1635724800
    }
    secret = "test_secret_key"
    
    signature = SignatureValidator.generate_signature(data, secret)
    
    # 验证签名格式
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256十六进制长度
    
    # 验证签名内容
    sorted_data = dict(sorted(data.items()))
    message = json.dumps(sorted_data, separators=(',', ':'), ensure_ascii=True)
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    assert signature == expected_signature


def test_verify_signature_valid():
    """测试验证有效签名"""
    data = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "tx_hash": "test_tx_hash",
        "block_number": 12345678,
        "timestamp": 1635724800
    }
    secret = "test_secret_key"
    
    # 生成签名
    signature = SignatureValidator.generate_signature(data, secret)
    
    # 验证签名
    is_valid = SignatureValidator.verify_signature(data, signature, secret)
    
    assert is_valid is True


def test_verify_signature_invalid():
    """测试验证无效签名"""
    data = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "tx_hash": "test_tx_hash",
        "block_number": 12345678,
        "timestamp": 1635724800
    }
    secret = "test_secret_key"
    
    # 使用错误的签名
    invalid_signature = "invalid_signature_123"
    
    # 验证签名
    is_valid = SignatureValidator.verify_signature(data, invalid_signature, secret)
    
    assert is_valid is False


def test_verify_signature_wrong_secret():
    """测试使用错误密钥验证签名"""
    data = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "tx_hash": "test_tx_hash",
        "block_number": 12345678,
        "timestamp": 1635724800
    }
    secret = "test_secret_key"
    wrong_secret = "wrong_secret_key"
    
    # 用正确密钥生成签名
    signature = SignatureValidator.generate_signature(data, secret)
    
    # 用错误密钥验证签名
    is_valid = SignatureValidator.verify_signature(data, signature, wrong_secret)
    
    assert is_valid is False


def test_verify_signature_modified_data():
    """测试验证被修改数据的签名"""
    original_data = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "tx_hash": "test_tx_hash",
        "block_number": 12345678,
        "timestamp": 1635724800
    }
    secret = "test_secret_key"
    
    # 生成原始数据的签名
    signature = SignatureValidator.generate_signature(original_data, secret)
    
    # 修改数据
    modified_data = original_data.copy()
    modified_data["amount"] = 20.123  # 修改金额
    
    # 用修改后的数据验证原始签名
    is_valid = SignatureValidator.verify_signature(modified_data, signature, secret)
    
    assert is_valid is False


def test_signature_data_order_independence():
    """测试签名不受数据字段顺序影响"""
    data1 = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "tx_hash": "test_tx_hash",
        "block_number": 12345678,
        "timestamp": 1635724800
    }
    
    # 改变字段顺序
    data2 = {
        "timestamp": 1635724800,
        "block_number": 12345678,
        "tx_hash": "test_tx_hash",
        "amount": 10.123,
        "order_id": "test_order_123"
    }
    
    secret = "test_secret_key"
    
    signature1 = SignatureValidator.generate_signature(data1, secret)
    signature2 = SignatureValidator.generate_signature(data2, secret)
    
    # 签名应该相同
    assert signature1 == signature2


def test_prepare_callback_data():
    """测试准备回调数据"""
    order_id = "test_order_123"
    amount = 10.123
    tx_hash = "test_tx_hash"
    block_number = 12345678
    timestamp = 1635724800
    
    data = SignatureValidator.prepare_callback_data(
        order_id, amount, tx_hash, block_number, timestamp
    )
    
    expected_data = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "txid": "test_tx_hash",  # 字段名改为 txid
        "block_number": 12345678,
        "timestamp": 1635724800
    }
    
    assert data == expected_data


def test_create_signed_callback():
    """测试创建带签名的回调数据"""
    order_id = "test_order_123"
    amount = 10.123
    tx_hash = "test_tx_hash"
    block_number = 12345678
    timestamp = 1635724800
    secret = "test_secret_key"
    
    callback_data = SignatureValidator.create_signed_callback(
        order_id, amount, tx_hash, block_number, timestamp, secret
    )
    
    # 验证包含所有必需字段
    assert "order_id" in callback_data
    assert "amount" in callback_data
    assert "txid" in callback_data  # 字段名改为 txid
    assert "block_number" in callback_data
    assert "timestamp" in callback_data
    assert "signature" in callback_data
    
    # 验证签名有效性
    signature = callback_data.pop("signature")
    is_valid = SignatureValidator.verify_signature(callback_data, signature, secret)
    
    assert is_valid is True


def test_signature_with_special_characters():
    """测试包含特殊字符的数据签名"""
    data = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "tx_hash": "0x1234567890abcdef",
        "message": "Special chars: 中文, émojis 🚀, quotes \"'",
        "timestamp": 1635724800
    }
    secret = "test_secret_key"
    
    # 生成并验证签名
    signature = SignatureValidator.generate_signature(data, secret)
    is_valid = SignatureValidator.verify_signature(data, signature, secret)
    
    assert is_valid is True


def test_signature_with_numeric_precision():
    """测试数值精度对签名的影响"""
    # 测试浮点数精度
    data1 = {
        "order_id": "test_order_123",
        "amount": 10.123456789,
        "timestamp": 1635724800
    }
    
    data2 = {
        "order_id": "test_order_123",
        "amount": 10.123456789,  # 完全相同
        "timestamp": 1635724800
    }
    
    data3 = {
        "order_id": "test_order_123",
        "amount": 10.12345678,  # 精度不同
        "timestamp": 1635724800
    }
    
    secret = "test_secret_key"
    
    signature1 = SignatureValidator.generate_signature(data1, secret)
    signature2 = SignatureValidator.generate_signature(data2, secret)
    signature3 = SignatureValidator.generate_signature(data3, secret)
    
    # 相同数据应该产生相同签名
    assert signature1 == signature2
    
    # 不同精度应该产生不同签名
    assert signature1 != signature3


def test_empty_data_signature():
    """测试空数据的签名"""
    data = {}
    secret = "test_secret_key"
    
    signature = SignatureValidator.generate_signature(data, secret)
    is_valid = SignatureValidator.verify_signature(data, signature, secret)
    
    assert is_valid is True
    assert isinstance(signature, str)
    assert len(signature) == 64


def test_none_values_in_data():
    """测试数据中包含None值的情况"""
    data = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "optional_field": None,
        "timestamp": 1635724800
    }
    secret = "test_secret_key"
    
    signature = SignatureValidator.generate_signature(data, secret)
    is_valid = SignatureValidator.verify_signature(data, signature, secret)
    
    assert is_valid is True