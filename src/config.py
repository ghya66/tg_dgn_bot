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
    
    # 能量API配置
    energy_api_username: str = ""
    energy_api_password: str = ""
    energy_api_base_url: str = "https://trxno.com"
    energy_api_backup_url: str = "https://trxfast.com"
    
    # 免费克隆功能文案
    free_clone_message: str = (
        "🎁 <b>免费克隆服务</b>\n\n"
        "本 Bot 支持免费克隆功能！\n\n"
        "📋 <b>服务内容：</b>\n"
        "• 克隆 Telegram 群组\n"
        "• 克隆频道内容\n"
        "• 批量导入成员\n\n"
        "💡 <b>申请方式：</b>\n"
        "需要使用此服务，请联系客服申请。\n\n"
        "👨‍💼 客服将为您提供详细的使用指南和技术支持。"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()