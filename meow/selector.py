"""Подбор комплектов товаров в пределах бюджета покупателя."""

from __future__ import annotations

from itertools import product

from meow.models import Conditions, Kit, Listing


class KitSelector:
    """Подбирает комплекты товаров по категориям с учётом общего бюджета."""

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
        # Проверка бюджета.
        if cond.budget_rub is None or cond.budget_rub <= 0:
            return []

        # Защита от пустых входных данных и некорректного лимита.
        if not candidates or not cond.categories or limit <= 0:
            return []

        # Проверяем наличие объявлений для каждой категории.
        category_listings: list[list[Listing]] = []

        for category in cond.categories:
            listings = candidates.get(category)

            if not listings:
                return []

            category_listings.append(listings)

        # Сортируем товары внутри каждой категории по возрастанию цены.
        # Это позволит сначала проверять самые бюджетные комбинации.
        sorted_listings = [
            sorted(lst, key=lambda item: item.price_rub)
            for lst in category_listings
        ]

        # Перебираем все комбинации по одному товару каждой категории.
        kits: list[Kit] = []

        for combination in product(*sorted_listings):
            total_rub = sum(item.price_rub for item in combination)

            # Отбрасываем комплекты, превышающие бюджет.
            if total_rub > cond.budget_rub:
                continue

            # Kit из models.py принимает список объявлений.
            kits.append(Kit(items=list(combination)))

            # Достаточно набранных вариантов.
            if len(kits) >= limit:
                break

        return kits