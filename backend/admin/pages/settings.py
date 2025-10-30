"""
系统设置页面

管理 API Key、环境变量等配置。
"""

import os

import streamlit as st


# ============================================================================
# API 配置
# ============================================================================

def render_api_settings():
    """渲染 API 配置"""
    st.subheader("🔑 API 配置")
    
    # 当前配置
    current_base_url = os.getenv("API_BASE_URL", "")
    current_api_key = os.getenv("API_KEY", "")
    
    # API Base URL
    api_base_url = st.text_input(
        "API 基础 URL",
        value=current_base_url,
        placeholder="http://localhost:8000",
        help="FastAPI 后端服务地址",
    )
    
    # API Key（脱敏显示）
    masked_key = current_api_key[:8] + "*" * (len(current_api_key) - 8) if current_api_key else ""
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        show_key = st.checkbox("显示完整 API Key", value=False)
        
        if show_key:
            api_key = st.text_input(
                "API Key",
                value=current_api_key,
                type="default",
                help="用于认证的 API Key",
            )
        else:
            st.text_input(
                "API Key",
                value=masked_key,
                type="password",
                disabled=True,
                help="用于认证的 API Key（已脱敏）",
            )
    
    with col2:
        st.write("")  # 占位
        st.write("")  # 占位
        if st.button("📋 复制"):
            st.code(current_api_key)
    
    st.divider()
    
    # 配置说明
    st.info("""
    ℹ️ **配置说明**
    
    请在 `.env` 文件中配置以下环境变量：
    
    ```env
    API_BASE_URL=http://localhost:8000
    API_KEY=your-api-key-here
    ```
    
    修改后需要重启 Streamlit 应用才能生效。
    """)


# ============================================================================
# 环境信息
# ============================================================================

def render_environment_info():
    """渲染环境信息"""
    st.subheader("🌍 环境信息")
    
    env_vars = {
        "环境": os.getenv("ENV", "development"),
        "API Base URL": os.getenv("API_BASE_URL", "N/A"),
        "API Key": os.getenv("API_KEY", "N/A")[:8] + "..." if os.getenv("API_KEY") else "N/A",
        "Log Level": os.getenv("LOG_LEVEL", "INFO"),
        "Log JSON Format": os.getenv("LOG_JSON_FORMAT", "false"),
    }
    
    # 显示为表格
    import pandas as pd
    
    df = pd.DataFrame([
        {"配置项": k, "值": v}
        for k, v in env_vars.items()
    ])
    
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================================
# 关于信息
# ============================================================================

def render_about():
    """渲染关于信息"""
    st.subheader("ℹ️ 关于")
    
    st.markdown("""
    ### TG DGN Bot 管理后台
    
    **版本**: v1.0.0  
    **环境**: Streamlit + FastAPI
    
    **功能模块**:
    - 📊 统计仪表板：订单统计、趋势分析
    - 📦 订单管理：订单列表、详情查看、状态更新
    - ⚙️ 系统设置：API 配置、环境变量
    - 🏥 健康监控：服务状态、组件健康检查
    
    **技术栈**:
    - 前端：Streamlit, Plotly
    - 后端：FastAPI, SQLAlchemy
    - 数据库：SQLite / PostgreSQL
    - 缓存：Redis
    - 队列：arq
    
    **开源地址**: [GitHub](https://github.com/Jack123-UU/tg_dgn_bot)
    """)


# ============================================================================
# 页面渲染入口
# ============================================================================

def render():
    """渲染系统设置页面"""
    st.title("⚙️ 系统设置")
    
    # Tab 导航
    tab1, tab2, tab3 = st.tabs(["🔑 API 配置", "🌍 环境信息", "ℹ️ 关于"])
    
    with tab1:
        render_api_settings()
    
    with tab2:
        render_environment_info()
    
    with tab3:
        render_about()
