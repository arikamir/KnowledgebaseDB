#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"; [[ "$ACTION" =~ ^(validate-manifest|publish|check)$ ]] || exit 2; shift
MANIFEST="" ACCOUNT="" CONTAINER="delivery-evidence" GATE_DIR="" EXPECTED_STAGE=""
while (($#)); do
  case "$1" in
    --manifest) MANIFEST="${2:-}"; shift 2 ;;
    --account) ACCOUNT="${2:-}"; shift 2 ;;
    --container) CONTAINER="${2:-}"; shift 2 ;;
    --gate-dir) GATE_DIR="${2:-}"; shift 2 ;;
    --stage) EXPECTED_STAGE="${2:-}"; shift 2 ;;
    *) exit 2 ;;
  esac
done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fail() { printf 'evidence gate: %s\n' "$1" >&2; exit 1; }

required_artifacts() {
  case "$1" in
    pre-promotion) printf '%s\n' artifact-provenance.json change-manifest.json release-manifest.json validation-summary.json ;;
    pre-migration) printf '%s\n' compatibility.json migration-plan.json schema-before.json ;;
    post-migration) printf '%s\n' migration-cleanup.json migration-result.json schema-after.json ;;
    pre-mutation) printf '%s\n' deployment-snapshot.json mutation-plan.json ;;
    post-mutation) printf '%s\n' mutation-journal.jsonl rollout.json ;;
    verification) printf '%s\n' deployment-snapshot.json smoke.json verification.json ;;
    rollback) printf '%s\n' rollback-journal.jsonl rollback-verification.json ;;
    *) return 1 ;;
  esac
}

validate_manifest() {
  [[ -f "$MANIFEST" && ! -L "$MANIFEST" ]] || fail "manifest missing"
  jq -e 'keys==["artifacts","buildId","environment","schemaVersion","stage"] and .schemaVersion==1 and
    (.environment|test("^[a-z0-9][a-z0-9._-]{1,62}$")) and
    (.buildId|test("^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")) and
    (.stage|test("^(pre-promotion|pre-migration|post-migration|pre-mutation|post-mutation|verification|rollback)$")) and
    (.artifacts|type=="array" and length>0 and length==(unique|length)) and
    all(.artifacts[]; test("^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$"))' "$MANIFEST" >/dev/null || fail "invalid manifest"
  stage="$(jq -r '.stage' "$MANIFEST")"
  actual="$(jq -r '.artifacts[]' "$MANIFEST" | LC_ALL=C sort)"
  expected="$(required_artifacts "$stage" | LC_ALL=C sort)"
  [[ "$actual" == "$expected" ]] || fail "required artifact set incomplete or unexpected"
  manifest_dir="$(cd "$(dirname "$MANIFEST")" && pwd)"
  while IFS= read -r artifact; do [[ -f "$manifest_dir/$artifact" && ! -L "$manifest_dir/$artifact" ]] || fail "required artifact missing"; done <<<"$expected"
}

case "$ACTION" in
  validate-manifest) validate_manifest ;;
  publish)
    validate_manifest
    [[ "$ACCOUNT" =~ ^[a-z0-9]{3,24}$ && "$CONTAINER" == delivery-evidence && -n "$GATE_DIR" ]] || fail "invalid publication destination"
    "$SCRIPT_DIR/publish-evidence.sh" --gate-manifest "$MANIFEST" --gate-dir "$GATE_DIR" --account "$ACCOUNT" --container "$CONTAINER"
    ;;
  check)
    [[ -d "$GATE_DIR" && -f "$GATE_DIR/gate-acceptance.json" && -f "$GATE_DIR/gate.receipt.json" ]] || fail "gate acceptance missing"
    acceptance="$GATE_DIR/gate-acceptance.json"; receipt="$GATE_DIR/gate.receipt.json"
    jq -e --arg stage "$EXPECTED_STAGE" 'keys==["artifacts","buildId","environment","schemaVersion","stage","status"] and
      .schemaVersion==1 and .status=="accepted" and .stage==$stage and (.artifacts|length>0) and
      all(.artifacts[]; .accepted==true and .authority=="azure-blob-version" and .controllerLocalAuthoritative==false)' "$acceptance" >/dev/null || fail "gate acceptance invalid or wrong stage"
    sha="$(shasum -a 256 "$acceptance" | awk '{print $1}')"; length="$(wc -c < "$acceptance" | tr -d ' ')"
    jq -e --arg sha "$sha" --arg length "$length" '.accepted==true and .sha256==$sha and (.length|tostring)==$length' "$receipt" >/dev/null || fail "gate receipt does not bind acceptance"
    verify_receipt() {
      local item="$1"
      "$SCRIPT_DIR/validate-evidence.sh" --verify-remote --account "$(jq -r '.storageAccount' <<<"$item")" \
        --container "$(jq -r '.container' <<<"$item")" --blob "$(jq -r '.blob' <<<"$item")" \
        --version-id "$(jq -r '.versionId' <<<"$item")" --sha256 "$(jq -r '.sha256' <<<"$item")" --length "$(jq -r '.length' <<<"$item")" >/dev/null
    }
    verify_receipt "$(cat "$receipt")" || fail "authoritative acceptance unavailable"
    while IFS= read -r item; do verify_receipt "$item" || fail "authoritative artifact unavailable"; done < <(jq -c '.artifacts[]' "$acceptance")
    jq -cn --arg stage "$EXPECTED_STAGE" --arg buildId "$(jq -r '.buildId' "$acceptance")" '{gate:"open",stage:$stage,buildId:$buildId,authority:"azure-blob-version"}'
    ;;
esac
