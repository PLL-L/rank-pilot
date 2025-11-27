# @Version        : 1.0
# @Update Time    : 2024/12/5 22:26
# @File           : local_file.py
# @IDE            : PyCharm
# @Desc           : 本地文件上传策略
import os
from typing import List
from anyio import Path as AsyncPath
from fastapi import UploadFile
from src.config import settings
from src.utils.file.base import AbstractUpload


class LocalFileStrategy(AbstractUpload):
    async def upload_file(
        self, path: str, file: UploadFile, accept: List[str] = None, max_size: int = 5
    ) -> dict:
        """
        本地文件上传
        :param path:
        :param file:
        :param accept:
        :param max_size:
        :return:
        """
        # 校验文件类型
        if not accept:
            accept = self.FILE_ACCEPT
        return await self.save(path, file, accept, max_size)

    async def upload_image(
        self, path: str, file: UploadFile, accept: list = None, max_size: int = 5
    ) -> dict:
        """

        :param path:
        :param file:
        :param accept:
        :param max_size:
        :return:
        """
        if not accept:
            accept = self.IMAGE_ACCEPT
        return await self.save(path, file, accept, max_size)

    async def upload_audio(
        self, path: str, file: UploadFile, accept: list = None, max_size: int = 5
    ) -> dict:
        """

        :param path:
        :param file:
        :param accept:
        :param max_size:
        :return:
        """
        if not accept:
            accept = self.AUDIO_ACCEPT
        return await self.save(path, file, accept, max_size)

    async def upload_video(
        self, path: str, file: UploadFile, accept: list = None, max_size: int = 5
    ) -> dict:
        """

        :param path:
        :param file:
        :param accept:
        :param max_size:
        :return:
        """
        if not accept:
            accept = self.VIDEO_ACCEPT
        return await self.save(path, file, accept, max_size)

    # 保存文件
    @classmethod
    async def async_save_local(cls, path: str, file: UploadFile):
        """
        保存文件
        :param path:
        :param file:
        :return:
        """
        # 获取文件后缀
        suffix = file.filename.split(".")[-1]
        # 判断文件目录是否存在
        file_path = cls.generate_relative_path(path, suffix=suffix)
        save_path = AsyncPath(file_path)
        if not await save_path.parent.exists():
            await save_path.parent.mkdir(parents=True)
        await save_path.write_bytes(await file.read())
        return file_path

    @classmethod
    async def save(
        cls, path: str, file: UploadFile, accept: list = None, max_size: int = 5
    ):
        """
        保存文件
        :param path:
        :param file:
        :param accept:
        :param max_size:
        :return:
        """
        cls.validate_file(file, max_size, accept)
        file_path = await cls.async_save_local(path, file)
        # 相对路径
        file_path = file_path.replace(settings.system.STATIC_PATH, "").replace(
            "\\", "/"
        )
        return {
            "remote_path": settings.STATIC_URL + file_path,
            "local_path": file_path,
        }

    # 删除文件
    async def delete_file(self, path: str):
        """
        删除文件
        :param path:
        :return:
        """
        # 获取相对路径（移除URL前缀）
        relative_path = path.replace(settings.system.STATIC_URL, "").replace("/", "\\")
        # 获取绝对路径，使用os.path.join确保跨平台兼容性
        abs_path = os.path.join(settings.system.STATIC_PATH, relative_path.lstrip("\\"))
        save_path = AsyncPath(abs_path)
        if await save_path.exists():
            await save_path.unlink()
