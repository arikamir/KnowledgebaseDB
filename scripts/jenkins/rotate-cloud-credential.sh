#!/usr/bin/env bash
set -euo pipefail

CLOUD="azure"
CREDENTIAL_ID="jenkins-azure-cloud"
MODE="normal"
OLD_VERSION="" NEW_VERSION="" EXPIRES_AT="" STATE_DIR="" EVIDENCE_DIR=""
MANAGER_URL="http://127.0.0.1:8080/credential-manager/update"
NETRC_FILE="" CRUMB_FILE="" SMOKE_COMMAND="" REVOKE_COMMAND="" RETIRED_DENIAL_COMMAND=""
OLD_SECRET_FD="" NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

usage() { printf 'credential rotation: invalid invocation\n' >&2; exit 2; }
while (($#)); do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --old-version) OLD_VERSION="${2:-}"; shift 2 ;;
    --new-version) NEW_VERSION="${2:-}"; shift 2 ;;
    --expires-at) EXPIRES_AT="${2:-}"; shift 2 ;;
    --state-dir) STATE_DIR="${2:-}"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    --manager-url) MANAGER_URL="${2:-}"; shift 2 ;;
    --netrc-file) NETRC_FILE="${2:-}"; shift 2 ;;
    --crumb-file) CRUMB_FILE="${2:-}"; shift 2 ;;
    --smoke-command) SMOKE_COMMAND="${2:-}"; shift 2 ;;
    --revoke-command) REVOKE_COMMAND="${2:-}"; shift 2 ;;
    --retired-denial-command) RETIRED_DENIAL_COMMAND="${2:-}"; shift 2 ;;
    --old-secret-fd) OLD_SECRET_FD="${2:-}"; shift 2 ;;
    --now) NOW="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

[[ "$MODE" =~ ^(normal|retry|emergency)$ ]] || usage
[[ "$OLD_VERSION" =~ ^[A-Za-z0-9._-]{1,128}$ && "$NEW_VERSION" =~ ^[A-Za-z0-9._-]{1,128}$ ]] || usage
[[ "$MANAGER_URL" =~ ^https?://(127\.0\.0\.1|localhost|\[::1\]):[0-9]+/credential-manager/update$ ]] || usage
[[ -d "$STATE_DIR" || ! -e "$STATE_DIR" ]] || usage
[[ -n "$EVIDENCE_DIR" && -r "$NETRC_FILE" && -r "$CRUMB_FILE" ]] || usage
for command_path in "$SMOKE_COMMAND" "$REVOKE_COMMAND" "$RETIRED_DENIAL_COMMAND"; do [[ -x "$command_path" ]] || usage; done
mkdir -p "$STATE_DIR" "$EVIDENCE_DIR"; chmod 0700 "$STATE_DIR" "$EVIDENCE_DIR"
QUARANTINE="$STATE_DIR/protected-promotion.quarantine"
DISABLED="$STATE_DIR/ordinary-provisioning.disabled"
STATE="$STATE_DIR/rotation-${NEW_VERSION}.json"
NEW_SECRET="" OLD_SECRET=""
cleanup() { unset NEW_SECRET OLD_SECRET; }
trap cleanup EXIT
IFS= read -r NEW_SECRET
[[ -n "$NEW_SECRET" ]] || { printf 'credential rotation: protected input missing\n' >&2; exit 1; }
if [[ -n "$OLD_SECRET_FD" ]]; then
  [[ "$OLD_SECRET_FD" =~ ^[3-9]$ ]] || usage
  IFS= read -r OLD_SECRET <&"$OLD_SECRET_FD"
fi
[[ "$MODE" == "emergency" || -n "$OLD_SECRET" ]] || { printf 'credential rotation: protected rollback input missing\n' >&2; exit 1; }
iso_epoch() { date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$1" '+%s' 2>/dev/null || date -u -d "$1" '+%s'; }

write_evidence() {
  local status="$1" retired="${2:-false}"
  jq -n --arg status "$status" --arg old "$OLD_VERSION" --arg new "$NEW_VERSION" --arg now "$NOW" \
    --argjson retired "$retired" '{schemaVersion:1,credentialId:"jenkins-azure-cloud",cloud:"azure",oldVersion:$old,newVersion:$new,status:$status,at:$now,retiredDenied:$retired}' \
    > "$EVIDENCE_DIR/credential-rotation-${NEW_VERSION}.json"
  chmod 0600 "$EVIDENCE_DIR/credential-rotation-${NEW_VERSION}.json"
}
quarantine() { jq -n --arg version "$NEW_VERSION" --arg reason "$1" --arg at "$NOW" '{version:$version,reason:$reason,at:$at}' > "$QUARANTINE"; chmod 0600 "$QUARANTINE"; }
fail_closed() { quarantine "$1"; write_evidence "$1"; printf 'credential rotation failed: %s\n' "$1" >&2; exit 1; }
valid_days=$(( ($(iso_epoch "$EXPIRES_AT") - $(iso_epoch "$NOW")) / 86400 ))
((valid_days >= 30 && valid_days <= 90)) || fail_closed replacement_validity_out_of_policy
manager_update() {
  local secret="$1" version="$2" response crumb
  crumb="$(cat "$CRUMB_FILE")"
  [[ "$crumb" == Jenkins-Crumb:* ]] || return 1
  response="$(printf '%s\n' "$secret" | jq -Rn --arg id "$CREDENTIAL_ID" --arg version "$version" --arg expires "$EXPIRES_AT" \
    '{credentialId:$id,clientSecret:input,version:$version,expiresAt:$expires}' | \
    curl --fail --silent --show-error --netrc-file "$NETRC_FILE" --header "$crumb" --header 'Content-Type: application/json' --data-binary @- "$MANAGER_URL")" || return 1
  [[ "$(jq -r '.status // empty' <<<"$response")" == "updated" && "$(jq -r '.version // empty' <<<"$response")" == "$version" ]]
}
smoke() { timeout 7200 "$SMOKE_COMMAND" --cloud "$CLOUD" --template "$1" --credential-version "$NEW_VERSION" --quarantined; }
all_smokes() { smoke "azure-aci-validator" && smoke "azure-aci-publisher" && smoke "azure-aci-deployer"; }
revoke() { "$REVOKE_COMMAND" --credential-version "$1"; }
restore_old() { [[ -n "$OLD_SECRET" ]] && manager_update "$OLD_SECRET" "$OLD_VERSION"; }

if [[ "$MODE" == "emergency" ]]; then
  quarantine emergency_rotation
  : > "$DISABLED"; chmod 0600 "$DISABLED"
  revoke "$OLD_VERSION" || fail_closed emergency_revoke_failed
  manager_update "$NEW_SECRET" "$NEW_VERSION" || fail_closed manager_update_failed
  all_smokes || fail_closed emergency_smoke_failed
  "$RETIRED_DENIAL_COMMAND" --credential-version "$OLD_VERSION" || fail_closed retired_credential_still_usable
  rm -f "$DISABLED" "$QUARANTINE"
  write_evidence emergency_rotated true
  exit 0
fi

if [[ "$MODE" == "retry" ]]; then
  [[ -f "$STATE" && "$(jq -r '.status' "$STATE")" == "retry_pending" ]] || fail_closed retry_state_missing
  (( $(iso_epoch "$NOW") >= $(jq -r '.retryAfter' "$STATE") )) || fail_closed retry_too_early
fi

manager_update "$NEW_SECRET" "$NEW_VERSION" || fail_closed manager_update_failed
if ! all_smokes; then
  quarantine partial_failure
  if [[ "$MODE" == "normal" ]]; then
    retry_after=$(( $(iso_epoch "$NOW") + 7200 ))
    jq -n --arg old "$OLD_VERSION" --arg new "$NEW_VERSION" --argjson retryAfter "$retry_after" '{status:"retry_pending",oldVersion:$old,newVersion:$new,retryAfter:$retryAfter}' > "$STATE"
    chmod 0600 "$STATE"; write_evidence retry_pending; exit 1
  fi
  restore_old || fail_closed rollback_failed
  jq -n --arg route "platform-operations-incident" --arg status "retry_failed_restored" '{status:$status,page:$route}' > "$STATE"
  write_evidence retry_failed_restored; exit 1
fi

revoke "$OLD_VERSION" || { restore_old || true; fail_closed revoke_failed_rolled_back; }
"$RETIRED_DENIAL_COMMAND" --credential-version "$OLD_VERSION" || fail_closed retired_credential_still_usable
rm -f "$QUARANTINE"
write_evidence rotated true
