import decimal
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel

from src.defined.site import TerminalTypeEnum, BusinessTypeEnum
from src.models.mixins import CommonMixin




class SiteTrafficMonitorBase(SQLModel):
    """
    流量监控基础模型
    """
    keyword: str = Field(default="", max_length=128, description="关键词")
    page: str = Field(default="", max_length=128, description="热门页面")
    domain_name: str = Field(max_length=255, description="域名名称")
    clicks: int = Field(default=0, description="点击量")
    impressions: int = Field(default=0, description="展现量")
    terminal_type: str = Field(default=TerminalTypeEnum.PC, max_length=100, description="终端类型")
    business_type: str = Field(default=BusinessTypeEnum.KEYWORD, max_length=128, description="业务类型")


    # 使用 sa_column 来精确定义 NUMERIC 类型
    ctr: Decimal = Field(
        default=0.0,
        sa_column=Column(Numeric(20, 2), nullable=False, default=0.0),
        description="点击率"
    )

    rank: Decimal = Field(
        max_digits=20,
        decimal_places=2,
        description="排名"

    )


class TrafficMonitorTable(CommonMixin, SiteTrafficMonitorBase, table=True):
    """
    流量监控表模型
    """
    __tablename__ = "site_traffic_monitor"