#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
LIVE=false
SKIP_CONTRACT=false
OUTPUT_DIR="$ROOT/artifacts/gitops-tests"

usage() {
  cat <<'EOF'
Usage: run-gitops-tests.sh [--live] [--output-dir PATH] [--skip-contract]

Runs identityless GitOps checks from the workstation. --live opts into read-only
AKS/Argo CD checks and requires the current kubectl context to be reachable.
EOF
}

while (($#)); do
  case "$1" in
    --live) LIVE=true; shift ;;
    --skip-contract) SKIP_CONTRACT=true; shift ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      [[ -n "$OUTPUT_DIR" ]] || { usage >&2; exit 2; }
      shift 2
      ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'run-gitops-tests: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

cd "$ROOT"
mkdir -p "$OUTPUT_DIR"
command -v jq >/dev/null 2>&1 || { echo "run-gitops-tests: jq is required" >&2; exit 2; }
command -v kubectl >/dev/null 2>&1 || { echo "run-gitops-tests: kubectl is required" >&2; exit 2; }
command -v helm >/dev/null 2>&1 || { echo "run-gitops-tests: helm is required" >&2; exit 2; }

echo "== GitOps release validation =="
scripts/ci/validate-gitops-release.sh
scripts/ci/validate-release-bundle.sh tests/contract/fixtures/gitops/valid-release-bundle.json

echo "== Kustomize rendering =="
kubectl kustomize deploy/argocd > "$OUTPUT_DIR/argocd-render.yaml"
kubectl kustomize deploy/k8s/overlays/argocd-nonprod > "$OUTPUT_DIR/application-render.yaml"
core_image="$(jq -r '.services.core.image' deploy/argocd/environments/nonprod/release.json)"
source_revision="$(jq -r '.sourceRevision' deploy/argocd/environments/nonprod/release.json)"
helm template core-migration-hook deploy/k8s/overlays/argocd-nonprod-migration \
  --set-string "image=$core_image" \
  --set-string "sourceRevision=$source_revision" \
  > "$OUTPUT_DIR/migration-render.yaml"

echo "== Static readiness =="
scripts/ci/check-gitops-platform-ready.sh --mode static --output "$OUTPUT_DIR/readiness-static.json"

if [[ "$SKIP_CONTRACT" != true ]]; then
  echo "== Feature contract tests =="
  PYTHONPATH=. pytest -q --confcutdir=tests/contract \
    tests/contract/test_argocd_application_set.py \
    tests/contract/test_argocd_entra_rbac.py \
    tests/contract/test_gitops_evidence.py \
    tests/contract/test_gitops_least_privilege.py \
    tests/contract/test_gitops_readiness.py \
    tests/contract/test_gitops_remediations.py \
    tests/contract/test_gitops_rollback.py \
    tests/contract/test_gitops_workflow_boundaries.py \
    tests/contract/test_release_declaration.py \
    tests/contract/test_release_pull_request_flow.py \
    | tee "$OUTPUT_DIR/contract-tests.txt"
fi

if [[ "$LIVE" == true ]]; then
  echo "== Live workstation checks =="
  current_context="$(kubectl config current-context 2>/dev/null || true)"
  [[ -n "$current_context" ]] || { echo "run-gitops-tests: no kubectl context is configured" >&2; exit 1; }
  api_server="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || true)"
  if ! kubectl get nodes -o wide > "$OUTPUT_DIR/nodes.txt" 2>&1; then
    printf 'run-gitops-tests: unable to reach Kubernetes API\ncontext: %s\nserver: %s\n' "$current_context" "$api_server" >&2
    cat "$OUTPUT_DIR/nodes.txt" >&2
    exit 1
  fi
  cat "$OUTPUT_DIR/nodes.txt"
  scripts/ci/check-gitops-platform-ready.sh --mode live --output "$OUTPUT_DIR/readiness-live.json"
  RUN_LIVE_GITOPS_TESTS=true GITOPS_EVIDENCE_OUTPUT="$OUTPUT_DIR/argocd-sync.json" \
    tests/integration/test_argocd_nonprod_sync.sh | tee "$OUTPUT_DIR/argocd-sync.txt"
  RUN_LIVE_GITOPS_TESTS=true tests/integration/test_argocd_rollback.sh | tee "$OUTPUT_DIR/argocd-rollback.txt"
  RUN_LIVE_GITOPS_TESTS=true tests/integration/test_argocd_entra_permissions.sh | tee "$OUTPUT_DIR/argocd-entra-permissions.txt"
fi

echo "GitOps checks completed: $OUTPUT_DIR"
