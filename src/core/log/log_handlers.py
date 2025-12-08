#!/usr/bin/python
# -*- coding: utf-8 -*-# @version        : 1.0
# @Create Time    : 2025/8/23
# @File           : log_handlers.py
# @IDE            : PyCharm
# @Desc           : 日志处理器实现

# 日志处理器实现：接管标准 logging 到 loguru
import inspect
import logging
from typing import Iterable, Optional

from loguru import logger as loguru_logger

from src.utils.track_utils import TrackContextUtils


class InterceptHandler(logging.Handler):
    """将标准 logging 记录转发到 loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            try:
                level = loguru_logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # 跳过 logging 内部帧，定位到真实调用点
            frame, depth = inspect.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            trace_id = TrackContextUtils.get_request_id() or "-"

            loguru_logger.bind(trace_id=trace_id).opt(
                depth=depth,
                exception=record.exc_info,  # 保留完整 traceback
            ).log(level, record.getMessage())
        except Exception:
            loguru_logger.exception("Error in InterceptHandler.emit()")

    def filter(self, record):

        # 检查日志是否来自 SQLAlchemy Engine 并且是 SQL 语句本身
        if record.name == 'sqlalchemy.engine.Engine':
            # SQLAlchemy 打印 SQL 语句的日志消息通常是一个字符串，且包含换行符。
            # 使用 split() 和 join() 是去除换行符和多余空格的有效方法。
            if isinstance(record.msg, str):
                record.msg = ' '.join(record.msg.split())
        return True

def setup_log_interception(
    logger_names: Optional[Iterable[str]] = None,
    level: int = logging.NOTSET,
) -> None:
    """将标准库与指定第三方库日志重定向至 loguru"""
    default_names = {
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy",
        "tortoise",
        "tortoise.db_client",
    }
    names = set(logger_names or default_names)

    root_logger = logging.getLogger()
    root_logger.handlers = [InterceptHandler()]
    root_logger.setLevel(level)

    for logger_name in ['sqlalchemy.pool', 'sqlalchemy.dialects', 'sqlalchemy.orm']:
        sqlalchemy_logger = logging.getLogger(logger_name)
        sqlalchemy_logger.handlers.clear()
        sqlalchemy_logger.propagate = False
        sqlalchemy_logger.setLevel(logging.WARNING)  # 设置为警告级别或更高

    for name in names:
        _logger = logging.getLogger(name)
        _logger.handlers = [InterceptHandler()]
        _logger.propagate = False
        _logger.setLevel(level)


    # 禁用 ASGI 相关日志
    # logging.getLogger("uvicorn").setLevel(logging.CRITICAL)
    # logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
    # logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)
    # logging.getLogger("gunicorn").setLevel(logging.CRITICAL)
    # logging.getLogger("gunicorn.error").setLevel(logging.CRITICAL)
    # logging.getLogger("gunicorn.access").setLevel(logging.CRITICAL)
    #
    # # 禁用其他可能输出日志的库
    # logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    # logging.getLogger("starlette").setLevel(logging.CRITICAL)

    critical_names = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "gunicorn",
        "gunicorn.error",
        "gunicorn.access",
        "asyncio",
        "starlette"

    ]
    for logger_name in critical_names:
        _logger = logging.getLogger(logger_name)
        _logger.handlers.clear()  # 清除所有处理器
        _logger.propagate = False
        _logger.setLevel(logging.CRITICAL)



