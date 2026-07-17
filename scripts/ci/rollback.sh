#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-rollback}"; [[ "$ACTION" =~ ^(rollback|recover)$ ]] || exit 2; shift || true
JOURNAL_DIR="" ATTEMPT="" NAMESPACE="${DELIVERY_NAMESPACE:-career-agent}" OPERATOR="" APPROVER="" OPERATOR_ROLE="" APPROVER_ROLE=""
while (($#)); do
  case "$1" in
    --journal-dir) JOURNAL_DIR="${2:-}"; shift 2 ;;
    --attempt) ATTEMPT="${2:-}"; shift 2 ;;
    --namespace) NAMESPACE="${2:-}"; shift 2 ;;
    --operator) OPERATOR="${2:-}"; shift 2 ;;
    --approver) APPROVER="${2:-}"; shift 2 ;;
    --operator-role) OPERATOR_ROLE="${2:-}"; shift 2 ;;
    --approver-role) APPROVER_ROLE="${2:-}"; shift 2 ;;
    *) exit 2 ;;
  esac
done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOURNAL="$JOURNAL_DIR/$ATTEMPT.jsonl"; SNAPSHOT="$JOURNAL_DIR/$ATTEMPT.snapshot.json"; QUARANTINE="$JOURNAL_DIR/$ATTEMPT.quarantine.json"
[[ -f "$JOURNAL" && -f "$SNAPSHOT" ]] || exit 1
"$SCRIPT_DIR/mutation-journal.sh" verify --journal-dir "$JOURNAL_DIR" --attempt "$ATTEMPT"
now_epoch() { "${DELIVERY_NOW_BIN:-date}" +%s; }
smoke_url() { case "$1" in core) printf '%s' "${CORE_SMOKE_URL:-}" ;; bff) printf '%s' "${BFF_SMOKE_URL:-}" ;; ui) printf '%s' "${UI_SMOKE_URL:-}" ;; esac; }
append() { "$SCRIPT_DIR/mutation-journal.sh" append --journal-dir "$JOURNAL_DIR" --attempt "$ATTEMPT" "$@"; }

if [[ "$ACTION" == recover ]]; then
  [[ -f "$QUARANTINE" && ! -e "$QUARANTINE.released" ]] || exit 1
  [[ "$OPERATOR_ROLE" == delivery-recovery-operator && "$APPROVER_ROLE" == platform-operations && "$OPERATOR" =~ ^[A-Za-z0-9._-]{3,128}$ && "$APPROVER" =~ ^[A-Za-z0-9._-]{3,128}$ && "$OPERATOR" != "$APPROVER" ]] || exit 1
  append --event recovery_approved --actor "$OPERATOR+$APPROVER" --result distinct-two-person-approval
  # Previously compensated later entries are reverified before continuation.
  while IFS=$'\t' read -r service previous; do
    "$SCRIPT_DIR/verify.sh" --namespace "$NAMESPACE" --service "$service" --expected-image "$previous" --smoke-url "$(smoke_url "$service")" || exit 1
  done < <(jq -rs '[.[] | select(.event=="reverse_verified")] | unique_by(.service) | .[] | [.service,.previousImage] | @tsv' "$JOURNAL")
fi

start="$(now_epoch)"; failed=0
while IFS= read -r encoded; do
  entry="$(jq -nr --arg value "$encoded" '$value | @base64d')"; service="$(jq -r '.service' <<<"$entry")"; previous="$(jq -r '.previousImage' <<<"$entry")"; intended="$(jq -r '.intendedImage' <<<"$entry")"
  jq -e --arg service "$service" '.[] | select(.event=="reverse_verified" and .service==$service)' < <(jq -s . "$JOURNAL") >/dev/null && continue
  verified=0; attempt_number=0
  for delay in 0 15 45; do
    attempt_number=$((attempt_number + 1)); elapsed=$(( $(now_epoch) - start ))
    ((elapsed < 1200)) || break
    "${DELIVERY_SLEEP_BIN:-sleep}" "$delay"
    append --event reverse_attempt --service "$service" --previous-image "$previous" --intended-image "$intended" --compensation-attempt "$attempt_number" --elapsed-seconds "$elapsed" --result requested
    if "$SCRIPT_DIR/deploy.sh" mutate --namespace "$NAMESPACE" --service "$service" --image "$previous" && \
       "$SCRIPT_DIR/verify.sh" --namespace "$NAMESPACE" --service "$service" --expected-image "$previous" --smoke-url "$(smoke_url "$service")" && \
       (( $(now_epoch) - start < 1200 )); then
      append --event reverse_verified --service "$service" --previous-image "$previous" --intended-image "$intended" --compensation-attempt "$attempt_number" --elapsed-seconds "$(( $(now_epoch) - start ))" --result restored
      verified=1; break
    fi
    append --event reverse_failed --service "$service" --previous-image "$previous" --intended-image "$intended" --compensation-attempt "$attempt_number" --elapsed-seconds "$(( $(now_epoch) - start ))" --result verification-failed
  done
  if ((verified == 0)); then failed=1; break; fi
done < <(jq -rs '[.[] | select(.event=="forward_completed")] | reverse | .[] | @base64' "$JOURNAL")

if ((failed)); then
  append --event terminal --elapsed-seconds "$(( $(now_epoch) - start ))" --result rollback_failed
  [[ -e "$QUARANTINE" ]] || { jq -n --arg attempt "$ATTEMPT" '{attemptId:$attempt,status:"rollback_failed",promotionQuarantined:true}' > "$QUARANTINE"; chmod 0444 "$QUARANTINE"; }
  exit 1
fi
append --event terminal --elapsed-seconds "$(( $(now_epoch) - start ))" --result "$([[ "$ACTION" == recover ]] && printf recovered || printf rolled_back)"
[[ "$ACTION" == recover ]] && { jq -n '{promotionQuarantined:false,recoveryVerified:true}' > "$QUARANTINE.released"; chmod 0444 "$QUARANTINE.released"; }
