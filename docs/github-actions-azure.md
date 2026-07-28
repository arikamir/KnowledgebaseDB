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
- `.github/workflows/infrastructure.yml` performs identityless Terraform
  formatting and schema validation. Full plan/apply remains on the approved
  private-network platform path because the state contains private Key Vault
  data-plane resources that GitHub-hosted runners cannot safely refresh. Run
  `scripts/azure/run-infrastructure-lifecycle.sh plan`, review its saved plan
  and SHA-256 receipt, then run it with `apply` and
  `INFRASTRUCTURE_APPLY_APPROVED=true`. Apply verifies and consumes that exact
  commit/trust-bound plan; it never regenerates the reviewed plan. Initial
  creation before the managed vault exists additionally requires
  `INFRASTRUCTURE_BOOTSTRAP_APPROVED=true`.
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
OIDC subjects include the immutable GitHub owner and repository IDs configured
by `github_repository_owner_id` and `github_repository_id`, matching GitHub's
ID-bound subject format even when repository visibility changes. Do not infer
the subject format from `use_default`: GitHub's immutable-default rollout can
leave that field set while emitting an ID-bound subject. Before applying the
Azure credentials, query the current-version repository endpoint and treat its
`sub_claim_prefix` as authoritative:

```bash
gh api repos/OWNER/REPOSITORY/actions/oidc/customization/sub \
  -H 'X-GitHub-Api-Version: 2026-03-10'
```

For this repository the verified response prefix is
`repo:arikamir@10241590/KnowledgebaseDB@1305159236`; Azure's failed-token
diagnostic reported the same prefix before the federated credentials were
updated. The Terraform owner/repository names and IDs must reproduce that
prefix exactly. Re-check it after a repository transfer or rename and update
Azure trust before running delivery again.

Every plan/apply must provide the coupled trust tuple
`TF_VAR_github_repository`, `TF_VAR_github_repository_owner_id`, and
`TF_VAR_github_repository_id`. Obtain all three from the repository and its
versioned OIDC `sub_claim_prefix`; none has a repository-specific Terraform
default. Do not place a client secret, kubeconfig, registry password, or Azure
access token in GitHub secrets.
