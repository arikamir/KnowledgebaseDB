#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"; shift || true
STATE="" EVIDENCE_DIR="" NOW="" ACTIVE="" CANDIDATE="" REPORT="" VERSION=""
while (($#)); do
  case "$1" in
    --state) STATE="${2:-}"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    --now) NOW="${2:-}"; shift 2 ;;
    --active-version) ACTIVE="${2:-}"; shift 2 ;;
    --candidate-version) CANDIDATE="${2:-}"; shift 2 ;;
    --probe-report) REPORT="${2:-}"; shift 2 ;;
    --version) VERSION="${2:-}"; shift 2 ;;
    *) printf 'bff certificate rotation: invalid argument %s\n' "$1" >&2; exit 2 ;;
  esac
done

[[ "$ACTION" =~ ^(stage|converge|activate|retire|rollback|emergency|release)$ ]] || exit 2
[[ -n "$STATE" && -n "$EVIDENCE_DIR" ]] || exit 2
command -v jq >/dev/null || exit 1
mkdir -p "$(dirname "$STATE")" "$EVIDENCE_DIR"; chmod 0700 "$(dirname "$STATE")" "$EVIDENCE_DIR"
[[ -n "$NOW" ]] || NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
jq -nr --arg value "$NOW" '$value|fromdateiso8601' >/dev/null

epoch() { jq -nr --arg value "$1" '$value|fromdateiso8601'; }
valid_version() { [[ "$1" =~ ^[A-Za-z0-9._-]{3,128}$ ]]; }
write_state() { local tmp; tmp="$(mktemp "$(dirname "$STATE")/.bff-cert.XXXXXX")"; jq "$@" "$STATE" >"$tmp"; chmod 0600 "$tmp"; mv "$tmp" "$STATE"; }
evidence() {
  local event="$1" status="$2" sequence output
  sequence="$(find "$EVIDENCE_DIR" -type f -name 'bff-certificate-*.json' | wc -l | tr -d ' ')"
  output="$EVIDENCE_DIR/bff-certificate-$(printf '%04d' "$sequence")-${event}.json"
  jq -cn --arg event "$event" --arg status "$status" --arg at "$NOW" \
    --arg active "$(jq -r '.activeVersion // ""' "$STATE")" --arg candidate "$(jq -r '.candidateVersion // ""' "$STATE")" \
    '{schemaVersion:1,event:$event,status:$status,at:$at,activeVersion:$active,candidateVersion:$candidate,containsPrivateMaterial:false}' >"$output"
  chmod 0600 "$output"
}
validate_report() {
  [[ -f "$1" ]] && jq -e --arg version "$2" '
    .schemaVersion==1 and .candidateVersion==$version and (.replicas|length)>0 and
    ([.replicas[].id]|length==(unique|length)) and
    all(.replicas[]; .mountedVersion==$version and .ready==true and .callback==true and .sessionRefresh==true and .delegatedToken==true and .healthToken==true)
  ' "$1" >/dev/null
}
disable_version() {
  [[ "${ROTATION_MODE:-dry-run}" == live ]] || return 0
  [[ "${ROTATION_LIVE_AUTHORIZED:-}" == true && -n "${BFF_ENTRA_APPLICATION_OBJECT_ID:-}" ]] || exit 1
  az ad app credential delete --id "$BFF_ENTRA_APPLICATION_OBJECT_ID" --key-id "$1" --only-show-errors >/dev/null
}

case "$ACTION" in
  stage)
    valid_version "$ACTIVE" && valid_version "$CANDIDATE" && [[ "$ACTIVE" != "$CANDIDATE" ]] || exit 2
    jq -cn --arg active "$ACTIVE" --arg candidate "$CANDIDATE" --arg now "$NOW" \
      '{schemaVersion:1,status:"candidate",activeVersion:$active,candidateVersion:$candidate,priorVersion:$active,
        introducedAt:$now,activatedAt:null,retryUntil:($now|fromdateiso8601+86400|todateiso8601),
        quarantineReason:null,operatorReleaseRequired:false,pageRequired:false,revokedVersions:[]}' >"$STATE"
    chmod 0600 "$STATE"; evidence candidate-staged candidate ;;
  converge)
    [[ -f "$STATE" && -n "$REPORT" ]] || exit 1
    candidate="$(jq -r '.candidateVersion' "$STATE")"
    if validate_report "$REPORT" "$candidate"; then
      write_state '.status="converged" | .pageRequired=false | .updatedAt=$now' --arg now "$NOW"
      evidence replicas-converged converged
    elif (( $(epoch "$NOW") >= $(epoch "$(jq -r '.retryUntil' "$STATE")") )); then
      write_state '.status="quarantined" | .quarantineReason="REPLICA_CONVERGENCE_TIMEOUT" | .operatorReleaseRequired=true | .pageRequired=true | .updatedAt=$now' --arg now "$NOW"
      evidence convergence-timeout quarantined; exit 1
    else
      write_state '.status="partial" | .pageRequired=true | .updatedAt=$now' --arg now "$NOW"
      evidence replica-removed partial; exit 1
    fi ;;
  activate)
    [[ -f "$STATE" && "$(jq -r '.status' "$STATE")" == converged && -n "$REPORT" ]] || exit 1
    candidate="$(jq -r '.candidateVersion' "$STATE")"; validate_report "$REPORT" "$candidate" || exit 1
    write_state '.activeVersion=.candidateVersion | .status="overlap" | .activatedAt=$now | .updatedAt=$now' --arg now "$NOW"
    evidence candidate-activated overlap ;;
  retire)
    [[ -f "$STATE" && "$(jq -r '.status' "$STATE")" == overlap && -n "$REPORT" ]] || exit 1
    elapsed=$(( $(epoch "$NOW") - $(epoch "$(jq -r '.activatedAt' "$STATE")") ))
    ((elapsed >= 86400 && elapsed <= 172800)) || exit 1
    candidate="$(jq -r '.activeVersion' "$STATE")"; validate_report "$REPORT" "$candidate" || exit 1
    prior="$(jq -r '.priorVersion' "$STATE")"; disable_version "$prior"
    write_state '.status="retired" | .retiredVersions=((.retiredVersions // [])+[.priorVersion]|unique) | .priorVersion=null | .candidateVersion=null | .updatedAt=$now' --arg now "$NOW"
    evidence prior-retired retired ;;
  rollback)
    [[ -f "$STATE" && -n "$REPORT" ]] || exit 1
    prior="$(jq -r '.priorVersion' "$STATE")"
    jq -e --arg version "$prior" '.revokedVersions|index($version)==null' "$STATE" >/dev/null || exit 1
    validate_report "$REPORT" "$prior" || exit 1
    write_state '.activeVersion=.priorVersion | .status="rolled_back" | .quarantineReason="FAILED_CANDIDATE" | .operatorReleaseRequired=true | .pageRequired=true | .updatedAt=$now' --arg now "$NOW"
    evidence candidate-rollback rolled_back ;;
  emergency)
    [[ -f "$STATE" ]] && valid_version "$VERSION" || exit 1
    disable_version "$VERSION"
    write_state '.revokedVersions=((.revokedVersions // [])+[$version]|unique) | .status="emergency_revoked" | .operatorReleaseRequired=true | .pageRequired=true | .noFallback=true | .clearSessionTokenCaches=true | .updatedAt=$now' --arg version "$VERSION" --arg now "$NOW"
    evidence emergency-revoked emergency_revoked ;;
  release)
    [[ -f "$STATE" && "$(jq -r '.operatorReleaseRequired' "$STATE")" == true ]] || exit 1
    write_state '.status="candidate" | .operatorReleaseRequired=false | .quarantineReason=null | .pageRequired=false | .retryUntil=($now|fromdateiso8601+86400|todateiso8601) | .updatedAt=$now' --arg now "$NOW"
    evidence operator-released candidate ;;
esac

jq -c '{status,activeVersion,candidateVersion,operatorReleaseRequired,pageRequired,noFallback:(.noFallback // false)}' "$STATE"
