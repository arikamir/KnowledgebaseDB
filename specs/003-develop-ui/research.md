# Research: Three-Service DevOps Career Agent UI

> Historical delivery decisions below are superseded by feature 006. Current
> authority is GitHub Actions for build and ACR publication and Argo CD for
> application reconciliation.

## Decision 1: Build a separate React and TypeScript UI service

- **Decision**: Implement a client-only React SPA with strict TypeScript, Vite,
  and client-side routing. Build static assets into an independent minimal web
  server container.
- **Rationale**: Component composition fits forms, milestones, reviews, and
  progress views. TypeScript checks the UI-to-BFF DTO boundary. Vite supports
  fast local iteration and optimized static output without introducing a UI
  server that could blur the separate BFF boundary.
- **Alternatives considered**: Next.js adds server behavior beside the mandated
  BFF and SSR/SEO is not required. Vue is equally viable but offers no stated
  project advantage. Server-rendered FastAPI couples UI and core deployment and
  is now explicitly invalid.
- **Sources**: [React application creation](https://react.dev/learn/creating-a-react-app),
  [Vite guide](https://vite.dev/guide/), [Vite build](https://vite.dev/guide/build)

## Decision 2: Inject UI configuration at runtime

- **Decision**: Serve nonsecret runtime configuration separately from hashed UI
  assets: relative BFF path, accepted BFF contract range, and public feature
  flags. Validate it before enabling personalized actions.
- **Rationale**: Vite environment substitution occurs at build time, which
  conflicts with environment-specific destinations without rebuilding. Runtime
  configuration allows one immutable image digest to move across environments.
- **Alternatives considered**: Per-environment builds weaken promotion and
  rollback. Baking a backend URL into the UI exposes topology and still does not
  satisfy the BFF-only rule.

## Decision 3: Build a separate TypeScript/Fastify BFF

- **Decision**: Use Node.js 24 LTS, strict TypeScript, Fastify JSON-schema
  validation, MSAL Node, Redis sessions, and a generated client for the core
  OpenAPI contract.
- **Rationale**: A TypeScript BFF shares UI-facing DTO types and isolates
  presentation orchestration while Fastify provides a small explicit API
  boundary. It remains independently deployable and contains no core domain
  rules.
- **Alternatives considered**: A Python/FastAPI BFF reduces languages but makes
  two similar Python services easier to blur and gives weaker UI contract
  ergonomics. Combining BFF with UI or core violates explicit requirements.
- **Sources**: [Node release policy](https://nodejs.org/en/about/previous-releases),
  [MSAL Node token acquisition](https://learn.microsoft.com/en-us/entra/msal/javascript/node/acquire-token-requests)

## Decision 4: Keep browser and BFF on one public origin

- **Decision**: Route `/` and static assets to the UI Service and `/bff/*` to
  the BFF through one TLS hostname, while retaining separate Deployments,
  Services, images, and rollouts. The core uses a private ClusterIP for BFF
  traffic; supported machine consumers use a separately governed private core
  route when required.
- **Rationale**: One browser origin eliminates credentialed CORS complexity and
  supports host-only secure cookies and exact-origin CSRF validation without
  sacrificing service independence.
- **Alternatives considered**: Separate public UI/BFF hosts are valid but add
  CORS, cookie, and CSRF configuration with no deployment benefit. Exposing the
  core on the browser origin would weaken the BFF-only boundary.
- **Sources**: [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/),
  [AKS application routing](https://learn.microsoft.com/en-us/azure/aks/app-routing)

## Decision 5: Make the BFF the Entra confidential web client

- **Decision**: The BFF performs single-tenant authorization-code sign-in with
  MSAL Node and requests the delegated core API scope. It stores Entra token
  cache material only in the encrypted server-side session store. The browser
  receives a random opaque `Secure`, `HttpOnly`, `SameSite=Lax`, host-only
  cookie and a session-bound CSRF token.
- **Rationale**: Tokens never enter browser storage or the UI bundle. The BFF
  can silently acquire a fresh core token and revoke its own session. Entra
  remains responsible for organizational policy and MFA.
- **Alternatives considered**: SPA token acquisition exposes tokens to the UI
  and bypasses the BFF session boundary. Implicit and password flows are not
  acceptable. OBO is unnecessary because the BFF obtains a token intended for
  the core during its own auth-code flow.
- **Sources**: [Microsoft authentication flows](https://learn.microsoft.com/en-us/entra/identity-platform/msal-authentication-flows),
  [app scenarios](https://learn.microsoft.com/en-us/entra/identity-platform/authentication-flows-app-scenarios)

## Decision 6: Require independent core token validation

- **Decision**: The BFF sends `Authorization: Bearer <core access token>` to
  `/api/v1`. The core validates signature/JWKS, issuer, tenant, audience,
  lifetime, authorized client, and required scope, then derives ownership from
  `(tid, oid)`. Browser employee IDs and identity headers are never authority.
- **Rationale**: This preserves authorization across the service boundary and
  protects direct core access even if routing or client behavior changes.
- **Alternatives considered**: Trusted BFF headers can be spoofed if network
  controls fail. ID tokens are not API access tokens. App-only identity loses
  per-employee ownership.
- **Source**: [Microsoft access-token validation](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens)

## Decision 7: Keep BFF orchestration thin and contracts independent

- **Decision**: Version UI-to-BFF as `/bff/v1` and BFF-to-core as `/api/v1`.
  Treat `specs/003-develop-ui/contracts/bff-api-v1.openapi.yaml` as the
  machine-readable browser/BFF source of truth and generate BFF route validators
  plus UI client/types/validators from it.
  Treat `specs/003-develop-ui/contracts/core-api-v1.openapi.yaml` as the
  machine-readable core API source of truth. Validate it and fail on checked-in
  generated-client/type/validator drift before generating the BFF core client
  and before core or BFF tests/builds. The BFF mapping layer has explicit
  contracts proving that each camelCase browser DTO maps to a valid core DTO;
  both boundaries and all generated consumers record their contract digest.
  Treat `specs/003-develop-ui/contracts/supported-guidance-topics-v1.yaml` as the
  source of truth for canonical topic IDs and aliases. Generate the core runtime
  catalog plus BFF/UI consumer artifacts from it and fail when any generated
  content drifts, duplicates an ID/alias, or changes deterministic order without
  a catalog-version change.
  The BFF validates view requests, composes UI DTOs, maps safe errors, propagates
  idempotency and trace context, and never scores reviews, authorizes ownership,
  chooses next actions, or persists domain state. Each boundary exposes
  non-mutating capability metadata with its current version, accepted peer
  range, and enabled mutation features. State-changing requests require a
  nonempty version-range intersection at both boundaries and fail closed when
  capability metadata is missing, malformed, or incompatible.
- **Rationale**: Independent major versions let UI composition evolve without
  changing core rules. Generated clients and provider/consumer contract tests
  prevent accidental drift. Repository dependency rules forbid UI imports of
  BFF/core runtime code and BFF imports of core application code; only generated
  contract/client artifacts cross those source boundaries. Change-plan fixtures
  prove presentation-only and composition-only changes do not select core.
- **Alternatives considered**: One shared API version couples releases.
  Duplicating domain decisions in the BFF creates inconsistent behavior.
  Build-time version assumptions alone cannot protect independently deployed
  old/new combinations. Generating a contract from implementation after the
  endpoint is written makes drift detection too late and was rejected. Separate
  hand-maintained UI, BFF, and core topic lists were rejected because support
  decisions would diverge across independently deployed services.

- **Route ownership**: Foundation provides shared core and BFF route registries
  for auth, health, capabilities, and cross-cutting dependencies. Each story
  contributes one feature route module through the registry. A monolithic router
  edited by every story was rejected because it creates false cross-story merge
  and verification dependencies.

## Decision 8: Retain normalized core learning persistence

- **Decision**: Normalize identity ownership, employee-session progress,
  reviews, answers, milestones, and lab reports in the core database. Keep
  versioned authored content as structured snapshots. Use Alembic for deployed
  schema evolution. Put actor-owned roadmap identity, stable milestone keys,
  and exactly-one employee/application ownership constraints in Foundation
  revision `006_owned_roadmaps`. Give US3 a deterministic employee-owned
  roadmap plus published-content fixture and US4 a deterministic employee-owned
  roadmap fixture. US3 revision `007_learning_sessions` and
  US4 revision `008_owned_progress` are sibling Alembic heads with
  `down_revision = 006_owned_roadmaps`; merge revision
  `009_merge_learning_progress` depends on both heads and is required for a
  combined release. Targeted upgrades name the intended branch head rather than
  ambiguous `head`; neither story migration depends on US1 or the other story.
- **Rationale**: Atomic scoring/completion, idempotent resume, ownership, and
  audit history require constraints and transactions. Foundation ownership
  removes the hidden sequential dependency from `006_owned_roadmaps` through
  `007_learning_sessions` to `008_owned_progress` and keeps the four slices
  independently testable. Only the core may access these records.
- **Alternatives considered**: JSON-only records weaken concurrency and query
  guarantees. BFF storage of learning state violates domain ownership. Seeding
  a fixture into a schema created by US1 would still make US3/US4 depend on US1.
  A single sequential chain from `006_owned_roadmaps` through
  `007_learning_sessions` to `008_owned_progress` was rejected because it makes
  US4 schema verification depend on US3 despite their independent stories.

## Decision 9: Use Redis only for BFF session state

- **Decision**: Store opaque session records, auth state/nonce, CSRF secret,
  expiry, encryption-key version, and encrypted MSAL cache material in a
  BFF-owned Redis dependency. Use a versioned Key Vault key ring with one active
  encrypting version, a bounded decrypt-only overlap set, lazy rewrite on
  authenticated access, and key-version indexes for compromise revocation. UI
  and core do not access Redis directly.
- **Rationale**: BFF replicas and restarts need shared revocable state. Redis is
  purpose-fit for expiring sessions and does not couple browser auth state to
  core persistence.
- **Alternatives considered**: Process memory is not restart/scale safe.
  Browser storage exposes tokens. Core database storage couples lifecycles.

## Decision 10: Use path routing, NetworkPolicy, and independent health

- **Decision**: Deploy UI, BFF, and core as separate workloads. A pinned ALB
  Controller manages the Application Gateway for Containers Gateway/HTTPRoutes
  for public UI and BFF only; the legacy NGINX Ingress/Web App Routing add-on and Ingress
  are removed. BFF reaches core through ClusterIP service DNS. Approved machines
  reach a separate Azure-internal L4 `LoadBalancer` through private DNS and
  approved VNet/peered/private-connected networks; core terminates HTTPS with a
  rotated Key Vault/CSI certificate, restricted source ranges/NSGs, and app-role
  authentication. NetworkPolicy denies UI-to-core. Each service exposes process-local
  liveness and dependency-aware readiness without making liveness depend on a
  downstream service. Each workload has resource requests, an HPA with two
  minimum/four maximum replicas and a 70% CPU target, a PDB with
  `maxUnavailable: 1`, and hostname topology spread with `maxSkew: 1` and
  `ScheduleAnyway`.
- **Rationale**: Routing and policy enforce the architecture while independent
  probes identify the failing service and avoid restart cascades. Explicit
  autoscaling and disruption policies make the scaling requirement testable and
  allow certificate/session behavior to be verified across BFF replicas without
  making the pilot unschedulable on a temporarily single-zone cluster.
- **Alternatives considered**: Public core routing for UI traffic bypasses the
  BFF. Shared probes hide failure origin. Liveness checks on dependencies cause
  cascading restarts. Fixed replica counts do not satisfy independent scaling;
  hard topology rejection can deadlock a constrained non-production cluster.
- **Sources**: [Kubernetes network policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/),
  [probe configuration](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

## Decision 11: Promote and roll back each immutable image independently

- **Decision**: Build, scan, and publish separate UI, BFF, and core images.
  Pin digests independently. Use backward-compatible expand-contract order:
  core, BFF, UI; remove old fields only after compatible consumers migrate.
  Verify current and previous compatible combinations. Before each deployment
  mutation, append the previous/intended state, compatibility result, mutation,
  compensating action, and reversibility to a journal. On failure, execute only
  completed reversible compensations in reverse order. Never automatically
  reverse a destructive database migration. Schema delivery runs a compatibility
  gate, writes accepted evidence, applies only an expand migration through
  `scripts/ci/migrate-core.sh` by creating a bounded Kubernetes Job in a
  dedicated namespace. Deployer RBAC permits Job `create/get/watch/delete`, Pod
  `get/list/watch`, and `get` on `pods/log`, while denying exec/attach/port-
  forward/secret/configuration/service-account mutation and database access. A
  cluster-admin-owned admission policy enforces the migrator service account,
  exact ACR core repository by digest, fixed runner/target set, nonprivileged
  security, allowlisted environment/volumes, and deadline/retry/TTL. The Job's
  dedicated Workload Identity alone receives the migration-only PostgreSQL DDL/backfill grants and network path. Job identity,
  immutable image digest, target, before/after heads, status/logs, timeout/retry,
  and cleanup become required evidence. The pipeline records the resulting
  branch heads as an irreversible journal entry and only then rolls out core. An irreversible
  mutation requires an operator-approved recovery plan before promotion.
- **Rationale**: This meets independent release/rollback requirements while
  preventing incompatible writes and keeping database migrations safe. A
  reverse journal restores all mutations made by the failed rollout rather than
  assuming that restoring one image digest also restores configuration or
  routing state.
- **Alternatives considered**: A combined image or synchronized release train
  violates independent operation. Blind database rollback risks data loss.
  A snapshot without compensating operations cannot safely unwind a partial
  multi-step rollout. Contract-first expansion was chosen so a failed core
  rollout can restore the previous image against the retained expanded schema;
  automatic down-migration was rejected as a data-loss risk.

## Decision 12: Test boundaries and journeys separately

- **Decision**: UI uses typecheck, lint, Vitest, Playwright, and accessibility
  checks. BFF tests auth/session/CSRF, error mapping, core-client contracts, and
  replica-safe sessions. Core tests token claims, owner isolation, migrations,
  lifecycle, scoring, and provider contracts. Deployment tests routing,
  NetworkPolicy, trace continuity, outage isolation, and independent rollback.
  Browser timing marks measure local-validation event-to-guidance time and the
  elapsed time from `career.result.fetch-resolved`, recorded after the complete
  response body is parsed and validated, to
  `career.result.accessible-render-committed`. Core performance uses
  the approved
  [`performance-profile-v1`](../../tests/performance/performance-profile-v1.json):
  two independent roadmap and guidance scenarios,
  each with 10 concurrent workers, two excluded successful warm-up requests per
  worker, and 10 measured requests per worker. The committed fixture set spans
  approved beginner, intermediate, and advanced profiles and supported guidance
  topics. The profile's full-profile and fixture-set digests cover the complete
  evidence schema; pinned BFF/core contract-byte digests bind the declared
  operation pairing. CI digest-matches both contracts, regenerates the
  BFF-to-core mapper, rejects drift, and retains the used mapper digest before
  deterministic worker assignment and 45-second roadmap/20-second guidance hard
  cancellation.
  Measurement uses a monotonic clock from core ASGI request entry through
  completion of response serialization after mapping and BFF transport have
  been excluded.
  Nearest-rank p95 is calculated over all 100 measured values per scenario;
  failures and timeouts remain in the denominator and contribute the scenario
  timeout value. Universal scenario enumeration separately comes from the
  approved manifest-digest and derived per-case-fixture-digest verified
  [readiness manifest](../../tests/fixtures/readiness-scenario-manifest-v1.yaml).
  Normal certificate rotation
  tests both a fresh authorization-code callback and an existing-session token
  refresh through every BFF replica before the old certificate can retire.
  Dependency tests build frozen core artifacts while changing UI presentation or
  BFF composition and reject forbidden cross-service source imports.
- **Rationale**: No single test layer can prove visual behavior, security
  boundaries, domain correctness, and operational independence. Explicit timing
  boundaries make the one-second outcomes reproducible; replica-directed sign-in
  closes the gap between certificate loading and actual authentication.
- **Alternatives considered**: End-to-end-only tests are slow and imprecise;
  unit-only tests cannot prove the deployed service graph.
- **Sources**: [Playwright best practices](https://playwright.dev/docs/best-practices),
  [WCAG 2.2](https://www.w3.org/TR/WCAG22/)

## Decision 13: Run all application services on one Azure AKS platform

- **Decision**: Deploy UI, BFF, and core as independent AKS Deployments in a
  shared application namespace. Install a version-pinned ALB Controller with a
  dedicated Workload Identity/RBAC before creating Application Gateway for
  Containers Gateway API resources for UI/BFF public paths. Keep core private:
  BFF uses ClusterIP, while approved machines use a TLS core endpoint behind an
  Azure-internal L4 LoadBalancer and private DNS. Do not create a public route
  for core.
- **Rationale**: This meets the Azure-only hosting requirement while reusing
  cluster capacity, identity, policy, DNS, and observability. Independent
  Kubernetes workloads preserve separate scaling and rollback without the cost
  and operational fragmentation of three compute products.
- **Alternatives considered**: Static Web Apps plus App Service plus AKS
  increases routing, identity, diagnostics, and release variation. Separate AKS
  clusters provide stronger isolation but are disproportionate for ten pilot
  users. Combining containers violates independent deployment requirements.
- **Sources**: [Application Gateway for Containers](https://learn.microsoft.com/en-us/azure/application-gateway/for-containers/overview),
  [Kubernetes Gateway API](https://gateway-api.sigs.k8s.io/). The AKS
  application-routing Gateway API implementation was also evaluated but is
  preview as of this plan and is not the production dependency.

## Decision 14: Use Azure-managed state and platform integrations

- **Decision**: Store images in ACR, secrets in Key Vault through Workload
  Identity/CSI, BFF sessions in Azure Managed Redis, core records in Azure
  Database for PostgreSQL Flexible Server, and telemetry in Azure Monitor and
  Application Insights. Prefer private endpoints and private DNS. Give UI, BFF,
  and core distinct service names and attach environment, service version, and
  image digest to safe telemetry. Record route-class rate/error/duration,
  readiness, dependency outcome, restart, replica, and HPA-saturation signals;
  use versioned `operational-alert-profile-v1`: alert on zero ready replicas for
  five minutes; 5xx at or above 5% with at least 20 requests in each of two
  five-minute windows; route p95 above 2 seconds for UI static, 30 seconds for
  roadmap, 10 seconds for guidance, or 5 seconds for other personalized API
  traffic across the same two-window/minimum-sample gate; three restarts in 10
  minutes; four HPA replicas at or above 70% average CPU for 15 minutes; an
  unacknowledged session-revocation outbox row at 2/6/12 hours; gateway/private-
  core certificate expiry at 30/14/7 days and critical below 48 hours; no
  successful directory reconciliation at 6/8 hours; or active-lab validation
  age at 30/36 hours, with immediate content-operations alert after three
  consecutive failures or an unavailable destination.
  Readiness/restart and second-window 5xx/latency breaches page Application
  Operations. HPA saturation warns Application and Platform Operations at 15
  minutes and pages both at 30; gateway, cluster, and managed-dependency causes
  also route to Platform Operations. Revocation backlog warns at 2 hours, pages
  at 6, and becomes a critical 12-hour deadline breach.
  Certificate alerts route to Platform Operations; reconciliation warnings/
  pages route to Application and Platform Operations; lab warnings route to
  Learning Content Operations and 36-hour pages also route to Application
  Operations.
  A bounded 12-hour AKS CronJob is the sole runtime allowed to assume the
  gateway-certificate/DNS identity and runs overlap/activation/reload/rollback
  from a digest-pinned runner. A separate bounded 20-hour CronJob assumes only
  the lab-validation identity and updates validation state; its NetworkPolicy
  excludes private/link-local/metadata/cluster destinations while the validator
  enforces the provider-domain/redirect allowlist.
- **Data-plane bootstrap**: An interactive Platform Operations identity, outside
  GitHub Actions, establishes the Managed Redis data-plane assignment and PostgreSQL
  Entra administrator plus separate core DML; lifecycle known-identity/status/
  reconciliation/outbox and unclaimed-retention-scheduling; retention audited
  security-definer claim/process-due procedure-only; lab-validation destination/
  status/counter-only; and migration DDL/backfill principals. Lifecycle may insert or narrowly update unclaimed scheduling
  fields but cannot read/delete/claim/complete queue rows. The retention
  procedures enforce eligibility, delete the identity and personalized owner
  graph, remove every link, and only then anonymize eligible security evidence,
  without granting direct queue or learning-row reads. The lab role cannot
  access profiles, learning sessions, or reviews. Bootstrap
  proves cross-role denial before access
  keys/password fallback are disabled. GitHub Actions may validate but cannot grant
  these roles.
- **Rationale**: Managed services remove backups, patching, failover, and
  storage scheduling from the application cluster. Workload Identity avoids
  long-lived Azure credentials. PostgreSQL also removes the single-writer
  limitation that would block later core scaling.
- **Alternatives considered**: In-cluster Redis and PostgreSQL are cheaper in
  raw compute but add stateful operations and failure coupling. SQLite on a PVC
  is acceptable only for local development, not the optimized Azure target.
  Azure Cache for Redis was rejected for new infrastructure because Microsoft
  has announced its retirement and recommends Azure Managed Redis.
  One undifferentiated telemetry component was rejected because it cannot prove
  which independently deployed service owns an injected failure.
- **Sources**: [Azure Managed Redis migration guidance](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-migration-guide),
  [AKS Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview),
  [Key Vault CSI identity access](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-identity-access)

## Decision 15: Optimize releases around immutable component changes

- **Decision**: Build and scan only changed service images, publish them to ACR,
  promote by digest, and deploy compatible changes in `core -> BFF -> UI`
  order. Use rolling updates with readiness gates, zero unavailable replicas
  where capacity permits, automated smoke/contract checks, runtime capability
  negotiation, accepted pre-mutation evidence, and mutation-journal rollback.
- **Rationale**: Component-aware builds reduce pipeline time and registry churn.
  Digest promotion proves the tested artifact is the deployed artifact, while
  additive contracts allow each service to release independently.
- **Alternatives considered**: Rebuilding all images for each change wastes
  time and couples releases. Mutable tags weaken provenance. A full service
  mesh/canary platform is unnecessary for the pilot and can be introduced when
  traffic and risk justify it.

## Decision 16: Use one Entra authority with distinct identities per trust hop

- **Decision**: Use two application registrations: a confidential BFF web
  client and a core protected API exposing a delegated scope. The browser gets
  only an opaque BFF cookie. The BFF obtains an employee-delegated core access
  token; the core validates allowed algorithm/signature, `iss`, `tid`, `aud`,
  `nbf`/`exp`, `azp`, `scp`, and `(tid, oid)`. For private capability and
  readiness reads that cannot depend on an employee session, the BFF uses the
  same confidential-client certificate to obtain an app-only token containing
  only `CareerAgent.Health.Read`. Separately, assign
  least-privilege Workload Identities to BFF, core, lifecycle reconciliation,
  and gateway, while the AKS kubelet identity pulls from ACR.
- The BFF authenticates its confidential-client code redemption with a rotating
  certificate stored in Key Vault and mounted by CSI; this credential is not
  reused for Azure resource access.
- **Rationale**: Microsoft Entra is the shared authority, but employee
  delegation, confidential-client authentication, Azure resource access, and
  image pulling have different audiences and privilege boundaries. Separate
  principals prevent one compromised service from inheriting another service's
  Azure permissions and keep reusable tokens out of the browser.
- **Alternatives considered**: A SPA app registration exposes OAuth tokens to
  browser code. One managed identity for all pods violates least privilege.
  Trusted identity headers do not give the core cryptographic authorization.
  Client credentials alone lose employee ownership context.
- **Sources**: [Configure app access to a web API](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-access-web-apis),
  [access-token validation](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens),
  [Azure Managed Redis Entra authentication](https://learn.microsoft.com/en-us/azure/redis/entra-for-authentication),
  [PostgreSQL Entra authentication](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-azure-ad-authentication)

## Decision 17: Separate delegated employee and app-only machine policies

- **Decision**: Expose dedicated core API application roles to approved machine
  registrations. Accept client-credentials tokens only on documented machine
  operations reached through an approved private route. Employee operations
  continue to require delegated scopes. BFF-specific compatibility headers are
  conditional on delegated BFF calls and are not part of machine request
  semantics. Machine roadmap creation uses application ownership keyed to the
  validated principal; machine progress may reference only that application's
  roadmap; guidance remains stateless apart from application-scoped
  idempotency/audit. No app-only call fabricates or selects an employee owner.
- **Rationale**: Automation remains independent of UI/BFF availability while
  the core can distinguish an application from an employee delegation and
  preserve stateful machine outcomes without weakening ownership. Private
  routing preserves the no-public-core requirement.
- **Alternatives considered**: Anonymous compatibility violates the security
  boundary. Employee tokens prevent unattended automation. Routing machines
  through BFF couples automation to browser concerns.

## Decision 18: Enforce idle and absolute BFF session deadlines in Redis

- **Decision**: Store immutable `created_at`/`absolute_expires_at` and rolling
  `last_seen_at`/`idle_expires_at`. Refresh idle expiry only on authenticated
  user activity and cap it at 30 idle minutes or 8 total hours.
- **Rationale**: The idle window covers a focused learning session while the
  absolute deadline prevents indefinite renewal. Redis makes expiry and
  revocation consistent across replicas.
- **Alternatives considered**: Browser-only or process-local expiry is not
  authoritative. Passive polling must not keep a session alive.

## Decision 19: Reconcile Entra lifecycle and enforce retention in core

- **Decision**: Run a four-hour core-image CronJob (stricter than the daily
  minimum) that checks known Entra object
  IDs for disabled/deleted status using a dedicated Workload Identity with
  administrator-consented, read-only Microsoft Graph `User.Read.All`. Mark
  departure, block personalized access, and enqueue both a durable revocation
  outbox row and an unclaimed retention action in one transaction before
  advancing the reconciliation checkpoint. Lifecycle can schedule but cannot
  read, claim, complete, or delete retention work; the separate retention
  identity processes due work only through audited security-definer procedures. A
  dispatcher running at least every five minutes sends the authenticated,
  idempotent command to a private BFF route protected by
  `LearningBff.Session.Revoke`, retries with at most a one-hour delay until
  acknowledgement, alerts at two hours, pages at six, and reaches a 12-hour
  post-recognition deadline so total disablement-to-revocation remains below 24
  hours; delete identity/profile/domain/idempotency and owner-linked outbox
  records by day 90. The successful retention transaction nulls the completed
  action's `ON DELETE SET NULL` owner FK only through identity deletion; the
  retained action contains no tenant/object/owner identifier or reversible
  hash. Security evidence may remain only after irreversible removal of every
  direct and indirect identity link; aggregate telemetry must be
  non-reidentifiable. Checkpoint reconciliation and retry throttling/transient
  failures without treating them as departure.
- **Rationale**: Sign-in checks stop returning users; reconciliation also catches
  employees who never return. The explicit control path revokes distributed
  Redis sessions without giving core direct Redis access. The transactional
  outbox prevents checkpoint/crash loss, and the dedicated identity confines
  Graph and revocation permission. Core owns data and retention transitions.
- **Alternatives considered**: Login-only checks miss dormant accounts. A new
  HR integration is outside scope. Inactivity is not proof of departure.
- **Source**: [Get user - Microsoft Graph](https://learn.microsoft.com/en-us/graph/api/user-get?view=graph-rest-1.0)

## Decision 20: Persist actor-scoped idempotency in core

- **Decision**: Require `Idempotency-Key` on retryable mutations. Persist a
  unique actor/operation/key record with canonical request hash, state, and
  established result. Invalid requests do not consume the key; identical valid
  replays return the result; changed payloads return `409
  IDEMPOTENCY_KEY_REUSED`. Retain complete response bodies for 30 days, then
  retain a non-reusable actor/operation/key/hash/status/resource tombstone while
  the actor remains eligible. A same-hash replay whose body cannot be
  reconstructed returns the sole approved expired-result response, `409
  IDEMPOTENCY_RESULT_EXPIRED`, without execution; `410`, generic conflict, and
  key reuse are prohibited. Purge the tombstone only with the owner graph.
- **Rationale**: UI controls and BFF deduplication cannot prevent replica races,
  timeouts after commit, or direct machine retries. Core is the only boundary
  able to guarantee one domain transition.
- **Alternatives considered**: Last-write-wins can overwrite progress.
  Reject-all breaks safe retries. Duplicate-and-reconcile corrupts scoring.

## Decision 21: Use GitHub Actions as a thin, repository-owned delivery orchestrator

- **Decision**: Put a Declarative `.github/workflows/delivery.yml` at repository root and keep
  change detection, validation, build/publish, promotion, deployment,
  verification, and rollback behavior in versioned repository scripts. GitHub Actions
  runs selected service validation in parallel with fail-fast behavior, then
  serializes protected-branch deployment in compatibility order.
- **Recovery and notification policy**: Manual rebuild/recovery requires a
  GitHub Actions Delivery Recovery Operator and a distinct Platform Operations
  approver. Automatic compensation uses at most three attempts with
  0/15/45-second delays and a 20-minute total deadline, stops at the first
  unverified reverse dependency, and quarantines as `rollback_failed` for
  two-person recovery. Pre-mutation application/platform/evidence failures route
  to their owning Application/Platform/Security teams; post-mutation and
  rollback failures page Application and Platform Operations with 15-minute
  acknowledgement and 30-minute incident escalation. Successful delivery is
  informational to Delivery and Application Operations.
- **Rationale**: GitHub Actions is the specified CI platform. A thin pipeline makes
  delivery reviewable with the source while keeping critical behavior locally
  testable. Declarative Pipeline supports parallel stages, fail-fast behavior,
  timeouts, and stage conditions; milestones and environment locking prevent a
  stale or concurrent build from overwriting a newer deployment.
- **Alternatives considered**: A provider-neutral runner does not satisfy the
  explicit GitHub Actions requirement. GitHub Actions and Azure Pipelines add an
  unrequested control plane. Rebuild-all wastes time and expands blast radius.
  Encoding all behavior directly in Groovy makes it harder to test and reuse.
- **Sources**: [GitHub Actions Pipeline syntax](https://www.github_actions.io/doc/book/pipeline/syntax/),
  [GitHub Actions tests and artifacts](https://www.github_actions.io/doc/pipeline/tour/tests-and-artifacts/),
  [GitHub Actions milestone step](https://www.github_actions.io/doc/pipeline/steps/pipeline-milestone-step/)

## Decision 22: Validate labs before publication and periodically afterward

- **Decision**: Require HTTPS, complete metadata, an approved provider domain,
  safe redirects, a bounded successful reachability check, and a recorded
  verification time before a lab becomes active. Revalidate active links on a
  schedule and move repeatedly failing links to unavailable state.
- **Rationale**: Displaying metadata alone cannot satisfy the publication-time
  reachability outcome or protect users from redirected unapproved destinations.
- **Alternatives considered**: Browser-only checks are inconsistent and expose
  users first. Manual-only checks do not detect links that later fail.

## Decision 23: Use existing retired controller Azure cloud ACI agents

- **Decision**: The retired CI controller remains at `http://localhost:8080` and
  uses its existing retired controller Azure cloud node named `azure` to provision and connect
  ephemeral ACI agents in the configured resource group. Separate publisher
  and deployer templates (`azure-aci-publisher` and `azure-aci-deployer`) use
  distinct ACR- and AKS-scoped user-assigned managed identities. A
  build emits immutable change and release manifests, deploys only ACR digests,
  snapshots existing service digests, and promotes changed services in
  `core -> BFF -> UI` order without rebuilding.
- **Controller and ACR loss handling**: The trusted controller plugin fsyncs
  every accepted-attempt transition to the normal run record and a host-managed
  append-only replicated audit volume before ACI allocation. Protected
  scheduling stops when either copy is unhealthy. Platform Operations performs
  hourly integrity checks and encrypted backup. The replica supplies RPO 0
  after an accepted transition and RTO at most four hours for controller-disk-
  loss recovery. Recovery restores the replica and reconciles build IDs against
  queue/run metadata, webhook audit, and Azure evidence. An accepted nonterminal
  orphan becomes `aborted_recovered`; protected delivery stays blocked until
  every post-mutation orphan has verified rollback or approved recovery in a
  verified terminal state. A digest published but not promoted is marked
  `published_unpromoted`, quarantined from release aliases, and cannot be used by
  another build without a new release manifest and fresh gates. Unreferenced
  unpromoted content becomes GC-eligible after 30 days while build ID, revision,
  scan, SBOM, release-manifest digest, and disposition evidence remain for 90
  days. Promoted or held digests are excluded from GC.
- **Validation template**: Every ref runs checkout, change planning,
  contract/catalog drift, lint, typecheck, unit, contract, and non-Azure
  integration validation on `azure-aci-validator`. The template has neither a
  system-assigned nor a user-assigned managed identity and its stages cannot
  invoke Azure login, ACR publication, evidence upload, database migration, or
  AKS operations. Pull requests and unprotected refs stop on this template.
  Reusing a publisher identity for validation was rejected because untrusted
  source would inherit delivery permission.
- **Rationale**: This uses the existing, user-confirmed cloud-agent connection
  instead of inventing a new controller endpoint or network path. Distinct ACI
  identities keep application-delivery permission out of the controller-held
  provisioning credential and preserve least privilege.
- **Provisioning credential boundary**: Cloud `azure` already authenticates
  with a service principal stored in the controller. Retain it only for ACI
  lifecycle and identity attachment; explicitly deny ACR push and AKS deploy.
  Application delivery authorization remains on the two ACI managed identities.
  Platform Operations owns this credential, rotates it at least every 90 days,
  and receives expiry alerts at 30, 14, and 7 days. Missing/unreadable expiry or
  fewer than 30 valid days quarantines Azure agent provisioning for protected
  deployments. Developer-local validation remains possible, but GitHub Actions never
  falls back to its controller or a local agent; all-ref GitHub Actions validation
  resumes only on the identityless ACI validator. Validate that the identityless
  validator plus publisher and deployer ACI templates can provision and connect
  with their declared identity boundaries before revoking the prior credential;
  revoke immediately after suspected
  compromise. Update the stable GitHub Actions credential ID only through the
  authenticated localhost API with CSRF protection using a dedicated GitHub Actions
  credential-manager identity. That identity may update only the stable cloud
  credential and cannot configure jobs, run builds, or read other credentials.
  Accept replacement secret material only through protected standard input or
  an inherited file descriptor with redacted logs and guaranteed cleanup.
  Quarantine clears only after all three replacement-template checks pass.
- **External infrastructure bootstrap**: Platform Operations, not GitHub Actions, uses
  an interactive Entra identity to initialize locked Azure Storage remote state
  and apply/import reviewed Terraform with pinned AzureRM/AzureAD providers and
  a committed provider lock file. `bootstrap-ui-platform.sh` applies/imports all
  reviewed Terraform, including evidence-lifecycle and monitoring resources;
  `bootstrap-data-principals.sh` creates and denial-tests the scoped data roles.
  Platform Operations installs the pinned ALB Controller and the cluster-admin-
  owned migration namespace/RBAC/admission guardrails. Neither bootstrap script
  emits the environment manifest. After all modules and delivery identities are
  applied, data principals are verified, and the controller and guardrails are
  live, `finalize-ui-platform.sh` alone emits a schema-validated,
  non-secret reviewed manifest containing state lineage/serial, repository
  configuration digest, resource/identity IDs, origins, controller/migration-
  policy attestations, and seven-day
  provider/quota/capacity attestations. GitHub Actions has no Terraform apply/import or
  state-read permission and blocks protected delivery when the manifest is
  missing, expired, stale, or inconsistent with live resources.
  Bootstrap privileges are PIM-activated and scoped by action: state-container
  `Storage Blob Data Contributor`, application-RG `Contributor` and `Role Based
  Access Control Administrator`, named shared Network/Private-DNS roles, a
  provider-registration/quota-read custom subscription role, JIT `Application
  Administrator`, and a separate JIT `Privileged Role Administrator` approver
  for the Microsoft Graph `User.Read.All` application consent. `Owner`, `Global
  Administrator`, standing privilege, unrelated app/data access, and GitHub Actions
  principals are denied. This split reflects that Azure Contributor cannot
  assign roles and that Application/Cloud Application Administrator consent
  excludes Microsoft Graph application permissions.
  The repository digest is defined by
  `config/platform-configuration-digest-v1.yaml`, which includes itself and
  canonicalizes allowlisted platform file path/mode/length/content in bytewise
  order. It excludes the emitted environment manifest plus local secrets,
  Terraform state/plan/cache, runtime evidence/logs, and VCS metadata, so it is
  non-self-referential and changes for matching add/remove/rename/mode/content
  drift.
- **Template identity binding**: Bind the Terraform output for the publisher
  identity only to `azure-aci-publisher`, and the deployer identity only to
  `azure-aci-deployer`. The deployer additionally receives control-plane
  `Reader` on only the target/configured resource group for live manifest and
  preflight checks, with no Terraform-state, Key Vault-secret, ACR-content,
  Redis-data, or PostgreSQL-data read. Post-bootstrap delivery-identity validation rejects
  missing, additional, swapped, or system-assigned identities by comparing the
  live GitHub Actions template and running ACI resource IDs with the reviewed manifest;
  it also proves that the validator is identityless.
- **Two-phase readiness**: The identityless validator checks manifest schema and
  repository digest. On protected refs the deployer performs target-resource-
  group-only live checks for AKS version/capacity/networking/OIDC, ALB Controller,
  ACR reachability, private DNS, data-plane principals, and legacy-ingress
  absence; subscription provider/quota checks use the unexpired external
  attestation rather than a GitHub Actions subscription-wide grant. Then run a separate
  delivery-identity validation for kubelet pull, publisher push,
  deployer AKS access, controller denial, cross-identity denial, and exact
  tenant/subscription/resource-group scope.
- **Evidence authority**: Store delivery manifests and verification evidence in
  a dedicated, access-restricted Azure Storage container. The normal retention
  period is a fixed locked 90-day version-level time policy. An incident hold
  sets the Azure version-level legal-hold boolean on every enumerated evidence-
  set blob version and may protect the set only through an expiry no later than
  180 days from creation; separate audit metadata includes hold ID, owner,
  reason, incident reference, start, target versions, and expiry. Partial set or
  clear enters retrying reconciliation and cannot be reported active/released.
  Release clears every version hold but cannot shorten the base lock, so deletion waits until both the
  90-day `immutable_until` has elapsed and no legal hold remains. Both delivery identities have custom writer roles with
  Azure ABAC conditions restricting their environment/stage prefixes; uploads
  use atomic create-if-absent semantics. Required-artifact and prohibited-content
  validation must pass, accepted pre-mutation evidence must exist, and the blob
  version receives a locked time-based immutability policy before promotion.
  Configured Delivery Operators and Security Reviewers Microsoft Entra groups
  hold read access. A separately configured Evidence Hold Managers Microsoft
  Entra group is the sole authority for creating, extending, and releasing hold
  requests and mutating their audited control metadata; it has no direct Azure
  blob-version hold permission. A separate reconciler identity is the sole data-
  plane principal that may apply or clear the exact enumerated version legal
  holds authorized by that metadata. Neither principal can read delivery
  evidence, create artifacts, change base retention, or delete blobs. GitHub Actions
  controller archives are
  convenience copies, not the system of record. A globally trusted,
  administrator-installed controller plugin built from a pinned protected
  revision and verified digest uses `RunListener` to create a controller
  `RunAction` with `pending` state before `node`, agent allocation, checkout, or
  workspace creation. It runs independently of repository .github/workflows/delivery.yml/shared-
  library calls, so omission or symbol shadowing cannot bypass creation; it owns
  monotonic updates, restart recovery, retention, and exactly-once finalization.
  Repository shell code may request allowed updates/synchronization but cannot
  create, replace, suppress, or finalize this state. The record is authoritative for controller
  lifecycle state and explicitly non-authoritative as delivery evidence. The
  audit uses append-only
  `started -> agent_requested -> agent_connected -> evidence_active` events and
  exactly one `succeeded | failed | aborted` terminal state. Every exit path
  records timestamps and failed stage. Authoritative evidence is
  required only after an authenticated delivery agent is available. Evidence
  must not contain tokens, kubeconfigs, secrets, or personal learner data.
  Digest pinning prevents a mutable tag from changing the deployed artifact;
  signed/fingerprinted evidence makes the source-to-environment transition
  auditable. Per-service snapshots support attempt-wide rollback of every
  service mutated by the accepted attempt while leaving untouched services
  unchanged.
- **Alternatives considered**: A dedicated Azure VM agent duplicates the
  existing ACI capability. Publishing the localhost controller as an OIDC
  issuer is insecure. Reusing the provisioning service principal for delivery
  would mix infrastructure and application privileges.
  Mutable tags cannot prove which bytes were deployed. A synchronized
  three-service release train unnecessarily redeploys unaffected services.
- **Sources**: [Azure managed identities](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview),
  [ACR image tagging and versioning](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-image-tag-version),
  [Azure built-in roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles),
  [Entra application-management roles](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/delegate-app-roles),
  [Entra built-in role consent limits](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference),
  [Terraform state in Azure Storage](https://learn.microsoft.com/en-us/azure/developer/terraform/store-state-in-azure-storage)

## Decision 24: Make readiness and requirements traceability release authorities

- **Decision**: Treat
  [implementation-readiness-contract.md](./contracts/implementation-readiness-contract.md)
  as the normative authority for outcome states, stable codes, numeric bounds,
  owners, evidence, SLO measurement, and prerequisite failure behavior. Treat
  [requirements-traceability.md](./requirements-traceability.md) as the
  exhaustive FR/SC-to-task/test/evidence ledger. A missing, empty, duplicate,
  out-of-order, or unknown-task row blocks implementation and release.
- **Pilot SLO decision**: The pilot has no production SLA and is measured only
  on Israel business days from 08:00-18:00:

  | Concern | Exact decision |
  |---|---|
  | Browser journey | 99.0% per calendar month. Run one observation per eligible minute; it succeeds only when public TLS Gateway, UI/runtime-config, and `/bff/v1/capabilities` readiness/contract checks all pass. Availability is successful eligible observations divided by all eligible observations. Maintenance is excluded only with at least 24-hour notice and is capped at four hours/month; unannounced and above-cap minutes remain in the denominator. |
  | Stateless UI/BFF/core | RPO 0 for Git, immutable ACR digest, and reviewed configuration; RTO at most 60 minutes. |
  | PostgreSQL | RPO at most five minutes; RTO at most four hours; continuous backup/PITR retention is seven days, and restored access waits for retention catch-up plus owner/access checks. |
  | Redis sessions | Durable-session RPO is intentionally excluded; RTO at most 60 minutes. Session loss may require sign-in but cannot lose core learning data, and restored state requires key/version validation. |
  | Delivery evidence | RPO 0 after immutable-version acceptance; access RTO at most four hours, with delivery blocked until recovery/completeness. |
  | retired CI controller audit | RPO 0 after a two-copy fsync; RTO at most four hours for replica restore and queue/run, webhook, and Azure-evidence reconciliation. Protected delivery stays blocked until accepted orphans are terminal and post-mutation orphans have verified rollback or approved recovery. |
  | Telemetry and labs | Telemetry may lose at most five minutes or 1,000 safe envelopes per process. Labs claim no provider RTO/RPO; scheduled validation runs every 20 hours and never exceeds 24 hours, while a report triggers validation within 15 minutes. |
  | Regional DR | Cross-region Entra/Azure managed-service failover and provider SLA commitments are excluded; dependency behavior still fails closed. |

  Monthly evidence contains scheduled/excluded minutes and notice, eligible/
  successful/failed one-minute observations, achieved availability, incidents,
  exercised RTO/RPO, PostgreSQL restore results, replicated controller-audit
  restore/reconciliation results, and owner approval. RTO runs from the first
  failed eligible observation or declared outage, whichever is earlier, to the
  first complete successful functional recovery check. RPO compares restored
  state with the last accepted authoritative domain transaction, deployment
  digest/configuration, controller transition, or immutable evidence version.
- **Prerequisite decision**: Planning-time existence is never evidence. The
  linked readiness contract defines each required evidence payload; the exact
  freshness and accountable-owner register is:

  | Prerequisite | Owner | Exact freshness/gate |
  |---|---|---|
  | Entra tenant/apps/scopes/roles/consent/groups/issuer | Identity/Security Operations | Validate within 24 hours before pilot and after every identity/config change. |
  | Approved machine clients/private networks | Security Reviewers and Platform Operations | Manifest attestation at most seven days old plus live DNS/TLS/denial probe on verification day. |
  | External bootstrap and final reviewed manifest | Platform Operations | Plan/state/assignment/controller/migration/provider/quota/capacity evidence at most seven days old; compare live target-RG resources on every protected build. |
  | AKS/ACR and platform controls | Platform Operations | Live capacity/OIDC/Workload-Identity/ALB/PDB/HPA/topology/private-DNS/migration/legacy-ingress preflight within 15 minutes of promotion. |
  | retired CI controller/cloud `azure` | Platform Operations | Check daily and on every protected build; provisioning principal must retain at least 30 valid days. |
  | ACI validator/publisher/deployer | Platform Operations | Smoke after credential/template change and within 24 hours before protected release. |
  | Redis/PostgreSQL/Key Vault/CSI/Gateway/Monitor/evidence | Platform Operations with Application Operations | Live identity/denial/readiness/version/immutable-write/exporter checks within 15 minutes of pilot opening and protected release. |
  | Lab providers/references | Learning Content Operations and Security Reviewers | Dual approvals and complete validation at most 24 hours old. |
  | Pilot population | Product/UX Research | Freeze roster/allocation/consent/script/facilitator evidence within seven days of the first participant. |
  | Browsers/assistive technology | Product/UX Research and Application Operations | Capture exact versions and matrix smoke on verification day; release evidence must be at most 30 days old. |

  A stale or failed row has the precise blocking effect in the readiness
  contract: it blocks the affected identity, consumer, publication, promotion,
  pilot opening, measured study, or UI release; there is no fallback credential,
  tenant, agent, service, or inferred assumption.
- **Rationale**: A single normative behavior contract plus an exhaustive ledger
  turns readiness from prose into reviewable implementation, test, evidence,
  and release gates. Exact denominators and freshness windows prevent teams from
  reporting success against different populations or stale prerequisites.
- **Alternatives considered**: Scattered best-effort guidance was rejected
  because values and stable codes drift. A production-grade regional SLA was
  rejected because this feature is a small non-production pilot. Treating
  planning assumptions as preflight evidence was rejected because external
  identity, capacity, controller, provider, and browser state can change.
