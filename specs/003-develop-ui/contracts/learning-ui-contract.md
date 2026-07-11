# UI-BFF and BFF-Core Learning Contracts

## Boundary rules

- Browser/UI calls only `/bff/v1` on the approved origin.
- BFF calls only private core `/api/v1` with a delegated core access token.
- UI and BFF never access core storage.
- BFF may validate, orchestrate, and compose view DTOs; it never calculates
  review scores, completion, owner access, milestones, or next action.
- BFF propagates `traceparent`, correlation ID, and idempotency key.

## Compatibility

### `GET /bff/v1/capabilities`

Returns the BFF contract version, accepted UI contract range, feature flags, and
the last verified core contract version, accepted BFF range, and compatibility
state:

```json
{
  "bffContractVersion": "1.4.0",
  "acceptedUiContractRange": ">=1.2.0 <2.0.0",
  "core": {
    "contractVersion": "1.3.0",
    "acceptedBffContractRange": ">=1.1.0 <2.0.0",
    "compatible": true
  },
  "featureFlags": {}
}
```

The UI reads this resource before enabling state-changing actions and preserves
safe unsaved input while compatibility is false or unknown. Every
state-changing UI request includes `X-UI-Contract-Version`; the BFF validates it
against `acceptedUiContractRange` before calling core or claiming an idempotency
key.

Core exposes the same core version and accepted BFF range through private
`GET /api/v1/capabilities`. Every BFF-to-core state-changing request includes
`X-BFF-Contract-Version`; core validates it before claiming an idempotency key
or executing domain work. At either boundary, an unsupported version returns
`409 application/problem+json` with code `CONTRACT_VERSION_UNSUPPORTED`, the
provided version, and the accepted range. BFF preserves this stable code for the
UI and neither boundary performs a downstream call or state mutation.

Breaking changes use a new major path. Within v1, changes are additive and
consumers ignore unknown fields.

## UI-to-BFF resources

- `POST /bff/v1/roadmaps`
- `POST /bff/v1/guidance`
- `POST /bff/v1/progress/check-ins`
- `GET /bff/v1/learning-sessions?roadmapId=<id>`
- `POST /bff/v1/learning-sessions/{id}/start`
- `PUT /bff/v1/learning-sessions/{id}/steps/{stepId}/completion`
- `POST /bff/v1/learning-sessions/{id}/review-attempts`
- `PUT /bff/v1/review-attempts/{attemptId}/answers/{questionId}`
- `POST /bff/v1/review-attempts/{attemptId}/submit`
- `POST /bff/v1/lab-references/{id}/reports`
- `GET /bff/v1/learning/next-action`

BFF responses are UI-shaped, camelCase, exclude authority inputs, and include
safe links/actions. Retryable mutations require session, CSRF, allowed Origin,
and `Idempotency-Key`. BFF binds it to the owner/operation and propagates it
unchanged.

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

## BFF-to-core resources

The generated core client maps BFF resources to versioned core endpoints:

- `POST /api/v1/roadmaps`
- `POST /api/v1/guidance`
- `POST /api/v1/progress/check-ins`
- `GET /api/v1/learning-sessions`
- `POST /api/v1/learning-sessions/{id}/start`
- `PUT /api/v1/learning-sessions/{id}/steps/{step_id}/completion`
- `POST /api/v1/learning-sessions/{id}/review-attempts`
- `PUT /api/v1/review-attempts/{attempt_id}/answers/{question_id}`
- `POST /api/v1/review-attempts/{attempt_id}/submit`
- `POST /api/v1/lab-references/{id}/reports`
- `GET /api/v1/learning/next-action`

Core owner identity always comes from the validated delegated token. No
`employee_id`, `tenant_id`, or `object_id` request field grants authority.

## Idempotency contract

- Key scope is authenticated actor plus operation; keys are opaque and bounded.
- First valid request claims the key and immutable canonical payload hash.
- An identical completed replay returns the established status/body without
  repeating side effects.
- Same key with a changed payload returns `409 IDEMPOTENCY_KEY_REUSED`.
- A concurrent duplicate returns retryable `409 IDEMPOTENCY_IN_PROGRESS` and
  the client retries using the same key.
- Validation failures do not consume a key. A timeout never causes the UI to
  generate a replacement key for the same intended action.

## Machine-consumer boundary

Documented machine operations retain `/api/v1` semantics but use a separate
app-role policy and private route. Application identity scopes idempotency and
audit; machine tokens cannot act as an employee unless a contract explicitly
defines and authorizes that ownership behavior.

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

## Review behavior

- Attempt creation snapshots 3-5 question IDs/content version.
- Unanswered question responses exclude correct keys and explanations.
- Answer response reveals correctness/explanation only for that question.
- Submit calculates score in core; `>=80%` atomically completes
  session/milestone and returns one next action.
- Below threshold returns `retryRequired`; prior attempts remain immutable.

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
