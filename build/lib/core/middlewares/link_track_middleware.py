# @Version        : 1.0
# @Update Time    : 2025/3/24 22:36
# @File           : link_track_middleware.py
# @IDE            : PyCharm
# @Desc           : 链路追踪中间件
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.utils.track_utils import TrackContextUtils


class LinkTrackMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_id = TrackContextUtils.set_request_id()  # 生成ID
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id  # 响应头透传
        return response
