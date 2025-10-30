"""
Streamlit 管理界面主应用

提供订单管理、统计仪表板、配置管理等功能。
"""

import os
from pathlib import Path

import streamlit as st

# 配置页面
st.set_page_config(
    page_title="TG DGN Bot 管理后台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/Jack123-UU/tg_dgn_bot",
        "Report a bug": "https://github.com/Jack123-UU/tg_dgn_bot/issues",
        "About": "TG DGN Bot 管理后台 v1.0.0",
    },
)

# ============================================================================
# 环境变量配置
# ============================================================================

def load_environment():
    """加载环境变量"""
    # 从 .env 文件加载（如果存在）
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    # 验证必需的环境变量
    required_vars = ["API_BASE_URL", "API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}")
        st.info("请在 .env 文件中配置：\n```\nAPI_BASE_URL=http://localhost:8000\nAPI_KEY=your-api-key\n```")
        st.stop()

load_environment()


# ============================================================================
# 侧边栏导航
# ============================================================================

def render_sidebar():
    """渲染侧边栏导航"""
    with st.sidebar:
        st.title("🤖 TG DGN Bot")
        st.caption("管理后台 v1.0.0")
        
        st.divider()
        
        # 导航菜单
        page = st.radio(
            "导航",
            [
                "📊 统计仪表板",
                "📦 订单管理",
                "⚙️ 系统设置",
                "🏥 健康监控",
            ],
            label_visibility="collapsed",
        )
        
        st.divider()
        
        # 环境信息
        st.caption(f"环境: {os.getenv('ENV', 'development')}")
        st.caption(f"API: {os.getenv('API_BASE_URL', 'N/A')}")
        
        return page


# ============================================================================
# 主应用路由
# ============================================================================

def main():
    """主应用入口"""
    # 渲染侧边栏并获取选中的页面
    page = render_sidebar()
    
    # 根据选择加载对应页面
    if page == "📊 统计仪表板":
        from backend.admin.pages import dashboard
        dashboard.render()
    
    elif page == "📦 订单管理":
        from backend.admin.pages import orders
        orders.render()
    
    elif page == "⚙️ 系统设置":
        from backend.admin.pages import settings
        settings.render()
    
    elif page == "🏥 健康监控":
        from backend.admin.pages import health
        health.render()


# ============================================================================
# 应用入口
# ============================================================================

if __name__ == "__main__":
    main()
