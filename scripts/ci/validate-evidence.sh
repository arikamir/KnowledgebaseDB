#!/usr/bin/env bash
set -euo pipefail

MODE="local"
FILE="" ACCOUNT="" CONTAINER="" BLOB="" VERSION_ID="" EXPECTED_SHA256="" EXPECTED_LENGTH=""

while (($#)); do
  case "$1" in
    --file) FILE="${2:-}"; shift 2 ;;
    --verify-remote) MODE="remote"; shift ;;
    --account) ACCOUNT="${2:-}"; shift 2 ;;
    --container) CONTAINER="${2:-}"; shift 2 ;;
    --blob) BLOB="${2:-}"; shift 2 ;;
    --version-id) VERSION_ID="${2:-}"; shift 2 ;;
    --sha256) EXPECTED_SHA256="${2:-}"; shift 2 ;;
    --length) EXPECTED_LENGTH="${2:-}"; shift 2 ;;
    *) printf 'evidence validation: invalid argument\n' >&2; exit 2 ;;
  esac
done

fail() { printf 'evidence validation: %s\n' "$1" >&2; exit 1; }

if [[ "$MODE" == "local" ]]; then
  [[ -n "$FILE" && -f "$FILE" && ! -L "$FILE" ]] || fail "regular non-symlink file required"
  [[ -r "$FILE" ]] || fail "file is not readable"

  # Evidence is deliberately fail-closed. These patterns cover credentials,
  # kubeconfigs, raw identity claims, and personal learning records; producers
  # must publish a redacted summary instead of a raw controller log/archive.
  prohibited_pattern='authorization[[:space:]"]*:[[:space:]"]*bearer|client[_-]?secret|access[_-]?token|refresh[_-]?token|private[_-]?key|BEGIN [A-Z ]*PRIVATE KEY|kubeconfig|(^|["[:space:]])password["[:space:]]*:|"(oid|tid|preferred_username|email|learner(Id)?|employee(Id)?|answers?)"[[:space:]]*:'
  if LC_ALL=C grep -Eiq "$prohibited_pattern" "$FILE"; then
    fail "prohibited credential, identity, or personal-learning content"
  fi

  jq -cn --arg sha256 "$(shasum -a 256 "$FILE" | awk '{print $1}')" \
    --argjson length "$(wc -c < "$FILE" | tr -d ' ')" \
    '{valid:true,sha256:$sha256,length:$length,controllerLocalAuthoritative:false}'
  exit 0
fi

command -v az >/dev/null || fail "az required"
command -v jq >/dev/null || fail "jq required"
[[ "$ACCOUNT" =~ ^[a-z0-9]{3,24}$ ]] || fail "invalid storage account"
[[ "$CONTAINER" == "delivery-evidence" ]] || fail "invalid evidence container"
[[ "$BLOB" =~ ^deliveries/[a-z0-9][a-z0-9._-]{1,62}/[A-Za-z0-9][A-Za-z0-9._-]{2,127}/[A-Za-z0-9][A-Za-z0-9._-]{1,63}/[A-Za-z0-9][A-Za-z0-9._-]{1,127}$ ]] || fail "invalid exact evidence path"
[[ "$EXPECTED_SHA256" =~ ^[a-f0-9]{64}$ && "$EXPECTED_LENGTH" =~ ^[0-9]+$ ]] || fail "invalid expected content identity"

show_args=(storage blob show --auth-mode login --account-name "$ACCOUNT" --container-name "$CONTAINER" --name "$BLOB" --only-show-errors -o json)
[[ -n "$VERSION_ID" ]] && show_args+=(--version-id "$VERSION_ID")
remote="$(az "${show_args[@]}")" || fail "exact blob version unavailable"

verified_version="$(jq -er '.versionId | select(type == "string" and length > 0)' <<<"$remote")" || fail "version id missing"
[[ -z "$VERSION_ID" || "$verified_version" == "$VERSION_ID" ]] || fail "version mismatch"
jq -e --arg sha "$EXPECTED_SHA256" --arg length "$EXPECTED_LENGTH" '
  .metadata.evidence_sha256 == $sha and .metadata.evidence_length == $length
' <<<"$remote" >/dev/null || fail "exact blob content identity mismatch"

jq -cn --arg versionId "$verified_version" --arg etag "$(jq -r '.etag // ""' <<<"$remote")" \
  --arg blob "$BLOB" --arg sha256 "$EXPECTED_SHA256" --argjson length "$EXPECTED_LENGTH" \
  '{valid:true,authority:"azure-blob-version",blob:$blob,versionId:$versionId,etag:$etag,sha256:$sha256,length:$length}'
