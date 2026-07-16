# Implementation Readiness Checklist: DevOps Career Agent UI

**Purpose**: Formal pre-implementation gate for the completeness, clarity, consistency, measurability, and traceability of the full UI, BFF, core, and Jenkins/Azure delivery requirements.
**Created**: 2026-07-11
**Feature**: [DevOps Career Agent UI specification](../spec.md)

**Note**: This checklist evaluates the quality of the written requirements, not the implemented system. Every item should be resolved from the specification and its design artifacts before implementation begins.

## Requirement Completeness

- [x] CHK001 Are the required and optional fields, data types, constraints, defaults, and authoritative sources explicitly defined for roadmap, guidance-profile, learning-session, review, and progress-check-in inputs? [Completeness, Gap, Spec §FR-002–FR-003, §FR-006, §FR-008, §FR-022–FR-031]
- [x] CHK002 Are success, validation/not-found, authentication expiry, compatibility failure, dependency outage, retry, navigation, refresh, and interruption requirements documented for each of the four primary journeys, with intentional exclusions identified? [Completeness, Gap, Spec §User Stories 1–4, §Edge Cases, §FR-010–FR-012, §FR-021, §FR-039]
- [x] CHK003 Are the responsibilities and prohibited responsibilities of the UI, BFF, and core defined for every personalized operation, machine operation, health interface, business rule, and stored data category? [Completeness, Spec §FR-035–FR-047, Plan §Service and API boundaries, Plan §Data ownership]
- [x] CHK004 Is the BFF session lifecycle complete across creation, identifier rotation, activity refresh, idle expiry, absolute expiry, logout, employee departure, replica changes, Redis failure, and recovery, including what fails closed and what saved data survives? [Completeness, Gap, Spec §FR-021, §FR-053–FR-061, Data Model §BffSession, Auth Contract §Session revocation and key rotation]
- [x] CHK005 Are dependency-failure requirements documented for the gateway, UI, BFF, core, Redis, PostgreSQL, Entra/JWKS, Key Vault, ACR, AKS, Azure Monitor, lab providers, Jenkins controller, ACI provisioning, and evidence storage? [Completeness, Gap, Spec §Edge Cases, §FR-048–FR-052, Plan §Azure topology, Plan §Jenkins delivery strategy]
- [x] CHK006 Are the initial empty allowlist, lab applicability, dual approval, publication, redirect validation, periodic revalidation, throttling, unavailability, recovery, reporting, and retirement requirements complete for external lab references? [Completeness, Spec §FR-025–FR-027, §FR-063, §FR-065–FR-066, SC-013, SC-037–SC-038]
- [x] CHK007 Are protected references, pull-request behavior, manual recovery/rebuild authority, stage transitions, agent trust classes, environment locks, required artifacts, notifications, and terminal outcomes explicitly defined for every Jenkins delivery path? [Completeness, Gap, Spec §FR-064, §FR-067, §FR-069–FR-070, Jenkins Contract §Trigger and reference policy, §Required stage state machine]

## Requirement Clarity

- [x] CHK008 Is a “supported topic” defined well enough to distinguish valid, unavailable, and uninterpretable guidance topics and their required outcomes? [Ambiguity, Spec §User Story 2, §FR-006–FR-007, §FR-012]
- [x] CHK009 Is the exactly-one recommended-next-action rule defined for ties, no eligible action, unavailable content, conflicting roadmap signals, and the progress story’s plural “next actions” wording? [Ambiguity, Conflict, Spec §User Story 4, §FR-009, §FR-033–FR-034, SC-016–SC-017]
- [x] CHK010 Are learning-session duration and review rules explicit about start and stop boundaries, pauses, required versus optional material, external-lab time, immediate-feedback timing, missed-only versus full retries, attempt limits, question reuse, and score-history treatment? [Clarity, Gap, Spec §FR-022, §FR-028–FR-031, SC-011, SC-014–SC-015]
- [x] CHK011 Are “saving,” “saved,” “not yet saved,” “failed to save,” active-session-only, and durable states precisely defined for navigation, refresh, browser closure, sign-out, expiry, outage, and emergency reauthentication? [Clarity, Spec §FR-010–FR-011, §FR-018, §FR-021, §FR-023–FR-024, Data Model §Ownership and service boundaries]
- [x] CHK012 Is the idempotency lifecycle explicit for validation failure, in-progress duplicates, identical replay, changed-payload conflict, timeout, retryable failure, final failure, result retention, and safe key expiry? [Clarity, Gap, Spec §FR-062, SC-032, Data Model §IdempotencyRecord, Learning Contract §Idempotency contract]
- [x] CHK013 Are compatibility requirements explicit for supported, disjoint, missing, malformed, unavailable, cached, and stale capability metadata at both service boundaries, including freshness, headers, fail-closed timing, and input/idempotency preservation? [Clarity, Spec §FR-039, SC-020, Plan §Service and API boundaries, Learning Contract §Compatibility]
- [x] CHK014 Is the rollback contract precise about the pre-attempt snapshot, every journaled mutation type, reversibility classification, compensating action, reverse order, retry/timeout limit, verification, failed compensation, and operator escalation? [Clarity, Gap, Spec §FR-052, SC-026, SC-035–SC-036, Plan §Jenkins delivery strategy]

## Requirement Consistency

- [x] CHK015 Are UI presentation, BFF browser/session composition, and core authorization/business/persistence boundaries stated consistently across the specification, plan, data model, authentication contract, learning contract, and tasks? [Consistency, Spec §FR-035–FR-047, Plan §Service and API boundaries, Data Model §Ownership and service boundaries]
- [x] CHK016 Are BFF-only Redis state and core-only PostgreSQL authority consistent with active-browser state, persistence indicators, atomic domain transitions, telemetry, backups, and retention requirements? [Consistency, Spec §FR-018, §FR-023–FR-024, §FR-031, §FR-060, Plan §Data ownership]
- [x] CHK017 Is one authoritative rule used for when a learning objective requires a lab versus permits an omission, including ownership of classification and treatment of borderline objectives? [Consistency, Spec §FR-025, §FR-065, SC-037, Plan §Lab governance]
- [x] CHK018 Are delegated employee-token and app-only machine-token acceptance and rejection rules consistent across issuer, tenant, audience, client, scope/role, subject, lifetime, ownership, and wrong-token-type requirements? [Consistency, Spec §FR-042, §FR-044–FR-045, §FR-054–FR-058, Auth Contract §BFF-to-core authorization, §Machine-consumer authorization]
- [x] CHK019 Does the 90-day departure policy consistently cover PostgreSQL records, Redis sessions and caches, idempotency results, backups/restores, logs, traces, audit/activity records, and aggregates, with a single unlinking standard for retained telemetry? [Consistency, Gap, Spec §FR-060–FR-061, SC-030–SC-031, Data Model §RetentionAction]
- [x] CHK020 Is evidence-hold authority consistently assigned to the configured Evidence Hold Managers Entra group, separate from evidence readers and workload writers, with consistent creation, extension, release, audit, expiry, and denial semantics? [Consistency, Spec §FR-070, Plan §Delivery evidence strategy, Jenkins Contract §Evidence retention contract]

## Acceptance Criteria Quality

- [x] CHK021 Do all pilot outcomes define eligibility, exactly-20-participant sampling, replacement/exclusion rules, task scripts, assistance rules, questionnaire wording, data collection, and pass/fail calculations? [Measurability, Spec §SC-001, §SC-007, §SC-011, §SC-015–SC-017, Spec §Assumptions]
- [x] CHK022 Do the one-second validation and accessible-result criteria define test environment, event boundaries, instrumentation, run count, failure treatment, and aggregation with sufficient precision for reproducible assessment? [Measurability, Spec §SC-003–SC-004, Plan §Performance Goals]
- [x] CHK023 Is the core performance profile fully traceable to an approved fixture set, full-profile and fixture-set digests, complete required-evidence schema, pinned BFF/core contract digests, regenerated mapper digest/drift gate, concurrency model, warm-up policy, attempt denominator, timeout policy, monotonic timing boundary, nearest-rank p95 calculation, and retained evidence? [Acceptance Criteria, Spec §SC-043, Tasks §T157]
- [x] CHK024 Do all “100%,” “all tested,” and “exactly one” outcomes define an enumerated scenario matrix and denominator, including authorization, recovery, compatibility, identity isolation, lab policy, controller audit, and evidence retention? [Measurability, Spec §SC-009–SC-014, §SC-019–SC-042, §SC-048]
- [x] CHK025 Do rollout, rollback, evidence, and credential-rotation success criteria define the authoritative observation source, required artifacts, ordering, terminal state, and failure threshold without relying on implicit Jenkins or Azure configuration? [Acceptance Criteria, Spec §SC-026, §SC-033–SC-036, §SC-039–SC-042]

## Scenario and Edge-Case Coverage

- [x] CHK026 Are primary, alternate, exception, and recovery requirements complete and mutually consistent for roadmap creation, guidance, focused learning, and progress review? [Coverage, Spec §User Stories 1–4, §Edge Cases]
- [x] CHK027 Are simultaneous tabs, identical and conflicting retries, delayed responses after logout, process restarts, replay after timeout, and idempotency-record expiry addressed without permitting duplicate or cross-owner transitions? [Coverage, Edge Case, Spec §FR-020, §FR-059, §FR-062, SC-032]
- [x] CHK028 Are content and contract version changes during an in-progress learning session, review attempt, lab visit, or progress submission addressed, including resume and safe-retry behavior? [Coverage, Gap, Spec §FR-024, §FR-028–FR-031, §FR-039, SC-020]
- [x] CHK029 Are Redis loss, PostgreSQL unavailability, directory state `unknown`, JWKS staleness, certificate-mount failure, and partial replica convergence covered with explicit authorization, readiness, retry, and no-partial-mutation requirements? [Coverage, Recovery, Gap, Spec §FR-048, §FR-057, §FR-061, §FR-068, Plan §Authentication and certificate lifecycle]
- [x] CHK030 Are lab redirect loops, allowlisted-to-unapproved redirects, throttling, intermittent failures, provider-domain changes, reports during validation, and recovery after three failures addressed in the written requirements? [Coverage, Edge Case, Spec §FR-027, §FR-063, §FR-066, SC-038]
- [x] CHK031 Are Jenkins cancellation, controller restart or disk loss, agent loss, Azure denial, ACR publication without promotion, evidence rejection, stale/concurrent builds, rollback failure, and irreversible migration recovery covered? [Coverage, Recovery, Gap, Spec §FR-052, §FR-064, §FR-069–FR-070, SC-035–SC-036]
- [x] CHK032 Are normal and emergency BFF-certificate, gateway-certificate, and Jenkins provisioning-credential rotation scenarios distinguished, including overlap, quarantine, replica convergence, revocation, rollback, and safe recovery? [Coverage, Spec §FR-068–FR-069, SC-040–SC-041, Plan §Authentication and certificate lifecycle, Plan §Jenkins provisioning credential lifecycle]

## Non-Functional Requirements

- [x] CHK033 Are the explicitly scoped accessibility behaviors complete for logical focus, visible focus, status/error announcements, semantic labels/headings, error association, reflow, timeout warnings, external-link context, progress visualization, review feedback, and focus restoration, while preserving the stated exclusion of formal WCAG certification? [Completeness, Spec §FR-013–FR-014, SC-005–SC-006, Spec §Assumptions]
- [x] CHK034 Is the supported-browser boundary defined by browser/version, device orientation, zoom or text scaling, and assistive-technology expectations rather than only “current mainstream” and viewport widths? [Ambiguity, Spec §FR-014, SC-006, Spec §Assumptions]
- [x] CHK035 Are least-privilege allow and deny matrices complete for the UI, BFF, core, lifecycle, retention, migration Job, ALB controller, gateway certificate/DNS, AKS kubelet, external bootstrap/consent operators, Jenkins controller/cloud principal, validator/publisher/deployer identities, credential manager, evidence readers, and hold managers, including data-plane and privilege-escalation denial? [Security, Completeness, Spec §FR-040, §FR-049–FR-058, §FR-064, §FR-067, §FR-069–FR-075]
- [x] CHK036 Are observability requirements measurable for service ownership, trace continuity, dependency outcome, readiness, latency, errors, restarts, scaling saturation, alert thresholds, routing, and prohibited personal or credential data? [Non-Functional, Measurability, Spec §FR-017, §FR-048, SC-024, Plan §Azure topology]
- [x] CHK037 Are scaling and resilience requirements defined independently for all three services, including requests/limits, replica bounds, HPA signal, disruption budget, topology policy, readiness behavior, and the effect of scaling one service on the others? [Non-Functional, Completeness, Spec §FR-035, §FR-041, §FR-048–FR-049, Plan §Azure topology]
- [x] CHK038 Are availability, durability, recovery-time, recovery-point, and data-loss expectations either quantified for the non-production pilot or explicitly excluded with an owner-approved rationale? [Gap, Non-Functional, Plan §Technical Context, Spec §Assumptions]

## Dependencies, Assumptions, and Traceability

- [x] CHK039 Are assumptions and prerequisites for the Entra tenant, approved machine consumers/private networks, external Platform Operations bootstrap and fresh manifest, existing AKS/ACR capacity, Jenkins cloud `azure`, ACI connectivity, Azure services, lab providers, pilot population, and supported browsers assigned validation evidence and an accountable owner? [Assumption, Dependency, Spec §Assumptions, Spec §FR-071–FR-074, Plan §Technical Context]
- [x] CHK040 Can every FR-001–FR-075 and SC-001–SC-050 obligation be traced to an acceptance scenario or explicit operational outcome, a normative contract or design decision, at least one implementation task, at least one positive or negative verification task, and a required evidence artifact or documented exception? [Traceability, Spec §Requirements, Spec §Success Criteria, Plan §Phase 2, Tasks §T001–T198]

## Notes

- Check an item only after the referenced artifacts contain enough information to answer it objectively.
- Record unresolved gaps inline and update the normative artifact before marking the item complete.
- Re-run cross-artifact analysis after resolving this formal gate and before implementation.
- **Completed 2026-07-13**: 40/40 items passed after digest, schema, denominator, traceability, and independent final-audit validation.
- **Revalidated 2026-07-16**: SC-050, the approved interaction-performance profile, and its structured exact-byte digest-bound fixture set extend the inventory to 125 ordered rows while preserving 198 mapped tasks and the independent SC-043 profile; callback timing is explicitly post-provider-exchange application processing, and canonical per-attempt SHA-256 evidence is fixed by two known-answer vectors.
