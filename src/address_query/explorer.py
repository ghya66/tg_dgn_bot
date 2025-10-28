"""
区块链浏览器链接生成器
"""
from typing import Dict
from ..config import settings


def explorer_links(address: str) -> Dict[str, str]:
    """
    生成浏览器链接
    
    Args:
        address: 波场地址
        
    Returns:
        包含 overview 和 txs 链接的字典
    """
    explorer = getattr(settings, 'tron_explorer', 'tronscan').lower()
    
    if explorer == 'oklink':
        base_url = "https://www.oklink.com/zh-hans/trx"
        return {
            "overview": f"{base_url}/address/{address}",
            "txs": f"{base_url}/address/{address}/transaction"
        }
    else:  # tronscan (default)
        base_url = "https://tronscan.org/#"
        return {
            "overview": f"{base_url}/address/{address}",
            "txs": f"{base_url}/address/{address}/transfers"
        }
