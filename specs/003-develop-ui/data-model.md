# Data Model: Three-Service Learning UI

## Ownership and service boundaries

- The UI stores presentation state and safe unsaved form values only.
- The BFF stores browser authentication/session state only in Azure Managed
  Redis in Azure environments and Redis locally.
- The core backend stores all identity links, roadmaps, learning content,
  progress, reviews, milestones, and activity records.
- The core derives the owner from validated Entra `(tid, oid)` claims. Neither
  UI nor BFF request bodies select an owner.

## Contract and route-control records

### BffApiContract

- Canonical artifact: `specs/003-develop-ui/contracts/bff-api-v1.openapi.yaml`
- `contract_version`, `document_digest`, `generated_bff_validator_digest`
- `generated_ui_client_digest`, `validated_at`, `drift_status`

The BFF OpenAPI document is authoritative for browser routes and camelCase DTOs.
BFF route validators plus UI client/types/validators consume the same digest;
mapping contracts prove BFF DTOs conform to the separate core contract.

### CoreApiContract

- Canonical artifact: `specs/003-develop-ui/contracts/core-api-v1.openapi.yaml`
- `contract_version`, `document_digest`, `generated_client_digest`
- `validated_at`, `drift_status`: `clean | contract_invalid | generated_drift`

The core OpenAPI document is authoritative for the private core boundary. Core
route/schema conformance and BFF core-client/type generation consume the same
digest; generated output may not become authoritative and a drifted client
cannot pass validation.

### GuidanceTopicCatalog

- Canonical artifact:
  `specs/003-develop-ui/contracts/supported-guidance-topics-v1.yaml`
- `catalog_version`, ordered `topics`
- Topic: stable `id`, `name`, `category`, unique normalized `aliases`, `status`:
  `active | unavailable | retired`
- Generated runtime artifact: `config/supported-guidance-topics-v1.yaml`

Canonical IDs are unique, and every trim/case-normalized lookup key resolves to
exactly one topic; a topic's own ID, name, and alias may normalize to the same
entry but no key may resolve across entries. UI choices, BFF normalization, core
support checks, and performance fixtures consume the same catalog version.
Runtime drift or an ambiguous normalized key fails contract validation before
build. Only an unambiguous `active` entry may execute guidance; `unavailable`
and `retired` remain known entries with the distinct retry semantics and stable
codes defined by the implementation-readiness contract.

### RouteRegistration

- `service`: `core | bff`
- `module`: `foundation | roadmap | guidance | learning | progress`
- `route_prefix`, `contract_operation_id`, `required_dependencies`
- Unique: `(service, route_prefix, contract_operation_id)`

Foundation owns the shared registry and cross-cutting auth/health/capability
dependencies. Feature modules contribute registrations without importing or
editing another feature module. This is a logical design record represented in
source configuration, not a database table.

## BFF session records (Azure Managed Redis / local Redis)

### BffSession

- `session_id_hash`: key derived from the opaque cookie; raw cookie is not stored
- `tenant_id`, `object_id`: validated Entra identity reference
- `display_name`: presentation value
- `csrf_secret_hash`
- `token_cache_ciphertext`: encrypted MSAL cache for the core delegated scope
- `encryption_key_version`: Key Vault version used for token-cache ciphertext
- `created_at`, `last_seen_at`, `idle_expires_at`, `absolute_expires_at`
- `auth_flow_state`: optional state/nonce/PKCE data with short expiry
- `revoked_at`, `revocation_reason`

State: `auth_pending -> active -> expired | revoked`. Rotate the identifier on
successful callback. Authenticated user activity sets `idle_expires_at` to the
earlier of 30 minutes from activity or the immutable 8-hour absolute deadline.
Background polling does not count as activity. Redis TTL enforces the earliest
deadline. Maintain a `(tenant_id, object_id)` session index or revocation marker
so lifecycle changes revoke every session across replicas.

Maintain a second index by `encryption_key_version`. Normal key rotation
rewrites active token caches on authenticated access and retires a decrypt-only
version only after its live-session index is empty. Compromise handling revokes
and clears every session in the affected version index before that decrypting
key is removed.

The BFF session contains no roadmap, progress, answers, scores, or domain
records. Browser-safe session DTOs omit tenant/object IDs and all token data.

## Core relational entities

### EmployeeIdentity

- `id`: internal stable identifier
- `tenant_id`: validated Entra `tid`
- `object_id`: validated Entra `oid`
- `display_name`: presentation-only value
- `employee_profile_id`: optional link to existing profile
- `created_at`, `last_login_at`, `updated_at`
- `lifecycle_status`: `active | departed`
- `directory_state`: `active | disabled | deleted | unknown`
- `lifecycle_checked_at`, `departed_at`, `access_blocked_at`
- `retention_due_at`
- Unique: `(tenant_id, object_id)`

State: `active -> departed -> row deleted`. Directory errors leave the prior
state unchanged. Departure blocks access immediately; retention is due no later
than 90 days after `departed_at`. Completion is recorded only on the unlinked
retention audit/action row because retaining a completed marker on
`EmployeeIdentity` would retain the identity itself.

### IdempotencyRecord

- `id`, `actor_type`: `employee | application`, `actor_id`
- `operation`, `idempotency_key`, `canonical_request_hash`
- `status`: `processing | succeeded | retryable_failed | final_failed`
- `response_status`, `response_body`, `resource_reference`
- `attempt_count`, `execution_lease_expires_at`, `last_heartbeat_at`, `retry_after`
- `created_at`, `completed_at`, `response_expires_at`, `tombstoned_at`, `expires_at`
- Unique: `(actor_type, actor_id, operation, idempotency_key)`

Invalid requests do not consume a key. Domain transition and successful result
are established atomically. Same-hash replays return the result; another hash
is a conflict. Long-running generation uses an operation/outbox record rather
than holding a database transaction open. Processing uses a 60-second lease and
15-second heartbeat; an expired lease is recovered under row lock by reconciling
the operation/outbox/resource reference before at most one same-key re-execution.
`retryable_failed` proves that no domain mutation committed and may return to
`processing` only after `retry_after`; `final_failed` replays its established
problem and never executes again. Full response bodies remain for 30 days, then
the actor/operation/key/hash/status/result reference remains as a non-reusable
tombstone. A body-expired same-hash replay returns `409
IDEMPOTENCY_RESULT_EXPIRED`; a changed hash remains `409`. Employee tombstones
are deleted only with the departed owner graph; machine tombstones remain until
90 days after principal revocation. Processing/retryable records cannot expire,
and `expires_at` cannot precede the point where replay is structurally unable to
repeat the associated transition.

### MachinePrincipal

- `id`, `tenant_id`, `client_id`, `display_name`
- `allowed_roles`, `status`: `active | revoked`
- `created_at`, `updated_at`, `revoked_at`
- Unique: `(tenant_id, client_id)`

Machine audit records use actor type/client ID and never fabricate an employee.
Machine roadmap/progress records reference this principal directly and cannot
reference an `EmployeeIdentity` as their owner.

### DirectoryReconciliationRun

- `id`, `started_at`, `completed_at`, `checkpoint`
- `status`: `running | completed | retryable_failed`
- `checked_count`, `departed_count`, `error_count`, `last_error_code`

The checkpoint advances past a departed owner only after departure blocking and
its revocation outbox row commit in the same transaction. BFF acknowledgement
is asynchronous and cannot be lost by checkpoint advancement.

### RetentionAction

- `id`, nullable `employee_identity_id`, `due_at`, `completed_at`
- `status`: `pending | running | completed | retryable_failed`
- `operation`: `purge_owner_graph`, `evidence_disposition`: `delete | irreversibly_anonymize`
- `attempt_count`, `last_error_code`, aggregate deleted/anonymized row counts

The lifecycle role may insert or narrowly update only the scheduling fields of
an unclaimed row while marking departure; it cannot select, delete, claim, or
complete queue rows. A unique owner/action rule makes that scheduling step
idempotent. The retention role has no direct table grant. It invokes audited
security-definer `claim_due_retention_action` and `process_retention_action`
procedures that enforce eligibility, claim/complete the row, traverse the
registered owner graph, and return only minimal action/status metadata.
The owner FK is `ON DELETE SET NULL`; it is non-null while work is pending or
running and MUST be null when status becomes `completed`. In the successful
procedure transaction, all owner-linked revocation-outbox rows are deleted,
every personalized/profile/domain/idempotency row is purged, and the
`EmployeeIdentity` row is deleted before completion is committed. The completed
action retains no tenant/object/owner identifier, linkable foreign key, or
reversible owner hash. A failure rolls back both the purge and unlinking.

### SessionRevocationOutbox

- Durable core relational table written atomically with departure blocking
- `id`, `reconciliation_run_id`, `employee_identity_id`, `tenant_id`,
  `object_id`, `departed_at`
- `status`: `pending | delivering | acknowledged | deadline_breached`
- `attempt_count`, `next_attempt_at`, `last_attempt_at`, `acknowledged_at`
- `last_error_code`, `created_at`, `updated_at`, `deadline_at`
- Unique idempotency scope: `(reconciliation_run_id, employee_identity_id)`
- Dispatch index: `(status, next_attempt_at)`

Reconciliation runs every four hours, leaving delivery margin within SC-031.
The dispatcher runs at least every five minutes, sends immediately when
possible, and retries failures with bounded exponential delays of 1, 5, 15, 30,
then at most 60 minutes until BFF acknowledgement. It alerts at two elapsed
hours, pages at six, and never discards an unacknowledged row; `deadline_at`
is no later than 12 hours after departure recognition. BFF validates the
dedicated application role and atomically revokes the owner-indexed sessions
before returning an idempotent acknowledgement. No browser route, display data,
token, cookie, or reusable credential is part of the command.

### CareerRoadmap (Foundation)

- `id`, `owner_type`: `employee | application`
- `employee_identity_id`: required only for employee ownership
- `machine_principal_id`: required only for application ownership
- `profile_snapshot`, `goal`, `status`
- `ui_contract_state`: `enriched | legacy_only`
- `created_at`, `updated_at`, `content_version`
- Check: exactly one owner reference is non-null and matches `owner_type`
- Unique owner references: `(employee_identity_id, id)` when employee-owned and
  `(machine_principal_id, id)` when application-owned

Roadmap identity and ownership are Foundation schema, not US1 schema. US1
creates roadmap records through the product journey; US3 and US4 may consume a
deterministic fixture without depending on US1 implementation.
Browser/BFF journeys create only employee-owned roadmaps. App-role roadmap
generation creates only application-owned roadmaps for the validated
`MachinePrincipal`; no request field selects either owner.
Foundation backfill marks a record `enriched` only when stable milestone keys,
ordinals, and ownership can be derived deterministically. Delegated BFF calls
return only enriched schemas; a `legacy_only` record yields `409
LEGACY_RECORD_NOT_UI_COMPATIBLE` and the BFF never invents missing domain data.
Approved machine v1 operations retain the legacy schema where documented.

### RoadmapMilestone (Foundation)

- `roadmap_id`, `milestone_key`, `ordinal`, `title`, `status`
- `created_at`, `completed_at`
- Unique: `(roadmap_id, milestone_key)` and `(roadmap_id, ordinal)`

The stable `milestone_key` is the shared reference used by learning content,
learning completion, and progress review.

### ProgressCheckIn (US4)

- `id`, `actor_type`: `employee | application`
- `employee_identity_id` or `machine_principal_id`: exactly one, derived from
  the validated actor and matching the referenced roadmap owner type
- `roadmap_id`
- `notes`: bounded actor-authored text
- `completed_step_references`: ordered compatibility values as submitted
- `normalized_milestone_keys`: ordered stable keys resolved by core
- `new_goals`: ordered string array
- `created_at`, `idempotency_record_id`
- Owner/reference constraint: `(employee_identity_id, roadmap_id)` must resolve
  to the same employee-owned roadmap; `(machine_principal_id, roadmap_id)` must
  resolve to the same application-owned roadmap
- Indexes: `(employee_identity_id, roadmap_id, created_at DESC)` and
  `(machine_principal_id, roadmap_id, created_at DESC)`

A valid check-in is append-only after creation. Any compatibility-only profile
identifier in the API request is ignored for authorization. Delegated calls may
reference only the employee's roadmap; app-role calls may reference only a
roadmap owned by that exact `MachinePrincipal`.

Core validates every explicit `completed_milestone_keys` entry against the owned
roadmap and returns `422` for an unknown key. Separately, it
trim/case-normalizes legacy `completed_steps` title/skill-area values using the
existing all-matches behavior; unknown legacy values remain in the append-only
check-in but change no milestone. It persists legacy submitted references and
the union of explicit plus legacy-resolved stable keys.

### ProgressReview (US4)

- `id`, `progress_check_in_id`, `roadmap_id`, `actor_type`
- `employee_identity_id` or `machine_principal_id`: exactly one owner reference
- `prior_roadmap_snapshot`, `updated_roadmap_snapshot`
- `current_status`, ordered `gaps`, `milestone_snapshot`
- `next_action_kind`, `next_action_target`, `next_action_reason`
- `presentation`, `follow_up_prompt`, `created_at`, `contract_version`
- Unique: `(progress_check_in_id)`
- Check: review owner matches its check-in and roadmap owner
- Indexes: `(employee_identity_id, roadmap_id, created_at DESC)` and
  `(machine_principal_id, roadmap_id, created_at DESC)`

Core creates the check-in, resulting roadmap revision, milestone updates,
review, and exactly one FR-034 next action in one transaction. Latest-review
restoration selects by validated actor and roadmap, then `created_at DESC`, then
stable review ID. A foreign or missing roadmap never creates either record. New
persisted reviews always reference a check-in; a nullable `check_in` response is
retained only for legacy nonpersisted machine-response compatibility.

### Story verification fixtures (test data only)

- `owned_roadmap`: deterministic employee, roadmap, and milestone identifiers
- `published_learning_content`: deterministic content version linked to the
  owned roadmap and containing 3-5 review questions
- `foreign_owned_roadmap`: deterministic second owner used only for denial tests

Fixtures are loaded by test setup after the Foundation migration and never by a
production migration. US3 uses `owned_roadmap` plus
`published_learning_content`; US4 uses `owned_roadmap`; both remain executable
without US1 tasks. The Foundation next-action selector always understands
roadmap/milestone state. When the learning sibling head is absent, retry and
resume sources are unavailable by design, so US4 deterministically falls through
to the next incomplete milestone or completed-roadmap review without querying a
nonexistent learning table. US3 registers its learning candidate source through
the Foundation interface without becoming a dependency of US4.

### LearningSessionContent

- `id`, `content_version`, `roadmap_id`, `milestone_key`
- `title`, `objective`, `estimated_minutes` (20-30 inclusive)
- `status`: `draft | published | retired`
- `body_snapshot`, `created_at`, `published_at`, `retired_at`, `resume_until`
- `retirement_reason`, `security_critical_retirement`
- Unique: `(id, content_version)`

### SessionStep

- `id`, `session_content_id`, `content_version`, `ordinal`
- `step_type`: `reading | activity | lab | review`
- `title`, `payload`
- Unique: `(session_content_id, content_version, ordinal)`

### EmployeeLearningSession

- `id`, `employee_identity_id`, `session_content_id`, `content_version`
- `status`: `not_started | in_progress | retry_required | completed`
- `current_step_ordinal`
- `started_at`, `last_activity_at`, `completed_at`
- Unique: `(employee_identity_id, session_content_id, content_version)`

```text
not_started -> in_progress
in_progress -> retry_required (review below 80%)
retry_required -> in_progress (retry starts)
in_progress | retry_required -> completed (review at least 80%)
```

Start/resume is idempotent. Core derives the cursor from the lowest incomplete
step, never a UI/BFF-provided ordinal. Start pins the content, ordered step,
question, and lab-reference versions. Normal retirement permits pinned-session
resume for 30 days; security-critical retirement blocks resume/submission
immediately while preserving saved history. No deployment mixes content or
question versions inside an active aggregate.

### StepProgress

- `employee_learning_session_id`, `session_step_id`
- `status`: `pending | completed`
- `completed_at`
- Unique: `(employee_learning_session_id, session_step_id)`

### HandsOnLabReference

- Shared foundational entity consumed by guidance and learning sessions; it is
  not owned by the learning-session aggregate.
- `id`, `content_version`, `provider`, `objective`, `prerequisites`
- `provider_policy_version`, `lab_required`, `omission_reason`
- `classifier_object_id`, `classified_at`, `applicability_policy_version`
- `omission_explanation` (20-500 characters when omission is allowed)
- `estimated_minutes`, `cost_status`: `free | paid | subscription | unknown`
- `destination_url`: HTTPS only
- `availability_state`: `active | reported | unavailable | retired`
- `consecutive_validation_failures`, `last_verified_at`, `row_version`
- `retirement_reason`, `retired_at`, `created_at`, `updated_at`

Opening a lab records activity but never implies completion. Learning Content
Operations owns applicability classification per content version; command,
configuration, deployment, troubleshooting, or running-system observation is
lab-required, and borderline objectives default to required. Only orientation,
conceptual comparison, or review-only objectives may carry a recorded omission.
Retirement is immutable for that reference version; reinstatement creates a new
approved and fully revalidated version.

### LabLinkReport

- `id`, `lab_reference_id`, `employee_identity_id`
- `reason`: `unavailable | unsuitable | cost_mismatch | other`
- `comment`: optional bounded text
- `created_at`

Reports are append-only.
The first report atomically changes `active` to `reported` and schedules an out-
of-cycle validation within 15 minutes. Row-version checks keep concurrent report
and validation transitions from overwriting each other; validation success never
deletes reports or silently clears the reported state.

### LabProviderApproval

- `id`, `policy_version`, `provider`, `approved_domains`
- `learning_owner_approver`, `security_approver`: distinct human Entra object IDs
- `learning_owner_group_id`, `security_reviewer_group_id`: policy-time group IDs
- `reason`, `audit_reference`
- `effective_at`, `retired_at`
- Unique: `(policy_version, provider)`

Both approvers must be active members of their configured groups at approval
time. One identity cannot satisfy both roles, including when it belongs to both
groups. Group membership evidence and approver IDs are retained with the policy
audit record, not exposed to learners.

### LabValidationAttempt

- `id`, `lab_reference_id`, `policy_version`, `attempted_at`
- `result`: `success | retryable_failure | final_failure`
- `status_code`, `redirect_domains`, `redirect_count`, `duration_ms`, `error_code`
- `prior_state`, `new_state`, `validator_identity_id`

Validation attempts contain no learner identity. Successful validation resets
the consecutive-failure counter; three consecutive scheduled failures make the
reference unavailable. At most five HTTPS redirects are accepted; a loop,
downgrade, unapproved/private destination, or excess hop is final. Provider-
policy removal immediately makes affected references unavailable, and a retired
reference cannot reactivate without a new version.

### ReviewQuestion

- `id`, `session_content_id`, `content_version`, `ordinal`
- `prompt`, `choices`
- `correct_answer_key`, `explanation`: core-only fields
- Published-session constraint: 3-5 questions

### ReviewAttempt

- `id`, `employee_learning_session_id`, `attempt_number`
- `question_snapshot_version`
- `status`: `in_progress | submitted`
- `correct_count`, `question_count`, `score_percent`, `passed`
- `started_at`, `submitted_at`
- Unique: `(employee_learning_session_id, attempt_number)`

Attempts are immutable after submit. Core calculates score and pass (`>=80%`)
inside the completion transaction. An in-progress response requires `started_at`
and null score/pass/submission time; a submitted response requires non-null
score, pass result, and `submitted_at`.
Only one attempt may be in progress. A failed attempt is followed by missed-
concept review and a new full attempt over the same pinned 3-5 question IDs;
answers are not copied and order remains stable. There is no lifetime attempt
limit, but no more than five new attempts may start in 60 minutes. History is
chronological and derives latest/highest labels; the first passing attempt
permanently establishes completion and later scored attempts are prohibited.

### ReviewAnswer

- `review_attempt_id`, `review_question_id`
- `submitted_answer_key`, `is_correct`, `answered_at`
- Unique: `(review_attempt_id, review_question_id)`

Correctness/explanation is returned only for the answered question. Unanswered
keys never cross the core boundary. Review restoration returns the employee's
submitted answer, correctness, explanation, and `answered_at` for each answered
question, but never returns an authoritative correct key for an unanswered
question.

### LearningMilestoneCompletion

- `id`, `employee_identity_id`, `roadmap_id`, `milestone_key`
- `source_learning_session_id`, `completed_at`
- Unique: `(employee_identity_id, roadmap_id, milestone_key)`

### LearningActivityEvent

- `id`, `employee_identity_id`, `event_type`
- `roadmap_id`, `learning_session_id`, `content_version`
- `request_id`, `trace_id`, `occurred_at`, `metadata`

Metadata excludes tokens, raw answers, correct keys, lab query strings, and
direct personal identifiers.

## Atomic operations

- Start/resume: owner-scoped get-or-create.
- Step completion: idempotent upsert and next incomplete cursor.
- Answer: idempotent per attempt/question; finalized attempts reject changes.
- Submit review: finalize score, update session, create milestone completion,
  record activity, and calculate exactly one next action in one transaction.
- Lab report: append report without mutating learning completion.
- Progress check-in: atomically append the owner-scoped check-in, apply valid
  milestone updates, snapshot the roadmap revision, persist the review, and
  calculate exactly one next action.
- Retryable mutation: establish the idempotency result with the domain change.
- Departure: atomically block identity access, insert or narrowly update an
  unclaimed retention schedule, and enqueue durable BFF session revocation
  before reconciliation checkpoint advancement.
- Retention: delete the identity and complete personalized owner graph, remove
  every direct/indirect owner link, and only then irreversibly anonymize eligible
  non-linkable security evidence or retain non-reidentifiable aggregate telemetry.
- Deployment rollback: append a compensating action before each mutation and
  execute completed reversible entries in descending sequence on failure.

## Migration rules

- Introduce Alembic and baseline existing profile/roadmap/check-in tables.
- Add employee/application owner links plus foundational roadmap/milestone
  identity, backfill only verified mappings, then enforce exactly-one owner
  constraints before any story migration.
- Foundation revision `006_owned_roadmaps` is the common parent. Revision
  `007_learning_sessions` has branch label `learning`; revision
  `008_owned_progress` has branch label `progress`; both declare
  `down_revision = 006_owned_roadmaps` and neither depends on the other.
- Revision `009_merge_learning_progress` is a merge-only revision with
  `down_revision = (007_learning_sessions, 008_owned_progress)`. Combined
  releases target `009_merge_learning_progress`; targeted verification/upgrades
  use `learning@head` or `progress@head`, never ambiguous bare `head` while both
  sibling heads exist.
- Revision `004_identity_lifecycle_idempotency` creates the audited
  security-definer retention relationship registry and registers only its
  baseline owner tables. Revisions `005_lab_references`, `006_owned_roadmaps`,
  `007_learning_sessions`, and `008_owned_progress` extend that registry only
  for the owner-linked tables they introduce; no procedure references a table
  before the table exists.
- All story migrations are expand-only. Fixture loading is separate from
  migrations, and only the migration runner records applied heads.
- Unowned legacy records remain available only through preserved legacy behavior.
- New `/api/v1` personalized reads require validated owner identity.
- Only the dedicated migration Job runs Alembic. Relational access is limited to
  mutually denied core application-DML; lifecycle known-identity/status/
  reconciliation/outbox plus unclaimed-retention scheduling; retention audited
  claim/process-due procedure-only with no direct queue or learning-row grants;
  and migration DDL/backfill roles. BFF/UI and Jenkins deployer have no
  PostgreSQL access.
- BFF Redis keys use a separate namespace and lifecycle; no domain migration is
  coupled to BFF deployment.
- Backfill active lifecycle status before enforcing retention constraints.
- Mark deterministically owned/keyed roadmap records `enriched`; retain any
  unverifiable record as `legacy_only` for machine compatibility and reject it
  from delegated BFF 200 responses with `LEGACY_RECORD_NOT_UI_COMPATIBLE`.
- Owner purge includes owner-scoped idempotency and session-revocation outbox
  rows. Any retained security event contains only non-linkable outcome/timing/
  aggregate-count fields; it has no tenant/object/owner identifier, foreign-key
  path, or reversible owner hash.
- Backup retention remains within the 90-day departure ceiling; restored data
  runs due retention before personalized access is enabled.

## Delivery evidence metadata (Azure Storage control plane)

Delivery evidence is not application-domain data and is not stored in core
PostgreSQL. Immutable blob paths encode `environment`, `build_id`, `stage`, and
`artifact`. Each blob records creation time, content hash, evidence class, and
retention state without credentials or learner identity. These are logical
control-plane records represented by blob metadata/manifests, not core tables.

### EvidenceSet

- `environment`, `build_id`, `source_revision`, `change_plan_hash`
- `required_artifact_classes`, `accepted_artifact_classes`
- `validation_status`: `pending | valid | rejected`
- `immutability_status`: `pending | locked | legal_hold | deletion_eligible | deleted`
- `promotion_gate_status`: `closed | open | consumed`
- Unique: `(environment, build_id)`

The gate opens only when every required pre-mutation artifact is present, its
hash and prohibited-content validation pass, and its accepted blob version has
a locked 90-day immutability policy. An unavailable or rejected write keeps the
gate closed.

### EvidenceArtifact

- `environment`, `build_id`, `stage`, `artifact`, `blob_version_id`
- `content_hash`, `evidence_class`, `created_at`, `immutable_until`
- `validation_status`, `contains_prohibited_content`: always false when accepted
- Unique immutable path: `(environment, build_id, stage, artifact)`

Creation uses `If-None-Match: *`; overwrite, tag mutation, and deletion are not
valid artifact transitions.

An incident hold records `evidence_set_id`, application `hold_id`, the complete
target `blob_version_id` inventory, `owner_object_id`, `reason`,
`incident_reference`, `started_at`, `expires_at`, `released_at`, operation
status (`applying | active | clearing | reconciling | released`), and audit
timestamps. Azure stores a boolean version-level legal hold on each target;
tags are not used for version scope. Each expiry extension appends actor, prior
expiry, new expiry, reason, and transition time. The locked `immutable_until` remains
fixed at creation plus 90 days and is never shortened or extended by a hold.
Normal state is `locked -> deletion_eligible -> deleted`; a hold adds
`legal_hold` until authorized release or expiry clears every target hold. Set/
clear is logically all-or-fail: a partial Azure operation enters `reconciling`,
alerts, and retries, and cannot report `active`/`released` until the inventory
matches. Clearing before
`immutable_until` leaves the version locked; clearing after it makes deletion
eligible. `expires_at` cannot exceed creation plus 180 days. Only the authorized
hold-management Entra group may create, extend, or release a request and mutate
the separate audited control metadata; it has no direct Azure blob-version hold
permission. An hourly dedicated reconciler reads only this hold-control
inventory and is the sole principal that applies or clears the exact enumerated
version holds and retries partial operations. Its identity cannot read/list/
delete blob content or mutate the fixed time-based policy.

### PlatformBootstrapManifest (reviewed configuration artifact)

- `schema_version`, `environment`, `generated_at`, `attestations_expires_at`
- `tenant_id`, `subscription_id`, `resource_group_id`
- `terraform_state_lineage`, `terraform_state_serial`, `configuration_digest`
- `configuration_digest_policy_version`, `configuration_digest_input_count`
- resource IDs for AKS, ACR, Key Vault, Redis, PostgreSQL, AGC, DNS, evidence
  storage, and all workload/delivery identities
- ALB Controller version/identity/readiness attestation
- migration namespace/RBAC/admission-policy/binding UID, resource-version, and
  readiness/denial attestation
- bootstrap operator/consent-approver object IDs, PIM assignment IDs/scopes,
  activation/expiry, and negative privilege-check results
- `browser_origin`, `private_machine_origin`, approved private network IDs
- provider-registration and quota/capacity attestation results

Only the external Platform Operations finalization command emits this non-secret
artifact after all Terraform, principals, denial checks, ALB Controller, and
migration guardrails are live; the bootstrap/apply commands never emit it. Code
review accepts it with the infrastructure change. The identityless Jenkins stage
validates schema and repository digest. A protected deployer stage compares
target-resource-group IDs/tags with live resources without reading Terraform
state. Missing fields, a configuration mismatch, or an attestation older than
seven days makes the manifest stale and blocks delivery.

The configuration digest is computed from the canonical versioned input policy,
not the whole Git tree. Its ordered stream contains normalized relative path,
executable mode, byte length, and content SHA-256 for every allowlisted regular
file. The policy includes itself and excludes this emitted manifest, local/
secret/runtime/VCS/Terraform-state artifacts, eliminating self-reference while
detecting matching add/remove/rename/mode/content drift.

### DeliveryControlIdentity (configuration inventory)

- `principal_object_id`, `principal_type`: `jenkins_local_user | entra_group`
- `role`: `jenkins_credential_manager | evidence_hold_manager`
- `scope_resource_id`, `allowed_operations`, `denied_operations`
- `configured_at`, `last_verified_at`, `status`: `active | quarantined | revoked`

The Jenkins credential manager may update only the stable cloud `azure`
credential entry through the localhost API; it cannot read other credentials,
configure jobs, or run builds. The evidence hold-manager principal is the
configured Evidence Hold Managers Entra group; its custom role may
create, extend, or release hold metadata only and cannot read evidence, create
artifacts, change base retention, or delete blobs.

### ProvisioningCredentialObservation

- `credential_id_hash`, `observed_at`, `expires_at`, `days_remaining`
- `status`: `healthy | rotation_due | quarantined | compromised | retired`
- `validator_template_check`, `publisher_template_check`,
  `deployer_template_check`, `quarantine_reason`

Missing/unreadable expiry or fewer than 30 valid days sets `quarantined` and
blocks new protected-branch Azure agents. Successful replacement checks for the
identityless validator and both privileged templates are required before normal
quarantine clears. Compromise revokes first and remains quarantined until all
three declared template checks pass.

### ControllerAuditAttempt

- `build_id`, `source_revision`, `started_at`, `completed_at`
- `result`: `pending | succeeded | failed | aborted | aborted_recovered`
- `lifecycle_event`: `started | agent_requested | agent_connected | evidence_active`
- `failed_stage`, `terminal_reason`, `authoritative_evidence_path`
- append-only event timestamps and one terminal-state constraint

The trusted controller state is a Jenkins `RunAction` created by an
administrator-installed, digest-verified `RunListener` plugin with
`result=pending`
before any executor, node, agent, checkout, or workspace. Repository code cannot
omit, create, replace, suppress, or finalize it. It is authoritative for controller lifecycle state but is
not authoritative delivery evidence. Every exit path changes `result` exactly
once from `pending` to a terminal value. When an authenticated agent becomes
available, the audit is copied into its EvidenceSet; otherwise the controller
record is access-restricted and retained for 90 days.

Before an ACI request, every accepted lifecycle transition is fsynced to both
the Jenkins run record and a host-managed append-only replicated controller-audit
store. Loss or divergence of either copy disables protected scheduling. The
replica provides zero accepted-transition RPO and a four-hour recovery target;
restart or controller-disk recovery reconciles build IDs against queue/run,
source-webhook, and Azure-evidence records, finalizes safe nonterminal orphans as
`aborted_recovered`, and keeps protected delivery blocked until every
post-mutation orphan has verified rollback or an approved terminal recovery.

### DeploymentMutationJournalEntry

- `environment`, `build_id`, `sequence`, `service`
- `previous_digest`, `intended_digest`, `previous_configuration_hash`
- `compatibility_result`, `mutation`, `compensating_action`
- `mutation_type`: `schema_expand | image_rollout | configuration | routing`
- `schema_heads_before`, `schema_heads_after`, `evidence_set_id`
- `reversible`, `recovery_plan_reference`
- `status`: `planned | applied | compensated | failed | operator_recovery`
- `applied_at`, `compensated_at`, `error_code`
- Unique: `(environment, build_id, sequence)`

Automatic rollback processes applied reversible entries in descending sequence.
An irreversible schema entry can transition to `applied` only after contract
compatibility and evidence gates pass and an operator recovery reference is
recorded. It has no compensating SQL. If migration fails, no core rollout entry
may be applied and the journal enters `operator_recovery`; if a later core
rollout fails, reversible image/configuration entries are compensated while the
expanded schema heads remain. Destructive database migration reversal is
prohibited.

## Runtime compatibility and operational observations

### InterfaceCapability

- `service`, `contract_name`, `active_version`, `accepted_peer_range`
- `enabled_mutations`, `service_version`, `image_digest`, `observed_at`
- `local_received_at`, `cache_age_seconds`, `decision`: `read_only | write_enabled | blocked`

A state-changing request is enabled only when UI/BFF and BFF/core ranges both
intersect and the requested mutation is advertised. Missing or malformed
capabilities are incompatible. Capability records are runtime responses and
release-manifest evidence, not durable learner data. Each boundary single-flight
refreshes at 45 seconds; write decisions require a complete compatible response
received within 60 seconds. At most five-minute-old metadata may support labelled
read-only availability and diagnostics, never mutation. Missing, malformed,
unavailable, or stale write metadata blocks before idempotency.

### WorkloadScalingProfile

- `service`: `ui | bff | core`
- application-container resources by service:
  - `ui`: CPU request/limit `50m`/`250m`, memory request/limit `64Mi`/`128Mi`
  - `bff`: CPU request/limit `100m`/`500m`, memory request/limit `256Mi`/`512Mi`
  - `core`: CPU request/limit `250m`/`1000m`, memory request/limit `512Mi`/`1Gi`
- `min_replicas`: 2, `max_replicas`: 4, `cpu_target_percent`: 70
- `pdb_max_unavailable`: 1, `topology_max_skew`: 1
- `topology_key`: `kubernetes.io/hostname`, `when_unsatisfiable`: `ScheduleAnyway`

The HPA CPU percentage is calculated against the named service's application-
container CPU request. Platform sidecars have separate profiles and cannot
replace or dilute these required values.

### PerformanceObservation

- `journey`, `operation`, `sample_id`
- `validation_event_at`, `guidance_visible_at`
- `fetch_resolved_at`, recorded after the complete response body is parsed and
  validated
- `accessible_result_ready_at`
- `core_request_started_at`, `core_response_completed_at`
- derived `validation_ms`, `result_render_ms`, `core_execution_ms`, `success`
- SC-043 evidence identity: `performance_profile_id` (`profileId`),
  `full_profile_digest` (`profileDigest`), `fixture_set_digest`
  (`fixtureDigest`), `bff_contract_digest` (`bffContractDigest`),
  `core_contract_digest` (`coreContractDigest`), `mapper_digest`
  (`mapperDigest`), `case_id` (`caseId`), and `scenario`
- SC-043 execution identity: `worker_index` (`workerIndex`),
  `request_ordinal` (`requestOrdinal`), `environment`, and
  `core_image_digest` (`coreImageDigest`)
- SC-043 measurement: `monotonic_duration_ms` (`monotonicDurationMs`),
  `raw_outcome` (`rawOutcome`), `percentile_value_ms`
  (`percentileValueMs`), `threshold_passed` (`thresholdPassed`), and
  `calculated_nearest_rank_p95_ms` (`calculatedNearestRankP95Ms`)
- `warmup`; warm-up observations are retained but excluded from measured
  denominators and percentile calculations

Validation checks require every supported local-error sample at or below 1,000
ms. Result checks require at least 95% of successful roadmap and guidance samples
at or below 1,000 ms from `career.result.fetch-resolved`. Core execution is
measured independently using the versioned SC-043 workload profile. Every
measured SC-043 observation MUST populate all fields in the profile's
`requiredEvidenceFields` list; the parenthesized JSON names above are the
serialized evidence keys and the snake-case names are the model vocabulary.

### CertificateRotationObservation

- `rotation_id`, `replica_id`, `certificate_version`, `observed_at`
- `fresh_sign_in_callback`: `passed | failed`
- `existing_session_token_refresh`: `passed | failed`
- `core_token_acquisition`: `passed | failed`

Normal retirement is ready only when every current BFF replica reports all three
checks as passed for the replacement version.

### SafeTelemetryEnvelope

- `timestamp`, `environment`, `service_name`, `service_version`, `image_digest`
- `trace_id`, `route_class`, `duration_ms`, `outcome`, `dependency_outcome`
- `readiness`, `replica_count`, `restart_count`, `hpa_at_max`

Tokens, request/response bodies, learner identifiers, raw answers, and answer
keys are prohibited.

### OperationalAlertProfile (`operational-alert-profile-v1`)

- readiness: `ready_replicas = 0` for 5 consecutive minutes
- error rate: `5xx_ratio >= 5%` with at least 20 requests in each of 2
  consecutive 5-minute windows
- latency p95 under the same sample/window gate: UI static `> 2s`, roadmap
  `> 30s`, guidance `> 10s`, other personalized API `> 5s`
- restart loop: at least 3 container restarts in any 10-minute window
- HPA saturation: 4 replicas and average CPU at or above 70% for 15 consecutive
  minutes; escalate from warning to page at 30 minutes
- session revocation: oldest unacknowledged outbox row alerts at 2 hours and
  pages at 6 hours; a 12-hour deadline breach is critical
- certificate expiry: public gateway and private-core TLS certificates warn at
  30, 14, and 7 days and page Platform Operations critically below 48 hours
- directory reconciliation: no successful run for 6 hours warns Application
  and Platform Operations; 8 hours pages both
- active lab validation: age above 30 hours warns Learning Content Operations;
  age above 36 hours pages Learning Content and Application Operations; three
  consecutive failures or an unavailable destination alerts Learning Content
  Operations immediately
- routing: readiness, restart, and second-window error/latency breaches page
  Application Operations; HPA warns/pages both Application and Platform
  Operations; gateway, cluster, or managed-dependency attribution also routes
  to Platform Operations

Every alert carries `environment`, `service_name`, `route_class`, breached
threshold/window, first-observed time, and attribution. Acknowledgement and
escalation state is retained as operational telemetry, not learner data.
