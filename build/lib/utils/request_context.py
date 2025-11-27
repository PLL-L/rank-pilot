# @Version        : 1.0
# @Update Time    : 2025/5/24 11:59
# @File           : request_context.py
# @IDE            : PyCharm
# @Desc           : 文件描述信息
import contextvars
from typing import Optional

# 存储请求上下文存储器
REQUEST_ID_MANAGER: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=""
)
