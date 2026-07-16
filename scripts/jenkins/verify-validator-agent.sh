#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="$ROOT/config/jenkins-validator-policy-v1.json"
TEMPLATE_JSON=""
RUNTIME=false

usage() {
  printf 'Usage: %s --template-json FILE [--policy FILE] [--runtime]\n' "$0" >&2
  exit 2
}

fail() {
  printf 'validator preflight failed: %s\n' "$1" >&2
  exit 1
}

while (($#)); do
  case "$1" in
    --template-json)
      (($# >= 2)) || usage
      TEMPLATE_JSON="$2"
      shift 2
      ;;
    --policy)
      (($# >= 2)) || usage
      POLICY="$2"
      shift 2
      ;;
    --runtime)
      RUNTIME=true
      shift
      ;;
    *) usage ;;
  esac
done

[[ -n "$TEMPLATE_JSON" && -f "$TEMPLATE_JSON" ]] || usage
[[ -f "$POLICY" ]] || fail "policy file is missing"
command -v jq >/dev/null 2>&1 || fail "jq is required"

jq -e '
  .version == 1 and
  .cloud == "azure" and
  .template == "azure-aci-validator" and
  .label == "azure-aci-validator" and
  .allRefs == true and
  .unprotectedRefDisposition == "stop_after_non_azure_validation" and
  .controllerOrLocalFallback == false and
  .suiteScript == "scripts/ci/validate-non-azure.sh" and
  .managedIdentity == {"systemAssigned": false, "userAssigned": []}
' "$POLICY" >/dev/null || fail "policy does not preserve all-ref identityless confinement"

cloud="$(jq -r '.cloud' "$POLICY")"
template="$(jq -r '.template' "$POLICY")"
label="$(jq -r '.label' "$POLICY")"

jq -e --arg cloud "$cloud" --arg template "$template" --arg label "$label" '
  .cloud == $cloud and
  .name == $template and
  .label == $label and
  (.image | type == "string" and test("^[^[:space:]@]+@sha256:[0-9a-f]{64}$")) and
  .environment == {} and
  .ports == [] and
  .volumes == [] and
  .systemAssignedIdentity == false and
  .userAssignedIdentities == []
' "$TEMPLATE_JSON" >/dev/null || fail "template exposes identity, credentials, mutable image, network, storage, or fallback surface"

if [[ "$RUNTIME" == true ]]; then
  while IFS='=' read -r key _; do
    case "$key" in
      AZURE_*|ARM_*|KUBECONFIG|DOCKER_CONFIG)
        fail "runtime exposes prohibited Azure or delivery environment"
        ;;
    esac
  done < <(env)

  if command -v curl >/dev/null 2>&1 &&
     [[ "$(curl --silent --output /dev/null --write-out '%{http_code}' \
       --max-time 2 --header 'Metadata: true' \
       'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fmanagement.azure.com%2F' || true)" == 200 ]]; then
    fail "runtime can obtain an Azure instance identity token"
  fi
fi

printf 'validator preflight passed\n'
