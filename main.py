"""Шим точки входа: сохраняет совместимость с ``./run`` и ``python3 main.py``.

Вся логика живёт в пакете ``meow`` (см. ``meow/main.py`` — composition root).
"""
import sys

from meow.main import main

if __name__ == "__main__":
    sys.exit(main())

