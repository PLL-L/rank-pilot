from datetime import datetime
from typing import Optional, Literal
from pydantic import field_validator
from sqlalchemy import Column, String, SMALLINT, NUMERIC, TIMESTAMP, text, Index, Integer
from sqlmodel import SQLModel, Field

from src.models.mixins import TimestampMixin

# 定义平台类型
PlatformType = Literal['百度PC', '百度M', '360PC', '360M']


class KeywordSearchConfigBase(SQLModel):
    """关键词搜索配置基础模型"""
    keyword: str = Field(
        min_length=1,
        max_length=128,
        sa_column=Column(String(128), nullable=False, comment="搜索关键词（128字符，支持表情包）"),
        description="搜索关键词，不超过128字符，支持表情包"
    )
    platform: PlatformType = Field(
        sa_column=Column(String(10), nullable=False, comment="搜索平台（百度PC/百度M/360PC/360M）"),
        description="搜索平台，可选值：百度PC、百度M、360PC、360M"
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
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True, comment="关键词最近一次执行时间"),
        description="关键词最近一次执行时间"
    )
    created_uid: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True, comment="创建人ID"),
        description="创建该记录的用户ID"
    )
    updated_uid: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True, comment="更新人ID"),
        description="最后更新该记录的用户ID"
    )
    @field_validator('keyword')
    @classmethod
    def validate_keyword(cls, v: str) -> str:
        """验证关键词"""
        if not v:
            raise ValueError('关键词不能为空')
        v = v.strip()
        if not v:
            raise ValueError('关键词不能为空')
        if len(v) > 128:
            raise ValueError('关键词不能超过128个字符')
        return v

    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """验证平台"""
        valid_platforms = ['百度PC', '百度M', '360PC', '360M']
        if v not in valid_platforms:
            raise ValueError(f'平台必须是以下之一：{", ".join(valid_platforms)}')
        return v

    @field_validator('city')
    @classmethod
    def validate_city(cls, v: Optional[str]) -> Optional[str]:
        """验证城市"""
        if v is not None:
            v = v.strip()
            if len(v) > 64:
                raise ValueError('城市名称不能超过64个字符')
        return v

    @field_validator('mobile_search_depth')
    @classmethod
    def validate_mobile_search_depth(cls, v: Optional[int]) -> Optional[int]:
        """验证移动端搜索深度"""
        if v is not None:
            if v < 0:
                raise ValueError('移动端搜索深度必须大于等于0')
            if v >= 500:
                raise ValueError('移动端搜索深度必须小于500')
        return v

    @field_validator('pc_search_depth')
    @classmethod
    def validate_pc_search_depth(cls, v: Optional[int]) -> Optional[int]:
        """验证PC端搜索深度"""
        if v is not None:
            if v < 0:
                raise ValueError('PC端搜索深度必须大于等于0')
            if v >= 500:
                raise ValueError('PC端搜索深度必须小于500')
        return v

    @field_validator('execute_cycle')
    @classmethod
    def validate_execute_cycle(cls, v: float) -> float:
        """验证执行周期"""
        if v < 0:
            raise ValueError('执行周期必须大于等于0')
        # 限制为1位小数
        return round(v, 1)

    @field_validator('remark')
    @classmethod
    def validate_remark(cls, v: Optional[str]) -> Optional[str]:
        """验证备注信息"""
        if v is not None:
            v = v.strip()
            if len(v) > 64:
                raise ValueError('备注信息不能超过64个字符')
        return v


class KeywordSearchConfigTable(TimestampMixin,KeywordSearchConfigBase, table=True):
    """关键词搜索配置表模型"""
    __tablename__ = "keyword_search_config"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    __table_args__ = (
        Index('idx_keyword_like', 'keyword', postgresql_ops={'keyword': 'varchar_pattern_ops'}),
        Index('idx_platform', 'platform'),
        Index('idx_remark_like', 'remark', postgresql_ops={'remark': 'varchar_pattern_ops'}),
        Index('idx_keyword_platform', 'keyword', 'platform'),
        Index('idx_create_time', 'created_at'),
        Index('idx_last_execute_time', 'last_execute_time'),
    )

