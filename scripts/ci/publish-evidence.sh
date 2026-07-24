#!/usr/bin/env bash
set -euo pipefail

FILE="" ENVIRONMENT="" BUILD_ID="" STAGE="" ARTIFACT="" ACCOUNT="" CONTAINER="delivery-evidence" RECEIPT=""
GATE_MANIFEST="" GATE_DIR=""
while (($#)); do
  case "$1" in
    --file) FILE="${2:-}"; shift 2 ;;
    --environment) ENVIRONMENT="${2:-}"; shift 2 ;;
    --build-id) BUILD_ID="${2:-}"; shift 2 ;;
    --stage) STAGE="${2:-}"; shift 2 ;;
    --artifact) ARTIFACT="${2:-}"; shift 2 ;;
    --account) ACCOUNT="${2:-}"; shift 2 ;;
    --container) CONTAINER="${2:-}"; shift 2 ;;
    --receipt) RECEIPT="${2:-}"; shift 2 ;;
    --gate-manifest) GATE_MANIFEST="${2:-}"; shift 2 ;;
    --gate-dir) GATE_DIR="${2:-}"; shift 2 ;;
    *) printf 'evidence publish: invalid argument\n' >&2; exit 2 ;;
  esac
done

fail() { printf 'evidence publish: %s\n' "$1" >&2; exit 1; }
valid_environment() { [[ "$1" =~ ^[a-z0-9][a-z0-9._-]{1,62}$ ]]; }
valid_component() { [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$ ]]; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "$GATE_MANIFEST" ]]; then
  [[ -f "$GATE_MANIFEST" && -n "$GATE_DIR" && -n "$ACCOUNT" && "$CONTAINER" == delivery-evidence && ! -e "$GATE_DIR" && ! -L "$GATE_DIR" ]] || fail "invalid gate publication request"
  "$SCRIPT_DIR/evidence-gate.sh" validate-manifest --manifest "$GATE_MANIFEST"
  ENVIRONMENT="$(jq -r '.environment' "$GATE_MANIFEST")"; BUILD_ID="$(jq -r '.buildId' "$GATE_MANIFEST")"; STAGE="$(jq -r '.stage' "$GATE_MANIFEST")"
  manifest_dir="$(cd "$(dirname "$GATE_MANIFEST")" && pwd)"; parent="$(dirname "$GATE_DIR")"; mkdir -p "$parent"
  staging="$(mktemp -d "$parent/.evidence-gate.XXXXXX")"; chmod 0700 "$staging"
  cleanup_gate() { rm -rf "$staging"; }
  trap cleanup_gate EXIT
  while IFS= read -r artifact_name; do
    "$SCRIPT_DIR/publish-evidence.sh" --file "$manifest_dir/$artifact_name" --environment "$ENVIRONMENT" \
      --build-id "$BUILD_ID" --stage "$STAGE" --artifact "$artifact_name" --account "$ACCOUNT" \
      --container "$CONTAINER" --receipt "$staging/$artifact_name.receipt.json" >/dev/null
  done < <(jq -r '.artifacts[]' "$GATE_MANIFEST")
  jq -s --arg environment "$ENVIRONMENT" --arg build "$BUILD_ID" --arg stage "$STAGE" \
    '{schemaVersion:1,environment:$environment,buildId:$build,stage:$stage,status:"accepted",artifacts:(sort_by(.artifact))}' \
    "$staging"/*.receipt.json > "$staging/gate-acceptance.json"
  chmod 0444 "$staging/gate-acceptance.json"
  "$SCRIPT_DIR/publish-evidence.sh" --file "$staging/gate-acceptance.json" --environment "$ENVIRONMENT" \
    --build-id "$BUILD_ID" --stage "$STAGE" --artifact gate-acceptance.json --account "$ACCOUNT" \
    --container "$CONTAINER" --receipt "$staging/gate.receipt.json" >/dev/null
  mv "$staging" "$GATE_DIR"; trap - EXIT
  printf '%s\n' "$GATE_DIR/gate.receipt.json"
  exit 0
fi

[[ -n "$FILE" && -n "$ENVIRONMENT" && -n "$BUILD_ID" && -n "$STAGE" && -n "$ARTIFACT" && -n "$ACCOUNT" ]] || fail "required argument missing"
valid_environment "$ENVIRONMENT" || fail "invalid environment"
valid_component "$BUILD_ID" && valid_component "$STAGE" && valid_component "$ARTIFACT" || fail "invalid path component"
[[ "$ACCOUNT" =~ ^[a-z0-9]{3,24}$ && "$CONTAINER" == "delivery-evidence" ]] || fail "invalid authoritative destination"
command -v az >/dev/null || fail "az required"
command -v jq >/dev/null || fail "jq required"

local_result="$($SCRIPT_DIR/validate-evidence.sh --file "$FILE")" || exit $?
sha256="$(jq -r '.sha256' <<<"$local_result")"
length="$(jq -r '.length' <<<"$local_result")"
blob="deliveries/$ENVIRONMENT/$BUILD_ID/$STAGE/$ARTIFACT"
delays=(1 4 16)

verify_exact() {
  local version="${1:-}"
  args=(--verify-remote --account "$ACCOUNT" --container "$CONTAINER" --blob "$blob" --sha256 "$sha256" --length "$length")
  [[ -n "$version" ]] && args+=(--version-id "$version")
  "$SCRIPT_DIR/validate-evidence.sh" "${args[@]}"
}

write_receipt() {
  local verification="$1" temporary
  [[ -z "$RECEIPT" ]] && return 0
  [[ ! -e "$RECEIPT" && ! -L "$RECEIPT" ]] || fail "receipt overwrite denied"
  mkdir -p "$(dirname "$RECEIPT")"
  temporary="$(mktemp "$(dirname "$RECEIPT")/.evidence-receipt.XXXXXX")"
  jq -c --arg account "$ACCOUNT" --arg container "$CONTAINER" --arg artifact "$ARTIFACT" '. + {schemaVersion:1,accepted:true,storageAccount:$account,container:$container,artifact:$artifact,controllerLocalAuthoritative:false}' <<<"$verification" > "$temporary"
  chmod 0600 "$temporary"
  mv "$temporary" "$RECEIPT"
}

for index in 0 1 2; do
  "${EVIDENCE_SLEEP_BIN:-sleep}" "${delays[$index]}"
  error_file="$(mktemp "${TMPDIR:-/tmp}/evidence-upload.XXXXXX")"
  if upload="$(az storage blob upload --auth-mode login --account-name "$ACCOUNT" \
      --container-name "$CONTAINER" --name "$blob" --file "$FILE" \
      --metadata "evidence_sha256=$sha256" "evidence_length=$length" \
      --if-none-match '*' --overwrite false --only-show-errors -o json 2>"$error_file")"; then
    version="$(jq -r '.versionId // ""' <<<"$upload")"
    [[ -n "$version" ]] || { rm -f "$error_file"; fail "upload returned no immutable version id"; }
    if verification="$(verify_exact "$version")"; then
      rm -f "$error_file"
      write_receipt "$verification"
      printf '%s\n' "$verification"
      exit 0
    fi
  else
    # A lost upload response is resolved only by an exact-path read. A matching
    # Azure version is success; a local copy is never accepted as evidence.
    if verification="$(verify_exact "" 2>/dev/null)"; then
      rm -f "$error_file"
      write_receipt "$verification"
      printf '%s\n' "$verification"
      exit 0
    fi
    if grep -Eiq '(ConditionNotMet|BlobAlreadyExists|PreconditionFailed|HTTP[^0-9]*412)' "$error_file"; then
      rm -f "$error_file"
      fail "immutable path already contains different evidence; overwrite denied"
    fi
  fi
  rm -f "$error_file"
done

fail "authoritative upload was not verified after attempts at 1/4/16 seconds"
