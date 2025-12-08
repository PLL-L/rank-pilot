"""
Description:
Author: 月间
Date: 2025-10-01 02:00:42
LastEditTime: 2025-10-01 02:18:27
LastEditors:
"""
#!/usr/bin/python
# -*- coding: utf-8 -*-# @version        : 1.0
# @Create Time    : 2025/8/23
# @File           : log_config.py
# @IDE            : PyCharm
# @Desc           : 日志配置参数管理

# 日志配置参数管理
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Any

from src.config import settings


@dataclass
class LogConfig:
    """日志配置类"""

    log_path: str = settings.system.LOG_PATH
    debug: bool = settings.system.DEBUG
    retention: str = "30 days"
    rotation: str = "100 MB"
    enqueue: bool = True
    encoding: str = "utf-8"
    compression: str = "zip"
    backtrace: bool = settings.system.DEBUG
    diagnose: bool = settings.system.DEBUG
    handlers: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        # 确保日志目录存在
        os.makedirs(self.log_path, exist_ok=True)
        self._init_handlers()

    def _init_handlers(self):
        """初始化日志处理器"""
        log_file_path = os.path.join(self.log_path, "rank_zen_{time:YYYY-MM-DD}.log")

        common_settings = {
            "enqueue": self.enqueue,
            "encoding": self.encoding,
            "compression": self.compression,
            "retention": self.retention,
            "rotation": self.rotation,
            "backtrace": self.backtrace,
            "diagnose": self.diagnose,
        }

        log_format = (
            "<level>[{level}]</level> | <green>{time:YYYY-MM-DD HH:mm:ss}</green> -> "
            "<magenta>{extra[trace_id]}</magenta> | <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - {message}"
        )

        # 统一日志处理器，所有等级的日志都写入同一个文件
        self.handlers.append(
            {
                "sink": log_file_path,
                "level": settings.system.LOG_LEVEL,  # 使用配置文件中的日志级别
                "format": log_format,
                "serialize": False,
                **common_settings,
            }
        )

        # 控制台输出配置
        self.handlers.append(
            {
                "sink": sys.stdout,
                "level": settings.system.LOG_LEVEL,  # 使用配置文件中的日志级别
                "format": log_format,
                "colorize": True,
                "serialize": False,
            }
        )


# 导出配置实例
log_config = LogConfig()
