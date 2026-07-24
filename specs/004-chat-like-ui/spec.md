# Feature Specification: Chat-like Career Guidance UI

**Feature Branch**: `005-chat-like-ui`  
**Created**: 2026-07-22  
**Status**: Draft  
**Input**: User description: "generate a chat like UI/UX"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask for career guidance (Priority: P1)

As a career learner, I want to ask a question in a familiar chat interface and receive a clear answer so that I can make progress without learning a complex workflow.

**Why this priority**: Asking and receiving guidance is the core value of the product and must stand alone as a usable MVP.

**Independent Test**: Open the application, enter a question, submit it, and verify that the conversation shows the user message followed by an assistant response or a clear recoverable error.

**Acceptance Scenarios**:

1. **Given** the chat view is ready, **When** the user enters a non-empty question and submits it, **Then** the question appears as a user message and the assistant response appears in the same conversation.
2. **Given** a response is being prepared, **When** the user views the conversation, **Then** a visible pending state communicates that work is in progress and prevents accidental duplicate submission.
3. **Given** the guidance service cannot respond, **When** the request fails, **Then** the conversation shows a concise error with an option to retry without losing the question.

### User Story 2 - Navigate and understand a conversation (Priority: P2)

As a learner, I want to distinguish my messages from assistant messages and review recent context so that the conversation remains understandable as it grows.

**Why this priority**: Clear context is necessary for trust and makes the primary guidance flow useful beyond a single exchange.

**Independent Test**: Populate a conversation with multiple exchanges and verify message ordering, speaker distinction, timestamps or equivalent context cues, and usable scrolling on desktop and narrow screens.

**Acceptance Scenarios**:

1. **Given** multiple exchanges exist, **When** the user reviews the conversation, **Then** messages are ordered chronologically and each message has an unambiguous speaker identity.
2. **Given** the conversation exceeds the visible area, **When** the user scrolls, **Then** earlier messages remain available and the composer remains discoverable.
3. **Given** an assistant response contains structured guidance, **When** it is displayed, **Then** headings, lists, links, and emphasis remain readable and visually distinct from surrounding text.

### User Story 3 - Recover, reset, and use the UI accessibly (Priority: P3)

As a learner using different devices or assistive tools, I want accessible controls and safe recovery actions so that I can continue or restart a conversation confidently.

**Why this priority**: Accessibility and recovery protect task completion and reduce frustration, while remaining separable from the core exchange flow.

**Independent Test**: Use keyboard-only navigation and a narrow viewport to send, retry, clear, and focus the composer; verify visible focus, readable labels, and confirmation before destructive reset.

**Acceptance Scenarios**:

1. **Given** the user navigates with a keyboard, **When** they move through the chat controls, **Then** focus order is logical, focus is visible, and every action has an accessible name.
2. **Given** the user chooses to clear the conversation, **When** the action is initiated, **Then** the UI asks for confirmation and preserves the conversation if the user cancels.
3. **Given** the viewport is narrow or text is enlarged, **When** the user interacts with the chat, **Then** content remains readable without horizontal scrolling and the composer remains usable.

## Edge Cases

- The user submits only whitespace or exceeds the supported message length; the UI explains the constraint and does not create an empty message.
- The user loses connectivity during a request; the pending state resolves to an actionable retry state and retains the draft.
- A response contains unsafe or unsupported content; it is presented as plain, safely rendered content and does not execute active content.
- The conversation is very long; the UI preserves responsiveness and communicates when older context is no longer loaded.
- A session expires while the user is composing; the draft remains visible and the user receives a clear sign-in or recovery action.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Home page MUST provide the dedicated chat view with a conversation area and a message composer; no separate chat route is required.
- **FR-002**: Users MUST be able to enter, edit, submit, and clear a message draft before submission.
- **FR-003**: The product MUST display user and assistant messages in chronological order with visually distinct speaker attribution.
- **FR-004**: The product MUST show an explicit pending state while an assistant response is being prepared and MUST prevent duplicate submissions for the same draft.
- **FR-005**: The product MUST show recoverable failure feedback with a retry action that preserves the failed question.
- **FR-006**: The product MUST preserve the active conversation context while the user remains in the session, including route changes and recoverable refreshes, and MUST provide a clearly labeled reset action.
- **FR-007**: The product MUST require confirmation before clearing the active conversation.
- **FR-008**: The product MUST present the existing BFF guidance DTO with readable hierarchy for `topicSummary`, `currentLevelFit`, `practicalNextAction`, `suggestions`, `commonPitfalls`, `relatedTopics`, and validated `labReferences`.
- **FR-009**: The product MUST provide accessible names, logical keyboard order, visible focus, and status announcements for composer, send, retry, reset, and pending states.
- **FR-010**: The product MUST remain usable on narrow screens and at enlarged text sizes without horizontal scrolling for primary interactions.
- **FR-011**: The product MUST validate empty, whitespace-only, and drafts longer than 2,000 characters before submission, reject over-limit input without truncation, and explain how to correct invalid input.
- **FR-012**: The product MUST render assistant responses as plain text plus the FR-008 structured fields; only `https://` lab-reference links may be interactive, and active or executable markup MUST never run in the user interface.
- **FR-013**: The product MUST communicate session expiry or authorization failure without discarding an unsent draft.
- **FR-014**: Guidance, Learning, Progress, and Roadmap views MUST provide consistent contextual navigation, including a way to return to the roadmap and continue the current learning path.
- **FR-015**: Completing a learning step, milestone assessment, or progress check-in MUST update the shared roadmap state consumed by Home, Roadmap, Guidance, Learning, and Progress views without requiring a full-page refresh.
- **FR-016**: The UI MUST use a shared roadmap/session data model and fixture set for development and acceptance scenarios so that milestone titles, completion states, scores, and next actions do not diverge across pages.
- **FR-017**: Each page MUST provide designed loading, empty, unavailable-service, and recoverable-error states that preserve user input and offer a clear next action.
- **FR-018**: The product MUST provide a consistent page-level context indicator identifying the active roadmap topic and the user’s current position in the learning journey.
- **FR-019**: The product MUST provide a milestone assessment flow that records pass/fail outcome, passing score, achievement tier, and evidence used to update roadmap progress.
- **FR-020**: The Roadmap view MUST remain usable on narrow screens with ten or more milestones; milestone markers MUST remain distinguishable through responsive layout, alternative labels, or an accessible list representation.
- **FR-021**: Automated accessibility coverage MUST verify keyboard focus order, visible focus, status announcements, and operability for milestone links, knowledge checks, check-in actions, and assessment controls.

### Key Entities

- **Conversation**: The active guidance exchange, including ordered messages and a resettable session context.
- **Message**: A user or assistant contribution with content, speaker, creation order, and delivery state.
- **Draft**: The user’s editable, unsent text and its validation state.
- **Delivery State**: The lifecycle of a message exchange, such as ready, pending, delivered, failed, or retryable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of first-time pilot users can submit a question and identify the assistant response without assistance.
- **SC-002**: The primary question-to-response flow is completed in no more than three intentional user actions after the user focuses the composer.
- **SC-003**: At least 95% of tested failed requests preserve the question and expose a working retry path.
- **SC-004**: Keyboard-only testers can reach and operate every primary chat action with no blocked interaction in 100% of acceptance runs.
- **SC-005**: On supported narrow-screen viewports, 100% of primary chat actions remain usable without horizontal scrolling.
- **SC-006**: At least 90% of pilot users rate message ownership, pending status, and recovery actions as understandable in post-task feedback.
- **SC-007**: Completing a Learning step or assessment is reflected in Home, Roadmap, and Progress views within one second without a full-page refresh in 95% of acceptance runs.
- **SC-008**: Users can move between Guidance, Learning, Progress, and Roadmap views and return to the active topic in no more than two intentional actions from any page.
- **SC-009**: Every page exposes a visible, actionable loading, empty, or error state when its backing service is delayed or unavailable in 100% of tested scenarios.
- **SC-010**: At least 95% of development and acceptance scenarios use the same shared roadmap fixture values across all page surfaces.
- **SC-011**: At least 90% of users can identify the current topic, next action, and milestone readiness state within ten seconds of opening the application.
- **SC-012**: Assessment completion records the score and achievement tier and updates the corresponding milestone state in 100% of successful assessment runs.
- **SC-013**: On the smallest supported viewport, all ten roadmap milestones remain identifiable and usable without horizontal scrolling in 100% of accessibility runs.
- **SC-014**: Keyboard-only testers can operate every cross-page navigation, knowledge check, check-in, and assessment control with no blocked interaction in 100% of acceptance runs.

## Assumptions

- The existing application session and guidance services remain the source of identity, authorization, and assistant responses.
- Version one targets a single active conversation per session; conversation search, sharing, attachments, voice input, and multi-user rooms are out of scope.
- Drafts are limited to 2,000 characters. Over-limit input is rejected without truncation so the learner can edit the original text.
- The pilot is reviewed on current desktop and mobile-sized browsers with modern accessibility support.
- The chat view will use the application’s existing visual language while introducing chat-specific hierarchy, status, and recovery patterns.
- Roadmap, Guidance, Learning, and Progress share one authoritative in-session learning state; development mocks and test fixtures represent that same state rather than independent page examples.
- Home (the primary chat surface), Roadmap, Guidance, Learning, and Progress are the five coordinated UI surfaces; the shared learner-state provider remains mounted above all route components.
- Milestone exams pass at 80%. Achievement tiers are derived consistently: bronze 80-89%, silver 90-94%, and gold 95-100%; failed scores below 80% have no medal.
