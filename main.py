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
