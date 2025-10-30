"""
API 客户端

封装与 FastAPI 后端的通信。
"""

import os
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# API 客户端类
# ============================================================================

class APIClient:
    """FastAPI 后端客户端"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        初始化 API 客户端
        
        Args:
            base_url: API 基础 URL（默认从环境变量读取）
            api_key: API Key（默认从环境变量读取）
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("API_KEY", "")
        self.timeout = timeout
        
        # 创建 httpx 客户端
        self.client = httpx.Client(
            base_url=self.base_url,
            headers=self._get_headers(),
            timeout=timeout,
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
    
    def _handle_response(self, response: httpx.Response) -> Any:
        """处理响应"""
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "api_request_failed",
                status_code=e.response.status_code,
                error=e.response.text,
            )
            raise APIError(
                message=f"API 请求失败: {e.response.status_code}",
                status_code=e.response.status_code,
                detail=e.response.text,
            )
        except Exception as e:
            logger.error("api_request_error", error=str(e))
            raise APIError(message=f"API 请求错误: {str(e)}")
    
    # ========================================================================
    # 订单管理 API
    # ========================================================================
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def get_orders(
        self,
        page: int = 1,
        page_size: int = 20,
        order_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取订单列表
        
        Args:
            page: 页码
            page_size: 每页数量
            order_type: 订单类型过滤
            status: 状态过滤
        
        Returns:
            订单列表数据
        """
        params = {"page": page, "page_size": page_size}
        if order_type:
            params["order_type"] = order_type
        if status:
            params["status"] = status
        
        response = self.client.get("/api/admin/orders", params=params)
        return self._handle_response(response)
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        获取单个订单详情
        
        Args:
            order_id: 订单 ID
        
        Returns:
            订单详情
        """
        response = self.client.get(f"/api/admin/orders/{order_id}")
        return self._handle_response(response)
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def update_order(
        self,
        order_id: str,
        status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新订单
        
        Args:
            order_id: 订单 ID
            status: 新状态
            notes: 备注
        
        Returns:
            更新后的订单
        """
        data = {}
        if status:
            data["status"] = status
        if notes:
            data["notes"] = notes
        
        response = self.client.put(f"/api/admin/orders/{order_id}", json=data)
        return self._handle_response(response)
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def cancel_order(self, order_id: str, reason: str) -> Dict[str, Any]:
        """
        取消订单
        
        Args:
            order_id: 订单 ID
            reason: 取消原因
        
        Returns:
            操作结果
        """
        response = self.client.delete(
            f"/api/admin/orders/{order_id}",
            params={"reason": reason},
        )
        return self._handle_response(response)
    
    # ========================================================================
    # 统计 API
    # ========================================================================
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def get_stats_summary(self) -> Dict[str, Any]:
        """
        获取统计摘要
        
        Returns:
            统计数据
        """
        response = self.client.get("/api/admin/stats/summary")
        return self._handle_response(response)
    
    # ========================================================================
    # 健康检查 API
    # ========================================================================
    
    def get_health(self) -> Dict[str, Any]:
        """
        获取整体健康状态
        
        Returns:
            健康检查结果
        """
        response = self.client.get("/health/")
        return self._handle_response(response)
    
    def get_health_db(self) -> Dict[str, Any]:
        """获取数据库健康状态"""
        response = self.client.get("/health/db")
        return self._handle_response(response)
    
    def get_health_redis(self) -> Dict[str, Any]:
        """获取 Redis 健康状态"""
        response = self.client.get("/health/redis")
        return self._handle_response(response)
    
    def get_health_worker(self) -> Dict[str, Any]:
        """获取 Worker 健康状态"""
        response = self.client.get("/health/worker")
        return self._handle_response(response)
    
    # ========================================================================
    # 关闭连接
    # ========================================================================
    
    def close(self):
        """关闭客户端连接"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# 异常类
# ============================================================================

class APIError(Exception):
    """API 错误"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        detail: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)
    
    def __str__(self):
        if self.status_code:
            return f"{self.message} (Status: {self.status_code})"
        return self.message


# ============================================================================
# 全局客户端实例（单例）
# ============================================================================

_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """
    获取全局 API 客户端实例（单例）
    
    Returns:
        APIClient 实例
    """
    global _client
    
    if _client is None:
        _client = APIClient()
    
    return _client
