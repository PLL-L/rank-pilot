#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Version        : 1.0
# @Update Time    : 2024/12/5 23:41
# @File           : __init__.py
# @IDE            : PyCharm
# @Desc           : 文件上传策略包

from src.utils.file.strategy.local_file import LocalFileStrategy
# from src.utils.file.strategy.qiniu_file import QiniuFileStrategy

__all__ = ["LocalFileStrategy"]
