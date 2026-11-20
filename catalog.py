"""Разработчик 2: каталог и фильтрация объявлений."""
from __future__ import annotations

from models import Conditions, Listing
import json


class Catalog:
    def __init__(self, listings: list[Listing]) -> None:
        self.listings = listings

    @classmethod
    def load(cls, path: str) -> "Catalog":
        
        with open(path, encoding="utf-8") as f:            
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Catalog JSON must contain a list")
        datalist: list[Listing]=[]
        
        for item in data:

            listing = Listing.from_dict(item)
            datalist.append(listing)

        return cls(datalist)
    @staticmethod
    def check_op( op,itemdata, consdata):

        match op:
            case "lt":
                return itemdata < consdata
            case "lte":
                return itemdata <= consdata
            case "gt":
                return itemdata > consdata
            case "gte":
                return itemdata >= consdata
            case "eq":
                return itemdata == consdata
            case _:
                return False
        

    def matches(self, item: Listing, cond: Conditions) -> bool:
        """Подходит ли объявление: город и ограничения его категории.

        Границы: lte/gte включают значение, lt/gt нет. Нет ключа = неизвестно = не подходит.
        """

        if item.city_id!=cond.city_id:
            return False
        
        for cons in cond.constraints:
            if item.category != cons.category:
                continue
            if cons.key not in item.attributes:
                return False
            itemdata = item.attributes[cons.key]
            if not self.check_op(cons.op, itemdata, cons.value):
                return False
        return True
        

    def candidates(self, cond: Conditions) -> dict[str, list[Listing]]:
        """Подходящие объявления по каждой запрошенной категории: {"table": [...], ...}."""

        result = {}

        for category in cond.categories:

            result[category] = [item for item in self.listings if item.category==category and self.matches(item,cond)]
        return result