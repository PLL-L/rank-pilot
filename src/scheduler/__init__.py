import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from src.core.db.db_redis import with_redis, AsyncRedisTool
from src.defined.redis_key import RedisKey
from src.scheduler.demo import demo_scheduler
from src.core import logger

scheduler = AsyncIOScheduler()

@with_redis
async def start_scheduler(redis: AsyncRedisTool):
    lock_acquired = await redis.set(
        RedisKey.SCHEDULER_LOCK,
        value=os.getpid(),
        ex=30,
        nx=True,
    )
    if lock_acquired:
        logger.info(f"🚀 定时调度器 进程 {os.getpid()} 获取到锁 🚀")
        await scheduler_add_job()
        scheduler.start()
    else:
        logger.info(f"定时调度器 进程 {os.getpid()} 未获取到锁！")


@with_redis
async def stop_scheduler(redis: AsyncRedisTool):
    await redis.delete(RedisKey.SCHEDULER_LOCK)
    if scheduler and scheduler.running:
        scheduler.shutdown()


async def scheduler_add_job():
    scheduler.add_job(
        demo_scheduler,
        'interval',
        seconds=600,
        id='unique_task'
    )