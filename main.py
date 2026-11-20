import argparse, json, sys
from llm_client import call_llm

CITIES = ["taganrog", "rostov-na-donu", "azov"]
CATEGORIES = ["table", "chair", "lamp"]

# TODO 1: схема для модели. Подумай, какие поля нужны:
# city_id, budget_rub, categories, ограничения по характеристикам.
# Важно: должна быть возможность сказать «не указано» (null),
# чтобы модель не выдумывала город или бюджет.
EXTRACT_SCHEMA = {}

def extract(messages):
    """Диалог -> условия. Вся история идёт в модель."""
    # TODO 2: system-промпт + история.
    # Правила из контракта: новая реплика заменяет старое значение
    # только этого условия; остальное сохраняется.
    # Не забудь: у решения поле text, у модели content.
    raise NotImplementedError

def find_missing(cond):
    """Вернуть список вопросов для clarify (поля budget_rub / city_id / categories)."""
    # TODO 3: каждый field не больше одного раза, спрашиваем обо ВСЕХ недостающих.
    raise NotImplementedError

def matches(item, cond):
    """Подходит ли объявление: город + ограничения по характеристикам."""
    # TODO 4: подумай про границы («до» включает, «меньше» нет),
    # и что отсутствующий ключ = неизвестно = не подходит, если есть ограничение.
    # Осторожно с False и 0: не проверяй через `if value`.
    raise NotImplementedError

def build_options(catalog, cond):
    """Найти до 3 разных комплектов: по одному товару на категорию, сумма <= бюджет."""
    # TODO 5: переборный поиск по комбинациям.
    # В каталоге до 250 объявлений, так что перебора хватит.
    raise NotImplementedError

def explain(option_items, cond):
    # TODO 6: короткое объяснение на основе данных каталога.
    # Можно простой шаблонной строкой, можно через модель.
    raise NotImplementedError

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    args = ap.parse_args()

    request = json.load(sys.stdin)
    catalog = json.load(open(args.catalog, encoding="utf-8"))

    cond = extract(request["messages"])
    questions = find_missing(cond)
    if questions:
        out = {"status": "clarify", "questions": questions}
    else:
        options = build_options(catalog, cond)
        if options:
            out = {"status": "ok", "options": options}
        else:
            out = {"status": "no_match", "message": "TODO: объясни препятствие"}

    print(json.dumps(out, ensure_ascii=False))   # в stdout только JSON
    # логи только через print(..., file=sys.stderr)

if __name__ == "__main__":
    main()