import asyncio
import json
import logging
import signal
import sys
import traceback
import uuid
from typing import Any, Dict, Optional, Callable, Awaitable
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from aio_pika.abc import AbstractIncomingMessage
from aio_pika.exceptions import MessageProcessError

from src.core import logger
from src.core.db.db_database import AsyncDatabaseTool
from src.core.db.db_redis import AsyncRedisTool
from src.core.log.logger import init_logger
from src.utils.track_utils import TrackContextUtils



class AsyncConsumer:
    """
    异步消息消费者基类

    提供完整的消息队列消费功能，包括：
    - 连接管理
    - 并发控制
    - 重试策略
    - 死信队列
    - 优雅关闭
    - 健康检查
    """

    def __init__(
            self,
            amqp_url: str,
            queue_name: str,
            exchange_name: Optional[str] = None,
            exchange_type: str = "direct",
            routing_key: Optional[str] = None,
            require_ack: bool = True,
            max_priority: Optional[int] = None,
            max_interval_retries: int = 0,
            retry_interval: int = 1,
            max_requeue_retries: int = 0,
            dlx_exchange: Optional[str] = None,
            dlx_queue: Optional[str] = None,
            prefetch_count: int = 1,
    ):
        # 验证配置
        self._validate_config(
            prefetch_count, exchange_type, max_interval_retries,
            retry_interval, max_requeue_retries
        )

        # 基础配置
        self.amqp_url = amqp_url
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.routing_key = routing_key
        self.require_ack = require_ack
        self.max_priority = max_priority

        # 重试配置
        # self.max_interval_retries = max_interval_retries
        self.retry_interval = retry_interval
        self.max_requeue_retries = max_requeue_retries

        # 死信队列配置
        self.dlx_exchange_name = dlx_exchange
        self.dlx_queue_name = dlx_queue

        # 并发控制
        self.prefetch_count = prefetch_count
        self._processing_semaphore = asyncio.Semaphore(prefetch_count)

        # MQ 连接资源
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.queue: Optional[aio_pika.Queue] = None
        self.dlx_exchange: Optional[aio_pika.Exchange] = None
        self.dlx_queue: Optional[aio_pika.Queue] = None

        # 中间件资源
        self.async_db = AsyncDatabaseTool()
        self.async_redis = AsyncRedisTool(start_health_check=False)

        # 生命周期回调
        self.release_callback: Optional[Callable[[], Awaitable[None]]] = None

        # 运行状态
        self._running = False
        self._shutdown_event = asyncio.Event()

        self._stop_consuming = False  # 停止消费新消息
        self._active_messages = 0  # 当前处理中的消息数

    def _validate_config(
            self,
            prefetch_count: int,
            exchange_type: str,
            max_interval_retries: int,
            retry_interval: int,
            max_requeue_retries: int
    ) -> None:
        """验证配置参数"""
        if prefetch_count <= 0:
            raise ValueError("prefetch_count must be positive")
        if exchange_type not in ["direct", "topic", "headers", "fanout"]:
            raise ValueError(f"Invalid exchange_type: {exchange_type}")
        # if max_interval_retries < 0:
        #     raise ValueError("max_interval_retries must be non-negative")
        if retry_interval <= 0:
            raise ValueError("retry_interval must be positive")
        if max_requeue_retries < 0:
            raise ValueError("max_requeue_retries must be non-negative")

    # ==================== 生命周期管理 ====================

    async def _init_middleware(self) -> None:
        """初始化中间件资源"""
        try:
            # 确保数据库连接正常
            # await self._ensure_database_connection()
            self.async_redis.start_health_check()
            init_logger(intercept_std_logging=True, level=logging.INFO)
        except Exception as e:
            logger.error(f"Failed to initialize middleware: {e}")
            raise


    async def _close_middleware(self) -> None:
        """关闭中间件资源"""
        errors = []

        # 逐个关闭，确保每个资源都能尝试关闭
        try:
            await self.async_db.close_pool()
        except Exception as e:
            errors.append(f"DB close error: {e}")
            logger.error(f"Error closing database pool: {e}")

        try:
            await self.async_redis.close_pool()
        except Exception as e:
            errors.append(f"Redis close error: {e}")
            logger.error(f"Error closing redis pool: {e}")

        if errors:
            raise Exception(f"Multiple close errors: {', '.join(errors)}")

    async def _connect_mq(self) -> None:
        """建立MQ连接和声明队列"""
        try:
            # 创建连接和通道
            self.connection = await aio_pika.connect_robust(self.amqp_url)
            self.channel = await self.connection.channel()

            # 设置QoS
            await self.channel.set_qos(prefetch_count=self.prefetch_count)

            # 声明死信队列（如果配置了）
            await self._declare_dead_letter_queue()

            # 声明主队列和交换机
            await self._declare_main_queue()

            # 初始化中间件
            await self._init_middleware()

            logger.info(f"MQ connection established for queue: {self.queue_name}")

        except Exception as e:
            logger.error(f"Failed to connect to MQ: {e}")
            await self._close_mq()
            raise

    async def _declare_dead_letter_queue(self) -> None:
        """声明死信队列"""
        if not (self.dlx_exchange_name and self.dlx_queue_name):
            return

        try:
            self.dlx_exchange = await self.channel.declare_exchange(
                self.dlx_exchange_name, ExchangeType.DIRECT, durable=True
            )

            self.dlx_queue = await self.channel.declare_queue(
                self.dlx_queue_name,
                durable=True,
                arguments={"x-dead-letter-exchange": self.dlx_exchange.name}
            )

            await self.dlx_queue.bind(self.dlx_exchange, routing_key=self.routing_key)
            logger.info(f"Dead letter queue declared: {self.dlx_queue_name}")

        except Exception as e:
            logger.error(f"Failed to declare dead letter queue: {e}")
            raise

    async def _declare_main_queue(self) -> None:
        """声明主队列和交换机"""
        # 构建队列参数
        arguments = {}
        if self.max_priority:
            arguments["x-max-priority"] = self.max_priority
        if self.dlx_exchange:
            arguments["x-dead-letter-exchange"] = self.dlx_exchange.name

        # 声明队列
        self.queue = await self.channel.declare_queue(
            self.queue_name, durable=True, arguments=arguments
        )

        # 声明和绑定交换机
        if self.exchange_name:
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name, ExchangeType(self.exchange_type), durable=True
            )
            await self.queue.bind(self.exchange, routing_key=self.routing_key)


    async def _close_mq(self) -> None:
        """关闭MQ连接"""
        # 分别关闭，避免一个失败影响其他
        if self.channel:
            try:
                await asyncio.wait_for(self.channel.close(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Channel close timeout")
            except asyncio.CancelledError:
                logger.info("Channel close cancelled")
            except Exception as e:
                logger.error(f"Error closing channel: {e}")

        if self.connection:
            try:
                await asyncio.wait_for(self.connection.close(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("👋 Connection close timeout 👋")
            except asyncio.CancelledError:
                logger.info("👋 Connection close cancelled 👋")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

    # ==================== 消息处理 ====================

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        """消息处理入口"""

        # 如果正在关闭，拒绝新消息
        if self._stop_consuming and self.channel and not self.channel.is_closed:
            # logger.info("Rejecting new message due to shutdown")
            if self.require_ack:
                await message.nack(requeue=True)  # 重新排队
            return

        async with self._processing_semaphore:
            try:
                self._active_messages += 1
                await self._process_message_safe(message)
            except Exception as e:
                logger.error(f"Unexpected error in message processing: {e}")
                if self.require_ack:
                    await message.nack(requeue=False)
            finally:
                self._active_messages -= 1

    async def _process_message_safe(self, message: AbstractIncomingMessage) -> None:
        """安全的消息处理流程"""
        try:
            # 设置上下文
            TrackContextUtils.set_request_id(title="consumer")

            # 解析消息体
            body = await self._parse_message_body(message.body)

            logger.info(f"Received message: {body}")

            # 执行处理逻辑（带重试）
            result_info  = await self.handle_message(body)

            # 处理ACK/NACK
            await self._handle_ack_nack(message, result_info)

        except json.JSONDecodeError:
            logger.error(f" Invalid JSON message: {message.body.decode('utf-8', errors='replace')}")
            if self.require_ack:
                await message.nack(requeue=False)

        except Exception as e:
            logger.error(f" Processing error: {e}\n{traceback.format_exc()}")
            if self.require_ack:
                await message.nack(requeue=False)

    async def _parse_message_body(self, body_bytes: bytes) -> Dict[str, Any]:
        """异步解析消息体"""
        # 小消息体直接解析，大消息体使用线程池
        if len(body_bytes) < 1024:  # 1KB阈值
            return json.loads(body_bytes)
        else:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, json.loads, body_bytes)

    # async def _execute_with_retry(self, body: Dict[str, Any]) -> bool:
    #     """执行带重试的处理逻辑"""
    #     retry_count = 0
    #
    #     while retry_count <= self.max_interval_retries:
    #         try:
    #             if retry_count > 0:
    #                 logger.info(f" Retrying (attempt {retry_count})")
    #                 await asyncio.sleep(self.retry_interval)
    #
    #             success = await self.handle_message(body)
    #
    #             # 处理成功或明确成功
    #             if success in [True, None]:
    #                 logger.info(f" Processing successful")
    #                 return True
    #
    #             # 处理失败，继续重试
    #             retry_count += 1
    #             logger.warning(f" Processing failed, retrying...")
    #
    #         except Exception as e:
    #             logger.error(f" Exception in handle_message: {e}")
    #             retry_count += 1
    #
    #     # 重试耗尽
    #     logger.error(f" Max retries ({self.max_interval_retries}) exceeded")
    #     return False

    async def _handle_ack_nack(self, message: AbstractIncomingMessage, result_info: dict) -> None:
        """处理消息确认"""
        if not self.require_ack:
            return

        if result_info.get("basic_ack"):
            await message.ack()
            logger.info(f" Message acknowledged")
            return

        # 处理失败的情况
        await self._handle_failed_message(message, result_info)

    async def _handle_failed_message(self, message: AbstractIncomingMessage, result_info) -> None:
        """处理失败消息的重试或死信"""
        if not self.max_requeue_retries:
            # 没有配置重试，直接发送到死信队列
            # requeue = False if self.dlx_queue else True
            requeue = result_info.get("requeue")
            await message.nack(requeue=requeue)
            logger.info(f" Message nacked (requeue={requeue})")
            return

        # 执行重试逻辑
        await self._handle_requeue_retry(message)

    async def _handle_requeue_retry(self, message: AbstractIncomingMessage) -> None:
        """处理重新入队重试"""
        try:
            headers = message.headers or {}
            current_retry_count = headers.get("x-retry-count", 0)

            # 使用原子操作更新计数
            new_retry_count = current_retry_count + 1
            updated_headers = dict(headers)  # 创建副本避免竞态
            updated_headers["x-retry-count"] = new_retry_count

            if new_retry_count <= self.max_requeue_retries:
                # 重新发布消息
                await self.channel.default_exchange.publish(
                    Message(
                        body=message.body,
                        delivery_mode=DeliveryMode.PERSISTENT,
                        headers=updated_headers,
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
                logger.info(f" Message requeued (retry {new_retry_count})")

            else:
                # 重试次数耗尽
                logger.warning(f" Requeue retries exhausted")
                requeue = False if self.dlx_queue else True
                await message.nack(requeue=requeue)
                logger.info(f" Message nacked (requeue={requeue})")

        except Exception as e:
            logger.error(f" Error in requeue retry: {e}")
            await message.nack(requeue=False)


    # ==================== 公共接口 ====================

    async def handle_message(self, body: Dict[str, Any]) -> bool:
        """
        处理消息的核心逻辑

        Args:
            body: 解析后的消息体

        Returns:
            bool: True/None 表示成功，False 表示失败
        """
        raise NotImplementedError("Subclasses must implement handle_message")

    async def start_consuming(self) -> None:
        """开始消费消息"""
        await self.queue.consume(self._on_message, no_ack=not self.require_ack)
        logger.info(f"Started consuming from queue: {self.queue_name}")

    async def run(self) -> None:
        """运行消费者"""
        await self._connect_mq()
        await self.start_consuming()

        # 等待关闭信号
        await self._shutdown_event.wait()

    async def close(self) -> None:
        """关闭消费者"""
        logger.info("Closing consumer...")
        await self._close_mq()
        await self._close_middleware()
        logger.info("Consumer closed")

    def start(self) -> None:
        """启动消费者（阻塞模式）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # 设置信号处理器
            self._setup_signal_handlers(loop)

            logger.info(
                f"Starting consumer - exchange: {self.exchange_name}, "
                f"queue: {self.queue_name}, routing_key: {self.routing_key}"
            )

            # 启动消费任务
            loop.create_task(self.run())
            loop.run_forever()

        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutdown signal received")
        finally:
            loop.run_until_complete(self.close())
            loop.close()
            logger.info("Shutdown complete")

    def _setup_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        """设置信号处理器"""

        def shutdown_handler():
            logger.info("Shutdown handler triggered")
            logger.info(f"Shutdown: waiting for {self._active_messages} active messages")
            self._stop_consuming = True
            # 如果没有活动消息，直接退出
            def check_and_shutdown():
                """检查是否可以关闭，如果不行则继续等待"""
                if self._active_messages == 0:
                    # 没有活动消息，立即退出
                    logger.info("No active messages, shutting down immediately")
                    self._shutdown_event.set()
                    loop.call_soon(loop.stop)  # ✅ 立即停止循环
                else:
                    # 还有活动消息，继续等待
                    logger.debug(f"Still waiting for {self._active_messages} messages...")
                    # 1 秒后再次检查
                    loop.call_later(1, check_and_shutdown)

            def force_shutdown():
                """30秒超时强制关闭"""
                remaining = self._active_messages
                if remaining > 0:
                    logger.warning(f"Force shutdown: {remaining} messages still active")
                    # 强制取消任务
                    try:
                        tasks = [
                            t for t in asyncio.all_tasks(loop)
                            if t is not asyncio.current_task(loop) and not t.done()
                        ]
                        for task in tasks:
                            task.cancel()
                    except Exception as e:
                        logger.error(f"Error cancelling tasks: {e}")
                else:
                    logger.info("All messages completed, shutting down gracefully")

                self._shutdown_event.set()
                loop.call_soon(loop.stop)

            # 开始检查
            loop.call_soon(check_and_shutdown)
            # 设置30秒超时
            loop.call_later(30.0, force_shutdown)

        if sys.platform != "win32":
            for signame in {"SIGINT", "SIGTERM"}:
                try:
                    loop.add_signal_handler(getattr(signal, signame), shutdown_handler)
                except ValueError as e:
                    logger.warning(f"Failed to set signal handler for {signame}: {e}")
