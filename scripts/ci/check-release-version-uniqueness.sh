#!/usr/bin/env bash
set -euo pipefail

version="${1:-}"
source_revision="${2:-${GITHUB_SHA:-}}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

[[ -n "$version" ]] || { printf 'release version uniqueness: version is required\n' >&2; exit 1; }

shopt -s nullglob
for file in "$root"/deploy/argocd/environments/*/release.json; do
  existing_version="$(jq -r '.releaseVersion' "$file")"
  [[ "$existing_version" == "$version" ]] || continue
  existing_source="$(jq -r '.sourceRevision' "$file")"
  [[ -z "$source_revision" || "$existing_source" == "$source_revision" ]] || {
    printf 'release version uniqueness: %s already belongs to %s\n' "$version" "$existing_source" >&2
    exit 1
  }
done

if [[ -n "${RELEASE_VERSION_LEDGER:-}" && -f "$RELEASE_VERSION_LEDGER" ]]; then
  awk -F '\t' -v version="$version" -v source="$source_revision" '$1 == version && $2 != source { exit 1 }' "$RELEASE_VERSION_LEDGER" || {
    printf 'release version uniqueness: %s is already recorded for another source revision\n' "$version" >&2
    exit 1
  }
fi

# The declaration can be reverted, so also inspect repository history when a
# clone has full history. A version is reusable only for the same source SHA.
if git -C "$root" rev-parse --git-dir >/dev/null 2>&1; then
  while IFS= read -r commit; do
    [[ -n "$commit" ]] || continue
    historical="$(git -C "$root" show "$commit:deploy/argocd/environments/nonprod/release.json" 2>/dev/null || true)"
    [[ -n "$historical" ]] || continue
    historical_version="$(jq -r '.releaseVersion // empty' <<<"$historical" 2>/dev/null || true)"
    [[ "$historical_version" == "$version" ]] || continue
    historical_source="$(jq -r '.sourceRevision // empty' <<<"$historical" 2>/dev/null || true)"
    [[ -z "$source_revision" || "$historical_source" == "$source_revision" ]] || {
      printf 'release version uniqueness: %s appeared in repository history for %s\n' "$version" "$historical_source" >&2
      exit 1
    }
  done < <(git -C "$root" rev-list --all -- deploy/argocd/environments/nonprod/release.json 2>/dev/null || true)
fi

printf 'release version uniqueness: %s is available\n' "$version"
