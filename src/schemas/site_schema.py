from pydantic import BaseModel, Field
from typing import Optional
# 请求模型
class DomainCreateRequest(BaseModel):
    """创建域名请求模型"""
    domain_name: str = Field(..., description="域名名称", min_length=1, max_length=255)
    domain_group: Optional[str] = Field(None, description="域名分组", max_length=16)
    server_id: Optional[str] = Field(None, description="服务器ID", max_length=16)
    remark: Optional[str] = Field(None, description="备注信息", max_length=64)

class DomainListRequest(BaseModel):
    """域名列表查询请求模型"""
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)
    domain_name: Optional[str] = Field(None, description="域名名称筛选")
    domain_group: Optional[str] = Field(None, description="域名分组筛选")
    server_id: Optional[str] = Field(None, description="服务器ID筛选")
    main_domain: Optional[str] = Field(None, description="主域名筛选")

class DomainSearchRequest(BaseModel):
    """域名搜索请求模型"""
    keyword: str = Field(..., description="搜索关键词", min_length=1)
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(10, description="每页大小", ge=1, le=100)

class TestDataRequest(BaseModel):
    """测试数据插入请求模型"""
    count: int = Field(10, description="插入数据数量", ge=1, le=100)