# Teardown Policy

## Expected managed scope

The companion provisioning skill creates these resources in one non-production resource group:

- Azure Kubernetes Service cluster
- Azure Container Registry
- Log Analytics workspace
- nine workload identities and one-to-one federated credentials
- the GitHub Actions publisher identity and exact ACR/evidence assignments
- AKS kubelet exact-ACR `AcrPull` role assignment (never a federated application identity)
- AGC/private-core/Redis/PostgreSQL/Key Vault/evidence resources declared by the feature-003 state
- Resource group

Terraform state, not this list, is the deletion authority. Stop if the destroy plan includes resources outside the expected application scope.
Stop when any required declared identity is absent from state; reconcile/import state first so teardown cannot orphan a principal or role assignment.

## Allowed environments

Only `nonprod`, `dev`, `test`, and `stage` may be destroyed by this skill. Production teardown requires a separate, purpose-built process and approval policy.

## Required evidence

Before apply, capture:

- active Azure subscription ID and name;
- Terraform-configured subscription ID;
- Terraform workspace;
- environment and resource-group output;
- destroy plan summary;
- exact confirmation phrase.

After apply, capture Terraform's result and read-only Azure verification. Do not commit credentials, state, plan files, kubeconfig, or exported secrets.
