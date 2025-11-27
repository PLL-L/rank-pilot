#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Version        : 1.0
# @Update Time    : 2024/12/5 23:41
# @File           : file_factory.py
# @IDE            : PyCharm
# @Desc           : 文件上传工厂类，用于创建和管理不同的文件上传策略

from typing import Dict, Optional, Type

from src.core.exception.custom_exception import GlobalErrorCodeException
from src.utils.file.base import AbstractUpload
from src.utils.file.strategy.local_file import LocalFileStrategy
# from src.utils.file.strategy.qiniu_file import QiniuFileStrategy
from src.utils.singleton import Singleton


class FileUploadFactory(metaclass=Singleton):
    """文件上传工厂类，用于创建和管理不同的文件上传策略

    使用单例模式确保全局只有一个工厂实例，避免重复创建上传策略对象。

    Attributes:
        _upload_strategy: 存储已创建的上传策略实例
    """

    _upload_strategy: Dict[str, AbstractUpload] = {}

    @classmethod
    def get_upload_strategy(cls, upload_type: str) -> AbstractUpload:
        """获取上传策略实例

        Args:
            upload_type: 上传类型，支持 "local" 和 "qiniu"

        Returns:
            AbstractUpload: 上传策略实例

        Raises:
            BaseAppException: 不支持的上传类型时抛出
        """
        if upload_type not in cls._upload_strategy:
            strategy = cls._create_strategy(upload_type)
            if strategy:
                cls._upload_strategy[upload_type] = strategy
            else:
                raise GlobalErrorCodeException(msg=f"暂不支持{upload_type}上传")
        return cls._upload_strategy[upload_type]

    @classmethod
    def _create_strategy(cls, upload_type: str) -> Optional[AbstractUpload]:
        """创建上传策略实例

        Args:
            upload_type: 上传类型

        Returns:
            Optional[AbstractUpload]: 上传策略实例，如果类型不支持则返回None
        """
        strategy_map: Dict[str, Type[AbstractUpload]] = {
            "local": LocalFileStrategy,
            # "qiniu": QiniuFileStrategy,
        }
        strategy_class = strategy_map.get(upload_type)
        return strategy_class() if strategy_class else None
