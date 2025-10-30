"""
IP 白名单中间件 (IP Whitelist Middleware)

保护管理员 API 和 Webhook 端点，仅允许白名单 IP 访问。

配置项: 
- ADMIN_IP_WHITELIST: 管理员 API 白名单（逗号分隔）
- WEBHOOK_IP_WHITELIST: Webhook 白名单（逗号分隔）

支持格式:
- 单个 IP: 192.168.1.1
- CIDR: 192.168.1.0/24
"""

import ipaddress
from typing import List, Optional

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_403_FORBIDDEN

from backend.api.config import settings

logger = structlog.get_logger(__name__)


def _parse_ip_whitelist(config_value: Optional[str]) -> List[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """
    解析 IP 白名单配置
    
    参数:
        config_value: 逗号分隔的 IP 或 CIDR（如 "192.168.1.1,10.0.0.0/8"）
    
    返回:
        IP 网络对象列表
    """
    if not config_value:
        return []
    
    networks = []
    for item in config_value.split(","):
        item = item.strip()
        if not item:
            continue
        
        try:
            # 尝试解析为网络（支持 CIDR 和单 IP）
            if "/" not in item:
                item = f"{item}/32"  # 单 IP 转为 /32 网络
            network = ipaddress.ip_network(item, strict=False)
            networks.append(network)
        except ValueError as e:
            logger.warning("invalid_ip_whitelist_entry", entry=item, error=str(e))
    
    return networks


def _get_client_ip(request: Request) -> str:
    """
    获取客户端真实 IP
    
    优先级:
    1. X-Forwarded-For (代理/负载均衡器)
    2. X-Real-IP (Nginx)
    3. request.client.host
    """
    # 检查代理头
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个（客户端 IP）
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # 回退到直接连接 IP
    return request.client.host if request.client else "unknown"


def _is_ip_allowed(client_ip: str, whitelist: List[ipaddress.IPv4Network | ipaddress.IPv6Network]) -> bool:
    """
    检查 IP 是否在白名单中
    
    参数:
        client_ip: 客户端 IP 字符串
        whitelist: IP 网络对象列表
    
    返回:
        True 如果 IP 在白名单中
    """
    if not whitelist:
        return True  # 空白名单 = 允许所有
    
    try:
        ip_obj = ipaddress.ip_address(client_ip)
        for network in whitelist:
            if ip_obj in network:
                return True
        return False
    except ValueError:
        logger.warning("invalid_client_ip", client_ip=client_ip)
        return False


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    IP 白名单中间件
    
    保护路径:
    - /api/admin/*: 使用 ADMIN_IP_WHITELIST
    - /api/webhook/*: 使用 WEBHOOK_IP_WHITELIST
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # 解析白名单配置
        self.admin_whitelist = _parse_ip_whitelist(
            getattr(settings, "ADMIN_IP_WHITELIST", None)
        )
        self.webhook_whitelist = _parse_ip_whitelist(
            getattr(settings, "WEBHOOK_IP_WHITELIST", None)
        )
        
        logger.info(
            "ip_whitelist_middleware_initialized",
            admin_whitelist_count=len(self.admin_whitelist),
            webhook_whitelist_count=len(self.webhook_whitelist),
        )
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = _get_client_ip(request)
        
        # 检查管理员 API
        if path.startswith("/api/admin/"):
            if not _is_ip_allowed(client_ip, self.admin_whitelist):
                logger.warning(
                    "admin_api_ip_rejected",
                    client_ip=client_ip,
                    path=path,
                )
                return Response(
                    content="Access denied: IP not in admin whitelist",
                    status_code=HTTP_403_FORBIDDEN,
                )
        
        # 检查 Webhook
        elif path.startswith("/api/webhook/"):
            if not _is_ip_allowed(client_ip, self.webhook_whitelist):
                logger.warning(
                    "webhook_ip_rejected",
                    client_ip=client_ip,
                    path=path,
                )
                return Response(
                    content="Access denied: IP not in webhook whitelist",
                    status_code=HTTP_403_FORBIDDEN,
                )
        
        # 通过验证，继续处理
        response = await call_next(request)
        return response
