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
