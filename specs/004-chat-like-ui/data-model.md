# Data Model: Chat-like Career Guidance UI

The browser model is a projection of BFF responses. It is not a second source of truth.
`LearnerState` owns conversation lifecycle, draft, delivery, and recovery state;
feature components own presentation and input interaction only. The provider remains
mounted above route components so navigation cannot discard the active conversation.

## LearnerState

| Field | Type | Rules |
|---|---|---|
| `roadmap` | `RoadmapSnapshot \| null` | Last validated authoritative roadmap; cleared on auth epoch change |
| `conversation` | `Conversation` | Shared in-memory conversation preserved across route changes; cleared on explicit reset or auth epoch change |
| `currentTopic` | `CurrentTopic \| null` | Must reference a roadmap milestone when present |
| `nextAction` | `NextAction \| null` | At most one action, using the BFF kind/target vocabulary |
| `milestones` | `MilestoneSnapshot[]` | Ordered by ordinal; keys are stable across refreshes |
| `lastUpdatedAt` | ISO timestamp | Set when a complete snapshot is published |
| `status` | `loading \| ready \| empty \| unavailable \| error` | Drives page-level states |
| `error` | `UiError \| null` | Retryable and field-specific details preserved |

`LearnerState` is the presentation-layer projection used by the Home chat surface and
the secondary Roadmap, Guidance, Learning, and Progress routes; durable ownership
remains in the BFF/core services.

## MilestoneSnapshot

| Field | Type | Rules |
|---|---|---|
| `milestoneKey` | string | Stable core key; unique within roadmap |
| `ordinal` | number | Positive display order |
| `title` | string | Required, safe text only |
| `completionState` | `pending \| in_progress \| completed` | Core value |
| `scorePercent` | number \| null | 0-100 when assessed |
| `passed` | boolean \| null | Required with a score after assessment |
| `achievementTier` | `bronze \| silver \| gold \| null` | Derived by one shared policy function: bronze 80-89%, silver 90-94%, gold 95-100%; null below 80% |
| `evidence` | `AssessmentEvidence[]` | Immutable references to assessment/check-in outcomes |

## Conversation

| Field | Type | Rules |
|---|---|---|
| `messages` | `Message[]` | Chronological, one active conversation per session |
| `assistantContent` | `{ topicSummary: string; currentLevelFit: string; practicalNextAction: string; suggestions: string[]; commonPitfalls: string[]; relatedTopics: string[]; labReferences: LabReference[] }` | Existing BFF guidance DTO; only `labReferences.destinationUrl` values beginning with `https://` are interactive |
| `draft` | string | Preserved across route changes, retry, and session expiry; whitespace invalid; maximum 2,000 characters |
| `deliveryState` | `ready \| pending \| delivered \| failed` | Duplicate submit blocked while pending |
| `failure` | `UiError \| null` | Retryable failure retains draft and question |

## AssessmentEvidence

| Field | Type | Rules |
|---|---|---|
| `assessmentId` | string | BFF/core identifier |
| `milestoneKey` | string | Must match a roadmap milestone |
| `scorePercent` | number | 0-100 |
| `passed` | boolean | True at 80% or higher |
| `achievementTier` | enum | Bronze 80-89%, silver 90-94%, gold 95-100%; derived, not user-editable |
| `recordedAt` | ISO timestamp | Server result time when available |

## LabReference

| Field | Type | Rules |
|---|---|---|
| `id` | string | BFF-provided reference identifier |
| `provider` | string | Display-only provider name |
| `objective` | string | Safe plain-text lab objective |
| `destinationUrl` | string | Interactive only when it begins with `https://` |
| `availabilityStatus` | `active \| unavailable \| retired` | Controls whether the link is actionable |

## State transitions

`loading -> ready|empty|unavailable|error`; `ready -> loading` on refresh; assessment
and check-in mutations enter `loading`, then publish a complete authoritative snapshot;
failed mutations return to `ready` with preserved input and a retryable error.
