# GitHub Actions Azure delivery

GitHub Actions is the sole CI/CD orchestrator. Repository workflows validate
the source, build and scan immutable images, push them to ACR, and open the
reviewed GitOps desired-state pull request. No controller plugin, ephemeral
controller agent, or direct AKS deployment job is part of this path.

## Workflows

- `.github/workflows/ci.yml` runs the full identityless validation suite on pull
  requests, pushes, and manual dispatch.
- `.github/workflows/delivery.yml` runs validation, digest-pinned image build /
  scan / publication and produces a validated non-production GitOps release
  bundle; the application hand-off is a reviewed desired-state pull request.
- `.github/workflows/infrastructure.yml` performs identityless Terraform
  formatting and schema validation. Full plan/apply remains on the approved
  private-network platform path because the state contains private Key Vault
  data-plane resources that GitHub-hosted runners cannot safely refresh. Run
  `scripts/azure/run-infrastructure-lifecycle.sh plan`, review its saved plan
  and SHA-256 receipt, then run it with `apply` and
  `INFRASTRUCTURE_APPLY_APPROVED=true`. Apply verifies and consumes that exact
  commit/trust/backend-bound plan; it never regenerates the reviewed plan. The
  Key Vault reachability probe is derived from the saved plan's
  `key_vault_target` output, so an unrelated accessible vault cannot satisfy the
  private-data-plane gate. The receipt records the effective publisher OIDC
  subject together with the immutable owner/repository IDs and must exactly
  match `TF_VAR_github_repository`, both ID values, and
  `TF_VAR_github_actions_environment`, preventing ignored or
  higher-precedence tfvars from silently changing trust. Initial
  creation before the managed vault exists additionally requires
  `INFRASTRUCTURE_BOOTSTRAP_APPROVED=true`. Saved plans default to a unique
  mode-`0700` directory under `${TMPDIR:-/tmp}`. Apply must set
  `INFRASTRUCTURE_ARTIFACT_DIRECTORY` to that reviewed plan directory. The
  script rejects symlinks, foreign-owned or permissive directories, and any
  artifact directory inside the repository because binary plans can contain
  sensitive state-derived values.
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
- variables: `ACR_LOGIN_SERVER`, `AKS_RESOURCE_GROUP`, `AKS_CLUSTER_NAME`,
  `EVIDENCE_STORAGE_ACCOUNT`, and the three service smoke URLs;
- environments: `nonprod-publisher`, `nonprod-release`,
  and `nonprod-recovery`, with required reviewers configured on release and
  recovery environments.

Configure the repository branch/tag rules so that `main` requires the
`ai/review` status check and protected `v*` tags cannot be created or moved by an
untrusted actor. The release bundle must pass
`scripts/ci/validate-release-bundle.sh` before
`deploy/argocd/environments/nonprod/release.json` is generated.
The pull request gate calls `scripts/ci/verify-ai-review.sh` and accepts only a
review from a repository-approved automated identity whose `commit_id` matches
the current pull-request head. A no-finding result may instead be proven by the
approved reviewer's positive reaction to a review-request marker containing the
exact head SHA, or by the connector's bot-authored no-findings comment naming
the reviewed commit together with its positive PR reaction. The initial approved identity is
`chatgpt-codex-connector[bot]`; changing that allowlist requires a reviewed
repository-policy update. The helper publishes the `ai/review` commit status
for branch protection and fails closed when the review is missing, stale,
unapproved, or contains findings.
Retries may reuse only an exact-head request comment owned by the configured
trusted requester that already has a positive reaction from an approved
reviewer. Otherwise the gate creates a fresh trusted request; comments from any
other identity cannot suppress or satisfy it.
For generated release and rollback PRs, the dedicated least-privilege review
job re-authenticates the proof and head immediately before merging that exact
SHA. A failed merge changes `ai/review` back to failure, so a successful status
is not left on an unmerged delivery PR. An exit guard always resets the status
when any receipt or API operation fails after success is published; for
merge-enabled runs it remains armed through proof recheck and merge completion.
The gate also requires the head SHA output by the PR-creation job, preventing a
push between jobs from substituting a different release or rollback head.

Terraform creates a publisher federated credential bound to the repository and
protected environment subject. The application
publisher can log in to ACR only; it has no AKS, Terraform, or platform-admin
permission. Pull requests and infrastructure validation receive no Azure or
Microsoft Graph token. Platform operators run full plan/apply only from the
private-network execution path with its separately approved identity.
The federated credential must match the subject GitHub emits for an
environment-bound job:
`repo:OWNER/REPOSITORY:environment:ENVIRONMENT`. For this repository's
publisher job, that is
`repo:arikamir/KnowledgebaseDB:environment:nonprod-publisher`. Numeric owner and
repository IDs are retained as reviewed receipt metadata so a rename or
transfer is explicit, but GitHub does not include those IDs in the emitted
subject and Azure trust must not insert them.

Every plan/apply must provide the coupled trust tuple
`TF_VAR_github_repository`, `TF_VAR_github_repository_owner_id`, and
`TF_VAR_github_repository_id`. Obtain the repository name and numeric IDs from
GitHub's repository API; none has a repository-specific Terraform default.
The private lifecycle also requires `TF_BACKEND_TENANT_ID` and
`TF_BACKEND_SUBSCRIPTION_ID`, verifies they match the active Azure CLI account,
and passes them explicitly to backend initialization. Do not place a client
secret, kubeconfig, registry password, or Azure access token in GitHub secrets.
