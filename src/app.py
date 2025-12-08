"""
FastAPI 应用主入口文件 - 使用 SQLModel
"""
from fastapi import FastAPI

from src.api import setup_routes
from src.core import logger
from src.config import settings
from src.core.exception.exception_handler import setup_exception_handlers
from src.core.middlewares import setup_middleware
from src.core.lifespan import lifespan
from src.core.middlewares.log_middleware import LoggingJSONResponse


def create_app() -> FastAPI:
    host = str(settings.FASTAPI_CONFIG.HOST)
    port = settings.FASTAPI_CONFIG.PORT
    server_address = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"

    serving_str = f"\nAPI Server URL:http://{host}:{port}"
    serving_str += f"\nSwagger UI Docs:{server_address}/docs"
    serving_str += f"\nRedoc HTML Docs:{server_address}/redoc"
    serving_str += f"\n配置文件路径: {settings.model_config['yaml_file']}"

    logger.info(serving_str)

    # 创建 FastAPI 应用实例
    app = FastAPI(
        title=settings.FASTAPI_CONFIG.TITLE,
        description=settings.FASTAPI_CONFIG.DESCRIPTION,
        version=settings.FASTAPI_CONFIG.VERSION,
        lifespan=lifespan,
        openapi_url=f"{settings.system.API_V1_STR}/openapi.json",
        default_response_class=LoggingJSONResponse
    )

    # 配置异常处理器
    setup_exception_handlers(app)

    # 配置中间件
    setup_middleware(app)

    # 配置路由
    setup_routes(app)

    return app