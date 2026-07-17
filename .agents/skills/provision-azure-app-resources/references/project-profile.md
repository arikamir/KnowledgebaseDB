# Project Azure Profile

Use this reference as a project-specific baseline. Re-read repository artifacts because they remain authoritative.

## Workload

- Application: DevOps Career Agent
- Runtime: React/Vite UI, Fastify BFF, Python 3.11 FastAPI core
- Public boundary: AGC/Gateway API routes `/` to UI and `/bff/*` to BFF; core is never public
- Health endpoint: `GET /health`
- Initial target: three independent non-production AKS workloads plus lifecycle workers
- Kubernetes namespaces: `career-agent`, `career-migrations`, `azure-alb-system`
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

Provision the resource group, ACR, AKS, AGC/private-core/data services, evidence stores, monitoring, all nine one-to-one workload identities, distinct Jenkins publisher/deployer identities, and exact RBAC. Keep UI and validator identityless.

Exclude by default:

- production database migration or a new managed database;
- any legacy Ingress, managed application routing, or NGINX controller;
- production high availability and multi-region failover;
- autoscaling-policy tuning;
- advanced secret-management integration;
- application deployment itself.

Add excluded components only when the user or a newer specification requires them.

## Required integration

- Disable ACR admin credentials.
- Grant the non-federatable AKS kubelet identity only `AcrPull` scoped to the exact ACR; prove push/delete/import/admin/role/federation/pod-assumption denial.
- Require OIDC/Workload Identity and one federated subject per BFF, core, lifecycle, retention, lab-revalidation, migration, evidence-hold-reconciler, ALB-controller, and gateway-certificate/DNS identity.
- Publisher may push only to the application ACR and publish/verify exact prefix-scoped immutable evidence. Deployer may mutate only the exact AKS target, read only the target resource group, and publish/verify exact prefix-scoped evidence. Neither may read Terraform state, secrets, Redis/PostgreSQL data, or assume the other role.
- Output the ACR login server so the Kustomize image reference can use `<login-server>/<repository>@sha256:<digest>`.
- Install the pinned ALB Controller before Gateway resources and route only UI/BFF through AGC HTTPS.
- Resolve and report the Gateway's actual public `https://<address>/` URL after rollout.
- Never persist kubeconfig or Azure credentials in the repository.
- Preserve the documented Kubernetes rollout and rollback flow.
