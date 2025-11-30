from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi_utils.cbv import cbv

from src.api.base import BaseController
from src.core.db.db_database import get_db_dependency
from src.schemas.response_schema import ResponseSchema
from src.service.keyword import KeywordService

keyword_bp = APIRouter()


@cbv(keyword_bp)
class KeywordController(BaseController):
    """关键词配置相关接口"""

    keyword_service: KeywordService = Depends(KeywordService)

    @keyword_bp.get("/platforms", description="获取可选平台列表", response_model=ResponseSchema)
    async def get_platforms(self):
        """获取平台列表，用于前端多选"""
        platforms = self.keyword_service.get_platforms()
        return self.success(data=platforms)

    @keyword_bp.post("/infos", description="查询关键词配置", response_model=ResponseSchema)
    async def list_keyword_infos(
        self,
        platforms: List[str] = Query(["百度PC", "百度M"], description="平台列表，必须，可多选，默认百度PC+百度M"),
        keywords: Optional[List[str]] = Query(None, description="关键词列表，可多选，支持模糊查询"),
        remark: Optional[str] = Query(None, description="备注信息，支持模糊查询"),
        session=Depends(get_db_dependency),
    ):
        """按平台、关键词和备注查询配置"""
        if not platforms:
            return self.error("平台参数不能为空")

        # 去除空字符串和两端空格
        cleaned_platforms = [p.strip() for p in platforms if p and p.strip()]
        if not cleaned_platforms:
            return self.error("平台参数不能为空")

        cleaned_keywords: List[str] = []
        if keywords:
            cleaned_keywords = [k.strip() for k in keywords if k and k.strip()]

        cleaned_remark: Optional[str] = None
        if remark:
            cleaned_remark = remark.strip() if remark.strip() else None

        try:
            result = await self.keyword_service.get_keyword_infos(
                session=session,
                platforms=cleaned_platforms,
                keywords=cleaned_keywords if cleaned_keywords else None,
                remark=cleaned_remark,
            )
            return self.success(data=result)
        except Exception as e:
            return self.error(str(e))

    @keyword_bp.get("/search/keyword", description="根据关键词模糊查询", response_model=ResponseSchema)
    async def search_by_keyword(
        self,
        keywords: List[str] = Query(..., description="关键词列表，必须，可多选，支持模糊查询"),
        platforms: Optional[List[str]] = Query(None, description="平台列表，可选过滤条件"),
        session=Depends(get_db_dependency),
    ):
        """根据关键词模糊查询配置"""
        if not keywords:
            return self.error("关键词参数不能为空")

        # 清洗关键词
        cleaned_keywords = [k.strip() for k in keywords if k and k.strip()]
        if not cleaned_keywords:
            return self.error("关键词参数不能为空")

        # 清洗平台
        cleaned_platforms = None
        if platforms:
            cleaned_platforms = [p.strip() for p in platforms if p and p.strip()]
            if not cleaned_platforms:
                cleaned_platforms = None

        try:
            result = await self.keyword_service.search_by_keyword(
                session=session,
                keywords=cleaned_keywords,
                platforms=cleaned_platforms,
            )
            return self.success(data=result)
        except Exception as e:
            return self.error(str(e))

    @keyword_bp.get("/search/remark", description="根据备注模糊查询", response_model=ResponseSchema)
    async def search_by_remark(
        self,
        remark: str = Query(..., description="备注信息，必须，支持模糊查询"),
        platforms: Optional[List[str]] = Query(None, description="平台列表，可选过滤条件"),
        session=Depends(get_db_dependency),
    ):
        """根据备注模糊查询配置"""
        if not remark or not remark.strip():
            return self.error("备注参数不能为空")

        cleaned_remark = remark.strip()

        # 清洗平台
        cleaned_platforms = None
        if platforms:
            cleaned_platforms = [p.strip() for p in platforms if p and p.strip()]
            if not cleaned_platforms:
                cleaned_platforms = None

        try:
            result = await self.keyword_service.search_by_remark(
                session=session,
                remark=cleaned_remark,
                platforms=cleaned_platforms,
            )
            return self.success(data=result)
        except Exception as e:
            return self.error(str(e))

    @keyword_bp.delete("/", description="删除关键词")
    async def delete_keyword(
        self,
        ids: list[int],
        session=Depends(get_db_dependency)
    ):
        """批量删除 关键词配置"""
        try:
            result = await self.keyword_service.delete_keyword_by_ids(
                session=session,
                ids=ids
            )
            return self.success("删除域名成功", data=result)
        except Exception as e:
            return self.error(str(e))
