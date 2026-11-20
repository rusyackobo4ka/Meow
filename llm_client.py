"""Разработчик 1: клиент модели Gemma через API организаторов.

Конфигурация приходит снаружи (см. config.LLMConfig). Env здесь не читается.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from config import LLMConfig

DEFAULT_TIMEOUT_S = 90
MAX_INPUT_BYTES = 32 * 1024

# Эндпоинт — сам LLM_BASE_URL (по контракту LLM_API.md это полный URL).
# Если контракт задаёт путь под base_url (например /chat/completions) —
# здесь достаточно дописать: url = self.config.base_url + "/chat/completions".


class LLMError(RuntimeError):


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete_json(self, messages: list[dict], schema: dict, max_tokens: int = 256) -> dict:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "buyer_requirements",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(body) > MAX_INPUT_BYTES:
            raise LLMError(
                f"вход превышает лимит {MAX_INPUT_BYTES} байт: {len(body)}"
            )

        request = urllib.request.Request(
            self.config.base_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
                "User-Agent": self.config.user_agent,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_S) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")[:500]
            except Exception:  # noqa: BLE001
                detail = ""
            raise LLMError(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise LLMError(f"сетевой сбой или превышен таймаут: {exc}") from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise LLMError("ответ API — не валидный JSON") from exc
        if not isinstance(data, dict):
            raise LLMError("ответ API — не объект")

        content = self._extract_content(data)
        parsed = self._parse_content(content)
        return parsed

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
                lines = lines[1:] if lines and lines[0].startswith("```") else lines
                lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
                text = "\n".join(lines)
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                raise LLMError("content модели — не валидный JSON") from exc
        else:
            parsed = content

        if not isinstance(parsed, dict):
            raise LLMError(f"ожидался объект, получено: {type(parsed).__name__}")
        return parsed
