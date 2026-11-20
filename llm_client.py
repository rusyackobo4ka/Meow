"""Разработчик 1: клиент модели Gemma через API организаторов."""
from __future__ import annotations


class LLMClient:
    """Настройки читаются из LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, LLM_USER_AGENT. Ключ в код не писать."""

    def __init__(self) -> None:
        # TODO: прочитать переменные окружения, проверить, что ключ задан
        raise NotImplementedError

    def complete_json(self, messages: list[dict], schema: dict, max_tokens: int = 256) -> dict:
        """Один вызов модели с response_format=json_schema (strict). Вернуть разобранный JSON.

        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        Лимиты: до 32 КБ текста, до 90 с, до 20 запросов в минуту.
        """
        raise NotImplementedError
