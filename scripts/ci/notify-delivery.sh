#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="$ROOT/config/jenkins-delivery-notifications-v1.json"
BUILD_ID="" EVENT="" STATE_DIR="" NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
while (($#)); do case "$1" in
  --build-id) BUILD_ID="${2:-}"; shift 2;; --event) EVENT="${2:-}"; shift 2;;
  --state-dir) STATE_DIR="${2:-}"; shift 2;; --now) NOW="${2:-}"; shift 2;;
  --policy) POLICY="${2:-}"; shift 2;; *) exit 2;; esac; done
[[ "$BUILD_ID" =~ ^[A-Za-z0-9._-]{1,128}$ && "$EVENT" =~ ^[a-z_]+$ && -n "$STATE_DIR" && -f "$POLICY" ]] || exit 2
jq -e --arg event "$EVENT" '.schemaVersion==1 and .retryWindowHours==24 and .events[$event]!=null' "$POLICY" >/dev/null || exit 1
mkdir -p "$STATE_DIR"; chmod 0700 "$STATE_DIR"
state="$STATE_DIR/$BUILD_ID-$EVENT.json"; now_epoch="$(jq -nr --arg v "$NOW" '$v|fromdateiso8601')"
if [[ -f "$state" ]]; then
  jq -e '.sent==false' "$state" >/dev/null || { jq -c . "$state"; exit 0; }
  first="$(jq -r '.firstAttemptAt|fromdateiso8601' "$state")"
  ((now_epoch - first <= 24 * 3600)) || { printf 'notification retry window expired\n' >&2; exit 1; }
  attempt="$(( $(jq -r '.attempts' "$state") + 1 ))"; first_at="$(jq -r '.firstAttemptAt' "$state")"
else attempt=1; first_at="$NOW"; fi
payload="$(jq -cn --arg build "$BUILD_ID" --arg event "$EVENT" --arg now "$NOW" --argjson contract "$(jq -c --arg event "$EVENT" '.events[$event]' "$POLICY")" '{schemaVersion:1,deduplicationKey:($build+"/"+$event),buildId:$build,event:$event,attemptedAt:$now,contract:$contract}')"
sent=false
if [[ -n "${DELIVERY_NOTIFY_COMMAND:-}" ]] && printf '%s\n' "$payload" | "$DELIVERY_NOTIFY_COMMAND"; then sent=true; fi
temporary="$(mktemp "$STATE_DIR/.notification.XXXXXX")"
jq -n --arg build "$BUILD_ID" --arg event "$EVENT" --arg first "$first_at" --arg last "$NOW" --argjson attempts "$attempt" --argjson sent "$sent" \
  '{schemaVersion:1,buildId:$build,event:$event,deduplicationKey:($build+"/"+$event),firstAttemptAt:$first,lastAttemptAt:$last,attempts:$attempts,sent:$sent}' > "$temporary"
chmod 0600 "$temporary"; mv "$temporary" "$state"; jq -c . "$state"
[[ "$sent" == true ]]
