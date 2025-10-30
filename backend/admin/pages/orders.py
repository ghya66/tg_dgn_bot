"""
订单管理页面

提供订单列表、详情查看、状态更新、取消等功能。
"""

from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from backend.admin.utils import APIError, get_api_client


# ============================================================================
# 订单状态映射
# ============================================================================

ORDER_STATUS_MAP = {
    "PENDING": {"label": "待支付", "color": "🟡"},
    "PAID": {"label": "已支付", "color": "🟢"},
    "DELIVERED": {"label": "已交付", "color": "✅"},
    "EXPIRED": {"label": "已过期", "color": "⚫"},
    "CANCELLED": {"label": "已取消", "color": "🔴"},
}

ORDER_TYPE_MAP = {
    "premium": "Premium 会员",
    "deposit": "余额充值",
    "trx_exchange": "TRX 兑换",
}


# ============================================================================
# 辅助函数
# ============================================================================

def format_datetime(dt_str: Optional[str]) -> str:
    """格式化日期时间"""
    if not dt_str:
        return "-"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str


def format_status(status: str) -> str:
    """格式化订单状态"""
    info = ORDER_STATUS_MAP.get(status, {"label": status, "color": "⚪"})
    return f"{info['color']} {info['label']}"


def format_order_type(order_type: str) -> str:
    """格式化订单类型"""
    return ORDER_TYPE_MAP.get(order_type, order_type)


# ============================================================================
# 订单列表视图
# ============================================================================

def render_orders_list():
    """渲染订单列表"""
    st.subheader("📦 订单列表")
    
    # 过滤器
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        order_type_filter = st.selectbox(
            "订单类型",
            ["全部", "premium", "deposit", "trx_exchange"],
            format_func=lambda x: "全部类型" if x == "全部" else ORDER_TYPE_MAP.get(x, x),
        )
    
    with col2:
        status_filter = st.selectbox(
            "订单状态",
            ["全部", "PENDING", "PAID", "DELIVERED", "EXPIRED", "CANCELLED"],
            format_func=lambda x: "全部状态" if x == "全部" else ORDER_STATUS_MAP[x]["label"],
        )
    
    with col3:
        page_size = st.selectbox("每页数量", [10, 20, 50, 100], index=1)
    
    with col4:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    
    # 获取订单列表
    try:
        client = get_api_client()
        
        # 构建查询参数
        params = {
            "page": st.session_state.get("orders_page", 1),
            "page_size": page_size,
        }
        
        if order_type_filter != "全部":
            params["order_type"] = order_type_filter
        
        if status_filter != "全部":
            params["status"] = status_filter
        
        # 请求数据
        with st.spinner("加载订单数据..."):
            data = client.get_orders(**params)
        
        # 显示统计信息
        st.caption(f"共 {data['total']} 条订单")
        
        # 订单列表
        if data["orders"]:
            # 转换为 DataFrame
            df = pd.DataFrame([
                {
                    "订单 ID": order["order_id"],
                    "类型": format_order_type(order["order_type"]),
                    "金额 (USDT)": f"${order['amount_usdt']:.3f}",
                    "状态": format_status(order["status"]),
                    "收件人": order.get("recipient", "-"),
                    "创建时间": format_datetime(order["created_at"]),
                    "支付时间": format_datetime(order.get("paid_at")),
                }
                for order in data["orders"]
            ])
            
            # 显示表格（使用 st.dataframe 支持排序）
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "订单 ID": st.column_config.TextColumn("订单 ID", width="medium"),
                    "类型": st.column_config.TextColumn("类型", width="small"),
                    "金额 (USDT)": st.column_config.TextColumn("金额", width="small"),
                    "状态": st.column_config.TextColumn("状态", width="small"),
                    "收件人": st.column_config.TextColumn("收件人", width="medium"),
                    "创建时间": st.column_config.TextColumn("创建时间", width="medium"),
                    "支付时间": st.column_config.TextColumn("支付时间", width="medium"),
                },
            )
            
            # 分页控制
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if st.button("⬅️ 上一页", disabled=(data["page"] <= 1)):
                    st.session_state.orders_page = data["page"] - 1
                    st.rerun()
            
            with col2:
                st.caption(f"第 {data['page']} 页 / 共 {(data['total'] + page_size - 1) // page_size} 页")
            
            with col3:
                max_page = (data["total"] + page_size - 1) // page_size
                if st.button("➡️ 下一页", disabled=(data["page"] >= max_page)):
                    st.session_state.orders_page = data["page"] + 1
                    st.rerun()
            
            # 订单详情查看
            st.divider()
            st.subheader("🔍 订单详情")
            
            order_id_input = st.text_input("输入订单 ID 查看详情")
            if order_id_input and st.button("查看详情"):
                render_order_detail(order_id_input)
        
        else:
            st.info("📭 暂无订单数据")
    
    except APIError as e:
        st.error(f"❌ 加载失败: {e.message}")
        if e.detail:
            st.code(e.detail)
    
    except Exception as e:
        st.error(f"❌ 未知错误: {str(e)}")


# ============================================================================
# 订单详情视图
# ============================================================================

def render_order_detail(order_id: str):
    """渲染订单详情"""
    try:
        client = get_api_client()
        
        with st.spinner("加载订单详情..."):
            order = client.get_order(order_id)
        
        # 显示订单信息
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("订单 ID", order["order_id"])
            st.metric("订单类型", format_order_type(order["order_type"]))
            st.metric("金额 (USDT)", f"${order['amount_usdt']:.3f}")
        
        with col2:
            st.metric("状态", format_status(order["status"]))
            st.metric("创建时间", format_datetime(order["created_at"]))
            st.metric("支付时间", format_datetime(order.get("paid_at")))
        
        # 收件人信息
        if order.get("recipient"):
            st.info(f"收件人: {order['recipient']}")
        
        # 交付时间
        if order.get("delivered_at"):
            st.success(f"✅ 已交付: {format_datetime(order['delivered_at'])}")
        
        # 操作按钮
        st.divider()
        st.subheader("🛠️ 订单操作")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 更新状态
            new_status = st.selectbox(
                "更新状态",
                ["PENDING", "PAID", "DELIVERED", "EXPIRED", "CANCELLED"],
                format_func=lambda x: ORDER_STATUS_MAP[x]["label"],
                index=["PENDING", "PAID", "DELIVERED", "EXPIRED", "CANCELLED"].index(order["status"]),
            )
            
            if st.button("✅ 更新状态", type="primary"):
                try:
                    with st.spinner("更新中..."):
                        client.update_order(order_id, status=new_status)
                    st.success("✅ 状态更新成功！")
                    st.rerun()
                except APIError as e:
                    st.error(f"❌ 更新失败: {e.message}")
        
        with col2:
            # 取消订单
            if order["status"] in ["PENDING", "PAID"]:
                cancel_reason = st.text_input("取消原因")
                
                if st.button("🔴 取消订单", type="secondary"):
                    if not cancel_reason:
                        st.warning("请输入取消原因")
                    else:
                        try:
                            with st.spinner("取消中..."):
                                client.cancel_order(order_id, reason=cancel_reason)
                            st.success("✅ 订单已取消！")
                            st.rerun()
                        except APIError as e:
                            st.error(f"❌ 取消失败: {e.message}")
    
    except APIError as e:
        st.error(f"❌ 加载失败: {e.message}")
        if e.status_code == 404:
            st.warning("订单不存在，请检查订单 ID")
    
    except Exception as e:
        st.error(f"❌ 未知错误: {str(e)}")


# ============================================================================
# 页面渲染入口
# ============================================================================

def render():
    """渲染订单管理页面"""
    st.title("📦 订单管理")
    
    # 初始化 session state
    if "orders_page" not in st.session_state:
        st.session_state.orders_page = 1
    
    # 渲染订单列表
    render_orders_list()
