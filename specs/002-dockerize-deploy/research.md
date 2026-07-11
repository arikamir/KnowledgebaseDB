# Research: Dockerize and Deploy to AKS

## Decision 1: Containerize the existing FastAPI service directly

- **Decision**: Package the current Python 3.11 FastAPI service in a Linux
  container image that installs the project package and runs Uvicorn against
  `api.app:app`.
- **Rationale**: The application already exposes a FastAPI app object and uses
  environment-based settings, so no application architecture change is needed
  to make it container-ready.
- **Alternatives considered**: Introduce a separate process manager or split
  the app into multiple services. Those add operational complexity that the
  current single-service feature does not require.

## Decision 2: Use `/health` as the container and AKS readiness signal

- **Decision**: Use the existing `/health` endpoint for local smoke checks and
  Kubernetes liveness/readiness probes.
- **Rationale**: The endpoint already returns a small deterministic response
  and is the simplest user-visible signal that the service process is alive and
  routable.
- **Alternatives considered**: Add a new deployment-only health endpoint.
  That would expand application behavior unnecessarily for this packaging
  feature.

## Decision 3: Keep runtime configuration externalized

- **Decision**: Supply runtime values through environment variables and
  Kubernetes configuration objects, with sensitive values represented only by
  examples or external references in source control.
- **Rationale**: The existing settings loader already supports environment
  variables, and the spec requires environment-specific values to vary without
  separate code branches or rebuilds.
- **Alternatives considered**: Bake settings into the image or maintain one
  source branch per environment. Both would violate repeatable package behavior.

## Decision 4: Use Kubernetes manifests with a base and AKS overlay

- **Decision**: Add Kubernetes manifests under `deploy/k8s/base` and an
  `aks-nonprod` overlay for the first AKS target.
- **Rationale**: Plain manifests keep the first deployment path understandable
  and require no extra release tooling beyond Kubernetes-compatible apply and
  rollout commands. The base and overlay split also leaves room for future
  targets.
- **Alternatives considered**: Helm chart for the first release. Helm is useful
  for larger release programs, but it is extra surface area for the first
  single-service non-production deployment.

## Decision 5: Roll back using Kubernetes rollout history

- **Decision**: Treat the previous Deployment revision as the rollback point
  and document validation before and after rollback.
- **Rationale**: This satisfies the feature requirement to restore the last
  known good release without rebuilding the application.
- **Alternatives considered**: Rebuild and redeploy a prior image. That is
  slower and weakens release immutability because rollback should reuse an
  already-built artifact.

## Decision 6: Validate with application, container, and deployment checks

- **Decision**: Keep pytest as the application regression check, add a local
  container smoke test, and define AKS rollout and health verification steps.
- **Rationale**: The feature changes packaging and deployment workflow more
  than business behavior, so verification must cover the application before
  packaging, the container after packaging, and the deployed service after
  rollout.
- **Alternatives considered**: Only running unit tests before deployment. That
  would not prove the package runs correctly or that AKS deployment works.
