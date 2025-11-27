#!/usr/bin/python
# -*- coding: utf-8 -*-# @version        : 1.0
# @Create Time    : 2024/3/23 22:30
# @File           : logger.py
# @IDE            : PyCharm
# @Desc           : 日志配置

# 日志封装
import logging
from typing import Any, Dict, Iterable, Optional

from loguru import logger as _logger

from .log_config import log_config
from .log_handlers import setup_log_interception
from src.utils.track_utils import TrackContextUtils


class Logger:
    """增强的日志实现，支持结构化日志、trace_id 注入、接管标准 logging"""

    def __init__(
        self,
        config=None,
        intercept_std_logging: bool = False,
        intercept_level: int = logging.NOTSET,
        intercept_names: Optional[Iterable[str]] = None,
    ):
        self.config = config or log_config
        self.logger = _logger
        self.logger.remove()

        # 全局 patch：为每条日志注入公共字段（trace_id/biz/service/env）
        self.logger = self.logger.patch(self._patch_record)

        # 添加 handlers（保持各自的 filter，避免覆盖）
        for handler in self.config.handlers:
            self.logger.add(**handler)

        if intercept_std_logging:
            setup_log_interception(logger_names=intercept_names, level=intercept_level)

    def _patch_record(self, record: Dict[str, Any]) -> None:
        extra = record["extra"]
        # 兜底字段
        extra.setdefault("trace_id", TrackContextUtils.get_request_id() or "-")
        extra.setdefault("biz", "-")
        # extra.setdefault("service", settings.SERVICE_NAME)
        # extra.setdefault("env", settings.ENV)

    def get_logger(self):
        return self.logger

    def enable_interception(
        self,
        level: int = logging.NOTSET,
        names: Optional[Iterable[str]] = None,
    ):
        setup_log_interception(logger_names=names, level=level)


# 全局实例（默认不拦截标准 logging，交由入口 init_logger 控制）
logger_instance = Logger(intercept_std_logging=False)
logger = logger_instance.get_logger()

# 兼容：若需要为某业务域提供预绑定标签
logger_tortoise = logger.bind(biz="orm")


def init_logger(
    intercept_std_logging: bool = True,
    level: int = logging.NOTSET,
    names: Optional[Iterable[str]] = None,
):
    """在应用启动处调用，按需启用标准 logging 拦截"""
    if intercept_std_logging:
        logger_instance.enable_interception(level=level, names=names)
    return logger


# 常用方法直出
info = logger.info
debug = logger.debug
warning = logger.warning
error = logger.error
critical = logger.critical
exception = logger.exception
