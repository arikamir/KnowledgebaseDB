#!/usr/bin/env bash
set -euo pipefail

[[ "${1:-}" == "upgrade" && -n "${2:-}" && $# -eq 2 ]] || {
  printf 'usage: run-migration.sh upgrade TARGET\n' >&2
  exit 2
}

case "$2" in
  learning@head) revision=007_learning_sessions ;;
  progress@head) revision=008_owned_progress ;;
  009_merge_learning_progress) revision=009_merge_learning_progress ;;
  *)
    printf 'migration target is not approved\n' >&2
    exit 2
    ;;
esac

current_heads() {
  alembic current 2>/dev/null | awk '{print $1}' | sed '/^$/d' | sort -u | paste -sd, -
}

before_heads="$(current_heads)"
[[ -n "$before_heads" ]] || before_heads="base"
printf 'MIGRATION_BEFORE_HEADS=%s\n' "$before_heads"

alembic upgrade "$revision"

after_heads="$(current_heads)"
[[ -n "$after_heads" ]] || {
  printf 'migration completed without a current revision\n' >&2
  exit 1
}
printf 'MIGRATION_AFTER_HEADS=%s\n' "$after_heads"
