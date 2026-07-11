# Deployment Contract: Dockerize and Deploy to AKS

## Container Runtime Contract

- The container starts the application as a web service.
- The service listens on port `8000` inside the container.
- `GET /health` returns a successful response when the service is alive.
- Logs are written to standard output and standard error.
- Runtime configuration is supplied through environment variables.
- The image must not require source changes for environment-specific behavior.

## Required Runtime Settings

| Setting | Purpose | Source |
|---------|---------|--------|
| `APP_NAME` | Application display name | Config value |
| `ENVIRONMENT` | Runtime environment name | Config value |
| `DATABASE_URL` | Application storage connection string | Secret or config reference |
| `LOG_LEVEL` | Runtime logging level | Config value |
| `MAX_CLARIFYING_QUESTIONS` | Roadmap intake limit | Config value |
| `ROADMAP_P95_SECONDS` | Roadmap response target | Config value |
| `TOPIC_GUIDANCE_P95_SECONDS` | Topic guidance response target | Config value |
| `MAX_CONCURRENT_EMPLOYEES` | Pilot concurrency target | Config value |

## Kubernetes Deployment Contract

- The AKS deployment creates one application workload for the initial
  non-production target.
- The workload exposes the application through a Kubernetes Service.
- Liveness and readiness probes use `GET /health`.
- The Deployment image reference is configurable without editing application
  source and must point to the exact immutable image digest that passed local
  validation; mutable tags are not sufficient as the release reference.
- Environment-specific configuration is supplied by Kubernetes configuration
  objects or externally managed values.
- Secret values are represented by examples or references only; real secret
  values are not committed.
- The deployment records rollout history so operators can restore the previous
  stable revision.

## Verification Contract

1. Application regression tests pass before a package is built.
2. The container starts locally and responds successfully on `/health`.
3. The AKS rollout completes successfully.
4. The deployed service responds successfully on `/health`.
5. Rollback restores the previous verified release when a rollout fails.
