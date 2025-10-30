# API 使用指南

## 目录
1. [快速开始](#快速开始)
2. [认证方式](#认证方式)
3. [API 端点](#api-端点)
4. [错误处理](#错误处理)
5. [示例代码](#示例代码)

## 快速开始

### 启动 API 服务

```bash
# 开发环境（热重载）
./scripts/start_api.sh

# 生产环境
ENV=production ./scripts/start_api.sh
```

### 访问 API 文档

开发环境下，访问 Swagger UI：
```
http://localhost:8000/docs
```

## 认证方式

### API Key 认证

所有管理员 API（`/api/admin/*`）需要提供 API Key：

```bash
# 通过 Header 传递
curl -H "X-API-Key: your-api-key-here" \
     http://localhost:8000/api/admin/orders
```

### 配置 API Key

在 `.env` 文件中配置：

```env
# 多个 API Key 用逗号分隔
API_KEYS=key1,key2,key3
```

### 公开端点

以下端点无需认证：
- `/` - 根路径
- `/health/*` - 健康检查
- `/metrics` - Prometheus 指标
- `/docs` - API 文档（仅开发环境）

### Webhook 端点保护

`/api/webhook/*` 端点受 IP 白名单保护：

```env
# 配置允许的 IP 地址
WEBHOOK_IP_WHITELIST=127.0.0.1,10.0.0.1
```

## API 端点

### 管理员 API

#### 1. 获取订单列表

```http
GET /api/admin/orders
```

**查询参数：**
- `page` (int): 页码，默认 1
- `page_size` (int): 每页数量，默认 20，最大 100
- `order_type` (str): 订单类型过滤（premium, deposit, trx_exchange）
- `status` (str): 状态过滤（PENDING, PAID, DELIVERED, EXPIRED, CANCELLED）

**响应示例：**
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "orders": [
    {
      "order_id": "PREM12345678",
      "order_type": "premium",
      "amount_usdt": 10.123,
      "status": "PAID",
      "recipient": "@username",
      "created_at": "2024-01-01T12:00:00",
      "paid_at": "2024-01-01T12:05:00",
      "delivered_at": null
    }
  ]
}
```

#### 2. 获取单个订单

```http
GET /api/admin/orders/{order_id}
```

**响应示例：**
```json
{
  "order_id": "PREM12345678",
  "order_type": "premium",
  "amount_usdt": 10.123,
  "status": "PAID",
  "recipient": "@username",
  "created_at": "2024-01-01T12:00:00",
  "paid_at": "2024-01-01T12:05:00",
  "delivered_at": null
}
```

#### 3. 更新订单

```http
PUT /api/admin/orders/{order_id}
```

**请求体：**
```json
{
  "status": "DELIVERED",
  "notes": "手动交付"
}
```

#### 4. 取消订单

```http
DELETE /api/admin/orders/{order_id}?reason=用户取消
```

**响应示例：**
```json
{
  "message": "Order cancelled successfully",
  "order_id": "PREM12345678"
}
```

#### 5. 获取统计摘要

```http
GET /api/admin/stats/summary
```

**响应示例：**
```json
{
  "total": 1000,
  "pending": 50,
  "paid": 100,
  "delivered": 800,
  "expired": 30,
  "cancelled": 20,
  "by_type": {
    "premium": 600,
    "deposit": 300,
    "trx_exchange": 100
  }
}
```

### Webhook API

#### TRC20 支付回调

```http
POST /api/webhook/trc20
```

**Headers：**
- `X-Signature`: HMAC-SHA256 签名

**签名计算：**
```python
import hmac
import hashlib

def generate_signature(order_id, amount_usdt, tx_hash, secret):
    message = f"{order_id}{amount_usdt}{tx_hash}"
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature
```

**请求体：**
```json
{
  "order_id": "PREM12345678",
  "tx_hash": "abc123...",
  "from_address": "TTest123...",
  "to_address": "TTest456...",
  "amount_usdt": 10.123,
  "block_number": 12345,
  "timestamp": 1234567890
}
```

**响应示例：**
```json
{
  "success": true,
  "order_id": "PREM12345678",
  "message": "Payment processed successfully"
}
```

### 健康检查 API

#### 1. 整体健康检查

```http
GET /health/
```

**响应示例：**
```json
{
  "status": "healthy",
  "checks": {
    "database": {
      "healthy": true,
      "message": "Database connection OK",
      "latency_ms": 2.34
    },
    "redis": {
      "healthy": true,
      "message": "Redis connection OK",
      "latency_ms": 1.23
    },
    "worker": {
      "healthy": true,
      "message": "2 worker(s) active, 0 job(s) in queue"
    }
  }
}
```

#### 2. 数据库健康检查

```http
GET /health/db
```

#### 3. Redis 健康检查

```http
GET /health/redis
```

#### 4. Worker 健康检查

```http
GET /health/worker
```

## 错误处理

### 错误响应格式

```json
{
  "detail": "Error message here"
}
```

### 常见错误码

- `400 Bad Request` - 请求参数错误
- `401 Unauthorized` - 缺少 API Key
- `403 Forbidden` - 无效的 API Key 或 IP 地址被拒绝
- `404 Not Found` - 资源不存在
- `429 Too Many Requests` - 请求超过限流
- `500 Internal Server Error` - 服务器内部错误

### 限流说明

- 管理员 API: 30 请求/分钟
- Webhook API: 100 请求/分钟
- 健康检查 API: 60 请求/分钟

## 示例代码

### Python 示例

```python
import httpx

# 配置
API_BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"

# 创建客户端
client = httpx.Client(
    base_url=API_BASE_URL,
    headers={"X-API-Key": API_KEY},
)

# 获取订单列表
response = client.get("/api/admin/orders", params={"page": 1, "page_size": 20})
orders = response.json()
print(f"Total orders: {orders['total']}")

# 获取单个订单
order_id = "PREM12345678"
response = client.get(f"/api/admin/orders/{order_id}")
order = response.json()
print(f"Order status: {order['status']}")

# 更新订单状态
response = client.put(
    f"/api/admin/orders/{order_id}",
    json={"status": "DELIVERED"},
)
print(f"Updated: {response.json()}")
```

### cURL 示例

```bash
# 获取订单列表
curl -H "X-API-Key: your-api-key" \
     "http://localhost:8000/api/admin/orders?page=1&page_size=20"

# 获取单个订单
curl -H "X-API-Key: your-api-key" \
     http://localhost:8000/api/admin/orders/PREM12345678

# 更新订单
curl -X PUT \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"status": "DELIVERED"}' \
     http://localhost:8000/api/admin/orders/PREM12345678

# 健康检查
curl http://localhost:8000/health/
```

### JavaScript 示例

```javascript
// 使用 fetch API
const API_BASE_URL = "http://localhost:8000";
const API_KEY = "your-api-key-here";

// 获取订单列表
async function getOrders(page = 1, pageSize = 20) {
  const response = await fetch(
    `${API_BASE_URL}/api/admin/orders?page=${page}&page_size=${pageSize}`,
    {
      headers: {
        "X-API-Key": API_KEY,
      },
    }
  );
  return await response.json();
}

// 获取单个订单
async function getOrder(orderId) {
  const response = await fetch(
    `${API_BASE_URL}/api/admin/orders/${orderId}`,
    {
      headers: {
        "X-API-Key": API_KEY,
      },
    }
  );
  return await response.json();
}

// 更新订单
async function updateOrder(orderId, status) {
  const response = await fetch(
    `${API_BASE_URL}/api/admin/orders/${orderId}`,
    {
      method: "PUT",
      headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status }),
    }
  );
  return await response.json();
}

// 使用示例
getOrders(1, 20).then(data => console.log(data));
```

## 监控和日志

### Prometheus 指标

访问 `/metrics` 端点获取 Prometheus 格式的指标：

```bash
curl http://localhost:8000/metrics
```

### 日志格式

开发环境使用人类可读格式：
```
2024-01-01 12:00:00 [info] request_received method=GET path=/api/admin/orders
```

生产环境使用 JSON 格式：
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "info",
  "event": "request_received",
  "method": "GET",
  "path": "/api/admin/orders"
}
```

## 部署建议

### 环境变量

```env
# 必需配置
ENV=production
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
API_KEYS=production-key-1,production-key-2

# 可选配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
LOG_LEVEL=INFO
LOG_JSON_FORMAT=true
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["./scripts/start_api.sh"]
```

### Kubernetes 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: your-image:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENV
          value: "production"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

## 常见问题

### Q: 如何调试认证问题？

A: 检查以下几点：
1. `.env` 文件中配置了 `API_KEYS`
2. 请求头中包含 `X-API-Key`
3. API Key 值正确（无多余空格）

### Q: Webhook 回调一直返回 403？

A: 检查 IP 白名单配置：
```env
WEBHOOK_IP_WHITELIST=你的回调服务器IP
```

### Q: 如何提高性能？

A: 调整以下参数：
1. 增加 worker 数量：`API_WORKERS=8`
2. 数据库连接池：`pool_size=20`
3. Redis 连接池：`max_connections=100`

### Q: 如何查看详细日志？

A: 设置日志级别：
```env
LOG_LEVEL=DEBUG
```
