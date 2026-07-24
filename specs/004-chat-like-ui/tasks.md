# Tasks: Chat-like Career Guidance UI

**Input**: Design documents from `/specs/004-chat-like-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup

**Purpose**: Establish the feature modules and shared test fixtures without changing
the existing browser-to-BFF boundary.

- [X] T001 [P] Add feature-local UI state types and exports in `ui/src/contracts/learner-state.ts`
- [X] T002 [P] Add the deterministic ten-milestone fixture shared by all mock pages in `ui/src/mocks/learner-fixture.ts`
- [X] T003 [P] Add baseline learner-state and assessment unit-test scaffolds in `ui/tests/unit/learner-state.test.ts`
- [X] T004 [P] Add the feature route journey fixture helpers in `ui/tests/e2e/chat-like-ui.spec.ts`

## Phase 2: Foundational Shared State

**Purpose**: Blocking infrastructure required by every user story.

- [X] T005 Implement the in-memory LearnerState provider, reducer, and auth-epoch invalidation in `ui/src/app/learner-state-context.tsx`
- [X] T006 Implement roadmap/session DTO normalization and achievement-tier derivation in `ui/src/app/learner-state-mappers.ts`
- [X] T007 Implement authoritative refresh and post-mutation synchronization through existing BFF operations in `ui/src/app/learner-state-client.ts`
- [X] T008 [P] Add shared contextual navigation and active-topic indicator components in `ui/src/components/LearnerContextNav.tsx`
- [X] T009 [P] Add reusable loading, empty, unavailable, error, and status-announcement components in `ui/src/components/AsyncState.tsx`
- [X] T010 Mount LearnerStateProvider above registered routes and invalidate it on session/auth-epoch changes in `ui/src/app/App.tsx`
- [X] T011 Add reducer, mapper, refresh, invalidation, and tier-policy tests in `ui/tests/unit/learner-state.test.ts`

**Checkpoint**: Shared state can load one fixture or authoritative BFF snapshot and
publish complete updates to all subscribed views.

## Phase 3: User Story 1 - Ask for career guidance (Priority: P1) MVP

**Goal**: A learner can submit a question in the chat composer and see a structured
assistant response, pending state, or retryable failure.

**Independent Test**: Open the chat view, submit a non-empty question, and verify the
user message plus assistant result; mock a 503 and verify the draft and retry action.

### Tests for User Story 1

- [X] T012 [P] [US1] Add component tests for message ordering, pending state, duplicate suppression, and successful assistant response in `ui/tests/unit/chat-composer.test.tsx`
- [X] T013 [P] [US1] Add Playwright success, validation, 503 retry, and preserved-draft journeys in `ui/tests/e2e/chat-like-ui.spec.ts`

### Implementation for User Story 1

- [X] T014 [US1] Implement the chat conversation model and delivery-state reducer through the shared LearnerState provider in `ui/src/app/learner-state-context.tsx` and `ui/src/components/chat/useChatConversation.ts`
- [X] T015 [US1] Implement the labelled Home composer, whitespace/length validation, and submit controls in `ui/src/components/chat/ChatComposer.tsx` and `ui/src/app/App.tsx`
- [X] T016 [US1] Implement semantic conversation log, safe structured guidance rendering, pending status, and retry feedback in `ui/src/components/chat/ChatConversation.tsx` and `ui/src/app/App.tsx`
- [X] T017 [US1] Wire the Home chat guidance submission to the existing BFF guidance contract with idempotent request handling in `ui/src/components/chat/useChatConversation.ts`
- [X] T018 [US1] Keep `/` as the default Home chat surface and expose its composer/conversation without adding a separate chat route in `ui/src/app/App.tsx`
- [X] T019 [US1] Add chat layout, pending/error, focus, and narrow-screen styles in `ui/src/styles/app.css`

**Checkpoint**: US1 is independently demonstrable as the MVP.

## Phase 4: User Story 2 - Navigate and understand a conversation (Priority: P2)

**Goal**: Learners can distinguish speakers, review chronological context, and move
between the learning surfaces without losing the active topic.

**Independent Test**: Populate multiple exchanges, verify chronological semantic
markup and scrolling at desktop and 320px, then navigate to and back from Roadmap,
Guidance, Learning, and Progress.

- [X] T020 [P] [US2] Add Playwright cross-page navigation and responsive conversation journeys in `ui/tests/e2e/navigation-session.spec.ts`
- [X] T021 [P] [US2] Add component tests for message speaker labels, timestamps/context cues, and live-region behavior in `ui/tests/unit/chat-conversation.test.tsx`
- [X] T022 [US2] Add shared context navigation and current-topic/next-action content to Home in `ui/src/app/App.tsx`, Roadmap in `ui/src/features/roadmap/RoadmapPage.tsx`, Guidance in `ui/src/features/guidance/GuidancePage.tsx`, Learning in `ui/src/features/learning/LearningPage.tsx`, and Progress in `ui/src/features/progress/ProgressPage.tsx` using `ui/src/components/LearnerContextNav.tsx`
- [X] T023 [US2] Refactor page data hooks to consume LearnerState snapshots and publish authoritative roadmap/progress updates in `ui/src/features/roadmap/useRoadmap.ts`, `ui/src/features/learning/useLearningSession.ts`, and `ui/src/features/progress/useProgress.ts`
- [X] T024 [US2] Normalize GET roadmap responses in `bff/src/contracts/progress.ts` and `bff/src/routes/roadmaps.ts`, and distinguish transient failures from not-found before learning-session mutations in `ui/src/features/learning/useLearningSession.ts`
- [X] T025 [US2] Add conversation scrolling, semantic list/log, structured content, and contextual navigation styles in `ui/src/styles/app.css`

**Checkpoint**: US1 and US2 remain independently usable and share one active-topic
snapshot without a full-page refresh.

## Phase 5: User Story 3 - Recover, reset, and use the UI accessibly (Priority: P3)

**Goal**: Learners can safely reset, recover from session/service failures, complete
knowledge checks and assessments, and operate all primary controls by keyboard.

**Independent Test**: Use keyboard-only navigation at 320px and enlarged text to send,
retry, reset, complete a check, and submit an assessment; verify focus, announcements,
confirmation, score/tier/evidence, and preserved drafts.

- [X] T026 [P] [US3] Add unit tests for draft preservation, reset confirmation, session expiry, field errors, and assessment tier transitions in `ui/tests/unit/recovery-accessibility.test.tsx`
- [X] T027 [P] [US3] Add Playwright keyboard, focus, live-region, 320px, enlarged-text, check-in, and assessment journeys in `ui/tests/e2e/accessibility.spec.ts`
- [X] T028 [US3] Implement reset confirmation dialog and session-expiry recovery that preserves unsent drafts in `ui/src/components/chat/ChatConversation.tsx` and `ui/src/components/SessionTimeoutDialog.tsx`
- [X] T029 [US3] Add knowledge-check answer validation, skip behavior, feedback, and completion summary in `ui/src/features/learning/LearningPage.tsx` and `ui/src/features/learning/KnowledgeCheck.tsx`
- [X] T030 [US3] Add assessment result normalization, evidence capture, passing score, and bronze/silver/gold tier rendering in `ui/src/features/learning/AssessmentResult.tsx` and `ui/src/app/learner-state-mappers.ts`
- [X] T031 [US3] Refresh authoritative learning session, roadmap, progress, and next-action data after step completion, assessment submission, and progress check-in in `ui/src/app/learner-state-client.ts`, `ui/src/features/learning/useLearningSession.ts`, and `ui/src/features/progress/useProgress.ts`
- [X] T032 [US3] Add responsive accessible milestone list fallback with textual tier labels and distinguishable markers in `ui/src/features/roadmap/RoadmapPage.tsx` and `ui/src/styles/app.css`
- [X] T033 [US3] Add field associations, visible focus, status/alert announcements, and focus restoration in `ui/src/components/AsyncState.tsx`, `ui/src/components/chat/ChatComposer.tsx`, `ui/src/components/chat/ChatConversation.tsx`, `ui/src/features/learning/LearningPage.tsx`, and `ui/src/styles/global.css`

**Checkpoint**: All three stories are independently testable with no primary-content
horizontal scrolling and no blocked keyboard interaction.

## Phase 6: Polish and Cross-Cutting Verification

- [X] T034 [P] Add contract tests for normalized roadmap GET payloads and assessment state mappings in `bff/tests/contract/roadmaps.test.ts` and `ui/tests/unit/learner-state.test.ts`
- [X] T035 [P] Add cross-page synchronization assertions for Home, Roadmap, and Progress within one second in `ui/tests/e2e/navigation-session.spec.ts`
- [X] T036 [P] Add loading, empty, unavailable, and recoverable-error assertions for Home, Roadmap, Guidance, Learning, and Progress in `ui/tests/e2e/chat-like-ui.spec.ts`
- [X] T037 [P] Audit safe rendering and ensure assistant content cannot execute active markup in `ui/src/components/chat/ChatConversation.tsx` and `ui/tests/unit/chat-conversation.test.tsx`
- [X] T038 Update feature quickstart and acceptance evidence instructions in `specs/004-chat-like-ui/quickstart.md`
- [X] T039 Run `npm --prefix ui run typecheck`, `npm --prefix ui test -- --run`, and `npm --prefix ui run test:e2e`; record results in `specs/004-chat-like-ui/verification.md`
- [ ] T040 [P] Run the one-participant PoC usability protocol for SC-001 and SC-006: submit a question, identify the assistant response, retry a failed request, and rate ownership/pending/recovery from 1-5; record participant count, task outcomes, ratings, and limitations in `specs/004-chat-like-ui/usability-results.md`

## Dependencies and Execution Order

### Phase Dependencies

- Setup (Phase 1) has no dependencies.
- Foundational (Phase 2) depends on Setup and blocks all story phases.
- US1 (Phase 3) depends on Foundational and is the MVP.
- US2 (Phase 4) depends on Foundational; it may proceed in parallel with US1 after shared state is complete.
- US3 (Phase 5) depends on Foundational and the learning surfaces from US2.
- Polish (Phase 6) depends on the stories being implemented.

### Parallel Opportunities

- T001-T004 can run in parallel.
- T008-T009 and T011 can run in parallel after T005-T007 define shared interfaces.
- T012-T013, T020-T021, and T026-T027 are parallel test tracks.
- T034-T038 are parallel after the relevant story implementation.

## Implementation Strategy

1. Complete Setup and Foundational phases; validate the shared state reducer.
2. Deliver US1 as the MVP and stop for an independent chat demonstration.
3. Add US2 navigation and synchronization, then verify all five page surfaces.
4. Add US3 recovery, assessment, responsive fallback, and accessibility hardening.
5. Run the final cross-cutting verification suite and record evidence.

## Traceability Summary

- FR-001 through FR-013: T012-T019 and T026-T033
- FR-014 through FR-018: T005-T011, T020-T025
- FR-019 through FR-021: T026-T035
- SC-001 through SC-006: T012-T019, T026-T033
- SC-007 through SC-014: T020-T039
- SC-001 and SC-006 pilot outcomes: T040
