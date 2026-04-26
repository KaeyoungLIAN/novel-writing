"""
Grok API 客户端。
封装 OpenAI 兼容接口的调用，支持自动重试和错误处理。
"""

import json
import time
from typing import Optional, Callable

import httpx


class GrokAPIError(Exception):
    """Grok API 调用异常"""
    pass


class GrokClient:
    """Grok API 客户端"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.x.ai/v1",
        model: str = "grok-3-mini",
        temperature: float = 1.0,
        max_tokens: int = 16384,
        timeout: int = 300,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        on_progress: Optional[Callable[[str], None]] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.on_progress = on_progress

    def _log(self, msg: str):
        if self.on_progress:
            self.on_progress(msg)

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_completion(
        self,
        messages: list,
        response_format: Optional[dict] = None,
    ) -> str:
        """
        调用 Grok Chat Completion API。

        Args:
            messages: OpenAI 格式的消息列表
            response_format: 可选，指定响应格式，如 {"type": "json_object"}

        Returns:
            模型返回的文本内容

        Raises:
            GrokAPIError: API 调用失败且重试用尽
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt > 1:
                    wait = self.retry_delay * (2 ** (attempt - 2))
                    self._log(f"  第 {attempt} 次重试，等待 {wait:.0f}s...")
                    time.sleep(wait)

                self._log(
                    f"  Grok API 调用中..."
                    + (f" (第{attempt}次)" if attempt > 1 else "")
                )

                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._build_headers(),
                        json=payload,
                    )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    self._log("  ✓ API 调用成功")
                    return content.strip()

                # 处理错误
                error_body = response.text[:500]
                if response.status_code == 429:
                    self._log(f"  ⚠ 限流 (429)，等待后重试")
                    last_error = GrokAPIError(f"Rate limited: {error_body}")
                elif response.status_code >= 500:
                    self._log(f"  ⚠ 服务端错误 ({response.status_code})")
                    last_error = GrokAPIError(f"Server error: {error_body}")
                else:
                    # 4xx 错误（除 429 外）不重试
                    raise GrokAPIError(
                        f"HTTP {response.status_code}: {error_body}"
                    )

            except httpx.TimeoutException as e:
                last_error = GrokAPIError(f"请求超时: {e}")
                self._log(f"  ⚠ 请求超时")
            except httpx.RequestError as e:
                last_error = GrokAPIError(f"网络错误: {e}")
                self._log(f"  ⚠ 网络错误")

        raise GrokAPIError(
            f"API 调用失败，已重试 {self.max_retries} 次: {last_error}"
        )

    def chat_completion_json(self, messages: list) -> dict:
        """
        调用 Grok API 并强制返回 JSON 对象。
        自动处理模型返回非 JSON 的情况（最多重试 2 次）。
        """
        last_error = None
        for parse_attempt in range(3):
            try:
                text = self.chat_completion(
                    messages,
                    response_format={"type": "json_object"},
                )
                return json.loads(text)
            except json.JSONDecodeError as e:
                last_error = e
                self._log(f"  ⚠ JSON 解析失败，重新生成")
                # 追加指令让模型修正输出
                messages.append({
                    "role": "assistant",
                    "content": text,
                })
                messages.append({
                    "role": "user",
                    "content": (
                        "你的输出不是合法的 JSON。请只输出纯 JSON 数组，"
                        "不要加任何 markdown 代码块标记（```）或额外说明。"
                    ),
                })

        raise GrokAPIError(
            f"JSON 解析失败，已重试 3 次: {last_error}"
        )
