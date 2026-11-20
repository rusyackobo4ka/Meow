"""Разработчик 3: подбор комплектов."""
from __future__ import annotations

from models import Conditions, Kit, Listing


class KitSelector:
    def select(self, candidates: dict[str, list[Listing]], cond: Conditions, limit: int = 3) -> list[Kit]:
        """До `limit` разных комплектов: по одному объявлению каждой категории, сумма <= бюджета.

        Пустой список = подходящих комплектов нет (будет no_match).
        """
        raise NotImplementedError
