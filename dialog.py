"""Разработчик 4: диалог (вопросы, объяснения) и сборка JSON-ответа."""
from __future__ import annotations

from models import Conditions, Kit, Question


class DialogManager:
    def find_missing(self, cond: Conditions) -> list[Question]:
        """Вопросы для clarify по недостающим budget_rub, city_id, categories (каждое поле один раз)."""

        questions = []
        QUESTION_TEXTS = {
            "budget_rub": "Какой у вас бюджет на весь комплект, в рублях?",
            "city_id": "В каком городе вам удобен самовывоз? Доступны Таганрог, Ростов-на-Дону и Азов.",
            "categories": "Какие предметы вам нужны? Можно выбрать стол, кресло и лампу.",
        }
        if cond.city_id is None:
            questions.append(Question("city_id", QUESTION_TEXTS["city_id"]))
        if cond.budget_rub is None:
            questions.append(Question("budget_rub", QUESTION_TEXTS["budget_rub"]))
        if cond.categories is None:
            questions.append(Question("categories", QUESTION_TEXTS["categories"]))

        return questions

    def explain(self, kit: Kit, cond: Conditions) -> str:
        """Понятное объяснение комплекта на данных каталога (цена, город, характеристики)."""
        """Kit - это то, что у нас есть в iteme, а cond - это то, что user хочет получить"""

        EXPLAINING_PHRASES = {
            "width_cm": "Стол «{title}» ({price_rub} ₽) шириной {width} см, что укладывается в ваш лимит {width_limit} см.",
            "color_temperature_k": "Лампа «{title}» ({price_rub} ₽) со светом {value} K",
            "chair_main": "Кресло «{title}» ({price_rub} ₽) ",
            "adjustable_height": {
                True: "с регулировкой высоты",
                False: "без регулировки высоты"
            },
            "end_phrase": "Всё в {city_id}, итого {total} ₽ при бюджете {total_limit} ₽."
        }

        response = f""
        for listing in kit:
            width = item.attributes.get("width_cm")
            ah = item.attributes.get("adjustable_height")
            color_temp = item.attributes.get("color_temperature_k")

            if width is not None:
                response += EXPLAINING_PHRASES["width_cm"].format( title = listing.title, price_rub = listing.price_rub, width = listing.attributes["width_cm"] ) + ' '
            if ah is not None:
                response += EXPLAINING_PHRASES["chair_main"].format( title = listing.title, price_rub = listing.price_rub ) + ' '
                response += EXPLAINING_PHRASES["adjustable_height"]
            if color_temp is not None:
                response += EXPLAINING_PHRASES["color_temperature_k"].format( title = lissting.title, price_rub = listing.price_rub, value = color_temp ) + ' '

            response += EXPLAINING_PHRASES["end_phrase"].format( city_id = cond.city_id, total = kit.total_rub(), total_limit = cond.budget_rub )

        return response

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
