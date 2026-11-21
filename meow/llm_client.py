from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from meow.config import LLMConfig

CALL_TIMEOUT_S = 60
TOTAL_DEADLINE_S = 100          # запас до лимита 120 с на весь run
MAX_TEXT_BYTES = 32768          # сумма content всех сообщений
MAX_BODY_BYTES = 65536          # весь JSON-запрос
RETRY_CODES = {429, 503}        # 502 лечит fallback на json_object, а не повтор
MAX_ATTEMPTS = 3
TEMPERATURE = 0                 # стабильное извлечение условий
EXPECTED_MODEL = "google/gemma-4-31B-it"


class LLMError(RuntimeError):
    status: int | None = None


class LLMFormatError(LLMError):
    """Ответ пришёл, но содержимое непригодно (не JSON, не объект, нет ключей)."""


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._started = time.monotonic()
        if config.model != EXPECTED_MODEL:
            print("предупреждение: модель " + str(config.model)
                  + " отличается от ожидаемой " + EXPECTED_MODEL,
                  file=sys.stderr)

    def complete_json(self, messages: list[dict], schema: dict, max_tokens: int = 256) -> dict:
        text_bytes = sum(len(m["content"].encode("utf-8")) for m in messages)
        if text_bytes > MAX_TEXT_BYTES:
            raise LLMError(
                "тексты сообщений превышают " + str(MAX_TEXT_BYTES)
                + " байт: " + str(text_bytes))

        fmt = {
            "type": "json_schema",
            "json_schema": {"name": "buyer_requirements", "strict": True, "schema": schema},
        }
        try:
            result = self._call(messages, fmt, max_tokens)
            self._check_required(result, schema)
            return result
        except LLMFormatError as exc:
            reason = exc
        except LLMError as exc:
            if exc.status not in (400, 502):
                raise
            reason = exc

        print("json_schema не сработала (" + str(reason) + "), пробую json_object",
              file=sys.stderr)
        result = self._call(messages, {"type": "json_object"}, max_tokens)
        self._check_required(result, schema)   # снова плохо -> ошибка, ненулевой код
        return result

    @staticmethod
    def _check_required(parsed: dict, schema: dict) -> None:
        missing = [k for k in schema.get("required", []) if k not in parsed]
        if missing:
            raise LLMFormatError("в ответе нет ключей: " + ", ".join(missing))

    def _call(self, messages: list[dict], response_format: dict, max_tokens: int) -> dict:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": TEMPERATURE,
            "response_format": response_format,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(body) > MAX_BODY_BYTES:
            raise LLMError(
                "запрос превышает " + str(MAX_BODY_BYTES) + " байт: " + str(len(body)))

        url = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.config.api_key,
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
                    left = TOTAL_DEADLINE_S - (time.monotonic() - self._started)
                    if pause >= left - CALL_TIMEOUT_S * 0 - 1:
                        # ждать дольше остатка дедлайна нет смысла
                        err = LLMError("HTTP " + str(exc.code)
                                       + ": Retry-After не укладывается в дедлайн")
                        err.status = exc.code
                        raise err from exc
                    time.sleep(max(0.0, pause))
                    continue
                err = LLMError("HTTP " + str(exc.code) + " " + str(exc.reason) + ": " + detail)
                err.status = exc.code
                raise err from exc
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                raise LLMError("сетевой сбой или таймаут: " + str(exc)) from exc

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
        raise LLMFormatError("в ответе API нет choices[0].message.content / content")

    @staticmethod
    def _parse_content(content: Any) -> dict:
        if isinstance(content, str):
            text = content.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines)
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                raise LLMFormatError("content модели — не валидный JSON") from exc
        else:
            parsed = content

        if not isinstance(parsed, dict):
            raise LLMFormatError("ожидался объект, получено: " + type(parsed).__name__)
        return parsed