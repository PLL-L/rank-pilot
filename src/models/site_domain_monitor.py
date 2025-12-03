from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Integer, String, Boolean
from sqlmodel import Field, SQLModel, Column, DateTime, func, Index

from src.models.mixins import CommonMixin


class SiteDomainMonitorBase(SQLModel):
    # 关键词：VARCHAR(128) 非空
    keyword: str = Field(
        sa_column=Column("keyword", String(128), nullable=False),
        description="关键词"
    )

    # 平台：VARCHAR(10) 非空
    platform: str = Field(
        sa_column=Column("platform", String(10), nullable=False),
        description="平台"
    )

    # 城市：VARCHAR(64) 非空
    city: str = Field(
        sa_column=Column("city", String(64), nullable=False),
        description="城市"
    )

    # 是否购买域名：BOOLEAN 非空，默认False
    is_buy_domain: bool = Field(
        default=False,
        sa_column=Column("is_buy_domain", Boolean, nullable=False, default=False),
        description="是否购买域名"
    )

    # 域名名称：VARCHAR(255) 可为空
    domain_name: Optional[str] = Field(
        default=None,
        sa_column=Column("domain_name", String(255), nullable=True),
        description="域名名称"
    )

    # 域名分组：VARCHAR(100) 可为空
    domain_group: Optional[str] = Field(
        default=None,
        sa_column=Column("domain_group", String(100), nullable=True),
        description="域名分组"
    )

    # 实际链接：VARCHAR(255) 可为空
    real_url: Optional[str] = Field(
        default=None,
        sa_column=Column("real_url", String(255), nullable=True),
        description="实际链接"
    )

    # 标题：VARCHAR(64) 可为空
    title: Optional[str] = Field(
        default=None,
        sa_column=Column("title", String(64), nullable=True),
        description="标题"
    )

    rank: Decimal = Field(
        max_digits=20,
        decimal_places=2,
        description="排名"

    )



class DomainMonitorTable(CommonMixin, SiteDomainMonitorBase, table=True):
    """域名监控表"""
    __tablename__ = "site_domain_monitor"