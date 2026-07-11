# Quickstart: Three-Service Learning UI

## Goal

Run UI, BFF, and core as independent local services, verify all four learning
journeys, and prove that browser traffic cannot bypass the BFF.

## Prerequisites

- Node.js 24 LTS and npm
- Python 3.11 and uv
- Redis
- Docker for container verification
- kubectl for manifest rendering/deployment checks
- Azure CLI access to the target AKS, ACR, Key Vault, Azure Managed Redis,
  PostgreSQL, and Azure Monitor resources
- Jenkins with Pipeline/Declarative Pipeline, Credentials Binding, JUnit, and
  approved ephemeral container-agent support; an environment lock mechanism is
  required for deployment jobs
- Existing functional Jenkins Azure cloud node named `azure`, with ACI capacity
  in the configured resource group

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
   uv run alembic upgrade head
   uv run uvicorn api.app:app --reload --app-dir src --port 8000
   ```

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

```bash
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
  Key Vault encryption-key rotation preserves only the intended grace window.
- Session access expires after 30 idle minutes and at 8 absolute hours without
  deleting saved learning state; background polling does not extend it.
- Machine app-role tokens succeed only on documented operations; delegated,
  missing-role, wrong-client, and wrong-audience tokens fail.
- Entra disable/delete simulation blocks access and revokes sessions at sign-in
  or within the daily reconciliation window; transient lookup failures do not.
- Retention tests delete or irreversibly anonymize departed-employee records by
  day 90 and preserve only unlinked aggregate telemetry; backup restore runs
  due retention before personalized access is enabled.
- Concurrent/replayed mutations with one key create one transition; changed
  payload reuse returns `409` and creates no state.
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
  using `performance-profile-v1`, records 100 measured attempts per scenario
  after warm-up, retains failures and timeouts in the denominator, and proves
  roadmap p95 is at most 30 seconds and guidance p95 is at most 10 seconds.
- UI, BFF, and core outage states are distinguishable.
- Each service can roll forward/back without rebuilding the other two.
- UI-to-core NetworkPolicy denial and BFF-to-core allowance are effective.
- Trace/correlation ID is continuous through BFF and core with no token/PII logs.
- Normal BFF certificate rotation completes a fresh sign-in callback, an
  existing-session token refresh, and core-token acquisition through every
  replica before the old certificate retires.

## AKS routing

- Public TLS host `/` -> UI ClusterIP Service.
- Same host `/bff/*` -> BFF ClusterIP Service.
- BFF -> private core ClusterIP `/api/v1` by service DNS.
- Core alone connects to managed PostgreSQL; BFF alone connects to managed
  Redis. Neither state service is mounted as an AKS application volume.
- Existing machine consumers use a separately governed private core route and
  Entra app-role policy, never the browser BFF cookie or delegated scope.
- UI, BFF, and core each render with two-to-four replica HPA policy, CPU/memory
  requests, a PDB allowing at most one unavailable replica, and hostname
  topology spread with `maxSkew: 1`; scaling one service leaves the others
  unchanged.

## Optimized Azure deployment

1. Validate and reuse the existing target ACR, including AKS kubelet `AcrPull`,
   publisher `AcrPush`, and deployer/controller denial boundaries. Provision or
   reuse Key Vault, Azure Managed Redis, Azure Database for PostgreSQL Flexible
   Server, Log Analytics/Application Insights, and AKS Workload Identity
   bindings. Keep resource identifiers in environment outputs, not source code.
2. Configure a Jenkins multibranch job to load the root `Jenkinsfile`. Permit
   Azure publication/deployment only from the protected ref; PRs validate only.
   Configure the target environment lock and milestone behavior.
3. Keep the Jenkins controller at `http://localhost:8080` and use its existing
   Azure cloud node named `azure` to create ephemeral ACI agents in the configured
   resource group. Configure `azure-aci-publisher` with an ACR-scoped
   user-assigned identity and `azure-aci-deployer` with an AKS-scoped
   user-assigned identity. Bind exactly the Terraform publisher identity output
   to the publisher template and exactly the deployer identity output to the
   deployer template; reject missing, additional, swapped, or system-assigned
   identities. Validate that the existing controller service
   principal can manage ACI and attach identities only, cannot push to ACR or
   deploy to AKS. Platform Operations rotates that credential every 90 days,
   monitors 30/14/7-day alerts, proves both replacement-agent paths before
   revoking the old credential, and revokes immediately on suspected compromise.
   Missing/unreadable expiry or fewer than 30 valid days quarantines cloud
   `azure` for protected Azure stages; local validation remains available and
   quarantine clears only after both replacement templates pass.
   Store no additional Azure delivery credential or kubeconfig in Jenkins.
   Use a dedicated Jenkins credential-manager identity that can update only the
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
   evidence. Configure Jenkins rotation with a stable credential ID and supply
   replacement secret material only through protected standard input or an
   inherited file descriptor.
4. Generate `change-plan.json`, validate selected UI/BFF/core lanes in parallel,
   and run the aggregate compatibility gate using runtime capability metadata
   plus current/previous supported images. Build and scan only selected
   images, push them once, resolve ACR digests, and create
   `release-manifest.json`.
   Before requesting an ACI agent, record the minimal controller audit fields:
   build ID, source revision, start time, result, and failed stage. Append
   `started`, `agent_requested`, `agent_connected`, `evidence_active`, and one
   terminal `succeeded | failed | aborted` state; close every exit path. Require
   authoritative Azure Storage evidence only after an authenticated delivery
   agent is available; never use a fallback Azure credential when provisioning
   or evidence upload fails.
5. Apply database expand migrations, deploy core, run core smoke/contract
   checks, deploy BFF, run auth/session/contract checks, then deploy UI and run
   browser journeys. Skip unselected services but preserve this ordering.
6. Verify the Gateway routes `/` to UI and `/bff/*` to BFF and that no route
   exposes core. Verify NetworkPolicy and private data-service connectivity.
   Validate each service HPA, PDB, resource request, readiness gate, and topology
   spread independently.
7. Confirm Azure Monitor contains correlated service version, deployment
   digest, route-class rate/error/duration, readiness, dependency, restart,
   replica, and HPA-saturation telemetry without secrets, tokens, request bodies,
   learner identifiers, or answer content. Inject failures and confirm alerts
   identify the owning service.
8. Before each mutation append previous/intended digest and configuration,
   compatibility result, mutation, compensating action, and reversibility to the
   deployment journal. On failure, stop promotion and execute only completed
   reversible compensations in reverse order. Do not apply an irreversible
   mutation without an operator recovery plan or reverse a destructive database
   migration automatically.
9. Run negative identity tests: wrong core audience/scope/client, UI token
   leakage, BFF-to-PostgreSQL, core-to-Redis, application-pod ACR access, and
   fake authentication in an Azure environment must all fail closed.
10. Confirm delivery evidence is uploaded to the dedicated Azure Storage
    container under `deliveries/<environment>/<build-id>/<stage>/<artifact>`,
    contains no token, kubeconfig, secret, or personal learner data,
    and expires after 90 days unless an approved incident hold with owner,
    reason, reference, and expiry extends it to no more than 180 days. Confirm
    required-artifact and prohibited-content validation succeeds before upload,
    `If-None-Match: *` rejects overwrite, the accepted blob version is locked
    immutable before promotion, and any missing/rejected evidence keeps the
    promotion gate closed.
11. Run lifecycle reconciliation against active, disabled, deleted, throttled,
   and unavailable directory fixtures; verify checkpoint restart, session
   revocation, lifecycle timestamps, and the 90-day retention boundary.

Pin and promote UI, BFF, and core ACR image digests independently. Deploy additive
core changes first, then BFF, then UI; remove old fields only after compatible
consumers are no longer deployed.

## Jenkins pipeline verification

Before enabling protected-branch deployment, run the repository CI scripts
locally and exercise the Jenkins job in validation-only mode:

```bash
bash -n scripts/ci/*.sh
scripts/ci/detect-changes.sh --base <baseline-sha> --head HEAD
scripts/ci/validate-service.sh ui
scripts/ci/validate-service.sh bff
scripts/ci/validate-service.sh core
```

The scripts are implementation-plan targets and become executable as their
corresponding tasks are completed. Verify change-plan fixtures for UI-only,
BFF-only, core-only, shared/all, docs-only, and first-build cases. Then inject a
validation failure and prove that no ACR publish or environment promotion runs;
substitute an image tag and prove deployment rejects it; inject a rollout
failure and prove downstream services are skipped and only the failing service
is restored by replaying the mutation journal in reverse. Include a reversible
configuration mutation and prove both configuration and digest return to their
prior values; prove an irreversible entry cannot enter automatic promotion.
Compare the live Jenkins ACI template and running container-group
identity resource IDs to the Terraform outputs. Confirm the Azure Storage copy
is authoritative, the controller archive is only a convenience copy, and the
evidence-content validator rejects tokens, kubeconfigs, secrets, and personal
learner data. Simulate pre-agent failure, abort, and agent connection and verify
the controller audit reaches exactly one terminal state and is copied into the
authoritative evidence set only after authenticated evidence activation.
