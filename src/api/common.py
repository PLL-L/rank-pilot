from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi_utils.cbv import cbv

from src.api.base import BaseController
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Response

from src.core import logger
from src.core.mq import aio_mq
from src.defined.mq_routing_key import MqRoutingKey
from src.schemas.file_schema import FileImportRequest
from src.schemas.response_schema import ResponseSchema
from src.service.common import CommonService
from src.utils.alarm import alarm_robot
from src.utils.alarm.alarm_factory import AlarmFactory

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

    @common_bp.post(
        "/file/upload",
        summary="文件上传",
        description="文件上传",
        response_model=ResponseSchema,
    )
    async def upload_file(
            self,
            file: UploadFile = File(...),
    ):

        resul = await self.common_service.upload_file_to_minio(file)

        return self.success(data=resul)

    @common_bp.post(
        "/file/import/record",  # 路由地址
        summary="新增文件导入记录",
        description="保存文件导入的相关元数据",
        response_model=ResponseSchema,
    )
    async def file_import_record(self,request: FileImportRequest,):
        result = await self.common_service.create_file_import_record(request.model_dump())
        return self.success(data=result)



    @common_bp.get(
        "/enum/list",  # 路由地址
        summary="枚举列表",
        description="枚举列表接口",
        response_model=ResponseSchema,
    )
    async def enum_list(self):
        result = await self.common_service.enum_list()
        return self.success(data=result)