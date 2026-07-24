# UX Requirements Checklist: Chat-like Career Guidance UI

**Purpose**: Validate that the Home-first chat and learning-journey requirements are complete, clear, consistent, and measurable.
**Created**: 2026-07-24
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 Are the Home chat surface, composer, conversation area, and reset scope explicitly defined? [Completeness, Spec §FR-001–FR-007]
- [X] CHK002 Are all five coordinated surfaces and their contextual-navigation relationships identified? [Completeness, Spec §FR-014, FR-018]
- [X] CHK003 Are requirements defined for loading, empty, unavailable-service, validation, and recoverable-error states on every surface? [Completeness, Spec §FR-017, SC-009]
- [X] CHK004 Are assessment outcome, score, tier, and evidence requirements all defined together? [Completeness, Spec §FR-019, SC-012]
- [X] CHK005 Are the shared roadmap fixture and authoritative state ownership requirements documented for both mock and service-backed scenarios? [Completeness, Spec §FR-015–FR-016, SC-010]

## Requirement Clarity

- [X] CHK006 Is “active conversation context” explicitly defined to include route changes, refresh recovery, and session expiry? [Clarity, Spec §FR-006, FR-013]
- [X] CHK007 Is the 2,000-character draft limit and reject-without-truncation rule unambiguous? [Clarity, Spec §FR-011]
- [X] CHK008 Are the BFF guidance fields and their expected readable hierarchy named without introducing an alternate response schema? [Clarity, Spec §FR-008, FR-012]
- [X] CHK009 Are the bronze, silver, gold, and failed score ranges explicit and mutually exclusive? [Clarity, Spec §FR-019, Assumptions]
- [X] CHK010 Is “current topic,” “next action,” and “milestone readiness” defined consistently across Home, Roadmap, Guidance, Learning, and Progress? [Clarity, Spec §FR-018, SC-011]

## Requirement Consistency

- [X] CHK011 Do the Home-first chat requirement and the no-separate-chat-route boundary remain consistent across the specification, plan, and tasks? [Consistency, Spec §FR-001]
- [X] CHK012 Do the structured-guidance requirements match the existing BFF DTO and the safe-link restriction? [Consistency, Spec §FR-008, FR-012]
- [X] CHK013 Are the five-surface navigation requirements consistent with the route list and the usability protocol? [Consistency, Spec §FR-014, SC-008]
- [X] CHK014 Are the score thresholds, passing threshold, medal labels, and progress-state requirements consistent across roadmap, learning, and progress descriptions? [Consistency, Spec §FR-019, SC-012]

## Acceptance Criteria Quality

- [X] CHK015 Can the primary question-to-response flow be objectively evaluated against the three-action limit? [Measurability, Spec §SC-002]
- [X] CHK016 Are retry preservation and response identification criteria measurable without relying on subjective interpretation? [Measurability, Spec §SC-001, SC-003]
- [X] CHK017 Is the one-second cross-page synchronization target defined with a clear start and end event? [Clarity, Spec §SC-007]
- [X] CHK018 Are the 90% pilot comprehension/rating outcomes explicitly framed as exploratory one-participant PoC evidence? [Acceptance Criteria, Spec §SC-001, SC-006]
- [X] CHK019 Are “smallest supported viewport” and “enlarged text” test conditions concretely identified? [Measurability, Spec §SC-005, SC-013]

## Scenario and Edge-Case Coverage

- [X] CHK020 Are primary, alternate, exception, and recovery requirements present for successful guidance, service failure, retry, reset, and session expiry? [Coverage, Spec §User Stories 1–3, Edge Cases]
- [X] CHK021 Are whitespace-only, over-limit, unsafe-content, long-conversation, connectivity-loss, and session-expiry cases all addressed with a user-preserving outcome? [Coverage, Spec §Edge Cases, FR-011–FR-013]
- [X] CHK022 Are partial state-update failures defined so that a completed assessment cannot be shown as synchronized before authoritative state is available? [Recovery, Spec §FR-015, SC-007]
- [X] CHK023 Are empty roadmaps, missing current topics, unavailable labs, and absent assessment scores explicitly handled? [Edge Case, Spec §FR-017–FR-019]

## Accessibility and Responsive Requirements

- [X] CHK024 Are accessible names, focus order, visible focus, announcements, and error associations specified for every primary chat and learning control? [Completeness, Spec §FR-009, FR-021]
- [X] CHK025 Are milestone markers required to have equivalent textual labels and a usable narrow-screen representation? [Coverage, Spec §FR-020, SC-013]
- [X] CHK026 Are keyboard-only and screen-reader expectations stated for contextual navigation, knowledge checks, check-ins, and assessment controls? [Accessibility, Spec §FR-021, SC-014]
- [X] CHK027 Are no-horizontal-scroll requirements scoped to primary content and all supported viewport/text-size conditions? [Clarity, Spec §FR-010, SC-005]

## Dependencies and Assumptions

- [X] CHK028 Are BFF endpoint ownership, browser-to-BFF boundaries, contract versioning, and guidance catalog compatibility documented as requirements dependencies? [Dependency, Spec §Assumptions, Plan §Technical Context]
- [X] CHK029 Is the distinction between LearnerState presentation projection and durable BFF/core ownership explicit? [Assumption, Spec §Assumptions, Data Model]
- [X] CHK030 Are the single-active-conversation, no-browser-persistence, and one-participant PoC boundaries visible to reviewers? [Assumption, Spec §Assumptions, usability-results.md]

## Notes

- This checklist validates requirement quality, not implementation behavior.
- Items should be reviewed before implementation and revisited when the BFF contract or user journey changes.
