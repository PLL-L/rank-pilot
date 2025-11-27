# @Version        : 1.0
# @Update Time    : 2025/3/24 22:42
# @File           : track_utils.py
# @IDE            : PyCharm
# @Desc           : 链路追踪上下文管理器
import asyncio
import contextvars
import uuid
from functools import wraps
from typing import Optional, Callable

from src.utils.request_context import REQUEST_ID_MANAGER


# 链路追踪上下文工具类
class TrackContextUtils:
    # 设置请求唯一id
    @staticmethod
    def set_request_id(req_id: str = None, title="trade_id") -> str:
        req_id = req_id or uuid.uuid4().hex
        req_id = f"{title}:{req_id}"
        REQUEST_ID_MANAGER.set(req_id)
        return req_id

    # 获取请求唯一id
    @staticmethod
    def get_request_id() -> str:
        return REQUEST_ID_MANAGER.get()


def auto_request_id(title: str = "trade_id"):
    """
    自动为函数添加log请求ID的装饰器

    Args:
        title: 请求ID的前缀
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 自动生成请求ID
            TrackContextUtils.set_request_id(title=title)
            try:
                # 调用原函数
                return await func(*args, **kwargs)
            finally:
                # 清理请求ID（可选）
                REQUEST_ID_MANAGER.set(None)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步函数版本
            TrackContextUtils.set_request_id(title=title)

            try:
                return func(*args, **kwargs)
            finally:
                REQUEST_ID_MANAGER.set(None)

        # 根据原函数类型返回对应的包装器
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
