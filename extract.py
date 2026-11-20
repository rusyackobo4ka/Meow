from __future__ import annotations

from models import Conditions, Constraint, CITIES, CATEGORIES, OPS
from llm_client import LLMClient
import sys


KEY_BY_CAT = {
    "table": "width_cm",
    "chair": "adjustable_height",
    "lamp": "color_temperature_k",
}
BOOL_KEYS = {"adjustable_height"}

SYSTEM_PROMPT = """Ты извлекаешь условия покупки мебели из диалога покупателя с помощником.
Верни ТОЛЬКО JSON одной строкой, без пояснений, с ровно четырьмя ключами:
city_id, budget_rub, categories, constraints.

Правила:
1. Учитывай ВСЮ историю. Новая реплика покупателя заменяет только то условие, которое она меняет, остальные сохраняются.
2. Короткий ответ («15 тысяч», «Азов») относится к вопросу помощника в предыдущей реплике.
3. Условия берутся только из реплик покупателя. Ничего не выдумывай и не подставляй значения по умолчанию.
4. Если значение не названо, неоднозначно или не из списка (другой город, шкаф и т.п.):
   city_id = "unknown", budget_rub = -1, categories = []. Неподдерживаемые товары в categories не добавляй.
5. constraints: если ограничений нет, верни [].

Города: Таганрог -> taganrog, Ростов / Ростов-на-Дону -> rostov-na-donu, Азов -> azov.
Категории (латиницей): стол -> table, стул / кресло -> chair, лампа / светильник -> lamp.
Единицы: 1 м = 100 см («полтора метра» = 150); «15 тысяч», «15к» = 15000.
Значение -1 используется только для budget_rub. В constraints отрицательных значений нет.
«без регулировки» -> value 0, «с регулировкой» -> value 1.
«уже 120 см» -> op lt, value 120 (не lte). «шире 100 см» -> op gt, value 100 (не gte).

Пример ответа:
{"city_id":"azov","budget_rub":8000,"categories":["table","lamp"],"constraints":[{"category":"table","key":"width_cm","op":"lte","value":100}]}
"""

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "city_id": {"type": "string", "enum": list(CITIES) + ["unknown"]},
        "budget_rub": {"type": "integer", "minimum": -1},
        "categories": {
            "type": "array",
            "maxItems": 3,
            "items": {"type": "string", "enum": list(CATEGORIES)},
        },
        "constraints": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": list(CATEGORIES)},
                    "key": {"type": "string", "enum": list(KEY_BY_CAT.values())},
                    "op": {"type": "string", "enum": list(OPS)},
                    "value": {"type": "integer", "minimum": 0},
                },
                "required": ["category", "key", "op", "value"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["city_id", "budget_rub", "categories", "constraints"],
    "additionalProperties": False,
}


class ConditionExtractor:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def extract(self, messages: list[dict]) -> Conditions:
        """messages: [{"role": "user"|"assistant", "text": "..."}] из входного JSON."""
        llm_msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            {"role": m["role"], "content": m["text"]} for m in messages
        ]

        raw = self.llm.complete_json(llm_msgs, EXTRACT_SCHEMA, 300)
        cond = self._normalize(raw)
        print("RAW:", raw, "\nCOND:", cond, file=sys.stderr)
        return cond

    @staticmethod
    def _normalize(data: dict) -> Conditions:
        # город: "unknown", регистр, мусор -> None
        city = data.get("city_id")
        city = city.strip().lower() if isinstance(city, str) else None
        if city not in CITIES:
            city = None

        # бюджет: -1 = не назван (bool это подкласс int, отсекаем отдельно)
        budget = data.get("budget_rub")
        if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
            budget = None

        # категории: [] -> None
        cats = data.get("categories")
        if isinstance(cats, list):
            cats = [c for c in dict.fromkeys(cats) if c in CATEGORIES]
            cats = cats or None
        else:
            cats = None

        # ограничения
        constraints: list[Constraint] = []
        raw_constraints = data.get("constraints")
        if not isinstance(raw_constraints, list):
            raw_constraints = []
        for c in raw_constraints:
            if not isinstance(c, dict):
                continue
            cat, key = c.get("category"), c.get("key")
            op, val = c.get("op"), c.get("value")
            if cat not in CATEGORIES or KEY_BY_CAT.get(cat) != key or op not in OPS:
                continue
            if key in BOOL_KEYS:
                if val in (0, 1):          # True/False тоже сюда попадают
                    val = bool(val)
                else:
                    continue
                if op != "eq":
                    continue
            else:
                if isinstance(val, bool) or not isinstance(val, int) or val <= 0:
                    continue
            if cats is not None and cat not in cats:
                continue
            constraints.append(Constraint(cat, key, op, val))

        return Conditions(city, budget, cats, constraints)
