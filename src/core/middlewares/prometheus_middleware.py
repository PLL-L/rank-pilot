import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response



# 导入 Prometheus 指标类型：Counter（计数器），Histogram（直方图/分桶）
from prometheus_client import Counter, Histogram

from src.core import logger

REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['status'])  # 总请求计数，带 status 标签区分成功/失败
REQUEST_DURATION = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint', 'status_code'],  # 3个标签

)  # 请求耗时直方图（秒）


class PrometheusMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        中间件调度方法

        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: FastAPI响应对象
        """
        try:
            # 记录请求开始时间
            start_time = time.perf_counter()

            # 执行请求获取响应
            response = await call_next(request)

            # 计算处理时间
            process_time = time.perf_counter() - start_time

            # 将耗时记录到直方图中
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code
            ).observe(process_time)

            # 成功计数加 1
            REQUEST_COUNT.labels(status="success").inc()

            return response

        except Exception as e:
            REQUEST_COUNT.labels(status="failure").inc()  # 失败计数加

            # logger.error(f"普罗米修斯 中间件处理失败: {str(e)}")
            # 确保异常被正确处理
            raise