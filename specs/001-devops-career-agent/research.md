# Research: DevOps Career Agent

## Decision 1: Internal web-service assistant with chat-style interaction

- **Decision**: Build the first release as an internal web service that can be
  embedded in a chat or portal experience.
- **Rationale**: The feature needs an interactive back-and-forth flow to gather
  employee context, present a roadmap, and revisit progress later.
- **Alternatives considered**: CLI-only assistant, static questionnaire, or
  document generator. These would be less natural for iterative career guidance.

## Decision 2: Modular skill catalog with extensible topic taxonomy

- **Decision**: Represent DevOps knowledge as a structured catalog of skill
  areas, guidance bundles, and progress milestones.
- **Rationale**: The user explicitly wants additional topics to be added later,
  so the core flow must be stable while content grows.
- **Alternatives considered**: Hard-coded prompt branches and one-off topic
  pages. Those approaches are brittle and make expansion expensive.

## Decision 3: Profile, roadmap, and progress checkpoints as first-class data

- **Decision**: Persist employee profile inputs, the generated roadmap, and
  follow-up check-ins.
- **Rationale**: Career guidance becomes more useful when the assistant can
  adapt recommendations instead of restarting from scratch.
- **Alternatives considered**: Stateless sessions only. That would lose context
  and make progress reviews impossible.

## Decision 4: Strict separation from HR decisions

- **Decision**: Treat the assistant as a guidance tool, not an HR authority.
- **Rationale**: The feature is about employee growth, not evaluation or
  compensation decisions.
- **Alternatives considered**: Blending career advice with policy or performance
  judgments. That would increase risk and reduce trust.

## Decision 5: Test around conversation outcomes, not model internals

- **Decision**: Validate the feature with user-story-level tests for roadmap
  quality, topic guidance, and progress updates.
- **Rationale**: The business outcome matters more than the specific model
  behavior.
- **Alternatives considered**: Unit tests focused on prompt text alone. Those do
  not prove the assistant is useful.
