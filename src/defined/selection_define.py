# -*- coding:utf-8 -*-
# -----------------------------
# 定义枚举类型数据返回值
# -----------------------------from .feedback import FeedbackStatus

# selection下拉字段
SELECT_DATA = {
    # 平台类型
    'platformType': [
        {'name': '百度PC', 'value': 'BAIDU_PC'},
        {'name': '百度M', 'value': 'BAIDU_M'},
        {'name': '360PC', 'value': '360PC'},
        {'name': '360M', 'value': '360M'},
    ],
    'accountStatus': [
        {'name': '未知', 'value': 'init'},
        {'name': '正常', 'value': 'normal'},
        {'name': '异常', 'value': 'abnormal'},
    ]
}
