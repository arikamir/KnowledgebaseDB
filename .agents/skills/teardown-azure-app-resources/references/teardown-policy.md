# Teardown Policy

## Expected managed scope

The companion provisioning skill creates these resources in one non-production resource group:

- Azure Kubernetes Service cluster
- Azure Container Registry
- Log Analytics workspace
- AKS kubelet `AcrPull` role assignment
- Resource group

Terraform state, not this list, is the deletion authority. Stop if the destroy plan includes resources outside the expected application scope.

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

