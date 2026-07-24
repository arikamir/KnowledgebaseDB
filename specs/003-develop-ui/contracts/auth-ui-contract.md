# UI, BFF, and Core Authentication Contract

## Public routing

- `/` and UI assets route to the separate UI Service.
- `/bff/*` routes to the separate BFF Service on the same TLS origin.
- Core `/api/v1` remains private. Machine consumers use an approved private
  route with their own app-role authentication policy.

## BFF browser-auth routes

### `GET /bff/v1/auth/login?return_to=<relative-path>`

- Starts single-tenant Entra authorization-code sign-in.
- Parses and canonicalizes the return target, requires its resolved origin to
  equal the configured UI origin, and accepts only a single-slash relative path.
  It rejects absolute/network-path references, raw or percent-encoded slash and
  backslash tricks, control characters, and fragments before storing auth state.
- Stores state, nonce, PKCE verifier, and return path in short-lived Redis state.
- Returns `302` with a `Location` header for the tenant-specific Microsoft
  authorization endpoint; no cookie or secret is included in evidence.

### `GET /bff/v1/auth/callback?code=<code>&state=<state>`

- Validates state/nonce and redeems code with MSAL Node.
- Requests the delegated core API scope and keeps the redeemed token cache
  transient until the lifecycle gate succeeds.
- Before activating a browser session, calls
  `POST /api/v1/identity/session-bootstrap` with a delegated core token. Core
  derives the employee from validated `(tid, oid)` claims and applies the
  authoritative lifecycle gate. Only `active` permits session activation;
  `disabled` or `deleted` returns safe access-denied feedback, and an
  indeterminate directory/lifecycle result fails closed with retryable
  sign-in-unavailable feedback.
- Session bootstrap is semantically idempotent by validated `(tid, oid)`: a
  repeat returns the same current eligibility/status and cannot create a
  duplicate employee or domain record, so it does not accept a domain
  `Idempotency-Key`.
- Completes the lifecycle gate before issuing the opaque cookie. A denied or
  indeterminate bootstrap leaves no active BFF session, server-side session
  record, persisted MSAL cache, or reusable browser credential.
- On an active result, stores the encrypted token cache in Redis and rotates to
  a new opaque BFF session.
- Returns `303` with the validated relative UI `Location` and a `Set-Cookie`
  header carrying the rotated opaque `__Host-learning_session` attributes. Tests
  and logs record attributes only, never the value.

### `POST /bff/v1/auth/logout`

- Always requires an exact allowed Origin. When the session is active, it also
  requires the matching session-bound CSRF token, revokes the local session
  first, returns an expiring `Set-Cookie` that clears the host-only cookie, then
  uses a validated `Location` for Entra logout. It never echoes the prior cookie
  value.
- A retry with a missing, expired, unknown, or already-revoked session cannot
  regain authority: after the Origin check it still returns the same
  cookie-clearing redirect, even when the first successful response was lost.
  No session-bound CSRF comparison is possible or required on this
  invalid-session cleanup branch, and the branch performs no domain mutation.
- It is intrinsically idempotent and does not require a domain idempotency key:
  a repeat converges on no active local session and a cleared cookie.

### `GET /bff/v1/session`

```json
{
  "authenticated": true,
  "user": {"displayName": "Employee Name"},
  "csrfToken": "session-bound-token",
  "idleExpiresAt": "2026-07-11T12:00:00Z",
  "absoluteExpiresAt": "2026-07-11T19:30:00Z"
}
```

No Entra/core token, raw claim, tenant/object ID, or secret is returned.

Session lookup has deterministic unauthenticated outcomes:

- a request with no session cookie returns `200` with
  `{"authenticated": false, "reason": "missing"}`;
- an unknown, expired, or revoked cookie atomically revokes any remaining
  server-side index, clears the cookie, and returns `401
  application/problem+json` with stable code `SESSION_NOT_ACTIVE` and no user
  fields;
- an indeterminate Redis or token-cache dependency returns retryable `503`
  without claiming that the employee is signed out or deleting saved core
  records.

## Cookie and CSRF

- Cookie: `__Host-learning_session`, random opaque value, `Secure`, `HttpOnly`,
  `SameSite=Lax`, `Path=/`, no `Domain`.
- Redis stores only a hash/index plus encrypted token-cache material.
- Rotate on callback and authorization-state change; revoke at logout/expiry.
- Expire after 30 minutes without authenticated user activity and no later than
  8 hours after sign-in; background polling does not extend idle expiry.
- Mutations require synchronizer token in `X-CSRF-Token` and exact Origin check.
- UI never stores tokens in localStorage, sessionStorage, IndexedDB, or bundle.

## BFF-to-core authorization

- For personalized operations, BFF acquires a delegated access token whose
  audience is the core API.
- Core validates signature/JWKS, issuer, tenant, audience, time claims,
  authorized BFF client, and required delegated scope.
- Core derives owner from validated `(tid, oid)`.
- Core rejects ID tokens, tokens for another audience, spoofed identity headers,
  expired tokens, missing scope, and unauthorized clients.
- For private `GET /api/v1/capabilities` and readiness compatibility checks,
  BFF uses its certificate to acquire an app-only core token containing only
  `CareerAgent.Health.Read`. Core rejects that token on every personalized or
  state-changing operation.

Core accepts only configured signing algorithms, validates `nbf` and `exp` with
bounded clock skew, and refreshes tenant JWKS without accepting an untrusted
key source. For v2 access tokens, the authorized BFF client is matched through `azp`; the
delegated permission is matched through `scp`; employee ownership uses the
tenant-stable `(tid, oid)` pair. Human-readable claims such as name, email, or
UPN are presentation values and never authorization keys.

The first-release delegated-token profile is exact and case-sensitive:

| Check | Required delegated employee-token value | Failure behavior |
|---|---|---|
| Signature and algorithm | JWS signature validates against the bounded-fresh tenant JWKS; `alg` is exactly `RS256` and is not taken from an untrusted key source | `401 DELEGATED_TOKEN_INVALID`; never try another tenant, symmetric key, or `alg=none` |
| Issuer and tenant | `tid` equals the configured tenant and `iss` equals that tenant's configured version-specific issuer | `401 DELEGATED_TOKEN_INVALID`; common/consumer/another-tenant issuers are rejected |
| Audience | `aud` equals the configured core API audience | `401 DELEGATED_TOKEN_INVALID` |
| Lifetime | `nbf` and `exp` are present and valid with configured skew capped at five minutes | `401 DELEGATED_TOKEN_INVALID` |
| Authorized client | v2 `azp`, or v1 `appid`, equals the configured BFF client; a missing, ambiguous, or mismatched client claim is rejected | `401 DELEGATED_TOKEN_INVALID` |
| Delegated grant | `scp` contains the exact configured employee scope; `roles` cannot substitute for it | `403 DELEGATED_SCOPE_REQUIRED` |
| Employee subject and ownership | nonempty `tid` and `oid` identify the employee; request fields, `sub`, names, email, UPN, and forwarded identity headers never override `(tid, oid)` | `401 DELEGATED_TOKEN_INVALID` for a missing employee subject; `403 OWNER_MISMATCH` for a foreign owner/reference |
| Wrong token type | the employee route receives a delegated token with `scp`; an app-only token is accepted only by an explicitly listed machine or BFF-health route | `401 WRONG_TOKEN_TYPE` before idempotency or domain work |

JWKS availability has a bounded fail-closed rule. A validator may continue using
a successfully verified tenant key only while the cached JWKS is no more than
24 hours old. An unknown `kid` forces one tenant-specific refresh before token
rejection. If a successful refresh still lacks that key, the token returns
`401 *_TOKEN_INVALID`; if metadata cannot be refreshed and no bounded-fresh
cached key can validate the token, the affected replica returns retryable
`503 AUTH_KEY_METADATA_UNAVAILABLE`, becomes unready, and performs no
idempotency claim, session activation, authorization decision, or domain
mutation. A stale key set, another tenant's metadata, discovery data obtained
over an untrusted channel, or a caller-selected JWKS URI is never accepted.

## Machine-consumer authorization

- Machine consumers obtain client-credentials access tokens for the core API.
- Core requires the operation's application role in `roles`, validates the
  approved client and standard token claims, and rejects `scp` as a substitute.
- Employee-personalized routes reject app-only tokens unless an explicit
  machine contract defines how ownership is authorized.
- Machine traffic uses a governed private core route; core gains no public
  browser route.

The app-only machine-token profile is evaluated independently on every request:

| Check | Required app-only machine-token value | Explicit deny/result |
|---|---|---|
| Signature, key, and algorithm | JWS signature validates against the bounded-fresh configured-tenant JWKS; `kid` resolves under the refresh rule above; `alg` is exactly `RS256` | Missing/invalid signature, unknown key after successful refresh, another key source, another algorithm, a symmetric algorithm, or `alg=none` returns `401 MACHINE_TOKEN_INVALID` |
| Issuer and tenant | `tid` equals the configured organizational tenant and `iss` is that tenant's configured version-specific issuer | Missing/mismatched `tid`, common/consumer issuer, or issuer/tenant mismatch returns `401 MACHINE_TOKEN_INVALID` |
| Audience | `aud` equals the configured core API audience exactly | Missing, multiple, alias, BFF, Graph, or another API audience returns `401 MACHINE_TOKEN_INVALID` |
| Lifetime | `nbf` and `exp` are present and valid with configured clock skew capped at five minutes | Not-yet-valid or expired tokens return `401 MACHINE_TOKEN_INVALID`; refresh tokens and ID tokens are never accepted |
| Client application | v2 `azp`, or v1 `appid`, is present, singular, maps to an active approved `MachinePrincipal`, and matches the private-route allowlist | Missing/ambiguous client claim, inactive/unapproved client, BFF client, lifecycle client, or another application's client returns `401 MACHINE_TOKEN_INVALID` |
| Application role | `roles` is an array containing the exact case-sensitive operation role from the table below, and every asserted role is assigned to that approved client | A valid token missing the route role, asserting an unknown/unassigned role, or attempting to use one route's role on another route returns `403 MACHINE_ROLE_REQUIRED` |
| Wrong token type | `scp` is absent; no delegated employee scope is present or accepted as a role substitute | Any nonempty `scp`, delegated employee token, browser cookie, or forwarded employee identity returns `401 WRONG_TOKEN_TYPE`, even when a `roles` claim is also present |
| Subject and ownership | `sub`/`oid` may describe the service principal but never an employee; the validated `azp`/`appid` maps to the sole application owner and audit/idempotency actor | Employee-subject selection, employee-owned references, request-supplied owner fields, another `MachinePrincipal`, or cross-application records return `403 MACHINE_OWNER_MISMATCH` before mutation |

| Application role | Permitted core operation |
|------------------|--------------------------|
| `CareerAgent.Roadmap.Generate` | `POST /api/v1/roadmaps` |
| `CareerAgent.Guidance.Read` | `POST /api/v1/guidance` |
| `CareerAgent.Progress.Write` | `POST /api/v1/progress/check-ins` |
| `CareerAgent.Health.Read` | BFF and approved-machine private health and compatibility reads only |

Machine tokens must contain the exact operation role and an approved tenant and
client identity. They cannot invoke employee learning sessions, answers,
reviews, or history, and cannot provide an employee ID to impersonate an owner.
Invalid tokens return `401`; valid tokens lacking the required role return
`403`. Machine application identity is the audit and idempotency actor.

Roadmap generation under `CareerAgent.Roadmap.Generate` creates an
application-owned roadmap whose owner is the validated `MachinePrincipal`.
`CareerAgent.Progress.Write` may mutate only a roadmap owned by that exact
principal. App-only calls cannot read or write employee-owned or another
application's records; request profile/roadmap fields never change the actor.
Machine guidance is stateless apart from application-scoped audit/idempotency.
This preserves roadmap/guidance/progress business outcomes without fabricating
an employee or weakening owner constraints. These application roles do not
grant roadmap list/get or progress-history reads; only each mutation's
established response is returned.

### Private machine transport

- Core serves one HTTPS listener on port 8443 through both the BFF-facing
  ClusterIP and machine-facing internal LoadBalancer. Its Key Vault/CSI server
  certificate includes `core.<namespace>.svc`,
  `core.<namespace>.svc.cluster.local`, and the private machine FQDN. BFF uses
  `https://core.<namespace>.svc:8443/api/v1` and validates a mounted private-CA
  trust bundle; approved machine trust stores use the same CA.
- Approved machine clients connect only from the AKS VNet, an explicitly
  approved peered VNet, or another private-connected network listed in the
  bootstrap manifest. Private DNS resolves the core machine hostname to an
  Azure-internal Kubernetes `LoadBalancer` address; no public IP or Gateway
  route exists for core.
- The internal load balancer is L4. Core terminates HTTPS itself and exposes
  HTTPS health probes. Certificate rotation keeps
  overlapping trust until every core replica serves the replacement version.
- Load-balancer source ranges, subnet NSGs, NetworkPolicy, TLS validation, and
  Entra application-role validation are cumulative controls. Passing a network
  check never bypasses token audience/client/role enforcement.

## Internal lifecycle authorization

- The lifecycle reconciliation workload calls only the BFF ClusterIP route
  `POST /internal/v1/session-revocations`; no public Gateway rule forwards
  `/internal/` to BFF or core, and the UI static server rejects that reserved
  prefix rather than serving the SPA fallback.
- Its access token is issued for the BFF internal API and must contain the
  application role `LearningBff.Session.Revoke`. The BFF independently validates
  signature, issuer, tenant, audience, lifetime, authorized lifecycle client,
  and exact role before accepting the command.
- The request contains validated `tenantId`, `objectId`, reconciliation-run ID,
  and departure timestamp only. It contains no display profile, cookie, token,
  or reusable credential.
- Acceptance atomically revokes all Redis sessions in the owner index and is
  idempotent by reconciliation-run ID plus owner. Missing, wrong-audience,
  delegated, or wrong-role tokens are rejected; NetworkPolicy permits only the
  lifecycle service account to reach the internal BFF route.

## Required Entra identities

- **BFF application registration**: single-tenant confidential web client with
  exact HTTPS callback/logout URIs, delegated permission to the core scope,
  only the `CareerAgent.Health.Read` core application role for nonpersonalized
  capability/readiness calls, a protected internal API exposing only the
  `LearningBff.Session.Revoke` application role to the lifecycle identity, and a
  rotating Key Vault-managed certificate credential mounted through CSI.
- **Core API application registration**: exposes the delegated learning scope
  and dedicated machine application roles and defines the expected audience.
  It does not perform interactive login.
- **Machine application registrations**: one approved confidential registration
  per machine consumer, assigned only the core roles its operations require.
- **BFF Workload Identity**: accesses only BFF Key Vault material and Azure
  Managed Redis. Redis uses TLS, the `https://redis.azure.com/.default` scope,
  proactive token refresh, and reconnect/re-authentication handling.
- **Core Workload Identity**: accesses only core Key Vault material and a
  PostgreSQL DML role mapped to that identity. It cannot alter schemas, consume
  lifecycle/retention-only operations, or access Redis. PostgreSQL
  tokens are refreshed for new pooled connections before expiry.
- **Lifecycle Workload Identity**: used only by the core-image reconciliation
  CronJob. It receives administrator-consented Microsoft Graph application
  permission `User.Read.All` for read-only lookup of known users, the dedicated
  BFF `LearningBff.Session.Revoke` application role, and only the PostgreSQL
  lifecycle role required to update active/departed/check timestamps on known
  `EmployeeIdentity` rows, create/update `DirectoryReconciliationRun` and
  `SessionRevocationOutbox`, and insert or narrowly update only unclaimed
  `RetentionAction` scheduling fields in the same departure transaction. It
  cannot select/delete retention rows, claim or complete retention work, read
  profile or learning content, delete the owner graph, perform general
  application DML or schema DDL, use the BFF employee scope, push ACR content,
  or deploy to AKS.
- **Retention Workload Identity**: used only by the retention CronJob. Its
  PostgreSQL role can execute only audited, security-definer claim/process-due
  procedures. Those procedures internally read, claim, complete, and audit due
  `RetentionAction` rows, delete the identity and complete personalized owner
  graph, remove every owner link, and only then irreversibly anonymize eligible
  unlinked security evidence, returning only minimal action status. The role has no direct queue or learning
  row access and cannot alter eligibility/departure timestamps, access
  Graph/BFF/Redis, perform schema DDL, or deploy to AKS.
- **Lab revalidation Workload Identity**: used only by the 20-hour bounded
  revalidation CronJob. Its PostgreSQL role can read active lab destinations and
  policy versions and update only validation timestamps/status/failure counters/
  safe error codes. It has no profile, learning-session, review, retention,
  schema, Redis, ACR-push, or AKS-deployment permission.
- **Migration Workload Identity**: bound only to the bounded in-cluster
  migration Job service account. It receives the PostgreSQL DDL/Alembic role and
  migration-only Key Vault access, but no Redis, application DML, lifecycle,
  ACR-push, Azure-control-plane, or AKS-deployment permission. The Jenkins
  deployer has only the dedicated-namespace Job/Pod/`pods/log` verbs and cannot
  alter the admission policy, assume this identity, or reach PostgreSQL.
- **ALB Controller Workload Identity**: bound only to the pinned ALB Controller
  service account. It receives `AppGw for Containers Configuration Manager` only
  on the exact Application Gateway for Containers resource group recorded in the
  bootstrap manifest and `Network Contributor` only on the single delegated
  association subnet. It receives no subscription scope, `Owner`, general
  `Contributor`, role-assignment/role-definition action, permission on another
  VNet/subnet/gateway, user-assigned-identity or federated-credential mutation,
  Key Vault/ACR/Storage/Redis/PostgreSQL data access, Kubernetes secret write or
  read beyond the named Gateway TLS reference, or ability to bind another
  service account to its identity.
- **Gateway certificate/DNS identity**: bound only to the bounded 12-hour
  rotation CronJob service account. Its custom Key Vault data role is scoped to
  the named public-gateway and private-core certificate resources and permits
  certificate-version create/import, metadata/public-chain read, enable, and
  disable only; private-key export plus unrelated secret, key, and certificate
  access are denied. Its custom DNS role is scoped to the named browser/private-
  core record sets and permits only required CNAME/A/TXT validation-record reads
  and writes. It receives no zone-wide destructive permission, AGC/AKS workload
  deployment permission, role-assignment/role-definition action, managed-
  identity/federated-credential mutation, ACR, Storage, Redis, PostgreSQL, or
  evidence access and is not shared with the BFF, core, ALB, or migration
  workloads.
- **Evidence hold reconciler identity**: bound only to the hourly hold-
  reconciler service account. It can read the separate hold-control inventory
  and set/clear the enumerated Azure blob-version legal-hold booleans, but cannot
  read/list/delete evidence content, write delivery artifacts, or change the
  fixed time-based immutability policy.
- **AKS kubelet identity**: holds only `AcrPull` on the exact application ACR
  resource recorded in the bootstrap manifest. It has no `AcrPush`, repository
  delete/import, registry-administration, role-assignment/role-definition,
  Key Vault, Storage, Redis, PostgreSQL, evidence, AGC, or DNS permission; no
  application service account may federate to or otherwise assume it, and
  application pods receive no ACR credential.
- **UI service**: has no employee OAuth token, confidential-client credential,
  Redis/PostgreSQL permission, or application Workload Identity by default.

Platform Operations uses an interactive Entra administrator outside Jenkins to
bootstrap the Azure Managed Redis data-plane assignment plus the PostgreSQL
Entra administrator and mutually exclusive core, lifecycle, retention, and
migration principals/grants. Lifecycle receives only the unclaimed-retention-
scheduling grants described above; retention receives only claim/process-due
procedure execution. The reviewed bootstrap verifies cross-role denial and then
disables Redis access-key and PostgreSQL password fallback. Jenkins may
validate these outcomes but may not create or grant the principals.

AKS enables its OIDC issuer and Workload Identity. Each Kubernetes service
account is bound to exactly one intended user-assigned identity through a
federated credential; pods carry the required Workload Identity label. Redis
access keys and PostgreSQL password authentication are disabled after Entra
connectivity and recovery access are verified.

## Configuration

### UI (public runtime values only)

- `BFF_BASE_PATH=/bff/v1`
- accepted BFF contract range and feature flags

### BFF

- Entra tenant/client/authority, credential reference, redirect/logout URIs
- delegated core scope, `CareerAgent.Health.Read`, core private base URL,
  private-CA trust-bundle path, accepted core API range, and allowed
  lifecycle-revocation audience/client/role
- Redis URL, active encryption-key version, bounded decrypt-only key versions,
  cookie/session TTL, allowed Origin
- request limits, timeouts, retry policy, service version

### Core

- issuer/tenant metadata, API audience, allowed BFF client, required scopes
- API version and persistence configuration

Azure deployment supplies confidential values through Key Vault CSI and
Microsoft Entra Workload Identity. Key Vault, Redis, PostgreSQL, gateway, and
telemetry permissions use narrowly scoped identities rather than stored Azure
credentials. ACR pull is intentionally assigned to the AKS kubelet identity.

Fake auth is local/test only and each deployed service fails closed on invalid
trust or destination configuration.

## Dependency failure, readiness, and replica convergence

- Liveness remains process-only. Readiness is evaluated by each replica against
  its own effective configuration and credentials; one healthy replica never
  masks another replica's dependency, trust, mount, or version failure.
- Redis, token-cache encryption, or the active session-key ring becoming
  unavailable makes that BFF replica unready. Session lookup and other operations
  requiring Redis return retryable `503 SESSION_DEPENDENCY_UNAVAILABLE` without
  treating the employee as signed out or deleting core data. Login/callback
  cannot issue a cookie or persist a token cache. When a cookie is presented,
  logout cannot report successful cleanup or clear it until Redis either commits
  revocation or authoritatively reports that no active session remains; an
  indeterminate lookup returns the retryable `503` and preserves the cookie. The
  no-cookie cleanup branch requires no Redis mutation. There is no process-local
  session store, access-key fallback, or best-effort mutation.
- PostgreSQL unavailability makes the affected core replica unready. Reads return
  retryable `503 PERSISTENCE_UNAVAILABLE`; a domain mutation, its actor-scoped
  idempotency claim/result, and every related owner/progress/review/outbox change
  execute in one database transaction. Connection loss, commit ambiguity, or
  token-refresh/reconnect failure rolls back the entire transaction or leaves its
  committed idempotency result authoritative; it never reports success for an
  unknown outcome. The BFF preserves valid input and retries the same intent with
  the same idempotency key only after readiness recovers.
- A missing, unreadable, expired, disabled, SAN-mismatched, public/private-key-
  mismatched, or wrong-version BFF client-certificate CSI mount makes that BFF
  replica unready and blocks new sign-in callbacks and new core-token acquisition.
  A request may finish only with a token that was already validated and remains
  unexpired; the replica never falls back to a client secret, exports the private
  key, skips core TLS validation, or uses a retired/compromised certificate.
  Missing private-core server-certificate or BFF private-CA mounts likewise make
  the affected replica unready; core traffic is never downgraded to HTTP or an
  unverified TLS channel.
- A replica whose configured JWKS version/freshness, certificate version, trust-
  bundle version, or contract version differs from the desired rollout state is
  marked `converging` and removed from readiness. A failed candidate is
  `quarantined` with a nonsecret reason. The prior valid version remains active
  during normal rotation, no prior credential/trust version is retired, and no
  rollout is declared complete until every desired replica reports the same
  candidate and passes its token/TLS probe. Retry uses bounded backoff; operator
  release is required after correction of a quarantined candidate.
- Authentication, lifecycle, and domain handlers validate authority and required
  dependencies before claiming idempotency or starting domain work. A dependency
  failure after transaction start triggers rollback, so a retry cannot observe a
  partially activated session, owner transition, or personalized mutation.

## Session revocation and key rotation

- Local logout deletes/revokes an active Redis session before clearing the
  cookie; every BFF replica observes revocation immediately. A retry after a
  lost response or an already-invalid session still clears the cookie after
  exact-Origin validation and performs no authority-increasing mutation.
- Entra SSO logout is a separate best-effort redirect and does not delay local
  revocation or imply tenant-wide token revocation.
- Session/token-cache encryption keys are versioned in Key Vault. BFF reads the
  current encrypting key and a bounded set of decrypt-only prior versions so
  rotation does not invalidate every session unexpectedly.
- Every session records its encryption-key version. Normal rotation rewrites
  active token caches to the current version on authenticated access and removes
  a prior decrypt-only version only after no live session references it.
- Compromise response revokes all sessions indexed by the affected key version,
  clears their token-cache material, verifies that no live session references
  it, and removes that decrypting version immediately after revocation
  completes; compromised keys receive no normal-rotation grace period.

## BFF client-certificate rotation

- Introduce the replacement certificate before changing the active version and
  register both public keys during a minimum 24-hour overlap.
- During normal rotation, keep the previous credential valid until every BFF
  replica reports the replacement Key Vault version and successfully acquires a
  delegated core token with it. Existing browser sessions, interactive sign-in,
  and personalized BFF requests continue without forced reauthentication.
- Remove the previous Entra credential within 48 hours of replacement
  activation only after the all-replica convergence and token-acquisition gate
  succeeds.
- On suspected compromise, revoke the affected credential immediately and clear
  affected token-cache entries without waiting for overlap or convergence.
  Emergency rotation may invalidate affected browser sessions and require
  reauthentication; the BFF returns a safe sign-in-required response and does
  not delete already saved roadmap, learning, review, or progress records.
- Rotation verification exercises a new sign-in, an existing session, and
  delegated core-token acquisition on every replica during normal rotation, and
  verifies rejection plus safe reauthentication after emergency revocation.

## Gateway and private-core certificate rotation

- Normal public-gateway rotation first creates a disabled candidate version and
  validates its issuer/chain, public/private-key match, required browser SANs,
  validity window, Key Vault state, and listener reference. The previous version
  remains enabled and available for rollback for at least a 24-hour overlap.
  DNS never points to a candidate-only frontend before validation succeeds.
- Activation is a distinct state. Every declared frontend and association in the
  authoritative AGC resource status must be fully provisioned and bound to the
  candidate version, and repeated HTTPS probes through every declared validation
  location must observe its thumbprint while both `/` and `/bff/` routes remain
  healthy. Only then may the candidate become `active`; only after the overlap
  and convergence gate may the prior version be disabled and later removed.
- A candidate that fails issuance, mount/reference, SAN/chain, activation, TLS
  probe, route health, or all-frontend convergence is marked `quarantined` with a
  nonsecret reason. Normal rotation leaves the prior listener/DNS state active.
  If failure occurs after candidate activation but before prior-version
  retirement, the controller restores the prior listener reference, verifies
  all-frontends/probes, quarantines the candidate, and requires explicit operator
  release after correction before another attempt.
- Suspected private-key compromise uses the emergency path: immediately disable
  and remove the compromised version from listener references without waiting
  for overlap, prohibit rollback to it, issue a new candidate, and keep any
  frontend that has not loaded the emergency version out of public readiness.
  If no safe certificate is available, TLS service remains unavailable rather
  than serving the compromised credential or an untrusted fallback. Recovery is
  complete only after all-frontends convergence, browser TLS/route verification,
  compromised-version rejection, and an audited operator acknowledgement.
- Private-core server-certificate rotation applies the same candidate,
  quarantine, normal-overlap, rollback, and compromise rules, substituting every
  core replica plus every BFF private-CA trust-bundle replica for AGC frontends.
  No old server certificate or CA is retired until every core replica serves the
  replacement and every BFF replica validates it; an emergency failure removes
  affected replicas from readiness and never downgrades private traffic to HTTP.

## Employee lifecycle

- BFF verifies active Entra status during sign-in before issuing a session.
- A core-image reconciliation job checks known identities every four hours,
  satisfying the daily-minimum requirement with end-to-end revocation margin.
- The reconciliation CronJob uses its dedicated Workload Identity and
  administrator-consented `User.Read.All` application permission only for
  read-only known-user checks; deletion is recognized by a not-found result.
- Disabled/deleted identities are marked departed and denied personalized
  access in the same transaction that inserts a durable owner-revocation outbox
  row; the reconciliation checkpoint advances only after that commit.
- A dispatcher running at least every five minutes sends the authenticated,
  idempotent outbox command to the private BFF internal route and retries after
  1, 5, 15, 30, then at most 60 minutes until acknowledgement. It alerts at two
  elapsed hours, pages at six, and retains any unacknowledged command through
  the 12-hour post-recognition deadline. BFF revokes all indexed Redis sessions
  before returning an idempotent acknowledgement.
- Throttling, timeout, permission, and directory availability errors are retried
  and never interpreted as proof of departure.
