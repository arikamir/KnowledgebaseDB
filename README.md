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

The non-production AKS deployment path is documented in
[specs/002-dockerize-deploy/quickstart.md](specs/002-dockerize-deploy/quickstart.md).
The Kubernetes assets live under `deploy/k8s/` and use an immutable image digest
for release promotion. If cluster access is unavailable, render the overlay
locally with `kubectl kustomize deploy/k8s/overlays/aks-nonprod`.

## Feature scope

- Career roadmap generation
- Skill-specific guidance
- Progress-aware roadmap updates
- HR/performance boundary detection
