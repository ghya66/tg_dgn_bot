"""
测试多环境配置系统
"""
import pytest
import os
from backend.api.config import Settings


def test_config_default_values():
    """测试默认配置值"""
    settings = Settings()
    
    assert settings.env == "dev"
    assert settings.debug is True
    assert settings.api_port == 8000
    assert settings.admin_port == 8501
    assert settings.database_url == "sqlite:///./data/bot.db"
    assert settings.redis_url == "redis://localhost:6379/0"


def test_config_is_development():
    """测试开发环境判断"""
    settings = Settings(env="dev")
    assert settings.is_development
    assert not settings.is_production


def test_config_is_production(monkeypatch):
    """测试生产环境判断"""
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("DEBUG", "false")
    
    settings = Settings()
    assert settings.is_production
    assert not settings.is_development
    assert settings.debug is False


def test_config_parse_api_keys():
    """测试API Keys解析"""
    settings = Settings(api_keys="key1,key2,key3")
    
    assert settings.allowed_api_keys == ["key1", "key2", "key3"]


def test_config_parse_api_keys_with_spaces():
    """测试API Keys解析（带空格）"""
    settings = Settings(api_keys="key1, key2 , key3")
    
    assert settings.allowed_api_keys == ["key1", "key2", "key3"]


def test_config_parse_webhook_ips():
    """测试Webhook IP白名单解析"""
    settings = Settings(webhook_ip_whitelist="127.0.0.1,192.168.1.1,10.0.0.1")
    
    assert settings.webhook_allowed_ips == ["127.0.0.1", "192.168.1.1", "10.0.0.1"]


def test_config_from_env_file(tmp_path, monkeypatch):
    """测试从环境文件加载配置"""
    # 创建临时 .env 文件
    env_file = tmp_path / ".env"
    env_file.write_text("""
ENV=staging
DEBUG=false
API_PORT=9000
ADMIN_USERNAME=test_admin
ADMIN_PASSWORD=test_password
    """.strip())
    
    # 设置环境变量指向临时文件
    monkeypatch.chdir(tmp_path)
    
    settings = Settings(_env_file=str(env_file))
    
    assert settings.env == "staging"
    assert settings.debug is False
    assert settings.api_port == 9000
    assert settings.admin_username == "test_admin"
    assert settings.admin_password == "test_password"


def test_config_rate_limit_defaults():
    """测试限流配置默认值"""
    settings = Settings()
    
    assert settings.rate_limit_enabled is True
    assert settings.rate_limit_per_minute == 60
    assert settings.rate_limit_per_hour == 1000


def test_config_circuit_breaker_defaults():
    """测试熔断器配置默认值"""
    settings = Settings()
    
    assert settings.circuit_breaker_enabled is True
    assert settings.circuit_failure_threshold == 5
    assert settings.circuit_recovery_timeout == 60


def test_config_arq_defaults():
    """测试arq任务队列配置默认值"""
    settings = Settings()
    
    assert settings.arq_max_jobs == 10
    assert settings.arq_job_timeout == 300
    assert settings.arq_max_tries == 3


def test_config_monitoring_defaults():
    """测试监控配置默认值"""
    settings = Settings()
    
    assert settings.prometheus_enabled is True
    assert settings.otlp_endpoint == ""
    assert settings.sentry_dsn == ""
    assert settings.log_level == "INFO"


def test_config_log_json_format_production(monkeypatch):
    """测试生产环境JSON日志格式"""
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("LOG_JSON_FORMAT", "true")
    
    settings = Settings()
    assert settings.log_json_format is True


def test_config_empty_api_keys():
    """测试空API Keys"""
    settings = Settings(api_keys="")
    assert settings.allowed_api_keys == []


def test_config_empty_webhook_ips():
    """测试空Webhook IP白名单"""
    settings = Settings(webhook_ip_whitelist="")
    assert settings.webhook_allowed_ips == []
