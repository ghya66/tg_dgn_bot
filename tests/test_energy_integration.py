#!/usr/bin/env python3
"""
能量兑换功能快速测试
测试API连接、配置验证、数据库结构
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config import settings
from src.energy.client import EnergyAPIClient, EnergyAPIError
from src.database import init_db, get_db, close_db, EnergyOrder


async def test_config():
    """测试配置"""
    print("🔍 检查能量API配置...")
    
    if not settings.energy_api_username:
        print("❌ 错误: ENERGY_API_USERNAME 未设置")
        return False
    
    if not settings.energy_api_password:
        print("❌ 错误: ENERGY_API_PASSWORD 未设置")
        return False
    
    print(f"✅ 用户名: {settings.energy_api_username}")
    print(f"✅ 主URL: {settings.energy_api_base_url}")
    print(f"✅ 备用URL: {settings.energy_api_backup_url}")
    
    return True


async def test_database():
    """测试数据库"""
    print("\n🔍 检查数据库表...")
    
    try:
        # 初始化数据库
        init_db()
        
        # 查询能量订单表
        db = get_db()
        try:
            count = db.query(EnergyOrder).count()
            print(f"✅ energy_orders 表存在，当前订单数: {count}")
            return True
        finally:
            close_db(db)
            
    except Exception as e:
        print(f"❌ 数据库错误: {e}")
        return False


async def test_api_connection():
    """测试API连接"""
    print("\n🔍 测试API连接...")
    
    client = EnergyAPIClient(
        username=settings.energy_api_username,
        password=settings.energy_api_password,
        base_url=settings.energy_api_base_url,
        backup_url=settings.energy_api_backup_url
    )
    
    try:
        # 查询账号信息
        print("📡 正在查询账号信息...")
        info = await client.get_account_info()
        
        print(f"✅ 连接成功!")
        print(f"  用户名: {info.username}")
        print(f"  TRX余额: {info.balance_trx}")
        print(f"  USDT余额: {info.balance_usdt}")
        print(f"  冻结余额: {info.frozen_balance}")
        
        # 查询价格
        print("\n📡 正在查询价格...")
        prices = await client.query_price()
        
        print(f"✅ 价格查询成功!")
        print(f"  6.5万能量: {prices.energy_65k_price} TRX")
        print(f"  13.1万能量: {prices.energy_131k_price} TRX")
        print(f"  笔数套餐: {prices.package_price} TRX/笔")
        
        return True
        
    except EnergyAPIError as e:
        print(f"❌ API错误: {e.code} - {e.message}")
        return False
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False
        
    finally:
        await client.close()


async def main():
    """主测试函数"""
    print("=" * 60)
    print("⚡ 能量兑换功能测试")
    print("=" * 60)
    
    # 测试配置
    if not await test_config():
        print("\n❌ 配置检查失败，请设置 ENERGY_API_USERNAME 和 ENERGY_API_PASSWORD")
        return 1
    
    # 测试数据库
    if not await test_database():
        print("\n❌ 数据库检查失败")
        return 1
    
    # 测试API连接
    if not await test_api_connection():
        print("\n❌ API连接测试失败")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！能量兑换功能已就绪")
    print("=" * 60)
    
    print("\n💡 下一步:")
    print("  1. 启动Bot: ./scripts/start_bot.sh")
    print("  2. 在Telegram中发送 /start")
    print("  3. 点击 '⚡ 能量兑换' 按钮")
    print("  4. 按照提示完成购买流程")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  测试中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
