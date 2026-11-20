"""Разработчик 1: клиент модели Gemma через API организаторов.

Конфигурация приходит снаружи (см. config.LLMConfig). Env здесь не читается.
"""
from __future__ import annotations

from config import LLMConfig

DEFAULT_TIMEOUT_S = 90
MAX_INPUT_BYTES = 32 * 1024


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete_json(self, messages: list[dict], schema: dict, max_tokens: int = 256) -> dict:
        """Один вызов модели с response_format=json_schema (strict).

        Заголовки:
          Authorization: Bearer {self.config.api_key}
          User-Agent: {self.config.user_agent}
        Лимиты: ≤32 КБ входа, ≤90 с, ≤20 запросов/мин.
        """
        raise NotImplementedError