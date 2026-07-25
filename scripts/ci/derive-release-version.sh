#!/usr/bin/env bash
set -euo pipefail

tag="${1:-${GITHUB_REF_NAME:-}}"
source_revision="${2:-${GITHUB_SHA:-}}"
semver='^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'

fail() {
  printf 'release version: %s\n' "$1" >&2
  exit 1
}

[[ -n "$tag" ]] || fail "tag is required"
[[ "$tag" =~ $semver ]] || fail "tag is not a valid SemVer 2 value: $tag"
[[ -n "$source_revision" && "$source_revision" =~ ^[0-9a-f]{40}$ ]] || fail "a lowercase 40-character source revision is required"
[[ "${GITHUB_REF_TYPE:-tag}" == "tag" ]] || fail "release must originate from a tag"
[[ "${GITHUB_REF_PROTECTED:-false}" == "true" ]] || fail "release tag is not proven protected"

if git rev-parse --git-dir >/dev/null 2>&1; then
  resolved="$(git rev-parse "refs/tags/$tag^{commit}" 2>/dev/null || true)"
  [[ "$resolved" == "$source_revision" ]] || fail "tag $tag does not point to source revision $source_revision"
fi

printf '%s\n' "${tag#v}"
