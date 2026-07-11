# UI, BFF, and Core Authentication Contract

## Public routing

- `/` and UI assets route to the separate UI Service.
- `/bff/*` routes to the separate BFF Service on the same TLS origin.
- Core `/api/v1` remains private. Machine consumers use an approved private
  route with their own app-role authentication policy.

## BFF browser-auth routes

### `GET /bff/v1/auth/login?return_to=<relative-path>`

- Starts single-tenant Entra authorization-code sign-in.
- Allows only same-origin relative return paths.
- Stores state, nonce, PKCE verifier, and return path in short-lived Redis state.
- Returns `302` to the tenant-specific Microsoft authorization endpoint.

### `GET /bff/v1/auth/callback?code=<code>&state=<state>`

- Validates state/nonce and redeems code with MSAL Node.
- Requests delegated core API scope and stores encrypted token cache in Redis.
- Rotates to a new opaque BFF session.
- Returns `303` to the stored UI path.

### `POST /bff/v1/auth/logout`

- Requires BFF session, CSRF token, and exact allowed Origin.
- Revokes local session first, clears cookie, then redirects to Entra logout.

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

- BFF acquires a delegated access token whose audience is the core API.
- Core validates signature/JWKS, issuer, tenant, audience, time claims,
  authorized BFF client, and required delegated scope.
- Core derives owner from validated `(tid, oid)`.
- Core rejects ID tokens, tokens for another audience, spoofed identity headers,
  expired tokens, missing scope, and unauthorized clients.

Core accepts only configured signing algorithms, validates `nbf` and `exp` with
bounded clock skew, and refreshes tenant JWKS without accepting an untrusted
key source. For v2 access tokens, the authorized BFF client is matched through `azp`; the
delegated permission is matched through `scp`; employee ownership uses the
tenant-stable `(tid, oid)` pair. Human-readable claims such as name, email, or
UPN are presentation values and never authorization keys.

## Machine-consumer authorization

- Machine consumers obtain client-credentials access tokens for the core API.
- Core requires the operation's application role in `roles`, validates the
  approved client and standard token claims, and rejects `scp` as a substitute.
- Employee-personalized routes reject app-only tokens unless an explicit
  machine contract defines how ownership is authorized.
- Machine traffic uses a governed private core route; core gains no public
  browser route.

| Application role | Permitted core operation |
|------------------|--------------------------|
| `CareerAgent.Roadmap.Generate` | `POST /api/v1/roadmaps` |
| `CareerAgent.Guidance.Read` | `POST /api/v1/guidance` |
| `CareerAgent.Progress.Write` | `POST /api/v1/progress/check-ins` |
| `CareerAgent.Health.Read` | Machine health and compatibility reads only |

Machine tokens must contain the exact operation role and an approved tenant and
client identity. They cannot invoke employee learning sessions, answers,
reviews, or history, and cannot provide an employee ID to impersonate an owner.
Invalid tokens return `401`; valid tokens lacking the required role return
`403`. Machine application identity is the audit and idempotency actor.

## Required Entra identities

- **BFF application registration**: single-tenant confidential web client with
  exact HTTPS callback/logout URIs, delegated permission to the core scope, and
  a rotating Key Vault-managed certificate credential mounted through CSI.
- **Core API application registration**: exposes the delegated learning scope
  and dedicated machine application roles and defines the expected audience.
  It does not perform interactive login.
- **Machine application registrations**: one approved confidential registration
  per machine consumer, assigned only the core roles its operations require.
- **BFF Workload Identity**: accesses only BFF Key Vault material and Azure
  Managed Redis. Redis uses TLS, the `https://redis.azure.com/.default` scope,
  proactive token refresh, and reconnect/re-authentication handling.
- **Core Workload Identity**: accesses only core Key Vault material and the
  PostgreSQL role mapped to that identity. PostgreSQL tokens are refreshed for
  new pooled connections before expiry. An Entra administrator bootstraps a
  nonadministrator database principal and grants only required schema/data
  permissions.
- **Gateway Workload Identity**: limited to required Key Vault certificate and
  Azure DNS operations.
- **AKS kubelet identity**: holds registry-scoped `AcrPull`; application pods do
  not receive ACR credentials.
- **UI service**: has no employee OAuth token, confidential-client credential,
  Redis/PostgreSQL permission, or application Workload Identity by default.

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
- delegated core scope, core private base URL, accepted core API range
- Redis URL, encryption-key reference, cookie/session TTL, allowed Origin
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

## Session revocation and key rotation

- Local logout deletes/revokes the Redis session before clearing the cookie;
  every BFF replica observes revocation immediately.
- Entra SSO logout is a separate best-effort redirect and does not delay local
  revocation or imply tenant-wide token revocation.
- Session/token-cache encryption keys are versioned in Key Vault. BFF reads the
  current encrypting key and a bounded set of decrypt-only prior versions so
  rotation does not invalidate every session unexpectedly.
- Compromise response can revoke all sessions for a key version and remove that
  decrypting version after the configured grace period.

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

## Employee lifecycle

- BFF verifies active Entra status during sign-in before issuing a session.
- A core-image reconciliation job checks known identities at least daily.
- Disabled/deleted identities are marked departed, denied personalized access,
  and have all indexed Redis sessions revoked.
- Throttling, timeout, permission, and directory availability errors are retried
  and never interpreted as proof of departure.
