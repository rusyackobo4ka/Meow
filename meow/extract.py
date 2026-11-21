from __future__ import annotations

from meow.models import Conditions, Constraint, CITIES, CATEGORIES, OPS
from meow.llm_client import LLMClient
import sys


KEY_BY_CAT = {
    "table": "width_cm",
    "chair": "adjustable_height",
    "lamp": "color_temperature_k",
}
BOOL_KEYS = {"adjustable_height"}


SYSTEM_PROMPT = """Ты извлекаешь условия покупки мебели из диалога покупателя с помощником.
Верни ТОЛЬКО JSON одной строкой, без пояснений, с ровно пятью ключами:
city_id, budget_rub, categories, unsupported_categories, constraints.

Правила:
1. Учитывай ВСЮ историю. Новая реплика покупателя заменяет только то условие, которое она меняет, остальные сохраняются.
2. Короткий ответ («15 тысяч», «Азов») относится к вопросу помощника в предыдущей реплике.
3. Условия берутся только из реплик покупателя. Ничего не выдумывай и не подставляй значения по умолчанию.
4. Если значение не названо, неоднозначно или город не из списка:
   city_id = "unknown", budget_rub = -1, categories = [].
5. Товар не из списка категорий (диван, шкаф, полка и т.п.) не добавляй в categories. Запиши его в unsupported_categories коротким словом покупателя в начальной форме («диван», «шкаф»).
   Если покупатель позже отказался от такого товара или заменил его поддерживаемым («тогда просто стол»), в unsupported_categories его уже нет.
   Если неподдерживаемых товаров нет, unsupported_categories = [].
6. constraints: если ограничений нет, верни [].

Города: Таганрог -> taganrog, Ростов / Ростов-на-Дону -> rostov-na-donu, Азов -> azov.
Категории (латиницей): стол -> table, стул / кресло -> chair, лампа / светильник -> lamp.
Единицы: 1 м = 100 см («полтора метра» = 150); «15 тысяч», «15к» = 15000.
Значение -1 используется только для budget_rub. В constraints отрицательных значений нет.
«без регулировки» -> value 0, «с регулировкой» -> value 1.
«уже 120 см» -> op lt, value 120 (не lte). «шире 100 см» -> op gt, value 100 (не gte).

Примеры ответа:
{"city_id":"azov","budget_rub":8000,"categories":["table","lamp"],"unsupported_categories":[],"constraints":[{"category":"table","key":"width_cm","op":"lte","value":100}]}
{"city_id":"taganrog","budget_rub":20000,"categories":["table"],"unsupported_categories":["диван"],"constraints":[]}
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
        "unsupported_categories" : {
            "type" : "array",
            "maxItems" : 6,
            "items" : {"type": "string", "maxLength" : 40},
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
    "required": ["city_id", "budget_rub", "categories", "constraints", "unsupported_categories"],
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

        # категории: [] -> unsupported_categories
        cats = data.get("categories")
        unsupported = data.get("unsupported_categories")
        if isinstance(cats, list):
            cats = [c for c in dict.fromkeys(x for x in cats if isinstance(x, str)) if c in CATEGORIES]
            cats = cats or None
        else:
            cats = None
        if isinstance(unsupported, list):
            unsupported = [s.strip() for s in unsupported if isinstance(s, str) and s.strip()][:6]
        else:
            unsupported = []


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
                if val in (0, 1):
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

        return Conditions(city, budget, cats, constraints, unsupported_categories=unsupported)
