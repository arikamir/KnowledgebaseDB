---
name: provision-azure-app-resources
description: Automatically create, validate, and optionally provision the Azure infrastructure required to deploy this repository's containerized application to non-production AKS. Must be used whenever application deployment is requested and the required Azure infrastructure is missing, incomplete, or unverified, even if the user only asks to deploy the application. Also use for explicit AKS, ACR, Terraform, Bicep, Azure prerequisite, or AKS-to-ACR requests. Uses deterministic project defaults for resource group, registry, cluster, managed identity/RBAC, monitoring, and outputs so repeatable infrastructure setup does not consume unnecessary planning effort.
---

# Provision Azure Application Resources

Create a repeatable, least-privilege Azure foundation for the containerized application described in `specs/002-dockerize-deploy/`.

## Trigger and fast path

When application deployment is requested, check for `infra/azure/` and verified outputs before doing deployment work. If the infrastructure is absent, incomplete, or its existence cannot be verified, run this skill first without asking the user to invoke it separately.

Use the deterministic Terraform fast path unless existing IaC or an explicit user request requires Bicep:

1. Run `bash scripts/bootstrap.sh <repository-root>` from the skill directory.
2. Reuse existing `infra/azure` files; never overwrite them silently.
3. Use `nonprod`, `israelcentral`, `Standard_B2s`, one node, and prefix `devopscareer` as project defaults.
4. Read the active Azure subscription with `az account show`. Ask only if no authenticated subscription exists or the user must choose among subscriptions.
5. Derive names from the prefix and environment. Resolve only global ACR-name collisions by adding a short deterministic suffix from the subscription ID.
6. Run formatting, initialization, validation, and plan.
7. If the original request said deploy, provision, create, or apply, continue through apply after presenting the plan and obtaining any required execution approval. Then resume the application deployment.

Do not spend a separate reasoning phase reconsidering the standard topology unless repository constraints or explicit requirements conflict with these defaults.

## Read project context

1. Read `references/project-profile.md`.
2. Read `specs/002-dockerize-deploy/plan.md`, `quickstart.md`, and `contracts/deployment-contract.md` when present.
3. Inspect existing infrastructure files before generating anything. Extend the established IaC tool and layout when one exists.
4. Inspect `deploy/k8s/` to keep infrastructure outputs compatible with the Kubernetes manifests.

## Establish exceptional inputs

Discover values from the repository, Azure CLI context, and existing IaC before asking the user. Obtain only missing values that materially affect the design:

- subscription and tenant context;
- Azure region only when the default is unsuitable;
- environment name, defaulting to `nonprod` for this project;
- globally unique ACR name;
- AKS and resource-group names;
- IaC tool only when explicitly requested or already established;
- network constraints, private-cluster requirements, and approved Kubernetes version;
- whether deployment is requested or only file generation.

Never guess a subscription, tenant, globally unique resource name, production topology, or destructive migration choice. Use `az account show` and availability checks when authenticated. Do not change the active subscription without explicit approval.

## Select the implementation

Prefer the repository's existing IaC tool. If none exists, use the bundled Terraform template through `bash scripts/bootstrap.sh <repository-root>`. Place files under `infra/azure/` and separate reusable configuration from environment values.

Create the smallest foundation that satisfies the deployment contract:

- resource group;
- Azure Container Registry with admin credentials disabled;
- AKS using managed identity and Azure RBAC-compatible access;
- `AcrPull` assignment from the kubelet identity to ACR;
- Log Analytics/Container Insights when required by the selected AKS configuration;
- managed AKS application routing with an external NGINX ingress controller;
- configurable node size/count, tags, region, Kubernetes version, and naming inputs;
- outputs for resource group, cluster name, ACR login server/resource ID, credential-fetch commands, and browser URL lookup.

Do not add a database, public ingress, DNS, Key Vault, production high availability, or advanced networking unless requirements call for it. The current application keeps `DATABASE_URL` external and the initial target is non-production.

## Generate safe infrastructure

- Pin provider/module versions to compatible ranges and commit the dependency lock file when the tool creates one.
- Use managed identities instead of stored service-principal credentials.
- Keep secrets and kubeconfig content out of Terraform/Bicep outputs, variable files, logs, and Git.
- Add validations for allowed environments and required naming constraints.
- Apply consistent tags such as application, environment, and managed-by.
- Avoid hard-coded subscription IDs, tenant IDs, personal object IDs, and mutable image tags.
- Provide an example variables file containing placeholders only; ignore real variable files and state.
- Document initialization, validation, plan/what-if, apply, credential retrieval, image push, and teardown commands in the project deployment documentation.

## Validate before deployment

Run all locally available checks appropriate to the chosen tool:

### Terraform

1. Run `terraform fmt -check -recursive infra/azure`.
2. Run `terraform -chdir=infra/azure init -backend=false` when provider access is available.
3. Run `terraform -chdir=infra/azure validate`.
4. Run a plan with an explicit variable file only when authenticated inputs are available.

### Bicep

1. Run `az bicep build --file infra/azure/main.bicep`.
2. Run the appropriate subscription or resource-group `az deployment ... what-if` when authenticated inputs are available.

Also validate rendered Kubernetes manifests with `kubectl kustomize deploy/k8s/overlays/aks-nonprod` when `kubectl` is available.

Report skipped checks and the concrete prerequisite needed to run each one.

## Deploy only with authorization

Treat file generation, formatting, validation, and read-only Azure discovery as authorized by a request to create the skill or prepare infrastructure. Treat `terraform apply`, `az deployment ... create`, role assignment changes, cluster credential writes, and resource deletion as external mutations.

Run deployment only when the user explicitly asks to provision/deploy/apply the Azure resources. Before applying:

1. Show the target subscription, tenant, region, resource group, resources, and estimated plan/what-if impact.
2. Check relevant Azure quotas and provider registrations.
3. Request approval for the exact mutating command when the execution environment requires it.
4. Never auto-approve destructive replacements without calling them out.

After deployment, verify ACR reachability, AKS provisioning state, node readiness, and the kubelet identity's `AcrPull` assignment. After application rollout, run `bash .agents/skills/provision-azure-app-resources/scripts/get-application-url.sh` and report its URL as the browser-accessible application endpoint. Do not claim the application is accessible until that URL responds successfully on `/health`.

## Handoff

Summarize:

- files created or changed;
- Azure resources planned or provisioned;
- validation results;
- unresolved inputs or cost/security decisions;
- exact next command for provisioning or application deployment.
