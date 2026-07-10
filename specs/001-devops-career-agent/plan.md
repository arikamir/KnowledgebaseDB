# Implementation Plan: DevOps Career Agent

**Branch**: `001-devops-career-agent` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-devops-career-agent/spec.md`

## Summary

Build an internal AI career-guidance assistant that helps employees grow toward
DevOps-adjacent roles by turning their current experience, target role, and
available time into an actionable roadmap, skill-specific guidance, and
progress-aware follow-up advice. The first release uses a modular conversation
and skill-catalog approach so new topics can be added without changing the core
user flow.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, Pydantic, an LLM provider API, structured
prompt templates, and a lightweight persistence layer  
**Storage**: PostgreSQL for profiles, roadmaps, and progress checkpoints; a
versioned content store for skill guidance  
**Testing**: pytest with service-level, integration, and conversation-flow tests  
**Target Platform**: Internal web service with chat-style UI integration  
**Project Type**: Web service / AI assistant  
**Performance Goals**: Return an initial usable roadmap within 30 seconds at
p95 and complete topic-guidance responses within 10 seconds at p95 during
normal internal pilot usage of up to 10 concurrent employees  
**Constraints**: Must stay focused on career guidance, avoid HR decisions, and
support extensible skill areas without redesigning the core flow. Security,
privacy hardening, data retention controls, and production access controls are
out of scope for the initial proof of concept. Roadmap intake must cap
clarifying questions at 3 and fall back to a best-effort roadmap with explicit
assumptions when context remains incomplete.  
**Scale/Scope**: Single-organization deployment with a growing library of
DevOps topics and future specializations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Spec, plan, and tasks describe the same scoped outcome.
- [x] User stories are independently testable and ordered by priority.
- [x] Unknowns are resolved or explicitly marked `NEEDS CLARIFICATION` / `TODO(...)`.
- [x] Each story has a verification strategy, test plan, or documented exception.
- [x] Documentation and runtime guidance updates are included when behavior or
      workflow changes.
- [x] Any added complexity is justified and tied to a specific requirement.

## Project Structure

### Documentation (this feature)

```text
specs/001-devops-career-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── spec.md
```

### Source Code (repository root)

```text
src/
├── agent/
│   ├── contracts/
│   ├── errors.py
│   ├── logging.py
│   ├── policy.py
│   ├── roadmap_presenter.py
│   ├── roadmap_service.py
│   ├── skill_guidance_service.py
│   ├── progress_service.py
│   └── settings.py
├── skills/
│   ├── catalog.py
│   └── resolver.py
├── knowledge/
│   ├── schemas.py
│   └── topics/
├── storage/
│   ├── database.py
│   ├── roadmap_repository.py
│   └── progress_repository.py
└── api/
    ├── app.py
    ├── router.py
    ├── routes/
    │   ├── roadmap.py
    │   ├── skills.py
    │   └── progress.py
    └── route_helpers.py

tests/
├── unit/
│   ├── agent/
│   ├── skills/
│   ├── storage/
│   └── api/
├── integration/
└── contract/
```

**Structure Decision**: Use a single service-oriented Python project with
modular subpackages for conversation handling, skill catalog management,
persistence, and API exposure. This keeps the first release simple while
leaving room for new topic areas and supporting workflows. No external
interface contracts are required for the first release because the assistant is
treated as an internal service with no public API commitment yet.

## Complexity Tracking

No constitution violations require justification for this feature.
