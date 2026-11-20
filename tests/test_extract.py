"""p1: валидация конфигурации без реального окружения.

`LLMConfig.from_env({dict})` позволяет проверить обязательность, обрезку
и валидацию LLM_* переменных без чтения process env.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import ConfigError, LLMConfig  # noqa: E402

ENV = {
    "LLM_BASE_URL": "https://api.example.org/v1",
    "LLM_MODEL": "google/gemma-4-31B-it",
    "LLM_API_KEY": "secret-key",
    "LLM_USER_AGENT": "team/1.0",
}


def test_from_env_ok() -> None:
    cfg = LLMConfig.from_env(dict(ENV))
    assert cfg.base_url == ENV["LLM_BASE_URL"]
    assert cfg.model == ENV["LLM_MODEL"]
    assert cfg.api_key == ENV["LLM_API_KEY"]
    assert cfg.user_agent == ENV["LLM_USER_AGENT"]


def test_from_env_trims_values() -> None:
    env = {k: f"  {v}  " for k, v in ENV.items()}
    cfg = LLMConfig.from_env(env)
    assert cfg.base_url == ENV["LLM_BASE_URL"]
    assert cfg.model == ENV["LLM_MODEL"]


def test_from_env_missing_var_raises() -> None:
    env = dict(ENV)
    del env["LLM_MODEL"]
    try:
        LLMConfig.from_env(env)
    except ConfigError as exc:
        assert "LLM_MODEL" in str(exc)
    else:
        raise AssertionError("ожидался ConfigError")


def test_from_env_blank_value_is_missing() -> None:
    env = dict(ENV)
    env["LLM_API_KEY"] = "   "
    try:
        LLMConfig.from_env(env)
    except ConfigError:
        pass
    else:
        raise AssertionError("ожидался ConfigError")


def test_bad_base_url_raises() -> None:
    env = dict(ENV)
    env["LLM_BASE_URL"] = "not-a-url"
    try:
        LLMConfig.from_env(env)
    except ConfigError as exc:
        assert "LLM_BASE_URL" in str(exc)
    else:
        raise AssertionError("ожидался ConfigError")


def test_repr_hides_api_key() -> None:
    cfg = LLMConfig.from_env(dict(ENV))
    assert ENV["LLM_API_KEY"] not in repr(cfg)


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
