# Argo CD application delivery

Argo CD is the application release controller for the non-production AKS
cluster. It is intentionally not an infrastructure controller:

1. Platform Operations provisions the AKS cluster, the `argocd`,
   `career-agent`, and `career-migrations` namespaces, workload identities,
   migration admission guardrails/runtime configuration, the gateway, and the
   namespace-scoped `career-agent-acr-pull` imagePullSecret through Terraform
   and the platform bootstrap process.
2. CI publishes the UI, BFF, and Core images to ACR, verifies the protected
   `v*` SemVer tag and source commit, validates a release bundle, and records immutable
   `repository@sha256:...` references in
   `deploy/argocd/environments/nonprod/release.json`.
3. CI opens or updates a bot-branch pull request. The required approved automated
   status and repository branch protection must pass before the release
   declaration is merged to GitHub `main`; missing or stale review status blocks
   the merge.
4. The `career-agent-services` ApplicationSet discovers that declaration and
   generates one Argo CD `Application` with two sources. A bounded `PreSync`
   Job runs the expand-only migration entrypoint from the exact Core digest in
   `career-migrations`; only after it succeeds may Argo CD reconcile the UI,
   BFF, and Core service overlay in `career-agent`.

The application workflow never obtains AKS write credentials, runs Terraform,
or applies platform manifests. Infrastructure workflow changes are separately
approved and must not publish or deploy application images.

`.github/workflows/infrastructure.yml` owns credential-free Terraform
validation. `scripts/azure/run-infrastructure-lifecycle.sh` owns reviewed
plan/apply on the private-network platform runner and emits the platform scope
artifact. `.github/workflows/delivery.yml` owns image publication and the
bot-branch desired-state pull request. `.github/workflows/rollback.yml` only
prepares a reviewed Git declaration reversion. This ownership boundary is
checked by `tests/contract/test_gitops_workflow_boundaries.py`.

## AKS operator connectivity

The AKS API access path is infrastructure-owned. Terraform creates the VNet and
AKS subnet and configures `api_server_authorized_ip_ranges` from reviewed
operator or VPN-egress CIDRs. In technical PoC mode it reuses
`poc_operator_source_cidrs`; formal environments must provide a reviewed
`aks_api_server_authorized_ip_ranges` value. The Terraform outputs
`aks_connection` and `aks_api_server_fqdn` provide non-secret connection
metadata and the kubeconfig refresh command. Do not widen the API to
`0.0.0.0/0` to work around a local DNS or VPN problem.

The `career-agent-acr-pull` Secret is platform-owned. The application overlay
references its name, but Argo CD does not create or manage its credential data.

The ApplicationSet generates an Argo CD `Application` from a service source and
a migration-hook source. It does not manage Terraform, namespaces, Application
Gateway, private load balancer, cluster controllers, migration identity,
admission policy, or other platform resources. `CreateNamespace=false` is
deliberate: a missing namespace or migration prerequisite is a platform
readiness failure, not an application release opportunity.

Platform bootstrap remains responsible for materializing the reviewed,
non-secret runtime identifiers and Key Vault references consumed by the
workload templates. ApplicationSet only selects the validated release images;
it does not synthesize platform configuration or copy credentials into Git.

The repository includes a dry-run-by-default renderer for that bootstrap
boundary. Supply the non-secret values from Terraform outputs and the approved
platform inventory, then explicitly opt in to the cluster write:

```bash
scripts/azure/apply-career-agent-platform-runtime.sh
APPLY=true scripts/azure/apply-career-agent-platform-runtime.sh
```

The script owns only the workload service accounts, Key Vault CSI provider
classes, and runtime ConfigMaps. It never creates the ACR pull Secret or
stores private key material. The Argo CD overlay references these resources
but does not manage them.

This first ApplicationSet is intentionally pinned to the `nonprod` declaration
and the existing UAE North application overlay. Adding another environment
requires a new reviewed ApplicationSet and AppProject destination rather than
silently widening this release boundary.

## Install order

After Argo CD is installed and its repository credential is configured without
putting a token in Git, apply the project and ApplicationSet as a
Platform Operations action:

```bash
kubectl apply -k deploy/argocd
```

Apply the non-secret Entra OIDC/RBAC contract through the platform-owned
bootstrap path; the script is dry-run by default and injects no client secret:

```bash
scripts/azure/apply-argocd-rbac.sh
APPLY=true scripts/azure/apply-argocd-rbac.sh
```

The Argo CD service account used for this installation must be allowed to
create Applications only in the `career-agent` AppProject. The project permits
service resources in `career-agent` and only the bounded migration `Job` kind
in `career-migrations`; it has no cluster-resource whitelist.

## Release declaration

`release.json` is the desired-state hand-off from CI to Argo CD. It must contain
one SemVer 2.0.0 release identity and all three service image digests. The
version must match the protected source tag (including optional prerelease/build
metadata after normalizing an optional `v` prefix). Validate it locally with:

```bash
scripts/ci/validate-gitops-release.sh
```

The file is the only release selector. Mutable tags, branch/manual releases,
registry credentials, Entra tokens, client secrets, and other secret material
are rejected by the validator and must never be committed. A rollback is a
approved-automated-review revert of this file to the last known-good Git revision; direct
Argo CD UI/CLI rollback is not authoritative and does not invoke Terraform.

## Readiness and timing evidence

Run `scripts/ci/check-gitops-platform-ready.sh` before the application release
hand-off. Its versioned JSON result reports `ready` or `blocked`, named checks
for the namespace, AppProject, `career-agent-acr-pull`, registry, and workload
prerequisites, an observation timestamp, and an actionable failure reason. The
command is read-only and never provisions the missing prerequisite.

Release evidence records protected-merge-to-sync (target: 10 minutes), affected service,
actionable failure reason and next action with diagnosis visibility (target: two
minutes), and drift detection (target: five minutes).

Use `scripts/ci/collect-argocd-evidence.sh` after a release or reconciliation
to produce a schema-v2 record linking the CI run, desired-state revision, generated Application, image
digests, readiness result, automated-review status, and timing fields. Failed syncs must
include an affected service and next action. `scripts/ci/prepare-gitops-rollback.sh`
creates an auditable rollback intent; only the resulting reviewed PR changes
desired state. Argo retry/self-heal/prune are bounded by the ApplicationSet's
five-attempt, three-minute backoff policy, and the previous Git declaration is
the last-known-good state when a new revision is unhealthy.
The collector requires `--automated-review-evidence`; pass the receipt artifact
emitted by the successful current-head gate so retained evidence cannot
silently attribute the review or pass status to caller-supplied values.
Also pass `--review-pull-request` and `--review-head-revision` from the
independently retained release or rollback scope artifact; mismatched receipts
are rejected. The collector uses `gh` with an authenticated GitHub token to
recheck the PR head, `ai/review` status, and approved review or exact-marker
reaction before writing the retained record.

## Azure Entra access

Human Argo CD operators authenticate through the configured Azure Entra SSO
integration. Map Entra groups or app roles to separate application-release,
infrastructure-administration, and read-only-observability permissions. The
ApplicationSet itself uses Argo CD's repository and controller identities; it
does not contain a human token or client secret. Runtime learner authentication
through the BFF is a separate concern. The non-secret mapping is defined in
`config/argocd-oidc-rbac.yaml`; platform bootstrap injects the OIDC secret and
rejects expired or revoked sessions before privileged actions.
