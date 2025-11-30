import random
import string
from typing import Optional

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core import logger
from src.core.db.db_database import transactional
from src.core.exception.custom_exception import GlobalErrorCodeException
from src.models.domain_model import DomainTable
from src.service.base import BaseService


class SiteService(BaseService):
    """站点域名管理服务"""

    @transactional
    async def get_domain_list(
        self,
        session: AsyncSession,
        page: int = 1,
        size: int = 10,
        domain_name: Optional[str] = None,
        domain_group: Optional[str] = None,
        server_number: Optional[str] = None,
        main_domain: Optional[str] = None,
        baidu_site_account: Optional[str] = None,
        is_baidu_verified: Optional[bool] = None
    ) -> dict:
        """
        获取域名列表（分页查询）

        Args:
            session: 数据库会话
            page: 页码，默认为1
            size: 每页大小，默认为10
            domain_name: 域名名称筛选（模糊查询）
            domain_group: 域名分组筛选
            server_number: 服务器ID筛选
            main_domain: 主域名筛选（模糊查询）
            baidu_site_account: 百度站平号筛选（模糊查询）
            is_baidu_verified: 是否通过百度认证

        Returns:
            dict: 包含域名列表和分页信息的字典

        Raises:
            GlobalErrorCodeException: 查询失败时抛出异常
        """
        try:
            # 参数验证
            if page < 1:
                raise GlobalErrorCodeException(msg="页码必须大于0")
            if size < 1 or size > 100:
                raise GlobalErrorCodeException(msg="每页大小必须在1-100之间")

            # 构建查询条件
            conditions = []

            if domain_name:
                conditions.append(DomainTable.domain_name.ilike(f"%{domain_name}%"))

            if domain_group:
                conditions.append(DomainTable.domain_group == domain_group)

            if server_number:
                conditions.append(DomainTable.server_number == server_number)

            if main_domain:
                conditions.append(DomainTable.main_domain.ilike(f"%{main_domain}%"))

            if baidu_site_account:
                conditions.append(DomainTable.baidu_site_account.ilike(f"%{baidu_site_account}%"))

            if is_baidu_verified is not None:
                conditions.append(DomainTable.is_baidu_verified == is_baidu_verified)

            # 构建基础查询
            base_query = select(DomainTable)

            # 应用筛选条件
            if conditions:
                base_query = base_query.where(and_(*conditions))

            # 计算总数
            count_query = select(DomainTable.id)
            if conditions:
                count_query = count_query.where(and_(*conditions))

            total_result = await session.execute(count_query)
            total_count = len(total_result.scalars().all())

            # 分页查询
            offset = (page - 1) * size
            query = base_query.order_by(DomainTable.created_at.desc()).offset(offset).limit(size)

            result = await session.execute(query)
            domain_list = result.scalars().all()

            # 计算分页信息
            total_pages = (total_count + size - 1) // size
            has_next = page < total_pages
            has_prev = page > 1

            logger.info(f"查询域名列表成功: 页码={page}, 大小={size}, 总数={total_count}")

            return {
                "items": domain_list,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total_count,
                    "pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }

        except GlobalErrorCodeException:
            # 重新抛出业务异常
            raise
        except Exception as e:
            logger.error(f"查询域名列表失败: {str(e)}")
            raise GlobalErrorCodeException(msg=f"查询域名列表失败: {str(e)}")

    @transactional
    async def get_domain_by_id(
        self,
        session: AsyncSession,
        id: int
    ) -> Optional[DomainTable]:
        """
        根据ID获取域名详情

        Args:
            session: 数据库会话
            id: 主键自增ID

        Returns:
            Optional[DomainTable]: 域名信息，不存在时返回None

        Raises:
            GlobalErrorCodeException: 查询失败时抛出异常
        """
        try:
            if not id:
                raise GlobalErrorCodeException(msg="域名ID不能为空")

            result = await session.get(DomainTable, id)

            if result:
                logger.info(f"查询域名详情成功: ID={id}")
            else:
                logger.warning(f"域名不存在: ID={id}")
            return result

        except Exception as e:

            logger.error(f"查询域名详情失败: ID={id}, 错误={str(e)}")
            raise GlobalErrorCodeException(msg="ID不能为空")

    @transactional
    async def get_domains_by_group(
        self,
        session: AsyncSession,
        domain_group: str,
        page: int = 1,
        size: int = 10
    ) -> dict:
        """
        根据域名分组获取域名列表

        Args:
            session: 数据库会话
            domain_group: 域名分组
            page: 页码，默认为1
            size: 每页大小，默认为10

        Returns:
            dict: 包含域名列表和分页信息的字典

        Raises:
            GlobalErrorCodeException: 查询失败时抛出异常
        """
        try:
            if not domain_group:
                raise GlobalErrorCodeException(msg="域名分组不能为空")

            # 调用通用列表查询方法
            return await self.get_domain_list(
                session=session,
                page=page,
                size=size,
                domain_group=domain_group
            )

        except GlobalErrorCodeException:
            # 重新抛出业务异常
            raise
        except Exception as e:
            logger.error(f"根据分组查询域名失败: 分组={domain_group}, 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"根据分组查询域名失败: {str(e)}")

    @transactional
    async def search_domains(
        self,
        session: AsyncSession,
        keyword: str,
        page: int = 1,
        size: int = 10
    ) -> dict:
        """
        搜索域名（支持域名名称和主域名模糊搜索）

        Args:
            session: 数据库会话
            keyword: 搜索关键词
            page: 页码，默认为1
            size: 每页大小，默认为10

        Returns:
            dict: 包含域名列表和分页信息的字典

        Raises:
            GlobalErrorCodeException: 搜索失败时抛出异常
        """
        try:
            if not keyword or not keyword.strip():
                raise GlobalErrorCodeException(msg="搜索关键词不能为空")

            keyword = keyword.strip()

            # 构建搜索条件（域名名称或主域名包含关键词）
            search_conditions = or_(
                DomainTable.domain_name.ilike(f"%{keyword}%"),
                DomainTable.main_domain.ilike(f"%{keyword}%")
            )

            # 构建查询
            base_query = select(DomainTable).where(search_conditions)
            count_query = select(DomainTable.id).where(search_conditions)

            # 计算总数
            total_result = await session.execute(count_query)
            total_count = len(total_result.scalars().all())

            # 分页查询
            offset = (page - 1) * size
            query = base_query.order_by(DomainTable.created_at.desc()).offset(offset).limit(size)

            result = await session.execute(query)
            domain_list = result.scalars().all()

            # 计算分页信息
            total_pages = (total_count + size - 1) // size
            has_next = page < total_pages
            has_prev = page > 1

            logger.info(f"搜索域名成功: 关键词={keyword}, 页码={page}, 大小={size}, 总数={total_count}")

            return {
                "items": domain_list,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total_count,
                    "pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }

        except GlobalErrorCodeException:
            # 重新抛出业务异常
            raise


    @transactional
    async def create_domain(
        self,
        session: AsyncSession,
        domain_name: str,
        domain_group: Optional[str] = None,
        server_number: Optional[str] = None,
        remark: Optional[str] = None
    ) -> DomainTable:
        """
        创建新的域名记录

        Args:
            session: 数据库会话
            domain_name: 域名名称
            domain_group: 域名分组，可选
            server_number: 服务器ID，可选
            remark: 备注信息，可选

        Returns:
            DomainTable: 创建的域名信息

        Raises:
            GlobalErrorCodeException: 创建失败时抛出异常
        """
        try:
            if not domain_name or not domain_name.strip():
                raise GlobalErrorCodeException(msg="域名名称不能为空")

            # 创建域名对象（会自动验证和计算主域名）
            domain = DomainTable(
                domain_name=domain_name.strip(),
                domain_group=domain_group.strip() if domain_group else None,
                server_number=server_number.strip() if server_number else None,
                remark=remark.strip() if remark else None
            )

            # 保存到数据库
            session.add(domain)
            await session.commit()
            await session.refresh(domain)

            logger.info(f"创建域名成功: ID={domain.id}, 域名={domain.domain_name}")
            return domain

        except GlobalErrorCodeException:
            # 重新抛出业务异常
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"创建域名失败: 域名={domain_name}, 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"创建域名失败: {str(e)}")

    @transactional
    async def insert_test_data(
        self,
        session: AsyncSession,
        count: int
    ) -> dict:
        """
        插入测试数据

        Args:
            session: 数据库会话
            count: 要插入的测试数据数量

        Returns:
            dict: 包含插入结果信息的字典

        Raises:
            GlobalErrorCodeException: 插入失败时抛出异常
        """
        try:
            import random
            import string

            if count <= 0:
                raise GlobalErrorCodeException(msg="插入数量必须大于0")

            if count > 1000:
                raise GlobalErrorCodeException(msg="单次插入数量不能超过1000条")

            # 测试数据模板
            test_domains = [
                "api.example.com",
                "www.test.com",
                "admin.production.com",
                "dev.staging.com",
                "blog.website.com",
                "shop.ecommerce.com",
                "mail.service.com",
                "cdn.content.com",
                "api.v2.com",
                "mobile.app.com"
            ]

            domain_groups = ["production", "development", "testing", "staging"]
            server_infos = ["server-01", "server-02", "server-03", "server-04"]
            remarks = [
                "主要API服务器",
                "测试环境域名",
                "生产环境域名",
                "备用服务器",
                "CDN加速域名",
                "移动端接口",
                "管理后台",
                "用户门户"
            ]
            created_uid = 123  # 假设创建者ID为123
            updated_uid = 123  # 假设更新者ID为123

            inserted_domains = []

            for i in range(count):
                # 随机选择测试数据
                domain_name = random.choice(test_domains)
                # 添加随机后缀避免重复
                random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                domain_name = f"{random_suffix}.{domain_name}"

                domain = DomainTable(
                    domain_name=domain_name,
                    domain_group=random.choice(domain_groups),
                    server_number=random.choice(server_infos),
                    remark=random.choice(remarks),
                    created_uid=created_uid,
                    updated_uid=updated_uid
                )

                session.add(domain)
                inserted_domains.append(domain)

            # 批量提交
            await session.commit()

            logger.info(f"成功插入 {count} 条测试数据")
            return {
                "count": count,
                "domains": [{"id": d.id, "domain_name": d.domain_name} for d in inserted_domains]
            }

        except GlobalErrorCodeException:
            # 重新抛出业务异常
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"插入测试数据失败: 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"插入测试数据失败: {str(e)}")


    @transactional
    async def delete_domain_by_ids(
            self,
            session: AsyncSession,
            ids: list[int]
    ) -> dict:
        """
        根据ID列表删除域名记录，若ids为空则删除全表

        Args:
            session: 数据库会话
            ids: 域名ID列表，为空时删除全表

        Returns:
            dict: 包含删除结果信息的字典

        Raises:
            GlobalErrorCodeException: 删除失败时抛出异常
        """
        try:
            if not ids:
                # 删除全表
                result = await session.execute(delete(DomainTable))
                deleted_count = result.rowcount
                await session.commit()
                logger.info(f"成功删除全表域名记录，共 {deleted_count} 条")
                return {"deleted_count": deleted_count,"message":"成功删除全表域名记录"}
            else:
                # 按ID删除
                await session.execute(delete(DomainTable).where(DomainTable.id.in_(ids)))
                await session.commit()
                logger.info(f"成功删除 {len(ids)} 条域名记录")
                return {"deleted_count": len(ids),"message":f"成功删除 {len(ids)} 条域名记录"}
        except GlobalErrorCodeException:
            # 重新抛出业务异常
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"删除域名失败: 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"删除域名失败: {str(e)}")

    @transactional
    async def get_domain_groups(self, session: AsyncSession) -> list:
        """
        获取所有域名分组信息（去重）

        Args:
            session: 数据库会话

        Returns:
            list: 去重后的域名分组列表

        Raises:
            GlobalErrorCodeException: 查询失败时抛出异常
        """
        try:
            # 查询所有非空的域名分组，使用distinct去重
            query = select(DomainTable.domain_group).distinct().where(DomainTable.domain_group.isnot(None))
            result = await session.execute(query)
            groups = result.scalars().all()

            # 过滤掉None值并转为列表
            groups = [group for group in groups if group]

            logger.info(f"获取域名分组成功，共 {len(groups)} 个分组")
            return groups

        except Exception as e:
            logger.error(f"获取域名分组失败: 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"获取域名分组失败: {str(e)}")


    @transactional
    async def get_server_numbers(self, session: AsyncSession) -> list:
        """
        获取所有服务器信息（去重）

        Args:
            session: 数据库会话

        Returns:
            list: 去重后的服务器信息列表

        Raises:
            GlobalErrorCodeException: 查询失败时抛出异常
        """
        try:
            # 查询所有非空的服务器信息，使用distinct去重
            query = select(DomainTable.server_number).distinct().where(DomainTable.server_number.isnot(None))
            result = await session.execute(query)
            servers = result.scalars().all()

            # 过滤掉None值并转为列表
            servers = [server for server in servers if server]

            logger.info(f"获取服务器信息成功，共 {len(servers)} 个服务器")
            return servers

        except Exception as e:
            logger.error(f"获取服务器信息失败: 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"获取服务器信息失败: {str(e)}")