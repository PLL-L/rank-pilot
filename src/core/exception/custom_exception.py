#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/2/19 14:12
# @Author  : YueXia
# @File    : custom_exception.py
# @Description : 自定义异常
from src.defined.http_code import HttpCode


class BaseException(Exception):
    """应用异常基类"""

    def __init__(
        self,
        exc: HttpCode = None,
        code: int = 400,
        msg: str = "错误",
        status_code: int = 200,
        # echo_exc: bool = False,
        # **kwargs,
    ):
        super().__init__()
        # 判断是否自定义异常，是返回自定义的异常，否则返回其他异常状态
        if exc:
            code, msg = exc.code, exc.msg
        self._code = code
        self._message = msg
        self._status_code = status_code
        # self.echo_exc = echo_exc
        # self.args = args or []
        # self.kwargs = kwargs or {}

    @property
    def code(self) -> int:
        return self._code

    @property
    def msg(self) -> str:
        return self._message

    @property
    def status_code(self) -> int:
        return self._status_code

    def __str__(self):
        return "{}: {}".format(self.code, self.msg)



class GlobalErrorCodeException(BaseException):
    """服务层异常基类"""
    pass



class ParamsErrorCodeException(BaseException):
    """参数异常异常基类"""
    def __init__(self, msg, code = None):
        super().__init__()
        self._code = code or HttpCode.PARAMS_VALID_ERROR.code
        self._message = msg
