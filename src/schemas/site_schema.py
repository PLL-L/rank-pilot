from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator, model_validator, validator

from src.utils.tools import parse_datetime


class DomainQueryParams(BaseModel):
    """域名列表查询参数模型"""
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)
    domain_name_list: Optional[List[str]] = Field(None, max_length=5,description="域名列表支持多选")
    domain_group: Optional[str] = Field(None, max_length=16, description="域名分组筛选")
    server_number: Optional[str] = Field(None, max_length=16, description="服务器信息筛选")
    baidu_site_account: Optional[str] = Field(None, max_length=32, description="百度站平号筛选")
    is_baidu_verified: Optional[bool] = Field(None, description="是否通过百度认证")
    sort_order: Optional[str] = Field(
        "desc",
        description="排序顺序，默认desc",
        pattern="^(asc|desc)$",
    )

class DomainMonitorQueryParams(BaseModel):
    """域名监控查询参数模型"""
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)
    platforms: List[str] = Field(
        ...,
        description="平台列表，必须，可多选，默认百度PC+百度M"
    )
    keyword: Optional[str] = Field(None, description="关键词，支持模糊查询")
    domain_names: Optional[List[str]] = Field(None, description="域名列表，可选，多选，完全匹配")
    is_buy_domain: Optional[bool] = Field(None, description="是否自购域名，可选")
    rank_min: Optional[int] = Field(None, ge=1,  description="最小排名，最小1")
    rank_max: Optional[int] = Field(None, ge=1,  description="最大排名，最小1")
    created_at_start: Optional[str] = Field(None, description="开始时间，格式：YYYY-MM-DD HH:MM:SS")
    created_at_end: Optional[str] = Field(None, description="结束时间，格式：YYYY-MM-DD HH:MM:SS")
    sort_order: Optional[str] = Field(
        "desc",
        description="排序顺序，默认desc",
        pattern="^(asc|desc)$"
    )



class AccountListRequest(BaseModel):
    """站平账号列表查询请求模型"""
    domain_names: Optional[List[str]] = Field(None,
                                              description="域名列表，精确匹配",
                                              max_length=5,
                                              )
    platforms: List[str] = Field(
        default_factory=list,
        description="平台列表，必须，可多选，默认百度",

    )
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)
    sort_order: Optional[str] = Field(
        "desc",
        description="排序顺序，默认desc",
        pattern="^(asc|desc)$"
    )
    @field_validator('domain_names','platforms')
    @classmethod
    def clean_domain_names(cls, v):
        """清理域名列表：去除空字符串和两端空格"""
        if v is None:
            return None

        # 如果是字符串列表，清理每个字符串
        if isinstance(v, list):
            # 去除两端空格，并过滤掉空字符串
            cleaned = [item.strip() for item in v if item is not None and str(item).strip()]
            # 如果清理后列表为空，返回 None
            return cleaned if cleaned else None

        return v

class TrendListRequest(BaseModel):
    """趋势图数据查询请求模型"""
    domain_names: str = Field(None, description="用户域名输入")
    terminal_type: str = Field(..., pattern="^(PC|MOBILE)$", description="终端类型，例如：PC, MOBILE")
    start_time: Optional[str] = Field(..., description="开始时间，格式：YYYY-MM-DD")
    end_time: Optional[str] = Field(..., description="结束时间，格式：YYYY-MM-DD")

    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def validate_datetime_string(cls, v):
        """验证日期时间字符串格式"""
        return parse_datetime(v)


class DomainMonitorPushRequest(BaseModel):
    """域名监控任务结果获取"""
    file_url: Optional[str] = Field(None, description="文件地址")
    file_name: Optional[str] = Field(None, description="文件名称")
    job_id_list: Optional[List[int]] = Field(..., description="job id")
    # execution_time: Optional[str] = Field(..., description="执行时间")


class AccountInfo(BaseModel):
    """站平账号信息模型 (用于推送)"""
    account_number: str = Field(description="站平账号")
    account_status: str = Field(description="账号状态")
    cookie: dict = Field(None, description="登陆后的cookie信息")
    domain_list: Optional[List[str]] = Field(None, description="账号关联的域名列表")
    managed_domain_count: int = Field(default=0, description="已管理的域名数量")


class DomainPushInfo(BaseModel):
    """域名推送信息模型"""
    domain_name: str = Field(description="域名名称")
    is_verified: bool = Field(description="是否已认证")
    push_token: str = Field(description="推送用的Token")
    account_number: str = Field(description="关联的站平账号")

class FileInfo(BaseModel):
    keyword_page: str = Field(description="关键词、热点数据 PC/M")
    chart: str = Field(description="趋势图 PC/M")


class TrafficMonitorPushRequest(BaseModel):
    """
    流量监控任务结果推送请求模型
    - 注意：JSON中的 `accont_info` 字段有拼写错误，这里使用正确的 `account_info`
    """
    account_info: AccountInfo = Field(description="站平账号的详细信息")
    file_info: FileInfo = Field(None, description="文件信息")
    domain_info_list: List[DomainPushInfo] = Field(description="本次任务处理的域名详细信息列表")


class TrafficMonitorListRequest(BaseModel):
    """流量监控列表查询请求模型"""
    domain_names: Optional[List[str]] = Field(None, description="域名列表，精确匹配",max_items=5)
    keywords: Optional[str] = Field(None, description="关键词列表，模糊匹配")
    execution_time: Optional[List[datetime]] = Field(None, description="日期范围 [start_time, end_time]")
    business_type: str = Field(..., min_length=1, description="业务类型")
    terminal_type: str = Field(..., min_length=1, description="终端类型")
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)
