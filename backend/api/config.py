"""
FastAPI 多环境配置管理
支持 dev/staging/prod 环境
"""
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    
    # ===== 环境配置 =====
    env: Literal["dev", "staging", "prod"] = Field(
        default="dev",
        description="运行环境"
    )
    debug: bool = Field(default=True, description="调试模式")
    
    # ===== 数据库配置 =====
    database_url: str = Field(
        default="sqlite:///./data/bot.db",
        description="数据库连接URL"
    )
    db_pool_size: int = Field(default=5, description="数据库连接池大小")
    db_max_overflow: int = Field(default=10, description="连接池溢出大小")
    
    # ===== Redis 配置 =====
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    redis_max_connections: int = Field(default=50, description="Redis最大连接数")
    
    # ===== API 配置 =====
    api_host: str = Field(default="0.0.0.0", description="API监听地址")
    api_port: int = Field(default=8000, description="API监听端口")
    api_workers: int = Field(default=4, description="API工作进程数")
    api_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="API密钥"
    )
    api_key_header: str = Field(default="X-API-Key", description="API Key请求头")
    
    # 支持两种字段名：api_key (单数, 向后兼容) 和 api_keys (复数, 推荐)
    api_key: Optional[str] = Field(default=None, description="API Key (向后兼容)")
    api_keys: Optional[str] = Field(default=None, description="允许的API Keys (逗号分隔)")
    
    # ===== Admin 配置 =====
    admin_host: str = Field(default="0.0.0.0", description="Admin监听地址")
    admin_port: int = Field(default=8501, description="Admin监听端口")
    admin_username: str = Field(default="admin", description="Admin用户名")
    admin_password: str = Field(default="admin123", description="Admin密码")
    
    # ===== Webhook 配置 =====
    webhook_ip_whitelist: str = Field(
        default="127.0.0.1,::1",
        description="Webhook IP白名单 (逗号分隔)"
    )
    webhook_signature_secret: str = Field(
        default="your-webhook-secret",
        description="Webhook签名密钥"
    )
    
    # ===== 限流配置 =====
    rate_limit_enabled: bool = Field(default=True, description="启用限流")
    rate_limit_per_minute: int = Field(default=60, description="每分钟请求限制")
    rate_limit_per_hour: int = Field(default=1000, description="每小时请求限制")
    
    # ===== 熔断配置 =====
    circuit_breaker_enabled: bool = Field(default=True, description="启用熔断器")
    circuit_failure_threshold: int = Field(default=5, description="熔断失败阈值")
    circuit_recovery_timeout: int = Field(default=60, description="熔断恢复超时(秒)")
    
    # ===== 日志配置 =====
    log_level: str = Field(default="INFO", description="日志级别")
    log_json_format: bool = Field(default=False, description="JSON格式日志")
    
    # ===== 监控配置 =====
    prometheus_enabled: bool = Field(default=True, description="启用Prometheus")
    otlp_endpoint: str = Field(default="", description="OpenTelemetry端点")
    sentry_dsn: str = Field(default="", description="Sentry DSN")
    
    # ===== 任务队列配置 =====
    arq_max_jobs: int = Field(default=10, description="arq最大并发任务数")
    arq_job_timeout: int = Field(default=300, description="任务超时(秒)")
    arq_max_tries: int = Field(default=3, description="任务最大重试次数")
    
    # ===== TRC20 配置 (复用现有) =====
    usdt_trc20_receive_addr: str = Field(
        default="TYourReceiveAddress",
        description="USDT TRC20 收款地址"
    )
    trc20_api_url: str = Field(
        default="https://api.trongrid.io",
        description="TRC20 API地址"
    )
    
    # ===== Telegram Bot 配置 (复用现有) =====
    bot_token: str = Field(default="", description="Telegram Bot Token")
    bot_webhook_url: str = Field(default="", description="Bot Webhook URL")
    
    # ===== 业务配置 =====
    order_timeout_minutes: int = Field(default=30, description="订单超时时间(分钟)")
    premium_prices: str = Field(
        default='{"3": 10.0, "6": 18.0, "12": 30.0}',
        description="Premium价格配置(JSON)"
    )
    
    # ===== 属性方法 =====
    @property
    def is_production(self) -> bool:
        """是否生产环境"""
        return self.env == "prod"
    
    @property
    def is_development(self) -> bool:
        """是否开发环境"""
        return self.env == "dev"
    
    @property
    def allowed_api_keys(self) -> list[str]:
        """
        解析API Keys列表
        
        优先使用 api_keys (复数)，如果不存在则使用 api_key (单数)
        """
        # 优先使用复数形式
        keys_str = self.api_keys or self.api_key or "dev-key-12345"
        return [k.strip() for k in keys_str.split(",") if k.strip()]
    
    @property
    def webhook_allowed_ips(self) -> list[str]:
        """解析Webhook白名单IP列表"""
        return [ip.strip() for ip in self.webhook_ip_whitelist.split(",") if ip.strip()]


# 全局配置实例
settings = Settings()
