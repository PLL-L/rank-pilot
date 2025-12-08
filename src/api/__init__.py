"""
路由配置
"""
from fastapi import FastAPI

from src.api.common import common_bp
from src.api.site import site_bp
# from src.api.fingerprint import fingerprint_bp

from src.config import settings

router_list = [
    {"router": common_bp, "prefix": "/common"},
    {"router": site_bp, "prefix": "/site", "tag": "域名管理"},
    # {"router": fingerprint_bp, "prefix": "/fingerprint", "tag": "指纹账号"},
]

def setup_routes(app: FastAPI):
    for router_config in router_list:
        app.include_router(
            router_config["router"],
            prefix=f"{settings.system.API_V1_STR}{router_config['prefix']}",
            tags=[router_config.get("tag", "")],
        )
