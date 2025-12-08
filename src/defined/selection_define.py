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
        {'name': '登陆失败', 'value': 'abnormal'},
    ],
    'businessType': [
        {'name': '关键词趋势列表', 'value': 'keyword'},
        {'name': '热门页面趋势列表', 'value': 'page'},
    ],
    'terminalType': [
        {'name': 'PC端', 'value': 'PC'},
        {'name': 'M端', 'value': 'MOBILE'},
    ],
    'isVerified': [
        {'name': '已认证', 'value': 1},
        {'name': '未认证', 'value': 0},
    ],
    'accountPlatformType': [
        {'name': '百度', 'value': "BAIDU"},
        {'name': '360', 'value': "360"},
    ],
}
