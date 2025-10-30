"""
统计仪表板页面

展示订单统计、趋势图表、实时数据等。
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend.admin.utils import APIError, get_api_client


# ============================================================================
# 统计卡片
# ============================================================================

def render_stats_cards(stats: dict):
    """渲染统计卡片"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 总订单数",
            value=stats.get("total", 0),
            delta=None,
        )
    
    with col2:
        st.metric(
            label="🟡 待支付",
            value=stats.get("pending", 0),
            delta=None,
        )
    
    with col3:
        st.metric(
            label="🟢 已支付",
            value=stats.get("paid", 0),
            delta=None,
        )
    
    with col4:
        st.metric(
            label="✅ 已交付",
            value=stats.get("delivered", 0),
            delta=None,
        )
    
    # 第二行
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="⚫ 已过期",
            value=stats.get("expired", 0),
            delta=None,
        )
    
    with col2:
        st.metric(
            label="🔴 已取消",
            value=stats.get("cancelled", 0),
            delta=None,
        )
    
    with col3:
        # 计算成功率
        total = stats.get("total", 0)
        delivered = stats.get("delivered", 0)
        success_rate = (delivered / total * 100) if total > 0 else 0
        
        st.metric(
            label="📈 成功率",
            value=f"{success_rate:.1f}%",
            delta=None,
        )
    
    with col4:
        # 计算转化率（已支付/总数）
        paid = stats.get("paid", 0) + delivered
        conversion_rate = (paid / total * 100) if total > 0 else 0
        
        st.metric(
            label="💰 支付率",
            value=f"{conversion_rate:.1f}%",
            delta=None,
        )


# ============================================================================
# 订单状态分布饼图
# ============================================================================

def render_status_pie_chart(stats: dict):
    """渲染订单状态分布饼图"""
    st.subheader("📊 订单状态分布")
    
    # 准备数据
    labels = ["待支付", "已支付", "已交付", "已过期", "已取消"]
    values = [
        stats.get("pending", 0),
        stats.get("paid", 0),
        stats.get("delivered", 0),
        stats.get("expired", 0),
        stats.get("cancelled", 0),
    ]
    
    # 过滤掉值为 0 的项
    filtered_data = [(l, v) for l, v in zip(labels, values) if v > 0]
    
    if filtered_data:
        labels, values = zip(*filtered_data)
        
        # 创建饼图
        fig = go.Figure(data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.4,  # 甜甜圈样式
                marker=dict(
                    colors=["#FDB462", "#80B1D3", "#8DD3C7", "#BEBADA", "#FB8072"],
                ),
            )
        ])
        
        fig.update_layout(
            showlegend=True,
            height=400,
            margin=dict(t=50, b=50, l=50, r=50),
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 暂无数据")


# ============================================================================
# 订单类型分布柱状图
# ============================================================================

def render_type_bar_chart(stats: dict):
    """渲染订单类型分布柱状图"""
    st.subheader("📦 订单类型分布")
    
    by_type = stats.get("by_type", {})
    
    # 准备数据
    type_labels = {
        "premium": "Premium 会员",
        "deposit": "余额充值",
        "trx_exchange": "TRX 兑换",
    }
    
    labels = [type_labels.get(k, k) for k in by_type.keys()]
    values = list(by_type.values())
    
    if values:
        # 创建柱状图
        fig = go.Figure(data=[
            go.Bar(
                x=labels,
                y=values,
                marker=dict(
                    color=["#FF6B6B", "#4ECDC4", "#45B7D1"],
                ),
                text=values,
                textposition="auto",
            )
        ])
        
        fig.update_layout(
            xaxis_title="订单类型",
            yaxis_title="订单数量",
            height=400,
            margin=dict(t=50, b=50, l=50, r=50),
            showlegend=False,
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 暂无数据")


# ============================================================================
# 订单状态流转漏斗图
# ============================================================================

def render_funnel_chart(stats: dict):
    """渲染订单流转漏斗图"""
    st.subheader("🔻 订单流转漏斗")
    
    # 准备数据（从创建到交付）
    stages = ["创建", "支付", "交付"]
    values = [
        stats.get("total", 0),
        stats.get("paid", 0) + stats.get("delivered", 0),
        stats.get("delivered", 0),
    ]
    
    # 创建漏斗图
    fig = go.Figure(data=[
        go.Funnel(
            y=stages,
            x=values,
            textposition="inside",
            textinfo="value+percent initial",
            marker=dict(
                color=["#FDB462", "#80B1D3", "#8DD3C7"],
            ),
        )
    ])
    
    fig.update_layout(
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
    )
    
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# 页面渲染入口
# ============================================================================

def render():
    """渲染统计仪表板页面"""
    st.title("📊 统计仪表板")
    
    # 刷新按钮
    col1, col2 = st.columns([6, 1])
    
    with col2:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    
    # 获取统计数据
    try:
        client = get_api_client()
        
        with st.spinner("加载统计数据..."):
            stats = client.get_stats_summary()
        
        # 渲染统计卡片
        render_stats_cards(stats)
        
        st.divider()
        
        # 渲染图表
        col1, col2 = st.columns(2)
        
        with col1:
            render_status_pie_chart(stats)
        
        with col2:
            render_type_bar_chart(stats)
        
        st.divider()
        
        # 渲染漏斗图
        render_funnel_chart(stats)
        
        # 最后更新时间
        from datetime import datetime
        st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    except APIError as e:
        st.error(f"❌ 加载失败: {e.message}")
        if e.detail:
            st.code(e.detail)
    
    except Exception as e:
        st.error(f"❌ 未知错误: {str(e)}")
