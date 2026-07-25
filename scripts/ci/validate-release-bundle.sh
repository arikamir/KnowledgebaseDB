#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUNDLE="${1:-${RELEASE_BUNDLE_PATH:-$ROOT/artifacts/release-bundle.json}}"
SEMVER='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'
TAG_SEMVER="^v?${SEMVER#^}"

fail() {
  printf 'gitops release bundle: %s\n' "$1" >&2
  exit 1
}

[[ -f "$BUNDLE" ]] || fail "bundle not found: $BUNDLE"
jq empty "$BUNDLE" >/dev/null 2>&1 || fail "invalid JSON: $BUNDLE"

jq -e \
  --arg semver "$SEMVER" \
  --arg tagSemver "$TAG_SEMVER" \
  '(
    (keys | sort) == ["ciRun", "environment", "releaseVersion", "schemaVersion", "services", "sourceRevision", "sourceTag", "validationEvidence"] and
    .schemaVersion == 1 and
    .environment == "nonprod" and
    (.releaseVersion | type == "string" and test($semver)) and
    (.sourceTag | type == "string" and test($tagSemver)) and
    ((.sourceTag | sub("^v"; "")) == .releaseVersion) and
    (.sourceRevision | type == "string" and test("^[0-9a-f]{40}$")) and
    (.ciRun | type == "object" and (keys | sort) == ["id", "repository", "workflow"] and all(.[]; type == "string" and length > 0)) and
    (.services | type == "object" and (keys | sort) == ["bff", "core", "ui"] and all(.[]; (keys | sort) == ["image"] and (.image | test("^[a-z0-9.-]+\\.azurecr\\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$")))) and
    (.validationEvidence | type == "object" and (keys | sort) == ["compatibility", "contract", "scan"] and all(.[]; type == "string" and length > 0)) and
    (tostring | test("(?i)(password|secret|token|private[_-]?key|client[_-]?secret|kubeconfig)") | not)
  )' "$BUNDLE" >/dev/null || fail "schema, SemVer, digest, evidence, or credential validation failed"

if [[ "${REQUIRE_PROTECTED_TAG:-false}" == "true" && "${GITHUB_REF_PROTECTED:-false}" != "true" ]]; then
  fail "source tag is not proven protected"
fi

if [[ -n "${GITHUB_SHA:-}" ]]; then
  bundle_revision="$(jq -r '.sourceRevision' "$BUNDLE")"
  [[ "$bundle_revision" == "$GITHUB_SHA" ]] || fail "bundle sourceRevision does not match GITHUB_SHA"
fi

printf 'gitops release bundle: valid (%s)\n' "$BUNDLE"
