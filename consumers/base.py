import logging
import sys
from typing import Callable, Awaitable
from aio_pika import Message, DeliveryMode
from aio_pika import connect_robust, ExchangeType
from aio_pika.abc import AbstractIncomingMessage
from aio_pika.exceptions import MessageProcessError
import json
import asyncio
from redis.asyncio import Redis
import signal
import traceback
import uuid

from src.core import logger
from src.core.db.db_database import AsyncDatabaseTool
from src.core.db.db_redis import AsyncRedisTool
from src.core.log.logger import init_logger
from src.utils.track_utils import TrackContextUtils


# from extensions import logger, db_base, redis_base, mongo_base


class AsyncConsumer:
    def __init__(
        self,
        amqp_url: str,
        queue_name: str,
        exchange_name: str = None,
        exchange_type: str = "direct",
        routing_key: str = None,
        require_ack: bool = True,
        max_priority: int = None,
        max_interval_retries: int = 0,
        retry_interval: int = 0,
        max_requeue_retries: int = 0,
        dlx_exchange: str = None,
        dlx_queue: str = None,
        prefetch_count: int = 1,
    ):
        """消费者基类

        Parameters
        ----------
        amqp_url : str
            MQ URI
        queue_name : str
            队列名
        exchange_name : str, optional
            交换机名称, by default None
        exchange_type : str, optional
            交换机类型, by default "direct"
        routing_key : str, optional
            路由key, by default None
        require_ack : bool, optional
            是否需要ack, by default True
        max_priority : int, optional
            最大优先级, by default None
        max_interval_retries : int, optional
            表示内部递归重试, 最大重试次数, by default 0
        retry_interval : int, optional
            重试间隔, by default 1
        max_requeue_retries : int, optional
            表示放回队列(尾部)重试, 最大重回队尾次数, by default 0
        dlx_exchange : str, optional
            死信交换机, by default None
        dlx_queue : str, optional
            死信队列名, by default None
        prefetch_count : int, optional
            每次从队列中获取的消息数量, by default 1
        """
        self.amqp_url = amqp_url
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.routing_key = routing_key
        self.require_ack = require_ack
        self.max_priority = max_priority
        self.max_interval_retries = max(0, max_interval_retries)
        self.retry_interval = max(1, retry_interval)
        self.max_requeue_retries = max(0, max_requeue_retries)
        self.dlx_exchange = dlx_exchange
        self.dlx_queue = dlx_queue
        self.async_db = AsyncDatabaseTool()
        self.async_redis = AsyncRedisTool(start_health_check=False)
        # self.async_mongo = mongo_base.get_db
        self.release_callback = None
        # 使用信号量控制并发
        self.prefetch_count = prefetch_count
        self.semaphore = asyncio.Semaphore(prefetch_count)

    async def init_middleware(self):
        self.async_redis.start_health_check()
        init_logger(
            intercept_std_logging=True,
            level=logging.INFO,
        )
        await asyncio.gather(
            # db_base.init_db(),
            # redis_base.init_redis(),
            # mongo_base.init_mongo()
        )

    async def close_middleware(self):
        await asyncio.gather(
            self.async_db.close_pool(),
            self.async_redis.close_pool(),
            # mongo_base.close_mongo()
        )

    async def connect(self):
        # 创建连接
        self.connection = await connect_robust(self.amqp_url)
        # 创建通道
        self.channel = await self.connection.channel()
        # 声明死信队列
        if self.dlx_exchange and self.dlx_queue:
            self.dlx_exchange = await self.channel.declare_exchange(
                self.dlx_exchange, ExchangeType.DIRECT, durable=True
            )
            self.dlx_queue = await self.channel.declare_queue(
                self.dlx_queue,
                durable=True,
                arguments={"x-dead-letter-exchange": self.dlx_exchange.name},
            )
            # 绑定死信队列到死信交换机
            await self.dlx_queue.bind(self.dlx_exchange, routing_key=self.routing_key)

        # 声明队列
        arguments = {}
        if self.max_priority:
            arguments.update({"x-max-priority": self.max_priority})
        if self.dlx_exchange and self.dlx_queue:
            arguments.update({"x-dead-letter-exchange": self.dlx_exchange.name})
        self.queue = await self.channel.declare_queue(
            self.queue_name, durable=True, arguments=arguments
        )

        if self.exchange_name:
            # 声明交换机
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name, ExchangeType(self.exchange_type), durable=True
            )
            # 绑定队列到交换机
            await self.queue.bind(self.exchange, routing_key=self.routing_key)
        # # 初始化其余中间件
        await self.init_middleware()

    async def start_consuming(self):
        await self.channel.set_qos(prefetch_count=self.prefetch_count)
        await self.queue.consume(self.on_message, no_ack=not self.require_ack)

    async def on_message(self, message: AbstractIncomingMessage):
        retry_count = 0
        try:
            async with self.semaphore:
                async with message.process(ignore_processed=True):
                    try:
                        TrackContextUtils.set_request_id(title="consumer_id")
                        body = json.loads(message.body)
                        logger.info(f"Received message: {body}")
                        success = None
                        while retry_count <= self.max_interval_retries:
                            if retry_count > 0:
                                logger.info(
                                    f"Retrying message, attempt {retry_count}"
                                )
                            success = await self.handle_message(body)
                            if success in [True, None]:
                                break
                            else:
                                retry_count += 1
                                await asyncio.sleep(1)
                        if self.require_ack:
                            if success in [True, None]:
                                await message.ack()
                                logger.info(f"Message processed: ack")
                            else:
                                requeue = False if self.dlx_queue else True
                                if self.max_requeue_retries > 0:
                                    headers = message.headers or {}
                                    retry_requeue_count = (
                                        headers.get("x-retry-count", 0) + 1
                                    )
                                    headers["x-retry-count"] = retry_requeue_count
                                    if (
                                        retry_requeue_count
                                        <= self.max_requeue_retries
                                    ):
                                        await self.channel.default_exchange.publish(
                                            Message(
                                                body=message.body,
                                                delivery_mode=DeliveryMode.PERSISTENT,
                                                headers=headers,
                                                content_type=message.content_type,
                                                content_encoding=message.content_encoding,
                                                correlation_id=message.correlation_id,
                                                expiration=message.expiration,
                                                message_id=message.message_id,
                                                user_id=message.user_id,
                                                app_id=message.app_id,
                                                type=message.type,
                                            ),
                                            routing_key=self.routing_key,
                                        )
                                        await message.ack()
                                        logger.info(f"Message processed: ack")
                                    else:
                                        logger.warning(f"Requeue count exceeded")
                                        if requeue is True:
                                            await message.ack()
                                            logger.info(f"Message processed: ack")
                                        else:
                                            await message.nack(requeue=False)
                                            logger.info(f"Message processed: nack")
                                else:
                                    await message.nack(requeue=requeue)
                                    logger.info(f"Message processed: nack")
                    except json.JSONDecodeError:
                        logger.error(
                            f"Invalid JSON message received:{message.body}"
                        )
                        if self.require_ack:
                            await message.nack(requeue=False)
                            logger.info(f"Message processed: nack")
        except MessageProcessError as e:
            logger.warning(
                f"Message has already been processed:{message.body} err:{e}"
            )

        except Exception as _:
            logger.error(
                f"Error processing message {message.body} err:{traceback.format_exc()}"
            )
            if self.require_ack:
                await message.nack(requeue=False)
        finally:
            pass


    async def handle_message(self, body):
        # 这里是消息处理逻辑，可以根据需要进行重写
        # 返回 True/None 表示处理成功，自动 ack 消息
        # 返回 False 表示处理失败，自动 nack 消息
        raise Exception("Received message but handle_message is not implemented")

    def sigint_close(self):
        if self.release_callback and callable(self.release_callback):
            # ! TODO 暂时还没想好解决方案，先注释
            # asyncio.run(self.release_callback())
            pass

    async def run(self):
        await self.connect()
        await self.start_consuming()

    async def close(self):
        await self.channel.close()
        await self.connection.close()
        await self.close_middleware()

    def start(self):
        loop = asyncio.get_event_loop()

        def shutdown():
            # 执行子类的资源回收动作
            self.sigint_close()
            logger.info("Shutting down, please wait...")
            tasks = [
                t
                for t in asyncio.all_tasks(loop)
                if t is not asyncio.current_task(loop)
            ]
            for task in tasks:
                task.cancel()
            loop.stop()

        for signame in {"SIGINT", "SIGTERM"}:
            if sys.platform != "win32":
                loop.add_signal_handler(getattr(signal, signame), shutdown)

        try:
            logger.info(
                f"Starting consumer exchange: {self.exchange_name} queue_name: {self.queue_name} routing_key: {self.routing_key}"
            )
            loop.create_task(self.run())
            loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
                logger.info("Interrupt received, shutting down...")
        finally:
            loop.run_until_complete(self.close())
            loop.close()
            logger.info("Shutdown complete")
