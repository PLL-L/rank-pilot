import asyncio
import random
import string
from datetime import datetime, timezone
from typing import Optional, List

from pandas import DataFrame
from sqlalchemy import select, and_, or_, delete, func, literal_column, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core import logger
from src.core.db.db_database import transactional
from src.core.exception.custom_exception import GlobalErrorCodeException
from src.models.site_domain_info import DomainInfoTable
from src.models.site_domain_monitor import DomainMonitorTable
from src.models.site_domain_info import  DomainInfoTable
from src.models.site_domain_monitor import SiteDomainMonitorTable
from src.models.site_keyword_info import KeywordInfoTable
from src.schemas.site_schema import DomainListRequest, DomainQueryParams
from src.service.base import BaseService
import pandas as pd


class SiteService(BaseService):
    """站点域名管理服务"""

    @staticmethod
    def extract_main_domain(domain: str) -> str:
        """
        从域名中提取主域名
        
        Args:
            domain: 完整域名
            
        Returns:
            str: 提取的主域名
            
        Examples:
            api.example.com -> example.com
            www.test.com -> test.com
            example.com -> example.com
        """
        try:
            # 去除首尾空格
            domain = domain.strip()
            # 简单的主域名提取逻辑
            # 例如：api.example.com -> example.com
            parts = domain.split('.')
            if len(parts) >= 2:
                # 取最后两个部分作为主域名
                return '.'.join(parts[-2:])
            return domain
        except Exception:
            return domain

    async def get_domain_list(
            self,
            session: AsyncSession,
            query: DomainQueryParams,
    ) -> dict:
        """
        获取域名列表（分页查询）

        Args:
            session: 数据库会话
            query: 查询参数对象

        Returns:
            dict: 包含域名列表和分页信息的字典

        Raises:
            GlobalErrorCodeException: 查询失败时抛出异常
        """
        try:
            # 参数验证
            if query.page < 1:
                raise GlobalErrorCodeException(msg="页码必须大于0")
            if query.size < 1 or query.size > 100:
                raise GlobalErrorCodeException(msg="每页大小必须在1-100之间")

            # 构建查询条件
            conditions = []

            if query.domain_name:
                conditions.append(DomainInfoTable.domain_name.ilike(f"%{query.domain_name}%"))

            if query.domain_group:
                conditions.append(DomainInfoTable.domain_group == query.domain_group)

            if query.server_info:
                conditions.append(DomainInfoTable.server_info == query.server_info)

            if query.main_domain:
                conditions.append(DomainInfoTable.main_domain.ilike(f"%{query.main_domain}%"))

            if query.baidu_site_account:
                conditions.append(DomainInfoTable.baidu_site_account.ilike(f"%{query.baidu_site_account}%"))

            if query.is_baidu_verified is not None:
                conditions.append(DomainInfoTable.is_baidu_verified == query.is_baidu_verified)

            # 构建基础查询
            base_query = select(DomainInfoTable)

            # 应用筛选条件
            if conditions:
                base_query = base_query.where(and_(*conditions))

            # 计算总数（优化：使用 count 直接计数）
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar_one()

            # 分页查询
            offset = (query.page - 1) * query.size
            final_query = base_query.order_by(DomainInfoTable.created_at.desc()).offset(offset).limit(query.size)

            result = await session.execute(final_query)
            domain_list = result.scalars().all()

            # 计算分页信息
            total_pages = (total_count + query.size - 1) // query.size
            has_next = query.page < total_pages
            has_prev = query.page > 1

            logger.info(f"查询域名列表成功: 页码={query.page}, 大小={query.size}, 总数={total_count}")

            return {
                "items": domain_list,
                "pagination": {
                    "page": query.page,
                    "size": query.size,
                    "total": total_count,
                    "pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }
        except Exception as e:
            logger.error(f"查询域名列表失败: {str(e)}")
            raise GlobalErrorCodeException(msg=f"查询域名列表失败: {str(e)}")

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

                # 使用服务层方法提取主域名
                main_domain = self.extract_main_domain(domain_name)

                domain = DomainInfoTable(
                    domain_name=domain_name,
                    main_domain=main_domain,
                    domain_group=random.choice(domain_groups),
                    server_info=random.choice(server_infos),
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

        except Exception as e:
            await session.rollback()
            logger.error(f"插入测试数据失败: 错误={str(e)}")

    async def get_all_groups(self, type: str, session: AsyncSession) -> list:
        """获取所有指定类型的分组信息（去重）

        Args:
            type: 分组类型，可选值：domain_group、server_number
            session: 数据库会话

        Returns:
            list: 去重后的分组列表
        """
        if type not in ["domain_group", "server_number"]:
            raise GlobalErrorCodeException(msg="分组类型错误")

        column = getattr(DomainInfoTable, type)
        query = select(column).distinct().where(column.isnot(None))
        result = await session.execute(query)
        groups = result.scalars().all()
        groups = [group for group in groups if group]
        logger.info(f"获取{type}成功，共 {len(groups)} 个分组")
        return groups

    async def delete_domain_by_ids(
            self,
            session: AsyncSession,
            ids: list[int]
    ) -> None:
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
                result = await session.execute(delete(DomainInfoTable))
                deleted_count = result.rowcount
                await session.commit()
                logger.info(f"成功删除全表域名记录，共 {deleted_count} 条")
            else:
                # 按ID删除
                await session.execute(delete(DomainInfoTable).where(DomainInfoTable.id.in_(ids)))
                await session.commit()
                logger.info(f"成功删除 {len(ids)} 条域名记录")
        except GlobalErrorCodeException:
            # 重新抛出业务异常
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"删除域名失败: 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"删除域名失败: {str(e)}")

    @transactional
    async def domain_monitor_pull_task(self, session: AsyncSession):
        """
        从数据库中拉取需要监控的域名任务
        1. 查找已到期或从未执行过的任务
        2. 使用悲观锁防止多个worker拉取到相同任务
        3. 每次拉取同一平台的最多5条任务
        4. 更新被拉取任务的 `last_monitored_at` 时间，防止被重复拉取

        Args:
            session: 数据库会话

        Returns:
            list[ DomainInfoTable]: 需要执行监控任务的域名对象列表
        """
        logger.info("开始拉取域名监控任务...")
        # 条件1：上次执行时间为null，或者 (上次执行时间 + 周期) < 当前时间
        utc_now = datetime.utcnow()
        condition1 = KeywordInfoTable.last_execute_time.is_(None)
        # 条件2: 已到期的任务
        # 核心逻辑：last_execute_time < now - (execute_cycle * 'minutes')::interval
        # 我们使用 func.cast 和 func.concat 来构造这个 interval
        condition2 = KeywordInfoTable.last_execute_time < (
                utc_now - (KeywordInfoTable.execute_cycle * text("INTERVAL '1 minute'"))
        )

        final_condition = or_(condition1, condition2)

        # 2. 查询并锁定任务
        stmt = select(
            KeywordInfoTable.platform,
            KeywordInfoTable.keyword,
            KeywordInfoTable.city,
            KeywordInfoTable.id,
            KeywordInfoTable.last_execute_time
        ).where(
            final_condition
        ).limit(5).with_for_update(skip_locked=True)

        result = await session.execute(stmt)
        tasks_to_run = result.mappings().all()

        if not tasks_to_run:
            logger.info("没有需要执行的域名监控任务")
            return []

        # 将Row对象列表转换为字典列表
        tasks_as_dicts = [dict(row) for row in tasks_to_run]

        return tasks_as_dicts

    @transactional
    async def domain_monitor_push_task(self, params, session: AsyncSession):
        file_url = params.file_url or "/Users/echo/Downloads/task1-group-0.csv"
        file_name = params.file_name or "task1-group-0.csv"

        # domain_query = select(
        #     DomainInfoTable.domain_name,
        #     DomainInfoTable.domain_group
        # )
        # domain_info = await session.execute(domain_query)
        # domain_info_list = domain_info.all()

        record_df: DataFrame = await asyncio.to_thread(pd.read_csv, file_url, encoding='utf-8')
        domains_to_insert = []
        record_df.fillna('', inplace=True)
        for key, val in record_df.iterrows():
            if not val.get("keyword"):
                continue
            domain = DomainMonitorTable(
                keyword=val.get("keyword"),
                platform=val.get("platform"),  # 转换大写
                city=val.get("city"),
                is_buy_domain=True,
                domain_name=val.get("domain_name"),
                domain_group="12",
                real_url=val.get("real_url"),
                title=val.get("title"),
                rank=val.get("rank"),
                # created_at=datetime.utcnow(),
                # updated_at = datetime.utcnow(),
                created_uid=1,
                updated_uid=1

            )
            domains_to_insert.append(domain)
            break

        session.add_all(domains_to_insert)

        await session.commit()

    ########################### 关键词
    @staticmethod
    def get_platforms() -> List[str]:
        """返回可选平台列表（用于前端多选）"""
        return ["BAIDU_PC", "BAIDU_M", "360PC", "360M"]

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

        # 去除空字符串和两端空格
        cleaned_platforms = [p.strip() for p in platforms if p and p.strip()]
        if not cleaned_platforms:
            raise GlobalErrorCodeException(msg="平台参数不能为空")

        valid_platforms = set(self.get_platforms())
        if any(p not in valid_platforms for p in cleaned_platforms):
            raise GlobalErrorCodeException(msg="平台参数不合法")

        conditions = [ KeywordInfoTable.platform.in_(cleaned_platforms)]

        # 处理关键词参数
        cleaned_keywords: List[str] = []
        if keywords:
            cleaned_keywords = [k.strip() for k in keywords if k and k.strip()]
            if cleaned_keywords:
                # 关键词模糊多选，OR 组合
                keyword_conditions = [
                     KeywordInfoTable.keyword.ilike(f"%{k}%") for k in cleaned_keywords
                ]
                conditions.append(or_(*keyword_conditions))
        # 处理备注参数
        if remark:
            cleaned_remark = remark.strip() if remark.strip() else None
            if cleaned_remark:
                # 备注模糊查询
                conditions.append( KeywordInfoTable.remark.ilike(f"%{cleaned_remark}%"))

        query = (
            select( KeywordInfoTable)
            .where(and_(*conditions))
            .order_by( KeywordInfoTable.created_at.desc())
        )

        result = await session.execute(query)
        items = result.scalars().all()
        return {"items": items}

    async def batch_create_keyword_test_data(
            self,
            session: AsyncSession,
            count: int = 10,
            created_uid: Optional[int] = None
    ) -> dict:
        """
        批量创建测试数据

        Args:
            session: 数据库会话
            count: 要创建的测试数据数量，默认10条
            created_uid: 创建人ID，可选

        Returns:
            dict: 包含创建结果的字典，包括成功数量和创建的数据列表

        Raises:
            GlobalErrorCodeException: 创建失败时抛出异常
        """
        try:
            # 验证数量范围
            if count <= 0:
                raise GlobalErrorCodeException(msg="创建数量必须大于0")
            if count > 1000:
                raise GlobalErrorCodeException(msg="单次批量创建数量不能超过1000条")

            platforms = self.get_platforms()
            cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", None]
            keywords_templates = [
                "测试关键词", "Python开发", "数据分析", "机器学习",
                "Web开发", "API接口", "数据库优化", "性能测试"
            ]
            remarks = ["测试数据", "自动生成", "批量导入", "压力测试", None]

            created_items = []
            for i in range(count):
                # 循环使用模板数据，创建多样化的测试数据
                keyword_config =  KeywordInfoTable(
                    keyword=f"{keywords_templates[i % len(keywords_templates)]}_{i+1}",
                    platform=platforms[i % len(platforms)],
                    city=cities[i % len(cities)],
                    mobile_search_depth=(i % 10 + 1) * 10 if i % 2 == 0 else None,
                    pc_search_depth=(i % 10 + 1) * 20 if i % 2 == 1 else None,
                    execute_cycle=float((i % 24) + 1),  # 1-24小时循环
                    remark=f"{remarks[i % len(remarks)] or '测试'}_{i+1}",
                    last_execute_time=None,
                    created_uid=created_uid,
                    updated_uid=created_uid
                )
                session.add(keyword_config)
                created_items.append(keyword_config)

            await session.commit()

            # 刷新数据以获取自动生成的ID和时间戳
            for item in created_items:
                await session.refresh(item)

            logger.info(f"成功批量创建 {count} 条测试数据")

            return {
                "created_count": count,
                "message": f"成功批量创建 {count} 条测试数据",
                "items": created_items
            }
        except Exception as e:
            await session.rollback()
            logger.error(f"批量创建测试数据失败: 错误={str(e)}")
    # 域名监控
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
                result = await session.execute(delete(KeywordInfoTable))
                deleted_count = result.rowcount
                await session.commit()
                logger.info(f"成功删除全表关键词配置，共 {deleted_count} 条")
                return {"deleted_count": deleted_count,"message":"成功删除全表关键词配置"}
            else:
                # 按ID删除
                await session.execute(delete( KeywordInfoTable).where( KeywordInfoTable.id.in_(ids)))
                await session.commit()
                logger.info(f"成功删除 {len(ids)} 条关键词配置")
                return {"deleted_count": len(ids),"message":f"成功删除 {len(ids)} 条关键词配置"}
        except Exception as e:
            await session.rollback()
            logger.error(f"删除关键词配置失败: 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"删除关键词失败: {str(e)}")

    ####### 域名监控
    async def get_domain_monitor_list(
            self,
            session: AsyncSession,
            platforms: List[str],
            keywords: Optional[List[str]] = None,
            domain_names: Optional[List[str]] = None,
            is_buy_domain: Optional[bool] = None,
            rank_range: Optional[tuple[int, int]] = None,
            created_at_range: Optional[tuple[datetime, datetime]] = None,
    ) -> dict:
        """根据多个条件查询域名监控数据

        Args:
            session: 数据库会话
            platforms: 平台列表，必须，多选，默认百度PC+百度M
            keywords: 关键词列表，可选，多选，支持模糊查询
            domain_names: 域名列表，可选，多选，完全匹配
            is_buy_domain: 是否自购域名，可选
            rank_range: 排名范围，可选，(min, max)
            created_at_range: 执行时间范围，可选，(start, end)

        Returns:
            dict: 包含查询结果的字典
        """
        # 数据清洗和验证
        if not platforms:
            raise GlobalErrorCodeException(msg="平台参数不能为空")

        # 去除空字符串和两端空格
        cleaned_platforms = [p.strip() for p in platforms if p and p.strip()]
        if not cleaned_platforms:
            raise GlobalErrorCodeException(msg="平台参数不能为空")

        valid_platforms = set(self.get_platforms())
        if any(p not in valid_platforms for p in cleaned_platforms):
            raise GlobalErrorCodeException(msg="平台参数不合法")

        conditions = [SiteDomainMonitorTable.platform.in_(cleaned_platforms)]

        # 处理关键词参数 - 支持多选模糊查询
        if keywords:
            cleaned_keywords = [k.strip() for k in keywords if k and k.strip()]
            if cleaned_keywords:
                # 关键词模糊多选，OR 组合
                keyword_conditions = [
                    SiteDomainMonitorTable.keyword.ilike(f"%{k}%") for k in cleaned_keywords
                ]
                conditions.append(or_(*keyword_conditions))

        # 处理域名参数 - 支持多选完全匹配
        if domain_names:
            cleaned_domain_names = [d.strip() for d in domain_names if d and d.strip()]
            if cleaned_domain_names:
                conditions.append(SiteDomainMonitorTable.domain_name.in_(cleaned_domain_names))

        # 处理是否自购域名参数
        if is_buy_domain is not None:
            conditions.append(SiteDomainMonitorTable.is_buy_domain == is_buy_domain)

        # 处理排名范围查询
        if rank_range is not None:
            min_rank, max_rank = rank_range
            if min_rank is not None:
                conditions.append(SiteDomainMonitorTable.rank >= min_rank)
            if max_rank is not None:
                conditions.append(SiteDomainMonitorTable.rank <= max_rank)

        # 处理执行时间范围查询
        if created_at_range is not None:
            start_at, end_at = created_at_range
            if start_at is not None:
                conditions.append(SiteDomainMonitorTable.created_at >= start_at)
            if end_at is not None:
                conditions.append(SiteDomainMonitorTable.created_at <= end_at)

        query = (
            select(SiteDomainMonitorTable)
            .where(and_(*conditions))
            .order_by(SiteDomainMonitorTable.created_at.desc())
        )

        result = await session.execute(query)
        items = result.scalars().all()
        return {"items": items}

    async def batch_create_domain_monitor_test_data(
            self,
            session: AsyncSession,
            count: int = 10,
            created_uid: Optional[int] = None
    ) -> dict:
        """
        批量创建测试数据

        Args:
            session: 数据库会话
            count: 要创建的测试数据数量，默认10条
            created_uid: 创建人ID，可选

        Returns:
            dict: 包含创建结果的字典，包括成功数量和创建的数据列表

        Raises:
            GlobalErrorCodeException: 创建失败时抛出异常
        """
        try:
            # 验证数量范围
            if count <= 0:
                raise GlobalErrorCodeException(msg="创建数量必须大于0")
            if count > 1000:
                raise GlobalErrorCodeException(msg="单次批量创建数量不能超过1000条")

            platforms = self.get_platforms()
            cities = ["北京", "上海", "广州", "深圳", "杭州", "成都"]
            keywords_templates = [
                "SEO优化", "关键词排名", "网站推广", "品牌营销",
                "流量获取", "搜索优化", "排名监控", "网站优化"
            ]
            domain_templates = [
                "example.com", "test-domain.cn", "demo-site.com",
                "sample-web.net", "monitor-test.com", "rank-check.cn"
            ]
            domain_groups = ["A组", "B组", "C组", "测试组", "线上组"]
            titles = ["测试标题", "SEO优化方案", "关键词排名监控", "网站流量分析", "品牌推广"]

            created_items = []
            now = datetime.now(timezone.utc)

            for i in range(count):
                # 循环使用模板数据，创建多样化的测试数据
                uid = created_uid if created_uid is not None else 1000 + (i % 10)

                monitor_data = SiteDomainMonitorTable(
                    keyword=f"{keywords_templates[i % len(keywords_templates)]}_{i + 1}",
                    platform=platforms[i % len(platforms)],
                    city=cities[i % len(cities)],
                    is_buy_domain=i % 3 == 0,  # 每3条有1条是自购域名
                    domain_name=f"{domain_templates[i % len(domain_templates)]}" if i % 2 == 0 else None,
                    domain_group=domain_groups[i % len(domain_groups)] if i % 2 == 0 else None,
                    real_url=f"https://{domain_templates[i % len(domain_templates)]}/page{i + 1}" if i % 2 == 0 else None,
                    title=f"{titles[i % len(titles)]}_{i + 1}" if i % 2 == 0 else None,
                    rank=(i % 100) + 1 if i % 3 != 0 else None,  # 排名1-100，部分为空
                    created_at=now,
                    updated_at=now,
                    created_uid=uid,
                    updated_uid=uid
                )
                session.add(monitor_data)
                created_items.append(monitor_data)

            await session.commit()

            # 刷新数据以获取自动生成的ID和时间戳
            for item in created_items:
                await session.refresh(item)

            logger.info(f"成功批量创建 {count} 条域名监控测试数据")

            return {
                "created_count": count,
                "message": f"成功批量创建 {count} 条测试数据",
                "items": created_items
            }
        except Exception as e:
            await session.rollback()
            logger.error(f"批量创建域名监控测试数据失败: 错误={str(e)}")
            raise GlobalErrorCodeException(msg=f"批量创建测试数据失败: {str(e)}")
