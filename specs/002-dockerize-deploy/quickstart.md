# Quickstart: Dockerize and Deploy to AKS

## Goal

Package the DevOps Career Agent as a container image, validate it locally, and
deploy the same package to a non-production AKS environment.

## Prerequisites

- Docker is available locally.
- `kubectl` can reach the target AKS cluster.
- The target namespace and image registry access are already configured.
- Runtime values and secret values are available outside source control.

## Local Validation

1. Run application regression tests:

   ```bash
   python3 -m pytest
   ```

2. Build the container image:

   ```bash
   docker build -t devops-career-agent:local .
   ```

3. Run the container locally:

   ```bash
   docker run --rm --env-file .env.example -p 8000:8000 devops-career-agent:local
   ```

4. In another shell, check health:

   ```bash
   curl http://localhost:8000/health
   ```

## AKS Deployment Flow

1. Tag and push the verified image to the registry used by AKS, then record its immutable digest.
2. Set that immutable image digest in the AKS non-production deployment overlay.
3. Validate the rendered overlay before applying it:

   ```bash
   kubectl apply -k deploy/k8s/overlays/aks-nonprod --dry-run=client
   ```

   If your local `kubectl` still attempts to contact the cluster for schema
   discovery, render the same overlay offline with:

   ```bash
   kubectl kustomize deploy/k8s/overlays/aks-nonprod
   ```

4. Apply the deployment:

   ```bash
   kubectl apply -k deploy/k8s/overlays/aks-nonprod
   ```

5. Wait for rollout completion:

   ```bash
   kubectl rollout status deployment/devops-career-agent -n devops-career-agent
   ```

6. Verify service health through the cluster-approved access path.

## Rollback Flow

1. Restore the previous stable Deployment revision:

   ```bash
   kubectl rollout undo deployment/devops-career-agent -n devops-career-agent
   ```

2. Wait for rollback completion:

   ```bash
   kubectl rollout status deployment/devops-career-agent -n devops-career-agent
   ```

3. Verify `/health` again before considering the rollback complete.

## Operational Notes

- Do not commit real cluster credentials, registry credentials, or secret
  values.
- Keep source-independent environment differences in deployment configuration.
- Treat the first AKS target as non-production.
- Use immutable image digests for release candidates and verified releases.
