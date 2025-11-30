from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi_utils.cbv import cbv

from src.api.base import BaseController
from src.core.db.db_database import get_db_dependency
from src.models.domain_model import DomainTable
from src.schemas.site_schema import DomainCreateRequest, DomainListRequest, DomainSearchRequest, TestDataRequest
from src.service.site import SiteService

site_bp = APIRouter()


@cbv(site_bp)
class SiteController(BaseController):
    site_service: SiteService = Depends(SiteService)

    @site_bp.get("/get_filter_options", description="获取筛选选项")
    async def get_filter_options(self,
                                 type: Optional[str] = Query(None,
                                                             description="筛选类型，可选值：domain_group、server_number"),
                                 session=Depends(get_db_dependency)):
        """获取域名分组和服务器信息（去重）"""
        try:
            msg = '参数错误: 筛选类型错误'
            if type:
                if type == "domain_group":
                    result = await self.site_service.get_domain_groups(session=session)
                    msg = "获取域名分组成功"
                elif type == "server_number":
                    result = await self.site_service.get_server_numbers(session=session)
                    msg = "获取服务器信息成功"
                else:
                    result = None
                    self.error(msg)
                return self.success(msg, data=result)
        except Exception as e:
            return self.error(str(e))

    @site_bp.post("/list", description="获取域名列表")
    async def get_domain_list(
            self,
            page: int = Query(1, description="页码", ge=1),
            size: int = Query(10, description="每页大小", ge=1, le=100),
            domain_name: Optional[str] = Query(None, description="域名名称筛选"),
            domain_group: Optional[str] = Query(None, description="域名分组筛选"),
            server_number: Optional[str] = Query(None, description="服务器信息筛选"),
            main_domain: Optional[str] = Query(None, description="主域名筛选"),
            baidu_site_account: Optional[str] = Query(None, description="百度站平号筛选"),
            is_baidu_verified: Optional[bool] = Query(None, description="是否通过百度认证"),
            session=Depends(get_db_dependency)
    ):
        """获取域名列表（支持分页和多条件筛选）"""
        try:
            result = await self.site_service.get_domain_list(
                session=session,
                page=page,
                size=size,
                domain_name=domain_name,
                domain_group=domain_group,
                server_number=server_number,
                main_domain=main_domain,
                baidu_site_account=baidu_site_account,
                is_baidu_verified=is_baidu_verified
            )
            return self.success("获取域名列表成功", data=result)
        except Exception as e:
            return self.error(str(e))

    @site_bp.get("/{id}", description="根据ID获取域名详情")
    async def get_domain_by_id(
            self,
            id: int,
            session=Depends(get_db_dependency)
    ):
        """根据ID获取域名详情"""
        try:
            result = await self.site_service.get_domain_by_id(
                session=session,
                id=id
            )
            if result:
                return self.success("获取域名详情成功", data=result)
            else:
                return self.error("域名不存在")
        except Exception as e:
            return self.error(str(e))

    @site_bp.get("/group/{domain_group}", description="根据分组获取域名列表")
    async def get_domains_by_group(
            self,
            domain_group: str,
            page: int = Query(1, description="页码", ge=1),
            size: int = Query(10, description="每页大小", ge=1, le=100),
            session=Depends(get_db_dependency)
    ):
        """根据域名分组获取域名列表"""
        result = await self.site_service.get_domains_by_group(
            session=session,
            domain_group=domain_group,
            page=page,
            size=size
        )
        return self.success("获取分组域名列表成功", data=result)

    @site_bp.get("/search/{keyword}", description="模糊搜索域名")
    async def search_domains(
            self,
            keyword: str,
            page: int = Query(1, description="页码", ge=1),
            size: int = Query(10, description="每页大小", ge=1, le=100),
            session=Depends(get_db_dependency)
    ):
        """搜索域名（支持域名名称和主域名模糊搜索）"""
        try:
            result = await self.site_service.search_domains(
                session=session,
                keyword=keyword,
                page=page,
                size=size
            )
            return self.success("搜索域名成功", data=result)
        except Exception as e:
            return self.error(str(e))

    @site_bp.post("/create", description="创建域名")
    async def create_domain(
            self,
            request: DomainCreateRequest,
            session=Depends(get_db_dependency)
    ):
        """创建新的域名记录"""
        try:
            result = await self.site_service.create_domain(
                session=session,
                domain_name=request.domain_name,
                domain_group=request.domain_group,
                server_number=request.server_number,
                remark=request.remark
            )
            return self.success("创建域名成功", data=result)
        except Exception as e:
            return self.error(str(e))

    @site_bp.post("/test-data", description="插入测试数据")
    async def insert_test_data(
            self,
            request: TestDataRequest,
            session=Depends(get_db_dependency)
    ):
        """插入测试数据"""
        try:
            result = await self.site_service.insert_test_data(
                session=session,
                count=request.count
            )
            return self.success(f"成功插入 {request.count} 条测试数据", data=result)
        except Exception as e:
            return self.error(str(e))

    @site_bp.delete("/", description="删除域名")
    async def delete_domain(
            self,
            ids: list[int],
            session=Depends(get_db_dependency)
    ):
        """批量删除域名记录"""
        try:
            result = await self.site_service.delete_domain_by_ids(
                session=session,
                ids=ids
            )
            return self.success("删除域名成功", data=result)
        except Exception as e:
            return self.error(str(e))

    @site_bp.get("/demo/{id}", description="演示接口")
    async def demo(self, id: int):
        """保留的演示接口"""
        rest = []
        return self.success("演示", data=rest)
