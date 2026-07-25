#!/usr/bin/env bash
set -euo pipefail

FROM=""
TO=""
OUTPUT=""
REASON=""
ACTOR="${GITHUB_ACTOR:-unknown}"
while (($#)); do
  case "$1" in
    --from) FROM="${2:-}"; shift 2 ;;
    --to) TO="${2:-}"; shift 2 ;;
    --output) OUTPUT="${2:-}"; shift 2 ;;
    --reason) REASON="${2:-}"; shift 2 ;;
    --actor) ACTOR="${2:-}"; shift 2 ;;
    *) echo "rollback: unknown argument $1" >&2; exit 2 ;;
  esac
done
[[ -f "$FROM" && -f "$TO" && -n "$OUTPUT" && -n "$REASON" ]] || { echo "rollback: --from, --to, --reason, and --output are required" >&2; exit 2; }
from_revision="$(jq -r '.sourceRevision' "$FROM")"
to_revision="$(jq -r '.sourceRevision' "$TO")"
[[ "$from_revision" =~ ^[0-9a-f]{40}$ && "$to_revision" =~ ^[0-9a-f]{40}$ ]] || { echo "rollback: declarations must contain full source revisions" >&2; exit 1; }
[[ "$from_revision" != "$to_revision" ]] || { echo "rollback: target must differ from current revision" >&2; exit 1; }
jq -e '(.environment == "nonprod" and (.services | keys | sort) == ["bff","core","ui"] and all(.services[]; .image | test("@sha256:[0-9a-f]{64}$")))' "$TO" >/dev/null || { echo "rollback: target declaration is not a valid nonprod digest release" >&2; exit 1; }

mkdir -p "$(dirname "$OUTPUT")"
jq -n --arg from "$from_revision" --arg to "$to_revision" --arg reason "$REASON" --arg actor "$ACTOR" --arg recordedAt "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{schemaVersion:1,eventType:"rollback",fromRevision:$from,toRevision:$to,reason:$reason,actor:$actor,approvalResult:"missing",outcome:"rejected",recordedAt:$recordedAt,authority:"reviewed Git declaration reversion"}' > "$OUTPUT"
printf 'rollback: prepared reviewed reversion from %s to %s\n' "$from_revision" "$to_revision"
