#!/usr/bin/env python3
"""
配置验证工具
检查所有必需的环境变量是否已正确配置
"""
import sys
import os
from pathlib import Path
from typing import List, Tuple

# 设置 PYTHONPATH 以便导入 src 模块
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


def check_env_file() -> bool:
    """检查 .env 文件是否存在"""
    if not os.path.exists('.env'):
        print("❌ 错误: .env 文件不存在")
        print("请复制 .env.example 并配置：")
        print("  cp .env.example .env")
        return False
    return True


def check_required_vars() -> Tuple[bool, List[str]]:
    """检查必需的环境变量"""
    required_vars = [
        'BOT_TOKEN',
        'USDT_TRC20_RECEIVE_ADDR',
        'WEBHOOK_SECRET',
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == f"your_{var.lower()}":
            missing_vars.append(var)
    
    return len(missing_vars) == 0, missing_vars


def check_optional_vars() -> List[str]:
    """检查可选的环境变量"""
    optional_vars = {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'REDIS_DB': '0',
        'ORDER_TIMEOUT_MINUTES': '30',
        'TRON_EXPLORER': 'tronscan',
        'ADDRESS_QUERY_RATE_LIMIT_MINUTES': '30',
    }
    
    warnings = []
    for var, default in optional_vars.items():
        value = os.getenv(var)
        if not value:
            warnings.append(f"{var} (使用默认值: {default})")
    
    return warnings


def validate_bot_token() -> bool:
    """验证 Bot Token 格式"""
    token = os.getenv('BOT_TOKEN', '')
    if not token or ':' not in token:
        print("❌ BOT_TOKEN 格式错误")
        print("正确格式: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        return False
    return True


def validate_address() -> bool:
    """验证 USDT 收款地址"""
    addr = os.getenv('USDT_TRC20_RECEIVE_ADDR', '')
    if not addr or not addr.startswith('T') or len(addr) != 34:
        print("❌ USDT_TRC20_RECEIVE_ADDR 格式错误")
        print("应为波场地址（T开头，34位）")
        return False
    return True


def main():
    """主函数"""
    print("🔍 开始配置验证...\n")
    
    # 加载 .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv 未安装，跳过 .env 加载")
    
    success = True
    
    # 检查 .env 文件
    if not check_env_file():
        return 1
    
    print("✅ .env 文件存在\n")
    
    # 检查必需变量
    print("📋 检查必需配置...")
    has_required, missing = check_required_vars()
    
    if not has_required:
        print("❌ 缺少必需的环境变量:")
        for var in missing:
            print(f"  • {var}")
        success = False
    else:
        print("✅ 所有必需配置已设置")
    
    # 验证格式
    if os.getenv('BOT_TOKEN'):
        if validate_bot_token():
            print("✅ BOT_TOKEN 格式正确")
        else:
            success = False
    
    if os.getenv('USDT_TRC20_RECEIVE_ADDR'):
        if validate_address():
            print("✅ USDT_TRC20_RECEIVE_ADDR 格式正确")
        else:
            success = False
    
    # 检查可选变量
    print("\n📋 检查可选配置...")
    warnings = check_optional_vars()
    
    if warnings:
        print("ℹ️  以下配置使用默认值:")
        for warning in warnings:
            print(f"  • {warning}")
    else:
        print("✅ 所有可选配置已设置")
    
    # 检查 Redis 连接
    print("\n🔍 检查 Redis 连接...")
    try:
        import redis
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_db = int(os.getenv('REDIS_DB', '0'))
        
        r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, socket_connect_timeout=2)
        r.ping()
        print(f"✅ Redis 连接成功 ({redis_host}:{redis_port}/{redis_db})")
    except ImportError:
        print("⚠️  redis 模块未安装")
        success = False
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        success = False
    
    # 检查数据库
    print("\n🔍 检查数据库...")
    try:
        from src.database import engine
        with engine.connect() as conn:
            print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        success = False
    
    # 总结
    print("\n" + "="*50)
    if success:
        print("✅ 配置验证通过！可以启动 Bot")
        print("\n运行以下命令启动：")
        print("  ./scripts/start_bot.sh")
        print("  或: python3 -m src.bot")
        return 0
    else:
        print("❌ 配置验证失败，请修复上述问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())
