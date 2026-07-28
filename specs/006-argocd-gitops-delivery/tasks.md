# Tasks: Argo CD GitOps Application Delivery

**Input**: Design documents from `/specs/006-argocd-gitops-delivery/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`

**Organization**: Tasks are grouped by user story so each independently
testable release slice can be implemented and verified without coupling
application delivery to infrastructure provisioning.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the repository paths, CI inputs, and test fixtures used
by every delivery story.

- [X] T001 [P] Document the repository ownership boundary and changed-file scope for infrastructure versus application release in `docs/argocd-gitops.md`.
- [X] T002 [P] Document required GitHub Actions environments, variables, OIDC identities, ACR coordinates, and protected-tag/branch prerequisites in `docs/github-actions-azure.md`.
- [X] T003 [P] Add reusable release-bundle and declaration fixtures for valid, malformed, unprotected-tag, tag/source-mismatch, mutable-tag, missing-service, duplicate-version, reused-version, and credential-containing inputs under `tests/contract/fixtures/gitops/`.
- [X] T004 [P] Record the clarified release conventions (SemVer tag, approved automated review, rollback PR, and `career-agent-acr-pull`) in `specs/006-argocd-gitops-delivery/quickstart.md`.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the immutable release contract and application-only Argo CD
boundary before any user story workflow can be exercised.

**Checkpoint**: The release declaration validates, the overlay renders three
workloads with the fixed image-pull-secret reference, and the ApplicationSet
cannot target platform-owned resources.

- [X] T005 [P] Define the release declaration and pre-declaration release-bundle JSON Schemas/contracts, including SemVer 2, source SHA, protected source tag, CI run/evidence links, exact `ui`/`bff`/`core` services, ACR digest references, explicit `nonprod` target, and no additional properties in `config/argocd-release.schema.json`, `config/gitops-release-bundle.schema.json`, and `specs/006-argocd-gitops-delivery/contracts/release-bundle.md`.
- [X] T006 [P] Implement identityless release-bundle/declaration validation for schema shape, environment-directory matching, immutable digests, and credential-string rejection in `scripts/ci/validate-release-bundle.sh` and `scripts/ci/validate-gitops-release.sh`.
- [X] T007 [P] Implement protected `v*` tag parsing, effective tag-protection verification, optional-prefix normalization, full SemVer 2 prerelease/build validation, tag-to-source-revision matching, and repository-lifetime version uniqueness in `scripts/ci/derive-release-version.sh` and `scripts/ci/check-release-version-uniqueness.sh`.
- [X] T008 [P] Add the application-only Kustomize overlay and patch UI, BFF, and Core pod specs to reference `career-agent-acr-pull` without creating or embedding secret data in `deploy/k8s/overlays/argocd-nonprod/kustomization.yaml` and `deploy/k8s/overlays/argocd-nonprod/application-images.yaml`.
- [X] T009 [P] Restrict the Argo CD source repository, destination namespace, cluster-resource whitelist, and namespace-resource allowlist in `deploy/argocd/project.yaml`.
- [X] T010 [P] Configure the fixed `main` Git file generator, missing-key failure mode, immutable image substitutions, application-only overlay, automated sync policy, and no-namespace-creation rule in `deploy/argocd/applicationset.yaml`.
- [X] T010a [P] Add the bounded `career-migrations` `PreSync` Job as a second Application source, using the exact release Core digest and platform-owned migration guardrails so schema expansion must succeed before service rollout.
- [X] T011 [P] Extend `tests/contract/test_argocd_application_set.py` to assert the fixed release path, three digest substitutions, `career-agent-acr-pull` reference, AppProject restrictions, and absence of gateway/namespace/platform resources.
- [X] T012 Run `scripts/ci/validate-release-bundle.sh`, `scripts/ci/validate-gitops-release.sh`, `kubectl kustomize deploy/argocd`, `kubectl kustomize deploy/k8s/overlays/argocd-nonprod`, and the focused contract tests; record the expected output in `specs/006-argocd-gitops-delivery/quickstart.md`.

## Phase 3: User Story 1 - Separate platform provisioning from application release (Priority: P1) 🎯 MVP

**Goal**: Make infrastructure provisioning and application release independently
executable, reviewable, and permission-bounded workflows.

**Independent Test**: Run identityless infrastructure validation, use the
private-network lifecycle runner with a Terraform plan input, and run the
application workflow with a release declaration input; verify that only the
private runner can change Azure/platform resources and application delivery
never obtains AKS/Terraform credentials or applies platform manifests.

### Tests for User Story 1

- [X] T013 [P] [US1] Add workflow contract tests that fail when application release jobs call Terraform, acquire AKS credentials, or reference platform overlays in `tests/contract/test_gitops_workflow_boundaries.py`.
- [X] T014 [P] [US1] Add a scope-evidence fixture and assertions for actor, inputs, changed resource set, result, and evidence links in `tests/contract/fixtures/gitops/workflow-scope.json`.

### Implementation for User Story 1

- [X] T015 [US1] Create identityless infrastructure validation in `.github/workflows/infrastructure.yml` plus the independently approved private-network Terraform plan/apply runner `scripts/azure/run-infrastructure-lifecycle.sh`, with plan artifacts, an explicit apply gate, and no build/publish/promote/deploy application-image steps.
- [X] T016 [US1] Refactor `.github/workflows/delivery.yml` so application publication and desired-state PR creation do not run `az aks get-credentials`, `scripts/ci/promote.sh`, Terraform, or platform bootstrap commands.
- [X] T017 [US1] Configure GitHub OIDC publisher permissions, least-privilege bot-branch/PR write permissions, application-release environment protection, and no infrastructure-admin access for the application job in `.github/workflows/delivery.yml` and `docs/github-actions-azure.md`.
- [X] T018 [US1] Add separate scope/evidence output for private infrastructure lifecycle and application workflows, including actor, source revision, environment, outcome, and artifact links, in `scripts/azure/run-infrastructure-lifecycle.sh` and `.github/workflows/delivery.yml`.
- [X] T019 [US1] Verify the split workflows with boundary tests that reject both application-to-infrastructure mutation and infrastructure-to-application image publication/deployment, plus a dry-run change-plan fixture in `scripts/ci/detect-changes.sh` and `tests/contract/test_gitops_workflow_boundaries.py`.

**Checkpoint**: US1 is complete when validation, private infrastructure
lifecycle, and application delivery run independently, their permissions and
evidence are distinct, and application delivery cannot mutate Azure or platform
resources.

## Phase 4: User Story 2 - Reconcile CI artifacts through Argo CD (Priority: P1) 🎯 MVP

**Goal**: Publish all three immutable images, create a reviewed desired-state
PR, and let Argo CD reconcile the exact SemVer-bound digests from GitHub `main`.

**Independent Test**: Publish a valid tagged release, merge the approved-automated-review
release PR, observe the generated Application sync, and verify that UI/BFF/Core
run the three declared digests while the namespace and gateway remain
platform-owned.

### Tests for User Story 2

- [X] T020 [P] [US2] Add release declaration contract tests for protected-tag matching, tag/source equality, full SemVer normalization including prerelease/build metadata, exact service completeness, digest immutability, unique versions, and invalid fixture rejection in `tests/contract/test_release_declaration.py`.
- [X] T021 [P] [US2] Add a GitHub workflow contract test proving that the publication job creates or updates a bot-branch release PR, verifies the approved current-head automated-review status through `scripts/ci/verify-ai-review.sh`, rejects unapproved/stale/missing review results, and does not bypass protected `main` in `tests/contract/test_release_pull_request_flow.py`.
- [X] T022 [P] [US2] Add an environment-gated reconciliation test script for ApplicationSet discovery, generated Application health, three Deployment digests, and `career-agent-acr-pull` availability in `tests/integration/test_argocd_nonprod_sync.sh`.

### Implementation for User Story 2

- [X] T023 [US2] Generate the SemVer-matched release declaration as the sole declaration writer from the published release manifest and CI run evidence in `scripts/ci/write-gitops-release.sh`.
- [X] T024 [US2] Update `.github/workflows/delivery.yml` to trigger releases only from verified protected `v*` tags, reject branch/manual release attempts and nonprod targets, derive and verify the tag version, validate the release bundle and repository-lifetime version uniqueness, write `deploy/argocd/environments/nonprod/release.json`, and open/update a bot-branch pull request whose approved current-head automated-review status is verified before merge.
- [X] T025 [US2] Validate the single release identity and three immutable digests after T023 writes `deploy/argocd/environments/nonprod/release.json`, rejecting partial or cross-release image combinations in `scripts/ci/validate-gitops-release.sh` without generating files.
- [X] T026 [US2] Add the versioned readiness schema and read-only check for the existing namespace, Argo CD project, `career-agent-acr-pull`, registry reachability, and required workload prerequisites in `config/gitops-readiness.schema.json`, `contracts/gitops-readiness.md`, and `scripts/ci/check-gitops-platform-ready.sh`.
- [X] T027 [US2] Invoke the identityless release gate and readiness command at the correct workflow boundary, validate the `ready`/`blocked` JSON result, and prove the release job cannot mutate infrastructure in `.github/workflows/delivery.yml` and `tests/contract/test_gitops_readiness.py`.
- [X] T028 [US2] Verify first sync, immutable image rendering, failed-image retention, out-of-band drift recovery, and elapsed-time thresholds of <=10 minutes from protected merge to sync and <=5 minutes for drift in `tests/integration/test_argocd_nonprod_sync.sh` and `specs/006-argocd-gitops-delivery/quickstart.md`.

**Checkpoint**: US2 is complete when a reviewed tagged release reaches the
declared non-production application state through Argo CD and no application
workflow directly mutates AKS or Azure infrastructure.

## Phase 5: User Story 3 - Operate, audit, and roll back releases (Priority: P2)

**Goal**: Make sync outcomes, health failures, audit links, and rollback through
a reviewed Git reversion visible and repeatable.

**Independent Test**: Promote an intentionally unhealthy declaration, observe a
failed health result and evidence record, merge a reviewed PR reverting to the
previous healthy declaration, and verify recovery without a Terraform run.

### Tests for User Story 3

- [X] T029 [P] [US3] Add schema and contract tests for CI-to-Argo evidence links, repository/branch, event and actor type, required automation or human identity, approved automated-review status-check, validation/readiness evidence, conditional affected-service/reason/next-action fields, merge-to-sync/failure-diagnosis/drift elapsed-time fields, and credential redaction in `tests/contract/test_gitops_evidence.py`.
- [X] T030 [P] [US3] Add rollback workflow contract tests proving only a reviewed release-declaration PR can change desired state and that direct Argo CD rollback is non-authoritative in `tests/contract/test_gitops_rollback.py`.
- [X] T031 [P] [US3] Add an environment-gated failure/drift/rollback scenario covering last-known-good retention, <=2-minute failure diagnosis, <=5-minute drift detection, and recovery evidence in `tests/integration/test_argocd_rollback.sh`.

### Implementation for User Story 3

- [X] T032 [US3] Define the release and reconciliation evidence schema, repository/branch, event/actor type, validation/readiness evidence, conditional rollback fields, affected-service/next-action diagnosis fields, and credential-redaction rules in `config/gitops-evidence.schema.json` and `specs/006-argocd-gitops-delivery/contracts/release-evidence.md`.
- [X] T033 [US3] Collect GitHub run, repository/branch, protected source tag, release version, source revision, image digests, event/actor identity, approved automated-review result, validation/readiness evidence, generated Application, sync/health result, rollback data when applicable, merge/sync/failure/drift timestamps, and elapsed-time evidence in `scripts/ci/collect-argocd-evidence.sh`.
- [X] T034 [US3] Implement the reviewed declaration-reversion workflow with actor, role, reason, source/target revisions, approved automated review, and merge result in `.github/workflows/rollback.yml` and `scripts/ci/prepare-gitops-rollback.sh`.
- [X] T035 [US3] Ensure Argo CD retry, self-heal, prune, and last-known-good behavior is bounded and observable in `deploy/argocd/applicationset.yaml` and `docs/argocd-gitops.md`.
- [X] T036 [US3] Document failed-release diagnosis, drift handling, reviewed rollback, and evidence lookup in `docs/argocd-gitops.md` and `specs/006-argocd-gitops-delivery/quickstart.md`.

**Checkpoint**: US3 is complete when operators can identify a failing service
and reason, revert through Git, and prove recovery without infrastructure work.

## Phase 6: User Story 4 - Authenticate delivery operators with Azure Entra (Priority: P2)

**Goal**: Enforce Entra SSO and distinct release, infrastructure, and read-only
permissions for every privileged delivery action.

**Independent Test**: Sign in with one principal from each role, verify allowed
and denied Application/Git actions, expire or revoke a session, and confirm the
audit event records tenant, subject, role, action, target, and result without
credential material.

### Tests for User Story 4

- [X] T037 [P] [US4] Add contract tests for Entra group/app-role mapping, default read-only policy, OIDC claim validation, session expiry/revocation requirements, and forbidden infrastructure permissions in `tests/contract/test_argocd_entra_rbac.py`.
- [X] T038 [P] [US4] Add an environment-gated permission matrix for application-release, infrastructure-admin, and observability-readonly principals in `tests/integration/test_argocd_entra_permissions.sh`.

### Implementation for User Story 4

- [X] T039 [US4] Define non-secret Argo CD RBAC role mappings and default read-only behavior in `config/argocd-rbac-policy.yaml`.
- [X] T040 [US4] Document the Entra OIDC application registration, redirect URI, required group/app-role claims, automated-review-independent operator roles, session/revocation policy, and secret/workload-identity injection in `docs/argocd-entra.md`.
- [X] T041 [US4] Apply the Entra OIDC/RBAC policy through the platform-owned Argo CD bootstrap path, validate tenant/subject/role claims for privileged actions, and keep tenant secrets, client secrets, and tokens out of `deploy/argocd/` desired state in `config/argocd-oidc-rbac.yaml` and `scripts/azure/apply-argocd-rbac.sh`.
- [X] T042 [US4] Add audit assertions for tenant, subject, resolved role, authentication result, action/event type, actor type, environment, release version, and timestamp with credential redaction in `scripts/ci/collect-argocd-evidence.sh` and `tests/contract/test_argocd_entra_rbac.py`.

**Checkpoint**: US4 is complete when Entra role tests pass for allow/deny,
expired-session actions are rejected, and every privileged action is attributable.

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Finish documentation, traceability, and repeatable validation across
all stories.

- [X] T043 [P] Update `docs/argocd-gitops.md`, `docs/github-actions-azure.md`, and `README.md` with the final GitOps hand-off, approved automated review, secret prerequisite, rollback, and Entra operator procedures.
- [X] T044 [P] Update `specs/006-argocd-gitops-delivery/quickstart.md` to match the implemented workflow commands, environment gates, evidence locations, and non-production verification steps.
- [X] T045 [P] Add requirements-to-task traceability for every functional identifier (FR-001, FR-002, FR-003, FR-004, FR-004a, FR-004b, FR-005, FR-006, FR-006a, FR-006b, FR-006c, FR-007, FR-007a, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-014a, FR-014b, FR-014c, FR-014d, FR-014e, FR-015, FR-015a, FR-016, FR-017, FR-018) and SC-001 through SC-012 in `specs/006-argocd-gitops-delivery/requirements-traceability.md`, with explicit task IDs and verification evidence.
- [X] T046 Run the full identityless validation suite, release-bundle/tag/automated-review contract tests, YAML/JSON parsing, shell syntax checks, Kustomize renders, and `git diff --check` from the repository root.
- [X] T047 Run the approved non-production end-to-end sync, Git/cluster-connectivity, concurrent-release convergence, drift, failure-retention, rollback, automated-review gate, and Entra permission checks; attach evidence links without committing secrets in `specs/006-argocd-gitops-delivery/quickstart.md`.
- [X] T048 Review all changed workflow permissions and generated manifests for least privilege, immutable digests, absence of platform resources, and credential redaction before merge in `docs/argocd-gitops.md`.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001-T004 can run in parallel.
- **Foundational (Phase 2)**: Depends on Setup; T005-T011 can run in parallel, then T012 is the checkpoint.
- **User Story 1 (Phase 3)**: Depends on the foundational checkpoint; it can run independently of US2, US3, and US4.
- **User Story 2 (Phase 4)**: Depends on the foundational checkpoint; it can run independently of US1, but the final workflow hand-off should incorporate US1's permission boundary.
- **User Story 3 (Phase 5)**: Depends on US2's generated Application and release PR path.
- **User Story 4 (Phase 6)**: Depends on the foundational checkpoint and can proceed in parallel with US1 and US2; live permission checks require the Argo CD installation.
- **Polish (Phase 7)**: Depends on all desired user stories and their checkpoints.

### User Story Dependencies

```text
Setup -> Foundational -> US1 (P1) ───────────────┐
                     -> US2 (P1) -> US3 (P2) ────┼-> Polish
                     -> US4 (P2) ────────────────┘
```

## Parallel Execution Examples

### User Story 1

```text
T013 tests/contract/test_gitops_workflow_boundaries.py
T014 tests/contract/fixtures/gitops/workflow-scope.json
T015 .github/workflows/infrastructure.yml
T017 .github/workflows/delivery.yml + docs/github-actions-azure.md
```

### User Story 2

```text
T020 tests/contract/test_release_declaration.py
T021 tests/contract/test_release_pull_request_flow.py
T023 scripts/ci/write-gitops-release.sh
T026 scripts/ci/check-gitops-platform-ready.sh
```

### User Story 3

```text
T029 tests/contract/test_gitops_evidence.py
T030 tests/contract/test_gitops_rollback.py
T032 config/gitops-evidence.schema.json
T033 scripts/ci/collect-argocd-evidence.sh
```

### User Story 4

```text
T037 tests/contract/test_argocd_entra_rbac.py
T039 config/argocd-rbac-policy.yaml
T040 docs/argocd-entra.md
```

## Implementation Strategy

### MVP First

The MVP is the combined P1 slice because the feature's value requires both
workflow separation and Argo CD reconciliation:

1. Complete Setup and Foundational phases.
2. Complete US1 and prove that application delivery cannot mutate infrastructure.
3. Complete US2 and prove a protected tagged release reaches non-production via
   the ApplicationSet using the three immutable digests.
4. Stop and validate the two P1 checkpoints before adding rollback/Entra polish.

### Incremental Delivery

1. Add US3 for evidence, drift handling, and reviewed Git rollback.
2. Add US4 for Entra OIDC/RBAC and permission/audit verification.
3. Run the final cross-cutting and live non-production checks.

### Parallel Team Strategy

After the foundational checkpoint, one contributor can implement US1, a second
US2, and a third US4. US3 should begin after US2's release PR and generated
Application contract stabilize.

## Notes

- Every task uses the required `- [ ] T###` checklist format.
- `[P]` means the task touches independent files and has no dependency on an
  incomplete task in its phase.
- `[US#]` maps a task to the corresponding story in `spec.md`.
- Tests are included because the constitution requires verification for risky
  delivery, identity, and rollback behavior.
- No task grants CI Terraform or cluster-admin permissions; platform bootstrap
  remains a separately approved responsibility.
