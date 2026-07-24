#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="$ROOT/config/jenkins-cloud-credential-policy-v1.json"
METADATA=""
ASSIGNMENTS=""
STATE_DIR=""
EVIDENCE_DIR=""
NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
ACK_VERSION=""
OPERATOR=""

usage() {
  printf 'Usage: %s --metadata FILE --assignments FILE --state-dir DIR --evidence-dir DIR [--policy FILE] [--now ISO8601]\n' "$0" >&2
  printf '   or: %s --acknowledge VERSION --operator ID --state-dir DIR [--now ISO8601]\n' "$0" >&2
  exit 2
}

while (($#)); do
  case "$1" in
    --metadata) METADATA="${2:-}"; shift 2 ;;
    --assignments) ASSIGNMENTS="${2:-}"; shift 2 ;;
    --policy) POLICY="${2:-}"; shift 2 ;;
    --state-dir) STATE_DIR="${2:-}"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    --now) NOW="${2:-}"; shift 2 ;;
    --acknowledge) ACK_VERSION="${2:-}"; shift 2 ;;
    --operator) OPERATOR="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

command -v jq >/dev/null 2>&1 || { printf 'credential health failed: jq is required\n' >&2; exit 1; }
[[ -n "$STATE_DIR" ]] || usage
mkdir -p "$STATE_DIR"
chmod 0700 "$STATE_DIR"
STATE_FILE="$STATE_DIR/state.json"
QUARANTINE_FILE="$STATE_DIR/protected-promotion.quarantine"
ALERT_FILE="$STATE_DIR/alerts.jsonl"

atomic_state() {
  local temporary
  temporary="$(mktemp "$STATE_DIR/.state.XXXXXX")"
  jq "$@" "$STATE_FILE" > "$temporary"
  chmod 0600 "$temporary"
  mv "$temporary" "$STATE_FILE"
}

if [[ -n "$ACK_VERSION" ]]; then
  [[ "$OPERATOR" =~ ^[A-Za-z0-9._@-]{1,128}$ && -f "$STATE_FILE" ]] || usage
  active_version="$(jq -r '.activeVersion' "$STATE_FILE")"
  [[ "$ACK_VERSION" == "$active_version" ]] || {
    printf 'credential health acknowledgement rejected: version mismatch\n' >&2
    exit 1
  }
  atomic_state --arg version "$ACK_VERSION" --arg operator "$OPERATOR" --arg now "$NOW" \
    '.acknowledgement = {version:$version,operator:$operator,at:$now}'
  jq -cn --arg version "$ACK_VERSION" '{status:"acknowledged",version:$version}'
  exit 0
fi

[[ -f "$METADATA" && -f "$ASSIGNMENTS" && -f "$POLICY" && -n "$EVIDENCE_DIR" ]] || usage
mkdir -p "$EVIDENCE_DIR"
chmod 0700 "$EVIDENCE_DIR"

verify_output="$(mktemp "$STATE_DIR/.verify.XXXXXX")"
verify_error="$(mktemp "$STATE_DIR/.verify-error.XXXXXX")"
trap 'rm -f "$verify_output" "$verify_error"' EXIT
set +e
"$ROOT/scripts/jenkins/verify-cloud-credential.sh" \
  --metadata "$METADATA" --assignments "$ASSIGNMENTS" --policy "$POLICY" --now "$NOW" \
  > "$verify_output" 2> "$verify_error"
verify_status=$?
set -e

version="$(jq -r '.version // "unknown"' "$verify_output" 2>/dev/null || printf 'unknown')"
days_remaining="$(jq -r '.daysRemaining // "null"' "$verify_output" 2>/dev/null || printf 'null')"
reason="$(jq -r '.reason // ""' "$verify_output" 2>/dev/null || true)"
[[ "$version" == "unknown" ]] && version="$(jq -r '.version // "unknown"' "$METADATA" 2>/dev/null || printf 'unknown')"

version_changed=false
if [[ ! -f "$STATE_FILE" ]]; then
  jq -n --arg version "$version" '{activeVersion:$version,emittedThresholds:[],firstThirtySeenAt:null,acknowledgement:null,lastCheckedAt:null}' > "$STATE_FILE"
  chmod 0600 "$STATE_FILE"
  version_changed=true
elif [[ "$(jq -r '.activeVersion' "$STATE_FILE")" != "$version" ]]; then
  jq -n --arg version "$version" '{activeVersion:$version,emittedThresholds:[],firstThirtySeenAt:null,acknowledgement:null,lastCheckedAt:null}' > "$STATE_FILE"
  chmod 0600 "$STATE_FILE"
  version_changed=true
fi

alert=""
escalation="none"
quarantined=false
status="healthy"

if ((verify_status != 0)) && [[ "$reason" != "minimum-validity" ]]; then
  alert="credential-report-invalid"
  escalation="platform-operations-incident"
  quarantined=true
  status="invalid"
elif [[ "$days_remaining" == "null" ]]; then
  alert="credential-report-invalid"
  escalation="platform-operations-incident"
  quarantined=true
  status="invalid"
else
  threshold=""
  if ((days_remaining <= 7)); then
    threshold="7"
  elif ((days_remaining <= 14)); then
    threshold="14"
  elif ((days_remaining <= 30)); then
    threshold="30"
  fi
  if [[ -n "$threshold" ]]; then
    alert="expiry-${threshold}-day"
    status="warning"
    if ! jq -e --arg threshold "$threshold" '.emittedThresholds | index($threshold) != null' "$STATE_FILE" >/dev/null; then
      jq -cn --arg event "$alert" --arg version "$version" --arg now "$NOW" \
        '{event:$event,version:$version,at:$now}' >> "$ALERT_FILE"
      atomic_state --arg threshold "$threshold" '.emittedThresholds += [$threshold]'
    fi
  fi
  if ((days_remaining <= 30)) && [[ "$(jq -r '.firstThirtySeenAt // empty' "$STATE_FILE")" == "" ]]; then
    atomic_state --arg now "$NOW" '.firstThirtySeenAt = $now'
  fi
  if ((days_remaining < 30)); then
    quarantined=true
  elif ((days_remaining == 30)); then
    acknowledged="$(jq -r --arg version "$version" '.acknowledgement.version == $version' "$STATE_FILE")"
    first_seen="$(jq -r '.firstThirtySeenAt' "$STATE_FILE")"
    now_epoch="$(jq -nr --arg value "$NOW" '$value | fromdateiso8601')"
    first_epoch="$(jq -nr --arg value "$first_seen" '$value | fromdateiso8601')"
    acknowledgement_hours="$(jq -r '.acknowledgementHours' "$POLICY")"
    if [[ "$acknowledged" != "true" ]] && ((now_epoch - first_epoch >= acknowledgement_hours * 3600)); then
      quarantined=true
    fi
  fi
  if ((days_remaining <= 14)); then
    escalation="platform-operations-incident"
    quarantined=true
  fi
fi

if [[ "$quarantined" == true ]]; then
  status="quarantined"
  jq -n --arg version "$version" --arg reason "${alert:-credential-policy-failed}" --arg now "$NOW" \
    '{version:$version,reason:$reason,at:$now}' > "$QUARANTINE_FILE"
  chmod 0600 "$QUARANTINE_FILE"
elif [[ -f "$QUARANTINE_FILE" ]]; then
  quarantined=true
  status="quarantined"
fi

atomic_state --arg now "$NOW" '.lastCheckedAt = $now'
evidence_name="credential-health-$(printf '%s' "$NOW" | tr -cd '0-9')-${version}.json"
evidence_file="$EVIDENCE_DIR/$evidence_name"
jq -n \
  --arg status "$status" --arg version "$version" --arg now "$NOW" \
  --arg alert "$alert" --arg escalation "$escalation" \
  --argjson days "$days_remaining" --argjson quarantined "$quarantined" \
  '{schemaVersion:1,status:$status,credentialId:"jenkins-azure-cloud",version:$version,checkedAt:$now,daysRemaining:$days,alert:(if $alert == "" then null else $alert end),escalation:$escalation,quarantined:$quarantined}' \
  > "$evidence_file"
chmod 0600 "$evidence_file"
cat "$evidence_file"

[[ "$quarantined" == false ]]
