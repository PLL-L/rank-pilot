"""
核心模块
"""
from .log.logger import logger
from src.config import settings

__all__ = ["logger", "settings"]