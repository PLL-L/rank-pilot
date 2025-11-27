from src.core import logger
from src.core.db.db_redis import with_redis, AsyncRedisTool
from src.utils.track_utils import auto_request_id, TrackContextUtils


@with_redis
@auto_request_id(title="scheduler_id")
async def demo_scheduler(redis: AsyncRedisTool):
    result = await redis.set("asd","123")
    logger.info(f"redis result: {result}")
