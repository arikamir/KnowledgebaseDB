# Quickstart: DevOps Career Agent

## Goal

Use this feature to guide an employee from a broad DevOps goal to a practical,
progress-aware roadmap.

## First-run flow

1. Collect the employee's current role, experience, target role, and available
   time. Ask up to 3 clarifying questions if needed; if the context is still
   incomplete, produce a best-effort roadmap and state the assumptions used.
2. Generate an initial roadmap with immediate, near-term, and longer-term
   actions.
3. Save the roadmap so the employee can return later with progress updates.
4. Let the employee ask for targeted guidance on one skill area at a time.

## Verification checklist

- Confirm the assistant can produce a roadmap from minimal input.
- Confirm topic-specific guidance works for common DevOps areas.
- Confirm a later check-in updates the next steps instead of restarting the
  experience.
- Confirm the assistant does not present HR decisions as part of the feature.

## Operational notes

- Add new skill areas through the skill catalog rather than rewriting the core
  guidance flow.
- Keep roadmap outputs practical and role-specific.
- Preserve previous plans so progress reviews remain meaningful.
- Use the host application's existing employee identity to retrieve prior
  roadmaps and progress check-ins.
- Initial proof-of-concept usage is non-production. Do not use regulated HR
  records, performance-review data, secrets, or production employee datasets.
  Security/privacy hardening, retention controls, and access controls are
  deferred until a production-readiness phase.
