# Implementation Plan: DevOps Career Agent UI

**Branch**: `003-develop-ui` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-develop-ui/spec.md`

## Summary

Deliver the learning experience as three independently operated services: a
React/TypeScript UI, a TypeScript/Fastify Backend for Frontend (BFF), and the
existing Python/FastAPI core. The UI owns presentation, the BFF owns browser
authentication and UI composition, and the core owns authorization, learning
rules, and durable records. All services run as independent AKS workloads and
use ACR, Application Gateway for Containers, Key Vault, Managed Redis,
PostgreSQL Flexible Server, and Azure Monitor. A shared foundational roadmap
schema and deterministic fixtures keep every user story independently testable;
per-service HPA, disruption, and topology policies keep those services
independently scalable and observable.

Jenkins at `http://localhost:8080` orchestrates delivery through its existing
Azure cloud `azure`. Ephemeral publisher and deployer ACI agents use separate
managed identities. Repository scripts classify changes, validate and publish
only affected images, promote immutable digests, record evidence, and perform
scoped rollback from a reverse-ordered mutation journal. Compatibility and
evidence gates fail closed before an incompatible or unaudited mutation reaches
the environment.

## Technical Context

**Language/Version**: UI and BFF use TypeScript on Node.js 24 LTS; core uses
Python 3.11
**Primary Dependencies**: React, Vite, React Router, Fastify, MSAL Node,
OpenAPI/JSON Schema clients, Redis client, FastAPI, Pydantic, SQLAlchemy,
Alembic, JWT/JWKS validation
**Storage**: UI has no durable storage; BFF stores encrypted opaque sessions and
MSAL cache material in Azure Managed Redis; core stores relational learning and
identity data in Azure Database for PostgreSQL Flexible Server; SQLite is local
development only; delivery evidence uses dedicated Azure Blob Storage
**Testing**: Vitest, Playwright, pytest, contract tests, integration tests,
container tests, AKS manifest/routing tests, Jenkins pipeline tests, Azure RBAC
negative tests, and pilot usability verification
**Target Platform**: Current mainstream desktop/mobile browsers and three Linux
containers on the existing non-production Azure AKS cluster
**Project Type**: Three-service web application with a static SPA, stateful BFF,
and authoritative JSON API
**Performance Goals**: Every locally detectable validation error is associated
with its field/status region within one second of the initiating browser event;
at least 95% of successful roadmap and guidance results become visibly and
accessibly ready within one second of the browser fetch resolving with the
complete validated success payload; preserve roadmap
30-second p95 and guidance 10-second p95 core targets; support 10 concurrent
pilot users
**Constraints**: Browser calls only `/bff/v1`; BFF calls private core `/api/v1`;
20-30 minute learning sessions; 3-5 review questions; 80% completion threshold;
responsive from 320px; WCAG 2.2 AA-oriented behavior; runtime configuration
without rebuild; immutable image digests; no OAuth token in UI; 30-minute idle
and 8-hour absolute sessions; daily Entra reconciliation; 90-day departed-user
retention ceiling; actor-scoped idempotency; protected-branch-only delivery;
distinct publisher/deployer ACI identities; no fallback Azure credential
**Scale/Scope**: One Entra tenant, four UI journeys, three application services,
one Redis dependency, one PostgreSQL database, and up to 10 concurrent employees

All technical decisions are resolved and supported by user input, repository
context, and [research.md](./research.md).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- [x] Spec, plan, and tasks describe the same three-service learning UI and
      Jenkins/Azure delivery outcome.
- [x] Four user stories are independently testable and priority ordered; US1 is
      the MVP. Shared owned-roadmap schema and deterministic roadmap/content
      fixtures are Foundation deliverables rather than US1 prerequisites.
- [x] Research resolves service boundaries, identity, persistence, Azure,
      Jenkins, evidence, and lab-governance decisions.
- [x] Tests precede or accompany implementation and cover each story plus
      security, retention, concurrency, accessibility, and deployment.
- [x] Contracts, quickstart, operations guidance, and agent context are included.
- [x] Added UI and BFF services are required by the specified isolation boundary;
      no unjustified constitutional exception exists.

**Post-design re-check**: Passed. Contracts preserve browser-to-BFF and
BFF-to-core boundaries; the data model preserves core ownership; evidence and
credential controls are testable; compatibility, scaling, rollback, timing,
rotation, dependency-isolation, and monitoring checks are explicit; all runtime
guidance is synchronized.

## Project Structure

### Documentation (this feature)

```text
specs/003-develop-ui/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- auth-ui-contract.md
|   |-- jenkins-delivery-contract.md
|   `-- learning-ui-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
Jenkinsfile

ui/
|-- Dockerfile
|-- package.json
|-- src/
|   |-- app/
|   |-- bff/
|   |-- components/
|   |-- features/
|   `-- styles/
`-- tests/
    |-- unit/
    `-- e2e/

bff/
|-- Dockerfile
|-- package.json
|-- src/
|   |-- auth/
|   |-- clients/
|   |-- contracts/
|   |-- routes/
|   `-- sessions/
`-- tests/
    |-- contract/
    |-- integration/
    `-- unit/

src/
|-- agent/
|-- api/routes/
|-- auth/
|-- lifecycle/
`-- storage/

alembic/
`-- versions/

tests/
|-- contract/
|-- integration/
|-- ci/
`-- unit/

deploy/k8s/
|-- base/
|   |-- ui/                 # Deployment, Service, HPA, PDB
|   |-- bff/                # Deployment, Service, HPA, PDB
|   |-- core/               # Deployment, Service, HPA, PDB
|   |-- lifecycle/
|   `-- network-policies.yaml
`-- overlays/aks-nonprod/
    |-- gateway.yaml
    |-- httproute.yaml
    |-- configmaps.yaml
    `-- workload-identities.yaml

infra/azure/
|-- identity.tf
|-- entra-bff-registration.tf
|-- entra-core-api-registration.tf
|-- entra-machine-registrations.tf
|-- entra-app-roles.tf
|-- jenkins-agent-identities.tf
|-- application-gateway-for-containers.tf
|-- gateway-certificates.tf
|-- gateway-dns.tf
|-- bff-client-certificate.tf
|-- bff-certificate-rotation.tf
|-- delivery-evidence-storage.tf
|-- delivery-evidence-hold-managers.tf
|-- key-vault.tf
|-- postgresql.tf
|-- redis.tf
|-- private-networking.tf
|-- monitoring.tf
`-- outputs.tf

scripts/ci/
|-- detect-changes.sh
|-- validate-service.sh
|-- build-publish.sh
|-- publish-evidence.sh
|-- validate-evidence.sh
|-- evidence-gate.sh
|-- manage-evidence-hold.sh
|-- manage-controller-audit.sh
|-- mutation-journal.sh
|-- promote.sh
|-- deploy.sh
|-- verify.sh
`-- rollback.sh

scripts/azure/
|-- preflight-ui-platform.sh
|-- rotate-gateway-certificate.sh
`-- rotate-bff-client-certificate.sh

scripts/jenkins/
|-- verify-agent.sh
|-- verify-managed-identity.sh
|-- verify-aci-identity-binding.sh
|-- verify-cloud-credential.sh
|-- configure-credential-manager.groovy
`-- rotate-cloud-credential.sh
```

**Structure Decision**: Keep UI, BFF, and core independently buildable at the
repository root. Keep environment-neutral Kubernetes manifests under
`deploy/k8s/base`, Azure bindings under `deploy/k8s/overlays/aks-nonprod`, and
Terraform under `infra/azure`. Jenkins remains thin and calls versioned scripts.

## Phase 0: Research Decisions

Phase 0 is complete in [research.md](./research.md). Key decisions are:

- React/Vite SPA with runtime configuration and no browser token storage.
- Separate Fastify BFF using Entra authorization code flow, encrypted Redis
  sessions, and certificate-based confidential-client authentication.
- FastAPI core independently validates delegated and app-only tokens and owns
  all business rules and PostgreSQL persistence.
- Owned roadmap and milestone identity is established in Foundation, with
  deterministic owned-roadmap and published-learning-content fixtures for US3
  and US4 so their migrations and tests do not depend on US1 implementation.
- One AKS platform hosts three independent workloads; Application Gateway for
  Containers exposes only UI and BFF. Each workload has an HPA, PDB, resource
  requests, and topology-spread policy.
- UI/BFF and BFF/core versions negotiate capabilities before state-changing
  operations, and repository dependency checks prevent presentation or
  composition changes from importing core business code.
- Jenkins uses existing cloud `azure` and distinct ephemeral publisher/deployer
  ACI templates rather than controller-held delivery credentials.
- Azure Storage is authoritative for delivery evidence; a minimal controller
  audit state machine covers failures before an authenticated ACI agent is
  available. Evidence validation and immutability are promotion gates.
- Lab providers start with an empty allowlist and require distinct content-owner
  and security-reviewer approvals.

## Phase 1: Design and Contracts

### Service and API boundaries

| Hop | Contract | Enforcement |
|---|---|---|
| Browser -> UI | Static assets and runtime config | No personalized data or OAuth tokens |
| Browser -> BFF | `/bff/v1`, opaque host-only cookie, CSRF | Origin, session, input, and expiry checks |
| BFF -> core | Private `/api/v1`, delegated core token | Signature, issuer, tenant, audience, client, scope, subject |
| Machine -> core | Private `/api/v1`, app-only token | Approved client and dedicated application role |
| UI/BFF/core -> Azure | Separate workload identities | Least-privilege dependency-specific RBAC |

Detailed behavior is defined in [auth-ui-contract.md](./contracts/auth-ui-contract.md),
[learning-ui-contract.md](./contracts/learning-ui-contract.md), and
[jenkins-delivery-contract.md](./contracts/jenkins-delivery-contract.md).

The UI declares its accepted BFF contract range in runtime configuration. The
BFF and core expose non-mutating capability metadata containing the active
contract version, compatible range, and enabled state-changing features. The UI
blocks a mutation unless its range intersects the BFF version; the BFF blocks it
unless its generated client range intersects the core version. Missing,
malformed, or disjoint capability metadata fails closed with a safe availability
response. CI runs the same negotiation against current and previous supported
images before promotion.

Dependency isolation is enforced structurally: UI source cannot import BFF or
core runtime modules; BFF source cannot import core application modules and may
consume only generated contract/client artifacts; core has no UI/BFF dependency.
Contract and change-plan tests prove that UI presentation-only and BFF
composition-only edits neither select nor require a core source change.

### Data ownership

The BFF persists only browser session and encrypted MSAL cache state in Redis.
The core owns employee identity, roadmap, guidance, learning session, review,
progress, milestone, lab-reference, provider-policy, idempotency, reconciliation,
and retention records in PostgreSQL. Field definitions, constraints, and state
transitions are in [data-model.md](./data-model.md).

The owned roadmap, stable milestone key, and employee ownership constraints are
created by a linear Foundation migration before any story migration. US1 uses
that schema to create roadmaps. US3 receives a deterministic owned-roadmap plus
published-learning-content fixture; US4 receives a deterministic owned-roadmap
fixture. No US3 or US4 migration has an Alembic dependency on a US1 task.

### Authentication and certificate lifecycle

The BFF is a confidential Entra web client and uses a Key Vault certificate
mounted by CSI. Rotation registers the replacement public key at least 24 hours
before retirement, waits for every BFF replica to report the new version and
acquire a core token, and proves a new sign-in callback plus an existing-session
token refresh through every replica before declaring readiness. The old
credential is removed within 48 hours. Emergency revocation bypasses overlap;
normal continuity checks must fail if any replica cannot complete sign-in or
token acquisition. Core machine consumers use separate app-only roles.

### Azure topology

Terraform provisions or imports ACR dependencies, Key Vault, Managed Redis,
PostgreSQL, monitoring, workload identities, Application Gateway for Containers,
DNS/certificates, Entra registrations, Jenkins identities, and evidence storage.
Gateway routes `/` to UI and `/bff/*` to BFF; core and data services remain
private. Kubernetes default-deny policies allow only declared service hops.

UI, BFF, and core each declare CPU/memory requests, an HPA with two minimum and
four maximum replicas at a 70% CPU target, a PDB with `maxUnavailable: 1`, and a
hostname topology-spread constraint with `maxSkew: 1` and
`ScheduleAnyway`. Readiness gates remove unhealthy replicas before traffic or
rollout completion; liveness remains process-local. The manifest test verifies
the policies independently and confirms that scaling one service does not
modify either of the others.

Each service emits a distinct Azure Monitor/Application Insights identity with
environment, service version, and image digest. Gateway, UI, BFF, and core
propagate trace context and record route-class request count, error count,
duration, readiness, dependency outcome, pod restart, replica, and HPA-saturation
signals without tokens, request bodies, learner identifiers, or answer content.
Alerts cover five-minute readiness loss, sustained 5xx/latency breaches, restart
loops, and HPA maximum saturation; injected failures must identify the owning
service.

### Jenkins delivery strategy

The controller at `http://localhost:8080` uses existing cloud `azure`.
`azure-aci-publisher` binds exactly the ACR/evidence publisher UAMI;
`azure-aci-deployer` binds exactly the AKS/evidence deployer UAMI. Preflight
compares live template and running ACI identity resource IDs with Terraform
outputs and rejects missing, additional, swapped, or system-assigned identities.

Pipeline execution classifies changes from merge base, validates affected lanes,
builds/scans/SBOMs selected images, resolves immutable ACR digests, and promotes
in `core -> BFF -> UI` order without rebuilding. Before each environment
mutation, it records the service, previous and intended digest/configuration,
compatibility result, mutation command, compensating command, and reversibility
in an append-only journal. Failure stops downstream promotion and replays only
completed reversible mutations in reverse order. A destructive or otherwise
irreversible mutation cannot enter automatic promotion; it requires a separate
operator-approved recovery plan. Database contract migrations are never
automatically reversed.

### Jenkins provisioning credential lifecycle

Platform Operations owns the service principal used only by Jenkins cloud
`azure` for ACI lifecycle and identity attachment. It has no ACR push or AKS
deployment permission. Rotation occurs at least every 90 days with alerts at
30, 14, and 7 days. Missing/unreadable expiry or fewer than 30 valid days places
cloud `azure` in quarantine: protected-branch Azure stages cannot request a new
agent, while local validation remains available. The local rotation procedure
uses a dedicated Jenkins credential-manager identity that can update only the
stable Azure cloud credential entry and cannot configure jobs, run builds, or
read unrelated credentials. It uses the localhost Jenkins API, CSRF crumb, and
protected standard-input or file-descriptor secret handoff. Secrets never enter
arguments, environment variables, logs, or retained files. Normal rotation
validates both templates before revocation and clears quarantine only after both
pass. Emergency rotation revokes first and disables ordinary build provisioning.
An audited rotation-validation path may provision only publisher and deployer
smoke agents; those agents cannot execute repository jobs, publish images, or
deploy workloads. Ordinary provisioning remains quarantined until both
replacement templates pass.

### Delivery evidence strategy

Before agent provisioning Jenkins creates a minimal, non-authoritative audit
attempt and appends lifecycle events for `started`, `agent_requested`,
`agent_connected`, `evidence_active`, and exactly one terminal state of
`succeeded`, `failed`, or `aborted`. Every exit path closes the attempt with
timestamps and the failed stage. Once an authenticated agent starts, the record
is copied into the authoritative evidence set; a pre-agent failure remains in
the access-restricted controller audit for 90 days and is never presented as
authoritative delivery evidence. Evidence is published under
`deliveries/<environment>/<build-id>/<stage>/<artifact>` to authoritative Azure
Storage. Uploads use `If-None-Match: *`.

Terraform defines a writer role excluding blob read, list, tag mutation, and
delete operations. Azure ABAC conditions restrict each identity to its assigned
environment/stage prefix. The content validator and required-artifact manifest
must pass before upload, and all pre-mutation evidence must be accepted before
promotion. A missing, rejected, or unavailable evidence write fails closed.
Accepted versions receive a locked time-based immutability policy for the
90-day retention window; an approved hold extends protection, never weakens it.
Configured Delivery Operators and Security Reviewers Entra groups receive read
access. A separately configured Evidence Hold Managers Entra group may
create/release only hold metadata for the evidence container through its custom
role assignment; it cannot read evidence, create delivery artifacts, change the
base retention policy, or delete blobs. Authorized
incident holds may extend selected evidence to at most 180 days and record
owner, reason, incident reference, start, and expiry.

### Lab governance

`config/approved-lab-providers.yaml` begins empty. A provider addition or domain
expansion requires two distinct humans: one member of the Learning Content
Owners Entra group and one member of the Application Security Reviewers group.
Publication validates HTTPS, redirects, metadata, reachability, and recorded
policy version; active references are revalidated every 24 hours.

## Phase 2: Implementation Planning

Implementation is decomposed in [tasks.md](./tasks.md):

1. Set up independent UI, BFF, and core build/test environments.
2. Complete shared identity, persistence, Azure, lifecycle, and lab foundations.
3. Deliver independently testable US1 roadmap MVP.
4. Deliver US2 skill guidance.
5. Deliver US3 focused learning and review.
6. Deliver US4 progress review.
7. Complete Jenkins/Azure delivery, security, evidence, operational, and pilot
   verification.

Tests are defined before or alongside implementation. Foundation blocks story
work; stories can run independently after foundation; cross-cutting release
verification follows selected stories.

## Complexity Tracking

No constitution violation requires an exception. The separate UI and BFF are
intentional requirements that isolate presentation, browser security, and core
business authority while preserving machine-consumer independence.
