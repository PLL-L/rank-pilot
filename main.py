import logging

import uvicorn

from src.app import create_app
from src.config import settings
from src.core.log.logger import init_logger

init_logger(
    intercept_std_logging=True,
    level=logging.INFO,
)
app = create_app()




if __name__ == "__main__":
    config = uvicorn.Config(
        app=app,
        host=settings.FASTAPI_CONFIG.HOST.__str__(),
        port=settings.FASTAPI_CONFIG.PORT,
        lifespan="on",
        reload=settings.system.DEBUG,
        access_log=False,  # 关闭日志
        # log_level="info",
        workers=1
    )
    server = uvicorn.Server(config=config)
    # 设置日志
    server.run()