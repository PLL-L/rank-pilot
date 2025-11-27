from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.db.db_database import transactional
from src.models.config_model import ConfigTable
from src.service.base import BaseService


class CommonService(BaseService):
    pass

    @transactional
    async def demo(self, id: int, session: AsyncSession):
        logger.info(f"123 - {id}")
        result = await session.get(ConfigTable, id)
        return result