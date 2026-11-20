"""Локальная удобность: подхватывает .env рядом с репозиторием, если он есть.

В автопроверке окружение выставляется организаторами, поэтому здесь это no-op.
Нужно, чтобы `./run` работал локально без ручного export переменных.
Существующие переменные окружения не перезаписываются.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"


def bootstrap_env(path: str | os.PathLike | None = None) -> None:
    """Если файл существует, прочитать строки KEY=VALUE в os.environ.

    Пропускаются пустые строки, комментарии (с ``#``) и строки без ``=``.
    Переменная, уже заданная в окружении, не перезаписывается.
    """
    env_path = Path(path) if path is not None else ENV_FILE
    if not env_path.exists():
        return

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
