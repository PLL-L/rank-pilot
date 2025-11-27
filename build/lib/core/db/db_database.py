#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/3/24 22:42
# @File    : db_database.py
# @Description : 数据库连接和会话管理
import asyncio
import functools
from contextlib import asynccontextmanager
from functools import wraps
from typing import Optional, Callable, Any, Coroutine, AsyncGenerator, Dict

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.core import logger
from src.utils.singleton import Singleton

# __all__ = ["AsyncDatabaseTool", "get_db_dependency", "get_db_context", "transactional"]


class DatabaseConfig:
    """数据库配置类"""

    def __init__(
            self,
            url: Optional[str] = None,
            pool_size: int = settings.db.ORM_DB.POOL_SIZE,
            max_overflow: int = settings.db.ORM_DB.MAX_OVERFLOW,
            pool_timeout: int = settings.db.ORM_DB.POOL_TIMEOUT,
            pool_recycle: int = settings.db.ORM_DB.POOL_RECYCLE,
            pool_pre_ping: bool = settings.db.ORM_DB.POOL_PRE_PING,
            echo: bool = settings.db.ORM_DB.DB_ECHO,
            pool_reset_on_return: bool = settings.db.ORM_DB.POOL_RESET_ON_RETURN,
            echo_pool: bool = settings.db.ORM_DB.ECHO_POOL,

    ):
        self.url = url or settings.db.ORM_DB.DB_URL
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo = echo
        self.pool_reset_on_return = pool_reset_on_return
        self.echo_pool = echo_pool



class AsyncDatabaseTool(metaclass=Singleton):
    """数据库操作工具类"""

    _engine: Optional[AsyncEngine] = None
    _async_session: Optional[async_sessionmaker[AsyncSession]] = None

    def __init__(
            self,
            config: Optional[DatabaseConfig] = None,
    ):
        self.config = config or DatabaseConfig()
        self._init_engine()

    def _init_engine(self) -> None:
        """初始化数据库引擎"""
        if not self.__class__._engine:
            self.__class__._engine = create_async_engine(
                url=self.config.url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=self.config.pool_pre_ping,
                echo=self.config.echo,
                pool_reset_on_return=self.config.pool_reset_on_return, # todo
                echo_pool = self.config.echo_pool #todo

            )

            self.__class__._async_session = async_sessionmaker(
                bind=self.__class__._engine,
                class_=AsyncSession,
                autocommit=False,
                expire_on_commit=False
            )

            logger.info("🐶 Database engine initialized 🐶")


    @property
    def async_session(self) -> async_sessionmaker[AsyncSession]:
        """获取会话工厂"""
        if self.__class__._async_session is None:
            self._init_engine()
        return self.__class__._async_session


    async def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池状态信息"""
        if not self.__class__._engine:
            return {}

        # SQLAlchemy 连接池状态信息
        pool = self.__class__._engine.pool
        checked_out = pool.checkedout()
        checked_in = pool.checkedin()
        overflow = pool.overflow()
        total = pool.size()
        usage_rate = checked_out / total if total > 0 else 0

        stats = {
            "pool_size": total,
            "checked_out_connections": checked_out,
            "checked_in_connections": checked_in,
            "overflow_connections": overflow,
            "usage_rate": f"{usage_rate:.2%}",
        }


        if usage_rate > 0.8:
            logger.warning(f"Database连接池使用率过高: {stats}")

        return stats

    @classmethod
    def from_url(cls, url: str = None) -> "AsyncDatabaseTool":
        """从URL创建实例"""
        if not url:
            url = settings.db.ORM_DB.DB_URL
        return cls(config=DatabaseConfig(url=url))

    async def close(self) -> None:
        """关闭当前客户端"""
        # 对于数据库，通常不需要单独关闭客户端
        pass

    @classmethod
    async def close_pool(cls) -> None:
        """释放连接池资源"""
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            cls._async_session = None

        logger.info("🐶 Database 连接池关闭完成 🐶 ")

    async def __aenter__(self) -> "AsyncDatabaseTool":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


async def get_db_dependency() -> AsyncGenerator[AsyncSession, Any]:
    """获取数据库会话依赖 - 依赖注入"""
    async with AsyncDatabaseTool.from_url() as db_tool:
        await db_tool.get_pool_stats()
        yield db_tool


@asynccontextmanager
async def get_db_context():
    """可以在任何地方使用的数据库上下文管理器"""
    async with AsyncDatabaseTool.from_url() as db_tool:
        await db_tool.get_pool_stats()
        async with db_tool.async_session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


def transactional( func: Callable[..., Coroutine[Any, Any, Any]]):
    """
    事务装饰器
    - 如果外部传入 session，则直接使用该 session
    - 如果没有传入 session，则自动创建并管理事务
    """

    @functools.wraps(func)
    async def wrapper(*args, session: Optional[AsyncSession] = None, **kwargs):
        # 外部已传入 session => 直接使用
        if session is not None:
            return await func(*args, session=session, **kwargs)

        # 外部没传 session => 自己创建并管理
        async with get_db_context() as session:
            # 将session作为关键字参数传入
            return await func(*args, **kwargs, session=session)

    return wrapper
