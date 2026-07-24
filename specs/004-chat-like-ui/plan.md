# Implementation Plan: Chat-like Career Guidance UI

**Branch**: `005-chat-like-ui` | **Date**: 2026-07-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-chat-like-ui/spec.md`

## Summary

Deliver a chat-first learner experience while preserving the existing Amarel-inspired
visual language and roadmap-centered journey. The UI remains a React/Vite SPA and
uses the existing browser-to-BFF contract boundary. A shared in-session learning
store will provide one authoritative roadmap, current-topic, milestone, assessment,
and next-action snapshot to Home, Roadmap, Guidance, Learning, and Progress. The
implementation adds resilient page states, contextual navigation, assessment
evidence, responsive milestone presentation, and automated accessibility coverage.

## Technical Context

**Language/Version**: TypeScript, React, and Vite on Node.js 24 LTS
**Primary Dependencies**: React Router, existing fetch-based BFF client, Vitest,
Testing Library, Playwright, ESLint
**Storage**: No new browser persistence; authoritative state remains in the BFF/core
learning APIs. Development fixtures are deterministic and shared by all page mocks.
**Testing**: TypeScript build/typecheck, Vitest unit/component tests, Playwright
responsive and accessibility journeys, existing contract-drift tests
**Target Platform**: Current and previous Chrome, Edge, Firefox, and Safari/WebKit;
320px-and-up responsive layouts; keyboard and screen-reader compatible
**Project Type**: React single-page web application backed by the existing BFF
**Performance Goals**: State updates visible across mounted views within one second
in 95% of acceptance runs; no avoidable full-page refresh; preserve existing BFF
roadmap/guidance timing budgets
**Constraints**: Browser calls only `/bff/v1`; no OAuth tokens in UI; preserve draft
on failures/session expiry; no primary-content horizontal scrolling; safe rendering;
visible focus and announced status changes; immutable existing contracts unless a
versioned contract change is required
**Scale/Scope**: Five coordinated views (Home as the primary chat surface, Roadmap,
Guidance, Learning, and Progress), one active learner session, ten or more
roadmap milestones, one shared fixture set, and up to 10 concurrent pilot users

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Spec, plan, and tasks describe the same scoped outcome.
- [x] User stories are independently testable and ordered by priority.
- [x] Unknowns are resolved from existing contracts and repository context.
- [x] Each story has a verification strategy in the test matrix below and in tasks.md.
- [x] Documentation and runtime guidance updates are included for shared state,
      fixtures, accessibility, and recovery behavior.
- [x] Added complexity is limited to a shared client-side state boundary and is
      required by FR-014 through FR-021.

## Project Structure

### Documentation (this feature)

```text
specs/004-chat-like-ui/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── verification.md
├── usability-results.md
├── contracts/
│   ├── ui-state-contract.md
│   └── assessment-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
ui/src/
├── app/                 # session bootstrap, routes, shared learner state
├── components/          # navigation, status, accessibility primitives
│   └── chat/            # Home chat controls and conversation rendering
├── contracts/           # generated BFF contract plus UI state types
├── features/
│   ├── guidance/
│   ├── learning/
│   ├── progress/
│   └── roadmap/
└── styles/
ui/tests/
├── unit/
└── e2e/
bff/src/contracts/       # existing versioned browser/core mappings
specs/004-chat-like-ui/   # feature design and acceptance artifacts
```

**Structure Decision**: Keep the feature in the existing UI feature modules and
add shared state/navigation primitives under `ui/src/app` and `ui/src/components`.
Reuse the existing BFF operations and generated contracts; introduce no direct
browser-to-core calls and no second persistence system.

## Phase 0: Research Findings

- Existing `RoadmapForm`, `RoadmapResult`, `GuidanceForm`, `useLearningSession`,
  `useProgress`, `PersistenceStatus`, and `route-registry` are the reusable seams.
- The authoritative BFF contract already supports `requestText`, clarification
  questions, progress check-ins, learning step completion, and review submission;
  no new chat payload or direct core endpoint is needed.
- `ProfileProvider` is intentionally in-memory. Shared roadmap state should use the
  same lifetime and be invalidated on auth-epoch changes; refresh reloads BFF data.
- Existing accessibility conventions require semantic logs/live regions, labelled
  controls, visible focus, field associations, and status/alert announcements.
- GET roadmap responses and post-assessment responses must be mapped/refetched as
  authoritative state before publishing cross-page updates; transient read failures
  must not trigger mutating auto-start behavior.

## Phase 1: Design

1. Add typed shared learner-state provider/store with deterministic fixture data for
   local mock mode and an adapter that refreshes existing BFF roadmap, learning,
   progress, and guidance resources.
2. Move contextual navigation and active-topic status into shared components so all
   five surfaces expose the same current topic, next action, and return path.
3. Model page states explicitly (`loading`, `ready`, `empty`, `unavailable`,
   `error`) and preserve drafts/last valid state through recoverable failures.
4. Add assessment/knowledge-check handling that records score, pass/fail, achievement
   tier, and evidence in shared state before notifying subscribers.
5. Render ten-milestone roadmaps as a responsive track plus an accessible list
   fallback; keep medal/tier labels textual for screen readers and small screens.
6. Verify with reducer/mapper unit tests, component keyboard/status tests, and
   Playwright journeys spanning all routes at desktop, 320px, and enlarged-text sizes.

## Delivery Sequence

- Foundation: shared types/store, fixture, route context, and state primitives.
- P1: chat composer, conversation states, retry/reset, safe rendering, session expiry.
- P2: contextual navigation and synchronized roadmap/topic surfaces.
- P3: learning checks, assessment evidence, progress check-in synchronization.
- Hardening: responsive milestone fallback, accessibility automation, docs and
  acceptance evidence.

## Open Decisions Resolved During Planning

- Shared state is an in-memory client cache synchronized from existing BFF endpoints;
  durable ownership remains in core/PostgreSQL through the BFF.
- Mock mode uses one fixture module imported by every page; it is not duplicated in
  individual components.
- Achievement tiers use one mapping function; the visual medal is paired with a text
  label and score where available. Passing is 80% or higher: bronze 80-89%, silver
  90-94%, and gold 95-100%; scores below 80% are failed.
- Assistant content is plain text plus validated structured fields; only validated
  HTTPS links are interactive and raw HTML is never injected.
- The assistant uses the existing BFF guidance DTO fields `topicSummary`,
  `currentLevelFit`, `practicalNextAction`, `suggestions`, `commonPitfalls`,
  `relatedTopics`, and validated `labReferences`, as defined by FR-008. LearnerState
  owns conversation lifecycle, draft, delivery, and recovery state; shared chat
  components rendered on Home own presentation and input interaction only. There is
  no separate `/chat` route.
- No new chat backend endpoint is invented. The composer uses existing guidance or
  roadmap `requestText` semantics and renders the structured result as an assistant
  message.

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Shared learner-state provider | FR-015/FR-016 require synchronized views without refresh | Per-page fetches and duplicated fixtures would diverge and cannot meet the consistency criterion |
| Responsive track plus accessible milestone list | FR-020 requires ten or more milestones to remain usable at 320px | A single horizontal track would create scrolling and inaccessible labels |

## Post-Design Constitution Check

- [x] Contracts preserve browser-to-BFF and BFF-to-core boundaries.
- [x] Shared state remains client-only while durable ownership remains in core.
- [x] Tests cover each story, synchronization, recovery, responsive behavior, and
      accessibility before implementation is considered complete.
- [x] No unresolved clarification items remain in this plan.
