#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Version        : 1.0
# @Update Time    : 2024/12/5 23:41
# @File           : alarm_factory.py
# @IDE            : PyCharm
# @Desc           : 报警工厂类，用于创建和管理不同的报警策略

from typing import Dict, Optional, Type, Any

from src.core.exception.custom_exception import GlobalErrorCodeException
from src.defined.alarm import AlarmType, AlarmModule
from src.utils.alarm.base import AbstractAlarm
from src.utils.alarm.strategy.feishu import FeishuStrategy
from src.utils.file.base import AbstractUpload
from src.utils.singleton import Singleton


class AlarmFactory(metaclass=Singleton):
    """告警工厂类，用于创建和管理不同的告警策略

    使用单例模式确保全局只有一个工厂实例，避免重复创建上传策略对象。

    Attributes:
        _upload_strategy: 存储已创建的告警策略实例
    """

    _alarm_strategy: Dict[str, AbstractAlarm] = {}

    @classmethod
    def get_alarm_strategy(cls, alarm_type: str) -> AbstractAlarm:
        """获取上传策略实例

        Args:
            alarm_type: 告警类型，支持 "feishu"
            alarm_module: str  告警模块 site

        Returns:
            AbstractAlarm: 上传策略实例

        Raises:
            BaseAppException: 不支持的上传类型时抛出
        """
        if alarm_type not in cls._alarm_strategy:
            strategy = cls._create_strategy(alarm_type)
            if strategy:
                cls._alarm_strategy[alarm_type] = strategy
            else:
                raise GlobalErrorCodeException(msg=f"暂不支持{alarm_type} 告警")
        return cls._alarm_strategy[alarm_type]

    @classmethod
    def _create_strategy(cls, alarm_type: str) -> Optional[AbstractAlarm]:
        """创建上传策略实例

        Args:
            alarm_type: 上传类型
            alarm_module

        Returns:
            Optional[AbstractUpload]: 上传策略实例，如果类型不支持则返回None
        """
        strategy_map: Dict[str, Any] = {
            AlarmType.FEISHU: FeishuStrategy,
        }
        strategy_class = strategy_map.get(alarm_type)
        return strategy_class() if strategy_class else None
