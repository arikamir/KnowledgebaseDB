# UI-BFF and BFF-Core Learning Contracts

## Boundary rules

- Browser/UI calls only `/bff/v1` on the approved origin.
- BFF calls only private core `/api/v1`; personalized calls use a delegated core
  access token and capability/readiness calls use an app-only token containing
  only `CareerAgent.Health.Read`.
- UI and BFF never access core storage.
- BFF may validate, orchestrate, and compose view DTOs; it never calculates
  review scores, completion, owner access, milestones, or next action.
- BFF propagates `traceparent` and correlation ID on downstream calls and
  propagates the actor-scoped idempotency key on canonical domain mutations.

## Authoritative schemas and supported topics

- [`bff-api-v1.openapi.yaml`](./bff-api-v1.openapi.yaml) is authoritative for
  browser/UI-to-BFF routes, camelCase request/response DTOs, session and
  capability payloads, headers, and status codes. BFF route validators and the
  UI client/types/validators are generated from the same digest; neither may
  hand-maintain a competing DTO.
- [`core-api-v1.openapi.yaml`](./core-api-v1.openapi.yaml) is authoritative for
  core v1 field names, types, required fields, numeric bounds, constraints,
  request bodies, response bodies, and documented status codes. The generated
  BFF core client and core validators use the same digest. Explicit BFF mapping
  tests prove every browser DTO maps to a valid core DTO without moving domain
  decisions into the BFF.
- Delegated BFF calls consume the core operations'
  `x-delegated-bff-response-schema` enriched schemas. Core returns `409
  LEGACY_RECORD_NOT_UI_COMPATIBLE` when a legacy record lacks deterministically
  backfilled ownership, milestone keys, ordinals, or persisted progress fields;
  the BFF never invents those values. Approved machine operations retain the
  documented legacy response schema.
- [`supported-guidance-topics-v1.yaml`](./supported-guidance-topics-v1.yaml) is
  authoritative for accepted canonical guidance-topic identifiers and allowed
  aliases. UI choices and BFF normalization derive from that catalog, and core
  rejects a topic absent from its active catalog version before claiming an
  idempotency key or executing guidance work.
- The capabilities response identifies the active BFF schema, core schema, and
  topic-catalog versions. A mismatch among deployed services, generated BFF
  routes/clients, UI consumers, or any authoritative artifact is incompatible
  and blocks state-changing operations and release rather than falling back to
  locally maintained fields or topics.
- [`implementation-readiness-contract.md`](./implementation-readiness-contract.md)
  is normative for the complete journey-outcome, dependency, topic/lab
  lifecycle, learning timing/versioning, persistence, idempotency, capability-
  freshness, measurement, accessibility/browser, service-level, and
  prerequisite matrices. Its stable codes and numeric bounds may not be relaxed
  by a service-local default.

## Compatibility

### `GET /bff/v1/capabilities`

Returns the BFF contract version, accepted UI contract range, feature flags, and
the last verified core contract version, accepted BFF range, and compatibility
state:

```json
{
  "bffContractVersion": "1.4.0",
  "bffApiSchemaVersion": "1.0.0",
  "acceptedUiContractRange": ">=1.2.0 <2.0.0",
  "core": {
    "contractVersion": "1.3.0",
    "acceptedBffContractRange": ">=1.1.0 <2.0.0",
    "apiSchemaVersion": "1.0.0",
    "guidanceTopicCatalogVersion": "1.0.0",
    "compatible": true
  },
  "featureFlags": {}
}
```

The UI reads this resource before enabling state-changing actions and preserves
safe unsaved input while compatibility is false or unknown. Every
state-changing UI request includes `X-UI-Contract-Version`; the BFF validates it
against `acceptedUiContractRange` before calling core or claiming an idempotency
key. `POST /bff/v1/auth/logout` is exempt from compatibility gating so an active
session can always be revoked after session-bound CSRF and exact-Origin checks,
and an invalid/already-revoked-session retry can still clear the cookie after
the exact-Origin check without regaining authority.

Core exposes the same core version and accepted BFF range through private
`GET /api/v1/capabilities`. The BFF reads it with its nonpersonalized
`CareerAgent.Health.Read` app-only token, independently of browser sessions.
Every delegated BFF-to-core state-changing request includes
`X-BFF-Contract-Version`; core validates it before claiming an idempotency key
or executing domain work. The header is optional and nonsemantic for approved
app-role machine consumers. At either boundary, an unsupported version returns
`409 application/problem+json` with code `CONTRACT_VERSION_UNSUPPORTED`, the
provided version, and the accepted range. BFF preserves this stable code for the
UI and neither boundary performs a downstream call or state mutation.

Breaking changes use a new major path. Within v1, changes are additive and
consumers ignore unknown fields.

Both boundaries single-flight refresh capability metadata at 45 seconds. A
state-changing request requires a complete compatible response received within
60 seconds; up-to-five-minute-old metadata is diagnostic/read-only and never
enables a mutation. Missing/malformed metadata returns `503
CAPABILITY_METADATA_INVALID`; fetch failure or write-stale metadata returns
`503 CAPABILITY_METADATA_UNAVAILABLE`. A `409` invalidates the cache. These
decisions occur before idempotency claim and preserve valid input.

## UI-to-BFF resources

- `POST /bff/v1/roadmaps`
- `GET /bff/v1/roadmaps`
- `GET /bff/v1/roadmaps/{id}`
- `POST /bff/v1/guidance`
- `POST /bff/v1/progress/check-ins`
- `GET /bff/v1/progress/reviews?roadmapId=<id>`
- `GET /bff/v1/learning-sessions?roadmapId=<id>`
- `GET /bff/v1/learning-sessions/{id}`
- `POST /bff/v1/learning-sessions/{id}/start`
- `PUT /bff/v1/learning-sessions/{id}/steps/{stepId}/completion`
- `POST /bff/v1/learning-sessions/{id}/review-attempts`
- `GET /bff/v1/learning-sessions/{id}/review-attempts`
- `GET /bff/v1/review-attempts/{id}`
- `PUT /bff/v1/review-attempts/{id}/answers/{questionId}`
- `POST /bff/v1/review-attempts/{id}/submit`
- `POST /bff/v1/lab-references/{id}/reports`
- `GET /bff/v1/learning/next-action`

BFF responses conform to `bff-api-v1.openapi.yaml`: UI-shaped camelCase DTOs
that exclude authority inputs and include only safe links/actions. Retryable
mutations require session, CSRF, allowed Origin, and `Idempotency-Key`. BFF binds
it to the owner/operation and propagates it unchanged.

## Browser refresh and persistence

- UI state is considered persisted only after the BFF confirms the successful
  core persistence result. Navigation within the active browser session may keep
  both persisted display state and explicitly marked unsaved state in memory.
- A browser refresh discards only BFF-unconfirmed UI state and displays a notice
  identifying that unsaved changes were discarded. It never labels a recovered
  local copy as saved.
- After refresh, the UI first restores the opaque BFF session. When the session
  remains valid, it reloads persisted roadmap, learning-session, review, and
  progress records through BFF read resources and replaces stale browser copies
  with those authoritative results.
- A missing session response (`200`, `authenticated=false`) or a definitively
  invalid session (`401 SESSION_NOT_ACTIVE`) requires sign-in. A retryable `503`
  leaves authentication state indeterminate and presents retry guidance rather
  than falsely signing the employee out. Already saved records remain unchanged
  and are reloaded through the BFF after successful reauthentication.
- UI persistence follows the normative `not_yet_saved -> saving -> saved |
  failed_to_save | save_unknown` state machine. An authentication epoch prevents
  any delayed response from a logged-out or replaced session from updating the
  UI. Sign-out/expiry clears UI memory but never saved core data; no personalized
  state or idempotency key is stored in browser durable storage.

## Result-render timing contract

For roadmap and skill-guidance success responses, the UI records
`career.result.fetch-resolved` immediately after the complete response body has
been parsed and validated, and records
`career.result.accessible-render-committed` after the corresponding result is
committed to the rendered accessibility tree, including its heading and status
announcement. The elapsed time between these marks is the SC-004 measurement
and must be no more than one second for at least 95% of successful requests.
Performance telemetry records only route class, duration, and outcome; it never
records employee input or result content.
The test worker/browser/viewport, start/stop marks, warm-up,
five-runs-per-local-constraint matrix, 100-attempt-per-journey accessible-render
matrix, failure denominators, and nearest-rank calculation are fixed by the
implementation readiness contract.

## BFF-to-core resources

The generated core client maps BFF resources to versioned core endpoints:

- `POST /api/v1/roadmaps`
- `GET /api/v1/roadmaps`
- `GET /api/v1/roadmaps/{roadmap_id}`
- `POST /api/v1/guidance`
- `POST /api/v1/progress/check-ins`
- `GET /api/v1/progress/reviews?roadmap_id=<id>`
- `GET /api/v1/learning-sessions?roadmap_id=<id>`
- `GET /api/v1/learning-sessions/{session_id}`
- `POST /api/v1/learning-sessions/{session_id}/start`
- `PUT /api/v1/learning-sessions/{session_id}/steps/{step_id}/completion`
- `POST /api/v1/learning-sessions/{session_id}/review-attempts`
- `GET /api/v1/learning-sessions/{session_id}/review-attempts`
- `GET /api/v1/review-attempts/{attempt_id}`
- `PUT /api/v1/review-attempts/{attempt_id}/answers/{question_id}`
- `POST /api/v1/review-attempts/{attempt_id}/submit`
- `POST /api/v1/lab-references/{lab_reference_id}/reports`
- `GET /api/v1/learning/next-action`

Core owner identity always comes from the validated delegated token. No
`employee_id`, `tenant_id`, or `object_id` request field grants authority.

## Idempotency contract

- This contract applies to retryable domain mutations marked with the canonical
  `Idempotency-Key` parameter. `POST /bff/v1/auth/logout` is intrinsically
  idempotent (a lost-response retry on the exact allowed Origin still clears an
  invalid/already-revoked cookie, so repeats converge on no active session/
  cookie), and
  `POST /api/v1/identity/session-bootstrap` is semantically idempotent by the
  validated tenant/subject (repeats return the same current eligibility/status);
  both are exempt from the header and create no duplicate domain record.
- Key scope is authenticated actor plus operation; keys are opaque and bounded.
- First valid request claims the key and immutable canonical payload hash.
- An identical completed replay returns the established status/body without
  repeating side effects.
- Same key with a changed payload returns `409 IDEMPOTENCY_KEY_REUSED`.
- A concurrent duplicate returns retryable `409 IDEMPOTENCY_IN_PROGRESS` and
  the client retries using the same key.
- Validation failures do not consume a key. A timeout never causes the UI to
  generate a replacement key for the same intended action.
- Processing records use a 60-second lease with a 15-second heartbeat and
  survive process restarts. Expired-lease recovery reconciles the durable
  operation/resource before at most one same-key re-execution.
- `retryable_failed` proves no domain mutation committed and may return to
  processing only after its recorded retry time. `final_failed` replays its
  established problem and never executes again.
- Full response bodies remain for 30 days, after which a non-reusable tombstone
  remains for the actor lifetime. A same-hash replay without a reconstructable
  body returns `409 IDEMPOTENCY_RESULT_EXPIRED`; a changed hash remains `409`.
  Nonterminal records never expire. A delayed pre-logout response is ignored by
  the new authentication epoch even when the durable result later reloads.

## Progress completion-reference compatibility

`completedSteps`/`completed_steps` prefers stable milestone keys. Core preserves
existing trim/case-insensitive milestone-title and skill-area matching, including
its prior all-matches behavior, then persists both the submitted references and
the normalized stable keys. An unknown stable key is `422`; an unknown legacy
value is retained in the check-in but changes no milestone. Newly persisted
reviews always contain their check-in; nullable core `check_in` exists only for
legacy nonpersisted machine-response compatibility and is never emitted by the
BFF.

## Machine-consumer boundary

Documented machine operations retain `/api/v1` semantics but use a separate
app-role policy and private route. Application identity scopes idempotency and
audit; they do not send the BFF-specific contract-version header. Machine tokens
cannot act as an employee. Machine roadmap creation persists an
application-owned roadmap for the validated machine principal; machine progress
accepts only that same principal's roadmap, while guidance remains stateless
apart from application-scoped audit/idempotency. Employee-owned and
cross-application references are rejected. App roles grant no roadmap list/get
or progress-history read operation beyond each mutation's established response.

## Lab publication validation

The provider allowlist begins empty. An addition or domain expansion requires
two distinct human approvers: one member of the configured Learning Content
Owners Microsoft Entra group and one member of the configured Application
Security Reviewers Microsoft Entra group. A person who belongs to both groups
cannot satisfy both approvals. The policy version and both approver identities
are recorded before publication validation begins.

A lab reference enters `active` state only when:

- its destination uses HTTPS;
- redirects remain on an approved provider domain;
- the final destination responds successfully within the configured timeout;
- provider, objective, prerequisites, duration, and cost status are present;
- the successful verification time is recorded.

Active links are revalidated periodically. A transient failure schedules a
bounded retry without exposing a new unverified destination. Repeated failures
move the reference to `unavailable`; users may continue learning and report the
link without losing progress.

Learning Content Operations records the per-content-version applicability
decision. Execution/configuration/deployment/troubleshooting/running-system
objectives—and every borderline case—require a lab; only orientation,
conceptual-comparison, or review-only content may carry a versioned omission.
Validation permits at most five HTTPS redirects and treats loops, downgrade,
private/unapproved destinations, or excess hops as final failures. Reports are
append-only, the first report queues validation within 15 minutes, and row-
version checks prevent a concurrent success from erasing report state. Provider
removal makes references unavailable immediately. Retirement is audited,
prevents new opens/publication, preserves learner progress/reports, and can be
reversed only by a newly approved/revalidated reference version.

## Review behavior

- Attempt creation snapshots 3-5 question IDs/content version.
- Unanswered question responses exclude correct keys and explanations.
- Answer response reveals the submitted choice, answer time,
  correctness/explanation only for that question.
- Restored in-progress attempts include `startedAt`, submitted answers, and null
  score/pass/submission time. Restored submitted attempts require non-null score,
  pass result, and `submittedAt`. Neither form exposes an unanswered correct key.
- Submit calculates score in core; `>=80%` atomically completes
  session/milestone and returns exactly one next action selected by the
  recommended-next-action contract below.
- Below threshold returns `retryRequired`; prior attempts remain immutable.
- The required-content clock, pause/exclusion marks, and first-review stop point
  are fixed by the readiness contract. Feedback is committed to an announced
  region within 1,000 ms of parsing the valid answer response.
- A failed review first exposes missed-concept material, then creates a new full
  attempt over the same pinned 3-5 questions with no copied answers. There is no
  lifetime cap; at most five attempts may start in 60 minutes. The first passing
  attempt permanently completes the session; chronological history retains and
  labels latest/highest scores.
- Start pins content, step, question, and lab versions. Normal retirement permits
  30-day resume; security-critical retirement blocks immediately while keeping
  saved history. An attempt never mixes versions, and compatibility recovery
  reloads the exact pinned aggregate before same-intent retry.

## Recommended next-action contract

Learning-completion and progress-review responses contain exactly one
`recommendedNextAction`. Core selects it and BFF preserves it without re-ranking
or adding alternatives. Core applies the first class with an eligible candidate:

1. retry failed material;
2. resume an active learning session;
3. continue the next incomplete roadmap milestone;
4. review or refresh the completed roadmap when no incomplete learning work
   remains.

Within the selected class, core resolves ties by lowest roadmap milestone
ordinal, then oldest unresolved activity time, then stable identifier. UI
displays only the selected action and never derives a competing recommendation.
The selector interface is Foundation-owned and always supports roadmap state.
Learning migrations register retry/resume candidates when present; when the
learning sibling head is absent, those two candidate sets are unavailable and
the selector deterministically falls through to the roadmap classes. Progress
review therefore remains independently implementable with only its sibling
migration and never queries a nonexistent learning table.

## Error contract

BFF returns `application/problem+json` with stable UI-safe fields:

```json
{
  "type": "https://errors.example/bff/dependency-unavailable",
  "title": "Learning service temporarily unavailable",
  "status": 503,
  "detail": "Try again without re-entering your information.",
  "code": "CORE_UNAVAILABLE",
  "traceId": "trace-id",
  "retryable": true,
  "fieldErrors": []
}
```

BFF maps core `401/403/404/409/422/429/503/504` into stable semantics and never
proxies stack traces, tokens, claims, answer keys, or another employee's IDs.
`409 CONTRACT_VERSION_UNSUPPORTED` remains distinguishable from idempotency
conflicts and always represents a pre-mutation compatibility rejection.

## Health contract

- UI `/health/live`, `/health/ready`: static server and runtime config only.
- BFF `/health/live`: process only; `/health/ready`: config, Redis, token-cache
  encryption, and supported core contract.
- Core `/health/live`: process only; `/health/ready`: app initialization and
  required persistence.

Transient downstream failure does not fail another service's liveness probe.
Azure Monitor records service name/version, ACR image digest, trace/correlation
ID, route class, latency, status, and dependency outcome across Gateway, BFF,
and core. Tokens, cookies, authorization headers, answers, and personal data are
excluded from telemetry.
