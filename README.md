# DevOps Career Agent

Internal AI assistant for helping employees plan and review DevOps-focused
career growth.

## Local development

- Run tests: `python3 -m pytest`
- Start the API: `uvicorn api.app:app --reload`

## Container workflow

Build and run the application as the same container image used for AKS:

```bash
docker build -t devops-career-agent:local .
docker run --rm --env-file .env.example -p 8000:8000 devops-career-agent:local
```

If you prefer Compose for local iteration, use:

```bash
docker compose up --build
```

Smoke test the running container:

```bash
curl http://localhost:8000/health
```

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
