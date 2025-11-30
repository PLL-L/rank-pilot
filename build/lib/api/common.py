from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from src.api.base import BaseController
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Response

from src.core import logger
from src.core.mq import aio_mq
from src.defined.mq_routing_key import MqRoutingKey
from src.service.common import CommonService

common_bp = APIRouter()


@cbv(common_bp)
class CommonController(BaseController):
    common_service: CommonService = Depends(CommonService)

    @common_bp.get("/metrics", description="普罗米修斯监控")
    async def metrics(self):
        return Response(
            content=generate_latest(),  # 生成当前所有指标的 prometheus 文本格式内容
            media_type=CONTENT_TYPE_LATEST  # 设置正确的 Content-Type，通常为 "text/plain; version=0.0.4"
        )


    @common_bp.get("/demo/test", description="演示接口")
    async def demos(self, ):
        logger.info(123)
        await aio_mq.publish(routing_key=MqRoutingKey.TEST_QUEUE, msg={"123": "213"})
        return self.success("演示")

    @common_bp.get("/demo/{id}", description="演示接口")
    async def demo(self, id: int ):
        res = await self.common_service.demo(id)
        return self.success("演示",data=res)