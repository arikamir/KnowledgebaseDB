#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
POLICY="$ROOT/config/jenkins-cloud-credential-policy-v1.json"
METADATA=""
ASSIGNMENTS=""
NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

usage() {
  printf 'Usage: %s --metadata FILE --assignments FILE [--policy FILE] [--now ISO8601]\n' "$0" >&2
  exit 2
}

while (($#)); do
  case "$1" in
    --metadata) METADATA="${2:-}"; shift 2 ;;
    --assignments) ASSIGNMENTS="${2:-}"; shift 2 ;;
    --policy) POLICY="${2:-}"; shift 2 ;;
    --now) NOW="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -f "$METADATA" && -f "$ASSIGNMENTS" && -f "$POLICY" ]] || usage
command -v jq >/dev/null 2>&1 || { printf 'credential verification failed: jq is required\n' >&2; exit 1; }

emit_failure() {
  local reason="$1"
  local version="${2:-unknown}"
  local days="${3:-null}"
  jq -cn --arg reason "$reason" --arg version "$version" --argjson days "$days" \
    '{status:"fail",reason:$reason,version:$version,daysRemaining:$days}'
  printf 'credential verification failed: %s\n' "$reason" >&2
  exit 1
}

jq -e '
  keys == ["capturedAt", "clientId", "cloud", "credentialId", "expiresAt", "identityResourceIds", "issuedAt", "resourceGroupId", "schemaVersion", "subscriptionId", "tenantId", "version"] and
  .schemaVersion == 1 and
  (.credentialId | type == "string" and length > 0) and
  (.cloud | type == "string") and
  (.version | type == "string" and test("^[A-Za-z0-9._-]{1,64}$")) and
  (.clientId | test("^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")) and
  (.tenantId | test("^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")) and
  (.subscriptionId | test("^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")) and
  (.issuedAt | fromdateiso8601 | type == "number") and
  (.expiresAt | fromdateiso8601 | type == "number") and
  (.capturedAt | fromdateiso8601 | type == "number") and
  (.resourceGroupId | type == "string") and
  (.identityResourceIds | (type == "array" and length == 2 and (unique | length) == 2))
' "$METADATA" >/dev/null 2>&1 || emit_failure "metadata-invalid"

jq -e '
  type == "array" and
  all(.[]; keys == ["roleDefinitionName", "scope"] and
    (.roleDefinitionName | type == "string" and length > 0) and
    (.scope | type == "string" and length > 0))
' "$ASSIGNMENTS" >/dev/null 2>&1 || emit_failure "role-assignment-report-invalid"

credential_id="$(jq -r '.credentialId' "$METADATA")"
cloud="$(jq -r '.cloud' "$METADATA")"
version="$(jq -r '.version' "$METADATA")"
subscription_id="$(jq -r '.subscriptionId' "$METADATA")"
resource_group_id="$(jq -r '.resourceGroupId' "$METADATA")"
expected_credential_id="$(jq -r '.credentialId' "$POLICY")"
expected_cloud="$(jq -r '.cloud' "$POLICY")"

[[ "$credential_id" == "$expected_credential_id" && "$cloud" == "$expected_cloud" ]] ||
  emit_failure "credential-binding-drift" "$version"
[[ "$resource_group_id" == "/subscriptions/${subscription_id}/resourceGroups/"* ]] ||
  emit_failure "resource-group-scope-invalid" "$version"

jq -e --arg rg "$resource_group_id" '
  .identityResourceIds | all(
    startswith($rg + "/providers/Microsoft.ManagedIdentity/userAssignedIdentities/")
  )
' "$METADATA" >/dev/null || emit_failure "identity-scope-invalid" "$version"

expected_assignments="$(jq -c '
  [{roleDefinitionName:"Jenkins ACI Provisioner",scope:.resourceGroupId}] +
  [.identityResourceIds[] | {roleDefinitionName:"Managed Identity Operator",scope:.}]
  | sort_by(.roleDefinitionName,.scope)
' "$METADATA")"
actual_assignments="$(jq -c 'if type == "array" then sort_by(.roleDefinitionName,.scope) else null end' "$ASSIGNMENTS" 2>/dev/null || true)"
[[ "$actual_assignments" == "$expected_assignments" ]] || emit_failure "role-assignment-drift" "$version"

jq -e --slurpfile policy "$POLICY" '
  all(.[]; (.roleDefinitionName as $role | ($policy[0].forbiddenRoleNames | index($role)) == null))
' "$ASSIGNMENTS" >/dev/null || emit_failure "forbidden-role-assignment" "$version"

now_epoch="$(jq -nr --arg value "$NOW" '$value | fromdateiso8601' 2>/dev/null)" || emit_failure "now-invalid" "$version"
expiry_epoch="$(jq -r '.expiresAt | fromdateiso8601' "$METADATA")"
days_remaining=$(((expiry_epoch - now_epoch) / 86400))
minimum_days="$(jq -r '.minimumValidDays' "$POLICY")"
if ((days_remaining < minimum_days)); then
  emit_failure "minimum-validity" "$version" "$days_remaining"
fi

jq -cn --arg credentialId "$credential_id" --arg version "$version" --argjson days "$days_remaining" \
  '{status:"pass",credentialId:$credentialId,version:$version,daysRemaining:$days}'
