#!/usr/bin/env bash
# Создаёт каркас проекта "ИИ-помощник покупателя" в ТЕКУЩЕЙ папке.
# Запускать из корня своего репозитория (куда уже скопированы data/, examples/, schemas/).
set -e

mkdir -p tests

# ---------- run ----------
cat > run << 'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
exec python3 main.py "$@"
EOF
chmod +x run

# ---------- models.py ----------
cat > models.py << 'EOF'
"""Общие типы данных. Ими обмениваются все модули, формат менять только по договорённости."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

CITIES = ["taganrog", "rostov-na-donu", "azov"]
CATEGORIES = ["table", "chair", "lamp"]
OPS = ("lt", "lte", "gt", "gte", "eq")


@dataclass
class Constraint:
    """Одно ограничение по характеристике, например стол не шире 100 см."""
    category: str   # table | chair | lamp
    key: str        # width_cm | adjustable_height | color_temperature_k
    op: str         # lt | lte | gt | gte | eq
    value: Any      # int или bool


@dataclass
class Conditions:
    """Условия покупателя. None означает, что в диалоге этого не сказано (нужно спросить)."""
    city_id: Optional[str] = None
    budget_rub: Optional[int] = None
    categories: Optional[list[str]] = None
    constraints: list[Constraint] = field(default_factory=list)


@dataclass
class Listing:
    """Одно объявление из каталога."""
    id: str
    category: str
    title: str
    description: str
    price_rub: int
    city_id: str
    attributes: dict[str, Any]

    @classmethod
    def from_dict(cls, d: dict) -> "Listing":
        return cls(d["id"], d["category"], d["title"], d["description"],
                   d["price_rub"], d["city_id"], d["attributes"])


@dataclass
class Kit:
    """Комплект: по одному объявлению каждой запрошенной категории."""
    items: list[Listing]

    @property
    def listing_ids(self) -> list[str]:
        return [x.id for x in self.items]

    @property
    def total_rub(self) -> int:
        return sum(x.price_rub for x in self.items)


@dataclass
class Question:
    """Вопрос для clarify."""
    field: str   # budget_rub | city_id | categories
    text: str
EOF

# ---------- llm_client.py (разработчик 1) ----------
cat > llm_client.py << 'EOF'
"""Разработчик 1: клиент модели Gemma через API организаторов."""
from __future__ import annotations


class LLMClient:
    """Настройки читаются из LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, LLM_USER_AGENT. Ключ в код не писать."""

    def __init__(self) -> None:
        # TODO: прочитать переменные окружения, проверить, что ключ задан
        raise NotImplementedError

    def complete_json(self, messages: list[dict], schema: dict, max_tokens: int = 256) -> dict:
        """Один вызов модели с response_format=json_schema (strict). Вернуть разобранный JSON.

        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        Лимиты: до 32 КБ текста, до 90 с, до 20 запросов в минуту.
        """
        raise NotImplementedError
EOF

# ---------- extract.py (разработчик 1) ----------
cat > extract.py << 'EOF'
"""Разработчик 1: из истории диалога получаем структурированные условия."""
from __future__ import annotations

from llm_client import LLMClient
from models import Conditions


class ConditionExtractor:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def extract(self, messages: list[dict]) -> Conditions:
        """messages: [{"role": "user"|"assistant", "text": "..."}] из входного JSON.

        Учитывать всю историю: новая реплика заменяет только своё условие.
        Неизвестное условие = None. Результат модели проверять по справочникам.
        """
        raise NotImplementedError
EOF

# ---------- catalog.py (разработчик 2) ----------
cat > catalog.py << 'EOF'
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
EOF

# ---------- selector.py (разработчик 3) ----------
cat > selector.py << 'EOF'
"""Разработчик 3: подбор комплектов."""
from __future__ import annotations

from models import Conditions, Kit, Listing


class KitSelector:
    def select(self, candidates: dict[str, list[Listing]], cond: Conditions, limit: int = 3) -> list[Kit]:
        """До `limit` разных комплектов: по одному объявлению каждой категории, сумма <= бюджета.

        Пустой список = подходящих комплектов нет (будет no_match).
        """
        raise NotImplementedError
EOF

# ---------- dialog.py (разработчик 4) ----------
cat > dialog.py << 'EOF'
"""Разработчик 4: диалог (вопросы, объяснения) и сборка JSON-ответа."""
from __future__ import annotations

from models import Conditions, Kit, Question


class DialogManager:
    def find_missing(self, cond: Conditions) -> list[Question]:
        """Вопросы для clarify по недостающим budget_rub, city_id, categories (каждое поле один раз)."""
        raise NotImplementedError

    def explain(self, kit: Kit, cond: Conditions) -> str:
        """Понятное объяснение комплекта на данных каталога (цена, город, характеристики)."""
        raise NotImplementedError

    def no_match_message(self, cond: Conditions) -> str:
        """Что мешает найти комплект и что покупатель может изменить."""
        raise NotImplementedError


class ResponseBuilder:
    """Собирает ответ строго по schemas/response.schema.json."""

    def clarify(self, questions: list[Question]) -> dict:
        raise NotImplementedError

    def ok(self, kits: list[Kit], explanations: list[str]) -> dict:
        raise NotImplementedError

    def no_match(self, message: str) -> dict:
        raise NotImplementedError
EOF

# ---------- assistant.py (главный класс, разработчик 5) ----------
cat > assistant.py << 'EOF'
"""Главный класс: связывает все модули. Бизнес-логики здесь нет, только порядок вызовов."""
from __future__ import annotations

from catalog import Catalog
from dialog import DialogManager, ResponseBuilder
from extract import ConditionExtractor
from llm_client import LLMClient
from selector import KitSelector


class BuyerAssistant:
    def __init__(self, catalog: Catalog, extractor: ConditionExtractor,
                 dialog: DialogManager, selector: KitSelector, builder: ResponseBuilder) -> None:
        self.catalog = catalog
        self.extractor = extractor
        self.dialog = dialog
        self.selector = selector
        self.builder = builder

    @classmethod
    def create(cls, catalog_path: str) -> "BuyerAssistant":
        return cls(Catalog.load(catalog_path), ConditionExtractor(LLMClient()),
                   DialogManager(), KitSelector(), ResponseBuilder())

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
EOF

# ---------- main.py (точка входа) ----------
cat > main.py << 'EOF'
"""Точка входа: ./run --catalog /path/catalog.json < request.json > response.json"""
import argparse
import json
import sys

from assistant import BuyerAssistant


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    args = parser.parse_args()

    try:
        request = json.load(sys.stdin)
        response = BuyerAssistant.create(args.catalog).handle(request)
    except Exception as exc:  # технический сбой: лог в stderr, код не 0
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # В stdout только один JSON, без префиксов и логов
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
EOF

# ---------- tests/check_examples.py ----------
cat > tests/check_examples.py << 'EOF'
"""Прогон открытых примеров: python3 tests/check_examples.py"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog.json"


def main() -> int:
    failed = 0
    for case in sorted((ROOT / "examples").iterdir()):
        request = (case / "request.json").read_text(encoding="utf-8")
        expected = json.loads((case / "response.json").read_text(encoding="utf-8"))
        proc = subprocess.run([str(ROOT / "run"), "--catalog", str(CATALOG)],
                              input=request, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            print(f"FAIL {case.name}: код {proc.returncode}\n{proc.stderr}")
            failed += 1
            continue
        got = json.loads(proc.stdout)
        ok = got.get("status") == expected["status"]
        print(("OK  " if ok else "FAIL"), case.name, "->", got.get("status"))
        failed += not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
EOF

# ---------- служебные файлы ----------
cat > requirements.txt << 'EOF'
# Сейчас внешних зависимостей нет (urllib из стандартной библиотеки).
# Если добавите пакет, укажите версию, например: jsonschema==4.23.0
EOF

[ -f .gitignore ] || printf '.env\n__pycache__/\n*.pyc\n' > .gitignore
[ -f README.md ] || printf '# ИИ-помощник покупателя\n\nTODO: установка, запуск, переменные окружения, где используется модель.\n' > README.md

echo "Готово. Структура:"
ls -1

