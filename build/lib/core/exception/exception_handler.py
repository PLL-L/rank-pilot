import traceback
# @Description :全局异常处理
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse

from starlette.responses import JSONResponse

from src.core import logger
from src.core.exception.custom_exception import  GlobalErrorCodeException
from src.utils.track_utils import TrackContextUtils


def filter_sensitive_info(data: dict[str, Any]) -> dict[str, Any]:
    """过滤敏感信息"""
    # 需要过滤的敏感字段
    sensitive_fields = {
        'password', 'token', 'access_token', 'refresh_token',
        'authorization', 'cookie', 'session'
    }

    filtered = {}
    for key, value in data.items():
        # 检查键名是否包含敏感字段
        if any(field in key.lower() for field in sensitive_fields):
            filtered[key] = '******'
        # 如果值是字典，递归过滤
        elif isinstance(value, dict):
            filtered[key] = filter_sensitive_info(value)
        # 如果值是列表，过滤列表中的字典
        elif isinstance(value, list):
            filtered[key] = [
                filter_sensitive_info(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            filtered[key] = value
    return filtered

def get_headers():
    return {"X-Request-ID": TrackContextUtils.get_request_id()}


async def get_request_info(request: Request) -> dict[str, Any]:
    """获取请求信息"""
    info = {
        "method": request.method,
        "url": str(request.url),
        "client_host": request.client.host if request.client else None,
        "path_params": request.path_params,
        "query_params": dict(request.query_params),
    }

    # 过滤请求头中的敏感信息
    headers = dict(request.headers)
    info["headers"] = filter_sensitive_info(headers)

    # 尝试获取请求体
    try:
        body = await request.body()
        if body:
            try:
                # 尝试解析为JSON并过滤敏感信息
                json_body = await request.json()
                if isinstance(json_body, dict):
                    info["body"] = filter_sensitive_info(json_body)
                else:
                    info["body"] = json_body
            except:
                # 如果不是JSON，则记录原始body
                info["body"] = body.decode('utf-8', errors='ignore')
    except:
        info["body"] = None

    return info


def setup_exception_handlers(app: FastAPI):

    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception):
        """
        全局异常处理
        :param request:
        :param exc:
        :return:
        """

        try:
            # 获取请求信息
            request_info = await get_request_info(request)
            # logger.exception(f"请求参数{request_info}, 未处理的异常: {exc}")
            # logger.error(f"请求参数{request_info}, 未处理的异常: {exc}")

            logger.info(f" global --- {traceback.format_exc()}")
        except Exception as log_exc:
            pass
            # logger.exception(f"记录异常信息时发生错误: {log_exc} 原始异常 {exc}")


        return JSONResponse(
            status_code=200,
            content={"msg": "服务器异常", "code": 500, "data": None},
            headers=get_headers(),
        )



    @app.exception_handler(GlobalErrorCodeException)
    async def global_error_exception_handler(request: Request, exc: GlobalErrorCodeException):
        """处理服务层异常"""
        logger.error(traceback.format_exc())
        logger.error(exc.__str__())

        return JSONResponse(
            status_code=200,
            content={"msg": exc.msg, "code": exc.code, "data": None},
            headers=get_headers(),
        )