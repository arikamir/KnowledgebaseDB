#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"; shift || true
STATE_DIR="" ENVIRONMENT="" ATTEMPT="" REVISION="" EXPECTED_REVISION=""
while (($#)); do case "$1" in
  --state-dir) STATE_DIR="${2:-}"; shift 2;; --environment) ENVIRONMENT="${2:-}"; shift 2;;
  --attempt) ATTEMPT="${2:-}"; shift 2;; --revision) REVISION="${2:-}"; shift 2;;
  --expected-revision) EXPECTED_REVISION="${2:-}"; shift 2;; *) exit 2;; esac; done
[[ "$ACTION" =~ ^(acquire|release)$ && "$ENVIRONMENT" =~ ^[a-z0-9][a-z0-9._-]{1,62}$ && "$ATTEMPT" =~ ^[A-Za-z0-9._-]{1,128}$ && -n "$STATE_DIR" ]] || exit 2
lock="$STATE_DIR/$ENVIRONMENT.lock"; owner="$lock/owner.json"
case "$ACTION" in
  acquire)
    [[ "$REVISION" =~ ^[0-9a-f]{40}$ && ( -z "$EXPECTED_REVISION" || "$REVISION" == "$EXPECTED_REVISION" ) ]] || { printf 'stale promotion revision\n' >&2; exit 1; }
    mkdir -p "$STATE_DIR"; chmod 0700 "$STATE_DIR"
    mkdir "$lock" 2>/dev/null || { printf 'environment already locked\n' >&2; exit 1; }
    jq -n --arg attempt "$ATTEMPT" --arg revision "$REVISION" '{attemptId:$attempt,sourceRevision:$revision}' > "$owner"; chmod 0444 "$owner" ;;
  release)
    [[ -f "$owner" && "$(jq -r '.attemptId' "$owner")" == "$ATTEMPT" ]] || exit 1
    rm -f "$owner"; rmdir "$lock" ;;
esac
