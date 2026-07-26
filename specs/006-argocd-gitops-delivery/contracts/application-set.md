# Contract: ApplicationSet and Generated Application

**Source**: `deploy/argocd/applicationset.yaml`  
**Project**: `deploy/argocd/project.yaml`  
**Overlay**: `deploy/k8s/overlays/argocd-nonprod`

## Generator input

The generator watches the canonical repository's protected `main` branch and
exactly one file: `deploy/argocd/environments/nonprod/release.json`. Missing
template keys are errors. A generated Application must carry the environment,
SemVer, source revision, and declaration path as labels/annotations.

The declaration environment is explicitly `nonprod`; any other environment is
rejected before the ApplicationSet can render an Application.

The declaration reaches `main` only through a CI-created/updated bot-branch pull
request that passes the required approved current-head automated review and branch-protection
checks. The ApplicationSet does not read that branch before merge.

## Generated Application invariants

1. `spec.project` is `career-agent`.
2. The source path is `deploy/k8s/overlays/argocd-nonprod`.
3. The destination is the in-cluster API server and namespace `career-agent`.
4. Kustomize receives exactly three image substitutions: UI, BFF, and Core.
5. Each substitution is an ACR `repository@sha256:<64-hex>` reference.
6. Each generated Deployment references the platform-owned
   `career-agent-acr-pull` image-pull secret by name; no Secret resource or
   credential data is generated.
7. Automated sync may self-heal and prune only resources in the AppProject.
8. `CreateNamespace=false`, so the platform workflow must provision the
   namespace before the first sync.
9. Cluster-scoped resources, gateway/route, private load balancer, Terraform,
   and platform controller paths are absent from the generated source.

## AppProject invariants

- The only source repository is the canonical GitHub repository.
- The only destination is the existing `career-agent` namespace.
- `clusterResourceWhitelist` is empty.
- Namespace resources are explicitly allowlisted; orphan warnings are enabled.
