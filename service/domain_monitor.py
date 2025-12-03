from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.exception.custom_exception import GlobalErrorCodeException
from src.models.site_domain_monitor import DomainMonitorTable
from src.service.base import BaseService


class DomainMonitorService(BaseService):
    """域名监控服务：负责数据库查询与业务校验"""

    @staticmethod
    def get_platforms() -> List[str]:
        """返回可选平台列表（用于前端多选）"""
        return ["BAIDU_PC", "BAIDU_M", "360PC", "360M"]

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

        conditions = [ DomainMonitorTable.platform.in_(cleaned_platforms)]

        # 处理关键词参数 - 支持多选模糊查询
        if keywords:
            cleaned_keywords = [k.strip() for k in keywords if k and k.strip()]
            if cleaned_keywords:
                # 关键词模糊多选，OR 组合
                keyword_conditions = [
                     DomainMonitorTable.keyword.ilike(f"%{k}%") for k in cleaned_keywords
                ]
                conditions.append(or_(*keyword_conditions))

        # 处理域名参数 - 支持多选完全匹配
        if domain_names:
            cleaned_domain_names = [d.strip() for d in domain_names if d and d.strip()]
            if cleaned_domain_names:
                conditions.append( DomainMonitorTable.domain_name.in_(cleaned_domain_names))

        # 处理是否自购域名参数
        if is_buy_domain is not None:
            conditions.append( DomainMonitorTable.is_buy_domain == is_buy_domain)

        # 处理排名范围查询
        if rank_range is not None:
            min_rank, max_rank = rank_range
            if min_rank is not None:
                conditions.append( DomainMonitorTable.rank >= min_rank)
            if max_rank is not None:
                conditions.append( DomainMonitorTable.rank <= max_rank)

        # 处理执行时间范围查询
        if created_at_range is not None:
            start_at, end_at = created_at_range
            if start_at is not None:
                conditions.append( DomainMonitorTable.created_at >= start_at)
            if end_at is not None:
                conditions.append( DomainMonitorTable.created_at <= end_at)

        query = (
            select( DomainMonitorTable)
            .where(and_(*conditions))
            .order_by( DomainMonitorTable.created_at.desc())
        )

        result = await session.execute(query)
        items = result.scalars().all()
        return {"items": items}

    async def batch_create_test_data(
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
                
                monitor_data =  DomainMonitorTable(
                    keyword=f"{keywords_templates[i % len(keywords_templates)]}_{i+1}",
                    platform=platforms[i % len(platforms)],
                    city=cities[i % len(cities)],
                    is_buy_domain=i % 3 == 0,  # 每3条有1条是自购域名
                    domain_name=f"{domain_templates[i % len(domain_templates)]}" if i % 2 == 0 else None,
                    domain_group=domain_groups[i % len(domain_groups)] if i % 2 == 0 else None,
                    real_url=f"https://{domain_templates[i % len(domain_templates)]}/page{i+1}" if i % 2 == 0 else None,
                    title=f"{titles[i % len(titles)]}_{i+1}" if i % 2 == 0 else None,
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
