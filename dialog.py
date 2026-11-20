"""Разработчик 4: диалог (вопросы, объяснения) и сборка JSON-ответа."""
from __future__ import annotations

from models import Conditions, Kit, Question


class DialogManager:
    def find_missing(self, cond: Conditions) -> list[Question]:
        """Вопросы для clarify по недостающим budget_rub, city_id, categories (каждое поле один раз)."""
        raise NotImplementedError

    def explain(self, kit: Kit, cond: Conditions) -> str:
        """Понятное объяснение комплекта на данных каталога (цена, город, характеристики)."""
        raise NotImplementedError

    def no_match_message(self, cond: Conditions) -> str:
        """Что мешает найти комплект и что покупатель может изменить."""
        raise NotImplementedError


class ResponseBuilder:
    """Собирает ответ строго по schemas/response.schema.json."""

    def clarify(self, questions: list[Question]) -> dict:
        raise NotImplementedError

    def ok(self, kits: list[Kit], explanations: list[str]) -> dict:
        raise NotImplementedError

    def no_match(self, message: str) -> dict:
        raise NotImplementedError
