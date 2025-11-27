"""
中间件配置
"""
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.middlewares.link_track_middleware import LinkTrackMiddleware
from src.core.middlewares.log_middleware import LogMiddleware
from src.core.middlewares.prometheus_middleware import PrometheusMiddleware


def setup_middleware(app: FastAPI):
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name=settings.system.RANK_ZEN_TRACE_ID,
        validator=lambda x: True
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.system.ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[settings.system.RANK_ZEN_TRACE_ID, ]
    )

    app.add_middleware(LogMiddleware)  # type: ignore

    app.add_middleware(PrometheusMiddleware)  # type: ignore

    # 6. 链路追踪最后注册（最先执行请求处理）
    app.add_middleware(LinkTrackMiddleware)