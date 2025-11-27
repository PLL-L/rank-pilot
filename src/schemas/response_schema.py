# @Version        : 1.0
# @Update Time    : 2024/6/16 1:05
# @File           : response_schema.py
# @IDE            : PyCharm
# @Desc           : 文件描述信息
# @Version        : 1.0
# @Create Time    : 2023/3/27 9:48
# @File           : response_schema.py
# @IDE            : PyCharm
# @Desc           : 全局响应
from datetime import datetime
from pydantic import Field
from typing import Generic, TypeVar, Sequence, Optional, Any
from fastapi_utils.api_model import APIModel

from src.defined.response_code import Status

DataT = TypeVar("DataT")


class ResponseSchema(APIModel):
    """
    默认响应模型
    """

    code: int = Field(Status.HTTP_SUCCESS, description="响应状态码（响应体内）")
    msg: str = Field("success", description="响应结果描述")
    data: Optional[Any] = Field(None, description="响应结果数据")
    success: bool = Field(True, description="是否成功")
    time: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="响应时间",
    )


# 可以设置泛型的输出模型
class ResponseGenericSchema(ResponseSchema, Generic[DataT]):
    """
    带有分页的响应模型
    """

    data: Optional[DataT] = Field(None, description="响应结果数据")


class PageResponseDataSchema(APIModel, Generic[DataT]):
    """
    带有分页的响应模型
    """

    records: Sequence[DataT] = Field([], description="响应结果数据")
    total: int = Field(0, description="总数据量")
    current: int = Field(1, description="当前页数")
    size: int = Field(10, description="每页多少条数据")


class PageResponse(ResponseSchema, Generic[DataT]):
    """
    带有分页的响应模型
    """

    data: Optional[PageResponseDataSchema[DataT]] = Field(None, description="响应结果数据")