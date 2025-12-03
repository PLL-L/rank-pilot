#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Version        : 1.0
# @Update Time    : 2024/11/26 23:26
# @File           : base.py
# @IDE            : PyCharm
# @Desc           : 告警抽象基类，定义了文件上传的通用接口和工具方法
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




class AbstractAlarm(ABC):
    """告警抽象基类，定义了文件上传的通用接口和工具方法

    Attributes:

    """

    @abstractmethod
    def send_message(self, title, message, msg_type=None, module="default"):
        pass




