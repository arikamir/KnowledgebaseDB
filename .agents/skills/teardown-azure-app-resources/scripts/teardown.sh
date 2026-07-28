#!/usr/bin/env bash
set -euo pipefail

mode="${1:-}"
repo_root="${2:-}"
confirmation="${3:-}"

if [[ "$mode" != "plan" && "$mode" != "apply" ]] || [[ -z "$repo_root" ]]; then
  echo "Usage: bash teardown.sh <plan|apply> <repository-root> [confirmation]" >&2
  exit 2
fi

infra="$repo_root/infra/azure"
vars="$infra/terraform.tfvars"
plan="$infra/destroy.tfplan"

for command_name in az terraform; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "[teardown] Required command not found: $command_name" >&2
    exit 1
  }
done

[[ -d "$infra" ]] || { echo "[teardown] Missing $infra" >&2; exit 1; }
[[ -f "$vars" ]] || { echo "[teardown] Missing ignored input file $vars" >&2; exit 1; }

terraform -chdir="$infra" init

state_inventory="$(terraform -chdir="$infra" state list)"
required_workloads=(bff core lifecycle retention lab-revalidation migration evidence-hold-reconciler alb-controller gateway-certificate-dns)
for identity in "${required_workloads[@]}"; do
  grep -Fq "azurerm_user_assigned_identity.workload[\"$identity\"]" <<<"$state_inventory" || {
    echo "[teardown] State parity failure: missing workload identity $identity; recover/import state before destroy" >&2
    exit 1
  }
  grep -Fq "azurerm_federated_identity_credential.workload[\"$identity\"]" <<<"$state_inventory" || {
    echo "[teardown] State parity failure: missing federation $identity; recover/import state before destroy" >&2
    exit 1
  }
done
for address in \
  azurerm_user_assigned_identity.github_actions_publisher \
  azurerm_role_assignment.publisher_exact_acr_push \
  azurerm_role_assignment.kubelet_exact_acr_pull \
  azurerm_role_assignment.publisher_evidence_prefix; do
  grep -Fq "$address" <<<"$state_inventory" || {
    echo "[teardown] State parity failure: missing $address; recover/import state before destroy" >&2
    exit 1
  }
done

environment="$(terraform -chdir="$infra" console -var-file=terraform.tfvars <<< 'var.environment' | tr -d '"[:space:]')"
case "$environment" in
  nonprod|dev|test|stage) ;;
  *) echo "[teardown] Refusing environment: $environment" >&2; exit 1 ;;
esac

configured_subscription="$(terraform -chdir="$infra" console -var-file=terraform.tfvars <<< 'var.subscription_id' | tr -d '"[:space:]')"
active_subscription="$(az account show --query id -o tsv)"
if [[ "$configured_subscription" != "$active_subscription" ]]; then
  echo "[teardown] Subscription mismatch: Terraform=$configured_subscription AzureCLI=$active_subscription" >&2
  exit 1
fi

if [[ "$mode" == "plan" ]]; then
  terraform -chdir="$infra" plan -destroy -var-file=terraform.tfvars -out=destroy.tfplan
  resource_group="$(terraform -chdir="$infra" output -raw resource_group_name)"
  echo "[teardown] Destroy plan: $plan"
  echo "[teardown] Subscription: $active_subscription"
  echo "[teardown] Environment: $environment"
  echo "[teardown] Resource group: $resource_group"
  echo "[teardown] Confirmation required: DESTROY-$environment-$resource_group"
  exit 0
fi

[[ -f "$plan" ]] || { echo "[teardown] Missing reviewed plan $plan; run plan first" >&2; exit 1; }
resource_group="$(terraform -chdir="$infra" output -raw resource_group_name)"
expected="DESTROY-$environment-$resource_group"
[[ "$confirmation" == "$expected" ]] || {
  echo "[teardown] Refusing apply. Required confirmation: $expected" >&2
  exit 1
}

terraform -chdir="$infra" apply "$plan"
remaining="$(terraform -chdir="$infra" state list)"
[[ -z "$remaining" ]] || { echo "[teardown] Managed resources remain after destroy" >&2; printf '%s\n' "$remaining" >&2; exit 1; }

if az group show --name "$resource_group" >/dev/null 2>&1; then
  echo "[teardown] Warning: resource group still exists: $resource_group" >&2
  exit 1
fi

echo "[teardown] Teardown verified for $resource_group"
