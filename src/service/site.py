import asyncio
import decimal
import json
import random
import traceback
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from typing import Optional, List, Dict
from zoneinfo import ZoneInfo

import pandas as pd
from pandas import DataFrame
from sqlalchemy import select, update, and_, or_, delete, func, text, case, asc
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Numeric
from sqlmodel import desc

from src.core import logger
from src.core.db.db_database import transactional
from src.core.exception.custom_exception import GlobalErrorCodeException, ParamsErrorCodeException
from src.defined.alarm import AlarmModule
from src.defined.site import BusinessTypeEnum
from src.models.site_domain_info import DomainInfoTable
from src.models.site_domain_monitor import DomainMonitorTable
from src.models.site_keyword_info import KeywordInfoTable
from src.models.site_platform_account import PlatformAccountTable
from src.models.site_traffic_monitor import TrafficMonitorTable
from src.models.site_traffic_monitor_chart import TrafficMonitorChartTable
from src.schemas.site_schema import DomainQueryParams, DomainMonitorPushRequest, \
    TrafficMonitorPushRequest, TrafficMonitorListRequest, DomainMonitorQueryParams, AccountListRequest, TrendListRequest
from src.service.base import BaseService
from src.utils.alarm import alarm_robot
from src.utils.async_function import run_bulk_update_sync
from src.utils.time_zone import TimeZone
from src.utils.tools import Tools


class SiteService(BaseService):
    """站点域名管理服务"""

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
        utc_now = datetime.utcnow()
        logger.info(f"开始拉取域名监控任务 {utc_now}...")

        condition1 = KeywordInfoTable.last_execute_time.is_(None)
        condition2 = KeywordInfoTable.last_execute_time < (
                utc_now - (KeywordInfoTable.execute_cycle * text("INTERVAL '1 hour'"))
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
        ).order_by(
            KeywordInfoTable.last_execute_time.asc().nulls_first()
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
        try:
            file_url = params.file_url
            file_name = params.file_name
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

            record_df: DataFrame = await asyncio.to_thread(pd.read_csv, file_url)
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
                    rank=decimal.Decimal(val.get("rank")),

                )
                domains_to_insert.append(domain)

            session.add_all(domains_to_insert)

            await session.commit()
        except Exception as e:
            error_msg = f"{traceback.format_exc()}"
            await alarm_robot.send_message("域名监控任务存储失败", error_msg, module=AlarmModule.SITE)
            raise

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
            PlatformAccountTable.status.in_(["init", "normal"]),
            due_condition
        ).order_by(
            PlatformAccountTable.last_check_time.nulls_first()
        ).limit(1).with_for_update(skip_locked=True)

        account_query = await session.execute(account_query)
        account_info = account_query.one_or_none()

        if not account_info:
            logger.info("没有需要执行的流量监控任务")
            return []

        logger.info(f"成功拉取到流量监控任务，账号ID: {account_info.id}, 用户名: {account_info.account_number}")
        result = {
            "id": account_info.id,
            "account_number": account_info.account_number,
            "password": account_info.password,
        }

        return result

    @transactional
    async def traffic_monitor_push_task(self, params: TrafficMonitorPushRequest, session: AsyncSession):
        try:
            account_info = params.account_info
            account_number = account_info.account_number
            account_status = account_info.account_status
            cookie = account_info.cookie
            domain_list = account_info.domain_list
            managed_domain_count = account_info.managed_domain_count
            domain_info_list = params.domain_info_list

            file_info = params.file_info
            keyword_page = file_info.keyword_page
            chart = file_info.chart

            # ----------------- 修改站平账号信息 -----------------
            account_res = update(
                PlatformAccountTable
            ).where(
                PlatformAccountTable.account_number == account_number
            ).values(
                status=account_status,
                cookie=cookie or None,
                domain_list=domain_list or None,
                managed_domain_count=managed_domain_count,
                last_check_time=datetime.utcnow(),
                updated_at=datetime.utcnow()
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

            # ----------------- 批量修改域名关联的账号信息 -----------------
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
            logger.info(f"需要批量修改域名关联的账号信息数据：{len(upd_domain_info_list)} 条记录！")
            if upd_domain_info_list:
                await session.run_sync(
                    run_bulk_update_sync,
                    DomainInfoTable,
                    upd_domain_info_list
                )

            keyword_page_df = pd.DataFrame()
            chart_df = pd.DataFrame()
            if keyword_page:
                keyword_page_df = await asyncio.to_thread(pd.read_csv, keyword_page)

            if chart:
                chart_df = await asyncio.to_thread(pd.read_csv, chart)


            execution_date = datetime.now().strftime('%Y-%m-%d')
            execution_date = datetime.strptime(execution_date, "%Y-%m-%d").date()
            # ----------------- 批量添加 趋势图 -----------------

            chart_to_insert = []
            if not chart_df.empty and len(chart_df) > 1:
                chart_df = chart_df.fillna('').astype(str)
                for _, val in chart_df.iterrows():
                    terminal_type = val.get("terminal")
                    domain = val.get("domain")
                    reference_number = f"{str(execution_date)}_{terminal_type}_{domain}"
                    chart_to_insert.append({
                        "clicks": int(val.get("click") or 0),
                        "impressions": int(val.get("display") or 0),
                        "domain_name": domain,
                        "hour_info": val.get("info"),
                        "terminal_type": terminal_type,
                        "execution_date": execution_date,
                        "reference_number": reference_number
                    })

                insert_stmt = insert(TrafficMonitorChartTable).values(chart_to_insert)

                # 2. 链式调用 ON CONFLICT DO UPDATE 逻辑（与单行逻辑相同）
                on_conflict_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=[TrafficMonitorChartTable.reference_number],
                    set_=dict(
                        clicks=insert_stmt.excluded.clicks,
                        impressions=insert_stmt.excluded.impressions,
                        hour_info=insert_stmt.excluded.hour_info,
                        updated_at=func.now()
                    )
                ).returning(TrafficMonitorChartTable.id)  # 返回关键字段

                result = await session.execute(on_conflict_stmt)

            # ----------------- 批量添加 流量表 -----------------

            keyword_page_to_insert = []
            if not keyword_page_df.empty and len(keyword_page_df) > 1:
                keyword_page_df = keyword_page_df.fillna('').astype(str)
                keyword_page_df['rank'] = keyword_page_df['rank'].apply(Decimal)
                keyword_page_df['ctr'] = keyword_page_df['ctr'].apply(Decimal)

                for _, val in keyword_page_df.iterrows():

                    keyword = val.get("keyword")
                    page = val.get("page")
                    business_type = val.get("type")
                    terminal_type = val.get("terminal")
                    domain = val.get("domain")
                    reference_number = f"{str(execution_date)}_{terminal_type}_{business_type}_{domain}_{page}"
                    if business_type == "keyword":
                        reference_number = f"{reference_number}_{keyword}"
                    keyword_page_to_insert.append({
                        "clicks": int(val.get("click")),
                        "impressions": int(val.get("display")),
                        "domain_name": domain,
                        "ctr": val.get("ctr"),
                        "terminal_type": terminal_type,
                        "rank": val.get("rank"),
                        "business_type": business_type,
                        "keyword": keyword,
                        "page": val.get("page"),
                        "reference_number": reference_number,
                        "execution_date": execution_date
                    })

                insert_stmt = insert(TrafficMonitorTable).values(keyword_page_to_insert)
                on_conflict_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=[TrafficMonitorTable.reference_number],
                    set_=dict(
                        clicks=insert_stmt.excluded.clicks,
                        ctr=insert_stmt.excluded.ctr,
                        rank=insert_stmt.excluded.rank,
                        impressions=insert_stmt.excluded.impressions,
                        updated_at=func.now()
                    )
                ).returning(TrafficMonitorTable.id)  # 返回关键字段

                result = await session.execute(on_conflict_stmt)

            logger.info(f"批量添加 -> 流量数据：{len(keyword_page_to_insert)} 条记录，趋势图数据: {len(chart_to_insert)} 条记录")

            await session.flush()
            await session.commit()
        except Exception as e:
            error_msg = f"{traceback.format_exc()}"
            await alarm_robot.send_message("流量监控任务存储失败", error_msg, module=AlarmModule.SITE)
            raise

    async def list_traffic_monitors(
            self,
            session: AsyncSession,
            params: TrafficMonitorListRequest,
    ) -> dict:

        business_type = params.business_type or "keyword"
        terminal_type = params.terminal_type or "PC"

        if not params.domain_names:
            return {"items": [], "pagination": { "page": params.page,"size": params.size,"total": 0,}}
        group_by_columns = []
        group_by_columns.append(TrafficMonitorTable.domain_name)
        if business_type == BusinessTypeEnum.KEYWORD.value:
            group_by_columns.append(TrafficMonitorTable.keyword)
        else:
            group_by_columns.append(TrafficMonitorTable.page)

        conditions = []

        # 1. 处理域名多选（精确匹配）
        if params.domain_names:
            conditions.append(TrafficMonitorTable.domain_name.in_(params.domain_names))

        # 2. 处理关键词多选（模糊匹配）
        if params.keywords and business_type == BusinessTypeEnum.KEYWORD:
            conditions.append(TrafficMonitorTable.keyword.ilike(f"%{params.keywords}%"))

        # 3. 处理日期范围
        if params.execution_time and len(params.execution_time) == 2:
            start_time, end_time = params.execution_time
            conditions.append(TrafficMonitorTable.execution_date >= start_time)
            conditions.append(TrafficMonitorTable.execution_date <= end_time)

        conditions.append(TrafficMonitorTable.business_type == business_type)
        conditions.append(TrafficMonitorTable.terminal_type == terminal_type)
        # 4. 构建基础查询条件
        base_where = and_(*conditions) if conditions else True

        # 聚合子查询
        select_by_columns = [
            TrafficMonitorTable.domain_name,
            func.max(TrafficMonitorTable.id).label("id"),
            func.max(TrafficMonitorTable.execution_date).label("execution_date"),
            func.sum(TrafficMonitorTable.clicks).label("clicks"),
            func.sum(TrafficMonitorTable.impressions).label("impressions"),
            func.avg(TrafficMonitorTable.rank).label("rank")

        ]
        if business_type == BusinessTypeEnum.KEYWORD:
            select_by_columns.append(TrafficMonitorTable.keyword)
        else:
            select_by_columns.append(TrafficMonitorTable.page)
        aggregated_query = select(
            *select_by_columns
        ).where(
            base_where
        ).group_by(
            *group_by_columns
        ).subquery()

        # 6. 计算总数（对聚合后的结果进行计数）
        count_query = select(func.count()).select_from(aggregated_query)
        total_result = await session.execute(count_query)
        total_count = total_result.scalar_one()

        # 7. 分页查询
        offset = (params.page - 1) * params.size
        final_query = (
            select(aggregated_query)
            .order_by(aggregated_query.c.execution_date.desc())
            .offset(offset)
            .limit(params.size)
        )

        data = await session.execute(final_query)
        data = data.all()

        items = []
        for val in data:
            ctr = val.clicks / val.impressions if val.impressions > 0 else 0
            record = {
                "id": val.id,
                "business_type": params.business_type,
                "domain_name": val.domain_name,
                "keyword": getattr(val, "keyword", ""),
                "page": getattr(val, "page", ""),
                "clicks": val.clicks,
                "impressions": val.impressions,
                "ctr": f"{Tools.reserve_two_digits(ctr)}%",
                "rank": Tools.reserve_two_digits(val.rank),
                "execution_date": f"{str(val.execution_date)} 00:00:00",
            }

            items.append(record)

        result = {
            "items": items,
            "pagination": {
                "page": params.page,
                "size": params.size,
                "total": total_count,
            }
        }
        logger.info(f"查询流量监控聚合数据成功: 页码={params.page}, 大小={params.size}, 总数={total_count}")

        return result

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
        # 构建查询条件
        conditions = []

        # 处理域名列表多选查询
        if query.domain_name_list:
            # 使用完全匹配的多选查询
            conditions.append(DomainInfoTable.domain_name.in_(query.domain_name_list))

        if query.domain_group:
            conditions.append(DomainInfoTable.domain_group == query.domain_group)

        if query.server_number:
            conditions.append(DomainInfoTable.server_number == query.server_number)

        if query.baidu_site_account:
            conditions.append(DomainInfoTable.account_number == query.baidu_site_account)

        if query.is_baidu_verified is not None:
            conditions.append(DomainInfoTable.is_verified == query.is_baidu_verified)

        # 构建基础查询
        base_query = select(*DomainInfoTable.__table__.columns)

        # 应用筛选条件
        if conditions:
            base_query = base_query.where(and_(*conditions))

        # 计算总数（优化：使用 count 直接计数）
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar_one()
        order_clause = DomainInfoTable.created_at.desc()
        if query.sort_order == "asc":
            order_clause = DomainInfoTable.created_at.asc()
        # 分页查询
        offset = (query.page - 1) * query.size
        final_query = base_query.order_by(
            order_clause
        ).offset(offset).limit(query.size)

        result = await session.execute(final_query)
        domain_list = result.mappings().all()
        domain_list = [dict(val) for val in domain_list]
        logger.info(f"查询域名列表成功: 页码={query.page}, 大小={query.size}, 总数={total_count}")

        return {
            "items": domain_list,
            "pagination": {
                "page": query.page,
                "size": query.size,
                "total": total_count,
            }
        }

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

    async def get_keyword_infos(
            self,
            session: AsyncSession,
            platforms: List[str],
            keyword: str = None,
            remark: str = None,
            sort_by: str = None,
            sort_order: str = None,
            page: int = 1,
            size: int = 10,
    ) -> dict:
        """根据平台、关键词与备注查询配置
        - 平台：必须、多选
        - 关键词：模糊查询（任意一个匹配即可）
        - 备注：可选、模糊查询
        """
        conditions = []
        if platforms:
            conditions = [KeywordInfoTable.platform.in_(platforms)]
        # 处理关键词参数
        if keyword:
            conditions.append(KeywordInfoTable.keyword.ilike(f"%{keyword}%"))
        # 处理备注参数
        if remark:
            conditions.append(KeywordInfoTable.remark.ilike(f"%{remark}%"))

        order_clause = KeywordInfoTable.last_execute_time.desc()
        # 处理排序参数
        if sort_by == "last_execute_time":
            if sort_order == "asc":
                order_clause = KeywordInfoTable.last_execute_time.asc()
            else:
                order_clause = KeywordInfoTable.last_execute_time.desc()
        elif sort_by == "created_at":
            if sort_order == "asc":
                order_clause = KeywordInfoTable.created_at.asc()
            else:
                order_clause = KeywordInfoTable.created_at.desc()

        # 分页查询
        offset = (page - 1) * size

        base_query = (
            select(*KeywordInfoTable.__table__.columns)
            .where(and_(*conditions))
        )
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar_one()

        final_query = base_query.order_by(
            order_clause
        ).offset(offset).limit(size)

        result = await session.execute(final_query)
        items = [dict(val) for val in result.mappings().all()]
        # 计算分页信息
        total_pages = (total_count + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1

        logger.info(f"查询关键词数据成功: 页码={page}, 大小={size}, 总数={total_count}")

        return {
            "items": items,
            "pagination": {
                "page": page,
                "size": size,
                "total": total_count,
                "pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }

    # 关键词删除
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
        platforms = params.get("platforms")
        keyword = params.get("keyword")
        domain_names = params.get("domain_names")
        is_buy_domain = params.get("is_buy_domain")
        rank_min = params.get("rank_min")
        rank_max = params.get("rank_max")
        created_at_start = params.get("created_at_start")
        created_at_end = params.get("created_at_end")
        sort_order = params.get("sort_order")
        page = params.get("page")
        size = params.get("size")
        conditions = []
        # 平台匹配
        if platforms:
            conditions = [DomainMonitorTable.platform.in_(platforms)]


        # 处理关键词参数 模糊查询
        if keyword:
            conditions.append(DomainMonitorTable.keyword.ilike(f"%{keyword}%"))

        # 处理域名参数 - 支持多选完全匹配
        if domain_names:
            conditions.append(DomainMonitorTable.domain_name.in_(domain_names))

        # 处理是否自购域名参数
        if is_buy_domain is not None:
            conditions.append(DomainMonitorTable.is_buy_domain == is_buy_domain)

        # 处理排名范围查询
        if rank_min:
            conditions.append(DomainMonitorTable.rank >= rank_min)
        if rank_max:
            conditions.append(DomainMonitorTable.rank <= rank_max)

        # 处理执行时间范围查询
        if created_at_start and created_at_end:
            conditions.append(DomainMonitorTable.created_at >= created_at_start)
            conditions.append(DomainMonitorTable.created_at <= created_at_end)

        # 构建基础查询
        base_query = select(*DomainMonitorTable.__table__.columns).where(and_(*conditions))

        # 计算总数（优化：使用 count 直接计数）
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar_one()

        order_clause = DomainMonitorTable.created_at.desc()
        if sort_order =="asc":
            order_clause = DomainMonitorTable.created_at.asc()

        # 分页查询
        offset = (page - 1) * size
        final_query = base_query.order_by(
            order_clause
        ).offset(offset).limit(size)

        result = await session.execute(final_query)
        items = [dict(val) for val in result.mappings().all()]

        # 计算分页信息
        total_pages = (total_count + size - 1) // size
        has_next = page < total_pages
        has_prev = page > 1

        logger.info(f"查询域名监控数据成功: 页码={page}, 大小={size}, 总数={total_count}")

        return {
            "items": items,
            "pagination": {
                "page": page,
                "size": size,
                "total": total_count,
                "pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }


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

        # 处理时间范围 - 按照执行时间(yy-mm-dd格式)进行匹配
        start_date = None
        end_date = None
        if params.start_time:
            start_date = datetime.strptime(params.start_time, '%Y-%m-%d').date()
        if params.end_time:
            end_date = datetime.strptime(params.end_time, '%Y-%m-%d').date()
        # 打印时间范围
        # print("时间范围：", params.start_time, "~", params.end_time)

        # 获取历史数据 - 按日期聚合
        return await self._get_historical_trend_chart(
            session, cleaned_domain_names, params.terminal_type, start_date, end_date
        )

    async def _get_historical_trend_chart(
            self,
            session: AsyncSession,
            domain_names: list[str],
            terminal_type: str,
            start_date: date = None,
            end_date: date = None
    ) -> dict:
        """获取历史趋势图数据

        Args:
            session: 数据库会话
            domain_names: 域名列表
            terminal_type: 终端类型
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            dict: 历史趋势图数据
        """
        # 如果开始日期和结束日期相同，则返回小时级别的数据
        if start_date and end_date and start_date == end_date:
            # 构建基础查询条件
            conditions = [
                TrafficMonitorChartTable.domain_name.in_(domain_names),
                TrafficMonitorChartTable.terminal_type == terminal_type,
                TrafficMonitorChartTable.execution_date == start_date
            ]

            # 查询指定日期的数据，包含hour_info字段
            query = (
                select(
                    TrafficMonitorChartTable.hour_info,
                    TrafficMonitorChartTable.impressions,
                    TrafficMonitorChartTable.clicks
                )
                .where(and_(*conditions))
            )

            result = await session.execute(query)
            rows = result.all()
            for row in rows:
                if row.hour_info:
                    return {"data": row.hour_info}
            return {"data": []}
        # 构建基础查询条件
        conditions = [
            TrafficMonitorChartTable.domain_name.in_(domain_names),
            TrafficMonitorChartTable.terminal_type == terminal_type
        ]

        # 添加时间范围条件 - 使用执行日期
        if start_date:
            conditions.append(TrafficMonitorChartTable.execution_date >= start_date)
        if end_date:
            conditions.append(TrafficMonitorChartTable.execution_date <= end_date)

        # 按执行日期分组聚合clicks和impressions
        query = (
            select(
                TrafficMonitorChartTable.execution_date.label("date"),
                func.sum(TrafficMonitorChartTable.impressions).label("impressions"),
                func.sum(TrafficMonitorChartTable.clicks).label("clicks")
            )
            .where(and_(*conditions))
            .group_by(TrafficMonitorChartTable.execution_date)
            .order_by("date")
        )

        result = await session.execute(query)
        aggregated_data = result.all()

        # 格式化返回数据
        data = []
        for row in aggregated_data:
            data.append({
                "label": row.date.strftime("%Y-%m-%d"),
                "display": row.impressions or 0,
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
        conditions = []
        if params.platforms:
            conditions.append(PlatformAccountTable.platform.in_(params.platforms))

        # 处理域名参数 - 支持多选完全匹配
        if params.domain_names:
            # 使用数组包含查询，查找域名列表中包含指定域名的账号
            domain_conditions = []
            for domain in params.domain_names:
                domain_conditions.append(PlatformAccountTable.domain_list.any(domain))
            conditions.append(or_(*domain_conditions))

        # 构建基础查询
        base_query = select(*PlatformAccountTable.__table__.columns).where(and_(*conditions))

        # 计算总数
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar_one()

        if params.sort_order == "asc":  # 升序 + nulls_last
            order_expr = PlatformAccountTable.last_check_time.nulls_last()
        else:  # 降序 + nulls_first
            order_expr = desc(PlatformAccountTable.last_check_time).nulls_first()
        # 分页查询
        offset = (params.page - 1) * params.size
        final_query = base_query.order_by(
            order_expr
        ).offset(offset).limit(params.size)

        result = await session.execute(final_query)
        items = [dict(val) for val in result.mappings().all()]

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
