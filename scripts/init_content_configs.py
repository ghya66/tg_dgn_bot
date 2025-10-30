"""
初始化文案配置数据
将 config.py 中的默认文案写入 content_configs 表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.bot_admin.config_manager import ContentConfig
from src.config import settings


def init_content_configs():
    """初始化文案配置"""
    # 使用 ConfigManager 的数据库连接
    from src.bot_admin.config_manager import ConfigManager
    config_mgr = ConfigManager()
    db = config_mgr._get_session()
    try:
        # 检查是否已存在数据
        existing = db.query(ContentConfig).count()
        if existing > 0:
            print(f"⚠️  content_configs 表已有 {existing} 条数据，跳过初始化")
            return
        
        print("📝 开始初始化文案配置...")
        
        # 1. 欢迎语
        welcome = ContentConfig(
            config_key="welcome_message",
            config_value=settings.welcome_message,
            description="Bot 欢迎语（/start 命令显示）"
        )
        db.add(welcome)
        print("  ✅ 已添加: welcome_message")
        
        # 2. 免费克隆说明
        clone = ContentConfig(
            config_key="free_clone_message",
            config_value=settings.free_clone_message,
            description="免费克隆功能说明文案"
        )
        db.add(clone)
        print("  ✅ 已添加: free_clone_message")
        
        # 3. 客服联系方式
        support = ContentConfig(
            config_key="support_contact",
            config_value=settings.support_contact,
            description="客服 Telegram 账号"
        )
        db.add(support)
        print("  ✅ 已添加: support_contact")
        
        # 4. 引流按钮配置
        promotion = ContentConfig(
            config_key="promotion_buttons",
            config_value=settings.promotion_buttons,
            description="欢迎页面引流按钮配置（JSON格式）"
        )
        db.add(promotion)
        print("  ✅ 已添加: promotion_buttons")
        
        # 5. 帮助文案
        help_text = ContentConfig(
            config_key="help_message",
            config_value=(
                "📖 <b>使用帮助</b>\n\n"
                "<b>核心功能：</b>\n"
                "💎 <b>Premium 直充</b> - 购买 Telegram 会员\n"
                "⚡ <b>能量兑换</b> - TRON 网络能量服务\n"
                "💰 <b>TRX 兑换</b> - USDT 快速兑换 TRX\n"
                "🔍 <b>地址查询</b> - 波场地址监控（免费）\n"
                "👤 <b>个人中心</b> - 余额充值和管理\n\n"
                "<b>支付方式：</b>\n"
                "• USDT (TRC20) - 推荐\n"
                "• 余额支付 - 快速便捷\n\n"
                "<b>常见问题：</b>\n"
                "❓ 如何充值？→ 点击【个人中心】→【充值 USDT】\n"
                "❓ 订单未到账？→ 联系客服查询\n"
                "❓ 如何查看历史？→ 【个人中心】→【充值记录】\n\n"
                "💡 遇到问题请联系客服 👨‍💼"
            ),
            description="Bot 帮助文案（/help 命令显示）"
        )
        db.add(help_text)
        print("  ✅ 已添加: help_message")
        
        # 提交事务
        db.commit()
        
        print("\n✅ 文案配置初始化完成！")
        print(f"   共添加 5 条配置记录")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ 初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_content_configs()
