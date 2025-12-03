import decimal
import json
import random
import string
import time
from datetime import datetime
from decimal import Decimal
from typing import TypeVar, Dict, Any, List, Optional

from src.core import settings
# 类型定义
T = TypeVar("T")
DictT = TypeVar("DictT", bound=Dict[str, Any])
ListT = TypeVar("ListT", bound=List[Any])

class Tools:

    @staticmethod
    def random_string(length: int = 10) -> str:
        """生成指定长度的随机字符串

        Args:
            length: 字符串长度，默认10

        Returns:
            str: 随机字符串
        """
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def list_dict_find(options: List[DictT], key: str, value: Any) -> Optional[DictT]:
        """在字典列表中查找指定键值的项

        Args:
            options: 字典列表
            key: 键名
            value: 值

        Returns:
            Optional[DictT]: 找到的项，未找到返回None
        """
        return next((item for item in options if item.get(key) == value), None)

    @classmethod
    def desensitize(cls, data: DictT) -> DictT:
        """数据脱敏处理

        Args:
            data: 需要脱敏的数据

        Returns:
            DictT: 脱敏后的数据
        """
        if not data:
            return data

        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = cls.desensitize(v)
            elif k in settings.system.DESENSITIZE_FIELDS:
                data[k] = "*****"

        return data

    @classmethod
    def get_file_name(cls, file_name=None, post_fix=None):
        ct = time.time()
        msecs = (ct - int(ct)) * 1000
        ctr = time.localtime(ct)
        t = time.strftime("%Y%m%d%H%M%S", ctr)
        s = "%s%03d" % (t, msecs)
        if file_name and '.' in file_name:
            post_fix = '.' + file_name.split('.')[-1]
        # end if
        return "{0}{1}".format(s, post_fix)

    @classmethod
    def reserve_two_digits(cls, value: str) -> str:
        """将 Decimal 值精确量化到 2 位小数，并返回字符串"""
        # decimal.ROUND_HALF_UP 是标准的四舍五入规则
        value = decimal.Decimal(value)
        quantized_value = value.quantize(Decimal("0.00"), rounding=decimal.ROUND_HALF_UP)
        # 返回字符串以确保 JSON 序列化时不会再次被处理，同时保留小数点后两位（如 1.00）
        return str(quantized_value)


class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, timedelta):
            return str(obj)
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        else:
            return json.JSONEncoder.default(self, obj)