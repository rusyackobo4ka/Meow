"""Тесты unsupported_categories для extractor. Подмен модели нет.

1) Тесты _normalize: вызываем напрямую со словарём (без сети), проверяем устойчивость.
2) Живые тесты: настоящая модель через LLM_* переменные окружения.
   Без LLM_API_KEY они пропускаются. Каждый тест создаёт новый LLMClient,
   потому что дедлайн 100 с считается от создания клиента.

Запуск: pytest -q tests/test_extractor_unsupported.py
"""
import os
from types import SimpleNamespace

import pytest

from meow.extract import ConditionExtractor, EXTRACT_SCHEMA, SYSTEM_PROMPT
from meow.llm_client import LLMClient

norm = ConditionExtractor._normalize


def raw(**over):
    base = {
        "city_id": "azov",
        "budget_rub": 15000,
        "categories": ["table"],
        "unsupported_categories": [],
        "constraints": [],
    }
    base.update(over)
    return base


# ---------- схема и промпт ----------

def test_schema_has_unsupported_categories():
    props = EXTRACT_SCHEMA["properties"]
    assert props["unsupported_categories"]["type"] == "array"
    assert props["unsupported_categories"]["items"]["type"] == "string"


def test_schema_requires_unsupported_categories():
    assert "unsupported_categories" in EXTRACT_SCHEMA["required"]


def test_prompt_mentions_unsupported_categories():
    assert "unsupported_categories" in SYSTEM_PROMPT
    assert "пятью" in SYSTEM_PROMPT


# ---------- _normalize ----------

def test_only_unsupported():
    c = norm(raw(categories=[], unsupported_categories=["диван"]))
    assert c.categories is None
    assert c.unsupported_categories == ["диван"]


def test_supported_plus_unsupported():
    c = norm(raw(categories=["table"], unsupported_categories=["диван"]))
    assert c.categories == ["table"]
    assert c.unsupported_categories == ["диван"]


def test_no_unsupported():
    c = norm(raw(categories=["table", "lamp"]))
    assert c.categories == ["table", "lamp"]
    assert c.unsupported_categories == []


def test_nothing_said_about_items():
    c = norm(raw(categories=[], unsupported_categories=[]))
    assert c.categories is None
    assert c.unsupported_categories == []


@pytest.mark.parametrize("value", [None, "диван", 5, {"a": 1}, True])
def test_unsupported_wrong_type_gives_empty_list(value):
    assert norm(raw(unsupported_categories=value)).unsupported_categories == []


def test_unsupported_key_missing():
    data = raw()
    del data["unsupported_categories"]
    assert norm(data).unsupported_categories == []


def test_unsupported_filters_junk():
    c = norm(raw(unsupported_categories=[1, None, "  ", "", ["x"], "шкаф", " полка "]))
    assert c.unsupported_categories == ["шкаф", "полка"]


def test_unsupported_cut_to_six_after_filtering():
    words = ["a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8"]
    c = norm(raw(unsupported_categories=[None, ""] * 3 + words))
    assert c.unsupported_categories == words[:6]


def test_unsupported_independent_of_categories_type():
    c = norm(raw(categories=None, unsupported_categories=["диван"]))
    assert c.categories is None
    assert c.unsupported_categories == ["диван"]


def test_unknown_words_do_not_leak_into_categories():
    c = norm(raw(categories=["table", "диван", "sofa"], unsupported_categories=["диван"]))
    assert c.categories == ["table"]
    assert c.unsupported_categories == ["диван"]


def test_unhashable_items_in_categories_do_not_crash():
    assert norm(raw(categories=[["table"], {"a": 1}, "table"])).categories == ["table"]


def test_unsupported_does_not_break_other_fields():
    c = norm(raw(
        city_id="taganrog", budget_rub=8000, unsupported_categories=["диван"],
        constraints=[{"category": "table", "key": "width_cm", "op": "lte", "value": 100}],
    ))
    assert (c.city_id, c.budget_rub, len(c.constraints)) == ("taganrog", 8000, 1)
    assert c.unsupported_categories == ["диван"]


# ---------- живые тесты с настоящей моделью ----------

live = pytest.mark.skipif(not os.environ.get("LLM_API_KEY"),
                          reason="нет LLM_API_KEY")


@pytest.fixture
def extractor():
    cfg = SimpleNamespace(
        base_url=os.environ.get(
            "LLM_BASE_URL",
            "https://sfedu-hackathon-ai-gateway.sfedu-hackathon-ai-gateway.workers.dev/v1"),
        model=os.environ.get("LLM_MODEL", "google/gemma-4-31B-it"),
        api_key=os.environ.get("LLM_API_KEY", ""),
        user_agent=os.environ.get("LLM_USER_AGENT", "hackathon-tests/1.0"),
    )
    return ConditionExtractor(LLMClient(cfg))


def user(text):
    return [{"role": "user", "text": text}]


@live
def test_live_only_unsupported(extractor):
    c = extractor.extract(user("Хочу диван, Азов, 15 тысяч"))
    assert c.categories is None
    assert c.unsupported_categories


@live
def test_live_wardrobe(extractor):
    c = extractor.extract(user("Хочу шкаф"))
    assert c.categories is None
    assert c.unsupported_categories


@live
def test_live_supported_plus_unsupported(extractor):
    c = extractor.extract(user("Хочу стол и диван, Азов, 15 тысяч"))
    assert c.categories == ["table"]
    assert c.unsupported_categories


@live
def test_live_all_supported(extractor):
    c = extractor.extract(user("Стол и лампа, Азов, 8 тысяч"))
    assert set(c.categories) == {"table", "lamp"}
    assert c.unsupported_categories == []


@live
def test_live_armchair_is_supported(extractor):
    c = extractor.extract(user("Нужно кресло, Таганрог, 10 тысяч"))
    assert c.categories == ["chair"]
    assert c.unsupported_categories == []


@live
def test_live_replaced_by_supported(extractor):
    history = [
        {"role": "user", "text": "Хочу диван"},
        {"role": "assistant",
         "text": "Диваны я не подбираю. Могу подобрать стол, стул или лампу. Что выбрать?"},
        {"role": "user", "text": "Тогда просто стол, Азов, 10 тысяч"},
    ]
    c = extractor.extract(history)
    assert c.categories == ["table"]
    assert c.unsupported_categories == []