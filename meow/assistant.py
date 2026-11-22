"""Главный класс: связывает все модули. Бизнес-логики здесь нет, только порядок вызовов."""
from __future__ import annotations

from meow.catalog import Catalog
from meow.dialog import DialogManager, ResponseBuilder
from meow.extract import ConditionExtractor
from meow.selector import KitSelector


class BuyerAssistant:
    def __init__(
        self,
        catalog: Catalog,
        extractor: ConditionExtractor,
        dialog: DialogManager,
        selector: KitSelector,
        builder: ResponseBuilder,
    ) -> None:
        self.catalog = catalog
        self.extractor = extractor
        self.dialog = dialog
        self.selector = selector
        self.builder = builder

    def handle(self, request: dict) -> dict:
        """Один запрос -> один ответ (clarify, ok или no_match)."""
        cond = self.extractor.extract(request["messages"])
        questions = self.dialog.find_missing(cond)
        if questions:
            return self.builder.clarify(questions)

        candidates = self.catalog.candidates(cond)
        kits = self.selector.select(candidates, cond)
        if not kits:
            return self.builder.no_match(self.dialog.no_match_message(cond))

        explanations = [self.dialog.explain(k, cond) for k in kits]
        return self.builder.ok(kits, explanations)
        
