#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec "$ROOT/.venv/bin/python" "$ROOT/scripts/ci/contract_gate.py" --write-digests
