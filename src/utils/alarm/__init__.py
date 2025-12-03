# @Version        : 1.0
# @Update Time    : 2024/11/26 23:25
# @File           : __init__.py.py
# @IDE            : PyCharm
# @Desc           : 文件描述信息
from src.config import settings
from src.utils.alarm.alarm_factory import AlarmFactory

alarm_robot = AlarmFactory.get_alarm_strategy(settings.system.ALARM_TYPE)
