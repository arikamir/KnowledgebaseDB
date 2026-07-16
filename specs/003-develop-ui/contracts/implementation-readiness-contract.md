# Implementation Readiness Contract

**Status**: Normative design contract
**Scope**: DevOps Career Agent UI, BFF, core, and non-production Azure pilot
**Version**: 1.0.0

## Authority and interpretation

This contract supplies the concrete behavior required to implement and verify
the feature where the specification, plan, data model, or another contract is
less specific. Existing security and ownership boundaries remain mandatory. A
conflict between this contract and an authoritative OpenAPI document, the
guidance-topic catalog, or an existing security contract blocks implementation
and release; no service may silently choose one interpretation.

The specialized [authentication](./auth-ui-contract.md),
[learning](./learning-ui-contract.md), and
[delivery](./jenkins-delivery-contract.md) contracts remain normative for their
respective boundaries. Every FR/SC obligation in this contract MUST have an
implementation task, positive/negative verification, and retained-evidence
mapping in [requirements-traceability.md](../requirements-traceability.md).
Missing, empty, duplicate, out-of-order, or unknown-task mappings block
implementation and release.

The approved [universal readiness scenario manifest](../../../tests/fixtures/readiness-scenario-manifest-v1.yaml)
fixes every stable case ID, parameterized operation set, denominator, manifest
digest, and derived per-case fixture digest used by the universal outcomes below. The approved
[core performance profile](../../../tests/performance/performance-profile-v1.json)
fixes the SC-043 requests, BFF-to-core operation mapping, assignment, hard
timeouts, percentile policy, pinned BFF/core contract-byte digests,
generated-mapper regeneration/drift verification, complete evidence schema,
full-profile digest, and fixture-set digest. Editing either artifact requires a
reviewed version increment;
an implementation-generated substitute is not authoritative.

The approved [interaction performance profile](../../../tests/performance/interaction-performance-profile-v1.json)
fixes the eight SC-050 operations, BFF/core contract bindings, deterministic
fixtures and assignment, scenario-specific monotonic timing boundaries,
warm-up, five-second timeout, 100-attempt denominator, nearest-rank p95,
required evidence schema, full-profile digest, and fixture-set digest. Editing
this profile likewise requires a reviewed version increment; runtime or test
code cannot substitute another scenario or boundary.

The following words are normative:

- **mutation** means any request that can create, update, complete, report, or
  delete domain state;
- **saved** means committed by core PostgreSQL and confirmed by a successful BFF
  response;
- **active browser state** means in-memory UI state that has not been confirmed
  as saved;
- **same intended action** means the same authenticated actor, operation,
  idempotency key, and canonical request hash;
- **operations owner** means one of Application Operations, Platform Operations,
  Learning Content Operations, Security Reviewers, or Product/UX Research as
  named in the applicable table below.

Every browser-visible problem response uses `application/problem+json`, a stable
`code`, a safe `detail`, `retryable`, `traceId`, and field errors when applicable.
The UI never derives authority or a domain transition from an error string.

## Formal implementation-gate model

This section is the single normative implementation-gate model. The
[formal implementation-gate checklist](../checklists/implementation-gate.md) is
the decision record for this model. The older
[requirements checklist](../checklists/requirements.md) and the
[implementation-readiness checklist](../checklists/implementation-readiness.md)
are required quality inputs, not competing gate authorities. An unchecked item
in any of the three active checklists blocks the gate whose entry criteria cite
that checklist. Historical notes never override a current normative artifact.

### Artifact authority and required inventory

Authority is divided by subject; there is no silent general-purpose precedence:

| Subject | Authoritative artifact | Conflict behavior |
|---|---|---|
| Project governance | `.specify/memory/constitution.md` | A violation blocks all implementation until the artifacts comply. Changing a constitutional principle requires a separate constitution amendment with the required version bump and impact report. |
| Product scope, journeys, functional requirements, and measurable outcomes | `spec.md` | A design artifact may refine but cannot weaken or replace an FR/SC. |
| Architecture, technology, ownership, and sequencing | `plan.md`, `data-model.md`, and `tasks.md` for their named subjects | A sequencing or ownership conflict blocks the affected task and every dependent checkpoint. |
| HTTP schemas and operation compatibility | `bff-api-v1.openapi.yaml` and `core-api-v1.openapi.yaml` | OpenAPI is authoritative for wire shape; conflicting prose or generated code blocks implementation and release. |
| Authentication, learning, delivery, and readiness behavior | The corresponding specialized contract, this contract, and `supported-guidance-topics-v1.yaml` | Specialized contracts refine the spec. Conflicts between specialized contracts, OpenAPI, security boundaries, or the spec block the affected task and release. |
| Approved test denominators and performance inputs | `tests/fixtures/readiness-scenario-manifest-v1.yaml`, `tests/performance/performance-profile-v1.json`, and `tests/performance/interaction-performance-profile-v1.json` | Digest, schema, denominator, timing-boundary, or mapping drift blocks the consuming checkpoint. |
| Requirement-to-task/evidence mapping | `requirements-traceability.md` | The exact structural rules below apply; prose elsewhere cannot excuse a bad row. |
| Live environment facts and protected-delivery authority | The reviewed bootstrap manifest and immutable evidence produced by the tasks named in `tasks.md` | Planning assumptions, Terraform state access by Jenkins, and runtime/test substitutions are never authoritative. |

Before T001 starts, the constitution, spec, plan, data model, research, quickstart,
tasks, all four specialized contracts, both OpenAPI files, the guidance catalog,
the readiness scenario manifest, both performance profiles, all three active
checklists, and the traceability matrix MUST exist and be internally
well-formed. A traceability evidence path may be absent before implementation
only when its row names the exact task that will produce it; all normative input
paths must already exist. No other missing artifact is accepted as future work.

The traceability matrix MUST contain exactly one row for each FR-001 through
FR-075 and SC-001 through SC-050, in identifier order. Every row MUST contain a
nonempty acceptance/operational outcome, existing normative source, at least one
existing implementation task, at least one existing positive or negative
verification task, and either a retained evidence path or an explicit
evidence-handling exception. Duplicate identifiers, skipped or out-of-order
identifiers, empty required cells, nonexistent normative paths, task references
outside T001-T198, or future outputs without their exact producer task are
blocking errors.

### Ordered gate states and entry criteria

Gate approval is checkpoint-specific; it does not assert that later live or
pilot evidence already exists.

| Gate state | Objective entry criteria | Decision authority and record |
|---|---|---|
| `SETUP_READY` | Required pre-T001 inventory exists; all three active checklists have zero unchecked items; prerequisite script resolves the feature and tasks; the constitution check reports zero violations; traceability has exactly 125 valid rows. External Azure evidence is not required. | Specification author and implementation lead record the checklist counts, artifact revision, and traceability validation result. |
| `FOUNDATION_READY` | Setup tasks T001-T009 pass. The test-first ordering and file-ownership rules in `tasks.md` are accepted. | Implementation lead records task/test evidence. |
| `US1_READY` | The exact US1 minimum-foundation task set and `scripts/ci/validate-us1-foundation.sh` pass. No other Foundation or release task may be added implicitly. | Implementation lead records the manifest digest and scoped test report. |
| `US2_READY` | The exact US1 minimum-foundation task set (without requiring US1 story implementation), T033/T051, and the US2 contract/catalog prerequisites pass. | Implementation lead records catalog and contract evidence. |
| `US3_READY` | The exact US1 minimum-foundation task set (without requiring US1 story implementation) plus T023-T025, T038-T040, and T088-T091 pass. | Implementation lead plus Learning Content Operations and Security Reviewers record policy/catalog evidence; no live provider evidence is needed for authoring. |
| `US4_READY` | The minimum owned-roadmap foundation named in `tasks.md` passes; US1 or US3 implementation is not a prerequisite. | Implementation lead records roadmap fixture/schema evidence. |
| `EXTERNAL_BOOTSTRAP_READY` | All authoring, guardrail, static-contract, identity/RBAC, migration-policy, dry-run, and live-harness producer tasks required before T194 pass; the operator/approver identities and fresh provider/quota/capacity attestations satisfy the prerequisite register. | Platform Operations and the distinct consent/security approver record the reviewed plan, exact authorization, freshness, and denial evidence. Only then may T194 mutate Azure. |
| `PROTECTED_DELIVERY_READY` | T194 has produced the reviewed nonsecret manifest; live preflights and identity denials are fresh; selected story/release tests, migration/evidence gates, controller audit, immutable evidence, change plan, and rollback controls pass. | Platform Operations and Application Operations approve immutable delivery evidence; Security Reviewers approve identity/security evidence. |
| `PILOT_READY` | Complete four-journey release, T154, browser/accessibility matrix, lab/reference gates, SLO recovery exercises, frozen participant protocol, and all T197/T198 prerequisites pass. | Product/UX Research owns participant/usability evidence; Learning Content Operations owns content/lab evidence; Application and Platform Operations own availability/recovery evidence. |

The US1 checkpoint is a local/container, roadmap-only non-release increment. It
may defer unrelated release infrastructure, live lab, browser-matrix, and pilot
evidence, but it may not defer the shared identity, ownership, authorization,
contract, session, persistence, idempotency, compatibility, or fail-closed
security boundaries included in its exact minimum-foundation manifest. A
complete release requires all four stories and all release-wide obligations.

### Deterministic gate evaluation

For gate evaluation, the following terms have exact meanings:

- **missing**: a required path, identifier, cell, case, digest, approval, or
  evidence value does not exist at its required checkpoint;
- **empty**: a required value contains no non-whitespace content or an expected
  collection has zero entries;
- **duplicate**: the same normative identifier, stable case ID, task ID within a
  manifest, or evidence identity appears more than once where uniqueness is
  required;
- **out-of-order**: FR, SC, task, migration, stage, or rollback order differs
  from its explicitly enumerated sequence;
- **unknown-task**: a task reference is not one of the current T001-T198 entries;
- **drift**: generated bytes, mapping, digest, schema, catalog, manifest, or
  deployed digest differs from the approved input or recorded output;
- **conflict**: two applicable normative artifacts require incompatible
  outcomes and neither is an explicitly permitted refinement;
- **stale**: evidence is older than its stated freshness window at the instant
  its consumer begins, or its source configuration changed after collection.

A gate is `blocked` when any required artifact/checklist/row is invalid, a
required test or denial case fails, an applicable prerequisite is missing or
stale, a normative conflict exists, or required evidence cannot be retained.
The owner in the gate/prerequisite table is accountable for resolution; the
decision authority records the failing condition, evidence path, affected
requirements/tasks, and corrective action. Clearance requires corrected input
plus rerun of the failed validator and every invalidated downstream validator.

Conditional delivery gates use only the archived change plan. UI-only,
BFF-only, core-only, shared-contract, infrastructure, documentation-only,
first/missing-baseline, and multi-path applicability are the exact classes in
the Jenkins delivery contract and SC-034. Multiple matches boolean-OR without
clearing an earlier selection. Documentation-only changes publish no image but
still run contract-integrity validation. A genuine first/missing baseline runs
all service and validation lanes. No job may recalculate applicability later.

Authoring evidence proves source, static policy, dry-run, or test-harness
quality and permits only the associated local task. External-execution evidence
records the authorized T194 mutation. Live attestation proves the current
deployed consumer at protected-release or pilot time. Evidence from one class
cannot substitute for another. Jenkins cannot repair bootstrap drift, execute
Terraform apply/import, read Terraform state, or replace approved inputs with
runtime/test values.

### Exceptions, revalidation, and safe stopping

A gate exception is valid only when the governing requirement explicitly
permits deferral. Its immutable record MUST include scope, rationale, accountable
owner, approver, creation and expiry times, affected FR/SC/task IDs, evidence
location, compensating controls, and the first checkpoint that remains blocked.
Exceptions cannot waive the constitution, an FR/SC, authorization/ownership,
fail-closed behavior, credential separation, privacy/retention, traceability
integrity, or required positive/negative verification. An unavailable owner,
denied privilege, or unavailable dependency blocks only its declared consumer;
it never grants a fallback identity, bypass, or silent scope reduction.

Local authoring may continue when an external prerequisite affects only live
bootstrap, a protected-delivery lane, a machine consumer, a lab reference, or
the pilot and no task dependency names that prerequisite. The affected
operation remains unavailable and fail-closed. Stopping at a checkpoint does
not invalidate accepted source artifacts, completed tasks, immutable evidence,
or unaffected service digests. After a delivery mutation, stopping follows the
journaled reverse rollback and verification rules; an irreversible migration
uses forward recovery and keeps protected delivery blocked.

Any edit to the constitution, spec, plan, data model, tasks, normative contract,
OpenAPI, catalog, readiness manifest, performance profile, traceability matrix,
or prerequisite source invalidates checklist answers and approvals whose cited
inputs or digests changed. Revalidation starts with T030/T034 structural and
drift checks, then reruns affected story/release validators using the archived
change plan. Freshness starts at the recorded successful collection time and
expires at the exact stated duration; configuration change invalidates it
immediately. Evidence current at review but stale before external execution,
protected delivery, or pilot opening MUST be renewed before that consumer.

### Checklist completion and responsibility policy

An item may be marked complete only when every clause is answered by a current
normative artifact and the checklist Notes cite the governing sections or a
validation result. The specification author proposes the mark; the decision
authority for the affected gate accepts it. Any substantive source edit triggers
the revalidation rule above. Unchecked advisory items may exist only in a
checklist explicitly labelled historical or non-gating; the three active
checklists named above allow none at `SETUP_READY`.

Responsibilities are fixed as follows: the specification author owns artifact
completeness and traceability; the implementation lead owns task ordering,
tests, and story checkpoints; Product/UX Research owns participant, usability,
browser, and accessibility study evidence; Security Reviewers own security
policy, machine-client/network approval, and negative authorization review;
Learning Content Operations owns topics, lab applicability, validation, and
retirement; Application Operations owns application readiness, eligible-minute
observations, monthly close, and application recovery; Platform Operations owns
Azure/Jenkins bootstrap, identities, infrastructure, delivery, immutable
evidence, and infrastructure recovery. Unavailable authorities leave their gate
blocked until an authorized delegate is recorded under the same separation-of-
duties rules.

## Primary-journey outcome contract

The requirements in this matrix apply to every implementation and end-to-end
test. A retained input is kept only in UI memory and is labelled `Not yet saved`
unless core previously confirmed it as saved.

| Journey | Success | Validation or not found | Authentication expiry | Compatibility failure | Dependency outage and retry | Navigation, refresh, and interruption | Intentional exclusions |
|---|---|---|---|---|---|---|---|
| US1 Create roadmap | Persist the employee-owned roadmap, render milestones, and mark the submitted profile/result `saved`. | Schema/domain validation returns `422 VALIDATION_FAILED` with associated fields before claiming the key. Creation has no referenced resource, so `404` is not applicable. | Stop submission, retain entered profile in memory, return `401 SESSION_NOT_ACTIVE`, and require sign-in. After sign-in, reload saved roadmaps; the unsaved profile is not claimed to be restored. | Return `409 CONTRACT_VERSION_UNSUPPORTED` before a downstream call, key claim, or mutation; retain the profile and disable submit until fresh compatible metadata exists. | BFF/core/PostgreSQL failure returns the dependency code in the dependency matrix. No automatic new mutation is submitted. The retry control reuses the original key and profile. | In-session navigation retains the form and last result. Refresh or browser closure discards unconfirmed form state with the required notice on next load. A confirmed roadmap reloads from BFF. | Resource-not-found and learning-step interruption do not apply to creation. |
| US2 Skill guidance | Resolve an active catalog topic, return guidance and eligible labs, and preserve the topic/profile for the active session. Guidance itself remains stateless; its idempotency result is still authoritative. | Blank/malformed fields return `422 VALIDATION_FAILED`; no unambiguous catalog match returns `422 GUIDANCE_TOPIC_UNINTERPRETABLE`; a known non-active topic returns `422 GUIDANCE_TOPIC_UNAVAILABLE`. No key is claimed. `404` is not applicable because no stored domain resource is addressed. | Stop the request, retain topic/profile in memory, require sign-in, and never substitute anonymous guidance. | Same pre-mutation `409` behavior as US1; the topic/profile remain editable. | A service outage is `CORE_UNAVAILABLE` or the exact dependency code, never a topic error. Retry reuses the same key. A lab-provider outage affects only that lab and never deletes the guidance result. | Navigation retains current guidance during the active session. Refresh/closure discards stateless unconfirmed guidance and reloads only durable employee records. | Stored-result restoration and roadmap-not-found are intentionally excluded because guidance is stateless in this release. |
| US3 Focused learning | Pin a published content version, persist each completed step, finalize review scoring atomically, and return exactly one next action on first passing score. | Missing/foreign session, step, attempt, or question is a safe `404 RESOURCE_NOT_FOUND`; malformed answers are `422 VALIDATION_FAILED`; a finalized attempt rejects changes with `409 REVIEW_ATTEMPT_FINALIZED`. | Stop new work and require sign-in. Confirmed steps/attempt answers survive and reload. An unconfirmed answer remains unsaved and is discarded on refresh/closure. | Block the attempted mutation before key claim. Existing saved progress remains readable when the compatible read path is available; otherwise show the availability state without rewriting it. | Retriable failure preserves saved steps and the active attempt. A retry uses the same key for the same answer/submit action. Lab failure follows the lab lifecycle and does not block non-lab steps. | Navigation and interruption resume at the lowest incomplete required step. Refresh reloads session, attempts, and submitted answers. Version-change behavior follows the pinned-version rules below. | Roadmap creation is not a prerequisite; deterministic owned-roadmap/content fixtures are valid. Anonymous/offline completion is excluded. |
| US4 Progress review | Atomically persist the owner-scoped check-in, roadmap revision, review, and exactly one core-selected next action. | Missing/foreign roadmap returns safe `404 RESOURCE_NOT_FOUND` and creates no check-in. Unknown stable milestone keys return `422 VALIDATION_FAILED`; legacy unmatched text is retained but changes no milestone as defined by the core contract. | Stop submission, retain unsaved notes in memory, require sign-in, then reload the latest saved review. | Return `409 CONTRACT_VERSION_UNSUPPORTED` before key claim or mutation and retain notes. | A retry after timeout/outage uses the same key. An indeterminate PostgreSQL outcome is resolved through the idempotency record before another execution. | In-session navigation retains the latest review. Refresh reloads saved check-ins/reviews; unsaved notes are discarded with notice. A delayed pre-logout response cannot update the signed-out UI. | Learning tables may be absent; retry/resume candidates are then unavailable and the selector falls through to roadmap candidates. |

For all four journeys, unexpected safe errors use `500 UNEXPECTED_ERROR`; they
preserve valid in-memory input, expose no diagnostic detail, and are not
automatically retried. Authentication, compatibility, and validation rejection
occur before idempotency claim. A timeout after dispatch is indeterminate and is
resolved only by replaying the same key.

## Stable dependency-failure contract

The following matrix is exhaustive for first-release runtime and delivery
dependencies. A mutation may be automatically retried only where the row says so.
All retry delays are server-side and use full jitter; `Retry-After` is returned
when the browser may retry.

| Dependency | Required failure behavior | Retry and no-partial-mutation rule | Readiness, recovery, owner, and evidence |
|---|---|---|---|
| Public Gateway | When no route/TLS listener is available, no application response is possible; synthetic monitoring records `GATEWAY_UNAVAILABLE`. No request reaches UI/BFF/core. | The browser may retry a safe page load. It never automatically replays a mutation. | Gateway health is independent of pod liveness. Recovery requires successful TLS, `/`, and `/bff/v1/capabilities` probes. Owner: Platform Operations. Evidence: probe time, hostname, certificate version, route, status, and trace ID. |
| UI service | Static/config failure prevents the journey but cannot affect BFF/core health or machine operations. Runtime-config validation fails closed as `UI_CONFIGURATION_INVALID`. | No mutation is emitted until validated BFF path/origin and fresh capability metadata are loaded. | UI readiness is false; liveness remains process-local. Owner: Application Operations. Evidence: image digest, config digest, readiness reason, and independent core/BFF probes. |
| BFF service | The UI shows `BFF_UNAVAILABLE`, retains safe in-memory input, and disables dependent actions. Core and approved machine operations continue. | No automatic mutation retry. User retry uses the same key. If a BFF process dies after dispatch, core idempotency resolves the result. | Zero ready replicas for five minutes pages Application Operations. Recovery requires BFF readiness plus fresh core capability verification. Evidence: BFF digest, replica/readiness count, dependency outcome, and trace ID. |
| Core service | BFF returns `503 CORE_UNAVAILABLE`; it never fabricates roadmap, score, next action, ownership, or persistence success. | Safe capability/read GETs may retry twice at 250 ms and 1 s. A dispatched mutation may be retried once only with the same key; otherwise control returns to the user. Core transactions are atomic. | BFF remains live but is not ready for personalized mutations. Owner: Application Operations. Evidence: route class, core digest, attempt count, status, and correlation ID. |
| Azure Managed Redis | Missing/indeterminate session or token-cache access returns `503 SESSION_DEPENDENCY_UNAVAILABLE`, never `401`, and never revokes or clears the cookie. No core call follows. | Token acquisition/session mutation is not retried inside the browser request after two connection attempts at 100 ms and 500 ms. Recovery re-reads the authoritative Redis record; no local fallback exists. | BFF readiness is false while Redis cannot be authenticated/read. Owner: Application Operations; Azure attribution also routes to Platform Operations. Evidence: token version only, connection outcome, retry count, and readiness transition—never keys or session values. |
| Azure Database for PostgreSQL | Connection/authentication failure returns `503 PERSISTENCE_UNAVAILABLE`. A transaction error rolls back all domain and idempotency changes. | Connection establishment retries twice at 250 ms and 1 s. A timeout after commit is resolved by same-key replay; a new key is prohibited. No cache or BFF state is treated as durable. | Core readiness is false until a read/write canary using the core role succeeds. Owner: Application Operations; managed-service cause also routes to Platform Operations. Evidence: transaction outcome, SQLSTATE class, pool/token generation, and trace ID without SQL values. |
| Entra authorization/token/directory endpoints | Interactive failure is `503 IDENTITY_PROVIDER_UNAVAILABLE`; lifecycle lookup failure leaves the previous directory state unchanged and never implies departure. Token acquisition failure cannot downgrade to anonymous or another credential. | Interactive authorization is user-retried. Workload token acquisition retries twice at 1 s and 4 s. Directory reconciliation uses its existing 1/5/15/30/60-minute bounded schedule. | BFF/core readiness is false only when their required token cannot be acquired; directory reconciliation has its separate 6/8-hour alert/page. Owner: Application Operations and Identity/Security Operations. Evidence excludes tokens and claims. |
| Tenant JWKS | Unknown signing key triggers one immediate trusted-issuer refresh. Cached keys are fresh for 6 hours and may be used for an already-known `kid` for at most 24 hours from successful fetch. A key still unknown after successful refresh is token-type-specific `401 DELEGATED_TOKEN_INVALID` or `401 MACHINE_TOKEN_INVALID`; unavailable or older-than-24-hour metadata without a bounded-fresh validating key is `503 AUTH_KEY_METADATA_UNAVAILABLE`. | Authentication fails closed before authorization, key claim, or mutation. No alternate issuer/key source is allowed. One refresh attempt per request prevents storms. | Readiness becomes false at the 24-hour bound or when the configured issuer cannot be validated. Recovery requires a successful HTTPS issuer/JWKS fetch and signature test. Owner: Identity/Security Operations. Evidence: issuer hash, `kid`, fetched age, result, never key material. |
| Key Vault/CSI key, trust, or certificate mount | Missing, unreadable, mismatched, or expired key/certificate/trust material makes the affected replica unready. BFF session decryption failure is `503 KEY_MATERIAL_UNAVAILABLE`, not logout. TLS listeners never start with an invalid certificate. | No plaintext/file/env fallback exists. A request is not forwarded from an unready replica. Rotation retry follows the rotation matrix below. | Recovery requires mount refresh, cryptographic parse, expected version/SAN/issuer validation, and a functional token/TLS probe. Owner: Platform Operations with Application Operations for BFF material. Evidence records only secret/certificate version IDs and validation outcome. |
| ACR | Existing running pods continue. Pull, scan, publish, or digest resolution failure stops that delivery lane as `ACR_UNAVAILABLE`; tags never substitute for digests. A digest published without promotion enters `published_unpromoted`. | Before mutation, no environment change occurs. During rollout, image-pull failure triggers the delivery rollback contract; it never rebuilds or promotes an unverified image. A `published_unpromoted` digest is quarantined from release aliases and is ineligible for another build unless that build creates a new release manifest and passes current gates. | Delivery gate fails; runtime readiness of existing pods is unchanged. Unreferenced unpromoted content becomes GC-eligible after 30 days, while build ID, revision, scan, SBOM, release-manifest digest, and disposition remain in evidence for 90 days. Promoted or held digests are excluded from GC. Owner: Platform Operations. Evidence: repository, digest, stage, identity, provenance/disposition, and safe Azure error code. |
| AKS/control plane | Runtime node/pod failures follow readiness/PDB/HPA behavior. An unavailable control plane blocks promotion and verification. | Before mutation, leave digests unchanged. After mutation, journal the failure and execute bounded rollback under the delivery rollback contract as soon as the control plane is reachable; never infer success from a timeout. | Owner: Platform Operations. Evidence: cluster/resource IDs, deployment generation, observed digest, rollout status, and journal state. |
| Azure Monitor/Application Insights | Telemetry export failure never authorizes, rejects, or rolls back a learner mutation and never changes readiness. Each process buffers at most 1,000 safe envelopes or five minutes, whichever is reached first, then drops oldest and increments a local dropped-count metric. | No request waits more than 100 ms for telemetry. Application state remains authoritative in PostgreSQL/Redis. | Recovery flushes only unexpired safe envelopes. Owner: Platform Operations. Evidence: exporter state, buffered/dropped count, and Azure resource-health observation; no personal content. |
| External lab provider | Opening failure does not complete a lab or learning step. UI shows `LAB_DESTINATION_UNAVAILABLE`, permits reporting, and preserves progress. Validation follows the lab matrix below. | Browser never automatically follows an unapproved redirect or repeats a state-changing report with a new key. | Lab state and validation age drive Learning Content Operations alerts. Evidence: reference/version, redirect-domain hashes, status class, duration, and safe reason. |
| Jenkins controller | An unaccepted trigger is not a delivery attempt. For every accepted attempt, the trusted controller plugin fsyncs each monotonic transition to both the normal run record and a host-managed append-only replicated controller-audit volume before ACI allocation. Protected scheduling is disabled while either copy is unhealthy. Controller loss before environment mutation leaves state unchanged; loss after mutation requires journal-driven recovery. | On restart or controller-disk loss, Platform Operations restores the replica and reconciles build IDs against queue/run metadata, webhook audit, and Azure evidence before protected delivery resumes. An accepted nonterminal orphan becomes `aborted_recovered`; if it mutated the environment, new protected delivery remains blocked until rollback is verified or an approved recovery reaches a verified terminal state. Duplicate promotion is prohibited. | Controller-audit RPO is zero after an accepted transition and RTO is at most four hours. Owner: Platform Operations. Evidence: two-copy health, hourly integrity result, encrypted-backup/restore result, build ID, source revision, lifecycle events, reconciliation decision, terminal result, failed stage, journal/recovery result, and evidence pointer. Jobs, agents, repository code, and delivery identities cannot modify or delete the replicated store. |
| ACI provisioning/connection | Failure stops before Azure application authentication and publication as `ACI_AGENT_UNAVAILABLE`; no local/static agent or second credential is used. Agent loss after a mutation is a delivery failure. | Before mutation, no change. After mutation, the deployer recovery path resumes the journal and rollback; a new build cannot supersede the environment lock. | Owner: Platform Operations. Evidence: cloud/template, identity binding, container-group ID, connection stage, and safe error. |
| Delivery evidence storage | Rejection/unavailability blocks the next mutation. After a mutation it triggers rollback. A controller-local archive is never authoritative. | Required writes retry three times at 1, 4, and 16 seconds with `If-None-Match: *`; an indeterminate write is verified by the exact immutable path/version before retry. No overwrite is allowed. | Owner: Platform Operations and Security Reviewers. Recovery requires accepted immutable version, policy confirmation, and evidence-set completeness. Evidence failure itself is recorded in the controller audit. |

## Guidance-topic states and outcomes

Topic normalization trims surrounding whitespace, compares case-insensitively,
and matches only the canonical ID, name, or aliases in the active versioned
catalog. Each normalized token must resolve to exactly one entry.

| Classification | Required outcome |
|---|---|
| Active unambiguous match | Canonicalize to the catalog ID, claim the idempotency key, and execute guidance. The response reports the requested and resolved topic. |
| Known entry with `status: unavailable` | Return `422 GUIDANCE_TOPIC_UNAVAILABLE`, `retryable=true`, preserve topic/profile, and do not claim the key. The UI may offer catalog topics but may not silently replace the request. |
| Known entry with `status: retired` | Return `422 GUIDANCE_TOPIC_UNAVAILABLE`, `retryable=false`, preserve topic/profile, and show that the topic is no longer offered. |
| No match or a normalization ambiguity | Return `422 GUIDANCE_TOPIC_UNINTERPRETABLE`, `retryable=false`, associate the error with `topic`, and do not claim the key. |
| Blank, over 128 Unicode code points, or schema-invalid input | Return `422 VALIDATION_FAILED` before catalog resolution or key claim. |
| Core/catalog dependency outage | Return `503 CORE_UNAVAILABLE` or `503 CAPABILITY_METADATA_UNAVAILABLE`; never describe it as an unavailable topic. |

Only a reviewed catalog change may change topic state. Learning Content
Operations owns the change; Application Operations owns generated-artifact and
runtime-catalog convergence. A topic catalog version mismatch is compatibility
failure, not a topic classification.

## External-lab governance and lifecycle

### Authoritative applicability rule

Learning Content Operations classifies the objective when publishing the content
version. A lab is mandatory when satisfying the objective requires the learner
to execute a command, change configuration, deploy, troubleshoot, or observe a
running system. A lab may be omitted only for `orientation`,
`conceptual_comparison`, or `review_only`. A borderline objective is classified
as requiring a lab. Splitting wording to evade the rule is prohibited.

`lab_required`, the classifier identity, decision time, and policy version are
recorded with the content version. An omission also records exactly one allowed
reason and a human-readable explanation of 20-500 characters. Security Reviewers
approve provider/domain trust but do not override the applicability decision.
Publication fails if the required lab or allowed omission record is absent.

### Provider and reference lifecycle

- The allowlist begins empty. Provider/domain addition or expansion requires the
  two distinct approvals already defined by FR-066 before validation.
- Validation permits HTTPS only, at most five redirects, and a 10-second timeout
  per attempt. The initial attempt plus at most two retries is the complete
  validation budget. A redirect loop, repeated URL, downgrade to HTTP, redirect
  to a non-approved domain, private/link-local/metadata/cluster address, or more
  than five redirects is a non-retryable final failure.
- `408`, `429`, `5xx`, DNS timeout, connection timeout, and TLS handshake timeout
  are retryable failures. `Retry-After` is honored only up to 60 seconds within
  the bounded job deadline. `4xx` other than `408`/`429`, invalid TLS, and policy
  violations are final failures.
- A reference may become `active` only after complete validation against the
  exact recorded policy version. Scheduled validation starts every 20 hours so
  every active reference is checked within 24 hours.
- One transient scheduled failure retains the prior state. Three consecutive
  failed scheduled validations transition `active` or `reported` to
  `unavailable` and immediately alert Learning Content Operations. A later
  complete successful validation resets the counter and transitions
  `unavailable` to `active` unless the reference or provider is retired.
- A learner report is append-only and never marks progress complete. The first
  report changes `active` to `reported` and queues an out-of-cycle validation
  within 15 minutes. Additional reports during queued/running validation remain
  append-only; validation and reporting use row-version checks so neither loses
  the other transition.
- Any provider-domain removal, approval expiry/revocation, or redirect to a newly
  unapproved domain immediately makes affected references `unavailable`; a new
  approval and successful complete validation are required for recovery.
- Learning Content Operations may retire a reference or provider only through a
  reviewed, audited content-policy change with reason and effective time.
  Retirement transitions any reference state to `retired`, prevents new
  publication and new external opens, stops scheduled validation, but preserves
  reports and audit history. In-progress learning retains completed non-lab
  steps and receives an alternate/skip explanation; retirement never grants lab
  completion. Reversal requires a new policy version, both provider approvals,
  and complete validation; it creates a new active reference version rather than
  mutating the retired version.

Validation evidence records reference/content/policy version, start/end,
attempts, redirect count and approved-domain decisions, status class, safe error,
prior/new state, and validator identity. It contains no learner identity or URL
query string.

## Learning timing, reviews, and version changes

### Required-content clock

The 20-30-minute session estimate and SC-011 measurement use an accumulated
required-content clock:

1. Start at `learning.required.started`, emitted after the first required step is
   committed to the accessibility tree following the employee's Start action.
2. Count required reading/activity interaction time and the first complete
   scored review attempt through `review.first-result-rendered`.
3. Pause before rendering optional material, when the employee explicitly
   leaves/pauses, when the document is hidden for more than five seconds, and
   immediately before opening an external lab. Resume when the next required
   step regains visible focus.
4. Stop after the first review result and explanations are committed to the
   accessibility tree. Retry study, later attempts, optional material, external
   lab time, and interruptions are separately accumulated and never added to the
   required-content duration.

Every segment records monotonic start/stop marks and a reason. A negative,
overlapping, or missing segment invalidates that participant's measurement run
and counts the SC-011 task as failed; it does not remove the participant.

### Review and retry rules

- A published review has exactly 3-5 scored questions aligned to the pinned
  objective/content version. Exactly one in-progress attempt may exist per
  employee learning session.
- Answer feedback is returned only for that answer. The UI commits correctness
  and explanation to an `aria-live="polite"` region within 1,000 ms after the
  complete valid BFF answer response is parsed. An unanswered correct key never
  crosses either API boundary.
- Submission scores the full 3-5-question attempt. At least 80% completes the
  session and milestone atomically. A lower score enters `retry_required`.
- The retry path first presents only missed concepts/questions and their saved
  explanations as review material, then creates a new full scored attempt using
  the same pinned 3-5 question IDs and content version. Answers are not copied.
  Question and choice order remain stable in the first release so restoration is
  deterministic.
- There is no lifetime attempt limit. Rate protection permits at most five new
  attempts per employee learning session in any rolling 60 minutes; the sixth
  returns `429 REVIEW_RETRY_RATE_LIMITED` with a 15-minute `Retry-After`. This
  does not change completion or discard history.
- Every submitted attempt, score, answer, `startedAt`, `answeredAt`, and
  `submittedAt` remains immutable. History displays attempts chronologically and
  labels the latest submitted and highest score. The first attempt reaching 80%
  permanently establishes completion; later attempts cannot be started and no
  lower score can reverse it.

### Content and contract changes during work

- Starting a learning session pins `content_version`, ordered step IDs, review
  question IDs, and lab-reference versions. Normal publication/retirement never
  changes that snapshot. New sessions use the latest published version.
- A normally retired content version remains resumable for existing sessions for
  30 days after `retired_at`. After that bound, core returns `409
  CONTENT_VERSION_RETIRED`, preserves completed steps/history, and offers the
  latest replacement session; no step is silently copied unless its stable step
  key and objective version are identical.
- A security-critical retirement may block the pinned version immediately. The
  audited retirement identifies the affected versions and reason. Saved history
  remains; any in-progress attempt cannot be submitted or scored, the retired
  session is no longer resumable, and the employee starts a replacement review.
- A lab version becoming unavailable or retired while its tab is open never
  completes the lab. On return, BFF reloads current lab state; non-lab progress
  and the pinned learning content remain intact.
- An in-progress review always submits against its question snapshot. A content
  deployment cannot mix question versions within an attempt.
- UI/BFF/core contract changes follow the capability freshness contract below.
  Incompatible mutations stop before key claim. Once compatibility returns, the
  exact saved session/attempt is reloaded and the same intended action may be
  retried.
- A progress submission evaluates the actor-owned roadmap revision in one
  transaction. If the roadmap changes before commit, core retries resolution
  once; a second conflict returns `409 ROADMAP_VERSION_CONFLICT`, creates no
  check-in, preserves notes, and requires an authoritative reload before retry
  with a new intended-action key.

## Browser persistence-state contract

The UI uses this state machine per form, answer, step, or result:

| State | Entry and display | Exit and durability |
|---|---|---|
| `not_yet_saved` | Local edit or compatible action not yet dispatched. Display `Not yet saved`. | Submit enters `saving`; discard/navigation policy below may remove it. |
| `saving` | A validated request has been dispatched with one key. Disable duplicate controls and announce `Saving`. | Confirmed success enters `saved`; definitive failure enters `failed_to_save`; timeout/connection loss enters `save_unknown`. |
| `save_unknown` | The response outcome is indeterminate. Display `Save status unknown—check before retrying`; never display success. | Same-key replay or authoritative reload resolves to `saved` or `failed_to_save`. A new key is prohibited. |
| `failed_to_save` | A definitive non-success response proves no successful result for that action. Display the stable safe error and retain editable values in memory. | Correction creates a new intended action/key; transient retry of unchanged input reuses the same key as governed by idempotency status. |
| `saved` | Core commit and successful BFF confirmation, or an authoritative BFF reload of that record. Display `Saved` with confirmation time. | A later local edit creates a separate `not_yet_saved` version while the last confirmed version remains durable. |

Navigation in the same active browser session retains these in-memory states.
Refresh and browser closure discard `not_yet_saved`, `failed_to_save`, and local
display copies; refresh first shows the discard notice and then reloads durable
records. `saving` becomes `save_unknown` after refresh and must be resolved by the
same key when that key is still in memory; because browser storage may not retain
the key, navigation is blocked while `saving` and the page presents an explicit
Cancel-and-check choice rather than encouraging refresh.

Sign-out clears all UI memory after local BFF revocation. Idle/absolute expiry
and emergency reauthentication clear personalized UI memory but never delete
saved core data. An outage preserves safe in-memory input only until refresh,
closure, sign-out, or expiry. No form, answer, key, token, or result is persisted
to localStorage, sessionStorage, IndexedDB, a service worker, or browser cache.

Every request is tagged with an in-memory authentication epoch. A response from
an older epoch, including a delayed response after logout, may be logged safely
but cannot update the UI or recreate a session. If core committed it, the result
appears only through authoritative reload after a new sign-in.

## Idempotency, concurrency, restart, and expiry

### State transitions

| Record state | Required behavior |
|---|---|
| Absent | After authentication, compatibility, and validation, atomically insert `processing` with actor, operation, key, canonical hash, a 60-second execution lease, and 15-second heartbeat. |
| `processing`, same hash, live lease | Return `409 IDEMPOTENCY_IN_PROGRESS`, `retryable=true`, and `Retry-After: 2`; do not execute again. |
| `processing`, same hash, expired lease | One worker atomically acquires recovery. It checks the operation/outbox/resource reference. A committed transition is finalized as `succeeded`; otherwise execution may restart once under the same key. |
| Any state, changed hash | Return `409 IDEMPOTENCY_KEY_REUSED`; never alter the record or domain state. |
| `succeeded`, same hash | Return the established status/body/resource reference exactly; no side effect is repeated. |
| `retryable_failed`, same hash | Return the recorded transient problem until `retry_after`; then one caller may atomically transition back to `processing` under the same key. This state guarantees that no domain mutation committed. |
| `final_failed`, same hash | Return the established final problem exactly. It never executes again. Schema/auth/compatibility rejection occurs before key creation and therefore is not stored as `final_failed`. |

Domain transition and `succeeded` result commit in one PostgreSQL transaction.
Process/pod restart cannot erase a claimed key. Multiple tabs and clients are
indistinguishable under the actor/operation/key uniqueness constraint. Owner
identity comes only from the validated token, so a key can never cross owners.

A caller timeout never creates a replacement key. It replays the same key after
two seconds. If no definitive result is available, the server returns
`IDEMPOTENCY_IN_PROGRESS`; it never guesses that the transition failed.

Full response bodies are retained for 30 days. After 30 days, the record retains
actor, operation, key, hash, terminal status, response status, and resource
reference as a non-reusable tombstone while the actor remains eligible. A
same-hash replay whose body can no longer be reconstructed returns `409
IDEMPOTENCY_RESULT_EXPIRED`; a changed hash remains `409`. The key is never made
reusable. Employee tombstones are purged only with the complete employee owner
graph after departure, when the actor can no longer authenticate. Machine
tombstones remain until 90 days after principal revocation. `processing` and
`retryable_failed` records cannot expire; recovery must first reach a terminal
state. These rules are the safe interpretation of `expires_at`.

`409 IDEMPOTENCY_RESULT_EXPIRED` is the sole approved expired-result outcome.
Returning `410`, returning a generic conflict without this stable code,
executing again, or permitting key reuse is prohibited.

## Capability metadata and cache freshness

Capability responses are never persisted as learner data. Freshness is measured
from the local monotonic receipt time of a successfully parsed HTTPS response;
clock values supplied by a peer are evidence only.

| Boundary | Fresh-write rule | Stale/read behavior | Failure code |
|---|---|---|---|
| UI to BFF | The UI may enable a mutation only when BFF capability metadata was fetched successfully within the previous 60 seconds and the UI range intersects the active BFF version/schema. Every mutation still sends `X-UI-Contract-Version`. | In-memory metadata may display read-only availability for five minutes with a `Checking service compatibility` banner, but it cannot enable a mutation after 60 seconds. It is never stored in browser durable storage. | Disjoint range: `409 CONTRACT_VERSION_UNSUPPORTED`. Missing/malformed fields: `503 CAPABILITY_METADATA_INVALID`. Fetch unavailable or older than 60 seconds for a write: `503 CAPABILITY_METADATA_UNAVAILABLE`. |
| BFF to core | BFF may forward a delegated mutation only when core capability metadata was fetched/validated within 60 seconds, the BFF range intersects core, active API/catalog versions match generated artifacts, and the mutation is advertised. It sends `X-BFF-Contract-Version`. | BFF may use metadata up to five minutes old only for safe read presentation and health diagnosis. It may not use stale metadata for a mutation. | Same codes and pre-idempotency behavior as UI/BFF. Core outage remains `503 CORE_UNAVAILABLE` when compatibility was fresh but execution failed. |

Each service uses a single-flight refresh when metadata reaches 45 seconds of
age. A parse failure never replaces the last valid cache entry, but the 60-second
write bound still applies. Recovery requires one complete compatible response;
unsupported state remains blocked until then. Logout is the sole compatibility
exemption and still requires its Origin/session/CSRF policy. Capability evidence
records boundary, receipt age, service/image/schema/catalog versions, range
intersection, requested mutation, decision, and stable failure code.

## Pilot usability protocol

### Population and sample

- Recruit a pre-screened roster of 24 internal employees and freeze a randomized
  order within three experience strata: 8 beginner, 8 intermediate, 8 advanced.
  The measured sample is exactly the first eligible 7 beginner, 7 intermediate,
  and 6 advanced participants in frozen order.
- Eligibility requires organizational Entra access, English working proficiency,
  no contribution to feature requirements/design/code/tests, no prior exposure
  to the task script, and consent to anonymous task/timing collection.
- A participant may be replaced only before the first measured task for consent
  withdrawal, inability to authenticate caused by an independently verified
  tenant/platform setup defect, or failure of an eligibility assertion. The next
  reserve in the same stratum replaces them. After the first task starts, every
  abandonment, outage, timeout, or inability is retained as a failed outcome and
  no replacement is allowed.
- At least five of the 20 participants perform the journey tasks at 375 CSS
  pixels using Chrome mobile emulation and at least five at 1440 CSS pixels; the
  remaining ten are balanced across 768 and 1024 pixels. Allocation is frozen
  before testing.

### Standard task script and assistance

Every participant receives the same neutral instructions, in order:

1. sign in and create a roadmap from the supplied valid profile; identify the
   first recommended action;
2. find one supplied supported topic and explain the practical next action;
3. complete the supplied focused session's required content and first review;
4. identify current/completed milestones and the one recommended next action;
5. observe one supplied validation error and one simulated temporary outage,
   then recover without re-entering valid information.

The facilitator may resolve equipment/accessibility setup before timing and may
repeat the written instruction verbatim. Any navigation hint, field suggestion,
definition, confirmation, or correction after timing starts is assistance. The
task may continue, but it fails every criterion requiring completion without
facilitator assistance. Screen/video is optional; event marks, outcome, viewport,
browser version, assistance flag, and anonymous participant ID are mandatory.

### Questionnaire and scoring

Use a five-point scale: 1 Strongly disagree, 2 Disagree, 3 Neither, 4 Agree,
5 Strongly agree. Ask exactly:

- SC-007: “The forms, progress feedback, results, and error messages were clear.”
- SC-015: “The review feedback and explanations helped me understand why my
  answers were correct or incorrect.”
- SC-017: “The completion feedback and recommended next action make me want to
  continue learning.”

SC-001 passes when at least 18 of all 20 unassisted participants both submit the
roadmap and identify the exact core-returned first action. SC-007 and SC-015 each
require at least 17 ratings of 4 or 5. SC-011 requires at least 18 accumulated
required-content durations from 20 through first-review result to be 20-30
minutes inclusive. SC-016 requires at least 18 participants to identify all
three requested elements without assistance. SC-017 requires at least 16 ratings
of 4 or 5. Missing answers, abandonment, assisted outcomes, or measurement errors
count as failures; additional observations never enter the denominator.

Product/UX Research owns recruitment, frozen allocation, scripts, consent,
facilitator log, raw anonymized events, calculation, and signed result summary.

## Reproducible one-second measurements

### Local validation

Use a production UI build on a dedicated 4-vCPU/8-GiB test worker with no CPU
throttling, 1440x900 viewport, animations disabled, and the exact browser version
recorded. The start mark is the first instruction in the click/Enter submit
handler before validation. The stop mark is after all relevant field guidance,
error summary, focus target, and accessibility status announcement are committed
to the accessibility tree.

The fixture manifest contains one case for every generated `required`, type,
enum, minimum/maximum, length, pattern, and documented cross-field constraint in
each of the four journey forms. Run each case five times in each supported browser
major version. Every measured case must be at most 1,000 ms. A browser crash,
missing mark, negative duration, validation exception, or timeout counts as a
failed measurement. Warm-up consists of one excluded valid and one excluded
invalid submission per browser; no later run is excluded.

### Accessible result rendering

Use the deployed non-production optimized build, 1440x900 viewport, and a fixed
valid roadmap/guidance fixture digest. For each journey, run 100 valid attempts:
10 sequential attempts on each of 10 isolated browser contexts after one excluded
warm-up per context. `career.result.fetch-resolved` occurs only after the complete
success body is parsed and schema-valid. `career.result.accessible-render-committed`
occurs after the result heading, content, and status announcement are present in
the accessibility tree.

At least 95 of 100 attempts must return a valid success payload. Among successful
payloads, at least 95% must render within 1,000 ms using nearest-rank p95.
Network/BFF/core failures remain in the 100-attempt availability count and may not
be replaced, although they have no render interval. Missing/invalid marks on a
successful payload count as render failures. Evidence retains environment,
browser/OS/viewport, UI/BFF/core digests, fixture digest, all raw marks/outcomes,
failure code, count, and calculation.

## Universal scenario denominator policy

“100%,” “all tested,” and “exactly one” mean every applicable case in this table,
not an implementation-selected sample. Each case runs once as a contract test
and once against the deployed pilot environment when it has an external
dependency. Parameterized actors/resources count as separate cases.

| Criteria | Required enumerated cases and denominator |
|---|---|
| SC-009 | 14 cases: four journey validation cases, US3/US4 not-found cases, and BFF plus core outage for each of four journeys. Pass requires 14/14 preserve every other valid field. |
| SC-010 | 16 cases: own and foreign roadmap, learning session, review attempt, and progress review for employee A and B. Own access 8/8; foreign access 0/8. |
| SC-012 | Six interruption cases: explicit leave, route navigation, refresh, browser close/reopen, session expiry/reauthentication, and BFF restart. Pass requires 6/6 resume at the lowest incomplete step. |
| SC-013/SC-037/SC-038 | 18 manifest cases: one required-lab case, three allowed omission reasons, seven separate missing-required-metadata cases, direct approved domain, approved redirect, loop, HTTP downgrade, unapproved redirect, private destination, and retired provider. All 18 applicable assertions must pass. |
| SC-014 | Five score cases: 0%, 79%, 80%, 100%, and fail-then-pass retry. Pass requires exact incomplete/complete transitions in 5/5 and no reversal. |
| SC-019/SC-023/SC-024 | UI, BFF, and core outage injected independently; for each, assert two unaffected service health probes and three approved machine operations. Denominator is 3 outages x 5 observations = 15; origin attribution must be 15/15. |
| SC-020 | At each of UI/BFF and BFF/core boundaries run current-supported, previous-supported, disjoint, missing, malformed, unavailable, fresh-cache, and stale-cache cases: 16 total. Every rejection must be pre-downstream, pre-key, and pre-mutation. |
| SC-021/SC-022 | For each of four journeys run normal BFF path, direct core attempt, and frozen-core presentation/composition build: 12 cases. All normal paths use BFF, all direct attempts fail, and all frozen-core builds pass. |
| SC-026/SC-033/SC-034/SC-035 | UI-only, BFF-only, core-only, all-service, docs-only, first-build, stale build, concurrent build, failure before mutation, and failure after each of the core, BFF, and UI mutations: 12 delivery cases. Each must produce the exact digest/journal outcome. |
| SC-027/SC-028 | Delegated valid plus wrong issuer, tenant, audience, algorithm/key, lifetime, client, scope, subject, ID-token, and spoofed-header cases; machine valid plus delegated, missing role, wrong role, wrong audience, wrong client, and the operation-specific ownership/spoof/isolation cases declared for that operation. The manifest fixes 11 delegated cases for each of 18 delegated operations (198) and 8 operation-specific machine cases for each of 4 machine operations (32). All accepts/rejects and owners must match. |
| SC-029 | Idle expiry immediately before/at/after 30 minutes and absolute expiry immediately before/at/after 8 hours, directed through every BFF replica, plus Redis-indeterminate lookup: denominator `7 x replica_count`; all boundaries and saved-data assertions must pass. |
| SC-030/SC-031 | Active, disabled, deleted, unknown, throttled, BFF-outage, dispatcher-restart, pre-deadline, deadline, purge success, purge rollback, restore catch-up, and anonymization-denial cases: 13 total. All access, ordering, timing, and unlinking assertions must pass. |
| SC-032 | Same-key simultaneous tabs, same-key delayed retry, changed payload, different actor same key, process restart while processing, timeout after commit, retryable failure, final failure, and expired-result replay: nine cases per retryable operation. Exactly one transition means committed transition count equals one in every same-intent case and zero additional transitions in every conflict case. |
| SC-036/SC-048 | Accepted success/failure/abort, unaccepted trigger, controller restart, replicated-volume disk-loss restore, pre-agent failure, agent connection, missing Jenkinsfile audit call, and attempted shadowing: ten cases. Accepted attempts finalize exactly once; the unaccepted trigger creates no attempt. |
| SC-039 | Validator, publisher, and deployer templates with required, missing, swapped, additional, and system-assigned identities plus PR/protected references: 17 cases. All unauthorized token/stage attempts must fail. |
| SC-040/SC-041 | For each of the three credential types, run normal, partial-convergence, rollback-injection, and emergency cases: 12 cases. All gates and saved-data outcomes must pass. |
| SC-042 | Authorized/unauthorized reader, writer cross-prefix/read/list/overwrite/delete, hold-manager set/extend/release/direct-Azure, reconciler exact/cross-version, partial set/clear, expiry, early release, post-lock deletion, 180-day ceiling, and prohibited-content cases: 20 cases. Every required allow/deny/lifecycle assertion must pass. |

The linked manifest, digest
`ca2bd36fcc96fd5cefc6bdcd7ae9366d02085940888925df954e47f16501f66d`,
assigns every stable case ID and parameterized case-ID template. CI MUST
recompute that digest over the manifest's declared payload scope and reject
drift before running a case.
Setup failure, unavailable dependency, crash, timeout, or missing evidence is a
failed case, not an exclusion. A case may be marked not applicable only where the
journey matrix explicitly does so; the reason is recorded before execution and
does not reduce another criterion's stated denominator.

## Rotation and partial-convergence matrix

| Credential | Normal rotation | Partial convergence or rollback | Emergency rotation |
|---|---|---|---|
| BFF confidential-client certificate | Register replacement, retain both for at least 24 hours, direct fresh callback, existing-session refresh, delegated token, and health-token tests through every current replica. Remove the prior credential no later than 48 hours after activation and only after all pass. | An unready/non-converged replica is removed from service. Keep the old credential and active version; retry for up to 24 hours. If still incomplete, mark rotation quarantined, page Application and Platform Operations, and do not retire old. A failed new credential rolls replicas back to the old active version. | Revoke compromised credential immediately, remove affected replicas from service, revoke sessions/token caches using it, activate a clean version, and require safe reauthentication. No overlap requirement overrides compromise response; saved core records survive. |
| Public-gateway/private-core TLS certificate | Make the replacement secret/version available at least 24 hours before retirement. Verify SAN/issuer/expiry, old+new trust, reload, HTTPS probes, and every gateway/core replica. Remove old trust within 48 hours after full convergence. | Keep old listener/trust active and remove non-converged endpoints from readiness. Retry for 24 hours, then quarantine and page Platform Operations. Before old removal, failed new probes roll back to old. | Revoke/remove the compromised version immediately, block unverified listeners, issue/mount replacement, and restore only after TLS plus route/health probes. Temporary availability loss is safer than serving compromised TLS. |
| Jenkins cloud `azure` provisioning credential | Rotate at most every 90 days and before fewer than 30 valid days remain. Install replacement through the credential-manager role, then provision identityless validator, publisher, and deployer smoke agents while the previous credential remains valid. Revoke old only after all three identity checks pass within two hours. | Failed/partial template validation leaves the old uncompromised credential active but quarantines protected promotion. Retry within two hours; otherwise page Platform Operations. Roll back the stable Jenkins credential entry to the old version without exposing either secret. | Revoke compromised credential immediately and disable ordinary provisioning. Only the audited quarantine path may install a replacement and run the three smoke agents. Ordinary builds resume only after all pass; no fallback credential/agent is permitted. |

All rotation evidence records credential/certificate version identifiers,
activation and retirement times, replica/template inventory, each probe, rollback
or quarantine, operator, alert, and outcome. Secret material is prohibited.

## Accessibility behavior and browser boundary

### Required accessibility behaviors

- Focus follows DOM/task order; positive `tabindex` is prohibited. Route changes
  move focus to the page `h1`; validation failure moves focus to the error summary
  and links each item to its field; successful mutation moves focus to the result
  heading. Closing a dialog or returning from an external lab restores focus to
  the invoking control.
- Every interactive element has a programmatic name, role, state, and keyboard
  operation. A visible focus indicator is at least 2 CSS pixels on two adjacent
  sides with a 3:1 contrast ratio against adjacent colors.
- In-progress, saved/failed, compatibility, outage, review feedback, and
  completion changes are announced through an appropriate polite live region;
  blocking validation/authentication errors use an assertive alert. Repeated
  renders do not announce unchanged content.
- Fields use visible labels, `aria-describedby` for guidance/errors, and
  `aria-invalid` only while invalid. Pages use one `h1` and nested headings
  without skipped structural levels.
- A session-timeout dialog appears two minutes before idle expiry and, when
  relevant, two minutes before the absolute expiry. It announces the remaining
  time, distinguishes extendable idle from non-extendable absolute expiry, and
  offers Continue/Sign out. Only an authenticated Continue action extends idle.
- External lab controls state provider, cost, estimated duration, and “opens in a
  new tab” in visible and accessible text. Opening/returning never implies
  completion.
- Progress is conveyed by text labels (`completed`, `current`, `upcoming`) in
  addition to color/graphics. Review feedback conveys correct/incorrect plus an
  explanation without relying on color or icons.
- At the required widths and scaling below, primary forms, navigation, results,
  learning steps, and reviews have no page-level horizontal scroll. Wide code or
  tabular examples may use a labelled internal scroll region without obscuring
  primary actions.
- Formal certification of complete WCAG 2.2 AA conformance remains excluded; the
  listed behaviors are mandatory and their failure blocks release.

### Browser, orientation, scaling, and assistive-technology matrix

At verification start, record and freeze the exact latest two stable major
versions of Chrome, Edge, Firefox, and Safari/WebKit; a major released during the
run does not change the matrix. Re-run the full gate before release if evidence is
older than 30 days.

| Platform | Required coverage |
|---|---|
| Windows 11 | Both frozen majors of Chrome, Edge, and Firefox at 320, 375, 768, 1024, 1440, and 1920 CSS pixels; keyboard-only on every width; NVDA current stable with latest Chrome and Firefox for all four journeys. |
| macOS current and previous supported release | Both frozen Chrome, Firefox, and Safari/WebKit majors at all six widths; keyboard-only; VoiceOver with latest Safari for all four journeys. |
| Mobile emulation | Latest frozen Chrome and Safari/WebKit at 375x812 portrait and 812x375 landscape plus 320x568 portrait; touch targets, on-screen keyboard, orientation change, and focus restoration. Physical mobile-device/AT certification is excluded from the pilot. |
| Zoom/text scaling | Latest Chrome, Edge, Firefox, and Safari at 200% browser zoom on a 1280x800 viewport; latest Chrome/Safari with 200% text scaling. No content/action loss, overlap, or page-level horizontal scrolling except labelled internal code/table regions. |

An assistive-technology expectation passes only when names/roles/states, reading
order, live announcements, field associations, dialog behavior, and focus
restoration are all correct. Automated checks supplement but never replace the
manual keyboard/NVDA/VoiceOver cases.

## Non-production pilot service-level decisions

These targets apply only to scheduled pilot windows, 08:00-18:00 Israel time on
business days. There is no production SLA in this feature.

| Concern | Pilot decision, rationale, and accountable owner |
|---|---|
| Browser-journey availability | Target 99.0% per calendar month during pilot windows. One synthetic observation runs per eligible minute and succeeds only when the public TLS Gateway request, UI/runtime-config load, and `/bff/v1/capabilities` response all pass their readiness and contract checks. Availability is `successful eligible observations / total eligible observations * 100`. Planned maintenance is excluded only with at least 24-hour notice and is capped at four hours/month; unannounced or above-cap minutes remain in the denominator. This is sufficient for a ten-to-twenty-user non-production pilot. Owners: Application and Platform Operations. |
| Stateless UI/BFF/core recovery | RTO 60 minutes from a last-known-good immutable ACR digest and reviewed configuration. RPO is zero for deployed source/config because Git, ACR digest, and deployment evidence are authoritative. Owner: Platform Operations. |
| PostgreSQL learning data | RPO at most five minutes and RTO at most four hours using Azure PostgreSQL continuous backup/PITR with seven-day retention. A restore remains inaccessible until retention catch-up and owner/access checks pass. Owners: Application and Platform Operations. |
| Redis browser sessions | Durable-session RPO is intentionally excluded: Redis session loss may require every employee to sign in again but may not lose saved learning data. RTO is 60 minutes; no backup is restored into authority without key/version validation. Rationale: session state is disposable and core is authoritative. Owner: Application Operations. |
| Delivery evidence | Once an upload is accepted, RPO is zero for that immutable version; required evidence write failure blocks mutation/causes rollback. Recovery target for evidence-store access is four hours, but delivery remains stopped until recovered. Owner: Platform Operations and Security Reviewers. |
| Jenkins controller audit | After the plugin accepts and fsyncs a transition to both copies, RPO is zero. Controller-disk-loss RTO is at most four hours, including replicated-store restore and queue/run, webhook, and Azure-evidence reconciliation. Protected scheduling remains blocked until every accepted orphan is terminal and every post-mutation orphan has verified rollback or approved recovery. Owner: Platform Operations. |
| Telemetry | No durability guarantee; up to five minutes or 1,000 envelopes per process may be lost. Telemetry is non-authoritative and never gates learner persistence. Owner: Platform Operations. |
| External labs | No availability/RTO/RPO target is claimed because providers are external. The product target is detection within the 20-hour schedule/24-hour maximum, report-triggered validation within 15 minutes, and non-blocking learner recovery. Owner: Learning Content Operations. |
| Entra and Azure managed-service regional disaster recovery | Cross-region failover and a contractual provider SLA are excluded from this non-production pilot. The application must fail closed and meet the dependency behaviors above; a future production feature must set regional DR targets. Owners: Platform Operations and Product Owner. |

Monthly evidence includes scheduled window minutes, exclusions and notice,
eligible/successful/failed one-minute observation totals, achieved availability,
incidents, actual RTO/RPO where exercised, PostgreSQL restore test, replicated
controller-audit restore/reconciliation test, and owner approval. RTO is measured
from the first failed eligible observation or declared outage, whichever is
earlier, to the first complete successful functional recovery check. RPO is
measured against the last accepted authoritative domain transaction, deployment
digest/configuration, controller transition, or immutable evidence version as
applicable.

## Prerequisite and assumption register

No prerequisite is assumed merely because it existed during planning. The named
evidence must be fresh at the stated gate.

| Prerequisite | Validation evidence and freshness | Accountable owner | Failure effect |
|---|---|---|---|
| Entra tenant, apps, scopes/roles, consent, groups, and trusted issuer | Tenant/app IDs, consent grants, exact callback/origins, role assignments, group IDs, issuer/JWKS TLS validation, and negative wrong-tenant/client tests; validate within 24 hours before pilot start and on every identity/config change. | Identity/Security Operations | Block sign-in, machine traffic, and protected delivery; no fallback tenant/credential. |
| Approved machine consumers and private networks | Bootstrap-manifest client IDs, roles, private CIDRs/peering, DNS/TLS probe, and cross-owner denials; manifest attestation at most seven days old and live probe on verification day. | Security Reviewers and Platform Operations | Block that machine consumer; browser pilot may continue if unaffected. |
| External Platform Operations bootstrap and final manifest | Reviewed plan/digest, state lineage/serial, assignments/denials, ALB/migration-policy attestations, and provider/quota/capacity attestations no older than seven days; compare live target-RG resources on every protected build. | Platform Operations | Block protected publication/promotion. Jenkins never repairs or reads Terraform state. |
| Existing AKS/ACR capacity and platform controls | AKS version/node capacity/OIDC/Workload Identity, ACR reachability/kubelet pull, Gateway API/ALB, PDB/HPA/topology, private DNS, migration guardrails, and legacy-ingress absence; live preflight within 15 minutes of promotion. | Platform Operations | Block promotion before mutation. |
| Jenkins controller and cloud `azure` | Controller/plugin digest/readiness, exact cloud/template names, service-principal scope/expiry at least 30 days, identity bindings, and denial tests; scheduled daily check plus every protected build. | Platform Operations | Quarantine protected builds; all-ref identityless validation may continue only when its template can be safely provisioned. |
| ACI provisioning and connectivity | Provision/connect one identityless validator and identity-bound publisher/deployer smoke agent; validate on credential/template change and within 24 hours before a protected release. | Platform Operations | Block affected lane with no local/fallback agent. |
| Azure Managed Redis, PostgreSQL, Key Vault/CSI, Gateway, Monitor, evidence storage | Resource IDs/private endpoints, Entra authentication, key/password fallback denial, readiness canaries, certificate/key versions, immutable evidence probe, and Monitor exporter health; live checks within 15 minutes of pilot opening and protected release. | Platform Operations with Application Operations | Do not open pilot or promote; runtime follows dependency matrix. |
| Lab providers and references | Dual-approval policy version plus complete validation no older than 24 hours; report queue and 30/36-hour alerts healthy. | Learning Content Operations and Security Reviewers | Do not publish/display the affected reference. Other learning remains available. |
| Pilot population | Frozen eligible roster/allocation, consent, non-contributor attestation, reserve order, task script, and facilitator briefing completed within seven days before first participant. | Product/UX Research | Do not begin measured pilot; no post-start denominator substitution. |
| Supported browsers and assistive technology | Exact browser/OS/AT versions and release dates, installed automation images, viewport/orientation/zoom configuration, and smoke run; capture on verification day and keep evidence no older than 30 days at release. | Product/UX Research and Application Operations | Block UI release evidence until the complete frozen matrix passes. |

## Readiness-gap traceability

| Checklist item | Governing section |
|---|---|
| CHK002 | Primary-journey outcome contract |
| CHK005, CHK029 | Stable dependency-failure contract |
| CHK006, CHK017, CHK030 | Guidance-topic states and outcomes; External-lab governance and lifecycle |
| CHK008 | Guidance-topic states and outcomes |
| CHK010, CHK028 | Learning timing, reviews, and version changes |
| CHK011 | Browser persistence-state contract |
| CHK012, CHK027 | Idempotency, concurrency, restart, and expiry; Browser persistence-state contract |
| CHK013 | Capability metadata and cache freshness |
| CHK021 | Pilot usability protocol |
| CHK022 | Reproducible one-second measurements |
| CHK023 | Approved core performance profile linked under Authority and interpretation |
| CHK024 | Universal scenario denominator policy |
| CHK032 | Rotation and partial-convergence matrix |
| CHK033, CHK034 | Accessibility behavior and browser boundary |
| CHK038 | Non-production pilot service-level decisions |
| CHK039 | Prerequisite and assumption register |
