import secrets
import string
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.db.db_database import transactional
from src.core.exception.custom_exception import GlobalErrorCodeException, ParamsErrorCodeException
from src.core.mq import aio_mq
from src.defined.file import  FileImportWorkType
from src.defined.mq_routing_key import MqRoutingKey
from src.models.config import ConfigTable
from src.models.file_record import FileRecordTable
from src.service.base import BaseService
from src.utils.file.strategy.minio_file import MinIOFileStrategy


class CommonService(BaseService):
    pass

    @transactional
    async def demo(self, id: int, session: AsyncSession):
        logger.info(f"123 - {id}")
        result = await session.get(ConfigTable, id)
        return result


    async def upload_file_to_minio(
        self,
        file: UploadFile,
        file_path: str = "test-files",
        use_random_filename: bool = False,
        custom_filename: Optional[str] = None
    ) -> dict:
        """
        上传文件到MinIO存储服务

        Args:
            file: FastAPI的UploadFile对象
            file_path: MinIO中的存储路径，默认为test-files/
            use_random_filename: 是否使用随机文件名，默认为False
            custom_filename: 自定义文件名，如果提供则优先使用

        Returns:
            dict: 包含文件上传结果的字典

        Raises:
            Exception: 上传失败时抛出异常
        """
        try:
            # 验证文件对象
            if not file or not file.filename:
                raise GlobalErrorCodeException(msg="文件对象或文件名为空")

            final_filename = file.filename
            # # 确定最终使用的文件名
            # final_filename = self._determine_filename(
            #     original_filename=file.filename,
            #     use_random=use_random_filename,
            #     custom_name=custom_filename
            # )

            # 初始化MinIO策略
            minio_strategy = MinIOFileStrategy()

            # 上传文件
            file_info = await minio_strategy.upload_file(
                file_content=file.file,
                file_path=file_path,
                file_name=final_filename,
                content_type=file.content_type,
                file_size=file.size
            )

            logger.info(f"文件上传成功: {final_filename} -> {file_info.get('url', 'N/A')}")
            return file_info

        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise GlobalErrorCodeException(msg=f"文件上传失败: {str(e)}")

    @transactional
    async def create_file_import_record(self, data: dict, session: AsyncSession):
        """
        创建文件导入记录
        """
        function_type = data.get("function_type")
        work_type = getattr(FileImportWorkType, function_type)
        if not work_type:
            raise ParamsErrorCodeException(msg="function_type 类型不支持!")

        record = FileRecordTable(
            file_url=data.get("file_url"),
            file_name=data.get("file_name"),
            function_type=function_type,
            operation_type=data.get("operation_type"),
            res_model=data.get("res_model"),
            res_id=data.get("res_id"),
            status="process",  # 初始状态
            params=data.get("params", {})
            # created_uid 可以从 request context 中获取当前用户ID，这里暂不处理
        )

        session.add(record)
        await session.flush()
        await session.commit()

        await aio_mq.publish(
            routing_key=MqRoutingKey.FILE_IMPORT,
            msg={"file_id": record.id, "work_type": work_type}
        )
        return record
