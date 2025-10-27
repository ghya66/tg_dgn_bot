"""
订单金额计算模块
base_amount + unique_suffix = final_amount
使用整数化（×10^6）避免浮点误差
"""
from typing import Tuple


class AmountCalculator:
    """金额计算器"""
    
    MICRO_USDT_MULTIPLIER = 1000000  # 10^6
    
    @staticmethod
    def generate_payment_amount(base_amount: float, unique_suffix: int) -> float:
        """
        生成支付金额
        
        Args:
            base_amount: 基础金额
            unique_suffix: 唯一后缀 (1-999)
            
        Returns:
            最终支付金额
        """
        if not (1 <= unique_suffix <= 999):
            raise ValueError("Unique suffix must be between 1 and 999")
        
        # 后缀转换为小数部分 (0.001 - 0.999)
        suffix_decimal = unique_suffix / 1000.0
        
        return base_amount + suffix_decimal
    
    @staticmethod
    def verify_amount(expected_amount: float, received_amount: float) -> bool:
        """
        验证金额是否匹配（使用整数化避免浮点误差）
        
        Args:
            expected_amount: 期望的金额
            received_amount: 接收到的金额
            
        Returns:
            是否匹配
        """
        # 转换为微USDT (乘以10^6)
        expected_micro = int(round(expected_amount * AmountCalculator.MICRO_USDT_MULTIPLIER))
        received_micro = int(round(received_amount * AmountCalculator.MICRO_USDT_MULTIPLIER))
        
        return expected_micro == received_micro
    
    @staticmethod
    def amount_to_micro_usdt(amount: float) -> int:
        """
        将金额转换为微USDT
        
        Args:
            amount: USDT金额
            
        Returns:
            微USDT金额
        """
        return int(round(amount * AmountCalculator.MICRO_USDT_MULTIPLIER))
    
    @staticmethod
    def micro_usdt_to_amount(micro_amount: int) -> float:
        """
        将微USDT转换为USDT金额
        
        Args:
            micro_amount: 微USDT金额
            
        Returns:
            USDT金额
        """
        return micro_amount / AmountCalculator.MICRO_USDT_MULTIPLIER
    
    @staticmethod
    def extract_suffix_from_amount(final_amount: float, base_amount: float) -> int:
        """
        从最终金额中提取后缀
        
        Args:
            final_amount: 最终金额
            base_amount: 基础金额
            
        Returns:
            后缀值 (1-999)
        """
        suffix_decimal = final_amount - base_amount
        suffix = int(round(suffix_decimal * 1000))
        
        if not (1 <= suffix <= 999):
            raise ValueError(f"Invalid suffix extracted: {suffix}")
        
        return suffix
    
    @staticmethod
    def is_valid_payment_amount(amount: float, min_base: float = 0.001, max_base: float = 999999.0) -> bool:
        """
        验证支付金额是否有效
        
        Args:
            amount: 支付金额
            min_base: 最小基础金额
            max_base: 最大基础金额
            
        Returns:
            是否有效
        """
        # 检查金额范围 - 最小值是 min_base，最大值是 max_base + 0.999
        if amount < min_base or amount > max_base + 0.999:
            return False
        
        # 将金额转换为字符串检查小数位数（不四舍五入）
        amount_str = str(amount)
        
        # 检查是否有小数点
        if '.' not in amount_str:
            return False
            
        decimal_part = amount_str.split('.')[1]
        
        # 必须恰好有3位小数
        if len(decimal_part) != 3:
            return False
        
        # 检查小数后缀是否在1-999范围内
        try:
            micro_decimal = int(decimal_part)
        except ValueError:
            return False
        
        # 后缀必须在1-999范围内
        return 1 <= micro_decimal <= 999


# 创建全局实例以便导入使用
amount_calculator = AmountCalculator()