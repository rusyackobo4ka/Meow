
import json
import subprocess
import sys
from pathlib import Path


def response_text(response: dict) -> str:
    """Преобразует JSON-ответ run в обычный текст."""

    status = response.get("status", "unknown")

    if status == "clarify":
        questions = response.get("questions", [])
        if questions:
            return "\n".join(q.get("text", "") for q in questions)
        return response.get("message", "Уточни, пожалуйста, детали запроса.")

    if status == "no_match":
        return response.get(
            "message",
            "К сожалению, подходящих вариантов не найдено."
        )

    if status == "ok":
        options = response.get("options", [])

        if not options:
            return "Подходящих вариантов не найдено."

        lines = [f"Нашёл {len(options)} вариантов:\n"]

        for i, option in enumerate(options, 1):
            total = option.get("total_rub", 0)
            listing_ids = option.get("listing_ids", [])
            explanation = option.get("explanation", "")

            lines.append(f"{i}. {explanation}")

            if listing_ids:
                lines.append(
                    f"   ID объявлений: {', '.join(listing_ids)}"
                )

            lines.append(f"   Итого: {total:,} ₽".replace(",", " "))
            lines.append("")

        return "\n".join(lines).strip()

    return response.get("message", "Не удалось обработать запрос.")


def main():
    if len(sys.argv) < 2:
        print("Использование: python chat.py <путь_к_каталогу>")
        return

    catalog = Path(sys.argv[1]).resolve()

    if not catalog.exists():
        print(f"Каталог не найден: {catalog}")
        return

    run_path = Path(__file__).parent / "run"

    if not run_path.exists():
        print(f"Не найден файл запуска: {run_path}")
        return

    messages = []

    print("\n=== Meow — подбор товаров ===")
    print("Напиши запрос. Для выхода введи exit или quit.\n")

    while True:
        try:
            user_text = input("Вы: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nДо встречи!")
            break

        if not user_text:
            continue

        if user_text.lower() in ("exit", "quit", "выход"):
            print("До встречи!")
            break
        if user_text.lower() in ("спасибо",):
            print("Meow: Пожалйста!")
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
                print("Ошибка запуска:")
                print(result.stderr)
                messages.pop()
                continue

            response = json.loads(result.stdout)

        except json.JSONDecodeError:
            print("Ошибка: run вернул некорректный JSON.")
            messages.pop()
            continue
        except Exception as e:
            print(f"Ошибка: {e}")
            messages.pop()
            continue

        answer = response_text(response)

        print("\nMeow:")
        print(answer)
        print()

        messages.append({
            "role": "assistant",
            "text": answer
        })


if __name__ == "__main__":
    main()
