# Tasks: Dockerize and Deploy to AKS

**Input**: Design documents from `/specs/002-dockerize-deploy/`
**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/, quickstart.md

**Verification**: The implementation plan requires container build validation,
AKS deployment rollout checks, and rollback coverage. Each user story includes
explicit validation tasks so the deployment path remains independently
testable.

**Organization**: Tasks are grouped by user story so each story can be built,
validated, and delivered independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and base deployment scaffolding

- [X] T001 [P] Create the root container build assets in `Dockerfile` and `.dockerignore`
- [X] T002 [P] Create the local container execution workflow in `compose.yaml`
- [X] T003 [P] Create the AKS base manifest scaffold in `deploy/k8s/base/deployment.yaml`, `deploy/k8s/base/service.yaml`, and `deploy/k8s/base/kustomization.yaml`
- [X] T004 [P] Create the AKS non-production overlay scaffold in `deploy/k8s/overlays/aks-nonprod/configmap.yaml`, `deploy/k8s/overlays/aks-nonprod/secret.example.yaml`, and `deploy/k8s/overlays/aks-nonprod/kustomization.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared deployment inputs and contract coverage that must exist before any user story work can be completed

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Add `.env.example` with the runtime keys from `src/agent/settings.py` for container and AKS use
- [X] T006 [P] Add deployment contract coverage in `tests/contract/test_deployment_contract.py` for the runtime port, `/health`, environment variables, and immutable release references

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Containerized Application Package (Priority: P1) 🎯 MVP

**Goal**: Package the application as a reusable container image that starts consistently in a local environment.

**Independent Test**: A maintainer can build the image from a clean checkout, run it with `.env.example`, and get a successful `/health` response without changing application source.

### Implementation for User Story 1

- [X] T007 [P] [US1] Finalize `Dockerfile` so the application starts with `uvicorn api.app:app` on port 8000 from the repository source tree
- [X] T008 [P] [US1] Finalize `compose.yaml` to build the image, load `.env.example`, and publish port 8000 for local smoke checks
- [X] T009 [P] [US1] Add container smoke coverage in `tests/integration/test_container_runtime.py` for startup and `/health`
- [X] T010 [US1] Update `README.md` with the container build, run, and smoke-check workflow

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - AKS Deployment and Verification (Priority: P2)

**Goal**: Deploy the packaged image to a non-production AKS environment and confirm the rollout becomes healthy.

**Independent Test**: An operator can apply the AKS overlay, wait for rollout completion, and verify `/health` from the deployed service.

### Implementation for User Story 2

- [X] T011 [P] [US2] Finalize `deploy/k8s/base/deployment.yaml` with labels, container port 8000, and `/health` probes
- [X] T012 [P] [US2] Finalize `deploy/k8s/base/service.yaml` for the application workload
- [X] T013 [US2] Finalize `deploy/k8s/base/kustomization.yaml` so the base renders as one workload
- [X] T014 [P] [US2] Populate `deploy/k8s/overlays/aks-nonprod/configmap.yaml` with non-secret runtime values from `src/agent/settings.py`
- [X] T015 [P] [US2] Populate `deploy/k8s/overlays/aks-nonprod/secret.example.yaml` with placeholder secret references only
- [X] T016 [US2] Finalize `deploy/k8s/overlays/aks-nonprod/kustomization.yaml` with namespace and immutable image-digest wiring

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Update and Recovery (Priority: P3)

**Goal**: Promote new releases and roll back to the previous stable revision if a rollout fails.

**Independent Test**: An operator can deploy a newer image, roll back the release, and verify the previous revision is healthy.

### Implementation for User Story 3

- [X] T017 [P] [US3] Add rollback flow coverage in `tests/integration/test_rollback_flow.py`
- [X] T018 [P] [US3] Update `specs/002-dockerize-deploy/quickstart.md` with `kubectl rollout undo` and post-rollback health checks
- [X] T019 [US3] Update `README.md` with immutable image-digest and last-known-good revision guidance

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T020 [P] Reconcile `README.md` and `specs/002-dockerize-deploy/quickstart.md` with the final container and AKS workflow wording
- [X] T021 [P] Tighten `tests/contract/test_deployment_contract.py` to match the final runtime contract and rollout expectations
- [X] T022 [P] Validate the rendered AKS overlay with `kubectl apply -k deploy/k8s/overlays/aks-nonprod --dry-run=client` and capture the same command in `specs/002-dockerize-deploy/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel if staffed
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - no dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - may reuse the packaged image but must remain independently useful
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - may reuse deployment revisions but must remain independently useful

### Within Each User Story

- Shared scaffolding before story-specific implementation
- Deployment inputs and contracts before runtime wiring
- Runtime wiring before story-specific validation
- Story complete before moving to the next priority

### Parallel Opportunities

- `T001` through `T004` can run in parallel because they touch different files
- `T005` and `T006` can run in parallel after Setup
- Within User Story 1, `T007`, `T008`, and `T009` can run in parallel
- Within User Story 2, `T011`, `T012`, `T014`, and `T015` can run in parallel; `T013` and `T016` finish the manifest wiring
- Within User Story 3, `T017` and `T018` can run in parallel
- Polish tasks `T020`, `T021`, and `T022` can run in parallel

## Parallel Example: User Story 1

```text
Task: "Finalize Dockerfile so the application starts with uvicorn api.app:app on port 8000 from the repository source tree"
Task: "Finalize compose.yaml to build the image, load .env.example, and publish port 8000 for local smoke checks"
Task: "Add container smoke coverage in tests/integration/test_container_runtime.py for startup and /health"
```

## Parallel Example: User Story 2

```text
Task: "Finalize deploy/k8s/base/deployment.yaml with labels, container port 8000, and /health probes"
Task: "Finalize deploy/k8s/base/service.yaml for the application workload"
Task: "Populate deploy/k8s/overlays/aks-nonprod/configmap.yaml with non-secret runtime values from src/agent/settings.py"
Task: "Populate deploy/k8s/overlays/aks-nonprod/secret.example.yaml with placeholder secret references only"
```

## Parallel Example: User Story 3

```text
Task: "Add rollback flow coverage in tests/integration/test_rollback_flow.py"
Task: "Update specs/002-dockerize-deploy/quickstart.md with kubectl rollout undo and post-rollback health checks"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate the containerized application package on its own

### Incremental Delivery

1. Complete Setup + Foundational
2. Add User Story 1 and validate the container workflow
3. Add User Story 2 and validate the AKS deployment independently
4. Add User Story 3 and validate the rollback workflow independently
5. Finish with polish tasks that improve consistency and operational clarity
