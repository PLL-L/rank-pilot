#!/usr/bin/env python


from enum import Enum

__all__ = ["HttpCode"]


class HttpCode(Enum):
    # 成功类
    SUCCESS = (0, "成功")
    ADD_SUCCESS = (0, "添加成功")
    UPDATE_SUCCESS = (0, "修改成功")
    REMOVE_SUCCESS = (0, "删除成功")

    # 失败类
    FAILED = (400, "失败")
    ADD_FAILED = (400, "添加失败")
    UPDATE_FAILED = (400, "修改失败")
    REMOVE_FAILED = (400, "删除失败")
    PARAMS_VALID_ERROR = (400, "参数校验错误")
    PARAMS_TYPE_ERROR = (400, "参数类型错误")
    REQUEST_METHOD_ERROR = (400, "请求方法错误")
    ASSERT_ARGUMENT_ERROR = (400, "断言参数错误")


    # 错误类
    REQUEST_404_ERROR = (404, "请求接口不存在")
    HTTP_400_BAD_REQUEST = (400, "请求错误")
    TOO_MANY_REQUESTS = (429, "请勿频繁请求")

    # 系统错误
    SYSTEM_ERROR = (500, "系统错误")
    SYSTEM_GATEWAY = (501, "表示服务器作为网关或代理，从上游服务器收到了无效响应。")
    SYSTEM_TIMEOUT_ERROR = (504, "请求超时")

    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}: {self.code} - {self.msg}"

    def __str__(self):
        return f"{self.code}: {self.msg}"
