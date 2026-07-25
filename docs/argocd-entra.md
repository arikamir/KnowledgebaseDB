# Argo CD Azure Entra integration

Argo CD operator access is protected by the Azure Entra tenant. This is a
platform-owned configuration: application delivery only consumes the resulting
ApplicationSet and never changes OIDC, RBAC, namespaces, or Azure resources.

## Registration and claims

Create one Entra application registration for the Argo CD server and use the
platform-approved redirect URI (`https://<argocd-host>/auth/callback`). Enable
the `groups` and `roles` claims and validate `tid`, `oid`, and `sub` on every
session. The platform stores the client secret in cluster secret management or
uses workload identity; it is never put in Git, desired state, release
bundles, or evidence.

The non-secret contract is split into [`config/argocd-oidc-rbac.yaml`](../config/argocd-oidc-rbac.yaml)
and [`config/argocd-rbac-policy.yaml`](../config/argocd-rbac-policy.yaml). Apply
it only from the platform bootstrap context:

```bash
scripts/azure/apply-argocd-rbac.sh                 # validate/dry-run contract
APPLY=true scripts/azure/apply-argocd-rbac.sh      # platform-approved apply
```

## Roles and boundaries

| Entra group/app role | Argo CD capability | Boundary |
| --- | --- | --- |
| `career-agent-application-release` | Read/sync the nonprod application and approve the Git release PR | No Terraform, Azure, namespace, gateway, or cluster-resource mutation |
| `career-agent-infrastructure-admin` | Run the separately approved infrastructure workflow | Not used for routine application release |
| `career-agent-observability-readonly` | View health, events, sync, and evidence | No sync, Git write, rollback, or infrastructure mutation |

The default Argo CD role is read-only. Privileged actions require an active,
non-expired and non-revoked session with a matching tenant and group/app-role
claim. Session expiry/revocation must be checked before a sync or approval is
accepted. GitHub Copilot review remains an independent required status check;
it does not replace operator authentication.

## Audit and secret handling

Audit events record tenant, subject, resolved role, authentication result,
action/event, environment, release version, and timestamp. They may include
the automation identity or human action record, but never tokens, client
secrets, kubeconfigs, connection strings, or learner data. Use
`scripts/ci/collect-argocd-evidence.sh` to produce a redacted evidence record.
