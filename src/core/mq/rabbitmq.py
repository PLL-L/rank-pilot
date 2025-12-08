# -*- coding: utf-8 -*-
# @Time :2024/08/04 17:58
# @Author : Pocket
# @Desc : rabbit mq
from aio_pika import (
    connect_robust,
    Connection,
    Channel,
    Message,
    ExchangeType,
    DeliveryMode,
    IncomingMessage,
)
from typing import Union
import json
import asyncio
import time
import logging
import arrow
import copy
from enum import Enum
from datetime import datetime, date, timedelta
import decimal

from src.core import logger, settings
from src.utils.json_encoder import CJsonEncoder


class CustomRabbitMQ:
    def __init__(self, url=None, **kwargs):
        self.url = url or settings.RABBITMQ_CONFIG.RABBITMQ_URL
        self.max_retries = kwargs.get("rabbitmq_max_retries", 3)
        self.initial_delay = kwargs.get("rabbitmq_initial_delay", 1.0)
        self.max_retry_time = kwargs.get("rabbitmq_max_retry_time", 10)
        self.exchange_durable = kwargs.get("rabbitmq_exchange_durable", True)
        self.exchange_name = settings.RABBITMQ_CONFIG.RABBITMQ_EXCHANGE_NAME
        self.exchange_type = settings.RABBITMQ_CONFIG.RABBITMQ_EXCHANGE_TYPE
        self.disable_logging = kwargs.get("rabbitmq_disable_logging", False)
        self.connection: Connection = None
        self.channel: Channel = None
        self.exchange = None
        self._reconnect_lock = asyncio.Lock()

    # def init_app(self, app) -> None:
    #     @app.on_event("startup")
    #     async def startup():
    #         await self.connect()
    #
    #     @app.on_event("shutdown")
    #     async def shutdown():
    #         await self.close()

    async def connect(self):
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name,
            ExchangeType(self.exchange_type),
            durable=self.exchange_durable,
        )
        if not self.exchange:
            raise RuntimeError("Failed to declare exchange")
        # 订阅 Basic.Return 消息
        self.channel.return_listener = self.on_message_returned
        logger.info(f"RabbitMQ connected exchange: {self.exchange_name}")

    async def close(self):
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()

    async def reconnect(self):
        # 防止并发协程重连打爆
        async with self._reconnect_lock:
            # 在锁内检查连接状态
            if self.connection is not None and not self.connection.is_closed:
                logger.info("Connection already exists, no need to reconnect.")
                return
            logger.warning("Reconnecting to RabbitMQ...")
            await self.close()
            await self.connect()

    async def on_message_returned(self, message: IncomingMessage):
        logger.warning(f"Message was returned: {message}")

    async def publish(
        self,
        routing_key: str,
        msg: Union[str, dict, list],
        priority=None,
        message_id=None,
    ):
        """消息发布

        Parameters
        ----------
        routing_key : str
            路由key
        msg : Union[str, dict, list]
            消息内容
        priority : int, optional
            消息优先级, by default None

        Raises
        ------
        ValueError
            _description_
        ValueError
            _description_
        """
        source_msg = copy.deepcopy(msg)
        if msg is None:
            raise ValueError("msg cannot be None")
        if not self.channel or self.channel.is_closed:
            await self.reconnect()
        if isinstance(msg, (dict, list)):
            msg = json.dumps(msg, cls=CJsonEncoder)
        elif not isinstance(msg, str):
            raise ValueError("msg must be a str, dict, or list")
        message = Message(
            msg.encode("utf-8"),
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=message_id,
            priority=priority,
            headers={"x-send-time": arrow.utcnow().to("+08:00").isoformat()},
        )
        retries = 0
        delay = self.initial_delay

        start_time = time.time()

        while retries < self.max_retries:
            try:
                await self.exchange.publish(
                    message, routing_key=routing_key, timeout=10
                )
                logger.info(
                    f"Message sent to exchange '{self.exchange_name}' with routing key '{routing_key}' successfully: {source_msg}"
                )
                return
            except Exception as e:
                retries += 1
                elapsed_time = time.time() - start_time
                if (
                    retries > self.max_retries
                    or elapsed_time + delay > self.max_retry_time
                ):
                    logger.warning(
                        f"Failed to publish message after {retries} retries and {elapsed_time:.2f} seconds err: {e}"
                    )
                    raise
                logger.warning(
                    f"Failed to publish message, retrying in {delay} seconds (attempt {retries}/{self.max_retries})"
                )
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff





