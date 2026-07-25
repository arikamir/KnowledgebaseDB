#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCHEMA="$ROOT/config/argocd-release.schema.json"
[[ -f "$SCHEMA" ]] && jq empty "$SCHEMA" || { printf 'gitops release: schema missing or invalid\n' >&2; exit 1; }
shopt -s nullglob
if (( $# > 0 )); then
  files=("$@")
else
  files=("$ROOT"/deploy/argocd/environments/*/release.json)
fi
(( ${#files[@]} > 0 )) || { printf 'gitops release: no release declarations found\n' >&2; exit 1; }

versions=()
for file in "${files[@]}"; do
  environment="$(basename "$(dirname "$file")")"
  jq -e --arg environment "$environment" '
    (keys | sort) == ["ciRun", "environment", "releaseVersion", "schemaVersion", "services", "sourceRevision", "sourceTag", "validationEvidence"] and
    .schemaVersion == 1 and .environment == $environment and
    (.releaseVersion | type == "string" and test("^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\\.[0-9A-Za-z-]+)*)?(\\+[0-9A-Za-z-]+(\\.[0-9A-Za-z-]+)*)?$")) and
    (.sourceTag | type == "string" and test("^v?(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\\.[0-9A-Za-z-]+)*)?(\\+[0-9A-Za-z-]+(\\.[0-9A-Za-z-]+)*)?$") ) and
    ((.sourceTag | sub("^v"; "")) == .releaseVersion) and
    (.sourceRevision | type == "string" and test("^[0-9a-f]{40}$")) and
    (.ciRun | type == "object" and (keys | sort) == ["id", "repository", "workflow"] and all(.[]; type == "string" and length > 0)) and
    (.services | (keys | sort) == ["bff", "core", "ui"]) and
    all(.services[]; (keys | sort) == ["image"] and (.image | test("^[a-z0-9.-]+\\.azurecr\\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$"))) and
    (.validationEvidence | type == "object" and (keys | sort) == ["compatibility", "contract", "scan"] and all(.[]; type == "string" and length > 0)) and
    (tostring | test("(?i)(password|secret|token|private[_-]?key|client[_-]?secret|kubeconfig)") | not)
  ' "$file" >/dev/null || { printf 'gitops release: invalid declaration %s\n' "$file" >&2; exit 1; }
  versions+=("$(jq -r '.releaseVersion' "$file")")
done

unique_versions="$(printf '%s\n' "${versions[@]}" | sort -u | wc -l | tr -d ' ')"
if (( ${#versions[@]} != unique_versions )); then
  printf 'gitops release: release versions must be unique across environments\n' >&2
  exit 1
fi

printf 'gitops release: %s declaration(s) valid\n' "${#files[@]}"
