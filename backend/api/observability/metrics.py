"""
Prometheus 指标
定义业务指标和性能指标
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional


# ===== 应用信息 =====
app_info = Info(
    "app",
    "Application information"
)

app_info.info({
    "name": "tg_dgn_bot_backend",
    "version": "1.0.0",
    "environment": "production"
})


# ===== 订单指标 =====

# 订单创建总数（按类型分类）
order_created_total = Counter(
    "order_created_total",
    "Total number of orders created",
    labelnames=["order_type"]  # premium, deposit, trx_exchange
)

# 订单支付总数（按类型分类）
order_paid_total = Counter(
    "order_paid_total",
    "Total number of orders paid",
    labelnames=["order_type"]
)

# 订单交付总数（按类型分类）
order_delivered_total = Counter(
    "order_delivered_total",
    "Total number of orders delivered",
    labelnames=["order_type"]
)

# 订单过期总数
order_expired_total = Counter(
    "order_expired_total",
    "Total number of orders expired",
    labelnames=["order_type"]
)

# 订单取消总数
order_cancelled_total = Counter(
    "order_cancelled_total",
    "Total number of orders cancelled",
    labelnames=["order_type", "reason"]
)

# 订单金额（直方图）
order_amount_histogram = Histogram(
    "order_amount_usdt",
    "Order amount distribution in USDT",
    labelnames=["order_type"],
    buckets=(5, 10, 20, 30, 50, 100, 200, 500, 1000)
)

# 当前待支付订单数（实时）
pending_orders_gauge = Gauge(
    "pending_orders",
    "Current number of pending orders",
    labelnames=["order_type"]
)


# ===== 用户指标 =====

# 用户注册总数
user_registered_total = Counter(
    "user_registered_total",
    "Total number of registered users"
)

# 用户余额总和（实时）
user_balance_total_gauge = Gauge(
    "user_balance_total_usdt",
    "Total user balance in USDT"
)

# 余额充值总数
balance_deposit_total = Counter(
    "balance_deposit_total",
    "Total number of balance deposits"
)

# 余额充值金额
balance_deposit_amount = Counter(
    "balance_deposit_amount_usdt",
    "Total balance deposit amount in USDT"
)

# 余额扣费总数
balance_debit_total = Counter(
    "balance_debit_total",
    "Total number of balance debits"
)

# 余额扣费金额
balance_debit_amount = Counter(
    "balance_debit_amount_usdt",
    "Total balance debit amount in USDT"
)


# ===== 任务指标 =====

# 任务执行总数（按任务名和状态分类）
task_executed_total = Counter(
    "task_executed_total",
    "Total number of tasks executed",
    labelnames=["task_name", "status"]  # success, failed, retry
)

# 任务执行时长（直方图）
task_duration_seconds = Histogram(
    "task_duration_seconds",
    "Task execution duration in seconds",
    labelnames=["task_name"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300)
)

# 任务队列长度（实时）
task_queue_length_gauge = Gauge(
    "task_queue_length",
    "Current length of task queue"
)

# 任务重试次数
task_retry_total = Counter(
    "task_retry_total",
    "Total number of task retries",
    labelnames=["task_name", "attempt"]
)


# ===== HTTP 指标 =====

# HTTP 请求总数（按方法、路径、状态码分类）
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    labelnames=["method", "endpoint", "status_code"]
)

# HTTP 请求时长（直方图）
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
)

# HTTP 请求大小（字节）
http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    labelnames=["method", "endpoint"],
    buckets=(100, 1000, 10000, 100000, 1000000)
)

# HTTP 响应大小（字节）
http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    labelnames=["method", "endpoint"],
    buckets=(100, 1000, 10000, 100000, 1000000)
)


# ===== Telegram API 指标 =====

# Telegram API 调用总数（按方法和状态分类）
telegram_api_calls_total = Counter(
    "telegram_api_calls_total",
    "Total number of Telegram API calls",
    labelnames=["method", "status"]  # success, failed
)

# Telegram API 调用时长
telegram_api_duration_seconds = Histogram(
    "telegram_api_duration_seconds",
    "Telegram API call duration in seconds",
    labelnames=["method"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30)
)


# ===== 数据库指标 =====

# 数据库连接池（实时）
db_pool_connections_gauge = Gauge(
    "db_pool_connections",
    "Current number of database connections",
    labelnames=["state"]  # idle, active
)

# 数据库查询总数（按表分类）
db_queries_total = Counter(
    "db_queries_total",
    "Total number of database queries",
    labelnames=["table", "operation"]  # select, insert, update, delete
)

# 数据库查询时长
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    labelnames=["table", "operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1)
)


# ===== 辅助函数 =====

def record_order_created(order_type: str, amount: float) -> None:
    """记录订单创建"""
    order_created_total.labels(order_type=order_type).inc()
    order_amount_histogram.labels(order_type=order_type).observe(amount)


def record_order_paid(order_type: str) -> None:
    """记录订单支付"""
    order_paid_total.labels(order_type=order_type).inc()


def record_order_delivered(order_type: str) -> None:
    """记录订单交付"""
    order_delivered_total.labels(order_type=order_type).inc()


def record_task_execution(
    task_name: str,
    duration: float,
    status: str = "success"
) -> None:
    """
    记录任务执行
    
    Args:
        task_name: 任务名称
        duration: 执行时长（秒）
        status: 执行状态（success/failed/retry）
    """
    task_executed_total.labels(task_name=task_name, status=status).inc()
    task_duration_seconds.labels(task_name=task_name).observe(duration)


def record_http_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
    request_size: Optional[int] = None,
    response_size: Optional[int] = None
) -> None:
    """
    记录 HTTP 请求
    
    Args:
        method: HTTP 方法（GET/POST/PUT/DELETE）
        endpoint: 端点路径
        status_code: HTTP 状态码
        duration: 请求时长（秒）
        request_size: 请求大小（字节）
        response_size: 响应大小（字节）
    """
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)
    
    if request_size is not None:
        http_request_size_bytes.labels(
            method=method,
            endpoint=endpoint
        ).observe(request_size)
    
    if response_size is not None:
        http_response_size_bytes.labels(
            method=method,
            endpoint=endpoint
        ).observe(response_size)
