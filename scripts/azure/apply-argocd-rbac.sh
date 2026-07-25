#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTRACT="${1:-$ROOT/config/argocd-oidc-rbac.yaml}"
RBAC_POLICY="${RBAC_POLICY:-$ROOT/config/argocd-rbac-policy.yaml}"

[[ -f "$CONTRACT" ]] || { printf 'argocd rbac: contract not found: %s\n' "$CONTRACT" >&2; exit 1; }
[[ -f "$RBAC_POLICY" ]] || { printf 'argocd rbac: policy not found: %s\n' "$RBAC_POLICY" >&2; exit 1; }
! rg -n -i 'clientSecret:|client_secret:|token:|password:' "$CONTRACT" >/dev/null || {
  printf 'argocd rbac: credential material is forbidden in the contract\n' >&2
  exit 1
}

if [[ "${APPLY:-false}" != "true" ]]; then
  printf 'argocd rbac: validated non-secret contract (set APPLY=true to apply through platform bootstrap)\n'
  exit 0
fi

command -v kubectl >/dev/null 2>&1 || { printf 'argocd rbac: kubectl is required\n' >&2; exit 1; }
kubectl apply --server-side --filename "$CONTRACT" --filename "$RBAC_POLICY"
