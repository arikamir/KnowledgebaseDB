# Contract: GitOps Platform Readiness

**Producer**: `scripts/ci/check-gitops-platform-ready.sh`  
**Schema**: `config/gitops-readiness.schema.json`  
**Consumer**: application-release hand-off and operator verification

## Result shape

```json
{
  "schemaVersion": 1,
  "status": "ready",
  "environment": "nonprod",
  "checks": {
    "namespace": {"status": "pass"},
    "argocdProject": {"status": "pass"},
    "registryPullSecret": {"status": "pass", "name": "career-agent-acr-pull"},
    "registry": {"status": "pass"},
    "workloadPrerequisites": {"status": "pass"}
  },
  "observedAt": "2026-07-25T12:00:00Z"
}
```

`status` is `ready` only when every named check passes. A blocked result must
include an actionable `failureReason`; it must never include credential data.
The command is read-only and must not create namespaces, Secrets, workloads,
Azure resources, or Terraform state.

## Acceptance and timing evidence

- The result identifies the explicit target environment.
- The pull-secret check expects the platform-owned name
  `career-agent-acr-pull` but never returns its data.
- A release run stores protected-merge, sync, healthy/failed, and drift timestamps
  alongside this result to evaluate SC-003, SC-005, and SC-008.
