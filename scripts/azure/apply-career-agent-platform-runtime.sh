#!/usr/bin/env bash
set -euo pipefail

# Render and (when explicitly requested) apply the platform-owned runtime
# resources for the career-agent namespace. These values are deliberately
# supplied by Terraform/platform bootstrap rather than by the Argo CD release
# overlay. No credential or private key is read or written by this script.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
NAMESPACE=${NAMESPACE:-career-agent}
APPLY=${APPLY:-false}
FORCE_CONFLICTS=${FORCE_CONFLICTS:-false}
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

required=(
  KEY_VAULT_NAME ENTRA_TENANT_ID
  BFF_WORKLOAD_CLIENT_ID CORE_WORKLOAD_CLIENT_ID
  BFF_CLIENT_CERTIFICATE_VERSION PRIVATE_CORE_CERTIFICATE_VERSION
  PRIVATE_CORE_DNS_ZONE_NAME PRIVATE_CORE_CERTIFICATE_ISSUER_NAME
  PUBLIC_ORIGIN MANAGED_REDIS_HOST POSTGRESQL_HOST
  ACCEPTED_BFF_CONTRACT_RANGE ENVIRONMENT
)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    printf 'missing required platform runtime variable: %s\n' "$name" >&2
    exit 2
  fi
done

if ! command -v envsubst >/dev/null 2>&1; then
  printf 'envsubst is required to render platform runtime manifests\n' >&2
  exit 2
fi

render() {
  local source=$1
  local target="$WORK_DIR/$(printf '%s' "$source" | tr '/' '_')"
  envsubst < "$ROOT/$source" > "$target"
  if grep -Eq '\$\{[A-Za-z_][A-Za-z0-9_]*\}' "$target"; then
    printf 'unresolved placeholder in rendered manifest: %s\n' "$source" >&2
    exit 2
  fi
  printf '%s\n' "$target"
}

manifests=(
  deploy/k8s/base/ui/runtime-config.yaml
  deploy/k8s/base/ui/service-account.yaml
  deploy/k8s/base/bff/service-account.yaml
  deploy/k8s/base/bff/secret-provider-class.yaml
  deploy/k8s/base/bff/configmap.yaml
  deploy/k8s/base/core/service-account.yaml
  deploy/k8s/base/core/secret-provider-class.yaml
  deploy/k8s/base/core/configmap.yaml
)
rendered=()
for manifest in "${manifests[@]}"; do
  rendered+=("$(render "$manifest")")
done

if [[ "$APPLY" == "true" ]]; then
  apply_args=()
  for path in "${rendered[@]}"; do
    apply_args+=("-f" "$path")
  done
  [[ "$FORCE_CONFLICTS" == true ]] && apply_args+=(--force-conflicts)
  kubectl -n "$NAMESPACE" apply --server-side --field-manager=platform-bootstrap "${apply_args[@]}"
  printf 'applied platform runtime resources to namespace %s\n' "$NAMESPACE"
else
  kubectl apply --dry-run=client -n "$NAMESPACE" -f "${rendered[0]}" >/dev/null
  printf 'validated platform runtime resources (dry run); set APPLY=true to apply to %s\n' "$NAMESPACE"
fi
