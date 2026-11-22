
import pytest

from meow.models import Conditions, Constraint, Listing
from meow.catalog import Catalog
from meow.dialog import DialogManager, ResponseBuilder


def L(id_, cat, price, city, attrs, title, desc=""):
    return Listing(
        id=id_,
        category=cat,
        title=title,
        description=desc,
        price_rub=price,
        city_id=city,
        attributes=attrs,
    )


@pytest.fixture
def catalog():
    return Catalog([
        # Азов: столы
        L("T1", "table", 3000, "azov", {"width_cm": 90}, "Стол Норд"),
        L("T2", "table", 5000, "azov", {"width_cm": 120}, "Стол Лофт"),
        L("T3", "table", 2000, "azov", {}, "Стол Эконом"),

        # Азов: лампы
        L("L1", "lamp", 800, "azov", {"color_temperature_k": 3000}, "Лампа Тёплая"),
        L("L2", "lamp", 1200, "azov", {"color_temperature_k": 4500}, "Лампа Нейтральная"),

        # Азов: кресла
        L("C1", "chair", 1500, "azov", {"adjustable_height": False}, "Стул Простой"),
        L("C2", "chair", 2500, "azov", {"adjustable_height": True}, "Кресло Комфорт"),

        # Таганрог: товары для проверки города
        L("TT1", "table", 4000, "taganrog", {"width_cm": 100}, "Стол Таганрог"),
        L("TL1", "lamp", 1000, "taganrog", {"color_temperature_k": 4000}, "Лампа Таганрог"),
    ])


@pytest.fixture
def dialog():
    return DialogManager()


# ======================= бюджетные альтернативы =======================

@pytest.mark.parametrize(
    "cond, expected_budget, expected_items",
    [
        (
            Conditions(
                city_id="azov",
                budget_rub=3000,
                categories=["table", "lamp"],
            ),
            2800,
            ["Стол Эконом", "Лампа Тёплая"],
        ),
        (
            Conditions(
                city_id="azov",
                budget_rub=2000,
                categories=["table", "lamp"],
            ),
            2800,
            ["Стол Эконом", "Лампа Тёплая"],
        ),
        (
            Conditions(
                city_id="azov",
                budget_rub=1000,
                categories=["table", "chair", "lamp"],
            ),
            4300,
            ["Стол Эконом", "Стул Простой", "Лампа Тёплая"],
        ),
    ],
    ids=[
        "budget_below_cheapest_kit",
        "budget_far_below_cheapest_kit",
        "three_categories",
    ],
)
def test_no_match_suggests_minimum_budget(
    cond, expected_budget, expected_items, catalog, dialog
):
    message = dialog.no_match_message(cond, catalog)

    assert f"{expected_budget:,}".replace(",", "\u00a0") in message

    for title in expected_items:
        assert title in message


def test_no_match_shows_current_budget(catalog, dialog):
    cond = Conditions(
        city_id="azov",
        budget_rub=2000,
        categories=["table", "lamp"],
    )

    message = dialog.no_match_message(cond, catalog)

    assert "2\u00a0000 ₽" in message
    assert "2\u00a0800 ₽" in message


def test_no_match_suggests_budget_only_for_requested_city(catalog, dialog):
    cond = Conditions(
        city_id="taganrog",
        budget_rub=1000,
        categories=["table", "lamp"],
    )

    message = dialog.no_match_message(cond, catalog)

    assert "5\u00a0000 ₽" in message
    assert "Таганроге" in message


# ======================= ограничения характеристик =======================

def test_no_match_does_not_ignore_constraints(catalog, dialog):
    cond = Conditions(
        city_id="azov",
        budget_rub=1000,
        categories=["table", "lamp"],
        constraints=[
            Constraint("table", "width_cm", "lte", 100),
            Constraint("lamp", "color_temperature_k", "gte", 4000),
        ],
    )

    message = dialog.no_match_message(cond, catalog)

    # Подходящие товары: стол за 3000 и лампа за 1200.
    # Минимальный комплект стоит 4200 рублей.
    assert "4\u00a0200 ₽" in message
    assert "Стол Норд" in message
    assert "Лампа Нейтральная" in message


def test_no_match_reports_missing_category(catalog, dialog):
    cond = Conditions(
        city_id="rostov-na-donu",
        budget_rub=50000,
        categories=["table", "chair", "lamp"],
    )

    message = dialog.no_match_message(cond, catalog)

    assert "нет подходящих объявлений" in message
    assert "кресло" in message
    assert "другой город" in message
    assert "Самый дешёвый подходящий комплект" not in message


def test_no_match_reports_impossible_constraints(catalog, dialog):
    cond = Conditions(
        city_id="azov",
        budget_rub=20000,
        categories=["table"],
        constraints=[
            Constraint("table", "width_cm", "lt", 50),
        ],
    )

    message = dialog.no_match_message(cond, catalog)

    assert "ограничения по характеристикам" in message
    assert "смягчить требования" in message
    assert "Самый дешёвый подходящий комплект" not in message


# ======================= формат ответа =======================

def test_no_match_response_keeps_contract(catalog, dialog):
    cond = Conditions(
        city_id="azov",
        budget_rub=1000,
        categories=["table", "lamp"],
    )

    message = dialog.no_match_message(cond, catalog)
    response = ResponseBuilder().no_match(message)

    assert response["status"] == "no_match"
    assert set(response) == {"status", "message"}
    assert response["message"].strip()


def test_no_match_never_changes_original_budget(catalog, dialog):
    cond = Conditions(
        city_id="azov",
        budget_rub=1000,
        categories=["table", "lamp"],
    )

    dialog.no_match_message(cond, catalog)

    assert cond.budget_rub == 1000
