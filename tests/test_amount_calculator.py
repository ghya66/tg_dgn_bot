"""
金额计算器测试
"""
import pytest
from src.payments.amount_calculator import AmountCalculator


def test_generate_payment_amount():
    """测试生成支付金额"""
    # 基本测试
    assert AmountCalculator.generate_payment_amount(10.0, 123) == 10.123
    assert AmountCalculator.generate_payment_amount(0.0, 1) == 0.001
    assert AmountCalculator.generate_payment_amount(999.0, 999) == 999.999
    
    # 边界测试
    assert AmountCalculator.generate_payment_amount(5.5, 1) == 5.501
    assert AmountCalculator.generate_payment_amount(100.25, 567) == 100.817


def test_generate_payment_amount_invalid_suffix():
    """测试无效后缀"""
    with pytest.raises(ValueError):
        AmountCalculator.generate_payment_amount(10.0, 0)  # 小于1
    
    with pytest.raises(ValueError):
        AmountCalculator.generate_payment_amount(10.0, 1000)  # 大于999


def test_verify_amount():
    """测试金额验证"""
    # 精确匹配
    assert AmountCalculator.verify_amount(10.123, 10.123) is True
    
    # 浮点误差测试
    amount1 = 10.1 + 0.023  # 可能有浮点误差
    amount2 = 10.123
    assert AmountCalculator.verify_amount(amount1, amount2) is True
    
    # 不匹配
    assert AmountCalculator.verify_amount(10.123, 10.124) is False
    
    # 边界情况
    assert AmountCalculator.verify_amount(0.001, 0.001) is True
    assert AmountCalculator.verify_amount(999.999, 999.999) is True


def test_amount_to_micro_usdt():
    """测试USDT转微USDT"""
    assert AmountCalculator.amount_to_micro_usdt(10.123) == 10123000
    assert AmountCalculator.amount_to_micro_usdt(0.001) == 1000
    assert AmountCalculator.amount_to_micro_usdt(999.999) == 999999000
    
    # 测试浮点精度
    assert AmountCalculator.amount_to_micro_usdt(10.123456) == 10123456


def test_micro_usdt_to_amount():
    """测试微USDT转USDT"""
    assert AmountCalculator.micro_usdt_to_amount(10123000) == 10.123
    assert AmountCalculator.micro_usdt_to_amount(1000) == 0.001
    assert AmountCalculator.micro_usdt_to_amount(999999000) == 999.999


def test_extract_suffix_from_amount():
    """测试从金额中提取后缀"""
    assert AmountCalculator.extract_suffix_from_amount(10.123, 10.0) == 123
    assert AmountCalculator.extract_suffix_from_amount(5.001, 5.0) == 1
    assert AmountCalculator.extract_suffix_from_amount(100.999, 100.0) == 999


def test_extract_suffix_invalid():
    """测试提取无效后缀"""
    with pytest.raises(ValueError):
        AmountCalculator.extract_suffix_from_amount(10.0, 10.0)  # 后缀为0
    
    with pytest.raises(ValueError):
        AmountCalculator.extract_suffix_from_amount(11.0, 10.0)  # 后缀为1000


def test_is_valid_payment_amount():
    """测试支付金额有效性"""
    # 有效金额
    assert AmountCalculator.is_valid_payment_amount(10.123) is True
    assert AmountCalculator.is_valid_payment_amount(0.001) is True
    assert AmountCalculator.is_valid_payment_amount(999.999) is True
    
    # 无效金额（没有3位小数后缀）
    assert AmountCalculator.is_valid_payment_amount(10.0) is False
    assert AmountCalculator.is_valid_payment_amount(10.1234) is False
    
    # 超出范围
    assert AmountCalculator.is_valid_payment_amount(0.0005) is False  # 太小
    assert AmountCalculator.is_valid_payment_amount(1000000.001) is False  # 太大


def test_round_trip_conversion():
    """测试往返转换的精度"""
    original_amounts = [0.001, 10.123, 999.999, 123.456]
    
    for amount in original_amounts:
        micro = AmountCalculator.amount_to_micro_usdt(amount)
        converted_back = AmountCalculator.micro_usdt_to_amount(micro)
        assert abs(amount - converted_back) < 0.000001  # 精度测试


def test_suffix_extraction_round_trip():
    """测试后缀提取的往返一致性"""
    base_amounts = [0.0, 10.0, 100.5, 999.0]
    suffixes = [1, 123, 456, 999]
    
    for base in base_amounts:
        for suffix in suffixes:
            # 生成金额
            total = AmountCalculator.generate_payment_amount(base, suffix)
            
            # 提取后缀
            extracted_suffix = AmountCalculator.extract_suffix_from_amount(total, base)
            
            # 验证一致性
            assert extracted_suffix == suffix