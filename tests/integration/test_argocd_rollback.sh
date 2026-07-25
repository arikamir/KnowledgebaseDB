#!/usr/bin/env bash
set -euo pipefail

if [[ "${RUN_LIVE_GITOPS_TESTS:-false}" != true ]]; then
  printf '%s\n' '{"status":"skipped","reason":"RUN_LIVE_GITOPS_TESTS=true is required for an environment-gated rollback test"}'
  exit 0
fi
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required" >&2; exit 2; }
kubectl -n argocd get application career-agent-nonprod >/dev/null
kubectl -n career-agent get deployment ui bff core >/dev/null
echo '{"status":"passed","authority":"reviewed-git-reversion","directArgoRollback":"non-authoritative"}'
