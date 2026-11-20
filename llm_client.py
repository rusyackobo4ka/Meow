from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from config import LLMConfig

CALL_TIMEOUT_S = 45
TOTAL_DEADLINE_S = 100          # запас до лимита 120 с на весь run
MAX_TEXT_BYTES = 32768          # сумма content всех сообщений
MAX_BODY_BYTES = 65536          # весь JSON-запрос
RETRY_CODES = {429, 503}        # 502 incomplete_output повтор не лечит
MAX_ATTEMPTS = 3


class LLMError(RuntimeError):
    status: int | None = None


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._started = time.monotonic()

    def complete_json(self, messages: list[dict], schema: dict, max_tokens: int = 256) -> dict:
        text_bytes = sum(len(m["content"].encode("utf-8")) for m in messages)
        if text_bytes > MAX_TEXT_BYTES:
            raise LLMError(f"тексты сообщений превышают {
                           MAX_TEXT_BYTES} байт: {text_bytes}")

        fmt = {
            "type": "json_schema",
            "json_schema": {"name": "buyer_requirements", "strict": True, "schema": schema},
        }
        try:
            return self._call(messages, fmt, max_tokens)
        except LLMError as exc:
            if exc.status in (400, 502):
                print(f"json_schema не сработала ({
                      exc}), пробую json_object", file=sys.stderr)
                return self._call(messages, {"type": "json_object"}, max_tokens)
            raise

    def _call(self, messages: list[dict], response_format: dict, max_tokens: int) -> dict:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "response_format": response_format,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(body) > MAX_BODY_BYTES:
            raise LLMError(f"запрос превышает {
                           MAX_BODY_BYTES} байт: {len(body)}")

        url = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
            "User-Agent": self.config.user_agent,
        }

        raw = b""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            remaining = TOTAL_DEADLINE_S - (time.monotonic() - self._started)
            if remaining <= 1:
                raise LLMError("исчерпан общий лимит времени")
            request = urllib.request.Request(
                url, data=body, method="POST", headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=min(CALL_TIMEOUT_S, remaining)) as resp:
                    raw = resp.read()
                break
            except urllib.error.HTTPError as exc:
                try:
                    detail = exc.read().decode("utf-8", "replace")[:500]
                except Exception:  # noqa: BLE001
                    detail = ""
                if exc.code in RETRY_CODES and attempt < MAX_ATTEMPTS:
                    try:
                        pause = float(exc.headers.get("Retry-After", 2))
                    except (TypeError, ValueError):
                        pause = 2.0
                    time.sleep(min(pause, 10))
                    continue
                err = LLMError(f"HTTP {exc.code} {exc.reason}: {detail}")
                err.status = exc.code
                raise err from exc
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                raise LLMError(f"сетевой сбой или таймаут: {exc}") from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise LLMError("ответ API — не валидный JSON") from exc
        if not isinstance(data, dict):
            raise LLMError("ответ API — не объект")
        return self._parse_content(self._extract_content(data))

    @staticmethod
    def _extract_content(data: dict) -> Any:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and "content" in message:
                    return message["content"]
        if "content" in data:
            return data["content"]
        raise LLMError("в ответе API нет choices[0].message.content / content")

    @staticmethod
    def _parse_content(content: Any) -> dict:
        if isinstance(content, str):
            text = content.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                lines = lines[1:] if lines and lines[0].startswith(
                    "```") else lines
                lines = lines[:-
                              1] if lines and lines[-1].strip() == "```" else lines
                text = "\n".join(lines)
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                raise LLMError("content модели — не валидный JSON") from exc
        else:
            parsed = content

        if not isinstance(parsed, dict):
            raise LLMError(f"ожидался объект, получено: {
                           type(parsed).__name__}")
        return parsed
