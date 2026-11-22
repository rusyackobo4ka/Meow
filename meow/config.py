"""Конфигурация приложения. Единственное место, где читаются env.

По ТЗ LLM_* приходят из os.environ; значения могут меняться в финальной проверке.
Дефолтов нет: отсутствие переменной — техническая ошибка.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

REQUIRED_ENV = ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "LLM_USER_AGENT")


class ConfigError(RuntimeError):
    """Ошибка конфигурации. main.py → stderr + код 1."""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str
    user_agent: str

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "LLMConfig":
        env = os.environ if env is None else env

        missing = [k for k in REQUIRED_ENV if not (env.get(k) or "").strip()]
        if missing:
            raise ConfigError(
                "не заданы переменные окружения: " + ", ".join(missing)
                + ". См. .env.example и README."
            )

        cfg = cls(
            base_url=env["LLM_BASE_URL"].strip(),
            model=env["LLM_MODEL"].strip(),
            api_key=env["LLM_API_KEY"].strip(),
            user_agent=env["LLM_USER_AGENT"].strip(),
        )
        cfg._validate()
        return cfg

    def _validate(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ConfigError(
                f"LLM_BASE_URL должен быть http(s) URL, получено: {self.base_url!r}"
            )

    def __repr__(self) -> str:
        return (
            f"LLMConfig(base_url={self.base_url!r}, model={self.model!r}, "
            f"api_key=***, user_agent={self.user_agent!r})"
        )


@dataclass(frozen=True)
class AppConfig:
    """Всё, что нужно приложению. Пока только LLM, дальше можно расширять."""
    llm: LLMConfig

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "AppConfig":
        return cls(llm=LLMConfig.from_env(env))

    def __repr__(self) -> str:
        return f"AppConfig(llm={self.llm!r})"
