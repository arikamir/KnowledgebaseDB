---
name: run-gitops-tests
description: Run this repository's Argo CD and GitOps validation from a developer workstation. Use when verifying release declarations, ApplicationSet rendering, platform readiness, non-production sync/rollback behavior, drift handling, or Entra operator permissions without deploying infrastructure or requiring a runner inside AKS.
---

# Run GitOps Tests

Run the repository's application-delivery checks from the user's workstation.
GitHub Actions remains responsible for building and pushing images; Argo CD
remains responsible for reconciling Git desired state. This skill never runs
Terraform, `kubectl apply`, an Argo CD sync command, or an Azure provisioning
operation.

## Workflow

### 1. Resolve the repository and mode

Run from the repository root or resolve it from the bundled runner:

```bash
bash .agents/skills/run-gitops-tests/scripts/run-gitops-tests.sh
```

The default mode is identityless/static. Use `--live` only when the user asks
for cluster checks or explicitly authorizes them. Live checks require the
workstation's current kubeconfig context to reach the AKS API; they do not
require a GitHub or AKS-hosted runner.

### 2. Run static checks first

The runner validates the nonprod release declaration and release-bundle
contract, renders both Argo CD and application-only Kustomize trees, produces a
static readiness record, and runs the feature contract tests. Static rendering
does not contact Azure or mutate Kubernetes.

### 3. Prepare a live workstation session

Refresh the local context when needed:

```bash
az login
az account set --subscription <subscription>
az aks get-credentials \
  --resource-group rg-devopscareeruae-nonprod \
  --name aks-devopscareeruae-nonprod \
  --overwrite-existing
kubectl config current-context
kubectl get nodes
```

If the API hostname does not resolve, stop. Diagnose public/private API access,
VPN/VNet reachability, and private DNS before retrying. Do not work around a
private endpoint by adding credentials to the repository.

### 4. Run live checks explicitly

```bash
bash .agents/skills/run-gitops-tests/scripts/run-gitops-tests.sh --live
```

Live mode runs read-only readiness checks and the environment-gated sync,
rollback, and Entra permission harnesses with
`RUN_LIVE_GITOPS_TESTS=true`. The harnesses inspect ApplicationSet/Application
health, UI/BFF/Core digest pins, the platform-owned
`career-agent-acr-pull` Secret, last-known-good rollback evidence, and the
current Argo CD operator identity. They do not alter desired state or cluster
resources.

### 5. Preserve evidence

Use `--output-dir artifacts/gitops-tests` (the default) and retain the JSON
readiness result plus test output with the associated GitHub release run or
desired-state revision. Evidence must not contain tokens, client secrets,
kubeconfigs, connection strings, or learner data.

## Failure handling

- **DNS/API unreachable**: report the current context and API hostname, then
  stop; the workstation needs network/VPN/private-DNS access or a refreshed
  kubeconfig.
- **Readiness blocked**: report the named failing check and reason. Do not
  create a namespace, Secret, workload, or Azure resource from this skill.
- **Digest or declaration failure**: treat the release as invalid and inspect
  the release PR/bundle; do not promote mutable tags.
- **Argo health/drift failure**: collect evidence and use the reviewed Git
  rollback workflow. Direct Argo CD UI/CLI rollback is not authoritative.
- **Entra permission failure**: report the role/session/claim failure without
  printing tokens or claims containing credential material.

## Bundled resource

`scripts/run-gitops-tests.sh` is the deterministic workstation entry point. It
supports `--live`, `--output-dir PATH`, and `--skip-contract` for a focused
readiness/integration run.
