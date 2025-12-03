import asyncio
import io
import json
import os
from datetime import timedelta
from typing import Optional, List, Union, BinaryIO

from fastapi import UploadFile
from minio import Minio, S3Error

from src.config import settings
from src.core import logger
from src.core.exception.custom_exception import GlobalErrorCodeException
from src.utils.file.base import AbstractUpload


class MinIOFileStrategy(AbstractUpload):
    def __init__(self):
        """
        初始化Minio客户端
        :param endpoint: Minio服务的URL
        :param access_key: Minio访问密钥
        :param secret_key: Minio密钥
        :param secure: 是否使用https
        """

        self.client = Minio(
            endpoint=settings.MINIO_CONFIG.ENDPOINT,
            access_key=settings.MINIO_CONFIG.ACCESS_KEY,
            secret_key=settings.MINIO_CONFIG.SECRET_KEY,
            secure=settings.MINIO_CONFIG.SECURE
        )

        self.bucket_name = settings.MINIO_CONFIG.BUCKET_NAME

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                }
            ]
        }
        self.client.set_bucket_policy(bucket_name=self.bucket_name, policy=json.dumps(policy))



    async def upload_file(
            self,
            file_content: Union[io.IOBase, bytes, BinaryIO],
            file_path: str,
            file_name: str,
            content_type: str = "application/octet-stream",
            file_size: Optional[int] = None
    ) -> dict:
        """
        从文件流上传文件到Minio
        :param file_content: 文件流对象或bytes数据
        :param file_name: Minio上存储的对象名称
        :param file_path: Minio上存储的路径

        :param content_type: 文件内容类型
        :param file_size: 文件大小（字节），如果为None则自动计算
        :return: 上传结果字典
        """
        try:


            # 确保存储桶存在
            if not await self.ensure_bucket_exists():
                raise GlobalErrorCodeException(code=-1, msg=f"存储桶 '{self.bucket_name}' 创建失败")

            # 处理bytes类型数据
            if isinstance(file_content, bytes):
                file_content = io.BytesIO(file_content)
                file_size = len(file_content.getvalue()) if file_size is None else file_size
            elif hasattr(file_content, 'getvalue'):
                # 如果是BytesIO，可以获取值来计算大小
                file_size = len(file_content.getvalue()) if file_size is None else file_size
            elif hasattr(file_content, 'seek') and hasattr(file_content, 'tell'):
                # 对于其他流对象，尝试计算大小
                if file_size is None:
                    current_pos = file_content.tell()
                    file_content.seek(0, 2)  # 移动到末尾
                    file_size = file_content.tell() - current_pos
                    file_content.seek(current_pos)  # 恢复位置

            # 上传文件流
            await asyncio.to_thread(
                self.client.put_object,
                bucket_name=self.bucket_name,
                object_name=f"{file_path}/{file_name}",
                data=file_content,
                length=file_size,
                content_type=content_type
            )

            # 生成访问URL
            file_url = f"http://{settings.MINIO_CONFIG.ENDPOINT}/{self.bucket_name}/{file_path}/{file_name}"

            # file_url = self.get_presigned_url(bucket_name, object_name)

            logger.info(f"文件流上传成功: {file_url}")

            return {
                "file_name": file_name,
                "file_url": file_url,
                "file_size": file_size
            }

        except S3Error as e:
            error_msg = f"文件流上传失败: {e}"
            logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"上传过程中发生错误: {e}"
            logger.error(error_msg)
            raise

    def get_presigned_url(
            self,
            bucket_name: str,
            object_name: str,
            expires: timedelta = timedelta(days=7)
    ) -> str:
        """
        生成预签名URL用于临时访问
        :param bucket_name: 存储桶名称
        :param object_name: 对象名称
        :param expires: 链接有效期
        :return: 预签名URL
        """
        try:
            return self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires
            )
        except S3Error as e:
            logger.error(f"生成预签名URL失败: {e}")
            return ""



    async def ensure_bucket_exists(self) -> bool:
        """确保存储桶存在"""
        try:
            # 使用 to_thread 将同步的 bucket_exists 调用变为异步非阻塞
            exists = await asyncio.to_thread(self.client.bucket_exists, bucket_name = self.bucket_name)
            if not exists:
                # 如果不存在，同样使用 to_thread 异步创建
                await asyncio.to_thread(self.client.make_bucket, bucket_name = self.bucket_name)
                logger.info(f"存储桶 '{self.bucket_name}' 创建成功")
            return True
        except S3Error as e:
            logger.error(f"创建存储桶失败: {e}")
            return False
        except Exception as e:
            logger.error(f"检查或创建存储桶时发生未知错误: {e}")
            return False

    def download_file_as_stream(self, bucket_name: str, object_name: str) -> Optional[io.BytesIO]:
        """
        下载文件为流对象
        :param bucket_name: 存储桶名称
        :param object_name: 对象名称
        :return: 文件流对象或None
        """
        try:
            response = self.client.get_object(bucket_name=bucket_name, object_name=object_name)
            file_data = response.read()
            response.close()
            response.release_conn()

            return io.BytesIO(file_data)
        except S3Error as e:
            logger.error(f"文件下载失败: {e}")
            return None


    def delete_file(self, object_name: str) -> dict:
        """
        删除文件
        :param object_name: Minio上存储的对象名称
        :return: 删除结果字典
        """
        try:
            self.client.remove_object(bucket_name=self.bucket_name, object_name=object_name)
            logger.info(f"文件删除成功: {object_name} from {self.bucket_name}")
            return {"success": True, "message": f"文件 {object_name} 删除成功"}
        except S3Error as e:
            error_msg = f"文件删除失败: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def list_objects(self, bucket_name: str, prefix: str = "") -> list:
        """
        列出存储桶中的对象
        """
        try:
            objects = self.client.list_objects(bucket_name= bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"列出对象失败: {e}")
            return []

    def file_exists(self, bucket_name: str, object_name: str) -> bool:
        """
        检查文件是否存在
        """
        try:
            self.client.stat_object(bucket_name=bucket_name, object_name=object_name)
            return True
        except S3Error:
            return False



if __name__ == '__main__':
    a = MinIOFileStrategy()
    with open("/Users/echo/Documents/以太天空/rankpilot_backend/main.py", 'rb') as file_stream:
        result3 = a.upload_file_from_stream(
            file_content=file_stream,
            file_name="test-files/main123.py",
            content_type="application/octet-stream",
            # file_size=os.path.getsize("/Users/echo/Documents/以太天空/rankpilot_backend/main.py")
        )
        print(result3)