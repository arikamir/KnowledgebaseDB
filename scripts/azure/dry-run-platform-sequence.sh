#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AUTHORIZATION="" ATTESTATION="" PRINCIPALS=""

usage() {
  printf 'Usage: %s --authorization FILE --attestation FILE --principals FILE\n' "$0" >&2
  exit 2
}

while (($#)); do
  case "$1" in
    --authorization) AUTHORIZATION="${2:-}"; shift 2 ;;
    --attestation) ATTESTATION="${2:-}"; shift 2 ;;
    --principals) PRINCIPALS="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
for input in "$AUTHORIZATION" "$ATTESTATION" "$PRINCIPALS"; do [[ -f "$input" ]] || usage; done

[[ ! -e "$ROOT/config/platform-bootstrap-nonprod.json" ]] || {
  printf 'platform sequence dry-run: live manifest must not exist before T194\n' >&2
  exit 1
}

"$ROOT/scripts/azure/bootstrap-ui-platform.sh" dry-run \
  --repo-root "$ROOT" --authorization "$AUTHORIZATION" --attestation "$ATTESTATION"
"$ROOT/scripts/azure/bootstrap-data-principals.sh" dry-run --principals "$PRINCIPALS"

install_contract="$ROOT/deploy/k8s/platform/alb-controller/install-contract.yaml"
migration="$ROOT/deploy/k8s/base/migration/kustomization.yaml"
[[ -f "$install_contract" && -f "$migration" ]] || exit 1
grep -Fq 'installOrder: gateway-api-crds,alb-controller,controller-ready-attestation,gateway-resources' "$install_contract"
grep -Fq 'liveInstallAllowed: "false-before-T194"' "$install_contract"
for guardrail in namespace.yaml service-account.yaml gitops-rbac.yaml network-policy.yaml validating-admission-policy.yaml; do
  grep -Fq "$guardrail" "$migration" || exit 1
done

finalizer="$ROOT/scripts/azure/finalize-ui-platform.sh"
grep -Fq 'PLATFORM_FINALIZATION_AUTHORIZED:-}" == T194' "$finalizer"
grep -Fq 'expected_output="$REPO_ROOT/config/platform-bootstrap-nonprod.json"' "$finalizer"
grep -Fq 'preflight-ui-platform.sh" live' "$finalizer"

jq -cn '{
  schemaVersion:1,status:"dry-run-valid",liveMutation:false,manifestEmitted:false,
  order:["terraform-apply-or-import","data-principal-bootstrap","alb-controller-install-and-attestation","migration-guardrails-install-and-attestation","identity-denial-attestation","sole-finalization"],
  liveExecutionGate:"T194"
}'
