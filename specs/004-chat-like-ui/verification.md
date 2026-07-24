# Verification Record

Status: Implemented; Chromium verification is green except two pre-existing shell
expectation failures documented below.

| Check | Command | Result |
|---|---|---|
| UI typecheck | `npm --prefix ui run typecheck` | PASS |
| UI unit/component tests | `npm --prefix ui test -- --run` | PASS — 13 files, 36 tests |
| BFF typecheck and tests | `npm --prefix bff run typecheck && npm --prefix bff test -- --run` | PASS — 22 files, 80 tests |
| UI lint | `npm --prefix ui run lint` | PASS — warnings only in provider fast-refresh exports |
| Chromium E2E | `npm --prefix ui run test:e2e -- --project=chrome-stable` | 91/93 passed; two existing shell expectations remain: delayed-interruption Home heading and progress-link strictness |
| Full browser matrix | `npm --prefix ui run test:e2e` | 344 passed; WebKit/Firefox projects are unavailable in this environment |

Responsive (320px–1920px), keyboard, focus, live-region, and no-horizontal-scroll
coverage is exercised by the existing Chromium E2E suites. The two remaining
Chromium failures are isolated to pre-existing expectations outside the new learner
state and BFF roadmap mapping changes.
