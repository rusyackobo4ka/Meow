"""Подбор комплектов товаров в пределах бюджета покупателя."""

from __future__ import annotations

from itertools import product

from meow.models import Conditions, Kit, Listing


class KitSelector:

    def select(
        self,
        candidates: dict[str, list[Listing]],
        cond: Conditions,
        limit: int = 3,
    ) -> list[Kit]:
        """Возвращает до limit комплектов, подходящих под бюджет.

        Для каждой запрошенной категории выбирается ровно одно объявление.
        Суммарная стоимость комплекта не должна превышать бюджет.

        Ограничения характеристик здесь не проверяются, поскольку они
        уже учтены на этапе фильтрации в catalog.py.

        Args:
            candidates: Объявления, сгруппированные по категориям.
            cond: Условия покупателя.
            limit: Максимальное количество возвращаемых комплектов.

        Returns:
            Список подходящих комплектов. Пустой список означает,
            что подходящих комплектов нет.
        """
        if cond.budget_rub is None or cond.budget_rub <= 0:
            return []

        if not candidates or not cond.categories or limit <= 0:
            return []

        category_listings: list[list[Listing]] = []

        for category in cond.categories:
            listings = candidates.get(category)

            if not listings:
                return []

            category_listings.append(listings)

        sorted_listings = [
            sorted(lst, key=lambda item: item.price_rub)
            for lst in category_listings
        ]

        kits: list[Kit] = []

        for combination in product(*sorted_listings):
            total_rub = sum(item.price_rub for item in combination)

            if total_rub > cond.budget_rub:
                continue

            kits.append(Kit(items=list(combination)))

            if len(kits) >= limit:
                break

        return kits