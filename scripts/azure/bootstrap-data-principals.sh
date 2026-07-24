#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-dry-run}"; shift || true
PRINCIPALS=""
while (($#)); do case "$1" in --principals) PRINCIPALS="${2:-}"; shift 2;; *) exit 2;; esac; done
[[ "$MODE" =~ ^(dry-run|apply)$ && -f "$PRINCIPALS" ]] || exit 2
jq -e '
  keys==["postgresql","redis","schemaVersion"] and .schemaVersion==1 and
  (.postgresql|keys|sort)==(["core-dml","lab-validation","lifecycle","migrator","retention"]|sort) and
  (.redis|keys)==["bff"] and all(.postgresql[],.redis[]; test("^[0-9a-fA-F-]{36}$"))
' "$PRINCIPALS" >/dev/null || { printf 'data bootstrap: incomplete principal matrix\n' >&2; exit 1; }
printf '[data-bootstrap] exact Redis/PostgreSQL principal matrix and cross-role denial plan validated\n'
[[ "$MODE" == dry-run ]] && exit 0
[[ "${PLATFORM_OPERATIONS_INTERACTIVE:-}" == true && "${DATA_PRINCIPAL_BOOTSTRAP_AUTHORIZED:-}" == true ]] || exit 1
command -v psql >/dev/null && command -v az >/dev/null || exit 1
[[ -n "${PGHOST:-}" && -n "${PGDATABASE:-}" ]] || exit 1
# The reviewed SQL owns grants; object IDs are passed as variables and no password fallback is created.
psql -v ON_ERROR_STOP=1 -f "${DATA_PRINCIPAL_SQL:?reviewed SQL required}" \
  -v core_oid="$(jq -r '.postgresql["core-dml"]' "$PRINCIPALS")" \
  -v lifecycle_oid="$(jq -r '.postgresql.lifecycle' "$PRINCIPALS")" \
  -v retention_oid="$(jq -r '.postgresql.retention' "$PRINCIPALS")" \
  -v lab_oid="$(jq -r '.postgresql["lab-validation"]' "$PRINCIPALS")" \
  -v migrator_oid="$(jq -r '.postgresql.migrator' "$PRINCIPALS")"
"${DATA_PRINCIPAL_DENIAL_TEST:?reviewed denial test required}" "$PRINCIPALS"
