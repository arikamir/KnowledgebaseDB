# Tasks: DevOps Career Agent UI

**Input**: Design documents from `/specs/003-develop-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tests**: Required by the specification and constitution for journeys, security, retention, concurrency, accessibility, and deployment.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish three independently buildable application projects.

- [ ] T001 Create the React/TypeScript/Vite UI project in ui/package.json, ui/tsconfig.json, ui/vite.config.ts, and ui/src/
- [ ] T002 [P] Create the TypeScript/Fastify BFF project in bff/package.json, bff/tsconfig.json, and bff/src/
- [ ] T003 [P] Add core authentication, PostgreSQL, Alembic, and test dependencies in pyproject.toml
- [ ] T004 [P] Configure UI lint, typecheck, Vitest, and Playwright in ui/package.json, ui/eslint.config.js, and ui/playwright.config.ts
- [ ] T005 [P] Configure BFF lint, typecheck, unit, contract, and integration tests in bff/package.json and bff/eslint.config.js
- [ ] T006 [P] Create independent container builds in ui/Dockerfile, bff/Dockerfile, and .dockerignore
- [ ] T007 [P] Add local Redis/PostgreSQL/UI/BFF/core services in compose.yaml
- [ ] T008 [P] Add safe runtime configuration examples in ui/public/runtime-config.example.json, bff/.env.example, and .env.example
- [ ] T009 Document local installation and commands in README.md

**Checkpoint**: UI, BFF, and core install and start independently.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared identity, persistence, lifecycle, contracts, and Azure platform.

**CRITICAL**: No user-story implementation starts before this phase passes.

### Tests

- [ ] T010 [P] Add delegated-token and endpoint-to-machine-role authorization matrices in tests/contract/test_core_authorization.py
- [ ] T011 [P] Add login, callback, CSRF, logout, 30-minute idle, and 8-hour expiry tests in bff/tests/integration/auth-session.test.ts
- [ ] T012 [P] Add owner isolation and departed-identity denial tests in tests/integration/test_identity_lifecycle.py
- [ ] T013 [P] Add concurrent replay, changed-payload, and first-valid idempotency tests in tests/integration/test_idempotency.py
- [ ] T014 [P] Add active/disabled/deleted/throttled Entra reconciliation tests in tests/integration/test_directory_reconciliation.py
- [ ] T015 [P] Add 90-day deletion/anonymization and restore catch-up tests in tests/integration/test_retention.py
- [ ] T016 [P] Add three-service routing, health, image, and NetworkPolicy tests in tests/contract/test_three_service_deployment.py
- [ ] T017 [P] Add AKS version, capacity, OIDC, networking, Gateway API, ACR, provider-registration, and quota preflight contracts in tests/contract/test_azure_ui_preflight.py
- [ ] T018 [P] Add BFF confidential-client, core protected-API, delegated-scope, redirect-URI, and application-role registration contracts in tests/contract/test_entra_application_registrations.py
- [ ] T019 [P] Add Application Gateway for Containers association, frontend, subnet, DNS, certificate, and private-core routing contracts in tests/contract/test_application_gateway.py
- [ ] T020 [P] Add BFF certificate creation, public-key registration, CSI mount, overlap, rotation, and retired-key rejection contracts in tests/contract/test_bff_certificate_lifecycle.py
- [ ] T021 [P] Add 24-hour overlap, replica convergence, 48-hour retirement, failed-token-acquisition quarantine/operator-release, and emergency-revocation contracts in tests/contract/test_bff_certificate_rotation_policy.py
- [ ] T022 [P] Add saved, saving, unsaved, failed-save, navigation, and refresh coverage in ui/tests/e2e/persistence-status.spec.ts
- [ ] T023 [P] Add lab HTTPS, redirect, approved-domain, 10-second timeout, two-retry, 24-hour cadence, three-consecutive-failure, recovery, metadata, and publication-state tests in tests/integration/test_lab_reference_validation.py
- [ ] T024 [P] Add provider approval, versioning, redirect-domain, omission-reason, and audit contracts in tests/contract/test_lab_provider_policy.py
- [ ] T025 [P] Add empty-default, configured-group membership, distinct-human dual approval, missing approval, self-approval, domain-expansion, membership-evidence, and policy-version tests in tests/contract/test_lab_provider_approval.py
- [ ] T026 [P] Add forbidden UI-to-core, UI-to-storage, BFF-to-storage, and cross-service source dependency tests in tests/contract/test_service_architecture_boundaries.py
- [ ] T027 [P] Add UI/BFF/core resource request, limit, HPA, PDB, replica, and topology-spread contracts in tests/contract/test_aks_workload_resilience.py
- [ ] T028 [P] Add browser-facing gateway certificate expiry, overlap, reload, rollback, and retired-certificate rejection contracts in tests/contract/test_gateway_certificate_rotation.py

### Core foundation

- [ ] T029 Create Alembic configuration and baseline migration in alembic.ini, alembic/env.py, and alembic/versions/003_baseline.py
- [ ] T030 Add identity, machine, idempotency, reconciliation, and retention ORM models in src/storage/identity_models.py and src/storage/operation_models.py
- [ ] T031 Add lifecycle/idempotency constraints and indexes in alembic/versions/004_identity_lifecycle_idempotency.py
- [ ] T032 Add lab-reference, link-report, provider-approval with approver/group identity evidence, and validation-history models in src/storage/lab_models.py
- [ ] T033 Add lab-reference constraints, distinct provider-approver enforcement, and validation-state indexes in alembic/versions/005_lab_references.py
- [ ] T034 Implement active-reference lookup, consecutive-failure updates, recovery, and reporting persistence in src/storage/lab_repository.py
- [ ] T035 Implement strict tenant JWKS and delegated/app-only validation in src/auth/bearer.py
- [ ] T036 Implement separate employee-scope and machine-role dependencies in src/api/routes/authz.py
- [ ] T037 Implement machine-role definitions and approved-client policy in src/auth/machine_roles.py
- [ ] T038 Apply `/api/v1` routing and authorization dependencies in src/api/router.py and src/api/app.py
- [ ] T039 Implement active owner lookup and machine allowlisting in src/storage/identity_repository.py
- [ ] T040 Implement transactional actor/operation idempotency in src/storage/idempotency_repository.py and src/api/idempotency.py
- [ ] T041 Implement PostgreSQL Entra token and pool refresh in src/storage/database.py
- [ ] T042 Implement problem-details, correlation, and safe logging middleware in src/api/errors.py and src/api/middleware.py
- [ ] T043 Add foundational owned profile, roadmap, and milestone ORM models plus deterministic owned-roadmap and published-learning-content fixtures in src/storage/roadmap_models.py, tests/fixtures/owned_roadmaps.py, and tests/fixtures/published_learning_content.py
- [ ] T044 Add owned profile, roadmap, milestone, ownership, and fixture-compatible constraints in alembic/versions/006_owned_roadmaps.py

### Identity and platform prerequisites

- [ ] T045 Implement read-only Azure and AKS readiness reporting in scripts/azure/preflight-ui-platform.sh
- [ ] T046 Provision Key Vault, Managed Redis, PostgreSQL, private networking, and monitoring in infra/azure/key-vault.tf, infra/azure/redis.tf, infra/azure/postgresql.tf, infra/azure/private-networking.tf, and infra/azure/monitoring.tf
- [ ] T047 Provision the delivery-evidence container, custom evidence-writer role, Azure ABAC environment/stage prefix conditions, immutable-storage policy, and Entra-group reader RBAC in infra/azure/delivery-evidence-storage.tf
- [ ] T048 Assign the configured Evidence Hold Managers Entra group a custom role limited to hold metadata and permitted immutable-policy extension in infra/azure/delivery-evidence-hold-managers.tf and infra/azure/outputs.tf
- [ ] T049 Enable AKS OIDC and distinct BFF/core/gateway identities in infra/azure/identity.tf
- [ ] T050 Provision the Application Gateway for Containers frontend, association, subnet delegation, and managed identity in infra/azure/application-gateway-for-containers.tf
- [ ] T051 Provision gateway certificate access and DNS records in infra/azure/gateway-certificates.tf and infra/azure/gateway-dns.tf
- [ ] T052 Implement browser-facing gateway certificate expiry alerts, overlap, activation, reload verification, rollback, and retired-version removal in infra/azure/gateway-certificates.tf and scripts/azure/rotate-gateway-certificate.sh
- [ ] T053 Provision or import the BFF confidential-client registration, exact redirect/logout URIs, and non-secret outputs in infra/azure/entra-bff-registration.tf
- [ ] T054 Provision or import the core protected-API registration, delegated scope, audience, and service principal in infra/azure/entra-core-api-registration.tf
- [ ] T055 Configure BFF delegated permission, administrative-consent bootstrap outputs, machine registrations, and application roles in infra/azure/entra-machine-registrations.tf and infra/azure/entra-app-roles.tf
- [ ] T056 Provision the Key Vault BFF client certificate and rotation policy in infra/azure/bff-client-certificate.tf and infra/azure/bff-certificate-rotation.tf
- [ ] T057 Register only the BFF certificate public key with Entra in infra/azure/entra-bff-registration.tf
- [ ] T058 Configure the BFF Key Vault CSI mount in deploy/k8s/base/bff/secret-provider-class.yaml and deploy/k8s/base/bff/deployment.yaml

### BFF and UI foundation

- [ ] T059 Generate and wrap the core OpenAPI client in bff/src/clients/core-client.ts and bff/src/contracts/core-api.ts
- [ ] T060 Implement encrypted Redis sessions and owner session indexes in bff/src/sessions/session-store.ts
- [ ] T061 Implement atomic idle touch, absolute expiry, logout, and owner revocation in bff/src/sessions/session-policy.ts
- [ ] T062 Implement Entra authorization code, state, nonce, PKCE, and certificate auth in bff/src/auth/entra.ts
- [ ] T063 Implement host-only cookie, Origin, CSRF, and session middleware in bff/src/auth/browser-session.ts
- [ ] T064 Implement auth, session, BFF capability advertisement, and health routes in bff/src/routes/auth.ts, bff/src/routes/capabilities.ts, and bff/src/routes/health.ts
- [ ] T065 Implement core capability/version metadata, UI/BFF and BFF/core version headers and pre-idempotency `409 CONTRACT_VERSION_UNSUPPORTED` gates, plus UI incompatible-write blocking with unsaved-input preservation in src/api/routes/capabilities.py, bff/src/compatibility/core-version.ts, bff/src/plugins/contract-version.ts, and ui/src/app/compatibility.ts
- [ ] T066 Add multi-replica certificate rollover, active-session and new-sign-in continuity, delegated token acquisition, retired-key rejection, and emergency-reauthentication verification in bff/tests/integration/certificate-rotation.test.ts
- [ ] T067 Implement certificate-version convergence and rotation readiness in bff/src/auth/certificate-rotation.ts
- [ ] T068 Implement normal and emergency certificate retirement in scripts/azure/rotate-bff-client-certificate.sh
- [ ] T069 Implement failed BFF certificate-candidate quarantine, auditable quarantine reasons, and explicit operator release before retry in bff/src/auth/certificate-rotation.ts and scripts/azure/rotate-bff-client-certificate.sh
- [ ] T070 Implement error mapping, trace, timeout, and idempotency propagation in bff/src/clients/core-request.ts
- [ ] T071 Implement validated runtime configuration and BFF-only HTTP access in ui/src/app/runtime-config.ts and ui/src/bff/client.ts
- [ ] T072 Create responsive accessible shell, direct entry points for all four journeys, status region, and expiry handling in ui/src/app/App.tsx and ui/src/styles/app.css
- [ ] T073 Implement reusable saved, saving, unsaved, and failed-save semantics in ui/src/components/PersistenceStatus.tsx and ui/src/app/persistence-state.ts

### Lifecycle and Azure foundation

- [ ] T074 Implement checkpointed daily Entra reconciliation in src/lifecycle/reconcile_directory.py
- [ ] T075 Implement departed-user blocking, session revocation, and retention scheduling in src/lifecycle/employee_lifecycle.py
- [ ] T076 Implement the record-level deletion/anonymization matrix and restore catch-up in src/lifecycle/retention.py
- [ ] T077 Create the empty initial allowlist and approval schema with configured Entra group IDs, distinct approver IDs, membership evidence, policy version, and audit reference in config/approved-lab-providers.yaml and config/lab-provider-policy.schema.json
- [ ] T078 Implement lab applicability, Entra-group approval validation, distinct-approver enforcement, and provider policy in src/agent/lab_provider_policy.py
- [ ] T079 Implement publication validation, 24-hour scheduled revalidation, consecutive-failure tracking, unavailable transitions, and recovery in src/agent/lab_reference_validator.py and src/lifecycle/revalidate_labs.py
- [ ] T080 Integrate provider-policy version and omission reasons into src/agent/lab_reference_validator.py and src/storage/lab_repository.py
- [ ] T081 Create independent UI/BFF/core workloads and lifecycle CronJobs in deploy/k8s/base/ui/, deploy/k8s/base/bff/, deploy/k8s/base/core/, and deploy/k8s/base/lifecycle/
- [ ] T082 Configure UI/BFF/core requests, limits, minimum replicas, HPAs, PDBs, and topology-spread constraints in deploy/k8s/base/ui/deployment.yaml, deploy/k8s/base/ui/hpa.yaml, deploy/k8s/base/ui/pdb.yaml, deploy/k8s/base/bff/deployment.yaml, deploy/k8s/base/bff/hpa.yaml, deploy/k8s/base/bff/pdb.yaml, deploy/k8s/base/core/deployment.yaml, deploy/k8s/base/core/hpa.yaml, and deploy/k8s/base/core/pdb.yaml
- [ ] T083 Create Gateway, service accounts, ConfigMaps, and digest overlays in deploy/k8s/overlays/aks-nonprod/
- [ ] T084 Bind Gateway API resources to the Azure association in deploy/k8s/overlays/aks-nonprod/gateway.yaml and deploy/k8s/overlays/aks-nonprod/httproute.yaml
- [ ] T085 Enforce default-deny and private machine routing in deploy/k8s/base/network-policies.yaml and deploy/k8s/overlays/aks-nonprod/private-machine-route.yaml

**Checkpoint**: Foundation passes and unblocks all stories.

---

## Phase 3: User Story 1 - Create a Career Roadmap (Priority: P1) MVP

**Goal**: Create and display an owned roadmap through UI -> BFF -> core.
**Independent Test**: Sign in, submit a valid profile, and verify roadmap, validation, preserved input, owner isolation, retry, keyboard, mobile, and outage behavior.

### Tests

- [ ] T086 [P] [US1] Add core roadmap ownership/idempotency contracts in tests/contract/test_roadmap_v1_contract.py
- [ ] T087 [P] [US1] Add BFF roadmap validation and mapping contracts in bff/tests/contract/roadmaps.test.ts
- [ ] T088 [P] [US1] Add roadmap browser, keyboard, 320/375/768/1024/1440/1920px, and outage tests in ui/tests/e2e/roadmap.spec.ts
- [ ] T089 [P] [US1] Add owned persistence and cross-employee denial tests in tests/integration/test_owned_roadmap_flow.py

### Implementation

- [ ] T090 [US1] Implement owned roadmap and milestone persistence against the foundational roadmap schema in src/storage/roadmap_repository.py
- [ ] T091 [US1] Implement authenticated idempotent roadmap creation in src/agent/roadmap_service.py and src/api/routes/roadmap.py
- [ ] T092 [US1] Implement BFF roadmap validation and composition in bff/src/routes/roadmaps.ts and bff/src/contracts/roadmap.ts
- [ ] T093 [P] [US1] Implement accessible profile/roadmap form in ui/src/features/roadmap/RoadmapForm.tsx
- [ ] T094 [P] [US1] Implement roadmap, milestones, loading, and error result in ui/src/features/roadmap/RoadmapResult.tsx
- [ ] T095 [US1] Implement preserved state and same-key retry in ui/src/features/roadmap/useRoadmap.ts
- [ ] T096 [US1] Connect the roadmap route in ui/src/app/routes.tsx
- [ ] T097 [US1] Integrate persistence status into ui/src/features/roadmap/RoadmapForm.tsx and ui/src/features/roadmap/useRoadmap.ts
- [ ] T098 [US1] Add roadmap trace, latency, outcome, and safe-error telemetry in bff/src/routes/roadmaps.ts and src/api/routes/roadmap.py
- [ ] T099 [US1] Record independent MVP verification steps in specs/003-develop-ui/quickstart.md

**Checkpoint**: User Story 1 is deployable as the MVP.

---

## Phase 4: User Story 2 - Explore Skill Guidance (Priority: P2)

**Goal**: Request focused guidance and preview complete external-lab metadata.
**Independent Test**: Request guidance without a roadmap and verify profile reuse, invalid topics, results, and lab preview.

### Tests

- [ ] T100 [P] [US2] Add core guidance contracts in tests/contract/test_guidance_v1_contract.py
- [ ] T101 [P] [US2] Add BFF guidance/error contracts in bff/tests/contract/guidance.test.ts
- [ ] T102 [P] [US2] Add guidance, reuse, lab, keyboard, outage, and 320/375/768/1024/1440/1920px coverage in ui/tests/e2e/guidance.spec.ts

### Implementation

- [ ] T103 [US2] Implement authenticated idempotent guidance in src/agent/skill_guidance_service.py and src/api/routes/skills.py
- [ ] T104 [US2] Implement BFF guidance composition in bff/src/routes/guidance.ts and bff/src/contracts/guidance.ts
- [ ] T105 [P] [US2] Implement accessible guidance form in ui/src/features/guidance/GuidanceForm.tsx
- [ ] T106 [P] [US2] Implement guidance and lab preview in ui/src/features/guidance/GuidanceResult.tsx and ui/src/features/labs/LabReferenceCard.tsx
- [ ] T107 [US2] Implement editable shared profile state in ui/src/app/profile-context.tsx and ui/src/features/guidance/useGuidance.ts
- [ ] T108 [US2] Connect guidance and safe external links in ui/src/app/routes.tsx
- [ ] T109 [US2] Integrate persistence status into ui/src/features/guidance/GuidanceForm.tsx and ui/src/features/guidance/useGuidance.ts
- [ ] T110 [US2] Add guidance and lab telemetry in bff/src/routes/guidance.ts and src/api/routes/skills.py

**Checkpoint**: User Story 2 works without a saved roadmap.

---

## Phase 5: User Story 3 - Complete a Focused Learning Session (Priority: P2)

**Goal**: Complete/resume a 20-30 minute session, lab, and 3-5 question review with an 80% threshold.
**Independent Test**: Using foundational owned-roadmap and published-learning-content fixtures, start, record, resume, report a lab, answer/retry, pass, and verify one milestone and roadmap-aware next action without US1 implementation.

### Tests

- [ ] T111 [P] [US3] Add learning/review/lab/next-action contracts in tests/contract/test_learning_v1_contract.py
- [ ] T112 [P] [US3] Add atomic scoring, retry, resume, and idempotency tests in tests/integration/test_learning_session_flow.py
- [ ] T113 [P] [US3] Add BFF composition and answer non-disclosure tests in bff/tests/contract/learning.test.ts
- [ ] T114 [P] [US3] Add session, resume, lab, review, keyboard, outage, and 320/375/768/1024/1440/1920px coverage in ui/tests/e2e/learning-session.spec.ts
- [ ] T115 [P] [US3] Add 20-30-minute required-content timing boundaries plus optional-material, external-lab, interruption, and retry exclusion accounting in tests/integration/test_learning_session_timing.py

### Implementation

- [ ] T116 [P] [US3] Add learning-session, step, review, answer, and milestone models in src/storage/learning_models.py
- [ ] T117 [US3] Add learning constraints and indexes in alembic/versions/007_learning_sessions.py
- [ ] T118 [US3] Implement owner-scoped learning persistence in src/storage/learning_repository.py
- [ ] T119 [US3] Implement start/resume, steps, and lab reports in src/agent/learning_service.py
- [ ] T120 [US3] Implement atomic scoring, 80% completion, and retry in src/agent/review_service.py
- [ ] T121 [US3] Implement exactly-one next-action policy in src/agent/next_action.py
- [ ] T122 [US3] Implement core learning endpoints in src/api/routes/learning.py
- [ ] T123 [US3] Implement BFF learning/review/lab routes in bff/src/routes/learning.ts
- [ ] T124 [P] [US3] Implement objective, duration, steps, and resume UI in ui/src/features/learning/LearningSession.tsx
- [ ] T125 [P] [US3] Implement lab preview/report UI in ui/src/features/labs/LabExperience.tsx
- [ ] T126 [P] [US3] Implement review, feedback, and retry UI in ui/src/features/review/SessionReview.tsx
- [ ] T127 [US3] Implement celebration and next action in ui/src/features/learning/CompletionPanel.tsx
- [ ] T128 [US3] Connect learning routes and interruption recovery in ui/src/app/routes.tsx and ui/src/features/learning/useLearningSession.ts
- [ ] T129 [US3] Integrate persisted-step and unsaved-review status into ui/src/features/learning/LearningSession.tsx and ui/src/features/learning/useLearningSession.ts
- [ ] T130 [US3] Add learning, review, lab, duration, retry, outcome, trace, and safe-error telemetry in bff/src/routes/learning.ts and src/api/routes/learning.py

**Checkpoint**: User Story 3 proves the complete learning loop.

---

## Phase 6: User Story 4 - Record and Review Progress (Priority: P3)

**Goal**: Submit an owned roadmap check-in and see status, gaps, milestones, and next action.
**Independent Test**: Verify successful, missing, foreign, retry, navigation, keyboard, and mobile scenarios with a seeded roadmap.

### Tests

- [ ] T131 [P] [US4] Add owned progress contracts in tests/contract/test_progress_v1_contract.py
- [ ] T132 [P] [US4] Add BFF progress/idempotency contracts in bff/tests/contract/progress.test.ts
- [ ] T133 [P] [US4] Add check-in, preservation, milestone, keyboard, outage, and 320/375/768/1024/1440/1920px coverage in ui/tests/e2e/progress.spec.ts

### Implementation

- [ ] T134 [US4] Add owned progress persistence in src/storage/progress_repository.py and alembic/versions/008_owned_progress.py
- [ ] T135 [US4] Implement authenticated progress review in src/agent/progress_service.py and src/api/routes/progress.py
- [ ] T136 [US4] Implement BFF progress mapping in bff/src/routes/progress.ts and bff/src/contracts/progress.ts
- [ ] T137 [P] [US4] Implement accessible preserved-note form in ui/src/features/progress/ProgressForm.tsx
- [ ] T138 [P] [US4] Implement status/gap/milestone result in ui/src/features/progress/ProgressReview.tsx
- [ ] T139 [US4] Integrate progress state and route in ui/src/features/progress/useProgress.ts and ui/src/app/routes.tsx
- [ ] T140 [US4] Integrate persistence status into ui/src/features/progress/ProgressForm.tsx and ui/src/features/progress/useProgress.ts
- [ ] T141 [US4] Add progress trace and denial telemetry in bff/src/routes/progress.ts and src/api/routes/progress.py

**Checkpoint**: All four stories are independently functional.

---

## Phase 7: Polish and Cross-Cutting Verification

- [ ] T142 [P] Add cross-journey navigation, landing-page, timeout-dialog, error-state, and 320/375/768/1024/1440/1920px accessibility coverage in ui/tests/e2e/accessibility.spec.ts
- [ ] T143 [P] Add token leakage, CSP, cookie, Origin, and CSRF tests in ui/tests/e2e/security.spec.ts and bff/tests/integration/browser-security.test.ts
- [ ] T144 [P] Add Redis/PostgreSQL Entra refresh tests in bff/tests/integration/redis-entra.test.ts and tests/integration/test_postgres_entra.py
- [ ] T145 [P] Add machine outage independence/private route tests in tests/integration/test_machine_consumer_flow.py
- [ ] T146 [P] Add supported and unsupported UI/BFF and BFF/core capability-range, version-header, pre-downstream-call, pre-idempotency, pre-mutation, and unsaved-input compatibility tests in tests/contract/test_version_compatibility.py
- [ ] T147 [P] Add outage diagnosis and trace continuity tests in tests/integration/test_service_outages.py
- [ ] T148 [P] Add 10-user concurrency, browser fetch-resolution-to-accessibility-tree performance marks, 95th-percentile result-render timing, and separate backend-latency verification in tests/integration/test_ui_feature_performance.py
- [ ] T149 [P] Add UI-only, BFF-only, core-only, multi-service, shared-contract, shared-build, documentation-only, first-build, missing-baseline, and audited rebuild-all change-plan tests in tests/ci/test_change_plan.py
- [ ] T150 [P] Add protected-ref, validation-only PR, cancellation, agent-loss, Azure-denial, stale-build, concurrent-build, digest-only, controller-audit lifecycle/recovery, evidence-gate failure, evidence-completeness, forward/reverse mutation-journal, ordered-rollout, and scoped-rollback contracts in tests/ci/test_jenkins_delivery.py
- [ ] T151 [P] Add Jenkins cloud `azure`, provisioning-service-principal scope/expiry, publisher/deployer ACI template, provisioning/connection failure, wrong-template, wrong-UAMI, wrong-subscription, forbidden ACR/AKS access, and Azure-RBAC-denial tests in tests/ci/test_jenkins_azure_agent.py
- [ ] T152 [P] Add exact-template, missing-identity, additional-identity, swapped-identity, and system-assigned-identity rejection tests in tests/ci/test_jenkins_aci_identity_binding.py
- [ ] T153 [P] Add 30/14/7-day warning, under-30-day rejection, credential-management identity least privilege, protected-input and log-redaction checks, Jenkins-update failure safety, both-template validation before normal revocation, retired-credential denial, emergency lockout, and temporary-material cleanup tests in tests/ci/test_jenkins_cloud_credential_lifecycle.py
- [ ] T154 [P] Add evidence authorization, hold-manager least privilege, writer read/list denial, cross-prefix denial, immutable-path overwrite/delete denial, immutable-policy enforcement, 90-day deletion, malformed and unauthorized holds, 180-day ceiling, hold expiry/release, and prohibited-content tests in tests/ci/test_delivery_evidence_retention.py
- [ ] T155 [P] Add per-service availability, latency, error-rate, dependency, certificate-expiry, reconciliation, and lab-validation alert contracts in tests/contract/test_azure_monitor_alerts.py
- [ ] T156 Implement merge-base classification and immutable change-plan output in scripts/ci/detect-changes.sh and selected-service validation dispatch in scripts/ci/validate-service.sh
- [ ] T157 Implement changed-image build, scan, SBOM, ACR push, digest resolution, and release-manifest generation in scripts/ci/build-publish.sh
- [ ] T158 Implement authoritative Azure Storage evidence upload, immutable path construction, atomic `If-None-Match: *` creation, overwrite rejection, and prohibited-content validation in scripts/ci/publish-evidence.sh and scripts/ci/validate-evidence.sh
- [ ] T159 Implement digest-only promotion, current-digest snapshot, ordered core-to-BFF-to-UI rollout, smoke verification, append-only forward/reverse mutation journaling, and scoped rollback in scripts/ci/promote.sh, scripts/ci/deploy.sh, scripts/ci/verify.sh, scripts/ci/mutation-journal.sh, and scripts/ci/rollback.sh
- [ ] T160 Implement mandatory pre-promotion, pre-mutation, post-mutation, verification, and rollback evidence gates in scripts/ci/evidence-gate.sh and scripts/ci/publish-evidence.sh
- [ ] T161 Implement controller audit creation, monotonic stage updates, terminal finalization, restart recovery, and retention cleanup in scripts/ci/manage-controller-audit.sh
- [ ] T162 Implement protected-ref, validation-only PR, fail-fast, controller-audit lifecycle, authenticated-agent evidence milestones and gates, reverse-mutation journal enforcement, environment-lock, `azure-aci-publisher`, and `azure-aci-deployer` stage boundaries in Jenkinsfile
- [ ] T163 Provision distinct publisher/deployer user-assigned identities and least-privilege ACR/AKS plus path-scoped evidence-create assignments in infra/azure/jenkins-agent-identities.tf
- [ ] T164 Validate Jenkins cloud `azure`, provisioning-service-principal scope/expiry/denials, configured resource group, ACI templates, managed identities, and target environment in scripts/jenkins/verify-agent.sh and scripts/jenkins/verify-managed-identity.sh
- [ ] T165 Bind publisher and deployer Terraform identity outputs to the `azure-aci-publisher` and `azure-aci-deployer` templates under Jenkins cloud `azure` and record the controlled procedure in docs/jenkins-azure-cloud.md
- [ ] T166 Validate live Jenkins template and running ACI identity resource IDs in scripts/jenkins/verify-aci-identity-binding.sh
- [ ] T167 Implement provisioning-service-principal expiry and scope inspection in scripts/jenkins/verify-cloud-credential.sh
- [ ] T168 Configure a dedicated Jenkins credential-management identity with permission limited to the stable Azure cloud credential entry in scripts/jenkins/configure-credential-manager.groovy and docs/jenkins-credential-manager.md
- [ ] T169 Configure tag-based 90-day deletion and bounded 180-day incident-hold lifecycle behavior and metadata in infra/azure/delivery-evidence-storage.tf
- [ ] T170 Implement authorized evidence hold creation, validation, release, audit, and expiry in scripts/ci/manage-evidence-hold.sh
- [ ] T171 Implement normal and emergency Jenkins Azure cloud-credential rotation in scripts/jenkins/rotate-cloud-credential.sh using a least-privilege credential-management identity, localhost Jenkins API authentication, CSRF protection, stable credential ID, protected-standard-input or file-descriptor secret handoff, log redaction, cleanup traps, an audited rotation-only smoke-agent path that cannot run jobs/publish/deploy, publisher/deployer ACI verification, retired-credential revocation, and ordinary-provisioning quarantine
- [ ] T172 Configure per-service availability, latency, error-rate, dependency, certificate-expiry, reconciliation, and lab-validation alerts with actionable routing in infra/azure/monitoring.tf
- [ ] T173 [P] Validate Gateway, private core, identities, health, PDB, topology, policies, and digest-only workload references in tests/contract/test_aks_ui_manifests.py
- [ ] T174 [P] Verify application identity isolation plus Jenkins publisher/deployer least privilege and denial boundaries in tests/integration/test_azure_identity_boundaries.py
- [ ] T175 Run all application and Jenkins delivery checks and record non-secret evidence in specs/003-develop-ui/verification.md
- [ ] T176 Document the local Jenkins controller, cloud `azure`, ACI templates, managed identities, deployment, reconciliation, retention, key rotation, incident handling, and rollback in docs/operations-ui.md
- [ ] T177 Update developer, Jenkins job setup, local pipeline verification, and architecture guidance in README.md and specs/003-develop-ui/quickstart.md
- [ ] T178 Define eligibility, recruitment, exactly-20-participant sampling, replacement rules, exclusions, task scripts, assistance rules, timing boundaries, questionnaire wording, and calculations in specs/003-develop-ui/usability-study.md
- [ ] T179 Record anonymized pilot observations and calculate SC-001, SC-007, SC-011, and SC-015 through SC-017 outcomes in specs/003-develop-ui/usability-results.md

---

## Dependencies and Execution Order

- Setup starts immediately; Foundation depends on Setup and blocks all stories.
- US1, US2, US3, and US4 depend only on Foundation and can then run in parallel.
- Foundational roadmap models, schema, and fixtures T043-T044 must complete before
  US1 persistence T090, independently seeded US3 work T111-T130, and independently
  seeded US4 work T131-T141.
- Polish depends on every story selected for release.
- Azure provisioning T046-T058 depends on readiness contracts and reporting in
  T017 and T045. Browser-certificate rotation T052 additionally depends on its
  contract T028 and gateway resources T050-T051.
- BFF authentication T062 and certificate work T066-T069 depend on Entra and
  certificate contracts T018 and T020-T021 plus infrastructure T053 and
  T056-T058. Compatibility implementation T065 depends on core routing T038,
  the generated client T059, and BFF capabilities T064.
- Workload resilience T082 depends on its contract T027 and base workloads T081.
  Application Gateway binding T084 depends on T019 and T050-T052.
- Machine-consumer verification T145 depends on machine authorization T037 and
  Entra roles T055. Lab policy and revalidation T077-T080 depend on tests
  T023-T025 and persistence T032-T034.
- Each story checkpoint requires its full phase: T086-T099 for US1, T100-T110
  for US2, T111-T130 for US3, and T131-T141 for US4.
- Jenkins and monitoring tests T149-T155 precede implementation T156-T172.
  Change classification T156 precedes publishing T157; evidence publication
  T158 and the mutation journal T159 precede gates T160; T156-T161 precede the
  Jenkinsfile integration T162. Promotion T159 also depends on overlays
  T083-T084.
- Jenkins identities T163 and template binding T165 precede live binding
  validation T166 and identity verification T174. Credential inspection T167
  and credential-manager configuration T168 precede rotation T171.
- Evidence lifecycle T169 and hold operations T170 depend on the evidence store
  and hold-manager group assignment T047-T048. Alert implementation T172 depends on
  monitoring infrastructure T046 and alert contracts T155.
- Manifest and identity verification T173-T174 must pass before release
  verification T175. Operations and developer documentation T176-T177 follow
  verified behavior.
- Pilot evidence T179 depends on the approved study protocol in T178.

```text
Setup -> Foundation -> US1 (MVP)
                    |-> US2
                    |-> US3
                    `-> US4
Selected stories -> Polish and release verification
```

### Within each story

- Write tests first and confirm they fail for the intended reason.
- Apply models/migrations before repositories and services.
- Implement core authority before BFF composition and UI integration.
- Pass the independent test before advancing the story checkpoint.

## Parallel Execution Examples

```text
US1: T086 | T087 | T088 | T089, then T093 | T094, then T097
US2: T100 | T101 | T102, then T105 | T106, then T109
US3: T111 | T112 | T113 | T114 | T115, then T124 | T125 | T126, then T129
US4: T131 | T132 | T133, then T137 | T138, then T140
Cross-cutting tests: T142-T155, then T173 | T174 after T156-T172
```

## Implementation Strategy

### MVP first

1. Complete Setup and Foundation.
2. Complete US1.
3. Stop and validate roadmap creation independently.
4. Deploy all three services with only the roadmap journey enabled.

### Incremental delivery

1. Foundation establishes identity, persistence, lifecycle, Azure, and contracts.
2. Add US1 roadmap MVP, then US2 guidance, US3 learning, and US4 progress.
3. Complete the Jenkins delivery pipeline and run cross-cutting verification
   before the complete release.

## Notes

- `[P]` tasks target different files and may run concurrently.
- Every user-story task carries its `[USn]` label.
- Commit after each task or cohesive task group.
- Do not start story work before the Foundation checkpoint passes.
