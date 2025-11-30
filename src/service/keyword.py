from typing import List

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.exception.custom_exception import GlobalErrorCodeException
from src.models.keyword_model import KeywordSearchConfigTable
from src.service.base import BaseService


class KeywordService(BaseService):
    """关键词配置服务：负责数据库查询与业务校验"""

    @staticmethod
    def get_platforms() -> List[str]:
        """返回可选平台列表（用于前端多选）"""
        return ["百度PC", "百度M", "360PC", "360M"]

    async def get_keyword_infos(
        self,
        session: AsyncSession,
        platforms: List[str],
        keywords: List[str] = None,
        remark: str = None,
    ) -> dict:
        """根据平台、关键词与备注查询配置
        - 平台：必须、多选
        - 关键词：可选、多选、模糊查询（任意一个匹配即可）
        - 备注：可选、模糊查询
        """
        valid_platforms = set(self.get_platforms())
        if any(p not in valid_platforms for p in platforms):
            raise GlobalErrorCodeException(msg="平台参数不合法")

        conditions = [KeywordSearchConfigTable.platform.in_(platforms)]

        if keywords:
            # 关键词模糊多选，OR 组合
            keyword_conditions = [
                KeywordSearchConfigTable.keyword.ilike(f"%{k}%") for k in keywords
            ]
            conditions.append(or_(*keyword_conditions))

        if remark:
            # 备注模糊查询
            conditions.append(KeywordSearchConfigTable.remark.ilike(f"%{remark}%"))

        query = (
            select(KeywordSearchConfigTable)
            .where(and_(*conditions))
            .order_by(KeywordSearchConfigTable.created_at.desc())
        )

        result = await session.execute(query)
        items = result.scalars().all()
        return {"items": items}

    async def search_by_keyword(
        self,
        session: AsyncSession,
        keywords: List[str],
        platforms: List[str] = None,
    ) -> dict:
        """
        根据关键词模糊查询配置

        Args:
            session: 数据库会话
            keywords: 关键词列表，支持模糊查询（OR组合）
            platforms: 平台列表，可选过滤条件

        Returns:
            dict: 包含查询结果的字典
        """
        if not keywords:
            raise GlobalErrorCodeException(msg="关键词参数不能为空")

        # 关键词模糊多选，OR 组合
        keyword_conditions = [
            KeywordSearchConfigTable.keyword.ilike(f"%{k}%") for k in keywords
        ]
        conditions = [or_(*keyword_conditions)]

        # 如果指定了平台，添加平台过滤
        if platforms:
            valid_platforms = set(self.get_platforms())
            if any(p not in valid_platforms for p in platforms):
                raise GlobalErrorCodeException(msg="平台参数不合法")
            conditions.append(KeywordSearchConfigTable.platform.in_(platforms))

        query = (
            select(KeywordSearchConfigTable)
            .where(and_(*conditions))
            .order_by(KeywordSearchConfigTable.created_at.desc())
        )

        result = await session.execute(query)
        items = result.scalars().all()
        return {"items": items}

    async def search_by_remark(
        self,
        session: AsyncSession,
        remark: str,
        platforms: List[str] = None,
    ) -> dict:
        """
        根据备注模糊查询配置

        Args:
            session: 数据库会话
            remark: 备注信息，支持模糊查询
            platforms: 平台列表，可选过滤条件

        Returns:
            dict: 包含查询结果的字典
        """
        if not remark or not remark.strip():
            raise GlobalErrorCodeException(msg="备注参数不能为空")

        conditions = [KeywordSearchConfigTable.remark.ilike(f"%{remark}%")]

        # 如果指定了平台，添加平台过滤
        if platforms:
            valid_platforms = set(self.get_platforms())
            if any(p not in valid_platforms for p in platforms):
                raise GlobalErrorCodeException(msg="平台参数不合法")
            conditions.append(KeywordSearchConfigTable.platform.in_(platforms))

        query = (
            select(KeywordSearchConfigTable)
            .where(and_(*conditions))
            .order_by(KeywordSearchConfigTable.created_at.desc())
        )

        result = await session.execute(query)
        items = result.scalars().all()
        return {"items": items}

    async def delete_keyword_by_ids(
            self,
            session: AsyncSession,
            ids: list[int]
    ) -> dict:
        """
        根据ID列表删除关键词配置，若ids为空则删除全表

        Args:
            session: 数据库会话
            ids: 关键词配置ID列表，为空时删除全表

        Returns:
            dict: 包含删除结果信息的字典

        Raises:
            GlobalErrorCodeException: 删除失败时抛出异常
        """
        try:
            if not ids:
                # 删除全表
                result = await session.execute(delete(KeywordSearchConfigTable))
                deleted_count = result.rowcount
                await session.commit()
                logger.info(f"成功删除全表关键词配置，共 {deleted_count} 条")
                return {"deleted_count": deleted_count,"message":"成功删除全表关键词配置"}
            else:
                # 按ID删除
                await session.execute(delete(KeywordSearchConfigTable).where(KeywordSearchConfigTable.id.in_(ids)))
                await session.commit()
                logger.info(f"成功删除 {len(ids)} 条关键词配置")
                return {"deleted_count": len(ids),"message":f"成功删除 {len(ids)} 条关键词配置"}
        except Exception as e:
            await session.rollback()
            logger.error(f"删除关键词配置失败: 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"删除关键词失败: {str(e)}")