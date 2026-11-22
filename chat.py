

import json
import subprocess
import sys
from pathlib import Path


# ---------- Цвета ----------

USE_COLOR = sys.stdout.isatty() or sys.stderr.isatty()

def color(code, text):
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


CYAN = "96"
BLUE = "94"
GREEN = "92"
YELLOW = "93"
RED = "91"
GRAY = "90"
BOLD = "1"
PURPLE = "95"


def title(text):
    print(color(BOLD + CYAN, text))


def success(text):
    print(color(GREEN, text))


def warning(text):
    print(color(YELLOW, text))


def error(text):
    print(color(RED, text), file=sys.stderr)


# ---------- Форматирование ответов ----------

def response_text(response: dict) -> str:
    """Обычный текст ответа для сохранения в историю."""

    status = response.get("status", "unknown")

    if status == "clarify":
        questions = response.get("questions", [])
        if questions:
            return "\n".join(
                q.get("text", "") for q in questions
            )
        return response.get(
            "message",
            "Уточни, пожалуйста, детали запроса."
        )

    if status == "no_match":
        return response.get(
            "message",
            "К сожалению, подходящих вариантов не найдено."
        )

    if status == "ok":
        options = response.get("options", [])
        if not options:
            return "Подходящих вариантов не найдено."

        lines = []

        for i, option in enumerate(options, 1):
            lines.append(
                f"Вариант {i}: {option.get('explanation', '')}"
            )
            lines.append(
                f"ID: {', '.join(option.get('listing_ids', []))}"
            )
            lines.append(
                f"Итого: {option.get('total_rub', 0)} рублей"
            )

        return "\n".join(lines)

    return response.get(
        "message",
        "Не удалось обработать запрос."
    )


def print_response(response: dict):
    """Красивый вывод ответа в терминал."""

    status = response.get("status", "unknown")

    print()
    title("  MEOW")
    print(color(GRAY, "  " + "─" * 42))

    if status == "clarify":
        questions = response.get("questions", [])

        warning("  Нужно немного уточнить:")
        print()

        for i, question in enumerate(questions, 1):
            print(
                color(BOLD + PURPLE, f"  {i}. ")
                + question.get("text", "")
            )

    elif status == "no_match":
        warning("  Подходящих вариантов не найдено.")
        print()
        print("  " + response.get("message", ""))

    elif status == "ok":
        options = response.get("options", [])

        if not options:
            warning("  Подходящих вариантов не найдено.")
        else:
            success(f"  Нашёл вариантов: {len(options)}")
            print()

            for i, option in enumerate(options, 1):
                print(color(BOLD + BLUE, f"  ┌─ ВАРИАНТ {i}"))

                explanation = option.get("explanation", "")
                print(f"  │  {explanation}")

                listing_ids = option.get("listing_ids", [])
                if listing_ids:
                    print(
                        color(GRAY, "  │  ID: ")
                        + ", ".join(listing_ids)
                    )

                total = option.get("total_rub", 0)
                formatted_total = f"{total:,}".replace(",", " ")

                print(
                    color(BOLD + GREEN, "  │  Итого: ")
                    + color(BOLD + GREEN, f"{formatted_total} ₽")
                )

                print(color(BLUE, "  └" + "─" * 30))
                print()

    else:
        error("  Не удалось обработать запрос.")
        print(response.get("message", ""))

    print(color(GRAY, "  " + "─" * 42))
    print()


# ---------- Основная программа ----------

def main():
    if len(sys.argv) < 2:
        error("Использование: python chat.py <путь_к_каталогу>")
        return

    catalog = Path(sys.argv[1]).resolve()

    if not catalog.exists():
        error(f"Каталог не найден: {catalog}")
        return

    run_path = Path(__file__).parent / "run"

    if not run_path.exists():
        error(f"Не найден файл запуска: {run_path}")
        return

    messages = []

    print()
    print(color(BOLD + CYAN, "  ╔══════════════════════════════════════╗"))
    print(color(BOLD + CYAN, "  ║           MEOW - BUYER AI            ║"))
    print(color(BOLD + CYAN, "  ╚══════════════════════════════════════╝"))
    print()
    print(color(GRAY, "  Умный помощник по подбору товаров"))
    print(color(GRAY, "  Напиши запрос или введи exit для выхода."))
    print()

    while True:
        try:
            user_text = input(
                color(BOLD + GREEN, "  Вы  ❯ ")
            ).strip()

        except (KeyboardInterrupt, EOFError):
            print()
            success("  До встречи! 🐾")
            break

        if not user_text:
            continue

        if user_text.lower() in ("exit", "quit", "выход"):
            print()
            success("  До встречи! 🐾")
            break

        if user_text.lower() == "спасибо":
            print()
            print(color(BOLD + CYAN, "  Meow ❯ ") + "Пожалуйста! 🐾")
            print()
            continue

        messages.append({
            "role": "user",
            "text": user_text
        })

        request = {"messages": messages}

        try:
            result = subprocess.run(
                [
                    str(run_path),
                    "--catalog",
                    str(catalog)
                ],
                input=json.dumps(request, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8"
            )

            if result.returncode != 0:
                error("  Ошибка запуска:")
                print(result.stderr)
                messages.pop()
                continue

            response = json.loads(result.stdout)

        except json.JSONDecodeError:
            error("  run вернул некорректный JSON.")
            messages.pop()
            continue

        except Exception as e:
            error(f"  Ошибка: {e}")
            messages.pop()
            continue

        print_response(response)

        answer = response_text(response)

        messages.append({
            "role": "assistant",
            "text": answer
        })


if __name__ == "__main__":
    main()

