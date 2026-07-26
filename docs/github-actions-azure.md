# GitHub Actions Azure delivery

GitHub Actions is the CI/CD orchestrator. Jenkins files and controller plugins
remain only as legacy migration material; no deployment job depends on a
Jenkins controller or ACI callback.

## Workflows

- `.github/workflows/ci.yml` runs the full identityless validation suite on pull
  requests, pushes, and manual dispatch.
- `.github/workflows/delivery.yml` runs validation, digest-pinned image build /
  scan / publication and produces a validated non-production GitOps release
  bundle; the application hand-off is a reviewed desired-state pull request.
- `.github/workflows/infrastructure.yml` is the only workflow with the
  infrastructure-admin Azure identity. It runs Terraform plan/apply for
  `infra/azure` and never builds, publishes, or reconciles application images.
- `.github/workflows/rollback.yml` restores a previous release declaration in
  a reviewed pull request; it does not call the Argo CD API directly.
- Application release triggers are protected `v*` tags only. The workflow
  verifies tag protection, tag/source equality, repository-lifetime SemVer
  uniqueness, and the required approved automated-review status before `main` can
  receive the declaration.
- `.github/workflows/reusable-validate.yml` is shared by delivery and regular
  CI so a protected ref cannot skip the all-ref validation gate.

Protected delivery uses GitHub OIDC and short-lived Azure tokens. Configure
these repository/environment values before enabling the workflows:

- application-release secrets: `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
  and `AZURE_PUBLISHER_CLIENT_ID`;
- infrastructure-only secret: `AZURE_INFRASTRUCTURE_CLIENT_ID`;
- variables: `ACR_LOGIN_SERVER`, `AKS_RESOURCE_GROUP`, `AKS_CLUSTER_NAME`,
  `EVIDENCE_STORAGE_ACCOUNT`, and the three service smoke URLs;
- environments: `nonprod-publisher`, `nonprod-release`,
  `infrastructure-plan`, `infrastructure-apply`, and `nonprod-recovery`, with
  required reviewers configured on release/apply/recovery environments.

Configure the repository branch/tag rules so that `main` requires the
`ai/review` status check and protected `v*` tags cannot be created or moved by an
untrusted actor. The release bundle must pass
`scripts/ci/validate-release-bundle.sh` before
`deploy/argocd/environments/nonprod/release.json` is generated.
The pull request gate calls `scripts/ci/verify-ai-review.sh` and accepts only a
review from a repository-approved automated identity whose `commit_id` matches
the current pull-request head. A no-finding result may instead be proven by the
approved reviewer's positive reaction to a review-request marker containing the
exact head SHA. The initial approved identity is
`chatgpt-codex-connector[bot]`; changing that allowlist requires a reviewed
repository-policy update. The helper publishes the `ai/review` commit status
for branch protection and fails closed when the review is missing, stale, or
unapproved.

Terraform creates separate publisher and infrastructure federated credentials
bound to the repository and protected environment subjects. The application
publisher can log in to ACR only; it has no AKS, Terraform, or platform-admin
permission. Pull requests receive no Azure token. The infrastructure identity
is gated by `infrastructure-apply` and is never referenced by delivery jobs.

The first Azure apply after creating the GitHub repository must include
`github_repository = "owner/name"`. Do not place a client secret, kubeconfig,
registry password, or Azure access token in GitHub secrets.
