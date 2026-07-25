# Contract: Entra Delivery Roles

Human Argo CD operators authenticate through the configured Microsoft Entra
tenant. The role mapping is an authorization contract, not a place to store
credentials.

| Entra group/app role | Argo CD capability | Explicit boundary |
| --- | --- | --- |
| `career-agent-application-release` | Read and sync the `career-agent` Application; approve/revert release declarations through protected Git workflow | No Terraform, Azure resource, namespace, gateway, or cluster-scoped access |
| `career-agent-infrastructure-admin` | Manage platform/Terraform workflow and platform bootstrap | Not used for routine application sync or Git release approval |
| `career-agent-observability-readonly` | View ApplicationSet/Application sync, health, events, and evidence | No sync, rollback, Git write, or infrastructure mutation |

Requirements:

- Every privileged action requires a valid, non-expired Entra session.
- Argo CD MUST validate the tenant (`tid`), subject (`sub`), object (`oid`),
  and assigned group/app-role claims before authorizing a privileged action.
- Session expiry or revocation MUST invalidate the action before any desired
  state, sync, or rollback mutation is attempted.
- Group/app-role claims are mapped explicitly in Argo CD RBAC; the default role
  is read-only.
- Argo CD's repository credential and controller workload identity are separate
  from human principals and are scoped to the repository/ApplicationSet duties.
- Client secrets and tokens are stored in cluster secret management or workload
  identity configuration, never in Git, manifests, or audit payloads.
- Audit events include tenant, subject, resolved role, action, target
  environment, release version, result, and timestamp without credential data.

The non-secret mapping contract is materialized by
`config/argocd-oidc-rbac.yaml` and applied only by the platform-owned bootstrap
path. OIDC client secrets and token material remain outside Git.
