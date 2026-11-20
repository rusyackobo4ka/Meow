"""Проверка экстракции на реальной модели.
Запуск: pytest -v -s test_extract_live.py
(-s нужен, чтобы видеть, что вернула модель)
"""
from __future__ import annotations

import time

import pytest

from config import AppConfig
from env_loader import bootstrap_env
from extract import ConditionExtractor
from llm_client import LLMClient


def U(text): return {"role": "user", "text": text}
def A(text): return {"role": "assistant", "text": text}


def cons_set(cond) -> set:
    return {(c.category, c.key, c.op, c.value) for c in cond.constraints}


@pytest.fixture(scope="session")
def config():
    bootstrap_env()
    return AppConfig.from_env()  # нет настроек, тест упадёт, и это правильно


@pytest.fixture
def extract(config):
    def run(messages):
        time.sleep(3)  # лимит API: 20 попыток за 60 с
        cond = ConditionExtractor(LLMClient(config.llm)).extract(
            messages)  # новый клиент = новый дедлайн
        print("\n", cond)
        return cond
    return run


def test_full_request(extract):
    c = extract(
        [U("Стол не шире метра, кресло с регулировкой высоты и лампа. Таганрог. До 15 000 ₽ за всё.")])
    assert c.city_id == "taganrog"
    assert c.budget_rub == 15000
    assert set(c.categories) == {"table", "chair", "lamp"}
    assert cons_set(c) == {("table", "width_cm", "lte", 100),
                           ("chair", "adjustable_height", "eq", True)}


def test_missing_city_and_budget(extract):
    c = extract([U("Нужен стол")])
    assert c.city_id is None
    assert c.budget_rub is None
    assert c.categories == ["table"]
    assert c.constraints == []


def test_missing_only_categories(extract):
    c = extract([U("Таганрог, до 10000")])
    assert c.city_id == "taganrog" and c.budget_rub == 10000
    assert c.categories is None


def test_extract_full_20_messages_with_sizes(extract):
    """Максимальная история по ТЗ (20 сообщений): замена условий, метры, границы, все категории."""
    c = extract([
        U("Привет! Ищу мебель для кабинета."),
        A("Здравствуйте! Какие категории вас интересуют?"),
        U("Стол и стул, может ещё лампу."),
        A("В каком городе будет самовывоз?"),
        U("В Ростове."),
        A("Какой общий бюджет на весь комплект, в рублях?"),
        U("Думаю, тысяч 30 хватит."),
        A("Уточните ширину стола."),
        U("Не шире метра."),
        A("А по стулу есть пожелания?"),
        U("Да, нужна регулировка высоты."),
        A("По лампе что важно?"),
        U("Цветовая температура от 3000 до 4000 кельвинов."),
        A("Бюджет всё ещё 30 тысяч?"),
        U("Нет, поднимем до 45 тысяч."),
        A("Ширину стола оставляем метр?"),
        U("Да, но не меньше 80 см."),
        A("Категории те же — стол, стул, лампа?"),
        U("Да, всё верно."),
        U("Кстати, если что, город можно и Таганрог."),
    ])

    # --- Основные условия ---
    assert c.city_id == "taganrog"
    assert c.budget_rub == 45_000
    assert set(c.categories) == {"table", "chair", "lamp"}

    cons = cons_set(c)

    # --- Стол: ширина в диапазоне [80, 100] ---
    assert ("table", "width_cm", "lte", 100) in cons
    assert ("table", "width_cm", "gte", 80) in cons

    # --- Стул: только регулировка. Других ключей у стула в ТЗ нет ---
    assert ("chair", "adjustable_height", "eq", True) in cons
    assert not any(
        cat == "chair" and k != "adjustable_height"
        for cat, k, _, _ in cons
    )

    # --- Лампа: [3000, 4000] ---
    assert ("lamp", "color_temperature_k", "gte", 3000) in cons
    assert ("lamp", "color_temperature_k", "lte", 4000) in cons

    # --- Типы значений: bool для adjustable_height, int для остальных ---
    for cat, k, _, value in cons:
        if k == "adjustable_height":
            assert isinstance(value, bool), f"{
                k} должен быть bool, получено {type(value)}"
        else:
            assert isinstance(value, int) and not isinstance(value, bool), (
                f"{k} должен быть int, получено {type(value)}"
            )

    # --- Состав: ровно по одному товару каждой категории запрошен ---
    assert len(c.categories) == 3
    assert len(set(c.categories)) == 3


def test_clarification_short_answer(extract):
    c = extract([
        U("Нужен стол не шире метра и лампа. Таганрог."),
        A("Какой у вас бюджет на весь комплект, в рублях?"),
        U("15 тысяч"),
    ])
    assert c.budget_rub == 15000
    assert c.city_id == "taganrog"
    assert set(c.categories) == {"table", "lamp"}
    assert ("table", "width_cm", "lte", 100) in cons_set(c)


def test_clarification_city_answer(extract):
    c = extract([
        U("Стол и лампа, до 8000"),
        A("В каком городе вам удобен самовывоз? Доступны Таганрог, Ростов-на-Дону и Азов."),
        U("Азов"),
    ])
    assert c.city_id == "azov" and c.budget_rub == 8000
    assert set(c.categories) == {"table", "lamp"}


def test_budget_replacement_keeps_rest(extract):
    c = extract([
        U("Стол и кресло, Ростов-на-Дону, до 20000"),
        A("Вот подходящие варианты..."),
        U("а теперь до 12 000"),
    ])
    assert c.budget_rub == 12000
    assert c.city_id == "rostov-na-donu"
    assert set(c.categories) == {"table", "chair"}


def test_constraint_replacement(extract):
    c = extract([
        U("Стол не шире 100 см, Азов, до 9000"),
        A("Вот подходящие варианты..."),
        U("давай стол не шире 80 см"),
    ])
    assert cons_set(c) == {("table", "width_cm", "lte", 80)}
    assert c.budget_rub == 9000


def test_unsupported_category(extract):
    c = extract([U("Нужен шкаф. Таганрог, до 10000")])
    assert c.categories is None


def test_city_outside_directory(extract):
    c = extract([U("Стол, Москва, до 10000")])
    assert c.city_id is None
    assert c.budget_rub == 10000


def test_one_and_half_meters(extract):
    c = extract([U("Стол не шире полутора метров, Азов, до 9000")])
    assert ("table", "width_cm", "lte", 150) in cons_set(c)


def test_strict_less(extract):
    c = extract([U("Стол уже 120 см, Азов, до 9000")])
    assert ("table", "width_cm", "lt", 120) in cons_set(c)


def test_strict_greater(extract):
    c = extract([U("Стол шире 100 см, Азов, до 9000")])
    assert ("table", "width_cm", "gt", 100) in cons_set(c)


def test_at_least(extract):
    c = extract([U("Стол не менее 140 см, Азов, до 9000")])
    assert ("table", "width_cm", "gte", 140) in cons_set(c)


def test_exact_value(extract):
    c = extract([U("Лампа ровно 4000 К, Таганрог, 5000 рублей")])
    assert ("lamp", "color_temperature_k", "eq", 4000) in cons_set(c)


def test_lamp_range(extract):
    c = extract([U("Лампа от 3000 до 4000 К, Таганрог, 5000 рублей")])
    assert {("lamp", "color_temperature_k", "gte", 3000),
            ("lamp", "color_temperature_k", "lte", 4000)} <= cons_set(c)


def test_no_adjustment(extract):
    c = extract([U("Кресло без регулировки высоты, Азов, до 7000")])
    assert ("chair", "adjustable_height", "eq", False) in cons_set(c)


def test_chair_synonym(extract):
    c = extract([U("Нужен стул, Таганрог, до 3000")])
    assert c.categories == ["chair"]


def test_budget_k_notation(extract):
    c = extract([U("Лампа, Азов, бюджет 5к")])
    assert c.budget_rub == 5000


def test_no_constraints_means_empty_list(extract):
    c = extract([U("Стол, кресло и лампа, Азов, до 20000")])
    assert c.constraints == []


def test_constraint_only_for_named_category(extract):
    c = extract([U("Стол и лампа, Азов, до 9000, стол не шире метра")])
    assert {k[0] for k in cons_set(c)} == {"table"}
