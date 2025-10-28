"""
地址验证器测试
"""
import pytest
from src.address_query.validator import AddressValidator


class TestAddressValidator:
    """地址验证器测试"""
    
    def test_valid_addresses(self):
        """测试有效地址"""
        valid_addresses = [
            "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH",
            "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # USDT contract
            "TN3W4H6rK2ce4vX9YnFQHwKENnHjoxb3m9",
            "TAUN6FwrnwwmaEqYcckffC7wYmbaS6cBiX",
        ]
        
        for addr in valid_addresses:
            is_valid, error_msg = AddressValidator.validate(addr)
            assert is_valid is True, f"地址 {addr} 应该有效，但验证失败: {error_msg}"
            assert error_msg is None
    
    def test_invalid_length(self):
        """测试长度错误"""
        # 太短
        is_valid, error_msg = AddressValidator.validate("TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZY")
        assert is_valid is False
        assert "长度错误" in error_msg
        assert "33" in error_msg
        
        # 太长
        is_valid, error_msg = AddressValidator.validate("TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYHH")
        assert is_valid is False
        assert "长度错误" in error_msg
        assert "35" in error_msg
    
    def test_invalid_prefix(self):
        """测试前缀错误"""
        # 不以 T 开头
        is_valid, error_msg = AddressValidator.validate("ALyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH")
        assert is_valid is False
        assert "T" in error_msg
        assert "开头" in error_msg
        
        # 以数字开头
        is_valid, error_msg = AddressValidator.validate("1LyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH")
        assert is_valid is False
    
    def test_invalid_characters(self):
        """测试无效字符（Base58 不包含 0, O, I, l）"""
        # 包含 0
        is_valid, error_msg = AddressValidator.validate("TLyqzVGLV1srkB7dT0TAEqgDSfPtXRJZYH")
        assert is_valid is False
        assert "无效字符" in error_msg
        
        # 包含 O
        is_valid, error_msg = AddressValidator.validate("TLyqzVGLV1srkB7dTOTAEqgDSfPtXRJZYH")
        assert is_valid is False
        
        # 包含 I
        is_valid, error_msg = AddressValidator.validate("TLyqzVGLV1srkB7dTITAEqgDSfPtXRJZYH")
        assert is_valid is False
        
        # 包含 l (小写 L)
        is_valid, error_msg = AddressValidator.validate("TLyqzVGLV1srkB7dTlTAEqgDSfPtXRJZYH")
        assert is_valid is False
    
    def test_empty_address(self):
        """测试空地址"""
        is_valid, error_msg = AddressValidator.validate("")
        assert is_valid is False
        assert "不能为空" in error_msg
    
    def test_special_characters(self):
        """测试特殊字符"""
        invalid_addresses = [
            "TLyqzVGLV1srkB7d@oTAEqgDSfPtXRJZYH",  # @
            "TLyqzVGLV1srkB7d#oTAEqgDSfPtXRJZYH",  # #
            "TLyqzVGLV1srkB7d-oTAEqgDSfPtXRJZYH",  # -
        ]
        
        for addr in invalid_addresses:
            is_valid, error_msg = AddressValidator.validate(addr)
            assert is_valid is False, f"地址 {addr} 应该无效"
            assert "无效字符" in error_msg
        
        # 空格会导致长度错误
        addr_with_space = "TLyqzVGLV1srkB7d ToTAEqgDSfPtXRJZYH"
        is_valid, error_msg = AddressValidator.validate(addr_with_space)
        assert is_valid is False
        assert "长度错误" in error_msg or "无效字符" in error_msg
    
    def test_ethereum_address(self):
        """测试以太坊地址（应拒绝）"""
        eth_addr = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        is_valid, error_msg = AddressValidator.validate(eth_addr)
        assert is_valid is False
        # 不以 T 开头，会先报这个错误
        assert "T" in error_msg or "开头" in error_msg
    
    def test_bitcoin_address(self):
        """测试比特币地址（应拒绝）"""
        btc_addr = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        is_valid, error_msg = AddressValidator.validate(btc_addr)
        assert is_valid is False
