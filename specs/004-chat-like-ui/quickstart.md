# Quickstart: Chat-like Career Guidance UI

## Local visual review

```bash
cd ui
npm install
npm run dev
```

Open `http://127.0.0.1:5173/` for the development mock session. The shared fixture
contains ten milestones and can be inspected at:

- `/` Home/current topic and chat composer
- `/roadmaps` full roadmap and course progress
- `/guidance` current-topic guidance and next action
- `/learning/session-1` learning steps and knowledge check
- `/progress` progress review and check-in

## Verification

```bash
npm run typecheck
npm test -- --run
npm run test:e2e
```

For production-shaped checks, disable the development mock and mock the BFF routes in
Playwright with `page.route('**/bff/v1/**')`. Verify success, loading, empty, 422, 503,
retry, duplicate-submit, session-expiry, keyboard, 320px, and enlarged-text scenarios.

## Implementation notes

- Keep browser calls under `/bff/v1` and use generated contracts.
- Do not add localStorage/sessionStorage for learner state or credentials.
- After assessment, step completion, or check-in, refresh authoritative state before
  showing a completed milestone on another page.
- Use `getByRole`/`getByLabel` in tests and preserve accessible text alongside medal icons.
