from enum import Enum
from typing import Optional, List, Any, Dict
from datetime import datetime

from sqlalchemy import ARRAY, String, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from src.defined.site import AccountStatus
from src.models.mixins import CommonMixin


# class AccountStatus(str, Enum):
#     """
#     账号状态枚举
#     """
#     INIT = "init"
#     NORMAL = "normal"
#     LOGIN_FAILED = "login_failed"


class SitePlatformAccountBase(SQLModel):
    """
    站平账号基础模型
    """
    platform: str = Field(default="pc", max_length=50, description="平台：百度/360")
    account_number: str = Field(max_length=128, description="用户名")
    password: str = Field(max_length=128, description="密码")
    status: str = Field(default="init", max_length=20, description="账号状态")
    # cookie: Optional[str] = Field(default=None, description="登陆后的cookie信息")
    cookie: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="登陆后的cookie信息"
    )
    last_check_time: Optional[datetime] = Field(default=None, description="上次检查时间")
    managed_domain_count: int = Field(default=0, description="已管理域名数")

    # 使用 sa_column 来指定 PostgreSQL 的 TEXT[] 数组类型
    domain_list: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(ARRAY(String)),
        description="域名列表"
    )


class PlatformAccountTable(CommonMixin, SitePlatformAccountBase, table=True):
    """
    站平账号表模型
    """
    __tablename__ = "site_platform_account"