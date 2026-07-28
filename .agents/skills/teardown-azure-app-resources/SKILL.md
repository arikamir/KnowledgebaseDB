---
name: teardown-azure-app-resources
description: Safely plan, execute, and verify teardown of this application's Terraform-managed non-production Azure infrastructure. Must be used whenever asked to tear down, destroy, remove, decommission, clean up, or delete the AKS/ACR Azure deployment environment created for this repository. Uses the Terraform state in infra/azure, blocks production environments and subscription mismatches, requires a reviewed destroy plan and exact confirmation, and never deletes unrelated resource groups or resources.
---

# Teardown Azure Application Resources

Remove only the Azure resources managed by this repository's Terraform state. Treat every teardown as destructive and irreversible for AKS workloads, ACR images, logs, and ephemeral cluster data.

## Use the deterministic workflow

1. Read `references/teardown-policy.md`.
2. Locate the repository root and confirm `infra/azure` exists.
3. Run `bash scripts/teardown.sh plan <repository-root>` from this skill directory.
4. Present the destroy-plan summary, active subscription, resource group, and irreversible data-loss warning.
5. Run apply only when the user explicitly requested teardown and approves the exact destructive command/confirmation phrase.
6. Run `bash scripts/teardown.sh apply <repository-root> <confirmation>`.
7. Verify that Terraform reports no managed resources and that the target resource group no longer exists or is empty as expected.

Do not redesign the teardown, manually enumerate normal resources, or use `az group delete` when valid Terraform state exists. The script is the standard path.

## Preconditions

Require all of the following:

- Azure CLI is authenticated.
- Terraform is installed.
- `infra/azure/terraform.tfvars` exists outside Git and selects a non-production environment.
- Terraform state is accessible and initialized.
- The active Azure subscription matches the Terraform subscription input.
- The environment is one of `nonprod`, `dev`, `test`, or `stage`.
- No production environment or shared-resource dependency appears in the destroy plan.

Stop when state is missing or inconsistent. Never infer that an Azure resource group is safe to delete merely from its name. State recovery/import is a separate, explicitly approved task.

## Protect data and shared dependencies

Before apply, call out that teardown deletes:

- the AKS cluster, AGC/private-core/data/evidence resources, and its workloads;
- images stored only in the application ACR;
- the Log Analytics workspace and retained logs;
- all nine workload identities/federated credentials, the GitHub Actions publisher identity, kubelet exact-ACR pull, their exact role assignments, and the application resource group managed by state.

The destroy plan must include all identities declared in `infra/azure/github-actions-identities.tf`. Missing identity state is an import/state-recovery blocker, not permission to leave an orphan. UI and validator must remain absent because they are intentionally identityless.

Check the plan for resources outside the expected application resource group and stop if any appear. Ask whether ACR images, Kubernetes manifests/state, logs, or diagnostic data require export. Do not create backups unless requested.

Do not remove local Terraform state, lock files, IaC source, Kubernetes manifests, or documentation after teardown. Those artifacts are needed for auditability and future recreation.

## Handle failures

- If plan creation fails, report the exact prerequisite or state error; do not fall back to broad Azure deletion.
- If apply partially fails, rerun `terraform plan -destroy` and report remaining managed resources.
- If Azure locks or policies block deletion, identify them read-only. Remove locks or change policy only with explicit authorization.
- If the subscription differs, stop and require the user to select the intended subscription; do not call `az account set` automatically.
- Never use `-auto-approve` without the script's exact confirmation guard.

## Handoff

Report the subscription, environment, resource group, plan path, destroy result, verification result, retained local artifacts, and any remaining billable resources.
