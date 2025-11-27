import random
import string
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