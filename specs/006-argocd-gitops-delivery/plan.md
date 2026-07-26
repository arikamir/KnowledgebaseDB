# Implementation Plan: Argo CD GitOps Application Delivery

**Branch**: `006-argocd-gitops-delivery` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-argocd-gitops-delivery/spec.md`

## Summary

Separate Azure/Terraform platform provisioning from application release. CI
builds, scans, and publishes the UI, BFF, and Core images, derives one SemVer
2.0.0 release version from a verified protected `v*` Git tag, validates a
versioned release bundle, and writes immutable image digests plus evidence to a
release declaration. CI opens or updates a bot-branch pull request; a verified
current-head automated-review status from an approved identity and protected `main` are mandatory before
merge. Argo CD's ApplicationSet reads only the reviewed non-production
declaration and generates an application-only Application. Argo CD reconciles
Git-based rollback, drift, and health; a direct Argo CD UI/CLI rollback is never
authoritative. Terraform and platform bootstrap own AKS, namespaces, gateways,
identities, Entra OIDC/RBAC configuration, and the out-of-band
`career-agent-acr-pull` registry secret.

## Technical Context

**Language/Version**: YAML and JSON manifests; Bash for CI/release gates; Python 3.11 for contract tests; application runtimes remain unchanged  
**Primary Dependencies**: Argo CD ApplicationSet controller, Argo CD `Application`/`AppProject` CRDs, Kubernetes Kustomize, GitHub Actions and pull-request automation, Azure Container Registry, Microsoft Entra OIDC/RBAC  
**Storage**: Protected GitHub `main` for desired state; ACR for immutable OCI images; existing protected evidence storage; Azure Key Vault references and the namespace-scoped `career-agent-acr-pull` secret for runtime/registry access; no new application database  
**Testing**: `jq`, `bash -n`, JSON Schema checks, `kubectl kustomize`, focused `pytest` contract tests, workflow static checks, and environment-gated Argo CD/Kubernetes tests with elapsed-time evidence  
**Target Platform**: Existing AKS non-production cluster in UAE North, namespace `career-agent`; platform prerequisites and the registry pull secret are provisioned independently by Terraform/platform bootstrap  
**Project Type**: Multi-service web application with GitOps delivery configuration and separate Azure infrastructure and application-release workflows  
**Performance Goals**: At least 95% of valid releases reach declared state within 10 minutes of protected merge; an operator can identify failed-release next action within two minutes; drift is detected within five minutes  
**Constraints**: Application release must not invoke Terraform, obtain AKS write credentials, or mutate cluster-scoped/platform resources; images are ACR `@sha256` digests; desired state contains no credentials; only verified protected SemVer tags can start a release; approved current-head automated review and branch protection are required; release versions cannot be reused for another source revision; namespace, gateway, and `career-agent-acr-pull` must already exist
**Scale/Scope**: Three services (UI, BFF, Core), one non-production environment initially, one generated Argo `Application`, one fixed registry-secret reference, and explicit separately reviewed expansion for later environments

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Spec, plan, and tasks describe the same scoped outcome: separated
      infrastructure/application workflows with Git-reviewed Argo delivery.
- [x] User stories are independently testable and ordered by priority; US1 and
      US2 are the combined P1 MVP and US3/US4 are explicit P2 increments.
- [x] Clarifications are resolved in `spec.md` and all technical decisions are
      recorded in `research.md`; no unresolved planning question remains.
- [x] Every story has an independent test, including elapsed-time assertions,
      negative permission checks, drift, rollback, and evidence validation.
- [x] Documentation and runtime guidance cover tag creation, approved automated review,
      pull-secret ownership, Git rollback, Entra roles, and readiness output.
- [x] Added complexity is bounded to the release schema, ApplicationSet,
      application overlay, readiness/evidence contracts, and workflow gates
      required by the functional requirements.

## Project Structure

### Documentation (this feature)

```text
specs/006-argocd-gitops-delivery/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── requirements-traceability.md
├── contracts/
│   ├── application-set.md
│   ├── entra-rbac.md
│   ├── gitops-readiness.md
│   ├── release-bundle.md
│   ├── release-declaration.md
│   └── release-evidence.md
└── tasks.md
```

### Source Code (repository root)

```text
deploy/argocd/
├── applicationset.yaml       # main-branch file generator and Application
├── project.yaml               # source/destination/resource boundary
├── kustomization.yaml
└── environments/nonprod/release.json

deploy/k8s/
├── base/{ui,bff,core}/
└── overlays/argocd-nonprod/   # application-only overlay and pull-secret ref

config/
├── argocd-release.schema.json
├── gitops-release-bundle.schema.json
├── gitops-evidence.schema.json
├── argocd-rbac-policy.yaml
├── argocd-oidc-rbac.yaml
└── gitops-readiness.schema.json

scripts/ci/
├── derive-release-version.sh
├── validate-release-bundle.sh
├── validate-gitops-release.sh
├── write-gitops-release.sh
├── check-gitops-platform-ready.sh
├── verify-ai-review.sh
├── collect-argocd-evidence.sh
├── detect-changes.sh
├── prepare-gitops-rollback.sh
└── check-release-version-uniqueness.sh

scripts/azure/
└── apply-argocd-rbac.sh       # platform-owned OIDC/RBAC bootstrap

.github/workflows/
├── delivery.yml               # publish and reviewed desired-state PR
├── infrastructure.yml        # Terraform-only workflow
└── rollback.yml               # reviewed declaration-reversion workflow

infra/azure/                   # Terraform-owned platform and identities
tests/contract/ and tests/integration/
README.md
docs/argocd-gitops.md
docs/github-actions-azure.md
docs/argocd-entra.md
```

**Structure Decision**: Preserve the existing three-service and Terraform
layout. Keep desired-state and application-only manifests under `deploy/argocd`
and `deploy/k8s/overlays/argocd-nonprod`; keep validation/contracts in `config`,
`scripts/ci`, and `tests`. The namespace, gateway, platform controllers,
Terraform state, and `career-agent-acr-pull` secret remain outside the generated
Application's resource set.

## Design and Delivery Phases

### Phase 0: Research outcomes

- Use the Argo CD Git file generator with `goTemplateOptions:
  [missingkey=error]`, fixed `main`, and the exact non-production declaration
  path. This fails closed when release fields are missing.
- Use a protected SemVer tag as the release-version authority. Normalize an
  optional `v` prefix, accept full SemVer 2 prerelease/build metadata, ensure the
  tag points at the build source revision, verify the effective protected-tag
  gate, and reject versions already associated with another source revision in
  repository history or the protected evidence store.
- Have CI create/update a bot-branch PR. Repository branch protection requires
  a verified current-head review from an approved automated identity before merge. Argo CD consumes
  only the merged `main` revision; it never reads an unreviewed branch as desired
  state.
- Make reviewed Git reversion the only rollback authority. Argo CD reconciles
  the reverted declaration and records the result; direct UI/CLI rollback must
  not become a divergent desired state.
- Keep a restricted AppProject and application-only Kustomize overlay. The
  overlay references, but does not create, the platform-owned
  `career-agent-acr-pull` image pull secret. The AppProject therefore does not
  grant Secret creation to the release Application.
- Define a readiness response with `status` (`ready` or `blocked`), named check
  results, environment, observed timestamp, and actionable failure reason. It
  may read prerequisites but must not mutate infrastructure.
- Define a release-bundle schema separate from the Argo CD declaration so CI
  evidence, the protected source tag, and the originating run are validated
  before the declaration is written.
- Configure Entra OIDC and Argo CD RBAC through a platform-owned bootstrap
  path. Git stores only non-secret role mappings; the workflow verifies claims,
  session validity, and revocation before privileged actions.
- Record `affectedService`, `nextAction`, `diagnosedAt`, and
  `nextActionVisibleAt` in failure evidence so the two-minute diagnosis target
  is measurable.
- Instrument live verification with `mergedAt`, `syncStartedAt`, and elapsed
  timestamps so SC-003 (10 minutes from protected merge), SC-005 (two minutes),
  and SC-008 (five minutes) are asserted rather than merely described.

### Phase 1: Design outputs

1. Model release tags, bundles, declarations, generated Applications, readiness,
   sync/rollback evidence, and delivery identities in `data-model.md`.
2. Define declaration, ApplicationSet, readiness, evidence, and Entra contracts
   in `contracts/`.
3. Keep executable schemas and identityless gates in `config/` and `scripts/ci`.
4. Document tag/PR/review, secret ownership, readiness, first sync, timing
   evidence, drift, and Git rollback in `quickstart.md` and `docs/argocd-gitops.md`.
5. Add contract and environment-gated tests for workflow boundaries, full
   SemVer, approved automated-review PR flow, three immutable digests, readiness output, timing,
   drift, rollback, and Entra permissions.

### Phase 2: Implementation sequencing

The existing task list follows this order:

1. release schema, full SemVer tag validation, and fixtures;
2. release-bundle schema/gate, application-only overlay, pull-secret reference,
   AppProject, and ApplicationSet;
3. explicit Terraform-only versus application-release workflow boundaries;
4. CI publication, bot-branch PR, approved automated review, and main-branch reconciliation;
5. readiness/evidence contracts and timing assertions;
6. Git rollback, drift recovery, Entra OIDC/RBAC, and final live verification.

### Post-design Constitution Re-check

**PASS**. The plan now matches every clarification: Git tags assign versions,
protected-tag and automated-review gates are verified before promotion, Git PR reversion
is authoritative, the pull secret is platform-owned, Entra OIDC/RBAC remains
platform-owned, and readiness/timing evidence are testable. The
application workflow has no infrastructure mutation path, all four stories have
independent tests, and documentation/tasks reference the same resource boundary.

## Complexity Tracking

No constitution violations remain. The additional readiness/evidence contracts
and timing tests are required to make FR-018 and SC-003/SC-005/SC-008 measurable;
the release-bundle/protected-review gates close the pre-promotion trust gap, and
the Entra contract remains platform-owned. These additions do not add a runtime
service or a new infrastructure project.
