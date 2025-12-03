from typing import List, Optional
from pydantic import BaseModel, Field


class KeywordQueryParams(BaseModel):
    """关键词查询参数模型"""
    platforms: List[str] = Field(
        ["BAIDU_PC", "BAIDU_M"],
        description="平台列表，必须，可多选，默认BAIDU_PC+BAIDU_M"
    )
    keywords: Optional[List[str]] = Field(
        None,
        description="关键词列表，可多选，支持模糊查询"
    )
    remark: Optional[str] = Field(
        None,
        description="备注信息，支持模糊查询"
    )


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