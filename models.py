"""Общие типы данных. Ими обмениваются все модули, формат менять только по договорённости."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

CITIES = ["taganrog", "rostov-na-donu", "azov"]
CATEGORIES = ["table", "chair", "lamp"]
OPS = ("lt", "lte", "gt", "gte", "eq")


@dataclass
class Constraint:
    """Одно ограничение по характеристике, например стол не шире 100 см."""
    category: str   # table | chair | lamp
    key: str        # width_cm | adjustable_height | color_temperature_k
    op: str         # lt | lte | gt | gte | eq
    value: Any      # int или bool


@dataclass
class Conditions:
    """Условия покупателя. None означает, что в диалоге этого не сказано (нужно спросить)."""
    city_id: Optional[str] = None
    budget_rub: Optional[int] = None
    categories: Optional[list[str]] = None
    constraints: list[Constraint] = field(default_factory=list)


@dataclass
class Listing:
    """Одно объявление из каталога."""
    id: str
    category: str
    title: str
    description: str
    price_rub: int
    city_id: str
    attributes: dict[str, Any]

    @classmethod
    def from_dict(cls, d: dict) -> "Listing":
        return cls(d["id"], d["category"], d["title"], d["description"],
                   d["price_rub"], d["city_id"], d["attributes"])


@dataclass
class Kit:
    """Комплект: по одному объявлению каждой запрошенной категории."""
    items: list[Listing]

    @property
    def listing_ids(self) -> list[str]:
        return [x.id for x in self.items]

    @property
    def total_rub(self) -> int:
        return sum(x.price_rub for x in self.items)


@dataclass
class Question:
    """Вопрос для clarify."""
    field: str   # budget_rub | city_id | categories
    text: str
