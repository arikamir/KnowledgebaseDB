# Research: Chat-like Career Guidance UI

## Decision: Reuse existing BFF operations and DTOs

The composer will use the existing guidance and roadmap request semantics (`requestText`,
clarifying questions, and structured result fields). Learning, progress, and review
continue to use their existing versioned operations.

Rationale: `bff/src/contracts/*` and the generated BFF contract are the authoritative
browser boundary. A new chat endpoint would duplicate behavior and create a second
contract to secure, version, and test.

Alternatives considered: adding `/chat` to the BFF; rejected because the current
guidance operation already returns the structured assistant content needed by the UI.

## Decision: App-level in-memory learner state

Add a typed provider/store above registered routes. It holds the last validated roadmap,
current topic, next action, milestone scores/tiers, and pending refresh state. On an
authentication epoch change it is cleared; on a browser refresh it reloads authoritative
BFF data. It must not write tokens, IDs, or learning state to browser storage.

Rationale: the existing `ProfileProvider` and persistence rules intentionally avoid
durable browser state, while FR-015 requires same-session updates without page refresh.

Alternatives considered: independent page hooks or localStorage; rejected because they
permit divergent fixtures/stale views and violate the existing browser persistence
boundary.

## Decision: Explicit state and error taxonomy

Every page distinguishes loading, ready, empty, unavailable, validation, and retryable
error states. A transient GET failure never triggers a mutating fallback such as starting
a learning session. Drafts remain in memory until a successful submission or explicit
reset.

Rationale: this matches existing `PersistenceStatus`, stable problem codes, and the
failure-preservation requirements in the feature spec.

## Decision: Responsive track plus semantic milestone list

The ten-milestone visual track remains the branded view, while a responsive list exposes
the same milestones, labels, scores, and tier text for narrow screens and assistive tech.

Rationale: a single horizontal track cannot reliably fit ten items at 320px or provide
adequate accessible names.

## Decision: Authoritative post-mutation refresh

After learning-step completion, assessment submission, or progress check-in, refresh the
affected session and roadmap/progress/next-action resources before publishing the shared
state. Normalize GET roadmap payloads through the browser mapper first.

Rationale: current hooks retain local responses and can leave other views stale; the core
owns milestone state and must remain authoritative.

## Decision: Accessibility-first chat semantics

Use a labelled textarea and submit control, a semantic `role=log` conversation region,
polite live announcements only for newly appended assistant responses, `role=status` for
pending state, and `role=alert` for blocking errors. Retry retains the failed draft and
focus returns to the first invalid field.

Rationale: these patterns match current UI tests and the frozen accessibility matrix.
