import base64
import hashlib
import hmac
import time
from datetime import datetime

from src.config import settings
from src.core.log.logger import init_logger
from src.defined.alarm import AlarmModule
from src.utils import http_client
from src.utils.alarm.base import AbstractAlarm


class FeishuStrategy(AbstractAlarm):
    ALARM_MODULE = {
        AlarmModule.SITE: {
            "hook": settings.FEISHU_ALARM.SITE_HOOK_KEY,
            "secret": settings.FEISHU_ALARM.SITE_HOOK_SECRET,
        }
    }

    @classmethod
    def _feishu_sign(cls, secret):
        timestamp = str(int(time.time()))
        # 拼接timestamp和secret
        string_to_sign = "{}\n{}".format(timestamp, secret)
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        # 对结果进行base64处理
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return timestamp, sign

    async def send_message(self, title, message, is_all=False, module="default"):

        hook = self.ALARM_MODULE.get(module).get("hook")
        secret = self.ALARM_MODULE.get(module).get("secret")

        send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content_blocks = [
            {"tag": "markdown", "content": f"**📢{settings.system.RUN_MODE}环境**"},
            {"tag": "markdown", "content": f"**时间：{send_time}**"},

        ]

        if is_all:
            content_blocks.append({"tag": "markdown", "content": "**请注意：这是一个全体通知！**<at id=all></at>"})

        if isinstance(message, list):
            for msg in message:
                content_blocks.append({
                    "tag": "markdown",
                    "content": f"- {msg}"
                })
        elif isinstance(message, dict):
            content_blocks.append({"tag": "markdown", "content": "\n ---\n"})

            for key, msg in message.items():
                if isinstance(msg, list):

                    content_blocks.append({"tag": "markdown", "content": f"**{key}:**"})
                    for val in msg:
                        content_blocks.append({
                            "tag": "markdown",
                            "content": f"- {val}"
                        })
                else:
                    content_blocks.append({
                        "tag": "markdown",
                        "content": f"**{key}:** {msg}"
                    })
        else:
            content_blocks.append({"tag": "markdown", "content": f"- 错误信息：{message}"})

        data = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "template": "yellow",
                    "title": {"tag": "plain_text", "content": title},
                },
                "elements": content_blocks,
            },
        }

        if secret:
            timestamp, sign = self._feishu_sign(secret)
            if timestamp and sign:
                data["timestamp"] = timestamp
                data["sign"] = sign

        url = f"{settings.FEISHU_ALARM.URL}{hook}"
        await http_client.post(url=url, json=data, title="feishu", timeout=5)


if __name__ == '__main__':
    import asyncio

    feishu = FeishuStrategy()
    msg = {
        "Excel重复详情": [
            "Excel中第26行与前面行关键词和平台重复: 后端服务 Docker 容器化部署-BAIDU_PC",
            "Excel中第29行与前面行关键词和平台重复: FastAPI 权限认证实现-BAIDU_M",
            "Excel中第34行与前面行关键词和平台重复: 后端接口压力测试工具-BAIDU_PC",
            "Excel中第36行与前面行关键词和平台重复: Python FastAPI 接口开发-BAIDU_PC",
            "Excel中第38行与前面行关键词和平台重复: PostgreSQL JSONB 查询优化-BAIDU_PC"
        ],
        "数据库重复详情": [
            "第3行不导入: ",
            "第4行不导入: ",
            "第8行不导入: ",
            "第9行不导入: ",
            "第10行不导入: ",
            "第11行不导入: ",
            "第12行不导入: ",
            "第16行不导入: ",
            "第17行不导入: ",
            "第18行不导入: ",
            "第19行不导入: ",
            "第20行不导入: ",
            "第21行不导入: ",
            "第22行不导入: "
        ],
        "错误详情": [
            "Excel第5行: 不支持的平台类型 'BAIDU_PC'",
            "Excel第6行: 不支持的平台类型 'BAIDU_PC'",
            "Excel第7行: 不支持的平台类型 'BAIDU_PC'",
            "Excel第13行: 不支持的平台类型 'BAIDU_M'",
            "Excel第14行: 不支持的平台类型 'BAIDU_M'",
            "Excel第15行: 不支持的平台类型 'BAIDU_M'",
            "Excel第23行: 移动平台'360M'必须填写M端搜索深度",
            "Excel第24行: 关键词不能为空",
            "Excel第25行: 不支持的平台类型 '百度 PC'",
            "Excel第27行: 不支持的平台类型 'BAIDU_PC'",
            "Excel第28行: 执行周期不能为空",
            "Excel第30行: 执行周期必须为数值",
            "Excel第31行: M端搜索深度必须为0-499之间的数值",
            "Excel第32行: 不支持的平台类型 '360'",
            "Excel第33行: 不支持的平台类型 'BAIDU_PC'",
            "Excel第35行: 不支持的平台类型 'BAIDU_PC'",
            "Excel第37行: 不支持的平台类型 'BAIDU_PC'",
            "Excel第39行: 平台不能为空"
        ]
    }
    asyncio.run(feishu.send_message(
        "测试",
        msg
        , module="site"))
