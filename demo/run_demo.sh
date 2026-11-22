set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CATALOG="$ROOT/demo/catalog.json"
fail=0
for req in "$ROOT"/demo/requests/*.json; do
  name="$(basename "$req" .json)"
  echo "=== $name"
  out="$("$ROOT/run" --catalog "$CATALOG" < "$req")"; code=$?
  if [ "$code" -ne 0 ]; then echo "ОШИБКА: код выхода $code" >&2; fail=1; continue; fi
  echo "$out" | python3 -m json.tool --no-ensure-ascii
  if python3 - "$out" "$ROOT/demo/expected/$name.json" << 'PY'
import json, sys
got = json.loads(sys.argv[1])
want = json.load(open(sys.argv[2], encoding="utf-8"))
sys.exit(0 if got == want else 1)
PY
  then echo "-> совпало с expected"
  else echo "-> ОТЛИЧАЕТСЯ от expected, проверьте вручную" >&2; fail=1
  fi
  sleep 3.5
done
exit $fail
