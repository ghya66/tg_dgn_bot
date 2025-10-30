"""
文案配置辅助函数
提供便捷的文案获取方法，支持缓存和回退机制
"""
import logging
from typing import Optional
from src.bot_admin.config_manager import ConfigManager
from src.utils.config_cache import get_config_cache
from src.config import settings

logger = logging.getLogger(__name__)


class ContentHelper:
    """文案配置辅助类"""
    
    def __init__(self):
        """初始化辅助类"""
        self.config_mgr = ConfigManager()
        self.cache = get_config_cache()
    
    def get_content(self, key: str, default: Optional[str] = None) -> str:
        """
        获取文案配置（支持缓存和回退）
        
        Args:
            key: 配置键
            default: 默认值（从 settings 获取）
            
        Returns:
            文案内容
        """
        # 1. 尝试从缓存读取
        cached_value = self.cache.get(key)
        if cached_value is not None:
            return cached_value
        
        # 2. 从数据库读取
        try:
            db_value = self.config_mgr.get_content(key)
            if db_value:
                # 写入缓存
                self.cache.set(key, db_value)
                logger.debug(f"从数据库读取文案配置: {key}")
                return db_value
        except Exception as e:
            logger.error(f"读取数据库配置失败 ({key}): {e}")
        
        # 3. 使用默认值（从 config.py）
        if default:
            logger.warning(f"使用默认配置: {key}")
            return default
        
        # 4. 尝试从 settings 获取
        fallback = getattr(settings, key, None)
        if fallback:
            logger.warning(f"使用 settings 配置: {key}")
            return fallback
        
        # 5. 返回错误提示
        logger.error(f"配置不存在: {key}")
        return f"⚠️ 配置缺失: {key}"
    
    def clear_cache(self, key: Optional[str] = None):
        """
        清除缓存
        
        Args:
            key: 配置键，如果为 None 则清空所有缓存
        """
        if key:
            self.cache.delete(key)
            logger.info(f"已清除缓存: {key}")
        else:
            self.cache.clear()
            logger.info("已清空所有配置缓存")


# 全局单例
_content_helper = ContentHelper()


def get_content(key: str, default: Optional[str] = None) -> str:
    """
    便捷函数：获取文案配置
    
    Args:
        key: 配置键
        default: 默认值
        
    Returns:
        文案内容
    """
    return _content_helper.get_content(key, default)


def clear_content_cache(key: Optional[str] = None):
    """
    便捷函数：清除文案缓存
    
    Args:
        key: 配置键，如果为 None 则清空所有缓存
    """
    _content_helper.clear_cache(key)
