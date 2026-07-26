# DevOps Career Agent

Internal AI assistant for helping employees plan and review DevOps-focused
career growth.

## Local development

The application has three independently buildable services. Node.js 24 LTS,
Python 3.11+, `uv`, npm, Docker, and Docker Compose are required.

### Core API

```bash
uv sync --extra test
uv run pytest
uv run uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

### Browser BFF

```bash
cd bff
npm install
npm run lint
npm run typecheck
npm test
npm run dev
```

### React UI

```bash
cd ui
npm install
npm run lint
npm run typecheck
npm test
npm run dev
```

The UI is served at `http://localhost:5173`, the BFF at
`http://localhost:3000`, and the private core API at `http://localhost:8000`.
Copy only the safe example values required for local work; never commit real
tenant credentials, session keys, tokens, or database passwords.

## Container workflow

Build and run all services with local PostgreSQL and Redis:

```bash
docker compose up --build
```

Each service can also be built independently:

```bash
docker build -t devops-career-agent-core:local .
docker build -t devops-career-agent-bff:local bff
docker build -t devops-career-agent-ui:local ui
```

Smoke test the running container:

```bash
curl http://localhost:8000/health
curl http://localhost:3000/health/ready
curl http://localhost:5173/health/ready
```

Stop local dependencies with `docker compose down`. Add `--volumes` only when
you intentionally want to discard local PostgreSQL and Redis data.

## AKS workflow

The current three-service workflow is documented in the
[feature quickstart](specs/003-develop-ui/quickstart.md) and the
[operations runbook](docs/operations-ui.md). The canonical API contracts are
`specs/003-develop-ui/contracts/bff-api-v1.openapi.yaml` and
`specs/003-develop-ui/contracts/core-api-v1.openapi.yaml`; regenerate/check
clients with `scripts/ci/generate_contracts.py --check` and validate the
supported topic catalog with `scripts/ci/validate-api-contracts.sh`.

Kubernetes assets live under `deploy/k8s/`. Render the complete non-production
overlay locally with:

```bash
kubectl kustomize deploy/k8s/overlays/aks-nonprod
```

The public Application Gateway for Containers URL is authoritative; retrieve it
only after bootstrap with `.agents/skills/provision-azure-app-resources/scripts/get-application-url.sh`.
The public Gateway routes `/` to UI and `/bff/*` to BFF. Core has no public
HTTPRoute and serves TLS on 8443 through ClusterIP plus the approved-source
internal LoadBalancer/private DNS endpoint.

Platform Operations provisions/tears down infrastructure only through the
mandatory repository skills and reviewed Terraform. GitHub Actions validates
the final manifest and uses short-lived OIDC identities; it cannot apply
Terraform or read state. See [GitHub Actions Azure delivery](docs/github-actions-azure.md).
Protected delivery builds immutable UI/BFF/core digests once, runs the combined Alembic target
`009_merge_learning_progress`, and promotes `core -> BFF -> UI` with evidence
and reverse recovery gates.

The application-release hand-off is GitOps-ready: Argo CD's
[ApplicationSet](docs/argocd-gitops.md) watches the protected GitHub `main`
branch and reconciles the SemVer/digest-pinned release declaration for the
three application services. Terraform and platform bootstrap remain separate
from this application release path.

Use `.github/workflows/infrastructure.yml` for the separately approved
Terraform/platform lifecycle, `.github/workflows/delivery.yml` for a protected
SemVer-tagged image release and approved-automated-review desired-state PR, and
`.github/workflows/rollback.yml` for a reviewed declaration reversion. The
application workflow has no AKS or Terraform credentials.

For local pipeline-equivalent verification run the Python suite, BFF/UI lint,
typecheck and tests, API contract gate, and both Kustomize renders described in
the feature quickstart. Local development uses SQLite/HTTP; deployed core uses
PostgreSQL Entra authentication and HTTPS with no password/plaintext fallback.

## Feature scope

- Career roadmap generation
- Skill-specific guidance
- Progress-aware roadmap updates
- HR/performance boundary detection
