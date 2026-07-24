#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
MANIFEST="$ROOT/config/us1-foundation-test-manifest-v1.txt"

[[ -f "$MANIFEST" ]] || { echo "missing US1 foundation manifest" >&2; exit 1; }
TESTS=()
while IFS= read -r line; do
  [[ -z "$line" ]] || TESTS+=("$line")
done < "$MANIFEST"
[[ ${#TESTS[@]} -gt 0 ]] || { echo "empty US1 foundation manifest" >&2; exit 1; }

SORTED=$(printf '%s\n' "${TESTS[@]}" | LC_ALL=C sort -u)
ACTUAL=$(printf '%s\n' "${TESTS[@]}")
[[ "$SORTED" == "$ACTUAL" ]] || { echo "manifest must be sorted and duplicate-free" >&2; exit 1; }

PYTHON_TESTS=()
BFF_TESTS=()
UI_UNIT_TESTS=()
UI_E2E_TESTS=()
for relative in "${TESTS[@]}"; do
  [[ "$relative" != *'*'* && "$relative" != *'?'* && "$relative" != *'['* ]] || { echo "globs are prohibited: $relative" >&2; exit 1; }
  [[ -f "$ROOT/$relative" ]] || { echo "manifest entry is not an exact file: $relative" >&2; exit 1; }
  case "$relative" in
    tests/*.py) PYTHON_TESTS+=("$relative") ;;
    bff/tests/*.ts) BFF_TESTS+=("${relative#bff/}") ;;
    ui/tests/unit/*.ts|ui/tests/unit/*.tsx) UI_UNIT_TESTS+=("${relative#ui/}") ;;
    ui/tests/e2e/*.ts) UI_E2E_TESTS+=("${relative#ui/}") ;;
    *) echo "unapproved test path: $relative" >&2; exit 1 ;;
  esac
done

cd "$ROOT"
scripts/ci/validate-api-contracts.sh
.venv/bin/python scripts/ci/generate_contracts.py --check
npm --prefix bff run typecheck
npm --prefix ui run typecheck
(( ${#PYTHON_TESTS[@]} == 0 )) || .venv/bin/pytest "${PYTHON_TESTS[@]}"
(( ${#BFF_TESTS[@]} == 0 )) || (cd "$ROOT/bff" && npx vitest run "${BFF_TESTS[@]}")
(( ${#UI_UNIT_TESTS[@]} == 0 )) || (cd "$ROOT/ui" && npx vitest run "${UI_UNIT_TESTS[@]}")
(( ${#UI_E2E_TESTS[@]} == 0 )) || (cd "$ROOT/ui" && npx playwright test --project=chromium-current "${UI_E2E_TESTS[@]}")
