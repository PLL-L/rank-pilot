import httpx
from httpx import Timeout
import asyncio
from typing import Optional, Dict, Any

# from src.core import
import logging as logger


class RetryHTTPClient:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def post(
            self,
            url: str,
            data: Optional[Dict[str, Any]] = None,
            json: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[Timeout] = Timeout(30.0),
            title: str = None,
    ) -> httpx.Response:
        """
        带重试机制的 POST 请求
        data 发表单
        json 发API接口
        timeout 30秒超时
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        url=url,
                        data=data,
                        json=json,
                        headers=headers
                    )

                    # 如果状态码是 2xx，直接返回
                    if 200 <= response.status_code < 300:
                        logger.info(f"{title} request url：{url}, 请求数据：{data or json} (尝试 {attempt + 1})")
                        return response

                    # 如果是服务器错误 (5xx)，进行重试
                    elif response.status_code >= 500:
                        logger.warning(
                            f"{title} 服务器错误，准备重试: {url} (状态码: {response.status_code}, 尝试 {attempt + 1})")
                    else:
                        # 客户端错误 (4xx)，不重试
                        logger.error(f" {title} 客户端错误: {url} (状态码: {response.status_code})")
                        return response

            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                logger.warning(f"{title} 网络错误，准备重试: {url} (错误: {e}, 尝试 {attempt + 1})")

            except Exception as e:
                last_exception = e
                logger.error(f"{title} 未知错误: {url} (错误: {e})")

            # 指数退避延迟
            if attempt < self.max_retries - 1:
                delay = self.base_delay * (2 ** attempt)  # 1, 2, 4 秒
                logger.info(f"等待 {delay} 秒后重试...")
                await asyncio.sleep(delay)

        # 所有重试都失败
        logger.error(f"所有重试失败: {url} (最后错误: {last_exception})")
