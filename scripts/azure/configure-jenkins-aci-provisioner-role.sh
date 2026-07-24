#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="${POLICY:-$ROOT/config/jenkins-aci-provisioner-role-v1.json}"
SUBSCRIPTION_ID="${1:-$(az account show --query id -o tsv)}"

[[ "$SUBSCRIPTION_ID" =~ ^[0-9a-fA-F-]{36}$ && -f "$POLICY" ]] || {
  printf 'usage: %s [subscription-id]\n' "$0" >&2
  exit 2
}
command -v az >/dev/null 2>&1 || { printf 'az is required\n' >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { printf 'jq is required\n' >&2; exit 1; }

role_name="$(jq -r '.roleName' "$POLICY")"
role_id="$(jq -r '.name' "$POLICY")"
tmp="$(mktemp "${TMPDIR:-/tmp}/jenkins-aci-provisioner-role.XXXXXX.json")"
trap 'rm -f "$tmp"' EXIT

jq --arg scope "/subscriptions/$SUBSCRIPTION_ID" '
  {
    Name: .name,
    IsCustom: true,
    Description: .description,
    Actions: .actions,
    NotActions: .notActions,
    DataActions: .dataActions,
    NotDataActions: .notDataActions,
    AssignableScopes: [$scope]
  }
' "$POLICY" >"$tmp"

existing="$(az role definition list --name "$role_name" --query '[0].name' -o tsv)"
if [[ -n "$existing" && "$existing" != "$role_id" ]]; then
  printf 'role name collision: expected %s, found %s\n' "$role_id" "$existing" >&2
  exit 1
fi
if [[ -n "$existing" ]]; then
  az role definition update --role-definition "$tmp" --only-show-errors >/dev/null
else
  az role definition create --role-definition "$tmp" --only-show-errors >/dev/null
fi

actual="$(az role definition list --name "$role_name" --query '[0].permissions[0].actions' -o json)"
expected="$(jq -c '.actions | sort' "$POLICY")"
[[ "$(jq -c 'sort' <<<"$actual")" == "$expected" ]] || {
  printf 'role action verification failed\n' >&2
  exit 1
}
printf 'Verified %s (%s) in subscription %s\n' "$role_name" "$role_id" "$SUBSCRIPTION_ID"
