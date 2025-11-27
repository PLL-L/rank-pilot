#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/7/29 13:29
# @Author  : YueJian
# @File    : db_redis.py
# @Description :
import asyncio
import json
from contextlib import asynccontextmanager
from functools import wraps
from typing import Union, Optional, Any, AsyncGenerator, Dict, TypeVar
from redis import asyncio as aioredis
from redis.exceptions import RedisError, ConnectionError, TimeoutError, ResponseError

__all__ = ["AsyncRedisTool", "get_redis_dependency"]

from src.config import settings
from src.core import logger
from src.utils.singleton import Singleton

T = TypeVar("T")
Field = Union[int, float, str]


class RedisConfig:
    """Redis配置类"""

    def __init__(
        self,
        url: Optional[str] = None,
        host: str = settings.db.REDIS_DB.REDIS_HOST,
        port: int = settings.db.REDIS_DB.REDIS_PORT,
        db: int = settings.db.REDIS_DB.REDIS_DB,
        password: Optional[str] = None,
        decode_responses: bool = True,
        max_connections: int = 20,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
    ):
        self.url = url
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval


class AsyncRedisTool(metaclass=Singleton):
    """Redis操作工具类"""

    _connection_pool: Optional[aioredis.ConnectionPool] = None
    _health_check_task: Optional[asyncio.Task] = None

    def __init__(
        self,
        config: Optional[RedisConfig] = None,
        auto_reconnect: bool = True,
        start_health_check = True
    ):
        self.config = config or RedisConfig()
        self.auto_reconnect = auto_reconnect
        self._client: Optional[aioredis.Redis] = None
        self._last_health_check = 0
        self._init_pool()
        if start_health_check: # 是否开启健康检测
            self.start_health_check()

    def _init_pool(self) -> None:
        """初始化连接池"""
        if not self.__class__._connection_pool:
            pool_kwargs = {
                "encoding": "utf-8",
                "decode_responses": self.config.decode_responses,
                "max_connections": self.config.max_connections,
                "socket_timeout": self.config.socket_timeout,
                "socket_connect_timeout": self.config.socket_connect_timeout,
                "retry_on_timeout": self.config.retry_on_timeout,
                "protocol": 3,
            }

            if self.config.url:
                self.__class__._connection_pool = aioredis.ConnectionPool.from_url(
                    url=self.config.url, **pool_kwargs
                )
            else:
                self.__class__._connection_pool = aioredis.ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    password=self.config.password,
                    **pool_kwargs,
                )
            logger.info("🥵 redis _connection_pool initialized 🥵")

    def start_health_check(self) -> None:
        """启动健康检查任务"""
        if self._health_check_task is None:
            logger.info("redis start health check ")
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                await self.health_check()
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                await asyncio.sleep(5)  # 失败后等待5秒再重试

    @property
    def client(self) -> aioredis.Redis:
        """获取Redis客户端"""
        if self._client is None:
            self._client = aioredis.Redis(
                connection_pool=self.__class__._connection_pool
            )
        return self._client

    async def _ensure_connection(self) -> None:
        """确保连接正常"""
        if not self.auto_reconnect:
            return

        try:
            await self.client.ping()
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis连接异常，尝试重连: {e}")
            await self._reconnect()
        except RedisError as e:
            logger.error(f"Redis错误: {e}")
            raise

    async def _reconnect(self) -> None:
        """重新连接"""
        try:
            await self.client.connection_pool.disconnect()
            self._client = None
            self._init_pool()
            await self.client.ping()
        except Exception as e:
            logger.error(f"Redis重连失败: {e}")
            raise

    async def execute_with_retry(
        self,
        operation: str,
        func: callable,
        *args,
        max_retries: int = 3,
        retry_delay: float = 0.1,
        **kwargs,
    ) -> Any:
        """带重试机制的执行操作"""
        last_error = None
        for attempt in range(max_retries):
            try:
                await self._ensure_connection()
                return await func(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
            except Exception as e:
                logger.error(f"Redis {operation} 操作失败: {e}")
                raise
        raise last_error

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """异步存储数据（自动JSON序列化）"""
        return await self.execute_with_retry(
            "set",
            self.client.set,
            name=key,
            value=json.dumps(value, ensure_ascii=False),
            ex=ex,
            px=px,
            nx=nx,
            xx=xx,
        )

    async def get(self, key: str, default: Any = None) -> Any:
        """异步获取数据（自动JSON反序列化）"""
        result = await self.execute_with_retry("get", self.client.get, key)
        try:
            return json.loads(result) if result else default
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON data for key {key}")
            return default

    async def delete(self, *keys: str) -> int:
        """异步删除一个或多个key"""
        return await self.execute_with_retry("delete", self.client.delete, *keys)

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间（秒）"""
        return await self.execute_with_retry("expire", self.client.expire, key, seconds)

    async def exists(self, key: str) -> int:
        """判断key是否存在"""
        return await self.execute_with_retry("exists", self.client.exists, key)

    async def incr(
        self,
        key: str,
        amount: int = 1,
        initial_value: int = 0,
        ttl: Optional[int] = None,
    ) -> int:
        """原子递增操作"""
        lua_script = """
        if redis.call("EXISTS", KEYS[1]) == 0 then
            redis.call("SET", KEYS[1], ARGV[2])
            if ARGV[3] ~= "0" then
                redis.call("EXPIRE", KEYS[1], ARGV[3])
            end
            return tonumber(ARGV[2])
        end
        return redis.call("INCRBY", KEYS[1], ARGV[1])
        """
        try:
            result = await self.execute_with_retry(
                "incr",
                self.client.eval,
                lua_script,
                1,
                key,
                str(amount),
                str(initial_value),
                str(ttl or 0),
            )
            return int(result)
        except ResponseError as e:
            logger.error(f"Redis incr error: {e}")
            await self.client.delete(key)
            return await self.incr(key, amount, initial_value, ttl)

    async def decr(
        self,
        key: str,
        amount: int = 1,
        initial_value: int = 0,
        ttl: Optional[int] = None,
    ) -> int:
        """原子递减操作"""
        return await self.incr(key, -amount, initial_value, ttl)

    async def pipeline(self):
        """获取异步管道操作对象"""
        await self._ensure_connection()
        return self.client.pipeline()

    async def publish(self, channel: str, message: Any) -> int:
        """异步发布消息到频道"""
        return await self.execute_with_retry(
            "publish", self.client.publish, channel, json.dumps(message)
        )

    async def subscribe(self, channel: str) -> aioredis.client.PubSub:
        """订阅频道"""
        await self._ensure_connection()
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池实时状态信息"""
        if not self.__class__._connection_pool:
            return {}

        pool = self.__class__._connection_pool
        in_use = len(pool._in_use_connections)
        idle = len(pool._available_connections)
        total = pool.max_connections
        usage_rate = in_use / total if total > 0 else 0

        stats = {
            "max_connections": total,
            "in_use_connections": in_use,
            "idle_connections": idle,
            "usage_rate": f"{usage_rate:.2%}",
        }

        if usage_rate > 0.8:
            logger.warning(f"Redis连接池使用率过高: {stats}")

        return stats

    async def health_check(self) -> bool:
        """连接池健康检查"""
        try:
            stats = await self.get_pool_stats()
            if (
                stats.get("in_use_connections", 0)
                >= stats.get("max_connections", 0) * 0.9
            ):
                logger.warning(f"Redis连接池使用率过高: {stats['usage_rate']}")
                return False
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    @classmethod
    def from_url(cls, url: str = None) -> "AsyncRedisTool":
        """从配置文件创建实例"""
        if not url:
            url = settings.db.REDIS_DB.REDIS_DB_URL.unicode_string()
        return cls(config=RedisConfig(url=url))

    async def close(self) -> None:
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None

    @classmethod
    async def close_pool(cls) -> None:
        """释放连接池资源"""
        if cls._connection_pool:
            await cls._connection_pool.disconnect()
            cls._connection_pool = None
        if cls._health_check_task:
            cls._health_check_task.cancel()
            try:
                await cls._health_check_task
            except asyncio.CancelledError:
                pass
            cls._health_check_task = None

        logger.info(" ✅ redis 连接池关闭完成 ✅")

    async def __aenter__(self) -> "AsyncRedisTool":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


async def get_redis_dependency() -> AsyncGenerator[AsyncRedisTool, Any]:
    """获取Redis实例依赖 依赖注入"""
    async with AsyncRedisTool.from_url() as redis:
        await redis.get_pool_stats()
        yield redis


@asynccontextmanager
async def get_redis_context():
    """可以在任何地方使用的上下文管理器"""
    async with AsyncRedisTool.from_url() as redis:
        await redis.get_pool_stats()
        yield redis


def with_redis(func):
    """自动提供Redis实例的装饰器（redis作为关键字参数）"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with get_redis_context() as redis:
            # 将redis作为关键字参数传入
            return await func(*args, **kwargs, redis=redis)

    return wrapper