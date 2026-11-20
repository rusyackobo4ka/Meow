"""p5: контракт `BuyerAssistant.handle` end-to-end на стабах.

BuyerAssistant получает зависимости через конструктор (DI из main.build_assistant),
поэтому в тест подставляются фейки — включая FakeLLM-клиент внутри
FakeExtractor. Проверяется порядок вызовов и форма ответа, без реального API.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from assistant import BuyerAssistant  # noqa: E402
from config import LLMConfig  # noqa: E402
from extract import ConditionExtractor  # noqa: E402
from llm_client import LLMClient  # noqa: E402
from models import Conditions, Kit, Listing, Question  # noqa: E402


# ---- стабы зависимостей ----

class FakeExtractor:
    """Имитирует ConditionExtractor с FakeLLM: возвращает готовые условия."""

    def __init__(self, conditions: Conditions) -> None:
        self.conditions = conditions
        self.calls: list[list[dict]] = []

    def extract(self, messages: list[dict]) -> Conditions:
        self.calls.append(messages)
        return self.conditions


class FakeCatalog:
    def __init__(self, candidates: dict[str, list[Listing]]) -> None:
        self._candidates = candidates
        self.calls: list[Conditions] = []

    def candidates(self, cond: Conditions) -> dict[str, list[Listing]]:
        self.calls.append(cond)
        return self._candidates


class FakeDialog:
    def __init__(self, questions: tuple[Question, ...] = (), message: str = "") -> None:
        self._questions = list(questions)
        self._message = message

    def find_missing(self, cond: Conditions) -> list[Question]:
        return list(self._questions)

    def explain(self, kit: Kit, cond: Conditions) -> str:
        return f"Комплект: {', '.join(kit.listing_ids)}, итого {kit.total_rub} руб."

    def no_match_message(self, cond: Conditions) -> str:
        return self._message


class FakeSelector:
    def __init__(self, kits: list[Kit]) -> None:
        self._kits = kits
        self.calls: list[Conditions] = []

    def select(self, candidates, cond, limit=3):
        self.calls.append(cond)
        return list(self._kits)


class FakeBuilder:
    """Имитирует ResponseBuilder: собирает словарь по разделу 4 ТЗ."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def clarify(self, questions: list[Question]) -> dict:
        self.calls.append(("clarify", questions))
        return {
            "status": "clarify",
            "questions": [{"field": q.field, "text": q.text} for q in questions],
        }

    def ok(self, kits: list[Kit], explanations: list[str]) -> dict:
        self.calls.append(("ok", kits, explanations))
        return {
            "status": "ok",
            "options": [
                {"listing_ids": k.listing_ids, "total_rub": k.total_rub,
                 "explanation": e}
                for k, e in zip(kits, explanations)
            ],
        }

    def no_match(self, message: str) -> dict:
        self.calls.append(("no_match", message))
        return {"status": "no_match", "message": message}


# ---- хелперы ----

def listing(item_id: str, price: int) -> Listing:
    return Listing(item_id, "chair", f"Товар {item_id}", "", price, "taganrog", {})


def full_conditions() -> Conditions:
    return Conditions(city_id="taganrog", budget_rub=5000, categories=["chair"])


def make_assistant(cat: FakeCatalog, sel: FakeSelector, dia: FakeDialog,
                   ex: FakeExtractor, b: FakeBuilder) -> BuyerAssistant:
    return BuyerAssistant(catalog=cat, extractor=ex, dialog=dia, selector=sel, builder=b)


# ---- тесты ----

def test_clarify_when_missing_conditions() -> None:
    cond = Conditions()  # всё неизвестно
    q = [Question("budget_rub", "Какой бюджет?"), Question("city_id", "Какой город?")]
    ex = FakeExtractor(cond)
    cat = FakeCatalog({})
    dia = FakeDialog(questions=q)
    sel = FakeSelector([])
    b = FakeBuilder()

    resp = make_assistant(cat, sel, dia, ex, b).handle(
        {"messages": [{"role": "user", "text": "хочу купить мебель"}]})

    assert resp["status"] == "clarify"
    assert [x["field"] for x in resp["questions"]] == ["budget_rub", "city_id"]
    # при clarify не должны вызываться поиск по каталогу и подбор
    assert cat.calls == [] and sel.calls == []


def test_ok_when_kits_found() -> None:
    cond = full_conditions()
    kit = Kit([listing("c1", 1200), listing("c2", 800)])
    ex = FakeExtractor(cond)
    cat = FakeCatalog({"chair": [listing("c1", 1200), listing("c2", 800)]})
    dia = FakeDialog()
    sel = FakeSelector([kit])
    b = FakeBuilder()

    resp = make_assistant(cat, sel, dia, ex, b).handle(
        {"messages": [{"role": "user", "text": "нужен стул"}]})

    assert resp["status"] == "ok"
    assert len(resp["options"]) == 1
    opt = resp["options"][0]
    assert opt["listing_ids"] == ["c1", "c2"]
    assert opt["total_rub"] == 2000
    assert opt["explanation"]
    assert cat.calls and sel.calls  # поиск и подбор происходили


def test_no_match_when_no_kits() -> None:
    cond = full_conditions()
    ex = FakeExtractor(cond)
    cat = FakeCatalog({"chair": []})
    dia = FakeDialog(message="В каталоге нет подходящих стульев.")
    sel = FakeSelector([])
    b = FakeBuilder()

    resp = make_assistant(cat, sel, dia, ex, b).handle(
        {"messages": [{"role": "user", "text": "нужен стул"}]})

    assert resp["status"] == "no_match"
    assert resp["message"]
    # при no_match объяснения не строятся
    assert b.calls == [("no_match", "В каталоге нет подходящих стульев.")]


def test_extractor_receives_full_history() -> None:
    messages = [
        {"role": "user", "text": "нужен стол и стул"},
        {"role": "assistant", "text": "Вопрос: какой бюджет?"},
        {"role": "user", "text": "до 10 тысяч"},
    ]
    ex = FakeExtractor(full_conditions())
    item = listing("c1", 1200)
    resp = make_assistant(FakeCatalog({"chair": [item]}), FakeSelector([Kit([item])]),
                          FakeDialog(), ex, FakeBuilder()).handle({"messages": messages})
    assert ex.calls == [messages]
    assert resp["status"] == "ok"
    assert resp["options"][0]["listing_ids"] == ["c1"]


def test_llm_client_wiring_like_main() -> None:
    """Сборка, как в main.build_assistant: LLMConfig -> LLMClient -> Extractor."""
    cfg = LLMConfig.from_env({
        "LLM_BASE_URL": "https://api.example.org/v1",
        "LLM_MODEL": "google/gemma-4-31B-it",
        "LLM_API_KEY": "k",
        "LLM_USER_AGENT": "team/1.0",
    })
    extractor = ConditionExtractor(LLMClient(cfg))
    assert isinstance(extractor.llm, LLMClient)


def main() -> int:
    failed = 0
    tests = [fn for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for fn in tests:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {fn.__name__}: {type(exc).__name__}: {exc}")
            failed += 1
        else:
            print(f"OK   {fn.__name__}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

