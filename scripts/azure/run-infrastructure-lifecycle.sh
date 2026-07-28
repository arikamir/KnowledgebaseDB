#!/usr/bin/env bash
set -euo pipefail
umask 077

usage() {
  echo "usage: $0 plan|apply" >&2
  exit 2
}

action="${1:-}"
case "$action" in
  plan|apply) ;;
  *) usage ;;
esac

for command_name in id mktemp stat; do
  command -v "$command_name" >/dev/null || {
    echo "required command not found: $command_name" >&2
    exit 1
  }
done

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
terraform_directory="$repository_root/infra/azure"
if [[ -n "${INFRASTRUCTURE_ARTIFACT_DIRECTORY:-}" ]]; then
  artifact_directory="$INFRASTRUCTURE_ARTIFACT_DIRECTORY"
  if [[ -L "$artifact_directory" ]]; then
    echo "infrastructure artifact directory must not be a symbolic link" >&2
    exit 1
  fi
  mkdir -m 700 -p "$artifact_directory"
else
  if [[ "$action" == "apply" ]]; then
    echo "apply requires INFRASTRUCTURE_ARTIFACT_DIRECTORY to identify the reviewed plan directory" >&2
    exit 1
  fi
  artifact_directory="$(mktemp -d "${TMPDIR:-/tmp}/knowledgebasedb-infrastructure.XXXXXX")"
fi
artifact_directory="$(cd "$artifact_directory" && pwd -P)"
artifact_directory_identity="$(
  stat -f '%u:%Lp' "$artifact_directory" 2>/dev/null ||
    stat -c '%u:%a' "$artifact_directory"
)"
if [[ "$artifact_directory_identity" != "$(id -u):700" ]]; then
  echo "infrastructure artifact directory must be owned by the current user with mode 0700" >&2
  exit 1
fi
plan_path="$artifact_directory/platform.tfplan"
receipt_path="$artifact_directory/platform.tfplan.receipt.json"
scope_path="$artifact_directory/scope.json"
temporary_plan=""
temporary_receipt=""
current_revision=""
target_key_vault_id=""
target_key_vault_name=""
planned_github_trust=""
expected_publisher_subject=""

write_scope() {
  local result="$1"
  if command -v jq >/dev/null; then
    jq -n \
      --arg actor "${USER:-private-platform-runner}" \
      --arg revision "$current_revision" \
      --arg result "$result" \
      --arg action "$action" \
      --arg backendTenantId "${TF_BACKEND_TENANT_ID:-}" \
      --arg backendSubscriptionId "${TF_BACKEND_SUBSCRIPTION_ID:-}" \
      --arg backendResourceGroup "${TF_BACKEND_RESOURCE_GROUP:-}" \
      --arg backendStorageAccount "${TF_BACKEND_STORAGE_ACCOUNT:-}" \
      --arg backendContainer "${TF_BACKEND_CONTAINER:-}" \
      --arg backendKey "${TF_BACKEND_KEY:-}" \
      --arg keyVaultId "$target_key_vault_id" \
      --arg keyVaultName "$target_key_vault_name" \
      --arg repository "${TF_VAR_github_repository:-}" \
      --arg ownerId "${TF_VAR_github_repository_owner_id:-}" \
      --arg repositoryId "${TF_VAR_github_repository_id:-}" \
      --arg githubEnvironment "${TF_VAR_github_actions_environment:-}" \
      --arg publisherSubject "$expected_publisher_subject" \
      '{workflow:"private-platform-lifecycle",actor:$actor,sourceRevision:$revision,environment:"infrastructure",changedResourceSet:["infra/azure"],result:$result,inputs:{action:$action,backend:{tenantId:$backendTenantId,subscriptionId:$backendSubscriptionId,resourceGroup:$backendResourceGroup,storageAccount:$backendStorageAccount,container:$backendContainer,key:$backendKey},keyVault:{id:$keyVaultId,name:$keyVaultName},githubTrust:{repository:$repository,ownerId:$ownerId,repositoryId:$repositoryId,environment:$githubEnvironment,subject:$publisherSubject}},evidenceLinks:["artifact://infrastructure/scope.json"]}' \
      > "$scope_path"
  else
    printf '{"workflow":"private-platform-lifecycle","result":"%s"}\n' "$result" > "$scope_path"
  fi
}

on_exit() {
  local status="$?"
  [[ -z "$temporary_plan" ]] || rm -f "$temporary_plan"
  [[ -z "$temporary_receipt" ]] || rm -f "$temporary_receipt"
  if (( status != 0 )); then
    write_scope "$action-failed" || true
  fi
}
trap on_exit EXIT

rm -f "$scope_path"

case "$artifact_directory/" in
  "$repository_root/"*)
    echo "infrastructure artifacts must be stored outside the repository worktree" >&2
    exit 1
    ;;
esac

for command_name in az git jq shasum terraform; do
  command -v "$command_name" >/dev/null || {
    echo "required command not found: $command_name" >&2
    exit 1
  }
done

if ! current_revision="$(git -C "$repository_root" rev-parse --verify 'HEAD^{commit}' 2>/dev/null)"; then
  echo "infrastructure lifecycle requires a resolvable Git source revision" >&2
  exit 1
fi
if [[ ! "$current_revision" =~ ^[0-9a-f]{40}$ ]]; then
  echo "infrastructure lifecycle requires a canonical 40-character Git source revision" >&2
  exit 1
fi
write_scope "$action-started"

required_variables=(
  TF_BACKEND_TENANT_ID
  TF_BACKEND_SUBSCRIPTION_ID
  TF_BACKEND_RESOURCE_GROUP
  TF_BACKEND_STORAGE_ACCOUNT
  TF_BACKEND_CONTAINER
  TF_BACKEND_KEY
  TF_VAR_github_repository
  TF_VAR_github_repository_owner_id
  TF_VAR_github_repository_id
  TF_VAR_github_actions_environment
)
for variable_name in "${required_variables[@]}"; do
  if [[ -z "${!variable_name:-}" ]]; then
    echo "required environment variable is unset: $variable_name" >&2
    exit 1
  fi
done

github_repository_owner="${TF_VAR_github_repository%%/*}"
github_repository_name="${TF_VAR_github_repository#*/}"
if [[ -z "$github_repository_owner" || -z "$github_repository_name" || "$github_repository_name" == */* ]]; then
  echo "TF_VAR_github_repository must contain exactly one owner/name pair" >&2
  exit 1
fi
expected_publisher_subject="repo:${github_repository_owner}/${github_repository_name}:environment:${TF_VAR_github_actions_environment}-publisher"

terraform_source_paths=(
  infra/azure
  config/operational-alert-profile-v1.yaml
  config/pilot-availability-profile-v1.yaml
)
if [[ -n "$(git -C "$repository_root" status --porcelain --untracked-files=all -- "${terraform_source_paths[@]}")" ]]; then
  echo "Terraform source inputs must have no staged, unstaged, or untracked changes" >&2
  exit 1
fi

if [[ "$action" == "plan" ]]; then
  rm -f "$plan_path" "$receipt_path"
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
    --arg backendTenantId "$TF_BACKEND_TENANT_ID" \
    --arg backendSubscriptionId "$TF_BACKEND_SUBSCRIPTION_ID" \
    --arg backendResourceGroup "$TF_BACKEND_RESOURCE_GROUP" \
    --arg backendStorageAccount "$TF_BACKEND_STORAGE_ACCOUNT" \
    --arg backendContainer "$TF_BACKEND_CONTAINER" \
    --arg backendKey "$TF_BACKEND_KEY" \
    --arg repository "$TF_VAR_github_repository" \
    --arg ownerId "$TF_VAR_github_repository_owner_id" \
    --arg repositoryId "$TF_VAR_github_repository_id" \
    --arg githubEnvironment "$TF_VAR_github_actions_environment" \
    --arg publisherSubject "$expected_publisher_subject" \
    '.schemaVersion == 3
      and .sourceRevision == $revision
      and .backend == {
        tenantId:$backendTenantId,
        subscriptionId:$backendSubscriptionId,
        resourceGroup:$backendResourceGroup,
        storageAccount:$backendStorageAccount,
        container:$backendContainer,
        key:$backendKey
      }
      and .githubTrust == {
        repository:$repository,
        ownerId:$ownerId,
        repositoryId:$repositoryId,
        environment:$githubEnvironment,
        subject:$publisherSubject,
        issuer:"https://token.actions.githubusercontent.com",
        audience:"api://AzureADTokenExchange"
      }' \
    "$receipt_path" >/dev/null || {
      echo "reviewed plan receipt does not match the current revision, backend, and trust tuple" >&2
      exit 1
    }
fi
active_subscription_id="$(az account show --query id --output tsv)"
active_tenant_id="$(az account show --query tenantId --output tsv)"
if [[ "$active_subscription_id" != "$TF_BACKEND_SUBSCRIPTION_ID" || "$active_tenant_id" != "$TF_BACKEND_TENANT_ID" ]]; then
  echo "active Azure CLI tenant/subscription does not match the required backend account" >&2
  exit 1
fi

terraform -chdir="$terraform_directory" fmt -check -recursive
terraform -chdir="$terraform_directory" init -reconfigure \
  -backend-config="tenant_id=$TF_BACKEND_TENANT_ID" \
  -backend-config="subscription_id=$TF_BACKEND_SUBSCRIPTION_ID" \
  -backend-config="resource_group_name=$TF_BACKEND_RESOURCE_GROUP" \
  -backend-config="storage_account_name=$TF_BACKEND_STORAGE_ACCOUNT" \
  -backend-config="container_name=$TF_BACKEND_CONTAINER" \
  -backend-config="key=$TF_BACKEND_KEY"
terraform -chdir="$terraform_directory" validate

verify_planned_key_vault() {
  local candidate_plan="$1"
  local target_key_vault
  local target_subscription_id
  local target_resource_group
  local actual_key_vault_id
  local normalized_actual_key_vault_id
  local normalized_target_key_vault_id
  local vault_inventory
  target_key_vault="$(
    terraform -chdir="$terraform_directory" show -json "$candidate_plan" |
      jq -cer '.planned_values.outputs.key_vault_target.value
        | select(
            (.name | type == "string" and test("^[A-Za-z0-9-]{3,24}$"))
            and (.resource_group_name | type == "string" and length > 0)
            and (.subscription_id | type == "string" and test("^[0-9a-fA-F-]{36}$"))
          )'
  )"
  target_key_vault_name="$(jq -r '.name' <<<"$target_key_vault")"
  target_resource_group="$(jq -r '.resource_group_name' <<<"$target_key_vault")"
  target_subscription_id="$(jq -r '.subscription_id' <<<"$target_key_vault")"
  target_key_vault_id="/subscriptions/$target_subscription_id/resourceGroups/$target_resource_group/providers/Microsoft.KeyVault/vaults/$target_key_vault_name"

  # The plan output binds this probe to the vault Terraform will manage. For
  # an established environment this proves data-plane authorization and
  # private-network reachability. Initial creation requires separate approval.
  actual_key_vault_id=""
  if actual_key_vault_id="$(
    az keyvault show \
      --name "$target_key_vault_name" \
      --subscription "$target_subscription_id" \
      --query id \
      --output tsv 2>/dev/null
  )"; then
    normalized_actual_key_vault_id="$(tr '[:upper:]' '[:lower:]' <<<"$actual_key_vault_id")"
    normalized_target_key_vault_id="$(tr '[:upper:]' '[:lower:]' <<<"$target_key_vault_id")"
    if [[ "$normalized_actual_key_vault_id" != "$normalized_target_key_vault_id" ]]; then
      echo "planned vault identity does not match the Azure resource" >&2
      exit 1
    fi
    az keyvault key list \
      --vault-name "$target_key_vault_name" \
      --subscription "$target_subscription_id" \
      --maxresults 1 \
      --query 'length(@)' \
      --output tsv >/dev/null
  else
    vault_inventory="$(az keyvault list --subscription "$target_subscription_id" --output json)"
    if jq -e --arg targetId "$target_key_vault_id" \
      'any(.[]; (.id | ascii_downcase) == ($targetId | ascii_downcase))' \
      <<<"$vault_inventory" >/dev/null; then
      echo "planned vault exists but its management metadata is unreadable" >&2
      exit 1
    fi
    if [[ "${INFRASTRUCTURE_BOOTSTRAP_APPROVED:-}" != "true" ]]; then
      echo "planned vault is absent; initial creation requires INFRASTRUCTURE_BOOTSTRAP_APPROVED=true" >&2
      exit 1
    fi
  fi
}

verify_planned_github_trust() {
  local candidate_plan="$1"
  planned_github_trust="$(
    terraform -chdir="$terraform_directory" show -json "$candidate_plan" |
      jq -cer '.planned_values.outputs.github_actions_publisher_trust.value
        | select(
            (.repository | type == "string" and length > 0)
            and (.owner_id | type == "string" and length > 0)
            and (.repository_id | type == "string" and length > 0)
            and (.environment | type == "string" and length > 0)
            and (.subject | type == "string" and length > 0)
            and .issuer == "https://token.actions.githubusercontent.com"
            and .audience == "api://AzureADTokenExchange"
          )
        | {
            repository,
            ownerId:.owner_id,
            repositoryId:.repository_id,
            environment,
            subject,
            issuer,
            audience
          }'
  )"
  jq -e \
    --arg repository "$TF_VAR_github_repository" \
    --arg ownerId "$TF_VAR_github_repository_owner_id" \
    --arg repositoryId "$TF_VAR_github_repository_id" \
    --arg githubEnvironment "$TF_VAR_github_actions_environment" \
    --arg publisherSubject "$expected_publisher_subject" \
    '. == {
      repository:$repository,
      ownerId:$ownerId,
      repositoryId:$repositoryId,
      environment:$githubEnvironment,
      subject:$publisherSubject,
      issuer:"https://token.actions.githubusercontent.com",
      audience:"api://AzureADTokenExchange"
    }' <<<"$planned_github_trust" >/dev/null || {
      echo "effective planned GitHub publisher trust does not match the approved trust tuple" >&2
      exit 1
    }
}

if [[ "$action" == "plan" ]]; then
  temporary_plan="$(mktemp "$artifact_directory/.platform.tfplan.XXXXXX")"
  temporary_receipt="$(mktemp "$artifact_directory/.platform.tfplan.receipt.XXXXXX")"
  terraform -chdir="$terraform_directory" plan -out="$temporary_plan"
  verify_planned_key_vault "$temporary_plan"
  verify_planned_github_trust "$temporary_plan"
  plan_sha256="$(shasum -a 256 "$temporary_plan" | awk '{print $1}')"
  jq -n \
    --arg revision "$current_revision" \
    --arg planSha256 "$plan_sha256" \
    --arg backendTenantId "$TF_BACKEND_TENANT_ID" \
    --arg backendSubscriptionId "$TF_BACKEND_SUBSCRIPTION_ID" \
    --arg backendResourceGroup "$TF_BACKEND_RESOURCE_GROUP" \
    --arg backendStorageAccount "$TF_BACKEND_STORAGE_ACCOUNT" \
    --arg backendContainer "$TF_BACKEND_CONTAINER" \
    --arg backendKey "$TF_BACKEND_KEY" \
    --arg keyVaultId "$target_key_vault_id" \
    --argjson githubTrust "$planned_github_trust" \
    '{schemaVersion:3,sourceRevision:$revision,planSha256:$planSha256,backend:{tenantId:$backendTenantId,subscriptionId:$backendSubscriptionId,resourceGroup:$backendResourceGroup,storageAccount:$backendStorageAccount,container:$backendContainer,key:$backendKey},keyVaultId:$keyVaultId,githubTrust:$githubTrust}' \
    > "$temporary_receipt"
  mv "$temporary_plan" "$plan_path"
  temporary_plan=""
  mv "$temporary_receipt" "$receipt_path"
  temporary_receipt=""
else
  verify_planned_key_vault "$plan_path"
  verify_planned_github_trust "$plan_path"
  jq -e --arg keyVaultId "$target_key_vault_id" '.keyVaultId == $keyVaultId' "$receipt_path" >/dev/null || {
    echo "reviewed plan vault does not match its receipt" >&2
    exit 1
  }
  jq -e --argjson githubTrust "$planned_github_trust" '.githubTrust == $githubTrust' "$receipt_path" >/dev/null || {
    echo "effective planned GitHub publisher trust does not match its receipt" >&2
    exit 1
  }
  terraform -chdir="$terraform_directory" apply "$plan_path"
fi

write_scope "$action-completed"

echo "infrastructure artifact directory: $artifact_directory"
echo "infrastructure $action completed from the private platform path"
