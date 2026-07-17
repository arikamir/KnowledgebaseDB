#!/usr/bin/env bash
set -euo pipefail

MANIFEST="" JOURNAL_DIR="" ATTEMPT="" ENVIRONMENT="" SNAPSHOT_OUT=""
while (($#)); do
  case "$1" in
    --manifest) MANIFEST="${2:-}"; shift 2 ;;
    --journal-dir) JOURNAL_DIR="${2:-}"; shift 2 ;;
    --attempt) ATTEMPT="${2:-}"; shift 2 ;;
    --environment) ENVIRONMENT="${2:-}"; shift 2 ;;
    --snapshot-out) SNAPSHOT_OUT="${2:-}"; shift 2 ;;
    *) exit 2 ;;
  esac
done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$MANIFEST" && "$ATTEMPT" =~ ^[A-Za-z0-9._-]{3,128}$ && "$ENVIRONMENT" =~ ^[a-z0-9][a-z0-9._-]{1,62}$ && -n "$JOURNAL_DIR" && -n "$SNAPSHOT_OUT" ]] || exit 2
jq -e '.selectorPolicy=="digest-only" and (.services|type=="object") and all(.services[]; .image|test("^[a-z0-9.-]+\\.azurecr\\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$"))' "$MANIFEST" >/dev/null || exit 1
for quarantine in "$JOURNAL_DIR"/*.quarantine.json; do [[ ! -e "$quarantine" || -e "$quarantine.released" ]] || { printf 'promotion: environment quarantined\n' >&2; exit 1; }; done
"$SCRIPT_DIR/deploy.sh" snapshot --namespace "$ENVIRONMENT" --output "$SNAPSHOT_OUT"
"$SCRIPT_DIR/mutation-journal.sh" init --journal-dir "$JOURNAL_DIR" --attempt "$ATTEMPT" --environment "$ENVIRONMENT" --snapshot "$SNAPSHOT_OUT"
smoke_url() { case "$1" in core) printf '%s' "${CORE_SMOKE_URL:-}" ;; bff) printf '%s' "${BFF_SMOKE_URL:-}" ;; ui) printf '%s' "${UI_SMOKE_URL:-}" ;; esac; }
for service in core bff ui; do
  jq -e --arg service "$service" '.services[$service] != null' "$MANIFEST" >/dev/null || continue
  previous="$(jq -r --arg service "$service" '.services[$service]' "$SNAPSHOT_OUT")"; intended="$(jq -r --arg service "$service" '.services[$service].image' "$MANIFEST")"
  common=(--journal-dir "$JOURNAL_DIR" --attempt "$ATTEMPT" --service "$service" --previous-image "$previous" --intended-image "$intended")
  "$SCRIPT_DIR/mutation-journal.sh" append "${common[@]}" --event forward_planned --result reversible
  if "$SCRIPT_DIR/deploy.sh" mutate --namespace "$ENVIRONMENT" --service "$service" --image "$intended"; then
    "$SCRIPT_DIR/mutation-journal.sh" append "${common[@]}" --event forward_completed --result mutation-applied
  else
    # A timeout or lost response may have applied the mutation. Compensating
    # from the immutable snapshot is safe even when the live read is also lost.
    actual="$($SCRIPT_DIR/deploy.sh current --namespace "$ENVIRONMENT" --service "$service" 2>/dev/null || true)"
    result="mutation-indeterminate-compensation-required"
    [[ "$actual" == "$intended" ]] && result="mutation-applied-response-lost"
    "$SCRIPT_DIR/mutation-journal.sh" append "${common[@]}" --event forward_completed --result "$result"
    "$SCRIPT_DIR/mutation-journal.sh" append "${common[@]}" --event forward_failed --result mutation-command-failed
    "$SCRIPT_DIR/rollback.sh" rollback --journal-dir "$JOURNAL_DIR" --attempt "$ATTEMPT" --namespace "$ENVIRONMENT" || true
    exit 1
  fi
  if "$SCRIPT_DIR/verify.sh" --namespace "$ENVIRONMENT" --service "$service" --expected-image "$intended" --smoke-url "$(smoke_url "$service")"; then
    "$SCRIPT_DIR/mutation-journal.sh" append "${common[@]}" --event forward_verified --result rollout-and-smoke-passed
  else
    "$SCRIPT_DIR/mutation-journal.sh" append "${common[@]}" --event forward_failed --result verification-failed
    "$SCRIPT_DIR/rollback.sh" rollback --journal-dir "$JOURNAL_DIR" --attempt "$ATTEMPT" --namespace "$ENVIRONMENT" || true
    exit 1
  fi
done
"$SCRIPT_DIR/mutation-journal.sh" append --journal-dir "$JOURNAL_DIR" --attempt "$ATTEMPT" --event terminal --result promoted
