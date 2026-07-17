# Pilot usability study protocol

Status: frozen implementation-readiness protocol. Owner: Product/UX Research.
This document materializes the normative protocol without changing its sample,
tasks, wording, scoring, or failure treatment. Freeze the completed roster,
allocation, consent, script, and facilitator evidence within seven days before
the first participant. Do not begin measurement while that evidence is stale.

## Frozen population and selection

Recruit and pre-screen exactly 24 internal employees. Assign anonymous IDs and
randomize order independently within these fixed strata:

| Stratum | Roster | Measured sample | Reserve |
|---|---:|---:|---:|
| Beginner | 8 | first 7 eligible in frozen order | next 1 |
| Intermediate | 8 | first 7 eligible in frozen order | next 1 |
| Advanced | 8 | first 6 eligible in frozen order | next 2 |

For every roster member, Product/UX Research must record `stratum`,
`frozen_order`, and boolean evidence that the person has organizational Entra
access, English working proficiency, did not contribute to feature
requirements/design/code/tests, has not seen the task script, and consented to
anonymous task/timing collection. A failed assertion makes the person
ineligible.

Replacement is allowed only before the first measured task and only for consent
withdrawal, an inability to authenticate caused by an independently verified
tenant/platform setup defect, or failure of an eligibility assertion. Use the
next reserve in frozen order from the same stratum and record the reason and
verification. Once task 1 starts, no replacement is permitted: abandonment,
outage, crash, timeout, inability, or missing evidence remains in the measured
20 as a failed outcome.

## Frozen viewport allocation

Freeze allocation before testing. At least five measured participants use 375
CSS pixels with Chrome mobile emulation; at least five use 1440 CSS pixels. The
remaining ten are balanced equally: five at 768 and five at 1024 CSS pixels.
Record exact browser name/version and viewport for each participant. Changing
allocation after measurement begins invalidates the study.

## Neutral five-task script

Give every participant these instructions verbatim and in order:

1. Sign in and create a roadmap from the supplied valid profile; identify the first recommended action.
2. Find one supplied supported topic and explain the practical next action.
3. Complete the supplied focused session's required content and first review.
4. Identify current/completed milestones and the one recommended next action.
5. Observe one supplied validation error and one simulated temporary outage, then recover without re-entering valid information.

The facilitator may resolve equipment or accessibility setup before timing and
may repeat the written instruction verbatim. After timing starts, any navigation
hint, field suggestion, definition, confirmation, or correction is assistance.
The participant may continue, but the task fails every criterion requiring an
unassisted outcome.

For every task retain anonymous participant ID, event marks, outcome, viewport,
browser version, assistance flag, and measurement-validity flag. Screen/video
is optional. For task 3, separately record required-content start, first-review
result, optional-material time, external-lab time, interruptions, and retries;
only the accumulated required-content duration through the first-review result
is evaluated against the inclusive 20-30 minute bound.

## Exact questionnaire

Use only this scale: `1 Strongly disagree`, `2 Disagree`, `3 Neither`, `4 Agree`,
`5 Strongly agree`. Ask exactly:

- SC-007: “The forms, progress feedback, results, and error messages were clear.”
- SC-015: “The review feedback and explanations helped me understand why my answers were correct or incorrect.”
- SC-017: “The completion feedback and recommended next action make me want to continue learning.”

## Fixed calculations and failure treatment

All denominators are the frozen measured 20. Additional observations are
reported separately and never enter a denominator.

- SC-001 passes at 18/20 or more when an unassisted participant both submits the roadmap and identifies the exact core-returned first action.
- SC-007 passes at 17/20 or more ratings of 4 or 5.
- SC-011 passes at 18/20 or more valid accumulated required-content durations through first-review result within 20-30 minutes inclusive.
- SC-015 passes at 17/20 or more ratings of 4 or 5.
- SC-016 passes at 18/20 or more unassisted identifications of current milestone, completed milestones, and recommended next action.
- SC-017 passes at 16/20 or more ratings of 4 or 5.

Missing answers, abandonment, setup/dependency failure after task 1 starts,
crash, timeout, assistance for an unassisted criterion, and missing or invalid
measurement evidence count as failures. Do not censor, substitute, or reduce
the denominator.

Product/UX Research owns recruitment, randomized frozen roster and allocation,
eligibility and consent evidence, supplied fixtures and neutral script,
facilitator log, raw anonymized events, calculations, and signed result summary.
