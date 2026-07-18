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
attempt-wide rollback of every attempt-mutated service from a reverse-ordered
mutation journal. Compatibility and
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
**Target Platform**: Latest two stable major releases of Chrome, Edge, Firefox,
and Safari/WebKit, using the frozen Windows 11/current-and-previous-macOS,
mobile portrait/landscape, 200% zoom/text-scaling, NVDA, and VoiceOver matrix;
three Linux containers on the existing non-production Azure AKS cluster
**Project Type**: Three-service web application with a static SPA, stateful BFF,
and authoritative JSON API
**Performance Goals**: The approved `tests/performance/performance-profile-v1.json`
fixes SC-043 operation pairing, pinned BFF/core contract digests,
generated-mapper drift verification, fixtures, deterministic assignment,
45-second roadmap/20-second guidance hard timeouts, full-profile and fixture-set
digests, evidence schema, and percentile policy. The separate approved
`tests/performance/interaction-performance-profile-v1.json` plus its exact-byte
digest-bound `tests/performance/interaction-performance-fixtures-v1.json` fixes
SC-050's eight learning, review, progress, session, logout, and callback
scenarios, scenario-specific BFF/core contract bindings and timing boundaries,
schema-valid state/requests, fixed UUIDv5/token/time derivation, canonical
per-attempt derived-input SHA-256 evidence with two known-answer vectors, two warm-ups per worker, 5-second hard timeout,
100-attempt denominator, nearest-rank p95, full-profile and fixture-set digests,
and evidence schema. Every locally detectable validation error is associated
with its field/status region within one second of the initiating browser event;
at least 95% of successful roadmap and guidance results become visibly and
accessibly ready within one second of the browser fetch resolving with the
complete validated success payload; preserve the SC-043 roadmap 30-second and
guidance 10-second core p95 targets under 10 concurrent pilot-user workloads
and satisfy every SC-050 scenario at 95 of 100 attempts within five seconds
under 10 concurrent workers. Its callback scenario measures only deterministic
post-provider-exchange BFF processing through redirect emission and prohibits a
live provider or network exchange. Failures and timeouts remain in each
profile's fixed denominator.
**Constraints**: Browser calls only `/bff/v1`; BFF calls private core `/api/v1`;
20-30 minute learning sessions; 3-5 review questions; 80% completion threshold;
responsive from 320px; keyboard operability, visible focus, meaningful labels
and headings, announced status and error changes, correct error associations,
no focus traps, and no primary-content horizontal scrolling as required by
FR-013, FR-014, SC-005, and SC-006; runtime configuration without rebuild;
immutable image digests; no OAuth token in UI; 30-minute idle and 8-hour absolute
sessions; four-hour Entra reconciliation satisfying the daily minimum; 90-day departed-user retention ceiling;
actor-scoped idempotency; protected-branch-only delivery; distinct
publisher/deployer ACI identities; no fallback Azure credential
**Scale/Scope**: One Entra tenant, four UI journeys, three application services,
one Redis dependency, one PostgreSQL database, and up to 10 concurrent employees

All technical decisions are resolved and supported by user input, repository
context, and [research.md](./research.md).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- [x] Spec, plan, and tasks describe the same three-service learning UI and
      Jenkins/Azure delivery outcome.
- [x] Four user stories are independently testable and priority ordered; US1 is
      the pre-release MVP. A named minimum-foundation gate provides only the
      shared identity, contract, persistence, and shell capabilities required
      by US1; story-specific and protected-release infrastructure remains in
      explicit later gates and does not block the US1 demonstration.
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
|-- requirements-traceability.md
|-- verification.md
|-- usability-study.md
|-- usability-results.md
|-- checklists/
|   `-- implementation-readiness.md
|-- contracts/
|   |-- auth-ui-contract.md
|   |-- bff-api-v1.digest
|   |-- bff-api-v1.openapi.yaml
|   |-- core-api-v1.digest
|   |-- core-api-v1.openapi.yaml
|   |-- implementation-readiness-contract.md
|   |-- jenkins-delivery-contract.md
|   |-- learning-ui-contract.md
|   `-- supported-guidance-topics-v1.yaml
`-- tasks.md
```

### Source Code (repository root)

```text
Jenkinsfile

ui/
|-- Dockerfile
|-- nginx.conf
|-- package.json
|-- src/
|   |-- app/
|   |   |-- route-registry.tsx
|   |   |-- restore-persisted-state.ts
|   |   |-- submitted-operation-registry.ts
|   |   `-- useSubmittedOperation.ts
|   |-- bff/
|   |-- components/SignOutAction.tsx
|   |-- contracts/
|   |   |-- bff-api.ts
|   |   `-- supported-guidance-topics.ts
|   |-- features/
|   |   |-- roadmap/routes.tsx
|   |   |-- guidance/routes.tsx
|   |   |-- learning/routes.tsx
|   |   `-- progress/routes.tsx
|   |-- telemetry/
|   |   |-- performance.ts
|   |   `-- safe-telemetry.ts
|   `-- styles/
`-- tests/
    |-- unit/
    `-- e2e/

bff/
|-- Dockerfile
|-- package.json
|-- src/
|   |-- auth/
|   |-- clients/core-client.ts
|   |-- compatibility/core-version.ts
|   |-- contracts/
|   |   |-- bff-api.ts
|   |   |-- core-api.ts
|   |   `-- supported-guidance-topics.ts
|   |-- plugins/
|   |   |-- contract-version.ts
|   |   `-- generated-validation.ts
|   |-- routes/
|   |   |-- registry.ts     # Foundation-owned registry
|   |   |-- roadmaps.ts
|   |   |-- guidance.ts
|   |   |-- learning.ts
|   |   |-- progress.ts
|   |   `-- internal-lifecycle.ts
|   `-- sessions/encryption-key-ring.ts
`-- tests/
    |-- contract/
    |-- integration/
    `-- unit/

src/
|-- agent/
|-- api/
|   |-- generated/
|   |   |-- core_api_models.py
|   |   `-- validation.py
|   `-- routes/
|       |-- registry.py
|       |-- capabilities.py
|       |-- health.py
|       |-- identity.py
|       |-- roadmap.py
|       |-- skills.py
|       |-- learning.py
|       `-- progress.py
|-- auth/
|-- lifecycle/
|   |-- bff_revocation_client.py
|   `-- dispatch_session_revocations.py
`-- storage/

alembic/
`-- versions/
    |-- 003_baseline.py
    |-- 004_identity_lifecycle_idempotency.py
    |-- 005_lab_references.py
    |-- 006_owned_roadmaps.py
    |-- 007_learning_sessions.py
    |-- 008_owned_progress.py
    `-- 009_merge_learning_progress.py

config/
|-- approved-lab-providers.yaml
|-- lab-provider-policy.schema.json
|-- operational-alert-profile-v1.yaml
|-- platform-configuration-digest-v1.yaml
|-- platform-bootstrap.example.json
|-- platform-bootstrap-nonprod.json
|-- platform-bootstrap.schema.json
|-- supported-guidance-topics-v1.yaml
`-- supported-guidance-topics.schema.json

docs/
|-- jenkins-azure-cloud.md
|-- jenkins-credential-manager.md
`-- operations-ui.md

tests/
|-- contract/
|-- fixtures/
|   |-- readiness-scenario-manifest-v1.yaml
|   |-- owned_roadmaps.py
|   `-- published_learning_content.py
|-- integration/
|-- ci/
|-- performance/
|   |-- interaction-performance-fixtures-v1.json
|   |-- interaction-performance-profile-v1.json
|   `-- performance-profile-v1.json
`-- unit/

deploy/k8s/
|-- platform/
|   `-- alb-controller/     # pinned chart values, namespace, WI, RBAC
|-- base/
|   |-- ui/                 # Deployment, Service, HPA, PDB
|   |-- bff/                # Deployment, Service, HPA, PDB
|   |-- core/               # ClusterIP plus TLS private-machine LoadBalancer
|   |-- lifecycle/
|   |-- retention/
|   |-- lab-revalidation/
|   |-- evidence-hold-reconciler/
|   |-- gateway-certificate-rotation/
|   |-- migration/          # namespace, Job, SA, RBAC, NetworkPolicy, admission
|   `-- network-policies.yaml
`-- overlays/aks-nonprod/
    |-- gateway.yaml
    |-- httproute.yaml
    |-- configmaps.yaml
    |-- private-machine-service.yaml
    |-- machine-tls-secret-provider-class.yaml
    `-- workload-identities.yaml

infra/azure/
|-- .terraform.lock.hcl
|-- backend.tf
|-- providers.tf
|-- versions.tf
|-- main.tf
|-- identity.tf
|-- entra-bff-registration.tf
|-- entra-core-api-registration.tf
|-- entra-machine-registrations.tf
|-- entra-app-roles.tf
|-- entra-lifecycle-permissions.tf
|-- jenkins-agent-identities.tf
|-- application-gateway-for-containers.tf
|-- gateway-certificates.tf
|-- gateway-dns.tf
|-- private-dns.tf
|-- core-machine-certificate.tf
|-- bff-client-certificate.tf
|-- bff-certificate-rotation.tf
|-- bff-session-encryption.tf
|-- delivery-evidence-storage.tf
|-- delivery-evidence-hold-managers.tf
|-- key-vault.tf
|-- postgresql.tf
|-- redis.tf
|-- data-plane-rbac.tf
|-- private-networking.tf
|-- monitoring.tf
`-- outputs.tf

scripts/ci/
|-- detect-changes.sh
|-- validate-service.sh
|-- validate-api-contracts.sh
|-- build-publish.sh
|-- migrate-core.sh
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
|-- bootstrap-ui-platform.sh
|-- bootstrap-data-principals.sh
|-- finalize-ui-platform.sh
|-- compute-platform-configuration-digest.sh
|-- preflight-ui-platform.sh
|-- validate-delivery-identities.sh
|-- get-application-url.sh
|-- rotate-gateway-certificate.sh
`-- rotate-bff-client-certificate.sh

scripts/jenkins/
|-- install-controller-audit-plugin.groovy
|-- configure-validator-agent.groovy
|-- configure-publisher-deployer-agents.groovy
|-- verify-agent.sh
|-- verify-managed-identity.sh
|-- verify-aci-identity-binding.sh
|-- verify-validator-agent.sh
|-- verify-cloud-credential.sh
|-- check-cloud-credential-health.sh
|-- install-cloud-credential-health-job.groovy
|-- configure-credential-manager.groovy
`-- rotate-cloud-credential.sh

jenkins-controller-audit-plugin/
|-- pom.xml
`-- src/main/java/io/knowledgebasedb/jenkins/audit/
    |-- ControllerAuditAction.java
    `-- ControllerAuditRunListener.java

.agents/skills/
|-- provision-azure-app-resources/ # feature-003 topology/templates/helpers
`-- teardown-azure-app-resources/  # feature-003 dependency-safe teardown
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
- `contracts/bff-api-v1.openapi.yaml` and
  `contracts/core-api-v1.openapi.yaml` are the machine-readable boundary sources
  of truth: drift and mapping validation precede generated BFF/UI consumers,
  service validation, or any image build.
- `contracts/supported-guidance-topics-v1.yaml` is the versioned source of truth
  for canonical guidance topics and aliases; the runtime catalog is generated
  from it and CI rejects drift or locally invented topic entries.
- Actor-owned roadmap and stable milestone identity is established in
  Foundation, with deterministic employee/application-owned roadmap and
  published-learning-content fixtures so story migrations and tests do not
  depend on US1 implementation.
- One AKS platform hosts three independent workloads. A pinned Application
  Gateway for Containers ALB Controller owns the public UI/BFF Gateway; core has
  only ClusterIP and a separately governed TLS internal-LoadBalancer machine
  endpoint. Each workload has an HPA, PDB, resource requests, and
  topology-spread policy.
- UI/BFF and BFF/core versions negotiate capabilities before state-changing
  operations, and repository dependency checks prevent presentation or
  composition changes from importing core business code.
- Jenkins uses existing cloud `azure` and distinct ephemeral publisher/deployer
  ACI templates rather than controller-held delivery credentials. An
  identityless `azure-aci-validator` template handles all-ref non-Azure
  validation; unprotected refs are confined to that template.
- Azure Storage is authoritative for delivery evidence; a minimal controller
  audit state machine covers failures before an authenticated ACI agent is
  available. Evidence validation and immutability are promotion gates.
- Lab providers start with an empty allowlist and require distinct content-owner
  and security-reviewer approvals.

## Phase 1: Design and Contracts

### Service and API boundaries

| Hop | Contract | Enforcement |
|---|---|---|
| Browser -> UI Service | Static assets and runtime config | Requests to the static service carry no personalized data or OAuth tokens |
| Browser -> BFF | `/bff/v1`, opaque host-only cookie, CSRF | Origin, session, input, and expiry checks |
| BFF -> core | Private `/api/v1`, delegated core token | Signature, issuer, tenant, audience, client, scope, subject |
| BFF readiness -> core | Private capability/readiness reads, app-only token | Approved BFF client and `CareerAgent.Health.Read` only |
| Machine -> core | Private `/api/v1`, app-only token | Approved client and dedicated application role |
| Lifecycle -> Graph/BFF | Read-only known-user lookup; private revocation command | Dedicated identity, admin-consented `User.Read.All`, and `LearningBff.Session.Revoke` |
| BFF/core/lifecycle/retention/lab-validation/migration/hold-reconciler/ALB/gateway -> Azure | Separate workload identities; UI has none by default | Redis; application DML; known-identity/reconciliation/outbox plus unclaimed-retention scheduling; audited claim/process-due retention procedures with no direct queue/learning reads; lab destination/status/counter-only; DDL/backfill; hold-inventory plus exact version-hold set/clear without content read/list/delete; AGC; and certificate/DNS grants are mutually scoped; AKS kubelet performs ACR pulls |

Detailed behavior is defined in [auth-ui-contract.md](./contracts/auth-ui-contract.md),
[core-api-v1.openapi.yaml](./contracts/core-api-v1.openapi.yaml),
[implementation-readiness-contract.md](./contracts/implementation-readiness-contract.md),
[learning-ui-contract.md](./contracts/learning-ui-contract.md), and
[jenkins-delivery-contract.md](./contracts/jenkins-delivery-contract.md).

Every FR/SC implementation, verification, and retained-evidence obligation is
mapped in [requirements-traceability.md](./requirements-traceability.md); CI
rejects missing, duplicate, out-of-order, empty, or unknown-task rows.

Both service boundaries are contract-first. Browser/BFF route or DTO changes
begin in `bff-api-v1.openapi.yaml`; CI generates BFF route validators plus the UI
client/types/validators from its digest. Core endpoint/schema changes begin in
`core-api-v1.openapi.yaml`; CI generates the BFF core client/types and core
validators from that digest. Explicit BFF mapping contracts must convert every
browser DTO to/from a valid core DTO without embedding domain rules. Any authored
contract, generated-consumer, validator, mapping, or checked-in digest drift
fails before service tests or builds. Hand-authored DTO duplication is
prohibited.

Guidance-topic support is also contract-first. The canonical IDs, display names,
aliases, activation state, and deterministic order live in
`supported-guidance-topics-v1.yaml`. Build tooling generates the runtime
`config/supported-guidance-topics-v1.yaml` plus checked-in BFF/UI catalog
artifacts, and contract tests fail on duplicate IDs/aliases, unknown fields,
nondeterministic order, or generated-consumer drift.

The UI declares its accepted BFF contract range in runtime configuration. The
BFF and core expose non-mutating capability metadata containing the active
contract version, applicable BFF/core API schema version, compatible range, and
enabled state-changing features. The UI
blocks a mutation unless its range intersects the BFF version; the BFF blocks it
unless its generated client range intersects the core version. Missing,
malformed, or disjoint capability metadata fails closed with a safe availability
response. The BFF reads private core capabilities with its certificate-backed
app-only token containing only `CareerAgent.Health.Read`; approved machine
operations retain their existing request shapes and do not send the
BFF-specific version header. CI runs the same negotiation against current and
previous supported images before promotion.

Dependency isolation is enforced structurally: UI source cannot import BFF or
core runtime modules; BFF source cannot import core application modules and may
consume only generated contract/client artifacts; core has no UI/BFF dependency.
Contract and change-plan tests prove that UI presentation-only and BFF
composition-only edits neither select nor require a core source change.

Foundation owns a shared core route registry in `src/api/routes/registry.py` and
a BFF route registry under `bff/src/routes/`. Foundation registers only shared
auth/health/capability dependencies. Each story owns its roadmap, guidance,
learning, or progress route module and registers it through the shared registry;
story modules never edit a monolithic router or import another story's service.

### Data ownership

The BFF persists only browser session and encrypted MSAL cache state in Redis.
The core owns employee identity, roadmap, guidance, learning session, review,
progress, milestone, lab-reference, provider-policy, idempotency, reconciliation,
and retention records in PostgreSQL. Field definitions, constraints, and state
transitions are in [data-model.md](./data-model.md).

Roadmap and progress ownership is actor-polymorphic without impersonation:
delegated BFF calls create employee-owned records, while approved app-role calls
create application-owned records keyed to the validated `MachinePrincipal`.
Machine progress is restricted to the same application's roadmaps; learning and
review records remain employee-only. Guidance is stateless except for
actor-scoped idempotency/audit.

The actor-owned roadmap, stable milestone key, and exactly-one
employee/application ownership constraints are created by Foundation revision
`006_owned_roadmaps`. US1 uses that schema without
a new schema head. US3 revision `007_learning_sessions` and US4 revision
`008_owned_progress` are named sibling branch heads, each with
`down_revision = 006_owned_roadmaps`; either branch can be upgraded and verified
without the other. Combined releases must apply both expand-only branches and
then revision `009_merge_learning_progress`, whose `down_revision` is
`(007_learning_sessions, 008_owned_progress)`, before core rollout.
Targeted releases use the named branch target and never use an ambiguous bare
`head`. US3 receives a deterministic owned-roadmap plus published-learning-
content fixture; US4 receives a deterministic owned-roadmap fixture.

Foundation backfill labels a roadmap UI-compatible only when actor ownership,
stable milestone keys, and ordinals are deterministic. Delegated BFF calls use
the enriched response schemas declared by the core OpenAPI extension; an
unverifiable legacy record returns `409 LEGACY_RECORD_NOT_UI_COMPATIBLE` instead
of a partial DTO or invented data. Approved machine v1 responses retain their
documented legacy shape.

### Authentication and certificate lifecycle

The BFF is a confidential Entra web client and uses a Key Vault certificate
mounted by CSI. Rotation registers the replacement public key at least 24 hours
before retirement, waits for every BFF replica to report the new version and
acquire a core token, and proves a new sign-in callback plus an existing-session
token refresh through every replica before declaring readiness. The old
credential is removed within 48 hours. Emergency revocation bypasses overlap;
normal continuity checks must fail if any replica cannot complete sign-in or
token acquisition. Core machine consumers use separate app-only roles. BFF
session/token-cache encryption uses a versioned Key Vault key ring: new writes
use the active version, a bounded decrypt-only set supports normal overlap,
authenticated access rewrites active caches, and compromise response revokes
every session indexed by the affected version before key removal.

The four-hour core-image lifecycle CronJob uses its own Workload Identity with
administrator-consented Microsoft Graph `User.Read.All` only for read-only
known-user checks. Departure blocking and a durable session-revocation outbox
row commit atomically before the reconciliation checkpoint advances. A
dispatcher running at least every five minutes calls the BFF ClusterIP
`POST /internal/v1/session-revocations` with a token containing only
`LearningBff.Session.Revoke`; it retries with at most a one-hour delay until
acknowledgement, alerts at two hours, pages at six, and enforces a twelve-hour
post-recognition deadline. The BFF validates the
lifecycle client and role, then atomically revokes owner-indexed sessions before
acknowledging. No public rule forwards the internal path to BFF/core, the UI
server rejects the reserved prefix, and NetworkPolicy permits only the lifecycle
service account.

### Azure topology

Platform Operations, never Jenkins, runs the reviewed Terraform bootstrap with
an interactive Entra identity. `backend.tf` uses Azure Storage remote state and
blob-lease locking; `versions.tf`, `providers.tf`, and the committed lock file pin
both AzureRM and AzureAD providers. The external bootstrap provisions/imports
Key Vault, Managed Redis, PostgreSQL, monitoring, Workload Identities,
Application Gateway for Containers, DNS/certificates, Entra registrations and
administrator consent, Jenkins delivery identities, data-plane principals, and
evidence storage. Platform Operations also installs the pinned ALB Controller
and the cluster-admin-owned migration namespace/RBAC/admission guardrails.
`bootstrap-ui-platform.sh` and `bootstrap-data-principals.sh` never emit the
environment manifest. Only after every Terraform module—including delivery-
evidence lifecycle and monitoring rules—has been applied, every declared
identity/principal exists, the controller and migration guardrails are live,
and live denial checks pass does `finalize-ui-platform.sh` emit the
schema-validated, non-secret reviewed
`platform-bootstrap-nonprod.json` with state lineage/serial, configuration
digest, tenant/subscription/resource-group, resource IDs, identity IDs, and
origins plus controller and migration-policy attestations. It also records
provider-registration and quota/capacity attestations
that expire after seven days. Jenkins has no Terraform apply/import permission and blocks protected
delivery when that manifest is missing, stale, or inconsistent with live
resources and exact ACI template bindings.

`platform-configuration-digest-v1.yaml` is the canonical digest policy and is
itself an input. It allowlists reviewed IaC/Kubernetes/provider-lock/platform-
script/config-schema/mandatory-skill regular files, normalizes repository-
relative paths, sorts them bytewise, and hashes a stream containing path,
executable mode, byte length, and per-file SHA-256. It rejects symlinks, path
traversal, and missing required inputs. The emitted environment manifest,
Terraform state/plan/cache/local `terraform.tfvars`, evidence/logs, secrets, and
VCS metadata are explicitly excluded, avoiding self-reference while making
matching add/remove/rename/mode/content drift observable.

Bootstrap authorization is just-in-time and time-bounded through PIM; no
standing human assignment is assumed. The permission matrix is:

| Bootstrap action | JIT permission and exact scope | Explicit denial/expiry |
|---|---|---|
| Terraform state | `Storage Blob Data Contributor` on only the named state container | No storage-account keys or other containers; deactivate after the run |
| Application resources | `Contributor` on only the application resource group | No `Owner`, subscription-wide resource writes, or role assignment through Contributor |
| Shared network/DNS, when outside the app RG | `Network Contributor` / `Private DNS Zone Contributor` on only named subnet/zone resources | No unrelated VNet/zone mutation |
| Azure role assignments | `Role Based Access Control Administrator` on only the app RG and named shared resources | No role-definition creation, Azure Policy, or broader assignment scope |
| Provider/quota prerequisites | Custom subscription role limited to the allowlisted provider read/register actions and quota/usage reads recorded in the manifest | No general subscription resource mutation; seven-day attestation expiry |
| Entra app objects | JIT `Application Administrator` for the declared registrations/service principals | No user/group/tenant administration or unrelated app ownership |
| Microsoft Graph application consent | A separate JIT `Privileged Role Administrator` approval only for declared `User.Read.All` consent | No `Global Administrator`; activation ends immediately after consent evidence |
| PostgreSQL bootstrap | PIM-controlled database-bootstrap administrator group while creating the scoped principals/procedures | No routine learning-data access; remove/deactivate after denial tests |

The finalization script records assignment IDs, activation/expiry, operator and
separate consent-approver object IDs, scopes, plan digest, and negative checks in
the manifest without secrets. It fails for standing/excess scope, one person
attempting both app change and Graph-consent approval, `Owner`/`Global
Administrator`, state access outside the container, or any Jenkins principal.

The existing AKS resource in `infra/azure/main.tf` enables OIDC and Workload
Identity and disables the legacy `web_app_routing` add-on. A pinned ALB
Controller release is installed by Platform Operations with its own Workload
Identity/RBAC during external bootstrap and attested by finalization before any
live Gateway/HTTPRoute application. Application Gateway for Containers terminates public TLS and
routes `/` to UI and `/bff/*` to BFF. No public rule forwards lifecycle/core
paths to BFF/core; the UI NGINX server explicitly returns 404 for
reserved `/api/` and `/internal/` prefixes even though its `/` fallback is broad.
The legacy NGINX Ingress manifest/controller is removed. Terraform and
the URL helper expose the AGC HTTPS browser origin as the sole authoritative
browser URL.

A bounded 12-hour `concurrencyPolicy: Forbid` CronJob is the only workload that
assumes the gateway-certificate/DNS identity. It mounts the reviewed rotation
script read-only into a digest-pinned Azure CLI runner, emits expiry/convergence
signals, and uses a default-deny NetworkPolicy. A separate bounded 20-hour
CronJob uses the lab-validation identity/role to keep every active reference
inside the 24-hour requirement; its egress permits PostgreSQL/Entra/DNS and
public HTTPS while excluding private, link-local, metadata, cluster, and other
internal ranges, with application allowlist/redirect checks still mandatory.

Core exposes one HTTPS listener on port 8443 through both its ClusterIP and the
machine-only internal LoadBalancer. The Key Vault-issued certificate contains
SANs for `core.<namespace>.svc`, `core.<namespace>.svc.cluster.local`, and the
private machine FQDN. BFF uses
`https://core.<namespace>.svc:8443/api/v1` and validates the mounted private-CA
bundle; approved machines trust the same CA. Approved machine consumers must be
inside the AKS VNet, a peered VNet, or an explicitly approved private-connected
network and use a private-DNS name for a Kubernetes `LoadBalancer` Service with
an Azure-internal annotation, restricted source ranges/NSGs, and no public IP.
Because the internal load balancer is L4, the core server itself terminates TLS
using a Key Vault-issued certificate mounted through CSI, serves HTTPS, rotates
the certificate without exposing its private key, and answers HTTPS health
probes. Machine app-role authentication remains mandatory after network and TLS
validation. Kubernetes default-deny policies allow only declared service hops.

After external finalization, Jenkins validates manifest/schema/repository digest on
the identityless validator. On a protected ref, the deployer template then uses
its narrowly scoped control-plane `Reader` grant on the target resource group
(with no Terraform-state or data-plane read) to compare manifest IDs/tags with
live resources and run a read-only platform preflight for ACR reachability, AKS
version/capacity/networking/OIDC, ALB Controller, private DNS,
data-plane principals, and legacy-ingress absence. A separate post-finalization
validation proves AKS kubelet `AcrPull`, publisher `AcrPush`, deployer AKS
permission, controller denial, cross-identity denial, and the declared
tenant/subscription/resource-group scopes.

The first-release application-container resource profile is exact:

| Service | CPU request | CPU limit | Memory request | Memory limit |
|---|---:|---:|---:|---:|
| UI | `50m` | `250m` | `64Mi` | `128Mi` |
| BFF | `100m` | `500m` | `256Mi` | `512Mi` |
| Core | `250m` | `1000m` | `512Mi` | `1Gi` |

UI, BFF, and core each use those Kubernetes requests/limits, an HPA with two
minimum and four maximum replicas at a 70% average CPU-utilization target
relative to that service's CPU request, a PDB with `maxUnavailable: 1`, and a
hostname topology-spread constraint with `maxSkew: 1` and `ScheduleAnyway`.
Injected platform sidecars, when present, declare their own resources and do not
alter these application-container values. Readiness gates remove unhealthy
replicas before traffic or rollout completion; liveness remains process-local.
The manifest test verifies each exact value and policy independently and
confirms that scaling one service does not modify either of the others.

Each service emits a distinct Azure Monitor/Application Insights identity with
environment, service version, and image digest. Gateway, UI, BFF, and core
propagate trace context and record route-class request count, error count,
duration, readiness, dependency outcome, pod restart, replica, and HPA-saturation
signals without tokens, request bodies, learner identifiers, or answer content.
`operational-alert-profile-v1` defines objective alert gates: zero ready replicas
for five consecutive minutes; at least 5% 5xx responses with at least 20 requests
in each of two consecutive five-minute windows; route-class p95 above 2 seconds
for UI static traffic, 30 seconds for roadmap, 10 seconds for guidance, or 5
seconds for other personalized API traffic with at least 20 requests in each of
two consecutive five-minute windows; at least three container restarts in any
10-minute window; or HPA at four replicas with average CPU at or above 70% for
15 consecutive minutes. An unacknowledged session-revocation outbox row alerts
at two hours, pages at six, and is critical at its 12-hour deadline. Public
gateway and private-core certificates warn Platform Operations at 30, 14, and
7 days before expiry and page critically below 48 hours. A directory
reconciliation with no successful completion for six hours warns Application
and Platform Operations and pages both at eight hours. An active lab reference
whose validation age exceeds 30 hours warns Learning Content Operations and
pages it plus Application Operations at 36 hours; three consecutive failures or
an unavailable destination alerts Learning Content Operations immediately.
Readiness and restart alerts page Application Operations
immediately; 5xx/latency alerts page after the second breached window; HPA
saturation warns Application and Platform Operations at 15 minutes and pages
both at 30 minutes. Gateway, cluster, or managed-dependency attribution also
routes to Platform Operations. Injected failures must identify the owning
service and exercise acknowledgement/escalation routing.

### Implementation readiness, pilot SLOs, and prerequisite gates

[implementation-readiness-contract.md](./contracts/implementation-readiness-contract.md)
is the normative readiness authority. Its formal implementation-gate model is
the single source for gate states, artifact authority, entry criteria,
exceptions, revalidation, checklist completion, and decision ownership. Its
outcome matrices, stable codes,
numeric bounds, owners, evidence fields, and failure effects are implementation
inputs and release gates. Missing or conflicting normative inputs block
implementation; evidence that can only be produced by implemented or deployed
behavior blocks the corresponding story, protected-release, or pilot checkpoint
rather than earlier local authoring. Every obligation must also have a valid row in
[requirements-traceability.md](./requirements-traceability.md); a missing,
empty, duplicate, out-of-order, or unknown-task mapping blocks implementation
and release. CI also verifies the readiness manifest's declared digest, derived
per-case fixture digests, operation set, and exact denominator arithmetic plus
both performance profiles' full-profile digests, the interaction fixture set's
exact-byte digest and derivation rules, pinned BFF/core contract digests, generated-mapper digest/drift gates where applicable,
evidence schemas, assignments, timing boundaries, and timeout policies; neither test code nor a runtime
environment may replace those approved inputs.

The non-production pilot operates only from 08:00-18:00 Israel time on business
days and has no production SLA. The exact pilot targets are:

| Concern | Target and measurement |
|---|---|
| Browser journey | 99.0% per calendar month. One observation runs per eligible minute and passes only when public TLS Gateway, UI/runtime-config, and `/bff/v1/capabilities` readiness/contract checks all pass. Availability is successful eligible observations divided by all eligible observations. Maintenance is excluded only with at least 24-hour notice, capped at four hours/month; unannounced and above-cap minutes remain in the denominator. |
| Stateless UI/BFF/core | RPO 0 for Git/ACR-digest/reviewed configuration and RTO at most 60 minutes from last-known-good immutable artifacts. |
| PostgreSQL | RPO at most five minutes and RTO at most four hours through continuous backup/PITR with seven-day retention; restore remains closed until retention catch-up and owner/access checks pass. |
| Redis sessions | Durable-session RPO is intentionally excluded; session loss may require sign-in but cannot lose core learning data. RTO is at most 60 minutes and restored state must pass key/version validation. |
| Delivery evidence | RPO 0 after immutable-version acceptance and RTO at most four hours; delivery remains stopped while evidence access or completeness is unavailable. |
| Jenkins controller audit | RPO 0 after a two-copy fsync and RTO at most four hours for replicated-store restore plus queue/run, webhook, and Azure-evidence reconciliation. Protected scheduling remains blocked until every accepted orphan is terminal and every post-mutation orphan has verified rollback or approved recovery. |
| Telemetry and labs | Telemetry may lose at most five minutes or 1,000 safe envelopes per process and is non-authoritative. External labs have no provider RTO/RPO; validation runs every 20 hours (never older than 24 hours) and a report triggers validation within 15 minutes. |
| Regional disaster recovery | Cross-region Entra/Azure managed-service failover and provider SLA commitments are excluded from this pilot; dependency behavior still fails closed. |

Monthly evidence records scheduled and excluded minutes plus notice, eligible/
successful/failed one-minute observations, achieved availability, incidents,
actual exercised RTO/RPO, the PostgreSQL restore test, the replicated controller-
audit restore/reconciliation test, and owner approval. RTO begins at the first
failed eligible observation or declared outage, whichever is earlier, and ends
at the first complete successful functional recovery check. RPO is measured
against the last accepted authoritative domain transaction, deployment digest/
configuration, controller transition, or immutable evidence version.
Application Operations owns the per-minute observation schedule, missed-run
failure accounting, and calendar-month close. Platform Operations co-approves
the recovery and infrastructure evidence. The monthly record is written through
the immutable delivery-evidence path; a missing observation is a failed eligible
minute, and a missed monthly close blocks the next pilot opening until reconciled.

No planning assumption satisfies a prerequisite. The full evidence payload in
the readiness contract is mandatory; this execution register fixes its owner and
freshness gate:

| Prerequisite | Accountable owner | Freshness/gate | Failure effect |
|---|---|---|---|
| Entra tenant/apps/scopes/roles/consent/groups/issuer | Identity/Security Operations | Within 24 hours before pilot and after every identity/config change | Block sign-in, machine traffic, and protected delivery. |
| Approved machine clients/private networks | Security Reviewers and Platform Operations | Manifest attestation at most seven days old plus live DNS/TLS/denial probe on verification day | Block the affected machine consumer. |
| External bootstrap and final reviewed manifest | Platform Operations | Plan/state/assignment/controller/migration/provider/quota/capacity evidence at most seven days old; compare live target-RG resources on every protected build | Block protected publication/promotion; Jenkins never repairs or reads Terraform state. |
| AKS/ACR and platform controls | Platform Operations | Live capacity/OIDC/Workload-Identity/ALB/PDB/HPA/topology/private-DNS/migration/legacy-ingress preflight within 15 minutes of promotion | Block promotion before mutation. |
| Jenkins controller/cloud `azure` | Platform Operations | Scheduled daily and every protected build; provisioning principal must have at least 30 valid days | Quarantine protected builds; only safe identityless validation may continue. |
| ACI validator/publisher/deployer | Platform Operations | Smoke after credential/template change and within 24 hours before protected release | Block the affected lane with no local/fallback agent. |
| Redis/PostgreSQL/Key Vault/CSI/Gateway/Monitor/evidence | Platform Operations with Application Operations | Live identity, denial, readiness, version, immutable-write, and exporter checks within 15 minutes of pilot opening and protected release | Do not open the pilot or promote. |
| Lab providers/references | Learning Content Operations and Security Reviewers | Dual-approval policy and complete validation at most 24 hours old | Do not publish/display the affected reference. |
| Pilot population | Product/UX Research | Frozen single-participant PoC allocation/consent/script/facilitator evidence within seven days of the participant | Do not begin the exploratory PoC. |
| Supported browsers/assistive technology | Product/UX Research and Application Operations | Exact version/matrix smoke on verification day; release evidence at most 30 days old | Block UI release evidence until the frozen matrix passes. |

### Jenkins delivery strategy

The controller at `http://localhost:8080` uses existing cloud `azure`.
Before `node`, agent allocation, checkout, or workspace creation, a globally
trusted administrator-installed controller plugin from a pinned protected
revision and verified artifact digest invokes a `RunListener` independently of
repository Jenkinsfiles/shared libraries, creates the pending controller
`RunAction` on run start, and owns monotonic updates, restart recovery,
retention, and exactly-once finalization. Omitting or shadowing an audit call in
SCM cannot bypass it. Repository scripts may request allowed stage transitions
or synchronize the record to evidence after authentication but cannot create,
replace, suppress, or finalize it.
Every ref then runs checkout, change planning, contract/catalog drift, lint,
typecheck, unit, contract, and non-Azure integration validation only on
`azure-aci-validator`, which has no system-assigned or user-assigned managed
identity. Pull requests and unprotected refs stop there. The template cannot
enter any stage that invokes Azure authentication, ACR publication, evidence
upload, migration, or AKS deployment. Protected delivery alone may request the
publisher/deployer templates after validation and the environment gate.
`azure-aci-publisher` binds exactly the ACR/evidence publisher UAMI;
`azure-aci-deployer` binds exactly the AKS/evidence deployer UAMI.
The deployer additionally has control-plane `Reader` only on the declared target
resource group so it can validate the bootstrap manifest and live platform; it
cannot read Terraform state, Redis/PostgreSQL data, Key Vault secret values, or
ACR content.
Post-bootstrap delivery-identity validation compares live template and running
ACI identity resource IDs with the reviewed bootstrap manifest
and rejects missing,
additional, swapped, or system-assigned identities; it also proves that the
validator template is identityless.

Pipeline execution classifies changes from merge base, validates affected lanes,
validates the canonical BFF/core OpenAPI and guidance-topic catalog contracts,
classifies the implementation-readiness contract as all-service plus every
validation lane and the requirements-traceability matrix as all-service plus
contract-integrity/infrastructure validation,
classifies a readiness-manifest change as all-service plus infrastructure
validation through T034/T156 and a performance-profile change as all-service
validation through T034/T157,
classifies mandatory Azure provision/teardown skill executable or Terraform-
template changes as infrastructure plus all-service work rather than docs-only,
checks generated BFF route/core-client/catalog, UI client/validator/type/catalog,
core validator/runtime-catalog, and BFF boundary-mapping drift,
archives mandatory boolean `contractIntegrity`, `readinessScenarios`,
`performanceProfile`, and `infrastructure` selections alongside the three
service selections; multiple matching paths boolean-OR those selections without
clearing and retain sorted unique reasons, so no later stage recalculates path
scope. A genuine first
or missing baseline is encoded only as JSON `null` and forces every service and
validation lane on; a malformed or unresolvable supplied revision blocks the
plan. The pipeline then builds/scans/SBOMs selected images, resolves immutable
ACR digests, and promotes
in `core -> BFF -> UI` order without rebuilding. Before each environment
mutation, it records the service, previous and intended digest/configuration,
compatibility result, mutation command, compensating command, and reversibility
in an append-only journal. Failure stops downstream promotion and replays only
completed reversible mutations in reverse order. Each entry receives at most
three attempts after 0/15/45-second delays inside a 20-minute total rollback
deadline; timeout or verification failure is journaled, stops at that dependency
instead of skipping out of order, sets `rollback_failed`, quarantines the
environment, and pages Application/Platform Operations for two-person recovery.
A destructive or otherwise
irreversible mutation cannot enter automatic promotion; it requires a separate
operator-approved recovery plan. Database contract migrations are never
automatically reversed.

Manual rebuild-all or recovery requires a configured Jenkins Delivery Recovery
Operator and a distinct Platform Operations approver; neither path bypasses
ordinary identity, compatibility, evidence, or lock gates. Pre-mutation
application failures notify Application/Delivery Operations, platform failures
notify Platform/Delivery Operations, evidence failures also notify Security
Reviewers, and any post-mutation or rollback failure pages Application and
Platform Operations with 15-minute acknowledgement and 30-minute incident-
commander escalation. The full notification/result matrix is normative in the
Jenkins delivery contract.

For a selected core schema change, the protected sequence is: schema
compatibility gate, accepted pre-mutation evidence, then
`scripts/ci/migrate-core.sh` creates and watches a bounded in-cluster Job whose
dedicated migration Workload Identity alone has the PostgreSQL DDL role and
network path. In the dedicated migration namespace, deployer RBAC permits Job
`create/get/watch/delete`, Pod `get/list/watch`, and `get` on `pods/log`, with no
exec/attach/port-forward/secret/configuration/service-account mutation or
database access. A cluster-admin-owned ValidatingAdmissionPolicy/Binding that
the deployer cannot change enforces the exact migrator service account, one
nonprivileged container, approved ACR core repository by digest, fixed runner,
allowed target, allowlisted environment/volumes, bounded deadline/retry/TTL,
and no host access. Because the deployer cannot push to ACR and the publisher
cannot create the Job, selecting and publishing the migration image require
separate identities. Status, logs, admission decision, identity, digest, heads,
timeout/retry result, and cleanup become evidence before core rollout. A combined US3/US4 release targets
revision `009_merge_learning_progress`; a targeted branch release names `learning@head` or
`progress@head`. Every migration journal entry is marked irreversible and has no
automatic compensating SQL. If migration succeeds but core rollout fails, image
rollback uses the retained expanded schema; evidence records the failed rollout,
restored digest, schema heads, and required operator recovery. If migration
itself fails, promotion stops, the database is quarantined for operator repair,
and no core image mutation occurs.

### Jenkins provisioning credential lifecycle

Platform Operations owns the service principal used only by Jenkins cloud
`azure` for ACI lifecycle and identity attachment. It has no ACR push or AKS
deployment permission. Rotation occurs at least every 90 days with alerts at
30, 14, and 7 days. Missing/unreadable expiry or fewer than 30 valid days places
cloud `azure` in quarantine: protected-branch Azure stages cannot request a new
agent. Developer-local validation remains available, but Jenkins has no local or
controller-agent fallback; ordinary Jenkins validation resumes only when the
identityless ACI validator can be provisioned. The local rotation procedure
uses a dedicated Jenkins credential-manager identity that can update only the
stable Azure cloud credential entry and cannot configure jobs, run builds, or
read unrelated credentials. It uses the localhost Jenkins API, CSRF crumb, and
protected standard-input or file-descriptor secret handoff. Secrets never enter
arguments, environment variables, logs, or retained files. Normal rotation
validates the identityless validator plus the publisher and deployer templates
before revocation and clears quarantine only after all three pass. Emergency
rotation revokes first and disables ordinary build provisioning. An audited
rotation-validation path may provision only one smoke agent from each declared
template; those agents cannot execute repository jobs, publish images, or deploy
workloads. Ordinary provisioning remains quarantined until all three
replacement-template checks pass.

### Delivery evidence strategy

Before agent provisioning the trusted controller-installed `RunListener` creates the
minimal, authoritative controller-lifecycle `RunAction` audit attempt, which is
explicitly non-authoritative as delivery evidence, without allocating an
executor or workspace and appends lifecycle events for `started`, `agent_requested`,
`agent_connected`, `evidence_active`, and exactly one terminal state of
`succeeded`, `failed`, or `aborted`. The listener runs even when the Jenkinsfile
contains no audit call or attempts to shadow repository/library symbols. Every exit path closes the attempt with
timestamps and the failed stage. Once an authenticated agent starts, the record
is copied into the authoritative evidence set; a pre-agent failure remains in
the access-restricted controller audit for 90 days and is never presented as
authoritative delivery evidence. Every transition is fsynced to both the normal
run record and a host-managed append-only replicated audit volume before ACI
allocation; protected scheduling fails closed while that store is unhealthy.
Platform Operations performs hourly integrity checks and encrypted backup. The
replica provides RPO 0 after an accepted transition and RTO at most four hours
for controller-disk-loss recovery. After restore, build IDs are reconciled
against queue/run metadata, webhook audit, and Azure evidence; an accepted
nonterminal orphan becomes `aborted_recovered`, and protected delivery remains
blocked until every post-mutation orphan has verified rollback or approved
recovery in a verified terminal state. Evidence is published under
`deliveries/<environment>/<build-id>/<stage>/<artifact>` to authoritative Azure
Storage. Uploads use `If-None-Match: *`.

A digest published to ACR but not promoted is explicitly
`published_unpromoted`, is ineligible for another build without a new release
manifest and fresh gates, and is quarantined from release aliases. Unreferenced
unpromoted artifacts become GC-eligible after 30 days while their provenance and
disposition remain in the 90-day evidence set; promoted or held digests are
excluded.

Terraform defines a writer role excluding blob read, list, tag mutation, and
delete operations. Azure ABAC conditions restrict each identity to its assigned
environment/stage prefix. The content validator and required-artifact manifest
must pass before upload, and all pre-mutation evidence must be accepted before
promotion. A missing, rejected, or unavailable evidence write fails closed.
Accepted versions receive a locked time-based immutability policy for the fixed
90-day retention window. An approved incident hold sets the Azure version-level
legal-hold boolean on every enumerated blob version rather than changing or
extending that locked interval. Clearing those holds never shortens the base
lock; deletion is eligible only after `immutable_until` and when no version hold
remains. Partial set/clear operations enter reconciliation and are never reported
active/released until every target version matches.
Configured Delivery Operators and Security Reviewers Entra groups receive read
access. A separately configured Evidence Hold Managers Entra group is the sole
authority for hold creation, expiry extension, and release requests and may
mutate only their separate audited control metadata; it has no direct Azure
blob-version hold permission. The dedicated reconciler identity alone applies
or clears the exact enumerated version-level legal holds authorized by that
metadata. Neither principal can read evidence, create delivery artifacts,
change the base retention policy, or delete blobs. Authorized holds
protect selected evidence only through an expiry no later than 180 days from
creation and record hold ID, owner, reason, incident reference, start, target-
version inventory, and expiry; expiry clears every version hold through the same
reconciled operation.

### Lab governance

`config/approved-lab-providers.yaml` begins empty. A provider addition or domain
expansion requires two distinct humans: one member of the Learning Content
Owners Entra group and one member of the Application Security Reviewers group.
Publication validates HTTPS, redirects, metadata, reachability, and recorded
policy version; the bounded 20-hour dedicated-identity CronJob revalidates
active references before the 24-hour limit.

## Phase 2: Implementation Planning

Implementation is decomposed in [tasks.md](./tasks.md):

1. Set up independent UI, BFF, and core build/test environments.
2. Complete the named minimum foundation required for the US1 roadmap MVP.
3. Deliver and independently demonstrate the US1 roadmap MVP locally and in the
   three-service container environment without claiming a protected release.
4. Complete each story's explicit additional prerequisites and deliver US2 skill
   guidance, US3 focused learning/review, and US4 progress review independently.
5. Complete the remaining Azure, lifecycle, lab, Jenkins, evidence, operational,
   and pilot foundations required for the complete release.
6. Complete Jenkins/Azure delivery, security, evidence, operational, and pilot
   verification.

Tests are defined before or alongside implementation. Only the named
minimum-foundation task set in `tasks.md` blocks US1. US2 and US3 add their
catalog and lab prerequisites; US4 consumes the minimum owned-roadmap foundation.
The remaining foundation and cross-cutting work blocks protected release, not
local story implementation. Cross-cutting release verification follows the
selected stories and complete-release prerequisites.

## Complexity Tracking

No constitution violation requires an exception. The separate UI and BFF are
intentional requirements that isolate presentation, browser security, and core
business authority while preserving machine-consumer independence.
