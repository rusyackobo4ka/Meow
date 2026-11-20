"""Точка входа: ./run --catalog /path/catalog.json < request.json > response.json"""
import argparse
import json
import sys

from assistant import BuyerAssistant
from catalog import Catalog
from config import AppConfig, ConfigError
from dialog import DialogManager, ResponseBuilder
from env_loader import bootstrap_env  # локальная удобность, опционально
from extract import ConditionExtractor
from llm_client import LLMClient
from selector import KitSelector


def build_assistant(config: AppConfig, catalog_path: str) -> BuyerAssistant:
    """Единственное место, где собирается граф объектов."""
    return BuyerAssistant(
        catalog=Catalog.load(catalog_path),
        extractor=ConditionExtractor(LLMClient(config.llm)),
        dialog=DialogManager(),
        selector=KitSelector(),
        builder=ResponseBuilder(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    args = parser.parse_args()

    bootstrap_env()

    try:
        config = AppConfig.from_env()
        assistant = build_assistant(config, args.catalog)
        request = json.load(sys.stdin)
        response = assistant.handle(request)
    except ConfigError as exc:
        print(f"error: ConfigError: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
