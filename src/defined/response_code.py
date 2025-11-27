# @Version        : 1.0
# @Create Time    : 2024/5/7 17:20
# @File           : response_code.py
# @IDE            : PyCharm
# @Desc           : 常用的响应状态码（响应体 Code）


class Status:
    """
    HTTP 状态码大全：https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Status
    """

    HTTP_SUCCESS = 200  # OK 请求成功
    HTTP_ERROR = 400  # BAD_REQUEST 因客户端错误的原因请求失败
    HTTP_401 = 401  # UNAUTHORIZED: 未授权
    HTTP_403 = 403  # FORBIDDEN: 禁止访问
    HTTP_404 = 404  # NOT_FOUND: 未找到
    HTTP_405 = 405  # METHOD_NOT_ALLOWED: 方法不允许
    HTTP_408 = 408  # REQUEST_TIMEOUT: 请求超时
    HTTP_500 = 500  # INTERNAL_SERVER_ERROR: 服务器内部错误
    HTTP_502 = 502  # BAD_GATEWAY: 错误的网关
    HTTP_503 = 503  # SERVICE_UNAVAILABLE: 服务不可用
