#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"; [[ "$ACTION" =~ ^(update|export)$ ]] || exit 2; shift
RUN_URL="" STAGE="" MUTATED="false" NETRC_FILE="" CRUMB_FILE="" OUTPUT=""
while (($#)); do
  case "$1" in
    --run-url) RUN_URL="${2:-}"; shift 2 ;;
    --stage) STAGE="${2:-}"; shift 2 ;;
    --environment-mutated) MUTATED="${2:-}"; shift 2 ;;
    --netrc-file) NETRC_FILE="${2:-}"; shift 2 ;;
    --crumb-file) CRUMB_FILE="${2:-}"; shift 2 ;;
    --output) OUTPUT="${2:-}"; shift 2 ;;
    *) exit 2 ;;
  esac
done
[[ "$RUN_URL" =~ ^https?://(127\.0\.0\.1|localhost|\[::1\]):[0-9]+/.+/$ && -r "$NETRC_FILE" && -r "$CRUMB_FILE" ]] || exit 2
crumb="$(cat "$CRUMB_FILE")"; [[ "$crumb" == Jenkins-Crumb:* ]] || exit 1
base="${RUN_URL}controller-audit"
if [[ "$ACTION" == update ]]; then
  [[ "$STAGE" =~ ^(agent_requested|agent_connected|evidence_active|pre_promotion|pre_migration|post_migration|pre_mutation|post_mutation|verification|rollback)$ && "$MUTATED" =~ ^(true|false)$ ]] || exit 2
  curl --fail --silent --show-error --netrc-file "$NETRC_FILE" --header "$crumb" --request POST \
    --data-urlencode "stage=$STAGE" --data-urlencode "environmentMutated=$MUTATED" "$base/update"
else
  [[ -n "$OUTPUT" && ! -e "$OUTPUT" && ! -L "$OUTPUT" ]] || exit 2
  temporary="$(mktemp "$(dirname "$OUTPUT")/.controller-audit.XXXXXX")"
  curl --fail --silent --show-error --netrc-file "$NETRC_FILE" --header "$crumb" --request POST "$base/export" > "$temporary"
  jq -e '.schemaVersion==1 and .controllerLocalAuthoritative==false and (.result|test("^(pending|succeeded|failed|aborted|aborted_recovered)$"))' "$temporary" >/dev/null || { rm -f "$temporary"; exit 1; }
  chmod 0600 "$temporary"; mv "$temporary" "$OUTPUT"
fi
