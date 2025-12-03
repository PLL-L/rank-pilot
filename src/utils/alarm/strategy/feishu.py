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
        AlarmModule.SITE : {
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

    async def send_message(self, title, message, msg_type="markdown", module="default"):

        hook = self.ALARM_MODULE.get(module).get("hook")
        secret = self.ALARM_MODULE.get(module).get("secret")

        message = str(message)
        send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"- 时间：{send_time}\n - 错误信息：{message}"

        if msg_type == "markdown":
            content_blocks = [
                {"tag": "markdown", "content": f"**{settings.system.RUN_MODE}环境**"},
                {"tag": "markdown", "content": "\n ---\n"},
                {"tag": "markdown", "content": message},
                {"tag": "markdown", "content": f"123"}
            ]

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
        else:

            data = {"msg_type": "text", "content": {"text": message}}
        if secret:
            timestamp, sign = self._feishu_sign(secret)
            if timestamp and sign:
                data["timestamp"] = timestamp
                data["sign"] = sign

        url = f"{settings.FEISHU_ALARM.URL}{hook}"
        await http_client.post(url=url, json=data,title="feishu", timeout=5)





if __name__ == '__main__':
    import asyncio
    feishu = FeishuStrategy()
    asyncio.run(feishu.send_message("测试", "你好呀", module="site"))