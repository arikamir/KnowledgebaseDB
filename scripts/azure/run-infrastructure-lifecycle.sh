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

for command_name in az jq terraform; do
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

mkdir -p "$artifact_directory"
az account show --output none

# This proves both data-plane authorization and private-network reachability.
# A GitHub-hosted runner cannot pass this preflight for the formal vault.
az keyvault key list \
  --vault-name "$KEY_VAULT_NAME" \
  --maxresults 1 \
  --query 'length(@)' \
  --output tsv >/dev/null

terraform -chdir="$terraform_directory" fmt -check -recursive
terraform -chdir="$terraform_directory" init -reconfigure \
  -backend-config="resource_group_name=$TF_BACKEND_RESOURCE_GROUP" \
  -backend-config="storage_account_name=$TF_BACKEND_STORAGE_ACCOUNT" \
  -backend-config="container_name=$TF_BACKEND_CONTAINER" \
  -backend-config="key=$TF_BACKEND_KEY"
terraform -chdir="$terraform_directory" validate
terraform -chdir="$terraform_directory" plan -out="$plan_path"

jq -n \
  --arg actor "${USER:-private-platform-runner}" \
  --arg revision "$(git -C "$repository_root" rev-parse HEAD)" \
  --arg action "$action" \
  '{workflow:"private-platform-lifecycle",actor:$actor,sourceRevision:$revision,environment:"infrastructure",changedResourceSet:["infra/azure"],result:($action + "-prepared"),evidenceLinks:["artifact://infrastructure/platform.tfplan"]}' \
  > "$artifact_directory/scope.json"

if [[ "$action" == "apply" ]]; then
  if [[ "${INFRASTRUCTURE_APPLY_APPROVED:-}" != "true" ]]; then
    echo "apply requires INFRASTRUCTURE_APPLY_APPROVED=true after plan review" >&2
    exit 1
  fi
  terraform -chdir="$terraform_directory" apply "$plan_path"
fi

echo "infrastructure $action completed from the private platform path"
