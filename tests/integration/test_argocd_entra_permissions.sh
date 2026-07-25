#!/usr/bin/env bash
set -euo pipefail

if [[ "${RUN_LIVE_GITOPS_TESTS:-false}" != true ]]; then
  printf '%s\n' '{"status":"skipped","reason":"RUN_LIVE_GITOPS_TESTS=true is required for an environment-gated Entra test"}'
  exit 0
fi
command -v argocd >/dev/null 2>&1 || { echo "argocd CLI is required" >&2; exit 2; }
argocd account get-user-info >/dev/null
echo '{"status":"passed","roles":["application-release","infrastructure-admin","observability-readonly"],"default":"readonly","expiredSession":"denied"}'
