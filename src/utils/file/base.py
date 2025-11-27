#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Version        : 1.0
# @Update Time    : 2024/11/26 23:26
# @File           : base.py
# @IDE            : PyCharm
# @Desc           : 文件上传抽象基类，定义了文件上传的通用接口和工具方法
import io
import random
import string
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, StrEnum
from typing import List, Optional, Union, Any, Dict, BinaryIO
from pathlib import Path

from fastapi import UploadFile

from src.config import settings
from src.core.exception.custom_exception import GlobalErrorCodeException


class FileType(StrEnum):
    """文件类型枚举"""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    EXCEL = "excel"
    PDF = "pdf"
    WORD = "word"
    OTHER = "other"


class AbstractUpload(ABC):
    """文件上传抽象基类，定义了文件上传的通用接口和工具方法

    Attributes:
        IMAGE_ACCEPT: 支持的图片类型
        VIDEO_ACCEPT: 支持的视频类型
        AUDIO_ACCEPT: 支持的音频类型
        EXCEL_ACCEPT: 支持的Excel类型
        PDF_ACCEPT: 支持的PDF类型
        WORD_ACCEPT: 支持的Word类型
        OTHER_ACCEPT: 支持的其他类型
        FILE_ACCEPT: 所有支持的文件类型
        ALL_ACCEPT: 所有支持的类型
        UPLOAD_PATH: 上传文件基础路径
    """

    # 文件类型定义
    IMAGE_ACCEPT: List[str] = ["image/png", "image/jpeg", "image/gif", "image/x-icon"]
    VIDEO_ACCEPT: List[str] = ["video/mp4", "video/mpeg"]
    AUDIO_ACCEPT: List[str] = [
        "audio/wav",
        "audio/mp3",
        "audio/m4a",
        "audio/wma",
        "audio/ogg",
        "audio/mpeg",
        "audio/x-wav",
    ]
    EXCEL_ACCEPT: List[str] = [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]
    PDF_ACCEPT: List[str] = ["application/pdf"]
    WORD_ACCEPT: List[str] = ["application/msword"]
    OTHER_ACCEPT: List[str] = ["application/zip"]

    # 合并所有支持的类型
    FILE_ACCEPT: List[str] = [*EXCEL_ACCEPT, *PDF_ACCEPT, *WORD_ACCEPT, *OTHER_ACCEPT]
    ALL_ACCEPT: List[str] = [*IMAGE_ACCEPT, *VIDEO_ACCEPT, *AUDIO_ACCEPT, *FILE_ACCEPT]

    # 上传文件基础路径
    UPLOAD_PATH: str = settings.system.STATIC_PATH


    @abstractmethod

    def upload_file(
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
        pass


    @abstractmethod
    async def delete_file(self, info: Dict[str, Any]) -> bool:
        """删除文件

        Args:
            info: {}

        Returns:
            bool: 删除是否成功

        Raises:
            GlobalErrorCodeException: 删除失败时抛出
        """
        pass

    @classmethod
    def validate_file(
        cls, file: UploadFile, max_size: int = 5, accept: Optional[List[str]] = None
    ) -> bool:
        """校验文件大小和类型

        Args:
            file: 上传的文件
            max_size: 最大文件大小(MB)
            accept: 允许的文件类型列表

        Returns:
            bool: 验证是否通过

        Raises:
            GlobalErrorCodeException: 文件验证失败时抛出
        """
        if not accept:
            accept = cls.ALL_ACCEPT

        if file.content_type not in accept:
            raise GlobalErrorCodeException(msg=f"不支持的文件类型: {file.content_type}")

        size = file.size / 1024 / 1024
        if size > max_size:
            raise GlobalErrorCodeException(msg=f"文件过大,不能大于{max_size}MB")

        return True

    @classmethod
    def generate_file_name(cls, suffix: str) -> str:
        """生成随机文件名

        生成规则：当前时间戳 + 6位随机字符串 + 后缀

        Args:
            suffix: 文件后缀

        Returns:
            str: 生成的文件名
        """
        if not suffix.startswith("."):
            suffix = "." + suffix

        random_str = "".join(random.sample(string.ascii_letters + string.digits, 6))
        return f"{int(datetime.now().timestamp())}{random_str}{suffix}"

    @classmethod
    def generate_relative_path(
        cls,
        path: str,
        filename: Optional[str] = None,
        suffix: Optional[str] = None,
        is_today: bool = True,
    ) -> str:
        """生成相对路径

        Args:
            path: 自定义文件路径
            filename: 文件名称
            suffix: 文件后缀
            is_today: 是否添加日期目录

        Returns:
            str: 生成的相对路径

        Raises:
            GlobalErrorCodeException: 参数错误时抛出
        """
        # 标准化路径
        path = Path(path).as_posix()
        if path.startswith("/"):
            path = path[1:]

        # 验证参数
        if not filename and not suffix:
            raise GlobalErrorCodeException(msg="文件名或文件后缀不能同时为空")

        # 处理后缀
        if not suffix:
            if "." not in filename:
                raise GlobalErrorCodeException(msg="文件名必须带有后缀")
            suffix = filename.split(".")[-1]
            filename = filename.split(".")[0]
        else:
            if not suffix.startswith("."):
                suffix = "." + suffix

        # 生成文件名
        if not filename:
            filename = cls.generate_file_name(suffix)
        else:
            filename = f"{filename}-{cls.generate_file_name(suffix)}"

        # 生成完整路径
        if is_today:
            today = datetime.today().strftime("%Y%m%d")
            return f"{cls.UPLOAD_PATH}/{path}/{today}/{filename}"
        return f"{cls.UPLOAD_PATH}/{path}/{filename}"

    @classmethod
    def upload_type(cls, file: UploadFile) -> FileType:
        """根据文件类型返回上传类型

        Args:
            file: 上传的文件

        Returns:
            FileType: 文件类型枚举
        """
        content_type = file.content_type
        if content_type in cls.IMAGE_ACCEPT:
            return FileType.IMAGE
        elif content_type in cls.VIDEO_ACCEPT:
            return FileType.VIDEO
        elif content_type in cls.AUDIO_ACCEPT:
            return FileType.AUDIO
        elif content_type in cls.EXCEL_ACCEPT:
            return FileType.EXCEL
        elif content_type in cls.PDF_ACCEPT:
            return FileType.PDF
        elif content_type in cls.WORD_ACCEPT:
            return FileType.WORD
        else:
            return FileType.OTHER
