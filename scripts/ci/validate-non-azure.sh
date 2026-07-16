#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

scripts/ci/validate-api-contracts.sh
.venv/bin/python scripts/ci/generate_contracts.py --check
.venv/bin/pytest -q

npm --prefix bff run lint
npm --prefix bff run typecheck
npm --prefix bff test
npm --prefix bff run build

npm --prefix ui run lint
npm --prefix ui run typecheck
npm --prefix ui test
npm --prefix ui run build

(
  cd ui
  npx playwright test --project=chromium-current
)
