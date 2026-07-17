#!/usr/bin/env bash
set -euo pipefail

MODE="close"
MONTH="" SCHEDULE="" OBSERVATIONS="" MAINTENANCE="" OWNER="" CO_APPROVER="" EVIDENCE_DIR="" GATE_DIR=""
while (($#)); do
  case "$1" in
    --check-opening) MODE="check-opening"; MONTH="${2:-}"; shift 2 ;;
    --month) MONTH="${2:-}"; shift 2 ;;
    --schedule) SCHEDULE="${2:-}"; shift 2 ;;
    --observations) OBSERVATIONS="${2:-}"; shift 2 ;;
    --maintenance) MAINTENANCE="${2:-}"; shift 2 ;;
    --owner) OWNER="${2:-}"; shift 2 ;;
    --co-approver) CO_APPROVER="${2:-}"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    --gate-dir) GATE_DIR="${2:-}"; shift 2 ;;
    *) exit 2 ;;
  esac
done
[[ "$MONTH" =~ ^[0-9]{4}-(0[1-9]|1[0-2])$ && -n "$EVIDENCE_DIR" && -n "$GATE_DIR" && -n "${EVIDENCE_ACCOUNT:-}" && -n "${EVIDENCE_CONTAINER:-}" ]] || exit 2
mkdir -p "$EVIDENCE_DIR" "$GATE_DIR"
chmod 0700 "$EVIDENCE_DIR" "$GATE_DIR"
GATE="$GATE_DIR/pilot-opening.blocked"
if [[ "$MODE" == "check-opening" ]]; then
  exists="$(az storage blob exists --auth-mode login --account-name "$EVIDENCE_ACCOUNT" --container-name "$EVIDENCE_CONTAINER" \
    --name "pilot-availability/$MONTH/monthly-close.json" --query exists -o tsv --only-show-errors)"
  if [[ "$exists" != "true" ]]; then
    printf 'prior calendar-month close missing\n' > "$GATE"; chmod 0600 "$GATE"; exit 1
  fi
  rm -f "$GATE"; exit 0
fi
[[ -f "$SCHEDULE" && -f "$OBSERVATIONS" && -f "$MAINTENANCE" ]] || exit 2
[[ "$OWNER" =~ ^application-operations:[A-Za-z0-9._@-]+$ ]] || exit 1
[[ "$CO_APPROVER" =~ ^platform-operations:[A-Za-z0-9._@-]+$ && "$CO_APPROVER" != *"${OWNER#*:}" ]] || exit 1
mkdir -p "$EVIDENCE_DIR/$MONTH" "$GATE_DIR"
chmod 0700 "$EVIDENCE_DIR" "$EVIDENCE_DIR/$MONTH" "$GATE_DIR"
: > "$GATE"; chmod 0600 "$GATE"
TARGET="$EVIDENCE_DIR/$MONTH/monthly-close.json"
[[ ! -e "$TARGET" ]] || { printf 'calendar-month close already exists\n' >&2; exit 1; }

scheduledMinutes=0 excludedMinutes=0 eligibleMinutes=0 successfulMinutes=0 failedMinutes=0
while IFS= read -r row; do
  timestamp="$(jq -er '.timestamp' <<<"$row")"
  [[ "$timestamp" == "$MONTH"-* ]] || { printf 'schedule escapes calendar-month\n' >&2; exit 1; }
  scheduledMinutes=$((scheduledMinutes + 1))
  ts_epoch="$(jq -nr --arg value "$timestamp" '$value | fromdateiso8601')"
  planned=false
  while IFS= read -r window; do
    start="$(jq -er '.start | fromdateiso8601' <<<"$window")"
    end="$(jq -er '.end | fromdateiso8601' <<<"$window")"
    announced="$(jq -er '.announcedAt | fromdateiso8601' <<<"$window")"
    if ((ts_epoch >= start && ts_epoch < end && start - announced >= 24 * 3600 && excludedMinutes < 240)); then planned=true; break; fi
  done < "$MAINTENANCE"
  if [[ "$planned" == true ]]; then excludedMinutes=$((excludedMinutes + 1)); continue; fi
  eligibleMinutes=$((eligibleMinutes + 1))
  success="$(jq -rs --arg timestamp "$timestamp" '[.[] | select(.timestamp==$timestamp)] | if length == 1 then .[0].success else false end' "$OBSERVATIONS")"
  if [[ "$success" == true ]]; then successfulMinutes=$((successfulMinutes + 1)); else failedMinutes=$((failedMinutes + 1)); fi
done < "$SCHEDULE"
((eligibleMinutes > 0 && successfulMinutes + failedMinutes == eligibleMinutes)) || exit 1
availabilityPercent="$(jq -nr --argjson ok "$successfulMinutes" --argjson total "$eligibleMinutes" '$ok * 10000 / $total | round / 100')"

temporary="$(mktemp "$EVIDENCE_DIR/$MONTH/.monthly-close.XXXXXX")"
trap 'rm -f "$temporary"' EXIT
jq -n --arg month "$MONTH" --arg period "calendar-month" --arg owner "$OWNER" --arg coApprover "$CO_APPROVER" \
  --argjson scheduledMinutes "$scheduledMinutes" --argjson excludedMinutes "$excludedMinutes" \
  --argjson eligibleMinutes "$eligibleMinutes" --argjson successfulMinutes "$successfulMinutes" \
  --argjson failedMinutes "$failedMinutes" --argjson availabilityPercent "$availabilityPercent" \
  '{schemaVersion:1,profileId:"pilot-availability-profile-v1",month:$month,rollupPeriod:$period,
    scheduledMinutes:$scheduledMinutes,excludedMinutes:$excludedMinutes,eligibleMinutes:$eligibleMinutes,
    successfulMinutes:$successfulMinutes,failedMinutes:$failedMinutes,availabilityPercent:$availabilityPercent,
    incidents:[],rtoRpoExercises:[],ownerApproval:{role:"application-operations",actor:$owner},
    recoveryEvidenceCoApproval:{role:"platform-operations",actor:$coApprover}}' > "$temporary"
chmod 0400 "$temporary"
mv "$temporary" "$TARGET"
az storage blob upload --auth-mode login --account-name "$EVIDENCE_ACCOUNT" --container-name "$EVIDENCE_CONTAINER" \
  --name "pilot-availability/$MONTH/monthly-close.json" --file "$TARGET" --if-none-match '*' --overwrite false --only-show-errors >/dev/null
rm -f "$GATE"
printf '%s\n' "$TARGET"
