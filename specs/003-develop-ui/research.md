# Research: Three-Service DevOps Career Agent UI

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
  old/new combinations.

## Decision 8: Retain normalized core learning persistence

- **Decision**: Normalize identity ownership, employee-session progress,
  reviews, answers, milestones, and lab reports in the core database. Keep
  versioned authored content as structured snapshots. Use Alembic for deployed
  schema evolution. Put the employee-owned roadmap identity, stable milestone
  key, and ownership constraints in the Foundation migration chain. Give US3 a
  deterministic owned-roadmap plus published-content fixture and US4 a
  deterministic owned-roadmap fixture; neither story migration depends on US1.
- **Rationale**: Atomic scoring/completion, idempotent resume, ownership, and
  audit history require constraints and transactions. Foundation ownership
  removes the hidden `006 -> 007 -> 008` story dependency and keeps the four
  slices independently testable. Only the core may access these records.
- **Alternatives considered**: JSON-only records weaken concurrency and query
  guarantees. BFF storage of learning state violates domain ownership. Seeding
  a fixture into a schema created by US1 would still make US3/US4 depend on US1.

## Decision 9: Use Redis only for BFF session state

- **Decision**: Store opaque session records, auth state/nonce, CSRF secret,
  expiry, and encrypted MSAL cache material in a BFF-owned Redis dependency.
  UI and core do not access it.
- **Rationale**: BFF replicas and restarts need shared revocable state. Redis is
  purpose-fit for expiring sessions and does not couple browser auth state to
  core persistence.
- **Alternatives considered**: Process memory is not restart/scale safe.
  Browser storage exposes tokens. Core database storage couples lifecycles.

## Decision 10: Use path routing, NetworkPolicy, and independent health

- **Decision**: Deploy UI, BFF, and core as separate ClusterIP Services.
  Gateway/Ingress reaches UI and BFF; BFF alone reaches core by private service
  DNS. NetworkPolicy denies UI-to-core. Each service exposes process-local
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
  reverse a destructive database migration; an irreversible mutation requires
  an operator-approved recovery plan before promotion.
- **Rationale**: This meets independent release/rollback requirements while
  preventing incompatible writes and keeping database migrations safe. A
  reverse journal restores all mutations made by the failed rollout rather than
  assuming that restoring one image digest also restores configuration or
  routing state.
- **Alternatives considered**: A combined image or synchronized release train
  violates independent operation. Blind database rollback risks data loss.
  A snapshot without compensating operations cannot safely unwind a partial
  multi-step rollout.

## Decision 12: Test boundaries and journeys separately

- **Decision**: UI uses typecheck, lint, Vitest, Playwright, and accessibility
  checks. BFF tests auth/session/CSRF, error mapping, core-client contracts, and
  replica-safe sessions. Core tests token claims, owner isolation, migrations,
  lifecycle, scoring, and provider contracts. Deployment tests routing,
  NetworkPolicy, trace continuity, outage isolation, and independent rollback.
  Browser timing marks measure local-validation event-to-guidance time and
  `responseEnd`-to-accessible-result-ready time. Normal certificate rotation
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

- **Decision**: Deploy UI, BFF, and core as independent AKS Deployments and
  ClusterIP Services in a shared application namespace. Use the AKS
  Application Gateway for Containers with Gateway API for the UI and BFF
  public paths; do not create a public route for core.
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
  alert on five-minute readiness loss, sustained 5xx/latency breach, restart
  loops, and sustained maximum-replica saturation.
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
  `nbf`/`exp`, `azp`, `scp`, and `(tid, oid)`. Separately, assign
  least-privilege Workload Identities to BFF,
  core, and gateway, while the AKS kubelet identity pulls from ACR.
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
  continue to require delegated scopes.
- **Rationale**: Automation remains independent of UI/BFF availability while
  the core can distinguish an application from an employee delegation. Private
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

- **Decision**: Run a daily core-image CronJob that checks known Entra object
  IDs for disabled/deleted status. Mark departure, revoke BFF sessions, block
  personalized access, and delete identity/profile/domain/idempotency records
  by day 90. Security evidence may remain only after irreversible removal of
  direct and indirect identity; aggregate telemetry must be non-reidentifiable.
  Checkpoint reconciliation and retry throttling/transient failures without
  treating them as departure.
- **Rationale**: Sign-in checks stop returning users; reconciliation also catches
  employees who never return. Core owns data and retention transitions.
- **Alternatives considered**: Login-only checks miss dormant accounts. A new
  HR integration is outside scope. Inactivity is not proof of departure.

## Decision 20: Persist actor-scoped idempotency in core

- **Decision**: Require `Idempotency-Key` on retryable mutations. Persist a
  unique actor/operation/key record with canonical request hash, state, and
  established result. Invalid requests do not consume the key; identical valid
  replays return the result; changed payloads return `409`. Retain the compact
  record while replay could repeat a transition and purge it with the owner.
- **Rationale**: UI controls and BFF deduplication cannot prevent replica races,
  timeouts after commit, or direct machine retries. Core is the only boundary
  able to guarantee one domain transition.
- **Alternatives considered**: Last-write-wins can overwrite progress.
  Reject-all breaks safe retries. Duplicate-and-reconcile corrupts scoring.

## Decision 21: Use Jenkins as a thin, repository-owned delivery orchestrator

- **Decision**: Put a Declarative `Jenkinsfile` at repository root and keep
  change detection, validation, build/publish, promotion, deployment,
  verification, and rollback behavior in versioned repository scripts. Jenkins
  runs selected service validation in parallel with fail-fast behavior, then
  serializes protected-branch deployment in compatibility order.
- **Rationale**: Jenkins is the specified CI platform. A thin pipeline makes
  delivery reviewable with the source while keeping critical behavior locally
  testable. Declarative Pipeline supports parallel stages, fail-fast behavior,
  timeouts, and stage conditions; milestones and environment locking prevent a
  stale or concurrent build from overwriting a newer deployment.
- **Alternatives considered**: A provider-neutral runner does not satisfy the
  explicit Jenkins requirement. GitHub Actions and Azure Pipelines add an
  unrequested control plane. Rebuild-all wastes time and expands blast radius.
  Encoding all behavior directly in Groovy makes it harder to test and reuse.
- **Sources**: [Jenkins Pipeline syntax](https://www.jenkins.io/doc/book/pipeline/syntax/),
  [Jenkins tests and artifacts](https://www.jenkins.io/doc/pipeline/tour/tests-and-artifacts/),
  [Jenkins milestone step](https://www.jenkins.io/doc/pipeline/steps/pipeline-milestone-step/)

## Decision 22: Validate labs before publication and periodically afterward

- **Decision**: Require HTTPS, complete metadata, an approved provider domain,
  safe redirects, a bounded successful reachability check, and a recorded
  verification time before a lab becomes active. Revalidate active links on a
  schedule and move repeatedly failing links to unavailable state.
- **Rationale**: Displaying metadata alone cannot satisfy the publication-time
  reachability outcome or protect users from redirected unapproved destinations.
- **Alternatives considered**: Browser-only checks are inconsistent and expose
  users first. Manual-only checks do not detect links that later fail.

## Decision 23: Use existing Jenkins Azure cloud ACI agents

- **Decision**: The Jenkins controller remains at `http://localhost:8080` and
  uses its existing Jenkins Azure cloud node named `azure` to provision and connect
  ephemeral ACI agents in the configured resource group. Separate publisher
  and deployer templates (`azure-aci-publisher` and `azure-aci-deployer`) use
  distinct ACR- and AKS-scoped user-assigned managed identities. A
  build emits immutable change and release manifests, deploys only ACR digests,
  snapshots existing service digests, and promotes changed services in
  `core -> BFF -> UI` order without rebuilding.
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
  deployments while retaining local validation. Validate that both ACI
  templates can provision and connect with their intended managed identities
  before revoking the prior credential; revoke immediately after suspected
  compromise. Update the stable Jenkins credential ID only through the
  authenticated localhost API with CSRF protection using a dedicated Jenkins
  credential-manager identity. That identity may update only the stable cloud
  credential and cannot configure jobs, run builds, or read other credentials.
  Accept replacement secret material only through protected standard input or
  an inherited file descriptor with redacted logs and guaranteed cleanup.
  Quarantine clears only after both replacement templates pass.
- **Template identity binding**: Bind the Terraform output for the publisher
  identity only to `azure-aci-publisher`, and the deployer identity only to
  `azure-aci-deployer`. Preflight rejects missing, additional, swapped, or
  system-assigned identities by comparing the live Jenkins template and running
  ACI resource IDs with the Terraform outputs.
- **Evidence authority**: Store delivery manifests and verification evidence in
  a dedicated, access-restricted Azure Storage container. The normal retention
  period is 90 days; an incident hold may extend an identified evidence set to
  no more than 180 days and must include owner, reason, incident reference,
  start, and expiry. Both delivery identities have custom writer roles with
  Azure ABAC conditions restricting their environment/stage prefixes; uploads
  use atomic create-if-absent semantics. Required-artifact and prohibited-content
  validation must pass, accepted pre-mutation evidence must exist, and the blob
  version receives a locked time-based immutability policy before promotion.
  Configured Delivery Operators and Security Reviewers Microsoft Entra groups
  hold read access. A separately configured Evidence Hold Managers Microsoft
  Entra group receives a custom role that may mutate only incident-hold
  metadata; it cannot read delivery evidence, create artifacts, change base
  retention, or delete blobs. Jenkins controller archives are
  convenience copies, not the system of record. A minimal controller audit uses
  append-only `started -> agent_requested -> agent_connected -> evidence_active`
  events and exactly one `succeeded | failed | aborted` terminal state. Every
  exit path records timestamps and failed stage. Authoritative evidence is
  required only after an authenticated delivery agent is available. Evidence
  must not contain tokens, kubeconfigs, secrets, or personal learner data.
  Digest pinning prevents a mutable tag from changing the deployed artifact;
  signed/fingerprinted evidence makes the source-to-environment transition
  auditable. Per-service snapshots support the required scoped rollback.
- **Alternatives considered**: A dedicated Azure VM agent duplicates the
  existing ACI capability. Publishing the localhost controller as an OIDC
  issuer is insecure. Reusing the provisioning service principal for delivery
  would mix infrastructure and application privileges.
  Mutable tags cannot prove which bytes were deployed. A synchronized
  three-service release train unnecessarily redeploys unaffected services.
- **Sources**: [Azure managed identities](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview),
  [ACR image tagging and versioning](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-image-tag-version)
