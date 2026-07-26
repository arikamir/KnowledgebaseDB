# Quickstart: Argo CD GitOps Application Delivery

This guide proves the application-release path without changing Azure
infrastructure. Terraform/platform bootstrap must already have created the AKS
cluster, the `argocd` and `career-agent` namespaces, gateway/routing, workload
identities, and the namespace-scoped `career-agent-acr-pull` imagePullSecret.

## 1. Run identityless validation

From the repository root:

```bash
scripts/ci/validate-gitops-release.sh
scripts/ci/validate-release-bundle.sh artifacts/release-bundle.json
scripts/ci/check-gitops-platform-ready.sh --mode static
bash -n scripts/ci/validate-gitops-release.sh
bash -n scripts/ci/validate-release-bundle.sh
bash -n scripts/ci/derive-release-version.sh
bash -n scripts/ci/collect-argocd-evidence.sh
bash -n scripts/ci/prepare-gitops-rollback.sh
kubectl kustomize deploy/argocd
kubectl kustomize deploy/k8s/overlays/argocd-nonprod
pytest -q --confcutdir=tests/contract tests/contract/test_argocd_application_set.py
```

The checks must report one valid declaration, render an AppProject and
ApplicationSet, render exactly the three application Deployments, and pass the
contract tests. Rendering does not contact Azure or mutate a cluster.

The repository-local implementation gate runs the feature contract suite,
shell/YAML/JSON checks, Kustomize renders, and `git diff --check`. The three
environment-gated scripts under `tests/integration/` intentionally report
`skipped` unless `RUN_LIVE_GITOPS_TESTS=true` is set in an approved nonprod
environment; no cluster credentials or Entra tokens are committed.

## 2. Install the Argo CD delivery boundary

After Argo CD is installed by the platform operator, configure its repository
credential and controller identity using the cluster's secret/workload-identity
mechanism. Do not commit a token, client secret, or kubeconfig. Then apply only
the delivery boundary:

```bash
kubectl apply -k deploy/argocd
kubectl -n argocd get appproject career-agent
kubectl -n argocd get applicationset career-agent-services
```

The namespace must already exist because the generated Application sets
`CreateNamespace=false`. The pull Secret is platform-owned and is not created by
the ApplicationSet.

Before the first application sync, render and apply the platform-owned runtime
identifiers and Key Vault references from the approved Terraform outputs. The
renderer is dry-run by default and requires an explicit opt-in:

```bash
scripts/azure/apply-career-agent-platform-runtime.sh
APPLY=true scripts/azure/apply-career-agent-platform-runtime.sh
```

Set the script's required environment variables from the platform inventory
(workload identity client IDs, Key Vault and certificate versions, private
data-service hostnames, tenant, origin, and contract range). Do not commit the
rendered files or any credential material. This step is platform bootstrap,
not application release delivery.

Use `.github/workflows/infrastructure.yml` for the separately approved
Terraform/platform lifecycle and `.github/workflows/delivery.yml` for ACR
publication plus the reviewed release PR. The application workflow never
obtains an AKS kubeconfig or infrastructure identity. A rollback uses
`.github/workflows/rollback.yml` to open a reviewed Git reversion; direct Argo
CD rollback is not authoritative.

## 3. Perform the first reviewed release

1. Create a protected SemVer tag such as `v1.2.3` (prerelease/build metadata is
   allowed). CI verifies the effective tag-protection gate and that the tag
   points to the build revision.
2. CI builds/scans/publishes all three services and records their immutable ACR
   digests, source tag, CI run, and validation evidence in a release bundle.
   The bundle schema and repository-lifetime version uniqueness gate must pass
   before a declaration can be generated.
3. CI opens or updates a bot-branch release pull request. The required GitHub
   approved automated-review status and normal branch protection must pass
   before merge; a missing, stale, unapproved, or failed result blocks the
   release. The gate is verified with `scripts/ci/verify-ai-review.sh` against
   the pull-request head commit.
4. Review the normalized SemVer, source SHA, three digests, explicit `nonprod`
   environment, and
   evidence, then merge through protected `main`. Do not run `kubectl apply` or
   Terraform from the application release workflow.
5. Watch the generated Application:

   ```bash
   kubectl -n argocd get applicationset career-agent-services
   kubectl -n argocd get application career-agent-nonprod -o wide
   kubectl -n career-agent get deploy ui bff core
   ```

6. Confirm each Deployment image is the exact digest in
   `deploy/argocd/environments/nonprod/release.json` and record sync/health
   timestamps and reasons.

7. Save the readiness result from
   `scripts/ci/check-gitops-platform-ready.sh`. It must report `ready` and pass
   the namespace, AppProject, `career-agent-acr-pull`, registry, and workload
   prerequisite checks.
8. Collect redacted release/sync evidence when the Application reaches a
   terminal state:

   ```bash
   scripts/ci/collect-argocd-evidence.sh \
     --release deploy/argocd/environments/nonprod/release.json \
     --output artifacts/argocd-evidence.json
   ```

## 4. Verify drift and recovery

For a controlled test, change an application-only field out of band and observe
that Argo CD reports `OutOfSync` and restores the declaration. If a release is
unhealthy, revert the release declaration to the previous reviewed revision (or
approve the documented rollback pull request), merge that change to `main`, and
confirm only the three application workloads reconcile. Direct Argo CD UI/CLI
rollback is not authoritative. No Terraform plan or platform mutation is part
of rollback.

Record elapsed time from protected merge to sync (SC-003: <=10 minutes), failed-release
diagnosis and next-action visibility (SC-005: <=2 minutes), and drift detection
(SC-008: <=5 minutes). A failed release record must identify the affected
service, actionable reason, and recommended next action.

## 5. Configure Entra access

Apply the non-secret role contract in `config/argocd-oidc-rbac.yaml` through the
platform-owned bootstrap path. Configure the Argo CD OIDC integration with the
tenant's approved application registration and map groups/app roles according to
[`contracts/entra-rbac.md`](contracts/entra-rbac.md). Use the default read-only
role, grant application-release separately from infrastructure-admin, and test
expired, revoked, and unassigned sessions. Keep the OIDC secret/workload
identity outside Git. See [`docs/argocd-gitops.md`](../../docs/argocd-gitops.md) for repository
and operations notes.

## 6. Failure expectations

- Missing service, malformed SemVer, mutable image tag, unsupported environment,
  duplicate/reused release version, or invalid bundle evidence: CI rejects the
  declaration before merge.
- A branch push, unprotected tag, tag/source mismatch, or failed/missing/stale/unapproved automated review/branch
  protection review cannot create a deployable release declaration.
- Missing registry access, unavailable Git/cluster, or unhealthy rollout: Argo
  CD reports a non-successful state and retains the last healthy application.
- Missing or invalid `career-agent-acr-pull`: readiness reports `blocked` with an
  actionable reason and no rollout starts.
- Unauthorized Entra principal: action is denied and the audit record contains
  the subject/role/result but no credential material.
