from typing import Optional

from sqlalchemy import Column, String, Integer, Boolean
from sqlmodel import SQLModel, Field

from src.models.mixins import CommonMixin


class DomainInfoBase(SQLModel):
    """域名信息基础模型"""
    domain_name: Optional[str] = Field(
        min_length=1,
        max_length=255,
        sa_column=Column(String(255), nullable=False, comment="域名信息"),
        description="用户录入的域名信息，前后去空格，需要校验域名的合法性"
    )
    main_domain: Optional[str] = Field(
        default=None,
        max_length=255,
        sa_column=Column(String(255), nullable=True, comment="主域名"),
        description="自动根据域名计算出来的主域名"
    )
    domain_group: Optional[str] = Field(
        default=None,
        max_length=16,
        sa_column=Column(String(16), nullable=True, comment="域名分组"),
        description="用户自定义的域名分组信息，不超过16个字符"
    )
    server_number: Optional[str] = Field(
        default=None,
        max_length=16,
        sa_column=Column(String(16), nullable=True, comment="服务器ID"),
        description="所在服务器信息，用户录入的字符串信息，不超过16个字符"
    )
    remark: Optional[str] = Field(
        default=None,
        max_length=64,
        sa_column=Column(String(64), nullable=True, comment="备注信息"),
        description="用户的备注信息，不超过64个字符"
    )
    account_number: Optional[str] = Field(
        default=None,
        max_length=32,
        sa_column=Column(String(32), nullable=True, comment="百度站平号"),
        description="百度站长平台账号名，不超过32个字符，站平账号检查时主动上传，上传后实时更新"
    )
    is_verified: Optional[bool] = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True, comment="是否通过百度认证"),
        description="是否通过百度站长平台认证"
    )
    push_token: Optional[str] = Field(
        default=None,
        max_length=32,
        sa_column=Column(String(32), nullable=True, comment="百度站长token"),
        description="百度站长平台token，不超过32个字符，站平账号检查时主动上传"
    )



class DomainInfoTable(CommonMixin, DomainInfoBase, table=True):
    """域名信息表模型"""
    __tablename__ = "site_domain_info"
