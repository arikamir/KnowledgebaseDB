#!/usr/bin/env bash
set -euo pipefail

ROLE="${EVIDENCE_HOLD_ROLE:-}"
ACTION="${1:-}"
[[ -n "$ACTION" ]] || { printf 'evidence hold: action required\n' >&2; exit 2; }
shift

STATE_DIR="${HOLD_STATE_DIR:-}"
AUDIT_DIR="${HOLD_AUDIT_DIR:-}"
NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
INVENTORY="" HOLD_ID="" OWNER="" REASON="" INCIDENT="" EXPIRES_AT=""
while (($#)); do
  case "$1" in
    --state-dir) STATE_DIR="${2:-}"; shift 2 ;;
    --audit-dir) AUDIT_DIR="${2:-}"; shift 2 ;;
    --now) NOW="${2:-}"; shift 2 ;;
    --inventory) INVENTORY="${2:-}"; shift 2 ;;
    --hold-id) HOLD_ID="${2:-}"; shift 2 ;;
    --owner) OWNER="${2:-}"; shift 2 ;;
    --reason) REASON="${2:-}"; shift 2 ;;
    --incident) INCIDENT="${2:-}"; shift 2 ;;
    --expires-at) EXPIRES_AT="${2:-}"; shift 2 ;;
    *) printf 'evidence hold: invalid argument\n' >&2; exit 2 ;;
  esac
done

command -v jq >/dev/null || { printf 'evidence hold: jq required\n' >&2; exit 1; }
[[ "$NOW" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || exit 2
[[ -n "$STATE_DIR" && -n "$AUDIT_DIR" ]] || exit 2
mkdir -p "$STATE_DIR" "$AUDIT_DIR"
chmod 0700 "$STATE_DIR" "$AUDIT_DIR"

valid_id() { [[ "$1" =~ ^[A-Za-z0-9._-]{3,128}$ ]]; }
epoch() { jq -nr --arg value "$1" '$value | fromdateiso8601'; }
audit() {
  local event="$1" hold="$2" status="$3"
  jq -cn --arg event "$event" --arg holdId "$hold" --arg actor "$ROLE" --arg at "$NOW" --arg status "$status" \
    '{schemaVersion:1,event:$event,holdId:$holdId,actorRole:$actor,at:$at,status:$status}' \
    >> "$AUDIT_DIR/$hold.jsonl"
  chmod 0600 "$AUDIT_DIR/$hold.jsonl"
}
atomic_write() {
  local target="$1" filter="$2" temporary
  shift 2
  temporary="$(mktemp "$STATE_DIR/.hold.XXXXXX")"
  jq "$filter" "$@" "$target" > "$temporary"
  chmod 0600 "$temporary"
  mv "$temporary" "$target"
}

case "$ACTION" in
  create)
    [[ "$ROLE" == "manager" && -f "$INVENTORY" ]] || exit 1
    valid_id "$HOLD_ID" && valid_id "$OWNER" && valid_id "$INCIDENT" || exit 2
    [[ ${#REASON} -ge 10 && ${#REASON} -le 500 ]] || exit 2
    jq -e '
      keys == ["container","evidenceSetId","expectedVersionCount","inventoryComplete","schemaVersion","storageAccount","versions"] and
      .schemaVersion == 1 and .inventoryComplete == true and
      (.expectedVersionCount == (.versions | length)) and .expectedVersionCount > 0 and
      (.storageAccount | test("^[a-z0-9]{3,24}$")) and .container == "delivery-evidence" and
      ([.versions[].blob] | length == (unique | length)) and
      ([.versions[].versionId] | length == (unique | length)) and
      all(.versions[]; keys == ["blob","immutableUntil","versionId"] and
        (.blob | test("^deliveries/[a-z0-9._-]+/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")) and
        (.versionId | test("^[A-Za-z0-9:._+-]{8,128}$")) and
        (.immutableUntil | fromdateiso8601 > 0))' "$INVENTORY" >/dev/null || exit 1
    now_epoch="$(epoch "$NOW")"; expiry_epoch="$(epoch "$EXPIRES_AT")"
    ((expiry_epoch > now_epoch && expiry_epoch <= now_epoch + 180 * 86400)) || exit 1
    target="$STATE_DIR/$HOLD_ID.json"; [[ ! -e "$target" ]] || exit 1
    jq --arg hold "$HOLD_ID" --arg owner "$OWNER" --arg reason "$REASON" \
      --arg incident "$INCIDENT" --arg now "$NOW" --arg expires "$EXPIRES_AT" '
      {schemaVersion:1,holdId:$hold,evidenceSetId,storageAccount,container,
       expectedVersionCount,inventoryComplete,ownerObjectId:$owner,reason:$reason,
       incidentReference:$incident,startedAt:$now,expiresAt:$expires,releasedAt:null,
       status:"applying",versions:[.versions[] + {desiredHold:true,appliedHold:false,deletionEligible:false}],
       lastReconciledAt:null}' "$INVENTORY" > "$target"
    chmod 0600 "$target"; audit created "$HOLD_ID" applying
    ;;
  extend)
    [[ "$ROLE" == "manager" ]] || exit 1
    valid_id "$HOLD_ID" || exit 2; target="$STATE_DIR/$HOLD_ID.json"; [[ -f "$target" ]] || exit 1
    started="$(jq -r '.startedAt' "$target")"; old="$(jq -r '.expiresAt' "$target")"
    (( $(epoch "$EXPIRES_AT") > $(epoch "$old") && $(epoch "$EXPIRES_AT") <= $(epoch "$started") + 180 * 86400 )) || exit 1
    atomic_write "$target" '.expiresAt=$expires | .extensionAudit += [{actorRole:"manager",priorExpiry:$prior,newExpiry:$expires,at:$now}]' \
      --arg expires "$EXPIRES_AT" --arg prior "$old" --arg now "$NOW"
    audit extended "$HOLD_ID" "$(jq -r '.status' "$target")"
    ;;
  release)
    [[ "$ROLE" == "manager" ]] || exit 1
    valid_id "$HOLD_ID" || exit 2; target="$STATE_DIR/$HOLD_ID.json"; [[ -f "$target" ]] || exit 1
    atomic_write "$target" '.status="clearing" | .releasedAt=$now | .versions |= map(.desiredHold=false)' --arg now "$NOW"
    audit release-requested "$HOLD_ID" clearing
    ;;
  reconcile|reconcile-all)
    [[ "$ROLE" == "reconciler" ]] || exit 1
    command -v az >/dev/null || exit 1
    if [[ "$ACTION" == "reconcile" ]]; then valid_id "$HOLD_ID" || exit 2; files=("$STATE_DIR/$HOLD_ID.json"); else files=("$STATE_DIR"/*.json); fi
    for target in "${files[@]}"; do
      [[ -f "$target" ]] || continue
      hold="$(jq -r '.holdId' "$target")"
      if (( $(epoch "$NOW") >= $(epoch "$(jq -r '.expiresAt' "$target")") )); then
        atomic_write "$target" '.status="clearing" | .versions |= map(.desiredHold=false)'
      fi
      account="$(jq -r '.storageAccount' "$target")"; container="$(jq -r '.container' "$target")"
      failures=0
      while IFS=$'\t' read -r blob version desired; do
        encoded_blob="$(jq -nr --arg value "$blob" '$value | @uri')"
        url="https://${account}.blob.core.windows.net/${container}/${encoded_blob}?comp=legalhold&versionid=${version}"
        if az rest --only-show-errors --method put --url "$url" --resource https://storage.azure.com/ \
          --headers x-ms-version=2023-11-03 "x-ms-legal-hold=${desired}" >/dev/null; then
          atomic_write "$target" '(.versions[] | select(.versionId==$version)).appliedHold=$desired' \
            --arg version "$version" --argjson desired "$desired"
        else failures=$((failures + 1)); fi
      done < <(jq -r '.versions[] | [.blob,.versionId,(.desiredHold|tostring)] | @tsv' "$target")
      if ((failures)); then
        atomic_write "$target" '.status="reconciling" | .lastReconciledAt=$now' --arg now "$NOW"
        audit reconcile-partial "$hold" reconciling
      elif jq -e 'all(.versions[]; .appliedHold == true)' "$target" >/dev/null; then
        atomic_write "$target" '.status="active" | .lastReconciledAt=$now' --arg now "$NOW"
        audit activated "$hold" active
      else
        atomic_write "$target" '.status="released" | .lastReconciledAt=$now |
          .versions |= map(.deletionEligible=((.immutableUntil|fromdateiso8601) <= ($now|fromdateiso8601)))' --arg now "$NOW"
        audit cleared "$hold" released
      fi
    done
    ;;
  *) printf 'evidence hold: unsupported action\n' >&2; exit 2 ;;
esac

[[ -n "$HOLD_ID" && -f "$STATE_DIR/$HOLD_ID.json" ]] && jq -c '{holdId,status,expiresAt}' "$STATE_DIR/$HOLD_ID.json" || true
