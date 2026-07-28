#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 plan|apply" >&2
  exit 2
}

action="${1:-}"
case "$action" in
  plan|apply) ;;
  *) usage ;;
esac

for command_name in az jq shasum terraform; do
  command -v "$command_name" >/dev/null || {
    echo "required command not found: $command_name" >&2
    exit 1
  }
done

required_variables=(
  TF_BACKEND_RESOURCE_GROUP
  TF_BACKEND_STORAGE_ACCOUNT
  TF_BACKEND_CONTAINER
  TF_BACKEND_KEY
  TF_VAR_github_repository
  TF_VAR_github_repository_owner_id
  TF_VAR_github_repository_id
  KEY_VAULT_NAME
)
for variable_name in "${required_variables[@]}"; do
  if [[ -z "${!variable_name:-}" ]]; then
    echo "required environment variable is unset: $variable_name" >&2
    exit 1
  fi
done

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
terraform_directory="$repository_root/infra/azure"
artifact_directory="${INFRASTRUCTURE_ARTIFACT_DIRECTORY:-$repository_root/artifacts/infrastructure}"
plan_path="$artifact_directory/platform.tfplan"
receipt_path="$artifact_directory/platform.tfplan.receipt.json"

mkdir -p "$artifact_directory"
az account show --output none

# For an established environment this proves both data-plane authorization and
# private-network reachability. Initial creation has no vault to probe and
# therefore requires a separate, explicit bootstrap approval.
if az keyvault show --name "$KEY_VAULT_NAME" --query id --output tsv >/dev/null 2>&1; then
  az keyvault key list \
    --vault-name "$KEY_VAULT_NAME" \
    --maxresults 1 \
    --query 'length(@)' \
    --output tsv >/dev/null
elif [[ "${INFRASTRUCTURE_BOOTSTRAP_APPROVED:-}" != "true" ]]; then
  echo "vault is absent or unreadable; initial creation requires INFRASTRUCTURE_BOOTSTRAP_APPROVED=true" >&2
  exit 1
fi

terraform -chdir="$terraform_directory" fmt -check -recursive
terraform -chdir="$terraform_directory" init -reconfigure \
  -backend-config="resource_group_name=$TF_BACKEND_RESOURCE_GROUP" \
  -backend-config="storage_account_name=$TF_BACKEND_STORAGE_ACCOUNT" \
  -backend-config="container_name=$TF_BACKEND_CONTAINER" \
  -backend-config="key=$TF_BACKEND_KEY"
terraform -chdir="$terraform_directory" validate

current_revision="$(git -C "$repository_root" rev-parse HEAD)"

if [[ "$action" == "plan" ]]; then
  terraform -chdir="$terraform_directory" plan -out="$plan_path"
  plan_sha256="$(shasum -a 256 "$plan_path" | awk '{print $1}')"
  jq -n \
    --arg revision "$current_revision" \
    --arg planSha256 "$plan_sha256" \
    --arg repository "$TF_VAR_github_repository" \
    --arg ownerId "$TF_VAR_github_repository_owner_id" \
    --arg repositoryId "$TF_VAR_github_repository_id" \
    '{schemaVersion:1,sourceRevision:$revision,planSha256:$planSha256,githubTrust:{repository:$repository,ownerId:$ownerId,repositoryId:$repositoryId}}' \
    > "$receipt_path"
else
  if [[ "${INFRASTRUCTURE_APPLY_APPROVED:-}" != "true" ]]; then
    echo "apply requires INFRASTRUCTURE_APPLY_APPROVED=true after plan review" >&2
    exit 1
  fi
  [[ -f "$plan_path" && -f "$receipt_path" ]] || {
    echo "apply requires the reviewed platform.tfplan and receipt" >&2
    exit 1
  }
  expected_sha256="$(jq -er '.planSha256' "$receipt_path")"
  actual_sha256="$(shasum -a 256 "$plan_path" | awk '{print $1}')"
  [[ "$actual_sha256" == "$expected_sha256" ]] || {
    echo "reviewed plan checksum does not match its receipt" >&2
    exit 1
  }
  jq -e \
    --arg revision "$current_revision" \
    --arg repository "$TF_VAR_github_repository" \
    --arg ownerId "$TF_VAR_github_repository_owner_id" \
    --arg repositoryId "$TF_VAR_github_repository_id" \
    '.sourceRevision == $revision and .githubTrust == {repository:$repository,ownerId:$ownerId,repositoryId:$repositoryId}' \
    "$receipt_path" >/dev/null || {
      echo "reviewed plan receipt does not match the current revision and trust tuple" >&2
      exit 1
    }
  terraform -chdir="$terraform_directory" apply "$plan_path"
fi

jq -n \
  --arg actor "${USER:-private-platform-runner}" \
  --arg revision "$current_revision" \
  --arg action "$action" \
  '{workflow:"private-platform-lifecycle",actor:$actor,sourceRevision:$revision,environment:"infrastructure",changedResourceSet:["infra/azure"],result:($action + "-completed"),evidenceLinks:["artifact://infrastructure/platform.tfplan","artifact://infrastructure/platform.tfplan.receipt.json"]}' \
  > "$artifact_directory/scope.json"

echo "infrastructure $action completed from the private platform path"
