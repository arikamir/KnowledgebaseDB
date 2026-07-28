# GitHub Actions Delivery Contract

## Authority

GitHub Actions is the only application CI/CD orchestrator. The protected
`.github/workflows/delivery.yml` workflow builds, tests, scans, and publishes
the UI, BFF, and core images. Infrastructure lifecycle operations remain on
the separately approved private platform path.

## Identity and privilege

- Validation is identityless and receives no Azure token.
- Publication uses the `nonprod-publisher` environment and its federated
  publisher identity.
- The publisher can push to the exact ACR and write its scoped immutable
  evidence; it cannot mutate AKS, read Terraform state, or access application
  data.
- The workflow has no deployer identity or kubeconfig. Argo CD reconciles the
  reviewed desired state from the protected `main` branch.

## Immutable build and publication

Every selected service is built once from the protected source revision.
Trivy and SBOM generation must pass before publication. Published references
are immutable ACR digests; tags are not deployment authority.

## GitOps handoff

Delivery generates a release declaration containing the exact UI, BFF, and
core digests, validates the release bundle, and opens a pull request. The pull
request must pass repository checks and the exact-head automated review gate.
Merging that pull request is the only application promotion action.

## Failure and rollback invariants

A failure before publication produces no desired-state change. A failure after
publication leaves unreferenced digests inert because no deployment consumes
them until the reviewed release declaration merges. Rollback is a reviewed Git
reversion through `.github/workflows/rollback.yml`; direct cluster rollback is
not authoritative.

## Required evidence

The workflow records the source revision, GitHub run, selected services,
scanner/SBOM results, immutable digests, release bundle, and desired-state pull
request. Secrets, tokens, kubeconfigs, Terraform state, and personal learning
data must never be included.
