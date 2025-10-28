"""
区块链浏览器链接测试
"""
import pytest
from unittest.mock import patch
from src.address_query.explorer import explorer_links


class TestExplorerLinks:
    """浏览器链接测试"""
    
    def test_tronscan_links(self):
        """测试 Tronscan 链接生成"""
        with patch('src.address_query.explorer.settings') as mock_settings:
            mock_settings.tron_explorer = 'tronscan'
            
            address = "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH"
            links = explorer_links(address)
            
            assert "overview" in links
            assert "txs" in links
            assert "tronscan.org" in links["overview"]
            assert "tronscan.org" in links["txs"]
            assert address in links["overview"]
            assert address in links["txs"]
            assert "/address/" in links["overview"]
            assert "/transfers" in links["txs"]
    
    def test_oklink_links(self):
        """测试 OKLink 链接生成"""
        with patch('src.address_query.explorer.settings') as mock_settings:
            mock_settings.tron_explorer = 'oklink'
            
            address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
            links = explorer_links(address)
            
            assert "overview" in links
            assert "txs" in links
            assert "oklink.com" in links["overview"]
            assert "oklink.com" in links["txs"]
            assert address in links["overview"]
            assert address in links["txs"]
            assert "/address/" in links["overview"]
            assert "/transaction" in links["txs"]
    
    def test_default_to_tronscan(self):
        """测试默认使用 Tronscan"""
        with patch('src.address_query.explorer.settings') as mock_settings:
            mock_settings.tron_explorer = 'unknown'
            
            address = "TN3W4H6rK2ce4vX9YnFQHwKENnHjoxb3m9"
            links = explorer_links(address)
            
            # 未知配置应默认使用 tronscan
            assert "tronscan.org" in links["overview"]
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        with patch('src.address_query.explorer.settings') as mock_settings:
            mock_settings.tron_explorer = 'OKLINK'  # 大写
            
            address = "TAUN6FwrnwwmaEqYcckffC7wYmbaS6cBiX"
            links = explorer_links(address)
            
            assert "oklink.com" in links["overview"]
    
    def test_links_structure(self):
        """测试链接结构正确性"""
        with patch('src.address_query.explorer.settings') as mock_settings:
            mock_settings.tron_explorer = 'tronscan'
            
            address = "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH"
            links = explorer_links(address)
            
            # 验证返回字典结构
            assert isinstance(links, dict)
            assert len(links) == 2
            assert all(isinstance(v, str) for v in links.values())
            
            # 验证 URL 有效性（基本检查）
            assert links["overview"].startswith("https://")
            assert links["txs"].startswith("https://")
