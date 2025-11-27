import traceback

from sqlalchemy.ext.asyncio import AsyncSession

from consumers.base import AsyncConsumer
from src.core.db.db_database import transactional
from src.core.db.db_redis import with_redis, AsyncRedisTool
from src.defined.mq_routing_key import MqRoutingKey
from src.models.config_model import ConfigTable
from src.core import logger, settings
from src.utils.track_utils import auto_request_id


class KgpRequestConsumer(AsyncConsumer):

    @with_redis
    @transactional
    async def handle_message(self, body, redis: AsyncRedisTool, session: AsyncSession):
        """
        执行入库
        :param body: {"request_type":"auth_update","data":{}}
        :return:
        """
        try:

            await redis.set("你好呀","123")
            result = await redis.get("你好呀")
            result1 = await session.get(ConfigTable, 1)
            logger.info(result)
            logger.info(f"mysql --- {result1}")
            logger.info("消息来了")
            logger.info("你好呀")
            return True
        except Exception as _:
            logger.warning(traceback.format_exc())
            return False




if __name__ == "__main__":
    consumer = KgpRequestConsumer(
        amqp_url=settings.RABBITMQ_CONFIG.RABBITMQ_URL,
        queue_name=MqRoutingKey.TEST_QUEUE,
        exchange_name=settings.RABBITMQ_CONFIG.RABBITMQ_EXCHANGE_NAME,
        routing_key=MqRoutingKey.TEST_QUEUE,
        require_ack=False
    )
    consumer.start()