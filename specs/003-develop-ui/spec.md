# Feature Specification: DevOps Career Agent UI

**Feature Branch**: `003-develop-ui`  
**Created**: 2026-07-11  
**Status**: Approved for implementation  
**Input**: User description: "Create a feature for developing a UI; the UI, Backend-for-Frontend, and core backend must be separately hosted services"

## Clarifications

### Session 2026-07-11

- Q: Which login and identity mechanism must the UI use? -> A: Microsoft Entra ID organizational sign-in.
- Q: What duration should each focused learning session target? -> A: 20-30 minutes.
- Q: How should the first release provide hands-on lab experience? -> A: Curated links to external hands-on labs.
- Q: How should review questions determine learning-session completion? -> A: Use 3-5 scored questions, an 80% threshold, immediate feedback, and retries.
- Q: Which motivation model should encourage continued learning? -> A: Use visible milestones, completion celebrations, and one recommended next action.
- Q: How must the UI be hosted relative to the backend service? -> A: The UI must be deployed and operated as a separate application.
- Q: Which service boundary should the separate UI use? -> A: A separately deployed BFF service must mediate between the UI service and the core backend.
- Q: Where must the three services run? -> A: The UI, BFF, and core backend must all run on Azure, using a shared AKS platform while retaining independent deployment lifecycles.
- Q: How should existing machine consumers authenticate to the core backend? -> A: Use Microsoft Entra client-credentials tokens with dedicated core API app roles.
- Q: What expiry policy should apply to authenticated BFF browser sessions? -> A: Use a 30-minute idle timeout and an 8-hour absolute limit.
- Q: What retention policy should apply to employee learning records? -> A: Retain records while employed, then delete or anonymize them within 90 days after departure.
- Q: How should the system recognize that an employee has departed? -> A: Use Microsoft Entra account disablement or deletion, checked at sign-in and by daily reconciliation.
- Q: How should concurrent or repeated state-changing submissions be resolved? -> A: Require an idempotency key and make the first valid submission authoritative.
- Q: Which continuous-integration system must execute the delivery workflow? -> A: Jenkins.
- Q: Which Azure container service runs Jenkins agents in the configured resource group? -> A: Ephemeral Azure Container Instances agents.
- Q: How are ACR publication and AKS deployment privileges separated for Jenkins agents? -> A: Separate publisher and deployer ACI templates use distinct user-assigned managed identities.
- Q: How do ephemeral ACI agents connect to the local Jenkins controller? -> A: The controller's existing Jenkins Azure cloud-node configuration provisions and connects them.
- Q: What is the configured Jenkins Azure cloud-node name? -> A: `azure`.
- Q: How does Jenkins cloud `azure` authenticate to provision ACI agents? -> A: An existing service-principal credential is configured in the Jenkins controller.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a Career Roadmap (Priority: P1)

An employee uses a browser-based interface to describe their current role, experience, target role, available learning time, and relevant preferences. The employee reviews the information, submits it, and receives a clearly structured career roadmap without needing to understand or call service endpoints directly.

**Why this priority**: Roadmap creation is the primary value of the career agent and provides a complete, independently useful first UI release.

**Independent Test**: A tester can open the application, complete the roadmap form with valid employee information, submit it, and read the resulting milestones and recommendations entirely through the UI.

**Acceptance Scenarios**:

1. **Given** an organizational employee opens the application, **When** they complete Microsoft Entra ID sign-in and view the landing page, **Then** they can identify the product purpose and begin creating a career roadmap.
2. **Given** an employee enters valid profile information, **When** they submit the roadmap request, **Then** the interface shows progress and presents the completed roadmap in a readable structure.
3. **Given** required information is missing or invalid, **When** the employee attempts to continue, **Then** the interface identifies each affected field and explains how to correct it without discarding valid entries.
4. **Given** roadmap generation fails, **When** the failure is returned or the request cannot complete, **Then** the employee sees a plain-language message and can retry without re-entering the full profile.
5. **Given** the UI is available but the backend service is unavailable, **When** an employee attempts to create a roadmap, **Then** the UI identifies the temporary service outage and preserves the employee's valid entries for retry.

---

### User Story 2 - Explore Skill Guidance (Priority: P2)

An employee selects or enters a DevOps topic and receives focused guidance that is appropriate for their profile. The employee can move between their roadmap and skill guidance without losing the current results during the active browser session.

**Why this priority**: Topic guidance turns a broad roadmap into actionable learning steps and reuses employee context already supplied through the primary journey.

**Independent Test**: A tester can enter a supported topic and employee profile, submit the request, and review the returned explanation and recommendations without first creating a roadmap.

**Acceptance Scenarios**:

1. **Given** an employee provides a supported topic and valid profile, **When** they request guidance, **Then** the interface presents the guidance with a clear topic heading and actionable content.
2. **Given** an employee has already entered profile information in the active session, **When** they open skill guidance, **Then** the interface reuses that information while allowing edits before submission.
3. **Given** a topic is unavailable or cannot be interpreted, **When** the employee submits it, **Then** the interface explains the issue and preserves the entered profile and topic for correction.
4. **Given** guidance includes practical experience, **When** the employee reviews the recommended lab, **Then** they can see its provider, objective, prerequisites, estimated duration, and external destination before opening it.

---

### User Story 3 - Complete a Focused Learning Session (Priority: P2)

An employee completes a short learning session that combines a clear objective, concise learning steps, a practical lab reference when appropriate, and a review that confirms understanding. The employee receives immediate feedback and can retry missed questions before moving on.

**Why this priority**: Focused sessions convert recommendations into repeatable learning activity and provide the progress signals that encourage continued learning.

**Independent Test**: A tester can start one learning session, follow its ordered content, open a lab reference, answer 3-5 review questions, receive explanations, retry missed questions, and complete the session by reaching at least 80%.

**Acceptance Scenarios**:

1. **Given** an employee reaches the review step, **When** the review is displayed, **Then** it contains between 3 and 5 scored questions related to the session objective.
2. **Given** an employee submits a review, **When** an answer is evaluated, **Then** the interface immediately identifies whether it was correct and explains the correct reasoning.
3. **Given** an employee scores below 80%, **When** results are shown, **Then** the session remains incomplete and the employee can retry missed material and questions.
4. **Given** an employee scores at least 80%, **When** the review completes, **Then** the learning session is marked complete and progress is updated.
5. **Given** a learning session is completed, **When** completion is recorded, **Then** the employee receives a concise celebration of the milestone and a single recommended next action.

---

### User Story 4 - Record and Review Progress (Priority: P3)

An employee records a progress check-in against a roadmap and receives an updated review that highlights completed work, gaps, and recommended next actions.

**Why this priority**: Progress review supports continued use after the initial plan but depends on an employee already having roadmap context.

**Independent Test**: Using an existing roadmap identifier, a tester can enter a progress update, submit it, and view the returned review and next actions through the UI.

**Acceptance Scenarios**:

1. **Given** an employee has a valid roadmap reference, **When** they submit a progress check-in, **Then** the interface shows the review, current status, and recommended next actions.
2. **Given** the roadmap reference is missing or unknown, **When** the employee submits a check-in, **Then** the interface clearly explains that a valid roadmap is required and preserves the entered progress notes.
3. **Given** a progress review is displayed, **When** the employee navigates to another UI area and returns during the active session, **Then** the latest review remains available.
4. **Given** an employee views their progress, **When** completed and upcoming work is shown, **Then** they can identify achieved milestones and one recommended next action.

### Edge Cases

- The interface remains usable when a user submits by keyboard rather than pointer input.
- Repeated submission controls are disabled while a request is in progress so one user action does not create duplicate requests.
- Long roadmap or guidance results remain readable and do not hide navigation or actions.
- Unexpected or partially structured error details are replaced with a safe, understandable message while preserving user-entered values.
- A browser refresh may clear unsaved session information, but the interface explains when information has not yet been saved.
- If an employee leaves before a learning session is complete, completed steps remain recorded and the employee can resume from the next incomplete step.
- Narrow screens reflow content without horizontal scrolling for primary forms, results, and navigation.
- If the service is temporarily unavailable, the UI distinguishes the outage from user input errors and provides a retry action.
- If an external lab link is unavailable, the employee can report the link and continue the learning session without losing progress.
- If lab validation is throttled or the provider returns an indeterminate temporary failure, the system records the attempt and retains the previous publication state until the configured consecutive-failure threshold is reached.
- If an employee leaves during a review, submitted answers and the incomplete session state are retained without incorrectly marking the session complete.
- If the UI deployment is unavailable, backend service health checks and existing machine consumers continue operating independently.
- If the UI and backend are temporarily on incompatible releases, the UI stops unsupported actions, shows a safe availability message, and does not corrupt saved progress.
- If the configured backend destination is missing or invalid, the UI fails closed with a clear operational error rather than sending personalized data to an unapproved destination.
- If a browser attempts to bypass the BFF and call a personalized backend capability directly, the backend rejects the request unless it carries independently valid authorization intended for that backend capability.
- If the UI is available but the BFF is unavailable, the UI preserves safe unsaved input, disables dependent operations, and presents a retryable service-unavailable state.
- If the BFF is unavailable, existing core-backend health checks and supported machine consumers continue operating independently.
- If a machine consumer presents a delegated employee token, browser session,
  missing app role, or token for the wrong audience, the core rejects the
  request without treating it as an approved machine identity.
- If a BFF session is idle for 30 minutes or reaches 8 hours from sign-in, the
  BFF revokes it and requires sign-in again without deleting saved progress.
- If an employee departs, their personalized roadmap, progress, and review
  history becomes ineligible for normal access and is deleted or irreversibly
  anonymized within 90 days.
- If daily Entra reconciliation finds an account disabled or deleted, the
  system revokes active BFF sessions and blocks personalized access even when
  the employee does not attempt another sign-in.
- If retries, multiple tabs, or concurrent clients repeat a state-changing
  operation with the same idempotency key and payload, the system returns the
  first valid result without creating duplicate state; reuse with a different
  payload is rejected as a conflict.
- If Jenkins or an Azure delivery dependency becomes unavailable before the
  first environment mutation, the release stops, reports the failed stage, and
  leaves all deployed digests unchanged. If the dependency becomes unavailable
  after one or more services have changed, the release restores every service
  changed by that delivery attempt in reverse deployment order and verifies the
  pre-attempt digests before it terminates.
- If the existing Jenkins Azure cloud-node configuration cannot provision or
  connect an ACI agent, the build stops before Azure authentication or
  publication and does not expose the local controller or create a fallback
  long-lived Azure credential.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a browser landing page that explains the application purpose and offers direct navigation to roadmap creation, skill guidance, focused learning sessions, and progress check-ins.
- **FR-002**: The system MUST provide a roadmap form covering the employee information required by the existing career-roadmap workflow.
- **FR-003**: The system MUST validate required, numeric, and constrained roadmap inputs before submission and place correction guidance beside or clearly associated with each invalid field.
- **FR-004**: The system MUST show a visible in-progress state for every submitted operation and prevent duplicate submissions until the operation completes or fails.
- **FR-005**: The system MUST present roadmap results with distinguishable sections for the employee goal, milestones, learning recommendations, and other returned guidance.
- **FR-006**: The system MUST provide a skill-guidance form that accepts a topic and the employee profile information required by the guidance workflow.
- **FR-007**: The system MUST present skill guidance with the requested topic, explanatory content, and actionable recommendations clearly distinguished.
- **FR-008**: The system MUST provide a progress check-in form that accepts a roadmap reference and the progress information required by the progress-review workflow.
- **FR-009**: The system MUST present a progress review with current status, identified gaps, and recommended next actions when those elements are returned.
- **FR-010**: The system MUST preserve valid form entries after validation, service, or connectivity errors so users can correct or retry without starting over.
- **FR-011**: The system MUST preserve the latest entered profile and displayed results while users navigate among UI areas during the active browser session.
- **FR-012**: The system MUST provide clear success, validation, not-found, service-unavailable, and unexpected-error feedback without exposing internal diagnostic details.
- **FR-013**: The system MUST make all primary journeys operable by keyboard and expose meaningful labels, headings, status changes, and error associations to assistive technologies.
- **FR-014**: The system MUST remain usable on supported desktop, tablet, and mobile-width screens without horizontal scrolling for primary content.
- **FR-015**: The system MUST provide a consistent way to return to the application landing page and switch between the four primary journeys.
- **FR-016**: The system MUST preserve the documented request semantics, response schemas, health behavior, and business outcomes used by existing machine consumers. Introducing Microsoft Entra authentication and private routing is an intentional compatibility change, and anonymous access MUST NOT be preserved.
- **FR-017**: The system MUST avoid displaying secrets, internal stack traces, or sensitive configuration values in UI content or browser-visible errors.
- **FR-018**: The system MUST clearly identify information retained only in the active browser session with a persistent `Not yet saved` indicator and MUST remove that indicator only after the BFF confirms successful persistence.
- **FR-019**: The system MUST require employees to authenticate with their organizational Microsoft Entra ID identity before accessing personalized learning information.
- **FR-020**: The system MUST associate saved roadmaps, progress, and learning activity with the authenticated employee and prevent employees from viewing another employee's information.
- **FR-021**: The system MUST provide a clear sign-out action and end access to personalized information when sign-out completes or the authenticated session expires.
- **FR-022**: The system MUST organize recommended learning into focused sessions designed to take 20-30 minutes and show the estimated duration before an employee starts.
- **FR-023**: The system MUST show progress within the current learning session and persist completed steps for the authenticated employee.
- **FR-024**: The system MUST allow an employee to leave a learning session and later resume from the next incomplete step.
- **FR-025**: The system MUST include curated external hands-on lab references where practical experience supports the learning objective.
- **FR-026**: Each lab reference MUST identify its provider, objective, prerequisites, estimated duration, cost status, and external destination before the employee opens it.
- **FR-027**: The system MUST clearly distinguish external lab content, preserve application progress when employees leave for a lab, and allow employees to report unavailable or unsuitable links.
- **FR-028**: Each learning session MUST include a review containing between 3 and 5 scored questions aligned with the session objective.
- **FR-029**: The system MUST provide immediate correctness feedback and a concise explanation after each submitted review answer.
- **FR-030**: The system MUST require a score of at least 80% to mark a learning session complete and MUST allow employees below the threshold to review material and retry.
- **FR-031**: The system MUST retain review attempts, scores, completion status, and the latest attempt time for the authenticated employee's progress history.
- **FR-032**: The system MUST present learning progress as visible roadmap and session milestones that distinguish completed, current, and upcoming work.
- **FR-033**: The system MUST acknowledge completed milestones with concise positive feedback and MUST present one clearly prioritized recommended next action.
- **FR-034**: The system MUST base the recommended next action on the employee's roadmap, completed sessions, review outcomes, and incomplete work without introducing competitive rankings.
- **FR-035**: The UI, BFF, and core backend MUST each be packaged, deployed, configured, scaled, updated, rolled back, and monitored as independent services.
- **FR-036**: The UI MUST access personalized career-roadmap, guidance, progress, learning, and identity-scoped capabilities only through the BFF and MUST NOT directly access core-backend interfaces or storage.
- **FR-037**: The core backend MUST remain independently available to approved machine consumers and private health monitoring while either the UI or BFF is unavailable, deploying, or rolling back.
- **FR-038**: The UI MUST use environment-specific BFF destination and trust configuration, and the BFF MUST use environment-specific core-backend destination and trust configuration, without requiring source changes or environment-specific rebuilds.
- **FR-039**: The UI, BFF, and core backend MUST detect unsupported interface-version combinations at their respective boundaries. The BFF MUST expose its contract version, accepted UI contract range, and current core-compatibility state through a capabilities resource; state-changing UI requests MUST identify the UI contract version. BFF-to-core requests MUST identify the BFF contract version, and the core MUST expose its contract version and accepted BFF range. Either boundary MUST reject an unsupported state-changing request with `409 CONTRACT_VERSION_UNSUPPORTED` before invoking downstream work, consuming an idempotency key, or changing state, while the UI preserves valid unsaved input and presents a safe retry or availability message.
- **FR-040**: Authentication boundaries MUST prevent reusable credentials and personalized records from reaching the UI, unapproved origins, or untrusted destinations.
- **FR-041**: The BFF MUST run as an independently addressable AKS workload with its own image, runtime configuration, health signal, scaling policy, deployment history, and rollback lifecycle; it MUST NOT share a process or deployment unit with the UI or core backend.
- **FR-042**: The BFF MUST be the only UI-facing service authorized to invoke personalized core capabilities. Core authorization MUST reject browser cookies, untrusted forwarded-identity headers, and tokens not issued for the core API.
- **FR-043**: The BFF MUST own browser-specific concerns, including sign-in initiation, browser session handling, request validation, user-facing response shaping, and safe translation of backend failures.
- **FR-044**: The BFF MUST call the core through its versioned private API and attach an access token intended specifically for the core API.
- **FR-045**: The core MUST derive employee ownership only from independently validated token claims and MUST ignore browser-provided identity fields and forwarded identity headers.
- **FR-046**: The BFF MUST avoid duplicating career-roadmap, learning-progress, review-scoring, next-action, and persistence business rules owned by the core backend.
- **FR-047**: The UI service MUST remain presentation-focused and MUST NOT own BFF session mediation, core-backend credentials, authoritative authorization decisions, or core business rules.
- **FR-048**: Each service MUST expose an independent health signal that distinguishes UI availability, BFF availability, and core-backend availability.
- **FR-049**: The UI, BFF, and core backend MUST all be hosted on Microsoft Azure and deployed as independent workloads on the shared AKS application platform.
- **FR-050**: Deployment MUST use Azure-managed platform capabilities for container images, ingress, secrets, session storage, relational persistence, identity, and observability where doing so reduces application operational burden.
- **FR-051**: The deployment topology MUST expose only the UI and BFF through the approved Azure-managed gateway; the core backend and data services MUST remain private.
- **FR-052**: A release MUST promote immutable UI, BFF, and core image digests independently through ACR and MUST support compatibility-checked progressive rollout and rollback without rebuilding images. If a multi-service delivery attempt fails, is aborted, or loses a required Jenkins or Azure dependency after an environment mutation, every service changed by that attempt MUST be restored to its pre-attempt digest in reverse deployment order; services not changed by that attempt MUST remain untouched.
- **FR-053**: The UI MUST use an opaque BFF session and MUST NOT receive, store, or forward Microsoft Entra access, ID, or refresh tokens.
- **FR-054**: The BFF MUST be registered as a confidential web client, use the authorization-code flow, and request only the delegated core API scopes required for the signed-in employee.
- **FR-055**: The core MUST independently validate delegated access-token signature, issuer, tenant, audience, lifetime, authorized client, required scope, and employee subject claims before authorizing personalized operations.
- **FR-056**: BFF and core workloads MUST use separate Microsoft Entra Workload Identities with least-privilege access to their Azure dependencies; ACR image pull MUST remain assigned to the AKS kubelet identity.
- **FR-057**: Azure Managed Redis and Azure Database for PostgreSQL connections MUST use Microsoft Entra token authentication in deployed Azure environments, with token refresh and reconnect behavior verified under expiry and transient failure.
- **FR-058**: Approved machine consumers MUST authenticate directly to the core using Microsoft Entra client-credentials access tokens containing dedicated core API application roles; browser sessions and employee-delegated scopes MUST NOT grant machine-consumer access.
- **FR-059**: Authenticated BFF browser sessions MUST expire after 30 minutes without activity and MUST expire no later than 8 hours after sign-in regardless of activity; expiry MUST revoke server-side session access and preserve already saved learning records.
- **FR-060**: The system MUST delete departed employees' identity, profile, roadmap, progress, learning, review, report, and idempotency records within 90 days. Security evidence MAY be irreversibly anonymized only after all direct and indirect employee links are removed, and aggregate telemetry MAY remain only when it cannot be reidentified.
- **FR-061**: The system MUST recognize departure from Microsoft Entra account disablement or deletion, enforce the status during sign-in, reconcile active employee identities at least daily, and revoke active browser sessions when departure is recognized.
- **FR-062**: Every retryable state-changing BFF and core operation MUST require and propagate an owner-scoped idempotency key; the first valid submission MUST be authoritative, an identical replay MUST return its established result, and key reuse with a different payload MUST return a conflict without changing state.
- **FR-063**: Before publication, every lab reference MUST pass HTTPS, approved-provider-domain, redirect-chain, metadata-completeness, and reachability validation. Active references MUST be revalidated at least once every 24 hours using a 10-second request timeout and no more than two retries. A reference MUST become unavailable after three consecutive failed scheduled validations and MAY return to active only after a later complete validation succeeds.
- **FR-064**: The Jenkins controller at `http://localhost:8080` MUST orchestrate continuous integration and delivery through the existing Jenkins Azure cloud node named `azure`, whose existing service principal is authorized only to provision and connect ephemeral Azure Container Instances agents in the configured resource group and attach their approved identities. Publication stages MUST run only on the publisher ACI template using its ACR-scoped user-assigned managed identity; promotion, deployment, verification, and rollback stages MUST run only on the deployer ACI template using its AKS-scoped user-assigned managed identity. The controller service principal MUST NOT receive ACR push or AKS deployment permission, and Jenkins MUST store no additional Azure application-delivery credential.
- **FR-065**: A published focused learning session MUST include a hands-on lab when its objective requires command execution, configuration, deployment, troubleshooting, or observation of a running system. A lab MAY be omitted for orientation, conceptual comparison, or review-only objectives only when the omission reason is recorded with the content version.
- **FR-066**: Lab destinations MUST belong to a versioned provider allowlist. Every addition or domain expansion MUST receive approval from two distinct human identities: one member of the configured Learning Content Owners Microsoft Entra group and one member of the configured Application Security Reviewers Microsoft Entra group. One identity MUST NOT satisfy both approvals, including when that person belongs to both groups. The change record MUST contain provider, domains, both approver identities, reason, effective time, policy version, and audit reference. The initial allowlist MUST be empty.
- **FR-067**: Jenkins cloud `azure` MUST bind the `azure-aci-publisher` template exclusively to the publisher user-assigned managed identity and the `azure-aci-deployer` template exclusively to the deployer user-assigned managed identity. A missing, additional, or mismatched identity binding MUST stop the pipeline before Azure authentication.
- **FR-068**: BFF confidential-client certificate rotation MUST introduce the replacement certificate at least 24 hours before retiring the previous certificate. During normal rotation, the previous certificate MUST remain valid until every BFF replica has loaded the replacement and successful core-token acquisition has been demonstrated; existing browser sessions and new sign-ins MUST continue without forced reauthentication, and the previous credential MUST be removed within 48 hours of replacement activation. A suspected compromise MUST trigger immediate revocation without waiting for the overlap period; emergency rotation MAY require affected employees to reauthenticate, but MUST preserve already saved learning records and present a safe sign-in recovery path.
- **FR-069**: The Jenkins cloud `azure` provisioning service principal MUST be owned by the platform operations team and rotated at least every 90 days. Platform operations MUST receive credential-expiry alerts at 30, 14, and 7 days before expiry. The credential MUST be replaced before fewer than 30 days of validity remain. Only a dedicated least-privilege Jenkins credential-manager role, usable through the controller's localhost administrative interface and restricted to the stable `azure` cloud credential entry, MAY install a replacement credential. Replacement secret material MUST NOT appear in command arguments, environment variables, repository files, retained temporary files, or logs. Normal rotation MUST prove ACI publisher and deployer agent provisioning before the previous credential is revoked. Suspected compromise MUST trigger immediate revocation, disable ordinary cloud-agent provisioning, and permit only an audited rotation-validation path until both templates pass.
- **FR-070**: Jenkins delivery evidence MUST be retained for 90 days in the non-production environment. Authorized readers MUST be derived from separately configured Delivery Operators and Security Reviewers Microsoft Entra group object IDs. Incident-hold creation, extension, and release MUST be restricted to a separately configured Evidence Hold Managers Microsoft Entra group and MUST be audited; evidence-reader membership alone MUST NOT grant hold-management authority. Publisher and deployer workload identities MAY create evidence only within their assigned immutable paths and MUST NOT receive general read, list, tag-mutation, or deletion permission. Path isolation MUST use Azure role-assignment conditions scoped to the assigned environment and delivery-stage prefix. Every upload MUST use `If-None-Match: *`, and an accepted evidence version MUST be protected by a default version-level Azure immutability policy so that no writer can successfully replace or delete it even if the conditional header is omitted or bypass is attempted. Evidence MUST be deleted after 90 days unless an incident hold is recorded; a hold MAY extend total retention to no later than 180 days from evidence creation and MUST record its owner, reason, incident reference, start, and expiry. Tokens, kubeconfigs, secrets, and personal learning data MUST never be archived.

### Key Entities

- **Employee Profile**: Information describing the employee's current role, experience level, target role, available learning time, preferences, and constraints.
- **Career Roadmap**: A generated career-development plan associated with an employee profile and containing milestones and learning recommendations.
- **Skill Guidance Request**: A selected DevOps topic combined with employee context for producing focused learning guidance.
- **Progress Check-In**: An employee's progress update associated with an existing roadmap.
- **Progress Review**: The evaluation returned for a check-in, including current status, gaps, and recommended next actions.
- **Active UI Session**: Temporary browser state containing form entries and the latest displayed results; it is not an additional permanent user record.
- **Employee Identity**: The organizational identity established through Microsoft Entra ID and used to scope access to the employee's saved learning information.
- **Learning Session**: A focused 20-30 minute unit containing a goal, ordered learning activities, progress state, and completion status.
- **Hands-On Lab Reference**: A curated external practical exercise with a provider, learning objective, prerequisites, expected duration, cost status, destination, and availability/reporting state.
- **Session Review**: A set of 3-5 scored questions tied to one learning session, including submitted answers, immediate explanations, attempt score, attempt time, and completion outcome.
- **Learning Milestone**: A meaningful roadmap or session achievement with completion state, completion time, and relationship to the employee's next recommended action.
- **Backend Service Interface**: The documented, versioned boundary through which the separately hosted UI requests authenticated roadmap, guidance, learning, and progress capabilities.
- **Backend for Frontend**: A service deployed separately from both the UI and core backend that manages UI-oriented sessions, request orchestration, response composition, and safe delegation to authoritative core-backend operations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 18 of 20 representative pilot participants can submit a valid roadmap and identify its first recommended action without facilitator assistance on their first attempt.
- **SC-002**: Users can reach and begin any of the four primary journeys within two interactions from the landing page.
- **SC-003**: For locally detectable input errors, users receive correction guidance within one second of attempting submission.
- **SC-004**: For at least 95% of successful roadmap and skill-guidance requests, no more than one second elapses between resolution of the browser's BFF fetch with the complete validated success payload and commitment of the corresponding result to the rendered accessibility tree; both boundaries MUST be captured by browser performance marks.
- **SC-005**: All primary journeys can be completed using keyboard-only navigation with a visible focus indicator and no focus traps.
- **SC-006**: Primary navigation, forms, results, learning content, review questions, and progress displays remain readable without page-level horizontal scrolling at viewport widths of 320, 375, 768, 1024, 1440, and 1920 pixels.
- **SC-007**: At least 17 of 20 representative pilot participants rate the clarity of forms, progress feedback, results, and errors as 4 or higher on a predefined 5-point questionnaire.
- **SC-008**: After approved machine consumers adopt Entra client-credentials authentication and the private core route, their supported operations complete without request-semantic, response-schema, health, or business-behavior regressions.
- **SC-009**: A failed request can be corrected or retried without re-entering valid information in 100% of tested validation, not-found, and temporary-outage scenarios.
- **SC-010**: In authorization testing, employees can access 100% of their own saved learning records and 0% of records belonging to another employee.
- **SC-011**: At least 18 of 20 representative pilot participants complete the required content and first review attempt of a focused session within 20-30 minutes; optional material, external-lab time, interruptions, and retries are recorded separately.
- **SC-012**: In all tested interruption scenarios, employees can resume at the next incomplete session step without repeating a recorded completed step.
- **SC-013**: In content-quality review, 100% of displayed lab references include provider, objective, prerequisites, estimated duration, cost status, and a reachable destination at the time of publication.
- **SC-014**: In all tested learning sessions, scores below 80% remain incomplete and scores of 80% or higher update completion and progress correctly.
- **SC-015**: At least 17 of 20 representative pilot participants rate the usefulness of review correctness feedback and explanations as 4 or higher on a predefined 5-point questionnaire.
- **SC-016**: At least 18 of 20 representative pilot participants can identify their current milestone, completed milestones, and recommended next action without facilitator assistance.
- **SC-017**: At least 16 of 20 representative pilot participants rate the statement "The completion feedback and recommended next action make me want to continue learning" as 4 or higher on a predefined 5-point questionnaire.
- **SC-018**: In deployment verification, each of the UI, BFF, and core backend can be released and rolled back without rebuilding or redeploying either of the other two services.
- **SC-019**: During a simulated UI outage, 100% of existing backend health checks and supported machine-consumer scenarios continue to operate normally.
- **SC-020**: In compatibility testing, 100% of unsupported UI-to-BFF and BFF-to-core version combinations return `409 CONTRACT_VERSION_UNSUPPORTED` before a downstream call, idempotency-key consumption, or state mutation, while preserving valid user-entered information and saved progress; supported combinations advertise mutually compatible ranges through the required capabilities and version metadata.
- **SC-021**: In architecture verification, 100% of browser-originated personalized operations pass through the BFF, and direct unauthenticated or improperly targeted backend requests are rejected.
- **SC-022**: Contract tests demonstrate that changing UI presentation or BFF response composition does not require changes to core backend business rules for all four primary user journeys.
- **SC-023**: During a simulated BFF outage, 100% of existing core-backend health checks and supported machine-consumer scenarios continue normally, while the UI clearly identifies the BFF outage without losing valid unsaved input.
- **SC-024**: Operational verification can independently identify whether an injected failure originates in the UI, BFF, or core backend in 100% of tested service-outage scenarios.
- **SC-025**: Deployment evidence shows all three application services running as independent AKS workloads, with images sourced from ACR and no public route to the core service.
- **SC-026**: A failed rollout is detected by health, rollout, and compatibility checks and restores every service changed by that delivery attempt to its pre-attempt digest in reverse deployment order without rebuilding images; services not changed by the attempt retain their image digest and deployment state.
- **SC-027**: Authentication verification proves that no reusable employee token reaches the UI, every personalized core request carries a valid delegated core token, and each workload identity can access only its documented Azure dependencies.
- **SC-028**: Machine-consumer authorization tests accept only approved client identities with the required core API application role and reject delegated tokens, wrong audiences, missing roles, and unapproved clients.
- **SC-029**: Session-expiry tests revoke access at the 30-minute idle and 8-hour absolute boundaries across all BFF replicas, require reauthentication, and leave previously saved roadmaps and learning progress unchanged.
- **SC-030**: Retention verification demonstrates that departed-employee records are unavailable for normal personalized access immediately after departure is recognized and are deleted or irreversibly anonymized no later than day 90.
- **SC-031**: Entra lifecycle tests detect disabled or deleted accounts at sign-in and within 24 hours without a login, revoke their active BFF sessions, and prevent new personalized access.
- **SC-032**: Concurrency tests demonstrate that identical retries and simultaneous submissions using one idempotency key create exactly one domain transition and return one established result, while mismatched payload reuse creates no additional state.
- **SC-033**: In delivery verification, a change affecting only one service validates and publishes only that service image, promotes the tested immutable digest, preserves the other two deployed digests, and stops before promotion when any required validation fails.
- **SC-034**: Shared contract, build-tooling, deployment, or indeterminate-baseline changes select every affected service; documentation-only changes publish no application image; first builds conservatively select all three services.
- **SC-035**: Concurrent or stale Jenkins builds cannot replace a newer environment state. An accepted delivery attempt that is aborted or loses a required Jenkins or Azure dependency before its first environment mutation leaves every digest unchanged; after a mutation, it restores every service changed by that attempt to its pre-attempt digest in reverse deployment order and verifies the restored environment before terminating.
- **SC-036**: A protected-branch delivery attempt begins only when Jenkins accepts the trigger and assigns a build identifier. Before requesting an ACI agent, Jenkins creates a non-authoritative controller audit record containing the build identifier, source revision, start time, `result=pending`, and no failed stage; it finalizes that record exactly once with completion time, terminal result, and failed stage or `none`. Triggers not accepted because the controller is unavailable are not delivery attempts and remain observable in the source-control or webhook-delivery audit. Once an authenticated publisher or deployer ACI agent starts, Jenkins publishes all available non-secret change plans, release manifests, test results, digest resolutions, scan and SBOM summaries, deployment snapshots, and rollback evidence to the authoritative Azure Storage evidence container. Failure to provision an ACI agent or publish required evidence is finalized in the controller audit record, MUST NOT trigger a fallback Azure credential, and MUST block the next environment mutation or trigger attempt-wide rollback when a prior mutation has occurred.
- **SC-037**: Content review shows that 100% of published sessions either contain a qualifying lab or record an allowed omission reason.
- **SC-038**: Every active lab destination resolves only through domains present in the provider-allowlist version recorded at publication time.
- **SC-039**: Delivery verification proves that publisher stages cannot obtain the deployer identity, deployer stages cannot obtain the publisher identity, and neither template can start with an undeclared managed identity.
- **SC-040**: Rotation verification demonstrates uninterrupted existing sessions, new sign-in, and delegated core-token acquisition across all BFF replicas during normal rotation, removal of the retired credential within 48 hours, immediate rejection of an emergency-revoked credential, and a safe reauthentication path that preserves saved learning records when emergency revocation invalidates affected sessions.
- **SC-041**: Credential-lifecycle verification detects a provisioning credential with fewer than 30 valid days, proves that only the localhost least-privilege credential-manager role can replace the stable Jenkins credential entry without exposing secret material, successfully creates both ACI templates, and confirms that the retired credential can no longer provision container groups.
- **SC-042**: Evidence-retention verification demonstrates authorized reader access, denial for unapproved identities, hold management only by the Evidence Hold Managers group, rejection of reader self-elevation, failure of every attempted replacement or deletion of an accepted evidence version, automatic deletion after 90 days, hold preservation through its declared expiry, deletion after hold release, enforcement of the 180-day total ceiling, and absence of prohibited credential and personal-data material.

## Assumptions

- The first UI release serves the existing internal pilot audience, uses Microsoft Entra ID organizational sign-in, and does not add application-managed registration, passwords, administrative roles, or account management.
- The existing roadmap, skill-guidance, progress-check-in, and health capabilities remain the authoritative source of application behavior.
- Existing machine consumers receive dedicated Entra application identities and
  core API app-role assignments; anonymous compatibility is not preserved.
- Aggregate telemetry may outlive personalized learning records only when it
  cannot be linked back to the departed employee.
- Daily Entra lifecycle reconciliation is an authorized background
  machine-to-machine operation and requests only the directory permissions
  required to determine whether known employee identities remain active.
- English is the only supported language in the first release.
- The UI, BFF, and core backend are three separate deployable services with independent runtime configuration, health monitoring, release, rollback, and scaling lifecycles.
- All three services run on the existing non-production Azure AKS platform; Azure-managed backing services are preferred over in-cluster stateful components.
- The UI service owns presentation, the BFF owns UI-oriented session mediation and orchestration, and the core backend owns authoritative authorization, business rules, and persistent data.
- The UI communicates with the BFF; it does not directly call personalized core-backend interfaces.
- The backend remains the authoritative owner of business rules and persistent learning data; the UI does not connect directly to backend storage.
- Each deployed environment provides approved UI-to-BFF and BFF-to-backend destinations and trust configuration outside source code.
- Active-session convenience state may be temporary; cross-device history, long-term drafts, and user-specific saved dashboards are outside this feature.
- The first release supports current mainstream desktop and mobile browsers used by the internal pilot.
- Pilot usability evaluation uses exactly 20 eligible internal employees, includes desktop and mobile-width scenarios, records task completion independently from satisfaction ratings, and excludes anyone who contributed to implementation. Additional observations may be reported separately but do not change the SC-001, SC-007, SC-011, or SC-015 through SC-017 denominator.
- Visual branding uses a clear, professional default presentation; a formal design system or custom brand package is not required for the first release.
- Advanced analytics, notifications, content authoring, and administrative reporting are outside this feature.
- Hands-on environments are operated by external providers; creating or managing temporary lab infrastructure is outside the first release.
- The initial lab-provider allowlist is empty. A provider becomes eligible only after approval by members of the configured Learning Content Owners and Application Security Reviewers Entra groups. Group object IDs are supplied as environment configuration and are not embedded in source code.
- The Jenkins controller runs locally at `http://localhost:8080` and its
  existing Jenkins Azure cloud node named `azure` creates ephemeral
  publisher and deployer agents in the configured resource group. Each template
  uses a distinct user-assigned managed identity for its ACR or AKS scope. The
  existing Jenkins Azure cloud-node configuration provisions and connects the
  agents; no new VPN, public controller endpoint, or inbound agent connection is
  introduced by this feature. The existing cloud-provisioning service principal
  is the only controller-held Azure credential and is excluded from ACR push and
  AKS deployment access; the controller stores no kubeconfig or additional
  Azure delivery credential.
- Competitive leaderboards, peer rankings, points, and streak-based rewards are outside the first release.
