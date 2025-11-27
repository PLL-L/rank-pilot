import secrets
import string
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import logger
from src.core.db.db_database import transactional
from src.core.exception.custom_exception import GlobalErrorCodeException
from src.models.config_model import ConfigTable
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

            # 确定最终使用的文件名
            final_filename = self._determine_filename(
                original_filename=file.filename,
                use_random=use_random_filename,
                custom_name=custom_filename
            )

            # 初始化MinIO策略
            minio_strategy = MinIOFileStrategy()

            # 上传文件
            file_info = minio_strategy.upload_file(
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

    def _determine_filename(
        self,
        original_filename: str,
        use_random: bool = False,
        custom_name: Optional[str] = None
    ) -> str:
        """
        确定最终使用的文件名

        Args:
            original_filename: 原始文件名
            use_random: 是否使用随机文件名
            custom_name: 自定义文件名

        Returns:
            str: 最终的文件名
        """
        # 优先使用自定义文件名
        if custom_name:
            return custom_name

        # 如果使用随机文件名
        if use_random:
            # 保留原始文件扩展名
            file_extension = ""
            if "." in original_filename:
                file_extension = original_filename.rsplit(".", 1)[1]

            # 生成8位随机字符串作为文件名
            random_name = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
            return f"{random_name}.{file_extension}" if file_extension else random_name

        # 默认使用原始文件名
        return original_filename