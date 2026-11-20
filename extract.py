"""Разработчик 1: из истории диалога получаем структурированные условия."""
from __future__ import annotations

from llm_client import LLMClient
from models import Conditions


class ConditionExtractor:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def extract(self, messages: list[dict]) -> Conditions:
        """messages: [{"role": "user"|"assistant", "text": "..."}] из входного JSON.

        Учитывать всю историю: новая реплика заменяет только своё условие.
        Неизвестное условие = None. Результат модели проверять по справочникам.
        """
        raise NotImplementedError
