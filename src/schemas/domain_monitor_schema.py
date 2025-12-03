from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class DomainMonitorQueryParams(BaseModel):
    """域名监控查询参数模型"""
    platforms: List[str] = Field(
        ["BAIDU_PC", "BAIDU_M"],
        description="平台列表，必须，可多选，默认百度PC+百度M"
    )
    keywords: Optional[List[str]] = Field(
        None,
        description="关键词列表，可多选，支持模糊查询"
    )
    domain_names: Optional[List[str]] = Field(
        None,
        description="域名列表，可多选，完全匹配"
    )
    is_buy_domain: Optional[bool] = Field(
        None,
        description="是否自购域名"
    )
    rank_range: Optional[tuple[int, int]] = Field(
        [1,100],
        description="排名范围，按[min,max]传，例：rank_range=1,10"
    )
    created_at_range: Optional[tuple[datetime, datetime]] = Field(
        (datetime(2025, 11, 1,0,0,0), datetime(2025, 12, 1,23,59,59)),
        description="执行时间范围，按[start,end]传，UTC ISO格式，例：created_at_range=2025-11-01T00:00:00Z,2025-12-01T00:00:00Z"
    )

    @field_validator('rank_range', mode='before')
    @classmethod
    def parse_rank_range(cls, v):
        if v in (None, ''):
            return None
        if isinstance(v, (tuple, list)) and len(v) == 2:
            return tuple(v)
        if isinstance(v, str):
            s = v.strip()
            if s.startswith('[') and s.endswith(']'):
                try:
                    import json
                    arr = json.loads(s)
                    if isinstance(arr, list) and len(arr) == 2:
                        return tuple(arr)
                except Exception:
                    pass
            parts = [p.strip() for p in s.split(',') if p.strip() != '']
            if len(parts) == 2:
                try:
                    return (int(parts[0]), int(parts[1]))
                except Exception:
                    return v
        return v

    @field_validator('created_at_range', mode='before')
    @classmethod
    def parse_created_at_range(cls, v):
        if v in (None, ''):
            return None
        if isinstance(v, (tuple, list)) and len(v) == 2:
            return tuple(v)
        if isinstance(v, str):
            s = v.strip()
            if s.startswith('[') and s.endswith(']'):
                try:
                    import json
                    arr = json.loads(s)
                    if isinstance(arr, list) and len(arr) == 2:
                        return tuple(arr)
                except Exception:
                    pass
            parts = [p.strip() for p in s.split(',') if p.strip() != '']
            if len(parts) == 2:
                return (parts[0], parts[1])
        return v

class DomainMonitorTestDataRequest(BaseModel):
    """域名监控测试数据创建请求模型"""
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
