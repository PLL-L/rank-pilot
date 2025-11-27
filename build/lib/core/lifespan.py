"""
应用生命周期管理
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.core import logger
from src.core.db.db_database import AsyncDatabaseTool
from src.core.db.db_mongodb import AsyncMongoManager
from src.core.db.db_redis import AsyncRedisTool
from src.scheduler import start_scheduler, stop_scheduler
from src.core.mq import aio_mq


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 🚀 应用启动时执行
    logger.info("🚀 Startup: lifespan startup 🚀")
    app.state.redis = AsyncRedisTool() # 需要手动归还连接
    app.state.db_tool = AsyncDatabaseTool()
    app.state.mongo_manager = AsyncMongoManager()
    await aio_mq.connect()
    await start_scheduler()

    yield
    
    # 🧹 应用关闭时执行 ❌
    logger.info("🧹 Shutdown: lifespan shutdown... 🧹")
    await app.state.redis.close_pool()
    await app.state.db_tool.close_pool()
    await app.state.mongo_manager.close_pool()
    await aio_mq.close()
    await stop_scheduler()


if __name__ == '__main__':
    pass
