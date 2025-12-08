from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class KeywordQueryParams(BaseModel):
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)
    """关键词查询参数模型"""
    platforms: List[str] = Field(
        ...,
        description="平台列表，必须，可多选，默认百度PC+百度M"
    )
    keyword: Optional[str] = Field(
        None,
        description="支持模糊查询",
    )
    remark: Optional[str] = Field(
        None,
        description="备注信息，支持模糊查询"
    )
    sort_by: Optional[str] = Field(
        "last_execute_time",
        description="排序字段，默认最后执行时间,可选创建时间(created_at)"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="排序顺序，默认desc"
    )
    @field_validator("keyword", "remark")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """对keyword和remark字段进行去空格预处理"""
        if v is not None:
            return v.strip()
        return v

class KeywordDeleteRequest(BaseModel):
    """关键词删除请求模型"""
    ids: list[int] = Field(
        ...,
        description="要删除的关键词ID列表"
    )


class KeywordTestDataRequest(BaseModel):
    """关键词测试数据创建请求模型"""
    count: int = Field(
        10,
        ge=1,
        le=1000,
        description="创建数量，范围1-1000"
    )
    created_uid: Optional[int] = Field(
        None,
        description="创建人ID"
    )