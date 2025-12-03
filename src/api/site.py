from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi_utils.cbv import cbv
from src.schemas.site_schema import DomainMonitorQueryParams, AccountListRequest, TrendListRequest

from src.api.base import BaseController
from src.core.db.db_database import get_db_dependency
from src.schemas.keyword_schema import KeywordDeleteRequest, KeywordTestDataRequest, KeywordQueryParams
from src.schemas.response_schema import ResponseSchema
from src.schemas.site_schema import  DomainQueryParams, DomainMonitorPushRequest, \
    TrafficMonitorPushRequest, TrafficMonitorListRequest

from src.service.site import SiteService

site_bp = APIRouter()


@cbv(site_bp)
class SiteController(BaseController):
    site_service: SiteService = Depends(SiteService)

    @site_bp.post("/domain/list", description="获取域名列表")
    async def get_domain_list(
            self,
            query: DomainQueryParams = Query(..., description="查询参数"),
            session=Depends(get_db_dependency)
    ):
        """获取域名列表（支持分页和多条件筛选）"""

        result = await self.site_service.get_domain_list(
            session=session,
            query=query,
        )
        return self.success(data=result)



    @site_bp.delete("/domain", description="删除域名")
    async def delete_domain(
            self,
            ids: list[int],
            session=Depends(get_db_dependency)
    ):
        """批量删除域名记录"""

        result = await self.site_service.delete_domain_by_ids(
            session=session,
            ids=ids
        )
        return self.success()



    @site_bp.get("/domain_monitor/pull_task", description="域名监控任务派发")
    async def domain_monitor_pull_task(self):
        """任务派发"""
        result = await self.site_service.domain_monitor_pull_task()
        return self.success(data = result)

    @site_bp.post("/domain_monitor/push_task", description="域名监控任务结果存储")
    async def domain_monitor_push_task(
            self,
            params: DomainMonitorPushRequest,
    ):
        """域名结果存储"""
        await self.site_service.domain_monitor_push_task(params)
        return self.success()


    @site_bp.get("/traffic_monitor/pull_task", description="流量监控任务派发")
    async def traffic_monitor_pull_task(self):
        """流量任务派发"""
        result = await self.site_service.traffic_monitor_pull_task()
        return self.success(data = result)

    @site_bp.post("/traffic_monitor/push_task", description="流量监控任务结果存储")
    async def traffic_monitor_push_task(
            self,
            params: TrafficMonitorPushRequest,
    ):
        """流量结果存储"""
        await self.site_service.traffic_monitor_push_task(params)
        return self.success()

    @site_bp.post("/domain_monitor/list", description="查询域名监控列表", response_model=ResponseSchema)
    async def list_domain_monitors(
            self,
            params: DomainMonitorQueryParams,
            session=Depends(get_db_dependency),
    ):
        """
        查询域名监控列表

        支持以下查询条件：
        - 平台：必须，多选，默认为百度PC+百度M
        - 关键词：支持多选，支持模糊查询
        - 域名列表：支持多选，完全匹配
        - 是否自购域名：checkbox
        - 排名：范围查询
        - 执行时间：范围查询
        """
        result = await self.site_service.get_domain_monitor_list(
            session=session,
            params=params,
        )
        return self.success(data=result)



    @site_bp.get("/keyword/platforms", description="获取可选平台列表", response_model=ResponseSchema)
    async def get_platforms(self):
        """获取平台列表，用于前端多选"""
        platforms = self.site_service.get_platforms()
        return self.success(data=platforms)

    @site_bp.post("/keyword/list", description="查询关键词配置", response_model=ResponseSchema)
    async def list_keyword_infos(
            self,
            params: KeywordQueryParams = Depends(),
            session=Depends(get_db_dependency),
    ):
        """按平台、关键词和备注查询配置"""
        result = await self.site_service.get_keyword_infos(
            session=session,
            platforms=params.platforms,
            keywords=params.keywords,
            remark=params.remark,
        )
        return self.success(data=result)

    @site_bp.delete("/keyword", description="删除关键词")
    async def delete_keyword(
            self,
            request: KeywordDeleteRequest,
            session=Depends(get_db_dependency)
    ):
        """批量删除 关键词配置"""

        result = await self.site_service.delete_keyword_by_ids(
            session=session,
            ids=request.ids
        )
        return self.success("删除域名成功", data=result)



    @site_bp.post("/traffic_monitor/list", description="查询流量监控聚合数据", response_model=ResponseSchema)
    async def list_traffic_monitors(
            self,
            params: TrafficMonitorListRequest,
            session=Depends(get_db_dependency),
    ):

        result = await self.site_service.list_traffic_monitors(
            session=session,
            params=params,
        )
        data = result['items']
        total = result['pagination']['total']
        return self.paginated_response(data=data,total=total,current=params.page, size=params.size)



    @site_bp.post("/account/list", description="站平账号列表", response_model=ResponseSchema)
    async def list_accounts(
            self,
            params: AccountListRequest,
            session=Depends(get_db_dependency),
    ):

        result = await self.site_service.list_site_accounts(
            session=session,
            params=params,
        )
        data = result['items']
        total = result['pagination']['total']
        return self.paginated_response(data=data,total=total,current=params.page, size=params.size)

    @site_bp.post("/trend/list", description="趋势图数据", response_model=ResponseSchema)
    async def get_trend_chart(
            self,
            params: TrendListRequest,
            session=Depends(get_db_dependency),
    ):

        result = await self.site_service.get_trend_chart(
            session=session,
            params=params,
        )
        return self.success(data=result['data'])
