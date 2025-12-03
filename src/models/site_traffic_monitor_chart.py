from typing import Optional, Dict, Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.defined.site import TerminalTypeEnum
from src.models.mixins import CommonMixin


class SiteTrafficMonitorChartBase(SQLModel):
    """
    流量监控图表基础模型
    """
    domain_name: str = Field(max_length=255, description="域名名称")
    clicks: int = Field(default=0, description="点击量")
    impressions: int = Field(default=0, description="展现量")

    # 使用 sa_column 来精确定义 PostgreSQL 的 JSONB 类型
    # 在 Python 代码中，可以将其作为字典（Dict）来处理
    hour_info: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="每日小时数据"
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