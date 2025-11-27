# @Version        : 1.0
# @Update Time    : 2025/2/8 22:01
# @File           : base_controller.py
# @IDE            : PyCharm
# @Desc           : 基础控制器，提供通用的响应处理和用户信息获取功能

from typing import Optional, TypeVar, Any, Union
from fastapi import Request

from src.defined.http_code import HttpCode
from src.schemas.response_schema import ResponseSchema, ResponseGenericSchema, PageResponseDataSchema

DataT = TypeVar("DataT", bound=Optional[Any])
11111

class BaseController:
    """基础控制器类，提供通用的响应处理和用户信息获取功能"""

    request: Request

    @staticmethod
    def _response(
        *,
        data: DataT = None,
        resp: HttpCode = HttpCode.SUCCESS,
        msg: Optional[str] = None,
        code: Optional[int] = None,
        success: bool = True,
    ) -> Union[ResponseSchema, ResponseGenericSchema]:
        """
        构建统一响应格式

        Args:
            data: 响应数据
            resp: HTTP响应码枚举
            msg: 响应消息
            code: 响应状态码

        Returns:
            Union[ResponseSchema, ResponseGenericSchema]: 统一响应对象
        """
        return ResponseSchema(
            code=code or resp.code, msg=msg or resp.msg, data=data, success=success
        )

    def success(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[int] = None,
        data: DataT = None,
        resp: HttpCode = HttpCode.SUCCESS,
    ) -> ResponseSchema:
        """
        成功响应

        Args:
            message: 响应消息
            code: 响应状态码
            data: 响应数据
            resp: HTTP响应码枚举

        Returns:
            ResponseSchema: 成功响应对象
        """
        return self._response(data=data, resp=resp, msg=message, code=code)

    def error(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[int] = None,
        data: DataT = None,
        fail: HttpCode = HttpCode.FAILED,
    ) -> ResponseSchema:
        """
        错误响应

        Args:
            message: 响应消息
            code: 响应状态码
            data: 响应数据
            fail: HTTP响应码枚举

        Returns:
            ResponseSchema: 错误响应对象
        """
        return self._response(data=data, resp=fail, msg=message, code=code)

    def paginated_response(
        self,
        data: Optional[DataT] = None,
        total: int = 0,
        current: int = 1,
        size: int = 10,
        msg: Optional[str] = "操作成功",
    ) -> ResponseGenericSchema:
        """
        分页响应

        Args:
            data: 分页数据
            total: 总记录数
            current: 当前页码
            size: 每页大小
            msg: 响应消息

        Returns:
            ResponseGenericSchema: 分页响应对象
        """
        page_data = PageResponseDataSchema(
            records=data,
            total=total,
            current=current,
            size=size,
        )
        return self._response(data=page_data, msg=msg)

