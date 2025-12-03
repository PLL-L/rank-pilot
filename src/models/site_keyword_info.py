from datetime import datetime
from typing import Optional, Literal

from sqlalchemy import Column, String, SMALLINT, NUMERIC, TIMESTAMP, Integer
from sqlmodel import SQLModel, Field

from src.models.mixins import CommonMixin

# 定义平台类型
PlatformType = Literal['BAIDU_PC', 'BAIDU_M', '360PC', '360M']


class KeywordInfoBase(SQLModel):
    """关键词搜索配置基础模型"""
    keyword: str = Field(
        min_length=1,
        max_length=128,
        sa_column=Column(String(128), nullable=False, comment="搜索关键词（128字符，支持表情包）"),
        description="搜索关键词，不超过128字符，支持表情包"
    )
    platform: PlatformType = Field(
        sa_column=Column(String(10), nullable=False, comment="搜索平台（BAIDU_PC/BAIDU_M/360PC/360M）"),
        description="搜索平台，可选值：BAIDU_PC、BAIDU_M、360PC、360M"
    )
    city: Optional[str] = Field(
        default=None,
        max_length=64,
        sa_column=Column(String(64), nullable=True, comment="搜索城市中文（国标GB/T 2260-2007，可空）"),
        description="搜索城市，遵循国标GB/T 2260-2007，不超过64个字符"
    )
    mobile_search_depth: Optional[int] = Field(
        default=None,
        sa_column=Column(SMALLINT, nullable=True, comment="移动端搜索深度（<500）"),
        description="移动端搜索深度，必须小于500且大于等于0"
    )
    pc_search_depth: Optional[int] = Field(
        default=None,
        sa_column=Column(SMALLINT, nullable=True, comment="PC端搜索深度（<500）"),
        description="PC端搜索深度，必须小于500且大于等于0"
    )
    execute_cycle: float = Field(
        sa_column=Column(NUMERIC(4, 1), nullable=False, comment="执行周期（小时，支持1位小数）"),
        description="执行周期（单位：小时），支持1位小数，必须大于等于0"
    )
    remark: Optional[str] = Field(
        default=None,
        max_length=64,
        sa_column=Column(String(64), nullable=True, comment="备注信息（64字符）"),
        description="备注信息，不超过64个字符"
    )
    last_execute_time: Optional[datetime] = Field(
        default=None,
        # sa_column=Column(TIMESTAMP(timezone=True), nullable=True, comment="关键词最近一次执行时间"),
        description="关键词最近一次执行时间"
    )



class KeywordInfoTable(CommonMixin, KeywordInfoBase, table=True):
    """关键词搜索配置表模型"""
    __tablename__ = "site_keyword_info"
