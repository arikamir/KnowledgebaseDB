#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-$(CDPATH='' cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
command -v terraform >/dev/null 2>&1 || { printf 'application URL: terraform is required\n' >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { printf 'application URL: jq is required\n' >&2; exit 1; }

output="$(terraform -chdir="$repo_root/infra/azure" output -json gateway_certificate_dns_bootstrap)"
url="$(jq -er '.browser_url | select(test("^https://[A-Za-z0-9.-]+/$"))' <<<"$output")" || {
  printf 'application URL: authoritative AGC browser URL is unavailable\n' >&2
  exit 1
}
printf '%s\n' "$url"
