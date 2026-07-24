#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"; shift || true
STATE_DIR=""; EVIDENCE_DIR=""; TARGET=""; NOW=""; ACTIVE=""; CANDIDATE=""; CREATED=""; EXPIRES=""
EXPECTED_SAN=""; ISSUER=""; PROBE_REPORT=""; COMPROMISED=""
while (($#)); do
  case "$1" in
    --state-dir) STATE_DIR="${2:-}"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    --target) TARGET="${2:-}"; shift 2 ;;
    --now) NOW="${2:-}"; shift 2 ;;
    --active-version) ACTIVE="${2:-}"; shift 2 ;;
    --candidate-version) CANDIDATE="${2:-}"; shift 2 ;;
    --candidate-created-at) CREATED="${2:-}"; shift 2 ;;
    --candidate-expires-at) EXPIRES="${2:-}"; shift 2 ;;
    --expected-san) EXPECTED_SAN="${2:-}"; shift 2 ;;
    --issuer) ISSUER="${2:-}"; shift 2 ;;
    --probe-report) PROBE_REPORT="${2:-}"; shift 2 ;;
    --compromised-version) COMPROMISED="${2:-}"; shift 2 ;;
    *) printf 'certificate rotation: invalid argument %s\n' "$1" >&2; exit 2 ;;
  esac
done

command -v jq >/dev/null || { printf 'certificate rotation: jq required\n' >&2; exit 1; }
[[ "$ACTION" =~ ^(stage|activate|converge|retire|rollback|emergency|scheduled)$ ]] || exit 2
[[ -n "$STATE_DIR" && -n "$EVIDENCE_DIR" ]] || exit 2
mkdir -p "$STATE_DIR" "$EVIDENCE_DIR"; chmod 0700 "$STATE_DIR" "$EVIDENCE_DIR"
[[ -n "$NOW" ]] || NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
jq -nr --arg value "$NOW" '$value | fromdateiso8601' >/dev/null || exit 2

valid_target() { [[ "$1" == public-gateway || "$1" == private-core ]]; }
valid_version() { [[ "$1" =~ ^[A-Za-z0-9._-]{3,128}$ ]]; }
epoch() { jq -nr --arg value "$1" '$value | fromdateiso8601'; }
state_path() { printf '%s/%s.json' "$STATE_DIR" "$1"; }
certificate_name() { [[ "$1" == public-gateway ]] && printf public-gateway-server || printf private-core-server; }

atomic_state() {
  local target="$1" filter="$2" source temporary; shift 2
  source="$(state_path "$target")"; temporary="$(mktemp "$STATE_DIR/.rotation.XXXXXX")"
  jq "$filter" "$@" "$source" >"$temporary"; chmod 0600 "$temporary"; mv "$temporary" "$source"
}

evidence() {
  local target="$1" event="$2" status="$3" state sequence output
  state="$(state_path "$target")"
  sequence="$(find "$EVIDENCE_DIR" -type f -name "${target}-*.json" 2>/dev/null | wc -l | tr -d ' ')"
  output="$EVIDENCE_DIR/${target}-$(printf '%04d' "$sequence")-${event}.json"
  jq -cn --arg target "$target" --arg event "$event" --arg status "$status" --arg at "$NOW" \
    --arg active "$(jq -r '.activeVersion // ""' "$state")" --arg candidate "$(jq -r '.candidateVersion // ""' "$state")" \
    --arg prior "$(jq -r '.priorActiveVersion // ""' "$state")" \
    '{schemaVersion:1,target:$target,event:$event,status:$status,at:$at,activeVersion:$active,candidateVersion:$candidate,priorActiveVersion:$prior,containsPrivateMaterial:false}' >"$output"
  chmod 0600 "$output"
}

disable_version() {
  local target="$1" version="$2"
  [[ "${ROTATION_MODE:-dry-run}" == live ]] || return 0
  [[ "${ROTATION_LIVE_AUTHORIZED:-}" == true && -n "${KEY_VAULT_NAME:-}" ]] || exit 1
  az keyvault certificate set-attributes --only-show-errors --vault-name "$KEY_VAULT_NAME" \
    --name "$(certificate_name "$target")" --version "$version" --enabled false >/dev/null
}

remove_nonconverged_endpoints() {
  local report="$1"
  [[ "${ROTATION_MODE:-dry-run}" == live ]] || return 0
  jq -r '.replicas[] | select(.ready != true or .san != true or .issuer != true or .expiry != true or .trust != true or .reload != true or .tls != true or .route != true) | .id' "$report" |
    while IFS= read -r pod; do
      kubectl -n career-agent patch pod "$pod" --subresource=status --type=merge \
        -p '{"status":{"conditions":[{"type":"platform.devopscareer.io/CertificateConverged","status":"False","reason":"CandidateProbeFailed"}]}}'
    done
}

validate_report() {
  local report="$1" target="$2" version="$3"
  [[ -f "$report" ]] || return 1
  jq -e --arg target "$target" --arg version "$version" '
    keys == ["certificateVersion","replicas","schemaVersion","target"] and .schemaVersion == 1 and
    .target == $target and .certificateVersion == $version and (.replicas | length) > 0 and
    ([.replicas[].id] | length == (unique | length)) and
    all(.replicas[]; keys == ["expiry","id","issuer","ready","reload","route","san","tls","trust"])
  ' "$report" >/dev/null
}

all_converged() {
  jq -e 'all(.replicas[]; .san and .issuer and .expiry and .trust and .reload and .tls and .route and .ready)' "$1" >/dev/null
}

if [[ "$ACTION" == scheduled ]]; then
  for target in public-gateway private-core; do
    state="$(state_path "$target")"
    [[ -f "$state" ]] || continue
    status="$(jq -r '.status' "$state")"; probe="$STATE_DIR/${target}-probe.json"
    if [[ ("$status" == overlap || "$status" == partial) && -f "$probe" ]]; then
      "${BASH_SOURCE[0]}" converge --state-dir "$STATE_DIR" --evidence-dir "$EVIDENCE_DIR" \
        --target "$target" --now "$NOW" --probe-report "$probe" >/dev/null || true
      status="$(jq -r '.status' "$state")"
    fi
    if [[ "$status" == converged && -f "$probe" ]]; then
      overlap="$(jq -r '.overlapStartedAt' "$state")"; elapsed=$(( $(epoch "$NOW") - $(epoch "$overlap") ))
      if ((elapsed >= 86400 && elapsed <= 172800)); then
        "${BASH_SOURCE[0]}" retire --state-dir "$STATE_DIR" --evidence-dir "$EVIDENCE_DIR" \
          --target "$target" --now "$NOW" --probe-report "$probe" >/dev/null || true
        status="$(jq -r '.status' "$state")"
      elif ((elapsed > 172800)); then
        atomic_state "$target" '.status="quarantined" | .pageRequired=true | .updatedAt=$now' --arg now "$NOW"
        evidence "$target" retirement-deadline-missed quarantined
        continue
      fi
    fi
    if [[ "$status" == partial && $(epoch "$NOW") -ge $(epoch "$(jq -r '.retryUntil' "$state")") ]]; then
      atomic_state "$target" '.status="quarantined" | .pageRequired=true | .updatedAt=$now' --arg now "$NOW"
      evidence "$target" retry-exhausted quarantined
    fi
  done
  exit 0
fi

valid_target "$TARGET" || exit 2
STATE="$(state_path "$TARGET")"

case "$ACTION" in
  stage)
    valid_version "$ACTIVE" && valid_version "$CANDIDATE" && [[ "$ACTIVE" != "$CANDIDATE" ]] || exit 2
    [[ -n "$CREATED" && -n "$EXPIRES" && -n "$EXPECTED_SAN" && -n "$ISSUER" ]] || exit 2
    (( $(epoch "$EXPIRES") > $(epoch "$NOW") + 30 * 86400 )) || exit 1
    jq -cn --arg target "$TARGET" --arg active "$ACTIVE" --arg candidate "$CANDIDATE" --arg created "$CREATED" \
      --arg expires "$EXPIRES" --arg san "$EXPECTED_SAN" --arg issuer "$ISSUER" --arg now "$NOW" \
      '{schemaVersion:1,target:$target,status:"staged_disabled",activeVersion:$active,priorActiveVersion:null,
        candidateVersion:$candidate,candidateCreatedAt:$created,candidateExpiresAt:$expires,expectedSan:$san,expectedIssuer:$issuer,
        candidateEnabled:false,activatedAt:null,overlapStartedAt:null,retryUntil:null,quarantined:false,pageRequired:false,
        compromisedVersions:[],safeFallbackAllowed:true,updatedAt:$now}' >"$STATE"
    chmod 0600 "$STATE"; evidence "$TARGET" candidate-staged staged_disabled
    ;;
  activate)
    [[ -f "$STATE" && -n "$PROBE_REPORT" ]] || exit 1
    candidate="$(jq -r '.candidateVersion' "$STATE")"; validate_report "$PROBE_REPORT" "$TARGET" "$candidate" && all_converged "$PROBE_REPORT" || exit 1
    atomic_state "$TARGET" '.priorActiveVersion=.activeVersion | .activeVersion=.candidateVersion | .candidateEnabled=true | .status="overlap" | .activatedAt=$now | .overlapStartedAt=$now | .updatedAt=$now' --arg now "$NOW"
    evidence "$TARGET" candidate-activated overlap
    ;;
  converge)
    [[ -f "$STATE" && -n "$PROBE_REPORT" ]] || exit 1
    active="$(jq -r '.activeVersion' "$STATE")"; validate_report "$PROBE_REPORT" "$TARGET" "$active" || exit 1
    if all_converged "$PROBE_REPORT"; then
      atomic_state "$TARGET" '.status="converged" | .retryUntil=null | .quarantined=false | .pageRequired=false | .updatedAt=$now' --arg now "$NOW"
      evidence "$TARGET" replica-convergence converged
    else
      retry_until="$(jq -nr --arg now "$NOW" '$now|fromdateiso8601|.+86400|todateiso8601')"
      remove_nonconverged_endpoints "$PROBE_REPORT"
      atomic_state "$TARGET" '.status="partial" | .retryUntil=$retry | .updatedAt=$now' --arg retry "$retry_until" --arg now "$NOW"
      evidence "$TARGET" replica-convergence partial
    fi
    ;;
  retire)
    [[ -f "$STATE" && -n "$PROBE_REPORT" ]] || exit 1
    [[ "$(jq -r '.status' "$STATE")" == converged ]] || exit 1
    started="$(jq -r '.overlapStartedAt' "$STATE")"; elapsed=$(( $(epoch "$NOW") - $(epoch "$started") ))
    ((elapsed >= 86400 && elapsed <= 172800)) || exit 1
    active="$(jq -r '.activeVersion' "$STATE")"; old="$(jq -r '.priorActiveVersion' "$STATE")"
    validate_report "$PROBE_REPORT" "$TARGET" "$active" && all_converged "$PROBE_REPORT" || exit 1
    disable_version "$TARGET" "$old"
    atomic_state "$TARGET" '.status="retired" | .retiredVersions=((.retiredVersions // []) + [.priorActiveVersion] | unique) | .priorActiveVersion=null | .candidateVersion=null | .updatedAt=$now' --arg now "$NOW"
    evidence "$TARGET" prior-version-retired retired
    ;;
  rollback)
    [[ -f "$STATE" && -n "$PROBE_REPORT" ]] || exit 1
    prior="$(jq -r '.priorActiveVersion // ""' "$STATE")"; [[ -n "$prior" ]] || exit 1
    jq -e --arg version "$prior" '.compromisedVersions | index($version) == null' "$STATE" >/dev/null || exit 1
    validate_report "$PROBE_REPORT" "$TARGET" "$prior" && all_converged "$PROBE_REPORT" || exit 1
    failed="$(jq -r '.activeVersion' "$STATE")"; disable_version "$TARGET" "$failed"
    atomic_state "$TARGET" '.activeVersion=.priorActiveVersion | .priorActiveVersion=null | .candidateVersion=null | .status="rolled_back_verified" | .quarantined=true | .updatedAt=$now' --arg now "$NOW"
    evidence "$TARGET" verified-rollback rolled_back_verified
    ;;
  emergency)
    [[ -f "$STATE" ]] && valid_version "$COMPROMISED" || exit 1
    disable_version "$TARGET" "$COMPROMISED"
    atomic_state "$TARGET" '.compromisedVersions=((.compromisedVersions // []) + [$version] | unique) | .status="emergency_revoked" | .safeFallbackAllowed=false | .quarantined=true | .pageRequired=true | .updatedAt=$now' --arg version "$COMPROMISED" --arg now "$NOW"
    evidence "$TARGET" emergency-revocation emergency_revoked
    ;;
esac

jq -c '{target,status,activeVersion,candidateVersion,priorActiveVersion,quarantined,pageRequired}' "$STATE"
