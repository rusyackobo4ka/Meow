"""Разработчик 2: каталог и фильтрация объявлений."""
from __future__ import annotations

from models import Conditions, Listing


class Catalog:
    def __init__(self, listings: list[Listing]) -> None:
        self.listings = listings

    @classmethod
    def load(cls, path: str) -> "Catalog":
        """Прочитать каталог из JSON-файла (аргумент --catalog), UTF-8."""
        raise NotImplementedError

    def matches(self, item: Listing, cond: Conditions) -> bool:
        """Подходит ли объявление: город и ограничения его категории.

        Границы: lte/gte включают значение, lt/gt нет. Нет ключа = неизвестно = не подходит.
        """
        raise NotImplementedError

    def candidates(self, cond: Conditions) -> dict[str, list[Listing]]:
        """Подходящие объявления по каждой запрошенной категории: {"table": [...], ...}."""
        raise NotImplementedError
