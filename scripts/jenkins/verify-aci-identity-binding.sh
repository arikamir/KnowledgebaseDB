#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="$ROOT/config/jenkins-aci-identity-policy-v1.json"
MANIFEST="" TEMPLATES="" RUNTIME_IDENTITIES="" AUTHORIZATION=""

usage() {
  printf 'Usage: %s --manifest FILE --templates FILE --runtime-identities FILE --authorization FILE [--policy FILE]\n' "$0" >&2
  exit 2
}

fail() { printf 'ACI identity binding verification failed: %s\n' "$1" >&2; exit 1; }

while (($#)); do
  case "$1" in
    --manifest) MANIFEST="${2:-}"; shift 2 ;;
    --templates) TEMPLATES="${2:-}"; shift 2 ;;
    --runtime-identities) RUNTIME_IDENTITIES="${2:-}"; shift 2 ;;
    --authorization) AUTHORIZATION="${2:-}"; shift 2 ;;
    --policy) POLICY="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

for input in "$MANIFEST" "$TEMPLATES" "$RUNTIME_IDENTITIES" "$AUTHORIZATION" "$POLICY"; do
  [[ -f "$input" ]] || usage
done
command -v jq >/dev/null 2>&1 || fail "jq is required"

jq -e '
  .schemaVersion == 1 and .manifestStatus == "reviewed" and
  .state.locked == true and .identities.validator == null and .identities.ui == null and
  (.identities.publisher | type == "string" and startswith("/subscriptions/")) and
  (.identities.deployer | type == "string" and startswith("/subscriptions/")) and
  .identities.publisher != .identities.deployer and
  (.review.generatedAt | fromdateiso8601 | type == "number") and
  (.review.expiresAt | fromdateiso8601 | type == "number")
' "$MANIFEST" >/dev/null || fail "reviewed bootstrap manifest or delivery identities are invalid"

cloud="$(jq -r '.cloud' "$POLICY")"
publisher="$(jq -r '.identities.publisher' "$MANIFEST")"
deployer="$(jq -r '.identities.deployer' "$MANIFEST")"

jq -e --arg cloud "$cloud" --arg publisher "$publisher" --arg deployer "$deployer" '
  keys == ["cloud", "controllerOrLocalFallback", "schemaVersion", "templates"] and
  .schemaVersion == 1 and .cloud == $cloud and .controllerOrLocalFallback == false and
  (.templates | keys == ["deployer", "publisher", "validator"]) and
  .templates.validator == {
    name:"azure-aci-validator", label:"azure-aci-validator",
    systemAssignedIdentity:false, userAssignedIdentities:[]
  } and
  .templates.publisher == {
    name:"azure-aci-publisher", label:"azure-aci-publisher",
    systemAssignedIdentity:false, userAssignedIdentities:[$publisher]
  } and
  .templates.deployer == {
    name:"azure-aci-deployer", label:"azure-aci-deployer",
    systemAssignedIdentity:false, userAssignedIdentities:[$deployer]
  }
' "$TEMPLATES" >/dev/null || fail "template has a missing, swapped, additional, or system-assigned identity"

jq -e --arg publisher "$publisher" --arg deployer "$deployer" '
  keys == ["deployer", "publisher", "validator"] and
  .validator == {systemAssignedIdentity:false,userAssignedIdentities:[]} and
  .publisher == {systemAssignedIdentity:false,userAssignedIdentities:[$publisher]} and
  .deployer == {systemAssignedIdentity:false,userAssignedIdentities:[$deployer]}
' "$RUNTIME_IDENTITIES" >/dev/null || fail "running ACI identity does not match its template and manifest"

jq -e --slurpfile policy "$POLICY" '
  .referenceType as $ref |
  (.requestedTemplates | type == "array") and
  ((.requestedTemplates | unique | length) == (.requestedTemplates | length)) and
  (.requestedStages | type == "object") and
  ($policy[0].referenceRules[$ref] != null) and
  all(.requestedTemplates[]; . as $template | $policy[0].referenceRules[$ref] | index($template) != null) and
  all(.requestedStages | to_entries[];
    .key as $template |
    (.value | type == "array") and
    all(.value[]; . as $stage | $policy[0].templates[$template].allowedStages | index($stage) != null))
' "$AUTHORIZATION" >/dev/null || fail "reference requested an unauthorized template, token, or stage"

resource_group_id="/subscriptions/$(jq -r '.subscriptionId' "$MANIFEST")/resourceGroups/$(jq -r '.resourceGroup' "$MANIFEST")"
aks_id="$(jq -r '.resources.aksId' "$MANIFEST")"
acr_id="$(jq -r '.resources.acrId' "$MANIFEST")"
jq -e --arg rg "$resource_group_id" --arg aks "$aks_id" --arg acr "$acr_id" --slurpfile policy "$POLICY" '
  keys == ["crossIdentityDenials", "deployerAssignments", "publisherAssignments", "referenceType", "requestedStages", "requestedTemplates", "requiredDenials"] and
  (.deployerAssignments | sort_by(.roleDefinitionName,.scope)) ==
    ([{roleDefinitionName:"Reader",scope:$rg},{roleDefinitionName:"Azure Kubernetes Service RBAC Writer",scope:$aks}] | sort_by(.roleDefinitionName,.scope)) and
  .publisherAssignments == [{roleDefinitionName:"AcrPush",scope:$acr}] and
  (.requiredDenials | sort) == ($policy[0].requiredDenials | sort) and
  (.crossIdentityDenials | sort) == ($policy[0].crossIdentityDenials | sort)
' "$AUTHORIZATION" >/dev/null || fail "role assignment or required denial evidence drifted"

printf 'ACI identity binding verification passed\n'
