# Implementation Plan: Dockerize and Deploy to AKS

**Branch**: `002-dockerize-deploy` | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-dockerize-deploy/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Package the existing DevOps Career Agent web service as a repeatable container
image and define a non-production AKS deployment path that operators can apply,
verify, update, and roll back. The plan adds container build assets, local
container validation, Kubernetes deployment artifacts for AKS, and operational
documentation while keeping cluster credentials and environment-specific values
outside source control.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, Uvicorn, Pydantic, SQLAlchemy, Docker,
Kubernetes manifests for AKS deployment  
**Storage**: Existing application storage remains environment-configured by
`DATABASE_URL`; the initial AKS rollout targets a non-production single-service
deployment and does not introduce a production database migration  
**Testing**: pytest for application regression checks; container smoke test
against `/health`; manifest validation through dry-run or schema validation
where local tools are available  
**Target Platform**: Linux container image deployed to Azure Kubernetes Service  
**Project Type**: Python web service  
**Performance Goals**: Preserve the existing pilot targets: initial roadmap
responses complete within 30 seconds p95, topic guidance within 10 seconds
p95, and up to 10 concurrent employees during the internal pilot  
**Constraints**: Build and deployment must not require source changes per
environment; cluster credentials, image registry credentials, and sensitive
configuration stay outside source control; initial deployment is non-production
and excludes production hardening, autoscaling policy tuning, and advanced
secret-management integration. The release flow must promote a single immutable
image digest from local validation to AKS; mutable tags are only human-readable
labels.
**Scale/Scope**: One deployable service, one AKS non-production target, one
repeatable rollback path, and a structure that can later add additional targets
or release variants

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
specs/002-dockerize-deploy/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── deployment-contract.md
└── spec.md
```

### Source Code (repository root)

```text
Dockerfile
.dockerignore
compose.yaml

deploy/
└── k8s/
    ├── base/
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   └── kustomization.yaml
    └── overlays/
        └── aks-nonprod/
            ├── configmap.yaml
            ├── secret.example.yaml
            └── kustomization.yaml

src/
├── agent/
├── api/
├── knowledge/
├── skills/
└── storage/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Keep the existing single Python web-service layout and
add deployment assets at the repository root and under `deploy/k8s/`. A
root-level `Dockerfile` and `.dockerignore` define the application package.
`compose.yaml` provides local container validation. Kubernetes base and AKS
non-production overlay files provide the first cluster deployment path without
mixing deployment configuration into the application source tree.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations require justification for this feature.
