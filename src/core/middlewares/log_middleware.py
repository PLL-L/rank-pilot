# @Version        : 1.0
# @Update Time    : 2024/12/9 22:25
# @File           : log_middleware.py
# @IDE            : PyCharm
# @Desc           : 日志中间件，用于记录请求和响应的详细信息

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.core.log import logger


class LogMiddleware(BaseHTTPMiddleware):
    """
    日志中间件

    用于记录HTTP请求和响应的详细信息，包括：
    - 请求方法和路径
    - 请求参数
    - 请求体
    - 响应状态
    - 响应时间
    - 响应大小
    """

    async def _set_body(self, request: Request) -> None:
        """
        设置请求体，用于重复读取请求体内容

        Args:
            request: FastAPI请求对象
        """
        receive_ = await request._receive()

        async def receive():
            return receive_

        request._receive = receive

    async def _log_request(self, request: Request) -> None:
        """
        记录请求信息

        Args:
            request: FastAPI请求对象
        """
        # 记录基本请求信息
        logger.info(
            f"----> {request.method} {request.url.path} "
            f"{request.client.host if request.client else 'unknown'}"
        )

        # 记录查询参数
        if request.query_params:
            logger.info(f"----> Query Params: {request.query_params}")

        # 记录请求体
        content_type = request.headers.get("Content-Type", "")
        if "application/json" in content_type:
            await self._set_body(request)
            try:
                body = await request.json()
                logger.info(f"----> Body: {body}")
            except Exception as e:
                logger.warning(f"解析JSON请求体失败: {str(e)}")

    async def _log_response(
        self, request: Request, response: Response, process_time: float
    ) -> None:
        """
        记录响应信息

        Args:
            request: FastAPI请求对象
            response: FastAPI响应对象
            process_time: 处理时间
        """
        http_version = f"http/{request.scope['http_version']}"
        content_length = response.headers.get("content-length", "0")

        logger.info(
            f"<---- {request.url.path} {request.method} "
            f"{response.status_code} {http_version} {content_length} "
            f"(耗时: {process_time:.2f}s)\n"
        )

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

            # 记录请求信息
            await self._log_request(request)

            # 执行请求获取响应
            response = await call_next(request)

            # 计算处理时间
            process_time = time.perf_counter() - start_time

            # 添加响应时间头
            response.headers["X-Response-Time"] = f"{process_time:.2f}s"

            # 记录响应信息
            await self._log_response(request, response, process_time)

            return response

        except Exception as e:
            # logger.error(f"日志中间件处理失败: {str(e)}")
            # 确保异常被正确处理
            raise
