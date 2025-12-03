from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Optional, List


class DomainQueryParams(BaseModel):
    """域名查询参数模型"""
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)
    domain_name: Optional[str] = Field(None, description="域名名称筛选")
    domain_group: Optional[str] = Field(None, description="域名分组筛选")
    server_info: Optional[str] = Field(None, description="服务器ID筛选")
    main_domain: Optional[str] = Field(None, description="主域名筛选")
    baidu_site_account: Optional[str] = Field(None, description="百度站平号筛选")
    is_baidu_verified: Optional[bool] = Field(None, description="是否通过百度认证")

    # 避免错误：将空字符串转换为 None
    @field_validator('is_baidu_verified', mode='before')
    @classmethod
    def validate_is_baidu_verified(cls, v):
        """将空字符串转换为 None"""
        if v == '' or v is None:
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ('true', '1', 'yes'):
                return True
            if v_lower in ('false', '0', 'no'):
                return False
        return v


class DomainListRequest(BaseModel):
    """域名列表查询请求模型"""
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)
    domain_name: Optional[str] = Field(None, description="域名名称筛选")
    domain_group: Optional[str] = Field(None, description="域名分组筛选")
    server_id: Optional[str] = Field(None, description="服务器ID筛选")
    main_domain: Optional[str] = Field(None, description="主域名筛选")


class DomainMonitorPushRequest(BaseModel):
    """域名监控任务结果获取"""
    file_url: Optional[str] = Field(None, description="文件地址")
    file_name: Optional[str] = Field(None, description="文件名称")
    job_id_list: Optional[List[int]] = Field(..., description="job id")
    execution_time: Optional[str] = Field(..., description="执行时间")


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
    domain_names: Optional[List[str]] = Field(None, description="域名列表，精确匹配")
    keywords: Optional[List[str]] = Field(None, description="关键词列表，模糊匹配")
    date_range: Optional[List[datetime]] = Field(None, description="日期范围 [start_time, end_time]")
    business_type: str = Field(description="业务类型")
    terminal_type: str = Field(description="终端类型")
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)


class DomainMonitorQueryParams(BaseModel):
    """域名监控查询参数模型"""
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)
    platforms: List[str] = Field(
        ["BAIDU_PC", "BAIDU_M"],
        description="平台列表，必须，可多选，默认百度PC+百度M"
    )
    keywords: Optional[List[str]] = Field(None, description="关键词列表，可选，多选，支持模糊查询")
    domain_names: Optional[List[str]] = Field(None, description="域名列表，可选，多选，完全匹配")
    is_buy_domain: Optional[bool] = Field(None, description="是否自购域名，可选")
    rank_min: Optional[int] = Field(None, description="最小排名，可选")
    rank_max: Optional[int] = Field(None, description="最大排名，可选")
    created_at_start: Optional[str] = Field(None, description="开始时间，格式：YYYY-MM-DD HH:MM:SS")
    created_at_end: Optional[str] = Field(None, description="结束时间，格式：YYYY-MM-DD HH:MM:SS")


class AccountListRequest(BaseModel):
    """站平账号列表查询请求模型"""
    domain_names: Optional[List[str]] = Field(None, description="域名列表，精确匹配")
    platforms: List[str] = Field(
        ["BAIDU"],
        description="平台列表，必须，可多选，默认百度PC"
    )
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)


class TrendListRequest(BaseModel):
    """趋势图数据查询请求模型"""
    domain_names: str = Field('www.lumianzhizhuanji.com', description="用户域名输入")
    terminal_type: str = Field('PC', description="终端类型，例如：PC, MOBILE")
    time_label: str = Field(default="today", description="时间标签，例如：today, 7d, 30d")
    start_time: Optional[str] = Field(None, description="开始时间，格式：YYYY-MM-DD HH:MM:SS")
    end_time: Optional[str] = Field(None, description="结束时间，格式：YYYY-MM-DD HH:MM:SS")

    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def validate_datetime_string(cls, v, info: ValidationInfo):
        """验证日期时间字符串格式"""
        try:
            # 支持多种格式
            if 'T' in v:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            else:
                datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
            return v
        except ValueError:
            raise ValueError(f"{info.field_name} 格式无效，应为 YYYY-MM-DD HH:MM:SS 或 ISO 格式")
