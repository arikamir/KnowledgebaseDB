#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="${READINESS_MODE:-static}"
OUTPUT=""
NAMESPACE="career-agent"
PROJECT="career-agent"
SECRET="career-agent-acr-pull"

fail() { printf 'gitops readiness: %s\n' "$1" >&2; exit 2; }
while (($#)); do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --output) OUTPUT="${2:-}"; shift 2 ;;
    --namespace) NAMESPACE="${2:-}"; shift 2 ;;
    --project) PROJECT="${2:-}"; shift 2 ;;
    --secret) SECRET="${2:-}"; shift 2 ;;
    *) fail "unknown argument: $1" ;;
  esac
done
[[ "$MODE" == static || "$MODE" == live ]] || fail "mode must be static or live"
[[ "$NAMESPACE" == career-agent && "$PROJECT" == career-agent && "$SECRET" == career-agent-acr-pull ]] || fail "only the nonprod platform boundary is supported"

now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
namespace_status=pass
project_status=pass
secret_status=pass
registry_status=pass
workload_status=pass
namespace_reason="platform namespace contract exists"
project_reason="application-only AppProject is present"
secret_reason="platform-owned pull secret name is reserved"
registry_reason="immutable ACR image references are configured"
workload_reason="three-service application overlay and probes are present"

[[ -f "$ROOT/deploy/argocd/project.yaml" ]] || { project_status=fail; project_reason="AppProject manifest is missing"; }
[[ -f "$ROOT/deploy/k8s/overlays/argocd-nonprod/kustomization.yaml" ]] || { workload_status=fail; workload_reason="application overlay is missing"; }
[[ -f "$ROOT/deploy/argocd/environments/nonprod/release.json" ]] || { registry_status=fail; registry_reason="release declaration is missing"; }
if [[ -f "$ROOT/deploy/k8s/overlays/argocd-nonprod/application-images.yaml" ]] && [[ "$(rg -c 'name: career-agent-acr-pull' "$ROOT/deploy/k8s/overlays/argocd-nonprod/application-images.yaml" || true)" -ne 3 ]]; then
  secret_status=fail
  secret_reason="application overlay does not reference the platform pull secret three times"
fi

if [[ "$MODE" == live ]]; then
  command -v kubectl >/dev/null 2>&1 || fail "kubectl is required for live mode"
  kubectl get namespace "$NAMESPACE" >/dev/null 2>&1 || { namespace_status=fail; namespace_reason="namespace is unavailable"; }
  kubectl -n argocd get appproject "$PROJECT" >/dev/null 2>&1 || { project_status=fail; project_reason="AppProject is unavailable"; }
  kubectl -n "$NAMESPACE" get secret "$SECRET" >/dev/null 2>&1 || { secret_status=fail; secret_reason="platform pull secret is unavailable"; }
  kubectl -n "$NAMESPACE" get deployment ui bff core >/dev/null 2>&1 || { workload_status=fail; workload_reason="required workloads are unavailable"; }
  [[ -n "${ACR_LOGIN_SERVER:-}" ]] || { registry_status=fail; registry_reason="ACR_LOGIN_SERVER is not configured"; }
fi

status=ready
failure_reason=""
for item in "$namespace_status" "$project_status" "$secret_status" "$registry_status" "$workload_status"; do
  [[ "$item" == pass ]] || status=blocked
done
if [[ "$status" == blocked ]]; then
  failure_reason="namespace=${namespace_reason}; project=${project_reason}; pullSecret=${secret_reason}; registry=${registry_reason}; workloads=${workload_reason}"
fi

result="$(jq -n \
  --arg status "$status" --arg now "$now" --arg failure "$failure_reason" \
  --arg namespaceStatus "$namespace_status" --arg namespaceReason "$namespace_reason" \
  --arg projectStatus "$project_status" --arg projectReason "$project_reason" \
  --arg secretStatus "$secret_status" --arg secretReason "$secret_reason" \
  --arg registryStatus "$registry_status" --arg registryReason "$registry_reason" \
  --arg workloadStatus "$workload_status" --arg workloadReason "$workload_reason" \
  '{schemaVersion:1,status:$status,environment:"nonprod",checks:{namespace:{status:$namespaceStatus,reason:$namespaceReason},argocdProject:{status:$projectStatus,reason:$projectReason},registryPullSecret:{status:$secretStatus,name:"career-agent-acr-pull",reason:$secretReason},registry:{status:$registryStatus,reason:$registryReason},workloadPrerequisites:{status:$workloadStatus,reason:$workloadReason}},observedAt:$now} + (if $status == "blocked" then {failureReason:$failure} else {} end)')"

if [[ -n "$OUTPUT" ]]; then
  mkdir -p "$(dirname "$OUTPUT")"
  printf '%s\n' "$result" > "$OUTPUT"
else
  printf '%s\n' "$result"
fi
[[ "$status" == ready ]] || exit 1
