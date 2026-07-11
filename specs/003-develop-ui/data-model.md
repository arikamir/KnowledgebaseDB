# Data Model: Three-Service Learning UI

## Ownership and service boundaries

- The UI stores presentation state and safe unsaved form values only.
- The BFF stores browser authentication/session state only in Azure Managed
  Redis in Azure environments and Redis locally.
- The core backend stores all identity links, roadmaps, learning content,
  progress, reviews, milestones, and activity records.
- The core derives the owner from validated Entra `(tid, oid)` claims. Neither
  UI nor BFF request bodies select an owner.

## BFF session records (Azure Managed Redis / local Redis)

### BffSession

- `session_id_hash`: key derived from the opaque cookie; raw cookie is not stored
- `tenant_id`, `object_id`: validated Entra identity reference
- `display_name`: presentation value
- `csrf_secret_hash`
- `token_cache_ciphertext`: encrypted MSAL cache for the core delegated scope
- `created_at`, `last_seen_at`, `idle_expires_at`, `absolute_expires_at`
- `auth_flow_state`: optional state/nonce/PKCE data with short expiry
- `revoked_at`, `revocation_reason`

State: `auth_pending -> active -> expired | revoked`. Rotate the identifier on
successful callback. Authenticated user activity sets `idle_expires_at` to the
earlier of 30 minutes from activity or the immutable 8-hour absolute deadline.
Background polling does not count as activity. Redis TTL enforces the earliest
deadline. Maintain a `(tenant_id, object_id)` session index or revocation marker
so lifecycle changes revoke every session across replicas.

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
- `lifecycle_status`: `active | departed | anonymized`
- `directory_state`: `active | disabled | deleted | unknown`
- `lifecycle_checked_at`, `departed_at`, `access_blocked_at`
- `retention_due_at`, `retention_completed_at`
- Unique: `(tenant_id, object_id)`

State: `active -> departed -> anonymized`. Directory errors leave the prior
state unchanged. Departure blocks access immediately; retention is due no later
than 90 days after `departed_at`.

### IdempotencyRecord

- `id`, `actor_type`: `employee | application`, `actor_id`
- `operation`, `idempotency_key`, `canonical_request_hash`
- `status`: `processing | succeeded | retryable_failed | final_failed`
- `response_status`, `response_body`, `resource_reference`
- `created_at`, `completed_at`, `expires_at`
- Unique: `(actor_type, actor_id, operation, idempotency_key)`

Invalid requests do not consume a key. Domain transition and successful result
are established atomically. Same-hash replays return the result; another hash
is a conflict. Long-running generation uses an operation/outbox record rather
than holding a database transaction open. `expires_at` cannot precede the point
where replay is structurally unable to repeat the associated transition.

### MachinePrincipal

- `id`, `tenant_id`, `client_id`, `display_name`
- `allowed_roles`, `status`: `active | revoked`
- `created_at`, `updated_at`, `revoked_at`
- Unique: `(tenant_id, client_id)`

Machine audit records use actor type/client ID and never fabricate an employee.

### DirectoryReconciliationRun

- `id`, `started_at`, `completed_at`, `checkpoint`
- `status`: `running | completed | retryable_failed`
- `checked_count`, `departed_count`, `error_count`, `last_error_code`

### RetentionAction

- `id`, `employee_identity_id`, `due_at`, `completed_at`
- `status`: `pending | running | completed | retryable_failed`
- `action`: `delete | anonymize`, `attempt_count`, `last_error_code`

### CareerRoadmap (Foundation)

- `id`, `employee_identity_id`, `profile_snapshot`, `goal`, `status`
- `created_at`, `updated_at`, `content_version`
- Unique owner reference: `(employee_identity_id, id)`

Roadmap identity and ownership are Foundation schema, not US1 schema. US1
creates roadmap records through the product journey; US3 and US4 may consume a
deterministic fixture without depending on US1 implementation.

### RoadmapMilestone (Foundation)

- `roadmap_id`, `milestone_key`, `ordinal`, `title`, `status`
- `created_at`, `completed_at`
- Unique: `(roadmap_id, milestone_key)` and `(roadmap_id, ordinal)`

The stable `milestone_key` is the shared reference used by learning content,
learning completion, and progress review.

### Story verification fixtures (test data only)

- `owned_roadmap`: deterministic employee, roadmap, and milestone identifiers
- `published_learning_content`: deterministic content version linked to the
  owned roadmap and containing 3-5 review questions
- `foreign_owned_roadmap`: deterministic second owner used only for denial tests

Fixtures are loaded by test setup after the Foundation migration and never by a
production migration. US3 uses `owned_roadmap` plus
`published_learning_content`; US4 uses `owned_roadmap`; both remain executable
without US1 tasks.

### LearningSessionContent

- `id`, `content_version`, `roadmap_id`, `milestone_key`
- `title`, `objective`, `estimated_minutes` (20-30 inclusive)
- `status`: `draft | published | retired`
- `body_snapshot`, `created_at`, `published_at`, `retired_at`
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
step, never a UI/BFF-provided ordinal.

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
- `estimated_minutes`, `cost_status`: `free | paid | subscription | unknown`
- `destination_url`: HTTPS only
- `availability_state`: `active | reported | unavailable | retired`
- `consecutive_validation_failures`, `last_verified_at`, `created_at`, `updated_at`

Opening a lab records activity but never implies completion.

### LabLinkReport

- `id`, `lab_reference_id`, `employee_identity_id`
- `reason`: `unavailable | unsuitable | cost_mismatch | other`
- `comment`: optional bounded text
- `created_at`

Reports are append-only.

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
- `status_code`, `redirect_domains`, `duration_ms`, `error_code`

Validation attempts contain no learner identity. Successful validation resets
the consecutive-failure counter; three consecutive scheduled failures make the
reference unavailable.

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
inside the completion transaction.

### ReviewAnswer

- `review_attempt_id`, `review_question_id`
- `submitted_answer_key`, `is_correct`, `answered_at`
- Unique: `(review_attempt_id, review_question_id)`

Correctness/explanation is returned only for the answered question. Unanswered
keys never cross the core boundary.

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
- Retryable mutation: establish the idempotency result with the domain change.
- Departure: block identity access and schedule retention before cleanup.
- Retention: delete/anonymize the owner graph and unlink aggregate telemetry.
- Deployment rollback: append a compensating action before each mutation and
  execute completed reversible entries in descending sequence on failure.

## Migration rules

- Introduce Alembic and baseline existing profile/roadmap/check-in tables.
- Add nullable owner links, foundational roadmap/milestone identity, backfill
  only verified mappings, then add constraints before any story migration.
- Keep one linear Alembic chain: story migrations depend on the Foundation head,
  never on another story task. Fixture loading is separate from migrations.
- Unowned legacy records remain available only through preserved legacy behavior.
- New `/api/v1` personalized reads require validated owner identity.
- Only core runs migrations or accesses relational storage.
- BFF Redis keys use a separate namespace and lifecycle; no domain migration is
  coupled to BFF deployment.
- Backfill active lifecycle status before enforcing retention constraints.
- Owner purge includes owner-scoped idempotency records and linkable audit data.
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
- `immutability_status`: `pending | locked | hold_extended | expired`
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

An incident hold records `evidence_set_id`, `owner_object_id`, `reason`,
`incident_reference`, `started_at`, `expires_at`, `released_at`, and audit
timestamps. Normal state is `retained -> expired -> deleted`; a hold changes
`retained -> held -> released | expired -> deleted`. `expires_at` cannot extend
the evidence beyond the 180-day maximum. Only the authorized hold-management
Entra group role assignment may mutate hold metadata.

### DeliveryControlIdentity (configuration inventory)

- `principal_object_id`, `principal_type`: `jenkins_local_user | entra_group`
- `role`: `jenkins_credential_manager | evidence_hold_manager`
- `scope_resource_id`, `allowed_operations`, `denied_operations`
- `configured_at`, `last_verified_at`, `status`: `active | quarantined | revoked`

The Jenkins credential manager may update only the stable cloud `azure`
credential entry through the localhost API; it cannot read other credentials,
configure jobs, or run builds. The evidence hold-manager principal is the
configured Evidence Hold Managers Entra group; its custom role may
create/release hold metadata only and cannot read evidence, create artifacts,
change base retention, or delete blobs.

### ProvisioningCredentialObservation

- `credential_id_hash`, `observed_at`, `expires_at`, `days_remaining`
- `status`: `healthy | rotation_due | quarantined | compromised | retired`
- `publisher_template_check`, `deployer_template_check`, `quarantine_reason`

Missing/unreadable expiry or fewer than 30 valid days sets `quarantined` and
blocks new protected-branch Azure agents. Successful replacement checks for both
templates are required before normal quarantine clears. Compromise revokes first
and remains quarantined until both checks pass.

### ControllerAuditAttempt

- `build_id`, `source_revision`, `started_at`, `completed_at`
- `state`: `started | agent_requested | agent_connected | evidence_active | succeeded | failed | aborted`
- `failed_stage`, `terminal_reason`, `authoritative_evidence_path`
- append-only event timestamps and one terminal-state constraint

Every exit path reaches exactly one terminal state. When an authenticated agent
becomes available, the audit is copied into its EvidenceSet; otherwise the
minimal non-authoritative controller record is access-restricted and retained
for 90 days.

### DeploymentMutationJournalEntry

- `environment`, `build_id`, `sequence`, `service`
- `previous_digest`, `intended_digest`, `previous_configuration_hash`
- `compatibility_result`, `mutation`, `compensating_action`
- `reversible`, `status`: `planned | applied | compensated | failed`
- `applied_at`, `compensated_at`, `error_code`
- Unique: `(environment, build_id, sequence)`

Automatic rollback processes applied reversible entries in descending sequence.
An irreversible entry cannot transition to `applied` without a separately
approved recovery plan; destructive database migration reversal is prohibited.

## Runtime compatibility and operational observations

### InterfaceCapability

- `service`, `contract_name`, `active_version`, `accepted_peer_range`
- `enabled_mutations`, `service_version`, `image_digest`, `observed_at`

A state-changing request is enabled only when UI/BFF and BFF/core ranges both
intersect and the requested mutation is advertised. Missing or malformed
capabilities are incompatible. Capability records are runtime responses and
release-manifest evidence, not durable learner data.

### WorkloadScalingProfile

- `service`: `ui | bff | core`
- `min_replicas`: 2, `max_replicas`: 4, `cpu_target_percent`: 70
- `pdb_max_unavailable`: 1, `topology_max_skew`: 1
- `topology_key`: `kubernetes.io/hostname`, `when_unsatisfiable`: `ScheduleAnyway`

### PerformanceObservation

- `journey`, `operation`, `sample_id`
- `validation_event_at`, `guidance_visible_at`
- `fetch_resolved_at`, recorded after the complete response body is parsed and
  validated
- `accessible_result_ready_at`
- `core_request_started_at`, `core_response_completed_at`
- derived `validation_ms`, `result_render_ms`, `core_execution_ms`, `success`
- `performance_profile_version`, `fixture_set_digest`, `warmup`, `outcome`

Validation checks require every supported local-error sample at or below 1,000
ms. Result checks require at least 95% of successful roadmap and guidance samples
at or below 1,000 ms from `career.result.fetch-resolved`. Core execution is
measured independently using the versioned SC-043 workload profile.

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
keys are prohibited. Alerts derive from five-minute readiness loss, sustained
5xx/latency breaches, restart loops, and sustained HPA maximum saturation.
