# Tasks: DevOps Career Agent

**Input**: Design documents from `/specs/001-devops-career-agent/`
**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, quickstart.md

**Verification**: The implementation plan requires pytest service-level and
conversation-flow coverage. Each user story includes explicit validation tasks
so the implementation remains independently testable.

**Organization**: Tasks are grouped by user story so each story can be built,
validated, and delivered independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and base repository structure

- [ ] T001 Create the project package skeleton in `src/agent/`, `src/skills/`,
  `src/knowledge/`, `src/storage/`, `src/api/`, `tests/unit/`,
  `tests/integration/`, and `tests/contract/`
- [ ] T002 Initialize Python project metadata, dependency declarations, and
  build scripts in `pyproject.toml`
- [ ] T003 [P] Add repository hygiene and local-development defaults in
  `.gitignore` and `.env.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure that must exist before any user story work
can be completed

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Define the shared feature schemas for employee profiles, skill
  areas, roadmaps, roadmap steps, and progress check-ins in
  `src/knowledge/schemas.py`
- [ ] T005 [P] Implement database connectivity, session handling, and schema
  bootstrap code in `src/storage/database.py`
- [ ] T006 [P] Implement application settings, structured logging, and shared
  error types in `src/agent/settings.py`, `src/agent/logging.py`, and
  `src/agent/errors.py`
- [ ] T007 Create the API application bootstrap and router registration in
  `src/api/app.py` and `src/api/routes.py`
- [ ] T008 Implement career-guidance boundary rules that detect HR,
  performance-management, and employee-evaluation requests in
  `src/agent/policy.py`
- [ ] T009 Add pytest coverage for HR and performance-management boundary
  prompts in `tests/unit/agent/test_policy.py` and
  `tests/integration/test_hr_boundary_flow.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in
parallel

---

## Phase 3: User Story 1 - Career Roadmap Creation (Priority: P1) 🎯 MVP

**Goal**: Turn an employee's current role, target role, and time constraints
into a personalized DevOps career roadmap.

**Independent Test**: An employee can provide basic career context and receive
an actionable roadmap without needing any other story.

### Implementation for User Story 1

- [ ] T010 [P] [US1] Define roadmap intake and response contracts in
  `src/agent/contracts/roadmap.py`, including required recommendation fields:
  skill area, experience-level fit, time horizon, concrete next action, and
  reason the step matters
- [ ] T011 [US1] Implement the roadmap synthesis service that converts employee
  context into prioritized milestones with skill area, experience-level fit,
  time horizon, concrete next action, and reason-it-matters fields in
  `src/agent/roadmap_service.py`
- [ ] T012 [P] [US1] Implement employee profile and roadmap persistence in
  `src/storage/roadmap_repository.py`
- [ ] T013 [US1] Expose the roadmap creation flow through the API in
  `src/api/routes/roadmap.py`
- [ ] T014 [US1] Add roadmap presentation formatting and follow-up prompt
  generation that consistently displays each recommendation's skill area,
  experience-level fit, time horizon, concrete next action, and reason it
  matters in `src/agent/roadmap_presenter.py`
- [ ] T015 [US1] Add pytest coverage for roadmap intake validation, required
  recommendation fields, roadmap synthesis, and single-session roadmap creation in
  `tests/unit/agent/test_roadmap_service.py` and
  `tests/integration/test_roadmap_flow.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and
usable on its own

---

## Phase 4: User Story 2 - Skill-Specific Guidance (Priority: P2)

**Goal**: Answer focused questions about individual DevOps topics with guidance
that reflects the employee's current level and future growth path.

**Independent Test**: An employee can ask about one DevOps topic and get a
useful answer without needing a full roadmap first.

### Implementation for User Story 2

- [ ] T016 [P] [US2] Build the extensible skill catalog loader and topic
  registry in `src/skills/catalog.py`
- [ ] T017 [US2] Implement topic guidance synthesis for a named skill area in
  `src/agent/skill_guidance_service.py`
- [ ] T018 [P] [US2] Seed the initial skill content for Jenkins, Azure DevOps,
  GitLab CI, Kubernetes, ArgoCD, Helm, .NET, MSI, Advanced Installer, Windows,
  OpenShift, Linux, Docker, Docker Compose, certificates, Vault, Ansible,
  Terraform, VMware, AWS, MLOps, and SecOps in `src/knowledge/topics/`
- [ ] T019 [US2] Implement topic normalization, unsupported-topic fallback, and
  future-extension rules in `src/skills/resolver.py`, including closest
  supported-topic suggestions and no detailed guidance for unsupported topics
- [ ] T020 [US2] Expose the skill guidance flow through the API in
  `src/api/routes/skills.py`
- [ ] T021 [US2] Add pytest coverage for topic resolution, unsupported-topic
  fallback behavior, skill catalog loading, and standalone skill guidance in
  `tests/unit/skills/test_catalog.py`, `tests/unit/skills/test_resolver.py`, and
  `tests/integration/test_skill_guidance_flow.py`

**Checkpoint**: At this point, User Stories 1 and 2 should both work
independently

---

## Phase 5: User Story 3 - Progress Review and Adaptation (Priority: P3)

**Goal**: Let an employee revisit prior guidance, record completed steps, and
receive an updated roadmap as goals and progress change.

**Independent Test**: An employee can return later, submit progress, and get a
revised plan without rebuilding everything from scratch.

### Implementation for User Story 3

- [ ] T022 [P] [US3] Define progress check-in request and response contracts in
  `src/agent/contracts/progress.py`
- [ ] T023 [US3] Implement progress checkpoint persistence in
  `src/storage/progress_repository.py`
- [ ] T024 [US3] Implement roadmap revision logic that updates recommendations
  from completed steps in `src/agent/progress_service.py`
- [ ] T025 [P] [US3] Expose the progress review and update flow in
  `src/api/routes/progress.py`
- [ ] T026 [US3] Preserve roadmap history and revised recommendation summaries
  in `src/agent/roadmap_revision.py`
- [ ] T027 [US3] Add pytest coverage for progress checkpoint persistence,
  roadmap revision, and returning an updated plan without restarting in
  `tests/unit/agent/test_progress_service.py` and
  `tests/integration/test_progress_flow.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T028 [P] Update implementation notes, operator guidance, and
  proof-of-concept security/privacy scope exclusions in
  `specs/001-devops-career-agent/quickstart.md`
- [ ] T029 [P] Refine roadmap copy and topic descriptions for consistency in
  `src/agent/roadmap_presenter.py` and `src/knowledge/topics/`
- [ ] T030 Add integration wiring, smoke-validation helpers, and response-time
  checks for roadmap creation, skill guidance, progress review, and HR-boundary
  handling in `src/api/app.py`, `src/api/routes.py`,
  `tests/integration/test_smoke_flows.py`, and
  `tests/integration/test_response_time_targets.py`
- [ ] T031 Review and normalize repository documentation references in
  `AGENTS.md` and `specs/001-devops-career-agent/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user
  stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel if staffed
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - no
  dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - may reuse the
  roadmap context but must remain independently useful
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - may reuse
  persisted roadmap data but must remain independently useful

### Within Each User Story

- Shared foundation before story-specific implementation
- Data/contracts before services
- Services before API wiring
- Presentation and revision logic after core service behavior
- Story complete before moving to the next priority

### Parallel Opportunities

- `T003` can run in parallel with any other Setup task that does not touch the
  same files
- `T005` and `T006` can run in parallel after Setup
- Within User Story 1, `T010` and `T012` can run in parallel
- Within User Story 2, `T016` and `T018` can run in parallel
- Within User Story 3, `T022` and `T023` can run in parallel
- Polish tasks `T028` and `T029` can run in parallel

---

## Parallel Example: User Story 1

```text
Task: "Define roadmap intake and response contracts in src/agent/contracts/roadmap.py"
Task: "Implement employee profile and roadmap persistence in src/storage/roadmap_repository.py"
Task: "Add pytest coverage for roadmap intake validation, roadmap synthesis, and single-session roadmap creation"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate the roadmap creation flow on its own

### Incremental Delivery

1. Complete Setup + Foundational
2. Add User Story 1 and validate the roadmap workflow
3. Add User Story 2 and validate topic guidance independently
4. Add User Story 3 and validate progress-aware updates independently
5. Finish with polish tasks that improve consistency and operational clarity

### Parallel Team Strategy

1. One developer can complete the foundation while another prepares skill
   content
2. Once the foundation is complete, the three user stories can be worked in
   parallel by different developers
3. Merge polish work only after the story-level flows are stable

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to the specific user story for traceability
- Keep each story independently completable and testable
- Avoid vague tasks, same-file conflicts, and cross-story dependencies that
  break independence
