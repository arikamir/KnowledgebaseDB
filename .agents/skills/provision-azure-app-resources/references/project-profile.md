# Project Azure Profile

Use this reference as a project-specific baseline. Re-read repository artifacts because they remain authoritative.

## Workload

- Application: DevOps Career Agent
- Runtime: Python 3.11 FastAPI/Uvicorn
- Container port: `8000`
- Health endpoint: `GET /health`
- Initial target: one non-production AKS workload
- Kubernetes namespace: `devops-career-agent`
- Kubernetes manifests: Kustomize base plus `deploy/k8s/overlays/aks-nonprod`
- Release requirement: deploy the exact verified ACR image digest, not only a mutable tag

## Required runtime configuration

Non-secret values belong in Kubernetes configuration. `DATABASE_URL` is sensitive or externally managed and must not be committed with a real value.

- `APP_NAME`
- `ENVIRONMENT`
- `DATABASE_URL`
- `LOG_LEVEL`
- `MAX_CLARIFYING_QUESTIONS`
- `ROADMAP_P95_SECONDS`
- `TOPIC_GUIDANCE_P95_SECONDS`
- `MAX_CONCURRENT_EMPLOYEES`

## Default scope

Provision a resource group, ACR, AKS, required managed identities/RBAC, and monitoring dependencies. Keep node sizing and counts configurable and economical for non-production use.

Exclude by default:

- production database migration or a new managed database;
- public ingress, DNS, and TLS;
- production high availability and multi-region failover;
- autoscaling-policy tuning;
- advanced secret-management integration;
- application deployment itself.

Add excluded components only when the user or a newer specification requires them.

## Required integration

- Disable ACR admin credentials.
- Grant the AKS kubelet identity `AcrPull` scoped to the ACR.
- Output the ACR login server so the Kustomize image reference can use `<login-server>/<repository>@sha256:<digest>`.
- Enable managed AKS application routing with an external controller and route `/` to the application service.
- Resolve and report the controller's actual public `http://<address>/` URL after rollout.
- Never persist kubeconfig or Azure credentials in the repository.
- Preserve the documented Kubernetes rollout and rollback flow.
