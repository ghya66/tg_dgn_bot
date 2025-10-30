"""
配置缓存管理器
用于缓存数据库配置，减少查询次数，提升响应速度
"""
import time
import logging
from typing import Optional, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)


class ConfigCache:
    """配置缓存管理器（线程安全）"""
    
    def __init__(self, ttl: int = 300):
        """
        初始化缓存管理器
        
        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
        """
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[str]:
        """
        从缓存获取配置
        
        Args:
            key: 配置键
            
        Returns:
            配置值，如果不存在或已过期则返回 None
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            cached = self._cache[key]
            
            # 检查是否过期
            if time.time() - cached['timestamp'] > self.ttl:
                logger.debug(f"配置缓存过期: {key}")
                del self._cache[key]
                return None
            
            logger.debug(f"从缓存读取配置: {key}")
            return cached['value']
    
    def set(self, key: str, value: str):
        """
        设置缓存
        
        Args:
            key: 配置键
            value: 配置值
        """
        with self._lock:
            self._cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
            logger.debug(f"配置已缓存: {key}")
    
    def delete(self, key: str):
        """
        删除缓存
        
        Args:
            key: 配置键
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"配置缓存已删除: {key}")
    
    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("配置缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            valid_count = 0
            expired_count = 0
            
            for key, cached in self._cache.items():
                if time.time() - cached['timestamp'] > self.ttl:
                    expired_count += 1
                else:
                    valid_count += 1
            
            return {
                'total': len(self._cache),
                'valid': valid_count,
                'expired': expired_count,
                'ttl': self.ttl
            }


# 全局单例
_config_cache = ConfigCache(ttl=300)  # 5 分钟 TTL


def get_config_cache() -> ConfigCache:
    """获取全局配置缓存实例"""
    return _config_cache
