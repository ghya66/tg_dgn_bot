"""
健康监控页面

展示服务状态、组件健康检查、实时刷新。
"""

from datetime import datetime

import streamlit as st

from backend.admin.utils import APIError, get_api_client


# ============================================================================
# 健康状态映射
# ============================================================================

HEALTH_STATUS_MAP = {
    "healthy": {"label": "健康", "color": "🟢", "style": "success"},
    "degraded": {"label": "降级", "color": "🟡", "style": "warning"},
    "unhealthy": {"label": "异常", "color": "🔴", "style": "error"},
}


# ============================================================================
# 整体健康状态
# ============================================================================

def render_overall_health(health_data: dict):
    """渲染整体健康状态"""
    status = health_data.get("status", "unknown")
    info = HEALTH_STATUS_MAP.get(status, {"label": "未知", "color": "⚪", "style": "info"})
    
    st.subheader(f"{info['color']} 服务状态: {info['label']}")
    
    # 使用 st.metric 显示
    col1, col2, col3 = st.columns(3)
    
    checks = health_data.get("checks", {})
    
    with col1:
        db_check = checks.get("database", {})
        db_status = "✅" if db_check.get("healthy") else "❌"
        db_latency = db_check.get("latency_ms", 0)
        
        st.metric(
            label=f"{db_status} 数据库",
            value=f"{db_latency:.2f} ms",
            delta=None,
        )
    
    with col2:
        redis_check = checks.get("redis", {})
        redis_status = "✅" if redis_check.get("healthy") else "❌"
        redis_latency = redis_check.get("latency_ms", 0)
        
        st.metric(
            label=f"{redis_status} Redis",
            value=f"{redis_latency:.2f} ms",
            delta=None,
        )
    
    with col3:
        worker_check = checks.get("worker", {})
        worker_status = "✅" if worker_check.get("healthy") else "❌"
        worker_msg = worker_check.get("message", "N/A")
        
        st.metric(
            label=f"{worker_status} Worker",
            value="正常" if worker_check.get("healthy") else "异常",
            delta=None,
        )
        
        st.caption(worker_msg)


# ============================================================================
# 组件详细检查
# ============================================================================

def render_component_checks():
    """渲染组件详细检查"""
    st.subheader("🔍 组件详细检查")
    
    try:
        client = get_api_client()
        
        # 创建 3 列
        col1, col2, col3 = st.columns(3)
        
        # 数据库检查
        with col1:
            st.markdown("### 💾 数据库")
            
            try:
                with st.spinner("检查中..."):
                    db_health = client.get_health_db()
                
                if db_health.get("healthy"):
                    st.success("✅ 连接正常")
                    st.caption(f"延迟: {db_health.get('latency_ms', 0):.2f} ms")
                else:
                    st.error("❌ 连接异常")
                    st.caption(db_health.get("message", "未知错误"))
            
            except APIError as e:
                st.error(f"❌ 检查失败: {e.message}")
        
        # Redis 检查
        with col2:
            st.markdown("### 🗄️ Redis")
            
            try:
                with st.spinner("检查中..."):
                    redis_health = client.get_health_redis()
                
                if redis_health.get("healthy"):
                    st.success("✅ 连接正常")
                    st.caption(f"延迟: {redis_health.get('latency_ms', 0):.2f} ms")
                else:
                    st.error("❌ 连接异常")
                    st.caption(redis_health.get("message", "未知错误"))
            
            except APIError as e:
                st.error(f"❌ 检查失败: {e.message}")
        
        # Worker 检查
        with col3:
            st.markdown("### ⚙️ Worker")
            
            try:
                with st.spinner("检查中..."):
                    worker_health = client.get_health_worker()
                
                if worker_health.get("healthy"):
                    st.success("✅ 运行正常")
                    st.caption(worker_health.get("message", "正常"))
                else:
                    st.warning("⚠️ 未发现 Worker")
                    st.caption(worker_health.get("message", "无活跃 Worker"))
            
            except APIError as e:
                st.error(f"❌ 检查失败: {e.message}")
    
    except Exception as e:
        st.error(f"❌ 未知错误: {str(e)}")


# ============================================================================
# 自动刷新控制
# ============================================================================

def render_auto_refresh_control():
    """渲染自动刷新控制"""
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        auto_refresh = st.checkbox("🔄 自动刷新", value=False)
    
    with col2:
        if auto_refresh:
            refresh_interval = st.selectbox(
                "刷新间隔",
                [5, 10, 30, 60],
                format_func=lambda x: f"{x} 秒",
                index=1,
            )
        else:
            refresh_interval = None
    
    with col3:
        if st.button("🔄 立即刷新", use_container_width=True):
            st.rerun()
    
    # 自动刷新逻辑
    if auto_refresh and refresh_interval:
        import time
        time.sleep(refresh_interval)
        st.rerun()


# ============================================================================
# 页面渲染入口
# ============================================================================

def render():
    """渲染健康监控页面"""
    st.title("🏥 健康监控")
    
    # 自动刷新控制
    render_auto_refresh_control()
    
    st.divider()
    
    # 获取整体健康状态
    try:
        client = get_api_client()
        
        with st.spinner("加载健康状态..."):
            health_data = client.get_health()
        
        # 渲染整体状态
        render_overall_health(health_data)
        
        st.divider()
        
        # 渲染组件详细检查
        render_component_checks()
        
        # 最后更新时间
        st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    except APIError as e:
        st.error(f"❌ 加载失败: {e.message}")
        if e.detail:
            st.code(e.detail)
    
    except Exception as e:
        st.error(f"❌ 未知错误: {str(e)}")
