"""Разработчик 4: диалог (вопросы, объяснения) и сборка JSON-ответа."""
from __future__ import annotations

from meow.models import Conditions, Kit, Question


class DialogManager:

    CITY_NAMES = {
            "taganrog": "Таганроге",
            "rostov-na-donu": "Ростове-на-Дону",
            "azov": "Азове"
        }

    CATEGORY_NAMES = {
        "table": "Стол",
        "chair": "Стул",
        "lamp": "Лампа"
    }
    CATEGORY_ACC = {"table": "стол", "chair": "кресло", "lamp": "лампу"}

    def find_missing(self, cond: Conditions) -> list[Question]:
        """Вопросы для clarify по недостающим budget_rub, city_id, categories (каждое поле один раз)."""
        
        questions = []
        QUESTION_TEXTS = {
            "budget_rub": "Какой у вас бюджет на весь комплект, в рублях?",
            "city_id": "В каком городе вам удобен самовывоз? Доступны Таганрог, Ростов-на-Дону и Азов.",
        }
        if cond.city_id is None:
            questions.append(Question("city_id", QUESTION_TEXTS["city_id"]))
        if cond.budget_rub is None:
            questions.append(Question("budget_rub", QUESTION_TEXTS["budget_rub"]))
        # categories: вопрос нужен, если категории не известны или покупатель назвал
        # неподдерживаемые товары («диван», «шкаф») — их по ТЗ нужно явно уточнить.
        if cond.categories is None or cond.unsupported_categories:
            questions.append(Question("categories", self._categories_question(cond)))

        return questions

    def _categories_question(self, cond: Conditions) -> str:
        """Текст вопроса по категориям: generic или с упоминанием неподдерживаемых товаров."""
        if not cond.unsupported_categories:
            return "Какие предметы вам нужны? Можно выбрать стол, кресло и лампу."

        unsupported = ", ".join(f"«{s}»" for s in cond.unsupported_categories)
        available = "стол, кресло и лампу"
        if cond.categories:
            names = [self.CATEGORY_ACC[c] for c in cond.categories]
            chosen = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " и " + names[-1]
            return (
                f"Такое я не подбираю: {unsupported}. Могу подобрать {available}. "
                f"Подобрать только {chosen} или добавить что-то из этого списка?"
            )
        return (
            f"Такое я не подбираю: {unsupported}. Могу подобрать {available}. "
            "Что вам подобрать?"
        )

    def explain(self, kit: Kit, cond: Conditions) -> str:
        """Понятное объяснение комплекта на данных каталога (цена, город, характеристики)."""
        """Kit - это то, что у нас есть в iteme, а cond - это то, что user хочет получить"""

        # Стол «Письменный стол» (6 500 ₽) шириной 95 см, что укладывается в ваш лимит 100 см.
        EXPLAINING_PHRASES = {
            "main_phrase": "{category} «{title}» ({price} ₽)",
            "width_cm": "шириной {value} см",
            "color_temperature_k": "свет {value} K",
            "adjustable_height": {
                True: "с регулировкой высоты",
                False: "без регулировки высоты"
            },
            "end_phrase": "Всё в {city}, итого {total} ₽ при бюджете {total_limit} ₽",

            "width_limit": "что укладывается в ваш лимит {value} см",
            "width_limit_segment": "что укладывается в ваш диапазон от {start_val} до {end_val} см",

            "color_limit_upper": "не выше {value} K, как вы и просили",
            "color_limit_lower": "не ниже {value} K, как вы и просили",
            "color_limit_segment": "в нужном вам диапазоне от {start_val} до {end_val} K"
        }

        response = f""
        for listing in kit.items:
            width = listing.attributes.get("width_cm")
            ah = listing.attributes.get("adjustable_height")
            color_temp = listing.attributes.get("color_temperature_k")

            response += EXPLAINING_PHRASES["main_phrase"].format( category = self.CATEGORY_NAMES[listing.category], title = listing.title, price = listing.price_rub )
            if width is not None:
                response += ' ' + EXPLAINING_PHRASES["width_cm"].format( value = width )
                limits = [c for c in cond.constraints if c.category == "table" and c.key == "width_cm"]
                upper = [c for c in limits if c.op in ("lte", "lt")]
                lower = [c for c in limits if c.op in ("gte", "gt")]
                if upper and lower:
                    response += ", " + EXPLAINING_PHRASES["width_limit_segment"].format( start_val = lower[0].value, end_val = upper[0].value )
                elif upper:
                    response += ", " + EXPLAINING_PHRASES["width_limit"].format( value = upper[0].value )

            if ah is not None:
                response += ' ' + EXPLAINING_PHRASES["adjustable_height"][ah]

            if color_temp is not None:
                response += ' ' + EXPLAINING_PHRASES["color_temperature_k"].format( value = color_temp )
                limits = [c for c in cond.constraints if c.category == "lamp" and c.key == "color_temperature_k"]
                upper = [c for c in limits if c.op in ("lte", "lt")]
                lower = [c for c in limits if c.op in ("gte", "gt")]
                if upper and lower:
                    response += ", " +  EXPLAINING_PHRASES["color_limit_segment"].format( start_val = lower[0].value, end_val = upper[0].value )
                elif upper and not lower:
                    response += ", " +  EXPLAINING_PHRASES["color_limit_upper"].format( value = upper[0].value )
                elif not upper and lower:
                    response += ", " +  EXPLAINING_PHRASES["color_limit_lower"].format( value = lower[0].value )

            response += ". "
        response += EXPLAINING_PHRASES["end_phrase"].format( city = self.CITY_NAMES[cond.city_id], total = kit.total_rub, total_limit = cond.budget_rub ) + '.'

        return response

    def no_match_message(self, cond: Conditions) -> str:
        """Что мешает найти комплект и что покупатель может изменить."""

        names = [self.CATEGORY_NAMES[c].lower() for c in cond.categories]
        budget = f"{cond.budget_rub:,}".replace(',', ' ')
        response = f"В {self.CITY_NAMES[cond.city_id]} не нашлось полного комплекта ({', '.join(names)}) в бюджете {budget} ₽"
        if cond.constraints:
            response += " с вашими ограничениями по характеристикам. "
        else:
            response += ". "

        options = ["увеличить бюджет", "рассмотреть другой город"]
        if cond.constraints:
            options.append("смягчить ограничения")

        response += f"Можно {', '.join(options[:-1])} или {options[-1]}. Скажите, что вам подходит."     

        return response

class ResponseBuilder:
    """Собирает ответ строго по schemas/response.schema.json."""

    def clarify(self, questions: list[Question]) -> dict:
        LLMAnswer = {
            "status": "clarify",
            "questions": []
        }

        for question in questions:
            LLMAnswer["questions"].append(
                {
                    "field": question.field,
                    "text": question.text
                }
            )

        return LLMAnswer

    def ok(self, kits: list[Kit], explanations: list[str]) -> dict:
        LLMAnswer = {
            "status": "ok",
            "options": []
        }

        for i in range(len(explanations)):
            kit = kits[i]
            exp = explanations[i]

            LLMAnswer["options"].append(
                {
                    "listing_ids": kit.listing_ids,
                    "total_rub": kit.total_rub,
                    "explanation": exp
                }
            )

        return LLMAnswer

    def no_match(self, message: str) -> dict:
        LLMAnswer = {
            "status": "no_match",
            "message": message
        }

        return LLMAnswer
