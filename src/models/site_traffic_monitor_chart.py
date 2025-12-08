from datetime import date
from typing import Optional, Dict, Any

from sqlalchemy import Column, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.defined.site import TerminalTypeEnum, BusinessTypeEnum
from src.models.mixins import CommonMixin


class SiteTrafficMonitorChartBase(SQLModel):
    """
    流量监控图表基础模型
    """
    domain_name: str = Field(max_length=255, description="域名名称")
    clicks: int = Field(default=0, description="点击量")
    impressions: int = Field(default=0, description="展现量")

    reference_number: str = Field(max_length=255, description="参考编号")

    hour_info: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="每日小时数据"
    )
    execution_date: date = Field(
        sa_type=Date,  # 指定数据库类型为 DATE
        sa_column_kwargs={"nullable": False},  # 数据库层面设为 NOT NULL
        description="执行日期"
    )
    # 将类型注解改为 str，以匹配数据库中的 VARCHAR 类型
    # Pydantic 仍然会使用 TerminalTypeEnum 来校验传入的值
    terminal_type: str = Field(
        default=TerminalTypeEnum.PC,
        max_length=100,
        description="终端类型"
    )


class TrafficMonitorChartTable(CommonMixin, SiteTrafficMonitorChartBase, table=True):
    """
    流量监控图表数据表模型
    """
    __tablename__ = "site_traffic_monitor_chart"