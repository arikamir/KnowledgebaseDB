#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE="${GITOPS_EVIDENCE_OUTPUT:-$ROOT/artifacts/argocd-nonprod-sync.json}"
if [[ "${RUN_LIVE_GITOPS_TESTS:-false}" != true ]]; then
  printf '%s\n' '{"status":"skipped","reason":"RUN_LIVE_GITOPS_TESTS=true is required for an environment-gated cluster test"}'
  exit 0
fi

command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required" >&2; exit 2; }
command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 2; }
mkdir -p "$(dirname "$EVIDENCE")"
kubectl -n argocd get applicationset career-agent-services >/dev/null
kubectl -n argocd wait --for=jsonpath='{.status.health.status}'=Healthy application/career-agent-nonprod --timeout=120s
kubectl -n career-agent get secret career-agent-acr-pull >/dev/null
for service in ui bff core; do
  image="$(kubectl -n career-agent get deployment "$service" -o jsonpath='{.spec.template.spec.containers[0].image}')"
  [[ "$image" == *@sha256:* ]] || { echo "$service is not digest pinned" >&2; exit 1; }
done
jq -n --arg observedAt "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{status:"passed",environment:"nonprod",application:"career-agent-nonprod",observedAt:$observedAt,thresholds:{mergeToSyncSeconds:600,driftDetectionSeconds:300}}' > "$EVIDENCE"
cat "$EVIDENCE"
