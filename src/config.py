"""
配置管理模块
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # Telegram Bot
    bot_token: str
    
    # USDT TRC20 支付
    usdt_trc20_receive_addr: str
    
    # HMAC 签名
    webhook_secret: str
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # 订单设置
    order_timeout_minutes: int = 30
    base_price_decimal_places: int = 3
    
    # TRON API (可选)
    tron_api_url: str = ""
    tron_api_key: str = ""
    tron_explorer: str = "tronscan"  # tronscan | oklink
    
    # 地址查询限频（分钟）
    address_query_rate_limit_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()