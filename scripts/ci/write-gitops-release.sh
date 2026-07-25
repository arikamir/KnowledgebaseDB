#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="" TAG="${GITHUB_REF_NAME:-}" SOURCE_REVISION="${GITHUB_SHA:-}" RUN_ID="${GITHUB_RUN_ID:-}"
OUTPUT_BUNDLE="" OUTPUT_DECLARATION="$ROOT/deploy/argocd/environments/nonprod/release.json"
CONTRACT_EVIDENCE="artifact://contract.json" SCAN_EVIDENCE="artifact://scan.json" COMPATIBILITY_EVIDENCE="artifact://compatibility.json"

while (($#)); do
  case "$1" in
    --manifest) MANIFEST="${2:-}"; shift 2 ;;
    --tag) TAG="${2:-}"; shift 2 ;;
    --source-revision) SOURCE_REVISION="${2:-}"; shift 2 ;;
    --run-id) RUN_ID="${2:-}"; shift 2 ;;
    --output-bundle) OUTPUT_BUNDLE="${2:-}"; shift 2 ;;
    --output-declaration) OUTPUT_DECLARATION="${2:-}"; shift 2 ;;
    --contract-evidence) CONTRACT_EVIDENCE="${2:-}"; shift 2 ;;
    --scan-evidence) SCAN_EVIDENCE="${2:-}"; shift 2 ;;
    --compatibility-evidence) COMPATIBILITY_EVIDENCE="${2:-}"; shift 2 ;;
    *) printf 'write gitops release: unknown argument %s\n' "$1" >&2; exit 2 ;;
  esac
done

[[ -f "$MANIFEST" && -n "$OUTPUT_BUNDLE" && -n "$OUTPUT_DECLARATION" ]] || { printf 'write gitops release: manifest and outputs are required\n' >&2; exit 2; }
[[ "$TAG" =~ ^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$ ]] || { printf 'write gitops release: invalid protected SemVer tag\n' >&2; exit 1; }
[[ "$SOURCE_REVISION" =~ ^[0-9a-f]{40}$ && -n "$RUN_ID" ]] || { printf 'write gitops release: source revision and CI run are required\n' >&2; exit 1; }

release_version="${TAG#v}"
mkdir -p "$(dirname "$OUTPUT_BUNDLE")" "$(dirname "$OUTPUT_DECLARATION")"
services="$(jq -ce '.services | (keys | sort) == ["bff", "core", "ui"] and all(.[]; (.image | type == "string"))' "$MANIFEST" >/dev/null && jq -c '{ui:{image:.services.ui.image},bff:{image:.services.bff.image},core:{image:.services.core.image}}' "$MANIFEST")" || {
  printf 'write gitops release: manifest must contain exactly ui, bff, and core services\n' >&2
  exit 1
}

jq -n \
  --arg version "$release_version" \
  --arg tag "$TAG" \
  --arg revision "$SOURCE_REVISION" \
  --arg run "$RUN_ID" \
  --arg repository "${GITHUB_REPOSITORY:-}" \
  --arg workflow "${GITHUB_WORKFLOW:-delivery.yml}" \
  --arg contract "$CONTRACT_EVIDENCE" \
  --arg scan "$SCAN_EVIDENCE" \
  --arg compatibility "$COMPATIBILITY_EVIDENCE" \
  --argjson services "$services" \
  '{schemaVersion:1,environment:"nonprod",releaseVersion:$version,sourceTag:$tag,sourceRevision:$revision,ciRun:{id:$run,repository:$repository,workflow:$workflow},services:$services,validationEvidence:{contract:$contract,scan:$scan,compatibility:$compatibility}}' > "$OUTPUT_BUNDLE"

REQUIRE_PROTECTED_TAG=true "$ROOT/scripts/ci/validate-release-bundle.sh" "$OUTPUT_BUNDLE"
"$ROOT/scripts/ci/check-release-version-uniqueness.sh" "$release_version" "$SOURCE_REVISION"

jq -n \
  --arg version "$release_version" \
  --arg tag "$TAG" \
  --arg revision "$SOURCE_REVISION" \
  --arg run "$RUN_ID" \
  --arg repository "${GITHUB_REPOSITORY:-}" \
  --arg workflow "${GITHUB_WORKFLOW:-delivery.yml}" \
  --arg contract "$CONTRACT_EVIDENCE" \
  --arg scan "$SCAN_EVIDENCE" \
  --arg compatibility "$COMPATIBILITY_EVIDENCE" \
  --argjson services "$services" \
  '{schemaVersion:1,environment:"nonprod",releaseVersion:$version,sourceTag:$tag,sourceRevision:$revision,ciRun:{id:$run,repository:$repository,workflow:$workflow},services:{ui:{image:$services.ui.image},bff:{image:$services.bff.image},core:{image:$services.core.image}},validationEvidence:{contract:$contract,scan:$scan,compatibility:$compatibility}}' > "$OUTPUT_DECLARATION"

validation_dir="$(mktemp -d "${TMPDIR:-/tmp}/gitops-release-validation.XXXXXX")"
trap 'rm -rf "$validation_dir"' EXIT
mkdir -p "$validation_dir/nonprod"
cp "$OUTPUT_DECLARATION" "$validation_dir/nonprod/release.json"
"$ROOT/scripts/ci/validate-gitops-release.sh" "$validation_dir/nonprod/release.json"
"$ROOT/scripts/ci/validate-gitops-release.sh"
printf 'write gitops release: declaration=%s bundle=%s\n' "$OUTPUT_DECLARATION" "$OUTPUT_BUNDLE"
