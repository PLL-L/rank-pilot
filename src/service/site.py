import asyncio
import decimal
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List

import pandas as pd
from pandas import DataFrame
from sqlalchemy import select, update, and_, or_, delete, func, text, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Numeric
from src.core import logger
from src.core.db.db_database import transactional
from src.core.exception.custom_exception import GlobalErrorCodeException, ParamsErrorCodeException
from src.models.site_domain_info import DomainInfoTable
from src.models.site_domain_monitor import DomainMonitorTable
from src.models.site_keyword_info import KeywordInfoTable
from src.models.site_platform_account import PlatformAccountTable
from src.models.site_traffic_monitor import TrafficMonitorTable
from src.models.site_traffic_monitor_chart import TrafficMonitorChartTable
from src.schemas.site_schema import DomainQueryParams, DomainMonitorPushRequest, \
    TrafficMonitorPushRequest, TrafficMonitorListRequest, DomainMonitorQueryParams, AccountListRequest, TrendListRequest
from src.service.base import BaseService
from src.utils.async_function import run_bulk_update_sync
from src.utils.tools import Tools


class SiteService(BaseService):
    """站点域名管理服务"""


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
        if not ids:
            # 删除全表
            await session.execute(delete(DomainInfoTable))
        else:
            # 按ID删除
            await session.execute(delete(DomainInfoTable).where(DomainInfoTable.id.in_(ids)))
        await session.commit()


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
            KeywordInfoTable.pc_search_depth,
            KeywordInfoTable.mobile_search_depth,
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
    async def domain_monitor_push_task(self, params: DomainMonitorPushRequest, session: AsyncSession):
        file_url = params.file_url or "/Users/echo/Downloads/task1-group-0.csv"
        file_name = params.file_name or "task1-group-0.csv"
        job_ids = params.job_id_list

        upd_record = update(
            KeywordInfoTable
        ).where(
            KeywordInfoTable.id.in_(job_ids)
        ).values(
            last_execute_time=datetime.utcnow()
        )
        await session.execute(upd_record)

        domain_query = select(
            DomainInfoTable.domain_name,
            DomainInfoTable.domain_group,
            DomainInfoTable.created_at
        )
        domain_info = await session.execute(domain_query)
        domain_info_list = domain_info.mappings().all()
        db_domain_info_dict = {val.domain_name: val.domain_group for val in domain_info_list}

        record_df: DataFrame = await asyncio.to_thread(pd.read_csv, file_url, encoding='utf-8')
        record_df = record_df.astype(str).fillna('')

        domains_to_insert = []
        for key, val in record_df.iterrows():
            domain_name = val.get("real_domain")
            db_domain_info = db_domain_info_dict.get(domain_name)
            domain = DomainMonitorTable(
                keyword=val.get("keyword"),
                platform=val.get("platform"),  # 转换大写
                city=val.get("city"),
                is_buy_domain=True if db_domain_info else False,
                domain_name=domain_name,
                domain_group=db_domain_info,
                real_url=val.get("real_url"),
                title=val.get("title"),
                rank=int(float(val.get("rank"))),

            )
            domains_to_insert.append(domain)

        session.add_all(domains_to_insert)

        await session.commit()

    @transactional
    async def traffic_monitor_pull_task(self, session: AsyncSession):
        """
        从数据库中拉取需要执行流量监控的站平账号任务
        1. 查找已到期或从未执行过的账号
        2. 使用数据库悲观锁防止多个worker并发拉取到相同任务
        3. 每次只拉取一个任务
        4. 更新被拉取任务的 `last_check_time` 时间，防止被重复拉取
        """
        logger.info("开始拉取流量监控任务...")

        # 1. 构建查询条件
        # 条件：上次检查时间为null，或者 (当前时间 - 上次检查时间 > 1 小时)
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        due_condition = or_(
            PlatformAccountTable.last_check_time.is_(None),
            PlatformAccountTable.last_check_time < one_hour_ago
        )

        # 2. 查询并使用悲观锁锁定任务
        account_query = select(
            PlatformAccountTable.id,
            PlatformAccountTable.account_number,
            PlatformAccountTable.password,
            PlatformAccountTable.domain_list
        ).where(
            due_condition
        ).order_by(
            PlatformAccountTable.last_check_time.nulls_first().asc()
        ).limit(1).with_for_update(skip_locked=True)

        account_info = await session.execute(account_query)
        task_to_run = account_info.scalar_one_or_none()

        if not task_to_run:
            logger.info("没有需要执行的流量监控任务")
            return []

        logger.info(f"成功拉取到流量监控任务，账号ID: {task_to_run.id}, 用户名: {task_to_run.account_number}")

        return task_to_run

    @transactional
    async def traffic_monitor_push_task(self, params: TrafficMonitorPushRequest, session: AsyncSession):
        account_info = params.account_info
        account_number = account_info.account_number
        account_status = account_info.account_status
        cookie = account_info.cookie
        domain_list = account_info.domain_list
        managed_domain_count = account_info.managed_domain_count

        domain_info_list = params.domain_info_list

        file_info = params.file_info

        # 修改站平账号信息
        account_res = update(
            PlatformAccountTable
        ).where(
            PlatformAccountTable.account_number == account_number
        ).values(
            status=account_status,
            cookie=cookie,
            domain_list=domain_list,
            managed_domain_count=managed_domain_count,
            last_check_time=datetime.utcnow(),
            updated_at = datetime.utcnow()
        )
        await session.execute(account_res)

        domain_ids_query = select(
            DomainInfoTable.id,
            DomainInfoTable.domain_name
        ).where(
            DomainInfoTable.domain_name.in_(domain_list)
        )
        domain_query = await session.execute(domain_ids_query)
        domain_ids = {val.domain_name: val.id for val in domain_query.all()}

        upd_domain_info_list = []
        for val in domain_info_list:
            domain_name = val.domain_name
            push_token = val.push_token
            is_verified = val.is_verified
            account_number = val.account_number
            domain_id = domain_ids.get(domain_name)

            if not domain_id:
                continue

            upd_domain_info_list.append({
                "id": domain_id,
                "is_verified": is_verified,
                "push_token": push_token,
                "account_number": account_number,
                "updated_at": datetime.utcnow()
            })

        # 使用 session.run_sync() 来调用同步的 bulk_update_mappings 方法
        # 批量修改域名关联的账号信息
        await session.run_sync(
            # 传入：同步方法本身, 模型类, 数据列表
            run_bulk_update_sync,
            DomainInfoTable,
            upd_domain_info_list
        )

        # 插入流量监控数据
        keyword_page_df, chart_df  = await asyncio.gather(
            asyncio.to_thread(pd.read_csv, file_info.keyword_page),
            asyncio.to_thread(pd.read_csv, file_info.chart),

        )


        chart_to_insert = []
        keyword_page_to_insert = []

        if not chart_df.empty:
            chart_df = chart_df.fillna('').astype(str)
            for _, val in chart_df.iterrows():
                item = TrafficMonitorChartTable(
                    clicks=int(val.get("click") or 0),
                    impressions=int(val.get("display") or 0),
                    domain_name=val.get("domain"),
                    hour_info=val.get("info"),
                    terminal_type=val.get("terminal"),
                )
                chart_to_insert.append(item)
        
        if not keyword_page_df.empty:
            keyword_page_df = keyword_page_df.fillna('').astype(str)
            keyword_page_df['rank'] = keyword_page_df['rank'].apply(Decimal)
            keyword_page_df['ctr'] = keyword_page_df['ctr'].apply(Decimal)

            for _, val in keyword_page_df.iterrows():
                item = TrafficMonitorTable(
                    clicks=int(val.get("click")),
                    impressions=int(val.get("display")),
                    domain_name=val.get("domain"),
                    ctr=val.get("ctr"),
                    terminal_type=val.get("terminal"),
                    rank=val.get("rank"),
                    business_type=val.get("type"),
                    keyword = val.get("keyword"),
                    page= val.get("page")
                )
                keyword_page_to_insert.append(item)



        session.add_all(chart_to_insert) # 批量添加 趋势图
        session.add_all(keyword_page_to_insert) # 批量添加 M 趋势图
        await session.flush()
        await session.commit()


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

        conditions = [KeywordInfoTable.platform.in_(cleaned_platforms)]

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
                conditions.append(KeywordInfoTable.remark.ilike(f"%{cleaned_remark}%"))

        query = (
            select(KeywordInfoTable)
            .where(and_(*conditions))
            .order_by(KeywordInfoTable.created_at.desc())
        )

        result = await session.execute(query)
        items = result.scalars().all()
        return {"items": items}


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
        if not ids:
            # 删除全表
            await session.execute(delete(KeywordInfoTable))
        else:
            # 按ID删除
            await session.execute(delete(KeywordInfoTable).where(KeywordInfoTable.id.in_(ids)))
        await session.commit()

    ####### 域名监控
    async def get_domain_monitor_list(
            self,
            session: AsyncSession,
            params: DomainMonitorQueryParams,
    ) -> dict:
        """根据多个条件查询域名监控数据（支持分页）

        Args:
            session: 数据库会话
            params: 查询参数对象，包含分页和筛选条件

        Returns:
            dict: 包含查询结果和分页信息的字典
        """
        # 参数验证
        if params.page < 1:
            raise GlobalErrorCodeException(msg="页码必须大于0")
        if params.size < 1 or params.size > 100:
            raise GlobalErrorCodeException(msg="每页大小必须在1-100之间")

        # 验证排名范围参数
        if params.rank_min is not None and (params.rank_min < 1 or params.rank_min > 500):
            raise GlobalErrorCodeException(msg="最小排名必须在1-500之间")
        if params.rank_max is not None and (params.rank_max < 1 or params.rank_max > 500):
            raise GlobalErrorCodeException(msg="最大排名必须在1-500之间")
        if params.rank_min is not None and params.rank_max is not None and params.rank_min > params.rank_max:
            raise GlobalErrorCodeException(msg="最小排名不能大于最大排名")

        # 验证时间范围参数
        if params.created_at_start and params.created_at_end:
            if params.created_at_start >= params.created_at_end:
                raise GlobalErrorCodeException(msg="起始时间必须小于结束时间")

        # 数据清洗和验证
        if not params.platforms:
            raise GlobalErrorCodeException(msg="平台参数不能为空")

        # 去除空字符串和两端空格
        cleaned_platforms = [p.strip() for p in params.platforms if p and p.strip()]
        if not cleaned_platforms:
            raise GlobalErrorCodeException(msg="平台参数不能为空")

        valid_platforms = set(self.get_platforms())
        if any(p not in valid_platforms for p in cleaned_platforms):
            raise GlobalErrorCodeException(msg="平台参数不合法")

        conditions = [DomainMonitorTable.platform.in_(cleaned_platforms)]

        # 处理关键词参数 - 支持多选模糊查询
        if params.keywords:
            cleaned_keywords = [k.strip() for k in params.keywords if k and k.strip()]
            if cleaned_keywords:
                # 关键词模糊多选，OR 组合
                keyword_conditions = [
                    DomainMonitorTable.keyword.ilike(f"%{k}%") for k in cleaned_keywords
                ]
                conditions.append(or_(*keyword_conditions))

        # 处理域名参数 - 支持多选完全匹配
        if params.domain_names:
            cleaned_domain_names = [d.strip() for d in params.domain_names if d and d.strip()]
            if cleaned_domain_names:
                conditions.append(DomainMonitorTable.domain_name.in_(cleaned_domain_names))

        # 处理是否自购域名参数
        if params.is_buy_domain is not None:
            conditions.append(DomainMonitorTable.is_buy_domain == params.is_buy_domain)

        # 处理排名范围查询
        if params.rank_min is not None:
            conditions.append(DomainMonitorTable.rank >= params.rank_min)
        if params.rank_max is not None:
            conditions.append(DomainMonitorTable.rank <= params.rank_max)

        # 处理执行时间范围查询
        if params.created_at_start:
            conditions.append(DomainMonitorTable.created_at >= params.created_at_start)
        if params.created_at_end:
            conditions.append(DomainMonitorTable.created_at <= params.created_at_end)

        # 构建基础查询
        base_query = select(DomainMonitorTable).where(and_(*conditions))

        # 计算总数（优化：使用 count 直接计数）
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar_one()

        # 分页查询
        offset = (params.page - 1) * params.size
        final_query = base_query.order_by(DomainMonitorTable.created_at.desc()).offset(offset).limit(params.size)

        result = await session.execute(final_query)
        items = result.scalars().all()

        # 计算分页信息
        total_pages = (total_count + params.size - 1) // params.size
        has_next = params.page < total_pages
        has_prev = params.page > 1

        logger.info(f"查询域名监控数据成功: 页码={params.page}, 大小={params.size}, 总数={total_count}")

        return {
            "items": items,
            "pagination": {
                "page": params.page,
                "size": params.size,
                "total": total_count,
                "pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }


    async def list_traffic_monitors(
            self,
            session: AsyncSession,
            params: TrafficMonitorListRequest,
    ) -> dict:
        # 参数验证
        if params.page < 1:
            raise ParamsErrorCodeException(msg="页码必须大于0")
        if params.size < 1 or params.size > 100:
            raise ParamsErrorCodeException(msg="每页大小必须在1-100之间")

        business_type = params.business_type or "keyword"
        terminal_type = params.terminal_type or "PC"
        conditions = []

        # 1. 处理域名多选（精确匹配）
        if params.domain_names:
            cleaned_domains = [d.strip() for d in params.domain_names if d and d.strip()]
            if cleaned_domains:
                conditions.append(TrafficMonitorTable.domain_name.in_(cleaned_domains))

        # 2. 处理关键词多选（模糊匹配）
        if params.keywords:
            cleaned_keywords = [k.strip() for k in params.keywords if k and k.strip()]
            if cleaned_keywords:
                keyword_conditions = [
                    TrafficMonitorTable.keyword.ilike(f"%{k}%") for k in cleaned_keywords
                ]
                conditions.append(or_(*keyword_conditions))

        # 3. 处理日期范围
        if params.date_range and len(params.date_range) == 2:
            start_time, end_time = params.date_range
            if start_time:
                conditions.append(TrafficMonitorTable.created_at >= start_time)
            if end_time:
                conditions.append(TrafficMonitorTable.created_at <= end_time)

        conditions.append(TrafficMonitorTable.business_type == business_type)
        conditions.append(TrafficMonitorTable.terminal_type == terminal_type)
        # 4. 构建基础查询条件
        base_where = and_(*conditions) if conditions else True

        # 聚合子查询
        aggregated_query = (
            select(
                TrafficMonitorTable.domain_name,
                TrafficMonitorTable.keyword,
                func.max(TrafficMonitorTable.created_at).label("created_at"),
                func.sum(TrafficMonitorTable.clicks).label("clicks"),
                func.sum(TrafficMonitorTable.impressions).label("impressions"),
                func.avg(TrafficMonitorTable.rank).label("rank")
            )
            .where(base_where)
            .group_by(
                TrafficMonitorTable.domain_name,
                TrafficMonitorTable.keyword
            )
        ).subquery()

        # 6. 计算总数（对聚合后的结果进行计数）
        count_query = select(func.count()).select_from(aggregated_query)
        total_result = await session.execute(count_query)
        total_count = total_result.scalar_one()

        # 7. 分页查询
        offset = (params.page - 1) * params.size
        final_query = (
            select(aggregated_query)
            .order_by(aggregated_query.c.created_at.desc())
            .offset(offset)
            .limit(params.size)
        )

        data = await session.execute(final_query)
        data = data.all()

        items = []
        for val in data:
            ctr = val.clicks / val.impressions if val.impressions > 0 else 0
            items.append({
                "business_type": params.business_type,
                "domain_name": val.domain_name,
                "keyword": val.keyword,
                "created_at": val.created_at,
                "clicks": val.clicks,
                "impressions": val.impressions,
                "ctr":  Tools.reserve_two_digits(ctr),
                "rank": Tools.reserve_two_digits(val.rank)
            })


        logger.info(f"查询流量监控聚合数据成功: 页码={params.page}, 大小={params.size}, 总数={total_count}")
        result = {
            "items": items,
            "pagination": {
                "page": params.page,
                "size": params.size,
                "total": total_count,
            }
        }

        return result

    async def get_trend_chart(
            self,
            session: AsyncSession,
            params: TrendListRequest,
    ) -> dict:
        """获取趋势图数据

        Args:
            session: 数据库会话
            params: 趋势图查询参数

        Returns:
            dict: 趋势图数据
        """
        # 类型字段校验：如果类型和域名有一个为空则返回空列表
        if not params.terminal_type or not params.domain_names:
            return {"data": []}

        # 数据清洗和验证
        # domain_names 是单个字符串，需要转换为列表
        if isinstance(params.domain_names, str):
            cleaned_domain_names = [d.strip() for d in params.domain_names.split(',') if d and d.strip()]
        else:
            cleaned_domain_names = [d.strip() for d in params.domain_names if d and d.strip()]
        if not cleaned_domain_names:
            return {"data": []}

        # 处理时间范围
        start_time = None
        end_time = None
        if params.start_time:
            start_time = datetime.fromisoformat(params.start_time.replace('Z', '+00:00'))
        if params.end_time:
            end_time = datetime.fromisoformat(params.end_time.replace('Z', '+00:00'))

        if params.time_label == "today":
            # 获取今天的数据 - 从 hour_info 中提取小时数据
            return await self._get_today_trend_chart(
                session, cleaned_domain_names, params.terminal_type, start_time, end_time
            )
        else:
            # 获取历史数据 - 按日期聚合
            return await self._get_historical_trend_chart(
                session, cleaned_domain_names, params.terminal_type, start_time, end_time
            )

    async def _get_today_trend_chart(
            self,
            session: AsyncSession,
            domain_names: list[str],
            terminal_type: str,
            start_time: datetime = None,
            end_time: datetime = None
    ) -> dict:
        """获取今日趋势图数据

        Args:
            session: 数据库会话
            domain_names: 域名列表
            terminal_type: 终端类型
            start_time: 开始时间（忽略，仅获取今日数据）
            end_time: 结束时间（忽略，仅获取今日数据）

        Returns:
            dict: 今日趋势图数据
        """
        # 构建查询条件
        conditions = [
            TrafficMonitorChartTable.domain_name.in_(domain_names),
            TrafficMonitorChartTable.terminal_type == terminal_type
        ]

        # 查询今日数据
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        conditions.append(TrafficMonitorChartTable.created_at >= today_start)

        # 查询hour_info数据
        query = select(TrafficMonitorChartTable).where(and_(*conditions))
        result = await session.execute(query)
        chart_data = result.scalars().all()

        # 提取hour_info字段数据
        data = []
        for item in chart_data:
            if item.hour_info:
                try:
                    # 解析hour_info JSON数据
                    hour_info_data = json.loads(item.hour_info)
                    if isinstance(hour_info_data, list):
                        data.extend(hour_info_data)
                except (json.JSONDecodeError, TypeError):
                    # 如果解析失败，跳过该项
                    continue

        return {"data": data}

    async def _get_historical_trend_chart(
            self,
            session: AsyncSession,
            domain_names: list[str],
            terminal_type: str,
            start_time: datetime = None,
            end_time: datetime = None
    ) -> dict:
        """获取历史趋势图数据

        Args:
            session: 数据库会话
            domain_names: 域名列表
            terminal_type: 终端类型
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            dict: 历史趋势图数据
        """
        # 构建基础查询条件
        conditions = [
            TrafficMonitorChartTable.domain_name.in_(domain_names),
            TrafficMonitorChartTable.terminal_type == terminal_type
        ]

        # 添加时间范围条件
        if start_time:
            conditions.append(TrafficMonitorChartTable.created_at >= start_time)
        if end_time:
            conditions.append(TrafficMonitorChartTable.created_at <= end_time)

        # 按日期分组聚合clicks和impressions
        # 使用func.date将created_at转换为日期格式进行分组
        query = (
            select(
                func.date(TrafficMonitorChartTable.created_at).label("date"),
                func.sum(TrafficMonitorChartTable.impressions).label("impressions"),
                func.sum(TrafficMonitorChartTable.clicks).label("clicks")
            )
            .where(and_(*conditions))
            .group_by(func.date(TrafficMonitorChartTable.created_at))
            .order_by("date")
        )

        result = await session.execute(query)
        aggregated_data = result.all()

        # 格式化返回数据
        data = []
        for row in aggregated_data:
            data.append({
                "label": row.date.strftime("%Y-%m-%d"),
                "impressions": row.impressions or 0,
                "click": row.clicks or 0
            })

        return {"data": data}


    async def list_site_accounts(
            self,
            session: AsyncSession,
            params: AccountListRequest,
    ) -> dict:
        """查询站平账号列表（支持分页）

        Args:
            session: 数据库会话
            params: 查询参数对象，包含平台、域名筛选和分页条件

        Returns:
            dict: 包含账号列表和分页信息的字典
        """
        # 参数验证
        if params.page < 1:
            raise ParamsErrorCodeException(msg="页码必须大于0")
        if params.size < 1 or params.size > 100:
            raise ParamsErrorCodeException(msg="每页大小必须在1-100之间")

        # 数据清洗和验证
        if not params.platforms:
            raise ParamsErrorCodeException(msg="平台参数不能为空")

        # 去除空字符串和两端空格
        cleaned_platforms = [p.strip() for p in params.platforms if p and p.strip()]
        if not cleaned_platforms:
            raise ParamsErrorCodeException(msg="平台参数不能为空")

        # 验证平台参数合法性（可以根据实际需求添加平台验证逻辑）
        valid_platforms = ["BAIDU", "360"]  # 可根据实际需求调整
        if any(p not in valid_platforms for p in cleaned_platforms):
            raise ParamsErrorCodeException(msg="平台参数不合法")

        conditions = [PlatformAccountTable.platform.in_(cleaned_platforms)]

        # 处理域名参数 - 支持多选完全匹配
        if params.domain_names:
            cleaned_domain_names = [d.strip() for d in params.domain_names if d and d.strip()]
            if cleaned_domain_names:
                # 使用数组包含查询，查找域名列表中包含指定域名的账号
                domain_conditions = []
                for domain in cleaned_domain_names:
                    domain_conditions.append(PlatformAccountTable.domain_list.any(domain))
                conditions.append(or_(*domain_conditions))

        # 构建基础查询
        base_query = select(PlatformAccountTable).where(and_(*conditions))

        # 计算总数
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar_one()

        # 分页查询
        offset = (params.page - 1) * params.size
        final_query = base_query.order_by(PlatformAccountTable.created_at.desc()).offset(offset).limit(params.size)

        result = await session.execute(final_query)
        items = result.scalars().all()

        # 计算分页信息
        total_pages = (total_count + params.size - 1) // params.size
        has_next = params.page < total_pages
        has_prev = params.page > 1

        logger.info(f"查询站平账号列表成功: 页码={params.page}, 大小={params.size}, 总数={total_count}")

        return {
            "items": items,
            "pagination": {
                "page": params.page,
                "size": params.size,
                "total": total_count,
                "pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }

