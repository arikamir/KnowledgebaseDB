# Quickstart: Three-Service Learning UI

> Delivery commands involving a local controller, ACI agents, or direct cluster
> promotion are obsolete. Follow `docs/github-actions-azure.md` and
> `specs/006-argocd-gitops-delivery/quickstart.md`.

## Goal

Run UI, BFF, and core as independent local services, verify all four learning
journeys, and prove that browser traffic cannot bypass the BFF.

## Prerequisites

- Node.js 24 LTS and npm
- Python 3.11 and uv
- Redis
- Docker for container verification
- kubectl for manifest rendering/deployment checks
- Terraform 1.7+ for the external Platform Operations bootstrap; use the
  committed provider lock file and configured Azure Storage backend
- Helm for the pinned ALB Controller installation
- Azure CLI access to the target AKS, ACR, Key Vault, Azure Managed Redis,
  PostgreSQL, and Azure Monitor resources
- GitHub Actions protected environments with OIDC federation to the declared
  least-privilege Azure identities
- A Platform Operations interactive Entra identity authorized to apply/import
  Terraform, grant the required Entra/data-plane roles, install the declared
  controller/guardrails, and invoke the sole finalization command that emits the
  reviewed non-secret bootstrap manifest through time-bounded PIM assignments. Use a
  separate JIT Privileged Role Administrator approver for Graph application
  consent; do not use Owner/Global Administrator or a GitHub Actions identity

## Normative implementation gates

Before implementing, testing, opening the pilot, or enabling protected delivery,
read and validate both of these authorities:

- [Implementation readiness contract](./contracts/implementation-readiness-contract.md):
  apply every journey/dependency outcome, stable code, numeric bound, owner,
  evidence field, SLO measurement rule, prerequisite freshness rule, and failure
  effect without local reinterpretation.
- [Requirements traceability matrix](./requirements-traceability.md): verify
  exactly one ordered row for each `FR-001` through `FR-075` and `SC-001`
  through `SC-049`, with a nonempty normative source, implementation task,
  positive/negative verification task, and retained-evidence disposition.
  Reject empty, duplicate, out-of-order, or unknown task IDs outside the current
  `T001`-`T198` sequence.

The readiness contract also freezes two approved test inputs: the
[universal scenario manifest](../../tests/fixtures/readiness-scenario-manifest-v1.yaml)
and [core performance profile](../../tests/performance/performance-profile-v1.json),
plus the [interaction performance profile](../../tests/performance/interaction-performance-profile-v1.json)
and its [digest-bound fixture set](../../tests/performance/interaction-performance-fixtures-v1.json).
Recompute the manifest digest, every derived per-case fixture digest, the
performance profiles' full-profile/fixture-set digests, the interaction fixture
set's exact-byte digest and derivation rules, and their pinned
BFF/core contract-byte digests; regenerate and digest the mapper; and reject
schema, evidence-field, operation-set, mapper, case-count, fixture, assignment,
or timeout drift before implementation or verification.

A conflict between either authority and an OpenAPI, authentication, learning, or
GitHub Actions delivery contract blocks implementation and release. Record the
validation result with the build/pilot evidence; a checklist pass or an
assumption from planning is not a substitute.

## Local configuration

### Core

```text
ENVIRONMENT=development
AUTH_MODE=fake
DATABASE_URL=sqlite:///./devops_career_agent.db
CORE_API_VERSION=1
```

### BFF

```text
ENVIRONMENT=development
AUTH_MODE=fake
CORE_BASE_URL=http://127.0.0.1:8000/api/v1
CORE_API_RANGE=1.x
CORE_CAPABILITIES_PATH=/capabilities
REDIS_URL=redis://127.0.0.1:6379/0
UI_ORIGIN=http://127.0.0.1:4173
COOKIE_SECURE=false
```

### UI runtime config

```json
{"bffBasePath":"/bff/v1","bffContractRange":"1.x"}
```

Fake auth is rejected outside local/test environments.

## Start services

1. Start Redis.
2. Apply core migrations and start core:

   ```bash
   uv sync --extra test
   # US1/US2 foundation only:
   uv run alembic upgrade 006_owned_roadmaps
   # US3-only verification instead uses: uv run alembic upgrade learning@head
   # US4-only verification instead uses: uv run alembic upgrade progress@head
   # The complete local UI uses the explicit merge target:
   uv run alembic upgrade 009_merge_learning_progress
   uv run uvicorn api.app:app --reload --app-dir src --port 8000
   ```

   Start from the feature baseline for each isolated story verification; do not
   apply all four targets sequentially to one database. Bare `head` is invalid
   while the named sibling branches exist.

3. Install and start BFF:

   ```bash
   cd bff
   npm ci
   npm run dev
   ```

4. Install and start UI:

   ```bash
   cd ui
   npm ci
   npm run dev
   ```

Use the local reverse-proxy/dev configuration so browser requests to `/bff`
reach the BFF while no UI route reaches core directly.

## Verification

### Roadmap-only local MVP (non-release)

This checkpoint demonstrates only User Story 1. It is **not a protected release**
and does not claim that the T194 Azure/GitHub Actions release gate has passed.

1. Start PostgreSQL, Redis, core, BFF, and UI with `docker compose up --build`.
2. Open `http://localhost:5173/roadmaps` and sign in through the configured
   local/test identity adapter.
3. Enter a current role, experience level, target role, and weekly hours.
4. Submit once and verify the ordered roadmap and milestones are announced and
   remain keyboard accessible.
5. Refresh and verify the owner-scoped roadmap restores from core persistence.
6. Repeat with another employee fixture and verify the first employee's
   roadmap cannot be listed or retrieved.
7. Inject a core outage, retry with the same operation key, and verify entered
   profile values remain while the UI reports the indeterminate save state.

At this checkpoint navigation exposes only Home and Roadmap. Guidance,
learning, review, and progress routes remain inactive until their story gates
pass. Run the reproducible foundation and US1 checks with:

```bash
scripts/ci/validate-us1-foundation.sh
.venv/bin/pytest tests/contract/test_roadmap_v1_contract.py tests/integration/test_owned_roadmap_flow.py
npm --prefix bff test -- roadmaps.test.ts
npm --prefix ui run test:e2e -- --project=chromium-current tests/e2e/roadmap.spec.ts
```

```bash
scripts/ci/validate-api-contracts.sh
uv run pytest
npm --prefix bff run typecheck
npm --prefix bff test
npm --prefix ui run typecheck
npm --prefix ui test
npm --prefix ui run test:e2e
docker build -f Dockerfile -t career-agent-core:test .
docker build -f bff/Dockerfile -t career-agent-bff:test bff
docker build -f ui/Dockerfile -t career-agent-ui:test ui
kubectl kustomize deploy/k8s/overlays/aks-nonprod
```

Run these representative readiness suites as their implementation tasks land;
each group is a release gate rather than an optional smoke test:

```bash
# Readiness, dependency isolation, identity preflight, and recovery
uv run pytest tests/integration/test_service_outages.py \
  tests/contract/test_azure_ui_preflight.py \
  tests/integration/test_deployed_entra_rollover.py

# Actor-scoped concurrency, replay, and expired-result behavior
uv run pytest tests/integration/test_idempotency.py

# Browser persistence and the full accessibility/responsive boundary
npm --prefix ui run test:e2e -- persistence-status.spec.ts \
  navigation-session.spec.ts accessibility.spec.ts

# AKS disruption/scaling, certificate convergence, and external-lab recovery
uv run pytest tests/contract/test_aks_workload_resilience.py \
  tests/contract/test_gateway_certificate_rotation.py \
  tests/integration/test_lab_reference_validation.py

# GitHub Actions disk-loss recovery, unpromoted artifacts, rollback, and evidence
uv run pytest tests/ci/test_github_actions_delivery.py \
  tests/ci/test_delivery_evidence_retention.py
```

Verify:

- UI makes personalized requests only to `/bff/v1`.
- BFF session cookie is opaque, Secure in HTTPS, HttpOnly, and host-only.
- Missing/mismatched CSRF and Origin are rejected.
- Core rejects wrong audience/issuer/tenant/client/scope and spoofed identity.
- Core rejects disallowed algorithms, untrusted signing keys, invalid `nbf` or
  `exp`, ID tokens, and app-only tokens on employee-delegated routes.
- UI storage and network traces contain no Entra access, ID, or refresh token.
- BFF and core service accounts are bound to different Workload Identities.
- BFF identity can access only its Redis/Key Vault dependencies; core identity
  can access only its PostgreSQL/Key Vault dependencies; cross-access fails.
- Redis and PostgreSQL connections survive token refresh and reconnect without
  falling back to access keys or database passwords.
- Logout revokes the session across BFF replicas before Entra redirect, and a
  normal Key Vault encryption-key rotation preserves only sessions referencing
  the bounded decrypt-only overlap set; compromise revokes affected sessions and
  removes the key immediately after reference-free revocation completes.
- Session access expires after 30 idle minutes and at 8 absolute hours without
  deleting saved learning state; background polling does not extend it.
- Machine app-role tokens create/mutate only application-owned roadmap/progress
  state and succeed only on documented operations; employee/cross-application
  references, delegated, missing-role, wrong-client, and wrong-audience tokens
  fail.
- Entra disable/delete simulation blocks access and revokes sessions at sign-in
  or within the four-hour reconciliation plus 12-hour delivery deadline;
  transient lookup failures do not imply departure.
- Retention tests delete the EmployeeIdentity and all personalized/domain/
  idempotency/outbox owner-linked records by day 90, anonymize only security
  evidence after every link is removed, and preserve only non-reidentifiable
  aggregate telemetry; backup restore runs
  due retention before personalized access is enabled.
- Concurrent/replayed mutations with one key create one transition; changed
  payload reuse returns `409` and creates no state.
- Complete idempotency results replay identically for 30 days. After body
  expiry, same-hash replay returns `409 IDEMPOTENCY_RESULT_EXPIRED`, changed-hash
  replay returns `409 IDEMPOTENCY_KEY_REUSED`, neither executes again, and the
  key remains non-reusable across process/pod restart and parallel clients.
- Foundation migrations create owned-roadmap and stable-milestone identity before
  story migrations. US3 passes with deterministic owned-roadmap and published
  learning-content fixtures, and US4 passes with a deterministic owned-roadmap
  fixture even when US1 implementation is absent.
- Roadmap, guidance, learning session/review, and progress journeys pass.
- Missing, malformed, or disjoint UI/BFF or BFF/core capability ranges block
  state-changing requests; current and previous supported combinations pass.
- Dependency checks reject UI imports of BFF/core runtime code and BFF imports
  of core application code. A presentation-only UI change and a composition-only
  BFF change both build/test against an unchanged frozen core artifact.
- Local field guidance appears within 1,000 ms of the initiating event in every
  supported validation case. For at least 95% of successful roadmap and guidance
  results, no more than 1,000 ms elapses between
  `career.result.fetch-resolved`, recorded after parsing and validating the
  complete payload, and `career.result.accessible-render-committed`.
- SC-043 performance verification runs separate roadmap and guidance scenarios
  using the approved full-profile and fixture-set digest-verified
  [`performance-profile-v1`](../../tests/performance/performance-profile-v1.json),
  digest-matches its pinned BFF/core contracts, regenerates and drift-checks the
  mapper, records all three contract/mapper digests and 100 measured attempts per
  scenario after warm-up, applies its exact 45-second roadmap/20-second guidance
  cancellation policy, retains failures and timeouts in the denominator, and
  proves roadmap p95 is at most 30 seconds and guidance p95 is at most 10
  seconds. Universal cases load the approved
  [`readiness-scenario-manifest-v1`](../../tests/fixtures/readiness-scenario-manifest-v1.yaml)
  and fail on manifest-digest, derived per-case-fixture-digest, operation-set, or
  denominator drift.
- UI, BFF, and core outage states are distinguishable.
- Redis indeterminacy returns `503 SESSION_DEPENDENCY_UNAVAILABLE` without
  clearing the cookie or calling core; PostgreSQL failure returns `503
  PERSISTENCE_UNAVAILABLE` with no partial transaction. A signing key still
  unknown after the one trusted-issuer refresh returns token-type-specific `401
  DELEGATED_TOKEN_INVALID` or `401 MACHINE_TOKEN_INVALID`; unavailable or
  older-than-24-hour metadata without a bounded-fresh validating key returns
  `503 AUTH_KEY_METADATA_UNAVAILABLE`. Missing CSI key/certificate state returns
  `503 KEY_MATERIAL_UNAVAILABLE` where an application response is possible and
  removes only affected replicas from readiness. Recovery requires the
  authoritative dependency check, not an in-memory or credential fallback.
- Each service can roll forward/back without rebuilding the other two.
- UI-to-core NetworkPolicy denial and BFF-to-core allowance are effective.
- Trace/correlation ID is continuous through BFF and core with no token/PII logs.
- Normal BFF certificate rotation completes a fresh sign-in callback, an
  existing-session token refresh, and core-token acquisition through every
  replica before the old certificate retires.
- The 12-hour gateway-certificate CronJob alone assumes its certificate/DNS
  identity and passes overlap, reload, rollback, and NetworkPolicy checks.
- The 20-hour lab-revalidation CronJob alone assumes its validation identity,
  updates only destination/status/counter fields, and cannot reach excluded
  private/link-local/metadata/cluster destinations.
- The frozen browser/assistive-technology matrix passes keyboard-only operation,
  visible focus, status/error announcements, field associations, dialogs and
  timeout focus restoration, external-lab disclosure, 200% zoom/text scaling,
  mobile orientation/keyboard behavior, and all required widths without lost
  actions or unlabelled primary-content horizontal scrolling.
- HPA/PDB/topology and readiness tests preserve service independence through
  replica loss, disruption, scaling, Redis/PostgreSQL/JWKS/CSI outage, and
  normal/emergency key or certificate rotation; no partially converged replica
  receives traffic.
- Pilot evidence proves the 99.0% monthly target from one eligible observation
  per minute in the 08:00-18:00 Israel-business-day window, applies the 24-hour-
  notice/four-hour maintenance cap, and records eligible/successful/failed
  totals. Recovery drills verify stateless and Redis RTO at most 60 minutes,
  PostgreSQL RPO at most five minutes/RTO at most four hours, delivery-evidence
  RPO 0/RTO at most four hours, and controller-audit RPO 0/RTO at most four
  hours. Every prerequisite-owner evidence record is within its normative
  freshness window before the pilot or protected release opens.

## AKS routing

- Pinned ALB Controller -> Application Gateway for Containers public TLS host;
  `/` reaches UI ClusterIP and `/bff/*` reaches BFF ClusterIP.
- BFF -> `https://core.<namespace>.svc:8443/api/v1` through private ClusterIP,
  validating the mounted private-CA bundle.
- Approved private-network machines -> private DNS -> Azure-internal L4
  LoadBalancer -> the same core-served HTTPS 8443 listener. The certificate SANs
  cover both Kubernetes service DNS names and the private FQDN; core mounts/
  rotates it from Key Vault and still requires the operation-specific Entra app role.
- The legacy Web App Routing/NGINX add-on, base Ingress manifest, public core
  path, and public IP for the machine endpoint are absent.
- Core alone connects to managed PostgreSQL; BFF alone connects to managed
  Redis. Neither state service is mounted as an AKS application volume.
- Existing machine consumers use a separately governed private core route and
  Entra app-role policy, never the browser BFF cookie or delegated scope.
- UI, BFF, and core each render with two-to-four replica HPA policy, CPU/memory
  requests, a PDB allowing at most one unavailable replica, and hostname
  topology spread with `maxSkew: 1`; scaling one service leaves the others
  unchanged.

## Optimized Azure deployment

1. As Platform Operations, outside GitHub Actions, configure the Azure Storage backend
   and run `scripts/azure/bootstrap-ui-platform.sh` with an interactive Entra
   identity. Review/apply or import locked Terraform that pins AzureRM/AzureAD,
   enables AKS OIDC/Workload Identity, disables legacy Web App Routing, and
   creates/reuses AGC, Key Vault, Azure Managed Redis, PostgreSQL, monitoring,
   private DNS/TLS, Workload Identities, GitHub Actions delivery identities, and
   evidence storage. GitHub Actions identities receive no Terraform apply/import or
   state-read permission.
2. Still as Platform Operations, run
   `scripts/azure/bootstrap-data-principals.sh` to establish the Redis data-plane
   assignment and separate core DML, lifecycle known-identity/status/
   reconciliation/outbox plus unclaimed-retention scheduling, retention audited
   claim/process-due procedure-only, lab destination/status/counter-only, and
   migration DDL/backfill PostgreSQL Entra
   roles. Prove cross-role denial, then disable Redis access keys and PostgreSQL
   password fallback. Neither bootstrap script emits the environment manifest.
3. Install/attest the pinned ALB Controller and the cluster-admin-owned
   migration namespace, RBAC, ValidatingAdmissionPolicy, and binding. After all
   Terraform—including evidence lifecycle and alert rules—data principals,
   identities, denials, controller, and migration guardrails are live, run
   `scripts/azure/finalize-ui-platform.sh`. Review the generated schema-valid
   `config/platform-bootstrap-nonprod.json`; it contains no secret, matches the
   final repository configuration digest/state serial/live resource IDs,
   includes controller and migration-policy attestations, and carries provider/
   quota/capacity attestations no older than seven days.
   Recompute the configuration digest strictly from
   `config/platform-configuration-digest-v1.yaml`; verify canonical path/mode/
   length/content hashing catches matching add/remove/rename/mode/content drift
   and excludes the emitted manifest, Terraform state/plan/cache/local tfvars,
   runtime evidence/logs, secrets, and VCS metadata.
4. Validate the existing target ACR, AKS kubelet `AcrPull`, publisher `AcrPush`,
   deployer/controller denial boundaries, and deployer target-resource-group-
   only `Reader` grant. The deployer cannot read Terraform state, secrets, ACR
   content, Redis data, or PostgreSQL data.
5. Configure a GitHub Actions multibranch job to load the root `.github/workflows/delivery.yml`. Permit
   Azure publication/deployment only from the protected ref; PRs validate only.
   Configure the target environment lock and milestone behavior.
6. Keep the retired CI controller at `http://localhost:8080` and use its existing
   Azure cloud node named `azure` to create ephemeral ACI agents in the configured
   resource group. Configure `azure-aci-publisher` with an ACR-scoped
   user-assigned identity and `azure-aci-deployer` with an AKS-scoped
   user-assigned identity. Bind exactly the reviewed bootstrap-manifest publisher
   identity to the publisher template and exactly its deployer identity to the
   deployer template; reject missing, additional, swapped, or system-assigned
   identities. Validate that the existing controller service
   principal can manage ACI and attach identities only, cannot push to ACR or
   deploy to AKS. Platform Operations rotates that credential every 90 days,
   monitors 30/14/7-day alerts, proves the identityless validator plus publisher
   and deployer replacement-agent paths before
   revoking the old credential, and revokes immediately on suspected compromise.
   Missing/unreadable expiry or fewer than 30 valid days quarantines cloud
   `azure` for protected Azure stages. Developer-local validation remains
   available during quarantine, but GitHub Actions has no controller/local-agent
   fallback; quarantine clears only after all three declared templates pass.
   Store no additional Azure delivery credential or kubeconfig in GitHub Actions.
   Use a dedicated GitHub Actions credential-manager identity that can update only the
   stable cloud credential and cannot configure jobs, run builds, or read other
   credentials. Configure a separate Evidence Hold Managers Entra group whose
   custom role can mutate only hold metadata and cannot read/write/delete
   evidence or alter base retention.
   Configure `DELIVERY_OPERATORS_GROUP_OBJECT_ID` and
   `SECURITY_REVIEWERS_GROUP_OBJECT_ID` outside repository defaults. Give both
   ACI identities create-only access to their immutable evidence paths, with no
   general evidence read, overwrite, or delete permission.
   Enforce the assigned environment/stage prefixes with Azure ABAC conditions,
   upload with `If-None-Match: *`, and enable immutable storage for accepted
   evidence. Configure GitHub Actions rotation with a stable credential ID and supply
   replacement secret material only through protected standard input or an
   inherited file descriptor.
6. Confirm the external Platform Operations bootstrap installed the version-
   pinned ALB Controller and its Workload Identity/RBAC and recorded the live
   version in the manifest before Gateway/HTTPRoute resources. Remove the legacy base Ingress and Web
   App Routing/NGINX controller. Verify Terraform outputs and the URL helper
   return the authoritative AGC HTTPS browser origin, while the separate
   private-machine output resolves only through private DNS.
7. Generate `change-plan.json`, validate selected UI/BFF/core lanes in parallel,
   and run the aggregate compatibility gate using runtime capability metadata
   plus current/previous supported images. Build and scan only selected
   images, push them once, resolve ACR digests, and create
   `release-manifest.json`.
   Before `node`, agent allocation, checkout, or workspace creation, the trusted
   administrator-installed `RunListener` plugin, built from a protected revision
   and verified against its pinned artifact digest, independently records the minimal audit fields:
   build ID, source revision, start time, result, and failed stage. Append
   `started`, `agent_requested`, `agent_connected`, `evidence_active`, and one
   terminal `succeeded | failed | aborted` state; close every exit path. Require
   authoritative Azure Storage evidence only after an authenticated delivery
   agent is available; never use a fallback Azure credential when provisioning
   or evidence upload fails.
8. For a selected schema change, have the deployer use only the dedicated-
   namespace Job `create/get/watch/delete`, Pod `get/list/watch`, and `pods/log`
   `get` permissions. Confirm the non-overridable admission policy rejects any
   wrong service account, image repository/digest form, runner/target, privilege,
   environment, volume, or deadline. The Job alone uses the migration Workload Identity,
   PostgreSQL DDL/backfill role, immutable core digest, and explicit target
   (`learning@head`, `progress@head`, or `009_merge_learning_progress`). Require
   before/after heads, status/logs, timeout/retry, and cleanup evidence. Then
   deploy core, run core smoke/contract checks, deploy BFF, run auth/session/
   contract checks, and deploy UI. Skip unselected services but preserve order.
9. Verify the Gateway routes `/` to UI and `/bff/*` to BFF and that no route
   exposes core. Verify NetworkPolicy and private data-service connectivity.
   Validate each service HPA, PDB, resource request, readiness gate, and topology
   spread independently.
10. Confirm Azure Monitor contains correlated service version, deployment
   digest, route-class rate/error/duration, readiness, dependency, restart,
   replica, and HPA-saturation telemetry without secrets, tokens, request bodies,
   learner identifiers, or answer content. Exercise certificate expiry at
   30/14/7 days and critical below 48 hours, missing reconciliation success at
   6/8 hours, and active-lab validation age at 30/36 hours plus three consecutive
   failures/unavailability. Confirm each alert reaches its documented Platform,
   Application, or Learning Content Operations owner.
11. Before each mutation append previous/intended digest and configuration,
   compatibility result, mutation, compensating action, and reversibility to the
   deployment journal. On failure, stop promotion and execute only completed
   reversible compensations in reverse order. Do not apply an irreversible
   mutation without an operator recovery plan or reverse a destructive database
   migration automatically.
12. Run negative identity tests: wrong core audience/scope/client, UI token
   leakage, BFF-to-PostgreSQL, core-to-Redis, application-pod ACR access, and
   fake authentication in an Azure environment must all fail closed.
13. Confirm delivery evidence is uploaded to the dedicated Azure Storage
    container under `deliveries/<environment>/<build-id>/<stage>/<artifact>`,
    contains no token, kubeconfig, secret, or personal learner data,
    receives a fixed locked 90-day version-level `immutable_until`. Confirm an
    approved incident hold with owner, reason, reference, and an expiry no later
    than 180 days sets the Azure version-level legal-hold boolean on every
    enumerated evidence-set blob version; release/expiry clears every version
    hold and never shortens the base lock. Confirm partial operations reconcile
    before the request is marked active/released and that the scheduled minimal
    reconciler clears expired holds from its separate inventory without blob-
    content read/delete permission. Confirm
    required-artifact and prohibited-content validation succeeds before upload,
    `If-None-Match: *` rejects overwrite, the accepted blob version is locked
    immutable before promotion, and any missing/rejected evidence keeps the
    promotion gate closed.
14. Run lifecycle reconciliation against active, disabled, deleted, throttled,
   and unavailable directory fixtures; verify checkpoint restart, session
   revocation, lifecycle timestamps, and the 90-day retention boundary.

Pin and promote UI, BFF, and core ACR image digests independently. Deploy additive
core changes first, then BFF, then UI; remove old fields only after compatible
consumers are no longer deployed.

## GitHub Actions pipeline verification

Before enabling protected-branch deployment, run the repository CI scripts
locally and exercise the GitHub Actions job in validation-only mode:

```bash
bash -n scripts/ci/*.sh
scripts/ci/detect-changes.sh --base <baseline-sha> --head HEAD
scripts/ci/validate-api-contracts.sh
scripts/ci/validate-service.sh ui
scripts/ci/validate-service.sh bff
scripts/ci/validate-service.sh core
```

The scripts are implementation-plan targets and become executable as their
corresponding tasks are completed. Verify change-plan fixtures for UI-only,
BFF-only, core-only, shared/all, mixed-path-union/no-clearing/reason-deduplication,
each BFF/core OpenAPI document, the guidance
catalog, the implementation-readiness contract, the 125-row traceability
matrix, readiness-manifest-only, either performance-profile-only,
interaction-performance-fixture-only, provision/teardown
skill executable/template changes, docs-only, first/missing-baseline,
invalid-supplied-baseline, and audited rebuild-all cases. Assert the archived
plan contains all three service
booleans plus mandatory `contractIntegrity`, `readinessScenarios`,
`performanceProfile`, and `infrastructure` booleans with the exact selection
rules in the GitHub Actions delivery contract; prove no downstream stage recalculates
them. Assert a first/missing baseline uses JSON `null`, selects every service
and lane, and records `missing-baseline`, while an invalid supplied revision
fails closed. Then inject a validation failure and prove that no ACR publish or
environment promotion runs;
substitute an image tag and prove deployment rejects it; inject a rollout
failure and prove downstream services are skipped while every
service/configuration mutated by that attempt is restored to its pre-attempt
state by replaying the mutation journal in reverse; untouched services retain
their state. Include a reversible
configuration mutation and prove both configuration and digest return to their
prior values; prove an irreversible entry cannot enter automatic promotion.
Compare the live GitHub Actions ACI template and running container-group identity
resource IDs to the reviewed bootstrap manifest. Confirm the identityless
validator executes the same non-Azure suite on protected and unprotected refs,
while unprotected refs stop before Azure stages. Confirm the Azure Storage copy
is authoritative, the controller archive is only a convenience copy, and the
evidence-content validator rejects tokens, kubeconfigs, secrets, and personal
learner data. Simulate pre-agent failure, abort, and agent connection and verify
the trusted controller `RunAction` is created without an executor/workspace even
when the .github/workflows/delivery.yml omits audit calls or shadows repository/library symbols,
reaches exactly one terminal state through the installed plugin, and is copied into the
authoritative evidence set only after authenticated evidence activation.
Prove every accepted transition is fsynced to the normal run record and the
host-managed append-only replicated controller-audit volume before ACI
allocation, and that an unhealthy copy disables protected scheduling. Simulate
controller-disk loss: restore the replica within the four-hour RTO with RPO 0,
reconcile build IDs against queue/run metadata, webhook audit, and Azure
evidence, mark each accepted nonterminal orphan `aborted_recovered`, and keep
protected delivery blocked until every post-mutation orphan has verified
rollback or approved recovery in a verified terminal state. Finally, stop a
build after ACR publication and prove the digest is `published_unpromoted`, is
quarantined from aliases and later-build reuse without a new manifest/fresh
gates, becomes GC-eligible only when unreferenced after 30 days, retains
provenance/disposition for 90 days, and excludes promoted or held digests.
